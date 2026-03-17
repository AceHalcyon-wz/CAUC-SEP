"""
压电陶瓷控制 API 测试模块

文件名: test_api_piezo.py
路径: backend/tests/
功能: 测试压电陶瓷控制API的所有端点，包括电压设置、位置控制、校准操作等
作者: CAUC-SEP Team
创建日期: 2026-03-16
依赖: pytest, pytest-asyncio, httpx, fastapi

测试内容：
1. 电压设置测试
   - 电压范围验证
   - 开环控制模式

2. 位置控制测试
   - 位移设置
   - 闭环控制模式
   - 校准数据验证

3. 校准操作测试
   - 添加校准点
   - 执行校准
   - 校准数据管理

4. 状态监控测试
   - 状态查询
   - 控制模式切换
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import piezo
from core.abstract import DeviceStatus
from core.piezo_controller import CalibrationType, ControlMode


@pytest.fixture
def mock_piezo_controller():
    """创建Mock压电陶瓷控制器实例。"""
    controller = MagicMock()
    controller.device_id = "test_piezo"
    controller.status = DeviceStatus.READY
    controller.last_error = None
    controller.simulation_mode = True

    # 控制模式
    controller.control_mode = ControlMode.OPEN_LOOP

    # 校准数据
    controller.calibration_valid = False
    controller.calibration_points = []

    # 异步方法Mock
    controller.connect = AsyncMock(return_value=True)
    controller.disconnect = AsyncMock(return_value=True)
    controller.set_voltage = AsyncMock(return_value=True)
    controller.set_displacement = AsyncMock(return_value=True)
    controller.get_voltage = AsyncMock(return_value=75.0)
    controller.get_displacement = AsyncMock(return_value=50.0)
    controller.add_calibration_point = AsyncMock(return_value=True)
    controller.perform_calibration = AsyncMock(return_value=True)
    controller.clear_calibration = AsyncMock(return_value=True)
    controller.set_control_mode = AsyncMock(return_value=True)
    controller.zero = AsyncMock(return_value=True)
    controller.max_extend = AsyncMock(return_value=True)

    controller.read_status = AsyncMock(
        return_value={
            "device_id": "test_piezo",
            "status": "ready",
            "control_mode": "open_loop",
            "current_voltage_v": 75.0,
            "current_displacement_um": 50.0,
            "target_displacement_um": 0.0,
            "calibration_valid": False,
            "calibration_points": 0,
            "max_voltage_v": 150.0,
            "max_displacement_um": 100.0,
            "connected": True,
            "simulation": True,
        }
    )

    controller.get_calibration_data = MagicMock(
        return_value={
            "valid": False,
            "type": "linear",
            "points": [],
            "coefficients": [],
            "point_count": 0,
        }
    )

    controller.get_control_mode = MagicMock(return_value=ControlMode.OPEN_LOOP)

    return controller


@pytest.fixture
def app_with_piezo(mock_piezo_controller):
    """创建带Mock压电陶瓷的FastAPI应用。"""
    app = FastAPI()
    app.include_router(piezo.router)
    piezo.set_piezo(mock_piezo_controller)
    return app


@pytest.fixture
def client_with_piezo(app_with_piezo):
    """创建测试客户端。"""
    with TestClient(app_with_piezo) as client:
        yield client


# ==================== 电压设置测试 ====================


class TestPiezoVoltageControl:
    """测试压电陶瓷电压控制功能。"""

    def test_set_voltage_success(self, client_with_piezo, mock_piezo_controller):
        """测试成功设置电压。"""
        mock_piezo_controller.status = DeviceStatus.READY
        mock_piezo_controller.set_voltage = AsyncMock(return_value=True)
        mock_piezo_controller.get_voltage = AsyncMock(return_value=75.0)
        mock_piezo_controller.get_displacement = AsyncMock(return_value=50.0)

        response = client_with_piezo.post(
            "/api/v1/piezo/voltage",
            json={"voltage_v": 75.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["current_voltage_v"] == 75.0

    def test_set_voltage_minimum(self, client_with_piezo, mock_piezo_controller):
        """测试设置最小电压。"""
        mock_piezo_controller.status = DeviceStatus.READY
        mock_piezo_controller.set_voltage = AsyncMock(return_value=True)
        mock_piezo_controller.get_voltage = AsyncMock(return_value=0.0)
        mock_piezo_controller.get_displacement = AsyncMock(return_value=0.0)

        response = client_with_piezo.post(
            "/api/v1/piezo/voltage",
            json={"voltage_v": 0.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_set_voltage_maximum(self, client_with_piezo, mock_piezo_controller):
        """测试设置最大电压。"""
        mock_piezo_controller.status = DeviceStatus.READY
        mock_piezo_controller.set_voltage = AsyncMock(return_value=True)
        mock_piezo_controller.get_voltage = AsyncMock(return_value=150.0)
        mock_piezo_controller.get_displacement = AsyncMock(return_value=100.0)

        response = client_with_piezo.post(
            "/api/v1/piezo/voltage",
            json={"voltage_v": 150.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_set_voltage_exceeds_maximum(self, client_with_piezo, mock_piezo_controller):
        """测试电压超出最大值。"""
        mock_piezo_controller.status = DeviceStatus.READY

        response = client_with_piezo.post(
            "/api/v1/piezo/voltage",
            json={"voltage_v": 200.0},
        )

        assert response.status_code == 422

    def test_set_voltage_negative(self, client_with_piezo, mock_piezo_controller):
        """测试负电压被拒绝。"""
        mock_piezo_controller.status = DeviceStatus.READY

        response = client_with_piezo.post(
            "/api/v1/piezo/voltage",
            json={"voltage_v": -10.0},
        )

        assert response.status_code == 422

    def test_set_voltage_disconnected_device(self, client_with_piezo, mock_piezo_controller):
        """测试设备断开时设置电压失败。"""
        mock_piezo_controller.status = DeviceStatus.DISCONNECTED

        response = client_with_piezo.post(
            "/api/v1/piezo/voltage",
            json={"voltage_v": 75.0},
        )

        assert response.status_code == 400

    def test_get_voltage_success(self, client_with_piezo, mock_piezo_controller):
        """测试成功获取电压。"""
        mock_piezo_controller.status = DeviceStatus.READY
        mock_piezo_controller.get_voltage = AsyncMock(return_value=75.0)
        mock_piezo_controller.get_displacement = AsyncMock(return_value=50.0)

        response = client_with_piezo.get("/api/v1/piezo/voltage")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["current_voltage_v"] == 75.0


# ==================== 位移控制测试 ====================


class TestPiezoDisplacementControl:
    """测试压电陶瓷位移控制功能。"""

    def test_set_displacement_success(self, client_with_piezo, mock_piezo_controller):
        """测试成功设置位移。"""
        mock_piezo_controller.status = DeviceStatus.READY
        mock_piezo_controller.set_displacement = AsyncMock(return_value=True)
        mock_piezo_controller.get_displacement = AsyncMock(return_value=50.0)
        mock_piezo_controller.get_voltage = AsyncMock(return_value=75.0)

        response = client_with_piezo.post(
            "/api/v1/piezo/displacement",
            json={"displacement_um": 50.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["current_displacement_um"] == 50.0

    def test_set_displacement_minimum(self, client_with_piezo, mock_piezo_controller):
        """测试设置最小位移。"""
        mock_piezo_controller.status = DeviceStatus.READY
        mock_piezo_controller.set_displacement = AsyncMock(return_value=True)
        mock_piezo_controller.get_displacement = AsyncMock(return_value=0.0)
        mock_piezo_controller.get_voltage = AsyncMock(return_value=0.0)

        response = client_with_piezo.post(
            "/api/v1/piezo/displacement",
            json={"displacement_um": 0.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_set_displacement_maximum(self, client_with_piezo, mock_piezo_controller):
        """测试设置最大位移。"""
        mock_piezo_controller.status = DeviceStatus.READY
        mock_piezo_controller.set_displacement = AsyncMock(return_value=True)
        mock_piezo_controller.get_displacement = AsyncMock(return_value=100.0)
        mock_piezo_controller.get_voltage = AsyncMock(return_value=150.0)

        response = client_with_piezo.post(
            "/api/v1/piezo/displacement",
            json={"displacement_um": 100.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_set_displacement_exceeds_maximum(self, client_with_piezo, mock_piezo_controller):
        """测试位移超出最大值。"""
        mock_piezo_controller.status = DeviceStatus.READY

        response = client_with_piezo.post(
            "/api/v1/piezo/displacement",
            json={"displacement_um": 150.0},
        )

        assert response.status_code == 422

    def test_set_displacement_negative(self, client_with_piezo, mock_piezo_controller):
        """测试负位移被拒绝。"""
        mock_piezo_controller.status = DeviceStatus.READY

        response = client_with_piezo.post(
            "/api/v1/piezo/displacement",
            json={"displacement_um": -10.0},
        )

        assert response.status_code == 422

    def test_set_displacement_disconnected_device(
        self, client_with_piezo, mock_piezo_controller
    ):
        """测试设备断开时设置位移失败。"""
        mock_piezo_controller.status = DeviceStatus.DISCONNECTED

        response = client_with_piezo.post(
            "/api/v1/piezo/displacement",
            json={"displacement_um": 50.0},
        )

        assert response.status_code == 400

    def test_get_displacement_success(self, client_with_piezo, mock_piezo_controller):
        """测试成功获取位移。"""
        mock_piezo_controller.status = DeviceStatus.READY
        mock_piezo_controller.get_displacement = AsyncMock(return_value=50.0)
        mock_piezo_controller.get_voltage = AsyncMock(return_value=75.0)

        response = client_with_piezo.get("/api/v1/piezo/displacement")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["current_displacement_um"] == 50.0


# ==================== 校准操作测试 ====================


class TestPiezoCalibration:
    """测试压电陶瓷校准功能。"""

    def test_add_calibration_point_success(self, client_with_piezo, mock_piezo_controller):
        """测试成功添加校准点。"""
        mock_piezo_controller.add_calibration_point = AsyncMock(return_value=True)
        mock_piezo_controller.get_calibration_data = MagicMock(
            return_value={
                "valid": False,
                "type": "linear",
                "points": [{"voltage_v": 75.0, "displacement_um": 50.0}],
                "coefficients": [],
                "point_count": 1,
            }
        )

        response = client_with_piezo.post(
            "/api/v1/piezo/calibrate/point",
            json={"voltage_v": 75.0, "displacement_um": 50.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["point_count"] == 1

    def test_add_calibration_point_invalid_voltage(
        self, client_with_piezo, mock_piezo_controller
    ):
        """测试添加无效电压校准点。"""
        response = client_with_piezo.post(
            "/api/v1/piezo/calibrate/point",
            json={"voltage_v": 200.0, "displacement_um": 50.0},
        )

        assert response.status_code == 422

    def test_add_calibration_point_invalid_displacement(
        self, client_with_piezo, mock_piezo_controller
    ):
        """测试添加无效位移校准点。"""
        response = client_with_piezo.post(
            "/api/v1/piezo/calibrate/point",
            json={"voltage_v": 75.0, "displacement_um": 150.0},
        )

        assert response.status_code == 422

    def test_perform_calibration_linear(self, client_with_piezo, mock_piezo_controller):
        """测试执行线性校准。"""
        mock_piezo_controller.perform_calibration = AsyncMock(return_value=True)

        response = client_with_piezo.post(
            "/api/v1/piezo/calibrate/perform",
            json={"calibration_type": "linear"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_perform_calibration_polynomial(
        self, client_with_piezo, mock_piezo_controller
    ):
        """测试执行多项式校准。"""
        mock_piezo_controller.perform_calibration = AsyncMock(return_value=True)

        response = client_with_piezo.post(
            "/api/v1/piezo/calibrate/perform",
            json={"calibration_type": "polynomial"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_perform_calibration_piecewise(
        self, client_with_piezo, mock_piezo_controller
    ):
        """测试执行分段校准。"""
        mock_piezo_controller.perform_calibration = AsyncMock(return_value=True)

        response = client_with_piezo.post(
            "/api/v1/piezo/calibrate/perform",
            json={"calibration_type": "piecewise"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_perform_calibration_invalid_type(
        self, client_with_piezo, mock_piezo_controller
    ):
        """测试无效校准类型。"""
        response = client_with_piezo.post(
            "/api/v1/piezo/calibrate/perform",
            json={"calibration_type": "invalid"},
        )

        assert response.status_code == 400

    def test_get_calibration_data(self, client_with_piezo, mock_piezo_controller):
        """测试获取校准数据。"""
        mock_piezo_controller.get_calibration_data = MagicMock(
            return_value={
                "valid": True,
                "type": "polynomial",
                "points": [
                    {"voltage_v": 0.0, "displacement_um": 0.0},
                    {"voltage_v": 75.0, "displacement_um": 50.0},
                    {"voltage_v": 150.0, "displacement_um": 100.0},
                ],
                "coefficients": [0.0, 0.667, 0.0],
                "point_count": 3,
            }
        )

        response = client_with_piezo.get("/api/v1/piezo/calibrate/data")

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["type"] == "polynomial"
        assert data["point_count"] == 3

    def test_clear_calibration(self, client_with_piezo, mock_piezo_controller):
        """测试清除校准数据。"""
        mock_piezo_controller.clear_calibration = AsyncMock(return_value=True)

        response = client_with_piezo.delete("/api/v1/piezo/calibrate")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


# ==================== 控制模式测试 ====================


class TestPiezoControlMode:
    """测试压电陶瓷控制模式功能。"""

    def test_set_control_mode_open_loop(self, client_with_piezo, mock_piezo_controller):
        """测试设置开环控制模式。"""
        mock_piezo_controller.set_control_mode = AsyncMock(return_value=True)

        response = client_with_piezo.post(
            "/api/v1/piezo/mode",
            json={"mode": "open_loop"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_set_control_mode_closed_loop(self, client_with_piezo, mock_piezo_controller):
        """测试设置闭环控制模式。"""
        mock_piezo_controller.set_control_mode = AsyncMock(return_value=True)

        response = client_with_piezo.post(
            "/api/v1/piezo/mode",
            json={"mode": "closed_loop"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_set_control_mode_invalid(self, client_with_piezo, mock_piezo_controller):
        """测试设置无效控制模式。"""
        response = client_with_piezo.post(
            "/api/v1/piezo/mode",
            json={"mode": "invalid_mode"},
        )

        assert response.status_code == 400

    def test_get_control_mode(self, client_with_piezo, mock_piezo_controller):
        """测试获取当前控制模式。"""
        mock_piezo_controller.get_control_mode = MagicMock(return_value=ControlMode.OPEN_LOOP)

        response = client_with_piezo.get("/api/v1/piezo/mode")

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "open_loop"


# ==================== 状态查询测试 ====================


class TestPiezoStatusQuery:
    """测试压电陶瓷状态查询功能。"""

    def test_get_status_success(self, client_with_piezo, mock_piezo_controller):
        """测试成功获取状态。"""
        mock_piezo_controller.read_status = AsyncMock(
            return_value={
                "device_id": "test_piezo",
                "status": "ready",
                "control_mode": "open_loop",
                "current_voltage_v": 75.0,
                "current_displacement_um": 50.0,
                "target_displacement_um": 0.0,
                "calibration_valid": False,
                "calibration_points": 0,
                "max_voltage_v": 150.0,
                "max_displacement_um": 100.0,
                "connected": True,
                "simulation": True,
            }
        )

        response = client_with_piezo.get("/api/v1/piezo/status")

        assert response.status_code == 200
        data = response.json()
        assert data["device_id"] == "test_piezo"
        assert data["status"] == "ready"
        assert data["current_voltage_v"] == 75.0
        assert data["current_displacement_um"] == 50.0

    def test_get_status_with_calibration(self, client_with_piezo, mock_piezo_controller):
        """测试获取带校准的状态。"""
        mock_piezo_controller.read_status = AsyncMock(
            return_value={
                "device_id": "test_piezo",
                "status": "ready",
                "control_mode": "closed_loop",
                "current_voltage_v": 75.0,
                "current_displacement_um": 50.0,
                "target_displacement_um": 50.0,
                "calibration_valid": True,
                "calibration_points": 3,
                "max_voltage_v": 150.0,
                "max_displacement_um": 100.0,
                "connected": True,
                "simulation": True,
            }
        )

        response = client_with_piezo.get("/api/v1/piezo/status")

        assert response.status_code == 200
        data = response.json()
        assert data["calibration_valid"] is True
        assert data["calibration_points"] == 3


# ==================== 便捷操作测试 ====================


class TestPiezoConvenienceOperations:
    """测试压电陶瓷便捷操作功能。"""

    def test_zero_position(self, client_with_piezo, mock_piezo_controller):
        """测试归零操作。"""
        mock_piezo_controller.status = DeviceStatus.READY
        mock_piezo_controller.zero = AsyncMock(return_value=True)

        response = client_with_piezo.post("/api/v1/piezo/zero")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_max_extend(self, client_with_piezo, mock_piezo_controller):
        """测试最大伸展操作。"""
        mock_piezo_controller.status = DeviceStatus.READY
        mock_piezo_controller.max_extend = AsyncMock(return_value=True)

        response = client_with_piezo.post("/api/v1/piezo/max_extend")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_connect_success(self, client_with_piezo, mock_piezo_controller):
        """测试成功连接。"""
        mock_piezo_controller.connect = AsyncMock(return_value=True)

        response = client_with_piezo.post("/api/v1/piezo/connect")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_disconnect_success(self, client_with_piezo, mock_piezo_controller):
        """测试成功断开连接。"""
        mock_piezo_controller.disconnect = AsyncMock(return_value=True)

        response = client_with_piezo.post("/api/v1/piezo/disconnect")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


# ==================== 设备未初始化测试 ====================


class TestPiezoNotInitialized:
    """测试设备未初始化场景。"""

    def test_status_not_initialized(self):
        """测试设备未初始化时获取状态。"""
        app = FastAPI()
        app.include_router(piezo.router)
        # 不设置设备

        with TestClient(app) as client:
            response = client.get("/api/v1/piezo/status")
            assert response.status_code == 503

    def test_set_voltage_not_initialized(self):
        """测试设备未初始化时设置电压。"""
        app = FastAPI()
        app.include_router(piezo.router)

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/piezo/voltage",
                json={"voltage_v": 75.0},
            )
            assert response.status_code == 503
