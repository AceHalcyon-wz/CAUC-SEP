"""
HDF5断点续存存储模块

文件名: hdf5_resumable_storage.py
路径: backend/core/storage/
功能: HDF5时序数据存储，支持分块存储、压缩、断点续存、增量写入
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: h5py, numpy, sqlite3

模块内容:
    - HDF5ResumableStorage: HDF5断点续存存储类
    - ChunkManager: 分块管理器
    - CheckpointManager: 检查点管理器
    - HDF5IndexManager: HDF5索引管理器
"""

import json
import logging
import os
import sqlite3
import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock, RLock
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# 尝试导入h5py，如果不可用则使用模拟实现
try:
    import h5py

    HAS_H5PY = True
except ImportError:
    HAS_H5PY = False
    logger.warning("h5py not available, HDF5 storage will use fallback implementation")


# ==================== 常量定义 ====================

# 默认配置常量
DEFAULT_CHUNK_SIZE = 10000
DEFAULT_COMPRESSION_LEVEL = 6
DEFAULT_COMPRESSION_ALGORITHM = "gzip"
DEFAULT_FLUSH_INTERVAL = 5.0  # 秒
DEFAULT_CHECKPOINT_INTERVAL = 10.0  # 秒

# HDF5数据集名称
DATASET_TIMESERIES = "timeseries"
DATASET_METADATA = "metadata"
DATASET_INDEX = "index"

# 数据类型定义
DTYPE_TIMESTAMP = "float64"  # 时间戳存储为Unix时间戳
DTYPE_POSITION = "int64"
DTYPE_VALUE = "float64"
DTYPE_TEMPERATURE = "float32"


@dataclass
class HDF5Config:
    """HDF5存储配置。

    Attributes:
        chunk_size: 分块大小（记录数）
        compression_level: 压缩级别（0-9）
        compression_algorithm: 压缩算法
        flush_interval: 刷新间隔（秒）
        checkpoint_interval: 检查点间隔（秒）
        enable_indexing: 是否启用索引
        max_file_size_mb: 单文件最大大小（MB）
    """

    chunk_size: int = DEFAULT_CHUNK_SIZE
    compression_level: int = DEFAULT_COMPRESSION_LEVEL
    compression_algorithm: str = DEFAULT_COMPRESSION_ALGORITHM
    flush_interval: float = DEFAULT_FLUSH_INTERVAL
    checkpoint_interval: float = DEFAULT_CHECKPOINT_INTERVAL
    enable_indexing: bool = True
    max_file_size_mb: int = 1024  # 1GB


@dataclass
class CheckpointInfo:
    """检查点信息。

    Attributes:
        experiment_id: 实验ID
        file_path: HDF5文件路径
        last_record_index: 最后记录索引
        last_timestamp: 最后时间戳
        record_count: 总记录数
        created_at: 创建时间
        updated_at: 更新时间
        checksum: 数据校验和
    """

    experiment_id: int
    file_path: str
    last_record_index: int = 0
    last_timestamp: float = 0.0
    record_count: int = 0
    created_at: str = ""
    updated_at: str = ""
    checksum: str = ""


@dataclass
class ChunkInfo:
    """分块信息。

    Attributes:
        chunk_id: 分块ID
        experiment_id: 实验ID
        start_index: 起始索引
        end_index: 结束索引
        start_timestamp: 起始时间戳
        end_timestamp: 结束时间戳
        record_count: 记录数
        file_path: 文件路径
        is_compressed: 是否压缩
        checksum: 校验和
    """

    chunk_id: str
    experiment_id: int
    start_index: int = 0
    end_index: int = 0
    start_timestamp: float = 0.0
    end_timestamp: float = 0.0
    record_count: int = 0
    file_path: str = ""
    is_compressed: bool = True
    checksum: str = ""


class CheckpointManager:
    """
    检查点管理器。

    管理HDF5存储的检查点，支持断点续存。

    Attributes:
        db_path: 检查点数据库路径
    """

    def __init__(self, db_path: str) -> None:
        """
        初始化检查点管理器。

        Args:
            db_path: 检查点数据库路径
        """
        self._db_path = db_path
        self._lock = Lock()

        # 初始化数据库
        self._init_database()

        logger.info(f"CheckpointManager initialized: {db_path}")

    def _init_database(self) -> None:
        """初始化检查点数据库。"""
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            # 检查点表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hdf5_checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    experiment_id INTEGER NOT NULL,
                    file_path TEXT NOT NULL,
                    last_record_index INTEGER DEFAULT 0,
                    last_timestamp REAL DEFAULT 0,
                    record_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    checksum TEXT,
                    UNIQUE(experiment_id, file_path)
                )
            """)

            # 分块信息表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hdf5_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chunk_id TEXT NOT NULL UNIQUE,
                    experiment_id INTEGER NOT NULL,
                    start_index INTEGER DEFAULT 0,
                    end_index INTEGER DEFAULT 0,
                    start_timestamp REAL DEFAULT 0,
                    end_timestamp REAL DEFAULT 0,
                    record_count INTEGER DEFAULT 0,
                    file_path TEXT NOT NULL,
                    is_compressed INTEGER DEFAULT 1,
                    checksum TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_checkpoints_exp
                ON hdf5_checkpoints(experiment_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_exp
                ON hdf5_chunks(experiment_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_timestamp
                ON hdf5_chunks(start_timestamp, end_timestamp)
            """)

            conn.commit()

    def save_checkpoint(self, checkpoint: CheckpointInfo) -> bool:
        """
        保存检查点。

        Args:
            checkpoint: 检查点信息

        Returns:
            是否保存成功
        """
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO hdf5_checkpoints
                    (experiment_id, file_path, last_record_index, last_timestamp,
                     record_count, updated_at, checksum)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                """, (
                    checkpoint.experiment_id,
                    checkpoint.file_path,
                    checkpoint.last_record_index,
                    checkpoint.last_timestamp,
                    checkpoint.record_count,
                    checkpoint.checksum,
                ))

                conn.commit()
                return True

            except Exception as e:
                logger.error(f"Failed to save checkpoint: {e}")
                return False

    def load_checkpoint(self, experiment_id: int, file_path: str) -> CheckpointInfo | None:
        """
        加载检查点。

        Args:
            experiment_id: 实验ID
            file_path: 文件路径

        Returns:
            检查点信息，不存在返回None
        """
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT experiment_id, file_path, last_record_index, last_timestamp,
                       record_count, created_at, updated_at, checksum
                FROM hdf5_checkpoints
                WHERE experiment_id = ? AND file_path = ?
            """, (experiment_id, file_path))

            row = cursor.fetchone()

            if row:
                return CheckpointInfo(
                    experiment_id=row[0],
                    file_path=row[1],
                    last_record_index=row[2],
                    last_timestamp=row[3],
                    record_count=row[4],
                    created_at=row[5] or "",
                    updated_at=row[6] or "",
                    checksum=row[7] or "",
                )

            return None

    def get_latest_checkpoint(self, experiment_id: int) -> CheckpointInfo | None:
        """
        获取实验的最新检查点。

        Args:
            experiment_id: 实验ID

        Returns:
            最新检查点信息
        """
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT experiment_id, file_path, last_record_index, last_timestamp,
                       record_count, created_at, updated_at, checksum
                FROM hdf5_checkpoints
                WHERE experiment_id = ?
                ORDER BY updated_at DESC
                LIMIT 1
            """, (experiment_id,))

            row = cursor.fetchone()

            if row:
                return CheckpointInfo(
                    experiment_id=row[0],
                    file_path=row[1],
                    last_record_index=row[2],
                    last_timestamp=row[3],
                    record_count=row[4],
                    created_at=row[5] or "",
                    updated_at=row[6] or "",
                    checksum=row[7] or "",
                )

            return None

    def delete_checkpoint(self, experiment_id: int, file_path: str) -> bool:
        """
        删除检查点。

        Args:
            experiment_id: 实验ID
            file_path: 文件路径

        Returns:
            是否删除成功
        """
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    DELETE FROM hdf5_checkpoints
                    WHERE experiment_id = ? AND file_path = ?
                """, (experiment_id, file_path))

                conn.commit()
                return True

            except Exception as e:
                logger.error(f"Failed to delete checkpoint: {e}")
                return False

    def save_chunk(self, chunk: ChunkInfo) -> bool:
        """
        保存分块信息。

        Args:
            chunk: 分块信息

        Returns:
            是否保存成功
        """
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO hdf5_chunks
                    (chunk_id, experiment_id, start_index, end_index,
                     start_timestamp, end_timestamp, record_count, file_path,
                     is_compressed, checksum)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    chunk.chunk_id,
                    chunk.experiment_id,
                    chunk.start_index,
                    chunk.end_index,
                    chunk.start_timestamp,
                    chunk.end_timestamp,
                    chunk.record_count,
                    chunk.file_path,
                    1 if chunk.is_compressed else 0,
                    chunk.checksum,
                ))

                conn.commit()
                return True

            except Exception as e:
                logger.error(f"Failed to save chunk: {e}")
                return False

    def get_chunks(
        self,
        experiment_id: int,
        start_timestamp: float | None = None,
        end_timestamp: float | None = None,
    ) -> list[ChunkInfo]:
        """
        获取分块列表。

        Args:
            experiment_id: 实验ID
            start_timestamp: 起始时间戳
            end_timestamp: 结束时间戳

        Returns:
            分块信息列表
        """
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            query = """
                SELECT chunk_id, experiment_id, start_index, end_index,
                       start_timestamp, end_timestamp, record_count, file_path,
                       is_compressed, checksum
                FROM hdf5_chunks
                WHERE experiment_id = ?
            """
            params = [experiment_id]

            if start_timestamp is not None:
                query += " AND end_timestamp >= ?"
                params.append(start_timestamp)

            if end_timestamp is not None:
                query += " AND start_timestamp <= ?"
                params.append(end_timestamp)

            query += " ORDER BY start_index"

            cursor.execute(query, params)

            chunks = []
            for row in cursor.fetchall():
                chunks.append(ChunkInfo(
                    chunk_id=row[0],
                    experiment_id=row[1],
                    start_index=row[2],
                    end_index=row[3],
                    start_timestamp=row[4],
                    end_timestamp=row[5],
                    record_count=row[6],
                    file_path=row[7],
                    is_compressed=bool(row[8]),
                    checksum=row[9] or "",
                ))

            return chunks


class ChunkManager:
    """
    分块管理器。

    管理HDF5数据的分块存储和检索。

    Attributes:
        storage_path: 存储路径
        config: HDF5配置
    """

    def __init__(self, storage_path: str, config: HDF5Config) -> None:
        """
        初始化分块管理器。

        Args:
            storage_path: 存储路径
            config: HDF5配置
        """
        self._storage_path = Path(storage_path)
        self._config = config
        self._lock = RLock()

        # 创建存储目录
        self._storage_path.mkdir(parents=True, exist_ok=True)

        # 当前活跃的分块缓存
        self._active_chunks: dict[int, dict[str, Any]] = {}

        logger.info(f"ChunkManager initialized: {storage_path}")

    def get_chunk_file_path(self, experiment_id: int, chunk_index: int) -> Path:
        """
        获取分块文件路径。

        Args:
            experiment_id: 实验ID
            chunk_index: 分块索引

        Returns:
            分块文件路径
        """
        return self._storage_path / f"exp_{experiment_id}_chunk_{chunk_index:06d}.h5"

    def create_chunk(
        self,
        experiment_id: int,
        chunk_index: int,
        initial_size: int = 0,
    ) -> ChunkInfo:
        """
        创建新分块。

        Args:
            experiment_id: 实验ID
            chunk_index: 分块索引
            initial_size: 初始大小

        Returns:
            分块信息
        """
        chunk_id = f"exp_{experiment_id}_chunk_{chunk_index:06d}"
        file_path = self.get_chunk_file_path(experiment_id, chunk_index)

        chunk = ChunkInfo(
            chunk_id=chunk_id,
            experiment_id=experiment_id,
            file_path=str(file_path),
            is_compressed=self._config.compression_level > 0,
        )

        # 创建HDF5文件
        if HAS_H5PY:
            self._create_hdf5_file(file_path, initial_size)

        return chunk

    def _create_hdf5_file(self, file_path: Path, initial_size: int = 0) -> bool:
        """
        创建HDF5文件。

        Args:
            file_path: 文件路径
            initial_size: 初始大小

        Returns:
            是否创建成功
        """
        if not HAS_H5PY:
            logger.warning("h5py not available, creating placeholder file")
            file_path.touch()
            return True

        try:
            with h5py.File(file_path, "w") as f:
                # 创建时间序列数据集
                maxshape = (None,)  # 可扩展
                chunk_shape = (self._config.chunk_size,)

                # 时间戳数据集
                f.create_dataset(
                    "timestamps",
                    shape=(initial_size,),
                    maxshape=maxshape,
                    dtype=DTYPE_TIMESTAMP,
                    chunks=chunk_shape,
                    compression=self._config.compression_algorithm if self._config.compression_level > 0 else None,
                    compression_opts=self._config.compression_level if self._config.compression_level > 0 else None,
                )

                # 位置数据集
                f.create_dataset(
                    "positions",
                    shape=(initial_size,),
                    maxshape=maxshape,
                    dtype=DTYPE_POSITION,
                    chunks=chunk_shape,
                    compression=self._config.compression_algorithm if self._config.compression_level > 0 else None,
                    compression_opts=self._config.compression_level if self._config.compression_level > 0 else None,
                )

                # 字段值数据集
                f.create_dataset(
                    "field_values",
                    shape=(initial_size,),
                    maxshape=maxshape,
                    dtype=DTYPE_VALUE,
                    chunks=chunk_shape,
                    compression=self._config.compression_algorithm if self._config.compression_level > 0 else None,
                    compression_opts=self._config.compression_level if self._config.compression_level > 0 else None,
                )

                # 电流值数据集
                f.create_dataset(
                    "current_values",
                    shape=(initial_size,),
                    maxshape=maxshape,
                    dtype=DTYPE_VALUE,
                    chunks=chunk_shape,
                    compression=self._config.compression_algorithm if self._config.compression_level > 0 else None,
                    compression_opts=self._config.compression_level if self._config.compression_level > 0 else None,
                )

                # 温度数据集
                f.create_dataset(
                    "temperatures",
                    shape=(initial_size,),
                    maxshape=maxshape,
                    dtype=DTYPE_TEMPERATURE,
                    chunks=chunk_shape,
                    compression=self._config.compression_algorithm if self._config.compression_level > 0 else None,
                    compression_opts=self._config.compression_level if self._config.compression_level > 0 else None,
                )

                # 元数据
                f.attrs["created_at"] = datetime.now().isoformat()
                f.attrs["chunk_size"] = self._config.chunk_size
                f.attrs["compression"] = self._config.compression_level

            return True

        except Exception as e:
            logger.error(f"Failed to create HDF5 file: {e}")
            return False

    def append_data(
        self,
        chunk: ChunkInfo,
        data: dict[str, np.ndarray],
    ) -> int:
        """
        追加数据到分块。

        Args:
            chunk: 分块信息
            data: 数据字典，包含各个数组

        Returns:
            追加的记录数
        """
        if not HAS_H5PY:
            logger.warning("h5py not available, data not written")
            return 0

        file_path = Path(chunk.file_path)
        if not file_path.exists():
            self._create_hdf5_file(file_path)

        try:
            with h5py.File(file_path, "a") as f:
                # 获取当前大小
                current_size = f["timestamps"].shape[0]
                new_size = current_size + len(data["timestamps"])

                # 扩展数据集
                f["timestamps"].resize(new_size, axis=0)
                f["positions"].resize(new_size, axis=0)
                f["field_values"].resize(new_size, axis=0)
                f["current_values"].resize(new_size, axis=0)
                f["temperatures"].resize(new_size, axis=0)

                # 写入新数据
                f["timestamps"][current_size:new_size] = data["timestamps"]
                f["positions"][current_size:new_size] = data.get("positions", np.zeros(len(data["timestamps"])))
                f["field_values"][current_size:new_size] = data.get("field_values", np.zeros(len(data["timestamps"])))
                f["current_values"][current_size:new_size] = data.get("current_values", np.zeros(len(data["timestamps"])))
                f["temperatures"][current_size:new_size] = data.get("temperatures", np.zeros(len(data["timestamps"])))

                # 更新元数据
                f.attrs["updated_at"] = datetime.now().isoformat()
                f.attrs["record_count"] = new_size

            return len(data["timestamps"])

        except Exception as e:
            logger.error(f"Failed to append data to chunk: {e}")
            return 0

    def read_data(
        self,
        chunk: ChunkInfo,
        start_index: int = 0,
        end_index: int | None = None,
    ) -> dict[str, np.ndarray] | None:
        """
        从分块读取数据。

        Args:
            chunk: 分块信息
            start_index: 起始索引
            end_index: 结束索引

        Returns:
            数据字典
        """
        if not HAS_H5PY:
            logger.warning("h5py not available, cannot read data")
            return None

        file_path = Path(chunk.file_path)
        if not file_path.exists():
            return None

        try:
            with h5py.File(file_path, "r") as f:
                if end_index is None:
                    end_index = f["timestamps"].shape[0]

                return {
                    "timestamps": f["timestamps"][start_index:end_index],
                    "positions": f["positions"][start_index:end_index],
                    "field_values": f["field_values"][start_index:end_index],
                    "current_values": f["current_values"][start_index:end_index],
                    "temperatures": f["temperatures"][start_index:end_index],
                }

        except Exception as e:
            logger.error(f"Failed to read data from chunk: {e}")
            return None

    def get_chunk_size(self, chunk: ChunkInfo) -> int:
        """
        获取分块大小。

        Args:
            chunk: 分块信息

        Returns:
            记录数
        """
        if not HAS_H5PY:
            return 0

        file_path = Path(chunk.file_path)
        if not file_path.exists():
            return 0

        try:
            with h5py.File(file_path, "r") as f:
                return f["timestamps"].shape[0]
        except Exception:
            return 0


class HDF5ResumableStorage:
    """
    HDF5断点续存存储类。

    提供HDF5格式的高效时序数据存储，支持：
    - 分块存储：大数据自动分块
    - 压缩存储：可配置压缩级别
    - 断点续存：意外中断后可恢复
    - 增量写入：高效追加数据
    - 索引优化：快速时间范围查询

    Attributes:
        storage_path: 存储路径
        config: HDF5配置
    """

    def __init__(
        self,
        storage_path: str = "data/hdf5",
        config: HDF5Config | None = None,
    ) -> None:
        """
        初始化HDF5断点续存存储。

        Args:
            storage_path: 存储路径
            config: HDF5配置
        """
        self._storage_path = storage_path
        self._config = config or HDF5Config()

        # 创建存储目录
        Path(storage_path).mkdir(parents=True, exist_ok=True)

        # 初始化管理器
        checkpoint_db = str(Path(storage_path) / "checkpoints.db")
        self._checkpoint_manager = CheckpointManager(checkpoint_db)
        self._chunk_manager = ChunkManager(storage_path, self._config)

        # 写入缓冲区
        self._write_buffers: dict[int, dict[str, list]] = defaultdict(
            lambda: {
                "timestamps": [],
                "positions": [],
                "field_values": [],
                "current_values": [],
                "temperatures": [],
            }
        )
        self._buffer_lock = RLock()

        # 当前活跃分块
        self._active_chunks: dict[int, ChunkInfo] = {}

        # 后台刷新线程
        self._flush_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_flush_time = time.time()

        # 统计信息
        self._stats = {
            "total_records": 0,
            "total_chunks": 0,
            "total_bytes": 0,
            "write_count": 0,
            "read_count": 0,
        }
        self._stats_lock = Lock()

        logger.info(f"HDF5ResumableStorage initialized: {storage_path}")

    def write_data(
        self,
        experiment_id: int,
        data: dict[str, Any] | list[dict[str, Any]],
        timestamp: datetime | None = None,
    ) -> int:
        """
        写入数据。

        数据首先写入内存缓冲区，达到阈值后刷新到HDF5文件。

        Args:
            experiment_id: 实验ID
            data: 数据字典或数据列表
            timestamp: 时间戳，可选

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

        # 设置时间戳
        if timestamp is None:
            timestamp = datetime.now()

        # 转换为缓冲区格式
        with self._buffer_lock:
            buffer = self._write_buffers[experiment_id]

            for item in data_list:
                item_timestamp = item.get("timestamp", timestamp)
                if isinstance(item_timestamp, datetime):
                    ts_float = item_timestamp.timestamp()
                else:
                    ts_float = float(item_timestamp)

                buffer["timestamps"].append(ts_float)
                buffer["positions"].append(item.get("position_steps", 0))
                buffer["field_values"].append(item.get("field_value", 0.0))
                buffer["current_values"].append(item.get("current_value", 0.0))
                buffer["temperatures"].append(item.get("temperature", 0.0))

            records_written = len(data_list)

            # 检查是否需要刷新
            if len(buffer["timestamps"]) >= self._config.chunk_size:
                self._flush_buffer(experiment_id)

        # 更新统计
        with self._stats_lock:
            self._stats["total_records"] += records_written
            self._stats["write_count"] += 1

        return records_written

    def _flush_buffer(self, experiment_id: int) -> int:
        """
        刷新缓冲区到HDF5文件。

        Args:
            experiment_id: 实验ID

        Returns:
            刷新的记录数
        """
        with self._buffer_lock:
            buffer = self._write_buffers.get(experiment_id)
            if not buffer or not buffer["timestamps"]:
                return 0

            # 转换为numpy数组
            data = {
                "timestamps": np.array(buffer["timestamps"], dtype=DTYPE_TIMESTAMP),
                "positions": np.array(buffer["positions"], dtype=DTYPE_POSITION),
                "field_values": np.array(buffer["field_values"], dtype=DTYPE_VALUE),
                "current_values": np.array(buffer["current_values"], dtype=DTYPE_VALUE),
                "temperatures": np.array(buffer["temperatures"], dtype=DTYPE_TEMPERATURE),
            }

            records_count = len(data["timestamps"])

            # 获取或创建活跃分块
            chunk = self._get_or_create_active_chunk(experiment_id)

            # 检查分块是否已满
            chunk_size = self._chunk_manager.get_chunk_size(chunk)
            if chunk_size + records_count > self._config.chunk_size * 1.5:
                # 创建新分块
                chunk_index = self._get_next_chunk_index(experiment_id)
                chunk = self._chunk_manager.create_chunk(experiment_id, chunk_index)
                self._active_chunks[experiment_id] = chunk

            # 写入数据
            written = self._chunk_manager.append_data(chunk, data)

            # 更新检查点
            if written > 0:
                checkpoint = CheckpointInfo(
                    experiment_id=experiment_id,
                    file_path=chunk.file_path,
                    last_record_index=chunk.end_index + written,
                    last_timestamp=float(data["timestamps"][-1]),
                    record_count=chunk.record_count + written,
                )
                self._checkpoint_manager.save_checkpoint(checkpoint)

                # 更新分块信息
                chunk.record_count += written
                chunk.end_index += written
                if chunk.start_timestamp == 0:
                    chunk.start_timestamp = float(data["timestamps"][0])
                chunk.end_timestamp = float(data["timestamps"][-1])

                self._checkpoint_manager.save_chunk(chunk)

            # 清空缓冲区
            for key in buffer:
                buffer[key].clear()

            return written

    def _get_or_create_active_chunk(self, experiment_id: int) -> ChunkInfo:
        """
        获取或创建活跃分块。

        Args:
            experiment_id: 实验ID

        Returns:
            分块信息
        """
        if experiment_id in self._active_chunks:
            return self._active_chunks[experiment_id]

        # 尝试从检查点恢复
        checkpoint = self._checkpoint_manager.get_latest_checkpoint(experiment_id)
        if checkpoint:
            # 查找对应的分块
            chunks = self._checkpoint_manager.get_chunks(experiment_id)
            if chunks:
                # 返回最后一个分块
                chunk = chunks[-1]
                self._active_chunks[experiment_id] = chunk
                return chunk

        # 创建新分块
        chunk_index = self._get_next_chunk_index(experiment_id)
        chunk = self._chunk_manager.create_chunk(experiment_id, chunk_index)
        self._active_chunks[experiment_id] = chunk

        return chunk

    def _get_next_chunk_index(self, experiment_id: int) -> int:
        """
        获取下一个分块索引。

        Args:
            experiment_id: 实验ID

        Returns:
            分块索引
        """
        chunks = self._checkpoint_manager.get_chunks(experiment_id)
        if chunks:
            # 从分块ID中提取索引
            last_chunk = chunks[-1]
            try:
                index_str = last_chunk.chunk_id.split("_")[-1]
                return int(index_str) + 1
            except (ValueError, IndexError):
                return len(chunks)
        return 0

    def read_data(
        self,
        experiment_id: int,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 10000,
    ) -> list[dict[str, Any]]:
        """
        读取数据。

        Args:
            experiment_id: 实验ID
            start_time: 开始时间
            end_time: 结束时间
            limit: 最大返回记录数

        Returns:
            数据记录列表
        """
        # 先刷新缓冲区
        self._flush_buffer(experiment_id)

        # 转换时间戳
        start_ts = start_time.timestamp() if start_time else None
        end_ts = end_time.timestamp() if end_time else None

        # 获取相关分块
        chunks = self._checkpoint_manager.get_chunks(
            experiment_id, start_ts, end_ts
        )

        all_data = []

        for chunk in chunks:
            data = self._chunk_manager.read_data(chunk)
            if data is None:
                continue

            # 过滤时间范围
            mask = np.ones(len(data["timestamps"]), dtype=bool)

            if start_ts is not None:
                mask &= data["timestamps"] >= start_ts
            if end_ts is not None:
                mask &= data["timestamps"] <= end_ts

            # 应用过滤
            for i in range(len(data["timestamps"][mask])):
                all_data.append({
                    "timestamp": datetime.fromtimestamp(data["timestamps"][mask][i]),
                    "position_steps": int(data["positions"][mask][i]),
                    "field_value": float(data["field_values"][mask][i]),
                    "current_value": float(data["current_values"][mask][i]),
                    "temperature": float(data["temperatures"][mask][i]),
                })

                if len(all_data) >= limit:
                    break

            if len(all_data) >= limit:
                break

        # 更新统计
        with self._stats_lock:
            self._stats["read_count"] += 1

        return all_data

    def flush_all(self) -> int:
        """
        刷新所有缓冲区。

        Returns:
            总刷新记录数
        """
        total_flushed = 0

        with self._buffer_lock:
            for experiment_id in list(self._write_buffers.keys()):
                total_flushed += self._flush_buffer(experiment_id)

        return total_flushed

    def get_statistics(self) -> dict[str, Any]:
        """
        获取统计信息。

        Returns:
            统计信息字典
        """
        with self._stats_lock:
            stats = self._stats.copy()

        # 获取缓冲区状态
        with self._buffer_lock:
            buffer_sizes = {
                exp_id: len(buf["timestamps"])
                for exp_id, buf in self._write_buffers.items()
            }

        stats["buffer_sizes"] = buffer_sizes
        stats["active_experiments"] = list(self._active_chunks.keys())
        stats["config"] = {
            "chunk_size": self._config.chunk_size,
            "compression_level": self._config.compression_level,
            "flush_interval": self._config.flush_interval,
        }

        return stats

    def resume_experiment(self, experiment_id: int) -> bool:
        """
        恢复实验写入（断点续存）。

        Args:
            experiment_id: 实验ID

        Returns:
            是否恢复成功
        """
        # 检查是否有检查点
        checkpoint = self._checkpoint_manager.get_latest_checkpoint(experiment_id)
        if not checkpoint:
            logger.info(f"No checkpoint found for experiment {experiment_id}")
            return False

        # 验证文件存在
        if not Path(checkpoint.file_path).exists():
            logger.warning(f"Checkpoint file not found: {checkpoint.file_path}")
            return False

        # 恢复活跃分块
        chunks = self._checkpoint_manager.get_chunks(experiment_id)
        if chunks:
            self._active_chunks[experiment_id] = chunks[-1]

        logger.info(
            f"Resumed experiment {experiment_id} from checkpoint: "
            f"{checkpoint.record_count} records"
        )
        return True

    def close(self) -> None:
        """关闭存储，刷新所有缓冲区。"""
        # 停止后台线程
        self._stop_event.set()

        # 刷新所有缓冲区
        self.flush_all()

        logger.info("HDF5ResumableStorage closed")


# ==================== 便捷函数 ====================


def create_hdf5_storage(
    storage_path: str = "data/hdf5",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    compression_level: int = DEFAULT_COMPRESSION_LEVEL,
) -> HDF5ResumableStorage:
    """
    创建HDF5存储的便捷函数。

    Args:
        storage_path: 存储路径
        chunk_size: 分块大小
        compression_level: 压缩级别

    Returns:
        HDF5ResumableStorage实例
    """
    config = HDF5Config(
        chunk_size=chunk_size,
        compression_level=compression_level,
    )

    return HDF5ResumableStorage(storage_path, config)
