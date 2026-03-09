"""
测试温控系统模块

测试内容：
- 初始化和配置
- 连接/断开
- PID控制算法
- 程序控温
- 温度保护机制
- 温度曲线记录
- 急停和复位

作者：Backend Engineer Agent
创建日期：2026-03-07
"""

from unittest.mock import MagicMock, patch

import pytest

from core.abstract import DeviceStatus
from core.temperature_controller import (
    PIDParameters,
    PIDState,
    TemperatureController,
    TemperatureControllerMode,
    TemperatureDataPoint,
    TemperatureProtectionConfig,
    TemperatureProtectionType,
    TemperatureProgramSegment,
)


class TestPIDParameters:
    """测试PID参数数据类。"""

    def test_default_parameters(self):
        """测试默认PID参数。"""
        params = PIDParameters()

        assert params.kp == 1.0
        assert params.ki == 0.1
        assert params.kd == 0.01
        assert params.setpoint == 300.0
        assert params.output_min == -100.0  # 支持负输出（冷却）
        assert params.output_max == 100.0
        assert params.integral_limit == 0.0  # 0表示自动计算

    def test_custom_parameters(self):
        """测试自定义PID参数。"""
        params = PIDParameters(
            kp=10.0,
            ki=1.0,
            kd=0.5,
            setpoint=200.0,
            output_min=0.0,
            output_max=100.0,
            integral_limit=30.0,
        )

        assert params.kp == 10.0
        assert params.ki == 1.0
        assert params.kd == 0.5
        assert params.setpoint == 200.0
        assert params.integral_limit == 30.0

    def test_validate_valid_parameters(self):
        """测试有效参数验证。"""
        params = PIDParameters(kp=5.0, ki=0.5, kd=0.05)
        assert params.validate() is True

    def test_validate_invalid_kp_low(self):
        """测试无效Kp（过低）。"""
        params = PIDParameters(kp=0.05)
        assert params.validate() is False

    def test_validate_invalid_kp_high(self):
        """测试无效Kp（过高）。"""
        params = PIDParameters(kp=150.0)
        assert params.validate() is False

    def test_validate_invalid_ki_low(self):
        """测试无效Ki（过低）。"""
        params = PIDParameters(ki=0.0001)
        assert params.validate() is False

    def test_validate_invalid_ki_high(self):
        """测试无效Ki（过高）。"""
        params = PIDParameters(ki=15.0)
        assert params.validate() is False

    def test_validate_invalid_kd_low(self):
        """测试无效Kd（过低）。"""
        params = PIDParameters(kd=0.0001)
        assert params.validate() is False

    def test_validate_invalid_kd_high(self):
        """测试无效Kd（过高）。"""
        params = PIDParameters(kd=15.0)
        assert params.validate() is False

    def test_validate_boundary_values(self):
        """测试边界值验证。"""
        # 最小值
        params_min = PIDParameters(kp=0.1, ki=0.001, kd=0.001)
        assert params_min.validate() is True

        # 最大值
        params_max = PIDParameters(kp=100.0, ki=10.0, kd=10.0)
        assert params_max.validate() is True


class TestTemperatureProgramSegment:
    """测试温度程序段数据类。"""

    def test_default_segment(self):
        """测试默认程序段。"""
        segment = TemperatureProgramSegment(target_temperature=300.0)

        assert segment.target_temperature == 300.0
        assert segment.ramp_rate == 1.0
        assert segment.hold_time == 0.0
        assert segment.segment_id == 0

    def test_custom_segment(self):
        """测试自定义程序段。"""
        segment = TemperatureProgramSegment(
            target_temperature=200.0,
            ramp_rate=5.0,
            hold_time=600.0,
            segment_id=3,
        )

        assert segment.target_temperature == 200.0
        assert segment.ramp_rate == 5.0
        assert segment.hold_time == 600.0
        assert segment.segment_id == 3

    def test_validate_valid_segment(self):
        """测试有效程序段验证。"""
        segment = TemperatureProgramSegment(
            target_temperature=300.0,
            ramp_rate=2.0,
            hold_time=100.0,
        )
        assert segment.validate() is True

    def test_validate_invalid_temperature_low(self):
        """测试无效温度（过低）。"""
        segment = TemperatureProgramSegment(target_temperature=50.0)
        assert segment.validate() is False

    def test_validate_invalid_temperature_high(self):
        """测试无效温度（过高）。"""
        segment = TemperatureProgramSegment(target_temperature=500.0)
        assert segment.validate() is False

    def test_validate_invalid_ramp_rate_low(self):
        """测试无效升降温速率（过低）。"""
        # ramp_rate范围是-10到10，0.05是有效值
        # 测试超出范围的负值
        segment = TemperatureProgramSegment(target_temperature=300.0, ramp_rate=-15.0)
        assert segment.validate() is False

    def test_validate_invalid_ramp_rate_high(self):
        """测试无效升降温速率（过高）。"""
        segment = TemperatureProgramSegment(target_temperature=300.0, ramp_rate=15.0)
        assert segment.validate() is False

    def test_validate_negative_hold_time(self):
        """测试无效恒温时间（负值）。"""
        segment = TemperatureProgramSegment(target_temperature=300.0, hold_time=-10.0)
        assert segment.validate() is False

    def test_validate_custom_temperature_range(self):
        """测试自定义温度范围验证。"""
        segment = TemperatureProgramSegment(target_temperature=100.0)
        assert segment.validate(min_temp=80.0, max_temp=350.0) is True
        assert segment.validate(min_temp=150.0, max_temp=350.0) is False


class TestTemperatureProtectionConfig:
    """测试温度保护配置数据类。"""

    def test_default_config(self):
        """测试默认保护配置。"""
        config = TemperatureProtectionConfig()

        assert config.high_temp_limit == 450.0
        assert config.low_temp_limit == 70.0
        assert config.max_rate_limit == 20.0
        assert config.enable_high_temp is True
        assert config.enable_low_temp is True
        assert config.enable_rate_limit is True

    def test_custom_config(self):
        """测试自定义保护配置。"""
        config = TemperatureProtectionConfig(
            high_temp_limit=400.0,
            low_temp_limit=80.0,
            max_rate_limit=15.0,
            enable_high_temp=False,
            enable_low_temp=False,
            enable_rate_limit=False,
        )

        assert config.high_temp_limit == 400.0
        assert config.low_temp_limit == 80.0
        assert config.max_rate_limit == 15.0
        assert config.enable_high_temp is False
        assert config.enable_low_temp is False
        assert config.enable_rate_limit is False

    def test_validate_valid_config(self):
        """测试有效配置验证。"""
        config = TemperatureProtectionConfig(
            high_temp_limit=400.0,
            low_temp_limit=100.0,
            max_rate_limit=15.0,
        )
        assert config.validate() is True

    def test_validate_invalid_temp_limits(self):
        """测试无效温度限制（高温低于低温）。"""
        config = TemperatureProtectionConfig(
            high_temp_limit=50.0,
            low_temp_limit=100.0,
        )
        assert config.validate() is False

    def test_validate_invalid_rate_limit(self):
        """测试无效温度变化率限制。"""
        config = TemperatureProtectionConfig(max_rate_limit=-5.0)
        assert config.validate() is False


class TestTemperatureControllerInit:
    """测试温度控制器初始化。"""

    def test_default_initialization(self):
        """测试默认初始化。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )

        assert controller.device_id == "test_controller"
        assert controller.simulation_mode is True
        assert controller.status == DeviceStatus.DISCONNECTED
        assert controller._current_temperature == 300.0
        assert controller._current_output == 0.0
        assert controller._mode == TemperatureControllerMode.MANUAL

    def test_custom_pid_initialization(self):
        """测试自定义PID参数初始化。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={
                "simulation": True,
                "pid_params": {
                    "kp": 10.0,
                    "ki": 1.0,
                    "kd": 0.5,
                    "setpoint": 250.0,
                },
            },
        )

        assert controller.pid_params.kp == 10.0
        assert controller.pid_params.ki == 1.0
        assert controller.pid_params.kd == 0.5
        assert controller.pid_params.setpoint == 250.0

    def test_custom_protection_initialization(self):
        """测试自定义保护配置初始化。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={
                "simulation": True,
                "protection": {
                    "high_temp_limit": 400.0,
                    "low_temp_limit": 100.0,
                    "max_rate_limit": 15.0,
                },
            },
        )

        assert controller.protection_config.high_temp_limit == 400.0
        assert controller.protection_config.low_temp_limit == 100.0
        assert controller.protection_config.max_rate_limit == 15.0

    def test_temperature_range_constants(self):
        """测试温度范围常量。"""
        assert TemperatureController.MIN_TEMPERATURE == 77.0
        assert TemperatureController.MAX_TEMPERATURE == 400.0
        assert TemperatureController.TEMPERATURE_TOLERANCE == 0.1


class TestTemperatureControllerConnection:
    """测试温度控制器连接管理。"""

    @pytest.mark.asyncio
    async def test_connect_simulation_mode(self):
        """测试仿真模式连接。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )

        result = await controller.connect()

        assert result is True
        assert controller.status == DeviceStatus.READY

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """测试断开连接。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()
        controller.status = DeviceStatus.READY

        result = await controller.disconnect()

        assert result is True
        assert controller.status == DeviceStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_disconnect_stops_pid_control(self):
        """测试断开连接时停止PID控制。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()
        await controller.start_pid_control()

        await controller.disconnect()

        assert controller._pid_running is False

    @pytest.mark.asyncio
    async def test_disconnect_stops_program(self):
        """测试断开连接时停止程序控温。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        # 加载并启动程序
        segments = [
            TemperatureProgramSegment(target_temperature=300.0, ramp_rate=1.0),
        ]
        await controller.load_program(segments)
        await controller.start_program()

        await controller.disconnect()

        assert controller._program_running is False


class TestTemperatureReadAndSet:
    """测试温度读取与设置。"""

    @pytest.mark.asyncio
    async def test_read_temperature_simulation(self):
        """测试仿真模式读取温度。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        temp = await controller.read_temperature()

        assert isinstance(temp, float)
        assert TemperatureController.MIN_TEMPERATURE * 0.9 <= temp

    @pytest.mark.asyncio
    async def test_set_temperature_valid(self):
        """测试设置有效温度。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        result = await controller.set_temperature(300.0)

        assert result is True
        assert controller.pid_params.setpoint == 300.0
        assert controller._mode == TemperatureControllerMode.MANUAL

    @pytest.mark.asyncio
    async def test_set_temperature_invalid_low(self):
        """测试设置无效温度（过低）。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        with pytest.raises(ValueError, match="Temperature must be"):
            await controller.set_temperature(50.0)

    @pytest.mark.asyncio
    async def test_set_temperature_invalid_high(self):
        """测试设置无效温度（过高）。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        with pytest.raises(ValueError, match="Temperature must be"):
            await controller.set_temperature(500.0)

    @pytest.mark.asyncio
    async def test_set_output_valid(self):
        """测试设置有效输出功率。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        result = await controller.set_output(50.0)

        assert result is True
        assert controller._current_output == 50.0

    @pytest.mark.asyncio
    async def test_set_output_invalid_low(self):
        """测试设置无效输出功率（过低）。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        # 输出范围是-100到100，-150超出范围
        with pytest.raises(ValueError, match="Output must be"):
            await controller.set_output(-150.0)

    @pytest.mark.asyncio
    async def test_set_output_invalid_high(self):
        """测试设置无效输出功率（过高）。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        with pytest.raises(ValueError, match="Output must be"):
            await controller.set_output(150.0)

    @pytest.mark.asyncio
    async def test_set_temperature_when_protection_triggered(self):
        """测试保护触发时设置温度。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        # 触发保护（需要提供current_temp和threshold参数）
        await controller._trigger_protection(
            TemperatureProtectionType.HIGH_TEMP,
            current_temp=460.0,
            threshold=450.0
        )

        result = await controller.set_temperature(300.0)

        assert result is False


class TestPIDControl:
    """测试PID控制。"""

    @pytest.mark.asyncio
    async def test_start_pid_control(self):
        """测试启动PID控制。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        result = await controller.start_pid_control()

        assert result is True
        assert controller._pid_running is True
        assert controller._mode == TemperatureControllerMode.PID
        assert controller._pid_task is not None

        # 清理
        await controller.stop_pid_control()

    @pytest.mark.asyncio
    async def test_stop_pid_control(self):
        """测试停止PID控制。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()
        await controller.start_pid_control()

        result = await controller.stop_pid_control()

        assert result is True
        assert controller._pid_running is False
        assert controller._current_output == 0.0

    @pytest.mark.asyncio
    async def test_set_pid_parameters(self):
        """测试设置PID参数。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        result = await controller.set_pid_parameters(kp=5.0, ki=0.5, kd=0.05)

        assert result is True
        assert controller.pid_params.kp == 5.0
        assert controller.pid_params.ki == 0.5
        assert controller.pid_params.kd == 0.05

    @pytest.mark.asyncio
    async def test_set_pid_parameters_invalid(self):
        """测试设置无效PID参数。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        result = await controller.set_pid_parameters(kp=0.05)  # 过低

        assert result is False

    @pytest.mark.asyncio
    async def test_set_pid_setpoint(self):
        """测试设置PID设定点。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        result = await controller.set_pid_parameters(setpoint=250.0)

        assert result is True
        assert controller.pid_params.setpoint == 250.0

    @pytest.mark.asyncio
    async def test_pid_control_with_invalid_params(self):
        """测试使用无效参数启动PID控制。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        # 设置无效参数
        controller.pid_params.kp = 0.05

        result = await controller.start_pid_control()

        assert result is False

    def test_calculate_pid_output(self):
        """测试PID输出计算。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )

        # 设置PID参数
        controller.pid_params.kp = 10.0
        controller.pid_params.ki = 1.0
        controller.pid_params.kd = 0.5
        controller.pid_params.setpoint = 300.0

        # 当前温度低于设定点
        current_temp = 280.0
        dt = 1.0

        output = controller._calculate_pid_output(current_temp, dt)

        # 输出应该为正（加热）
        assert output > 0
        assert 0 <= output <= 100

    def test_calculate_pid_output_at_setpoint(self):
        """测试在设定点时的PID输出。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )

        controller.pid_params.setpoint = 300.0
        current_temp = 300.0
        dt = 1.0

        # 重置PID状态
        controller._pid_state = PIDState()

        output = controller._calculate_pid_output(current_temp, dt)

        # 在设定点时，比例项为0，输出应该接近0
        assert abs(output) < 10  # 允许小的积分和微分项

    def test_calculate_pid_output_integral_limit(self):
        """测试PID积分限幅。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )

        controller.pid_params.ki = 10.0
        controller.pid_params.integral_limit = 5.0
        controller.pid_params.setpoint = 300.0

        # 模拟长时间误差
        controller._pid_state.integral = 100.0  # 超过限幅

        current_temp = 280.0
        dt = 1.0

        output = controller._calculate_pid_output(current_temp, dt)

        # 积分项应该被限幅
        assert abs(controller._pid_state.integral) <= controller.pid_params.integral_limit


class TestProgramControl:
    """测试程序控温。"""

    @pytest.mark.asyncio
    async def test_load_program(self):
        """测试加载温度程序。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        segments = [
            TemperatureProgramSegment(target_temperature=300.0, ramp_rate=2.0, hold_time=100.0),
            TemperatureProgramSegment(target_temperature=200.0, ramp_rate=-1.0, hold_time=200.0),
        ]

        result = await controller.load_program(segments)

        assert result is True
        assert len(controller._program) == 2
        assert controller._program[0].segment_id == 0
        assert controller._program[1].segment_id == 1

    @pytest.mark.asyncio
    async def test_load_program_invalid_segment(self):
        """测试加载无效程序段。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        segments = [
            TemperatureProgramSegment(target_temperature=500.0),  # 无效温度
        ]

        result = await controller.load_program(segments)

        assert result is False

    @pytest.mark.asyncio
    async def test_start_program(self):
        """测试启动程序控温。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        segments = [
            TemperatureProgramSegment(target_temperature=310.0, ramp_rate=10.0, hold_time=1.0),
        ]
        await controller.load_program(segments)

        result = await controller.start_program()

        assert result is True
        assert controller._program_running is True

        # 等待程序完成
        await asyncio.sleep(2)

        # 清理
        await controller.stop_program()

    @pytest.mark.asyncio
    async def test_stop_program(self):
        """测试停止程序控温。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        segments = [
            TemperatureProgramSegment(target_temperature=400.0, ramp_rate=1.0, hold_time=100.0),
        ]
        await controller.load_program(segments)
        await controller.start_program()

        result = await controller.stop_program()

        assert result is True
        assert controller._program_running is False

    @pytest.mark.asyncio
    async def test_start_program_without_loading(self):
        """测试未加载程序时启动。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        result = await controller.start_program()

        assert result is False

    @pytest.mark.asyncio
    async def test_get_program_status(self):
        """测试获取程序状态。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        segments = [
            TemperatureProgramSegment(target_temperature=300.0, ramp_rate=2.0),
            TemperatureProgramSegment(target_temperature=200.0, ramp_rate=-1.0),
        ]
        await controller.load_program(segments)

        status = await controller.get_program_status()

        assert status["running"] is False
        assert status["total_segments"] == 2
        assert len(status["program"]) == 2


class TestTemperatureProtection:
    """测试温度保护机制。"""

    @pytest.mark.asyncio
    async def test_high_temperature_protection(self):
        """测试高温保护。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        # 设置高温保护阈值
        controller.protection_config.high_temp_limit = 350.0
        # 禁用温度变化率保护，避免干扰
        controller.protection_config.enable_rate_limit = False

        # 模拟高温（设置上次温度时间，避免变化率保护）
        controller._last_temperature = 360.0
        controller._last_temperature_time = time.time()
        controller._current_temperature = 360.0

        result = await controller._check_protection(360.0)

        assert result is True
        assert controller._protection_triggered is True
        assert controller._protection_type == TemperatureProtectionType.HIGH_TEMP

    @pytest.mark.asyncio
    async def test_low_temperature_protection(self):
        """测试低温保护。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        # 设置低温保护阈值
        controller.protection_config.low_temp_limit = 100.0
        # 禁用温度变化率保护，避免干扰
        controller.protection_config.enable_rate_limit = False

        # 模拟低温（设置上次温度时间，避免变化率保护）
        controller._last_temperature = 90.0
        controller._last_temperature_time = time.time()
        controller._current_temperature = 90.0

        result = await controller._check_protection(90.0)

        assert result is True
        assert controller._protection_triggered is True
        assert controller._protection_type == TemperatureProtectionType.LOW_TEMP

    @pytest.mark.asyncio
    async def test_rate_limit_protection(self):
        """测试温度变化率保护。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        # 设置变化率限制
        controller.protection_config.max_rate_limit = 10.0

        # 清空历史窗口并添加初始数据点
        controller._temperature_history_window.clear()
        # 添加一个旧的数据点（0.5秒前，温度300K）
        old_time = time.time() - 0.5
        controller._temperature_history_window.append((old_time, 300.0))

        # 当前温度变化率 = (320 - 300) / 0.5 * 60 = 2400 K/min
        result = await controller._check_protection(320.0)

        assert result is True
        assert controller._protection_triggered is True
        assert controller._protection_type == TemperatureProtectionType.RATE_LIMIT

    @pytest.mark.asyncio
    async def test_clear_protection(self):
        """测试清除保护状态。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        # 触发保护（需要提供current_temp和threshold参数）
        await controller._trigger_protection(
            TemperatureProtectionType.HIGH_TEMP,
            current_temp=460.0,
            threshold=450.0
        )

        # 温度回到安全范围
        controller._current_temperature = 300.0

        result = await controller.clear_protection()

        assert result is True
        assert controller._protection_triggered is False
        assert controller._protection_type is None

    @pytest.mark.asyncio
    async def test_clear_protection_unsafe_temperature(self):
        """测试在危险温度时清除保护。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        # 触发保护（需要提供current_temp和threshold参数）
        await controller._trigger_protection(
            TemperatureProtectionType.HIGH_TEMP,
            current_temp=460.0,
            threshold=450.0
        )

        # 温度仍在危险范围
        controller._current_temperature = 460.0

        result = await controller.clear_protection()

        assert result is False
        assert controller._protection_triggered is True

    @pytest.mark.asyncio
    async def test_set_protection_config(self):
        """测试设置保护配置。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        result = await controller.set_protection_config(
            high_temp_limit=400.0,
            low_temp_limit=100.0,
            max_rate_limit=15.0,
        )

        assert result is True
        assert controller.protection_config.high_temp_limit == 400.0
        assert controller.protection_config.low_temp_limit == 100.0
        assert controller.protection_config.max_rate_limit == 15.0

    @pytest.mark.asyncio
    async def test_protection_stops_pid_control(self):
        """测试保护触发时停止PID控制。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()
        await controller.start_pid_control()

        # 触发保护（需要提供current_temp和threshold参数）
        await controller._trigger_protection(
            TemperatureProtectionType.HIGH_TEMP,
            current_temp=460.0,
            threshold=450.0
        )

        assert controller._pid_running is False
        assert controller._current_output == 0.0

    @pytest.mark.asyncio
    async def test_protection_stops_program(self):
        """测试保护触发时停止程序控温。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        segments = [
            TemperatureProgramSegment(target_temperature=300.0, ramp_rate=1.0),
        ]
        await controller.load_program(segments)
        await controller.start_program()

        # 触发保护（需要提供current_temp和threshold参数）
        await controller._trigger_protection(
            TemperatureProtectionType.HIGH_TEMP,
            current_temp=460.0,
            threshold=450.0
        )

        assert controller._program_running is False


class TestTemperatureHistory:
    """测试温度曲线记录。"""

    @pytest.mark.asyncio
    async def test_record_temperature(self):
        """测试记录温度数据。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        await controller._record_temperature(300.0)

        assert len(controller._temperature_history) == 1
        assert controller._temperature_history[0].temperature == 300.0

    @pytest.mark.asyncio
    async def test_get_temperature_history(self):
        """测试获取温度历史记录。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        # 记录多个数据点
        for temp in [300.0, 301.0, 302.0]:
            await controller._record_temperature(temp)

        history = await controller.get_temperature_history()

        assert len(history) == 3
        assert history[0]["temperature"] == 300.0
        assert history[2]["temperature"] == 302.0

    @pytest.mark.asyncio
    async def test_get_temperature_history_with_time_filter(self):
        """测试带时间过滤的历史记录。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        # 记录数据
        await controller._record_temperature(300.0)
        await asyncio.sleep(0.1)
        start_time = time.time()
        await controller._record_temperature(301.0)
        await controller._record_temperature(302.0)
        end_time = time.time()

        history = await controller.get_temperature_history(
            start_time=start_time,
            end_time=end_time,
        )

        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_get_temperature_history_with_limit(self):
        """测试带数量限制的历史记录。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        # 记录多个数据点
        for temp in range(300, 310):
            await controller._record_temperature(float(temp))

        history = await controller.get_temperature_history(limit=5)

        assert len(history) == 5
        # 应该返回最后5个
        assert history[-1]["temperature"] == 309.0

    @pytest.mark.asyncio
    async def test_clear_temperature_history(self):
        """测试清除温度历史记录。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        await controller._record_temperature(300.0)
        await controller.clear_temperature_history()

        assert len(controller._temperature_history) == 0

    @pytest.mark.asyncio
    async def test_export_temperature_history_csv(self):
        """测试导出CSV格式历史记录。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        await controller._record_temperature(300.0)
        await controller._record_temperature(301.0)

        csv_data = await controller.export_temperature_history(format="csv")

        assert "timestamp,datetime,temperature,setpoint,output,mode" in csv_data
        assert "300.0" in csv_data
        assert "301.0" in csv_data

    @pytest.mark.asyncio
    async def test_export_temperature_history_json(self):
        """测试导出JSON格式历史记录。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        await controller._record_temperature(300.0)

        json_data = await controller.export_temperature_history(format="json")

        assert '"temperature": 300.0' in json_data

    @pytest.mark.asyncio
    async def test_export_temperature_history_invalid_format(self):
        """测试导出无效格式。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        with pytest.raises(ValueError, match="Unsupported format"):
            await controller.export_temperature_history(format="xml")

    @pytest.mark.asyncio
    async def test_history_max_length(self):
        """测试历史记录最大长度限制。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        # 记录超过最大长度的数据
        for i in range(controller.MAX_HISTORY_LENGTH + 100):
            await controller._record_temperature(300.0 + i * 0.01)

        assert len(controller._temperature_history) == controller.MAX_HISTORY_LENGTH


class TestEmergencyStop:
    """测试急停与复位。"""

    @pytest.mark.asyncio
    async def test_emergency_stop(self):
        """测试紧急停止。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()
        await controller.start_pid_control()

        result = await controller.emergency_stop()

        assert result is True
        assert controller.status == DeviceStatus.EMERGENCY_STOP
        assert controller._pid_running is False
        assert controller._current_output == 0.0

    @pytest.mark.asyncio
    async def test_reset_emergency(self):
        """测试复位急停状态。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()
        await controller.emergency_stop()

        result = await controller.reset_emergency()

        assert result is True
        assert controller.status == DeviceStatus.READY

    @pytest.mark.asyncio
    async def test_emergency_stop_stops_program(self):
        """测试急停停止程序控温。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        segments = [
            TemperatureProgramSegment(target_temperature=300.0, ramp_rate=1.0),
        ]
        await controller.load_program(segments)
        await controller.start_program()

        await controller.emergency_stop()

        assert controller._program_running is False


class TestReadStatus:
    """测试读取设备状态。"""

    @pytest.mark.asyncio
    async def test_read_status(self):
        """测试读取完整状态。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        status = await controller.read_status()

        assert status["device_id"] == "test_controller"
        assert status["status"] == "ready"
        assert "current_temperature" in status
        assert "current_output" in status
        assert "pid_params" in status
        assert "protection" in status
        assert "program" in status
        assert "pid_running" in status
        assert "connected" in status

    @pytest.mark.asyncio
    async def test_read_status_with_protection(self):
        """测试保护触发时的状态。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )
        await controller.connect()

        # 触发保护（需要提供current_temp和threshold参数）
        await controller._trigger_protection(
            TemperatureProtectionType.HIGH_TEMP,
            current_temp=460.0,
            threshold=450.0
        )

        status = await controller.read_status()

        assert status["protection"]["triggered"] is True
        assert status["protection"]["type"] == "high_temperature"


class TestIntegration:
    """集成测试。"""

    @pytest.mark.asyncio
    async def test_full_pid_control_workflow(self):
        """测试完整PID控制工作流。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )

        # 1. 连接
        result = await controller.connect()
        assert result is True

        # 2. 设置温度
        result = await controller.set_temperature(310.0)
        assert result is True

        # 3. 设置PID参数
        result = await controller.set_pid_parameters(kp=5.0, ki=0.5, kd=0.1)
        assert result is True

        # 4. 启动PID控制
        result = await controller.start_pid_control()
        assert result is True

        # 5. 运行一段时间
        await asyncio.sleep(2)

        # 6. 停止PID控制
        result = await controller.stop_pid_control()
        assert result is True

        # 7. 断开连接
        result = await controller.disconnect()
        assert result is True

    @pytest.mark.asyncio
    async def test_full_program_workflow(self):
        """测试完整程序控温工作流。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )

        # 1. 连接
        result = await controller.connect()
        assert result is True

        # 2. 加载程序
        segments = [
            TemperatureProgramSegment(target_temperature=310.0, ramp_rate=10.0, hold_time=1.0),
        ]
        result = await controller.load_program(segments)
        assert result is True

        # 3. 启动程序
        result = await controller.start_program()
        assert result is True

        # 4. 等待程序完成
        await asyncio.sleep(3)

        # 5. 检查状态
        status = await controller.get_program_status()
        assert status["running"] is False

        # 6. 断开连接
        result = await controller.disconnect()
        assert result is True

    @pytest.mark.asyncio
    async def test_protection_workflow(self):
        """测试保护工作流。"""
        controller = TemperatureController(
            device_id="test_controller",
            config={"simulation": True},
        )

        # 1. 连接
        result = await controller.connect()
        assert result is True

        # 2. 设置保护配置
        result = await controller.set_protection_config(
            high_temp_limit=350.0,
            low_temp_limit=100.0,
        )
        assert result is True

        # 3. 启动PID控制
        result = await controller.start_pid_control()
        assert result is True

        # 4. 模拟高温
        controller._current_temperature = 360.0
        await controller._check_protection(360.0)

        # 5. 验证保护触发
        assert controller._protection_triggered is True
        assert controller._pid_running is False

        # 6. 温度回到安全范围
        controller._current_temperature = 300.0

        # 7. 清除保护
        result = await controller.clear_protection()
        assert result is True

        # 8. 断开连接
        result = await controller.disconnect()
        assert result is True


# 导入asyncio和time模块
import asyncio
import time
