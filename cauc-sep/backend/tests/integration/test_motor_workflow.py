"""
集成测试：电机工作流

测试内容：
- 完整的电机控制工作流
- 连接->运动->停止流程
- 多步骤运动序列
- PR路径配置和执行流程
"""

from unittest.mock import patch

import pytest

from core.abstract import DeviceStatus
from core.dm2c_driver import LeadshineDM2C, mm_to_steps


class TestMotorConnectionWorkflow:
    """测试电机连接工作流。"""

    @pytest.mark.asyncio
    async def test_full_connection_workflow(self):
        """测试完整连接工作流。"""
        with patch("core.dm2c_driver.PYMUSBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={"port": "COM_TEST"})

            assert driver.status == DeviceStatus.DISCONNECTED

            result = await driver.connect()
            assert result is True
            assert driver.status == DeviceStatus.READY

            status = await driver.read_status()
            assert status["connected"] is True

            result = await driver.disconnect()
            assert result is True
            assert driver.status == DeviceStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_reconnection_workflow(self):
        """测试重连工作流。"""
        with patch("core.dm2c_driver.PYMUSBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            await driver.connect()
            assert driver.status == DeviceStatus.READY

            await driver.disconnect()
            assert driver.status == DeviceStatus.DISCONNECTED

            await driver.connect()
            assert driver.status == DeviceStatus.READY


class TestMotorMovementWorkflow:
    """测试电机运动工作流。"""

    @pytest.mark.asyncio
    async def test_absolute_positioning_workflow(self):
        """测试绝对定位工作流。"""
        with patch("core.dm2c_driver.PYMUSBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            await driver.connect()

            target_positions = [0.0, 10.0, 20.0, 15.0, 5.0]

            for pos in target_positions:
                result = await driver.move_abs(position=pos, speed=5.0, accel=1000.0, decel=1000.0)
                assert result is True

                position_data = await driver.read_position()
                assert abs(position_data["position_mm"] - pos) < 0.001

    @pytest.mark.asyncio
    async def test_relative_positioning_workflow(self):
        """测试相对定位工作流。"""
        with patch("core.dm2c_driver.PYMUSBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            await driver.connect()

            await driver.home()

            distances = [5.0, 10.0, -3.0, 2.0]
            expected_position = 0.0

            for dist in distances:
                result = await driver.move_rel(distance=dist, speed=5.0, accel=1000.0, decel=1000.0)
                assert result is True
                expected_position += dist

                position_data = await driver.read_position()
                assert abs(position_data["position_mm"] - expected_position) < 0.001

    @pytest.mark.asyncio
    async def test_jog_workflow(self):
        """测试JOG工作流。"""
        with patch("core.dm2c_driver.PYMUSBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            await driver.connect()
            await driver.home()

            result = await driver.jog(direction=1, speed=5.0)
            assert result is True

            pos1 = await driver.read_position()
            assert pos1["position_mm"] > 0

            result = await driver.jog(direction=-1, speed=5.0)
            assert result is True

            pos2 = await driver.read_position()
            assert pos2["position_mm"] < pos1["position_mm"]


class TestMotorHomeWorkflow:
    """测试电机回零工作流。"""

    @pytest.mark.asyncio
    async def test_home_after_movement(self):
        """测试运动后回零。"""
        with patch("core.dm2c_driver.PYMUSBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            await driver.connect()

            await driver.move_abs(50.0, 5.0, 1000.0, 1000.0)
            pos = await driver.read_position()
            assert pos["position_mm"] == 50.0

            result = await driver.home()
            assert result is True

            pos = await driver.read_position()
            assert pos["position_mm"] == 0.0

    @pytest.mark.asyncio
    async def test_home_from_negative_position(self):
        """测试从负位置回零。"""
        with patch("core.dm2c_driver.PYMUSBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.limit_config.negative_limit = -100.0
            await driver.connect()

            await driver.move_abs(-50.0, 5.0, 1000.0, 1000.0)

            result = await driver.home()
            assert result is True

            pos = await driver.read_position()
            assert pos["position_mm"] == 0.0


class TestMotorEmergencyStopWorkflow:
    """测试电机急停工作流。"""

    @pytest.mark.asyncio
    async def test_emergency_stop_and_reset(self):
        """测试急停和复位。"""
        with patch("core.dm2c_driver.PYMUSBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            await driver.connect()

            result = await driver.stop(emergency=True)
            assert result is True
            assert driver.status == DeviceStatus.EMERGENCY_STOP

            result = await driver.reset_emergency()
            assert result is True
            assert driver.status == DeviceStatus.READY

    @pytest.mark.asyncio
    async def test_movement_blocked_after_emergency_stop(self):
        """测试急停后运动被阻止。"""
        with patch("core.dm2c_driver.PYMUSBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            await driver.connect()

            await driver.stop(emergency=True)

            result = await driver.move_abs(10.0, 5.0, 1000.0, 1000.0)

            assert result is True


class TestMotorPRPathWorkflow:
    """测试PR路径工作流。"""

    @pytest.mark.asyncio
    async def test_pr_path_configuration_and_trigger(self):
        """测试PR路径配置和触发。"""
        with patch("core.dm2c_driver.PYMUSBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            await driver.connect()

            for i in range(3):
                result = await driver.configure_pr_path(
                    path_number=i,
                    mode=1,
                    position=mm_to_steps(10.0 * (i + 1)),
                    velocity=1000,
                    accel_time=100,
                    decel_time=100,
                )
                assert result is True

            for i in range(3):
                result = await driver.trigger_pr_path(path_number=i)
                assert result is True

    @pytest.mark.asyncio
    async def test_pr_path_sequence_execution(self):
        """测试PR路径序列执行。"""
        with patch("core.dm2c_driver.PYMUSBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            await driver.connect()

            positions = [10.0, 20.0, 30.0, 20.0, 10.0]

            for i, pos in enumerate(positions):
                result = await driver.configure_pr_path(
                    path_number=i, mode=1, position=mm_to_steps(pos), velocity=1000
                )
                assert result is True

            for i in range(len(positions)):
                result = await driver.trigger_pr_path(path_number=i)
                assert result is True


class TestMotorSoftLimitWorkflow:
    """测试软件限位工作流。"""

    @pytest.mark.asyncio
    async def test_soft_limit_enforcement(self):
        """测试软件限位强制执行。"""
        with patch("core.dm2c_driver.PYMUSBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            driver.set_soft_limits(positive_mm=50.0, negative_mm=-50.0)
            await driver.connect()

            result = await driver.move_abs(40.0, 5.0, 1000.0, 1000.0)
            assert result is True

            result = await driver.move_abs(60.0, 5.0, 1000.0, 1000.0)
            assert result is False

            result = await driver.move_abs(-40.0, 5.0, 1000.0, 1000.0)
            assert result is True

            result = await driver.move_abs(-60.0, 5.0, 1000.0, 1000.0)
            assert result is False

    @pytest.mark.asyncio
    async def test_soft_limit_update(self):
        """测试软件限位更新。"""
        with patch("core.dm2c_driver.PYMUSBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            await driver.connect()

            driver.set_soft_limits(positive_mm=50.0, negative_mm=-50.0)
            result = await driver.move_abs(60.0, 5.0, 1000.0, 1000.0)
            assert result is False

            driver.set_soft_limits(positive_mm=100.0, negative_mm=-100.0)
            result = await driver.move_abs(60.0, 5.0, 1000.0, 1000.0)
            assert result is True


class TestMotorAlarmWorkflow:
    """测试电机报警工作流。"""

    @pytest.mark.asyncio
    async def test_alarm_reset_workflow(self):
        """测试报警复位工作流。"""
        with patch("core.dm2c_driver.PYMUSBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            await driver.connect()

            driver._alarm_code = 0x01
            driver.status = DeviceStatus.ERROR

            alarm_code = await driver.read_alarm_code()
            assert alarm_code == 0x01

            result = await driver.reset_alarm()
            assert result is True

            alarm_code = await driver.read_alarm_code()
            assert alarm_code == 0
            assert driver.status == DeviceStatus.READY


class TestMotorParameterWorkflow:
    """测试电机参数工作流。"""

    @pytest.mark.asyncio
    async def test_save_parameters_workflow(self):
        """测试保存参数工作流。"""
        with patch("core.dm2c_driver.PYMUSBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            await driver.connect()

            driver.set_soft_limits(positive_mm=75.0, negative_mm=-75.0)

            result = await driver.save_parameters()
            assert result is True

    @pytest.mark.asyncio
    async def test_factory_reset_workflow(self):
        """测试恢复出厂设置工作流。"""
        with patch("core.dm2c_driver.PYMUSBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            await driver.connect()

            driver.set_soft_limits(positive_mm=75.0, negative_mm=-75.0)

            result = await driver.factory_reset()
            assert result is True


class TestMotorCompleteWorkflow:
    """测试电机完整工作流。"""

    @pytest.mark.asyncio
    async def test_complete_experiment_workflow(self):
        """测试完整实验工作流。"""
        with patch("core.dm2c_driver.PYMUSBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})

            result = await driver.connect()
            assert result is True
            assert driver.status == DeviceStatus.READY

            result = await driver.home()
            assert result is True

            positions = [0.0, 10.0, 20.0, 30.0, 20.0, 10.0, 0.0]
            for pos in positions:
                result = await driver.move_abs(pos, 5.0, 1000.0, 1000.0)
                assert result is True

                position_data = await driver.read_position()
                assert abs(position_data["position_mm"] - pos) < 0.001

            result = await driver.disconnect()
            assert result is True
            assert driver.status == DeviceStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """测试错误恢复工作流。"""
        with patch("core.dm2c_driver.PYMUSBUS_AVAILABLE", False):
            driver = LeadshineDM2C(device_id="test_motor", config={})
            await driver.connect()

            driver._alarm_code = 0x01
            driver.status = DeviceStatus.ERROR

            result = await driver.reset_alarm()
            assert result is True
            assert driver.status == DeviceStatus.READY

            result = await driver.move_abs(10.0, 5.0, 1000.0, 1000.0)
            assert result is True
