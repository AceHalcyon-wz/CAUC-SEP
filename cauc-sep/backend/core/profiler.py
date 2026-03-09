"""
性能分析核心模块。

实现应用性能监控（APM）功能，支持性能采样、分析和报告生成。

功能：
    - CPU/内存性能采样
    - 函数级别性能追踪
    - 性能热点分析
    - 性能报告生成
    - 性能指标导出

技术栈：
    - Python 3.11+
    - cProfile 性能分析
    - psutil 系统监控
    - memory_profiler 内存分析

作者：Backend Engineer Agent
创建日期：2026-03-07
依赖：psutil, pydantic
"""

import cProfile
import functools
import gc
import io
import logging
import pstats
import time
import tracemalloc
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# 性能指标数据结构
# ============================================================================


class MetricType(str, Enum):
    """性能指标类型枚举。"""

    CPU = "cpu"  # CPU使用率
    MEMORY = "memory"  # 内存使用
    TIME = "time"  # 执行时间
    CALLS = "calls"  # 函数调用次数
    CUSTOM = "custom"  # 自定义指标


@dataclass
class PerformanceMetric:
    """性能指标数据结构。

    Attributes:
        name: 指标名称
        metric_type: 指标类型
        value: 指标值
        unit: 单位
        timestamp: 时间戳
        tags: 标签字典
    """

    name: str
    metric_type: MetricType
    value: float
    unit: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    tags: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式。

        Returns:
            dict: 指标数据字典
        """
        return {
            "name": self.name,
            "metric_type": self.metric_type.value,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
        }


@dataclass
class FunctionProfile:
    """函数性能分析结果。

    Attributes:
        function_name: 函数名称
        total_calls: 总调用次数
        total_time: 总执行时间（秒）
        avg_time: 平均执行时间（秒）
        min_time: 最小执行时间（秒）
        max_time: 最大执行时间（秒）
        cumulative_time: 累计时间（秒）
        file_path: 文件路径
        line_number: 行号
    """

    function_name: str
    total_calls: int = 0
    total_time: float = 0.0
    avg_time: float = 0.0
    min_time: float = 0.0
    max_time: float = 0.0
    cumulative_time: float = 0.0
    file_path: str = ""
    line_number: int = 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式。

        Returns:
            dict: 函数性能数据字典
        """
        return {
            "function_name": self.function_name,
            "total_calls": self.total_calls,
            "total_time": round(self.total_time, 6),
            "avg_time": round(self.avg_time, 6),
            "min_time": round(self.min_time, 6),
            "max_time": round(self.max_time, 6),
            "cumulative_time": round(self.cumulative_time, 6),
            "file_path": self.file_path,
            "line_number": self.line_number,
        }


@dataclass
class MemorySnapshot:
    """内存快照数据结构。

    Attributes:
        timestamp: 时间戳
        current_memory_mb: 当前内存使用（MB）
        peak_memory_mb: 峰值内存使用（MB）
        memory_blocks: 内存块数量
        traceback_count: 追踪数量
        top_allocations: 内存分配TOP列表
    """

    timestamp: datetime = field(default_factory=datetime.now)
    current_memory_mb: float = 0.0
    peak_memory_mb: float = 0.0
    memory_blocks: int = 0
    traceback_count: int = 0
    top_allocations: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式。

        Returns:
            dict: 内存快照数据字典
        """
        return {
            "timestamp": self.timestamp.isoformat(),
            "current_memory_mb": round(self.current_memory_mb, 2),
            "peak_memory_mb": round(self.peak_memory_mb, 2),
            "memory_blocks": self.memory_blocks,
            "traceback_count": self.traceback_count,
            "top_allocations": self.top_allocations,
        }


# ============================================================================
# 系统资源监控
# ============================================================================


class SystemMonitor:
    """系统资源监控器。

    提供CPU、内存、磁盘等系统资源的实时监控。

    Example:
        >>> monitor = SystemMonitor()
        >>> cpu_percent = monitor.get_cpu_percent()
        >>> memory_info = monitor.get_memory_info()
    """

    def __init__(self):
        """初始化系统监控器。"""
        try:
            import psutil

            self._psutil = psutil
            self._available = True
        except ImportError:
            self._psutil = None
            self._available = False
            logger.warning("[SystemMonitor] psutil not available, using fallback")

    def get_cpu_percent(self, interval: float = 0.1) -> float:
        """获取CPU使用率。

        Args:
            interval: 采样间隔（秒）

        Returns:
            float: CPU使用率百分比
        """
        if self._available:
            return self._psutil.cpu_percent(interval=interval)
        return 0.0

    def get_memory_info(self) -> dict[str, float]:
        """获取内存信息。

        Returns:
            dict: 内存信息字典（单位：MB）
        """
        if self._available:
            mem = self._psutil.virtual_memory()
            return {
                "total_mb": mem.total / (1024 * 1024),
                "available_mb": mem.available / (1024 * 1024),
                "used_mb": mem.used / (1024 * 1024),
                "percent": mem.percent,
            }
        return {
            "total_mb": 0.0,
            "available_mb": 0.0,
            "used_mb": 0.0,
            "percent": 0.0,
        }

    def get_disk_info(self, path: str = "/") -> dict[str, float]:
        """获取磁盘信息。

        Args:
            path: 磁盘路径

        Returns:
            dict: 磁盘信息字典（单位：GB）
        """
        if self._available:
            disk = self._psutil.disk_usage(path)
            return {
                "total_gb": disk.total / (1024 * 1024 * 1024),
                "used_gb": disk.used / (1024 * 1024 * 1024),
                "free_gb": disk.free / (1024 * 1024 * 1024),
                "percent": disk.percent,
            }
        return {
            "total_gb": 0.0,
            "used_gb": 0.0,
            "free_gb": 0.0,
            "percent": 0.0,
        }

    def get_process_info(self) -> dict[str, Any]:
        """获取当前进程信息。

        Returns:
            dict: 进程信息字典
        """
        if self._available:
            process = self._psutil.Process()
            with process.oneshot():
                return {
                    "pid": process.pid,
                    "cpu_percent": process.cpu_percent(),
                    "memory_mb": process.memory_info().rss / (1024 * 1024),
                    "num_threads": process.num_threads(),
                    "num_fds": process.num_fds() if hasattr(process, "num_fds") else 0,
                    "create_time": datetime.fromtimestamp(process.create_time()).isoformat(),
                }
        return {
            "pid": 0,
            "cpu_percent": 0.0,
            "memory_mb": 0.0,
            "num_threads": 0,
            "num_fds": 0,
            "create_time": datetime.now().isoformat(),
        }

    def collect_metrics(self) -> list[PerformanceMetric]:
        """收集所有系统指标。

        Returns:
            list[PerformanceMetric]: 性能指标列表
        """
        metrics = []
        timestamp = datetime.now()

        # CPU指标
        cpu_percent = self.get_cpu_percent(interval=0.0)
        metrics.append(
            PerformanceMetric(
                name="system.cpu.percent",
                metric_type=MetricType.CPU,
                value=cpu_percent,
                unit="%",
                timestamp=timestamp,
                tags={"source": "psutil"},
            )
        )

        # 内存指标
        mem_info = self.get_memory_info()
        metrics.append(
            PerformanceMetric(
                name="system.memory.used_mb",
                metric_type=MetricType.MEMORY,
                value=mem_info["used_mb"],
                unit="MB",
                timestamp=timestamp,
                tags={"source": "psutil"},
            )
        )
        metrics.append(
            PerformanceMetric(
                name="system.memory.percent",
                metric_type=MetricType.MEMORY,
                value=mem_info["percent"],
                unit="%",
                timestamp=timestamp,
                tags={"source": "psutil"},
            )
        )

        # 进程指标
        proc_info = self.get_process_info()
        metrics.append(
            PerformanceMetric(
                name="process.memory_mb",
                metric_type=MetricType.MEMORY,
                value=proc_info["memory_mb"],
                unit="MB",
                timestamp=timestamp,
                tags={"source": "psutil", "pid": str(proc_info["pid"])},
            )
        )
        metrics.append(
            PerformanceMetric(
                name="process.cpu_percent",
                metric_type=MetricType.CPU,
                value=proc_info["cpu_percent"],
                unit="%",
                timestamp=timestamp,
                tags={"source": "psutil", "pid": str(proc_info["pid"])},
            )
        )

        return metrics


# ============================================================================
# 性能分析器
# ============================================================================


class PerformanceProfiler:
    """性能分析器。

    提供函数级别的性能分析和热点检测。

    Example:
        >>> profiler = PerformanceProfiler()
        >>> with profiler.profile("my_function"):
        ...     # 执行代码
        ...     pass
        >>> report = profiler.get_report()
    """

    def __init__(self):
        """初始化性能分析器。"""
        self._profile: Optional[cProfile.Profile] = None
        self._function_stats: dict[str, FunctionProfile] = {}
        self._call_times: dict[str, list[float]] = {}
        self._system_monitor = SystemMonitor()
        self._memory_snapshots: list[MemorySnapshot] = []
        self._is_memory_tracking = False

    def start_profiling(self) -> None:
        """开始性能分析。"""
        self._profile = cProfile.Profile()
        self._profile.enable()
        logger.debug("[PerformanceProfiler] Profiling started")

    def stop_profiling(self) -> dict[str, Any]:
        """停止性能分析并返回结果。

        Returns:
            dict: 分析结果
        """
        if not self._profile:
            return {}

        self._profile.disable()

        # 提取统计数据
        stream = io.StringIO()
        stats = pstats.Stats(self._profile, stream=stream)
        stats.sort_stats("cumulative")

        # 解析函数统计
        function_profiles = []
        for func, (cc, nc, tt, ct, callers) in stats.stats.items():
            file_path, line_number, func_name = func
            profile = FunctionProfile(
                function_name=func_name,
                total_calls=nc,
                total_time=tt,
                avg_time=tt / nc if nc > 0 else 0,
                cumulative_time=ct,
                file_path=file_path,
                line_number=line_number,
            )
            function_profiles.append(profile)

        # 按累计时间排序
        function_profiles.sort(key=lambda x: x.cumulative_time, reverse=True)

        logger.debug(
            f"[PerformanceProfiler] Profiling stopped, {len(function_profiles)} functions profiled"
        )

        return {
            "function_profiles": [fp.to_dict() for fp in function_profiles[:100]],  # TOP 100
            "total_functions": len(function_profiles),
            "profile_time": datetime.now().isoformat(),
        }

    def start_memory_tracking(self) -> None:
        """开始内存追踪。"""
        if not self._is_memory_tracking:
            tracemalloc.start()
            self._is_memory_tracking = True
            logger.debug("[PerformanceProfiler] Memory tracking started")

    def stop_memory_tracking(self) -> MemorySnapshot:
        """停止内存追踪并返回快照。

        Returns:
            MemorySnapshot: 内存快照
        """
        if not self._is_memory_tracking:
            return MemorySnapshot()

        # 获取当前内存快照
        current, peak = tracemalloc.get_traced_memory()
        snapshot = tracemalloc.take_snapshot()

        # 获取TOP内存分配
        top_stats = snapshot.statistics("lineno")[:10]
        top_allocations = [
            {
                "file": str(stat.traceback),
                "size_mb": stat.size / (1024 * 1024),
                "count": stat.count,
            }
            for stat in top_stats
        ]

        memory_snapshot = MemorySnapshot(
            current_memory_mb=current / (1024 * 1024),
            peak_memory_mb=peak / (1024 * 1024),
            memory_blocks=len(snapshot.statistics("lineno")),
            traceback_count=len(snapshot.traces),
            top_allocations=top_allocations,
        )

        tracemalloc.stop()
        self._is_memory_tracking = False

        logger.debug(
            f"[PerformanceProfiler] Memory tracking stopped, peak: {memory_snapshot.peak_memory_mb:.2f} MB"
        )

        return memory_snapshot

    @contextmanager
    def profile(self, name: str = "profile_session"):
        """性能分析上下文管理器。

        Args:
            name: 分析会话名称

        Yields:
            PerformanceProfiler: 分析器实例
        """
        self.start_profiling()
        try:
            yield self
        finally:
            result = self.stop_profiling()
            logger.info(
                f"[PerformanceProfiler] Profile session '{name}' completed: {result['total_functions']} functions"
            )

    @contextmanager
    def track_memory(self):
        """内存追踪上下文管理器。

        Yields:
            PerformanceProfiler: 分析器实例
        """
        self.start_memory_tracking()
        try:
            yield self
        finally:
            snapshot = self.stop_memory_tracking()
            self._memory_snapshots.append(snapshot)

    def record_function_time(self, func_name: str, execution_time: float) -> None:
        """记录函数执行时间。

        Args:
            func_name: 函数名称
            execution_time: 执行时间（秒）
        """
        if func_name not in self._call_times:
            self._call_times[func_name] = []

        self._call_times[func_name].append(execution_time)

        # 更新函数统计
        times = self._call_times[func_name]
        if func_name not in self._function_stats:
            self._function_stats[func_name] = FunctionProfile(function_name=func_name)

        stats = self._function_stats[func_name]
        stats.total_calls = len(times)
        stats.total_time = sum(times)
        stats.avg_time = stats.total_time / stats.total_calls
        stats.min_time = min(times)
        stats.max_time = max(times)

    def get_function_stats(self) -> list[dict[str, Any]]:
        """获取函数统计信息。

        Returns:
            list: 函数统计列表
        """
        return [stats.to_dict() for stats in self._function_stats.values()]

    def get_memory_snapshots(self) -> list[dict[str, Any]]:
        """获取内存快照列表。

        Returns:
            list: 内存快照列表
        """
        return [snapshot.to_dict() for snapshot in self._memory_snapshots]

    def get_system_metrics(self) -> list[dict[str, Any]]:
        """获取系统指标。

        Returns:
            list: 系统指标列表
        """
        return [metric.to_dict() for metric in self._system_monitor.collect_metrics()]

    def clear(self) -> None:
        """清空所有统计数据。"""
        self._function_stats.clear()
        self._call_times.clear()
        self._memory_snapshots.clear()
        logger.debug("[PerformanceProfiler] All stats cleared")


# ============================================================================
# 性能分析装饰器
# ============================================================================


def profile_function(name: Optional[str] = None):
    """函数性能分析装饰器。

    自动记录函数执行时间和性能指标。

    Args:
        name: 函数名称（可选，默认使用函数名）

    Returns:
        Callable: 装饰器函数

    Example:
        >>> @profile_function("process_data")
        ... def process_data(data):
        ...     return data * 2
    """

    def decorator(func: Callable) -> Callable:
        func_name = name or func.__name__

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                execution_time = time.perf_counter() - start_time
                _global_profiler.record_function_time(func_name, execution_time)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                execution_time = time.perf_counter() - start_time
                _global_profiler.record_function_time(func_name, execution_time)

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============================================================================
# 性能报告生成器
# ============================================================================


class PerformanceReport:
    """性能报告生成器。

    生成详细的性能分析报告，支持多种格式输出。

    Example:
        >>> report = PerformanceReport()
        >>> report.add_section("CPU Analysis", cpu_data)
        >>> report.generate("html")
    """

    def __init__(self):
        """初始化性能报告生成器。"""
        self._sections: dict[str, dict[str, Any]] = {}
        self._created_at = datetime.now()

    def add_section(self, name: str, data: dict[str, Any]) -> None:
        """添加报告章节。

        Args:
            name: 章节名称
            data: 章节数据
        """
        self._sections[name] = {
            "name": name,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }

    def generate_summary(self) -> dict[str, Any]:
        """生成摘要报告。

        Returns:
            dict: 摘要报告数据
        """
        return {
            "report_type": "performance_summary",
            "created_at": self._created_at.isoformat(),
            "sections": list(self._sections.keys()),
            "section_count": len(self._sections),
        }

    def generate_full_report(self) -> dict[str, Any]:
        """生成完整报告。

        Returns:
            dict: 完整报告数据
        """
        return {
            "report_type": "performance_full",
            "created_at": self._created_at.isoformat(),
            "sections": self._sections,
        }

    def generate_html(self) -> str:
        """生成HTML格式报告。

        Returns:
            str: HTML报告内容
        """
        html_parts = [
            "<!DOCTYPE html>",
            "<html lang='zh-CN'>",
            "<head>",
            "    <meta charset='UTF-8'>",
            "    <title>性能分析报告</title>",
            "    <style>",
            "        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }",
            "        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }",
            "        h1 { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }",
            "        h2 { color: #555; margin-top: 30px; }",
            "        .section { margin: 20px 0; padding: 15px; background: #f9f9f9; border-left: 4px solid #007bff; }",
            "        .metric { display: inline-block; margin: 10px; padding: 10px; background: #e3f2fd; border-radius: 4px; }",
            "        .metric-value { font-size: 24px; font-weight: bold; color: #007bff; }",
            "        .metric-label { font-size: 12px; color: #666; }",
            "        table { width: 100%; border-collapse: collapse; margin: 10px 0; }",
            "        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }",
            "        th { background: #007bff; color: white; }",
            "        tr:hover { background: #f5f5f5; }",
            "        .timestamp { color: #999; font-size: 12px; }",
            "    </style>",
            "</head>",
            "<body>",
            "    <div class='container'>",
            f"        <h1>性能分析报告</h1>",
            f"        <p class='timestamp'>生成时间: {self._created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>",
        ]

        # 添加各章节
        for section_name, section_data in self._sections.items():
            html_parts.append(f"        <div class='section'>")
            html_parts.append(f"            <h2>{section_name}</h2>")

            data = section_data.get("data", {})

            # 根据数据类型生成不同的HTML
            if "function_profiles" in data:
                # 函数性能表格
                html_parts.append("            <table>")
                html_parts.append(
                    "                <tr><th>函数名</th><th>调用次数</th><th>总时间(s)</th><th>平均时间(s)</th><th>累计时间(s)</th></tr>"
                )
                for func in data["function_profiles"][:20]:  # TOP 20
                    html_parts.append(
                        f"                <tr>"
                        f"<td>{func['function_name']}</td>"
                        f"<td>{func['total_calls']}</td>"
                        f"<td>{func['total_time']:.6f}</td>"
                        f"<td>{func['avg_time']:.6f}</td>"
                        f"<td>{func['cumulative_time']:.6f}</td>"
                        f"</tr>"
                    )
                html_parts.append("            </table>")
            elif "current_memory_mb" in data:
                # 内存指标
                html_parts.append(
                    f"            <div class='metric'>"
                    f"<div class='metric-value'>{data['current_memory_mb']:.2f} MB</div>"
                    f"<div class='metric-label'>当前内存</div>"
                    f"</div>"
                )
                html_parts.append(
                    f"            <div class='metric'>"
                    f"<div class='metric-value'>{data['peak_memory_mb']:.2f} MB</div>"
                    f"<div class='metric-label'>峰值内存</div>"
                    f"</div>"
                )
            else:
                # 通用数据显示
                for key, value in data.items():
                    if isinstance(value, (int, float, str)):
                        html_parts.append(
                            f"            <div class='metric'>"
                            f"<div class='metric-value'>{value}</div>"
                            f"<div class='metric-label'>{key}</div>"
                            f"</div>"
                        )

            html_parts.append("        </div>")

        html_parts.extend(
            [
                "    </div>",
                "</body>",
                "</html>",
            ]
        )

        return "\n".join(html_parts)


# ============================================================================
# API响应模型
# ============================================================================


class PerformanceMetricsResponse(BaseModel):
    """性能指标响应模型。"""

    metrics: list[dict[str, Any]] = Field(..., description="性能指标列表")
    timestamp: str = Field(..., description="时间戳")


class FunctionProfileResponse(BaseModel):
    """函数性能响应模型。"""

    function_profiles: list[dict[str, Any]] = Field(..., description="函数性能列表")
    total_functions: int = Field(0, description="总函数数")


class MemorySnapshotResponse(BaseModel):
    """内存快照响应模型。"""

    current_memory_mb: float = Field(0.0, description="当前内存使用(MB)")
    peak_memory_mb: float = Field(0.0, description="峰值内存使用(MB)")
    memory_blocks: int = Field(0, description="内存块数量")
    top_allocations: list[dict[str, Any]] = Field(default_factory=list, description="TOP内存分配")


class SystemInfoResponse(BaseModel):
    """系统信息响应模型。"""

    cpu: dict[str, float] = Field(..., description="CPU信息")
    memory: dict[str, float] = Field(..., description="内存信息")
    disk: dict[str, float] = Field(..., description="磁盘信息")
    process: dict[str, Any] = Field(..., description="进程信息")


# ============================================================================
# 全局实例
# ============================================================================

# 全局性能分析器实例
_global_profiler = PerformanceProfiler()

# 全局系统监控实例
_system_monitor = SystemMonitor()


def get_profiler() -> PerformanceProfiler:
    """获取全局性能分析器实例。

    Returns:
        PerformanceProfiler: 性能分析器实例
    """
    return _global_profiler


def get_system_monitor() -> SystemMonitor:
    """获取全局系统监控实例。

    Returns:
        SystemMonitor: 系统监控实例
    """
    return _system_monitor
