"""
监控追踪子模块

文件名: __init__.py
路径: backend/core/monitoring/
功能: 提供分布式链路追踪、性能分析和系统指标收集能力
作者: Backend Engineer Agent
创建日期: 2024-01-15
更新日期: 2026-03-14
版本: 1.0.0

核心功能：
    - 分布式链路追踪（OpenTelemetry兼容）
    - 性能分析器（函数级性能剖析）
    - 系统指标收集（CPU、内存、IO等）
    - 查询性能监控（数据库查询追踪）

导出组件：
    - TracingMiddleware: 链路追踪中间件
    - init_tracing: 初始化追踪系统
    - tracer: 全局追踪器实例
    - Tracer: 追踪器类
    - traced: 追踪装饰器
    - get_trace_storage: 获取追踪存储实例
    - PerformanceProfiler: 性能分析器
    - profile_function: 函数性能分析装饰器
    - get_profiler: 获取分析器实例
    - SystemMonitor: 系统监控器
    - get_system_monitor: 获取系统监控器
    - MetricsCollector: 指标收集器
    - get_metrics_collector: 获取指标收集器
    - QueryMonitor: 查询监控器
    - get_query_monitor: 获取查询监控器

依赖：
    - opentelemetry: 分布式追踪SDK（可选）
    - asyncio: 异步IO支持
    - time: 时间测量
    - typing: 类型注解支持

使用示例：
    >>> from backend.core.monitoring import init_tracing, traced, PerformanceProfiler
    >>> 
    >>> # 初始化追踪
    >>> tracer = init_tracing(service_name="cauc-sep-backend")
    >>> 
    >>> # 性能分析
    >>> profiler = get_profiler()
    >>> profiler.start_profiling()
"""

from .tracing import (
    TracingMiddleware,
    init_tracing,
    tracer,
    Tracer,
    traced,
    get_trace_storage,
)
from .profiler import (
    PerformanceProfiler,
    profile_function,
    get_profiler,
    SystemMonitor,
    get_system_monitor,
)
from .metrics import (
    Metric,
    MetricType,
    Counter,
    Gauge,
    Histogram,
    MetricsRegistry,
    BusinessMetricsCollector,
    default_registry,
    business_metrics,
    get_business_metrics,
)
from .query_monitor import (
    QueryMetric,
    QueryStatistics,
    QueryPerformanceMonitor,
    setup_query_monitoring,
    QueryPerformanceTracker,
    track_query_performance,
    get_query_monitor,
    init_query_monitor,
    record_query,
    get_slow_queries,
    get_query_statistics,
)

__all__ = [
    "TracingMiddleware",
    "init_tracing",
    "tracer",
    "Tracer",
    "traced",
    "get_trace_storage",
    "PerformanceProfiler",
    "profile_function",
    "get_profiler",
    "SystemMonitor",
    "get_system_monitor",
    "Metric",
    "MetricType",
    "Counter",
    "Gauge",
    "Histogram",
    "MetricsRegistry",
    "BusinessMetricsCollector",
    "default_registry",
    "business_metrics",
    "get_business_metrics",
    "QueryMetric",
    "QueryStatistics",
    "QueryPerformanceMonitor",
    "setup_query_monitoring",
    "QueryPerformanceTracker",
    "track_query_performance",
    "get_query_monitor",
    "init_query_monitor",
    "record_query",
    "get_slow_queries",
    "get_query_statistics",
]
