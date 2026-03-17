"""
抽象基类单元测试

文件名: test_abstract.py
路径: backend/tests/unit/core/
功能: 测试 AbstractDevice 和 AbstractStepper 抽象基类
作者: CAUC-SEP Team
创建日期: 2026-03-16
依赖: pytest, pytest-asyncio

测试内容：
- TestDeviceStatus: 设备状态枚举测试
- TestSoftwareLimitConfig: 软件限位配置测试
- TestAbstractDevice: 抽象设备基类测试
- TestAbstractStepper: 抽象步进电机测试
"""

import pytest

from core.abstract import AbstractDevice, AbstractStepper, DeviceStatus, SoftwareLimitConfig


# ==================== 测试用 Mock 类 ====================


class MockDevice(AbstractDevice):
    """测试用模拟设备。

    实现 AbstractDevice 的所有抽象方法用于测试。
    """

    async def connect(self) -> bool:
        """连接设备。"""
        self.status = DeviceStatus.CONNECTING
        self.status = DeviceStatus.READY
        return True

    async def disconnect(self) -> bool:
        """断开设备。"""
        self.status = DeviceStatus.DISCONNECTED
        return True

    async def read_status(self) -> dict:
        """读取状态。"""
        return {"status": self.status.value, "connected": self.is_connected}


class MockStepper(AbstractStepper):
    """测试用模拟步进电机。

    实现 AbstractStepper 的所有抽象方法用于测试。
    """

    async def connect(self) -> bool:
        """连接设备。"""
        self.status = DeviceStatus.READY
        return True

    async def disconnect(self) -> bool:
        """断开设备。"""
        self.status = DeviceStatus.DISCONNECTED
        return True

    async def read_status(self) -> dict:
        """读取状态。"""
        return {"status": self.status.value}

    async def move_abs(self, position: float, speed: float, accel: float, decel: float) -> bool:
        """绝对定位。"""
        if not self.check_position_limit(position):
            raise ValueError(f"位置 {position} 超出限位范围")
        self.status = DeviceStatus.BUSY
        self.status = DeviceStatus.READY
        return True

    async def move_rel(self, distance: float, speed: float, accel: float, decel: float) -> bool:
        """相对定位。"""
        return True

    async def jog(self, direction: int, speed: float) -> bool:
        """JOG点动。"""
        return True

    async def home(self, mode: str = "origin") -> bool:
        """回零。"""
        return True

    async def read_position(self) -> dict:
        """读取位置。"""
        return {"position_mm": 0.0, "position_steps": 1600}

    async def stop(self, emergency: bool = False) -> bool:
        """停止。"""
        if emergency:
            self.status = DeviceStatus.EMERGENCY_STOP
        return True


# ==================== DeviceStatus 测试 ====================


class TestDeviceStatus:
    """DeviceStatus 枚举测试。"""

    def test_status_values(self):
        """测试状态枚举值。"""
        assert DeviceStatus.DISCONNECTED.value == "disconnected"
        assert DeviceStatus.CONNECTING.value == "connecting"
        assert DeviceStatus.READY.value == "ready"
        assert DeviceStatus.BUSY.value == "busy"
        assert DeviceStatus.ERROR.value == "error"
        assert DeviceStatus.EMERGENCY_STOP.value == "emergency_stop"

    def test_status_count(self):
        """测试状态枚举数量。"""
        assert len(DeviceStatus) == 6

    def test_status_comparison(self):
        """测试状态枚举比较。"""
        assert DeviceStatus.READY != DeviceStatus.ERROR
        assert DeviceStatus.DISCONNECTED == DeviceStatus.DISCONNECTED

    def test_valid_transitions_mapping(self):
        """测试合法状态转换映射。"""
        transitions = DeviceStatus.get_valid_transitions()

        # 验证所有状态都有转换映射
        assert len(transitions) == 6
        assert DeviceStatus.DISCONNECTED in transitions
        assert DeviceStatus.CONNECTING in transitions
        assert DeviceStatus.READY in transitions
        assert DeviceStatus.BUSY in transitions
        assert DeviceStatus.ERROR in transitions
        assert DeviceStatus.EMERGENCY_STOP in transitions

    def test_can_transition_to_valid(self):
        """测试合法状态转换。"""
        # DISCONNECTED -> CONNECTING
        assert DeviceStatus.DISCONNECTED.can_transition_to(DeviceStatus.CONNECTING)

        # CONNECTING -> READY
        assert DeviceStatus.CONNECTING.can_transition_to(DeviceStatus.READY)

        # READY -> BUSY
        assert DeviceStatus.READY.can_transition_to(DeviceStatus.BUSY)

        # BUSY -> READY
        assert DeviceStatus.BUSY.can_transition_to(DeviceStatus.READY)

        # ERROR -> READY (复位后)
        assert DeviceStatus.ERROR.can_transition_to(DeviceStatus.READY)

    def test_can_transition_to_invalid(self):
        """测试非法状态转换。"""
        # DISCONNECTED 不能直接转换到 READY
        assert not DeviceStatus.DISCONNECTED.can_transition_to(DeviceStatus.READY)

        # DISCONNECTED 不能直接转换到 BUSY
        assert not DeviceStatus.DISCONNECTED.can_transition_to(DeviceStatus.BUSY)

        # READY 不能转换到 CONNECTING
        assert not DeviceStatus.READY.can_transition_to(DeviceStatus.CONNECTING)

    def test_error_and_emergency_transitions(self):
        """测试错误和急停状态转换。"""
        # READY 可以转换到 ERROR
        assert DeviceStatus.READY.can_transition_to(DeviceStatus.ERROR)

        # READY 可以转换到 EMERGENCY_STOP
        assert DeviceStatus.READY.can_transition_to(DeviceStatus.EMERGENCY_STOP)

        # BUSY 可以转换到 ERROR
        assert DeviceStatus.BUSY.can_transition_to(DeviceStatus.ERROR)

        # BUSY 可以转换到 EMERGENCY_STOP
        assert DeviceStatus.BUSY.can_transition_to(DeviceStatus.EMERGENCY_STOP)

        # ERROR 可以转换到 DISCONNECTED
        assert DeviceStatus.ERROR.can_transition_to(DeviceStatus.DISCONNECTED)

        # EMERGENCY_STOP 可以转换到 DISCONNECTED
        assert DeviceStatus.EMERGENCY_STOP.can_transition_to(DeviceStatus.DISCONNECTED)


# ==================== SoftwareLimitConfig 测试 ====================


class TestSoftwareLimitConfig:
    """SoftwareLimitConfig 测试。"""

    def test_default_config(self):
        """测试默认配置。"""
        config = SoftwareLimitConfig()
        assert config.positive_limit == 100.0
        assert config.negative_limit == -100.0
        assert config.enable is True

    def test_custom_config(self):
        """测试自定义配置。"""
        config = SoftwareLimitConfig(positive_limit=50.0, negative_limit=-50.0, enable=False)
        assert config.positive_limit == 50.0
        assert config.negative_limit == -50.0
        assert config.enable is False

    def test_invalid_config_negative_greater_than_positive(self):
        """测试无效配置：负向限位大于正向限位。"""
        with pytest.raises(ValueError, match="负向限位.*必须小于正向限位"):
            SoftwareLimitConfig(positive_limit=50.0, negative_limit=100.0)

    def test_invalid_config_equal_limits(self):
        """测试无效配置：正负限位相等。"""
        with pytest.raises(ValueError, match="负向限位.*必须小于正向限位"):
            SoftwareLimitConfig(positive_limit=50.0, negative_limit=50.0)

    def test_nan_limits(self):
        """测试 NaN 限位。"""
        with pytest.raises(ValueError, match="正向限位不能是NaN或无穷大"):
            SoftwareLimitConfig(positive_limit=float("nan"), negative_limit=-100.0)

        with pytest.raises(ValueError, match="负向限位不能是NaN或无穷大"):
            SoftwareLimitConfig(positive_limit=100.0, negative_limit=float("nan"))

    def test_infinity_limits(self):
        """测试无穷大限位。"""
        with pytest.raises(ValueError, match="正向限位不能是NaN或无穷大"):
            SoftwareLimitConfig(positive_limit=float("inf"), negative_limit=-100.0)

        with pytest.raises(ValueError, match="负向限位不能是NaN或无穷大"):
            SoftwareLimitConfig(positive_limit=100.0, negative_limit=float("-inf"))

    def test_is_within_limits_enabled(self):
        """测试启用限位检查。"""
        config = SoftwareLimitConfig(positive_limit=50.0, negative_limit=-50.0, enable=True)

        assert config.is_within_limits(0.0) is True
        assert config.is_within_limits(50.0) is True
        assert config.is_within_limits(-50.0) is True
        assert config.is_within_limits(51.0) is False
        assert config.is_within_limits(-51.0) is False

    def test_is_within_limits_disabled(self):
        """测试禁用限位检查。"""
        config = SoftwareLimitConfig(positive_limit=50.0, negative_limit=-50.0, enable=False)

        assert config.is_within_limits(0.0) is True
        assert config.is_within_limits(1000.0) is True
        assert config.is_within_limits(-1000.0) is True

    def test_clamp_position(self):
        """测试位置限制功能。"""
        config = SoftwareLimitConfig(positive_limit=50.0, negative_limit=-50.0, enable=True)

        # 在范围内的位置不变
        assert config.clamp_position(0.0) == 0.0
        assert config.clamp_position(25.0) == 25.0

        # 超出范围的位置被限制
        assert config.clamp_position(100.0) == 50.0
        assert config.clamp_position(-100.0) == -50.0

    def test_clamp_position_disabled(self):
        """测试禁用限位时的位置限制。"""
        config = SoftwareLimitConfig(positive_limit=50.0, negative_limit=-50.0, enable=False)

        # 禁用限位时不限制
        assert config.clamp_position(100.0) == 100.0
        assert config.clamp_position(-100.0) == -100.0

    def test_get_range(self):
        """测试获取限位范围。"""
        config = SoftwareLimitConfig(positive_limit=100.0, negative_limit=-100.0)
        assert config.get_range() == 200.0

    def test_to_dict(self):
        """测试序列化为字典。"""
        config = SoftwareLimitConfig(positive_limit=50.0, negative_limit=-50.0, enable=False)
        data = config.to_dict()

        assert data["positive_limit"] == 50.0
        assert data["negative_limit"] == -50.0
        assert data["enable"] is False

    def test_from_dict(self):
        """测试从字典反序列化。"""
        data = {"positive_limit": 75.0, "negative_limit": -75.0, "enable": False}
        config = SoftwareLimitConfig.from_dict(data)

        assert config.positive_limit == 75.0
        assert config.negative_limit == -75.0
        assert config.enable is False

    def test_from_dict_with_defaults(self):
        """测试从字典反序列化（使用默认值）。"""
        config = SoftwareLimitConfig.from_dict({})

        assert config.positive_limit == 100.0
        assert config.negative_limit == -100.0
        assert config.enable is True

    def test_from_dict_invalid_type(self):
        """测试从无效类型反序列化。"""
        with pytest.raises(ValueError, match="配置数据必须是字典类型"):
            SoftwareLimitConfig.from_dict("invalid")

    def test_repr(self):
        """测试字符串表示。"""
        config = SoftwareLimitConfig(positive_limit=50.0, negative_limit=-50.0, enable=True)
        repr_str = repr(config)

        assert "SoftwareLimitConfig" in repr_str
        assert "positive_limit=50.0" in repr_str
        assert "negative_limit=-50.0" in repr_str

    def test_equality(self):
        """测试相等性比较。"""
        config1 = SoftwareLimitConfig(positive_limit=50.0, negative_limit=-50.0, enable=True)
        config2 = SoftwareLimitConfig(positive_limit=50.0, negative_limit=-50.0, enable=True)
        config3 = SoftwareLimitConfig(positive_limit=100.0, negative_limit=-100.0, enable=True)

        assert config1 == config2
        assert config1 != config3
        assert config1 != "not a config"

    def test_property_setters_validation(self):
        """测试属性设置器的验证。"""
        config = SoftwareLimitConfig()

        # 测试正向限位设置器
        with pytest.raises(ValueError, match="正向限位必须是数值类型"):
            config.positive_limit = "invalid"

        # 测试负向限位设置器
        with pytest.raises(ValueError, match="负向限位必须是数值类型"):
            config.negative_limit = "invalid"

        # 测试 enable 设置器
        with pytest.raises(ValueError, match="enable必须是布尔类型"):
            config.enable = "invalid"


# ==================== AbstractDevice 测试 ====================


class TestAbstractDevice:
    """AbstractDevice 测试。"""

    def test_device_initialization(self):
        """测试设备初始化。"""
        device = MockDevice("test_device", {"port": "COM1"})
        assert device.device_id == "test_device"
        assert device.status == DeviceStatus.DISCONNECTED
        assert device.is_connected is False

    @pytest.mark.asyncio
    async def test_device_connect(self):
        """测试设备连接。"""
        device = MockDevice("test_device", {})
        result = await device.connect()
        assert result is True
        assert device.status == DeviceStatus.READY
        assert device.is_connected is True

    @pytest.mark.asyncio
    async def test_device_disconnect(self):
        """测试设备断开。"""
        device = MockDevice("test_device", {})
        await device.connect()
        result = await device.disconnect()
        assert result is True
        assert device.status == DeviceStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """测试错误处理。"""
        device = MockDevice("test_device", {})
        device.set_error("Test error")
        assert device.status == DeviceStatus.ERROR
        assert device.last_error == "Test error"

        device.clear_error()
        assert device.last_error is None

    def test_is_ready_property(self):
        """测试 is_ready 属性。"""
        device = MockDevice("test_device", {})
        assert device.is_ready is False

        device.status = DeviceStatus.READY
        assert device.is_ready is True

    def test_is_busy_property(self):
        """测试 is_busy 属性。"""
        device = MockDevice("test_device", {})
        assert device.is_busy is False

        device.status = DeviceStatus.BUSY
        assert device.is_busy is True

    def test_is_error_property(self):
        """测试 is_error 属性。"""
        device = MockDevice("test_device", {})
        assert device.is_error is False

        device.status = DeviceStatus.ERROR
        assert device.is_error is True

    def test_is_emergency_stop_property(self):
        """测试 is_emergency_stop 属性。"""
        device = MockDevice("test_device", {})
        assert device.is_emergency_stop is False

        device.status = DeviceStatus.EMERGENCY_STOP
        assert device.is_emergency_stop is True

    def test_status_transition_warning(self, caplog):
        """测试非标准状态转换警告。"""
        import logging

        caplog.set_level(logging.WARNING)

        device = MockDevice("test_device", {})
        # DISCONNECTED -> READY 是非法转换
        device.status = DeviceStatus.READY

        # 应该有警告日志
        assert any("非标准状态转换" in record.message for record in caplog.records)

    def test_set_status_strict_valid(self):
        """测试严格模式下的合法状态转换。"""
        device = MockDevice("test_device", {})

        # DISCONNECTED -> CONNECTING 是合法的
        device.set_status_strict(DeviceStatus.CONNECTING)
        assert device.status == DeviceStatus.CONNECTING

        # CONNECTING -> READY 是合法的
        device.set_status_strict(DeviceStatus.READY)
        assert device.status == DeviceStatus.READY

    def test_set_status_strict_invalid(self):
        """测试严格模式下的非法状态转换。"""
        device = MockDevice("test_device", {})

        # DISCONNECTED -> READY 是非法的
        with pytest.raises(ValueError, match="非法状态转换"):
            device.set_status_strict(DeviceStatus.READY)

    @pytest.mark.asyncio
    async def test_reset_from_error(self):
        """测试从错误状态复位。"""
        device = MockDevice("test_device", {})
        device.set_error("Test error")

        result = await device.reset()

        assert result is True
        assert device.status == DeviceStatus.READY
        assert device.last_error is None

    @pytest.mark.asyncio
    async def test_reset_from_emergency_stop(self):
        """测试从急停状态复位。"""
        device = MockDevice("test_device", {})
        device.status = DeviceStatus.EMERGENCY_STOP

        result = await device.reset()

        assert result is True
        assert device.status == DeviceStatus.READY

    @pytest.mark.asyncio
    async def test_reset_from_non_error_state(self):
        """测试从非错误状态复位（应该失败）。"""
        device = MockDevice("test_device", {})
        device.status = DeviceStatus.READY

        result = await device.reset()

        assert result is False
        assert device.status == DeviceStatus.READY

    def test_get_status_info(self):
        """测试获取状态信息。"""
        device = MockDevice("test_device", {"port": "COM1"})
        device.status = DeviceStatus.READY

        info = device.get_status_info()

        assert info["device_id"] == "test_device"
        assert info["status"] == "ready"
        assert info["is_connected"] is True
        assert info["is_ready"] is True
        assert info["is_busy"] is False
        assert info["is_error"] is False
        assert info["is_emergency_stop"] is False

    def test_cannot_instantiate_abstract(self):
        """测试不能实例化抽象类。"""
        with pytest.raises(TypeError):
            AbstractDevice("test", {})


# ==================== AbstractStepper 测试 ====================


class TestAbstractStepper:
    """AbstractStepper 测试。"""

    @pytest.mark.asyncio
    async def test_stepper_initialization(self):
        """测试步进电机初始化。"""
        stepper = MockStepper("test_stepper", {})
        assert stepper.limit_config is not None
        assert stepper.limit_config.positive_limit == 100.0

    @pytest.mark.asyncio
    async def test_set_limits(self):
        """测试设置限位。"""
        stepper = MockStepper("test_stepper", {})
        stepper.set_limits(50.0, -50.0)
        assert stepper.limit_config.positive_limit == 50.0
        assert stepper.limit_config.negative_limit == -50.0

    @pytest.mark.asyncio
    async def test_position_limit_check(self):
        """测试位置限位检查。"""
        stepper = MockStepper("test_stepper", {})
        stepper.set_limits(50.0, -50.0)

        assert stepper.check_position_limit(0.0) is True
        assert stepper.check_position_limit(50.0) is True
        assert stepper.check_position_limit(51.0) is False

    @pytest.mark.asyncio
    async def test_move_with_limit_check(self):
        """测试带限位检查的移动。"""
        stepper = MockStepper("test_stepper", {})
        stepper.set_limits(50.0, -50.0)
        await stepper.connect()

        # 正常移动
        result = await stepper.move_abs(10.0, 10.0, 100.0, 100.0)
        assert result is True

        # 超出限位
        with pytest.raises(ValueError):
            await stepper.move_abs(100.0, 10.0, 100.0, 100.0)

    @pytest.mark.asyncio
    async def test_emergency_stop(self):
        """测试急停。"""
        stepper = MockStepper("test_stepper", {})
        await stepper.connect()

        result = await stepper.stop(emergency=True)
        assert result is True
        assert stepper.status == DeviceStatus.EMERGENCY_STOP
        assert stepper.is_emergency_stop is True

    def test_inheritance(self):
        """测试继承关系。"""
        stepper = MockStepper("test_stepper", {})

        assert isinstance(stepper, AbstractDevice)
        assert isinstance(stepper, AbstractStepper)

    def test_default_limit_config(self):
        """测试默认软件限位配置。"""
        stepper = MockStepper("test_stepper", {})

        assert stepper.limit_config is not None
        assert stepper.limit_config.positive_limit == 100.0
        assert stepper.limit_config.negative_limit == -100.0
        assert stepper.limit_config.enable is True

    def test_set_limit_config(self):
        """测试设置软件限位配置。"""
        stepper = MockStepper("test_stepper", {})
        new_config = SoftwareLimitConfig(positive_limit=50.0, negative_limit=-50.0, enable=False)

        stepper.limit_config = new_config

        assert stepper.limit_config.positive_limit == 50.0
        assert stepper.limit_config.negative_limit == -50.0
        assert stepper.limit_config.enable is False

    def test_set_limit_config_invalid_type(self):
        """测试设置无效类型的限位配置。"""
        stepper = MockStepper("test_stepper", {})

        with pytest.raises(ValueError, match="limit_config必须是SoftwareLimitConfig类型"):
            stepper.limit_config = "invalid"

    @pytest.mark.asyncio
    async def test_all_abstract_methods(self):
        """测试所有抽象方法实现。"""
        stepper = MockStepper("test_stepper", {})

        assert await stepper.connect() is True
        assert await stepper.disconnect() is True
        assert await stepper.move_abs(10.0, 5.0, 1000.0, 1000.0) is True
        assert await stepper.move_rel(5.0, 5.0, 1000.0, 1000.0) is True
        assert await stepper.jog(1, 5.0) is True
        assert await stepper.home() is True
        assert await stepper.read_position() == {"position_mm": 0.0, "position_steps": 1600}
        assert await stepper.stop() is True
        assert await stepper.stop(emergency=True) is True

    @pytest.mark.asyncio
    async def test_wait_for_motion_complete(self):
        """测试等待运动完成。"""
        stepper = MockStepper("test_stepper", {})
        await stepper.connect()

        # 模拟运动完成
        result = await stepper.wait_for_motion_complete(timeout=1.0)
        assert result is True  # 因为状态是 READY，不是 BUSY

    @pytest.mark.asyncio
    async def test_wait_for_motion_complete_timeout(self):
        """测试等待运动完成超时。"""
        stepper = MockStepper("test_stepper", {})
        await stepper.connect()

        # 设置为 BUSY 状态模拟运动中
        stepper.status = DeviceStatus.BUSY

        # 应该超时，因为状态一直是 BUSY
        result = await stepper.wait_for_motion_complete(timeout=0.2)
        assert result is False

    def test_get_position_info(self):
        """测试获取位置信息。"""
        stepper = MockStepper("test_stepper", {})
        stepper.set_limits(positive=50.0, negative=-50.0)

        info = stepper.get_position_info()

        assert info["device_id"] == "test_stepper"
        assert "limits" in info
        assert info["limits"]["positive_limit"] == 50.0
        assert info["limits"]["negative_limit"] == -50.0

    def test_cannot_instantiate_abstract(self):
        """测试不能实例化抽象类。"""
        with pytest.raises(TypeError):
            AbstractStepper("test", {})


# ==================== 抽象方法签名测试 ====================


class TestAbstractMethodsSignature:
    """测试抽象方法签名。"""

    def test_abstract_device_methods(self):
        """测试 AbstractDevice 抽象方法签名。"""
        import inspect

        assert hasattr(AbstractDevice, "connect")
        assert hasattr(AbstractDevice, "disconnect")
        assert hasattr(AbstractDevice, "read_status")

        connect_sig = inspect.signature(AbstractDevice.connect)
        assert "self" in connect_sig.parameters

        disconnect_sig = inspect.signature(AbstractDevice.disconnect)
        assert "self" in disconnect_sig.parameters

    def test_abstract_stepper_methods(self):
        """测试 AbstractStepper 抽象方法签名。"""
        import inspect

        methods = ["move_abs", "move_rel", "jog", "home", "read_position", "stop"]

        for method_name in methods:
            assert hasattr(AbstractStepper, method_name)
            method = getattr(AbstractStepper, method_name)
            sig = inspect.signature(method)
            assert "self" in sig.parameters
