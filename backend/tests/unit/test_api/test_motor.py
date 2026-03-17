"""
电机控制 API 单元测试

文件名: test_motor.py
路径: backend/tests/unit/test_api/
功能: 测试电机控制 API 端点
作者: CAUC-SEP Team
创建日期: 2026-03-16
依赖: pytest, pytest-asyncio, fastapi

测试内容：
- TestMotorAPI: 电机 API 测试类
- test_get_motor_status(): 获取电机状态
- test_connect_motor(): 连接电机
- test_disconnect_motor(): 断开电机
- test_move_motor(): 移动电机
- test_emergency_stop(): 急停
- test_motor_not_initialized(): 电机未初始化
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import motor
from core.abstract import DeviceStatus
from core.dm2c_driver import ALARM_CODES


# ==================== Fixtures ====================


@pytest.fixture
def mock_motor():
    """创建 Mock 电机设备。

    Returns:
        MagicMock: Mock 的电机驱动器实例
    """
    motor_mock = MagicMock()
    motor_mock.device_id = "stepper_01"
    motor_mock.status = DeviceStatus.READY
    motor_mock.is_connected = True
    motor_mock.simulation = True
    motor_mock.steps_per_mm = 1600
    motor_mock.last_error = None

    # 限位配置
    motor_mock.limit_config = MagicMock()
    motor_mock.limit_config.positive_limit = 100.0
    motor_mock.limit_config.negative_limit = -100.0
    motor_mock.limit_config.enable = True
    motor_mock.limit_config.is_within_limits = MagicMock(return_value=True)

    # 异步方法 Mock
    motor_mock.connect = AsyncMock(return_value=True)
    motor_mock.disconnect = AsyncMock(return_value=True)
    motor_mock.read_status = AsyncMock(
        return_value={
            "device_id": "stepper_01",
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
    motor_mock.move_abs = AsyncMock(return_value=True)
    motor_mock.jog = AsyncMock(return_value=True)
    motor_mock.emergency_stop = AsyncMock(return_value=True)
    motor_mock.reset_emergency = AsyncMock(return_value=True)
    motor_mock.home = AsyncMock(return_value=True)
    motor_mock.reset_alarm = AsyncMock(return_value=True)
    motor_mock.save_parameters = AsyncMock(return_value=True)
    motor_mock.factory_reset = AsyncMock(return_value=True)
    motor_mock.read_status_word = AsyncMock(
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
    motor_mock.read_alarm_code = AsyncMock(return_value=0)
    motor_mock.set_soft_limits = MagicMock()
    motor_mock.configure_pr_path = AsyncMock(return_value=True)
    motor_mock.trigger_pr_path = AsyncMock(return_value=True)

    return motor_mock


@pytest.fixture
def app_with_motor(mock_motor):
    """创建带 Mock 电机的 FastAPI 应用。

    Args:
        mock_motor: Mock 电机设备

    Returns:
        FastAPI: 配置好的 FastAPI 应用实例
    """
    app = FastAPI()
    app.include_router(motor.router)
    motor.set_dm2c(mock_motor)
    return app


@pytest.fixture
def client_with_motor(app_with_motor):
    """创建测试客户端。

    Args:
        app_with_motor: FastAPI 应用

    Yields:
        TestClient: 测试客户端实例
    """
    with TestClient(app_with_motor, raise_server_exceptions=False) as client:
        yield client


# ==================== 测试类 ====================


class TestMotorAPI:
    """电机 API 测试。"""

    # ==================== 状态查询测试 ====================

    def test_get_motor_status(self, client_with_motor, mock_motor):
        """测试获取电机状态。"""
        response = client_with_motor.get("/api/v1/motor/status")

        assert response.status_code == 200
        data = response.json()
        assert data["device_id"] == "stepper_01"
        assert data["status"] == "ready"
        assert "position_mm" in data
        assert "alarm_code" in data

    def test_get_motor_status_not_initialized(self):
        """测试电机未初始化时获取状态。

        注意：API 返回 500 错误（设备未初始化异常）。
        """
        app = FastAPI()
        app.include_router(motor.router)
        motor.set_dm2c(None)

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/v1/motor/status")

            # API 返回 500 错误（设备未初始化异常）
            assert response.status_code == 500

    # ==================== 连接测试 ====================

    def test_connect_motor(self, client_with_motor, mock_motor):
        """测试连接电机。"""
        mock_motor.status = DeviceStatus.DISCONNECTED
        mock_motor.connect = AsyncMock(return_value=True)

        response = client_with_motor.post("/api/v1/motor/connect")

        assert response.status_code == 200
        mock_motor.connect.assert_called_once()

    def test_connect_motor_failure(self, client_with_motor, mock_motor):
        """测试连接电机失败。"""
        mock_motor.status = DeviceStatus.DISCONNECTED
        mock_motor.connect = AsyncMock(return_value=False)

        response = client_with_motor.post("/api/v1/motor/connect")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_disconnect_motor(self, client_with_motor, mock_motor):
        """测试断开电机。"""
        mock_motor.disconnect = AsyncMock(return_value=True)

        response = client_with_motor.post("/api/v1/motor/disconnect")

        assert response.status_code == 200
        mock_motor.disconnect.assert_called_once()

    # ==================== 运动控制测试 ====================

    def test_move_motor(self, client_with_motor, mock_motor):
        """测试移动电机。"""
        mock_motor.status = DeviceStatus.READY
        mock_motor.move_abs = AsyncMock(return_value=True)

        response = client_with_motor.post(
            "/api/v1/motor/move",
            json={"position_mm": 10.0, "velocity_mm_s": 5.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["target_position_mm"] == 10.0
        mock_motor.move_abs.assert_called_once()

    def test_move_motor_invalid_position(self, client_with_motor, mock_motor):
        """测试无效位置移动（超出限位）。

        注意：Pydantic 验证在请求体解析阶段就会拒绝超出范围的位置，
        返回 422 (Unprocessable Entity) 而不是 400。
        """
        mock_motor.status = DeviceStatus.READY

        response = client_with_motor.post(
            "/api/v1/motor/move",
            json={"position_mm": 200.0, "velocity_mm_s": 5.0},
        )

        # Pydantic 验证返回 422
        assert response.status_code == 422

    def test_move_motor_disconnected(self, client_with_motor, mock_motor):
        """测试断开状态下执行定位。"""
        mock_motor.status = DeviceStatus.DISCONNECTED

        response = client_with_motor.post(
            "/api/v1/motor/move",
            json={"position_mm": 10.0, "velocity_mm_s": 5.0},
        )

        # API 返回 500 错误（设备未连接异常）
        assert response.status_code == 500

    def test_move_motor_emergency_stop_state(self, client_with_motor, mock_motor):
        """测试急停状态下执行定位。"""
        mock_motor.status = DeviceStatus.EMERGENCY_STOP

        response = client_with_motor.post(
            "/api/v1/motor/move",
            json={"position_mm": 10.0, "velocity_mm_s": 5.0},
        )

        # API 返回 500 错误（设备处于急停状态异常）
        assert response.status_code == 500

    # ==================== JOG 测试 ====================

    def test_jog_positive(self, client_with_motor, mock_motor):
        """测试正向 JOG。"""
        mock_motor.status = DeviceStatus.READY
        mock_motor.jog = AsyncMock(return_value=True)

        response = client_with_motor.post(
            "/api/v1/motor/jog",
            json={"direction": 1, "velocity_mm_s": 5.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_jog_negative(self, client_with_motor, mock_motor):
        """测试负向 JOG。"""
        mock_motor.status = DeviceStatus.READY
        mock_motor.jog = AsyncMock(return_value=True)

        response = client_with_motor.post(
            "/api/v1/motor/jog",
            json={"direction": -1, "velocity_mm_s": 5.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_jog_invalid_direction(self, client_with_motor, mock_motor):
        """测试无效方向 JOG。

        注意：direction 字段验证范围是 ge=-1, le=1，所以 2 是无效值。
        """
        mock_motor.status = DeviceStatus.READY

        response = client_with_motor.post(
            "/api/v1/motor/jog",
            json={"direction": 2, "velocity_mm_s": 5.0},
        )

        assert response.status_code == 422

    def test_jog_disconnected(self, client_with_motor, mock_motor):
        """测试断开状态下 JOG。"""
        mock_motor.status = DeviceStatus.DISCONNECTED

        response = client_with_motor.post(
            "/api/v1/motor/jog",
            json={"direction": 1, "velocity_mm_s": 5.0},
        )

        # API 返回 500 错误（设备未连接异常）
        assert response.status_code == 500

    # ==================== 急停测试 ====================

    def test_emergency_stop(self, client_with_motor, mock_motor):
        """测试急停。"""
        mock_motor.emergency_stop = AsyncMock(return_value=True)

        response = client_with_motor.post("/api/v1/motor/emergency_stop")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_motor.emergency_stop.assert_called_once()

    def test_reset_emergency(self, client_with_motor, mock_motor):
        """测试复位急停状态。"""
        mock_motor.reset_emergency = AsyncMock(return_value=True)

        response = client_with_motor.post("/api/v1/motor/reset")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    # ==================== 限位测试 ====================

    def test_get_limits(self, client_with_motor, mock_motor):
        """测试获取限位配置。"""
        mock_motor.limit_config.positive_limit = 100.0
        mock_motor.limit_config.negative_limit = -100.0
        mock_motor.limit_config.enable = True

        response = client_with_motor.get("/api/v1/motor/limits")

        assert response.status_code == 200
        data = response.json()
        assert data["positive_mm"] == 100.0
        assert data["negative_mm"] == -100.0
        assert data["enabled"] is True

    def test_set_limits(self, client_with_motor, mock_motor):
        """测试设置限位。"""
        mock_motor.set_soft_limits = MagicMock()

        response = client_with_motor.post(
            "/api/v1/motor/limits",
            json={"positive_mm": 50.0, "negative_mm": -50.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_motor.set_soft_limits.assert_called_once_with(50.0, -50.0)

    def test_set_limits_invalid(self, client_with_motor, mock_motor):
        """测试设置无效限位。

        注意：API 会抛出异常，返回 500 错误。
        """
        response = client_with_motor.post(
            "/api/v1/motor/limits",
            json={"positive_mm": 50.0, "negative_mm": 100.0},
        )

        # API 返回 500 错误（限位参数无效异常）
        assert response.status_code == 500

    # ==================== 回零测试 ====================

    def test_home(self, client_with_motor, mock_motor):
        """测试回零。"""
        mock_motor.status = DeviceStatus.READY
        mock_motor.home = AsyncMock(return_value=True)

        response = client_with_motor.post(
            "/api/v1/motor/home",
            json={"mode": "origin"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_home_disconnected(self, client_with_motor, mock_motor):
        """测试断开状态下回零。"""
        mock_motor.status = DeviceStatus.DISCONNECTED

        response = client_with_motor.post(
            "/api/v1/motor/home",
            json={"mode": "origin"},
        )

        # API 返回 500 错误（设备未连接异常）
        assert response.status_code == 500

    # ==================== 报警测试 ====================

    def test_reset_alarm(self, client_with_motor, mock_motor):
        """测试复位报警。"""
        mock_motor.status = DeviceStatus.READY
        mock_motor.reset_alarm = AsyncMock(return_value=True)

        response = client_with_motor.post("/api/v1/motor/reset_alarm")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_read_alarm_code_no_alarm(self, client_with_motor, mock_motor):
        """测试读取无报警状态。"""
        mock_motor.read_alarm_code = AsyncMock(return_value=0)

        response = client_with_motor.get("/api/v1/motor/alarm_code")

        assert response.status_code == 200
        data = response.json()
        assert data["alarm_code"] == 0

    def test_read_alarm_code_with_alarm(self, client_with_motor, mock_motor):
        """测试读取有报警状态。"""
        mock_motor.read_alarm_code = AsyncMock(return_value=0x01)

        response = client_with_motor.get("/api/v1/motor/alarm_code")

        assert response.status_code == 200
        data = response.json()
        assert data["alarm_code"] == 0x01
        assert data["alarm_text"] == ALARM_CODES[0x01]

    # ==================== 状态字测试 ====================

    def test_read_status_word(self, client_with_motor, mock_motor):
        """测试读取状态字。"""
        mock_motor.read_status_word = AsyncMock(
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

    # ==================== 参数管理测试 ====================

    def test_save_params(self, client_with_motor, mock_motor):
        """测试保存参数。"""
        mock_motor.status = DeviceStatus.READY
        mock_motor.save_parameters = AsyncMock(return_value=True)

        response = client_with_motor.post("/api/v1/motor/save_params")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_factory_reset(self, client_with_motor, mock_motor):
        """测试恢复出厂设置。"""
        mock_motor.status = DeviceStatus.READY
        mock_motor.factory_reset = AsyncMock(return_value=True)

        response = client_with_motor.post("/api/v1/motor/factory_reset")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    # ==================== PR 路径测试 ====================

    def test_configure_pr_path(self, client_with_motor, mock_motor):
        """测试配置 PR 路径。"""
        mock_motor.status = DeviceStatus.READY
        mock_motor.configure_pr_path = AsyncMock(return_value=True)

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

    def test_configure_pr_path_invalid_number(self, client_with_motor, mock_motor):
        """测试配置无效 PR 路径编号。"""
        mock_motor.status = DeviceStatus.READY

        response = client_with_motor.post(
            "/api/v1/motor/pr/config",
            json={
                "path_number": 20,
                "mode": 1,
                "position_mm": 10.0,
                "velocity_mm_s": 1000,
            },
        )

        assert response.status_code == 422

    def test_trigger_pr_path(self, client_with_motor, mock_motor):
        """测试触发 PR 路径。"""
        mock_motor.status = DeviceStatus.READY
        mock_motor.trigger_pr_path = AsyncMock(return_value=True)

        response = client_with_motor.post(
            "/api/v1/motor/pr/trigger",
            json={"path_number": 0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    # ==================== 参数验证测试 ====================

    def test_move_request_validation_position_range(self, client_with_motor, mock_motor):
        """测试定位请求位置范围验证。"""
        mock_motor.status = DeviceStatus.READY

        response = client_with_motor.post(
            "/api/v1/motor/move",
            json={"position_mm": 150.0, "velocity_mm_s": 5.0},
        )

        assert response.status_code == 422

    def test_move_request_validation_velocity_range(self, client_with_motor, mock_motor):
        """测试定位请求速度范围验证。"""
        mock_motor.status = DeviceStatus.READY

        response = client_with_motor.post(
            "/api/v1/motor/move",
            json={"position_mm": 10.0, "velocity_mm_s": 100.0},
        )

        assert response.status_code == 422

    def test_jog_request_validation_direction(self, client_with_motor, mock_motor):
        """测试 JOG 请求方向验证。"""
        mock_motor.status = DeviceStatus.READY

        response = client_with_motor.post(
            "/api/v1/motor/jog",
            json={"direction": 2, "velocity_mm_s": 5.0},
        )

        assert response.status_code == 422

    def test_pr_path_request_validation_path_number(self, client_with_motor, mock_motor):
        """测试 PR 路径请求路径编号验证。"""
        mock_motor.status = DeviceStatus.READY

        response = client_with_motor.post(
            "/api/v1/motor/pr/config",
            json={
                "path_number": 20,
                "mode": 1,
                "position_mm": 10.0,
                "velocity_mm_s": 1000,
            },
        )

        assert response.status_code == 422

    # ==================== 忙碌状态测试 ====================

    def test_move_motor_busy(self, client_with_motor, mock_motor):
        """测试忙碌状态下执行定位。

        注意：API 允许在 BUSY 状态下发送新的运动命令（会排队执行），
        所以返回 200 而不是错误。
        """
        mock_motor.status = DeviceStatus.BUSY

        response = client_with_motor.post(
            "/api/v1/motor/move",
            json={"position_mm": 10.0, "velocity_mm_s": 5.0},
        )

        # API 允许在 BUSY 状态下发送命令
        assert response.status_code == 200

    def test_jog_busy(self, client_with_motor, mock_motor):
        """测试忙碌状态下 JOG。

        注意：API 允许在 BUSY 状态下发送新的 JOG 命令，
        所以返回 200 而不是错误。
        """
        mock_motor.status = DeviceStatus.BUSY

        response = client_with_motor.post(
            "/api/v1/motor/jog",
            json={"direction": 1, "velocity_mm_s": 5.0},
        )

        # API 允许在 BUSY 状态下发送命令
        assert response.status_code == 200

    # ==================== 错误状态测试 ====================

    def test_move_motor_error_state(self, client_with_motor, mock_motor):
        """测试错误状态下执行定位。"""
        mock_motor.status = DeviceStatus.ERROR
        mock_motor.last_error = "Test error"

        response = client_with_motor.post(
            "/api/v1/motor/move",
            json={"position_mm": 10.0, "velocity_mm_s": 5.0},
        )

        # API 返回 500 错误（设备处于错误状态异常）
        assert response.status_code == 500
