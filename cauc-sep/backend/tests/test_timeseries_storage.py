"""
时序数据存储模块测试。

测试功能：
    - 时序数据写入和查询
    - 数据分层管理
    - 数据归档和压缩
    - 查询优化和缓存

作者：Backend Engineer Agent
创建日期：2026-03-08
"""

import asyncio
import gzip
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.timeseries_storage import (
    CompressionType,
    DataArchiver,
    DataTier,
    DataTierManager,
    QueryOptimizer,
    StorageStatistics,
    TierConfig,
    TimeSeriesStorage,
    create_timeseries_storage,
)


class TestDataTier:
    """数据分层枚举测试。"""

    def test_tier_values(self):
        """测试数据层枚举值。"""
        assert DataTier.HOT.value == "hot"
        assert DataTier.WARM.value == "warm"
        assert DataTier.COLD.value == "cold"

    def test_tier_order(self):
        """测试数据层顺序。"""
        tiers = [DataTier.HOT, DataTier.WARM, DataTier.COLD]
        assert tiers[0] == DataTier.HOT
        assert tiers[2] == DataTier.COLD


class TestCompressionType:
    """压缩类型枚举测试。"""

    def test_compression_values(self):
        """测试压缩类型枚举值。"""
        assert CompressionType.NONE.value == "none"
        assert CompressionType.GZIP.value == "gzip"
        assert CompressionType.ZLIB.value == "zlib"
        assert CompressionType.NPZ.value == "npz"


class TestTierConfig:
    """数据层配置测试。"""

    def test_default_config(self):
        """测试默认配置。"""
        config = TierConfig(tier=DataTier.HOT)

        assert config.tier == DataTier.HOT
        assert config.max_age_hours == 168
        assert config.compression == CompressionType.GZIP
        assert config.max_size_mb == 1024
        assert config.auto_archive is True

    def test_custom_config(self):
        """测试自定义配置。"""
        config = TierConfig(
            tier=DataTier.WARM,
            max_age_hours=72,
            compression=CompressionType.ZLIB,
            storage_path="/data/warm",
            max_size_mb=2048,
            auto_archive=False,
        )

        assert config.tier == DataTier.WARM
        assert config.max_age_hours == 72
        assert config.compression == CompressionType.ZLIB
        assert config.storage_path == "/data/warm"
        assert config.max_size_mb == 2048
        assert config.auto_archive is False


class TestStorageStatistics:
    """存储统计信息测试。"""

    def test_default_statistics(self):
        """测试默认统计信息。"""
        stats = StorageStatistics()

        assert stats.total_records == 0
        assert stats.total_bytes == 0
        assert stats.hot_records == 0
        assert stats.warm_records == 0
        assert stats.cold_records == 0
        assert stats.compressed_files == 0
        assert stats.last_archive_time is None
        assert stats.archive_count == 0

    def test_update_statistics(self):
        """测试更新统计信息。"""
        stats = StorageStatistics()
        now = datetime.now()

        stats.update(
            total_records=100,
            hot_records=50,
            warm_records=30,
            cold_records=20,
            last_archive_time=now,
            archive_count=5,
        )

        assert stats.total_records == 100
        assert stats.hot_records == 50
        assert stats.warm_records == 30
        assert stats.cold_records == 20
        assert stats.last_archive_time == now
        assert stats.archive_count == 5

    def test_thread_safe_update(self):
        """测试线程安全更新。"""
        import threading

        stats = StorageStatistics()

        def increment():
            for _ in range(100):
                stats.update(total_records=stats.total_records + 1)

        threads = [threading.Thread(target=increment) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 由于线程安全，最终值应该是1000
        assert stats.total_records == 1000


class TestTimeSeriesStorage:
    """时序数据存储测试。"""

    @pytest.fixture
    def temp_storage_env(self):
        """创建临时存储环境。"""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_timeseries.db")

        yield db_path, temp_dir

        # 清理
        import gc
        import time

        gc.collect()
        time.sleep(0.05)
        try:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass  # Windows文件锁问题，忽略

    @pytest.fixture
    def mock_models(self):
        """Mock数据模型。"""
        # 创建Mock DataRecord类
        mock_record_class = MagicMock()
        mock_record_class.__name__ = "DataRecord"

        with patch.dict("sys.modules", {"models": MagicMock(DataRecord=mock_record_class)}):
            yield mock_record_class

    def test_storage_initialization(self, temp_storage_env):
        """测试存储初始化。"""
        db_path, temp_dir = temp_storage_env

        storage = TimeSeriesStorage(db_path=db_path)

        assert storage._db_path == db_path
        assert storage._buffer_size == 10000
        assert DataTier.HOT in storage._tier_configs
        assert DataTier.WARM in storage._tier_configs
        assert DataTier.COLD in storage._tier_configs

    def test_custom_tier_configs(self, temp_storage_env):
        """测试自定义数据层配置。"""
        db_path, temp_dir = temp_storage_env

        custom_configs = {
            DataTier.HOT: TierConfig(
                tier=DataTier.HOT,
                max_age_hours=12,
                compression=CompressionType.NONE,
            ),
            DataTier.WARM: TierConfig(
                tier=DataTier.WARM,
                max_age_hours=48,
                compression=CompressionType.GZIP,
            ),
        }

        storage = TimeSeriesStorage(db_path=db_path, tier_configs=custom_configs)

        assert storage._tier_configs[DataTier.HOT].max_age_hours == 12
        assert storage._tier_configs[DataTier.WARM].max_age_hours == 48

    def test_get_default_tier_configs(self, temp_storage_env):
        """测试获取默认数据层配置。"""
        db_path, temp_dir = temp_storage_env

        storage = TimeSeriesStorage(db_path=db_path)
        configs = storage._get_default_tier_configs()

        assert DataTier.HOT in configs
        assert DataTier.WARM in configs
        assert DataTier.COLD in configs
        assert configs[DataTier.HOT].max_age_hours == 24
        assert configs[DataTier.WARM].max_age_hours == 168
        assert configs[DataTier.COLD].max_age_hours == 720

    @pytest.mark.asyncio
    async def test_write_single_data(self, temp_storage_env, mock_models):
        """测试写入单条数据。"""
        db_path, temp_dir = temp_storage_env

        storage = TimeSeriesStorage(db_path=db_path, buffer_size=5)

        data = {
            "position_steps": 100,
            "position_mm": 6.25,
            "field_value": 50.0,
            "current_value": 0.5,
        }

        count = await storage.write_data(1, data)

        assert count == 1
        assert len(storage._hot_buffer[1]) == 1

    @pytest.mark.asyncio
    async def test_write_batch_data(self, temp_storage_env, mock_models):
        """测试批量写入数据。"""
        db_path, temp_dir = temp_storage_env

        storage = TimeSeriesStorage(db_path=db_path, buffer_size=100)

        data_list = [{"position_steps": i * 100, "field_value": i * 10.0} for i in range(10)]

        count = await storage.write_data(1, data_list)

        assert count == 10
        assert len(storage._hot_buffer[1]) == 10

    @pytest.mark.asyncio
    async def test_write_empty_data(self, temp_storage_env):
        """测试写入空数据。"""
        db_path, temp_dir = temp_storage_env

        storage = TimeSeriesStorage(db_path=db_path)

        count = await storage.write_data(1, {})
        assert count == 0

        count = await storage.write_data(1, [])
        assert count == 0

        count = await storage.write_data(1, None)
        assert count == 0

    @pytest.mark.asyncio
    async def test_write_with_timestamp(self, temp_storage_env, mock_models):
        """测试带时间戳写入。"""
        db_path, temp_dir = temp_storage_env

        storage = TimeSeriesStorage(db_path=db_path)

        custom_time = datetime(2026, 1, 1, 12, 0, 0)
        data = {"field_value": 100.0}

        await storage.write_data(1, data, timestamp=custom_time)

        assert storage._hot_buffer[1][0]["timestamp"] == custom_time

    @pytest.mark.asyncio
    async def test_buffer_flush_on_threshold(self, temp_storage_env, mock_models):
        """测试缓冲区阈值刷新。"""
        db_path, temp_dir = temp_storage_env

        # 设置小缓冲区大小以触发刷新
        storage = TimeSeriesStorage(db_path=db_path, buffer_size=3)

        # Mock flush方法
        flush_called = []

        original_flush = storage._flush_buffer

        async def mock_flush():
            flush_called.append(True)
            return await original_flush()

        storage._flush_buffer = mock_flush

        # 写入数据触发刷新
        for i in range(5):
            await storage.write_data(1, {"field_value": i})

        # 缓冲区大小为3，写入5条数据应该触发刷新
        assert len(flush_called) >= 1

    def test_get_tier_config(self, temp_storage_env):
        """测试获取数据层配置。"""
        db_path, temp_dir = temp_storage_env

        storage = TimeSeriesStorage(db_path=db_path)

        hot_config = storage.get_tier_config(DataTier.HOT)
        assert hot_config.tier == DataTier.HOT

        # 测试不存在的层返回默认配置
        unknown_config = storage.get_tier_config(DataTier.COLD)
        assert unknown_config.tier == DataTier.COLD

    def test_update_tier_config(self, temp_storage_env):
        """测试更新数据层配置。"""
        db_path, temp_dir = temp_storage_env

        storage = TimeSeriesStorage(db_path=db_path)

        new_config = TierConfig(
            tier=DataTier.HOT,
            max_age_hours=48,
            compression=CompressionType.ZLIB,
        )

        storage.update_tier_config(new_config)

        updated_config = storage.get_tier_config(DataTier.HOT)
        assert updated_config.max_age_hours == 48
        assert updated_config.compression == CompressionType.ZLIB

    @pytest.mark.asyncio
    async def test_start_stop_background_tasks(self, temp_storage_env):
        """测试启动和停止后台任务。"""
        db_path, temp_dir = temp_storage_env

        storage = TimeSeriesStorage(db_path=db_path)

        await storage.start_background_tasks()
        assert storage._is_running is True
        assert storage._archive_task is not None

        await storage.stop_background_tasks()
        assert storage._is_running is False


class TestDataTierManager:
    """数据分层管理器测试。"""

    @pytest.fixture
    def tier_manager_env(self):
        """创建分层管理器环境。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker

            db_path = os.path.join(temp_dir, "test.db")
            engine = create_engine(f"sqlite:///{db_path}")
            Session = sessionmaker(bind=engine)

            tier_configs = {
                DataTier.HOT: TierConfig(
                    tier=DataTier.HOT,
                    max_age_hours=24,
                    storage_path=os.path.join(temp_dir, "hot"),
                ),
                DataTier.WARM: TierConfig(
                    tier=DataTier.WARM,
                    max_age_hours=168,
                    storage_path=os.path.join(temp_dir, "warm"),
                ),
                DataTier.COLD: TierConfig(
                    tier=DataTier.COLD,
                    max_age_hours=720,
                    storage_path=os.path.join(temp_dir, "cold"),
                ),
            }

            manager = DataTierManager(
                engine=engine,
                session_factory=Session,
                tier_configs=tier_configs,
            )

            yield manager, temp_dir

    def test_initialization(self, tier_manager_env):
        """测试初始化。"""
        manager, temp_dir = tier_manager_env

        assert manager._tier_configs is not None
        assert DataTier.HOT in manager._tier_configs

    def test_update_config(self, tier_manager_env):
        """测试更新配置。"""
        manager, temp_dir = tier_manager_env

        new_config = TierConfig(
            tier=DataTier.HOT,
            max_age_hours=12,
            storage_path=os.path.join(temp_dir, "new_hot"),
        )

        manager.update_config(new_config)

        assert manager._tier_configs[DataTier.HOT].max_age_hours == 12

    def test_get_data_tier(self, tier_manager_env):
        """测试根据时间戳判断数据层。"""
        manager, temp_dir = tier_manager_env

        now = datetime.now()

        # 热数据（最近1小时）
        hot_time = now - timedelta(hours=1)
        assert manager.get_data_tier(hot_time) == DataTier.HOT

        # 温数据（2天前）
        warm_time = now - timedelta(days=2)
        assert manager.get_data_tier(warm_time) == DataTier.WARM

        # 冷数据（30天前）
        cold_time = now - timedelta(days=30)
        assert manager.get_data_tier(cold_time) == DataTier.COLD

    @pytest.mark.asyncio
    async def test_migrate_data_tiers(self, tier_manager_env):
        """测试数据分层迁移。"""
        manager, temp_dir = tier_manager_env

        # Mock数据库查询
        with patch.object(manager, "_Session") as mock_session:
            mock_session_instance = MagicMock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.query.return_value.filter.return_value.limit.return_value.all.return_value = (
                []
            )

            result = await manager.migrate_data_tiers()

            assert "hot_to_warm" in result
            assert "warm_to_cold" in result


class TestDataArchiver:
    """数据归档器测试。"""

    @pytest.fixture
    def archiver_env(self):
        """创建归档器环境。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker

            db_path = os.path.join(temp_dir, "test.db")
            engine = create_engine(f"sqlite:///{db_path}")
            Session = sessionmaker(bind=engine)

            tier_configs = {
                DataTier.COLD: TierConfig(
                    tier=DataTier.COLD,
                    max_age_hours=720,
                ),
            }

            tier_manager = DataTierManager(
                engine=engine,
                session_factory=Session,
                tier_configs=tier_configs,
            )

            archiver = DataArchiver(
                tier_manager=tier_manager,
                storage_path=Path(temp_dir),
            )

            yield archiver, temp_dir

    def test_initialization(self, archiver_env):
        """测试初始化。"""
        archiver, temp_dir = archiver_env

        assert archiver._storage_path == Path(temp_dir)
        assert archiver._archive_path.exists()

    def test_compress_data_gzip(self, archiver_env):
        """测试GZIP压缩。"""
        archiver, temp_dir = archiver_env
        archiver._compression = CompressionType.GZIP

        data = [{"id": 1, "value": "test"}]
        compressed = archiver._compress_data(data)

        assert isinstance(compressed, bytes)
        assert len(compressed) > 0

        # 验证可以解压
        decompressed = gzip.decompress(compressed)
        assert json.loads(decompressed.decode("utf-8")) == data

    def test_compress_data_zlib(self, archiver_env):
        """测试ZLIB压缩。"""
        import zlib

        archiver, temp_dir = archiver_env
        archiver._compression = CompressionType.ZLIB

        data = [{"id": 1, "value": "test"}]
        compressed = archiver._compress_data(data)

        assert isinstance(compressed, bytes)

        # 验证可以解压
        decompressed = zlib.decompress(compressed)
        assert json.loads(decompressed.decode("utf-8")) == data

    def test_compress_data_none(self, archiver_env):
        """测试无压缩。"""
        archiver, temp_dir = archiver_env
        archiver._compression = CompressionType.NONE

        data = [{"id": 1, "value": "test"}]
        compressed = archiver._compress_data(data)

        assert isinstance(compressed, bytes)
        assert json.loads(compressed.decode("utf-8")) == data

    def test_decompress_data(self, archiver_env):
        """测试数据解压。"""
        archiver, temp_dir = archiver_env
        archiver._compression = CompressionType.GZIP

        original_data = [{"id": 1, "value": "test"}, {"id": 2, "value": "test2"}]
        compressed = archiver._compress_data(original_data)
        decompressed = archiver._decompress_data(compressed)

        assert decompressed == original_data

    def test_archive_index_operations(self, archiver_env):
        """测试归档索引操作。"""
        archiver, temp_dir = archiver_env

        # 添加索引
        archiver._archive_index[1] = [
            {
                "filename": "exp_1_20260101.json.gz",
                "record_count": 100,
                "archived_at": datetime.now().isoformat(),
            }
        ]

        archiver._save_archive_index()

        # 重新加载
        archiver._archive_index = {}
        archiver._load_archive_index()

        assert 1 in archiver._archive_index
        assert archiver._archive_index[1][0]["record_count"] == 100

    @pytest.mark.asyncio
    async def test_load_archived_data(self, archiver_env):
        """测试加载归档数据。"""
        archiver, temp_dir = archiver_env

        # 创建测试归档文件
        test_data = [
            {
                "id": 1,
                "timestamp": datetime.now().isoformat(),
                "field_value": 100.0,
            },
            {
                "id": 2,
                "timestamp": datetime.now().isoformat(),
                "field_value": 200.0,
            },
        ]

        archive_file = archiver._archive_path / "exp_1_20260101.json.gz"
        with gzip.open(archive_file, "wb") as f:
            f.write(archiver._compress_data(test_data))

        # 更新索引
        archiver._archive_index[1] = [
            {
                "filename": "exp_1_20260101.json.gz",
                "record_count": 2,
                "archived_at": datetime.now().isoformat(),
            }
        ]

        # 加载数据
        loaded_data = await archiver.load_archived_data(1)

        assert len(loaded_data) == 2
        assert loaded_data[0]["field_value"] == 100.0

    @pytest.mark.asyncio
    async def test_load_archived_data_with_time_filter(self, archiver_env):
        """测试带时间过滤加载归档数据。"""
        archiver, temp_dir = archiver_env

        now = datetime.now()
        test_data = [
            {
                "id": 1,
                "timestamp": (now - timedelta(hours=2)).isoformat(),
                "field_value": 100.0,
            },
            {
                "id": 2,
                "timestamp": (now - timedelta(hours=1)).isoformat(),
                "field_value": 200.0,
            },
        ]

        archive_file = archiver._archive_path / "exp_1_20260102.json.gz"
        with gzip.open(archive_file, "wb") as f:
            f.write(archiver._compress_data(test_data))

        archiver._archive_index[1] = [
            {
                "filename": "exp_1_20260102.json.gz",
                "record_count": 2,
                "archived_at": datetime.now().isoformat(),
            }
        ]

        # 过滤最近1.5小时的数据
        start_time = now - timedelta(hours=1.5)
        loaded_data = await archiver.load_archived_data(1, start_time=start_time)

        assert len(loaded_data) == 1
        assert loaded_data[0]["field_value"] == 200.0

    @pytest.mark.asyncio
    async def test_delete_old_archives(self, archiver_env):
        """测试删除旧归档。"""
        archiver, temp_dir = archiver_env

        # 创建旧归档
        old_time = datetime.now() - timedelta(days=100)
        old_archive_file = archiver._archive_path / "exp_1_old.json.gz"
        with gzip.open(old_archive_file, "wb") as f:
            f.write(archiver._compress_data([{"id": 1}]))

        archiver._archive_index[1] = [
            {
                "filename": "exp_1_old.json.gz",
                "record_count": 1,
                "archived_at": old_time.isoformat(),
            }
        ]

        # 删除90天前的归档
        deleted = await archiver.delete_old_archives(90)

        assert deleted == 1
        assert not old_archive_file.exists()
        assert 1 not in archiver._archive_index

    def test_get_statistics(self, archiver_env):
        """测试获取统计信息。"""
        archiver, temp_dir = archiver_env

        archiver._archive_index = {
            1: [
                {
                    "record_count": 100,
                    "size_bytes": 1024,
                    "archived_at": datetime.now().isoformat(),
                }
            ],
            2: [
                {
                    "record_count": 200,
                    "size_bytes": 2048,
                    "archived_at": (datetime.now() - timedelta(days=10)).isoformat(),
                }
            ],
        }

        stats = archiver.get_statistics()

        assert stats["total_records"] == 300
        assert stats["total_size_mb"] > 0
        assert stats["experiment_count"] == 2


class TestQueryOptimizer:
    """查询优化器测试。"""

    @pytest.fixture
    def optimizer_env(self):
        """创建优化器环境。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            from collections import defaultdict
            from threading import Lock

            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker

            db_path = os.path.join(temp_dir, "test.db")
            engine = create_engine(f"sqlite:///{db_path}")
            Session = sessionmaker(bind=engine)

            hot_buffer = defaultdict(list)
            buffer_lock = Lock()

            optimizer = QueryOptimizer(
                session_factory=Session,
                hot_buffer=hot_buffer,
                buffer_lock=buffer_lock,
                cache_size=10,
            )

            yield optimizer, temp_dir

    def test_initialization(self, optimizer_env):
        """测试初始化。"""
        optimizer, temp_dir = optimizer_env

        assert optimizer._cache_size == 10
        assert optimizer._cache_ttl == 60

    def test_generate_cache_key(self, optimizer_env):
        """测试生成缓存键。"""
        optimizer, temp_dir = optimizer_env

        key1 = optimizer._generate_cache_key(1, None, None, 100)
        key2 = optimizer._generate_cache_key(1, None, None, 100)
        key3 = optimizer._generate_cache_key(2, None, None, 100)

        assert key1 == key2
        assert key1 != key3

    def test_cache_put_and_get(self, optimizer_env):
        """测试缓存存取。"""
        optimizer, temp_dir = optimizer_env

        cache_key = "test_key"
        data = [{"id": 1, "value": "test"}]

        optimizer._put_to_cache(cache_key, data)

        cached = optimizer._get_from_cache(cache_key)
        assert cached == data

    def test_cache_expiration(self, optimizer_env):
        """测试缓存过期。"""
        optimizer, temp_dir = optimizer_env
        optimizer._cache_ttl = 0.1  # 100ms

        cache_key = "test_key"
        data = [{"id": 1}]

        optimizer._put_to_cache(cache_key, data)

        # 立即获取应该命中
        cached = optimizer._get_from_cache(cache_key)
        assert cached == data

        # 等待过期
        import time

        time.sleep(0.2)

        # 过期后应该返回None
        cached = optimizer._get_from_cache(cache_key)
        assert cached is None

    def test_cache_lru_eviction(self, optimizer_env):
        """测试LRU缓存淘汰。"""
        optimizer, temp_dir = optimizer_env
        optimizer._cache_size = 3

        # 添加4个缓存项
        for i in range(4):
            optimizer._put_to_cache(f"key_{i}", [{"id": i}])

        # 缓存大小应该为3
        assert len(optimizer._query_cache) == 3

        # 最旧的key_0应该被淘汰
        assert optimizer._get_from_cache("key_0") is None
        assert optimizer._get_from_cache("key_1") is not None
        assert optimizer._get_from_cache("key_2") is not None
        assert optimizer._get_from_cache("key_3") is not None

    def test_clear_cache(self, optimizer_env):
        """测试清空缓存。"""
        optimizer, temp_dir = optimizer_env

        optimizer._put_to_cache("key_1", [{"id": 1}])
        optimizer._put_to_cache("key_2", [{"id": 2}])

        optimizer.clear_cache()

        assert len(optimizer._query_cache) == 0

    def test_get_cache_statistics(self, optimizer_env):
        """测试获取缓存统计。"""
        optimizer, temp_dir = optimizer_env

        optimizer._put_to_cache("key_1", [{"id": 1}])
        optimizer._put_to_cache("key_2", [{"id": 2}])

        stats = optimizer.get_cache_statistics()

        assert stats["cache_size"] == 2
        assert stats["max_cache_size"] == 10
        assert stats["cache_ttl_seconds"] == 60


class TestCreateTimeseriesStorage:
    """便捷函数测试。"""

    def test_create_with_defaults(self):
        """测试使用默认参数创建。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")

            storage = create_timeseries_storage(db_path)

            assert storage._db_path == db_path
            assert storage._tier_configs[DataTier.HOT].max_age_hours == 24
            assert storage._tier_configs[DataTier.WARM].max_age_hours == 168
            assert storage._tier_configs[DataTier.COLD].max_age_hours == 720

    def test_create_with_custom_hours(self):
        """测试使用自定义时间创建。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")

            storage = create_timeseries_storage(
                db_path=db_path,
                hot_max_hours=12,
                warm_max_hours=48,
                cold_max_hours=360,
            )

            assert storage._tier_configs[DataTier.HOT].max_age_hours == 12
            assert storage._tier_configs[DataTier.WARM].max_age_hours == 48
            assert storage._tier_configs[DataTier.COLD].max_age_hours == 360


class TestIntegration:
    """集成测试。"""

    @pytest.fixture
    def full_storage_env(self):
        """创建完整存储环境。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "integration.db")

            storage = TimeSeriesStorage(
                db_path=db_path,
                buffer_size=100,
            )

            yield storage, temp_dir

    @pytest.mark.asyncio
    async def test_write_and_query_workflow(self, full_storage_env):
        """测试写入和查询工作流。"""
        storage, temp_dir = full_storage_env

        # 写入数据到缓冲区
        for i in range(10):
            await storage.write_data(
                1,
                {
                    "position_steps": i * 100,
                    "field_value": i * 10.0,
                },
            )

        # 验证缓冲区
        assert len(storage._hot_buffer[1]) == 10

    @pytest.mark.asyncio
    async def test_tier_config_update_workflow(self, full_storage_env):
        """测试配置更新工作流。"""
        storage, temp_dir = full_storage_env

        # 更新热数据配置
        new_hot_config = TierConfig(
            tier=DataTier.HOT,
            max_age_hours=12,
            compression=CompressionType.NONE,
        )
        storage.update_tier_config(new_hot_config)

        # 验证配置已更新
        config = storage.get_tier_config(DataTier.HOT)
        assert config.max_age_hours == 12


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
