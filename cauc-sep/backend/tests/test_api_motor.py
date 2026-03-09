"""
测试电机控制 API 端点

测试内容：
- 获取电机状态
- 连接/断开电机
- 绝对/相对定位
- JOG点动
- 急停和复位
- 限位配置
- PR路径配置和触发
- 回零操作
- 报警复位
- 参数保存/恢复
- 状态字和报警代码读取
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import motor
from core.abstract import DeviceStatus
from core.dm2c_driver import ALARM_CODES


@pytest.fixture
def app_with_motor(mock_dm2c):
    """创建带Mock电机的FastAPI应用。"""
    app = FastAPI()
    app.include_router(motor.router)
    motor.set_dm2c(mock_dm2c)
    return app


@pytest.fixture
def client_with_motor(app_with_motor):
    """创建测试客户端。"""
    with TestClient(app_with_motor) as client:
        yield client


class TestMotorStatusEndpoint:
    """测试电机状态端点。"""

    def test_get_motor_status_success(self, client_with_motor, mock_dm2c):
        """测试成功获取电机状态。"""
        mock_dm2c.read_status = AsyncMock(
            return_value={
                "device_id": "test_motor",
                "status": "ready",
                "position_steps": 0,
                "position_mm": 0.0,
                "alarm_code": 0,
                "alarm_text": "无报警",
                "status_word": {
                    "fault": False,
                    "enabled": True,
                    "running": False,
                    "cmd_complete": True,
                    "path_complete": True,
                    "home_complete": True,
                    "raw_value": 0x72,
                },
                "limit_positive": 100.0,
                "limit_negative": -100.0,
                "connected": True,
            }
        )

        response = client_with_motor.get("/api/v1/motor/status")

        assert response.status_code == 200
        data = response.json()
        assert data["device_id"] == "test_motor"
        assert data["status"] == "ready"
        assert "position_mm" in data
        assert "alarm_code" in data

    def test_get_motor_status_not_initialized(self):
        """测试电机未初始化时获取状态。"""
        app = FastAPI()
        app.include_router(motor.router)
        motor.set_dm2c(None)

        with TestClient(app) as client:
            response = client.get("/api/v1/motor/status")

            assert response.status_code == 503


class TestMotorConnectionEndpoints:
    """测试电机连接端点。"""

    def test_connect_motor_success(self, client_with_motor, mock_dm2c):
        """测试成功连接电机。"""
        mock_dm2c.connect = AsyncMock(return_value=True)

        response = client_with_motor.post("/api/v1/motor/connect")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Connected" in data["message"]

    def test_connect_motor_failure(self, client_with_motor, mock_dm2c):
        """测试连接电机失败。"""
        mock_dm2c.connect = AsyncMock(return_value=False)

        response = client_with_motor.post("/api/v1/motor/connect")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_disconnect_motor_success(self, client_with_motor, mock_dm2c):
        """测试成功断开电机。"""
        mock_dm2c.disconnect = AsyncMock(return_value=True)

        response = client_with_motor.post("/api/v1/motor/disconnect")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestMotorMoveEndpoints:
    """测试电机运动端点。"""

    def test_motor_move_success(self, client_with_motor, mock_dm2c):
        """测试成功执行绝对定位。"""
        mock_dm2c.status = DeviceStatus.READY
        mock_dm2c.move_abs = AsyncMock(return_value=True)

        response = client_with_motor.post(
            "/api/v1/motor/move", json={"position_mm": 10.0, "velocity_mm_s": 5.0}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["target_position_mm"] == 10.0
        assert "target_position_steps" in data

    def test_motor_move_disconnected(self, client_with_motor, mock_dm2c):
        """测试断开状态下执行定位。"""
        mock_dm2c.status = DeviceStatus.DISCONNECTED

        response = client_with_motor.post(
            "/api/v1/motor/move", json={"position_mm": 10.0, "velocity_mm_s": 5.0}
        )

        assert response.status_code == 400
        assert "not connected" in response.json()["detail"].lower()

    def test_motor_move_emergency_stop_state(self, client_with_motor, mock_dm2c):
        """测试急停状态下执行定位。"""
        mock_dm2c.status = DeviceStatus.EMERGENCY_STOP

        response = client_with_motor.post(
            "/api/v1/motor/move", json={"position_mm": 10.0, "velocity_mm_s": 5.0}
        )

        assert response.status_code == 400
        assert "emergency stop" in response.json()["detail"].lower()

    def test_motor_move_soft_limit_exceeded(self, client_with_motor, mock_dm2c):
        """测试超出软件限位。"""
        mock_dm2c.status = DeviceStatus.READY
        mock_dm2c.move_abs = AsyncMock(return_value=False)
        
        response = client_with_motor.post(
            "/api/v1/motor/move",
            json={
                "position_mm": 50.0,
                "velocity_mm_s": 5.0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False


class TestMotorJogEndpoint:
    """测试JOG端点。"""

    def test_jog_positive_success(self, client_with_motor, mock_dm2c):
        """测试成功正向JOG。"""
        mock_dm2c.status = DeviceStatus.READY
        mock_dm2c.jog = AsyncMock(return_value=True)

        response = client_with_motor.post(
            "/api/v1/motor/jog", json={"direction": 1, "velocity_mm_s": 5.0}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "+" in data["message"]

    def test_jog_negative_success(self, client_with_motor, mock_dm2c):
        """测试成功负向JOG。"""
        mock_dm2c.status = DeviceStatus.READY
        mock_dm2c.jog = AsyncMock(return_value=True)

        response = client_with_motor.post(
            "/api/v1/motor/jog", json={"direction": -1, "velocity_mm_s": 5.0}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "-" in data["message"]

    def test_jog_disconnected(self, client_with_motor, mock_dm2c):
        """测试断开状态下JOG。"""
        mock_dm2c.status = DeviceStatus.DISCONNECTED

        response = client_with_motor.post(
            "/api/v1/motor/jog", json={"direction": 1, "velocity_mm_s": 5.0}
        )

        assert response.status_code == 400


class TestMotorEmergencyStopEndpoints:
    """测试急停端点。"""

    def test_emergency_stop_success(self, client_with_motor, mock_dm2c):
        """测试成功执行急停。"""
        mock_dm2c.emergency_stop = AsyncMock(return_value=True)

        response = client_with_motor.post("/api/v1/motor/emergency_stop")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Emergency stop" in data["message"]

    def test_reset_emergency_success(self, client_with_motor, mock_dm2c):
        """测试成功复位急停状态。"""
        mock_dm2c.reset_emergency = AsyncMock(return_value=True)

        response = client_with_motor.post("/api/v1/motor/reset")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestMotorLimitEndpoints:
    """测试限位端点。"""

    def test_get_limits(self, client_with_motor, mock_dm2c):
        """测试获取限位配置。"""
        mock_dm2c.limit_config.positive_limit = 100.0
        mock_dm2c.limit_config.negative_limit = -100.0
        mock_dm2c.limit_config.enable = True

        response = client_with_motor.get("/api/v1/motor/limits")

        assert response.status_code == 200
        data = response.json()
        assert data["positive_mm"] == 100.0
        assert data["negative_mm"] == -100.0
        assert data["enabled"] is True

    def test_set_limits_success(self, client_with_motor, mock_dm2c):
        """测试成功设置限位。"""
        mock_dm2c.set_soft_limits = MagicMock()

        response = client_with_motor.post(
            "/api/v1/motor/limits", json={"positive_mm": 50.0, "negative_mm": -50.0}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_dm2c.set_soft_limits.assert_called_once_with(50.0, -50.0)


class TestMotorPRPathEndpoints:
    """测试PR路径端点。"""

    def test_configure_pr_path_success(self, client_with_motor, mock_dm2c):
        """测试成功配置PR路径。"""
        mock_dm2c.status = DeviceStatus.READY
        mock_dm2c.configure_pr_path = AsyncMock(return_value=True)

        response = client_with_motor.post(
            "/api/v1/motor/pr/config",
            json={
                "path_number": 0,
                "mode": 1,
                "position_mm": 10.0,
                "velocity_mm_s": 1000,
                "accel_time": 100,
                "decel_time": 100,
                "dwell_time": 0,
                "special_param": 0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_configure_pr_path_disconnected(self, client_with_motor, mock_dm2c):
        """测试断开状态下配置PR路径。"""
        mock_dm2c.status = DeviceStatus.DISCONNECTED

        response = client_with_motor.post(
            "/api/v1/motor/pr/config",
            json={"path_number": 0, "mode": 1, "position_mm": 10.0, "velocity_mm_s": 1000},
        )

        assert response.status_code == 400

    def test_trigger_pr_path_success(self, client_with_motor, mock_dm2c):
        """测试成功触发PR路径。"""
        mock_dm2c.status = DeviceStatus.READY
        mock_dm2c.trigger_pr_path = AsyncMock(return_value=True)

        response = client_with_motor.post("/api/v1/motor/pr/trigger", json={"path_number": 0})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_trigger_pr_path_disconnected(self, client_with_motor, mock_dm2c):
        """测试断开状态下触发PR路径。"""
        mock_dm2c.status = DeviceStatus.DISCONNECTED

        response = client_with_motor.post("/api/v1/motor/pr/trigger", json={"path_number": 0})

        assert response.status_code == 400


class TestMotorHomeEndpoint:
    """测试回零端点。"""

    def test_home_success(self, client_with_motor, mock_dm2c):
        """测试成功执行回零。"""
        mock_dm2c.status = DeviceStatus.READY
        mock_dm2c.home = AsyncMock(return_value=True)

        response = client_with_motor.post("/api/v1/motor/home", json={"mode": "origin"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Homing" in data["message"]

    def test_home_disconnected(self, client_with_motor, mock_dm2c):
        """测试断开状态下执行回零。"""
        mock_dm2c.status = DeviceStatus.DISCONNECTED

        response = client_with_motor.post("/api/v1/motor/home", json={"mode": "origin"})

        assert response.status_code == 400


class TestMotorAlarmEndpoints:
    """测试报警端点。"""

    def test_reset_alarm_success(self, client_with_motor, mock_dm2c):
        """测试成功复位报警。"""
        mock_dm2c.status = DeviceStatus.READY
        mock_dm2c.reset_alarm = AsyncMock(return_value=True)

        response = client_with_motor.post("/api/v1/motor/reset_alarm")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_reset_alarm_disconnected(self, client_with_motor, mock_dm2c):
        """测试断开状态下复位报警。"""
        mock_dm2c.status = DeviceStatus.DISCONNECTED

        response = client_with_motor.post("/api/v1/motor/reset_alarm")

        assert response.status_code == 400


class TestMotorParameterEndpoints:
    """测试参数管理端点。"""

    def test_save_params_success(self, client_with_motor, mock_dm2c):
        """测试成功保存参数。"""
        mock_dm2c.status = DeviceStatus.READY
        mock_dm2c.save_parameters = AsyncMock(return_value=True)

        response = client_with_motor.post("/api/v1/motor/save_params")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "EEPROM" in data["message"]

    def test_save_params_disconnected(self, client_with_motor, mock_dm2c):
        """测试断开状态下保存参数。"""
        mock_dm2c.status = DeviceStatus.DISCONNECTED

        response = client_with_motor.post("/api/v1/motor/save_params")

        assert response.status_code == 400

    def test_factory_reset_success(self, client_with_motor, mock_dm2c):
        """测试成功恢复出厂设置。"""
        mock_dm2c.status = DeviceStatus.READY
        mock_dm2c.factory_reset = AsyncMock(return_value=True)

        response = client_with_motor.post("/api/v1/motor/factory_reset")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_factory_reset_disconnected(self, client_with_motor, mock_dm2c):
        """测试断开状态下恢复出厂设置。"""
        mock_dm2c.status = DeviceStatus.DISCONNECTED

        response = client_with_motor.post("/api/v1/motor/factory_reset")

        assert response.status_code == 400


class TestMotorStatusWordEndpoint:
    """测试状态字端点。"""

    def test_read_status_word_success(self, client_with_motor, mock_dm2c):
        """测试成功读取状态字。"""
        mock_dm2c.read_status_word = AsyncMock(
            return_value={
                "fault": False,
                "enabled": True,
                "running": False,
                "cmd_complete": True,
                "path_complete": True,
                "home_complete": True,
                "raw_value": 0x72,
            }
        )

        response = client_with_motor.get("/api/v1/motor/status_word")

        assert response.status_code == 200
        data = response.json()
        assert data["fault"] is False
        assert data["enabled"] is True
        assert data["raw_value"] == 0x72


class TestMotorAlarmCodeEndpoint:
    """测试报警代码端点。"""

    def test_read_alarm_code_no_alarm(self, client_with_motor, mock_dm2c):
        """测试读取无报警状态。"""
        mock_dm2c.read_alarm_code = AsyncMock(return_value=0)

        response = client_with_motor.get("/api/v1/motor/alarm_code")

        assert response.status_code == 200
        data = response.json()
        assert data["alarm_code"] == 0

    def test_read_alarm_code_with_alarm(self, client_with_motor, mock_dm2c):
        """测试读取有报警状态。"""
        mock_dm2c.read_alarm_code = AsyncMock(return_value=0x01)

        response = client_with_motor.get("/api/v1/motor/alarm_code")

        assert response.status_code == 200
        data = response.json()
        assert data["alarm_code"] == 0x01
        assert data["alarm_text"] == ALARM_CODES[0x01]


class TestMotorAPIValidation:
    """测试API输入验证。"""

    def test_move_request_validation_position_range(self, client_with_motor, mock_dm2c):
        """测试定位请求位置范围验证。"""
        mock_dm2c.status = DeviceStatus.READY

        response = client_with_motor.post(
            "/api/v1/motor/move", json={"position_mm": 150.0, "velocity_mm_s": 5.0}
        )

        assert response.status_code == 422

    def test_move_request_validation_velocity_range(self, client_with_motor, mock_dm2c):
        """测试定位请求速度范围验证。"""
        mock_dm2c.status = DeviceStatus.READY

        response = client_with_motor.post(
            "/api/v1/motor/move", json={"position_mm": 10.0, "velocity_mm_s": 100.0}
        )

        assert response.status_code == 422

    def test_jog_request_validation_direction(self, client_with_motor, mock_dm2c):
        """测试JOG请求方向验证。"""
        mock_dm2c.status = DeviceStatus.READY

        response = client_with_motor.post(
            "/api/v1/motor/jog", json={"direction": 2, "velocity_mm_s": 5.0}
        )

        assert response.status_code == 422

    def test_pr_path_request_validation_path_number(self, client_with_motor, mock_dm2c):
        """测试PR路径请求路径编号验证。"""
        mock_dm2c.status = DeviceStatus.READY

        response = client_with_motor.post(
            "/api/v1/motor/pr/config",
            json={"path_number": 20, "mode": 1, "position_mm": 10.0, "velocity_mm_s": 1000},
        )

        assert response.status_code == 422
