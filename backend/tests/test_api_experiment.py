"""
测试实验管理 API 端点

测试内容：
- 实验创建
- 实验启动/停止
- 实验列表查询
- 实验详情获取
- 实验数据导出
"""

import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import experiment


@pytest.fixture
def app_with_experiment():
    """创建带实验路由的FastAPI应用。"""
    app = FastAPI()
    app.include_router(experiment.router)
    return app


@pytest.fixture
def client_with_experiment(app_with_experiment, temp_storage):
    """创建带存储的测试客户端。"""
    experiment.set_storage(temp_storage)

    with TestClient(app_with_experiment) as client:
        yield client, temp_storage


class TestExperimentStartEndpoint:
    """测试实验启动端点。"""

    def test_start_experiment_success(self, client_with_experiment):
        """测试成功启动实验。"""
        client, storage = client_with_experiment

        response = client.post(
            "/api/v1/experiment/start", json={"name": "测试实验", "description": "这是一个测试实验"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "experiment_id" in data
        assert data["experiment_id"] > 0

    def test_start_experiment_minimal(self, client_with_experiment):
        """测试最小参数启动实验。"""
        client, storage = client_with_experiment

        response = client.post("/api/v1/experiment/start", json={"name": "最小实验"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_start_experiment_empty_name(self, client_with_experiment):
        """测试空名称启动实验。"""
        client, storage = client_with_experiment

        response = client.post("/api/v1/experiment/start", json={"name": ""})

        assert response.status_code == 422

    def test_start_experiment_long_name(self, client_with_experiment):
        """测试过长名称启动实验。"""
        client, storage = client_with_experiment

        long_name = "A" * 101

        response = client.post("/api/v1/experiment/start", json={"name": long_name})

        assert response.status_code == 422


class TestExperimentStopEndpoint:
    """测试实验停止端点。"""

    def test_stop_experiment_success(self, client_with_experiment):
        """测试成功停止实验。"""
        client, storage = client_with_experiment

        start_response = client.post("/api/v1/experiment/start", json={"name": "测试实验"})
        exp_id = start_response.json()["experiment_id"]

        response = client.post(f"/api/v1/experiment/{exp_id}/stop")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["experiment_id"] == exp_id

    def test_stop_experiment_nonexistent(self, client_with_experiment):
        """测试停止不存在的实验。"""
        client, storage = client_with_experiment

        response = client.post("/api/v1/experiment/99999/stop")

        assert response.status_code == 200


class TestExperimentListEndpoint:
    """测试实验列表端点。"""

    def test_list_experiments_empty(self, client_with_experiment):
        """测试空实验列表。"""
        client, storage = client_with_experiment

        response = client.get("/api/v1/experiment/")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["experiments"] == []

    def test_list_experiments_with_data(self, client_with_experiment):
        """测试带数据的实验列表。"""
        client, storage = client_with_experiment

        for i in range(3):
            client.post("/api/v1/experiment/start", json={"name": f"实验{i+1}"})

        response = client.get("/api/v1/experiment/")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
        assert len(data["experiments"]) == 3

    def test_list_experiments_with_limit(self, client_with_experiment):
        """测试带限制的实验列表。"""
        client, storage = client_with_experiment

        for i in range(10):
            client.post("/api/v1/experiment/start", json={"name": f"实验{i+1}"})

        response = client.get("/api/v1/experiment/?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data["experiments"]) <= 5

    def test_list_experiments_structure(self, client_with_experiment):
        """测试实验列表结构。"""
        client, storage = client_with_experiment

        client.post("/api/v1/experiment/start", json={"name": "测试实验"})

        response = client.get("/api/v1/experiment/")

        assert response.status_code == 200
        data = response.json()

        for exp in data["experiments"]:
            assert "id" in exp
            assert "exp_name" in exp
            assert "status" in exp


class TestExperimentDetailEndpoint:
    """测试实验详情端点。"""

    def test_get_experiment_success(self, client_with_experiment):
        """测试成功获取实验详情。"""
        client, storage = client_with_experiment

        start_response = client.post(
            "/api/v1/experiment/start", json={"name": "测试实验", "description": "测试描述"}
        )
        exp_id = start_response.json()["experiment_id"]

        response = client.get(f"/api/v1/experiment/{exp_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == exp_id
        assert data["exp_name"] == "测试实验"

    def test_get_experiment_not_found(self, client_with_experiment):
        """测试获取不存在的实验。"""
        client, storage = client_with_experiment

        response = client.get("/api/v1/experiment/99999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_experiment_structure(self, client_with_experiment):
        """测试实验详情结构。"""
        client, storage = client_with_experiment

        start_response = client.post("/api/v1/experiment/start", json={"name": "测试实验"})
        exp_id = start_response.json()["experiment_id"]

        response = client.get(f"/api/v1/experiment/{exp_id}")

        assert response.status_code == 200
        data = response.json()

        assert "id" in data
        assert "exp_name" in data
        assert "status" in data
        assert "started_at" in data


class TestExperimentExportEndpoint:
    """测试实验导出端点。"""

    def test_export_experiment_success(self, client_with_experiment):
        """测试成功导出实验数据。"""
        client, storage = client_with_experiment

        start_response = client.post("/api/v1/experiment/start", json={"name": "导出测试"})
        exp_id = start_response.json()["experiment_id"]

        for i in range(10):
            storage.add_data_record(
                experiment_id=exp_id,
                position_steps=i * 100,
                position_mm=i * 0.0625,
                field_value=i * 10.0,
                current_value=i * 0.1,
            )

        response = client.get(f"/api/v1/experiment/{exp_id}/export")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "filepath" in data

        if os.path.exists(data["filepath"]):
            os.remove(data["filepath"])

    def test_export_experiment_no_data(self, client_with_experiment):
        """测试导出无数据的实验。"""
        client, storage = client_with_experiment

        start_response = client.post("/api/v1/experiment/start", json={"name": "空实验"})
        exp_id = start_response.json()["experiment_id"]

        response = client.get(f"/api/v1/experiment/{exp_id}/export")

        assert response.status_code == 500

    def test_export_experiment_not_found(self, client_with_experiment):
        """测试导出不存在的实验。"""
        client, storage = client_with_experiment

        response = client.get("/api/v1/experiment/99999/export")

        assert response.status_code == 500


class TestExperimentAPIValidation:
    """测试实验API输入验证。"""

    def test_start_experiment_missing_name(self, client_with_experiment):
        """测试缺少名称启动实验。"""
        client, storage = client_with_experiment

        response = client.post("/api/v1/experiment/start", json={})

        assert response.status_code == 422

    def test_list_experiments_invalid_limit(self, client_with_experiment):
        """测试无效限制参数。"""
        client, storage = client_with_experiment

        response = client.get("/api/v1/experiment/?limit=-1")

        assert response.status_code == 422


class TestExperimentWorkflow:
    """测试实验完整工作流。"""

    def test_full_experiment_workflow(self, client_with_experiment):
        """测试完整实验工作流。"""
        client, storage = client_with_experiment

        start_response = client.post(
            "/api/v1/experiment/start",
            json={"name": "完整工作流测试", "description": "测试完整实验流程"},
        )
        assert start_response.status_code == 200
        exp_id = start_response.json()["experiment_id"]

        for i in range(5):
            storage.add_data_record(
                experiment_id=exp_id,
                position_steps=i * 100,
                position_mm=i * 0.0625,
                field_value=i * 10.0,
            )

        detail_response = client.get(f"/api/v1/experiment/{exp_id}")
        assert detail_response.status_code == 200
        assert detail_response.json()["status"] == "running"

        stop_response = client.post(f"/api/v1/experiment/{exp_id}/stop")
        assert stop_response.status_code == 200

        list_response = client.get("/api/v1/experiment/")
        assert list_response.status_code == 200
        exp_ids = [e["id"] for e in list_response.json()["experiments"]]
        assert exp_id in exp_ids


class TestExperimentStorageIntegration:
    """测试实验存储集成。"""

    def test_storage_persistence(self, client_with_experiment):
        """测试存储持久化。"""
        client, storage = client_with_experiment

        response = client.post("/api/v1/experiment/start", json={"name": "持久化测试"})
        exp_id = response.json()["experiment_id"]

        experiment = storage.get_experiment(exp_id)
        assert experiment is not None
        assert experiment["exp_name"] == "持久化测试"

    def test_multiple_experiments(self, client_with_experiment):
        """测试多个实验。"""
        client, storage = client_with_experiment

        exp_ids = []
        for i in range(5):
            response = client.post("/api/v1/experiment/start", json={"name": f"实验{i+1}"})
            exp_ids.append(response.json()["experiment_id"])

        assert len(set(exp_ids)) == 5

        response = client.get("/api/v1/experiment/")
        assert response.json()["count"] == 5


class TestExperimentAPIErrorHandling:
    """测试实验API错误处理。"""

    def test_invalid_experiment_id_format(self, client_with_experiment):
        """测试无效实验ID格式。"""
        client, storage = client_with_experiment

        response = client.get("/api/v1/experiment/invalid")

        assert response.status_code == 422

    def test_storage_not_initialized(self):
        """测试存储未初始化。"""
        app = FastAPI()
        app.include_router(experiment.router)
        experiment.set_storage(None)

        with TestClient(app) as client:
            response = client.post("/api/v1/experiment/start", json={"name": "测试"})

            assert response.status_code == 503
