"""
Pytest配置和共享fixtures

文件名: conftest.py
路径: backend/tests/
功能: 提供测试所需的共享fixtures、配置测试环境、Mock硬件设备
作者: CAUC-SEP Team
创建日期: 2024-01-01
更新日期: 2026-03-16
依赖: pytest, pytest-asyncio, fastapi, sqlalchemy, numpy, httpx

主要功能：
- 提供共享测试fixtures
- 配置测试环境
- Mock硬件设备和外部依赖
- 创建临时数据库和存储
- 支持httpx异步测试客户端

Fixtures列表：
- event_loop: 事件循环
- temp_db: 临时数据库
- test_db_session: 测试数据库会话（支持事务回滚）
- mock_modbus_client: Mock Modbus客户端
- mock_dm2c: Mock DM2C驱动器
- mock_serial_port: Mock串口
- mock_config: Mock设备配置
- physics_analyzer: 物理分析器
- sample_hysteresis_data: 模拟磁滞回线数据
- sample_signal_data: 模拟信号数据
- clean_device_registry: 清理设备注册表
- test_client: FastAPI同步测试客户端
- async_client: httpx异步测试客户端
- temp_storage: 临时数据存储
- sample_experiment_data: 示例实验数据
- mock_websocket: Mock WebSocket连接
"""

import asyncio
import os
import sys
import tempfile
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import numpy as np
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.abstract import DeviceStatus
from core.analysis import PhysicsAnalyzer
from core.storage.data_storage import DataStorage
from core.dm2c_driver import LeadshineDM2C
from main import app
from models import Base


# ==================== 事件循环 Fixtures ====================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop]:
    """创建会话级别事件循环。"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==================== 数据库 Fixtures ====================


@pytest.fixture
def temp_db():
    """创建临时数据库。

    创建一个临时的SQLite数据库用于测试，
    测试结束后自动清理。

    Yields:
        Tuple[Session, str]: 数据库会话和数据库路径
    """
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session, db_path

    session.close()
    engine.dispose()
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture(scope="function")
def test_db_engine():
    """创建测试数据库引擎（内存数据库，支持事务回滚）。

    使用内存SQLite数据库，配置StaticPool以支持事务回滚。
    每个测试函数使用独立的数据库实例。

    Yields:
        Engine: SQLAlchemy引擎实例
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_db_engine) -> Generator[Session, None, None]:
    """创建测试数据库会话（支持事务回滚）。

    每个测试用例运行在独立的事务中，
    测试结束后自动回滚，保证测试隔离。

    Args:
        test_db_engine: 测试数据库引擎

    Yields:
        Session: 数据库会话实例
    """
    connection = test_db_engine.connect()
    transaction = connection.begin()

    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    # 配置session在每次flush后自动过期对象
    session.expire_on_commit = False

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def temp_storage():
    """创建临时数据存储。

    创建一个临时的DataStorage实例用于测试。

    Yields:
        DataStorage: 数据存储实例
    """
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    storage = DataStorage(db_path)
    yield storage

    # 确保关闭数据库连接
    if hasattr(storage, "engine"):
        storage.engine.dispose()

    # 尝试删除临时文件
    import gc

    gc.collect()

    for _ in range(5):
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
            break
        except PermissionError:
            import time

            time.sleep(0.1)
            gc.collect()


# ==================== Mock 设备 Fixtures ====================


@pytest.fixture
def mock_modbus_client():
    """创建Mock Modbus客户端。

    模拟Modbus串口客户端的基本操作。

    Returns:
        MagicMock: Mock的Modbus客户端实例
    """
    client = MagicMock()
    client.connect = MagicMock(return_value=True)
    client.close = MagicMock()
    client.read_holding_registers = MagicMock()
    client.write_register = MagicMock()
    client.write_registers = MagicMock()
    return client


@pytest.fixture
def mock_dm2c(mock_modbus_client):
    """创建Mock DM2C驱动器实例。

    模拟Leadshine DM2C步进电机驱动器的行为。

    Args:
        mock_modbus_client: Mock的Modbus客户端

    Returns:
        LeadshineDM2C: 配置好Mock的驱动器实例
    """
    with patch("core.dm2c_driver.PYMUSBUS_AVAILABLE", False):
        driver = LeadshineDM2C(
            device_id="test_motor",
            config={"port": "COM_TEST", "slave_id": 1, "baudrate": 115200, "steps_per_mm": 1600},
        )
        driver.client = mock_modbus_client
        driver.status = DeviceStatus.READY
        return driver


@pytest_asyncio.fixture
async def mock_serial_port():
    """创建Mock串口。

    模拟串口的基本读写操作。

    Yields:
        MagicMock: Mock的串口实例
    """
    with patch("serial.Serial") as mock_serial:
        mock_instance = MagicMock()
        mock_instance.is_open = True
        mock_instance.read = AsyncMock(return_value=b"\x01\x02\x03\x04")
        mock_instance.write = AsyncMock(return_value=4)
        mock_instance.close = MagicMock()
        yield mock_instance


@pytest.fixture
def mock_config():
    """创建Mock设备配置。

    Returns:
        Dict: 设备配置字典
    """
    return {
        "port": "COM3",
        "slave_id": 1,
        "steps_per_mm": 1600,
        "baudrate": 115200,
        "simulation": True,
    }


# ==================== 分析器 Fixtures ====================


@pytest.fixture
def physics_analyzer():
    """创建物理分析器实例。

    Returns:
        PhysicsAnalyzer: 物理分析器实例
    """
    return PhysicsAnalyzer()


@pytest.fixture
def sample_hysteresis_data():
    """生成模拟磁滞回线数据。

    生成带有噪声的磁滞回线数据用于测试。

    Returns:
        Tuple[np.ndarray, np.ndarray]: 磁场强度和磁矩数据
    """
    h_field = np.linspace(-1000, 1000, 200)
    h_field = np.concatenate([h_field, h_field[::-1]])

    ms = 1.0

    moment = ms * np.tanh(h_field / 200)
    noise = np.random.normal(0, 0.02, len(h_field))
    moment += noise

    return h_field, moment


@pytest.fixture
def sample_signal_data():
    """生成模拟信号数据。

    生成带有噪声的正弦信号用于测试。

    Returns:
        Tuple[np.ndarray, np.ndarray]: x坐标和信号数据
    """
    x = np.linspace(0, 10, 100)
    signal_clean = np.sin(x)
    noise = np.random.normal(0, 0.1, len(x))
    signal_noisy = signal_clean + noise
    return x, signal_noisy


# ==================== 设备注册表 Fixtures ====================


@pytest.fixture(autouse=True)
def clean_device_registry():
    """自动清理设备注册表（每个测试前后）。"""
    from core.device_management.device_registry import DeviceRegistry

    # 测试前清空注册表
    DeviceRegistry.clear()

    yield

    # 测试后清空注册表
    DeviceRegistry.clear()


# ==================== 测试客户端 Fixtures ====================


@pytest.fixture
def test_client(mock_dm2c):
    """创建FastAPI同步测试客户端。

    Args:
        mock_dm2c: Mock的DM2C驱动器

    Yields:
        TestClient: FastAPI测试客户端实例
    """
    # 确保注册表为空（已在 clean_device_registry 中清理）

    # 注意：不手动设置设备，让 lifespan 函数处理设备初始化
    # 这样可以避免重复注册问题

    with TestClient(app) as client:
        yield client

    # 清理（已在 clean_device_registry 中处理）


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """创建httpx异步测试客户端。

    使用httpx.AsyncClient进行异步API测试，
    支持异步请求和响应验证。

    Yields:
        httpx.AsyncClient: 异步HTTP客户端实例

    Example:
        async def test_api(async_client):
            response = await async_client.get("/api/v1/motor/status")
            assert response.status_code == 200
    """
    from httpx import ASGITransport

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        timeout=30.0,
    ) as client:
        yield client


@pytest_asyncio.fixture
async def async_client_with_mock(mock_dm2c) -> AsyncGenerator[httpx.AsyncClient, None]:
    """创建带Mock设备的httpx异步测试客户端。

    预配置Mock设备，适用于需要设备依赖的API测试。

    Args:
        mock_dm2c: Mock的DM2C驱动器

    Yields:
        httpx.AsyncClient: 异步HTTP客户端实例
    """
    from httpx import ASGITransport

    # 设置Mock设备
    from api import motor

    motor.set_dm2c(mock_dm2c)

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        timeout=30.0,
    ) as client:
        yield client


# ==================== 实验数据 Fixtures ====================


@pytest.fixture
def sample_experiment_data(temp_storage):
    """创建示例实验数据。

    创建包含用户、实验和数据记录的完整测试数据。

    Args:
        temp_storage: 临时数据存储

    Returns:
        Tuple[DataStorage, int, int]: 数据存储、用户ID、实验ID
    """
    user_id = temp_storage.create_user(
        username="test_user", password_hash="hash123", role="operator"
    )

    exp_id = temp_storage.create_experiment(
        exp_name="测试实验", exp_type="hysteresis", user_id=user_id
    )

    for i in range(10):
        temp_storage.add_data_record(
            experiment_id=exp_id,
            position_steps=i * 100,
            position_mm=i * 0.0625,
            field_value=i * 10.0,
            current_value=i * 0.1,
        )

    return temp_storage, user_id, exp_id


# ==================== WebSocket Fixtures ====================


@pytest.fixture
def mock_websocket():
    """创建Mock WebSocket连接。

    Returns:
        AsyncMock: Mock的WebSocket实例
    """
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_json = AsyncMock()
    ws.close = AsyncMock()
    ws.send_bytes = AsyncMock()
    ws.receive_bytes = AsyncMock()
    return ws


# ==================== Pytest 配置钩子 ====================


def pytest_configure(config):
    """Pytest配置钩子。"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
