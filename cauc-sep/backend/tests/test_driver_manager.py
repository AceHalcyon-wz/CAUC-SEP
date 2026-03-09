"""
文件名: test_driver_manager.py
路径: backend/tests/
功能: 驱动进程管理器单元测试
作者: Backend Engineer Agent
创建日期: 2026-03-07
依赖: pytest, unittest.mock
"""

import asyncio
import time
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.abstract import AbstractDevice, DeviceStatus
from core.driver_manager import (
    DriverProcessConfig,
    DriverProcessInfo,
    DriverProcessManager,
    DriverProcessStatus,
    IPCMessage,
    IPCMessageType,
    create_driver_manager,
    driver_process_entry,
)


class MockDevice(AbstractDevice):
    """模拟设备类，用于测试。"""

    def __init__(self, device_id: str, config: Dict[str, Any]):
        """初始化模拟设备。"""
        super().__init__(device_id, config)
        self._connected = False
        self._position = 0.0
        self._call_count = {"connect": 0, "disconnect": 0, "test_method": 0}

    async def connect(self) -> bool:
        """模拟连接。"""
        self._call_count["connect"] += 1
        self._connected = True
        self.status = DeviceStatus.READY
        return True

    async def disconnect(self) -> bool:
        """模拟断开连接。"""
        self._call_count["disconnect"] += 1
        self._connected = False
        self.status = DeviceStatus.DISCONNECTED
        return True

    async def read_status(self) -> Dict[str, Any]:
        """读取状态。"""
        return {
            "device_id": self.device_id,
            "status": self.status.value,
            "connected": self._connected,
            "position": self._position,
        }

    async def test_method(self, value: float) -> float:
        """测试方法。"""
        self._call_count["test_method"] += 1
        self._position = value
        return value * 2

    def get_call_count(self, method: str) -> int:
        """获取方法调用次数。"""
        return self._call_count.get(method, 0)


class TestIPCMessage:
    """IPC消息测试类。"""

    def test_ipc_message_creation(self):
        """测试IPC消息创建。"""
        msg = IPCMessage(
            msg_type=IPCMessageType.COMMAND,
            payload={"test": "data"},
            source="test_source",
        )

        assert msg.msg_type == IPCMessageType.COMMAND
        assert msg.payload == {"test": "data"}
        assert msg.source == "test_source"
        assert msg.timestamp > 0

    def test_ipc_message_serialization(self):
        """测试IPC消息序列化。"""
        msg = IPCMessage(
            msg_type=IPCMessageType.STATUS,
            payload={"status": "running"},
            source="driver_1",
            request_id="req_123",
        )

        data = msg.to_dict()

        assert data["msg_type"] == "status"
        assert data["payload"]["status"] == "running"
        assert data["source"] == "driver_1"
        assert data["request_id"] == "req_123"

    def test_ipc_message_deserialization(self):
        """测试IPC消息反序列化。"""
        data = {
            "msg_type": "error",
            "payload": {"error": "test error"},
            "timestamp": 12345.0,
            "source": "driver_2",
            "request_id": "req_456",
        }

        msg = IPCMessage.from_dict(data)

        assert msg.msg_type == IPCMessageType.ERROR
        assert msg.payload["error"] == "test error"
        assert msg.timestamp == 12345.0
        assert msg.source == "driver_2"
        assert msg.request_id == "req_456"


class TestDriverProcessConfig:
    """驱动进程配置测试类。"""

    def test_config_creation(self):
        """测试配置创建。"""
        config = DriverProcessConfig(
            driver_id="test_driver",
            driver_class=MockDevice,
            config={"port": "COM1"},
            auto_restart=True,
            max_restart_count=5,
        )

        assert config.driver_id == "test_driver"
        assert config.driver_class == MockDevice
        assert config.config == {"port": "COM1"}
        assert config.auto_restart is True
        assert config.max_restart_count == 5

    def test_config_defaults(self):
        """测试配置默认值。"""
        config = DriverProcessConfig(
            driver_id="test_driver",
            driver_class=MockDevice,
        )

        assert config.config == {}
        assert config.auto_restart is True
        assert config.max_restart_count == 3
        assert config.restart_delay == 5.0
        assert config.heartbeat_interval == 10.0
        assert config.heartbeat_timeout == 30.0


class TestDriverProcessInfo:
    """驱动进程信息测试类。"""

    def test_info_creation(self):
        """测试进程信息创建。"""
        info = DriverProcessInfo(driver_id="test_driver")

        assert info.driver_id == "test_driver"
        assert info.status == DriverProcessStatus.STOPPED
        assert info.pid is None
        assert info.start_time is None
        assert info.restart_count == 0

    def test_info_serialization(self):
        """测试进程信息序列化。"""
        info = DriverProcessInfo(
            driver_id="test_driver",
            status=DriverProcessStatus.RUNNING,
            pid=12345,
            start_time=1000.0,
            restart_count=2,
            last_error="test error",
        )

        data = info.to_dict()

        assert data["driver_id"] == "test_driver"
        assert data["status"] == "running"
        assert data["pid"] == 12345
        assert data["start_time"] == 1000.0
        assert data["restart_count"] == 2
        assert data["last_error"] == "test error"


class TestDriverProcessManager:
    """驱动进程管理器测试类。"""

    def test_manager_creation(self):
        """测试管理器创建。"""
        manager = DriverProcessManager()

        assert manager is not None
        assert len(manager._drivers) == 0
        assert len(manager._processes) == 0

    def test_register_driver(self):
        """测试驱动注册。"""
        manager = DriverProcessManager()

        result = manager.register_driver(
            driver_id="motor_1",
            driver_class=MockDevice,
            config={"port": "COM1"},
        )

        assert result is True
        assert "motor_1" in manager._drivers
        assert "motor_1" in manager._process_info

    def test_register_duplicate_driver(self):
        """测试重复注册驱动。"""
        manager = DriverProcessManager()

        manager.register_driver("motor_1", MockDevice)

        with pytest.raises(ValueError, match="已存在"):
            manager.register_driver("motor_1", MockDevice)

    def test_register_invalid_driver_class(self):
        """测试注册无效驱动类。"""
        manager = DriverProcessManager()

        class InvalidClass:
            pass

        with pytest.raises(ValueError, match="必须继承自 AbstractDevice"):
            manager.register_driver("motor_1", InvalidClass)

    def test_unregister_driver(self):
        """测试驱动注销。"""
        manager = DriverProcessManager()

        manager.register_driver("motor_1", MockDevice)
        result = manager.unregister_driver("motor_1")

        assert result is True
        assert "motor_1" not in manager._drivers

    def test_unregister_nonexistent_driver(self):
        """测试注销不存在的驱动。"""
        manager = DriverProcessManager()

        with pytest.raises(KeyError, match="不存在"):
            manager.unregister_driver("motor_1")

    def test_get_driver_info(self):
        """测试获取驱动信息。"""
        manager = DriverProcessManager()

        manager.register_driver(
            "motor_1",
            MockDevice,
            config={"port": "COM1"},
            auto_restart=False,
        )

        info = manager.get_driver_info("motor_1")

        assert info["driver_id"] == "motor_1"
        assert info["status"] == "stopped"
        assert info["config"]["auto_restart"] is False

    def test_get_all_drivers_info(self):
        """测试获取所有驱动信息。"""
        manager = DriverProcessManager()

        manager.register_driver("motor_1", MockDevice)
        manager.register_driver("motor_2", MockDevice)

        all_info = manager.get_all_drivers_info()

        assert len(all_info) == 2
        assert "motor_1" in all_info
        assert "motor_2" in all_info

    def test_create_driver_manager_function(self):
        """测试便捷函数。"""
        manager = create_driver_manager()

        assert isinstance(manager, DriverProcessManager)


class TestDriverProcessManagerIntegration:
    """驱动进程管理器集成测试类。"""

    @pytest.mark.asyncio
    async def test_start_stop_driver(self):
        """测试启动和停止驱动进程。"""
        manager = DriverProcessManager()

        try:
            # 注册驱动
            manager.register_driver(
                "test_driver",
                MockDevice,
                {"port": "COM_TEST"},
                heartbeat_interval=2.0,
            )

            # 启动驱动
            result = manager.start_driver("test_driver")
            assert result is True

            # 等待进程启动
            await asyncio.sleep(1.0)

            # 检查状态
            info = manager.get_driver_info("test_driver")
            assert info["status"] == "running"
            assert info["pid"] is not None

            # 停止驱动
            result = manager.stop_driver("test_driver")
            assert result is True

            # 等待进程停止
            await asyncio.sleep(0.5)

            # 检查状态
            info = manager.get_driver_info("test_driver")
            assert info["status"] == "stopped"

        finally:
            manager.shutdown()

    @pytest.mark.asyncio
    async def test_send_command(self):
        """测试发送命令。"""
        manager = DriverProcessManager()

        try:
            manager.register_driver(
                "test_driver",
                MockDevice,
                heartbeat_interval=5.0,
            )

            manager.start_driver("test_driver")
            await asyncio.sleep(1.5)

            # 发送测试命令
            result = await manager.send_command(
                "test_driver",
                "test_method",
                {"value": 10.0},
                timeout=5.0,
            )

            assert result["success"] is True
            assert result["result"] == 20.0  # test_method returns value * 2

        finally:
            manager.shutdown()

    @pytest.mark.asyncio
    async def test_send_command_to_stopped_driver(self):
        """测试向停止的驱动发送命令。"""
        manager = DriverProcessManager()

        try:
            manager.register_driver("test_driver", MockDevice)

            with pytest.raises(RuntimeError, match="未运行"):
                await manager.send_command("test_driver", "test_method")

        finally:
            manager.shutdown()

    @pytest.mark.asyncio
    async def test_start_all_stop_all(self):
        """测试批量启动和停止。"""
        manager = DriverProcessManager()

        try:
            manager.register_driver("driver_1", MockDevice, heartbeat_interval=3.0)
            manager.register_driver("driver_2", MockDevice, heartbeat_interval=3.0)

            # 启动所有
            start_results = manager.start_all()
            assert start_results["driver_1"] is True
            assert start_results["driver_2"] is True

            await asyncio.sleep(1.5)

            # 检查状态
            info1 = manager.get_driver_info("driver_1")
            info2 = manager.get_driver_info("driver_2")
            assert info1["status"] == "running"
            assert info2["status"] == "running"

            # 停止所有
            stop_results = manager.stop_all()
            assert stop_results["driver_1"] is True
            assert stop_results["driver_2"] is True

        finally:
            manager.shutdown()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """测试上下文管理器。"""
        with DriverProcessManager() as manager:
            manager.register_driver("test_driver", MockDevice)
            manager.start_driver("test_driver")
            await asyncio.sleep(0.5)

            info = manager.get_driver_info("test_driver")
            assert info["status"] == "running"

        # 退出上下文后自动关闭
        assert manager._running is False


class TestDriverProcessStatus:
    """驱动进程状态测试类。"""

    def test_status_values(self):
        """测试状态枚举值。"""
        assert DriverProcessStatus.STOPPED.value == "stopped"
        assert DriverProcessStatus.STARTING.value == "starting"
        assert DriverProcessStatus.RUNNING.value == "running"
        assert DriverProcessStatus.STOPPING.value == "stopping"
        assert DriverProcessStatus.ERROR.value == "error"
        assert DriverProcessStatus.RESTARTING.value == "restarting"


class TestIPCMessageType:
    """IPC消息类型测试类。"""

    def test_message_type_values(self):
        """测试消息类型枚举值。"""
        assert IPCMessageType.COMMAND.value == "command"
        assert IPCMessageType.STOP.value == "stop"
        assert IPCMessageType.RESTART.value == "restart"
        assert IPCMessageType.PING.value == "ping"
        assert IPCMessageType.STATUS.value == "status"
        assert IPCMessageType.HEARTBEAT.value == "heartbeat"
        assert IPCMessageType.ERROR.value == "error"
        assert IPCMessageType.LOG.value == "log"
        assert IPCMessageType.DATA.value == "data"
        assert IPCMessageType.RESPONSE.value == "response"


# 性能测试
class TestDriverProcessManagerPerformance:
    """驱动进程管理器性能测试类。"""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_rapid_start_stop(self):
        """测试快速启动停止。"""
        manager = DriverProcessManager()

        try:
            manager.register_driver("test_driver", MockDevice, heartbeat_interval=1.0)

            # 快速启动停止5次
            for i in range(5):
                manager.start_driver("test_driver")
                await asyncio.sleep(0.3)
                manager.stop_driver("test_driver")
                await asyncio.sleep(0.1)

            info = manager.get_driver_info("test_driver")
            assert info["status"] == "stopped"

        finally:
            manager.shutdown()

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_multiple_drivers(self):
        """测试多驱动管理。"""
        manager = DriverProcessManager()

        try:
            # 注册5个驱动
            for i in range(5):
                manager.register_driver(
                    f"driver_{i}",
                    MockDevice,
                    heartbeat_interval=3.0,
                )

            # 启动所有
            manager.start_all()
            await asyncio.sleep(2.0)

            # 检查所有驱动状态
            all_info = manager.get_all_drivers_info()
            for driver_id, info in all_info.items():
                assert info["status"] == "running"

            # 停止所有
            manager.stop_all()

        finally:
            manager.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
