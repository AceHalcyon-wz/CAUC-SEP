"""
缓存系统子模块

文件名: __init__.py
路径: backend/core/cache/
功能: 提供统一的缓存管理接口，支持Redis和本地内存缓存
作者: Backend Engineer Agent
创建日期: 2024-01-15
更新日期: 2026-03-14
版本: 1.0.0

核心功能：
    - Redis缓存管理（分布式缓存）
    - 本地内存缓存（进程内缓存）
    - 缓存策略实现（LRU、TTL）
    - 缓存清理任务（自动过期清理）

导出组件：
    - CacheManager: 缓存管理器主类
    - CacheBackend: 缓存后端枚举
    - RedisConfig: Redis配置类
    - CacheStrategy: 缓存策略基类
    - LRUStrategy: LRU缓存策略
    - TTLStrategy: TTL缓存策略
    - LocalCache: 本地缓存实现

依赖：
    - redis: Redis客户端（可选，用于分布式缓存）
    - asyncio: 异步IO支持
    - typing: 类型注解支持

使用示例：
    >>> from backend.core.cache import CacheManager, LocalCache, LRUStrategy
    >>> 
    >>> # 初始化缓存管理器
    >>> await init_cache_manager(backend="local")
    >>> cache = get_cache_manager()
    >>> 
    >>> # 使用本地缓存
    >>> local_cache = LocalCache(max_size=1000, default_ttl=300)
    >>> await local_cache.set("key", "value")
    >>> value = await local_cache.get("key")
"""

from .cache import (
    CacheBackend,
    CacheManager,
    RedisConfig,
    get_cache_manager,
    init_cache_manager,
)
from .cache_strategy import CacheStrategy, LRUStrategy, TTLStrategy
from .local_cache import (
    LocalCache,
    start_all_cache_cleanup_tasks,
    stop_all_cache_cleanup_tasks,
)

__all__ = [
    "CacheManager",
    "CacheBackend",
    "RedisConfig",
    "get_cache_manager",
    "init_cache_manager",
    "CacheStrategy",
    "LRUStrategy",
    "TTLStrategy",
    "LocalCache",
    "start_all_cache_cleanup_tasks",
    "stop_all_cache_cleanup_tasks",
]
