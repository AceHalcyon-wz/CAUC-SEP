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
    - record_span: 记录追踪跨度
    - tracer: 全局追踪器实例
    - Profiler: 性能分析器
    - profile_function: 函数性能分析装饰器
    - MetricsCollector: 指标收集器
    - QueryMonitor: 查询监控器

依赖：
    - opentelemetry: 分布式追踪SDK（可选）
    - asyncio: 异步IO支持
    - time: 时间测量
    - typing: 类型注解支持

使用示例：
    >>> from backend.core.monitoring import init_tracing, record_span, Profiler
    >>> 
    >>> # 初始化追踪
    >>> init_tracing(service_name="cauc-sep-backend")
    >>> 
    >>> # 记录追踪跨度
    >>> with record_span("operation_name"):
    ...     # 执行操作
    ...     pass
    >>> 
    >>> # 性能分析
    >>> profiler = get_profiler()
    >>> profiler.start()
"""

from .tracing import (
    TracingMiddleware,
    init_tracing,
    record_span,
    tracer,
)
from .profiler import Profiler, profile_function, get_profiler
from .metrics import MetricsCollector, get_metrics_collector
from .query_monitor import QueryMonitor, get_query_monitor

__all__ = [
    "TracingMiddleware",
    "init_tracing",
    "record_span",
    "tracer",
    "Profiler",
    "profile_function",
    "get_profiler",
    "MetricsCollector",
    "get_metrics_collector",
    "QueryMonitor",
    "get_query_monitor",
]
