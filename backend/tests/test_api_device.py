"""
测试设备管理 API 端点

测试内容：
- 设备列表
- 设备状态查询
- 设备连接管理
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import device


@pytest.fixture
def app_with_device():
    """创建带设备路由的FastAPI应用。"""
    app = FastAPI()
    app.include_router(device.router)
    return app


@pytest.fixture
def client_with_device(app_with_device):
    """创建测试客户端。"""
    with TestClient(app_with_device) as client:
        yield client


class TestDeviceListEndpoint:
    """测试设备列表端点。"""

    def test_list_devices_success(self, client_with_device):
        """测试成功获取设备列表。"""
        response = client_with_device.get("/api/v1/device/list")

        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "devices" in data
        assert isinstance(data["devices"], list)

    def test_list_devices_contains_expected_device(self, client_with_device):
        """测试设备列表包含预期设备。"""
        response = client_with_device.get("/api/v1/device/list")

        assert response.status_code == 200
        data = response.json()

        assert data["count"] >= 1

        device_ids = [d["device_id"] for d in data["devices"]]
        assert "stepper_01" in device_ids

    def test_list_devices_structure(self, client_with_device):
        """测试设备列表结构。"""
        response = client_with_device.get("/api/v1/device/list")

        assert response.status_code == 200
        data = response.json()

        for dev in data["devices"]:
            assert "device_id" in dev
            assert "device_type" in dev
            assert "device_name" in dev
            assert "status" in dev


class TestDeviceStatusEndpoint:
    """测试设备状态端点。"""

    def test_get_device_status_success(self, client_with_device):
        """测试成功获取设备状态。"""
        response = client_with_device.get("/api/v1/device/stepper_01/status")

        assert response.status_code == 200
        data = response.json()
        assert data["device_id"] == "stepper_01"
        assert "status" in data
        assert "message" in data

    def test_get_device_status_any_device_id(self, client_with_device):
        """测试获取任意设备ID的状态。"""
        response = client_with_device.get("/api/v1/device/any_device/status")

        assert response.status_code == 200
        data = response.json()
        assert data["device_id"] == "any_device"

    def test_get_device_status_response_structure(self, client_with_device):
        """测试设备状态响应结构。"""
        response = client_with_device.get("/api/v1/device/test_device/status")

        assert response.status_code == 200
        data = response.json()

        assert "device_id" in data
        assert "status" in data
        assert "message" in data


class TestDeviceStorageIntegration:
    """测试设备存储集成。"""

    def test_set_and_get_storage(self, temp_storage):
        """测试设置和获取存储实例。"""
        app = FastAPI()
        app.include_router(device.router)

        device.set_storage(temp_storage)

        assert device.storage == temp_storage

    def test_storage_not_initialized_error(self):
        """测试存储未初始化错误。"""
        app = FastAPI()
        app.include_router(device.router)
        device.set_storage(None)

        with TestClient(app) as client:
            with pytest.raises(Exception):
                client.get("/api/v1/device/list")


class TestDeviceEndpointsWithStorage:
    """测试带存储的设备端点。"""

    @pytest.fixture
    def client_with_storage(self, temp_storage):
        """创建带存储的测试客户端。"""
        app = FastAPI()
        app.include_router(device.router)
        device.set_storage(temp_storage)

        with TestClient(app) as client:
            yield client, temp_storage

    def test_device_endpoint_with_real_storage(self, client_with_storage):
        """测试带真实存储的设备端点。"""
        client, storage = client_with_storage

        storage.create_device(
            device_id="test_device_01",
            device_type="stepper_motor",
            device_name="测试电机",
            status="ready",
        )

        response = client.get("/api/v1/device/list")

        assert response.status_code == 200


class TestDeviceAPIErrorHandling:
    """测试设备API错误处理。"""

    def test_invalid_endpoint(self, client_with_device):
        """测试无效端点。"""
        response = client_with_device.get("/api/v1/device/invalid/endpoint")

        assert response.status_code == 404

    def test_method_not_allowed(self, client_with_device):
        """测试不允许的HTTP方法。"""
        response = client_with_device.post("/api/v1/device/list")

        assert response.status_code == 405


class TestDeviceAPIResponseFormat:
    """测试设备API响应格式。"""

    def test_list_devices_json_format(self, client_with_device):
        """测试设备列表JSON格式。"""
        response = client_with_device.get("/api/v1/device/list")

        assert response.headers["content-type"] == "application/json"

    def test_device_status_json_format(self, client_with_device):
        """测试设备状态JSON格式。"""
        response = client_with_device.get("/api/v1/device/test/status")

        assert response.headers["content-type"] == "application/json"


class TestDeviceAPIDocumentation:
    """测试设备API文档。"""

    def test_openapi_schema_exists(self, app_with_device):
        """测试OpenAPI模式存在。"""
        with TestClient(app_with_device) as client:
            response = client.get("/openapi.json")

            assert response.status_code == 200
            schema = response.json()
            assert "openapi" in schema
            assert "paths" in schema

    def test_device_endpoints_in_schema(self, app_with_device):
        """测试设备端点在OpenAPI模式中。"""
        with TestClient(app_with_device) as client:
            response = client.get("/openapi.json")
            schema = response.json()

            assert "/api/v1/device/list" in schema["paths"]
            assert "/api/v1/device/{device_id}/status" in schema["paths"]
