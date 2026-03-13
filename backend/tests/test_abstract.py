"""
测试硬件抽象层 (HAL)

测试内容：
- DeviceStatus枚举及状态转换
- SoftwareLimitConfig类
- AbstractDevice抽象类
- AbstractStepper抽象类
"""

import pytest

from core.abstract import AbstractDevice, AbstractStepper, DeviceStatus, SoftwareLimitConfig


class TestDeviceStatus:
    """测试设备状态枚举。"""

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


class TestSoftwareLimitConfig:
    """测试软件限位配置类。"""

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

    def test_is_within_limits_enabled(self):
        """测试启用限位检查。"""
        config = SoftwareLimitConfig(positive_limit=100.0, negative_limit=-100.0, enable=True)

        assert config.is_within_limits(0.0) is True
        assert config.is_within_limits(50.0) is True
        assert config.is_within_limits(100.0) is True
        assert config.is_within_limits(-50.0) is True
        assert config.is_within_limits(-100.0) is True

        assert config.is_within_limits(101.0) is False
        assert config.is_within_limits(-101.0) is False
        assert config.is_within_limits(150.0) is False

    def test_is_within_limits_disabled(self):
        """测试禁用限位检查。"""
        config = SoftwareLimitConfig(positive_limit=100.0, negative_limit=-100.0, enable=False)

        assert config.is_within_limits(0.0) is True
        assert config.is_within_limits(1000.0) is True
        assert config.is_within_limits(-1000.0) is True

    def test_boundary_values(self):
        """测试边界值。"""
        config = SoftwareLimitConfig(positive_limit=50.0, negative_limit=-50.0, enable=True)

        assert config.is_within_limits(50.0) is True
        assert config.is_within_limits(-50.0) is True
        assert config.is_within_limits(50.0001) is False
        assert config.is_within_limits(-50.0001) is False

    def test_zero_limits(self):
        """测试接近零的限位。"""
        # 注意：正负限位不能相等，负向限位必须小于正向限位
        config = SoftwareLimitConfig(positive_limit=0.001, negative_limit=-0.001, enable=True)

        assert config.is_within_limits(0.0) is True
        assert config.is_within_limits(0.001) is True
        assert config.is_within_limits(-0.001) is True
        assert config.is_within_limits(0.002) is False
        assert config.is_within_limits(-0.002) is False

    def test_equal_limits_raises_error(self):
        """测试相等限位应抛出错误。"""
        with pytest.raises(ValueError, match="负向限位.*必须小于正向限位"):
            SoftwareLimitConfig(positive_limit=0.0, negative_limit=0.0, enable=True)

    def test_invalid_limits_negative_greater_than_positive(self):
        """测试无效限位：负向限位大于等于正向限位。"""
        with pytest.raises(ValueError, match="负向限位.*必须小于正向限位"):
            SoftwareLimitConfig(positive_limit=50.0, negative_limit=100.0)

        with pytest.raises(ValueError, match="负向限位.*必须小于正向限位"):
            SoftwareLimitConfig(positive_limit=50.0, negative_limit=50.0)

    def test_nan_limits(self):
        """测试NaN限位。"""
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

    def test_property_setters_validation(self):
        """测试属性设置器的验证。"""
        config = SoftwareLimitConfig()

        # 测试正向限位设置器
        with pytest.raises(ValueError, match="正向限位必须是数值类型"):
            config.positive_limit = "invalid"

        # 测试负向限位设置器
        with pytest.raises(ValueError, match="负向限位必须是数值类型"):
            config.negative_limit = "invalid"

        # 测试enable设置器
        with pytest.raises(ValueError, match="enable必须是布尔类型"):
            config.enable = "invalid"

    def test_clamp_position(self):
        """测试位置限制功能。"""
        config = SoftwareLimitConfig(positive_limit=100.0, negative_limit=-100.0, enable=True)

        # 在范围内的位置不变
        assert config.clamp_position(50.0) == 50.0
        assert config.clamp_position(-50.0) == -50.0

        # 超出范围的位置被限制
        assert config.clamp_position(150.0) == 100.0
        assert config.clamp_position(-150.0) == -100.0

        # 禁用限位时不限制
        config.enable = False
        assert config.clamp_position(150.0) == 150.0

    def test_get_range(self):
        """测试获取限位范围。"""
        config = SoftwareLimitConfig(positive_limit=100.0, negative_limit=-100.0)
        assert config.get_range() == 200.0

        config2 = SoftwareLimitConfig(positive_limit=50.0, negative_limit=-50.0)
        assert config2.get_range() == 100.0

    def test_to_dict(self):
        """测试序列化为字典。"""
        config = SoftwareLimitConfig(positive_limit=50.0, negative_limit=-50.0, enable=True)
        data = config.to_dict()

        assert data["positive_limit"] == 50.0
        assert data["negative_limit"] == -50.0
        assert data["enable"] is True

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
        assert "enable=True" in repr_str

    def test_equality(self):
        """测试相等性比较。"""
        config1 = SoftwareLimitConfig(positive_limit=50.0, negative_limit=-50.0, enable=True)
        config2 = SoftwareLimitConfig(positive_limit=50.0, negative_limit=-50.0, enable=True)
        config3 = SoftwareLimitConfig(positive_limit=100.0, negative_limit=-100.0, enable=True)

        assert config1 == config2
        assert config1 != config3
        assert config1 != "not a config"


class ConcreteDevice(AbstractDevice):
    """具体设备实现类（用于测试）。"""

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


class TestAbstractDevice:
    """测试抽象设备基类。"""

    def test_initialization(self):
        """测试初始化。"""
        device = ConcreteDevice(device_id="test_device", config={"port": "COM1"})

        assert device.device_id == "test_device"
        assert device.config == {"port": "COM1"}
        assert device.status == DeviceStatus.DISCONNECTED
        assert device.last_error is None

    def test_status_property(self):
        """测试状态属性。"""
        device = ConcreteDevice(device_id="test_device", config={})

        assert device.status == DeviceStatus.DISCONNECTED

        device.status = DeviceStatus.READY
        assert device.status == DeviceStatus.READY

        device.status = DeviceStatus.ERROR
        assert device.status == DeviceStatus.ERROR

    def test_status_transition_warning(self, caplog):
        """测试非标准状态转换警告。"""
        import logging

        caplog.set_level(logging.WARNING)

        device = ConcreteDevice(device_id="test_device", config={})
        # DISCONNECTED -> READY 是非法转换
        device.status = DeviceStatus.READY

        # 应该有警告日志
        assert any("非标准状态转换" in record.message for record in caplog.records)

    def test_set_status_strict_valid(self):
        """测试严格模式下的合法状态转换。"""
        device = ConcreteDevice(device_id="test_device", config={})

        # DISCONNECTED -> CONNECTING 是合法的
        device.set_status_strict(DeviceStatus.CONNECTING)
        assert device.status == DeviceStatus.CONNECTING

        # CONNECTING -> READY 是合法的
        device.set_status_strict(DeviceStatus.READY)
        assert device.status == DeviceStatus.READY

    def test_set_status_strict_invalid(self):
        """测试严格模式下的非法状态转换。"""
        device = ConcreteDevice(device_id="test_device", config={})

        # DISCONNECTED -> READY 是非法的
        with pytest.raises(ValueError, match="非法状态转换"):
            device.set_status_strict(DeviceStatus.READY)

    def test_is_connected_property(self):
        """测试is_connected属性。"""
        device = ConcreteDevice(device_id="test_device", config={})

        assert device.is_connected is False

        device.status = DeviceStatus.READY
        assert device.is_connected is True

        device.status = DeviceStatus.BUSY
        assert device.is_connected is True

        device.status = DeviceStatus.ERROR
        assert device.is_connected is True

    def test_is_ready_property(self):
        """测试is_ready属性。"""
        device = ConcreteDevice(device_id="test_device", config={})

        assert device.is_ready is False

        device.status = DeviceStatus.READY
        assert device.is_ready is True

        device.status = DeviceStatus.BUSY
        assert device.is_ready is False

    def test_is_busy_property(self):
        """测试is_busy属性。"""
        device = ConcreteDevice(device_id="test_device", config={})

        assert device.is_busy is False

        device.status = DeviceStatus.BUSY
        assert device.is_busy is True

    def test_is_error_property(self):
        """测试is_error属性。"""
        device = ConcreteDevice(device_id="test_device", config={})

        assert device.is_error is False

        device.status = DeviceStatus.ERROR
        assert device.is_error is True

    def test_is_emergency_stop_property(self):
        """测试is_emergency_stop属性。"""
        device = ConcreteDevice(device_id="test_device", config={})

        assert device.is_emergency_stop is False

        device.status = DeviceStatus.EMERGENCY_STOP
        assert device.is_emergency_stop is True

    def test_last_error_property(self):
        """测试错误信息属性。"""
        device = ConcreteDevice(device_id="test_device", config={})

        assert device.last_error is None

        device._last_error = "Test error"
        assert device.last_error == "Test error"

    def test_set_error(self):
        """测试set_error方法。"""
        device = ConcreteDevice(device_id="test_device", config={})

        device.set_error("Connection failed")

        assert device.status == DeviceStatus.ERROR
        assert device.last_error == "Connection failed"

    def test_clear_error(self):
        """测试clear_error方法。"""
        device = ConcreteDevice(device_id="test_device", config={})
        device.set_error("Test error")

        device.clear_error()

        assert device.last_error is None
        # 状态不应该改变
        assert device.status == DeviceStatus.ERROR

    @pytest.mark.asyncio
    async def test_connect_implementation(self):
        """测试连接实现。"""
        device = ConcreteDevice(device_id="test_device", config={})

        result = await device.connect()
        assert result is True
        assert device.status == DeviceStatus.READY

    @pytest.mark.asyncio
    async def test_disconnect_implementation(self):
        """测试断开实现。"""
        device = ConcreteDevice(device_id="test_device", config={})
        device.status = DeviceStatus.READY

        result = await device.disconnect()
        assert result is True
        assert device.status == DeviceStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_read_status_implementation(self):
        """测试读取状态实现。"""
        device = ConcreteDevice(device_id="test_device", config={})
        device.status = DeviceStatus.READY

        status = await device.read_status()
        assert status["status"] == "ready"

    @pytest.mark.asyncio
    async def test_reset_from_error(self):
        """测试从错误状态复位。"""
        device = ConcreteDevice(device_id="test_device", config={})
        device.set_error("Test error")

        result = await device.reset()

        assert result is True
        assert device.status == DeviceStatus.READY
        assert device.last_error is None

    @pytest.mark.asyncio
    async def test_reset_from_emergency_stop(self):
        """测试从急停状态复位。"""
        device = ConcreteDevice(device_id="test_device", config={})
        device.status = DeviceStatus.EMERGENCY_STOP

        result = await device.reset()

        assert result is True
        assert device.status == DeviceStatus.READY

    @pytest.mark.asyncio
    async def test_reset_from_non_error_state(self):
        """测试从非错误状态复位（应该失败）。"""
        device = ConcreteDevice(device_id="test_device", config={})
        device.status = DeviceStatus.READY

        result = await device.reset()

        assert result is False
        assert device.status == DeviceStatus.READY

    def test_get_status_info(self):
        """测试获取状态信息。"""
        device = ConcreteDevice(device_id="test_device", config={"port": "COM1"})
        device.status = DeviceStatus.READY

        info = device.get_status_info()

        assert info["device_id"] == "test_device"
        assert info["status"] == "ready"
        assert info["is_connected"] is True
        assert info["is_ready"] is True
        assert info["is_busy"] is False
        assert info["is_error"] is False
        assert info["is_emergency_stop"] is False
        assert info["last_error"] is None


class ConcreteStepper(AbstractStepper):
    """具体步进电机实现类（用于测试）。"""

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
        return {"position_mm": 0.0}

    async def stop(self, emergency: bool = False) -> bool:
        """停止。"""
        return True


class TestAbstractStepper:
    """测试抽象步进电机接口。"""

    def test_inheritance(self):
        """测试继承关系。"""
        stepper = ConcreteStepper(device_id="test_stepper", config={})

        assert isinstance(stepper, AbstractDevice)
        assert isinstance(stepper, AbstractStepper)

    def test_initialization(self):
        """测试初始化。"""
        stepper = ConcreteStepper(device_id="test_stepper", config={"steps_per_mm": 1600})

        assert stepper.device_id == "test_stepper"
        assert stepper.config == {"steps_per_mm": 1600}
        assert stepper.status == DeviceStatus.DISCONNECTED

    def test_default_limit_config(self):
        """测试默认软件限位配置。"""
        stepper = ConcreteStepper(device_id="test_stepper", config={})

        assert stepper.limit_config is not None
        assert stepper.limit_config.positive_limit == 100.0
        assert stepper.limit_config.negative_limit == -100.0
        assert stepper.limit_config.enable is True

    def test_set_limit_config(self):
        """测试设置软件限位配置。"""
        stepper = ConcreteStepper(device_id="test_stepper", config={})
        new_config = SoftwareLimitConfig(positive_limit=50.0, negative_limit=-50.0, enable=False)

        stepper.limit_config = new_config

        assert stepper.limit_config.positive_limit == 50.0
        assert stepper.limit_config.negative_limit == -50.0
        assert stepper.limit_config.enable is False

    def test_set_limit_config_invalid_type(self):
        """测试设置无效类型的限位配置。"""
        stepper = ConcreteStepper(device_id="test_stepper", config={})

        with pytest.raises(ValueError, match="limit_config必须是SoftwareLimitConfig类型"):
            stepper.limit_config = "invalid"

    def test_set_limits_convenience_method(self):
        """测试便捷方法设置限位。"""
        stepper = ConcreteStepper(device_id="test_stepper", config={})

        stepper.set_limits(positive=75.0, negative=-75.0, enable=False)

        assert stepper.limit_config.positive_limit == 75.0
        assert stepper.limit_config.negative_limit == -75.0
        assert stepper.limit_config.enable is False

    def test_check_position_limit(self):
        """测试位置限位检查。"""
        stepper = ConcreteStepper(device_id="test_stepper", config={})
        stepper.set_limits(positive=100.0, negative=-100.0, enable=True)

        assert stepper.check_position_limit(50.0) is True
        assert stepper.check_position_limit(100.0) is True
        assert stepper.check_position_limit(-50.0) is True
        assert stepper.check_position_limit(150.0) is False
        assert stepper.check_position_limit(-150.0) is False

    @pytest.mark.asyncio
    async def test_all_abstract_methods(self):
        """测试所有抽象方法实现。"""
        stepper = ConcreteStepper(device_id="test_stepper", config={})

        assert await stepper.connect() is True
        assert await stepper.disconnect() is True
        assert await stepper.move_abs(10.0, 5.0, 1000.0, 1000.0) is True
        assert await stepper.move_rel(5.0, 5.0, 1000.0, 1000.0) is True
        assert await stepper.jog(1, 5.0) is True
        assert await stepper.home() is True
        assert await stepper.read_position() == {"position_mm": 0.0}
        assert await stepper.stop() is True
        assert await stepper.stop(emergency=True) is True

    @pytest.mark.asyncio
    async def test_wait_for_motion_complete(self):
        """测试等待运动完成。"""
        stepper = ConcreteStepper(device_id="test_stepper", config={})
        await stepper.connect()

        # 模拟运动完成
        result = await stepper.wait_for_motion_complete(timeout=1.0)
        assert result is True  # 因为状态是READY，不是BUSY

    @pytest.mark.asyncio
    async def test_wait_for_motion_complete_timeout(self):
        """测试等待运动完成超时。"""
        stepper = ConcreteStepper(device_id="test_stepper", config={})
        await stepper.connect()

        # 设置为BUSY状态模拟运动中
        stepper.status = DeviceStatus.BUSY

        # 应该超时，因为状态一直是BUSY
        result = await stepper.wait_for_motion_complete(timeout=0.2)
        assert result is False

    def test_get_position_info(self):
        """测试获取位置信息。"""
        stepper = ConcreteStepper(device_id="test_stepper", config={})
        stepper.set_limits(positive=50.0, negative=-50.0)

        info = stepper.get_position_info()

        assert info["device_id"] == "test_stepper"
        assert "limits" in info
        assert info["limits"]["positive_limit"] == 50.0
        assert info["limits"]["negative_limit"] == -50.0

    def test_cannot_instantiate_abstract(self):
        """测试不能实例化抽象类。"""
        with pytest.raises(TypeError):
            AbstractDevice("test", {})

        with pytest.raises(TypeError):
            AbstractStepper("test", {})


class TestAbstractMethodsSignature:
    """测试抽象方法签名。"""

    def test_abstract_device_methods(self):
        """测试AbstractDevice抽象方法签名。"""
        import inspect

        assert hasattr(AbstractDevice, "connect")
        assert hasattr(AbstractDevice, "disconnect")
        assert hasattr(AbstractDevice, "read_status")

        connect_sig = inspect.signature(AbstractDevice.connect)
        assert "self" in connect_sig.parameters

        disconnect_sig = inspect.signature(AbstractDevice.disconnect)
        assert "self" in disconnect_sig.parameters

    def test_abstract_stepper_methods(self):
        """测试AbstractStepper抽象方法签名。"""
        import inspect

        methods = ["move_abs", "move_rel", "jog", "home", "read_position", "stop"]

        for method_name in methods:
            assert hasattr(AbstractStepper, method_name)
            method = getattr(AbstractStepper, method_name)
            sig = inspect.signature(method)
            assert "self" in sig.parameters
