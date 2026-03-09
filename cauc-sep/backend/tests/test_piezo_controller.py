"""
测试压电陶瓷控制器驱动

测试内容：
- 初始化和配置
- 连接/断开
- 电压控制（开环模式）
- 位移控制（闭环模式）
- 校准功能
- 非线性补偿
- 磁滞补偿
- 边界条件处理
"""

import pytest

from core.abstract import DeviceStatus
from core.piezo_controller import (
    CalibrationData,
    CalibrationPoint,
    CalibrationType,
    ControlMode,
    PiezoConfig,
    PiezoController,
)


class TestPiezoConfig:
    """测试压电陶瓷配置类。"""

    def test_default_config(self):
        """测试默认配置。"""
        config = PiezoConfig()

        assert config.max_voltage_v == 150.0
        assert config.min_voltage_v == 0.0
        assert config.voltage_resolution_v == 0.001
        assert config.max_displacement_um == 100.0
        assert config.min_displacement_um == 0.0
        assert config.displacement_resolution_nm == 1.0
        assert config.default_mode == ControlMode.OPEN_LOOP
        assert config.hysteresis_compensation is True

    def test_custom_config(self):
        """测试自定义配置。"""
        config = PiezoConfig(
            max_voltage_v=200.0,
            voltage_resolution_v=0.01,
            max_displacement_um=150.0,
            default_mode=ControlMode.CLOSED_LOOP,
            hysteresis_compensation=False,
        )

        assert config.max_voltage_v == 200.0
        assert config.voltage_resolution_v == 0.01
        assert config.max_displacement_um == 150.0
        assert config.default_mode == ControlMode.CLOSED_LOOP
        assert config.hysteresis_compensation is False


class TestCalibrationPoint:
    """测试校准点数据类。"""

    def test_calibration_point_creation(self):
        """测试创建校准点。"""
        point = CalibrationPoint(voltage_v=75.0, displacement_um=50.0)

        assert point.voltage_v == 75.0
        assert point.displacement_um == 50.0


class TestCalibrationData:
    """测试校准数据类。"""

    def test_default_calibration_data(self):
        """测试默认校准数据。"""
        data = CalibrationData()

        assert data.points == []
        assert data.calibration_type == CalibrationType.LINEAR
        assert data.coefficients == []
        assert data.valid is False

    def test_calibration_data_with_points(self):
        """测试带校准点的数据。"""
        points = [
            CalibrationPoint(voltage_v=0.0, displacement_um=0.0),
            CalibrationPoint(voltage_v=75.0, displacement_um=50.0),
            CalibrationPoint(voltage_v=150.0, displacement_um=100.0),
        ]
        data = CalibrationData(points=points, valid=True)

        assert len(data.points) == 3
        assert data.valid is True


class TestPiezoControllerInit:
    """测试压电陶瓷控制器初始化。"""

    def test_default_initialization(self):
        """测试默认初始化。"""
        piezo = PiezoController(device_id="test_piezo", config={})

        assert piezo.device_id == "test_piezo"
        assert piezo.simulation is True
        assert piezo.status == DeviceStatus.DISCONNECTED
        assert piezo._current_voltage == 0.0
        assert piezo._current_displacement == 0.0
        assert piezo._control_mode == ControlMode.OPEN_LOOP

    def test_custom_initialization(self):
        """测试自定义初始化。"""
        config = {
            "simulation": True,
            "max_voltage_v": 200.0,
            "max_displacement_um": 150.0,
            "default_mode": "closed_loop",
            "hysteresis_compensation": False,
        }
        piezo = PiezoController(device_id="custom_piezo", config=config)

        assert piezo.piezo_config.max_voltage_v == 200.0
        assert piezo.piezo_config.max_displacement_um == 150.0
        assert piezo._control_mode == ControlMode.CLOSED_LOOP
        assert piezo.piezo_config.hysteresis_compensation is False

    def test_hardware_config_initialization(self):
        """测试硬件配置初始化。"""
        config = {
            "simulation": False,
            "port": "COM3",
            "baudrate": 115200,
        }
        piezo = PiezoController(device_id="hw_piezo", config=config)

        assert piezo.simulation is False
        assert piezo.port == "COM3"
        assert piezo.baudrate == 115200


class TestPiezoControllerConnection:
    """测试压电陶瓷控制器连接管理。"""

    @pytest.mark.asyncio
    async def test_connect_simulation_mode(self):
        """测试仿真模式连接。"""
        piezo = PiezoController(device_id="test_piezo", config={"simulation": True})

        result = await piezo.connect()

        assert result is True
        assert piezo.status == DeviceStatus.READY

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """测试断开连接。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo.status = DeviceStatus.READY

        result = await piezo.disconnect()

        assert result is True
        assert piezo.status == DeviceStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_read_status(self):
        """测试读取状态。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo.status = DeviceStatus.READY
        piezo._current_voltage = 75.0
        piezo._current_displacement = 50.0

        result = await piezo.read_status()

        assert result["device_id"] == "test_piezo"
        assert result["status"] == "ready"
        assert result["current_voltage_v"] == 75.0
        assert result["current_displacement_um"] == 50.0
        assert "control_mode" in result
        assert "calibration_valid" in result


class TestVoltageControl:
    """测试电压控制功能。"""

    @pytest.mark.asyncio
    async def test_set_voltage_simulation(self):
        """测试仿真模式设置电压。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo.status = DeviceStatus.READY

        result = await piezo.set_voltage(75.0)

        assert result is True
        assert piezo._current_voltage == 75.0

    @pytest.mark.asyncio
    async def test_set_voltage_boundary_min(self):
        """测试设置最小电压。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo.status = DeviceStatus.READY

        result = await piezo.set_voltage(0.0)

        assert result is True
        assert piezo._current_voltage == 0.0

    @pytest.mark.asyncio
    async def test_set_voltage_boundary_max(self):
        """测试设置最大电压。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo.status = DeviceStatus.READY

        result = await piezo.set_voltage(150.0)

        assert result is True
        assert piezo._current_voltage == 150.0

    @pytest.mark.asyncio
    async def test_set_voltage_exceed_max(self):
        """测试设置超出最大电压。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo.status = DeviceStatus.READY

        with pytest.raises(ValueError, match="超出有效范围"):
            await piezo.set_voltage(200.0)

    @pytest.mark.asyncio
    async def test_set_voltage_negative(self):
        """测试设置负电压。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo.status = DeviceStatus.READY

        with pytest.raises(ValueError, match="超出有效范围"):
            await piezo.set_voltage(-10.0)

    @pytest.mark.asyncio
    async def test_set_voltage_quantization(self):
        """测试电压量化（分辨率）。"""
        piezo = PiezoController(
            device_id="test_piezo",
            config={"voltage_resolution_v": 0.01},  # 10mV分辨率
        )
        piezo.status = DeviceStatus.READY

        # 设置非分辨率整数倍的电压
        result = await piezo.set_voltage(75.123)

        assert result is True
        # 应该量化到最接近的分辨率值
        assert piezo._current_voltage == 75.12

    @pytest.mark.asyncio
    async def test_get_voltage(self):
        """测试获取电压。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo._current_voltage = 75.0

        voltage = await piezo.get_voltage()

        assert voltage == 75.0


class TestDisplacementControl:
    """测试位移控制功能。"""

    @pytest.mark.asyncio
    async def test_set_displacement_without_calibration(self):
        """测试无校准数据时设置位移（线性近似）。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo.status = DeviceStatus.READY

        result = await piezo.set_displacement(50.0)

        assert result is True
        # 线性近似：50μm = 50%位移 = 75V
        assert piezo._current_voltage == 75.0
        assert piezo._target_displacement == 50.0

    @pytest.mark.asyncio
    async def test_set_displacement_boundary_min(self):
        """测试设置最小位移。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo.status = DeviceStatus.READY

        result = await piezo.set_displacement(0.0)

        assert result is True
        assert piezo._current_voltage == 0.0

    @pytest.mark.asyncio
    async def test_set_displacement_boundary_max(self):
        """测试设置最大位移。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo.status = DeviceStatus.READY

        result = await piezo.set_displacement(100.0)

        assert result is True
        assert piezo._current_voltage == 150.0

    @pytest.mark.asyncio
    async def test_set_displacement_exceed_max(self):
        """测试设置超出最大位移。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo.status = DeviceStatus.READY

        with pytest.raises(ValueError, match="超出有效范围"):
            await piezo.set_displacement(150.0)

    @pytest.mark.asyncio
    async def test_set_displacement_negative(self):
        """测试设置负位移。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo.status = DeviceStatus.READY

        with pytest.raises(ValueError, match="超出有效范围"):
            await piezo.set_displacement(-10.0)

    @pytest.mark.asyncio
    async def test_get_displacement(self):
        """测试获取位移。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo._current_displacement = 50.0

        displacement = await piezo.get_displacement()

        assert displacement == 50.0


class TestControlMode:
    """测试控制模式切换。"""

    @pytest.mark.asyncio
    async def test_set_control_mode_open_loop(self):
        """测试设置开环控制模式。"""
        piezo = PiezoController(device_id="test_piezo", config={})

        result = await piezo.set_control_mode(ControlMode.OPEN_LOOP)

        assert result is True
        assert piezo._control_mode == ControlMode.OPEN_LOOP

    @pytest.mark.asyncio
    async def test_set_control_mode_closed_loop(self):
        """测试设置闭环控制模式。"""
        piezo = PiezoController(device_id="test_piezo", config={})

        result = await piezo.set_control_mode(ControlMode.CLOSED_LOOP)

        assert result is True
        assert piezo._control_mode == ControlMode.CLOSED_LOOP

    def test_get_control_mode(self):
        """测试获取控制模式。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo._control_mode = ControlMode.CLOSED_LOOP

        mode = piezo.get_control_mode()

        assert mode == ControlMode.CLOSED_LOOP


class TestCalibration:
    """测试校准功能。"""

    @pytest.mark.asyncio
    async def test_add_calibration_point(self):
        """测试添加校准点。"""
        piezo = PiezoController(device_id="test_piezo", config={})

        result = await piezo.add_calibration_point(voltage_v=75.0, displacement_um=50.0)

        assert result is True
        assert len(piezo._calibration_data.points) == 1
        assert piezo._calibration_data.points[0].voltage_v == 75.0
        assert piezo._calibration_data.points[0].displacement_um == 50.0

    @pytest.mark.asyncio
    async def test_add_multiple_calibration_points(self):
        """测试添加多个校准点。"""
        piezo = PiezoController(device_id="test_piezo", config={})

        await piezo.add_calibration_point(voltage_v=0.0, displacement_um=0.0)
        await piezo.add_calibration_point(voltage_v=75.0, displacement_um=50.0)
        await piezo.add_calibration_point(voltage_v=150.0, displacement_um=100.0)

        assert len(piezo._calibration_data.points) == 3

    @pytest.mark.asyncio
    async def test_add_calibration_point_invalid_voltage(self):
        """测试添加无效电压的校准点。"""
        piezo = PiezoController(device_id="test_piezo", config={})

        with pytest.raises(ValueError, match="超出有效范围"):
            await piezo.add_calibration_point(voltage_v=200.0, displacement_um=50.0)

    @pytest.mark.asyncio
    async def test_add_calibration_point_invalid_displacement(self):
        """测试添加无效位移的校准点。"""
        piezo = PiezoController(device_id="test_piezo", config={})

        with pytest.raises(ValueError, match="超出有效范围"):
            await piezo.add_calibration_point(voltage_v=75.0, displacement_um=150.0)

    @pytest.mark.asyncio
    async def test_clear_calibration(self):
        """测试清除校准数据。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        await piezo.add_calibration_point(voltage_v=75.0, displacement_um=50.0)

        result = await piezo.clear_calibration()

        assert result is True
        assert len(piezo._calibration_data.points) == 0
        assert piezo._calibration_data.valid is False

    @pytest.mark.asyncio
    async def test_perform_linear_calibration(self):
        """测试执行线性校准。"""
        piezo = PiezoController(device_id="test_piezo", config={})

        # 添加校准点
        await piezo.add_calibration_point(voltage_v=0.0, displacement_um=0.0)
        await piezo.add_calibration_point(voltage_v=150.0, displacement_um=100.0)

        result = await piezo.perform_calibration(CalibrationType.LINEAR)

        assert result is True
        assert piezo._calibration_data.valid is True
        assert piezo._calibration_data.calibration_type == CalibrationType.LINEAR
        assert len(piezo._calibration_data.coefficients) == 2

    @pytest.mark.asyncio
    async def test_perform_polynomial_calibration(self):
        """测试执行多项式校准。"""
        piezo = PiezoController(device_id="test_piezo", config={})

        # 添加多个校准点
        await piezo.add_calibration_point(voltage_v=0.0, displacement_um=0.0)
        await piezo.add_calibration_point(voltage_v=50.0, displacement_um=30.0)
        await piezo.add_calibration_point(voltage_v=100.0, displacement_um=65.0)
        await piezo.add_calibration_point(voltage_v=150.0, displacement_um=100.0)

        result = await piezo.perform_calibration(CalibrationType.POLYNOMIAL)

        assert result is True
        assert piezo._calibration_data.valid is True
        assert piezo._calibration_data.calibration_type == CalibrationType.POLYNOMIAL

    @pytest.mark.asyncio
    async def test_perform_piecewise_calibration(self):
        """测试执行分段线性校准。"""
        piezo = PiezoController(device_id="test_piezo", config={})

        await piezo.add_calibration_point(voltage_v=0.0, displacement_um=0.0)
        await piezo.add_calibration_point(voltage_v=75.0, displacement_um=50.0)
        await piezo.add_calibration_point(voltage_v=150.0, displacement_um=100.0)

        result = await piezo.perform_calibration(CalibrationType.PIECEWISE)

        assert result is True
        assert piezo._calibration_data.valid is True
        assert piezo._calibration_data.calibration_type == CalibrationType.PIECEWISE

    @pytest.mark.asyncio
    async def test_perform_calibration_insufficient_points(self):
        """测试校准点不足时执行校准。"""
        piezo = PiezoController(device_id="test_piezo", config={})

        # 只添加一个点
        await piezo.add_calibration_point(voltage_v=75.0, displacement_um=50.0)

        result = await piezo.perform_calibration(CalibrationType.LINEAR)

        assert result is False
        assert piezo._calibration_data.valid is False

    def test_get_calibration_data(self):
        """测试获取校准数据。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo._calibration_data.points = [
            CalibrationPoint(voltage_v=0.0, displacement_um=0.0),
            CalibrationPoint(voltage_v=150.0, displacement_um=100.0),
        ]
        piezo._calibration_data.valid = True

        data = piezo.get_calibration_data()

        assert data["valid"] is True
        assert data["point_count"] == 2
        assert len(data["points"]) == 2


class TestVoltageToDisplacementConversion:
    """测试电压-位移转换。"""

    @pytest.mark.asyncio
    async def test_linear_conversion_with_calibration(self):
        """测试线性校准后的电压-位移转换。"""
        piezo = PiezoController(device_id="test_piezo", config={})

        # 添加线性校准点
        await piezo.add_calibration_point(voltage_v=0.0, displacement_um=0.0)
        await piezo.add_calibration_point(voltage_v=150.0, displacement_um=100.0)
        await piezo.perform_calibration(CalibrationType.LINEAR)

        # 设置电压
        await piezo.set_voltage(75.0)

        # 验证位移（线性关系：75V → 50μm）
        assert abs(piezo._current_displacement - 50.0) < 0.1

    @pytest.mark.asyncio
    async def test_polynomial_conversion_with_calibration(self):
        """测试多项式校准后的电压-位移转换。"""
        piezo = PiezoController(device_id="test_piezo", config={})

        # 添加非线性校准点（模拟压电陶瓷非线性）
        await piezo.add_calibration_point(voltage_v=0.0, displacement_um=0.0)
        await piezo.add_calibration_point(voltage_v=50.0, displacement_um=28.0)  # 非线性
        await piezo.add_calibration_point(voltage_v=100.0, displacement_um=62.0)  # 非线性
        await piezo.add_calibration_point(voltage_v=150.0, displacement_um=100.0)
        await piezo.perform_calibration(CalibrationType.POLYNOMIAL)

        # 设置电压
        await piezo.set_voltage(75.0)

        # 验证位移（应该在非线性曲线上）
        assert 0 < piezo._current_displacement < 100

    @pytest.mark.asyncio
    async def test_piecewise_conversion_with_calibration(self):
        """测试分段线性校准后的电压-位移转换。"""
        piezo = PiezoController(device_id="test_piezo", config={})

        # 添加分段校准点
        await piezo.add_calibration_point(voltage_v=0.0, displacement_um=0.0)
        await piezo.add_calibration_point(voltage_v=75.0, displacement_um=45.0)
        await piezo.add_calibration_point(voltage_v=150.0, displacement_um=100.0)
        await piezo.perform_calibration(CalibrationType.PIECEWISE)

        # 设置电压
        await piezo.set_voltage(37.5)  # 在第一段中间

        # 验证位移（分段线性插值）
        assert abs(piezo._current_displacement - 22.5) < 0.1


class TestDisplacementToVoltageConversion:
    """测试位移-电压转换。"""

    @pytest.mark.asyncio
    async def test_linear_inverse_conversion(self):
        """测试线性校准后的位移-电压转换。"""
        piezo = PiezoController(device_id="test_piezo", config={})

        # 添加线性校准点
        await piezo.add_calibration_point(voltage_v=0.0, displacement_um=0.0)
        await piezo.add_calibration_point(voltage_v=150.0, displacement_um=100.0)
        await piezo.perform_calibration(CalibrationType.LINEAR)

        # 设置位移
        await piezo.set_displacement(50.0)

        # 验证电压（线性关系：50μm → 75V）
        assert abs(piezo._current_voltage - 75.0) < 0.1

    @pytest.mark.asyncio
    async def test_polynomial_inverse_conversion(self):
        """测试多项式校准后的位移-电压转换。"""
        piezo = PiezoController(device_id="test_piezo", config={})

        # 添加非线性校准点
        await piezo.add_calibration_point(voltage_v=0.0, displacement_um=0.0)
        await piezo.add_calibration_point(voltage_v=50.0, displacement_um=28.0)
        await piezo.add_calibration_point(voltage_v=100.0, displacement_um=62.0)
        await piezo.add_calibration_point(voltage_v=150.0, displacement_um=100.0)
        await piezo.perform_calibration(CalibrationType.POLYNOMIAL)

        # 设置位移
        await piezo.set_displacement(50.0)

        # 验证电压（应该在合理范围内）
        assert 0 < piezo._current_voltage < 150

    @pytest.mark.asyncio
    async def test_piecewise_inverse_conversion(self):
        """测试分段线性校准后的位移-电压转换。"""
        piezo = PiezoController(device_id="test_piezo", config={})

        # 添加分段校准点
        await piezo.add_calibration_point(voltage_v=0.0, displacement_um=0.0)
        await piezo.add_calibration_point(voltage_v=75.0, displacement_um=45.0)
        await piezo.add_calibration_point(voltage_v=150.0, displacement_um=100.0)
        await piezo.perform_calibration(CalibrationType.PIECEWISE)

        # 设置位移
        await piezo.set_displacement(22.5)  # 在第一段中间

        # 验证电压（分段线性插值逆）
        assert abs(piezo._current_voltage - 37.5) < 0.5


class TestHysteresisCompensation:
    """测试磁滞补偿功能。"""

    @pytest.mark.asyncio
    async def test_hysteresis_compensation_enabled(self):
        """测试启用磁滞补偿。"""
        piezo = PiezoController(
            device_id="test_piezo",
            config={"hysteresis_compensation": True},
        )
        piezo.status = DeviceStatus.READY

        # 先设置一个电压
        await piezo.set_voltage(50.0)

        # 再设置更高的电压（上升）
        await piezo.set_voltage(75.0)

        # 验证电压历史记录
        assert len(piezo._voltage_history) == 2

    @pytest.mark.asyncio
    async def test_hysteresis_compensation_disabled(self):
        """测试禁用磁滞补偿。"""
        piezo = PiezoController(
            device_id="test_piezo",
            config={"hysteresis_compensation": False},
        )
        piezo.status = DeviceStatus.READY

        await piezo.set_voltage(75.0)

        assert piezo._current_voltage == 75.0

    @pytest.mark.asyncio
    async def test_voltage_history_limit(self):
        """测试电压历史记录限制。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo.status = DeviceStatus.READY
        piezo._max_history_length = 10

        # 设置超过限制数量的电压
        for i in range(15):
            await piezo.set_voltage(float(i))

        # 验证历史记录不超过限制
        assert len(piezo._voltage_history) == 10

    def test_apply_hysteresis_compensation_rising(self):
        """测试电压上升时的磁滞补偿。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo._voltage_history = [50.0]

        # 上升10V
        compensated = piezo._apply_hysteresis_compensation(60.0)

        # 应该有额外的补偿
        assert compensated > 60.0

    def test_apply_hysteresis_compensation_falling(self):
        """测试电压下降时的磁滞补偿。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo._voltage_history = [60.0]

        # 下降10V
        compensated = piezo._apply_hysteresis_compensation(50.0)

        # 应该有减少的补偿
        assert compensated < 50.0


class TestConvenienceMethods:
    """测试便捷方法。"""

    @pytest.mark.asyncio
    async def test_zero(self):
        """测试归零操作。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo.status = DeviceStatus.READY
        piezo._current_voltage = 75.0

        result = await piezo.zero()

        assert result is True
        assert piezo._current_voltage == 0.0

    @pytest.mark.asyncio
    async def test_max_extend(self):
        """测试最大伸展操作。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo.status = DeviceStatus.READY

        result = await piezo.max_extend()

        assert result is True
        assert piezo._current_voltage == 150.0

    @pytest.mark.asyncio
    async def test_step_voltage_positive(self):
        """测试正电压步进。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo.status = DeviceStatus.READY
        piezo._current_voltage = 50.0

        result = await piezo.step_voltage(10.0)

        assert result is True
        assert piezo._current_voltage == 60.0

    @pytest.mark.asyncio
    async def test_step_voltage_negative(self):
        """测试负电压步进。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo.status = DeviceStatus.READY
        piezo._current_voltage = 50.0

        result = await piezo.step_voltage(-10.0)

        assert result is True
        assert piezo._current_voltage == 40.0

    @pytest.mark.asyncio
    async def test_step_displacement_positive(self):
        """测试正位移步进。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo.status = DeviceStatus.READY
        piezo._current_displacement = 50.0

        result = await piezo.step_displacement(10.0)

        assert result is True
        assert piezo._target_displacement == 60.0

    @pytest.mark.asyncio
    async def test_step_displacement_negative(self):
        """测试负位移步进。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo.status = DeviceStatus.READY
        piezo._current_displacement = 50.0

        result = await piezo.step_displacement(-10.0)

        assert result is True
        assert piezo._target_displacement == 40.0


class TestVoltageQuantization:
    """测试电压量化功能。"""

    def test_quantize_voltage_default_resolution(self):
        """测试默认分辨率量化。"""
        piezo = PiezoController(device_id="test_piezo", config={})

        # 1mV分辨率
        quantized = piezo._quantize_voltage(75.1234)

        assert quantized == 75.123

    def test_quantize_voltage_custom_resolution(self):
        """测试自定义分辨率量化。"""
        piezo = PiezoController(
            device_id="test_piezo",
            config={"voltage_resolution_v": 0.01},
        )

        # 10mV分辨率
        quantized = piezo._quantize_voltage(75.123)

        assert quantized == 75.12

    def test_quantize_voltage_boundary(self):
        """测试边界值量化。"""
        piezo = PiezoController(device_id="test_piezo", config={})

        # 超出最大值的量化
        quantized = piezo._quantize_voltage(200.0)

        assert quantized == 150.0  # 限制到最大值

        # 超出最小值的量化
        quantized = piezo._quantize_voltage(-10.0)

        assert quantized == 0.0  # 限制到最小值


class TestCalibrationPointSorting:
    """测试校准点排序。"""

    @pytest.mark.asyncio
    async def test_calibration_points_sorted_by_voltage(self):
        """测试校准点按电压排序。"""
        piezo = PiezoController(device_id="test_piezo", config={})

        # 乱序添加校准点
        await piezo.add_calibration_point(voltage_v=150.0, displacement_um=100.0)
        await piezo.add_calibration_point(voltage_v=0.0, displacement_um=0.0)
        await piezo.add_calibration_point(voltage_v=75.0, displacement_um=50.0)

        # 验证排序
        voltages = [p.voltage_v for p in piezo._calibration_data.points]
        assert voltages == [0.0, 75.0, 150.0]


class TestPiecewiseInterpolation:
    """测试分段线性插值。"""

    def test_piecewise_interpolate_within_segment(self):
        """测试段内插值。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo._calibration_data.points = [
            CalibrationPoint(voltage_v=0.0, displacement_um=0.0),
            CalibrationPoint(voltage_v=75.0, displacement_um=50.0),
            CalibrationPoint(voltage_v=150.0, displacement_um=100.0),
        ]

        # 在第一段内插值
        result = piezo._piecewise_interpolate(37.5, "voltage_to_displacement")

        assert abs(result - 25.0) < 0.1

    def test_piecewise_interpolate_boundary_low(self):
        """测试低于最小值的边界处理。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo._calibration_data.points = [
            CalibrationPoint(voltage_v=50.0, displacement_um=30.0),
            CalibrationPoint(voltage_v=150.0, displacement_um=100.0),
        ]

        result = piezo._piecewise_interpolate(25.0, "voltage_to_displacement")

        assert result == 30.0  # 返回最小值

    def test_piecewise_interpolate_boundary_high(self):
        """测试高于最大值的边界处理。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo._calibration_data.points = [
            CalibrationPoint(voltage_v=0.0, displacement_um=0.0),
            CalibrationPoint(voltage_v=100.0, displacement_um=70.0),
        ]

        result = piezo._piecewise_interpolate(150.0, "voltage_to_displacement")

        assert result == 70.0  # 返回最大值


class TestPolynomialInverse:
    """测试多项式逆变换。"""

    def test_solve_polynomial_inverse_linear(self):
        """测试线性多项式逆变换。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        # 线性系数：displacement = 0.667 * voltage + 0
        piezo._calibration_data.coefficients = [0.667, 0.0]

        voltage = piezo._solve_polynomial_inverse(50.0)

        assert abs(voltage - 75.0) < 1.0

    def test_solve_polynomial_inverse_cubic(self):
        """测试三次多项式逆变换。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        # 三次多项式系数
        piezo._calibration_data.coefficients = [0.00001, -0.001, 0.7, 0.0]

        voltage = piezo._solve_polynomial_inverse(50.0)

        # 应该在合理范围内
        assert 0 <= voltage <= 150


class TestEdgeCases:
    """测试边界情况。"""

    @pytest.mark.asyncio
    async def test_set_voltage_at_resolution_limit(self):
        """测试设置分辨率极限电压。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo.status = DeviceStatus.READY

        # 设置最小分辨率电压
        result = await piezo.set_voltage(0.001)

        assert result is True
        assert piezo._current_voltage == 0.001

    @pytest.mark.asyncio
    async def test_set_displacement_at_resolution_limit(self):
        """测试设置分辨率极限位移。"""
        piezo = PiezoController(
            device_id="test_piezo",
            config={"displacement_resolution_nm": 1.0},
        )
        piezo.status = DeviceStatus.READY

        # 设置最小位移（假设1nm = 0.001μm）
        result = await piezo.set_displacement(0.001)

        assert result is True

    @pytest.mark.asyncio
    async def test_calibration_with_duplicate_points(self):
        """测试重复校准点。"""
        piezo = PiezoController(device_id="test_piezo", config={})

        # 添加重复点
        await piezo.add_calibration_point(voltage_v=75.0, displacement_um=50.0)
        await piezo.add_calibration_point(voltage_v=75.0, displacement_um=50.0)

        # 校准应该仍然成功
        result = await piezo.perform_calibration(CalibrationType.LINEAR)

        # 由于点重复，可能无法正确拟合
        # 这里主要测试不会崩溃

    @pytest.mark.asyncio
    async def test_multiple_voltage_changes(self):
        """测试连续多次电压变化。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo.status = DeviceStatus.READY

        # 连续设置不同电压
        for voltage in [10.0, 50.0, 100.0, 75.0, 25.0]:
            result = await piezo.set_voltage(voltage)
            assert result is True

        # 验证最终电压
        assert piezo._current_voltage == 25.0


class TestIntegration:
    """集成测试。"""

    @pytest.mark.asyncio
    async def test_full_calibration_workflow(self):
        """测试完整校准工作流。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo.status = DeviceStatus.READY

        # 1. 连接设备
        result = await piezo.connect()
        assert result is True

        # 2. 添加校准点
        await piezo.add_calibration_point(voltage_v=0.0, displacement_um=0.0)
        await piezo.add_calibration_point(voltage_v=50.0, displacement_um=32.0)
        await piezo.add_calibration_point(voltage_v=100.0, displacement_um=68.0)
        await piezo.add_calibration_point(voltage_v=150.0, displacement_um=100.0)

        # 3. 执行多项式校准
        result = await piezo.perform_calibration(CalibrationType.POLYNOMIAL)
        assert result is True

        # 4. 设置位移
        result = await piezo.set_displacement(50.0)
        assert result is True

        # 5. 验证电压在合理范围
        assert 0 < piezo._current_voltage < 150

        # 6. 读取状态
        status = await piezo.read_status()
        assert status["calibration_valid"] is True
        assert status["calibration_points"] == 4

    @pytest.mark.asyncio
    async def test_open_loop_control_workflow(self):
        """测试开环控制工作流。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo.status = DeviceStatus.READY

        # 设置开环模式
        await piezo.set_control_mode(ControlMode.OPEN_LOOP)

        # 通过电压控制
        await piezo.set_voltage(75.0)
        assert piezo._current_voltage == 75.0

        # 步进控制
        await piezo.step_voltage(10.0)
        assert piezo._current_voltage == 85.0

        # 归零
        await piezo.zero()
        assert piezo._current_voltage == 0.0

    @pytest.mark.asyncio
    async def test_closed_loop_control_workflow(self):
        """测试闭环控制工作流。"""
        piezo = PiezoController(device_id="test_piezo", config={})
        piezo.status = DeviceStatus.READY

        # 添加校准
        await piezo.add_calibration_point(voltage_v=0.0, displacement_um=0.0)
        await piezo.add_calibration_point(voltage_v=150.0, displacement_um=100.0)
        await piezo.perform_calibration(CalibrationType.LINEAR)

        # 设置闭环模式
        await piezo.set_control_mode(ControlMode.CLOSED_LOOP)

        # 通过位移控制
        await piezo.set_displacement(50.0)
        assert abs(piezo._current_voltage - 75.0) < 0.5

        # 步进控制
        await piezo.step_displacement(10.0)
        assert abs(piezo._target_displacement - 60.0) < 0.01

        # 最大伸展
        await piezo.max_extend()
        assert piezo._current_voltage == 150.0
