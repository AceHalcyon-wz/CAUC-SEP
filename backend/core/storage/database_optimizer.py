"""
数据库优化模块

文件名: database_optimizer.py
路径: backend/core/storage/
功能: SQLite数据库软件层面优化、缓存机制、批量写入优化、HDF5采集数据优化
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: sqlite3, sqlalchemy, h5py, numpy

模块内容:
    - SQLiteOptimizedConnection: SQLite连接优化器
    - DatabaseCacheManager: 数据库缓存管理器
    - BatchWriteManager: 批量写入管理器
    - HDF5StorageManager: HDF5采集数据存储管理器
    - DatabaseOptimizer: 综合数据库优化器
"""

import asyncio
import gzip
import json
import logging
import os
import sqlite3
import threading
import time
import zlib
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from threading import Lock
from threading import RLock
from typing import Any
from typing import Callable

import numpy as np
from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


# ==================== 常量定义 ====================

# SQLite PRAGMA配置常量
SQLITE_JOURNAL_MODE_WAL = "WAL"
SQLITE_SYNC_MODE_NORMAL = "NORMAL"
SQLITE_SYNC_MODE_FULL = "FULL"
SQLITE_SYNC_MODE_OFF = "OFF"
SQLITE_TEMP_STORE_MEMORY = "MEMORY"
SQLITE_TEMP_STORE_FILE = "FILE"

# 默认缓存配置
DEFAULT_CACHE_SIZE_MB = 64
DEFAULT_CACHE_TTL_SECONDS = 300
DEFAULT_BATCH_SIZE = 1000
DEFAULT_FLUSH_INTERVAL_SECONDS = 5

# HDF5配置
HDF5_CHUNK_SIZE = 10000
HDF5_COMPRESSION_LEVEL = 6


@dataclass
class SQLiteOptimizationConfig:
    """SQLite优化配置。

    Attributes:
        journal_mode: 日志模式（WAL/DELETE/TRUNCATE/PERSIST/MEMORY）
        synchronous: 同步模式（OFF/NORMAL/FULL）
        cache_size_mb: 缓存大小（MB）
        temp_store: 临时存储位置（MEMORY/FILE）
        busy_timeout_ms: 忙等待超时（毫秒）
        foreign_keys: 是否启用外键约束
        mmap_size_mb: 内存映射大小（MB），0表示禁用
        page_size: 页大小（字节），必须是2的幂
    """

    journal_mode: str = SQLITE_JOURNAL_MODE_WAL
    synchronous: str = SQLITE_SYNC_MODE_NORMAL
    cache_size_mb: int = DEFAULT_CACHE_SIZE_MB
    temp_store: str = SQLITE_TEMP_STORE_MEMORY
    busy_timeout_ms: int = 30000
    foreign_keys: bool = True
    mmap_size_mb: int = 0
    page_size: int = 4096


@dataclass
class CacheConfig:
    """缓存配置。

    Attributes:
        max_size: 最大缓存条目数
        default_ttl: 默认过期时间（秒）
        cleanup_interval: 清理间隔（秒）
        enable_statistics: 是否启用统计
    """

    max_size: int = 10000
    default_ttl: float = DEFAULT_CACHE_TTL_SECONDS
    cleanup_interval: float = 60.0
    enable_statistics: bool = True


@dataclass
class BatchWriteConfig:
    """批量写入配置。

    Attributes:
        batch_size: 批量大小
        flush_interval: 刷新间隔（秒）
        max_retries: 最大重试次数
        retry_delay: 重试延迟（秒）
    """

    batch_size: int = DEFAULT_BATCH_SIZE
    flush_interval: float = DEFAULT_FLUSH_INTERVAL_SECONDS
    max_retries: int = 3
    retry_delay: float = 0.1


@dataclass
class HDF5Config:
    """HDF5存储配置。

    Attributes:
        chunk_size: 分块大小
        compression_level: 压缩级别（0-9）
        compression_algorithm: 压缩算法（gzip/lzf/zlib）
        enable_checksum: 是否启用校验和
        max_file_size_mb: 单文件最大大小（MB）
    """

    chunk_size: int = HDF5_CHUNK_SIZE
    compression_level: int = HDF5_COMPRESSION_LEVEL
    compression_algorithm: str = "gzip"
    enable_checksum: bool = True
    max_file_size_mb: int = 1024


@dataclass
class DatabaseStatistics:
    """数据库统计信息。

    Attributes:
        total_queries: 总查询次数
        total_writes: 总写入次数
        cache_hits: 缓存命中次数
        cache_misses: 缓存未命中次数
        batch_writes: 批量写入次数
        avg_query_time_ms: 平均查询时间（毫秒）
        avg_write_time_ms: 平均写入时间（毫秒）
        last_optimization: 最后优化时间
    """

    total_queries: int = 0
    total_writes: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    batch_writes: int = 0
    avg_query_time_ms: float = 0.0
    avg_write_time_ms: float = 0.0
    last_optimization: datetime | None = None
    _lock: Lock = field(default_factory=Lock, repr=False)

    def update_query_time(self, duration_ms: float) -> None:
        """更新查询时间统计。"""
        with self._lock:
            self.total_queries += 1
            self.avg_query_time_ms = (
                self.avg_query_time_ms * (self.total_queries - 1) + duration_ms
            ) / self.total_queries

    def update_write_time(self, duration_ms: float) -> None:
        """更新写入时间统计。"""
        with self._lock:
            self.total_writes += 1
            self.avg_write_time_ms = (
                self.avg_write_time_ms * (self.total_writes - 1) + duration_ms
            ) / self.total_writes


class SQLiteOptimizedConnection:
    """
    SQLite优化连接管理器。

    提供SQLite数据库连接的优化配置，包括WAL模式、
    同步模式、缓存大小、内存映射等优化设置。

    Attributes:
        db_path: 数据库文件路径
        config: SQLite优化配置
    """

    def __init__(
        self,
        db_path: str,
        config: SQLiteOptimizationConfig | None = None,
    ) -> None:
        """
        初始化SQLite优化连接管理器。

        Args:
            db_path: 数据库文件路径
            config: SQLite优化配置，None使用默认配置
        """
        self._db_path = db_path
        self._config = config or SQLiteOptimizationConfig()
        self._engine: Engine | None = None
        self._session_factory: sessionmaker | None = None
        self._lock = RLock()

        # 初始化引擎
        self._initialize_engine()

        logger.info(
            f"SQLiteOptimizedConnection initialized: {db_path}, "
            f"journal={self._config.journal_mode}, "
            f"sync={self._config.synchronous}"
        )

    def _initialize_engine(self) -> None:
        """初始化SQLAlchemy引擎。"""
        # 创建引擎
        self._engine = create_engine(
            f"sqlite:///{self._db_path}",
            connect_args={
                "check_same_thread": False,
                "timeout": 30,
                "isolation_level": None,  # 自动提交模式
            },
            pool_pre_ping=True,
            pool_recycle=3600,
        )

        # 设置SQLite PRAGMA优化
        @event.listens_for(self._engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """设置SQLite性能优化参数。"""
            cursor = dbapi_connection.cursor()

            # 启用外键约束
            if self._config.foreign_keys:
                cursor.execute("PRAGMA foreign_keys=ON")

            # 设置日志模式为WAL（提高并发性能）
            cursor.execute(f"PRAGMA journal_mode={self._config.journal_mode}")

            # 设置同步模式（性能与安全平衡）
            cursor.execute(f"PRAGMA synchronous={self._config.synchronous}")

            # 设置缓存大小（单位：页，每页约4KB）
            # 负数表示以KB为单位
            cache_size_pages = -self._config.cache_size_mb * 1024
            cursor.execute(f"PRAGMA cache_size={cache_size_pages}")

            # 设置临时存储在内存中
            cursor.execute(f"PRAGMA temp_store={self._config.temp_store}")

            # 设置忙等待时间（毫秒）
            cursor.execute(f"PRAGMA busy_timeout={self._config.busy_timeout_ms}")

            # 设置内存映射大小（字节）
            if self._config.mmap_size_mb > 0:
                mmap_size_bytes = self._config.mmap_size_mb * 1024 * 1024
                cursor.execute(f"PRAGMA mmap_size={mmap_size_bytes}")

            # 设置页大小（仅在创建数据库时有效）
            # cursor.execute(f"PRAGMA page_size={self._config.page_size}")

            cursor.close()

        # 创建会话工厂
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

    @contextmanager
    def get_session(self) -> Session:
        """
        获取数据库会话（上下文管理器）。

        Yields:
            Session: 数据库会话实例

        Example:
            >>> with conn.get_session() as session:
            ...     user = session.query(User).first()
        """
        if not self._session_factory:
            raise RuntimeError("Database engine not initialized")

        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_engine(self) -> Engine:
        """
        获取SQLAlchemy引擎。

        Returns:
            Engine: SQLAlchemy引擎实例
        """
        if not self._engine:
            raise RuntimeError("Database engine not initialized")
        return self._engine

    def execute_pragma(self, pragma: str, value: str | int) -> Any:
        """
        执行PRAGMA命令。

        Args:
            pragma: PRAGMA名称
            value: PRAGMA值

        Returns:
            执行结果
        """
        with self._engine.connect() as conn:
            result = conn.execute(text(f"PRAGMA {pragma}={value}"))
            return result.scalar()

    def get_pragma_value(self, pragma: str) -> Any:
        """
        获取PRAGMA当前值。

        Args:
            pragma: PRAGMA名称

        Returns:
            PRAGMA当前值
        """
        with self._engine.connect() as conn:
            result = conn.execute(text(f"PRAGMA {pragma}"))
            return result.scalar()

    def get_database_info(self) -> dict[str, Any]:
        """
        获取数据库信息。

        Returns:
            数据库信息字典
        """
        info = {
            "db_path": self._db_path,
            "journal_mode": self.get_pragma_value("journal_mode"),
            "synchronous": self.get_pragma_value("synchronous"),
            "cache_size": self.get_pragma_value("cache_size"),
            "temp_store": self.get_pragma_value("temp_store"),
            "busy_timeout": self.get_pragma_value("busy_timeout"),
            "foreign_keys": self.get_pragma_value("foreign_keys"),
            "mmap_size": self.get_pragma_value("mmap_size"),
            "page_count": self.get_pragma_value("page_count"),
            "page_size": self.get_pragma_value("page_size"),
        }

        # 计算数据库大小
        if os.path.exists(self._db_path):
            info["file_size_mb"] = os.path.getsize(self._db_path) / (1024 * 1024)

        return info

    def optimize_database(self) -> dict[str, Any]:
        """
        执行数据库优化操作。

        包括VACUUM、ANALYZE、优化索引等。

        Returns:
            优化结果字典
        """
        result = {
            "vacuum": False,
            "analyze": False,
            "integrity_check": False,
            "errors": [],
        }

        try:
            with self._engine.connect() as conn:
                # 执行VACUUM（重建数据库，清理碎片）
                conn.execute(text("VACUUM"))
                result["vacuum"] = True
                logger.info("Database VACUUM completed")

                # 执行ANALYZE（更新统计信息）
                conn.execute(text("ANALYZE"))
                result["analyze"] = True
                logger.info("Database ANALYZE completed")

                # 执行完整性检查
                check_result = conn.execute(text("PRAGMA integrity_check")).scalar()
                result["integrity_check"] = check_result == "ok"
                if result["integrity_check"]:
                    logger.info("Database integrity check passed")
                else:
                    result["errors"].append(f"Integrity check failed: {check_result}")

        except Exception as e:
            result["errors"].append(str(e))
            logger.error(f"Database optimization failed: {e}")

        return result

    def close(self) -> None:
        """关闭数据库连接。"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("SQLiteOptimizedConnection closed")


class DatabaseCacheManager:
    """
    数据库缓存管理器。

    提供设备状态、实验数据、配置参数的缓存机制，
    减少数据库访问压力，提升查询性能。

    Attributes:
        config: 缓存配置
    """

    def __init__(self, config: CacheConfig | None = None) -> None:
        """
        初始化数据库缓存管理器。

        Args:
            config: 缓存配置，None使用默认配置
        """
        self._config = config or CacheConfig()
        self._lock = RLock()

        # 缓存存储
        self._cache: dict[str, tuple[Any, float | None, float]] = {}
        # 格式: {key: (value, expire_at, created_at)}

        # 统计信息
        self._stats = DatabaseStatistics()

        # 缓存键前缀
        self._key_prefixes = {
            "device_status": "dev_status:",
            "device_config": "dev_config:",
            "experiment_data": "exp_data:",
            "calibration": "calib:",
            "user_session": "session:",
        }

        logger.info(
            f"DatabaseCacheManager initialized: max_size={self._config.max_size}, "
            f"ttl={self._config.default_ttl}s"
        )

    def _make_key(self, category: str, identifier: str) -> str:
        """
        生成缓存键。

        Args:
            category: 缓存类别
            identifier: 标识符

        Returns:
            完整的缓存键
        """
        prefix = self._key_prefixes.get(category, "")
        return f"{prefix}{identifier}"

    def _evict_expired(self) -> int:
        """
        清理过期缓存条目。

        Returns:
            清理的条目数
        """
        evicted = 0
        current_time = time.time()
        keys_to_remove = []

        for key, (_, expire_at, _) in self._cache.items():
            if expire_at is not None and expire_at < current_time:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._cache[key]
            evicted += 1

        return evicted

    def _evict_lru(self, count: int = 1) -> int:
        """
        LRU淘汰最少使用的缓存条目。

        Args:
            count: 需要淘汰的条目数

        Returns:
            实际淘汰的条目数
        """
        if not self._cache:
            return 0

        # 按创建时间排序，删除最旧的
        sorted_keys = sorted(
            self._cache.keys(),
            key=lambda k: self._cache[k][2],  # created_at
        )

        evicted = 0
        for key in sorted_keys[:count]:
            del self._cache[key]
            evicted += 1

        return evicted

    def get(self, category: str, identifier: str) -> Any | None:
        """
        获取缓存值。

        Args:
            category: 缓存类别
            identifier: 标识符

        Returns:
            缓存值，不存在或已过期返回None
        """
        key = self._make_key(category, identifier)
        current_time = time.time()

        with self._lock:
            if key not in self._cache:
                self._stats.cache_misses += 1
                return None

            value, expire_at, created_at = self._cache[key]

            # 检查是否过期
            if expire_at is not None and expire_at < current_time:
                del self._cache[key]
                self._stats.cache_misses += 1
                return None

            self._stats.cache_hits += 1
            return value

    def set(
        self,
        category: str,
        identifier: str,
        value: Any,
        ttl: float | None = None,
    ) -> bool:
        """
        设置缓存值。

        Args:
            category: 缓存类别
            identifier: 标识符
            value: 缓存值
            ttl: 过期时间（秒），None使用默认值

        Returns:
            是否设置成功
        """
        key = self._make_key(category, identifier)
        effective_ttl = ttl if ttl is not None else self._config.default_ttl
        current_time = time.time()
        expire_at = current_time + effective_ttl if effective_ttl else None

        with self._lock:
            # 如果达到最大大小，执行淘汰
            if len(self._cache) >= self._config.max_size:
                # 先清理过期条目
                self._evict_expired()
                # 如果还是满，执行LRU淘汰
                if len(self._cache) >= self._config.max_size:
                    self._evict_lru(1)

            self._cache[key] = (value, expire_at, current_time)
            return True

    def delete(self, category: str, identifier: str) -> bool:
        """
        删除缓存值。

        Args:
            category: 缓存类别
            identifier: 标识符

        Returns:
            是否删除成功
        """
        key = self._make_key(category, identifier)

        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear_category(self, category: str) -> int:
        """
        清空指定类别的缓存。

        Args:
            category: 缓存类别

        Returns:
            清理的条目数
        """
        prefix = self._key_prefixes.get(category, "")
        count = 0

        with self._lock:
            keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
            for key in keys_to_remove:
                del self._cache[key]
                count += 1

        return count

    def clear_all(self) -> None:
        """清空所有缓存。"""
        with self._lock:
            self._cache.clear()
            logger.info("All cache cleared")

    def get_statistics(self) -> dict[str, Any]:
        """
        获取缓存统计信息。

        Returns:
            统计信息字典
        """
        with self._lock:
            total_requests = self._stats.cache_hits + self._stats.cache_misses
            hit_rate = self._stats.cache_hits / total_requests if total_requests > 0 else 0

            return {
                "cache_size": len(self._cache),
                "max_size": self._config.max_size,
                "cache_hits": self._stats.cache_hits,
                "cache_misses": self._stats.cache_misses,
                "hit_rate": hit_rate,
                "utilization": (
                    len(self._cache) / self._config.max_size if self._config.max_size > 0 else 0
                ),
            }

    def get_device_status(self, device_id: str) -> dict[str, Any] | None:
        """
        获取设备状态缓存。

        Args:
            device_id: 设备ID

        Returns:
            设备状态字典
        """
        return self.get("device_status", device_id)

    def set_device_status(
        self,
        device_id: str,
        status: dict[str, Any],
        ttl: float = 10.0,
    ) -> bool:
        """
        设置设备状态缓存。

        Args:
            device_id: 设备ID
            status: 设备状态字典
            ttl: 过期时间（秒），默认10秒

        Returns:
            是否设置成功
        """
        return self.set("device_status", device_id, status, ttl)

    def get_experiment_data(
        self,
        experiment_id: int,
        data_type: str = "latest",
    ) -> Any | None:
        """
        获取实验数据缓存。

        Args:
            experiment_id: 实验ID
            data_type: 数据类型

        Returns:
            实验数据
        """
        return self.get("experiment_data", f"{experiment_id}:{data_type}")

    def set_experiment_data(
        self,
        experiment_id: int,
        data: Any,
        data_type: str = "latest",
        ttl: float | None = None,
    ) -> bool:
        """
        设置实验数据缓存。

        Args:
            experiment_id: 实验ID
            data: 实验数据
            data_type: 数据类型
            ttl: 过期时间（秒）

        Returns:
            是否设置成功
        """
        return self.set("experiment_data", f"{experiment_id}:{data_type}", data, ttl)


class BatchWriteManager:
    """
    批量写入管理器。

    实现数据的批量写入优化，减少数据库写入次数，
    提升写入性能，支持自动刷新和手动刷新。

    Attributes:
        config: 批量写入配置
    """

    def __init__(
        self,
        session_factory: Callable[[], Session],
        config: BatchWriteConfig | None = None,
    ) -> None:
        """
        初始化批量写入管理器。

        Args:
            session_factory: 会话工厂
            config: 批量写入配置
        """
        self._session_factory = session_factory
        self._config = config or BatchWriteConfig()
        self._lock = RLock()

        # 写入缓冲区
        self._buffer: dict[str, list[Any]] = defaultdict(list)
        # 格式: {table_name: [model_instances]}

        # 统计信息
        self._stats = DatabaseStatistics()

        # 后台刷新任务
        self._flush_task: asyncio.Task[None] | None = None
        self._is_running = False

        logger.info(
            f"BatchWriteManager initialized: batch_size={self._config.batch_size}, "
            f"flush_interval={self._config.flush_interval}s"
        )

    def add(self, table_name: str, model_instance: Any) -> int:
        """
        添加数据到缓冲区。

        Args:
            table_name: 表名
            model_instance: 模型实例

        Returns:
            当前缓冲区大小
        """
        with self._lock:
            self._buffer[table_name].append(model_instance)

            # 检查是否需要刷新
            total_buffered = sum(len(buf) for buf in self._buffer.values())
            if total_buffered >= self._config.batch_size:
                # 同步刷新（在后台线程中执行）
                threading.Thread(target=self._sync_flush, daemon=True).start()

            return total_buffered

    def add_batch(self, table_name: str, model_instances: list[Any]) -> int:
        """
        批量添加数据到缓冲区。

        Args:
            table_name: 表名
            model_instances: 模型实例列表

        Returns:
            当前缓冲区大小
        """
        with self._lock:
            self._buffer[table_name].extend(model_instances)

            total_buffered = sum(len(buf) for buf in self._buffer.values())
            if total_buffered >= self._config.batch_size:
                threading.Thread(target=self._sync_flush, daemon=True).start()

            return total_buffered

    def _sync_flush(self) -> bool:
        """
        同步刷新缓冲区到数据库。

        Returns:
            是否刷新成功
        """
        with self._lock:
            if not self._buffer:
                return True

            # 复制缓冲区并清空
            buffer_copy = dict(self._buffer)
            self._buffer.clear()

        # 执行批量写入
        return self._execute_batch_write(buffer_copy)

    def _execute_batch_write(self, buffer: dict[str, list[Any]]) -> bool:
        """
        执行批量写入操作。

        Args:
            buffer: 缓冲区数据

        Returns:
            是否写入成功
        """
        start_time = time.time()

        for attempt in range(self._config.max_retries):
            session = self._session_factory()
            try:
                for table_name, instances in buffer.items():
                    if instances:
                        session.bulk_save_objects(instances)

                session.commit()

                duration_ms = (time.time() - start_time) * 1000
                self._stats.update_write_time(duration_ms)
                self._stats.batch_writes += 1

                total_records = sum(len(instances) for instances in buffer.values())
                logger.debug(
                    f"Batch write completed: {total_records} records in {duration_ms:.2f}ms"
                )
                return True

            except Exception as e:
                session.rollback()
                logger.error(f"Batch write failed (attempt {attempt + 1}): {e}")

                if attempt < self._config.max_retries - 1:
                    time.sleep(self._config.retry_delay * (attempt + 1))
                else:
                    # 重试失败，将数据放回缓冲区
                    with self._lock:
                        for table_name, instances in buffer.items():
                            self._buffer[table_name].extend(instances)
                    return False

            finally:
                session.close()

        return False

    async def async_flush(self) -> bool:
        """
        异步刷新缓冲区到数据库。

        Returns:
            是否刷新成功
        """
        # 在线程池中执行同步刷新
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_flush)

    def flush(self) -> bool:
        """
        手动刷新缓冲区到数据库。

        Returns:
            是否刷新成功
        """
        return self._sync_flush()

    def get_buffer_size(self) -> int:
        """
        获取当前缓冲区大小。

        Returns:
            缓冲区中的记录数
        """
        with self._lock:
            return sum(len(buf) for buf in self._buffer.values())

    def get_statistics(self) -> dict[str, Any]:
        """
        获取批量写入统计信息。

        Returns:
            统计信息字典
        """
        return {
            "buffer_size": self.get_buffer_size(),
            "batch_size": self._config.batch_size,
            "batch_writes": self._stats.batch_writes,
            "total_writes": self._stats.total_writes,
            "avg_write_time_ms": self._stats.avg_write_time_ms,
        }

    async def start_auto_flush(self) -> None:
        """启动自动刷新任务。"""
        if self._is_running:
            return

        self._is_running = True
        self._flush_task = asyncio.create_task(self._auto_flush_loop())
        logger.info("Auto flush task started")

    async def stop_auto_flush(self) -> None:
        """停止自动刷新任务。"""
        self._is_running = False

        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # 刷新剩余数据
        await self.async_flush()
        logger.info("Auto flush task stopped")

    async def _auto_flush_loop(self) -> None:
        """自动刷新循环。"""
        while self._is_running:
            try:
                await asyncio.sleep(self._config.flush_interval)

                if not self._is_running:
                    break

                if self.get_buffer_size() > 0:
                    await self.async_flush()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Auto flush error: {e}")


class HDF5StorageManager:
    """
    HDF5采集数据存储管理器。

    实现大规模采集数据的高效存储，包括分块存储、
    压缩、索引优化和断点续存机制。

    Attributes:
        storage_path: 存储路径
        config: HDF5配置
    """

    def __init__(
        self,
        storage_path: str,
        config: HDF5Config | None = None,
    ) -> None:
        """
        初始化HDF5存储管理器。

        Args:
            storage_path: 存储路径
            config: HDF5配置
        """
        self._storage_path = Path(storage_path)
        self._config = config or HDF5Config()
        self._lock = RLock()

        # 创建存储目录
        self._storage_path.mkdir(parents=True, exist_ok=True)

        # 文件索引
        self._file_index: dict[int, dict[str, Any]] = {}
        self._load_file_index()

        # 写入缓冲区
        self._write_buffer: dict[int, list[dict[str, Any]]] = defaultdict(list)

        # 统计信息
        self._stats = DatabaseStatistics()

        logger.info(
            f"HDF5StorageManager initialized: path={storage_path}, "
            f"chunk_size={self._config.chunk_size}"
        )

    def _load_file_index(self) -> None:
        """加载文件索引。"""
        index_file = self._storage_path / "hdf5_index.json"

        if index_file.exists():
            try:
                with open(index_file, encoding="utf-8") as f:
                    data = json.load(f)
                    self._file_index = {int(k): v for k, v in data.get("experiments", {}).items()}
            except Exception as e:
                logger.warning(f"Failed to load HDF5 index: {e}")
                self._file_index = {}

    def _save_file_index(self) -> None:
        """保存文件索引。"""
        index_file = self._storage_path / "hdf5_index.json"

        try:
            with open(index_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "experiments": self._file_index,
                        "last_updated": datetime.now().isoformat(),
                    },
                    f,
                    indent=2,
                )
        except Exception as e:
            logger.error(f"Failed to save HDF5 index: {e}")

    def _get_hdf5_file_path(self, experiment_id: int, part: int = 0) -> Path:
        """
        获取HDF5文件路径。

        Args:
            experiment_id: 实验ID
            part: 文件分片编号

        Returns:
            HDF5文件路径
        """
        if part == 0:
            return self._storage_path / f"exp_{experiment_id}.h5"
        return self._storage_path / f"exp_{experiment_id}_part{part}.h5"

    def _compress_data(self, data: np.ndarray) -> np.ndarray:
        """
        压缩数据。

        Args:
            data: 原始数据

        Returns:
            压缩后的数据
        """
        # HDF5内部会处理压缩，这里返回原始数据
        return data

    def write_data(
        self,
        experiment_id: int,
        data: dict[str, Any] | list[dict[str, Any]],
        timestamp: datetime | None = None,
    ) -> int:
        """
        写入采集数据。

        Args:
            experiment_id: 实验ID
            data: 数据字典或数据列表
            timestamp: 时间戳

        Returns:
            写入的记录数
        """
        if not data:
            return 0

        # 标准化数据格式
        if isinstance(data, dict):
            data_list = [data]
        else:
            data_list = data

        # 添加时间戳
        if timestamp is None:
            timestamp = datetime.now()

        for item in data_list:
            if "timestamp" not in item:
                item["timestamp"] = timestamp

        # 添加到缓冲区
        with self._lock:
            self._write_buffer[experiment_id].extend(data_list)

            # 检查是否需要刷新
            if len(self._write_buffer[experiment_id]) >= self._config.chunk_size:
                self._flush_buffer(experiment_id)

        return len(data_list)

    def _flush_buffer(self, experiment_id: int) -> bool:
        """
        刷新缓冲区到HDF5文件。

        Args:
            experiment_id: 实验ID

        Returns:
            是否刷新成功
        """
        if experiment_id not in self._write_buffer:
            return True

        data_list = self._write_buffer[experiment_id]
        if not data_list:
            return True

        try:
            import h5py

            # 获取文件路径
            file_info = self._file_index.get(experiment_id, {"part": 0, "records": 0})
            part = file_info.get("part", 0)
            file_path = self._get_hdf5_file_path(experiment_id, part)

            # 检查文件大小
            if file_path.exists():
                file_size_mb = file_path.stat().st_size / (1024 * 1024)
                if file_size_mb >= self._config.max_file_size_mb:
                    part += 1
                    file_path = self._get_hdf5_file_path(experiment_id, part)

            # 转换数据为NumPy数组
            timestamps = np.array(
                [
                    (
                        d["timestamp"].timestamp()
                        if isinstance(d["timestamp"], datetime)
                        else d["timestamp"]
                    )
                    for d in data_list
                ],
                dtype=np.float64,
            )

            # 提取数值数据
            numeric_data = {}
            for key in [
                "position_steps",
                "position_mm",
                "field_value",
                "current_value",
                "temperature",
            ]:
                if key in data_list[0]:
                    values = [d.get(key) for d in data_list]
                    numeric_data[key] = np.array(values, dtype=np.float64)

            # 写入HDF5文件
            with h5py.File(file_path, "a") as f:
                # 创建或获取数据集
                if "timestamps" not in f:
                    f.create_dataset(
                        "timestamps",
                        data=timestamps,
                        maxshape=(None,),
                        chunks=(self._config.chunk_size,),
                        compression=self._config.compression_algorithm,
                        compression_opts=self._config.compression_level,
                    )
                else:
                    # 追加数据
                    dataset = f["timestamps"]
                    current_size = dataset.shape[0]
                    dataset.resize((current_size + len(timestamps),))
                    dataset[current_size:] = timestamps

                # 写入数值数据
                for key, values in numeric_data.items():
                    if key not in f:
                        f.create_dataset(
                            key,
                            data=values,
                            maxshape=(None,),
                            chunks=(self._config.chunk_size,),
                            compression=self._config.compression_algorithm,
                            compression_opts=self._config.compression_level,
                        )
                    else:
                        dataset = f[key]
                        current_size = dataset.shape[0]
                        dataset.resize((current_size + len(values),))
                        dataset[current_size:] = values

                # 存储元数据
                if "metadata" not in f:
                    f.create_group("metadata")
                f["metadata"].attrs["last_updated"] = datetime.now().isoformat()
                f["metadata"].attrs["record_count"] = len(timestamps)

            # 更新索引
            self._file_index[experiment_id] = {
                "part": part,
                "records": file_info.get("records", 0) + len(data_list),
                "last_updated": datetime.now().isoformat(),
            }
            self._save_file_index()

            # 清空缓冲区
            self._write_buffer[experiment_id] = []

            logger.debug(
                f"HDF5 write completed: {len(data_list)} records for experiment {experiment_id}"
            )
            return True

        except ImportError:
            logger.error("h5py not installed, falling back to JSON storage")
            return self._fallback_json_write(experiment_id, data_list)
        except Exception as e:
            logger.error(f"HDF5 write failed: {e}")
            return False

    def _fallback_json_write(self, experiment_id: int, data_list: list[dict[str, Any]]) -> bool:
        """
        JSON回退写入方法。

        Args:
            experiment_id: 实验ID
            data_list: 数据列表

        Returns:
            是否写入成功
        """
        try:
            file_path = self._storage_path / f"exp_{experiment_id}.json.gz"

            # 读取现有数据
            existing_data = []
            if file_path.exists():
                with gzip.open(file_path, "rt", encoding="utf-8") as f:
                    existing_data = json.load(f)

            # 追加新数据
            existing_data.extend(data_list)

            # 写入文件
            with gzip.open(file_path, "wt", encoding="utf-8") as f:
                json.dump(existing_data, f, ensure_ascii=False)

            # 清空缓冲区
            self._write_buffer[experiment_id] = []

            return True

        except Exception as e:
            logger.error(f"JSON fallback write failed: {e}")
            return False

    def read_data(
        self,
        experiment_id: int,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 10000,
    ) -> list[dict[str, Any]]:
        """
        读取采集数据。

        Args:
            experiment_id: 实验ID
            start_time: 开始时间
            end_time: 结束时间
            limit: 最大返回记录数

        Returns:
            数据记录列表
        """
        try:
            import h5py

            file_info = self._file_index.get(experiment_id)
            if not file_info:
                return []

            file_path = self._get_hdf5_file_path(experiment_id, file_info.get("part", 0))
            if not file_path.exists():
                return []

            result = []

            with h5py.File(file_path, "r") as f:
                timestamps = f["timestamps"][:]

                # 时间范围过滤
                mask = np.ones(len(timestamps), dtype=bool)
                if start_time:
                    start_ts = start_time.timestamp()
                    mask &= timestamps >= start_ts
                if end_time:
                    end_ts = end_time.timestamp()
                    mask &= timestamps <= end_ts

                # 应用过滤
                filtered_indices = np.where(mask)[0][:limit]

                for idx in filtered_indices:
                    record = {
                        "timestamp": datetime.fromtimestamp(timestamps[idx]),
                    }

                    # 读取数值数据
                    for key in [
                        "position_steps",
                        "position_mm",
                        "field_value",
                        "current_value",
                        "temperature",
                    ]:
                        if key in f:
                            record[key] = float(f[key][idx])

                    result.append(record)

            return result

        except ImportError:
            return self._fallback_json_read(experiment_id, start_time, end_time, limit)
        except Exception as e:
            logger.error(f"HDF5 read failed: {e}")
            return []

    def _fallback_json_read(
        self,
        experiment_id: int,
        start_time: datetime | None,
        end_time: datetime | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """
        JSON回退读取方法。

        Args:
            experiment_id: 实验ID
            start_time: 开始时间
            end_time: 结束时间
            limit: 最大返回记录数

        Returns:
            数据记录列表
        """
        try:
            file_path = self._storage_path / f"exp_{experiment_id}.json.gz"
            if not file_path.exists():
                return []

            with gzip.open(file_path, "rt", encoding="utf-8") as f:
                data = json.load(f)

            result = []
            for record in data:
                ts = record.get("timestamp")
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts)

                if start_time and ts < start_time:
                    continue
                if end_time and ts > end_time:
                    continue

                result.append(record)
                if len(result) >= limit:
                    break

            return result

        except Exception as e:
            logger.error(f"JSON fallback read failed: {e}")
            return []

    def flush_all(self) -> None:
        """刷新所有缓冲区。"""
        with self._lock:
            for experiment_id in list(self._write_buffer.keys()):
                self._flush_buffer(experiment_id)

    def get_statistics(self) -> dict[str, Any]:
        """
        获取存储统计信息。

        Returns:
            统计信息字典
        """
        total_records = sum(info.get("records", 0) for info in self._file_index.values())
        total_size = 0

        for file_path in self._storage_path.glob("*.h5"):
            total_size += file_path.stat().st_size

        return {
            "experiment_count": len(self._file_index),
            "total_records": total_records,
            "total_size_mb": total_size / (1024 * 1024),
            "buffer_size": sum(len(buf) for buf in self._write_buffer.values()),
            "storage_path": str(self._storage_path),
        }

    def delete_experiment(self, experiment_id: int) -> bool:
        """
        删除实验数据。

        Args:
            experiment_id: 实验ID

        Returns:
            是否删除成功
        """
        try:
            file_info = self._file_index.get(experiment_id)
            if not file_info:
                return False

            # 删除所有分片文件
            part = 0
            while True:
                file_path = self._get_hdf5_file_path(experiment_id, part)
                if file_path.exists():
                    file_path.unlink()
                else:
                    break
                part += 1

            # 删除索引
            del self._file_index[experiment_id]
            self._save_file_index()

            # 清空缓冲区
            if experiment_id in self._write_buffer:
                del self._write_buffer[experiment_id]

            logger.info(f"Experiment {experiment_id} data deleted")
            return True

        except Exception as e:
            logger.error(f"Failed to delete experiment {experiment_id}: {e}")
            return False


class DatabaseOptimizer:
    """
    综合数据库优化器。

    整合SQLite优化、缓存管理、批量写入和HDF5存储，
    提供统一的数据库优化接口。

    Attributes:
        db_path: 数据库文件路径
        storage_path: 数据存储路径
    """

    def __init__(
        self,
        db_path: str = "experiments.db",
        storage_path: str = "data/hdf5",
        sqlite_config: SQLiteOptimizationConfig | None = None,
        cache_config: CacheConfig | None = None,
        batch_config: BatchWriteConfig | None = None,
        hdf5_config: HDF5Config | None = None,
    ) -> None:
        """
        初始化综合数据库优化器。

        Args:
            db_path: 数据库文件路径
            storage_path: HDF5数据存储路径
            sqlite_config: SQLite优化配置
            cache_config: 缓存配置
            batch_config: 批量写入配置
            hdf5_config: HDF5配置
        """
        self._db_path = db_path
        self._storage_path = storage_path

        # 初始化各组件
        self._sqlite_conn = SQLiteOptimizedConnection(db_path, sqlite_config)
        self._cache_manager = DatabaseCacheManager(cache_config)
        self._batch_writer = BatchWriteManager(
            self._sqlite_conn.get_session,
            batch_config,
        )
        self._hdf5_storage = HDF5StorageManager(storage_path, hdf5_config)

        # 统计信息
        self._stats = DatabaseStatistics()

        logger.info(f"DatabaseOptimizer initialized: db={db_path}, storage={storage_path}")

    @contextmanager
    def get_session(self) -> Session:
        """
        获取数据库会话。

        Yields:
            Session: 数据库会话实例
        """
        with self._sqlite_conn.get_session() as session:
            yield session

    def get_cache(self) -> DatabaseCacheManager:
        """
        获取缓存管理器。

        Returns:
            DatabaseCacheManager: 缓存管理器实例
        """
        return self._cache_manager

    def get_batch_writer(self) -> BatchWriteManager:
        """
        获取批量写入管理器。

        Returns:
            BatchWriteManager: 批量写入管理器实例
        """
        return self._batch_writer

    def get_hdf5_storage(self) -> HDF5StorageManager:
        """
        获取HDF5存储管理器。

        Returns:
            HDF5StorageManager: HDF5存储管理器实例
        """
        return self._hdf5_storage

    def optimize(self) -> dict[str, Any]:
        """
        执行全面优化操作。

        Returns:
            优化结果字典
        """
        result = {
            "sqlite_optimization": self._sqlite_conn.optimize_database(),
            "cache_statistics": self._cache_manager.get_statistics(),
            "batch_statistics": self._batch_writer.get_statistics(),
            "hdf5_statistics": self._hdf5_storage.get_statistics(),
            "timestamp": datetime.now().isoformat(),
        }

        self._stats.last_optimization = datetime.now()
        return result

    def get_all_statistics(self) -> dict[str, Any]:
        """
        获取所有统计信息。

        Returns:
            统计信息字典
        """
        return {
            "database_info": self._sqlite_conn.get_database_info(),
            "cache": self._cache_manager.get_statistics(),
            "batch_write": self._batch_writer.get_statistics(),
            "hdf5_storage": self._hdf5_storage.get_statistics(),
            "last_optimization": (
                self._stats.last_optimization.isoformat() if self._stats.last_optimization else None
            ),
        }

    async def start_background_tasks(self) -> None:
        """启动所有后台任务。"""
        await self._batch_writer.start_auto_flush()
        logger.info("DatabaseOptimizer background tasks started")

    async def stop_background_tasks(self) -> None:
        """停止所有后台任务。"""
        await self._batch_writer.stop_auto_flush()
        self._hdf5_storage.flush_all()
        logger.info("DatabaseOptimizer background tasks stopped")

    def close(self) -> None:
        """关闭所有资源。"""
        self._batch_writer.flush()
        self._hdf5_storage.flush_all()
        self._sqlite_conn.close()
        self._cache_manager.clear_all()
        logger.info("DatabaseOptimizer closed")


# ==================== 便捷函数 ====================


def create_optimized_database(
    db_path: str = "experiments.db",
    storage_path: str = "data/hdf5",
    enable_cache: bool = True,
    enable_batch_write: bool = True,
    enable_hdf5: bool = True,
) -> DatabaseOptimizer:
    """
    创建优化数据库的便捷函数。

    Args:
        db_path: 数据库文件路径
        storage_path: HDF5存储路径
        enable_cache: 是否启用缓存
        enable_batch_write: 是否启用批量写入
        enable_hdf5: 是否启用HDF5存储

    Returns:
        DatabaseOptimizer: 数据库优化器实例

    Example:
        >>> optimizer = create_optimized_database("experiments.db", "data/hdf5")
        >>> with optimizer.get_session() as session:
        ...     users = session.query(User).all()
    """
    cache_config = CacheConfig() if enable_cache else CacheConfig(max_size=0)
    batch_config = BatchWriteConfig() if enable_batch_write else BatchWriteConfig(batch_size=1)
    hdf5_config = HDF5Config() if enable_hdf5 else None

    return DatabaseOptimizer(
        db_path=db_path,
        storage_path=storage_path,
        cache_config=cache_config,
        batch_config=batch_config,
        hdf5_config=hdf5_config,
    )


def optimize_sqlite_database(db_path: str) -> dict[str, Any]:
    """
    优化SQLite数据库的便捷函数。

    Args:
        db_path: 数据库文件路径

    Returns:
        优化结果字典

    Example:
        >>> result = optimize_sqlite_database("experiments.db")
        >>> print(result["vacuum"])
    """
    conn = SQLiteOptimizedConnection(db_path)
    try:
        return conn.optimize_database()
    finally:
        conn.close()
