"""
崩溃报告系统测试模块。

测试崩溃报告的生成、存储、查询和清理功能。

作者：Backend Engineer Agent
创建日期：2026-03-07
"""

import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from core.crash_report import (
    CrashReport,
    CrashReportManager,
    CrashReportStorage,
    CrashSeverity,
    CrashStatus,
    SystemInfo,
    capture_crashes,
    get_crash_report_manager,
    init_crash_report_manager,
)


class TestSystemInfo:
    """系统信息收集测试。"""

    def test_collect_system_info(self):
        """测试系统信息收集。"""
        info = SystemInfo.collect(
            app_start_time=time.time() - 100,
            app_version="0.3.0",
        )

        assert info.python_version != ""
        assert info.platform_system != ""
        assert info.cpu_count > 0
        assert info.memory_total_mb > 0
        assert info.process_id > 0
        assert info.app_version == "0.3.0"
        assert info.uptime_seconds >= 100

    def test_system_info_to_dict(self):
        """测试系统信息转换为字典。"""
        info = SystemInfo(
            python_version="3.11.0",
            platform_system="Windows",
            cpu_count=8,
            memory_total_mb=16384.0,
        )

        data = info.to_dict()

        assert data["python_version"] == "3.11.0"
        assert data["platform_system"] == "Windows"
        assert data["cpu_count"] == 8
        assert data["memory_total_mb"] == 16384.0


class TestCrashReport:
    """崩溃报告测试。"""

    def test_crash_report_creation(self):
        """测试崩溃报告创建。"""
        report = CrashReport(
            severity=CrashSeverity.HIGH,
            exception_type="ValueError",
            exception_message="Invalid parameter",
            exception_traceback="Traceback...",
        )

        assert report.report_id != ""
        assert report.timestamp is not None
        assert report.severity == CrashSeverity.HIGH
        assert report.status == CrashStatus.NEW
        assert report.exception_type == "ValueError"

    def test_crash_report_to_dict(self):
        """测试崩溃报告转换为字典。"""
        report = CrashReport(
            report_id="test123",
            severity=CrashSeverity.MEDIUM,
            exception_type="KeyError",
            exception_message="Key not found",
            tags=["test", "unit"],
        )

        data = report.to_dict()

        assert data["report_id"] == "test123"
        assert data["severity"] == CrashSeverity.MEDIUM
        assert data["exception_type"] == "KeyError"
        assert data["tags"] == ["test", "unit"]


class TestCrashReportStorage:
    """崩溃报告存储测试。"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库。"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        # Windows上需要确保数据库连接关闭后才能删除文件
        import time

        time.sleep(0.1)
        try:
            Path(db_path).unlink(missing_ok=True)
        except PermissionError:
            # 文件仍被锁定，忽略清理
            pass

    def test_save_and_get_report(self, temp_db):
        """测试保存和获取崩溃报告。"""
        storage = CrashReportStorage(db_path=temp_db)

        report = CrashReport(
            severity=CrashSeverity.HIGH,
            exception_type="RuntimeError",
            exception_message="Test error",
            exception_traceback="Test traceback",
        )

        # 保存报告
        saved_report = storage.save_report(report)
        assert saved_report.report_id == report.report_id

        # 获取报告
        retrieved = storage.get_report(report.report_id)
        assert retrieved is not None
        assert retrieved.exception_type == "RuntimeError"
        assert retrieved.exception_message == "Test error"

        # 关闭数据库连接
        storage.close()

    def test_query_reports(self, temp_db):
        """测试查询崩溃报告。"""
        storage = CrashReportStorage(db_path=temp_db)

        # 创建多个报告
        for i in range(5):
            report = CrashReport(
                severity=CrashSeverity.HIGH if i < 3 else CrashSeverity.LOW,
                exception_type=f"Exception{i}",
                exception_message=f"Error {i}",
            )
            storage.save_report(report)

        # 查询高严重程度报告
        reports = storage.query_reports(severity=CrashSeverity.HIGH)
        assert len(reports) == 3

        # 查询所有报告
        all_reports = storage.query_reports()
        assert len(all_reports) == 5

        # 关闭数据库连接
        storage.close()

    def test_update_report_status(self, temp_db):
        """测试更新崩溃报告状态。"""
        storage = CrashReportStorage(db_path=temp_db)

        report = CrashReport(
            severity=CrashSeverity.HIGH,
            exception_type="TestError",
            exception_message="Test",
        )
        storage.save_report(report)

        # 更新状态
        success = storage.update_report_status(
            report_id=report.report_id,
            status=CrashStatus.ACKNOWLEDGED,
            notes="Investigating",
        )
        assert success is True

        # 验证更新
        updated = storage.get_report(report.report_id)
        assert updated.status == CrashStatus.ACKNOWLEDGED
        assert updated.notes == "Investigating"

        # 关闭数据库连接
        storage.close()

    def test_get_statistics(self, temp_db):
        """测试获取统计信息。"""
        storage = CrashReportStorage(db_path=temp_db)

        # 创建不同严重程度的报告
        for severity in [CrashSeverity.CRITICAL, CrashSeverity.HIGH, CrashSeverity.MEDIUM]:
            report = CrashReport(
                severity=severity,
                exception_type="TestError",
                exception_message="Test",
            )
            storage.save_report(report)

        stats = storage.get_statistics()

        assert stats["total_reports"] == 3
        assert stats["by_severity"][CrashSeverity.CRITICAL] == 1
        assert stats["by_severity"][CrashSeverity.HIGH] == 1
        assert stats["by_severity"][CrashSeverity.MEDIUM] == 1

        # 关闭数据库连接
        storage.close()

    def test_cleanup_old_reports(self, temp_db):
        """测试清理过期报告。"""
        storage = CrashReportStorage(db_path=temp_db)

        # 创建已解决的报告
        report1 = CrashReport(
            severity=CrashSeverity.HIGH,
            exception_type="TestError",
            exception_message="Test",
        )
        storage.save_report(report1)
        storage.update_report_status(report1.report_id, CrashStatus.RESOLVED)

        # 创建新报告
        report2 = CrashReport(
            severity=CrashSeverity.HIGH,
            exception_type="TestError",
            exception_message="Test",
        )
        storage.save_report(report2)

        # 清理（保留1天，由于报告都是新的，不会删除）
        deleted = storage.cleanup_old_reports(max_age_days=1)
        assert deleted == 0

        # 验证报告仍然存在
        all_reports = storage.query_reports()
        assert len(all_reports) == 2

        # 关闭数据库连接
        storage.close()

    def test_export_report(self, temp_db):
        """测试导出崩溃报告。"""
        storage = CrashReportStorage(db_path=temp_db)

        report = CrashReport(
            severity=CrashSeverity.HIGH,
            exception_type="TestError",
            exception_message="Test",
        )
        storage.save_report(report)

        # 导出报告
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = storage.export_report(report.report_id, output_dir=temp_dir)
            assert filepath is not None
            assert Path(filepath).exists()
            assert filepath.endswith(".json.gz")

        # 关闭数据库连接
        storage.close()


class TestCrashReportManager:
    """崩溃报告管理器测试。"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库。"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        # Windows上需要等待文件释放
        import time

        time.sleep(0.1)
        try:
            Path(db_path).unlink(missing_ok=True)
        except PermissionError:
            pass

    def test_capture_exception(self, temp_db):
        """测试捕获异常。"""
        manager = CrashReportManager(
            app_start_time=time.time(),
            app_version="0.3.0",
            db_path=temp_db,
        )

        try:
            raise ValueError("Test exception")
        except Exception:
            report = manager.capture_exception(
                severity=CrashSeverity.MEDIUM,
                context_data={"test": "value"},
            )

        assert report.exception_type == "ValueError"
        assert report.exception_message == "Test exception"
        assert report.severity == CrashSeverity.MEDIUM
        assert report.context_data == {"test": "value"}

        # 关闭管理器
        manager.close()

    def test_determine_severity(self, temp_db):
        """测试判断严重程度。"""
        manager = CrashReportManager(
            app_start_time=time.time(),
            app_version="0.3.0",
            db_path=temp_db,
        )

        # 测试致命错误
        assert manager._determine_severity(MemoryError()) == CrashSeverity.CRITICAL

        # 测试严重错误
        assert manager._determine_severity(OSError()) == CrashSeverity.HIGH
        assert manager._determine_severity(ConnectionError()) == CrashSeverity.HIGH

        # 测试中等错误
        assert manager._determine_severity(ValueError()) == CrashSeverity.MEDIUM
        assert manager._determine_severity(KeyError()) == CrashSeverity.MEDIUM

        # 测试轻微错误
        assert manager._determine_severity(Exception()) == CrashSeverity.LOW

        # 关闭管理器
        manager.close()


class TestCaptureCrashesDecorator:
    """崩溃捕获装饰器测试。"""

    @pytest.fixture
    def temp_db(self):
        """创建临时数据库。"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        # Windows上需要等待文件释放
        import time

        time.sleep(0.1)
        try:
            Path(db_path).unlink(missing_ok=True)
        except PermissionError:
            pass

    def test_capture_crashes_sync(self, temp_db):
        """测试同步函数崩溃捕获。"""
        manager = init_crash_report_manager(
            app_start_time=time.time(),
            app_version="0.3.0",
            db_path=temp_db,
            install_hook=False,
        )

        @capture_crashes(severity=CrashSeverity.HIGH, reraise=False)
        def risky_function():
            raise RuntimeError("Test error")

        # 执行函数（不会抛出异常）
        result = risky_function()
        assert result is None

        # 验证崩溃报告已创建
        storage = get_crash_report_manager().storage
        reports = storage.query_reports()
        assert len(reports) == 1
        assert reports[0]["exception_type"] == "RuntimeError"

        # 关闭管理器
        manager.close()

    @pytest.mark.asyncio
    async def test_capture_crashes_async(self, temp_db):
        """测试异步函数崩溃捕获。"""
        manager = init_crash_report_manager(
            app_start_time=time.time(),
            app_version="0.3.0",
            db_path=temp_db,
            install_hook=False,
        )

        @capture_crashes(severity=CrashSeverity.HIGH, reraise=False)
        async def async_risky_function():
            raise RuntimeError("Async test error")

        # 执行函数（不会抛出异常）
        result = await async_risky_function()
        assert result is None

        # 验证崩溃报告已创建
        storage = get_crash_report_manager().storage
        reports = storage.query_reports()
        assert len(reports) == 1
        assert reports[0]["exception_type"] == "RuntimeError"

        # 关闭管理器
        manager.close()

    def test_capture_crashes_reraise(self, temp_db):
        """测试崩溃捕获后重新抛出异常。"""
        manager = init_crash_report_manager(
            app_start_time=time.time(),
            app_version="0.3.0",
            db_path=temp_db,
            install_hook=False,
        )

        @capture_crashes(severity=CrashSeverity.HIGH, reraise=True)
        def risky_function():
            raise RuntimeError("Test error")

        # 执行函数（会抛出异常）
        with pytest.raises(RuntimeError, match="Test error"):
            risky_function()

        # 验证崩溃报告已创建
        storage = get_crash_report_manager().storage
        reports = storage.query_reports()
        assert len(reports) == 1

        # 关闭管理器
        manager.close()


class TestGlobalManager:
    """全局管理器测试。"""

    def test_init_and_get_manager(self):
        """测试初始化和获取全局管理器。"""
        import time as time_module

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            manager = init_crash_report_manager(
                app_start_time=time_module.time(),
                app_version="0.3.0",
                db_path=db_path,
                install_hook=False,
            )

            # 验证全局实例
            retrieved = get_crash_report_manager()
            assert retrieved is manager

            # 关闭数据库连接
            if manager.storage:
                manager.storage.close()

        finally:
            # Windows上需要等待文件释放
            time_module.sleep(0.2)
            try:
                Path(db_path).unlink(missing_ok=True)
            except PermissionError:
                pass
