"""
性能分析 API 测试模块。

测试功能：
    - 系统资源监控
    - 函数性能分析
    - 内存追踪
    - 性能报告生成

作者：Test Debugger Agent
创建日期：2026-03-08
依赖：pytest, httpx
"""

import time

import pytest
from fastapi.testclient import TestClient

from api.performance import router
from core.monitoring.profiler import (
    FunctionProfile,
    MemorySnapshot,
    PerformanceProfiler,
    PerformanceReport,
    SystemMonitor,
    get_profiler,
    get_system_monitor,
)


class TestPerformanceAPI:
    """性能分析API测试。"""

    @pytest.fixture
    def profiler(self):
        """创建性能分析器。"""
        profiler = get_profiler()
        yield profiler

    @pytest.fixture
    def monitor(self):
        """创建系统监控器。"""
        monitor = get_system_monitor()
        yield monitor

    @pytest.fixture
    def test_client(self, profiler, monitor):
        """创建测试客户端。"""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        with TestClient(app) as client:
            yield client

    def test_get_system_info(self, test_client):
        """测试获取系统资源信息。"""
        response = test_client.get("/api/v1/performance/system")

        assert response.status_code == 200
        data = response.json()
        assert "cpu" in data
        assert "memory" in data
        assert "disk" in data
        assert "process" in data

    def test_get_performance_metrics(self, test_client):
        """测试获取性能指标。"""
        response = test_client.get("/api/v1/performance/metrics")

        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert "timestamp" in data

    def test_get_cpu_stats(self, test_client):
        """测试获取CPU统计信息。"""
        response = test_client.get("/api/v1/performance/cpu")

        assert response.status_code == 200
        data = response.json()
        assert "cpu_percent" in data
        assert "cpu_count" in data
        assert "timestamp" in data

    def test_get_memory_stats(self, test_client):
        """测试获取内存统计信息。"""
        response = test_client.get("/api/v1/performance/memory")

        assert response.status_code == 200
        data = response.json()
        assert "total_mb" in data
        assert "available_mb" in data
        assert "used_mb" in data
        assert "percent" in data
        assert "timestamp" in data

    def test_get_function_profiles(self, test_client, profiler):
        """测试获取函数性能数据。"""
        # 添加一些函数性能数据
        profiler.record_function_call("test_func", 0.1)
        profiler.record_function_call("test_func", 0.2)
        profiler.record_function_call("another_func", 0.05)

        response = test_client.get("/api/v1/performance/functions")

        assert response.status_code == 200
        data = response.json()
        assert "function_profiles" in data
        assert "total_functions" in data

    def test_start_profiling(self, test_client):
        """测试开始性能分析。"""
        response = test_client.post("/api/v1/performance/profile/start")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "timestamp" in data

    def test_stop_profiling(self, test_client, profiler):
        """测试停止性能分析。"""
        # 先开始分析
        profiler.start_profiling()

        response = test_client.post("/api/v1/performance/profile/stop")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_profile_snapshot(self, test_client, profiler):
        """测试获取性能快照。"""
        # 添加一些数据
        profiler.record_function_call("test_func", 0.1)

        response = test_client.get("/api/v1/performance/profile/snapshot")

        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "system_metrics" in data
        assert "function_stats" in data

    def test_get_memory_snapshots(self, test_client, profiler):
        """测试获取内存快照列表。"""
        # 添加内存快照
        profiler.take_memory_snapshot()

        response = test_client.get("/api/v1/performance/memory/snapshots")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "snapshots" in data
        assert "timestamp" in data

    def test_start_memory_tracking(self, test_client):
        """测试开始内存追踪。"""
        response = test_client.post("/api/v1/performance/memory/track/start")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_stop_memory_tracking(self, test_client, profiler):
        """测试停止内存追踪。"""
        # 先开始追踪
        profiler.start_memory_tracking()

        response = test_client.post("/api/v1/performance/memory/track/stop")

        assert response.status_code == 200
        data = response.json()
        assert "current_memory_mb" in data
        assert "peak_memory_mb" in data

    def test_generate_performance_report(self, test_client, profiler):
        """测试生成性能报告。"""
        # 添加一些数据
        profiler.record_function_call("test_func", 0.1)

        response = test_client.post(
            "/api/v1/performance/report/generate",
            params={"include_functions": True, "include_memory": True, "include_system": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "report" in data
        assert "timestamp" in data

    def test_generate_html_report(self, test_client, profiler):
        """测试生成HTML报告。"""
        response = test_client.get("/api/v1/performance/report/html")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "html" in data

    def test_clear_performance_data(self, test_client, profiler):
        """测试清空性能数据。"""
        # 添加一些数据
        profiler.record_function_call("test_func", 0.1)

        response = test_client.delete("/api/v1/performance/data/clear")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_performance_health_check(self, test_client):
        """测试性能监控系统健康检查。"""
        response = test_client.get("/api/v1/performance/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "warning", "unhealthy"]

    def test_get_performance_hotspots(self, test_client, profiler):
        """测试获取性能热点。"""
        # 添加一些函数调用数据
        profiler.record_function_call("slow_func", 0.5)  # 500ms
        profiler.record_function_call("fast_func", 0.001)  # 1ms

        response = test_client.get(
            "/api/v1/performance/hotspots",
            params={"threshold_ms": 10.0, "limit": 20},
        )

        assert response.status_code == 200
        data = response.json()
        assert "threshold_ms" in data
        assert "hotspots" in data

    def test_get_performance_summary(self, test_client, profiler):
        """测试获取性能摘要。"""
        # 添加一些数据
        profiler.record_function_call("test_func", 0.1)

        response = test_client.get("/api/v1/performance/summary")

        assert response.status_code == 200
        data = response.json()
        assert "system" in data
        assert "functions" in data
        assert "memory" in data
        assert "timestamp" in data


class TestPerformanceProfiler:
    """性能分析器测试。"""

    @pytest.fixture
    def profiler(self):
        """创建性能分析器。"""
        return PerformanceProfiler()

    def test_profiler_initialization(self, profiler):
        """测试分析器初始化。"""
        assert profiler is not None

    def test_record_function_call(self, profiler):
        """测试记录函数调用。"""
        profiler.record_function_call("test_func", 0.1)
        profiler.record_function_call("test_func", 0.2)

        stats = profiler.get_function_stats()

        assert len(stats) > 0
        func_stat = next((s for s in stats if s.get("name") == "test_func"), None)
        assert func_stat is not None
        assert func_stat.get("total_calls") == 2

    def test_start_stop_profiling(self, profiler):
        """测试开始和停止分析。"""
        profiler.start_profiling()
        time.sleep(0.01)
        result = profiler.stop_profiling()

        assert result is not None

    def test_take_memory_snapshot(self, profiler):
        """测试内存快照。"""
        snapshot = profiler.take_memory_snapshot()

        assert snapshot is not None
        assert snapshot.current_memory_mb > 0

    def test_get_memory_snapshots(self, profiler):
        """测试获取内存快照列表。"""
        profiler.take_memory_snapshot()
        profiler.take_memory_snapshot()

        snapshots = profiler.get_memory_snapshots()

        assert len(snapshots) >= 2

    def test_clear_profiler(self, profiler):
        """测试清空分析器数据。"""
        profiler.record_function_call("test_func", 0.1)
        profiler.take_memory_snapshot()

        profiler.clear()

        stats = profiler.get_function_stats()
        snapshots = profiler.get_memory_snapshots()

        assert len(stats) == 0
        assert len(snapshots) == 0


class TestSystemMonitor:
    """系统监控器测试。"""

    @pytest.fixture
    def monitor(self):
        """创建系统监控器。"""
        return SystemMonitor()

    def test_monitor_initialization(self, monitor):
        """测试监控器初始化。"""
        assert monitor is not None

    def test_get_cpu_percent(self, monitor):
        """测试获取CPU使用率。"""
        cpu_percent = monitor.get_cpu_percent(interval=0.0)

        assert isinstance(cpu_percent, float)
        assert 0 <= cpu_percent <= 100

    def test_get_memory_info(self, monitor):
        """测试获取内存信息。"""
        mem_info = monitor.get_memory_info()

        assert "total_mb" in mem_info
        assert "available_mb" in mem_info
        assert "used_mb" in mem_info
        assert "percent" in mem_info

    def test_get_disk_info(self, monitor):
        """测试获取磁盘信息。"""
        disk_info = monitor.get_disk_info()

        assert isinstance(disk_info, dict)

    def test_get_process_info(self, monitor):
        """测试获取进程信息。"""
        proc_info = monitor.get_process_info()

        assert "memory_mb" in proc_info
        assert "cpu_percent" in proc_info

    def test_collect_metrics(self, monitor):
        """测试收集指标。"""
        metrics = monitor.collect_metrics()

        assert isinstance(metrics, list)
        assert len(metrics) > 0


class TestFunctionProfile:
    """函数性能配置测试。"""

    def test_function_profile_creation(self):
        """测试函数性能配置创建。"""
        profile = FunctionProfile(
            name="test_func",
            total_calls=10,
            total_time=1.0,
            avg_time=0.1,
            min_time=0.05,
            max_time=0.2,
        )

        assert profile.name == "test_func"
        assert profile.total_calls == 10
        assert profile.avg_time == 0.1

    def test_function_profile_to_dict(self):
        """测试函数性能配置转换为字典。"""
        profile = FunctionProfile(
            name="test_func",
            total_calls=10,
            total_time=1.0,
            avg_time=0.1,
            min_time=0.05,
            max_time=0.2,
        )

        data = profile.to_dict()

        assert data["name"] == "test_func"
        assert data["total_calls"] == 10
        assert data["avg_time"] == 0.1


class TestMemorySnapshot:
    """内存快照测试。"""

    def test_memory_snapshot_creation(self):
        """测试内存快照创建。"""
        snapshot = MemorySnapshot(
            current_memory_mb=100.0,
            peak_memory_mb=150.0,
            memory_blocks=[],
            top_allocations=[],
        )

        assert snapshot.current_memory_mb == 100.0
        assert snapshot.peak_memory_mb == 150.0


class TestPerformanceReport:
    """性能报告测试。"""

    def test_report_creation(self):
        """测试报告创建。"""
        report = PerformanceReport()

        assert report is not None

    def test_add_section(self):
        """测试添加章节。"""
        report = PerformanceReport()
        report.add_section("Test Section", {"key": "value"})

        assert "Test Section" in report.sections

    def test_generate_full_report(self):
        """测试生成完整报告。"""
        report = PerformanceReport()
        report.add_section("System", {"cpu": 50.0})
        report.add_section("Functions", {"count": 10})

        full_report = report.generate_full_report()

        assert "System" in full_report
        assert "Functions" in full_report

    def test_generate_html(self):
        """测试生成HTML。"""
        report = PerformanceReport()
        report.add_section("System", {"cpu": 50.0})

        html = report.generate_html()

        assert "<html" in html.lower() or "<!doctype" in html.lower()


class TestProfileDecorator:
    """性能分析装饰器测试。"""

    def test_profile_decorator(self, profiler):
        """测试性能分析装饰器。"""
        set_profiler(profiler)

        @profiler.profile
        def test_function():
            time.sleep(0.01)
            return "result"

        result = test_function()

        assert result == "result"

        # 验证函数被记录
        stats = profiler.get_function_stats()
        func_stat = next((s for s in stats if "test_function" in s.get("name", "")), None)
        assert func_stat is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
