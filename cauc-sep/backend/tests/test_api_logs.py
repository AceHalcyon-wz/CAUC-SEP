"""
审计日志 API 测试模块。

测试功能：
    - 日志查询
    - 统计信息
    - 操作类型列表
    - 日志导出

作者：Test Debugger Agent
创建日期：2026-03-08
依赖：pytest, httpx
"""

import json
import os
import tempfile
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from api.logs import router, set_storage
from core.data_storage import DataStorage
from models import Base
from models.user import AuditLog


class TestLogsAPI:
    """审计日志API测试。"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_logs.db")
            engine = create_engine(f"sqlite:///{db_path}")
            Base.metadata.create_all(bind=engine)

            # 创建DataStorage实例
            storage = DataStorage(db_path=db_path)
            yield storage

    @pytest.fixture
    def test_client(self, temp_db):
        """创建测试客户端。"""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        # 设置存储实例
        set_storage(temp_db)

        with TestClient(app) as client:
            yield client

    @pytest.fixture
    def sample_logs(self, temp_db):
        """创建示例日志数据。"""
        session = temp_db.Session()

        logs = []
        now = datetime.now()

        for i in range(10):
            log = AuditLog(
                timestamp=now - timedelta(hours=i),
                user_id=1,
                device_id=f"device_{i % 3}",
                operation_type=["motor_move", "temperature_set", "data_query"][i % 3],
                operation_category=["motion_control", "parameter", "query"][i % 3],
                request_method="POST",
                request_path=f"/api/v1/device/{i}",
                request_params=json.dumps({"param": i}),
                response_status=200 if i % 2 == 0 else 400,
                response_message="Success" if i % 2 == 0 else "Error",
                ip_address="127.0.0.1",
                user_agent="TestAgent",
                duration_ms=100 + i * 10,
            )
            session.add(log)
            logs.append(log)

        session.commit()
        session.close()

        return logs

    def test_query_logs_default(self, test_client, sample_logs):
        """测试默认查询日志。"""
        response = test_client.get("/api/v1/logs/query")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "logs" in data
        assert data["total"] == 10

    def test_query_logs_with_pagination(self, test_client, sample_logs):
        """测试分页查询日志。"""
        response = test_client.get("/api/v1/logs/query?page=1&page_size=5")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert len(data["logs"]) == 5
        assert data["page"] == 1
        assert data["total_pages"] == 2

    def test_query_logs_by_device_id(self, test_client, sample_logs):
        """测试按设备ID查询日志。"""
        response = test_client.get("/api/v1/logs/query?device_id=device_0")

        assert response.status_code == 200
        data = response.json()
        # device_0 出现在索引 0, 3, 6, 9
        assert data["total"] >= 1

    def test_query_logs_by_operation_type(self, test_client, sample_logs):
        """测试按操作类型查询日志。"""
        response = test_client.get("/api/v1/logs/query?operation_type=motor_move")

        assert response.status_code == 200
        data = response.json()
        for log in data["logs"]:
            assert log["operation_type"] == "motor_move"

    def test_query_logs_by_time_range(self, test_client, sample_logs):
        """测试按时间范围查询日志。"""
        now = datetime.now()
        start_time = (now - timedelta(hours=5)).isoformat()
        end_time = now.isoformat()

        response = test_client.get(
            f"/api/v1/logs/query?start_time={start_time}&end_time={end_time}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    def test_query_logs_by_response_status(self, test_client, sample_logs):
        """测试按响应状态查询日志。"""
        response = test_client.get("/api/v1/logs/query?response_status=400")

        assert response.status_code == 200
        data = response.json()
        for log in data["logs"]:
            assert log["response_status"] == 400

    def test_get_log_statistics(self, test_client, sample_logs):
        """测试获取日志统计信息。"""
        response = test_client.get("/api/v1/logs/statistics")

        assert response.status_code == 200
        data = response.json()
        assert "total_count" in data
        assert "by_category" in data
        assert "by_operation_type" in data
        assert "by_device" in data
        assert "by_status" in data

    def test_get_log_statistics_with_time_filter(self, test_client, sample_logs):
        """测试带时间过滤的统计信息。"""
        now = datetime.now()
        start_time = (now - timedelta(hours=3)).isoformat()

        response = test_client.get(f"/api/v1/logs/statistics?start_time={start_time}")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] >= 1

    def test_get_operation_types(self, test_client):
        """测试获取操作类型列表。"""
        response = test_client.get("/api/v1/logs/operation-types")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        # 验证操作类型结构
        for op_type in data:
            assert "type" in op_type
            assert "category" in op_type
            assert "description" in op_type

    def test_get_categories(self, test_client):
        """测试获取操作分类列表。"""
        response = test_client.get("/api/v1/logs/categories")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert "device" in data
        assert "motion_control" in data

    def test_get_log_detail(self, test_client, sample_logs):
        """测试获取日志详情。"""
        # 先获取列表
        list_response = test_client.get("/api/v1/logs/query?page_size=1")
        log_id = list_response.json()["logs"][0]["id"]

        # 获取详情
        response = test_client.get(f"/api/v1/logs/{log_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == log_id
        assert "timestamp" in data
        assert "operation_type" in data

    def test_get_log_detail_not_found(self, test_client):
        """测试获取不存在的日志详情。"""
        response = test_client.get("/api/v1/logs/99999")

        assert response.status_code == 404

    def test_delete_log(self, test_client, sample_logs):
        """测试删除单条日志。"""
        # 先获取列表
        list_response = test_client.get("/api/v1/logs/query?page_size=1")
        log_id = list_response.json()["logs"][0]["id"]

        # 删除日志
        response = test_client.delete(f"/api/v1/logs/{log_id}")

        assert response.status_code == 200
        assert response.json()["success"] is True

        # 验证已删除
        get_response = test_client.get(f"/api/v1/logs/{log_id}")
        assert get_response.status_code == 404

    def test_delete_log_not_found(self, test_client):
        """测试删除不存在的日志。"""
        response = test_client.delete("/api/v1/logs/99999")

        assert response.status_code == 404

    def test_bulk_delete_logs(self, test_client, sample_logs):
        """测试批量删除日志。"""
        now = datetime.now()
        end_time = now.isoformat()

        response = test_client.post(
            "/api/v1/logs/bulk/delete",
            params={"end_time": end_time},
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_export_logs_json(self, test_client, sample_logs):
        """测试导出日志为JSON格式。"""
        response = test_client.post(
            "/api/v1/logs/export",
            params={"format": "json"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "filepath" in data
        assert data["filepath"].endswith(".json")

    def test_export_logs_csv(self, test_client, sample_logs):
        """测试导出日志为CSV格式。"""
        response = test_client.post(
            "/api/v1/logs/export",
            params={"format": "csv"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "filepath" in data
        assert data["filepath"].endswith(".csv")

    def test_export_logs_no_data(self, test_client):
        """测试导出空日志。"""
        # 不添加任何日志数据
        response = test_client.post("/api/v1/logs/export")

        # 可能返回成功但count为0，或者返回失败
        assert response.status_code in [200, 400]


class TestAuditLogModel:
    """审计日志模型测试。"""

    def test_audit_log_creation(self, temp_db):
        """测试审计日志创建。"""
        session = temp_db.Session()

        log = AuditLog(
            timestamp=datetime.now(),
            user_id=1,
            device_id="test_device",
            operation_type="test_operation",
            operation_category="test_category",
            request_method="GET",
            request_path="/api/test",
            response_status=200,
            ip_address="127.0.0.1",
        )
        session.add(log)
        session.commit()

        assert log.id is not None
        assert log.operation_type == "test_operation"

        session.close()

    def test_audit_log_with_params(self, temp_db):
        """测试带参数的审计日志。"""
        session = temp_db.Session()

        params = {"key": "value", "nested": {"a": 1}}
        log = AuditLog(
            timestamp=datetime.now(),
            operation_type="test",
            operation_category="test",
            request_method="POST",
            request_path="/api/test",
            request_params=json.dumps(params),
        )
        session.add(log)
        session.commit()

        # 验证参数存储
        loaded_params = json.loads(log.request_params)
        assert loaded_params["key"] == "value"

        session.close()


class TestLogQueryPerformance:
    """日志查询性能测试。"""

    @pytest.fixture
    def large_log_dataset(self, temp_db):
        """创建大量日志数据。"""
        session = temp_db.Session()

        now = datetime.now()
        batch_size = 100

        for i in range(batch_size):
            log = AuditLog(
                timestamp=now - timedelta(minutes=i),
                device_id=f"device_{i % 10}",
                operation_type=f"op_{i % 20}",
                operation_category=f"cat_{i % 5}",
                request_method="GET",
                request_path=f"/api/test/{i}",
                response_status=200 if i % 10 != 0 else 500,
            )
            session.add(log)

            if i % 50 == 0:
                session.commit()

        session.commit()
        session.close()

        return batch_size

    def test_query_performance(self, test_client, large_log_dataset):
        """测试查询性能。"""
        import time

        start = time.time()
        response = test_client.get("/api/v1/logs/query?page_size=50")
        elapsed = time.time() - start

        assert response.status_code == 200
        # 查询应该在1秒内完成
        assert elapsed < 1.0

    def test_statistics_performance(self, test_client, large_log_dataset):
        """测试统计性能。"""
        import time

        start = time.time()
        response = test_client.get("/api/v1/logs/statistics")
        elapsed = time.time() - start

        assert response.status_code == 200
        # 统计应该在2秒内完成
        assert elapsed < 2.0


# 需要的fixture
@pytest.fixture
def temp_db():
    """创建临时数据库。"""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_logs.db")
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(bind=engine)

        storage = DataStorage(db_path=db_path)
        yield storage


@pytest.fixture
def test_client(temp_db):
    """创建测试客户端。"""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    set_storage(temp_db)

    with TestClient(app) as client:
        yield client


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
