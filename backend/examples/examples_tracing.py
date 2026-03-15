"""
链路追踪系统使用示例。

展示如何在项目中使用追踪功能：
    1. 基础追踪使用
    2. 装饰器追踪
    3. API集成
    4. 数据查询和分析

作者：Backend Engineer Agent
创建日期：2026-03-07
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tracing import SpanKind, SpanStatus, get_current_span, init_tracing, traced


def example_basic_tracing():
    """基础追踪使用示例。"""
    print("=" * 60)
    print("示例1: 基础追踪使用")
    print("=" * 60)

    tracer = init_tracing(db_path="example_traces.db")

    trace = tracer.start_trace(
        name="example_operation",
        kind=SpanKind.SERVER,
        attributes={
            "user_id": "user123",
            "operation_type": "data_processing",
        },
    )

    print(f"✓ 开始追踪: {trace.trace_id}")

    span1 = tracer.start_span(name="step1_validation")
    span1.set_attribute("validation_type", "input_check")

    import time

    time.sleep(0.1)

    span1.set_status(SpanStatus.OK)
    span1.end()
    print("✓ 完成步骤1: 数据验证")

    span2 = tracer.start_span(name="step2_processing")
    span2.set_attribute("data_size", 1000)

    span2.add_event("data_loaded", {"records": 1000})

    time.sleep(0.15)

    span2.add_event("processing_complete", {"success_rate": 0.98})
    span2.set_status(SpanStatus.OK)
    span2.end()
    print("✓ 完成步骤2: 数据处理")

    tracer.end_trace(trace)
    print(f"✓ 追踪完成，持续时间: {trace.root_span.duration_ms}ms")
    print()


@traced(name="decorated_function", kind=SpanKind.INTERNAL)
def example_decorated_function(data: list) -> int:
    """装饰器追踪示例。"""
    span = get_current_span()
    if span:
        span.set_attribute("data_length", len(data))

    result = sum(data)

    if span:
        span.set_attribute("result", result)

    return result


@traced(name="async_decorated_function", kind=SpanKind.INTERNAL)
async def example_async_decorated_function(url: str) -> dict:
    """异步函数装饰器追踪示例。"""
    span = get_current_span()
    if span:
        span.set_attribute("url", url)

    await asyncio.sleep(0.1)

    result = {"status": "success", "url": url}

    if span:
        span.set_attribute("response_status", 200)

    return result


def example_decorator_tracing():
    """装饰器追踪使用示例。"""
    print("=" * 60)
    print("示例2: 装饰器追踪")
    print("=" * 60)

    tracer = init_tracing(db_path="example_traces.db")

    result1 = example_decorated_function([1, 2, 3, 4, 5])
    print(f"✓ 同步函数结果: {result1}")

    result2 = asyncio.run(example_async_decorated_function("https://api.example.com/data"))
    print(f"✓ 异步函数结果: {result2}")

    print()


def example_error_tracing():
    """错误追踪示例。"""
    print("=" * 60)
    print("示例3: 错误追踪")
    print("=" * 60)

    tracer = init_tracing(db_path="example_traces.db")

    @traced(name="error_function")
    def function_with_error():
        """会抛出异常的函数。"""
        span = get_current_span()
        if span:
            span.set_attribute("attempt", 1)

        raise ValueError("示例错误：数据格式不正确")

    try:
        function_with_error()
    except ValueError as e:
        print(f"✓ 捕获异常: {e}")
        print("✓ 异常已自动记录到追踪数据")

    print()


def example_trace_query():
    """追踪数据查询示例。"""
    print("=" * 60)
    print("示例4: 追踪数据查询")
    print("=" * 60)

    from tracing import get_trace_storage

    storage = get_trace_storage()
    if not storage:
        print("✗ 追踪存储未初始化")
        return

    traces = storage.query_traces(limit=5)
    print(f"✓ 最近 {len(traces)} 条追踪记录:")
    for trace in traces:
        print(f"  - Trace ID: {trace['trace_id'][:16]}...")
        print(f"    名称: {trace['root_span_name']}")
        print(f"    持续时间: {trace['duration_ms']}ms")
        print(f"    状态: {trace['status']}")
        print()

    stats = storage.get_statistics()
    print("✓ 追踪统计信息:")
    print(f"  - 总追踪数: {stats['total_traces']}")
    print(f"  - 平均持续时间: {stats['avg_duration_ms']:.2f}ms")
    print(f"  - 最大持续时间: {stats['max_duration_ms']}ms")
    print(f"  - 错误率: {stats['error_rate']:.2%}")
    print()


def example_api_integration():
    """API集成示例。"""
    print("=" * 60)
    print("示例5: FastAPI集成")
    print("=" * 60)

    print("FastAPI集成步骤:")
    print("1. 在main.py中初始化追踪系统:")
    print("   from core.tracing import init_tracing, TracingMiddleware, tracer")
    print("   init_tracing(db_path='traces.db')")
    print()
    print("2. 添加追踪中间件:")
    print("   app.add_middleware(TracingMiddleware, tracer=tracer)")
    print()
    print("3. 在API端点使用装饰器:")
    print("   @router.post('/api/data')")
    print("   @traced(name='api.process_data')")
    print("   async def process_data(request: DataRequest):")
    print("       span = get_current_span()")
    print("       span.set_attribute('request_id', request.id)")
    print("       # 处理逻辑...")
    print()
    print("4. 访问追踪API:")
    print("   GET  /api/v1/tracing/traces         # 查询追踪列表")
    print("   GET  /api/v1/tracing/traces/{id}    # 查询追踪详情")
    print("   GET  /api/v1/tracing/statistics     # 查询统计信息")
    print("   GET  /api/v1/tracing/health         # 健康检查")
    print("   GET  /api/v1/tracing/search?query=  # 搜索追踪")
    print()


def example_distributed_tracing():
    """分布式追踪示例。"""
    print("=" * 60)
    print("示例6: 分布式追踪")
    print("=" * 60)

    print("分布式追踪支持:")
    print("1. W3C Trace Context格式:")
    print("   - 请求头: traceparent")
    print("   - 格式: version-traceid-parentid-flags")
    print("   - 示例: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01")
    print()
    print("2. 跨服务传递:")
    print("   # 服务A")
    print("   trace = tracer.start_trace('service_a')")
    print("   headers = {'traceparent': f'00-{trace.trace_id}-{span.span_id}-01'}")
    print("   requests.post('http://service-b/api', headers=headers)")
    print()
    print("   # 服务B")
    print("   # TracingMiddleware会自动解析traceparent并继续追踪")
    print()
    print("3. Baggage传递:")
    print("   trace.set_baggage('user_id', 'user123')")
    print("   # 在下游服务中获取:")
    print("   user_id = trace.get_baggage('user_id')")
    print()


def main():
    """运行所有示例。"""
    print("\n" + "=" * 60)
    print("链路追踪系统使用示例")
    print("=" * 60 + "\n")

    example_basic_tracing()
    example_decorator_tracing()
    example_error_tracing()
    example_trace_query()
    example_api_integration()
    example_distributed_tracing()

    print("=" * 60)
    print("所有示例完成！")
    print("=" * 60)

    import os

    if os.path.exists("example_traces.db"):
        os.remove("example_traces.db")
        print("\n✓ 清理示例数据库")


if __name__ == "__main__":
    main()
