"""
数据库优化使用示例

文件名: database_optimizer_example.py
路径: backend/core/storage/
功能: 展示数据库优化组件的使用方法
作者: Backend Engineer Agent
创建日期: 2026-03-25

本文件提供数据库优化组件的使用示例，包括：
    - SQLite优化配置
    - 缓存机制使用
    - 批量写入操作
    - HDF5数据存储
    - 综合优化器使用
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from backend.core.storage.database_optimizer import (
    BatchWriteConfig,
    BatchWriteManager,
    CacheConfig,
    DatabaseCacheManager,
    DatabaseOptimizer,
    HDF5Config,
    HDF5StorageManager,
    SQLiteOptimizationConfig,
    SQLiteOptimizedConnection,
    create_optimized_database,
    optimize_sqlite_database,
)


def example_sqlite_optimization() -> None:
    """
    SQLite优化配置示例。

    展示如何配置和使用SQLite优化连接。
    """
    print("\n" + "=" * 60)
    print("示例1: SQLite优化配置")
    print("=" * 60)

    # 1. 创建优化配置
    config = SQLiteOptimizationConfig(
        journal_mode="WAL",  # WAL模式提升并发性能
        synchronous="NORMAL",  # 平衡性能与安全
        cache_size_mb=128,  # 128MB缓存
        temp_store="MEMORY",  # 临时存储在内存
        busy_timeout_ms=30000,  # 30秒忙等待超时
        foreign_keys=True,  # 启用外键约束
        mmap_size_mb=256,  # 256MB内存映射
    )

    # 2. 创建优化连接
    conn = SQLiteOptimizedConnection("data/experiments.db", config)

    # 3. 获取数据库信息
    db_info = conn.get_database_info()
    print(f"数据库信息: {db_info}")

    # 4. 使用会话
    with conn.get_session() as session:
        # 执行查询操作
        # result = session.execute(text("SELECT COUNT(*) FROM experiments"))
        # count = result.scalar()
        print("会话已创建，可执行数据库操作")

    # 5. 执行优化操作
    # result = conn.optimize_database()
    # print(f"优化结果: {result}")

    # 6. 关闭连接
    conn.close()
    print("SQLite优化配置示例完成")


def example_cache_mechanism() -> None:
    """
    缓存机制使用示例。

    展示如何使用缓存管理器减少数据库访问压力。
    """
    print("\n" + "=" * 60)
    print("示例2: 缓存机制使用")
    print("=" * 60)

    # 1. 创建缓存配置
    config = CacheConfig(
        max_size=10000,  # 最大缓存10000条
        default_ttl=300.0,  # 默认过期时间5分钟
        cleanup_interval=60.0,  # 每分钟清理一次过期缓存
        enable_statistics=True,  # 启用统计
    )

    # 2. 创建缓存管理器
    cache = DatabaseCacheManager(config)

    # 3. 缓存设备状态
    device_status = {
        "device_id": "motor_001",
        "status": "running",
        "position": 10000,
        "speed": 500,
        "temperature": 35.5,
        "timestamp": datetime.now().isoformat(),
    }
    cache.set_device_status("motor_001", device_status, ttl=10.0)
    print(f"已缓存设备状态: motor_001")

    # 4. 获取设备状态缓存
    cached_status = cache.get_device_status("motor_001")
    print(f"从缓存获取设备状态: {cached_status}")

    # 5. 缓存实验数据
    experiment_data = {
        "experiment_id": 1,
        "data_type": "latest",
        "records": [
            {"timestamp": datetime.now().isoformat(), "value": 123.45},
            {"timestamp": datetime.now().isoformat(), "value": 124.56},
        ],
    }
    cache.set_experiment_data(1, experiment_data, "latest", ttl=60.0)
    print(f"已缓存实验数据: experiment_id=1")

    # 6. 获取实验数据缓存
    cached_data = cache.get_experiment_data(1, "latest")
    print(f"从缓存获取实验数据: {cached_data}")

    # 7. 获取缓存统计信息
    stats = cache.get_statistics()
    print(f"缓存统计信息: {stats}")

    # 8. 清空缓存
    cache.clear_all()
    print("缓存已清空")


def example_batch_write() -> None:
    """
    批量写入使用示例。

    展示如何使用批量写入管理器优化数据库写入性能。
    """
    print("\n" + "=" * 60)
    print("示例3: 批量写入使用")
    print("=" * 60)

    # 1. 创建批量写入配置
    config = BatchWriteConfig(
        batch_size=1000,  # 每1000条刷新一次
        flush_interval=5.0,  # 每5秒刷新一次
        max_retries=3,  # 最大重试3次
        retry_delay=0.1,  # 重试延迟0.1秒
    )

    # 2. 创建SQLite连接
    conn = SQLiteOptimizedConnection("data/experiments.db")

    # 3. 创建批量写入管理器
    batch_writer = BatchWriteManager(conn.get_session, config)

    # 4. 模拟添加数据到缓冲区
    # 实际使用时，model_instance应该是SQLAlchemy模型实例
    class MockModel:
        """模拟模型类"""

        def __init__(self, data: dict):
            self.data = data

    # 添加单条数据
    for i in range(10):
        model = MockModel({"id": i, "value": f"test_{i}"})
        buffer_size = batch_writer.add("mock_table", model)
        print(f"添加数据 {i}, 当前缓冲区大小: {buffer_size}")

    # 5. 批量添加数据
    models = [MockModel({"id": i, "value": f"batch_{i}"}) for i in range(100)]
    buffer_size = batch_writer.add_batch("mock_table", models)
    print(f"批量添加100条数据, 当前缓冲区大小: {buffer_size}")

    # 6. 手动刷新缓冲区
    # success = batch_writer.flush()
    # print(f"手动刷新结果: {success}")

    # 7. 获取统计信息
    stats = batch_writer.get_statistics()
    print(f"批量写入统计信息: {stats}")

    # 8. 关闭连接
    conn.close()
    print("批量写入示例完成")


def example_hdf5_storage() -> None:
    """
    HDF5数据存储使用示例。

    展示如何使用HDF5存储管理器存储大规模采集数据。
    """
    print("\n" + "=" * 60)
    print("示例4: HDF5数据存储使用")
    print("=" * 60)

    # 1. 创建HDF5配置
    config = HDF5Config(
        chunk_size=10000,  # 分块大小
        compression_level=6,  # 压缩级别
        compression_algorithm="gzip",  # 压缩算法
        enable_checksum=True,  # 启用校验和
        max_file_size_mb=1024,  # 单文件最大1GB
    )

    # 2. 创建HDF5存储管理器
    storage = HDF5StorageManager("data/hdf5", config)

    # 3. 写入单条数据
    data_record = {
        "timestamp": datetime.now(),
        "position_steps": 10000,
        "position_mm": 50.5,
        "field_value": 123.45,
        "current_value": 1.23,
        "temperature": 25.5,
    }
    count = storage.write_data(1, data_record)
    print(f"写入单条数据, 记录数: {count}")

    # 4. 批量写入数据
    data_records = []
    for i in range(100):
        record = {
            "timestamp": datetime.now() + timedelta(seconds=i),
            "position_steps": 10000 + i * 10,
            "position_mm": 50.5 + i * 0.05,
            "field_value": 123.45 + i * 0.1,
            "current_value": 1.23 + i * 0.01,
            "temperature": 25.5 + i * 0.1,
        }
        data_records.append(record)

    count = storage.write_data(1, data_records)
    print(f"批量写入数据, 记录数: {count}")

    # 5. 刷新缓冲区
    storage.flush_all()
    print("缓冲区已刷新")

    # 6. 读取数据
    start_time = datetime.now() - timedelta(hours=1)
    end_time = datetime.now()
    records = storage.read_data(1, start_time, end_time, limit=10)
    print(f"读取数据记录数: {len(records)}")

    # 7. 获取统计信息
    stats = storage.get_statistics()
    print(f"HDF5存储统计信息: {stats}")

    print("HDF5数据存储示例完成")


async def example_database_optimizer() -> None:
    """
    综合数据库优化器使用示例。

    展示如何使用综合优化器统一管理所有优化组件。
    """
    print("\n" + "=" * 60)
    print("示例5: 综合数据库优化器使用")
    print("=" * 60)

    # 1. 使用便捷函数创建优化数据库
    optimizer = create_optimized_database(
        db_path="data/experiments.db",
        storage_path="data/hdf5",
        enable_cache=True,
        enable_batch_write=True,
        enable_hdf5=True,
    )

    # 2. 启动后台任务
    await optimizer.start_background_tasks()
    print("后台任务已启动")

    # 3. 使用数据库会话
    with optimizer.get_session() as session:
        # 执行数据库操作
        # result = session.execute(text("SELECT COUNT(*) FROM experiments"))
        # count = result.scalar()
        print("会话已创建，可执行数据库操作")

    # 4. 使用缓存
    cache = optimizer.get_cache()
    cache.set_device_status("motor_001", {"status": "running"}, ttl=10.0)
    cached_status = cache.get_device_status("motor_001")
    print(f"缓存设备状态: {cached_status}")

    # 5. 使用批量写入
    batch_writer = optimizer.get_batch_writer()
    # batch_writer.add("table_name", model_instance)
    print("批量写入管理器已获取")

    # 6. 使用HDF5存储
    hdf5_storage = optimizer.get_hdf5_storage()
    hdf5_storage.write_data(1, {"timestamp": datetime.now(), "value": 123.45})
    print("HDF5存储管理器已获取")

    # 7. 获取所有统计信息
    all_stats = optimizer.get_all_statistics()
    print(f"所有统计信息: {all_stats}")

    # 8. 执行优化操作
    # result = optimizer.optimize()
    # print(f"优化结果: {result}")

    # 9. 停止后台任务
    await optimizer.stop_background_tasks()
    print("后台任务已停止")

    # 10. 关闭优化器
    optimizer.close()
    print("优化器已关闭")


async def example_async_operations() -> None:
    """
    异步操作示例。

    展示如何在异步环境中使用数据库优化组件。
    """
    print("\n" + "=" * 60)
    print("示例6: 异步操作")
    print("=" * 60)

    # 创建优化器
    optimizer = create_optimized_database(
        db_path="data/experiments.db",
        storage_path="data/hdf5",
    )

    # 启动后台任务
    await optimizer.start_background_tasks()

    # 模拟异步写入操作
    batch_writer = optimizer.get_batch_writer()

    class AsyncModel:
        """异步模型类"""

        def __init__(self, data: dict):
            self.data = data

    # 添加数据
    for i in range(50):
        model = AsyncModel({"id": i, "value": f"async_{i}"})
        batch_writer.add("async_table", model)

    # 异步刷新
    await batch_writer.async_flush()
    print("异步刷新完成")

    # 停止后台任务
    await optimizer.stop_background_tasks()
    optimizer.close()
    print("异步操作示例完成")


def example_optimize_existing_database() -> None:
    """
    优化现有数据库示例。

    展示如何对现有数据库执行优化操作。
    """
    print("\n" + "=" * 60)
    print("示例7: 优化现有数据库")
    print("=" * 60)

    # 使用便捷函数优化数据库
    result = optimize_sqlite_database("data/experiments.db")
    print(f"优化结果: {result}")


def main() -> None:
    """主函数，运行所有示例。"""
    print("\n" + "=" * 60)
    print("数据库优化组件使用示例")
    print("=" * 60)

    # 确保数据目录存在
    Path("data/hdf5").mkdir(parents=True, exist_ok=True)

    # 运行同步示例
    example_sqlite_optimization()
    example_cache_mechanism()
    example_batch_write()
    example_hdf5_storage()
    example_optimize_existing_database()

    # 运行异步示例
    asyncio.run(example_database_optimizer())
    asyncio.run(example_async_operations())

    print("\n" + "=" * 60)
    print("所有示例运行完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
