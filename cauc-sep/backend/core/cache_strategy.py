"""
设备状态缓存策略模块

文件名: cache_strategy.py
路径: core/
功能: 设备状态缓存装饰器、缓存失效策略、缓存预热、穿透保护
作者: Backend Engineer Agent
创建日期: 2026-03-08
依赖: cache.py, local_cache.py
"""

import asyncio
import hashlib
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from threading import Lock
from typing import Any, Optional, TypeVar

from core.cache import RedisCacheManager, get_cache_manager
from core.local_cache import TTLCache, get_device_config_cache, get_device_status_cache

logger = logging.getLogger(__name__)

# 类型变量
T = TypeVar("T")


class InvalidationType(Enum):
    """缓存失效类型枚举。"""

    TIME_BASED = "time_based"  # 基于时间的失效
    EVENT_BASED = "event_based"  # 基于事件的失效
    MANUAL = "manual"  # 手动失效
    DEPENDENCY = "dependency"  # 依赖失效


@dataclass
class CacheInvalidationEvent:
    """缓存失效事件。

    Attributes:
        event_type: 事件类型
        cache_key: 缓存键
        device_id: 设备ID
        timestamp: 时间戳
        reason: 失效原因
    """

    event_type: InvalidationType
    cache_key: str
    device_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    reason: str = ""


@dataclass
class CacheStrategy:
    """缓存策略配置。

    Attributes:
        ttl: 过期时间（秒）
        use_local_cache: 是否使用本地缓存
        use_redis_cache: 是否使用Redis缓存
        local_ttl: 本地缓存TTL（通常比Redis短）
        preload: 是否预热
        protect_penetration: 是否启用穿透保护
        penetration_ttl: 空值缓存TTL（秒）
    """

    ttl: int = 300
    use_local_cache: bool = True
    use_redis_cache: bool = True
    local_ttl: int = 10  # 本地缓存更短，保证实时性
    preload: bool = False
    protect_penetration: bool = True
    penetration_ttl: int = 60  # 空值缓存60秒


class CacheInvalidationManager:
    """
    缓存失效管理器。

    管理缓存的失效策略，支持基于时间和事件的失效机制。
    """

    def __init__(self) -> None:
        """初始化缓存失效管理器。"""
        self._invalidation_events: list[CacheInvalidationEvent] = []
        self._event_handlers: dict[str, list[Callable]] = {}
        self._dependency_map: dict[str, set[str]] = {}  # key -> dependent keys
        self._lock = Lock()

        logger.info("CacheInvalidationManager initialized")

    def register_event_handler(
        self,
        event_name: str,
        handler: Callable[[CacheInvalidationEvent], None],
    ) -> None:
        """注册事件处理器。

        Args:
            event_name: 事件名称
            handler: 处理函数
        """
        with self._lock:
            if event_name not in self._event_handlers:
                self._event_handlers[event_name] = []
            self._event_handlers[event_name].append(handler)

    def emit_event(self, event: CacheInvalidationEvent) -> None:
        """发送失效事件。

        Args:
            event: 失效事件
        """
        with self._lock:
            self._invalidation_events.append(event)
            # 保留最近1000个事件
            if len(self._invalidation_events) > 1000:
                self._invalidation_events = self._invalidation_events[-1000:]

        # 触发事件处理器
        handlers = self._event_handlers.get(event.event_type.value, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

    def add_dependency(self, key: str, depends_on: str) -> None:
        """添加缓存依赖关系。

        当 depends_on 失效时，key 也会失效。

        Args:
            key: 缓存键
            depends_on: 依赖的键
        """
        with self._lock:
            if depends_on not in self._dependency_map:
                self._dependency_map[depends_on] = set()
            self._dependency_map[depends_on].add(key)

    def invalidate_dependents(self, key: str) -> list[str]:
        """失效所有依赖键。

        Args:
            key: 触发失效的键

        Returns:
            list[str]: 被失效的键列表
        """
        invalidated: list[str] = []

        with self._lock:
            dependents = self._dependency_map.get(key, set()).copy()

        for dependent_key in dependents:
            # 递归失效
            invalidated.extend(self.invalidate_dependents(dependent_key))
            invalidated.append(dependent_key)

        return invalidated

    def get_recent_events(self, count: int = 100) -> list[CacheInvalidationEvent]:
        """获取最近的失效事件。

        Args:
            count: 事件数量

        Returns:
            list[CacheInvalidationEvent]: 事件列表
        """
        with self._lock:
            return self._invalidation_events[-count:]

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息。

        Returns:
            dict[str, Any]: 统计信息
        """
        with self._lock:
            event_counts: dict[str, int] = {}
            for event in self._invalidation_events:
                key = event.event_type.value
                event_counts[key] = event_counts.get(key, 0) + 1

            return {
                "total_events": len(self._invalidation_events),
                "event_counts": event_counts,
                "dependency_count": len(self._dependency_map),
            }


class DeviceStatusCacheManager:
    """
    设备状态缓存管理器。

    专门用于管理设备状态的缓存，支持：
    - 设备连接状态缓存
    - 设备配置信息缓存
    - 缓存自动刷新
    - 设备状态变更自动失效
    """

    def __init__(
        self,
        redis_manager: RedisCacheManager | None = None,
        invalidation_manager: CacheInvalidationManager | None = None,
    ) -> None:
        """初始化设备状态缓存管理器。

        Args:
            redis_manager: Redis缓存管理器
            invalidation_manager: 失效管理器
        """
        self._redis_manager = redis_manager or get_cache_manager()
        self._invalidation_manager = invalidation_manager or CacheInvalidationManager()
        self._local_status_cache = get_device_status_cache()
        self._local_config_cache = get_device_config_cache()

        # 设备状态变更监听器
        self._status_listeners: dict[str, list[Callable]] = {}
        self._lock = Lock()

        logger.info("DeviceStatusCacheManager initialized")

    def _make_status_key(self, device_id: str) -> str:
        """生成设备状态缓存键。

        Args:
            device_id: 设备ID

        Returns:
            str: 缓存键
        """
        return f"device:{device_id}:status"

    def _make_config_key(self, device_id: str) -> str:
        """生成设备配置缓存键。

        Args:
            device_id: 设备ID

        Returns:
            str: 缓存键
        """
        return f"device:{device_id}:config"

    # ==================== 状态缓存操作 ====================

    async def get_device_status(
        self,
        device_id: str,
        fetch_func: Callable[[], "asyncio.Future[dict[str, Any]]"] | None = None,
    ) -> dict[str, Any] | None:
        """获取设备状态（优先本地缓存）。

        Args:
            device_id: 设备ID
            fetch_func: 获取状态的异步函数

        Returns:
            dict[str, Any] | None: 设备状态
        """
        # 1. 尝试本地缓存
        local_key = self._make_status_key(device_id)
        cached = self._local_status_cache.get(local_key)
        if cached is not None:
            return cached

        # 2. 尝试Redis缓存
        if self._redis_manager:
            redis_cached = await self._redis_manager.async_get(local_key)
            if redis_cached is not None:
                # 回填本地缓存
                self._local_status_cache.set(local_key, redis_cached, ttl=10)
                return redis_cached

        # 3. 从数据源获取
        if fetch_func is not None:
            try:
                status = await fetch_func()
                if status:
                    # 缓存结果
                    await self.set_device_status(device_id, status)
                    return status
            except Exception as e:
                logger.error(f"Failed to fetch device status: {e}")

        return None

    async def set_device_status(
        self,
        device_id: str,
        status: dict[str, Any],
        ttl: int = 10,
    ) -> None:
        """设置设备状态缓存。

        Args:
            device_id: 设备ID
            status: 状态数据
            ttl: 过期时间（秒）
        """
        key = self._make_status_key(device_id)

        # 更新本地缓存
        self._local_status_cache.set(key, status, ttl=ttl)

        # 更新Redis缓存
        if self._redis_manager:
            await self._redis_manager.async_set(key, status, ttl=ttl)

    async def invalidate_device_status(self, device_id: str) -> None:
        """失效设备状态缓存。

        Args:
            device_id: 设备ID
        """
        key = self._make_status_key(device_id)

        # 删除本地缓存
        self._local_status_cache.delete(key)

        # 删除Redis缓存
        if self._redis_manager:
            await self._redis_manager.async_delete(key)

        # 发送失效事件
        self._invalidation_manager.emit_event(
            CacheInvalidationEvent(
                event_type=InvalidationType.EVENT_BASED,
                cache_key=key,
                device_id=device_id,
                reason="Device status changed",
            )
        )

        logger.debug(f"Invalidated device status cache: {device_id}")

    # ==================== 配置缓存操作 ====================

    async def get_device_config(
        self,
        device_id: str,
        fetch_func: Callable[[], "asyncio.Future[dict[str, Any]]"] | None = None,
    ) -> dict[str, Any] | None:
        """获取设备配置（优先本地缓存）。

        Args:
            device_id: 设备ID
            fetch_func: 获取配置的异步函数

        Returns:
            dict[str, Any] | None: 设备配置
        """
        local_key = self._make_config_key(device_id)

        # 1. 尝试本地缓存
        cached = self._local_config_cache.get(local_key)
        if cached is not None:
            return cached

        # 2. 尝试Redis缓存
        if self._redis_manager:
            redis_cached = await self._redis_manager.async_get(local_key)
            if redis_cached is not None:
                self._local_config_cache.set(local_key, redis_cached, ttl=300)
                return redis_cached

        # 3. 从数据源获取
        if fetch_func is not None:
            try:
                config = await fetch_func()
                if config:
                    await self.set_device_config(device_id, config)
                    return config
            except Exception as e:
                logger.error(f"Failed to fetch device config: {e}")

        return None

    async def set_device_config(
        self,
        device_id: str,
        config: dict[str, Any],
        ttl: int = 300,
    ) -> None:
        """设置设备配置缓存。

        Args:
            device_id: 设备ID
            config: 配置数据
            ttl: 过期时间（秒）
        """
        key = self._make_config_key(device_id)

        # 更新本地缓存
        self._local_config_cache.set(key, config, ttl=ttl)

        # 更新Redis缓存
        if self._redis_manager:
            await self._redis_manager.async_set(key, config, ttl=ttl)

    async def invalidate_device_config(self, device_id: str) -> None:
        """失效设备配置缓存。

        Args:
            device_id: 设备ID
        """
        key = self._make_config_key(device_id)

        # 删除本地缓存
        self._local_config_cache.delete(key)

        # 删除Redis缓存
        if self._redis_manager:
            await self._redis_manager.async_delete(key)

        # 发送失效事件
        self._invalidation_manager.emit_event(
            CacheInvalidationEvent(
                event_type=InvalidationType.EVENT_BASED,
                cache_key=key,
                device_id=device_id,
                reason="Device config changed",
            )
        )

        logger.debug(f"Invalidated device config cache: {device_id}")

    # ==================== 批量操作 ====================

    async def invalidate_all_device_cache(self, device_id: str) -> None:
        """失效设备的所有缓存。

        Args:
            device_id: 设备ID
        """
        await self.invalidate_device_status(device_id)
        await self.invalidate_device_config(device_id)

        # 失效依赖键
        dependent_keys = self._invalidation_manager.invalidate_dependents(f"device:{device_id}")
        for key in dependent_keys:
            self._local_status_cache.delete(key)
            self._local_config_cache.delete(key)
            if self._redis_manager:
                await self._redis_manager.async_delete(key)

    async def refresh_device_status(
        self,
        device_id: str,
        fetch_func: Callable[[], "asyncio.Future[dict[str, Any]]"],
    ) -> dict[str, Any] | None:
        """强制刷新设备状态缓存。

        Args:
            device_id: 设备ID
            fetch_func: 获取状态的异步函数

        Returns:
            dict[str, Any] | None: 新的状态数据
        """
        try:
            status = await fetch_func()
            if status:
                await self.set_device_status(device_id, status)
                return status
        except Exception as e:
            logger.error(f"Failed to refresh device status: {e}")

        return None

    # ==================== 状态变更监听 ====================

    def register_status_listener(
        self,
        device_id: str,
        listener: Callable[[str, dict[str, Any]], None],
    ) -> None:
        """注册设备状态变更监听器。

        Args:
            device_id: 设备ID
            listener: 监听函数
        """
        with self._lock:
            if device_id not in self._status_listeners:
                self._status_listeners[device_id] = []
            self._status_listeners[device_id].append(listener)

    async def notify_status_change(
        self,
        device_id: str,
        new_status: dict[str, Any],
    ) -> None:
        """通知设备状态变更。

        Args:
            device_id: 设备ID
            new_status: 新状态
        """
        # 更新缓存
        await self.set_device_status(device_id, new_status)

        # 触发监听器
        listeners = self._status_listeners.get(device_id, [])
        for listener in listeners:
            try:
                result = listener(device_id, new_status)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Status listener error: {e}")

    def get_statistics(self) -> dict[str, Any]:
        """获取缓存统计信息。

        Returns:
            dict[str, Any]: 统计信息
        """
        return {
            "local_status_cache": self._local_status_cache.get_statistics(),
            "local_config_cache": self._local_config_cache.get_statistics(),
            "invalidation": self._invalidation_manager.get_statistics(),
            "redis_available": self._redis_manager is not None,
        }


# ==================== 缓存穿透保护 ====================


class CachePenetrationProtector:
    """
    缓存穿透保护器。

    防止恶意请求穿透缓存直接访问数据源。
    使用空值缓存和布隆过滤器两种策略。
    """

    def __init__(
        self,
        null_cache: TTLCache[str, bool] | None = None,
        null_cache_ttl: int = 60,
    ) -> None:
        """初始化穿透保护器。

        Args:
            null_cache: 空值缓存实例
            null_cache_ttl: 空值缓存TTL
        """
        self._null_cache = null_cache or TTLCache(
            max_size=10000,
            default_ttl=null_cache_ttl,
        )
        self._null_cache_ttl = null_cache_ttl
        self._lock = Lock()

        # 统计
        self._blocked_count = 0
        self._allowed_count = 0

        logger.info("CachePenetrationProtector initialized")

    def _make_null_key(self, key: str) -> str:
        """生成空值缓存键。"""
        return f"null:{hashlib.md5(key.encode()).hexdigest()}"

    def is_null_cached(self, key: str) -> bool:
        """检查键是否被标记为空值。

        Args:
            key: 缓存键

        Returns:
            bool: 是否为空值
        """
        null_key = self._make_null_key(key)
        return self._null_cache.exists(null_key)

    def mark_as_null(self, key: str) -> None:
        """将键标记为空值。

        Args:
            key: 缓存键
        """
        null_key = self._make_null_key(key)
        self._null_cache.set(null_key, True, ttl=self._null_cache_ttl)

    def clear_null_mark(self, key: str) -> None:
        """清除空值标记。

        Args:
            key: 缓存键
        """
        null_key = self._make_null_key(key)
        self._null_cache.delete(null_key)

    async def get_with_protection(
        self,
        key: str,
        fetch_func: Callable[[], "asyncio.Future[T | None]"],
        cache_get: Callable[[str], T | None],
        cache_set: Callable[[str, T, int | None], None],
        ttl: int = 300,
    ) -> T | None:
        """带穿透保护的获取操作。

        Args:
            key: 缓存键
            fetch_func: 数据获取函数
            cache_get: 缓存获取函数
            cache_set: 缓存设置函数
            ttl: 缓存TTL

        Returns:
            T | None: 数据值
        """
        # 1. 检查是否为空值
        if self.is_null_cached(key):
            with self._lock:
                self._blocked_count += 1
            logger.debug(f"Blocked penetration for key: {key}")
            return None

        # 2. 尝试从缓存获取
        cached = cache_get(key)
        if cached is not None:
            return cached

        # 3. 从数据源获取
        try:
            value = await fetch_func()
            with self._lock:
                self._allowed_count += 1

            if value is not None:
                # 缓存有效值
                cache_set(key, value, ttl)
                return value
            else:
                # 标记为空值
                self.mark_as_null(key)
                return None

        except Exception as e:
            logger.error(f"Fetch error for key '{key}': {e}")
            return None

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息。"""
        with self._lock:
            return {
                "blocked_count": self._blocked_count,
                "allowed_count": self._allowed_count,
                "null_cache_size": len(self._null_cache),
                "block_rate": (
                    self._blocked_count / (self._blocked_count + self._allowed_count)
                    if (self._blocked_count + self._allowed_count) > 0
                    else 0
                ),
            }


# ==================== 缓存预热 ====================


class CachePreloader:
    """
    缓存预热器。

    在系统启动或特定时机预加载热点数据到缓存。
    """

    def __init__(
        self,
        device_cache_manager: DeviceStatusCacheManager | None = None,
    ) -> None:
        """初始化缓存预热器。

        Args:
            device_cache_manager: 设备缓存管理器
        """
        self._device_cache_manager = device_cache_manager
        self._preload_tasks: list[Callable] = []
        self._lock = Lock()

        logger.info("CachePreloader initialized")

    def register_preload_task(self, task: Callable[[], "asyncio.Future[None]"]) -> None:
        """注册预热任务。

        Args:
            task: 预热任务函数
        """
        with self._lock:
            self._preload_tasks.append(task)

    async def preload_all(self) -> dict[str, bool]:
        """执行所有预热任务。

        Returns:
            dict[str, bool]: 各任务的执行结果
        """
        results: dict[str, bool] = {}

        with self._lock:
            tasks = self._preload_tasks.copy()

        for i, task in enumerate(tasks):
            task_name = getattr(task, "__name__", f"task_{i}")
            try:
                await task()
                results[task_name] = True
                logger.info(f"Preload task completed: {task_name}")
            except Exception as e:
                results[task_name] = False
                logger.error(f"Preload task failed: {task_name} - {e}")

        return results

    async def preload_device_configs(
        self,
        device_ids: list[str],
        fetch_func: Callable[[str], "asyncio.Future[dict[str, Any]]"],
    ) -> dict[str, bool]:
        """预热设备配置缓存。

        Args:
            device_ids: 设备ID列表
            fetch_func: 获取配置的函数

        Returns:
            dict[str, bool]: 各设备的预热结果
        """
        if not self._device_cache_manager:
            logger.warning("DeviceCacheManager not set, skipping preload")
            return {}

        results: dict[str, bool] = {}

        for device_id in device_ids:
            try:
                config = await fetch_func(device_id)
                if config:
                    await self._device_cache_manager.set_device_config(device_id, config)
                    results[device_id] = True
                else:
                    results[device_id] = False
            except Exception as e:
                results[device_id] = False
                logger.error(f"Failed to preload config for {device_id}: {e}")

        logger.info(f"Preloaded {sum(results.values())}/{len(device_ids)} device configs")
        return results


# ==================== 设备状态缓存装饰器 ====================


def device_status_cached(
    device_id_param: str = "device_id",
    ttl: int = 10,
    use_local: bool = True,
    use_redis: bool = True,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    设备状态缓存装饰器。

    自动缓存设备状态数据，支持本地和Redis双层缓存。

    Args:
        device_id_param: 设备ID参数名
        ttl: 缓存TTL（秒）
        use_local: 是否使用本地缓存
        use_redis: 是否使用Redis缓存

    Returns:
        装饰器函数

    Example:
        >>> @device_status_cached(device_id_param="device_id", ttl=10)
        ... async def get_motor_status(device_id: str):
        ...     return await motor.read_status()
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            import inspect

            # 获取设备ID
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            device_id = bound.arguments.get(device_id_param)

            if not device_id:
                return await func(*args, **kwargs)

            # 生成缓存键
            cache_key = f"device:{device_id}:status"

            # 尝试本地缓存
            if use_local:
                local_cache = get_device_status_cache()
                cached = local_cache.get(cache_key)
                if cached is not None:
                    return cached

            # 尝试Redis缓存
            redis_manager = get_cache_manager()
            if use_redis and redis_manager:
                redis_cached = await redis_manager.async_get(cache_key)
                if redis_cached is not None:
                    # 回填本地缓存
                    if use_local:
                        local_cache = get_device_status_cache()
                        local_cache.set(cache_key, redis_cached, ttl=ttl)
                    return redis_cached

            # 执行函数
            result = await func(*args, **kwargs)

            # 缓存结果
            if result is not None:
                if use_local:
                    local_cache = get_device_status_cache()
                    local_cache.set(cache_key, result, ttl=ttl)
                if use_redis and redis_manager:
                    await redis_manager.async_set(cache_key, result, ttl=ttl)

            return result

        return wrapper

    return decorator


def device_config_cached(
    device_id_param: str = "device_id",
    ttl: int = 300,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    设备配置缓存装饰器。

    自动缓存设备配置数据，使用较长的TTL。

    Args:
        device_id_param: 设备ID参数名
        ttl: 缓存TTL（秒）

    Returns:
        装饰器函数

    Example:
        >>> @device_config_cached(device_id_param="device_id", ttl=300)
        ... async def get_motor_config(device_id: str):
        ...     return await motor.read_config()
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            import inspect

            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            device_id = bound.arguments.get(device_id_param)

            if not device_id:
                return await func(*args, **kwargs)

            cache_key = f"device:{device_id}:config"

            # 尝试本地缓存
            local_cache = get_device_config_cache()
            cached = local_cache.get(cache_key)
            if cached is not None:
                return cached

            # 尝试Redis缓存
            redis_manager = get_cache_manager()
            if redis_manager:
                redis_cached = await redis_manager.async_get(cache_key)
                if redis_cached is not None:
                    local_cache.set(cache_key, redis_cached, ttl=ttl)
                    return redis_cached

            # 执行函数
            result = await func(*args, **kwargs)

            # 缓存结果
            if result is not None:
                local_cache.set(cache_key, result, ttl=ttl)
                if redis_manager:
                    await redis_manager.async_set(cache_key, result, ttl=ttl)

            return result

        return wrapper

    return decorator


# ==================== 全局实例 ====================

_global_invalidation_manager: CacheInvalidationManager | None = None
_global_device_cache_manager: DeviceStatusCacheManager | None = None
_global_penetration_protector: CachePenetrationProtector | None = None
_global_preloader: CachePreloader | None = None


def get_invalidation_manager() -> CacheInvalidationManager:
    """获取全局失效管理器。"""
    global _global_invalidation_manager
    if _global_invalidation_manager is None:
        _global_invalidation_manager = CacheInvalidationManager()
    return _global_invalidation_manager


def get_device_cache_manager() -> DeviceStatusCacheManager:
    """获取全局设备缓存管理器。"""
    global _global_device_cache_manager
    if _global_device_cache_manager is None:
        _global_device_cache_manager = DeviceStatusCacheManager(
            invalidation_manager=get_invalidation_manager(),
        )
    return _global_device_cache_manager


def get_penetration_protector() -> CachePenetrationProtector:
    """获取全局穿透保护器。"""
    global _global_penetration_protector
    if _global_penetration_protector is None:
        _global_penetration_protector = CachePenetrationProtector()
    return _global_penetration_protector


def get_preloader() -> CachePreloader:
    """获取全局预热器。"""
    global _global_preloader
    if _global_preloader is None:
        _global_preloader = CachePreloader(
            device_cache_manager=get_device_cache_manager(),
        )
    return _global_preloader


def get_all_cache_stats() -> dict[str, Any]:
    """获取所有缓存统计信息。"""
    return {
        "device_cache": get_device_cache_manager().get_statistics(),
        "penetration_protector": get_penetration_protector().get_statistics(),
        "invalidation": get_invalidation_manager().get_statistics(),
    }
