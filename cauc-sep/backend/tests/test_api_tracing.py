"""
链路追踪 API 测试模块。

测试功能：
    - 追踪列表查询
    - 追踪详情查询
    - 统计信息
    - 健康检查

作者：Test Debugger Agent
创建日期：2026-03-08
依赖：pytest, httpx
"""

import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.tracing import router
from core.tracing import (
    TraceStorage,
    TraceContext,
    Tracer,
    Span,
    get_trace_storage,
    set_trace_storage,
)


class TestTracingAPI:
    """链路追踪API测试。"""

    @pytest.fixture
    def temp_storage(self):
        """创建临时追踪存储。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_tracing.db")
            storage = TraceStorage(db_path=db_path)
            set_trace_storage(storage)
            yield storage

    @pytest.fixture
    def test_client(self, temp_storage):
        """创建测试客户端。"""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        with TestClient(app) as client:
            yield client

    @pytest.fixture
    def sample_traces(self, temp_storage):
        """创建示例追踪数据。"""
        traces = []
        now = datetime.now()

        for i in range(5):
            trace_id = f"{i:032x}"
            with Tracer(
                service_name="test-service",
                trace_id=trace_id,
                storage=temp_storage,
            ) as tracer:
                with tracer.span("operation_1") as span:
                    span.set_attribute("index", i)
                    span.set_attribute("status", "ok" if i % 2 == 0 else "error")

                if i % 2 == 1:
                    with tracer.span("operation_2") as span:
                        span.set_error("TestError", "Test error message")

            traces.append(trace_id)

        return traces

    def test_list_traces_default(self, test_client, sample_traces):
        """测试默认查询追踪列表。"""
        response = test_client.get("/api/v1/tracing/traces")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "traces" in data

    def test_list_traces_with_limit(self, test_client, sample_traces):
        """测试带限制的追踪列表查询。"""
        response = test_client.get("/api/v1/tracing/traces?limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["traces"]) <= 2

    def test_list_traces_by_service_name(self, test_client, sample_traces):
        """测试按服务名称查询追踪。"""
        response = test_client.get(
            "/api/v1/tracing/traces?service_name=test-service"
        )

        assert response.status_code == 200
        data = response.json()
        for trace in data["traces"]:
            assert trace.get("service_name") == "test-service"

    def test_list_traces_by_status(self, test_client, sample_traces):
        """测试按状态查询追踪。"""
        response = test_client.get("/api/v1/tracing/traces?status=error")

        assert response.status_code == 200
        data = response.json()
        for trace in data["traces"]:
            assert trace.get("status") == "error"

    def test_list_traces_by_time_range(self, test_client, sample_traces):
        """测试按时间范围查询追踪。"""
        now = datetime.now()
        start_time = (now - timedelta(hours=1)).isoformat()
        end_time = now.isoformat()

        response = test_client.get(
            f"/api/v1/tracing/traces?start_time={start_time}&end_time={end_time}"
        )

        assert response.status_code == 200

    def test_get_trace_detail(self, test_client, sample_traces):
        """测试获取追踪详情。"""
        trace_id = sample_traces[0]

        response = test_client.get(f"/api/v1/tracing/traces/{trace_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["trace_id"] == trace_id
        assert "spans" in data

    def test_get_trace_detail_invalid_id(self, test_client):
        """测试无效的追踪ID。"""
        response = test_client.get("/api/v1/tracing/traces/invalid")

        assert response.status_code == 400

    def test_get_trace_detail_not_found(self, test_client):
        """测试不存在的追踪。"""
        # 32位十六进制字符串
        fake_id = "a" * 32
        response = test_client.get(f"/api/v1/tracing/traces/{fake_id}")

        assert response.status_code == 404

    def test_get_trace_statistics(self, test_client, sample_traces):
        """测试获取追踪统计信息。"""
        response = test_client.get("/api/v1/tracing/statistics")

        assert response.status_code == 200
        data = response.json()
        assert "total_traces" in data
        assert "error_rate" in data

    def test_get_trace_statistics_with_hours(self, test_client, sample_traces):
        """测试带时间范围的统计信息。"""
        response = test_client.get("/api/v1/tracing/statistics?hours=24")

        assert response.status_code == 200
        data = response.json()
        assert "total_traces" in data

    def test_cleanup_old_traces(self, test_client, sample_traces):
        """测试清理过期追踪。"""
        response = test_client.delete(
            "/api/v1/tracing/traces/cleanup?max_age_days=0"
        )

        assert response.status_code == 200
        data = response.json()
        assert "deleted_count" in data
        assert data["success"] is True

    def test_tracing_health_check(self, test_client, sample_traces):
        """测试追踪系统健康检查。"""
        response = test_client.get("/api/v1/tracing/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "unhealthy"]

    def test_search_traces(self, test_client, sample_traces):
        """测试搜索追踪。"""
        response = test_client.get(
            "/api/v1/tracing/search?query=operation&limit=10"
        )

        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "traces" in data

    def test_get_span_detail_not_implemented(self, test_client):
        """测试获取Span详情（未实现）。"""
        span_id = "a" * 16
        response = test_client.get(f"/api/v1/tracing/spans/{span_id}")

        assert response.status_code == 501


class TestTraceStorage:
    """追踪存储测试。"""

    @pytest.fixture
    def storage(self):
        """创建追踪存储。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_storage.db")
            storage = TraceStorage(db_path=db_path)
            yield storage

    def test_storage_initialization(self, storage):
        """测试存储初始化。"""
        assert storage is not None

    def test_save_and_retrieve_trace(self, storage):
        """测试保存和检索追踪。"""
        trace_id = "a" * 32

        # 创建追踪上下文
        context = TraceContext(
            trace_id=trace_id,
            span_id="a" * 16,
            service_name="test-service",
        )

        # 保存追踪
        storage.save_trace(context, [])

        # 检索追踪
        traces = storage.query_traces(limit=10)
        assert len(traces) > 0

    def test_get_statistics(self, storage):
        """测试获取统计信息。"""
        stats = storage.get_statistics()

        assert "total_traces" in stats
        assert "error_rate" in stats

    def test_cleanup_old_traces(self, storage):
        """测试清理过期追踪。"""
        deleted = storage.cleanup_old_traces(max_age_days=0)

        assert isinstance(deleted, int)
        assert deleted >= 0


class TestTracer:
    """追踪器测试。"""

    @pytest.fixture
    def storage(self):
        """创建追踪存储。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_tracer.db")
            storage = TraceStorage(db_path=db_path)
            yield storage

    def test_tracer_creation(self, storage):
        """测试追踪器创建。"""
        tracer = Tracer(
            service_name="test-service",
            storage=storage,
        )

        assert tracer.service_name == "test-service"
        assert tracer.trace_id is not None

    def test_tracer_with_custom_trace_id(self, storage):
        """测试自定义追踪ID。"""
        custom_id = "a" * 32
        tracer = Tracer(
            service_name="test-service",
            trace_id=custom_id,
            storage=storage,
        )

        assert tracer.trace_id == custom_id

    def test_span_creation(self, storage):
        """测试Span创建。"""
        with Tracer(service_name="test-service", storage=storage) as tracer:
            with tracer.span("test_operation") as span:
                assert span.name == "test_operation"
                assert span.span_id is not None

    def test_span_attributes(self, storage):
        """测试Span属性设置。"""
        with Tracer(service_name="test-service", storage=storage) as tracer:
            with tracer.span("test_operation") as span:
                span.set_attribute("key1", "value1")
                span.set_attribute("key2", 123)

                assert span.attributes["key1"] == "value1"
                assert span.attributes["key2"] == 123

    def test_span_error(self, storage):
        """测试Span错误记录。"""
        with Tracer(service_name="test-service", storage=storage) as tracer:
            with tracer.span("test_operation") as span:
                span.set_error("TestError", "Test error message")

                assert span.status == "error"
                assert span.error_type == "TestError"
                assert span.error_message == "Test error message"

    def test_nested_spans(self, storage):
        """测试嵌套Span。"""
        with Tracer(service_name="test-service", storage=storage) as tracer:
            with tracer.span("parent") as parent:
                parent.set_attribute("level", 0)

                with tracer.span("child1") as child1:
                    child1.set_attribute("level", 1)

                    with tracer.span("grandchild") as grandchild:
                        grandchild.set_attribute("level", 2)

                with tracer.span("child2") as child2:
                    child2.set_attribute("level", 1)

    def test_span_events(self, storage):
        """测试Span事件。"""
        with Tracer(service_name="test-service", storage=storage) as tracer:
            with tracer.span("test_operation") as span:
                span.add_event("event1", {"detail": "test"})

                assert len(span.events) == 1
                assert span.events[0]["name"] == "event1"


class TestTraceContext:
    """追踪上下文测试。"""

    def test_context_creation(self):
        """测试上下文创建。"""
        context = TraceContext(
            trace_id="a" * 32,
            span_id="b" * 16,
            service_name="test-service",
        )

        assert context.trace_id == "a" * 32
        assert context.span_id == "b" * 16
        assert context.service_name == "test-service"

    def test_context_with_parent(self):
        """测试带父Span的上下文。"""
        context = TraceContext(
            trace_id="a" * 32,
            span_id="b" * 16,
            parent_span_id="c" * 16,
            service_name="test-service",
        )

        assert context.parent_span_id == "c" * 16

    def test_context_to_dict(self):
        """测试上下文转换为字典。"""
        context = TraceContext(
            trace_id="a" * 32,
            span_id="b" * 16,
            service_name="test-service",
        )

        data = context.to_dict()

        assert data["trace_id"] == "a" * 32
        assert data["span_id"] == "b" * 16
        assert data["service_name"] == "test-service"


class TestSpan:
    """Span测试。"""

    def test_span_creation(self):
        """测试Span创建。"""
        span = Span(
            name="test_span",
            trace_id="a" * 32,
            span_id="b" * 16,
        )

        assert span.name == "test_span"
        assert span.status == "ok"

    def test_span_duration(self):
        """测试Span持续时间。"""
        import time

        span = Span(
            name="test_span",
            trace_id="a" * 32,
            span_id="b" * 16,
        )

        span.start()
        time.sleep(0.01)
        span.end()

        assert span.duration_ms > 0

    def test_span_to_dict(self):
        """测试Span转换为字典。"""
        span = Span(
            name="test_span",
            trace_id="a" * 32,
            span_id="b" * 16,
        )
        span.set_attribute("key", "value")

        data = span.to_dict()

        assert data["name"] == "test_span"
        assert data["trace_id"] == "a" * 32
        assert data["attributes"]["key"] == "value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
