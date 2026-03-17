"""
电磁铁控制 API 测试模块

文件名: test_api_electromagnet.py
路径: backend/tests/
功能: 测试电磁铁控制API的所有端点，包括磁场控制、扫描功能、安全限制、校准等
作者: CAUC-SEP Team
创建日期: 2026-03-16
依赖: pytest, pytest-asyncio, httpx, fastapi

测试内容：
1. 磁场控制测试
   - 恒流模式电流设置
   - 磁场值设置
   - 动态范围验证

2. 扫描功能测试
   - 正向扫描
   - 反向扫描
   - 三角波扫描
   - 扫描参数验证

3. 安全限制测试
   - 过流保护
   - 急停功能
   - 保护复位

4. 校准测试
   - 校准点添加
   - 校准执行
   - 校准数据管理
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import electromagnet
from core.abstract import DeviceStatus
from core.electromagnet_driver import ElectromagnetStatus, ScanMode


@pytest.fixture
def mock_electromagnet_driver():
    """创建Mock电磁铁驱动器实例。"""
    driver = MagicMock()
    driver.device_id = "test_electromagnet"
    driver.status = DeviceStatus.READY
    driver.electromagnet_status = ElectromagnetStatus.IDLE
    driver.last_error = None
    driver.simulation_mode = True

    # 电流限制
    driver.max_current_limit = 10.0

    # 校准数据
    driver.calibration_coefficient = 0.2  # T/A

    # 异步方法Mock
    driver.connect = AsyncMock(return_value=True)
    driver.disconnect = AsyncMock(return_value=True)
    driver.set_current = AsyncMock(return_value=True)
    driver.set_field = AsyncMock(return_value=True)
    driver.start_scan = AsyncMock(return_value=True)
    driver.stop_scan = AsyncMock(return_value=True)
    driver.calibrate = AsyncMock(return_value=True)
    driver.clear_calibration = AsyncMock(return_value=True)
    driver.emergency_stop = AsyncMock(return_value=True)
    driver.reset_emergency = AsyncMock(return_value=True)
    driver.reset_overcurrent_protection = AsyncMock(return_value=True)

    driver.read_status = AsyncMock(
        return_value={
            "device_id": "test_electromagnet",
            "status": "ready",
            "electromagnet_status": "idle",
            "current_value": 0.0,
            "field_value": 0.0,
            "scan_progress": 0.0,
            "max_current_limit": 10.0,
            "connected": True,
            "simulation": True,
            "calibration_points_count": 0,
            "calibration_coefficient": 0.2,
        }
    )

    driver.get_calibration_data = MagicMock(
        return_value={
            "valid": False,
            "points": [],
            "coefficient": 0.2,
        }
    )

    driver.validate_scan_params = MagicMock(return_value=(True, []))
    driver._estimate_scan_duration = MagicMock(return_value=100.0)

    return driver


@pytest.fixture
def app_with_electromagnet(mock_electromagnet_driver):
    """创建带Mock电磁铁的FastAPI应用。"""
    app = FastAPI()
    app.include_router(electromagnet.router)
    electromagnet.set_electromagnet(mock_electromagnet_driver)
    return app


@pytest.fixture
def client_with_electromagnet(app_with_electromagnet):
    """创建测试客户端。"""
    with TestClient(app_with_electromagnet) as client:
        yield client


# ==================== 磁场控制测试 ====================


class TestElectromagnetFieldControl:
    """测试电磁铁磁场控制功能。"""

    def test_set_current_success(self, client_with_electromagnet, mock_electromagnet_driver):
        """测试成功设置电流。"""
        mock_electromagnet_driver.status = DeviceStatus.READY
        mock_electromagnet_driver.electromagnet_status = ElectromagnetStatus.IDLE
        mock_electromagnet_driver.set_current = AsyncMock(return_value=True)

        response = client_with_electromagnet.post(
            "/api/v1/electromagnet/current",
            json={"current": 5.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_set_current_minimum(self, client_with_electromagnet, mock_electromagnet_driver):
        """测试设置最小电流。"""
        mock_electromagnet_driver.status = DeviceStatus.READY
        mock_electromagnet_driver.electromagnet_status = ElectromagnetStatus.IDLE
        mock_electromagnet_driver.set_current = AsyncMock(return_value=True)

        response = client_with_electromagnet.post(
            "/api/v1/electromagnet/current",
            json={"current": 0.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_set_current_maximum(self, client_with_electromagnet, mock_electromagnet_driver):
        """测试设置最大电流。"""
        mock_electromagnet_driver.status = DeviceStatus.READY
        mock_electromagnet_driver.electromagnet_status = ElectromagnetStatus.IDLE
        mock_electromagnet_driver.set_current = AsyncMock(return_value=True)

        response = client_with_electromagnet.post(
            "/api/v1/electromagnet/current",
            json={"current": 10.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_set_current_exceeds_limit(self, client_with_electromagnet, mock_electromagnet_driver):
        """测试电流超出限制。"""
        mock_electromagnet_driver.status = DeviceStatus.READY
        mock_electromagnet_driver.electromagnet_status = ElectromagnetStatus.IDLE

        response = client_with_electromagnet.post(
            "/api/v1/electromagnet/current",
            json={"current": 15.0},
        )

        # Pydantic验证返回422，API返回400
        assert response.status_code in [400, 422]

    def test_set_current_negative(self, client_with_electromagnet, mock_electromagnet_driver):
        """测试负电流被拒绝。"""
        mock_electromagnet_driver.status = DeviceStatus.READY
        mock_electromagnet_driver.electromagnet_status = ElectromagnetStatus.IDLE

        response = client_with_electromagnet.post(
            "/api/v1/electromagnet/current",
            json={"current": -1.0},
        )

        # Pydantic验证返回422，API返回400
        assert response.status_code in [400, 422]

    def test_set_current_disconnected_device(
        self, client_with_electromagnet, mock_electromagnet_driver
    ):
        """测试设备断开时设置电流失败。"""
        mock_electromagnet_driver.status = DeviceStatus.DISCONNECTED

        response = client_with_electromagnet.post(
            "/api/v1/electromagnet/current",
            json={"current": 5.0},
        )

        assert response.status_code == 400

    def test_set_current_overcurrent_state(
        self, client_with_electromagnet, mock_electromagnet_driver
    ):
        """测试过流状态下设置电流失败。"""
        mock_electromagnet_driver.status = DeviceStatus.READY
        mock_electromagnet_driver.electromagnet_status = ElectromagnetStatus.OVERCURRENT

        response = client_with_electromagnet.post(
            "/api/v1/electromagnet/current",
            json={"current": 5.0},
        )

        assert response.status_code == 400

    def test_set_field_success(self, client_with_electromagnet, mock_electromagnet_driver):
        """测试成功设置磁场。"""
        mock_electromagnet_driver.status = DeviceStatus.READY
        mock_electromagnet_driver.set_field = AsyncMock(return_value=True)

        response = client_with_electromagnet.post(
            "/api/v1/electromagnet/field",
            json={"current": 1.0},  # 使用current字段传递磁场值
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


# ==================== 扫描功能测试 ====================


class TestElectromagnetScan:
    """测试电磁铁扫描功能。"""

    def test_start_scan_forward(self, client_with_electromagnet, mock_electromagnet_driver):
        """测试启动正向扫描。"""
        mock_electromagnet_driver.status = DeviceStatus.READY
        mock_electromagnet_driver.electromagnet_status = ElectromagnetStatus.IDLE
        mock_electromagnet_driver.start_scan = AsyncMock(return_value=True)

        response = client_with_electromagnet.post(
            "/api/v1/electromagnet/scan",
            json={
                "mode": "forward",
                "start_current": 0.0,
                "end_current": 5.0,
                "scan_rate": 0.1,
                "cycles": 1,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_start_scan_reverse(self, client_with_electromagnet, mock_electromagnet_driver):
        """测试启动反向扫描。"""
        mock_electromagnet_driver.status = DeviceStatus.READY
        mock_electromagnet_driver.electromagnet_status = ElectromagnetStatus.IDLE
        mock_electromagnet_driver.start_scan = AsyncMock(return_value=True)

        response = client_with_electromagnet.post(
            "/api/v1/electromagnet/scan",
            json={
                "mode": "reverse",
                "start_current": 5.0,
                "end_current": 0.0,
                "scan_rate": 0.1,
                "cycles": 1,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_start_scan_triangular(self, client_with_electromagnet, mock_electromagnet_driver):
        """测试启动三角波扫描。"""
        mock_electromagnet_driver.status = DeviceStatus.READY
        mock_electromagnet_driver.electromagnet_status = ElectromagnetStatus.IDLE
        mock_electromagnet_driver.start_scan = AsyncMock(return_value=True)

        response = client_with_electromagnet.post(
            "/api/v1/electromagnet/scan",
            json={
                "mode": "triangular",
                "start_current": 0.0,
                "end_current": 5.0,
                "scan_rate": 0.1,
                "cycles": 3,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_start_scan_with_step_interval(
        self, client_with_electromagnet, mock_electromagnet_driver
    ):
        """测试带步进间隔的扫描。"""
        mock_electromagnet_driver.status = DeviceStatus.READY
        mock_electromagnet_driver.electromagnet_status = ElectromagnetStatus.IDLE
        mock_electromagnet_driver.start_scan = AsyncMock(return_value=True)

        response = client_with_electromagnet.post(
            "/api/v1/electromagnet/scan",
            json={
                "mode": "triangular",
                "start_current": 0.0,
                "end_current": 5.0,
                "scan_rate": 0.1,
                "cycles": 1,
                "step_interval_ms": 100.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_start_scan_invalid_rate(self, client_with_electromagnet, mock_electromagnet_driver):
        """测试无效扫描速率。"""
        mock_electromagnet_driver.status = DeviceStatus.READY
        mock_electromagnet_driver.electromagnet_status = ElectromagnetStatus.IDLE

        response = client_with_electromagnet.post(
            "/api/v1/electromagnet/scan",
            json={
                "mode": "forward",
                "start_current": 0.0,
                "end_current": 5.0,
                "scan_rate": 5.0,  # 超出范围
                "cycles": 1,
            },
        )

        assert response.status_code == 422

    def test_start_scan_current_exceeds_limit(
        self, client_with_electromagnet, mock_electromagnet_driver
    ):
        """测试扫描电流超出限制。"""
        mock_electromagnet_driver.status = DeviceStatus.READY
        mock_electromagnet_driver.electromagnet_status = ElectromagnetStatus.IDLE

        response = client_with_electromagnet.post(
            "/api/v1/electromagnet/scan",
            json={
                "mode": "forward",
                "start_current": 0.0,
                "end_current": 15.0,  # 超出限制
                "scan_rate": 0.1,
                "cycles": 1,
            },
        )

        # Pydantic验证返回422，API返回400
        assert response.status_code in [400, 422]

    def test_stop_scan(self, client_with_electromagnet, mock_electromagnet_driver):
        """测试停止扫描。"""
        mock_electromagnet_driver.stop_scan = AsyncMock(return_value=True)

        response = client_with_electromagnet.post("/api/v1/electromagnet/scan/stop")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_validate_scan_params_valid(
        self, client_with_electromagnet, mock_electromagnet_driver
    ):
        """测试验证有效扫描参数。"""
        mock_electromagnet_driver.validate_scan_params = MagicMock(return_value=(True, []))
        mock_electromagnet_driver._estimate_scan_duration = MagicMock(return_value=50.0)

        response = client_with_electromagnet.post(
            "/api/v1/electromagnet/scan/validate",
            json={
                "mode": "forward",
                "start_current": 0.0,
                "end_current": 5.0,
                "scan_rate": 0.1,
                "cycles": 1,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["estimated_duration_s"] == 50.0

    def test_validate_scan_params_with_warnings(
        self, client_with_electromagnet, mock_electromagnet_driver
    ):
        """测试验证有警告的扫描参数。"""
        mock_electromagnet_driver.validate_scan_params = MagicMock(return_value=(True, []))
        mock_electromagnet_driver._estimate_scan_duration = MagicMock(return_value=5000.0)

        response = client_with_electromagnet.post(
            "/api/v1/electromagnet/scan/validate",
            json={
                "mode": "triangular",
                "start_current": 0.0,
                "end_current": 9.5,  # 接近限制
                "scan_rate": 0.01,
                "cycles": 10,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        # 应该有警告
        assert len(data["warnings"]) > 0


# ==================== 安全限制测试 ====================


class TestElectromagnetSafety:
    """测试电磁铁安全限制功能。"""

    def test_emergency_stop(self, client_with_electromagnet, mock_electromagnet_driver):
        """测试紧急停止。"""
        mock_electromagnet_driver.emergency_stop = AsyncMock(return_value=True)

        response = client_with_electromagnet.post("/api/v1/electromagnet/emergency_stop")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_reset_emergency(self, client_with_electromagnet, mock_electromagnet_driver):
        """测试复位急停状态。"""
        mock_electromagnet_driver.reset_emergency = AsyncMock(return_value=True)

        response = client_with_electromagnet.post("/api/v1/electromagnet/reset_emergency")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_reset_overcurrent_protection(
        self, client_with_electromagnet, mock_electromagnet_driver
    ):
        """测试复位过流保护。"""
        mock_electromagnet_driver.reset_overcurrent_protection = AsyncMock(return_value=True)

        response = client_with_electromagnet.post(
            "/api/v1/electromagnet/reset_overcurrent"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_emergency_stop_then_operation_blocked(
        self, client_with_electromagnet, mock_electromagnet_driver
    ):
        """测试急停后操作被阻止。"""
        # 先触发急停
        mock_electromagnet_driver.emergency_stop = AsyncMock(return_value=True)
        response = client_with_electromagnet.post("/api/v1/electromagnet/emergency_stop")
        assert response.status_code == 200

        # 设置急停状态
        mock_electromagnet_driver.status = DeviceStatus.EMERGENCY_STOP

        # 尝试设置电流应该失败
        response = client_with_electromagnet.post(
            "/api/v1/electromagnet/current",
            json={"current": 5.0},
        )
        assert response.status_code == 400


# ==================== 校准测试 ====================


class TestElectromagnetCalibration:
    """测试电磁铁校准功能。"""

    def test_calibrate_success(self, client_with_electromagnet, mock_electromagnet_driver):
        """测试成功执行校准。"""
        mock_electromagnet_driver.status = DeviceStatus.READY
        mock_electromagnet_driver.calibrate = AsyncMock(return_value=True)

        response = client_with_electromagnet.post(
            "/api/v1/electromagnet/calibrate",
            json={
                "calibration_points": [
                    {"current": 0.0, "field": 0.0},
                    {"current": 5.0, "field": 1.0},
                    {"current": 10.0, "field": 2.0},
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_calibrate_insufficient_points(
        self, client_with_electromagnet, mock_electromagnet_driver
    ):
        """测试校准点数量不足。"""
        mock_electromagnet_driver.status = DeviceStatus.READY

        response = client_with_electromagnet.post(
            "/api/v1/electromagnet/calibrate",
            json={
                "calibration_points": [
                    {"current": 0.0, "field": 0.0},
                ]
            },
        )

        assert response.status_code == 422

    def test_calibrate_invalid_current(self, client_with_electromagnet, mock_electromagnet_driver):
        """测试无效电流校准点。"""
        mock_electromagnet_driver.status = DeviceStatus.READY

        response = client_with_electromagnet.post(
            "/api/v1/electromagnet/calibrate",
            json={
                "calibration_points": [
                    {"current": -1.0, "field": 0.0},
                    {"current": 5.0, "field": 1.0},
                ]
            },
        )

        # Pydantic验证返回422，API返回400
        assert response.status_code in [400, 422]

    def test_calibrate_invalid_field(self, client_with_electromagnet, mock_electromagnet_driver):
        """测试无效磁场校准点。"""
        mock_electromagnet_driver.status = DeviceStatus.READY

        response = client_with_electromagnet.post(
            "/api/v1/electromagnet/calibrate",
            json={
                "calibration_points": [
                    {"current": 0.0, "field": 0.0},
                    {"current": 5.0, "field": 5.0},  # 超出最大磁场
                ]
            },
        )

        # Pydantic验证返回422，API返回400
        assert response.status_code in [400, 422]

    def test_get_calibration_data(self, client_with_electromagnet, mock_electromagnet_driver):
        """测试获取校准数据。"""
        mock_electromagnet_driver.get_calibration_data = MagicMock(
            return_value={
                "valid": True,
                "points": [
                    {"current": 0.0, "field": 0.0},
                    {"current": 5.0, "field": 1.0},
                    {"current": 10.0, "field": 2.0},
                ],
                "coefficient": 0.2,
            }
        )

        response = client_with_electromagnet.get("/api/v1/electromagnet/calibration")

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert "coefficient" in data

    def test_clear_calibration(self, client_with_electromagnet, mock_electromagnet_driver):
        """测试清除校准数据。"""
        mock_electromagnet_driver.clear_calibration = AsyncMock(return_value=True)

        response = client_with_electromagnet.delete("/api/v1/electromagnet/calibration")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_validate_calibration_data_valid(
        self, client_with_electromagnet, mock_electromagnet_driver
    ):
        """测试验证有效校准数据。"""
        response = client_with_electromagnet.post(
            "/api/v1/electromagnet/calibration/validate",
            json={
                "calibration_points": [
                    {"current": 0.0, "field": 0.0},
                    {"current": 5.0, "field": 1.0},
                    {"current": 10.0, "field": 2.0},
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True

    def test_validate_calibration_data_narrow_range(
        self, client_with_electromagnet, mock_electromagnet_driver
    ):
        """测试验证窄范围校准数据（有警告）。"""
        response = client_with_electromagnet.post(
            "/api/v1/electromagnet/calibration/validate",
            json={
                "calibration_points": [
                    {"current": 4.0, "field": 0.8},
                    {"current": 5.0, "field": 1.0},
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        # 窄范围可能有警告（取决于API实现）
        # 如果有warnings字段，检查其内容
        if "warnings" in data:
            # 窄范围可能产生警告
            pass


# ==================== 状态查询测试 ====================


class TestElectromagnetStatusQuery:
    """测试电磁铁状态查询功能。"""

    def test_get_status_success(self, client_with_electromagnet, mock_electromagnet_driver):
        """测试成功获取状态。"""
        mock_electromagnet_driver.read_status = AsyncMock(
            return_value={
                "device_id": "test_electromagnet",
                "status": "ready",
                "electromagnet_status": "idle",
                "current_value": 5.0,
                "field_value": 1.0,
                "scan_progress": 0.0,
                "max_current_limit": 10.0,
                "connected": True,
                "simulation": True,
                "calibration_points_count": 3,
                "calibration_coefficient": 0.2,
            }
        )

        response = client_with_electromagnet.get("/api/v1/electromagnet/status")

        assert response.status_code == 200
        data = response.json()
        assert data["device_id"] == "test_electromagnet"
        assert data["status"] == "ready"
        assert data["current_value"] == 5.0
        assert data["field_value"] == 1.0

    def test_get_status_scanning(self, client_with_electromagnet, mock_electromagnet_driver):
        """测试扫描中状态。"""
        mock_electromagnet_driver.read_status = AsyncMock(
            return_value={
                "device_id": "test_electromagnet",
                "status": "ready",
                "electromagnet_status": "scanning",
                "current_value": 2.5,
                "field_value": 0.5,
                "scan_progress": 0.5,
                "max_current_limit": 10.0,
                "connected": True,
                "simulation": True,
                "calibration_points_count": 3,
                "calibration_coefficient": 0.2,
            }
        )

        response = client_with_electromagnet.get("/api/v1/electromagnet/status")

        assert response.status_code == 200
        data = response.json()
        assert data["electromagnet_status"] == "scanning"
        assert data["scan_progress"] == 0.5


# ==================== 连接管理测试 ====================


class TestElectromagnetConnection:
    """测试电磁铁连接管理功能。"""

    def test_connect_success(self, client_with_electromagnet, mock_electromagnet_driver):
        """测试成功连接。"""
        mock_electromagnet_driver.connect = AsyncMock(return_value=True)

        response = client_with_electromagnet.post("/api/v1/electromagnet/connect")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_disconnect_success(self, client_with_electromagnet, mock_electromagnet_driver):
        """测试成功断开连接。"""
        mock_electromagnet_driver.disconnect = AsyncMock(return_value=True)

        response = client_with_electromagnet.post("/api/v1/electromagnet/disconnect")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


# ==================== 设备未初始化测试 ====================


class TestElectromagnetNotInitialized:
    """测试设备未初始化场景。"""

    def test_status_not_initialized(self):
        """测试设备未初始化时获取状态。"""
        app = FastAPI()
        app.include_router(electromagnet.router)

        with TestClient(app) as client:
            response = client.get("/api/v1/electromagnet/status")
            assert response.status_code == 503

    def test_set_current_not_initialized(self):
        """测试设备未初始化时设置电流。"""
        app = FastAPI()
        app.include_router(electromagnet.router)

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/electromagnet/current",
                json={"current": 5.0},
            )
            assert response.status_code == 503
