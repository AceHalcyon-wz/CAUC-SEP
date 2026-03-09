"""
Redis缓存管理器模块

文件名: cache.py
路径: core/
功能: Redis连接池管理、缓存操作、分布式缓存支持
作者: Backend Engineer Agent
创建日期: 2026-03-08
依赖: redis, asyncio
"""

import asyncio
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from threading import Lock
from typing import Any, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

# 类型变量，用于泛型装饰器
T = TypeVar("T")


class CacheBackend(Enum):
    """缓存后端类型枚举。"""

    REDIS = "redis"
    MEMORY = "memory"
    NONE = "none"  # 禁用缓存


@dataclass
class RedisConfig:
    """Redis连接配置。

    Attributes:
        host: Redis服务器地址
        port: Redis服务器端口
        db: Redis数据库编号
        password: Redis密码（可选）
        max_connections: 最大连接数
        socket_timeout: Socket超时时间（秒）
        socket_connect_timeout: 连接超时时间（秒）
        retry_on_timeout: 超时是否重试
        decode_responses: 是否自动解码响应
    """

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str | None = None
    max_connections: int = 10
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    retry_on_timeout: bool = True
    decode_responses: bool = True


@dataclass
class CacheStatistics:
    """缓存统计信息。

    Attributes:
        hits: 缓存命中次数
        misses: 缓存未命中次数
        sets: 设置缓存次数
        deletes: 删除缓存次数
        errors: 错误次数
        total_latency_ms: 总延迟（毫秒）
        last_error: 最后一次错误信息
        last_error_time: 最后一次错误时间
    """

    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    total_latency_ms: float = 0.0
    last_error: str | None = None
    last_error_time: datetime | None = None

    @property
    def hit_rate(self) -> float:
        """计算缓存命中率。

        Returns:
            float: 命中率（0.0-1.0）
        """
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total

    @property
    def avg_latency_ms(self) -> float:
        """计算平均延迟。

        Returns:
            float: 平均延迟（毫秒）
        """
        total_ops = self.hits + self.misses + self.sets + self.deletes
        if total_ops == 0:
            return 0.0
        return self.total_latency_ms / total_ops


class RedisCacheManager:
    """
    Redis缓存管理器。

    提供统一的Redis缓存操作接口，支持连接池、自动重连、统计监控。
    支持同步和异步两种操作模式。

    Attributes:
        config: Redis连接配置
        backend: 当前缓存后端类型
    """

    def __init__(
        self,
        config: RedisConfig | None = None,
        fallback_to_memory: bool = True,
        key_prefix: str = "cauc_sep:",
    ) -> None:
        """初始化Redis缓存管理器。

        Args:
            config: Redis连接配置
            fallback_to_memory: Redis不可用时是否回退到内存缓存
            key_prefix: 缓存键前缀
        """
        self._config = config or RedisConfig()
        self._fallback_to_memory = fallback_to_memory
        self._key_prefix = key_prefix
        self._backend = CacheBackend.NONE

        # Redis连接池
        self._sync_pool: Any | None = None
        self._async_pool: Any | None = None

        # 内存缓存回退
        self._memory_cache: dict[str, tuple[Any, float | None]] = {}
        self._memory_cache_lock = Lock()

        # 统计信息
        self._statistics = CacheStatistics()
        self._stats_lock = Lock()

        # 初始化连接
        self._initialize()

        logger.info(
            f"RedisCacheManager initialized: backend={self._backend.value}, "
            f"prefix={key_prefix}"
        )

    def _initialize(self) -> None:
        """初始化Redis连接池。"""
        try:
            import redis
            from redis.asyncio import ConnectionPool as AsyncConnectionPool

            # 创建同步连接池
            self._sync_pool = redis.ConnectionPool(
                host=self._config.host,
                port=self._config.port,
                db=self._config.db,
                password=self._config.password,
                max_connections=self._config.max_connections,
                socket_timeout=self._config.socket_timeout,
                socket_connect_timeout=self._config.socket_connect_timeout,
                retry_on_timeout=self._config.retry_on_timeout,
                decode_responses=self._config.decode_responses,
            )

            # 创建异步连接池
            self._async_pool = AsyncConnectionPool(
                host=self._config.host,
                port=self._config.port,
                db=self._config.db,
                password=self._config.password,
                max_connections=self._config.max_connections,
                socket_timeout=self._config.socket_timeout,
                socket_connect_timeout=self._config.socket_connect_timeout,
                decode_responses=self._config.decode_responses,
            )

            self._backend = CacheBackend.REDIS
            logger.info(
                f"Redis connection pool created: {self._config.host}:{self._config.port}"
            )

        except ImportError:
            logger.warning(
                "Redis package not installed, falling back to memory cache"
            )
            self._backend = CacheBackend.MEMORY if self._fallback_to_memory else CacheBackend.NONE
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            self._backend = CacheBackend.MEMORY if self._fallback_to_memory else CacheBackend.NONE

    def _make_key(self, key: str) -> str:
        """生成带前缀的缓存键。

        Args:
            key: 原始键名

        Returns:
            str: 带前缀的键名
        """
        return f"{self._key_prefix}{key}"

    def _record_latency(self, start_time: float) -> None:
        """记录操作延迟。

        Args:
            start_time: 开始时间（time.time()返回值）
        """
        latency_ms = (time.time() - start_time) * 1000
        with self._stats_lock:
            self._statistics.total_latency_ms += latency_ms

    def _record_error(self, error: Exception) -> None:
        """记录错误信息。

        Args:
            error: 异常对象
        """
        with self._stats_lock:
            self._statistics.errors += 1
            self._statistics.last_error = str(error)
            self._statistics.last_error_time = datetime.now()

    # ==================== 同步操作 ====================

    def get(self, key: str) -> Any | None:
        """获取缓存值（同步）。

        Args:
            key: 缓存键

        Returns:
            Any | None: 缓存值，不存在返回None
        """
        start_time = time.time()
        full_key = self._make_key(key)

        try:
            if self._backend == CacheBackend.REDIS:
                import redis

                client = redis.Redis(connection_pool=self._sync_pool)
                value = client.get(full_key)

                if value is not None:
                    with self._stats_lock:
                        self._statistics.hits += 1
                    self._record_latency(start_time)
                    return json.loads(value)

                with self._stats_lock:
                    self._statistics.misses += 1
                self._record_latency(start_time)
                return None

            elif self._backend == CacheBackend.MEMORY:
                with self._memory_cache_lock:
                    cached = self._memory_cache.get(full_key)
                    if cached is not None:
                        value, expire_at = cached
                        if expire_at is None or expire_at > time.time():
                            with self._stats_lock:
                                self._statistics.hits += 1
                            self._record_latency(start_time)
                            return value
                        # 已过期，删除
                        del self._memory_cache[full_key]

                    with self._stats_lock:
                        self._statistics.misses += 1
                    self._record_latency(start_time)
                    return None

            else:
                with self._stats_lock:
                    self._statistics.misses += 1
                return None

        except Exception as e:
            self._record_error(e)
            logger.error(f"Cache get error for key '{key}': {e}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """设置缓存值（同步）。

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None表示永不过期

        Returns:
            bool: 是否设置成功
        """
        start_time = time.time()
        full_key = self._make_key(key)

        try:
            if self._backend == CacheBackend.REDIS:
                import redis

                client = redis.Redis(connection_pool=self._sync_pool)
                serialized = json.dumps(value, ensure_ascii=False, default=str)

                if ttl:
                    result = client.setex(full_key, ttl, serialized)
                else:
                    result = client.set(full_key, serialized)

                with self._stats_lock:
                    self._statistics.sets += 1
                self._record_latency(start_time)
                return bool(result)

            elif self._backend == CacheBackend.MEMORY:
                with self._memory_cache_lock:
                    expire_at = time.time() + ttl if ttl else None
                    self._memory_cache[full_key] = (value, expire_at)

                with self._stats_lock:
                    self._statistics.sets += 1
                self._record_latency(start_time)
                return True

            else:
                return False

        except Exception as e:
            self._record_error(e)
            logger.error(f"Cache set error for key '{key}': {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除缓存值（同步）。

        Args:
            key: 缓存键

        Returns:
            bool: 是否删除成功
        """
        start_time = time.time()
        full_key = self._make_key(key)

        try:
            if self._backend == CacheBackend.REDIS:
                import redis

                client = redis.Redis(connection_pool=self._sync_pool)
                client.delete(full_key)

                with self._stats_lock:
                    self._statistics.deletes += 1
                self._record_latency(start_time)
                return True

            elif self._backend == CacheBackend.MEMORY:
                with self._memory_cache_lock:
                    self._memory_cache.pop(full_key, None)

                with self._stats_lock:
                    self._statistics.deletes += 1
                self._record_latency(start_time)
                return True

            else:
                return False

        except Exception as e:
            self._record_error(e)
            logger.error(f"Cache delete error for key '{key}': {e}")
            return False

    def exists(self, key: str) -> bool:
        """检查缓存键是否存在（同步）。

        Args:
            key: 缓存键

        Returns:
            bool: 是否存在
        """
        full_key = self._make_key(key)

        try:
            if self._backend == CacheBackend.REDIS:
                import redis

                client = redis.Redis(connection_pool=self._sync_pool)
                return bool(client.exists(full_key))

            elif self._backend == CacheBackend.MEMORY:
                with self._memory_cache_lock:
                    cached = self._memory_cache.get(full_key)
                    if cached is not None:
                        _, expire_at = cached
                        return expire_at is None or expire_at > time.time()
                    return False

            else:
                return False

        except Exception as e:
            self._record_error(e)
            logger.error(f"Cache exists error for key '{key}': {e}")
            return False

    def mget(self, keys: list[str]) -> dict[str, Any]:
        """批量获取缓存值（同步）。

        Args:
            keys: 缓存键列表

        Returns:
            dict[str, Any]: 键值对字典
        """
        if not keys:
            return {}

        start_time = time.time()
        full_keys = [self._make_key(k) for k in keys]
        result: dict[str, Any] = {}

        try:
            if self._backend == CacheBackend.REDIS:
                import redis

                client = redis.Redis(connection_pool=self._sync_pool)
                values = client.mget(full_keys)

                for i, value in enumerate(values):
                    if value is not None:
                        result[keys[i]] = json.loads(value)

                with self._stats_lock:
                    self._statistics.hits += len(result)
                    self._statistics.misses += len(keys) - len(result)
                self._record_latency(start_time)

            elif self._backend == CacheBackend.MEMORY:
                with self._memory_cache_lock:
                    for i, full_key in enumerate(full_keys):
                        cached = self._memory_cache.get(full_key)
                        if cached is not None:
                            value, expire_at = cached
                            if expire_at is None or expire_at > time.time():
                                result[keys[i]] = value
                                with self._stats_lock:
                                    self._statistics.hits += 1
                            else:
                                del self._memory_cache[full_key]
                                with self._stats_lock:
                                    self._statistics.misses += 1
                        else:
                            with self._stats_lock:
                                self._statistics.misses += 1
                self._record_latency(start_time)

            return result

        except Exception as e:
            self._record_error(e)
            logger.error(f"Cache mget error: {e}")
            return {}

    def mset(self, mapping: dict[str, Any], ttl: int | None = None) -> bool:
        """批量设置缓存值（同步）。

        Args:
            mapping: 键值对字典
            ttl: 过期时间（秒），None表示永不过期

        Returns:
            bool: 是否设置成功
        """
        if not mapping:
            return True

        start_time = time.time()

        try:
            if self._backend == CacheBackend.REDIS:
                import redis

                client = redis.Redis(connection_pool=self._sync_pool)
                pipe = client.pipeline()

                for key, value in mapping.items():
                    full_key = self._make_key(key)
                    serialized = json.dumps(value, ensure_ascii=False, default=str)
                    if ttl:
                        pipe.setex(full_key, ttl, serialized)
                    else:
                        pipe.set(full_key, serialized)

                pipe.execute()

                with self._stats_lock:
                    self._statistics.sets += len(mapping)
                self._record_latency(start_time)
                return True

            elif self._backend == CacheBackend.MEMORY:
                with self._memory_cache_lock:
                    expire_at = time.time() + ttl if ttl else None
                    for key, value in mapping.items():
                        full_key = self._make_key(key)
                        self._memory_cache[full_key] = (value, expire_at)

                with self._stats_lock:
                    self._statistics.sets += len(mapping)
                self._record_latency(start_time)
                return True

            else:
                return False

        except Exception as e:
            self._record_error(e)
            logger.error(f"Cache mset error: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """删除匹配模式的所有键（同步）。

        Args:
            pattern: 键模式（支持通配符*）

        Returns:
            int: 删除的键数量
        """
        full_pattern = self._make_key(pattern)
        deleted_count = 0

        try:
            if self._backend == CacheBackend.REDIS:
                import redis

                client = redis.Redis(connection_pool=self._sync_pool)
                keys = client.keys(full_pattern)
                if keys:
                    deleted_count = client.delete(*keys)

                with self._stats_lock:
                    self._statistics.deletes += deleted_count

            elif self._backend == CacheBackend.MEMORY:
                import fnmatch

                with self._memory_cache_lock:
                    keys_to_delete = [
                        k for k in self._memory_cache
                        if fnmatch.fnmatch(k, full_pattern)
                    ]
                    for k in keys_to_delete:
                        del self._memory_cache[k]
                    deleted_count = len(keys_to_delete)

                with self._stats_lock:
                    self._statistics.deletes += deleted_count

            return deleted_count

        except Exception as e:
            self._record_error(e)
            logger.error(f"Cache delete_pattern error for '{pattern}': {e}")
            return 0

    # ==================== 异步操作 ====================

    async def async_get(self, key: str) -> Any | None:
        """获取缓存值（异步）。

        Args:
            key: 缓存键

        Returns:
            Any | None: 缓存值，不存在返回None
        """
        start_time = time.time()
        full_key = self._make_key(key)

        try:
            if self._backend == CacheBackend.REDIS:
                from redis.asyncio import Redis

                client = Redis(connection_pool=self._async_pool)
                value = await client.get(full_key)

                if value is not None:
                    with self._stats_lock:
                        self._statistics.hits += 1
                    self._record_latency(start_time)
                    return json.loads(value)

                with self._stats_lock:
                    self._statistics.misses += 1
                self._record_latency(start_time)
                return None

            elif self._backend == CacheBackend.MEMORY:
                # 内存缓存使用同步操作
                return self.get(key)

            else:
                with self._stats_lock:
                    self._statistics.misses += 1
                return None

        except Exception as e:
            self._record_error(e)
            logger.error(f"Async cache get error for key '{key}': {e}")
            return None

    async def async_set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """设置缓存值（异步）。

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None表示永不过期

        Returns:
            bool: 是否设置成功
        """
        start_time = time.time()
        full_key = self._make_key(key)

        try:
            if self._backend == CacheBackend.REDIS:
                from redis.asyncio import Redis

                client = Redis(connection_pool=self._async_pool)
                serialized = json.dumps(value, ensure_ascii=False, default=str)

                if ttl:
                    result = await client.setex(full_key, ttl, serialized)
                else:
                    result = await client.set(full_key, serialized)

                with self._stats_lock:
                    self._statistics.sets += 1
                self._record_latency(start_time)
                return bool(result)

            elif self._backend == CacheBackend.MEMORY:
                # 内存缓存使用同步操作
                return self.set(key, value, ttl)

            else:
                return False

        except Exception as e:
            self._record_error(e)
            logger.error(f"Async cache set error for key '{key}': {e}")
            return False

    async def async_delete(self, key: str) -> bool:
        """删除缓存值（异步）。

        Args:
            key: 缓存键

        Returns:
            bool: 是否删除成功
        """
        start_time = time.time()
        full_key = self._make_key(key)

        try:
            if self._backend == CacheBackend.REDIS:
                from redis.asyncio import Redis

                client = Redis(connection_pool=self._async_pool)
                await client.delete(full_key)

                with self._stats_lock:
                    self._statistics.deletes += 1
                self._record_latency(start_time)
                return True

            elif self._backend == CacheBackend.MEMORY:
                return self.delete(key)

            else:
                return False

        except Exception as e:
            self._record_error(e)
            logger.error(f"Async cache delete error for key '{key}': {e}")
            return False

    async def async_mget(self, keys: list[str]) -> dict[str, Any]:
        """批量获取缓存值（异步）。

        Args:
            keys: 缓存键列表

        Returns:
            dict[str, Any]: 键值对字典
        """
        if not keys:
            return {}

        start_time = time.time()
        full_keys = [self._make_key(k) for k in keys]
        result: dict[str, Any] = {}

        try:
            if self._backend == CacheBackend.REDIS:
                from redis.asyncio import Redis

                client = Redis(connection_pool=self._async_pool)
                values = await client.mget(full_keys)

                for i, value in enumerate(values):
                    if value is not None:
                        result[keys[i]] = json.loads(value)

                with self._stats_lock:
                    self._statistics.hits += len(result)
                    self._statistics.misses += len(keys) - len(result)
                self._record_latency(start_time)

            elif self._backend == CacheBackend.MEMORY:
                return self.mget(keys)

            return result

        except Exception as e:
            self._record_error(e)
            logger.error(f"Async cache mget error: {e}")
            return {}

    async def async_mset(self, mapping: dict[str, Any], ttl: int | None = None) -> bool:
        """批量设置缓存值（异步）。

        Args:
            mapping: 键值对字典
            ttl: 过期时间（秒），None表示永不过期

        Returns:
            bool: 是否设置成功
        """
        if not mapping:
            return True

        start_time = time.time()

        try:
            if self._backend == CacheBackend.REDIS:
                from redis.asyncio import Redis

                client = Redis(connection_pool=self._async_pool)
                pipe = client.pipeline()

                for key, value in mapping.items():
                    full_key = self._make_key(key)
                    serialized = json.dumps(value, ensure_ascii=False, default=str)
                    if ttl:
                        pipe.setex(full_key, ttl, serialized)
                    else:
                        pipe.set(full_key, serialized)

                await pipe.execute()

                with self._stats_lock:
                    self._statistics.sets += len(mapping)
                self._record_latency(start_time)
                return True

            elif self._backend == CacheBackend.MEMORY:
                return self.mset(mapping, ttl)

            else:
                return False

        except Exception as e:
            self._record_error(e)
            logger.error(f"Async cache mset error: {e}")
            return False

    # ==================== 管理操作 ====================

    def get_statistics(self) -> dict[str, Any]:
        """获取缓存统计信息。

        Returns:
            dict[str, Any]: 统计信息字典
        """
        with self._stats_lock:
            stats = {
                "backend": self._backend.value,
                "key_prefix": self._key_prefix,
                "hits": self._statistics.hits,
                "misses": self._statistics.misses,
                "sets": self._statistics.sets,
                "deletes": self._statistics.deletes,
                "errors": self._statistics.errors,
                "hit_rate": self._statistics.hit_rate,
                "total_latency_ms": self._statistics.total_latency_ms,
                "avg_latency_ms": self._statistics.avg_latency_ms,
                "last_error": self._statistics.last_error,
                "last_error_time": (
                    self._statistics.last_error_time.isoformat()
                    if self._statistics.last_error_time
                    else None
                ),
            }

        if self._backend == CacheBackend.MEMORY:
            with self._memory_cache_lock:
                stats["memory_cache_size"] = len(self._memory_cache)

        if self._backend == CacheBackend.REDIS and self._sync_pool:
            stats["redis_pool_info"] = {
                "max_connections": self._config.max_connections,
                "host": self._config.host,
                "port": self._config.port,
                "db": self._config.db,
            }

        return stats

    def health_check(self) -> dict[str, Any]:
        """执行缓存健康检查。

        Returns:
            dict[str, Any]: 健康检查结果
        """
        result = {
            "healthy": True,
            "backend": self._backend.value,
            "timestamp": datetime.now().isoformat(),
            "errors": [],
        }

        try:
            if self._backend == CacheBackend.REDIS:
                import redis

                client = redis.Redis(connection_pool=self._sync_pool)
                client.ping()
                result["redis_ping"] = "passed"

            elif self._backend == CacheBackend.MEMORY:
                result["memory_cache_status"] = "active"

            else:
                result["healthy"] = False
                result["errors"].append("Cache backend is NONE")

        except Exception as e:
            result["healthy"] = False
            result["errors"].append(str(e))

        return result

    def clear(self) -> bool:
        """清空所有缓存（谨慎使用）。

        Returns:
            bool: 是否清空成功
        """
        try:
            if self._backend == CacheBackend.REDIS:
                import redis

                client = redis.Redis(connection_pool=self._sync_pool)
                # 只删除带前缀的键
                keys = client.keys(f"{self._key_prefix}*")
                if keys:
                    client.delete(*keys)

            elif self._backend == CacheBackend.MEMORY:
                with self._memory_cache_lock:
                    self._memory_cache.clear()

            logger.info(f"Cache cleared for prefix: {self._key_prefix}")
            return True

        except Exception as e:
            self._record_error(e)
            logger.error(f"Cache clear error: {e}")
            return False

    def close(self) -> None:
        """关闭连接池。"""
        try:
            if self._sync_pool:
                self._sync_pool.disconnect()
                self._sync_pool = None

            if self._async_pool:
                # 异步连接池需要异步关闭
                pass

            logger.info("RedisCacheManager closed")

        except Exception as e:
            logger.error(f"Error closing cache manager: {e}")

    async def async_close(self) -> None:
        """异步关闭连接池。"""
        try:
            if self._async_pool:
                await self._async_pool.disconnect()
                self._async_pool = None

            self.close()

        except Exception as e:
            logger.error(f"Error async closing cache manager: {e}")


# ==================== 缓存装饰器 ====================


def cached(
    key: str | Callable[..., str],
    ttl: int = 300,
    cache_manager: RedisCacheManager | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    缓存装饰器（同步函数）。

    自动缓存函数返回值，支持动态键名生成。

    Args:
        key: 缓存键，可以是字符串或生成键的函数
        ttl: 过期时间（秒）
        cache_manager: 缓存管理器实例，None则使用全局实例

    Returns:
        装饰器函数

    Example:
        >>> @cached("user:{user_id}", ttl=60)
        ... def get_user(user_id: int):
        ...     return db.query(User).get(user_id)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # 获取缓存管理器
            manager = cache_manager or _get_global_cache_manager()
            if manager is None:
                return func(*args, **kwargs)

            # 生成缓存键
            if callable(key):
                cache_key = key(*args, **kwargs)
            else:
                # 支持格式化占位符
                try:
                    # 获取函数参数名
                    import inspect
                    sig = inspect.signature(func)
                    bound = sig.bind(*args, **kwargs)
                    bound.apply_defaults()
                    cache_key = key.format(**bound.arguments)
                except (KeyError, AttributeError):
                    cache_key = key

            # 尝试从缓存获取
            cached_value = manager.get(cache_key)
            if cached_value is not None:
                return cached_value

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            manager.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator


def async_cached(
    key: str | Callable[..., str],
    ttl: int = 300,
    cache_manager: RedisCacheManager | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    缓存装饰器（异步函数）。

    自动缓存异步函数返回值，支持动态键名生成。

    Args:
        key: 缓存键，可以是字符串或生成键的函数
        ttl: 过期时间（秒）
        cache_manager: 缓存管理器实例，None则使用全局实例

    Returns:
        装饰器函数

    Example:
        >>> @async_cached("device:{device_id}:status", ttl=10)
        ... async def get_device_status(device_id: str):
        ...     return await device.read_status()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # 获取缓存管理器
            manager = cache_manager or _get_global_cache_manager()
            if manager is None:
                return await func(*args, **kwargs)

            # 生成缓存键
            if callable(key):
                cache_key = key(*args, **kwargs)
            else:
                try:
                    import inspect
                    sig = inspect.signature(func)
                    bound = sig.bind(*args, **kwargs)
                    bound.apply_defaults()
                    cache_key = key.format(**bound.arguments)
                except (KeyError, AttributeError):
                    cache_key = key

            # 尝试从缓存获取
            cached_value = await manager.async_get(cache_key)
            if cached_value is not None:
                return cached_value

            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            await manager.async_set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator


# ==================== 全局实例管理 ====================

_global_cache_manager: RedisCacheManager | None = None
_global_cache_lock = Lock()


def init_cache_manager(
    config: RedisConfig | None = None,
    fallback_to_memory: bool = True,
    key_prefix: str = "cauc_sep:",
) -> RedisCacheManager:
    """初始化全局缓存管理器。

    Args:
        config: Redis连接配置
        fallback_to_memory: Redis不可用时是否回退到内存缓存
        key_prefix: 缓存键前缀

    Returns:
        RedisCacheManager: 全局缓存管理器实例
    """
    global _global_cache_manager

    if _global_cache_manager is None:
        with _global_cache_lock:
            if _global_cache_manager is None:
                _global_cache_manager = RedisCacheManager(
                    config=config,
                    fallback_to_memory=fallback_to_memory,
                    key_prefix=key_prefix,
                )

    return _global_cache_manager


def get_cache_manager() -> RedisCacheManager | None:
    """获取全局缓存管理器。

    Returns:
        RedisCacheManager | None: 缓存管理器实例
    """
    return _global_cache_manager


def _get_global_cache_manager() -> RedisCacheManager | None:
    """内部函数：获取全局缓存管理器。"""
    return _global_cache_manager


# ==================== 便捷函数 ====================


def cache_get(key: str) -> Any | None:
    """便捷函数：获取缓存值。

    Args:
        key: 缓存键

    Returns:
        Any | None: 缓存值
    """
    manager = get_cache_manager()
    if manager:
        return manager.get(key)
    return None


def cache_set(key: str, value: Any, ttl: int | None = None) -> bool:
    """便捷函数：设置缓存值。

    Args:
        key: 缓存键
        value: 缓存值
        ttl: 过期时间（秒）

    Returns:
        bool: 是否设置成功
    """
    manager = get_cache_manager()
    if manager:
        return manager.set(key, value, ttl)
    return False


def cache_delete(key: str) -> bool:
    """便捷函数：删除缓存值。

    Args:
        key: 缓存键

    Returns:
        bool: 是否删除成功
    """
    manager = get_cache_manager()
    if manager:
        return manager.delete(key)
    return False


async def cache_async_get(key: str) -> Any | None:
    """便捷函数：异步获取缓存值。

    Args:
        key: 缓存键

    Returns:
        Any | None: 缓存值
    """
    manager = get_cache_manager()
    if manager:
        return await manager.async_get(key)
    return None


async def cache_async_set(key: str, value: Any, ttl: int | None = None) -> bool:
    """便捷函数：异步设置缓存值。

    Args:
        key: 缓存键
        value: 缓存值
        ttl: 过期时间（秒）

    Returns:
        bool: 是否设置成功
    """
    manager = get_cache_manager()
    if manager:
        return await manager.async_set(key, value, ttl)
    return False
