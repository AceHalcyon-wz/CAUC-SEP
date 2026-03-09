"""
本地TTL缓存模块

文件名: local_cache.py
路径: core/
功能: 本地内存缓存、TTL过期、LRU淘汰策略、线程安全
作者: Backend Engineer Agent
创建日期: 2026-03-08
依赖: threading, collections, time
"""

import asyncio
import logging
import time
from collections import OrderedDict
from collections.abc import Callable, Hashable
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from threading import RLock
from typing import Any, Generic, TypeVar

logger = logging.getLogger(__name__)

# 类型变量
K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


@dataclass
class CacheEntry(Generic[V]):
    """缓存条目。

    Attributes:
        value: 缓存值
        expire_at: 过期时间戳（None表示永不过期）
        created_at: 创建时间戳
        access_count: 访问次数
        last_access_at: 最后访问时间戳
    """

    value: V
    expire_at: float | None = None
    created_at: float = field(default_factory=time.time)
    access_count: int = 0
    last_access_at: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        """检查是否已过期。

        Returns:
            bool: 是否已过期
        """
        if self.expire_at is None:
            return False
        return time.time() > self.expire_at

    def touch(self) -> None:
        """更新访问信息。"""
        self.access_count += 1
        self.last_access_at = time.time()


@dataclass
class LocalCacheStatistics:
    """本地缓存统计信息。

    Attributes:
        hits: 命中次数
        misses: 未命中次数
        evictions: 淘汰次数（LRU或过期）
        size: 当前缓存大小
        max_size: 最大缓存大小
        total_access: 总访问次数
    """

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    max_size: int = 0
    total_access: int = 0

    @property
    def hit_rate(self) -> float:
        """计算命中率。

        Returns:
            float: 命中率（0.0-1.0）
        """
        if self.total_access == 0:
            return 0.0
        return self.hits / self.total_access


class TTLCache(Generic[K, V]):
    """
    带TTL和LRU淘汰策略的本地缓存。

    特性：
        - TTL过期自动清理
        - LRU淘汰策略
        - 线程安全
        - 统计监控
        - 支持批量操作

    Attributes:
        max_size: 最大缓存条目数
        default_ttl: 默认过期时间（秒）
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: float | None = 300.0,
        cleanup_interval: float = 60.0,
    ) -> None:
        """初始化TTL缓存。

        Args:
            max_size: 最大缓存条目数，0表示无限制
            default_ttl: 默认过期时间（秒），None表示永不过期
            cleanup_interval: 自动清理间隔（秒），0表示禁用自动清理
        """
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._cleanup_interval = cleanup_interval

        # 使用OrderedDict实现LRU
        self._cache: OrderedDict[K, CacheEntry[V]] = OrderedDict()
        self._lock = RLock()

        # 统计信息
        self._statistics = LocalCacheStatistics(max_size=max_size)

        # 自动清理任务
        self._cleanup_task: asyncio.Task[None] | None = None
        self._is_running = False

        logger.info(
            f"TTLCache initialized: max_size={max_size}, "
            f"default_ttl={default_ttl}s, cleanup_interval={cleanup_interval}s"
        )

    @property
    def max_size(self) -> int:
        """获取最大缓存大小。"""
        return self._max_size

    @property
    def default_ttl(self) -> float | None:
        """获取默认过期时间。"""
        return self._default_ttl

    def _evict_expired(self) -> int:
        """清理过期条目。

        Returns:
            int: 清理的条目数
        """
        evicted = 0
        keys_to_remove: list[K] = []

        for key, entry in self._cache.items():
            if entry.is_expired():
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._cache[key]
            evicted += 1

        if evicted > 0:
            with self._lock:
                self._statistics.evictions += evicted
                self._statistics.size = len(self._cache)
            logger.debug(f"Evicted {evicted} expired entries")

        return evicted

    def _evict_lru(self, count: int = 1) -> int:
        """LRU淘汰最少使用的条目。

        Args:
            count: 需要淘汰的条目数

        Returns:
            int: 实际淘汰的条目数
        """
        evicted = 0

        for _ in range(count):
            if not self._cache:
                break

            # OrderedDict的第一个元素是最久未访问的
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            evicted += 1

        if evicted > 0:
            self._statistics.evictions += evicted
            self._statistics.size = len(self._cache)
            logger.debug(f"LRU evicted {evicted} entries")

        return evicted

    def get(self, key: K) -> V | None:
        """获取缓存值。

        Args:
            key: 缓存键

        Returns:
            V | None: 缓存值，不存在或已过期返回None
        """
        with self._lock:
            self._statistics.total_access += 1

            if key not in self._cache:
                self._statistics.misses += 1
                return None

            entry = self._cache[key]

            # 检查是否过期
            if entry.is_expired():
                del self._cache[key]
                self._statistics.misses += 1
                self._statistics.evictions += 1
                self._statistics.size = len(self._cache)
                return None

            # 更新访问信息并移到末尾（LRU）
            entry.touch()
            self._cache.move_to_end(key)
            self._statistics.hits += 1

            return entry.value

    def set(
        self,
        key: K,
        value: V,
        ttl: float | None = None,
    ) -> None:
        """设置缓存值。

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None使用默认值
        """
        with self._lock:
            # 计算过期时间
            effective_ttl = ttl if ttl is not None else self._default_ttl
            expire_at = time.time() + effective_ttl if effective_ttl else None

            # 如果键已存在，先删除
            if key in self._cache:
                del self._cache[key]
            # 如果达到最大大小，执行LRU淘汰
            elif self._max_size > 0 and len(self._cache) >= self._max_size:
                self._evict_lru(1)

            # 创建缓存条目
            entry = CacheEntry(value=value, expire_at=expire_at)
            self._cache[key] = entry
            self._statistics.size = len(self._cache)

    def delete(self, key: K) -> bool:
        """删除缓存条目。

        Args:
            key: 缓存键

        Returns:
            bool: 是否删除成功
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._statistics.size = len(self._cache)
                return True
            return False

    def exists(self, key: K) -> bool:
        """检查键是否存在。

        Args:
            key: 缓存键

        Returns:
            bool: 是否存在且未过期
        """
        with self._lock:
            if key not in self._cache:
                return False

            entry = self._cache[key]
            if entry.is_expired():
                del self._cache[key]
                self._statistics.size = len(self._cache)
                return False

            return True

    def clear(self) -> None:
        """清空所有缓存。"""
        with self._lock:
            self._cache.clear()
            self._statistics.size = 0
            logger.info("Cache cleared")

    def get_or_set(
        self,
        key: K,
        factory: Callable[[], V],
        ttl: float | None = None,
    ) -> V:
        """获取缓存值，不存在则通过工厂函数创建并缓存。

        Args:
            key: 缓存键
            factory: 创建值的工厂函数
            ttl: 过期时间（秒）

        Returns:
            V: 缓存值或新创建的值
        """
        with self._lock:
            # 尝试获取
            value = self.get(key)
            if value is not None:
                return value

            # 创建新值
            value = factory()
            self.set(key, value, ttl)
            return value

    async def async_get_or_set(
        self,
        key: K,
        factory: Callable[[], V] | Callable[[], "asyncio.Future[V]"],
        ttl: float | None = None,
    ) -> V:
        """异步获取缓存值，不存在则通过工厂函数创建并缓存。

        Args:
            key: 缓存键
            factory: 创建值的工厂函数（同步或异步）
            ttl: 过期时间（秒）

        Returns:
            V: 缓存值或新创建的值
        """
        with self._lock:
            value = self.get(key)
            if value is not None:
                return value

        # 在锁外执行工厂函数
        result = factory()
        if asyncio.iscoroutine(result):
            value = await result
        else:
            value = result

        self.set(key, value, ttl)
        return value

    def mget(self, keys: list[K]) -> dict[K, V]:
        """批量获取缓存值。

        Args:
            keys: 缓存键列表

        Returns:
            dict[K, V]: 键值对字典
        """
        result: dict[K, V] = {}

        with self._lock:
            for key in keys:
                value = self.get(key)
                if value is not None:
                    result[key] = value

        return result

    def mset(self, mapping: dict[K, V], ttl: float | None = None) -> None:
        """批量设置缓存值。

        Args:
            mapping: 键值对字典
            ttl: 过期时间（秒）
        """
        with self._lock:
            for key, value in mapping.items():
                self.set(key, value, ttl)

    def cleanup(self) -> int:
        """手动清理过期条目。

        Returns:
            int: 清理的条目数
        """
        with self._lock:
            return self._evict_expired()

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息。

        Returns:
            dict[str, Any]: 统计信息字典
        """
        with self._lock:
            return {
                "hits": self._statistics.hits,
                "misses": self._statistics.misses,
                "evictions": self._statistics.evictions,
                "size": self._statistics.size,
                "max_size": self._statistics.max_size,
                "total_access": self._statistics.total_access,
                "hit_rate": self._statistics.hit_rate,
                "utilization": (
                    self._statistics.size / self._statistics.max_size
                    if self._statistics.max_size > 0
                    else 0
                ),
            }

    def get_all_keys(self) -> list[K]:
        """获取所有键。

        Returns:
            list[K]: 键列表
        """
        with self._lock:
            return list(self._cache.keys())

    def get_entry_info(self, key: K) -> dict[str, Any] | None:
        """获取缓存条目详情。

        Args:
            key: 缓存键

        Returns:
            dict[str, Any] | None: 条目信息，不存在返回None
        """
        with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]
            return {
                "key": key,
                "expire_at": (
                    datetime.fromtimestamp(entry.expire_at).isoformat() if entry.expire_at else None
                ),
                "created_at": datetime.fromtimestamp(entry.created_at).isoformat(),
                "access_count": entry.access_count,
                "last_access_at": datetime.fromtimestamp(entry.last_access_at).isoformat(),
                "ttl_remaining": (entry.expire_at - time.time() if entry.expire_at else None),
                "is_expired": entry.is_expired(),
            }

    async def start_cleanup_task(self) -> None:
        """启动自动清理任务。"""
        if self._cleanup_interval <= 0 or self._is_running:
            return

        self._is_running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info(f"Cache cleanup task started (interval: {self._cleanup_interval}s)")

    async def stop_cleanup_task(self) -> None:
        """停止自动清理任务。"""
        self._is_running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        logger.info("Cache cleanup task stopped")

    async def _cleanup_loop(self) -> None:
        """自动清理循环。"""
        while self._is_running:
            try:
                await asyncio.sleep(self._cleanup_interval)
                if self._is_running:
                    evicted = self.cleanup()
                    if evicted > 0:
                        logger.debug(f"Auto cleanup: evicted {evicted} entries")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")

    def __len__(self) -> int:
        """获取缓存大小。"""
        return len(self._cache)

    def __contains__(self, key: K) -> bool:
        """检查键是否存在。"""
        return self.exists(key)

    def __getitem__(self, key: K) -> V:
        """通过下标获取值。"""
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key: K, value: V) -> None:
        """通过下标设置值。"""
        self.set(key, value)

    def __delitem__(self, key: K) -> None:
        """通过下标删除值。"""
        if not self.delete(key):
            raise KeyError(key)


class LRUCache(TTLCache[K, V]):
    """
    纯LRU缓存（无TTL）。

    继承自TTLCache，默认禁用过期功能。
    """

    def __init__(self, max_size: int = 1000) -> None:
        """初始化LRU缓存。

        Args:
            max_size: 最大缓存条目数
        """
        super().__init__(max_size=max_size, default_ttl=None, cleanup_interval=0)


# ==================== 缓存装饰器 ====================


def local_cached(
    key: str | Callable[..., str] | None = None,
    ttl: float | None = 300.0,
    max_size: int = 1000,
    cache_instance: TTLCache | None = None,
) -> Callable[[Callable[..., V]], Callable[..., V]]:
    """
    本地缓存装饰器（同步函数）。

    Args:
        key: 缓存键模板，None则使用函数名+参数hash
        ttl: 过期时间（秒）
        max_size: 最大缓存大小
        cache_instance: 共享的缓存实例

    Returns:
        装饰器函数

    Example:
        >>> @local_cached("user:{user_id}", ttl=60)
        ... def get_user_name(user_id: int):
        ...     return db.query(User).get(user_id).name
    """
    # 创建或使用共享缓存实例
    cache = cache_instance or TTLCache(max_size=max_size, default_ttl=ttl)

    def decorator(func: Callable[..., V]) -> Callable[..., V]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> V:
            # 生成缓存键
            if callable(key):
                cache_key = key(*args, **kwargs)
            elif key is not None:
                try:
                    import inspect

                    sig = inspect.signature(func)
                    bound = sig.bind(*args, **kwargs)
                    bound.apply_defaults()
                    cache_key = key.format(**bound.arguments)
                except (KeyError, AttributeError):
                    cache_key = key
            else:
                # 使用函数名和参数生成键
                cache_key = f"{func.__name__}:{hash((args, tuple(sorted(kwargs.items()))))}"

            # 尝试从缓存获取
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # 执行函数并缓存
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result

        # 添加缓存实例引用
        wrapper.cache = cache  # type: ignore

        return wrapper

    return decorator


def async_local_cached(
    key: str | Callable[..., str] | None = None,
    ttl: float | None = 300.0,
    max_size: int = 1000,
    cache_instance: TTLCache | None = None,
) -> Callable[[Callable[..., V]], Callable[..., V]]:
    """
    本地缓存装饰器（异步函数）。

    Args:
        key: 缓存键模板
        ttl: 过期时间（秒）
        max_size: 最大缓存大小
        cache_instance: 共享的缓存实例

    Returns:
        装饰器函数

    Example:
        >>> @async_local_cached("device:{device_id}:config", ttl=120)
        ... async def get_device_config(device_id: str):
        ...     return await device.read_config()
    """
    cache = cache_instance or TTLCache(max_size=max_size, default_ttl=ttl)

    def decorator(func: Callable[..., V]) -> Callable[..., V]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> V:
            # 生成缓存键
            if callable(key):
                cache_key = key(*args, **kwargs)
            elif key is not None:
                try:
                    import inspect

                    sig = inspect.signature(func)
                    bound = sig.bind(*args, **kwargs)
                    bound.apply_defaults()
                    cache_key = key.format(**bound.arguments)
                except (KeyError, AttributeError):
                    cache_key = key
            else:
                cache_key = f"{func.__name__}:{hash((args, tuple(sorted(kwargs.items()))))}"

            # 尝试从缓存获取
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # 执行函数并缓存
            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result

        wrapper.cache = cache  # type: ignore

        return wrapper

    return decorator


# ==================== 全局缓存实例 ====================

# 设备状态缓存（高频访问，短TTL）
_device_status_cache: TTLCache[str, dict[str, Any]] = TTLCache(
    max_size=500,
    default_ttl=10.0,  # 10秒过期
    cleanup_interval=30.0,
)

# 设备配置缓存（低频更新，长TTL）
_device_config_cache: TTLCache[str, dict[str, Any]] = TTLCache(
    max_size=200,
    default_ttl=300.0,  # 5分钟过期
    cleanup_interval=60.0,
)

# 用户会话缓存
_user_session_cache: TTLCache[str, dict[str, Any]] = TTLCache(
    max_size=1000,
    default_ttl=1800.0,  # 30分钟过期
    cleanup_interval=300.0,
)


def get_device_status_cache() -> TTLCache[str, dict[str, Any]]:
    """获取设备状态缓存实例。"""
    return _device_status_cache


def get_device_config_cache() -> TTLCache[str, dict[str, Any]]:
    """获取设备配置缓存实例。"""
    return _device_config_cache


def get_user_session_cache() -> TTLCache[str, dict[str, Any]]:
    """获取用户会话缓存实例。"""
    return _user_session_cache


def get_all_local_cache_stats() -> dict[str, dict[str, Any]]:
    """获取所有本地缓存统计信息。

    Returns:
        dict: 各缓存的统计信息
    """
    return {
        "device_status": _device_status_cache.get_statistics(),
        "device_config": _device_config_cache.get_statistics(),
        "user_session": _user_session_cache.get_statistics(),
    }


async def start_all_cache_cleanup_tasks() -> None:
    """启动所有缓存的自动清理任务。"""
    await _device_status_cache.start_cleanup_task()
    await _device_config_cache.start_cleanup_task()
    await _user_session_cache.start_cleanup_task()
    logger.info("All local cache cleanup tasks started")


async def stop_all_cache_cleanup_tasks() -> None:
    """停止所有缓存的自动清理任务。"""
    await _device_status_cache.stop_cleanup_task()
    await _device_config_cache.stop_cleanup_task()
    await _user_session_cache.stop_cleanup_task()
    logger.info("All local cache cleanup tasks stopped")
