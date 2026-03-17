"""
温度控制 API 测试模块

文件名: test_api_temperature.py
路径: backend/tests/
功能: 测试温度控制API的所有端点，包括温度设置、PID参数、程序控温、温度曲线等
作者: CAUC-SEP Team
创建日期: 2026-03-16
依赖: pytest, pytest-asyncio, httpx, fastapi

测试内容：
1. 温度设置测试
   - 温度设定点设置
   - 温度范围验证

2. PID参数测试
   - PID参数设置
   - PID参数验证
   - PID控制启停

3. 程序控温测试
   - 程序设置
   - 程序启停
   - 多段程序验证

4. 温度曲线测试
   - 历史记录获取
   - 历史记录清除
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import temperature
from core.abstract import DeviceStatus
from core.temperature_controller import PIDParameters


@pytest.fixture
def mock_temperature_controller():
    """创建Mock温度控制器实例。"""
    controller = MagicMock()
    controller.device_id = "test_temp_controller"
    controller.status = DeviceStatus.READY
    controller.last_error = None
    controller.simulation_mode = True

    # 温度范围常量
    controller.MIN_TEMPERATURE = 77.0
    controller.MAX_TEMPERATURE = 400.0

    # PID参数
    controller.pid_params = PIDParameters(
        kp=10.0,
        ki=0.5,
        kd=1.0,
        setpoint=300.0,
        output_min=0.0,
        output_max=100.0,
    )

    # 异步方法Mock
    controller.connect = AsyncMock(return_value=True)
    controller.disconnect = AsyncMock(return_value=True)
    controller.set_temperature = AsyncMock(return_value=True)
    controller.set_pid_parameters = AsyncMock(return_value=True)
    controller.start_pid_control = AsyncMock(return_value=True)
    controller.stop_pid_control = AsyncMock(return_value=True)
    controller.load_program = AsyncMock(return_value=True)
    controller.start_program = AsyncMock(return_value=True)
    controller.stop_program = AsyncMock(return_value=True)
    controller.set_protection_config = AsyncMock(return_value=True)
    controller.clear_protection = AsyncMock(return_value=True)
    controller.emergency_stop = AsyncMock(return_value=True)
    controller.reset_emergency = AsyncMock(return_value=True)
    controller.clear_temperature_history = AsyncMock(return_value=True)
    controller.export_temperature_history = AsyncMock(return_value="timestamp,temp,setpoint\n")

    controller.read_status = AsyncMock(
        return_value={
            "device_id": "test_temp_controller",
            "status": "ready",
            "current_temperature": 300.0,
            "current_output": 0.0,
            "setpoint": 300.0,
            "mode": "PID",
            "pid_running": False,
            "connected": True,
            "simulation": True,
            "program": {"running": False, "progress": 0.0, "current_segment": 0},
            "protection": {"triggered": False, "type": None},
        }
    )

    controller.get_temperature_history = AsyncMock(
        return_value=[
            {"timestamp": 0.0, "temperature": 300.0, "setpoint": 300.0},
            {"timestamp": 1.0, "temperature": 301.0, "setpoint": 300.0},
            {"timestamp": 2.0, "temperature": 300.5, "setpoint": 300.0},
        ]
    )

    return controller


@pytest.fixture
def app_with_temperature(mock_temperature_controller):
    """创建带Mock温度控制器的FastAPI应用。"""
    app = FastAPI()
    app.include_router(temperature.router)
    temperature.set_temperature_controller(mock_temperature_controller)
    return app


@pytest.fixture
def client_with_temperature(app_with_temperature):
    """创建测试客户端。"""
    with TestClient(app_with_temperature) as client:
        yield client


# ==================== 温度设置测试 ====================


class TestTemperatureSetpoint:
    """测试温度设定点功能。"""

    def test_set_temperature_success(self, client_with_temperature, mock_temperature_controller):
        """测试成功设置温度。"""
        mock_temperature_controller.status = DeviceStatus.READY
        mock_temperature_controller.set_temperature = AsyncMock(return_value=True)

        response = client_with_temperature.post(
            "/api/v1/temperature/setpoint",
            json={"temperature": 350.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_set_temperature_minimum(self, client_with_temperature, mock_temperature_controller):
        """测试设置最低温度（液氮温度）。"""
        mock_temperature_controller.status = DeviceStatus.READY
        mock_temperature_controller.set_temperature = AsyncMock(return_value=True)

        response = client_with_temperature.post(
            "/api/v1/temperature/setpoint",
            json={"temperature": 77.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_set_temperature_maximum(self, client_with_temperature, mock_temperature_controller):
        """测试设置最高温度。"""
        mock_temperature_controller.status = DeviceStatus.READY
        mock_temperature_controller.set_temperature = AsyncMock(return_value=True)

        response = client_with_temperature.post(
            "/api/v1/temperature/setpoint",
            json={"temperature": 400.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_set_temperature_below_minimum(self, client_with_temperature, mock_temperature_controller):
        """测试设置低于最低温度。"""
        mock_temperature_controller.status = DeviceStatus.READY

        response = client_with_temperature.post(
            "/api/v1/temperature/setpoint",
            json={"temperature": 50.0},
        )

        # Pydantic验证返回422，API返回400
        assert response.status_code in [400, 422]

    def test_set_temperature_above_maximum(self, client_with_temperature, mock_temperature_controller):
        """测试设置高于最高温度。"""
        mock_temperature_controller.status = DeviceStatus.READY

        response = client_with_temperature.post(
            "/api/v1/temperature/setpoint",
            json={"temperature": 500.0},
        )

        # Pydantic验证返回422，API返回400
        assert response.status_code in [400, 422]

    def test_set_temperature_disconnected_device(
        self, client_with_temperature, mock_temperature_controller
    ):
        """测试设备断开时设置温度失败。"""
        mock_temperature_controller.status = DeviceStatus.DISCONNECTED

        response = client_with_temperature.post(
            "/api/v1/temperature/setpoint",
            json={"temperature": 300.0},
        )

        assert response.status_code == 400


# ==================== PID参数测试 ====================


class TestPIDParameters:
    """测试PID参数功能。"""

    def test_set_pid_parameters_success(self, client_with_temperature, mock_temperature_controller):
        """测试成功设置PID参数。"""
        mock_temperature_controller.status = DeviceStatus.READY
        mock_temperature_controller.set_pid_parameters = AsyncMock(return_value=True)

        response = client_with_temperature.post(
            "/api/v1/temperature/pid",
            json={
                "kp": 15.0,
                "ki": 0.8,
                "kd": 1.5,
                "setpoint": 320.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_set_pid_parameters_invalid_kp(self, client_with_temperature, mock_temperature_controller):
        """测试无效Kp参数。"""
        mock_temperature_controller.status = DeviceStatus.READY

        response = client_with_temperature.post(
            "/api/v1/temperature/pid",
            json={
                "kp": 200.0,  # 超出范围
                "ki": 0.5,
                "kd": 1.0,
                "setpoint": 300.0,
            },
        )

        # Pydantic验证返回422，API返回400
        assert response.status_code in [400, 422]

    def test_set_pid_parameters_invalid_ki(self, client_with_temperature, mock_temperature_controller):
        """测试无效Ki参数。"""
        mock_temperature_controller.status = DeviceStatus.READY

        response = client_with_temperature.post(
            "/api/v1/temperature/pid",
            json={
                "kp": 10.0,
                "ki": 20.0,  # 超出范围
                "kd": 1.0,
                "setpoint": 300.0,
            },
        )

        # Pydantic验证返回422，API返回400
        assert response.status_code in [400, 422]

    def test_set_pid_parameters_invalid_kd(self, client_with_temperature, mock_temperature_controller):
        """测试无效Kd参数。"""
        mock_temperature_controller.status = DeviceStatus.READY

        response = client_with_temperature.post(
            "/api/v1/temperature/pid",
            json={
                "kp": 10.0,
                "ki": 0.5,
                "kd": 20.0,  # 超出范围
                "setpoint": 300.0,
            },
        )

        # Pydantic验证返回422，API返回400
        assert response.status_code in [400, 422]

    def test_set_pid_parameters_invalid_setpoint(
        self, client_with_temperature, mock_temperature_controller
    ):
        """测试无效设定点。"""
        mock_temperature_controller.status = DeviceStatus.READY

        response = client_with_temperature.post(
            "/api/v1/temperature/pid",
            json={
                "kp": 10.0,
                "ki": 0.5,
                "kd": 1.0,
                "setpoint": 500.0,  # 超出范围
            },
        )

        # Pydantic验证返回422，API返回400
        assert response.status_code in [400, 422]

    def test_get_pid_parameters(self, client_with_temperature, mock_temperature_controller):
        """测试获取PID参数。"""
        response = client_with_temperature.get("/api/v1/temperature/pid")

        assert response.status_code == 200
        data = response.json()
        assert "kp" in data
        assert "ki" in data
        assert "kd" in data
        assert "setpoint" in data

    def test_validate_pid_parameters_valid(self, client_with_temperature, mock_temperature_controller):
        """测试验证有效的PID参数。"""
        response = client_with_temperature.post(
            "/api/v1/temperature/pid/validate",
            json={
                "kp": 10.0,
                "ki": 0.5,
                "kd": 1.0,
                "setpoint": 300.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True

    def test_validate_pid_parameters_with_warnings(
        self, client_with_temperature, mock_temperature_controller
    ):
        """测试验证有警告的PID参数。"""
        response = client_with_temperature.post(
            "/api/v1/temperature/pid/validate",
            json={
                "kp": 60.0,  # 较大值
                "ki": 6.0,   # 较大值
                "kd": 1.0,
                "setpoint": 300.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        # 参数有效但有警告
        assert len(data["warnings"]) > 0

    def test_start_pid_control(self, client_with_temperature, mock_temperature_controller):
        """测试启动PID控制。"""
        mock_temperature_controller.status = DeviceStatus.READY
        mock_temperature_controller.start_pid_control = AsyncMock(return_value=True)

        response = client_with_temperature.post("/api/v1/temperature/pid/start")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_stop_pid_control(self, client_with_temperature, mock_temperature_controller):
        """测试停止PID控制。"""
        mock_temperature_controller.stop_pid_control = AsyncMock(return_value=True)

        response = client_with_temperature.post("/api/v1/temperature/pid/stop")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


# ==================== 程序控温测试 ====================


class TestTemperatureProgram:
    """测试程序控温功能。"""

    def test_set_program_success(self, client_with_temperature, mock_temperature_controller):
        """测试成功设置温度程序。"""
        mock_temperature_controller.status = DeviceStatus.READY
        mock_temperature_controller.load_program = AsyncMock(return_value=True)
        mock_temperature_controller.start_program = AsyncMock(return_value=True)

        response = client_with_temperature.post(
            "/api/v1/temperature/program",
            json={
                "segments": [
                    {
                        "target_temperature": 350.0,
                        "ramp_rate": 2.0,
                        "hold_time": 600.0,
                    },
                    {
                        "target_temperature": 300.0,
                        "ramp_rate": -1.0,
                        "hold_time": 300.0,
                    },
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_set_program_single_segment(self, client_with_temperature, mock_temperature_controller):
        """测试单段温度程序。"""
        mock_temperature_controller.status = DeviceStatus.READY
        mock_temperature_controller.load_program = AsyncMock(return_value=True)
        mock_temperature_controller.start_program = AsyncMock(return_value=True)

        response = client_with_temperature.post(
            "/api/v1/temperature/program",
            json={
                "segments": [
                    {
                        "target_temperature": 350.0,
                        "ramp_rate": 5.0,
                        "hold_time": 0.0,
                    }
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_set_program_invalid_temperature(self, client_with_temperature, mock_temperature_controller):
        """测试无效温度程序段。"""
        mock_temperature_controller.status = DeviceStatus.READY

        response = client_with_temperature.post(
            "/api/v1/temperature/program",
            json={
                "segments": [
                    {
                        "target_temperature": 500.0,  # 超出范围
                        "ramp_rate": 2.0,
                        "hold_time": 600.0,
                    }
                ]
            },
        )

        # Pydantic验证返回422，API返回400
        assert response.status_code in [400, 422]

    def test_set_program_invalid_ramp_rate(self, client_with_temperature, mock_temperature_controller):
        """测试无效升降温速率。"""
        mock_temperature_controller.status = DeviceStatus.READY

        response = client_with_temperature.post(
            "/api/v1/temperature/program",
            json={
                "segments": [
                    {
                        "target_temperature": 350.0,
                        "ramp_rate": 20.0,  # 超出范围
                        "hold_time": 600.0,
                    }
                ]
            },
        )

        # Pydantic验证返回422，API返回400
        assert response.status_code in [400, 422]

    def test_set_program_negative_hold_time(self, client_with_temperature, mock_temperature_controller):
        """测试负保持时间。"""
        mock_temperature_controller.status = DeviceStatus.READY

        response = client_with_temperature.post(
            "/api/v1/temperature/program",
            json={
                "segments": [
                    {
                        "target_temperature": 350.0,
                        "ramp_rate": 2.0,
                        "hold_time": -10.0,
                    }
                ]
            },
        )

        # Pydantic验证返回422，API返回400
        assert response.status_code in [400, 422]

    def test_stop_program(self, client_with_temperature, mock_temperature_controller):
        """测试停止温度程序。"""
        mock_temperature_controller.stop_program = AsyncMock(return_value=True)

        response = client_with_temperature.post("/api/v1/temperature/program/stop")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_set_program_disconnected_device(
        self, client_with_temperature, mock_temperature_controller
    ):
        """测试设备断开时设置程序失败。"""
        mock_temperature_controller.status = DeviceStatus.DISCONNECTED

        response = client_with_temperature.post(
            "/api/v1/temperature/program",
            json={
                "segments": [
                    {
                        "target_temperature": 350.0,
                        "ramp_rate": 2.0,
                        "hold_time": 600.0,
                    }
                ]
            },
        )

        assert response.status_code == 400


# ==================== 温度曲线测试 ====================


class TestTemperatureHistory:
    """测试温度历史记录功能。"""

    def test_get_history_success(self, client_with_temperature, mock_temperature_controller):
        """测试成功获取历史记录。"""
        mock_temperature_controller.get_temperature_history = AsyncMock(
            return_value=[
                {"timestamp": 0.0, "temperature": 300.0, "setpoint": 300.0},
                {"timestamp": 1.0, "temperature": 301.0, "setpoint": 300.0},
            ]
        )

        response = client_with_temperature.post(
            "/api/v1/temperature/history",
            json={"duration_seconds": 60.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["timestamps"]) > 0
        assert len(data["temperatures"]) > 0

    def test_get_history_custom_duration(self, client_with_temperature, mock_temperature_controller):
        """测试自定义时长历史记录。"""
        mock_temperature_controller.get_temperature_history = AsyncMock(
            return_value=[
                {"timestamp": i, "temperature": 300.0 + i * 0.1, "setpoint": 300.0}
                for i in range(100)
            ]
        )

        response = client_with_temperature.post(
            "/api/v1/temperature/history",
            json={"duration_seconds": 300.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_history_invalid_duration(self, client_with_temperature, mock_temperature_controller):
        """测试无效时长。"""
        response = client_with_temperature.post(
            "/api/v1/temperature/history",
            json={"duration_seconds": 5000.0},  # 超出范围
        )

        assert response.status_code == 422

    def test_clear_history(self, client_with_temperature, mock_temperature_controller):
        """测试清除历史记录。"""
        mock_temperature_controller.clear_temperature_history = AsyncMock(return_value=True)

        response = client_with_temperature.post("/api/v1/temperature/history/clear")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_export_history_csv(self, client_with_temperature, mock_temperature_controller):
        """测试导出CSV格式历史记录。"""
        mock_temperature_controller.export_temperature_history = AsyncMock(
            return_value="timestamp,temperature,setpoint\n0,300.0,300.0\n"
        )

        response = client_with_temperature.get("/api/v1/temperature/history/export?format=csv")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["format"] == "csv"

    def test_export_history_json(self, client_with_temperature, mock_temperature_controller):
        """测试导出JSON格式历史记录。"""
        mock_temperature_controller.export_temperature_history = AsyncMock(
            return_value='[{"timestamp": 0, "temperature": 300.0}]'
        )

        response = client_with_temperature.get("/api/v1/temperature/history/export?format=json")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["format"] == "json"


# ==================== 保护功能测试 ====================


class TestTemperatureProtection:
    """测试温度保护功能。"""

    def test_set_protection_config(self, client_with_temperature, mock_temperature_controller):
        """测试设置保护配置。"""
        mock_temperature_controller.set_protection_config = AsyncMock(return_value=True)

        response = client_with_temperature.post(
            "/api/v1/temperature/protection",
            json={
                "max_temperature": 450.0,
                "min_temperature": 70.0,
                "max_deviation": 20.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_clear_protection(self, client_with_temperature, mock_temperature_controller):
        """测试清除保护状态。"""
        mock_temperature_controller.clear_protection = AsyncMock(return_value=True)

        response = client_with_temperature.post("/api/v1/temperature/protection/clear")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_emergency_stop(self, client_with_temperature, mock_temperature_controller):
        """测试紧急停止。"""
        mock_temperature_controller.emergency_stop = AsyncMock(return_value=True)

        response = client_with_temperature.post("/api/v1/temperature/emergency_stop")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_reset_emergency(self, client_with_temperature, mock_temperature_controller):
        """测试复位急停状态。"""
        mock_temperature_controller.reset_emergency = AsyncMock(return_value=True)

        response = client_with_temperature.post("/api/v1/temperature/reset")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


# ==================== 状态查询测试 ====================


class TestTemperatureStatusQuery:
    """测试温度状态查询功能。"""

    def test_get_status_success(self, client_with_temperature, mock_temperature_controller):
        """测试成功获取状态。"""
        mock_temperature_controller.read_status = AsyncMock(
            return_value={
                "device_id": "test_temp_controller",
                "status": "ready",
                "current_temperature": 300.0,
                "current_output": 25.0,
                "setpoint": 300.0,
                "mode": "PID",
                "pid_running": True,
                "connected": True,
                "simulation": True,
                "program": {"running": False, "progress": 0.0, "current_segment": 0},
                "protection": {"triggered": False, "type": None},
            }
        )

        response = client_with_temperature.get("/api/v1/temperature/status")

        assert response.status_code == 200
        data = response.json()
        assert data["device_id"] == "test_temp_controller"
        assert data["status"] == "ready"
        assert data["current_temperature"] == 300.0
        assert data["pid_enabled"] is True

    def test_get_status_with_program_running(
        self, client_with_temperature, mock_temperature_controller
    ):
        """测试程序运行中状态。"""
        mock_temperature_controller.read_status = AsyncMock(
            return_value={
                "device_id": "test_temp_controller",
                "status": "ready",
                "current_temperature": 320.0,
                "current_output": 50.0,
                "setpoint": 350.0,
                "mode": "PROGRAM",
                "pid_running": True,
                "connected": True,
                "simulation": True,
                "program": {"running": True, "progress": 0.5, "current_segment": 1},
                "protection": {"triggered": False, "type": None},
            }
        )

        response = client_with_temperature.get("/api/v1/temperature/status")

        assert response.status_code == 200
        data = response.json()
        assert data["program_running"] is True
        assert data["program_segment"] == 1

    def test_get_status_with_protection_triggered(
        self, client_with_temperature, mock_temperature_controller
    ):
        """测试保护触发状态。"""
        mock_temperature_controller.read_status = AsyncMock(
            return_value={
                "device_id": "test_temp_controller",
                "status": "error",
                "current_temperature": 450.0,
                "current_output": 0.0,
                "setpoint": 350.0,
                "mode": "PID",
                "pid_running": False,
                "connected": True,
                "simulation": True,
                "program": {"running": False, "progress": 0.0, "current_segment": 0},
                "protection": {"triggered": True, "type": "high_temp"},
            }
        )

        response = client_with_temperature.get("/api/v1/temperature/status")

        assert response.status_code == 200
        data = response.json()
        assert data["protection_active"] is True
        assert data["protection_type"] == "high_temp"


# ==================== 连接管理测试 ====================


class TestTemperatureConnection:
    """测试温度控制器连接管理功能。"""

    def test_connect_success(self, client_with_temperature, mock_temperature_controller):
        """测试成功连接。"""
        mock_temperature_controller.connect = AsyncMock(return_value=True)

        response = client_with_temperature.post("/api/v1/temperature/connect")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_disconnect_success(self, client_with_temperature, mock_temperature_controller):
        """测试成功断开连接。"""
        mock_temperature_controller.disconnect = AsyncMock(return_value=True)

        response = client_with_temperature.post("/api/v1/temperature/disconnect")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


# ==================== 设备未初始化测试 ====================


class TestTemperatureNotInitialized:
    """测试设备未初始化场景。"""

    def test_status_not_initialized(self):
        """测试设备未初始化时获取状态。"""
        app = FastAPI()
        app.include_router(temperature.router)

        with TestClient(app) as client:
            response = client.get("/api/v1/temperature/status")
            assert response.status_code == 503
