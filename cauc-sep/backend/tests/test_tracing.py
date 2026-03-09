"""
链路追踪系统测试模块。

测试功能：
    - 追踪上下文管理
    - 追踪装饰器
    - 追踪数据存储
    - API端点测试

作者：Backend Engineer Agent
创建日期：2026-03-07
"""

import asyncio
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from core.tracing import (
    Span,
    SpanKind,
    SpanStatus,
    TraceContext,
    TraceStorage,
    Tracer,
    generate_span_id,
    generate_trace_id,
    get_current_span,
    get_current_trace,
    init_tracing,
    set_current_span,
    set_current_trace,
    traced,
)


class TestTracingBasics:
    """追踪基础功能测试。"""

    def test_generate_trace_id(self):
        """测试Trace ID生成。"""
        trace_id = generate_trace_id()

        assert isinstance(trace_id, str)
        assert len(trace_id) == 32
        assert all(c in "0123456789abcdef" for c in trace_id)

    def test_generate_span_id(self):
        """测试Span ID生成。"""
        span_id = generate_span_id()

        assert isinstance(span_id, str)
        assert len(span_id) == 16
        assert all(c in "0123456789abcdef" for c in span_id)

    def test_span_duration(self):
        """测试Span持续时间计算。"""
        span = Span(
            span_id="test123",
            trace_id="test_trace",
            name="test_span",
        )

        # 未结束时持续时间为None
        assert span.duration_ms is None

        # 结束后计算持续时间
        span.end()
        assert span.duration_ms is not None
        assert span.duration_ms >= 0

    def test_span_attributes(self):
        """测试Span属性设置。"""
        span = Span(
            span_id="test123",
            trace_id="test_trace",
            name="test_span",
        )

        span.set_attribute("key1", "value1")
        span.set_attribute("key2", 123)

        assert span.attributes["key1"] == "value1"
        assert span.attributes["key2"] == 123

    def test_span_events(self):
        """测试Span事件添加。"""
        span = Span(
            span_id="test123",
            trace_id="test_trace",
            name="test_span",
        )

        span.add_event("test_event", {"detail": "test"})

        assert len(span.events) == 1
        assert span.events[0].name == "test_event"
        assert span.events[0].attributes["detail"] == "test"

    def test_span_status(self):
        """测试Span状态设置。"""
        span = Span(
            span_id="test123",
            trace_id="test_trace",
            name="test_span",
        )

        span.set_status(SpanStatus.OK)
        assert span.status == SpanStatus.OK

        span.set_status(SpanStatus.ERROR, "Test error")
        assert span.status == SpanStatus.ERROR
        assert span.attributes["status_description"] == "Test error"


class TestTraceContext:
    """追踪上下文测试。"""

    def test_create_span(self):
        """测试创建Span。"""
        trace = TraceContext(trace_id=generate_trace_id())

        span = trace.create_span(name="test_span", kind=SpanKind.INTERNAL)

        assert span.name == "test_span"
        assert span.trace_id == trace.trace_id
        assert span in trace.spans

    def test_baggage(self):
        """测试Baggage功能。"""
        trace = TraceContext(trace_id=generate_trace_id())

        trace.set_baggage("key1", "value1")

        assert trace.get_baggage("key1") == "value1"
        assert trace.get_baggage("nonexistent") is None

    def test_to_dict(self):
        """测试转换为字典。"""
        trace = TraceContext(trace_id=generate_trace_id())
        trace.create_span(name="span1")

        trace_dict = trace.to_dict()

        assert trace_dict["trace_id"] == trace.trace_id
        assert len(trace_dict["spans"]) == 1


class TestTracer:
    """追踪器测试。"""

    def test_start_trace(self):
        """测试开始追踪。"""
        tracer = Tracer(service_name="test_service")

        trace = tracer.start_trace(name="test_operation")

        assert trace is not None
        assert trace.root_span is not None
        assert trace.root_span.name == "test_operation"
        assert get_current_trace() == trace

    def test_end_trace(self):
        """测试结束追踪。"""
        tracer = Tracer(service_name="test_service")

        trace = tracer.start_trace(name="test_operation")
        tracer.end_trace(trace)

        assert get_current_trace() is None

    def test_start_span(self):
        """测试创建Span。"""
        tracer = Tracer(service_name="test_service")

        trace = tracer.start_trace(name="root")
        span = tracer.start_span(name="child_span")

        assert span.name == "child_span"
        assert span.parent_span_id == trace.root_span.span_id


class TestTracedDecorator:
    """追踪装饰器测试。"""

    def test_sync_function(self):
        """测试同步函数追踪。"""

        @traced(name="test_function")
        def test_func(x, y):
            return x + y

        result = test_func(1, 2)

        assert result == 3

    @pytest.mark.asyncio
    async def test_async_function(self):
        """测试异步函数追踪。"""

        @traced(name="async_test_function")
        async def async_func(x, y):
            await asyncio.sleep(0.01)
            return x + y

        result = await async_func(1, 2)

        assert result == 3

    def test_exception_handling(self):
        """测试异常处理。"""

        @traced(name="error_function")
        def error_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            error_func()


class TestTraceStorage:
    """追踪数据存储测试。"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库。"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        storage = None
        yield db_path

        # 清理
        import gc
        import time

        gc.collect()
        time.sleep(0.05)
        try:
            Path(db_path).unlink(missing_ok=True)
        except PermissionError:
            pass  # Windows文件锁问题，忽略

    def test_save_and_query_trace(self, temp_db):
        """测试保存和查询追踪。"""
        storage = TraceStorage(db_path=temp_db)

        # 创建追踪
        trace = TraceContext(trace_id=generate_trace_id())
        root_span = trace.create_span(name="root", kind=SpanKind.SERVER)
        trace.root_span = root_span
        root_span.set_attribute("service.name", "test_service")
        root_span.end()

        # 保存追踪
        storage.save_trace(trace)

        # 查询追踪
        traces = storage.query_traces(service_name="test_service")

        assert len(traces) == 1
        assert traces[0]["trace_id"] == trace.trace_id

    def test_get_trace_detail(self, temp_db):
        """测试获取追踪详情。"""
        storage = TraceStorage(db_path=temp_db)

        # 创建追踪
        trace = TraceContext(trace_id=generate_trace_id())
        root_span = trace.create_span(name="root", kind=SpanKind.SERVER)
        trace.root_span = root_span
        root_span.set_attribute("service.name", "test_service")

        child_span = trace.create_span(
            name="child",
            kind=SpanKind.INTERNAL,
            parent_span_id=root_span.span_id,
        )

        root_span.end()
        child_span.end()

        # 保存追踪
        storage.save_trace(trace)

        # 获取详情
        detail = storage.get_trace_detail(trace.trace_id)

        assert detail is not None
        assert detail["trace_id"] == trace.trace_id
        assert len(detail["spans"]) == 2

    def test_get_statistics(self, temp_db):
        """测试获取统计信息。"""
        storage = TraceStorage(db_path=temp_db)

        # 创建多个追踪
        for i in range(3):
            trace = TraceContext(trace_id=generate_trace_id())
            root_span = trace.create_span(name=f"root_{i}", kind=SpanKind.SERVER)
            trace.root_span = root_span
            root_span.set_attribute("service.name", "test_service")
            root_span.end()
            storage.save_trace(trace)

        # 获取统计
        stats = storage.get_statistics()

        assert stats["total_traces"] == 3
        assert stats["avg_duration_ms"] >= 0

    def test_cleanup_old_traces(self, temp_db):
        """测试清理过期追踪。"""
        storage = TraceStorage(db_path=temp_db)

        # 创建追踪
        trace = TraceContext(trace_id=generate_trace_id())
        root_span = trace.create_span(name="root", kind=SpanKind.SERVER)
        trace.root_span = root_span
        root_span.set_attribute("service.name", "test_service")
        root_span.end()

        storage.save_trace(trace)

        # 清理（保留1天，刚创建的不应该被删除）
        deleted_count = storage.cleanup_old_traces(max_age_days=1)

        # 由于刚创建，不应该被删除
        assert deleted_count == 0


class TestIntegration:
    """集成测试。"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库。"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        yield db_path

        # 清理
        import gc
        import time

        gc.collect()
        time.sleep(0.05)
        try:
            Path(db_path).unlink(missing_ok=True)
        except PermissionError:
            pass  # Windows文件锁问题，忽略

    def test_full_workflow(self, temp_db):
        """测试完整工作流程。"""
        # 初始化追踪系统
        tracer = init_tracing(db_path=temp_db)

        # 开始追踪
        trace = tracer.start_trace(
            name="test_workflow",
            kind=SpanKind.SERVER,
            attributes={"user_id": "test_user"},
        )

        # 创建子Span
        span1 = tracer.start_span(name="operation1")
        span1.set_attribute("step", 1)
        span1.end()

        span2 = tracer.start_span(name="operation2")
        span2.set_attribute("step", 2)
        span2.add_event("important_event", {"detail": "test"})
        span2.end()

        # 结束追踪
        tracer.end_trace(trace)

        # 验证存储
        storage = get_current_trace().__class__.__bases__[0]  # 获取TraceStorage
        from core.tracing import get_trace_storage

        storage = get_trace_storage()

        traces = storage.query_traces(service_name="cauc-sep")
        assert len(traces) == 1

        detail = storage.get_trace_detail(trace.trace_id)
        assert detail is not None
        assert len(detail["spans"]) == 3  # root + 2 children


class TestTracingMiddleware:
    """追踪中间件测试。"""

    @pytest.fixture
    def mock_app(self):
        """创建Mock应用。"""

        async def app(scope, receive, send):
            if scope["type"] == "http":
                await send({"type": "http.response.start", "status": 200})
                await send({"type": "http.response.body", "body": b"OK"})

        return app

    @pytest.mark.asyncio
    async def test_middleware_http_request(self, mock_app):
        """测试HTTP请求追踪。"""
        from core.tracing import TracingMiddleware

        tracer = Tracer(service_name="test_service")
        middleware = TracingMiddleware(mock_app, tracer=tracer)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/test",
            "headers": [],
            "server": ("localhost", 8000),
        }

        receive_called = []
        send_called = []

        async def receive():
            receive_called.append(True)
            return {"type": "http.request"}

        async def send(message):
            send_called.append(message)

        await middleware(scope, receive, send)

        assert len(send_called) >= 1

    @pytest.mark.asyncio
    async def test_middleware_excluded_path(self, mock_app):
        """测试排除路径。"""
        from core.tracing import TracingMiddleware

        tracer = Tracer(service_name="test_service")
        middleware = TracingMiddleware(mock_app, tracer=tracer)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/docs",
            "headers": [],
        }

        send_called = []

        async def receive():
            return {"type": "http.request"}

        async def send(message):
            send_called.append(message)

        await middleware(scope, receive, send)

        # 排除路径不应该创建追踪
        assert get_current_trace() is None

    @pytest.mark.asyncio
    async def test_middleware_websocket_exclusion(self, mock_app):
        """测试WebSocket路径排除。"""
        from core.tracing import TracingMiddleware

        tracer = Tracer(service_name="test_service")
        middleware = TracingMiddleware(mock_app, tracer=tracer)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/ws/test",
            "headers": [],
        }

        send_called = []

        async def receive():
            return {"type": "http.request"}

        async def send(message):
            send_called.append(message)

        await middleware(scope, receive, send)

        assert get_current_trace() is None

    @pytest.mark.asyncio
    async def test_middleware_traceparent_header(self, mock_app):
        """测试W3C Trace Context头解析。"""
        from core.tracing import TracingMiddleware

        tracer = Tracer(service_name="test_service")
        middleware = TracingMiddleware(mock_app, tracer=tracer)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/test",
            "headers": [
                (b"traceparent", b"00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"),
            ],
            "server": ("localhost", 8000),
        }

        send_called = []

        async def receive():
            return {"type": "http.request"}

        async def send(message):
            send_called.append(message)

        await middleware(scope, receive, send)

    @pytest.mark.asyncio
    async def test_middleware_exception_handling(self, mock_app):
        """测试异常处理。"""
        from core.tracing import TracingMiddleware

        async def failing_app(scope, receive, send):
            raise ValueError("Test error")

        tracer = Tracer(service_name="test_service")
        middleware = TracingMiddleware(failing_app, tracer=tracer)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/test",
            "headers": [],
            "server": ("localhost", 8000),
        }

        async def receive():
            return {"type": "http.request"}

        async def send(message):
            pass

        with pytest.raises(ValueError):
            await middleware(scope, receive, send)


class TestSpanKind:
    """Span类型枚举测试。"""

    def test_span_kind_values(self):
        """测试Span类型枚举值。"""
        assert SpanKind.SERVER.value == "server"
        assert SpanKind.CLIENT.value == "client"
        assert SpanKind.PRODUCER.value == "producer"
        assert SpanKind.CONSUMER.value == "consumer"
        assert SpanKind.INTERNAL.value == "internal"


class TestSpanStatus:
    """Span状态枚举测试。"""

    def test_span_status_values(self):
        """测试Span状态枚举值。"""
        assert SpanStatus.UNSET.value == "unset"
        assert SpanStatus.OK.value == "ok"
        assert SpanStatus.ERROR.value == "error"


class TestSpanEvent:
    """Span事件测试。"""

    def test_span_event_creation(self):
        """测试Span事件创建。"""
        from core.tracing import SpanEvent

        event = SpanEvent(
            name="test_event",
            timestamp=datetime.now(),
            attributes={"key": "value"},
        )

        assert event.name == "test_event"
        assert isinstance(event.timestamp, datetime)
        assert event.attributes["key"] == "value"


class TestSpanToDict:
    """Span字典转换测试。"""

    def test_span_to_dict_complete(self):
        """测试完整Span转换为字典。"""
        span = Span(
            span_id="test_span_id",
            trace_id="test_trace_id",
            parent_span_id="parent_id",
            name="test_operation",
            kind=SpanKind.SERVER,
            status=SpanStatus.OK,
        )
        span.set_attribute("custom_key", "custom_value")
        span.add_event("test_event", {"detail": "test"})
        span.end()

        result = span.to_dict()

        assert result["span_id"] == "test_span_id"
        assert result["trace_id"] == "test_trace_id"
        assert result["parent_span_id"] == "parent_id"
        assert result["name"] == "test_operation"
        assert result["kind"] == "server"
        assert result["status"] == "ok"
        assert result["duration_ms"] is not None
        assert "custom_key" in result["attributes"]
        assert len(result["events"]) == 1


class TestTraceContextToDict:
    """Trace上下文字典转换测试。"""

    def test_trace_context_to_dict_complete(self):
        """测试完整Trace上下文转换为字典。"""
        trace = TraceContext(trace_id=generate_trace_id())
        trace.set_baggage("user_id", "12345")

        root_span = trace.create_span(name="root", kind=SpanKind.SERVER)
        trace.root_span = root_span

        child_span = trace.create_span(
            name="child",
            kind=SpanKind.INTERNAL,
            parent_span_id=root_span.span_id,
        )

        root_span.end()
        child_span.end()

        result = trace.to_dict()

        assert result["trace_id"] == trace.trace_id
        assert result["root_span"] is not None
        assert len(result["spans"]) == 2
        assert result["baggage"]["user_id"] == "12345"


class TestTracerAdvanced:
    """追踪器高级测试。"""

    def test_tracer_with_storage(self):
        """测试带存储的追踪器。"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            tracer = Tracer(service_name="test_service")
            storage = TraceStorage(db_path=db_path)
            tracer.set_storage(storage)

            trace = tracer.start_trace(name="test_operation")
            tracer.end_trace(trace)

            # 关闭数据库连接
            storage.engine.dispose()

        finally:
            # 等待文件释放
            import time
            import gc

            gc.collect()
            time.sleep(0.1)
            try:
                Path(db_path).unlink(missing_ok=True)
            except PermissionError:
                pass  # Windows文件锁问题，忽略

    def test_tracer_nested_spans(self):
        """测试嵌套Span。"""
        tracer = Tracer(service_name="test_service")

        trace = tracer.start_trace(name="root_operation")

        span1 = tracer.start_span(name="level1")
        span2 = tracer.start_span(name="level2")

        assert span2.parent_span_id == span1.span_id
        assert span1.parent_span_id == trace.root_span.span_id

        tracer.end_span(span2)
        tracer.end_span(span1)
        tracer.end_trace(trace)

    def test_tracer_end_span_without_parent(self):
        """测试结束没有父Span的Span。"""
        tracer = Tracer(service_name="test_service")

        trace = tracer.start_trace(name="root")
        root_span = trace.root_span

        # 结束根Span
        tracer.end_span(root_span)

        # 当前Span应该恢复为根Span
        current = get_current_span()
        assert current == root_span

        tracer.end_trace(trace)


class TestTracedDecoratorAdvanced:
    """追踪装饰器高级测试。"""

    def test_decorator_with_attributes(self):
        """测试带属性的装饰器。"""

        @traced(
            name="custom_name",
            kind=SpanKind.CLIENT,
            attributes={"service": "test"},
        )
        def test_func():
            return "result"

        result = test_func()

        assert result == "result"

    @pytest.mark.asyncio
    async def test_decorator_async_exception(self):
        """测试异步函数异常追踪。"""

        @traced(name="async_error")
        async def async_error_func():
            raise RuntimeError("Async error")

        with pytest.raises(RuntimeError):
            await async_error_func()

    def test_decorator_creates_new_trace(self):
        """测试装饰器创建新追踪。"""
        # 确保没有活跃的追踪上下文
        set_current_trace(None)
        set_current_span(None)

        @traced(name="standalone_func")
        def standalone_func():
            return "standalone"

        result = standalone_func()

        assert result == "standalone"
        # 追踪应该已结束
        assert get_current_trace() is None


class TestTraceStorageAdvanced:
    """追踪存储高级测试。"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库。"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        yield db_path

        # 清理
        import gc
        import time

        gc.collect()
        time.sleep(0.05)
        try:
            Path(db_path).unlink(missing_ok=True)
        except PermissionError:
            pass  # Windows文件锁问题，忽略

    def test_query_with_time_filter(self, temp_db):
        """测试时间范围查询。"""
        storage = TraceStorage(db_path=temp_db)

        # 创建追踪
        trace = TraceContext(trace_id=generate_trace_id())
        root_span = trace.create_span(name="root", kind=SpanKind.SERVER)
        trace.root_span = root_span
        root_span.set_attribute("service.name", "test_service")
        root_span.end()

        storage.save_trace(trace)

        # 查询时间范围
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now() + timedelta(hours=1)

        traces = storage.query_traces(
            service_name="test_service",
            start_time=start_time,
            end_time=end_time,
        )

        assert len(traces) == 1

    def test_query_with_status_filter(self, temp_db):
        """测试状态过滤查询。"""
        storage = TraceStorage(db_path=temp_db)

        # 创建成功追踪
        trace1 = TraceContext(trace_id=generate_trace_id())
        root_span1 = trace1.create_span(name="success", kind=SpanKind.SERVER)
        trace1.root_span = root_span1
        root_span1.set_attribute("service.name", "test_service")
        root_span1.set_status(SpanStatus.OK)
        root_span1.end()
        storage.save_trace(trace1)

        # 创建错误追踪
        trace2 = TraceContext(trace_id=generate_trace_id())
        root_span2 = trace2.create_span(name="error", kind=SpanKind.SERVER)
        trace2.root_span = root_span2
        root_span2.set_attribute("service.name", "test_service")
        root_span2.set_status(SpanStatus.ERROR)
        root_span2.end()
        storage.save_trace(trace2)

        # 查询错误追踪
        error_traces = storage.query_traces(status="error")
        assert len(error_traces) == 1

        # 查询成功追踪
        ok_traces = storage.query_traces(status="ok")
        assert len(ok_traces) == 1

    def test_get_nonexistent_trace(self, temp_db):
        """测试获取不存在的追踪。"""
        storage = TraceStorage(db_path=temp_db)

        detail = storage.get_trace_detail("nonexistent_id")
        assert detail is None

    def test_statistics_empty_storage(self, temp_db):
        """测试空存储统计。"""
        storage = TraceStorage(db_path=temp_db)

        stats = storage.get_statistics()

        assert stats["total_traces"] == 0
        assert stats["avg_duration_ms"] == 0
        assert stats["error_count"] == 0
        assert stats["error_rate"] == 0.0


class TestAPIResponseModels:
    """API响应模型测试。"""

    def test_trace_list_response(self):
        """测试追踪列表响应模型。"""
        from core.tracing import TraceListResponse

        response = TraceListResponse(
            total=10,
            traces=[{"trace_id": "test"}],
        )

        assert response.total == 10
        assert len(response.traces) == 1

    def test_trace_detail_response(self):
        """测试追踪详情响应模型。"""
        from core.tracing import TraceDetailResponse

        response = TraceDetailResponse(
            trace_id="test_id",
            service_name="test_service",
            start_time=datetime.now().isoformat(),
            status="ok",
            span_count=5,
        )

        assert response.trace_id == "test_id"
        assert response.service_name == "test_service"
        assert response.span_count == 5

    def test_trace_statistics_response(self):
        """测试追踪统计响应模型。"""
        from core.tracing import TraceStatisticsResponse

        response = TraceStatisticsResponse(
            total_traces=100,
            avg_duration_ms=50.5,
            max_duration_ms=500,
            min_duration_ms=1,
            error_count=5,
            error_rate=0.05,
        )

        assert response.total_traces == 100
        assert response.avg_duration_ms == 50.5
        assert response.error_rate == 0.05


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
