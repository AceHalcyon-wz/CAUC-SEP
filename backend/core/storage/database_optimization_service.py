"""
数据库优化服务模块

文件名: database_optimization_service.py
路径: backend/core/storage/
功能: 数据库优化统一服务入口，整合SQLite优化、缓存管理、批量写入、HDF5存储
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: sqlite3, sqlalchemy, h5py, numpy

模块内容:
    - DatabaseOptimizationService: 数据库优化统一服务类
    - DeviceStatusCache: 设备状态专用缓存
    - ExperimentDataCache: 实验数据专用缓存
    - DatabaseHealthChecker: 数据库健康检查器
"""

import asyncio
import json
import logging
import os
import sqlite3
import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock, RLock
from typing import Any, Callable

import numpy as np
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)


# ==================== 常量定义 ====================

# SQLite PRAGMA 配置常量
SQLITE_JOURNAL_MODE_WAL = "WAL"
SQLITE_SYNC_MODE_NORMAL = "NORMAL"
SQLITE_TEMP_STORE_MEMORY = "MEMORY"

# 默认配置常量
DEFAULT_CACHE_SIZE_MB = 64
DEFAULT_CACHE_TTL_SECONDS = 300
DEFAULT_BATCH_SIZE = 1000
DEFAULT_FLUSH_INTERVAL_SECONDS = 5
DEFAULT_HDF5_CHUNK_SIZE = 10000
DEFAULT_HDF5_COMPRESSION_LEVEL = 6

# 设备状态缓存 TTL（秒）
DEVICE_STATUS_CACHE_TTL = 10
# 实验数据缓存 TTL（秒）
EXPERIMENT_DATA_CACHE_TTL = 60


@dataclass
class OptimizationConfig:
    """数据库优化配置。

    Attributes:
        enable_wal_mode: 是否启用WAL模式
        enable_cache: 是否启用缓存
        enable_batch_write: 是否启用批量写入
        enable_hdf5_storage: 是否启用HDF5存储
        cache_size_mb: 缓存大小（MB）
        batch_size: 批量写入大小
        hdf5_chunk_size: HDF5分块大小
        hdf5_compression_level: HDF5压缩级别
    """

    enable_wal_mode: bool = True
    enable_cache: bool = True
    enable_batch_write: bool = True
    enable_hdf5_storage: bool = True
    cache_size_mb: int = DEFAULT_CACHE_SIZE_MB
    batch_size: int = DEFAULT_BATCH_SIZE
    hdf5_chunk_size: int = DEFAULT_HDF5_CHUNK_SIZE
    hdf5_compression_level: int = DEFAULT_HDF5_COMPRESSION_LEVEL


@dataclass
class OptimizationStatistics:
    """优化统计信息。

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


class DeviceStatusCache:
    """
    设备状态专用缓存。

    提供设备状态数据的高速缓存，支持自动过期和实时更新。
    减少对数据库的频繁查询压力。

    Attributes:
        ttl: 缓存过期时间（秒）
        max_size: 最大缓存条目数
    """

    def __init__(
        self,
        ttl: float = DEVICE_STATUS_CACHE_TTL,
        max_size: int = 1000,
    ) -> None:
        """
        初始化设备状态缓存。

        Args:
            ttl: 缓存过期时间（秒），默认10秒
            max_size: 最大缓存条目数，默认1000
        """
        self._ttl = ttl
        self._max_size = max_size
        self._lock = RLock()

        # 缓存存储: {device_id: (status_data, expire_at, created_at)}
        self._cache: dict[str, tuple[dict[str, Any], float, float]] = {}

        # 统计信息
        self._hits = 0
        self._misses = 0

        logger.info(
            f"DeviceStatusCache initialized: ttl={ttl}s, max_size={max_size}"
        )

    def get(self, device_id: str) -> dict[str, Any] | None:
        """
        获取设备状态缓存。

        Args:
            device_id: 设备ID

        Returns:
            设备状态字典，不存在或已过期返回None
        """
        current_time = time.time()

        with self._lock:
            if device_id not in self._cache:
                self._misses += 1
                return None

            status, expire_at, created_at = self._cache[device_id]

            # 检查是否过期
            if expire_at < current_time:
                del self._cache[device_id]
                self._misses += 1
                return None

            self._hits += 1
            return status

    def set(
        self,
        device_id: str,
        status: dict[str, Any],
        ttl: float | None = None,
    ) -> bool:
        """
        设置设备状态缓存。

        Args:
            device_id: 设备ID
            status: 设备状态字典
            ttl: 过期时间（秒），None使用默认值

        Returns:
            是否设置成功
        """
        effective_ttl = ttl if ttl is not None else self._ttl
        current_time = time.time()
        expire_at = current_time + effective_ttl

        with self._lock:
            # 如果达到最大大小，执行LRU淘汰
            if (
                len(self._cache) >= self._max_size
                and device_id not in self._cache
            ):
                self._evict_lru(1)

            self._cache[device_id] = (status, expire_at, current_time)
            return True

    def delete(self, device_id: str) -> bool:
        """
        删除设备状态缓存。

        Args:
            device_id: 设备ID

        Returns:
            是否删除成功
        """
        with self._lock:
            if device_id in self._cache:
                del self._cache[device_id]
                return True
            return False

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

    def clear_all(self) -> None:
        """清空所有缓存。"""
        with self._lock:
            self._cache.clear()
            logger.info("DeviceStatusCache cleared")

    def get_statistics(self) -> dict[str, Any]:
        """
        获取缓存统计信息。

        Returns:
            统计信息字典
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0

            return {
                "cache_size": len(self._cache),
                "max_size": self._max_size,
                "ttl": self._ttl,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "utilization": (
                    len(self._cache) / self._max_size if self._max_size > 0 else 0
                ),
            }


class ExperimentDataCache:
    """
    实验数据专用缓存。

    提供实验数据的高速缓存，支持按实验ID分组管理，
    支持数据追加和范围查询。

    Attributes:
        ttl: 缓存过期时间（秒）
        max_records_per_experiment: 每个实验最大缓存记录数
    """

    def __init__(
        self,
        ttl: float = EXPERIMENT_DATA_CACHE_TTL,
        max_records_per_experiment: int = 10000,
        max_experiments: int = 10,
    ) -> None:
        """
        初始化实验数据缓存。

        Args:
            ttl: 缓存过期时间（秒），默认60秒
            max_records_per_experiment: 每个实验最大缓存记录数
            max_experiments: 最大缓存实验数
        """
        self._ttl = ttl
        self._max_records = max_records_per_experiment
        self._max_experiments = max_experiments
        self._lock = RLock()

        # 缓存存储: {experiment_id: (data_list, expire_at, created_at)}
        self._cache: dict[int, tuple[list[dict[str, Any]], float, float]] = {}

        # 统计信息
        self._hits = 0
        self._misses = 0

        logger.info(
            f"ExperimentDataCache initialized: ttl={ttl}s, "
            f"max_records={max_records_per_experiment}"
        )

    def get_latest(
        self,
        experiment_id: int,
        count: int = 100,
    ) -> list[dict[str, Any]]:
        """
        获取实验最新数据。

        Args:
            experiment_id: 实验ID
            count: 返回记录数

        Returns:
            数据记录列表
        """
        current_time = time.time()

        with self._lock:
            if experiment_id not in self._cache:
                self._misses += 1
                return []

            data_list, expire_at, created_at = self._cache[experiment_id]

            # 检查是否过期
            if expire_at < current_time:
                del self._cache[experiment_id]
                self._misses += 1
                return []

            self._hits += 1
            return data_list[-count:] if data_list else []

    def append(
        self,
        experiment_id: int,
        data: dict[str, Any] | list[dict[str, Any]],
        ttl: float | None = None,
    ) -> int:
        """
        追加实验数据到缓存。

        Args:
            experiment_id: 实验ID
            data: 数据字典或数据列表
            ttl: 过期时间（秒），None使用默认值

        Returns:
            缓存中的总记录数
        """
        if isinstance(data, dict):
            data_list = [data]
        else:
            data_list = data

        effective_ttl = ttl if ttl is not None else self._ttl
        current_time = time.time()
        expire_at = current_time + effective_ttl

        with self._lock:
            # 如果实验不存在，创建新缓存
            if experiment_id not in self._cache:
                # 检查是否达到最大实验数
                if len(self._cache) >= self._max_experiments:
                    self._evict_oldest_experiment()

                self._cache[experiment_id] = ([], expire_at, current_time)

            # 追加数据
            cached_data, _, created_at = self._cache[experiment_id]
            cached_data.extend(data_list)

            # 如果超过最大记录数，删除旧数据
            if len(cached_data) > self._max_records:
                remove_count = len(cached_data) - self._max_records
                del cached_data[:remove_count]

            # 更新过期时间
            self._cache[experiment_id] = (cached_data, expire_at, created_at)

            return len(cached_data)

    def _evict_oldest_experiment(self) -> int:
        """
        淘汰最旧的实验缓存。

        Returns:
            淘汰的实验数
        """
        if not self._cache:
            return 0

        # 找到最旧的实验
        oldest_id = min(
            self._cache.keys(),
            key=lambda k: self._cache[k][2],  # created_at
        )

        del self._cache[oldest_id]
        logger.debug(f"Evicted oldest experiment cache: {oldest_id}")
        return 1

    def clear_experiment(self, experiment_id: int) -> bool:
        """
        清空指定实验的缓存。

        Args:
            experiment_id: 实验ID

        Returns:
            是否清空成功
        """
        with self._lock:
            if experiment_id in self._cache:
                del self._cache[experiment_id]
                return True
            return False

    def clear_all(self) -> None:
        """清空所有缓存。"""
        with self._lock:
            self._cache.clear()
            logger.info("ExperimentDataCache cleared")

    def get_statistics(self) -> dict[str, Any]:
        """
        获取缓存统计信息。

        Returns:
            统计信息字典
        """
        with self._lock:
            total_records = sum(
                len(data) for data, _, _ in self._cache.values()
            )
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0

            return {
                "experiment_count": len(self._cache),
                "max_experiments": self._max_experiments,
                "total_records": total_records,
                "max_records_per_experiment": self._max_records,
                "ttl": self._ttl,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
            }


class DatabaseHealthChecker:
    """
    数据库健康检查器。

    定期检查数据库健康状态，包括连接状态、
    磁盘空间、索引完整性等。

    Attributes:
        db_path: 数据库文件路径
    """

    def __init__(self, db_path: str) -> None:
        """
        初始化数据库健康检查器。

        Args:
            db_path: 数据库文件路径
        """
        self._db_path = db_path
        self._lock = Lock()

        logger.info(f"DatabaseHealthChecker initialized for {db_path}")

    def check_health(self) -> dict[str, Any]:
        """
        执行完整的健康检查。

        Returns:
            健康检查结果字典
        """
        result = {
            "healthy": True,
            "timestamp": datetime.now().isoformat(),
            "db_path": self._db_path,
            "checks": {},
            "errors": [],
            "warnings": [],
        }

        # 检查数据库文件
        file_check = self._check_database_file()
        result["checks"]["file"] = file_check
        if not file_check.get("exists", False):
            result["healthy"] = False
            result["errors"].append("Database file does not exist")
            return result

        # 检查数据库连接
        connection_check = self._check_connection()
        result["checks"]["connection"] = connection_check
        if not connection_check.get("connected", False):
            result["healthy"] = False
            result["errors"].append(f"Database connection failed: {connection_check.get('error')}")

        # 检查完整性
        integrity_check = self._check_integrity()
        result["checks"]["integrity"] = integrity_check
        if not integrity_check.get("passed", False):
            result["healthy"] = False
            result["errors"].append("Database integrity check failed")

        # 检查磁盘空间
        disk_check = self._check_disk_space()
        result["checks"]["disk_space"] = disk_check
        if disk_check.get("low_space", False):
            result["warnings"].append(
                f"Low disk space: {disk_check.get('free_gb', 0):.2f}GB remaining"
            )

        # 检查WAL模式
        wal_check = self._check_wal_mode()
        result["checks"]["wal_mode"] = wal_check

        # 检查索引状态
        index_check = self._check_indexes()
        result["checks"]["indexes"] = index_check

        return result

    def _check_database_file(self) -> dict[str, Any]:
        """
        检查数据库文件状态。

        Returns:
            文件检查结果
        """
        result = {
            "exists": False,
            "size_mb": 0,
            "writable": False,
        }

        if os.path.exists(self._db_path):
            result["exists"] = True
            result["size_mb"] = os.path.getsize(self._db_path) / (1024 * 1024)
            result["writable"] = os.access(self._db_path, os.W_OK)

        return result

    def _check_connection(self) -> dict[str, Any]:
        """
        检查数据库连接。

        Returns:
            连接检查结果
        """
        result = {
            "connected": False,
            "error": None,
        }

        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result["connected"] = True
        except Exception as e:
            result["error"] = str(e)

        return result

    def _check_integrity(self) -> dict[str, Any]:
        """
        检查数据库完整性。

        Returns:
            完整性检查结果
        """
        result = {
            "passed": False,
            "message": None,
        }

        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                check_result = cursor.fetchone()[0]
                result["passed"] = check_result == "ok"
                result["message"] = check_result
        except Exception as e:
            result["message"] = str(e)

        return result

    def _check_disk_space(self) -> dict[str, Any]:
        """
        检查磁盘空间。

        Returns:
            磁盘空间检查结果
        """
        result = {
            "total_gb": 0,
            "free_gb": 0,
            "used_percent": 0,
            "low_space": False,
        }

        try:
            stat = os.statvfs(os.path.dirname(self._db_path))
            result["total_gb"] = stat.f_blocks * stat.f_frsize / (1024**3)
            result["free_gb"] = stat.f_bavail * stat.f_frsize / (1024**3)
            result["used_percent"] = (
                (stat.f_blocks - stat.f_bavail) / stat.f_blocks * 100
                if stat.f_blocks > 0
                else 0
            )
            result["low_space"] = result["free_gb"] < 1.0  # 小于1GB警告
        except Exception:
            pass

        return result

    def _check_wal_mode(self) -> dict[str, Any]:
        """
        检查WAL模式状态。

        Returns:
            WAL模式检查结果
        """
        result = {
            "enabled": False,
            "journal_mode": None,
        }

        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA journal_mode")
                journal_mode = cursor.fetchone()[0]
                result["journal_mode"] = journal_mode
                result["enabled"] = journal_mode.upper() == "WAL"
        except Exception:
            pass

        return result

    def _check_indexes(self) -> dict[str, Any]:
        """
        检查索引状态。

        Returns:
            索引检查结果
        """
        result = {
            "index_count": 0,
            "tables": {},
        }

        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.cursor()

                # 获取所有表
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%'"
                )
                tables = [row[0] for row in cursor.fetchall()]

                # 获取每个表的索引
                for table in tables:
                    cursor.execute(f"PRAGMA index_list({table})")
                    indexes = cursor.fetchall()
                    result["tables"][table] = len(indexes)
                    result["index_count"] += len(indexes)

        except Exception:
            pass

        return result


class DatabaseOptimizationService:
    """
    数据库优化统一服务类。

    整合SQLite优化、缓存管理、批量写入和HDF5存储，
    提供统一的数据库优化接口。

    Attributes:
        db_path: 数据库文件路径
        storage_path: HDF5数据存储路径
        config: 优化配置
    """

    def __init__(
        self,
        db_path: str = "experiments.db",
        storage_path: str = "data/hdf5",
        config: OptimizationConfig | None = None,
    ) -> None:
        """
        初始化数据库优化服务。

        Args:
            db_path: 数据库文件路径
            storage_path: HDF5数据存储路径
            config: 优化配置
        """
        self._db_path = db_path
        self._storage_path = storage_path
        self._config = config or OptimizationConfig()

        # 初始化引擎
        self._engine: Engine | None = None
        self._session_factory: sessionmaker | None = None

        # 初始化缓存
        self._device_status_cache = DeviceStatusCache()
        self._experiment_data_cache = ExperimentDataCache()

        # 初始化健康检查器
        self._health_checker = DatabaseHealthChecker(db_path)

        # 统计信息
        self._statistics = OptimizationStatistics()

        # 初始化数据库
        self._initialize_database()

        logger.info(
            f"DatabaseOptimizationService initialized: db={db_path}, "
            f"storage={storage_path}"
        )

    def _initialize_database(self) -> None:
        """初始化数据库引擎和优化设置。"""
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
            cursor.execute("PRAGMA foreign_keys=ON")

            # 设置日志模式为WAL（提高并发性能）
            if self._config.enable_wal_mode:
                cursor.execute(f"PRAGMA journal_mode={SQLITE_JOURNAL_MODE_WAL}")

            # 设置同步模式（性能与安全平衡）
            cursor.execute(f"PRAGMA synchronous={SQLITE_SYNC_MODE_NORMAL}")

            # 设置缓存大小（单位：页，每页约4KB）
            cache_size_pages = -self._config.cache_size_mb * 1024
            cursor.execute(f"PRAGMA cache_size={cache_size_pages}")

            # 设置临时存储在内存中
            cursor.execute(f"PRAGMA temp_store={SQLITE_TEMP_STORE_MEMORY}")

            # 设置忙等待时间（毫秒）
            cursor.execute("PRAGMA busy_timeout=30000")

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
            >>> with service.get_session() as session:
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

    def get_device_status_cache(self) -> DeviceStatusCache:
        """
        获取设备状态缓存实例。

        Returns:
            DeviceStatusCache: 设备状态缓存实例
        """
        return self._device_status_cache

    def get_experiment_data_cache(self) -> ExperimentDataCache:
        """
        获取实验数据缓存实例。

        Returns:
            ExperimentDataCache: 实验数据缓存实例
        """
        return self._experiment_data_cache

    def get_health_checker(self) -> DatabaseHealthChecker:
        """
        获取健康检查器实例。

        Returns:
            DatabaseHealthChecker: 健康检查器实例
        """
        return self._health_checker

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
            "timestamp": datetime.now().isoformat(),
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
                check_result = conn.execute(
                    text("PRAGMA integrity_check")
                ).scalar()
                result["integrity_check"] = check_result == "ok"
                if result["integrity_check"]:
                    logger.info("Database integrity check passed")
                else:
                    result["errors"].append(
                        f"Integrity check failed: {check_result}"
                    )

        except Exception as e:
            result["errors"].append(str(e))
            logger.error(f"Database optimization failed: {e}")

        self._statistics.last_optimization = datetime.now()
        return result

    def get_all_statistics(self) -> dict[str, Any]:
        """
        获取所有统计信息。

        Returns:
            统计信息字典
        """
        return {
            "database": {
                "total_queries": self._statistics.total_queries,
                "total_writes": self._statistics.total_writes,
                "avg_query_time_ms": self._statistics.avg_query_time_ms,
                "avg_write_time_ms": self._statistics.avg_write_time_ms,
                "last_optimization": (
                    self._statistics.last_optimization.isoformat()
                    if self._statistics.last_optimization
                    else None
                ),
            },
            "device_status_cache": self._device_status_cache.get_statistics(),
            "experiment_data_cache": self._experiment_data_cache.get_statistics(),
            "config": {
                "wal_mode": self._config.enable_wal_mode,
                "cache_enabled": self._config.enable_cache,
                "batch_write_enabled": self._config.enable_batch_write,
                "hdf5_storage_enabled": self._config.enable_hdf5_storage,
            },
        }

    def check_health(self) -> dict[str, Any]:
        """
        执行健康检查。

        Returns:
            健康检查结果
        """
        return self._health_checker.check_health()

    def clear_all_caches(self) -> None:
        """清空所有缓存。"""
        self._device_status_cache.clear_all()
        self._experiment_data_cache.clear_all()
        logger.info("All caches cleared")

    def close(self) -> None:
        """关闭所有资源。"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None

        self.clear_all_caches()
        logger.info("DatabaseOptimizationService closed")


# ==================== 全局实例管理 ====================

_global_service: DatabaseOptimizationService | None = None
_global_service_lock = Lock()


def get_optimization_service(
    db_path: str = "experiments.db",
    storage_path: str = "data/hdf5",
    config: OptimizationConfig | None = None,
) -> DatabaseOptimizationService:
    """
    获取全局数据库优化服务实例。

    Args:
        db_path: 数据库文件路径
        storage_path: HDF5存储路径
        config: 优化配置

    Returns:
        DatabaseOptimizationService: 全局服务实例
    """
    global _global_service

    if _global_service is None:
        with _global_service_lock:
            if _global_service is None:
                _global_service = DatabaseOptimizationService(
                    db_path=db_path,
                    storage_path=storage_path,
                    config=config,
                )

    return _global_service


def init_optimization_service(
    db_path: str = "experiments.db",
    storage_path: str = "data/hdf5",
    enable_wal: bool = True,
    enable_cache: bool = True,
    cache_size_mb: int = 64,
) -> DatabaseOptimizationService:
    """
    初始化全局数据库优化服务。

    Args:
        db_path: 数据库文件路径
        storage_path: HDF5存储路径
        enable_wal: 是否启用WAL模式
        enable_cache: 是否启用缓存
        cache_size_mb: 缓存大小（MB）

    Returns:
        DatabaseOptimizationService: 服务实例
    """
    config = OptimizationConfig(
        enable_wal_mode=enable_wal,
        enable_cache=enable_cache,
        cache_size_mb=cache_size_mb,
    )

    return get_optimization_service(db_path, storage_path, config)
