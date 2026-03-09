"""
Pytest配置和共享fixtures

功能：
- 提供测试所需的共享fixtures
- 配置测试环境
- Mock硬件设备
"""

import asyncio
import os
import sys
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import motor
from core.abstract import DeviceStatus
from core.analysis import PhysicsAnalyzer
from core.data_storage import DataStorage
from core.dm2c_driver import LeadshineDM2C
from main import app
from models import Base


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环。"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_db():
    """创建临时数据库。"""
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


@pytest.fixture
def mock_modbus_client():
    """创建Mock Modbus客户端。"""
    client = MagicMock()
    client.connect = MagicMock(return_value=True)
    client.close = MagicMock()
    client.read_holding_registers = MagicMock()
    client.write_register = MagicMock()
    client.write_registers = MagicMock()
    return client


@pytest.fixture
def mock_dm2c(mock_modbus_client):
    """创建Mock DM2C驱动器实例。"""
    with patch("core.dm2c_driver.PYMUSBUS_AVAILABLE", False):
        driver = LeadshineDM2C(
            device_id="test_motor",
            config={"port": "COM_TEST", "slave_id": 1, "baudrate": 115200, "steps_per_mm": 1600},
        )
        driver.client = mock_modbus_client
        driver.status = DeviceStatus.READY
        return driver


@pytest.fixture
def physics_analyzer():
    """创建物理分析器实例。"""
    return PhysicsAnalyzer()


@pytest.fixture
def sample_hysteresis_data():
    """生成模拟磁滞回线数据。"""
    h_field = np.linspace(-1000, 1000, 200)
    h_field = np.concatenate([h_field, h_field[::-1]])

    ms = 1.0

    moment = ms * np.tanh(h_field / 200)
    noise = np.random.normal(0, 0.02, len(h_field))
    moment += noise

    return h_field, moment


@pytest.fixture
def sample_signal_data():
    """生成模拟信号数据。"""
    x = np.linspace(0, 10, 100)
    signal_clean = np.sin(x)
    noise = np.random.normal(0, 0.1, len(x))
    signal_noisy = signal_clean + noise
    return x, signal_noisy


@pytest.fixture(autouse=True)
def clean_device_registry():
    """自动清理设备注册表（每个测试前后）。"""
    from core.device_registry import DeviceRegistry
    
    # 测试前清空注册表
    DeviceRegistry.clear()
    
    yield
    
    # 测试后清空注册表
    DeviceRegistry.clear()


@pytest.fixture
def test_client(mock_dm2c):
    """创建FastAPI测试客户端。"""
    from core.device_registry import DeviceRegistry

    # 确保注册表为空（已在 clean_device_registry 中清理）
    
    # 注意：不手动设置设备，让 lifespan 函数处理设备初始化
    # 这样可以避免重复注册问题

    with TestClient(app) as client:
        yield client

    # 清理（已在 clean_device_registry 中处理）


@pytest.fixture
def temp_storage():
    """创建临时数据存储。"""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    storage = DataStorage(db_path)
    yield storage

    # 确保关闭数据库连接
    if hasattr(storage, 'engine'):
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


@pytest.fixture
def sample_experiment_data(temp_storage):
    """创建示例实验数据。"""
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


@pytest.fixture
def mock_websocket():
    """创建Mock WebSocket连接。"""
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_json = AsyncMock()
    ws.close = AsyncMock()
    return ws


def pytest_configure(config):
    """Pytest配置钩子。"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
