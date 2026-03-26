"""
数据存储子模块

文件名: __init__.py
路径: backend/core/storage/
功能: 提供数据持久化存储解决方案，支持关系型数据库和时序数据存储
作者: Backend Engineer Agent
创建日期: 2024-01-15
更新日期: 2026-03-14
版本: 1.0.0

核心功能：
    - 数据库连接和会话管理（SQLAlchemy）
    - 实验数据存储（结构化数据）
    - 时序数据存储（高频采集数据）
    - 数据管道处理（ETL流程）
    - 索引优化（查询性能优化）

导出组件：
    - DataStorage: 数据存储主类
    - DatabaseManager: 数据库管理器
    - get_db_session: 获取数据库会话
    - TimeSeriesStorage: 时序数据存储
    - DataPipeline: 数据管道处理器
    - IndexOptimizer: 索引优化器

依赖：
    - sqlalchemy: ORM框架
    - asyncpg: PostgreSQL异步驱动
    - aiomysql: MySQL异步驱动（可选）
    - typing: 类型注解支持

使用示例：
    >>> from backend.core.storage import DataStorage, get_db_session
    >>> 
    >>> # 获取数据库会话
    >>> async with get_db_session() as session:
    ...     # 执行数据库操作
    ...     result = await session.execute("SELECT * FROM experiments")
    >>> 
    >>> # 使用数据存储
    >>> storage = DataStorage()
    >>> await storage.save_experiment_data(exp_id, data)
"""

from .data_storage import DataStorage
from .database import (
    DatabaseConnectionPool,
    DatabasePoolManager,
    get_pool_manager,
    get_default_pool,
    init_database_pool,
    create_pool,
)
from .timeseries_storage import TimeSeriesStorage
from .data_pipeline import DataPipeline
from .index_optimizer import IndexOptimizer
from .database_optimizer import (
    DatabaseOptimizer,
    SQLiteOptimizedConnection,
    DatabaseCacheManager,
    BatchWriteManager,
    HDF5StorageManager,
    SQLiteOptimizationConfig,
    CacheConfig,
    BatchWriteConfig,
    HDF5Config,
    create_optimized_database,
    optimize_sqlite_database,
)

__all__ = [
    "BatchWriteConfig",
    "BatchWriteManager",
    "CacheConfig",
    "DataPipeline",
    "DataStorage",
    "DatabaseCacheManager",
    "DatabaseConnectionPool",
    "DatabaseOptimizer",
    "DatabasePoolManager",
    "HDF5Config",
    "HDF5StorageManager",
    "IndexOptimizer",
    "SQLiteOptimizationConfig",
    "SQLiteOptimizedConnection",
    "TimeSeriesStorage",
    "create_optimized_database",
    "create_pool",
    "get_default_pool",
    "get_pool_manager",
    "init_database_pool",
    "optimize_sqlite_database",
]
