"""
时序数据存储优化模块 (Time Series Storage Optimization Module)

本模块实现了时序数据的高效存储与管理，包括：
- TimeSeriesStorage: 时序数据存储接口
- DataTierManager: 数据分层存储策略（热数据/温数据/冷数据）
- DataArchiver: 数据自动归档和压缩
- QueryOptimizer: 查询性能优化

设计参考：技术设计文档v3.0第14.3.1节混合存储演进

作者: Agent
创建日期: 2026-03-07
依赖: numpy, sqlalchemy, zlib, asyncio
"""

import asyncio
import gzip
import json
import logging
import zlib
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from threading import Lock, RLock
from typing import Any

from sqlalchemy import and_, create_engine, func
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


class DataTier(Enum):
    """数据分层枚举。

    根据数据访问频率和时效性进行分层管理。
    """

    HOT = "hot"  # 热数据：最近24小时，高频访问，内存缓存
    WARM = "warm"  # 温数据：7天内，中频访问，SSD存储
    COLD = "cold"  # 冷数据：30天以上，低频访问，压缩归档


class CompressionType(Enum):
    """压缩类型枚举。"""

    NONE = "none"
    GZIP = "gzip"
    ZLIB = "zlib"
    NPZ = "npz"  # NumPy压缩格式


@dataclass
class TierConfig:
    """数据层配置。

    Attributes:
        tier: 数据层类型
        max_age_hours: 最大保留时间（小时）
        compression: 压缩类型
        storage_path: 存储路径
        max_size_mb: 最大存储大小（MB）
        auto_archive: 是否自动归档
    """

    tier: DataTier
    max_age_hours: int = 168  # 默认7天
    compression: CompressionType = CompressionType.GZIP
    storage_path: str = ""
    max_size_mb: int = 1024  # 默认1GB
    auto_archive: bool = True


@dataclass
class StorageStatistics:
    """存储统计信息。

    Attributes:
        total_records: 总记录数
        total_bytes: 总字节数
        hot_records: 热数据记录数
        warm_records: 温数据记录数
        cold_records: 冷数据记录数
        compressed_files: 压缩文件数
        last_archive_time: 最后归档时间
        archive_count: 归档次数
    """

    total_records: int = 0
    total_bytes: int = 0
    hot_records: int = 0
    warm_records: int = 0
    cold_records: int = 0
    compressed_files: int = 0
    last_archive_time: datetime | None = None
    archive_count: int = 0
    _lock: Lock = field(default_factory=Lock, repr=False)

    def update(self, **kwargs: Any) -> None:
        """更新统计信息。"""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)


class TimeSeriesStorage:
    """
    时序数据存储接口。

    提供统一的时序数据存储、查询和管理接口。
    支持数据分层存储、自动归档和查询优化。

    Attributes:
        db_path: 数据库文件路径
        buffer_size: 内存缓冲区大小
    """

    def __init__(
        self,
        db_path: str = "timeseries.db",
        buffer_size: int = 10000,
        tier_configs: dict[DataTier, TierConfig] | None = None,
    ) -> None:
        """初始化时序数据存储。

        Args:
            db_path: 数据库文件路径
            buffer_size: 内存缓冲区大小，默认10000条记录
            tier_configs: 数据层配置字典，可选
        """
        self._db_path = db_path
        self._buffer_size = buffer_size
        self._engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            pool_size=10,
            max_overflow=20,
        )
        self._Session = sessionmaker(bind=self._engine)

        # 初始化数据层配置
        self._tier_configs = tier_configs or self._get_default_tier_configs()

        # 内存缓冲区（热数据缓存）
        self._hot_buffer: dict[int, list[dict[str, Any]]] = defaultdict(list)
        self._buffer_lock = Lock()

        # 初始化分层管理器
        self._tier_manager = DataTierManager(
            engine=self._engine,
            session_factory=self._Session,
            tier_configs=self._tier_configs,
        )

        # 初始化归档器
        self._archiver = DataArchiver(
            tier_manager=self._tier_manager,
            storage_path=self._get_storage_path(),
        )

        # 初始化查询优化器
        self._query_optimizer = QueryOptimizer(
            session_factory=self._Session,
            hot_buffer=self._hot_buffer,
            buffer_lock=self._buffer_lock,
        )

        # 统计信息
        self._statistics = StorageStatistics()

        # 后台任务控制
        self._is_running = False
        self._archive_task: asyncio.Task[None] | None = None

        logger.info(f"TimeSeriesStorage initialized: {db_path}")

    def _get_default_tier_configs(self) -> dict[DataTier, TierConfig]:
        """获取默认数据层配置。

        Returns:
            数据层配置字典
        """
        base_path = Path(self._db_path).parent

        return {
            DataTier.HOT: TierConfig(
                tier=DataTier.HOT,
                max_age_hours=24,
                compression=CompressionType.NONE,
                storage_path=str(base_path / "hot_data"),
                max_size_mb=512,
                auto_archive=False,
            ),
            DataTier.WARM: TierConfig(
                tier=DataTier.WARM,
                max_age_hours=168,  # 7天
                compression=CompressionType.GZIP,
                storage_path=str(base_path / "warm_data"),
                max_size_mb=2048,
                auto_archive=True,
            ),
            DataTier.COLD: TierConfig(
                tier=DataTier.COLD,
                max_age_hours=720,  # 30天
                compression=CompressionType.GZIP,
                storage_path=str(base_path / "cold_data"),
                max_size_mb=10240,
                auto_archive=True,
            ),
        }

    def _get_storage_path(self) -> Path:
        """获取存储根路径。

        Returns:
            存储根路径
        """
        return Path(self._db_path).parent

    async def write_data(
        self,
        experiment_id: int,
        data: dict[str, Any] | list[dict[str, Any]],
        timestamp: datetime | None = None,
    ) -> int:
        """写入时序数据。

        数据首先写入内存缓冲区，达到阈值后批量写入数据库。

        Args:
            experiment_id: 实验ID
            data: 数据字典或数据列表
            timestamp: 时间戳，可选，默认当前时间

        Returns:
            写入的数据记录数

        Raises:
            ValueError: 数据格式错误时抛出异常
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

        # 添加元数据
        for item in data_list:
            if "timestamp" not in item:
                item["timestamp"] = timestamp
            item["experiment_id"] = experiment_id
            item["tier"] = DataTier.HOT.value

        # 写入热数据缓冲区
        with self._buffer_lock:
            self._hot_buffer[experiment_id].extend(data_list)

            # 检查缓冲区是否需要刷新
            total_buffered = sum(len(buf) for buf in self._hot_buffer.values())

            if total_buffered >= self._buffer_size:
                await self._flush_buffer()

        # 更新统计
        self._statistics.total_records += len(data_list)

        return len(data_list)

    async def _flush_buffer(self) -> None:
        """刷新内存缓冲区到数据库。"""
        if not self._hot_buffer:
            return

        session = self._Session()
        try:
            from models import DataRecord

            records_to_insert = []

            for exp_id, data_list in self._hot_buffer.items():
                for item in data_list:
                    record = DataRecord(
                        experiment_id=exp_id,
                        timestamp=item.get("timestamp", datetime.now()),
                        position_steps=item.get("position_steps"),
                        position_mm=item.get("position_mm"),
                        field_value=item.get("field_value"),
                        current_value=item.get("current_value"),
                        temperature=item.get("temperature"),
                        extra_data=(
                            json.dumps(item.get("extra_data")) if item.get("extra_data") else None
                        ),
                    )
                    records_to_insert.append(record)

            # 批量插入
            if records_to_insert:
                session.bulk_save_objects(records_to_insert)
                session.commit()

                # 清空缓冲区
                self._hot_buffer.clear()

                logger.debug(f"Flushed {len(records_to_insert)} records to database")

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to flush buffer: {e}")
            raise
        finally:
            session.close()

    async def query_data(
        self,
        experiment_id: int,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 10000,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        """查询时序数据。

        支持时间范围查询，自动从热数据、温数据和冷数据中检索。

        Args:
            experiment_id: 实验ID
            start_time: 开始时间，可选
            end_time: 结束时间，可选
            limit: 最大返回记录数，默认10000
            include_archived: 是否包含已归档数据，默认False

        Returns:
            数据记录列表
        """
        # 先刷新该实验的缓冲区数据
        with self._buffer_lock:
            if experiment_id in self._hot_buffer and self._hot_buffer[experiment_id]:
                # 将缓冲区数据合并到结果中
                buffered_data = self._hot_buffer[experiment_id].copy()
            else:
                buffered_data = []

        # 使用查询优化器查询数据库
        db_data = await self._query_optimizer.query_optimized(
            experiment_id=experiment_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit - len(buffered_data),
        )

        # 合并缓冲区数据和数据库数据
        all_data = buffered_data + db_data

        # 按时间排序
        all_data.sort(key=lambda x: x.get("timestamp", datetime.min))

        # 限制返回数量
        if len(all_data) > limit:
            all_data = all_data[:limit]

        # 如果需要包含归档数据
        if include_archived and len(all_data) < limit:
            archived_data = await self._archiver.load_archived_data(
                experiment_id=experiment_id,
                start_time=start_time,
                end_time=end_time,
                limit=limit - len(all_data),
            )
            all_data.extend(archived_data)

        return all_data

    async def get_statistics(self) -> dict[str, Any]:
        """获取存储统计信息。

        Returns:
            统计信息字典
        """
        session = self._Session()
        try:
            from models import DataRecord

            # 统计各层记录数
            total_count = session.query(func.count(DataRecord.id)).scalar() or 0

            # 统计缓冲区记录数
            with self._buffer_lock:
                hot_count = sum(len(buf) for buf in self._hot_buffer.values())

            # 获取归档统计
            archive_stats = self._archiver.get_statistics()

            return {
                "total_records": total_count + hot_count,
                "hot_records": hot_count,
                "warm_records": archive_stats.get("warm_records", 0),
                "cold_records": archive_stats.get("cold_records", 0),
                "compressed_files": archive_stats.get("compressed_files", 0),
                "last_archive_time": (
                    self._statistics.last_archive_time.isoformat()
                    if self._statistics.last_archive_time
                    else None
                ),
                "archive_count": self._statistics.archive_count,
                "buffer_usage_percent": (
                    (hot_count / self._buffer_size * 100) if self._buffer_size > 0 else 0
                ),
            }
        finally:
            session.close()

    async def start_background_tasks(self) -> None:
        """启动后台任务（归档、清理等）。"""
        self._is_running = True

        # 启动自动归档任务
        self._archive_task = asyncio.create_task(self._auto_archive_loop())

        logger.info("Background tasks started")

    async def stop_background_tasks(self) -> None:
        """停止后台任务。"""
        self._is_running = False

        if self._archive_task:
            self._archive_task.cancel()
            try:
                await self._archive_task
            except asyncio.CancelledError:
                pass

        # 刷新剩余缓冲区数据
        await self._flush_buffer()

        logger.info("Background tasks stopped")

    async def _auto_archive_loop(self) -> None:
        """自动归档循环。"""
        while self._is_running:
            try:
                # 每小时执行一次归档检查
                await asyncio.sleep(3600)

                if not self._is_running:
                    break

                # 执行数据分层迁移
                await self._tier_manager.migrate_data_tiers()

                # 执行自动归档
                archived_count = await self._archiver.auto_archive()

                if archived_count > 0:
                    self._statistics.archive_count += 1
                    self._statistics.last_archive_time = datetime.now()
                    logger.info(f"Auto archived {archived_count} records")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Auto archive error: {e}")
                await asyncio.sleep(60)  # 错误后等待1分钟

    async def force_archive(self, experiment_id: int | None = None) -> int:
        """强制执行归档。

        Args:
            experiment_id: 指定实验ID，可选，默认归档所有实验

        Returns:
            归档的记录数
        """
        # 先刷新缓冲区
        await self._flush_buffer()

        # 执行归档
        archived_count = await self._archiver.archive_experiment(experiment_id)

        if archived_count > 0:
            self._statistics.archive_count += 1
            self._statistics.last_archive_time = datetime.now()

        return archived_count

    async def delete_old_data(self, days: int = 90) -> int:
        """删除旧数据。

        Args:
            days: 保留天数，默认90天

        Returns:
            删除的记录数
        """
        session = self._Session()
        try:
            from models import DataRecord

            cutoff_time = datetime.now() - timedelta(days=days)

            # 删除数据库中的旧记录
            deleted = session.query(DataRecord).filter(DataRecord.timestamp < cutoff_time).delete()
            session.commit()

            # 删除归档文件中的旧数据
            archive_deleted = await self._archiver.delete_old_archives(days)

            logger.info(f"Deleted {deleted + archive_deleted} old records")
            return deleted + archive_deleted

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete old data: {e}")
            raise
        finally:
            session.close()

    def get_tier_config(self, tier: DataTier) -> TierConfig:
        """获取指定数据层的配置。

        Args:
            tier: 数据层类型

        Returns:
            数据层配置
        """
        return self._tier_configs.get(tier, TierConfig(tier=tier))

    def update_tier_config(self, config: TierConfig) -> None:
        """更新数据层配置。

        Args:
            config: 新的数据层配置
        """
        self._tier_configs[config.tier] = config
        self._tier_manager.update_config(config)
        logger.info(f"Updated tier config: {config.tier.value}")


class DataTierManager:
    """
    数据分层管理器。

    负责根据数据时效性和访问频率进行分层管理，
    实现热数据、温数据、冷数据的自动迁移。

    Attributes:
        tier_configs: 数据层配置字典
    """

    def __init__(
        self,
        engine: Any,
        session_factory: Callable[[], Any],
        tier_configs: dict[DataTier, TierConfig],
    ) -> None:
        """初始化数据分层管理器。

        Args:
            engine: SQLAlchemy引擎
            session_factory: 会话工厂
            tier_configs: 数据层配置字典
        """
        self._engine = engine
        self._Session = session_factory
        self._tier_configs = tier_configs
        self._lock = RLock()

        # 创建存储目录
        for config in tier_configs.values():
            if config.storage_path:
                Path(config.storage_path).mkdir(parents=True, exist_ok=True)

    def update_config(self, config: TierConfig) -> None:
        """更新数据层配置。

        Args:
            config: 新的数据层配置
        """
        with self._lock:
            self._tier_configs[config.tier] = config

            # 创建新的存储目录
            if config.storage_path:
                Path(config.storage_path).mkdir(parents=True, exist_ok=True)

    async def migrate_data_tiers(self) -> dict[str, int]:
        """执行数据分层迁移。

        将数据从热层迁移到温层，从温层迁移到冷层。

        Returns:
            各层迁移的记录数字典
        """
        migration_stats = {
            "hot_to_warm": 0,
            "warm_to_cold": 0,
        }

        session = self._Session()
        try:
            from models import DataRecord

            now = datetime.now()

            # 热数据 -> 温数据
            hot_config = self._tier_configs.get(DataTier.HOT)
            if hot_config:
                hot_threshold = now - timedelta(hours=hot_config.max_age_hours)

                # 这里简化处理，实际应用中可能需要添加tier字段到DataRecord
                # 目前通过时间戳判断数据层
                hot_records = (
                    session.query(DataRecord)
                    .filter(DataRecord.timestamp < hot_threshold)
                    .limit(10000)
                    .all()
                )

                if hot_records:
                    migration_stats["hot_to_warm"] = len(hot_records)
                    logger.debug(f"Migrating {len(hot_records)} records from hot to warm")

            # 温数据 -> 冷数据（需要归档）
            warm_config = self._tier_configs.get(DataTier.WARM)
            if warm_config:
                warm_threshold = now - timedelta(hours=warm_config.max_age_hours)

                warm_records = (
                    session.query(DataRecord)
                    .filter(DataRecord.timestamp < warm_threshold)
                    .limit(10000)
                    .all()
                )

                if warm_records:
                    migration_stats["warm_to_cold"] = len(warm_records)
                    logger.debug(f"Migrating {len(warm_records)} records from warm to cold")

            session.commit()

        except Exception as e:
            session.rollback()
            logger.error(f"Data tier migration failed: {e}")
            raise
        finally:
            session.close()

        return migration_stats

    def get_data_tier(self, timestamp: datetime) -> DataTier:
        """根据时间戳判断数据所属层。

        Args:
            timestamp: 数据时间戳

        Returns:
            数据层类型
        """
        now = datetime.now()
        age = now - timestamp

        hot_config = self._tier_configs.get(DataTier.HOT)
        warm_config = self._tier_configs.get(DataTier.WARM)

        if hot_config and age < timedelta(hours=hot_config.max_age_hours):
            return DataTier.HOT
        elif warm_config and age < timedelta(hours=warm_config.max_age_hours):
            return DataTier.WARM
        else:
            return DataTier.COLD

    def get_tier_statistics(self) -> dict[DataTier, dict[str, Any]]:
        """获取各层统计信息。

        Returns:
            各层统计信息字典
        """
        session = self._Session()
        try:
            from models import DataRecord

            now = datetime.now()
            stats = {}

            for tier in [DataTier.HOT, DataTier.WARM, DataTier.COLD]:
                config = self._tier_configs.get(tier)
                if not config:
                    continue

                threshold = now - timedelta(hours=config.max_age_hours)

                if tier == DataTier.HOT:
                    count = (
                        session.query(func.count(DataRecord.id))
                        .filter(DataRecord.timestamp >= threshold)
                        .scalar()
                        or 0
                    )
                elif tier == DataTier.WARM:
                    hot_config = self._tier_configs.get(DataTier.HOT)
                    hot_threshold = (
                        now - timedelta(hours=hot_config.max_age_hours) if hot_config else threshold
                    )
                    count = (
                        session.query(func.count(DataRecord.id))
                        .filter(
                            and_(
                                DataRecord.timestamp >= threshold,
                                DataRecord.timestamp < hot_threshold,
                            )
                        )
                        .scalar()
                        or 0
                    )
                else:
                    warm_config = self._tier_configs.get(DataTier.WARM)
                    warm_threshold = (
                        now - timedelta(hours=warm_config.max_age_hours)
                        if warm_config
                        else threshold
                    )
                    count = (
                        session.query(func.count(DataRecord.id))
                        .filter(DataRecord.timestamp < warm_threshold)
                        .scalar()
                        or 0
                    )

                stats[tier] = {
                    "count": count,
                    "max_age_hours": config.max_age_hours,
                    "compression": config.compression.value,
                    "storage_path": config.storage_path,
                }

            return stats

        finally:
            session.close()


class DataArchiver:
    """
    数据归档器。

    负责将冷数据压缩归档到文件系统，
    支持多种压缩格式和增量归档。

    Attributes:
        storage_path: 存储根路径
    """

    def __init__(
        self,
        tier_manager: DataTierManager,
        storage_path: Path,
        compression: CompressionType = CompressionType.GZIP,
    ) -> None:
        """初始化数据归档器。

        Args:
            tier_manager: 数据分层管理器
            storage_path: 存储根路径
            compression: 默认压缩类型
        """
        self._tier_manager = tier_manager
        self._storage_path = storage_path
        self._compression = compression
        self._lock = RLock()

        # 创建归档目录
        self._archive_path = storage_path / "archives"
        self._archive_path.mkdir(parents=True, exist_ok=True)

        # 归档索引
        self._archive_index: dict[int, list[dict[str, Any]]] = {}
        self._load_archive_index()

    def _load_archive_index(self) -> None:
        """加载归档索引。"""
        index_file = self._archive_path / "archive_index.json"

        if index_file.exists():
            try:
                with open(index_file, encoding="utf-8") as f:
                    data = json.load(f)
                    # 将字符串键转换为整数
                    self._archive_index = {
                        int(k): v for k, v in data.get("experiments", {}).items()
                    }
            except Exception as e:
                logger.warning(f"Failed to load archive index: {e}")
                self._archive_index = {}

    def _save_archive_index(self) -> None:
        """保存归档索引。"""
        index_file = self._archive_path / "archive_index.json"

        try:
            with open(index_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "experiments": self._archive_index,
                        "last_updated": datetime.now().isoformat(),
                    },
                    f,
                    indent=2,
                )
        except Exception as e:
            logger.error(f"Failed to save archive index: {e}")

    async def auto_archive(self) -> int:
        """自动归档过期数据。

        Returns:
            归档的记录数
        """
        session = self._tier_manager._Session()
        try:
            from models import DataRecord

            # 获取冷数据配置
            cold_config = self._tier_manager._tier_configs.get(DataTier.COLD)
            if not cold_config:
                return 0

            threshold = datetime.now() - timedelta(hours=cold_config.max_age_hours)

            # 查询需要归档的数据
            records_to_archive = (
                session.query(DataRecord)
                .filter(DataRecord.timestamp < threshold)
                .order_by(DataRecord.experiment_id, DataRecord.timestamp)
                .limit(50000)
                .all()
            )

            if not records_to_archive:
                return 0

            # 按实验ID分组归档
            records_by_exp: dict[int, list[DataRecord]] = defaultdict(list)
            for record in records_to_archive:
                records_by_exp[record.experiment_id].append(record)

            total_archived = 0

            for exp_id, records in records_by_exp.items():
                archived = await self._archive_experiment_records(exp_id, records)
                total_archived += archived

                # 从数据库删除已归档记录
                record_ids = [r.id for r in records]
                session.query(DataRecord).filter(DataRecord.id.in_(record_ids)).delete()

            session.commit()

            return total_archived

        except Exception as e:
            session.rollback()
            logger.error(f"Auto archive failed: {e}")
            raise
        finally:
            session.close()

    async def archive_experiment(self, experiment_id: int | None = None) -> int:
        """归档指定实验的数据。

        Args:
            experiment_id: 实验ID，None表示归档所有实验

        Returns:
            归档的记录数
        """
        session = self._tier_manager._Session()
        try:
            from models import DataRecord

            if experiment_id:
                records = (
                    session.query(DataRecord)
                    .filter(DataRecord.experiment_id == experiment_id)
                    .order_by(DataRecord.timestamp)
                    .all()
                )
            else:
                # 归档所有冷数据
                cold_config = self._tier_manager._tier_configs.get(DataTier.COLD)
                if not cold_config:
                    return 0

                threshold = datetime.now() - timedelta(hours=cold_config.max_age_hours)
                records = (
                    session.query(DataRecord)
                    .filter(DataRecord.timestamp < threshold)
                    .order_by(DataRecord.experiment_id, DataRecord.timestamp)
                    .limit(100000)
                    .all()
                )

            if not records:
                return 0

            # 按实验ID分组
            records_by_exp: dict[int, list[DataRecord]] = defaultdict(list)
            for record in records:
                records_by_exp[record.experiment_id].append(record)

            total_archived = 0

            for exp_id, exp_records in records_by_exp.items():
                archived = await self._archive_experiment_records(exp_id, exp_records)
                total_archived += archived

                # 删除已归档记录
                record_ids = [r.id for r in exp_records]
                session.query(DataRecord).filter(DataRecord.id.in_(record_ids)).delete()

            session.commit()

            return total_archived

        except Exception as e:
            session.rollback()
            logger.error(f"Archive experiment failed: {e}")
            raise
        finally:
            session.close()

    async def _archive_experiment_records(self, experiment_id: int, records: list[Any]) -> int:
        """归档单个实验的记录。

        Args:
            experiment_id: 实验ID
            records: 记录列表

        Returns:
            归档的记录数
        """
        if not records:
            return 0

        # 转换为字典列表
        data_list = []
        for record in records:
            data_list.append(
                {
                    "id": record.id,
                    "timestamp": record.timestamp.isoformat() if record.timestamp else None,
                    "position_steps": record.position_steps,
                    "position_mm": record.position_mm,
                    "field_value": record.field_value,
                    "current_value": record.current_value,
                    "temperature": record.temperature,
                    "extra_data": json.loads(record.extra_data) if record.extra_data else None,
                }
            )

        # 生成归档文件名
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_filename = f"exp_{experiment_id}_{timestamp_str}.json.gz"
        archive_file = self._archive_path / archive_filename

        # 压缩并保存
        compressed_data = self._compress_data(data_list)

        try:
            with gzip.open(archive_file, "wb") as f:
                f.write(compressed_data)

            # 更新归档索引
            if experiment_id not in self._archive_index:
                self._archive_index[experiment_id] = []

            self._archive_index[experiment_id].append(
                {
                    "filename": archive_filename,
                    "record_count": len(records),
                    "start_time": (
                        records[0].timestamp.isoformat() if records[0].timestamp else None
                    ),
                    "end_time": (
                        records[-1].timestamp.isoformat() if records[-1].timestamp else None
                    ),
                    "archived_at": datetime.now().isoformat(),
                    "size_bytes": len(compressed_data),
                }
            )

            self._save_archive_index()

            logger.info(f"Archived {len(records)} records for experiment {experiment_id}")
            return len(records)

        except Exception as e:
            logger.error(f"Failed to archive records: {e}")
            # 清理失败的归档文件
            if archive_file.exists():
                archive_file.unlink()
            raise

    def _compress_data(self, data: list[dict[str, Any]]) -> bytes:
        """压缩数据。

        Args:
            data: 数据列表

        Returns:
            压缩后的字节数据
        """
        json_str = json.dumps(data, ensure_ascii=False)
        json_bytes = json_str.encode("utf-8")

        if self._compression == CompressionType.GZIP:
            return gzip.compress(json_bytes)
        elif self._compression == CompressionType.ZLIB:
            return zlib.compress(json_bytes)
        else:
            return json_bytes

    def _decompress_data(self, compressed_data: bytes) -> list[dict[str, Any]]:
        """解压数据。

        Args:
            compressed_data: 压缩的字节数据

        Returns:
            数据列表
        """
        try:
            if self._compression == CompressionType.GZIP:
                json_bytes = gzip.decompress(compressed_data)
            elif self._compression == CompressionType.ZLIB:
                json_bytes = zlib.decompress(compressed_data)
            else:
                json_bytes = compressed_data

            json_str = json_bytes.decode("utf-8")
            return json.loads(json_str)

        except Exception as e:
            logger.error(f"Failed to decompress data: {e}")
            return []

    async def load_archived_data(
        self,
        experiment_id: int,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 10000,
    ) -> list[dict[str, Any]]:
        """加载已归档的数据。

        Args:
            experiment_id: 实验ID
            start_time: 开始时间，可选
            end_time: 结束时间，可选
            limit: 最大返回记录数

        Returns:
            数据记录列表
        """
        if experiment_id not in self._archive_index:
            return []

        all_data = []

        for archive_info in self._archive_index[experiment_id]:
            archive_file = self._archive_path / archive_info["filename"]

            if not archive_file.exists():
                continue

            try:
                with gzip.open(archive_file, "rb") as f:
                    compressed_data = f.read()

                data = self._decompress_data(compressed_data)

                # 时间范围过滤
                if start_time or end_time:
                    filtered_data = []
                    for item in data:
                        item_time = datetime.fromisoformat(item["timestamp"])
                        if start_time and item_time < start_time:
                            continue
                        if end_time and item_time > end_time:
                            continue
                        filtered_data.append(item)
                    data = filtered_data

                all_data.extend(data)

                if len(all_data) >= limit:
                    break

            except Exception as e:
                logger.error(f"Failed to load archive {archive_info['filename']}: {e}")
                continue

        return all_data[:limit]

    async def delete_old_archives(self, days: int) -> int:
        """删除旧的归档文件。

        Args:
            days: 保留天数

        Returns:
            删除的记录数
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        deleted_count = 0

        for exp_id, archives in list(self._archive_index.items()):
            archives_to_keep = []

            for archive_info in archives:
                archived_time = datetime.fromisoformat(archive_info["archived_at"])

                if archived_time < cutoff_time:
                    # 删除归档文件
                    archive_file = self._archive_path / archive_info["filename"]
                    if archive_file.exists():
                        archive_file.unlink()
                        deleted_count += archive_info["record_count"]
                else:
                    archives_to_keep.append(archive_info)

            if archives_to_keep:
                self._archive_index[exp_id] = archives_to_keep
            else:
                del self._archive_index[exp_id]

        self._save_archive_index()

        return deleted_count

    def get_statistics(self) -> dict[str, Any]:
        """获取归档统计信息。

        Returns:
            统计信息字典
        """
        total_records = 0
        total_size = 0
        warm_records = 0
        cold_records = 0

        for _exp_id, archives in self._archive_index.items():
            for archive_info in archives:
                record_count = archive_info.get("record_count", 0)
                size_bytes = archive_info.get("size_bytes", 0)

                total_records += record_count
                total_size += size_bytes

                # 根据归档时间判断数据层
                archived_time = datetime.fromisoformat(archive_info["archived_at"])
                age = datetime.now() - archived_time

                if age < timedelta(days=7):
                    warm_records += record_count
                else:
                    cold_records += record_count

        return {
            "total_records": total_records,
            "total_size_mb": total_size / (1024 * 1024),
            "warm_records": warm_records,
            "cold_records": cold_records,
            "compressed_files": sum(len(archives) for archives in self._archive_index.values()),
            "experiment_count": len(self._archive_index),
        }


class QueryOptimizer:
    """
    查询优化器。

    提供查询性能优化功能，包括索引优化、
    查询缓存和批量查询。

    Attributes:
        cache_size: 查询缓存大小
    """

    def __init__(
        self,
        session_factory: Callable[[], Any],
        hot_buffer: dict[int, list[dict[str, Any]]],
        buffer_lock: Lock,
        cache_size: int = 100,
    ) -> None:
        """初始化查询优化器。

        Args:
            session_factory: 会话工厂
            hot_buffer: 热数据缓冲区引用
            buffer_lock: 缓冲区锁
            cache_size: 查询缓存大小，默认100
        """
        self._Session = session_factory
        self._hot_buffer = hot_buffer
        self._buffer_lock = buffer_lock

        # 查询缓存
        self._cache_size = cache_size
        self._query_cache: dict[str, tuple[list[dict[str, Any]], datetime]] = {}
        self._cache_lock = Lock()

        # 缓存过期时间（秒）
        self._cache_ttl = 60

    async def query_optimized(
        self,
        experiment_id: int,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 10000,
    ) -> list[dict[str, Any]]:
        """执行优化查询。

        使用缓存和索引优化查询性能。

        Args:
            experiment_id: 实验ID
            start_time: 开始时间，可选
            end_time: 结束时间，可选
            limit: 最大返回记录数

        Returns:
            数据记录列表
        """
        # 生成缓存键
        cache_key = self._generate_cache_key(experiment_id, start_time, end_time, limit)

        # 检查缓存
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result

        # 执行数据库查询
        result = await self._execute_query(experiment_id, start_time, end_time, limit)

        # 存入缓存
        self._put_to_cache(cache_key, result)

        return result

    def _generate_cache_key(
        self,
        experiment_id: int,
        start_time: datetime | None,
        end_time: datetime | None,
        limit: int,
    ) -> str:
        """生成缓存键。

        Args:
            experiment_id: 实验ID
            start_time: 开始时间
            end_time: 结束时间
            limit: 限制数量

        Returns:
            缓存键字符串
        """
        key_parts = [
            str(experiment_id),
            start_time.isoformat() if start_time else "None",
            end_time.isoformat() if end_time else "None",
            str(limit),
        ]
        return "|".join(key_parts)

    def _get_from_cache(self, cache_key: str) -> list[dict[str, Any]] | None:
        """从缓存获取数据。

        Args:
            cache_key: 缓存键

        Returns:
            缓存的数据，未命中返回None
        """
        with self._cache_lock:
            if cache_key not in self._query_cache:
                return None

            data, timestamp = self._query_cache[cache_key]

            # 检查是否过期
            if (datetime.now() - timestamp).total_seconds() > self._cache_ttl:
                del self._query_cache[cache_key]
                return None

            return data

    def _put_to_cache(self, cache_key: str, data: list[dict[str, Any]]) -> None:
        """将数据存入缓存。

        Args:
            cache_key: 缓存键
            data: 要缓存的数据
        """
        with self._cache_lock:
            # LRU缓存淘汰
            if len(self._query_cache) >= self._cache_size:
                # 删除最旧的缓存项
                oldest_key = min(
                    self._query_cache.keys(),
                    key=lambda k: self._query_cache[k][1],
                )
                del self._query_cache[oldest_key]

            self._query_cache[cache_key] = (data, datetime.now())

    async def _execute_query(
        self,
        experiment_id: int,
        start_time: datetime | None,
        end_time: datetime | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """执行数据库查询。

        Args:
            experiment_id: 实验ID
            start_time: 开始时间
            end_time: 结束时间
            limit: 限制数量

        Returns:
            查询结果列表
        """
        session = self._Session()
        try:
            from models import DataRecord

            # 构建查询
            query = session.query(DataRecord).filter(DataRecord.experiment_id == experiment_id)

            # 时间范围过滤
            if start_time:
                query = query.filter(DataRecord.timestamp >= start_time)
            if end_time:
                query = query.filter(DataRecord.timestamp <= end_time)

            # 使用索引优化排序
            query = query.order_by(DataRecord.timestamp).limit(limit)

            # 执行查询
            records = query.all()

            # 转换为字典列表
            result = []
            for record in records:
                result.append(
                    {
                        "id": record.id,
                        "experiment_id": record.experiment_id,
                        "timestamp": record.timestamp.isoformat() if record.timestamp else None,
                        "position_steps": record.position_steps,
                        "position_mm": record.position_mm,
                        "field_value": record.field_value,
                        "current_value": record.current_value,
                        "temperature": record.temperature,
                        "extra_data": json.loads(record.extra_data) if record.extra_data else None,
                    }
                )

            return result

        finally:
            session.close()

    def clear_cache(self) -> None:
        """清空查询缓存。"""
        with self._cache_lock:
            self._query_cache.clear()

    def get_cache_statistics(self) -> dict[str, Any]:
        """获取缓存统计信息。

        Returns:
            缓存统计字典
        """
        with self._cache_lock:
            return {
                "cache_size": len(self._query_cache),
                "max_cache_size": self._cache_size,
                "cache_ttl_seconds": self._cache_ttl,
            }


# ==================== 便捷函数 ====================


def create_timeseries_storage(
    db_path: str = "timeseries.db",
    hot_max_hours: int = 24,
    warm_max_hours: int = 168,
    cold_max_hours: int = 720,
) -> TimeSeriesStorage:
    """创建时序数据存储的便捷函数。

    Args:
        db_path: 数据库路径
        hot_max_hours: 热数据最大保留时间（小时）
        warm_max_hours: 温数据最大保留时间（小时）
        cold_max_hours: 冷数据最大保留时间（小时）

    Returns:
        TimeSeriesStorage实例

    Example:
        >>> storage = create_timeseries_storage("data/ts.db")
        >>> await storage.write_data(1, {"field_value": 1.5})
    """
    base_path = Path(db_path).parent

    tier_configs = {
        DataTier.HOT: TierConfig(
            tier=DataTier.HOT,
            max_age_hours=hot_max_hours,
            compression=CompressionType.NONE,
            storage_path=str(base_path / "hot_data"),
        ),
        DataTier.WARM: TierConfig(
            tier=DataTier.WARM,
            max_age_hours=warm_max_hours,
            compression=CompressionType.GZIP,
            storage_path=str(base_path / "warm_data"),
        ),
        DataTier.COLD: TierConfig(
            tier=DataTier.COLD,
            max_age_hours=cold_max_hours,
            compression=CompressionType.GZIP,
            storage_path=str(base_path / "cold_data"),
        ),
    }

    return TimeSeriesStorage(db_path=db_path, tier_configs=tier_configs)


async def migrate_to_timeseries_storage(
    old_storage: Any, new_storage: TimeSeriesStorage, batch_size: int = 10000
) -> int:
    """从旧存储迁移数据到时序存储。

    Args:
        old_storage: 旧的数据存储实例
        new_storage: 新的时序存储实例
        batch_size: 批量迁移大小

    Returns:
        迁移的记录数

    Example:
        >>> old = DataStorage("old.db")
        >>> new = create_timeseries_storage("new.db")
        >>> count = await migrate_to_timeseries_storage(old, new)
    """
    # 获取所有实验
    experiments = old_storage.list_experiments(limit=1000)
    total_migrated = 0

    for exp in experiments:
        exp_id = exp["id"]

        # 获取实验数据
        records = old_storage.get_experiment_data(exp_id, limit=100000)

        if not records:
            continue

        # 批量写入新存储
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]

            # 转换格式
            data_list = []
            for record in batch:
                data_list.append(
                    {
                        "timestamp": (
                            datetime.fromisoformat(record["timestamp"])
                            if record.get("timestamp")
                            else None
                        ),
                        "position_steps": record.get("position_steps"),
                        "position_mm": record.get("position_mm"),
                        "field_value": record.get("field_value"),
                        "current_value": record.get("current_value"),
                        "temperature": record.get("temperature"),
                        "extra_data": record.get("extra_data"),
                    }
                )

            await new_storage.write_data(exp_id, data_list)
            total_migrated += len(batch)

    return total_migrated
