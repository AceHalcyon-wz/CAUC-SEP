"""
测试DM2C步进驱动器驱动

测试内容：
- 初始化和配置
- 连接/断开
- 绝对/相对定位
- JOG点动模式
- 回零操作
- 状态字解析(0x1003)
- 报警代码读取(0x2203)
- 报警信息本地化
- 报警清除功能
- PR路径配置和触发
- 急停和复位
- 参数保存/恢复
- 软件限位检查
"""

from unittest.mock import MagicMock, patch

import pytest

from core.abstract import DeviceStatus
from core.dm2c_driver import (
    ALARM_CODES,
    ALARM_INFO_MAP,
    CMD_CLEAR_ALARM,
    CMD_FACTORY_RESET,
    CMD_JOG_NEG,
    CMD_JOG_POS,
    CMD_JOG_STOP,
    CMD_RESET_ALARM,
    CMD_SAVE_PARAM,
    CMD_TRIGGER_HOME,
    DEFAULT_STEPS_PER_MM,
    DI_CONFIG_ADDRS,
    DI_FUNCTIONS,
    DO_CONFIG_ADDRS,
    DO_FUNCTIONS,
    HOME_DIRECTION_NEGATIVE,
    HOME_DIRECTION_POSITIVE,
    HOME_MODE_DOUBLE_LIMIT,
    HOME_MODE_ENCODER_Z,
    HOME_MODE_EXTERNAL_SIGNAL,
    HOME_MODE_SINGLE_LIMIT,
    PR_PATH_BASE_ADDR,
    PR_PATH_ENTRY_SIZE,
    REG_DI_STATUS,
    REG_DO_STATUS,
    REG_HOME_DIRECTION,
    REG_HOME_MODE,
    REG_HOME_OFFSET,
    REG_HOME_SPEED_HIGH,
    REG_HOME_SPEED_LOW,
    STATUS_CMD_COMPLETE_BIT,
    STATUS_ENABLE_BIT,
    STATUS_FAULT_BIT,
    STATUS_HOME_COMPLETE_BIT,
    STATUS_INVALID_BIT,
    STATUS_PATH_COMPLETE_BIT,
    STATUS_RUNNING_BIT,
    TRIGGER_EMERGENCY_STOP,
    TRIGGER_HOME,
    AlarmInfo,
    AlarmSeverity,
    LeadshineDM2C,
    get_alarm_info,
    mm_to_steps,
    steps_to_mm,
)


class TestUnitConversion:
    """测试单位转换函数。"""

    def test_mm_to_steps_default(self):
        """测试毫米转步数（默认参数）。"""
        assert mm_to_steps(1.0) == 1600
        assert mm_to_steps(0.0) == 0
        assert mm_to_steps(10.0) == 16000
        assert mm_to_steps(-5.0) == -8000

    def test_mm_to_steps_custom(self):
        """测试毫米转步数（自定义参数）。"""
        assert mm_to_steps(1.0, steps_per_mm=800) == 800
        assert mm_to_steps(1.0, steps_per_mm=3200) == 3200

    def test_steps_to_mm_default(self):
        """测试步数转毫米（默认参数）。"""
        assert steps_to_mm(1600) == 1.0
        assert steps_to_mm(0) == 0.0
        assert steps_to_mm(16000) == 10.0
        assert steps_to_mm(-8000) == -5.0

    def test_steps_to_mm_custom(self):
        """测试步数转毫米（自定义参数）。"""
        assert steps_to_mm(800, steps_per_mm=800) == 1.0
        assert steps_to_mm(3200, steps_per_mm=3200) == 1.0

    def test_round_trip_conversion(self):
        """测试往返转换精度。"""
        for mm in [0.0, 1.0, 10.5, -5.25, 100.0]:
            steps = mm_to_steps(mm)
            mm_back = steps_to_mm(steps)
            assert abs(mm_back - mm) < 0.001


class TestAlarmCodes:
    """测试报警代码映射。"""

    def test_alarm_codes_exist(self):
        """测试报警代码存在。"""
        assert 0x01 in ALARM_CODES
        assert 0x02 in ALARM_CODES
        assert 0x80 in ALARM_CODES
        assert 0x200 in ALARM_CODES

    def test_alarm_codes_descriptions(self):
        """测试报警代码描述。"""
        assert ALARM_CODES[0x01] == "过流"
        assert ALARM_CODES[0x02] == "过压"
        assert ALARM_CODES[0x80] == "锁轴（缺相）故障"
        assert ALARM_CODES[0x200] == "EEPROM故障"


class TestAlarmInfoMap:
    """测试报警信息映射表。"""

    def test_alarm_info_map_completeness(self):
        """测试报警信息映射表完整性。"""
        # 验证所有ALARM_CODES中的代码都有对应的详细信息
        for code in ALARM_CODES.keys():
            assert code in ALARM_INFO_MAP, f"Missing alarm info for code 0x{code:04X}"

    def test_alarm_info_structure(self):
        """测试报警信息数据结构。"""
        for code, info in ALARM_INFO_MAP.items():
            assert isinstance(info, AlarmInfo)
            assert info.code == code
            assert isinstance(info.name_zh, str) and len(info.name_zh) > 0
            assert isinstance(info.name_en, str) and len(info.name_en) > 0
            assert isinstance(info.description_zh, str) and len(info.description_zh) > 0
            assert isinstance(info.description_en, str) and len(info.description_en) > 0
            assert isinstance(info.severity, AlarmSeverity)
            assert isinstance(info.possible_causes, list) and len(info.possible_causes) > 0
            assert isinstance(info.solutions, list) and len(info.solutions) > 0

    def test_alarm_severity_classification(self):
        """测试报警严重程度分类。"""
        # 严重报警
        critical_alarms = [0x01, 0x02, 0x40, 0x80]
        for code in critical_alarms:
            assert ALARM_INFO_MAP[code].severity == AlarmSeverity.CRITICAL

        # 警告
        warning_alarms = [0x100, 0x200, 0x210]
        for code in warning_alarms:
            assert ALARM_INFO_MAP[code].severity == AlarmSeverity.WARNING


class TestGetAlarmInfo:
    """测试get_alarm_info函数。"""

    def test_get_alarm_info_no_alarm_zh(self):
        """测试无报警时的中文信息。"""
        result = get_alarm_info(0, language="zh")

        assert result["code"] == 0
        assert result["name"] == "无报警"
        assert result["description"] == "设备运行正常"
        assert result["severity"] == AlarmSeverity.INFO.value
        assert result["possible_causes"] == []
        assert result["solutions"] == []

    def test_get_alarm_info_no_alarm_en(self):
        """测试无报警时的英文信息。"""
        result = get_alarm_info(0, language="en")

        assert result["code"] == 0
        assert result["name"] == "No Alarm"
        assert result["description"] == "Device operating normally"
        assert result["severity"] == AlarmSeverity.INFO.value

    def test_get_alarm_info_over_current_zh(self):
        """测试过流报警中文信息。"""
        result = get_alarm_info(0x01, language="zh")

        assert result["code"] == 0x01
        assert result["name"] == "过流保护"
        assert "电机电流超过额定值" in result["description"]
        assert result["severity"] == AlarmSeverity.CRITICAL.value
        assert len(result["possible_causes"]) > 0
        assert len(result["solutions"]) > 0

    def test_get_alarm_info_over_current_en(self):
        """测试过流报警英文信息。"""
        result = get_alarm_info(0x01, language="en")

        assert result["code"] == 0x01
        assert result["name"] == "Over Current Protection"
        assert "Motor current exceeds" in result["description"]
        assert result["severity"] == AlarmSeverity.CRITICAL.value

    def test_get_alarm_info_over_voltage_zh(self):
        """测试过压报警中文信息。"""
        result = get_alarm_info(0x02, language="zh")

        assert result["code"] == 0x02
        assert result["name"] == "过压保护"
        assert "直流母线电压超过安全阈值" in result["description"]
        assert result["severity"] == AlarmSeverity.CRITICAL.value

    def test_get_alarm_info_eeprom_fault_zh(self):
        """测试EEPROM故障中文信息。"""
        result = get_alarm_info(0x200, language="zh")

        assert result["code"] == 0x200
        assert result["name"] == "EEPROM故障"
        assert "EEPROM读写异常" in result["description"]
        assert result["severity"] == AlarmSeverity.WARNING.value

    def test_get_alarm_info_unknown_alarm_zh(self):
        """测试未知报警中文信息。"""
        unknown_code = 0x9999
        result = get_alarm_info(unknown_code, language="zh")

        assert result["code"] == unknown_code
        assert "未知报警" in result["name"]
        assert "未定义的报警代码" in result["description"]
        assert result["severity"] == AlarmSeverity.WARNING.value
        assert "联系技术支持" in result["solutions"]

    def test_get_alarm_info_unknown_alarm_en(self):
        """测试未知报警英文信息。"""
        unknown_code = 0x9999
        result = get_alarm_info(unknown_code, language="en")

        assert result["code"] == unknown_code
        assert "Unknown Alarm" in result["name"]
        assert "Undefined alarm code" in result["description"]
        assert "Contact technical support" in result["solutions"]


class TestAlarmLocalization:
    """测试报警描述本地化。"""

    def test_all_alarms_have_zh_and_en(self):
        """测试所有报警都有中英文描述。"""
        for code, info in ALARM_INFO_MAP.items():
            # 中文检查
            assert info.name_zh, f"Missing Chinese name for alarm 0x{code:04X}"
            assert info.description_zh, f"Missing Chinese description for alarm 0x{code:04X}"

            # 英文检查
            assert info.name_en, f"Missing English name for alarm 0x{code:04X}"
            assert info.description_en, f"Missing English description for alarm 0x{code:04X}"

    def test_localization_consistency(self):
        """测试本地化一致性。"""
        for code, info in ALARM_INFO_MAP.items():
            zh_result = get_alarm_info(code, language="zh")
            en_result = get_alarm_info(code, language="en")

            # 代码和严重程度应该一致
            assert zh_result["code"] == en_result["code"]
            assert zh_result["severity"] == en_result["severity"]

            # 名称和描述应该不同（不同语言）
            assert zh_result["name"] != en_result["name"]
            assert zh_result["description"] != en_result["description"]


class TestAlarmClearCommand:
    """测试报警清除命令。"""

    def test_clear_alarm_command_value(self):
        """测试报警清除命令值。"""
        # 根据DM2C-RS556用户手册V1.8，报警清除命令为0x0001
        assert CMD_CLEAR_ALARM == 0x0001

    def test_clear_alarm_vs_reset_alarm(self):
        """测试清除报警与复位报警命令的区别。"""
        # 新版清除命令
        assert CMD_CLEAR_ALARM == 0x0001
        # 旧版复位命令（向后兼容）
        assert CMD_RESET_ALARM == 0x1111


class TestStatusBits:
    """测试状态字位定义。"""

    def test_status_bits_values(self):
        """测试状态字位值（基于DM2C-RS556用户手册V1.8）。"""
        assert STATUS_FAULT_BIT == 0x01  # Bit0: 故障位
        assert STATUS_ENABLE_BIT == 0x02  # Bit1: 使能位
        assert STATUS_RUNNING_BIT == 0x04  # Bit2: 运行位
        assert STATUS_INVALID_BIT == 0x08  # Bit3: 无效位
        assert STATUS_CMD_COMPLETE_BIT == 0x10  # Bit4: 指令完成位
        assert STATUS_PATH_COMPLETE_BIT == 0x20  # Bit5: 路径完成位
        assert STATUS_HOME_COMPLETE_BIT == 0x40  # Bit6: 回零完成位

    def test_status_bits_no_overlap(self):
        """测试状态字位不重叠。"""
        bits = [
            STATUS_FAULT_BIT,
            STATUS_ENABLE_BIT,
            STATUS_RUNNING_BIT,
            STATUS_INVALID_BIT,
            STATUS_CMD_COMPLETE_BIT,
            STATUS_PATH_COMPLETE_BIT,
            STATUS_HOME_COMPLETE_BIT,
        ]
        for i, bit1 in enumerate(bits):
            for bit2 in bits[i + 1 :]:
                assert bit1 & bit2 == 0


class TestCommandCodes:
    """测试控制命令代码。"""

    def test_command_codes(self):
        """测试命令代码值。"""
        assert CMD_JOG_POS == 0x4001
        assert CMD_JOG_NEG == 0x4002
        assert CMD_JOG_STOP == 0x4000
        assert CMD_RESET_ALARM == 0x1111
        assert CMD_SAVE_PARAM == 0x2211
        assert CMD_FACTORY_RESET == 0x2233
        assert TRIGGER_HOME == 0x020
        assert TRIGGER_EMERGENCY_STOP == 0x040


class TestPRPathConstants:
    """测试PR路径常量。"""

    def test_pr_path_constants(self):
        """测试PR路径常量。"""
        assert PR_PATH_BASE_ADDR == 0x6200
        assert PR_PATH_ENTRY_SIZE == 8


class TestLeadshineDM2CInit:
    """测试DM2C初始化。"""

    def test_default_initialization(self):
        """测试默认初始化。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            assert driver.device_id == "test_motor"
            assert driver.port == "COM1"
            assert driver.slave_id == 1
            assert driver.baudrate == 115200
            assert driver.steps_per_mm == DEFAULT_STEPS_PER_MM
            assert driver.status == DeviceStatus.DISCONNECTED
            assert driver._current_position == 0
            assert driver._alarm_code == 0

    def test_custom_initialization(self):
        """测试自定义初始化。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(
                device_id="custom_motor",
                config={"port": "COM3", "slave_id": 2, "baudrate": 9600, "steps_per_mm": 3200},
            )

            assert driver.device_id == "custom_motor"
            assert driver.port == "COM3"
            assert driver.slave_id == 2
            assert driver.baudrate == 9600
            assert driver.steps_per_mm == 3200

    def test_limit_config_initialization(self):
        """测试限位配置初始化。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            assert driver.limit_config.positive_limit == 100.0
            assert driver.limit_config.negative_limit == -100.0
            assert driver.limit_config.enable is True


class TestLeadshineDM2CConnection:
    """测试DM2C连接管理。"""

    @pytest.mark.asyncio
    async def test_connect_simulation_mode(self):
        """测试仿真模式连接。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            result = await driver.connect()

            assert result is True
            assert driver.status == DeviceStatus.READY

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """测试断开连接。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.status = DeviceStatus.READY

            result = await driver.disconnect()

            assert result is True
            assert driver.status == DeviceStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_connect_with_mock_modbus(self, mock_modbus_client):
        """测试使用Mock Modbus连接。"""
        # 模拟pymodbus可用
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            # 模拟ModbusSerialClient类
            mock_modbus_class = MagicMock()
            mock_modbus_class.return_value = mock_modbus_client
            mock_modbus_client.connect.return_value = True

            # 在模块中注入Mock类
            import core.dm2c_driver as driver_module

            original_modbus = getattr(driver_module, "ModbusSerialClient", None)
            driver_module.ModbusSerialClient = mock_modbus_class

            try:
                driver = LeadshineDM2C(device_id="test_motor", config={"port": "COM_TEST"})
                result = await driver.connect()

                assert result is True
                assert driver.status == DeviceStatus.READY
                mock_modbus_client.connect.assert_called_once()
            finally:
                # 恢复原始状态
                if original_modbus is not None:
                    driver_module.ModbusSerialClient = original_modbus
                elif hasattr(driver_module, "ModbusSerialClient"):
                    delattr(driver_module, "ModbusSerialClient")


class TestLeadshineDM2CMovement:
    """测试DM2C运动控制。"""

    @pytest.mark.asyncio
    async def test_move_abs_simulation(self):
        """测试仿真模式绝对定位。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.status = DeviceStatus.READY

            result = await driver.move_abs(position=10.0, speed=5.0, accel=1000.0, decel=1000.0)

            assert result is True
            assert driver._current_position == mm_to_steps(10.0)

    @pytest.mark.asyncio
    async def test_move_abs_soft_limit_exceeded(self):
        """测试绝对定位超出软件限位。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.limit_config.positive_limit = 50.0
            driver.status = DeviceStatus.READY

            result = await driver.move_abs(position=100.0, speed=5.0, accel=1000.0, decel=1000.0)

            assert result is False

    @pytest.mark.asyncio
    async def test_move_rel_simulation(self):
        """测试仿真模式相对定位。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.status = DeviceStatus.READY
            driver._current_position = mm_to_steps(10.0)

            result = await driver.move_rel(distance=5.0, speed=5.0, accel=1000.0, decel=1000.0)

            assert result is True
            assert driver._current_position == mm_to_steps(15.0)


class TestLeadshineDM2CJOG:
    """测试DM2C JOG功能。"""

    @pytest.mark.asyncio
    async def test_jog_positive_simulation(self):
        """测试仿真模式正向JOG。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.status = DeviceStatus.READY
            initial_pos = driver._current_position

            result = await driver.jog(direction=1, speed=5.0)

            assert result is True
            assert driver._current_position > initial_pos

    @pytest.mark.asyncio
    async def test_jog_negative_simulation(self):
        """测试仿真模式负向JOG。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.status = DeviceStatus.READY
            initial_pos = driver._current_position

            result = await driver.jog(direction=-1, speed=5.0)

            assert result is True
            assert driver._current_position < initial_pos

    @pytest.mark.asyncio
    async def test_jog_stop_simulation(self):
        """测试仿真模式停止JOG。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.status = DeviceStatus.READY

            result = await driver.jog_stop()

            assert result is True

    @pytest.mark.asyncio
    async def test_set_jog_speed_simulation(self):
        """测试仿真模式设置JOG速度。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            result = await driver.set_jog_speed(speed=10.0)

            assert result is True

    @pytest.mark.asyncio
    async def test_set_jog_acceleration_simulation(self):
        """测试仿真模式设置JOG加减速。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            result = await driver.set_jog_acceleration(accel_time=200, decel_time=200)

            assert result is True

    @pytest.mark.asyncio
    async def test_jog_with_mock(self, mock_modbus_client):
        """测试使用Mock执行JOG。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            # Mock写寄存器成功
            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_modbus_client.write_register.return_value = mock_result

            result = await driver.jog(direction=1, speed=5.0)

            assert result is True
            # 验证调用了两次写寄存器：速度和控制字
            assert mock_modbus_client.write_register.call_count == 2

    @pytest.mark.asyncio
    async def test_jog_stop_with_mock(self, mock_modbus_client):
        """测试使用Mock停止JOG。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_modbus_client.write_register.return_value = mock_result

            result = await driver.jog_stop()

            assert result is True
            mock_modbus_client.write_register.assert_called_once_with(
                LeadshineDM2C.REG_CONTROL_WORD, CMD_JOG_STOP, slave=1
            )

    @pytest.mark.asyncio
    async def test_set_jog_speed_with_mock(self, mock_modbus_client):
        """测试使用Mock设置JOG速度。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_modbus_client.write_register.return_value = mock_result

            result = await driver.set_jog_speed(speed=10.0)

            assert result is True
            expected_speed_steps = int(10.0 * DEFAULT_STEPS_PER_MM)
            mock_modbus_client.write_register.assert_called_once_with(
                LeadshineDM2C.REG_JOG_SPEED, expected_speed_steps, slave=1
            )

    @pytest.mark.asyncio
    async def test_set_jog_acceleration_with_mock(self, mock_modbus_client):
        """测试使用Mock设置JOG加减速。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_modbus_client.write_register.return_value = mock_result

            result = await driver.set_jog_acceleration(accel_time=200, decel_time=150)

            assert result is True
            assert mock_modbus_client.write_register.call_count == 2

    @pytest.mark.asyncio
    async def test_jog_registers_address(self):
        """测试JOG寄存器地址正确性。"""
        assert LeadshineDM2C.REG_JOG_SPEED == 0x01E1
        assert LeadshineDM2C.REG_JOG_ACCEL_TIME == 0x01E7
        assert LeadshineDM2C.REG_JOG_DECEL_TIME == 0x01E8

    @pytest.mark.asyncio
    async def test_home_simulation(self):
        """测试仿真模式回零。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.status = DeviceStatus.READY
            driver._current_position = mm_to_steps(50.0)

            result = await driver.home()

            assert result is True
            assert driver._current_position == 0


class TestLeadshineDM2CStop:
    """测试DM2C停止控制。"""

    @pytest.mark.asyncio
    async def test_normal_stop_simulation(self):
        """测试仿真模式正常停止。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.status = DeviceStatus.BUSY

            result = await driver.stop(emergency=False)

            assert result is True

    @pytest.mark.asyncio
    async def test_emergency_stop_simulation(self):
        """测试仿真模式急停。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.status = DeviceStatus.BUSY

            result = await driver.stop(emergency=True)

            assert result is True
            assert driver.status == DeviceStatus.EMERGENCY_STOP

    @pytest.mark.asyncio
    async def test_emergency_stop_alias(self):
        """测试急停别名方法。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.status = DeviceStatus.READY

            result = await driver.emergency_stop()

            assert result is True
            assert driver.status == DeviceStatus.EMERGENCY_STOP

    @pytest.mark.asyncio
    async def test_reset_emergency(self):
        """测试复位急停状态。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.status = DeviceStatus.EMERGENCY_STOP

            result = await driver.reset_emergency()

            assert result is True
            assert driver.status == DeviceStatus.READY


class TestLeadshineDM2CPosition:
    """测试DM2C位置读取。"""

    @pytest.mark.asyncio
    async def test_read_position_simulation(self):
        """测试仿真模式读取位置。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver._current_position = mm_to_steps(25.5)

            result = await driver.read_position()

            assert "position_steps" in result
            assert "position_mm" in result
            assert result["position_steps"] == mm_to_steps(25.5)
            assert abs(result["position_mm"] - 25.5) < 0.001


class TestLeadshineDM2CStatus:
    """测试DM2C状态读取。"""

    @pytest.mark.asyncio
    async def test_read_status_word_simulation(self):
        """测试仿真模式读取状态字。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            result = await driver.read_status_word()

            assert "fault" in result
            assert "enabled" in result
            assert "running" in result
            assert "invalid" in result
            assert "cmd_complete" in result
            assert "path_complete" in result
            assert "home_complete" in result
            assert "raw_value" in result

    @pytest.mark.asyncio
    async def test_read_status_word_with_mock(self, mock_modbus_client):
        """测试使用Mock读取状态字。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_result.registers = [0x72]
            mock_modbus_client.read_holding_registers.return_value = mock_result

            result = await driver.read_status_word()

            assert result["fault"] is False
            assert result["enabled"] is True
            assert result["running"] is False
            assert result["invalid"] is False
            assert result["cmd_complete"] is True
            assert result["path_complete"] is True
            assert result["home_complete"] is True
            assert result["raw_value"] == 0x72

    @pytest.mark.asyncio
    async def test_read_status_word_invalid_bit(self, mock_modbus_client):
        """测试状态字无效位(Bit3)解析。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_result.registers = [0x0A]
            mock_modbus_client.read_holding_registers.return_value = mock_result

            result = await driver.read_status_word()

            assert result["fault"] is False
            assert result["enabled"] is True
            assert result["running"] is False
            assert result["invalid"] is True
            assert result["raw_value"] == 0x0A

    @pytest.mark.asyncio
    async def test_read_status_word_all_bits(self, mock_modbus_client):
        """测试状态字所有位解析。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_result.registers = [0x7F]
            mock_modbus_client.read_holding_registers.return_value = mock_result

            result = await driver.read_status_word()

            assert result["fault"] is True
            assert result["enabled"] is True
            assert result["running"] is True
            assert result["invalid"] is True
            assert result["cmd_complete"] is True
            assert result["path_complete"] is True
            assert result["home_complete"] is True
            assert result["raw_value"] == 0x7F

    @pytest.mark.asyncio
    async def test_read_status_word_cmd_complete_bit(self, mock_modbus_client):
        """测试状态字指令完成位(Bit4)解析。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_result.registers = [0x12]
            mock_modbus_client.read_holding_registers.return_value = mock_result

            result = await driver.read_status_word()

            assert result["fault"] is False
            assert result["enabled"] is True
            assert result["cmd_complete"] is True
            assert result["raw_value"] == 0x12

    @pytest.mark.asyncio
    async def test_read_status_word_path_complete_bit(self, mock_modbus_client):
        """测试状态字路径完成位(Bit5)解析。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_result.registers = [0x22]
            mock_modbus_client.read_holding_registers.return_value = mock_result

            result = await driver.read_status_word()

            assert result["fault"] is False
            assert result["enabled"] is True
            assert result["path_complete"] is True
            assert result["raw_value"] == 0x22

    @pytest.mark.asyncio
    async def test_read_status_word_home_complete_bit(self, mock_modbus_client):
        """测试状态字回零完成位(Bit6)解析。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_result.registers = [0x42]
            mock_modbus_client.read_holding_registers.return_value = mock_result

            result = await driver.read_status_word()

            assert result["fault"] is False
            assert result["enabled"] is True
            assert result["home_complete"] is True
            assert result["raw_value"] == 0x42

    @pytest.mark.asyncio
    async def test_read_alarm_code_simulation(self):
        """测试仿真模式读取报警代码。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            result = await driver.read_alarm_code()

            assert result == 0

    @pytest.mark.asyncio
    async def test_read_alarm_code_with_mock(self, mock_modbus_client):
        """测试使用Mock读取报警代码。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_result.registers = [0x01]
            mock_modbus_client.read_holding_registers.return_value = mock_result

            result = await driver.read_alarm_code()

            assert result == 0x01

    @pytest.mark.asyncio
    async def test_read_full_status(self):
        """测试读取完整状态。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.status = DeviceStatus.READY
            driver._current_position = mm_to_steps(10.0)

            result = await driver.read_status()

            assert result["device_id"] == "test_motor"
            assert result["status"] == "ready"
            assert "position_steps" in result
            assert "position_mm" in result
            assert "alarm_code" in result
            assert "alarm_text" in result
            assert "status_word" in result
            assert "limit_positive" in result
            assert "limit_negative" in result
            assert "connected" in result


class TestLeadshineDM2CAlarmReset:
    """测试DM2C报警复位。"""

    @pytest.mark.asyncio
    async def test_reset_alarm_simulation(self):
        """测试仿真模式报警复位。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver._alarm_code = 0x01
            driver.status = DeviceStatus.ERROR

            result = await driver.reset_alarm()

            assert result is True
            assert driver._alarm_code == 0
            assert driver.status == DeviceStatus.READY


class TestLeadshineDM2CParameters:
    """测试DM2C参数管理。"""

    @pytest.mark.asyncio
    async def test_save_parameters_simulation(self):
        """测试仿真模式保存参数。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            result = await driver.save_parameters()

            assert result is True

    @pytest.mark.asyncio
    async def test_factory_reset_simulation(self):
        """测试仿真模式恢复出厂设置。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            result = await driver.factory_reset()

            assert result is True


class TestLeadshineDM2CPRPath:
    """测试DM2C PR路径配置。"""

    @pytest.mark.asyncio
    async def test_configure_pr_path_simulation(self):
        """测试仿真模式配置PR路径。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            result = await driver.configure_pr_path(
                path_number=0,
                mode=1,
                position=16000,
                velocity=1000,
                accel_time=100,
                decel_time=100,
                dwell_time=0,
                special_param=0,
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_configure_pr_path_invalid_number(self):
        """测试配置无效PR路径编号。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            result = await driver.configure_pr_path(
                path_number=16, mode=1, position=16000, velocity=1000
            )

            assert result is False

            result = await driver.configure_pr_path(
                path_number=-1, mode=1, position=16000, velocity=1000
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_trigger_pr_path_simulation(self):
        """测试仿真模式触发PR路径。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            result = await driver.trigger_pr_path(path_number=0)

            assert result is True

    @pytest.mark.asyncio
    async def test_trigger_pr_path_invalid_number(self):
        """测试触发无效PR路径编号。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            result = await driver.trigger_pr_path(path_number=16)

            assert result is False

            result = await driver.trigger_pr_path(path_number=-1)

            assert result is False

    @pytest.mark.asyncio
    async def test_configure_pr_path_with_mock(self, mock_modbus_client):
        """测试使用Mock配置PR路径。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_modbus_client.write_registers.return_value = mock_result

            result = await driver.configure_pr_path(
                path_number=5, mode=1, position=32000, velocity=2000, accel_time=150, decel_time=150
            )

            assert result is True

            expected_addr = PR_PATH_BASE_ADDR + 5 * PR_PATH_ENTRY_SIZE
            mock_modbus_client.write_registers.assert_called_once()
            call_args = mock_modbus_client.write_registers.call_args
            assert call_args[0][0] == expected_addr

    @pytest.mark.asyncio
    async def test_configure_pr_path_full_8_parameters(self, mock_modbus_client):
        """
        测试完整8参数PR路径配置。

        验证所有参数按正确顺序写入：
        - 偏移0: 模式
        - 偏移1: 位置高字
        - 偏移2: 位置低字
        - 偏移3: 速度
        - 偏移4: 加速时间
        - 偏移5: 减速时间
        - 偏移6: 停留时间
        - 偏移7: 特殊参数
        """
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_modbus_client.write_registers.return_value = mock_result

            # 测试位置：0x00012345 (74565步)
            test_position = 0x00012345
            pos_high = (test_position >> 16) & 0xFFFF  # 0x0001
            pos_low = test_position & 0xFFFF  # 0x2345

            result = await driver.configure_pr_path(
                path_number=3,
                mode=2,
                position=test_position,
                velocity=5000,
                accel_time=200,
                decel_time=300,
                dwell_time=1000,
                special_param=5,
            )

            assert result is True

            # 验证写入地址
            expected_addr = PR_PATH_BASE_ADDR + 3 * PR_PATH_ENTRY_SIZE
            call_args = mock_modbus_client.write_registers.call_args
            assert call_args[0][0] == expected_addr

            # 验证写入值顺序
            written_values = call_args[0][1]
            assert written_values[0] == 2  # 模式
            assert written_values[1] == pos_high  # 位置高字
            assert written_values[2] == pos_low  # 位置低字
            assert written_values[3] == 5000  # 速度
            assert written_values[4] == 200  # 加速时间
            assert written_values[5] == 300  # 减速时间
            assert written_values[6] == 1000  # 停留时间
            assert written_values[7] == 5  # 特殊参数

    @pytest.mark.asyncio
    async def test_configure_pr_path_negative_position(self, mock_modbus_client):
        """测试配置负位置PR路径。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_modbus_client.write_registers.return_value = mock_result

            # 负位置：-10000步
            negative_position = -10000
            # 转换为无符号32位
            unsigned_position = negative_position & 0xFFFFFFFF
            pos_high = (unsigned_position >> 16) & 0xFFFF
            pos_low = unsigned_position & 0xFFFF

            result = await driver.configure_pr_path(
                path_number=0, mode=1, position=negative_position, velocity=1000
            )

            assert result is True

            call_args = mock_modbus_client.write_registers.call_args
            written_values = call_args[0][1]
            assert written_values[1] == pos_high
            assert written_values[2] == pos_low

    @pytest.mark.asyncio
    async def test_trigger_pr_path_with_mock(self, mock_modbus_client):
        """测试使用Mock触发PR路径。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_modbus_client.write_register.return_value = mock_result

            result = await driver.trigger_pr_path(path_number=7)

            assert result is True

            # 验证触发值：0x0100 | path_number
            expected_trigger = 0x0100 | 7
            mock_modbus_client.write_register.assert_called_once_with(
                driver.REG_TRIGGER, expected_trigger, slave=1
            )

    @pytest.mark.asyncio
    async def test_trigger_pr_path_boundary_values(self, mock_modbus_client):
        """测试PR路径触发边界值。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_modbus_client.write_register.return_value = mock_result

            # 测试路径0
            result = await driver.trigger_pr_path(path_number=0)
            assert result is True
            expected_trigger = 0x0100 | 0
            mock_modbus_client.write_register.assert_called_with(
                driver.REG_TRIGGER, expected_trigger, slave=1
            )

            # 测试路径15
            result = await driver.trigger_pr_path(path_number=15)
            assert result is True
            expected_trigger = 0x0100 | 15
            mock_modbus_client.write_register.assert_called_with(
                driver.REG_TRIGGER, expected_trigger, slave=1
            )

    @pytest.mark.asyncio
    async def test_configure_pr_path_all_16_paths(self, mock_modbus_client):
        """测试配置所有16条PR路径。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_modbus_client.write_registers.return_value = mock_result

            for path_num in range(16):
                result = await driver.configure_pr_path(
                    path_number=path_num,
                    mode=1,
                    position=path_num * 1000,
                    velocity=1000,
                )
                assert result is True

                expected_addr = PR_PATH_BASE_ADDR + path_num * PR_PATH_ENTRY_SIZE
                call_args = mock_modbus_client.write_registers.call_args
                assert call_args[0][0] == expected_addr


class TestLeadshineDM2CSoftLimits:
    """测试DM2C软件限位。"""

    def test_set_soft_limits(self):
        """测试设置软件限位。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            driver.set_soft_limits(positive_mm=50.0, negative_mm=-50.0)

            assert driver.limit_config.positive_limit == 50.0
            assert driver.limit_config.negative_limit == -50.0
            assert driver.limit_config.enable is True

    @pytest.mark.asyncio
    async def test_move_respects_soft_limits(self):
        """测试运动遵守软件限位。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.set_soft_limits(positive_mm=50.0, negative_mm=-50.0)
            driver.status = DeviceStatus.READY

            result = await driver.move_abs(position=40.0, speed=5.0, accel=1000.0, decel=1000.0)
            assert result is True

            result = await driver.move_abs(position=60.0, speed=5.0, accel=1000.0, decel=1000.0)
            assert result is False

            result = await driver.move_abs(position=-40.0, speed=5.0, accel=1000.0, decel=1000.0)
            assert result is True

            result = await driver.move_abs(position=-60.0, speed=5.0, accel=1000.0, decel=1000.0)
            assert result is False


class TestLeadshineDM2CWriteRegister:
    """测试DM2C寄存器写入。"""

    @pytest.mark.asyncio
    async def test_write_register_no_client(self):
        """测试无客户端时写入寄存器。"""
        driver = LeadshineDM2C(device_id="test_motor", config={})
        driver.client = None

        result = await driver._write_register(0x1801, 0x1111)

        assert result is False

    @pytest.mark.asyncio
    async def test_write_register_success(self, mock_modbus_client):
        """测试成功写入寄存器。"""
        driver = LeadshineDM2C(device_id="test_motor", config={})
        driver.client = mock_modbus_client

        mock_result = MagicMock()
        mock_result.isError.return_value = False
        mock_modbus_client.write_register.return_value = mock_result

        result = await driver._write_register(0x1801, 0x1111)

        assert result is True
        mock_modbus_client.write_register.assert_called_once_with(0x1801, 0x1111, slave=1)

    @pytest.mark.asyncio
    async def test_write_register_failure(self, mock_modbus_client):
        """测试写入寄存器失败。"""
        driver = LeadshineDM2C(device_id="test_motor", config={})
        driver.client = mock_modbus_client

        mock_result = MagicMock()
        mock_result.isError.return_value = True
        mock_modbus_client.write_register.return_value = mock_result

        result = await driver._write_register(0x1801, 0x1111)

        assert result is False


class TestHomeModeConstants:
    """测试回零模式常量。"""

    def test_home_mode_values(self):
        """测试回零模式值。"""
        assert HOME_MODE_SINGLE_LIMIT == 0
        assert HOME_MODE_DOUBLE_LIMIT == 1
        assert HOME_MODE_EXTERNAL_SIGNAL == 2
        assert HOME_MODE_ENCODER_Z == 3

    def test_home_direction_values(self):
        """测试回零方向值。"""
        assert HOME_DIRECTION_POSITIVE == 0
        assert HOME_DIRECTION_NEGATIVE == 1

    def test_home_register_addresses(self):
        """测试回零寄存器地址。"""
        assert REG_HOME_MODE == 0x0280
        assert REG_HOME_SPEED_HIGH == 0x0281
        assert REG_HOME_SPEED_LOW == 0x0282
        assert REG_HOME_OFFSET == 0x0283
        assert REG_HOME_DIRECTION == 0x0284

    def test_home_trigger_command(self):
        """测试回零触发命令。"""
        assert CMD_TRIGGER_HOME == 0x0008


class TestConfigureHomeMode:
    """测试回零模式配置。"""

    @pytest.mark.asyncio
    async def test_configure_home_mode_simulation(self):
        """测试仿真模式配置回零模式。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            result = await driver.configure_home_mode(HOME_MODE_SINGLE_LIMIT)
            assert result is True

            result = await driver.configure_home_mode(HOME_MODE_DOUBLE_LIMIT)
            assert result is True

            result = await driver.configure_home_mode(HOME_MODE_EXTERNAL_SIGNAL)
            assert result is True

            result = await driver.configure_home_mode(HOME_MODE_ENCODER_Z)
            assert result is True

    @pytest.mark.asyncio
    async def test_configure_home_mode_invalid(self):
        """测试配置无效回零模式。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            with pytest.raises(ValueError, match="Invalid home mode"):
                await driver.configure_home_mode(4)

            with pytest.raises(ValueError, match="Invalid home mode"):
                await driver.configure_home_mode(-1)

    @pytest.mark.asyncio
    async def test_configure_home_mode_with_mock(self, mock_modbus_client):
        """测试使用Mock配置回零模式。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_modbus_client.write_register.return_value = mock_result

            result = await driver.configure_home_mode(HOME_MODE_ENCODER_Z)

            assert result is True
            mock_modbus_client.write_register.assert_called_once_with(
                REG_HOME_MODE, HOME_MODE_ENCODER_Z, slave=1
            )


class TestConfigureHomeSpeed:
    """测试回零速度配置。"""

    @pytest.mark.asyncio
    async def test_configure_home_speed_simulation(self):
        """测试仿真模式配置回零速度。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            result = await driver.configure_home_speed(speed_high=5000, speed_low=500)

            assert result is True

    @pytest.mark.asyncio
    async def test_configure_home_speed_boundary(self):
        """测试回零速度边界值。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            # 最小值
            result = await driver.configure_home_speed(speed_high=1, speed_low=1)
            assert result is True

            # 最大值
            result = await driver.configure_home_speed(speed_high=10000, speed_low=10000)
            assert result is True

    @pytest.mark.asyncio
    async def test_configure_home_speed_invalid_high(self):
        """测试配置无效高速。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            with pytest.raises(ValueError, match="Invalid high speed"):
                await driver.configure_home_speed(speed_high=0, speed_low=500)

            with pytest.raises(ValueError, match="Invalid high speed"):
                await driver.configure_home_speed(speed_high=10001, speed_low=500)

    @pytest.mark.asyncio
    async def test_configure_home_speed_invalid_low(self):
        """测试配置无效低速。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            with pytest.raises(ValueError, match="Invalid low speed"):
                await driver.configure_home_speed(speed_high=5000, speed_low=0)

            with pytest.raises(ValueError, match="Invalid low speed"):
                await driver.configure_home_speed(speed_high=5000, speed_low=10001)

    @pytest.mark.asyncio
    async def test_configure_home_speed_with_mock(self, mock_modbus_client):
        """测试使用Mock配置回零速度。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_modbus_client.write_register.return_value = mock_result

            result = await driver.configure_home_speed(speed_high=3000, speed_low=300)

            assert result is True
            assert mock_modbus_client.write_register.call_count == 2


class TestConfigureHomeOffset:
    """测试回零偏移配置。"""

    @pytest.mark.asyncio
    async def test_configure_home_offset_simulation(self):
        """测试仿真模式配置回零偏移。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            result = await driver.configure_home_offset(offset=1600)
            assert result is True

            result = await driver.configure_home_offset(offset=-1600)
            assert result is True

    @pytest.mark.asyncio
    async def test_configure_home_offset_with_mock(self, mock_modbus_client):
        """测试使用Mock配置回零偏移。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_modbus_client.write_register.return_value = mock_result

            result = await driver.configure_home_offset(offset=3200)

            assert result is True
            mock_modbus_client.write_register.assert_called_once()


class TestConfigureHomeDirection:
    """测试回零方向配置。"""

    @pytest.mark.asyncio
    async def test_configure_home_direction_simulation(self):
        """测试仿真模式配置回零方向。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            result = await driver.configure_home_direction(HOME_DIRECTION_POSITIVE)
            assert result is True

            result = await driver.configure_home_direction(HOME_DIRECTION_NEGATIVE)
            assert result is True

    @pytest.mark.asyncio
    async def test_configure_home_direction_invalid(self):
        """测试配置无效回零方向。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            with pytest.raises(ValueError, match="Invalid home direction"):
                await driver.configure_home_direction(2)

            with pytest.raises(ValueError, match="Invalid home direction"):
                await driver.configure_home_direction(-1)

    @pytest.mark.asyncio
    async def test_configure_home_direction_with_mock(self, mock_modbus_client):
        """测试使用Mock配置回零方向。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_modbus_client.write_register.return_value = mock_result

            result = await driver.configure_home_direction(HOME_DIRECTION_NEGATIVE)

            assert result is True
            mock_modbus_client.write_register.assert_called_once_with(
                REG_HOME_DIRECTION, HOME_DIRECTION_NEGATIVE, slave=1
            )


class TestHomeOperation:
    """测试回零操作。"""

    @pytest.mark.asyncio
    async def test_home_simulation(self):
        """测试仿真模式回零。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.status = DeviceStatus.READY
            driver._current_position = mm_to_steps(50.0)

            result = await driver.home()

            assert result is True
            assert driver._current_position == 0

    @pytest.mark.asyncio
    async def test_home_with_mock(self, mock_modbus_client):
        """测试使用Mock执行回零。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client
            driver.status = DeviceStatus.READY

            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_modbus_client.write_register.return_value = mock_result

            result = await driver.home()

            assert result is True
            mock_modbus_client.write_register.assert_called_once_with(
                driver.REG_TRIGGER, TRIGGER_HOME, slave=1
            )

    @pytest.mark.asyncio
    async def test_complete_home_workflow(self):
        """测试完整回零工作流。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.status = DeviceStatus.READY

            # 1. 配置回零模式
            result = await driver.configure_home_mode(HOME_MODE_ENCODER_Z)
            assert result is True

            # 2. 配置回零速度
            result = await driver.configure_home_speed(speed_high=5000, speed_low=500)
            assert result is True

            # 3. 配置回零偏移
            result = await driver.configure_home_offset(offset=1600)
            assert result is True

            # 4. 配置回零方向
            result = await driver.configure_home_direction(HOME_DIRECTION_POSITIVE)
            assert result is True

            # 5. 执行回零
            driver._current_position = mm_to_steps(100.0)
            result = await driver.home()
            assert result is True
            assert driver._current_position == 0


class TestIOConstants:
    """测试IO配置常量。"""

    def test_di_config_addresses(self):
        """测试DI配置寄存器地址。"""
        assert DI_CONFIG_ADDRS[1] == 0x0145  # Pr4.02
        assert DI_CONFIG_ADDRS[2] == 0x0147  # Pr4.03
        assert DI_CONFIG_ADDRS[3] == 0x0149  # Pr4.04
        assert DI_CONFIG_ADDRS[4] == 0x014B  # Pr4.05
        assert DI_CONFIG_ADDRS[5] == 0x014D  # Pr4.06
        assert DI_CONFIG_ADDRS[6] == 0x014F  # Pr4.07
        assert DI_CONFIG_ADDRS[7] == 0x0151  # Pr4.08

    def test_do_config_addresses(self):
        """测试DO配置寄存器地址。"""
        assert DO_CONFIG_ADDRS[1] == 0x0157  # Pr4.11
        assert DO_CONFIG_ADDRS[2] == 0x0159  # Pr4.12
        assert DO_CONFIG_ADDRS[3] == 0x015B  # Pr4.13

    def test_di_functions(self):
        """测试DI功能代码定义。"""
        assert DI_FUNCTIONS[0x00] == "无效输入"
        assert DI_FUNCTIONS[0x07] == "报警清除"
        assert DI_FUNCTIONS[0x08] == "使能"
        assert DI_FUNCTIONS[0x20] == "触发命令(CTRG)"

    def test_do_functions(self):
        """测试DO功能代码定义。"""
        assert DO_FUNCTIONS[0x00] == "无效输出"
        assert DO_FUNCTIONS[0x20] == "指令完成(CMD_OK)"
        assert DO_FUNCTIONS[0x21] == "路径完成(MC_OK)"
        assert DO_FUNCTIONS[0x25] == "报警输出(ALM)"

    def test_io_status_registers(self):
        """测试IO状态寄存器地址。"""
        assert REG_DI_STATUS == 0x0179  # Pr4.28
        assert REG_DO_STATUS == 0x017B  # Pr4.29


class TestConfigureDI:
    """测试DI配置功能。"""

    @pytest.mark.asyncio
    async def test_configure_di_simulation(self):
        """测试仿真模式配置DI。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            # 测试配置DI1为使能
            result = await driver.configure_di(1, 0x08)
            assert result is True

            # 测试配置DI4为正限位
            result = await driver.configure_di(4, 0x25)
            assert result is True

            # 测试配置DI6为回零
            result = await driver.configure_di(6, 0x21)
            assert result is True

    @pytest.mark.asyncio
    async def test_configure_di_invalid_number(self):
        """测试无效DI端口号。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            # DI端口号超出范围
            result = await driver.configure_di(0, 0x08)
            assert result is False

            result = await driver.configure_di(8, 0x08)
            assert result is False

    @pytest.mark.asyncio
    async def test_configure_di_invalid_function(self):
        """测试无效DI功能代码。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            # 功能代码超出范围
            result = await driver.configure_di(1, 0x99)
            assert result is False

    @pytest.mark.asyncio
    async def test_configure_di_with_mock(self, mock_modbus_client):
        """测试使用Mock配置DI。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_modbus_client.write_register.return_value = mock_result

            result = await driver.configure_di(1, 0x08)

            assert result is True
            mock_modbus_client.write_register.assert_called_once_with(
                DI_CONFIG_ADDRS[1], 0x08, slave=1
            )


class TestConfigureDO:
    """测试DO配置功能。"""

    @pytest.mark.asyncio
    async def test_configure_do_simulation(self):
        """测试仿真模式配置DO。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            # 测试配置DO1为报警输出
            result = await driver.configure_do(1, 0x25)
            assert result is True

            # 测试配置DO2为到位信号
            result = await driver.configure_do(2, 0x23)
            assert result is True

            # 测试配置DO3为指令完成
            result = await driver.configure_do(3, 0x20)
            assert result is True

    @pytest.mark.asyncio
    async def test_configure_do_invalid_number(self):
        """测试无效DO端口号。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            # DO端口号超出范围
            result = await driver.configure_do(0, 0x25)
            assert result is False

            result = await driver.configure_do(4, 0x25)
            assert result is False

    @pytest.mark.asyncio
    async def test_configure_do_invalid_function(self):
        """测试无效DO功能代码。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            # 功能代码超出范围
            result = await driver.configure_do(1, 0x99)
            assert result is False

    @pytest.mark.asyncio
    async def test_configure_do_with_mock(self, mock_modbus_client):
        """测试使用Mock配置DO。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_modbus_client.write_register.return_value = mock_result

            result = await driver.configure_do(1, 0x25)

            assert result is True
            mock_modbus_client.write_register.assert_called_once_with(
                DO_CONFIG_ADDRS[1], 0x25, slave=1
            )


class TestReadDIConfig:
    """测试读取DI配置。"""

    @pytest.mark.asyncio
    async def test_read_di_config_simulation(self):
        """测试仿真模式读取DI配置。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            result = await driver.read_di_config(1)
            assert result == 0  # 仿真模式默认返回0

    @pytest.mark.asyncio
    async def test_read_di_config_invalid_number(self):
        """测试读取无效DI端口号配置。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            result = await driver.read_di_config(0)
            assert result == -1

            result = await driver.read_di_config(8)
            assert result == -1

    @pytest.mark.asyncio
    async def test_read_di_config_with_mock(self, mock_modbus_client):
        """测试使用Mock读取DI配置。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_result.registers = [0x08]  # 使能功能
            mock_modbus_client.read_holding_registers.return_value = mock_result

            result = await driver.read_di_config(1)

            assert result == 0x08
            mock_modbus_client.read_holding_registers.assert_called_once_with(
                DI_CONFIG_ADDRS[1], 1, slave=1
            )


class TestReadDOConfig:
    """测试读取DO配置。"""

    @pytest.mark.asyncio
    async def test_read_do_config_simulation(self):
        """测试仿真模式读取DO配置。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            result = await driver.read_do_config(1)
            assert result == 0  # 仿真模式默认返回0

    @pytest.mark.asyncio
    async def test_read_do_config_invalid_number(self):
        """测试读取无效DO端口号配置。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            result = await driver.read_do_config(0)
            assert result == -1

            result = await driver.read_do_config(4)
            assert result == -1

    @pytest.mark.asyncio
    async def test_read_do_config_with_mock(self, mock_modbus_client):
        """测试使用Mock读取DO配置。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_result.registers = [0x23]  # 到位信号
            mock_modbus_client.read_holding_registers.return_value = mock_result

            result = await driver.read_do_config(1)

            assert result == 0x23
            mock_modbus_client.read_holding_registers.assert_called_once_with(
                DO_CONFIG_ADDRS[1], 1, slave=1
            )


class TestReadDIStatus:
    """测试读取DI状态。"""

    @pytest.mark.asyncio
    async def test_read_di_status_simulation(self):
        """测试仿真模式读取DI状态。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            result = await driver.read_di_status()

            assert "raw_value" in result
            assert "di1" in result
            assert "di7" in result
            assert "active" in result
            assert result["raw_value"] == 0
            assert result["active"] == []

    @pytest.mark.asyncio
    async def test_read_di_status_with_mock(self, mock_modbus_client):
        """测试使用Mock读取DI状态。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            # 模拟DI1和DI4激活 (0x01 | 0x08 = 0x09)
            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_result.registers = [0x09]
            mock_modbus_client.read_holding_registers.return_value = mock_result

            result = await driver.read_di_status()

            assert result["raw_value"] == 0x09
            assert result["di1"] is True
            assert result["di4"] is True
            assert result["di2"] is False
            assert "DI1" in result["active"]
            assert "DI4" in result["active"]

    @pytest.mark.asyncio
    async def test_read_di_status_all_active(self, mock_modbus_client):
        """测试所有DI激活状态。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            # 所有DI激活 (0x7F)
            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_result.registers = [0x7F]
            mock_modbus_client.read_holding_registers.return_value = mock_result

            result = await driver.read_di_status()

            assert result["raw_value"] == 0x7F
            for i in range(1, 8):
                assert result[f"di{i}"] is True
            assert len(result["active"]) == 7


class TestReadDOStatus:
    """测试读取DO状态。"""

    @pytest.mark.asyncio
    async def test_read_do_status_simulation(self):
        """测试仿真模式读取DO状态。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            result = await driver.read_do_status()

            assert "raw_value" in result
            assert "do1" in result
            assert "do3" in result
            assert "active" in result
            assert result["raw_value"] == 0
            assert result["active"] == []

    @pytest.mark.asyncio
    async def test_read_do_status_with_mock(self, mock_modbus_client):
        """测试使用Mock读取DO状态。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            # 模拟DO1和DO3激活 (0x01 | 0x04 = 0x05)
            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_result.registers = [0x05]
            mock_modbus_client.read_holding_registers.return_value = mock_result

            result = await driver.read_do_status()

            assert result["raw_value"] == 0x05
            assert result["do1"] is True
            assert result["do3"] is True
            assert result["do2"] is False
            assert "DO1" in result["active"]
            assert "DO3" in result["active"]

    @pytest.mark.asyncio
    async def test_read_do_status_all_active(self, mock_modbus_client):
        """测试所有DO激活状态。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", True):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.client = mock_modbus_client

            # 所有DO激活 (0x07)
            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_result.registers = [0x07]
            mock_modbus_client.read_holding_registers.return_value = mock_result

            result = await driver.read_do_status()

            assert result["raw_value"] == 0x07
            for i in range(1, 4):
                assert result[f"do{i}"] is True
            assert len(result["active"]) == 3


class TestReadIOStatus:
    """测试读取完整IO状态。"""

    @pytest.mark.asyncio
    async def test_read_io_status_simulation(self):
        """测试仿真模式读取完整IO状态。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            result = await driver.read_io_status()

            assert "di" in result
            assert "do" in result
            assert "raw_value" in result["di"]
            assert "raw_value" in result["do"]


class TestConfigureAllDI:
    """测试批量配置DI。"""

    @pytest.mark.asyncio
    async def test_configure_all_di_simulation(self):
        """测试仿真模式批量配置DI。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            config = {
                1: 0x08,  # DI1: 使能
                2: 0x23,  # DI2: JOG+
                3: 0x24,  # DI3: JOG-
                4: 0x25,  # DI4: 正限位
                5: 0x26,  # DI5: 负限位
            }

            results = await driver.configure_all_di(config)

            assert len(results) == 5
            for di_num in config:
                assert results[di_num] is True

    @pytest.mark.asyncio
    async def test_configure_all_di_partial_failure(self):
        """测试批量配置DI部分失败。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            config = {
                1: 0x08,  # 有效
                2: 0x99,  # 无效功能代码
                3: 0x24,  # 有效
            }

            results = await driver.configure_all_di(config)

            assert results[1] is True
            assert results[2] is False
            assert results[3] is True


class TestConfigureAllDO:
    """测试批量配置DO。"""

    @pytest.mark.asyncio
    async def test_configure_all_do_simulation(self):
        """测试仿真模式批量配置DO。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            config = {
                1: 0x25,  # DO1: 报警输出
                2: 0x23,  # DO2: 到位信号
                3: 0x20,  # DO3: 指令完成
            }

            results = await driver.configure_all_do(config)

            assert len(results) == 3
            for do_num in config:
                assert results[do_num] is True

    @pytest.mark.asyncio
    async def test_configure_all_do_partial_failure(self):
        """测试批量配置DO部分失败。"""
        with patch("core.dm2c_driver.PYMODBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            config = {
                1: 0x25,  # 有效
                2: 0x99,  # 无效功能代码
            }

            results = await driver.configure_all_do(config)

            assert results[1] is True
            assert results[2] is False
