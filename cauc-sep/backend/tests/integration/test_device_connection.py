"""
文件名: test_device_connection.py
路径: backend/tests/integration/
功能: 设备连接流程集成测试
作者: Test Debugger Agent
创建日期: 2026-03-08
依赖: pytest, asyncio
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.abstract import DeviceStatus
from core.error_recovery import (
    DeviceConnectionRecovery,
    DeviceConnectionState,
    RecoveryState,
    RecoveryStrategy,
    RetryConfig,
    RetryExecutor,
    RetryResult,
)


class MockDevice:
    """模拟设备类，用于测试。

    不继承AbstractDevice以避免实现所有抽象方法。
    """

    def __init__(
        self,
        device_id: str,
        config: dict,
        fail_on_connect: bool = False,
        fail_on_disconnect: bool = False,
        connect_delay: float = 0.1,
    ):
        """初始化模拟设备。

        Args:
            device_id: 设备ID
            config: 设备配置
            fail_on_connect: 连接时是否失败
            fail_on_disconnect: 断开时是否失败
            connect_delay: 连接延迟时间
        """
        self.device_id = device_id
        self.config = config
        self.fail_on_connect = fail_on_connect
        self.fail_on_disconnect = fail_on_disconnect
        self.connect_delay = connect_delay
        self.connect_count = 0
        self.disconnect_count = 0
        self._status = DeviceStatus.DISCONNECTED

    @property
    def status(self) -> DeviceStatus:
        """获取设备状态。"""
        return self._status

    @status.setter
    def status(self, value: DeviceStatus):
        """设置设备状态。"""
        self._status = value

    async def connect(self) -> bool:
        """连接设备。"""
        await asyncio.sleep(self.connect_delay)
        self.connect_count += 1

        if self.fail_on_connect:
            self._status = DeviceStatus.ERROR
            raise ConnectionError(f"Mock device {self.device_id} connect failed")

        self._status = DeviceStatus.READY
        return True

    async def disconnect(self) -> bool:
        """断开设备连接。"""
        self.disconnect_count += 1

        if self.fail_on_disconnect:
            raise RuntimeError(f"Mock device {self.device_id} disconnect failed")

        self._status = DeviceStatus.DISCONNECTED
        return True

    async def read_status(self) -> dict:
        """读取设备状态。"""
        return {
            "device_id": self.device_id,
            "status": self._status.value,
            "connected": self._status != DeviceStatus.DISCONNECTED,
        }

    async def health_check(self) -> bool:
        """健康检查。"""
        return self._status == DeviceStatus.READY


class TestDeviceConnectionBasic:
    """设备连接基础测试。"""

    @pytest.mark.asyncio
    async def test_device_connect_success(self):
        """测试设备连接成功。"""
        device = MockDevice("test_device_01", {})

        result = await device.connect()

        assert result is True
        assert device.status == DeviceStatus.READY
        assert device.connect_count == 1

    @pytest.mark.asyncio
    async def test_device_disconnect_success(self):
        """测试设备断开连接成功。"""
        device = MockDevice("test_device_01", {})
        await device.connect()

        result = await device.disconnect()

        assert result is True
        assert device.status == DeviceStatus.DISCONNECTED
        assert device.disconnect_count == 1

    @pytest.mark.asyncio
    async def test_device_connect_failure(self):
        """测试设备连接失败。"""
        device = MockDevice("test_device_01", {}, fail_on_connect=True)

        with pytest.raises(ConnectionError):
            await device.connect()

        assert device.status == DeviceStatus.ERROR
        assert device.connect_count == 1

    @pytest.mark.asyncio
    async def test_device_reconnect_flow(self):
        """测试设备重连流程。"""
        device = MockDevice("test_device_01", {})

        # 首次连接
        result1 = await device.connect()
        assert result1 is True
        assert device.status == DeviceStatus.READY

        # 断开连接
        result2 = await device.disconnect()
        assert result2 is True
        assert device.status == DeviceStatus.DISCONNECTED

        # 重新连接
        result3 = await device.connect()
        assert result3 is True
        assert device.status == DeviceStatus.READY
        assert device.connect_count == 2


class TestRetryExecutor:
    """重试执行器测试。"""

    @pytest.mark.asyncio
    async def test_retry_executor_success_first_try(self):
        """测试首次尝试成功。"""
        config = RetryConfig(max_retries=3, initial_delay=0.1)
        executor = RetryExecutor(config)

        async def success_func():
            return "success"

        result = await executor.execute(success_func)

        assert result.success is True
        assert result.attempts == 1
        assert result.result == "success"

    @pytest.mark.asyncio
    async def test_retry_executor_success_after_retry(self):
        """测试重试后成功。"""
        config = RetryConfig(max_retries=3, initial_delay=0.05)
        executor = RetryExecutor(config)

        call_count = 0

        async def retry_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"

        result = await executor.execute(retry_func)

        assert result.success is True
        assert result.attempts == 3
        assert result.result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_executor_all_failures(self):
        """测试所有重试都失败。"""
        config = RetryConfig(max_retries=3, initial_delay=0.05)
        executor = RetryExecutor(config)

        async def fail_func():
            raise ValueError("Permanent error")

        result = await executor.execute(fail_func)

        assert result.success is False
        assert result.attempts == 3
        assert isinstance(result.last_exception, ValueError)

    @pytest.mark.asyncio
    async def test_retry_executor_with_specific_exceptions(self):
        """测试特定异常重试。"""
        config = RetryConfig(
            max_retries=3,
            initial_delay=0.05,
            retryable_exceptions=[ConnectionError],
        )
        executor = RetryExecutor(config)

        call_count = 0

        async def mixed_error_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Retryable")
            raise ValueError("Non-retryable")

        # 第一次是可重试异常
        result = await executor.execute(mixed_error_func)

        assert result.success is False
        assert result.attempts == 2  # 第一次重试后遇到不可重试异常

    @pytest.mark.asyncio
    async def test_retry_executor_exponential_backoff(self):
        """测试指数退避策略。"""
        config = RetryConfig(
            max_retries=3,
            initial_delay=0.1,
            backoff_factor=2.0,
            strategy=RecoveryStrategy.EXPONENTIAL_BACKOFF,
            jitter=False,
        )
        executor = RetryExecutor(config)

        delays = []
        call_count = 0

        async def track_delay_func():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise ValueError("Retry")
            return "done"

        import time

        start = time.time()
        result = await executor.execute(track_delay_func)
        elapsed = time.time() - start

        assert result.success is True
        # 预期延迟: 0.1 + 0.2 = 0.3 (两次重试间隔)
        assert elapsed >= 0.25  # 允许一些误差


class TestDeviceConnectionRecovery:
    """设备连接恢复测试。"""

    @pytest.fixture
    def temp_state_file(self):
        """创建临时状态文件。"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{}")
            yield f.name

    @pytest.mark.asyncio
    async def test_register_device(self, temp_state_file):
        """测试注册设备。"""
        recovery = DeviceConnectionRecovery(state_file=temp_state_file)

        connect_func = AsyncMock(return_value=True)
        disconnect_func = AsyncMock(return_value=True)

        recovery.register_device(
            "device_01",
            connect_func,
            disconnect_func,
        )

        assert "device_01" in recovery._connect_funcs
        assert "device_01" in recovery._disconnect_funcs
        assert "device_01" in recovery._device_states

    @pytest.mark.asyncio
    async def test_connect_device_success(self, temp_state_file):
        """测试连接设备成功。"""
        recovery = DeviceConnectionRecovery(state_file=temp_state_file)

        connect_func = AsyncMock(return_value=True)
        recovery.register_device("device_01", connect_func)

        result = await recovery.connect_device("device_01")

        assert result is True
        state = recovery.get_device_state("device_01")
        assert state["connected"] is True
        assert state["state"] == RecoveryState.RECOVERED.value

    @pytest.mark.asyncio
    async def test_connect_device_failure(self, temp_state_file):
        """测试连接设备失败。"""
        recovery = DeviceConnectionRecovery(
            state_file=temp_state_file,
            default_config=RetryConfig(max_retries=2, initial_delay=0.05),
        )

        connect_func = AsyncMock(side_effect=ConnectionError("Failed"))
        recovery.register_device("device_01", connect_func)

        result = await recovery.connect_device("device_01")

        assert result is False
        state = recovery.get_device_state("device_01")
        assert state["connected"] is False
        assert state["state"] == RecoveryState.EXHAUSTED.value

    @pytest.mark.asyncio
    async def test_disconnect_device(self, temp_state_file):
        """测试断开设备连接。"""
        recovery = DeviceConnectionRecovery(state_file=temp_state_file)

        connect_func = AsyncMock(return_value=True)
        disconnect_func = AsyncMock(return_value=True)
        recovery.register_device("device_01", connect_func, disconnect_func)

        # 先连接
        await recovery.connect_device("device_01")

        # 再断开
        result = await recovery.disconnect_device("device_01")

        assert result is True
        state = recovery.get_device_state("device_01")
        assert state["connected"] is False

    @pytest.mark.asyncio
    async def test_unregister_device(self, temp_state_file):
        """测试注销设备。"""
        recovery = DeviceConnectionRecovery(state_file=temp_state_file)

        connect_func = AsyncMock(return_value=True)
        recovery.register_device("device_01", connect_func)

        recovery.unregister_device("device_01")

        assert "device_01" not in recovery._connect_funcs
        assert "device_01" not in recovery._device_states

    @pytest.mark.asyncio
    async def test_get_all_states(self, temp_state_file):
        """测试获取所有设备状态。"""
        recovery = DeviceConnectionRecovery(state_file=temp_state_file)

        for i in range(3):
            connect_func = AsyncMock(return_value=True)
            recovery.register_device(f"device_{i:02d}", connect_func)

        states = recovery.get_all_states()

        assert len(states) == 3
        assert "device_00" in states
        assert "device_01" in states
        assert "device_02" in states


class TestDeviceConnectionRecoveryLoop:
    """设备连接恢复循环测试。"""

    @pytest.fixture
    def temp_state_file(self):
        """创建临时状态文件。"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{}")
            yield f.name

    @pytest.mark.asyncio
    async def test_recovery_loop_reconnects(self, temp_state_file):
        """测试恢复循环重新连接。"""
        recovery = DeviceConnectionRecovery(
            state_file=temp_state_file,
            default_config=RetryConfig(max_retries=2, initial_delay=0.05),
        )

        connect_count = 0

        async def connect_func():
            nonlocal connect_count
            connect_count += 1
            return True

        recovery.register_device("device_01", connect_func)

        # 启动恢复循环
        recovery.start_recovery("device_01")

        # 等待连接
        await asyncio.sleep(0.3)

        # 停止恢复循环
        await recovery.stop_recovery("device_01")

        assert connect_count >= 1

    @pytest.mark.asyncio
    async def test_recovery_loop_with_health_check(self, temp_state_file):
        """测试带健康检查的恢复循环。"""
        recovery = DeviceConnectionRecovery(
            state_file=temp_state_file,
            default_config=RetryConfig(max_retries=2, initial_delay=0.05),
        )

        connect_count = 0
        health_check_count = 0

        async def connect_func():
            nonlocal connect_count
            connect_count += 1
            return True

        async def health_check_func():
            nonlocal health_check_count
            health_check_count += 1
            return health_check_count < 3  # 前两次健康，第三次不健康

        recovery.register_device(
            "device_01",
            connect_func,
            health_check_func=health_check_func,
        )

        # 启动恢复循环
        recovery.start_recovery("device_01")

        # 等待健康检查触发
        await asyncio.sleep(0.5)

        # 停止恢复循环
        await recovery.stop_recovery("device_01")

        assert health_check_count >= 1


class TestDeviceConnectionStatePersistence:
    """设备连接状态持久化测试。"""

    @pytest.mark.asyncio
    async def test_state_persistence(self):
        """测试状态持久化。"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            state_file = f.name

        # 创建恢复管理器并连接设备
        recovery1 = DeviceConnectionRecovery(
            state_file=state_file,
            default_config=RetryConfig(max_retries=1, initial_delay=0.01),
        )

        connect_func = AsyncMock(return_value=True)
        recovery1.register_device("device_01", connect_func)
        await recovery1.connect_device("device_01")

        # 创建新的恢复管理器加载状态
        recovery2 = DeviceConnectionRecovery(state_file=state_file)

        state = recovery2.get_device_state("device_01")

        assert state is not None
        assert state["device_id"] == "device_01"

        # 清理
        Path(state_file).unlink(missing_ok=True)


class TestDeviceConnectionErrorScenarios:
    """设备连接错误场景测试。"""

    @pytest.fixture
    def temp_state_file(self):
        """创建临时状态文件。"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{}")
            yield f.name

    @pytest.mark.asyncio
    async def test_connect_unregistered_device(self, temp_state_file):
        """测试连接未注册设备。"""
        recovery = DeviceConnectionRecovery(state_file=temp_state_file)

        result = await recovery.connect_device("unknown_device")

        assert result is False

    @pytest.mark.asyncio
    async def test_disconnect_with_error(self, temp_state_file):
        """测试断开连接时出错。"""
        recovery = DeviceConnectionRecovery(state_file=temp_state_file)

        async def connect_func():
            return True

        async def disconnect_func():
            raise RuntimeError("Disconnect error")

        recovery.register_device("device_01", connect_func, disconnect_func)
        await recovery.connect_device("device_01")

        # 应该不会抛出异常
        result = await recovery.disconnect_device("device_01")

        assert result is True

    @pytest.mark.asyncio
    async def test_concurrent_connect_requests(self, temp_state_file):
        """测试并发连接请求。"""
        recovery = DeviceConnectionRecovery(
            state_file=temp_state_file,
            default_config=RetryConfig(max_retries=1, initial_delay=0.01),
        )

        connect_count = 0

        async def slow_connect():
            nonlocal connect_count
            connect_count += 1
            await asyncio.sleep(0.1)
            return True

        recovery.register_device("device_01", slow_connect)

        # 并发连接
        results = await asyncio.gather(
            recovery.connect_device("device_01"),
            recovery.connect_device("device_01"),
            recovery.connect_device("device_01"),
        )

        # 所有请求应该返回成功
        assert all(results)


class TestDeviceConnectionMultipleDevices:
    """多设备连接测试。"""

    @pytest.fixture
    def temp_state_file(self):
        """创建临时状态文件。"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{}")
            yield f.name

    @pytest.mark.asyncio
    async def test_connect_multiple_devices(self, temp_state_file):
        """测试连接多个设备。"""
        recovery = DeviceConnectionRecovery(state_file=temp_state_file)

        devices = {}
        for i in range(5):
            device = MockDevice(f"device_{i:02d}", {})
            devices[f"device_{i:02d}"] = device
            recovery.register_device(
                f"device_{i:02d}",
                device.connect,
                device.disconnect,
            )

        # 并发连接所有设备
        results = await asyncio.gather(
            *[recovery.connect_device(device_id) for device_id in devices.keys()]
        )

        assert all(results)

        # 验证所有设备状态
        for device_id in devices.keys():
            state = recovery.get_device_state(device_id)
            assert state["connected"] is True

    @pytest.mark.asyncio
    async def test_partial_device_failure(self, temp_state_file):
        """测试部分设备连接失败。"""
        recovery = DeviceConnectionRecovery(
            state_file=temp_state_file,
            default_config=RetryConfig(max_retries=1, initial_delay=0.01),
        )

        # 注册成功和失败的设备
        for i in range(3):
            device = MockDevice(f"device_{i:02d}", {})
            recovery.register_device(f"device_{i:02d}", device.connect, device.disconnect)

        # 注册一个会失败的设备
        fail_device = MockDevice("device_fail", {}, fail_on_connect=True)
        recovery.register_device("device_fail", fail_device.connect, fail_device.disconnect)

        # 并发连接
        results = await asyncio.gather(
            recovery.connect_device("device_00"),
            recovery.connect_device("device_01"),
            recovery.connect_device("device_02"),
            recovery.connect_device("device_fail"),
        )

        assert results[0] is True
        assert results[1] is True
        assert results[2] is True
        assert results[3] is False


class TestRetryConfigStrategies:
    """重试策略测试。"""

    def test_exponential_backoff_calculation(self):
        """测试指数退避计算。"""
        config = RetryConfig(
            initial_delay=1.0,
            max_delay=100.0,
            backoff_factor=2.0,
            strategy=RecoveryStrategy.EXPONENTIAL_BACKOFF,
            jitter=False,
        )

        # 验证退避时间
        assert config.calculate_delay(1) == 1.0
        assert config.calculate_delay(2) == 2.0
        assert config.calculate_delay(3) == 4.0
        assert config.calculate_delay(4) == 8.0

    def test_linear_backoff_calculation(self):
        """测试线性退避计算。"""
        config = RetryConfig(
            initial_delay=1.0,
            max_delay=100.0,
            strategy=RecoveryStrategy.LINEAR_BACKOFF,
            jitter=False,
        )

        assert config.calculate_delay(1) == 1.0
        assert config.calculate_delay(2) == 2.0
        assert config.calculate_delay(3) == 3.0

    def test_fixed_interval_calculation(self):
        """测试固定间隔计算。"""
        config = RetryConfig(
            initial_delay=2.0,
            strategy=RecoveryStrategy.FIXED_INTERVAL,
            jitter=False,
        )

        assert config.calculate_delay(1) == 2.0
        assert config.calculate_delay(2) == 2.0
        assert config.calculate_delay(10) == 2.0

    def test_immediate_strategy(self):
        """测试立即重试策略。"""
        config = RetryConfig(strategy=RecoveryStrategy.IMMEDIATE)

        assert config.calculate_delay(1) == 0.0
        assert config.calculate_delay(10) == 0.0

    def test_max_delay_limit(self):
        """测试最大延迟限制。"""
        config = RetryConfig(
            initial_delay=10.0,
            max_delay=50.0,
            backoff_factor=2.0,
            strategy=RecoveryStrategy.EXPONENTIAL_BACKOFF,
            jitter=False,
        )

        # 第4次重试应该是80，但被限制为50
        assert config.calculate_delay(4) == 50.0

    def test_jitter_adds_randomness(self):
        """测试抖动添加随机性。"""
        config = RetryConfig(
            initial_delay=10.0,
            jitter=True,
        )

        # 多次计算，结果应该有变化
        delays = [config.calculate_delay(1) for _ in range(10)]

        # 不应该所有值都相同
        assert len(set(delays)) > 1


class TestDeviceConnectionIntegrationWithRealComponents:
    """与真实组件的集成测试。"""

    @pytest.mark.asyncio
    async def test_integration_with_dm2c_driver(self):
        """测试与DM2C驱动集成。"""
        from core.dm2c_driver import LeadshineDM2C

        # 使用仿真模式
        driver = LeadshineDM2C(
            "stepper_test",
            {"port": "COM_TEST", "slave_id": 1, "steps_per_mm": 1600},
            simulation=True,
        )

        # 连接
        result = await driver.connect()
        assert result is True
        assert driver.status != DeviceStatus.DISCONNECTED

        # 读取状态
        status = await driver.read_status()
        assert "status" in status

        # 断开
        result = await driver.disconnect()
        assert result is True

    @pytest.mark.asyncio
    async def test_integration_with_electromagnet(self):
        """测试与电磁铁驱动集成。"""
        from core.electromagnet_driver import ElectromagnetDriver

        driver = ElectromagnetDriver(
            "electromagnet_test",
            {"simulation": True, "max_current": 10.0},
        )

        # 连接
        result = await driver.connect()
        assert result is True

        # 读取状态
        status = await driver.read_status()
        assert "connected" in status

        # 断开
        result = await driver.disconnect()
        assert result is True

    @pytest.mark.asyncio
    async def test_integration_with_temperature_controller(self):
        """测试与温控系统集成。"""
        from core.temperature_controller import TemperatureController

        controller = TemperatureController(
            "temp_test",
            {"simulation": True, "pid_params": {"kp": 1.0, "ki": 0.1, "kd": 0.01}},
        )

        # 连接
        result = await controller.connect()
        assert result is True

        # 读取状态
        status = await controller.read_status()
        assert "connected" in status

        # 断开
        result = await controller.disconnect()
        assert result is True
