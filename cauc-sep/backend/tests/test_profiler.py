"""
性能分析模块测试。

测试性能采样、分析和报告生成功能。

作者：Backend Engineer Agent
创建日期：2026-03-07
"""

import time
from datetime import datetime

import pytest

from core.profiler import (
    FunctionProfile,
    MemorySnapshot,
    MetricType,
    PerformanceMetric,
    PerformanceProfiler,
    PerformanceReport,
    SystemMonitor,
    get_profiler,
    get_system_monitor,
    profile_function,
)


class TestPerformanceMetric:
    """性能指标测试。"""

    def test_metric_creation(self):
        """测试指标创建。"""
        metric = PerformanceMetric(
            name="test_metric",
            metric_type=MetricType.CPU,
            value=50.5,
            unit="%",
        )

        assert metric.name == "test_metric"
        assert metric.metric_type == MetricType.CPU
        assert metric.value == 50.5
        assert metric.unit == "%"
        assert isinstance(metric.timestamp, datetime)

    def test_metric_to_dict(self):
        """测试指标字典转换。"""
        metric = PerformanceMetric(
            name="memory_usage",
            metric_type=MetricType.MEMORY,
            value=1024.5,
            unit="MB",
            tags={"service": "test"},
        )

        result = metric.to_dict()

        assert result["name"] == "memory_usage"
        assert result["metric_type"] == "memory"
        assert result["value"] == 1024.5
        assert result["unit"] == "MB"
        assert result["tags"]["service"] == "test"


class TestFunctionProfile:
    """函数性能测试。"""

    def test_function_profile_creation(self):
        """测试函数性能创建。"""
        profile = FunctionProfile(
            function_name="test_function",
            total_calls=10,
            total_time=1.5,
            avg_time=0.15,
            min_time=0.1,
            max_time=0.2,
            cumulative_time=2.0,
        )

        assert profile.function_name == "test_function"
        assert profile.total_calls == 10
        assert profile.total_time == 1.5
        assert profile.avg_time == 0.15

    def test_function_profile_to_dict(self):
        """测试函数性能字典转换。"""
        profile = FunctionProfile(
            function_name="process_data",
            total_calls=100,
            total_time=5.0,
            file_path="/test/module.py",
            line_number=42,
        )

        result = profile.to_dict()

        assert result["function_name"] == "process_data"
        assert result["total_calls"] == 100
        assert result["total_time"] == 5.0
        assert result["file_path"] == "/test/module.py"
        assert result["line_number"] == 42


class TestMemorySnapshot:
    """内存快照测试。"""

    def test_memory_snapshot_creation(self):
        """测试内存快照创建。"""
        snapshot = MemorySnapshot(
            current_memory_mb=512.5,
            peak_memory_mb=1024.0,
            memory_blocks=1000,
            traceback_count=50,
        )

        assert snapshot.current_memory_mb == 512.5
        assert snapshot.peak_memory_mb == 1024.0
        assert snapshot.memory_blocks == 1000

    def test_memory_snapshot_to_dict(self):
        """测试内存快照字典转换。"""
        snapshot = MemorySnapshot(
            current_memory_mb=256.0,
            peak_memory_mb=512.0,
            top_allocations=[{"file": "test.py", "size_mb": 100.0, "count": 10}],
        )

        result = snapshot.to_dict()

        assert result["current_memory_mb"] == 256.0
        assert result["peak_memory_mb"] == 512.0
        assert len(result["top_allocations"]) == 1


class TestSystemMonitor:
    """系统监控测试。"""

    def test_system_monitor_creation(self):
        """测试系统监控器创建。"""
        monitor = SystemMonitor()
        assert monitor is not None

    def test_get_cpu_percent(self):
        """测试CPU使用率获取。"""
        monitor = SystemMonitor()
        cpu_percent = monitor.get_cpu_percent(interval=0.0)

        assert isinstance(cpu_percent, float)
        assert 0.0 <= cpu_percent <= 100.0

    def test_get_memory_info(self):
        """测试内存信息获取。"""
        monitor = SystemMonitor()
        mem_info = monitor.get_memory_info()

        assert "total_mb" in mem_info
        assert "available_mb" in mem_info
        assert "used_mb" in mem_info
        assert "percent" in mem_info

    def test_get_disk_info(self):
        """测试磁盘信息获取。"""
        monitor = SystemMonitor()
        disk_info = monitor.get_disk_info()

        assert "total_gb" in disk_info
        assert "used_gb" in disk_info
        assert "free_gb" in disk_info
        assert "percent" in disk_info

    def test_get_process_info(self):
        """测试进程信息获取。"""
        monitor = SystemMonitor()
        proc_info = monitor.get_process_info()

        assert "pid" in proc_info
        assert "cpu_percent" in proc_info
        assert "memory_mb" in proc_info
        assert "num_threads" in proc_info

    def test_collect_metrics(self):
        """测试指标收集。"""
        monitor = SystemMonitor()
        metrics = monitor.collect_metrics()

        assert isinstance(metrics, list)
        assert len(metrics) > 0

        # 验证指标类型
        for metric in metrics:
            assert isinstance(metric, PerformanceMetric)
            assert metric.name
            assert metric.metric_type in [
                MetricType.CPU,
                MetricType.MEMORY,
                MetricType.TIME,
            ]


class TestPerformanceProfiler:
    """性能分析器测试。"""

    def test_profiler_creation(self):
        """测试分析器创建。"""
        profiler = PerformanceProfiler()
        assert profiler is not None

    def test_record_function_time(self):
        """测试函数时间记录。"""
        profiler = PerformanceProfiler()

        # 记录多次执行时间
        profiler.record_function_time("test_func", 0.1)
        profiler.record_function_time("test_func", 0.2)
        profiler.record_function_time("test_func", 0.15)

        stats = profiler.get_function_stats()

        assert len(stats) == 1
        assert stats[0]["function_name"] == "test_func"
        assert stats[0]["total_calls"] == 3
        assert stats[0]["min_time"] == 0.1
        assert stats[0]["max_time"] == 0.2

    def test_get_system_metrics(self):
        """测试系统指标获取。"""
        profiler = PerformanceProfiler()
        metrics = profiler.get_system_metrics()

        assert isinstance(metrics, list)
        assert len(metrics) > 0

    def test_clear_stats(self):
        """测试清空统计数据。"""
        profiler = PerformanceProfiler()

        # 记录一些数据
        profiler.record_function_time("func1", 0.1)
        profiler.record_function_time("func2", 0.2)

        # 清空
        profiler.clear()

        stats = profiler.get_function_stats()
        assert len(stats) == 0

    def test_profile_context_manager(self):
        """测试性能分析上下文管理器。"""

        def test_function():
            time.sleep(0.01)
            return "result"

        profiler = PerformanceProfiler()

        with profiler.profile("test_session"):
            result = test_function()

        assert result == "result"

    def test_memory_tracking_context_manager(self):
        """测试内存追踪上下文管理器。"""
        profiler = PerformanceProfiler()

        with profiler.track_memory():
            # 分配一些内存
            data = [i for i in range(10000)]

        snapshots = profiler.get_memory_snapshots()
        # 内存追踪可能不可用，所以只检查不抛异常
        assert isinstance(snapshots, list)


class TestProfileFunctionDecorator:
    """性能分析装饰器测试。"""

    def test_sync_function_profiling(self):
        """测试同步函数性能分析。"""
        profiler = get_profiler()
        profiler.clear()

        @profile_function("test_sync_func")
        def sync_function():
            time.sleep(0.01)
            return 42

        result = sync_function()

        assert result == 42

        stats = profiler.get_function_stats()
        assert any(s["function_name"] == "test_sync_func" for s in stats)

    @pytest.mark.asyncio
    async def test_async_function_profiling(self):
        """测试异步函数性能分析。"""
        profiler = get_profiler()
        profiler.clear()

        @profile_function("test_async_func")
        async def async_function():
            await asyncio.sleep(0.01)
            return "async_result"

        import asyncio

        result = await async_function()

        assert result == "async_result"

        stats = profiler.get_function_stats()
        assert any(s["function_name"] == "test_async_func" for s in stats)


class TestPerformanceReport:
    """性能报告测试。"""

    def test_report_creation(self):
        """测试报告创建。"""
        report = PerformanceReport()
        assert report is not None

    def test_add_section(self):
        """测试添加章节。"""
        report = PerformanceReport()
        report.add_section("CPU分析", {"cpu_percent": 50.0})

        summary = report.generate_summary()

        assert "sections" in summary
        assert "CPU分析" in summary["sections"]

    def test_generate_full_report(self):
        """测试生成完整报告。"""
        report = PerformanceReport()
        report.add_section("系统资源", {"cpu_percent": 45.0, "memory_mb": 1024.0})
        report.add_section("函数性能", {"function_profiles": []})

        full_report = report.generate_full_report()

        assert full_report["report_type"] == "performance_full"
        assert "系统资源" in full_report["sections"]
        assert "函数性能" in full_report["sections"]

    def test_generate_html(self):
        """测试生成HTML报告。"""
        report = PerformanceReport()
        report.add_section("系统资源", {"cpu_percent": 50.0})

        html = report.generate_html()

        assert "<!DOCTYPE html>" in html
        assert "性能分析报告" in html
        assert "系统资源" in html


class TestGlobalInstances:
    """全局实例测试。"""

    def test_get_profiler(self):
        """测试获取全局分析器。"""
        profiler = get_profiler()
        assert isinstance(profiler, PerformanceProfiler)

    def test_get_system_monitor(self):
        """测试获取全局监控器。"""
        monitor = get_system_monitor()
        assert isinstance(monitor, SystemMonitor)

    def test_global_profiler_is_singleton(self):
        """测试全局分析器单例。"""
        profiler1 = get_profiler()
        profiler2 = get_profiler()

        assert profiler1 is profiler2


class TestMetricType:
    """性能指标类型枚举测试。"""

    def test_metric_type_values(self):
        """测试指标类型枚举值。"""
        assert MetricType.CPU.value == "cpu"
        assert MetricType.MEMORY.value == "memory"
        assert MetricType.TIME.value == "time"
        assert MetricType.CALLS.value == "calls"
        assert MetricType.CUSTOM.value == "custom"


class TestSystemMonitorAdvanced:
    """系统监控高级测试。"""

    def test_get_disk_info_custom_path(self):
        """测试自定义路径磁盘信息获取。"""
        monitor = SystemMonitor()

        # Windows系统使用C:，Linux使用/
        import platform

        if platform.system() == "Windows":
            disk_info = monitor.get_disk_info("C:\\")
        else:
            disk_info = monitor.get_disk_info("/")

        assert "total_gb" in disk_info
        assert "used_gb" in disk_info
        assert "free_gb" in disk_info
        assert "percent" in disk_info

    def test_get_process_info_fields(self):
        """测试进程信息字段完整性。"""
        monitor = SystemMonitor()
        proc_info = monitor.get_process_info()

        assert "pid" in proc_info
        assert "cpu_percent" in proc_info
        assert "memory_mb" in proc_info
        assert "num_threads" in proc_info
        assert "create_time" in proc_info

    def test_collect_metrics_types(self):
        """测试收集指标类型正确性。"""
        monitor = SystemMonitor()
        metrics = monitor.collect_metrics()

        # 检查指标类型分布
        metric_types = {m.metric_type for m in metrics}
        assert MetricType.CPU in metric_types
        assert MetricType.MEMORY in metric_types

    def test_collect_metrics_timestamps(self):
        """测试收集指标时间戳。"""
        monitor = SystemMonitor()
        before = datetime.now()
        metrics = monitor.collect_metrics()
        after = datetime.now()

        for metric in metrics:
            assert before <= metric.timestamp <= after

    def test_fallback_when_psutil_unavailable(self):
        """测试psutil不可用时的降级处理。"""
        monitor = SystemMonitor()
        monitor._available = False

        cpu = monitor.get_cpu_percent()
        assert cpu == 0.0

        mem = monitor.get_memory_info()
        assert mem["total_mb"] == 0.0

        disk = monitor.get_disk_info()
        assert disk["total_gb"] == 0.0


class TestPerformanceProfilerAdvanced:
    """性能分析器高级测试。"""

    def test_start_stop_profiling(self):
        """测试开始和停止性能分析。"""
        profiler = PerformanceProfiler()

        profiler.start_profiling()

        # 执行一些操作
        for _ in range(100):
            _ = sum(range(100))

        result = profiler.stop_profiling()

        assert "function_profiles" in result
        assert "total_functions" in result
        assert result["total_functions"] >= 0

    def test_stop_profiling_without_start(self):
        """测试未开始时停止分析。"""
        profiler = PerformanceProfiler()

        result = profiler.stop_profiling()

        assert result == {}

    def test_record_function_time_multiple(self):
        """测试多次记录函数时间。"""
        profiler = PerformanceProfiler()

        # 记录不同函数的时间
        profiler.record_function_time("func_a", 0.1)
        profiler.record_function_time("func_a", 0.2)
        profiler.record_function_time("func_b", 0.3)
        profiler.record_function_time("func_a", 0.15)

        stats = profiler.get_function_stats()

        assert len(stats) == 2

        func_a_stats = next(s for s in stats if s["function_name"] == "func_a")
        assert func_a_stats["total_calls"] == 3
        assert func_a_stats["min_time"] == 0.1
        assert func_a_stats["max_time"] == 0.2
        assert abs(func_a_stats["avg_time"] - 0.15) < 0.001

    def test_memory_tracking_multiple_snapshots(self):
        """测试多次内存追踪。"""
        profiler = PerformanceProfiler()

        # 第一次追踪
        with profiler.track_memory():
            _ = [i for i in range(1000)]

        # 第二次追踪
        with profiler.track_memory():
            _ = [i for i in range(2000)]

        snapshots = profiler.get_memory_snapshots()
        assert len(snapshots) == 2

    def test_clear_clears_all_data(self):
        """测试清空所有数据。"""
        profiler = PerformanceProfiler()

        profiler.record_function_time("func1", 0.1)
        profiler.record_function_time("func2", 0.2)

        with profiler.track_memory():
            pass

        profiler.clear()

        assert len(profiler.get_function_stats()) == 0
        assert len(profiler.get_memory_snapshots()) == 0


class TestProfileFunctionDecoratorAdvanced:
    """性能分析装饰器高级测试。"""

    def test_decorator_with_exception(self):
        """测试装饰器处理异常。"""
        profiler = get_profiler()
        profiler.clear()

        @profile_function("error_func")
        def error_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            error_func()

        # 即使异常，也应该记录时间
        stats = profiler.get_function_stats()
        assert any(s["function_name"] == "error_func" for s in stats)

    def test_decorator_preserves_function_name(self):
        """测试装饰器保留函数名。"""

        @profile_function()
        def my_function():
            pass

        assert my_function.__name__ == "my_function"

    def test_decorator_with_args_kwargs(self):
        """测试装饰器处理参数。"""
        profiler = get_profiler()
        profiler.clear()

        @profile_function("param_func")
        def param_func(a, b, c=None):
            return a + b + (c or 0)

        result = param_func(1, 2, c=3)

        assert result == 6

        stats = profiler.get_function_stats()
        assert any(s["function_name"] == "param_func" for s in stats)


class TestPerformanceReportAdvanced:
    """性能报告高级测试。"""

    def test_generate_summary_structure(self):
        """测试摘要报告结构。"""
        report = PerformanceReport()
        report.add_section("CPU", {"cpu_percent": 50.0})
        report.add_section("Memory", {"memory_mb": 1024.0})

        summary = report.generate_summary()

        assert "report_type" in summary
        assert summary["report_type"] == "performance_summary"
        assert "sections" in summary
        assert "CPU" in summary["sections"]
        assert "Memory" in summary["sections"]
        assert summary["section_count"] == 2

    def test_generate_full_report_structure(self):
        """测试完整报告结构。"""
        report = PerformanceReport()
        report.add_section("Test", {"value": 123})

        full_report = report.generate_full_report()

        assert full_report["report_type"] == "performance_full"
        assert "sections" in full_report
        assert "Test" in full_report["sections"]

        # 验证章节包含时间戳
        assert "timestamp" in full_report["sections"]["Test"]

    def test_generate_html_with_function_profiles(self):
        """测试生成包含函数性能的HTML报告。"""
        report = PerformanceReport()
        report.add_section(
            "函数性能",
            {
                "function_profiles": [
                    {
                        "function_name": "test_func",
                        "total_calls": 100,
                        "total_time": 1.5,
                        "avg_time": 0.015,
                        "cumulative_time": 2.0,
                    }
                ]
            },
        )

        html = report.generate_html()

        assert "<!DOCTYPE html>" in html
        assert "函数性能" in html
        assert "test_func" in html
        assert "<table>" in html

    def test_generate_html_with_memory_data(self):
        """测试生成包含内存数据的HTML报告。"""
        report = PerformanceReport()
        report.add_section(
            "内存分析",
            {
                "current_memory_mb": 512.5,
                "peak_memory_mb": 1024.0,
            },
        )

        html = report.generate_html()

        assert "内存分析" in html
        assert "512.5" in html or "512.50" in html
        assert "1024.0" in html or "1024.00" in html

    def test_generate_html_with_generic_data(self):
        """测试生成包含通用数据的HTML报告。"""
        report = PerformanceReport()
        report.add_section("通用指标", {"requests_per_second": 1500, "latency_ms": 25})

        html = report.generate_html()

        assert "通用指标" in html
        assert "1500" in html
        assert "25" in html


class TestFunctionProfileAdvanced:
    """函数性能高级测试。"""

    def test_function_profile_with_file_info(self):
        """测试带文件信息的函数性能。"""
        profile = FunctionProfile(
            function_name="process_data",
            total_calls=50,
            total_time=2.5,
            avg_time=0.05,
            min_time=0.03,
            max_time=0.1,
            cumulative_time=3.0,
            file_path="/app/services/data_processor.py",
            line_number=42,
        )

        result = profile.to_dict()

        assert result["file_path"] == "/app/services/data_processor.py"
        assert result["line_number"] == 42

    def test_function_profile_zero_calls(self):
        """测试零调用函数性能。"""
        profile = FunctionProfile(function_name="unused_func")

        result = profile.to_dict()

        assert result["total_calls"] == 0
        assert result["total_time"] == 0.0
        assert result["avg_time"] == 0.0


class TestMemorySnapshotAdvanced:
    """内存快照高级测试。"""

    def test_memory_snapshot_with_top_allocations(self):
        """测试带TOP分配的内存快照。"""
        snapshot = MemorySnapshot(
            current_memory_mb=256.0,
            peak_memory_mb=512.0,
            memory_blocks=5000,
            traceback_count=100,
            top_allocations=[
                {
                    "file": "/app/main.py:100",
                    "size_mb": 100.0,
                    "count": 50,
                },
                {
                    "file": "/app/utils.py:50",
                    "size_mb": 50.0,
                    "count": 25,
                },
            ],
        )

        result = snapshot.to_dict()

        assert len(result["top_allocations"]) == 2
        assert result["top_allocations"][0]["size_mb"] == 100.0


class TestPerformanceMetricAdvanced:
    """性能指标高级测试。"""

    def test_metric_with_tags(self):
        """测试带标签的性能指标。"""
        metric = PerformanceMetric(
            name="api.response_time",
            metric_type=MetricType.TIME,
            value=0.125,
            unit="s",
            tags={"endpoint": "/api/users", "method": "GET", "status": "200"},
        )

        result = metric.to_dict()

        assert result["tags"]["endpoint"] == "/api/users"
        assert result["tags"]["method"] == "GET"

    def test_metric_custom_timestamp(self):
        """测试自定义时间戳。"""
        custom_time = datetime(2026, 1, 1, 12, 0, 0)
        metric = PerformanceMetric(
            name="test_metric",
            metric_type=MetricType.CUSTOM,
            value=100.0,
            timestamp=custom_time,
        )

        assert metric.timestamp == custom_time


class TestAPIResponseModels:
    """API响应模型测试。"""

    def test_performance_metrics_response(self):
        """测试性能指标响应模型。"""
        from core.profiler import PerformanceMetricsResponse

        response = PerformanceMetricsResponse(
            metrics=[{"name": "cpu", "value": 50.0}],
            timestamp=datetime.now().isoformat(),
        )

        assert len(response.metrics) == 1
        assert response.timestamp is not None

    def test_function_profile_response(self):
        """测试函数性能响应模型。"""
        from core.profiler import FunctionProfileResponse

        response = FunctionProfileResponse(
            function_profiles=[{"function_name": "test"}],
            total_functions=1,
        )

        assert len(response.function_profiles) == 1
        assert response.total_functions == 1

    def test_memory_snapshot_response(self):
        """测试内存快照响应模型。"""
        from core.profiler import MemorySnapshotResponse

        response = MemorySnapshotResponse(
            current_memory_mb=256.0,
            peak_memory_mb=512.0,
            memory_blocks=1000,
            top_allocations=[],
        )

        assert response.current_memory_mb == 256.0
        assert response.peak_memory_mb == 512.0

    def test_system_info_response(self):
        """测试系统信息响应模型。"""
        from core.profiler import SystemInfoResponse

        response = SystemInfoResponse(
            cpu={"percent": 50.0},
            memory={"used_mb": 1024.0},
            disk={"used_gb": 100.0},
            process={"pid": 1234},
        )

        assert response.cpu["percent"] == 50.0
        assert response.memory["used_mb"] == 1024.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
