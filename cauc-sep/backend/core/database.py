"""
数据库连接池管理模块

文件名: database.py
路径: core/
功能: 数据库连接池管理、健康检查、多数据库支持（SQLite/PostgreSQL）
作者: Backend Engineer Agent
创建日期: 2026-03-08
依赖: sqlalchemy, asyncio
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from threading import Lock, RLock
from typing import Any, Callable, Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool, StaticPool

logger = logging.getLogger(__name__)


class DatabaseType(Enum):
    """数据库类型枚举。"""

    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"


@dataclass
class PoolConfig:
    """连接池配置。

    Attributes:
        pool_size: 连接池大小（默认5）
        max_overflow: 最大溢出连接数（默认10）
        pool_timeout: 获取连接超时时间（秒，默认30）
        pool_recycle: 连接回收时间（秒，默认3600）
        pool_pre_ping: 是否启用连接健康检查（默认True）
        echo_pool: 是否打印连接池日志（默认False）
    """

    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: float = 30.0
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    echo_pool: bool = False


@dataclass
class PoolStatistics:
    """连接池统计信息。

    Attributes:
        pool_size: 当前连接池大小
        checked_out: 已借出连接数
        overflow: 溢出连接数
        checked_in: 已归还连接数
        total_connections: 总连接数
        available_connections: 可用连接数
        wait_count: 等待获取连接的次数
        wait_time_ms: 总等待时间（毫秒）
    """

    pool_size: int = 0
    checked_out: int = 0
    overflow: int = 0
    checked_in: int = 0
    total_connections: int = 0
    available_connections: int = 0
    wait_count: int = 0
    wait_time_ms: float = 0.0
    last_check_time: datetime = field(default_factory=datetime.now)


class DatabaseConnectionPool:
    """
    数据库连接池管理器。

    提供统一的数据库连接池管理，支持SQLite和PostgreSQL。
    实现连接健康检查、自动重连和统计监控。

    Attributes:
        db_path: 数据库路径或连接字符串
        db_type: 数据库类型
        pool_config: 连接池配置
    """

    def __init__(
        self,
        db_path: str = "experiments.db",
        db_type: DatabaseType = DatabaseType.SQLITE,
        pool_config: PoolConfig | None = None,
        echo: bool = False,
    ) -> None:
        """初始化数据库连接池。

        Args:
            db_path: 数据库路径或连接字符串
            db_type: 数据库类型
            pool_config: 连接池配置
            echo: 是否打印SQL语句
        """
        self._db_path = db_path
        self._db_type = db_type
        self._pool_config = pool_config or PoolConfig()
        self._echo = echo

        # 创建引擎和会话工厂
        self._engine: Engine | None = None
        self._session_factory: sessionmaker | None = None

        # 统计信息
        self._statistics = PoolStatistics()
        self._lock = RLock()

        # 健康检查任务
        self._health_check_task: asyncio.Task[None] | None = None
        self._is_running = False

        # 初始化连接池
        self._initialize_pool()

        logger.info(
            f"DatabaseConnectionPool initialized: {db_type.value} - {db_path}"
        )

    def _initialize_pool(self) -> None:
        """初始化数据库连接池。"""
        if self._db_type == DatabaseType.SQLITE:
            self._engine = self._create_sqlite_engine()
        elif self._db_type == DatabaseType.POSTGRESQL:
            self._engine = self._create_postgresql_engine()
        else:
            raise ValueError(f"Unsupported database type: {self._db_type}")

        # 创建会话工厂
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

        # 设置连接池事件监听
        self._setup_pool_events()

    def _create_sqlite_engine(self) -> Engine:
        """创建SQLite数据库引擎。

        Returns:
            SQLAlchemy引擎实例
        """
        # SQLite连接参数
        connect_args = {
            "check_same_thread": False,
            "timeout": 30,
            "isolation_level": None,  # 自动提交模式
        }

        # 对于SQLite，使用StaticPool或QueuePool
        # 内存数据库使用StaticPool，文件数据库使用QueuePool
        if self._db_path == ":memory:":
            pool_class = StaticPool
            pool_args = {}
        else:
            pool_class = QueuePool
            pool_args = {
                "pool_size": self._pool_config.pool_size,
                "max_overflow": self._pool_config.max_overflow,
                "pool_timeout": self._pool_config.pool_timeout,
                "pool_recycle": self._pool_config.pool_recycle,
                "pool_pre_ping": self._pool_config.pool_pre_ping,
                "echo_pool": self._pool_config.echo_pool,
            }

        engine = create_engine(
            f"sqlite:///{self._db_path}",
            connect_args=connect_args,
            echo=self._echo,
            poolclass=pool_class,
            **pool_args,
        )

        # SQLite性能优化设置
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """设置SQLite性能优化参数。"""
            cursor = dbapi_connection.cursor()
            # 启用外键约束
            cursor.execute("PRAGMA foreign_keys=ON")
            # 设置日志模式为WAL（提高并发性能）
            cursor.execute("PRAGMA journal_mode=WAL")
            # 设置同步模式（性能与安全平衡）
            cursor.execute("PRAGMA synchronous=NORMAL")
            # 设置缓存大小（单位：页，每页约4KB）
            cursor.execute("PRAGMA cache_size=-64000")  # 64MB缓存
            # 设置临时存储在内存中
            cursor.execute("PRAGMA temp_store=MEMORY")
            # 设置忙等待时间（毫秒）
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()

        return engine

    def _create_postgresql_engine(self) -> Engine:
        """创建PostgreSQL数据库引擎。

        Returns:
            SQLAlchemy引擎实例
        """
        # PostgreSQL连接字符串格式：
        # postgresql://user:password@host:port/database
        engine = create_engine(
            self._db_path,
            echo=self._echo,
            pool_size=self._pool_config.pool_size,
            max_overflow=self._pool_config.max_overflow,
            pool_timeout=self._pool_config.pool_timeout,
            pool_recycle=self._pool_config.pool_recycle,
            pool_pre_ping=self._pool_config.pool_pre_ping,
            echo_pool=self._pool_config.echo_pool,
        )

        return engine

    def _setup_pool_events(self) -> None:
        """设置连接池事件监听。"""
        if not self._engine:
            return

        @event.listens_for(self._engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            """连接借出事件。"""
            with self._lock:
                self._statistics.checked_out += 1
                self._statistics.last_check_time = datetime.now()

        @event.listens_for(self._engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            """连接归还事件。"""
            with self._lock:
                self._statistics.checked_in += 1
                self._statistics.last_check_time = datetime.now()

        @event.listens_for(self._engine, "close")
        def on_close(dbapi_connection, connection_record):
            """连接关闭事件。"""
            with self._lock:
                self._statistics.total_connections -= 1

    @contextmanager
    def get_session(self) -> Session:
        """获取数据库会话（同步上下文管理器）。

        Yields:
            Session: 数据库会话实例

        Example:
            >>> with pool.get_session() as session:
            ...     user = session.query(User).first()
        """
        if not self._session_factory:
            raise RuntimeError("Database pool not initialized")

        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @asynccontextmanager
    async def get_async_session(self):
        """获取数据库会话（异步上下文管理器）。

        Yields:
            Session: 数据库会话实例

        Example:
            >>> async with pool.get_async_session() as session:
            ...     user = session.query(User).first()
        """
        if not self._session_factory:
            raise RuntimeError("Database pool not initialized")

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
        """获取数据库引擎。

        Returns:
            Engine: SQLAlchemy引擎实例
        """
        if not self._engine:
            raise RuntimeError("Database pool not initialized")
        return self._engine

    def get_session_factory(self) -> sessionmaker:
        """获取会话工厂。

        Returns:
            sessionmaker: 会话工厂实例
        """
        if not self._session_factory:
            raise RuntimeError("Database pool not initialized")
        return self._session_factory

    def get_statistics(self) -> dict[str, Any]:
        """获取连接池统计信息。

        Returns:
            统计信息字典
        """
        with self._lock:
            stats = {
                "db_type": self._db_type.value,
                "db_path": self._db_path,
                "pool_config": {
                    "pool_size": self._pool_config.pool_size,
                    "max_overflow": self._pool_config.max_overflow,
                    "pool_timeout": self._pool_config.pool_timeout,
                    "pool_recycle": self._pool_config.pool_recycle,
                    "pool_pre_ping": self._pool_config.pool_pre_ping,
                },
                "statistics": {
                    "checked_out": self._statistics.checked_out,
                    "checked_in": self._statistics.checked_in,
                    "total_connections": self._statistics.total_connections,
                    "wait_count": self._statistics.wait_count,
                    "wait_time_ms": self._statistics.wait_time_ms,
                    "last_check_time": (
                        self._statistics.last_check_time.isoformat()
                        if self._statistics.last_check_time
                        else None
                    ),
                },
            }

            # 获取连接池状态
            if self._engine and hasattr(self._engine, "pool"):
                pool = self._engine.pool
                stats["pool_status"] = {
                    "size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                }

            return stats

    def health_check(self) -> dict[str, Any]:
        """执行数据库健康检查。

        Returns:
            健康检查结果字典
        """
        result = {
            "healthy": True,
            "db_type": self._db_type.value,
            "timestamp": datetime.now().isoformat(),
            "errors": [],
        }

        try:
            if not self._engine:
                result["healthy"] = False
                result["errors"].append("Engine not initialized")
                return result

            # 执行简单查询测试连接
            with self._engine.connect() as conn:
                if self._db_type == DatabaseType.SQLITE:
                    conn.execute(text("SELECT 1"))
                elif self._db_type == DatabaseType.POSTGRESQL:
                    conn.execute(text("SELECT 1"))

            result["connection_test"] = "passed"

        except Exception as e:
            result["healthy"] = False
            result["errors"].append(str(e))
            logger.error(f"Database health check failed: {e}")

        return result

    async def start_health_check_task(self, interval: int = 60) -> None:
        """启动后台健康检查任务。

        Args:
            interval: 检查间隔（秒）
        """
        if self._is_running:
            return

        self._is_running = True
        self._health_check_task = asyncio.create_task(
            self._health_check_loop(interval)
        )
        logger.info(f"Health check task started (interval: {interval}s)")

    async def stop_health_check_task(self) -> None:
        """停止后台健康检查任务。"""
        self._is_running = False

        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        logger.info("Health check task stopped")

    async def _health_check_loop(self, interval: int) -> None:
        """健康检查循环。

        Args:
            interval: 检查间隔（秒）
        """
        while self._is_running:
            try:
                await asyncio.sleep(interval)

                if not self._is_running:
                    break

                result = self.health_check()

                if not result["healthy"]:
                    logger.warning(
                        f"Database health check failed: {result['errors']}"
                    )
                    # 尝试重新初始化连接池
                    try:
                        self._initialize_pool()
                        logger.info("Database pool reinitialized")
                    except Exception as e:
                        logger.error(f"Failed to reinitialize pool: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")

    def close(self) -> None:
        """关闭连接池。"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None

        logger.info("Database connection pool closed")

    async def close_async(self) -> None:
        """异步关闭连接池。"""
        await self.stop_health_check_task()
        self.close()

    def __enter__(self) -> "DatabaseConnectionPool":
        """上下文管理器入口。"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器退出。"""
        self.close()


class DatabasePoolManager:
    """
    数据库连接池管理器（多数据库支持）。

    管理多个数据库连接池，提供统一的访问接口。

    Example:
        >>> manager = DatabasePoolManager()
        >>> manager.register("main", "experiments.db", DatabaseType.SQLITE)
        >>> with manager.get_session("main") as session:
        ...     pass
    """

    def __init__(self) -> None:
        """初始化数据库连接池管理器。"""
        self._pools: dict[str, DatabaseConnectionPool] = {}
        self._lock = Lock()

        logger.info("DatabasePoolManager initialized")

    def register(
        self,
        name: str,
        db_path: str,
        db_type: DatabaseType = DatabaseType.SQLITE,
        pool_config: PoolConfig | None = None,
        echo: bool = False,
    ) -> DatabaseConnectionPool:
        """注册数据库连接池。

        Args:
            name: 连接池名称
            db_path: 数据库路径
            db_type: 数据库类型
            pool_config: 连接池配置
            echo: 是否打印SQL

        Returns:
            DatabaseConnectionPool: 连接池实例
        """
        with self._lock:
            if name in self._pools:
                logger.warning(f"Pool '{name}' already exists, replacing")

            pool = DatabaseConnectionPool(
                db_path=db_path,
                db_type=db_type,
                pool_config=pool_config,
                echo=echo,
            )
            self._pools[name] = pool

            logger.info(f"Database pool registered: {name}")
            return pool

    def get_pool(self, name: str) -> DatabaseConnectionPool:
        """获取数据库连接池。

        Args:
            name: 连接池名称

        Returns:
            DatabaseConnectionPool: 连接池实例

        Raises:
            KeyError: 连接池不存在
        """
        if name not in self._pools:
            raise KeyError(f"Pool '{name}' not found")
        return self._pools[name]

    @contextmanager
    def get_session(self, name: str = "default"):
        """获取数据库会话。

        Args:
            name: 连接池名称

        Yields:
            Session: 数据库会话
        """
        pool = self.get_pool(name)
        with pool.get_session() as session:
            yield session

    def get_all_statistics(self) -> dict[str, Any]:
        """获取所有连接池统计信息。

        Returns:
            统计信息字典
        """
        return {
            name: pool.get_statistics()
            for name, pool in self._pools.items()
        }

    def health_check_all(self) -> dict[str, dict[str, Any]]:
        """检查所有数据库健康状态。

        Returns:
            健康检查结果字典
        """
        return {
            name: pool.health_check()
            for name, pool in self._pools.items()
        }

    def close_all(self) -> None:
        """关闭所有连接池。"""
        for name, pool in self._pools.items():
            pool.close()
            logger.info(f"Pool '{name}' closed")

        self._pools.clear()

    async def close_all_async(self) -> None:
        """异步关闭所有连接池。"""
        for name, pool in self._pools.items():
            await pool.close_async()
            logger.info(f"Pool '{name}' closed")

        self._pools.clear()

    def __enter__(self) -> "DatabasePoolManager":
        """上下文管理器入口。"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器退出。"""
        self.close_all()


# ==================== 全局实例 ====================

_global_pool_manager: DatabasePoolManager | None = None
_global_pool_lock = Lock()


def get_pool_manager() -> DatabasePoolManager:
    """获取全局数据库连接池管理器。

    Returns:
        DatabasePoolManager: 全局管理器实例
    """
    global _global_pool_manager

    if _global_pool_manager is None:
        with _global_pool_lock:
            if _global_pool_manager is None:
                _global_pool_manager = DatabasePoolManager()

    return _global_pool_manager


def get_default_pool() -> DatabaseConnectionPool:
    """获取默认数据库连接池。

    Returns:
        DatabaseConnectionPool: 默认连接池实例
    """
    manager = get_pool_manager()

    if "default" not in manager._pools:
        manager.register(
            name="default",
            db_path="experiments.db",
            db_type=DatabaseType.SQLITE,
        )

    return manager.get_pool("default")


# ==================== 便捷函数 ====================


def create_pool(
    db_path: str = "experiments.db",
    db_type: DatabaseType = DatabaseType.SQLITE,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_timeout: float = 30.0,
    pool_recycle: int = 3600,
    pool_pre_ping: bool = True,
    echo: bool = False,
) -> DatabaseConnectionPool:
    """创建数据库连接池的便捷函数。

    Args:
        db_path: 数据库路径
        db_type: 数据库类型
        pool_size: 连接池大小
        max_overflow: 最大溢出连接数
        pool_timeout: 获取连接超时时间
        pool_recycle: 连接回收时间
        pool_pre_ping: 是否启用健康检查
        echo: 是否打印SQL

    Returns:
        DatabaseConnectionPool: 连接池实例

    Example:
        >>> pool = create_pool("experiments.db", pool_size=10)
        >>> with pool.get_session() as session:
        ...     users = session.query(User).all()
    """
    config = PoolConfig(
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        pool_pre_ping=pool_pre_ping,
    )

    return DatabaseConnectionPool(
        db_path=db_path,
        db_type=db_type,
        pool_config=config,
        echo=echo,
    )


def init_database_pool(
    db_path: str = "experiments.db",
    pool_size: int = 5,
    max_overflow: int = 10,
) -> DatabaseConnectionPool:
    """初始化默认数据库连接池。

    Args:
        db_path: 数据库路径
        pool_size: 连接池大小
        max_overflow: 最大溢出连接数

    Returns:
        DatabaseConnectionPool: 连接池实例
    """
    manager = get_pool_manager()

    if "default" in manager._pools:
        return manager.get_pool("default")

    return manager.register(
        name="default",
        db_path=db_path,
        db_type=DatabaseType.SQLITE,
        pool_config=PoolConfig(
            pool_size=pool_size,
            max_overflow=max_overflow,
        ),
    )
