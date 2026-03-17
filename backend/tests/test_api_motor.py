"""
电机控制 API 测试模块

文件名: test_api_motor.py
路径: backend/tests/
功能: 测试电机控制API的所有端点，包括位置控制、速度控制、回零、急停等
作者: CAUC-SEP Team
创建日期: 2026-03-16
依赖: pytest, pytest-asyncio, httpx, fastapi

测试内容：
1. 位置控制测试
   - 绝对定位
   - 相对定位
   - 位置范围验证

2. 速度控制测试
   - JOG正向/负向运动
   - 速度范围验证

3. 回零操作测试
   - 回零启动
   - 回零状态验证

4. 急停功能测试
   - 急停触发
   - 急停复位

5. 状态查询测试
   - 状态读取
   - 状态字解析
   - 报警代码读取
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from api import motor
from api.motor import MotorAPIException
from core.abstract import DeviceStatus
from core.dm2c_driver import ALARM_CODES
from schemas.common import ErrorResponse


@pytest.fixture
def mock_motor_driver():
    """创建Mock电机驱动器实例。"""
    driver = MagicMock()
    driver.device_id = "test_motor"
    driver.status = DeviceStatus.READY
    driver.steps_per_mm = 1600
    driver.last_error = None

    # 限位配置
    driver.limit_config = MagicMock()
    driver.limit_config.positive_limit = 100.0
    driver.limit_config.negative_limit = -100.0
    driver.limit_config.enable = True
    driver.limit_config.is_within_limits = MagicMock(return_value=True)

    # 异步方法Mock
    driver.connect = AsyncMock(return_value=True)
    driver.disconnect = AsyncMock(return_value=True)
    driver.move_abs = AsyncMock(return_value=True)
    driver.move_rel = AsyncMock(return_value=True)
    driver.jog = AsyncMock(return_value=True)
    driver.stop = AsyncMock(return_value=True)
    driver.emergency_stop = AsyncMock(return_value=True)
    driver.reset_emergency = AsyncMock(return_value=True)
    driver.home = AsyncMock(return_value=True)
    driver.reset_alarm = AsyncMock(return_value=True)
    driver.save_parameters = AsyncMock(return_value=True)
    driver.factory_reset = AsyncMock(return_value=True)
    driver.read_status = AsyncMock(
        return_value={
            "device_id": "test_motor",
            "status": "ready",
            "position_steps": 0,
            "position_mm": 0.0,
            "velocity_mm_s": 0.0,
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
            "simulation": True,
        }
    )
    driver.read_status_word = AsyncMock(
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
    driver.read_alarm_code = AsyncMock(return_value=0)
    driver.configure_pr_path = AsyncMock(return_value=True)
    driver.trigger_pr_path = AsyncMock(return_value=True)
    driver.set_soft_limits = MagicMock()

    return driver


@pytest.fixture
def app_with_motor(mock_motor_driver):
    """创建带Mock电机的FastAPI应用。"""
    app = FastAPI()
    
    # 添加异常处理器
    @app.exception_handler(MotorAPIException)
    async def motor_api_exception_handler(request: Request, exc: MotorAPIException):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error_code": exc.error_code,
                "message": exc.message,
                "detail": exc.detail,
            },
        )
    
    app.include_router(motor.router)
    motor.set_dm2c(mock_motor_driver)
    return app


@pytest.fixture
def client_with_motor(app_with_motor):
    """创建测试客户端。"""
    with TestClient(app_with_motor) as client:
        yield client


# ==================== 位置控制测试 ====================


class TestMotorPositionControl:
    """测试电机位置控制功能。"""

    def test_absolute_positioning_success(self, client_with_motor, mock_motor_driver):
        """测试成功执行绝对定位。"""
        mock_motor_driver.status = DeviceStatus.READY
        mock_motor_driver.move_abs = AsyncMock(return_value=True)

        response = client_with_motor.post(
            "/api/v1/motor/move",
            json={"position_mm": 25.0, "velocity_mm_s": 10.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["target_position_mm"] == 25.0
        assert "target_position_steps" in data

    def test_absolute_positioning_with_full_params(
        self, client_with_motor, mock_motor_driver
    ):
        """测试带完整参数的绝对定位。"""
        mock_motor_driver.status = DeviceStatus.READY
        mock_motor_driver.move_abs = AsyncMock(return_value=True)

        response = client_with_motor.post(
            "/api/v1/motor/move",
            json={
                "position_mm": 50.0,
                "velocity_mm_s": 20.0,
                "accel_mm_s2": 500.0,
                "decel_mm_s2": 500.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["target_position_mm"] == 50.0

    def test_positioning_negative_position(self, client_with_motor, mock_motor_driver):
        """测试负向位置定位。"""
        mock_motor_driver.status = DeviceStatus.READY
        mock_motor_driver.move_abs = AsyncMock(return_value=True)

        response = client_with_motor.post(
            "/api/v1/motor/move",
            json={"position_mm": -50.0, "velocity_mm_s": 10.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["target_position_mm"] == -50.0

    def test_positioning_zero_position(self, client_with_motor, mock_motor_driver):
        """测试归零位置定位。"""
        mock_motor_driver.status = DeviceStatus.READY
        mock_motor_driver.move_abs = AsyncMock(return_value=True)

        response = client_with_motor.post(
            "/api/v1/motor/move",
            json={"position_mm": 0.0, "velocity_mm_s": 10.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["target_position_mm"] == 0.0

    def test_positioning_disconnected_device(self, client_with_motor, mock_motor_driver):
        """测试设备断开时定位失败。"""
        mock_motor_driver.status = DeviceStatus.DISCONNECTED

        response = client_with_motor.post(
            "/api/v1/motor/move",
            json={"position_mm": 10.0, "velocity_mm_s": 5.0},
        )

        assert response.status_code == 400

    def test_positioning_emergency_stop_state(self, client_with_motor, mock_motor_driver):
        """测试急停状态下定位失败。"""
        mock_motor_driver.status = DeviceStatus.EMERGENCY_STOP

        response = client_with_motor.post(
            "/api/v1/motor/move",
            json={"position_mm": 10.0, "velocity_mm_s": 5.0},
        )

        assert response.status_code == 400

    def test_positioning_soft_limit_exceeded(self, client_with_motor, mock_motor_driver):
        """测试超出软件限位时定位失败。"""
        mock_motor_driver.status = DeviceStatus.READY
        mock_motor_driver.limit_config.is_within_limits = MagicMock(return_value=False)

        response = client_with_motor.post(
            "/api/v1/motor/move",
            json={"position_mm": 150.0, "velocity_mm_s": 5.0},
        )

        # Pydantic验证会返回422，或者API返回400
        assert response.status_code in [400, 422]

    def test_positioning_invalid_position_too_high(self, client_with_motor, mock_motor_driver):
        """测试位置超出上限验证。"""
        mock_motor_driver.status = DeviceStatus.READY

        response = client_with_motor.post(
            "/api/v1/motor/move",
            json={"position_mm": 150.0, "velocity_mm_s": 5.0},
        )

        # Pydantic验证会返回422
        assert response.status_code in [400, 422]

    def test_positioning_invalid_velocity(self, client_with_motor, mock_motor_driver):
        """测试无效速度验证。"""
        mock_motor_driver.status = DeviceStatus.READY

        response = client_with_motor.post(
            "/api/v1/motor/move",
            json={"position_mm": 10.0, "velocity_mm_s": 100.0},
        )

        assert response.status_code == 422


# ==================== 速度控制测试 ====================


class TestMotorVelocityControl:
    """测试电机速度控制功能。"""

    def test_jog_positive_success(self, client_with_motor, mock_motor_driver):
        """测试成功正向JOG。"""
        mock_motor_driver.status = DeviceStatus.READY
        mock_motor_driver.jog = AsyncMock(return_value=True)

        response = client_with_motor.post(
            "/api/v1/motor/jog",
            json={"direction": 1, "velocity_mm_s": 10.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "正向" in data["message"] or "+" in data["message"]

    def test_jog_negative_success(self, client_with_motor, mock_motor_driver):
        """测试成功负向JOG。"""
        mock_motor_driver.status = DeviceStatus.READY
        mock_motor_driver.jog = AsyncMock(return_value=True)

        response = client_with_motor.post(
            "/api/v1/motor/jog",
            json={"direction": -1, "velocity_mm_s": 10.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "负向" in data["message"] or "-" in data["message"]

    def test_jog_custom_velocity(self, client_with_motor, mock_motor_driver):
        """测试自定义速度JOG。"""
        mock_motor_driver.status = DeviceStatus.READY
        mock_motor_driver.jog = AsyncMock(return_value=True)

        response = client_with_motor.post(
            "/api/v1/motor/jog",
            json={"direction": 1, "velocity_mm_s": 15.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_jog_invalid_direction(self, client_with_motor, mock_motor_driver):
        """测试无效方向JOG。"""
        mock_motor_driver.status = DeviceStatus.READY

        response = client_with_motor.post(
            "/api/v1/motor/jog",
            json={"direction": 2, "velocity_mm_s": 10.0},
        )

        assert response.status_code == 422

    def test_jog_invalid_velocity_too_high(self, client_with_motor, mock_motor_driver):
        """测试速度超出上限JOG。"""
        mock_motor_driver.status = DeviceStatus.READY

        response = client_with_motor.post(
            "/api/v1/motor/jog",
            json={"direction": 1, "velocity_mm_s": 50.0},
        )

        assert response.status_code == 422

    def test_jog_disconnected_device(self, client_with_motor, mock_motor_driver):
        """测试设备断开时JOG失败。"""
        mock_motor_driver.status = DeviceStatus.DISCONNECTED

        response = client_with_motor.post(
            "/api/v1/motor/jog",
            json={"direction": 1, "velocity_mm_s": 10.0},
        )

        assert response.status_code == 400


# ==================== 回零操作测试 ====================


class TestMotorHoming:
    """测试电机回零功能。"""

    def test_home_success(self, client_with_motor, mock_motor_driver):
        """测试成功执行回零。"""
        mock_motor_driver.status = DeviceStatus.READY
        mock_motor_driver.home = AsyncMock(return_value=True)

        response = client_with_motor.post(
            "/api/v1/motor/home",
            json={"mode": "origin"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "回零" in data["message"] or "Homing" in data["message"]

    def test_home_with_mode(self, client_with_motor, mock_motor_driver):
        """测试指定模式回零。"""
        mock_motor_driver.status = DeviceStatus.READY
        mock_motor_driver.home = AsyncMock(return_value=True)

        response = client_with_motor.post(
            "/api/v1/motor/home",
            json={"mode": "negative"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_home_disconnected_device(self, client_with_motor, mock_motor_driver):
        """测试设备断开时回零失败。"""
        mock_motor_driver.status = DeviceStatus.DISCONNECTED

        response = client_with_motor.post(
            "/api/v1/motor/home",
            json={"mode": "origin"},
        )

        assert response.status_code == 400

    def test_home_emergency_stop_state(self, client_with_motor, mock_motor_driver):
        """测试急停状态下回零失败。"""
        mock_motor_driver.status = DeviceStatus.EMERGENCY_STOP

        response = client_with_motor.post(
            "/api/v1/motor/home",
            json={"mode": "origin"},
        )

        assert response.status_code == 400


# ==================== 急停功能测试 ====================


class TestMotorEmergencyStop:
    """测试电机急停功能。"""

    def test_emergency_stop_success(self, client_with_motor, mock_motor_driver):
        """测试成功执行急停。"""
        mock_motor_driver.emergency_stop = AsyncMock(return_value=True)

        response = client_with_motor.post("/api/v1/motor/emergency_stop")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "急停" in data["message"] or "Emergency" in data["message"]

    def test_reset_emergency_success(self, client_with_motor, mock_motor_driver):
        """测试成功复位急停状态。"""
        mock_motor_driver.reset_emergency = AsyncMock(return_value=True)

        response = client_with_motor.post("/api/v1/motor/reset")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_emergency_stop_then_move_blocked(
        self, client_with_motor, mock_motor_driver
    ):
        """测试急停后运动被阻止。"""
        # 先触发急停
        mock_motor_driver.emergency_stop = AsyncMock(return_value=True)
        response = client_with_motor.post("/api/v1/motor/emergency_stop")
        assert response.status_code == 200

        # 设置急停状态
        mock_motor_driver.status = DeviceStatus.EMERGENCY_STOP

        # 尝试运动应该失败
        response = client_with_motor.post(
            "/api/v1/motor/move",
            json={"position_mm": 10.0, "velocity_mm_s": 5.0},
        )
        assert response.status_code == 400


# ==================== 状态查询测试 ====================


class TestMotorStatusQuery:
    """测试电机状态查询功能。"""

    def test_get_status_success(self, client_with_motor, mock_motor_driver):
        """测试成功获取状态。"""
        mock_motor_driver.read_status = AsyncMock(
            return_value={
                "device_id": "test_motor",
                "status": "ready",
                "position_steps": 16000,
                "position_mm": 10.0,
                "velocity_mm_s": 0.0,
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
                "simulation": True,
            }
        )

        response = client_with_motor.get("/api/v1/motor/status")

        assert response.status_code == 200
        data = response.json()
        assert data["device_id"] == "test_motor"
        assert data["status"] == "ready"
        assert data["position_mm"] == 10.0

    def test_get_status_word_success(self, client_with_motor, mock_motor_driver):
        """测试成功获取状态字。"""
        mock_motor_driver.read_status_word = AsyncMock(
            return_value={
                "fault": False,
                "enabled": True,
                "running": True,
                "cmd_complete": False,
                "path_complete": False,
                "home_complete": True,
                "raw_value": 0x76,
            }
        )

        response = client_with_motor.get("/api/v1/motor/status_word")

        assert response.status_code == 200
        data = response.json()
        assert data["fault"] is False
        assert data["enabled"] is True
        assert data["running"] is True
        assert data["raw_value"] == 0x76

    def test_get_alarm_code_no_alarm(self, client_with_motor, mock_motor_driver):
        """测试无报警状态。"""
        mock_motor_driver.read_alarm_code = AsyncMock(return_value=0)

        response = client_with_motor.get("/api/v1/motor/alarm_code")

        assert response.status_code == 200
        data = response.json()
        assert data["alarm_code"] == 0
        # ALARM_CODES字典中没有0键，默认返回"未知故障"
        assert "alarm_text" in data

    def test_get_alarm_code_with_alarm(self, client_with_motor, mock_motor_driver):
        """测试有报警状态。"""
        mock_motor_driver.read_alarm_code = AsyncMock(return_value=0x01)

        response = client_with_motor.get("/api/v1/motor/alarm_code")

        assert response.status_code == 200
        data = response.json()
        assert data["alarm_code"] == 0x01
        assert data["alarm_text"] == ALARM_CODES.get(0x01, "未知故障")

    def test_get_limits_success(self, client_with_motor, mock_motor_driver):
        """测试成功获取限位配置。"""
        mock_motor_driver.limit_config.positive_limit = 80.0
        mock_motor_driver.limit_config.negative_limit = -80.0
        mock_motor_driver.limit_config.enable = True

        response = client_with_motor.get("/api/v1/motor/limits")

        assert response.status_code == 200
        data = response.json()
        assert data["positive_mm"] == 80.0
        assert data["negative_mm"] == -80.0
        assert data["enabled"] is True

    def test_status_not_initialized(self):
        """测试设备未初始化时获取状态。"""
        # 创建新的应用，不设置设备
        app = FastAPI()
        
        # 添加异常处理器
        @app.exception_handler(MotorAPIException)
        async def motor_api_exception_handler(request: Request, exc: MotorAPIException):
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "success": False,
                    "error_code": exc.error_code,
                    "message": exc.message,
                    "detail": exc.detail,
                },
            )
        
        app.include_router(motor.router)
        # 不调用motor.set_dm2c()，模拟设备未初始化

        with TestClient(app) as client:
            response = client.get("/api/v1/motor/status")
            # 设备未初始化时应该返回503
            assert response.status_code == 503


# ==================== 连接管理测试 ====================


class TestMotorConnection:
    """测试电机连接管理功能。"""

    def test_connect_success(self, client_with_motor, mock_motor_driver):
        """测试成功连接。"""
        mock_motor_driver.connect = AsyncMock(return_value=True)

        response = client_with_motor.post("/api/v1/motor/connect")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_connect_failure(self, client_with_motor, mock_motor_driver):
        """测试连接失败。"""
        mock_motor_driver.connect = AsyncMock(return_value=False)
        mock_motor_driver.last_error = "Connection timeout"

        response = client_with_motor.post("/api/v1/motor/connect")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_disconnect_success(self, client_with_motor, mock_motor_driver):
        """测试成功断开连接。"""
        mock_motor_driver.disconnect = AsyncMock(return_value=True)

        response = client_with_motor.post("/api/v1/motor/disconnect")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


# ==================== 限位配置测试 ====================


class TestMotorLimitConfig:
    """测试电机限位配置功能。"""

    def test_set_limits_success(self, client_with_motor, mock_motor_driver):
        """测试成功设置限位。"""
        mock_motor_driver.set_soft_limits = MagicMock()

        response = client_with_motor.post(
            "/api/v1/motor/limits",
            json={"positive_mm": 50.0, "negative_mm": -50.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_motor_driver.set_soft_limits.assert_called_once_with(50.0, -50.0)

    def test_set_limits_invalid_range(self, client_with_motor, mock_motor_driver):
        """测试无效限位范围（负限位大于正限位）。"""
        response = client_with_motor.post(
            "/api/v1/motor/limits",
            json={"positive_mm": -50.0, "negative_mm": 50.0},
        )

        assert response.status_code == 422


# ==================== PR路径测试 ====================


class TestMotorPRPath:
    """测试电机PR路径功能。"""

    def test_configure_pr_path_success(self, client_with_motor, mock_motor_driver):
        """测试成功配置PR路径。"""
        mock_motor_driver.status = DeviceStatus.READY
        mock_motor_driver.configure_pr_path = AsyncMock(return_value=True)

        response = client_with_motor.post(
            "/api/v1/motor/pr/config",
            json={
                "path_number": 0,
                "mode": 1,
                "position_mm": 25.0,
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

    def test_configure_pr_path_invalid_number(self, client_with_motor, mock_motor_driver):
        """测试无效路径编号。"""
        mock_motor_driver.status = DeviceStatus.READY

        response = client_with_motor.post(
            "/api/v1/motor/pr/config",
            json={
                "path_number": 20,
                "mode": 1,
                "position_mm": 25.0,
                "velocity_mm_s": 1000,
            },
        )

        assert response.status_code == 422

    def test_trigger_pr_path_success(self, client_with_motor, mock_motor_driver):
        """测试成功触发PR路径。"""
        mock_motor_driver.status = DeviceStatus.READY
        mock_motor_driver.trigger_pr_path = AsyncMock(return_value=True)

        response = client_with_motor.post(
            "/api/v1/motor/pr/trigger",
            json={"path_number": 0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_trigger_pr_path_invalid_number(self, client_with_motor, mock_motor_driver):
        """测试触发无效路径编号。"""
        mock_motor_driver.status = DeviceStatus.READY

        response = client_with_motor.post(
            "/api/v1/motor/pr/trigger",
            json={"path_number": 20},
        )

        assert response.status_code == 422


# ==================== 报警复位测试 ====================


class TestMotorAlarmReset:
    """测试电机报警复位功能。"""

    def test_reset_alarm_success(self, client_with_motor, mock_motor_driver):
        """测试成功复位报警。"""
        mock_motor_driver.status = DeviceStatus.READY
        mock_motor_driver.reset_alarm = AsyncMock(return_value=True)

        response = client_with_motor.post("/api/v1/motor/reset_alarm")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_reset_alarm_disconnected(self, client_with_motor, mock_motor_driver):
        """测试断开状态下复位报警失败。"""
        mock_motor_driver.status = DeviceStatus.DISCONNECTED

        response = client_with_motor.post("/api/v1/motor/reset_alarm")

        assert response.status_code == 400


# ==================== 参数管理测试 ====================


class TestMotorParameterManagement:
    """测试电机参数管理功能。"""

    def test_save_params_success(self, client_with_motor, mock_motor_driver):
        """测试成功保存参数。"""
        mock_motor_driver.status = DeviceStatus.READY
        mock_motor_driver.save_parameters = AsyncMock(return_value=True)

        response = client_with_motor.post("/api/v1/motor/save_params")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "EEPROM" in data["message"]

    def test_factory_reset_success(self, client_with_motor, mock_motor_driver):
        """测试成功恢复出厂设置。"""
        mock_motor_driver.status = DeviceStatus.READY
        mock_motor_driver.factory_reset = AsyncMock(return_value=True)

        response = client_with_motor.post("/api/v1/motor/factory_reset")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
