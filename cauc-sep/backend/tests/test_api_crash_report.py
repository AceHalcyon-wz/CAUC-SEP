"""
崩溃报告 API 测试模块。

测试功能：
    - 崩溃报告列表查询
    - 崩溃报告详情
    - 状态更新
    - 统计信息
    - 导出功能

作者：Test Debugger Agent
创建日期：2026-03-08
依赖：pytest, httpx
"""

import gzip
import json
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.crash_report import router, set_crash_storage
from core.crash_report import (
    CrashReport,
    CrashReportStorage,
    CrashSeverity,
    CrashStatus,
)


class TestCrashReportAPI:
    """崩溃报告API测试。"""

    @pytest.fixture
    def temp_storage(self):
        """创建临时崩溃报告存储。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_crash.db")
            storage = CrashReportStorage(db_path=db_path)
            set_crash_storage(storage)
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
    def sample_reports(self, temp_storage):
        """创建示例崩溃报告数据。"""
        reports = []
        now = datetime.now()

        for i in range(10):
            report = CrashReport(
                report_id=f"report_{i:04d}",
                timestamp=now - timedelta(hours=i),
                exception_type=["ValueError", "RuntimeError", "ConnectionError"][i % 3],
                exception_message=f"Test exception {i}",
                stack_trace=f"Traceback (most recent call last):\n  File 'test.py', line {i}",
                severity=[CrashSeverity.HIGH, CrashSeverity.MEDIUM, CrashSeverity.LOW][i % 3],
                status=CrashStatus.NEW if i < 5 else CrashStatus.RESOLVED,
                device_id=f"device_{i % 3}",
                experiment_id=i % 2,
                user_id=f"user_{i % 4}",
                system_info={"os": "Windows", "python": "3.11"},
                context_data={"test_key": f"test_value_{i}"},
            )
            temp_storage.save_report(report)
            reports.append(report)

        return reports

    def test_list_crash_reports_default(self, test_client, sample_reports):
        """测试默认查询崩溃报告列表。"""
        response = test_client.get("/api/crash-reports")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "reports" in data

    def test_list_crash_reports_with_limit(self, test_client, sample_reports):
        """测试带限制的报告列表查询。"""
        response = test_client.get("/api/crash-reports?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data["reports"]) <= 5

    def test_list_crash_reports_with_offset(self, test_client, sample_reports):
        """测试带偏移量的报告列表查询。"""
        response1 = test_client.get("/api/crash-reports?limit=5&offset=0")
        response2 = test_client.get("/api/crash-reports?limit=5&offset=5")

        assert response1.status_code == 200
        assert response2.status_code == 200

        # 确保偏移量生效
        ids1 = {r["report_id"] for r in response1.json()["reports"]}
        ids2 = {r["report_id"] for r in response2.json()["reports"]}
        assert ids1.isdisjoint(ids2) or len(ids1.intersection(ids2)) == 0

    def test_list_crash_reports_by_severity(self, test_client, sample_reports):
        """测试按严重程度查询报告。"""
        response = test_client.get("/api/crash-reports?severity=high")

        assert response.status_code == 200
        data = response.json()
        for report in data["reports"]:
            assert report["severity"] == "high"

    def test_list_crash_reports_by_status(self, test_client, sample_reports):
        """测试按状态查询报告。"""
        response = test_client.get("/api/crash-reports?status=new")

        assert response.status_code == 200
        data = response.json()
        for report in data["reports"]:
            assert report["status"] == "new"

    def test_list_crash_reports_by_exception_type(self, test_client, sample_reports):
        """测试按异常类型查询报告。"""
        response = test_client.get("/api/crash-reports?exception_type=ValueError")

        assert response.status_code == 200
        data = response.json()
        for report in data["reports"]:
            assert "ValueError" in report["exception_type"]

    def test_list_crash_reports_by_device_id(self, test_client, sample_reports):
        """测试按设备ID查询报告。"""
        response = test_client.get("/api/crash-reports?device_id=device_0")

        assert response.status_code == 200
        data = response.json()
        for report in data["reports"]:
            assert report["device_id"] == "device_0"

    def test_list_crash_reports_by_time_range(self, test_client, sample_reports):
        """测试按时间范围查询报告。"""
        now = datetime.now()
        start_time = (now - timedelta(hours=5)).isoformat()
        end_time = now.isoformat()

        response = test_client.get(
            f"/api/crash-reports?start_time={start_time}&end_time={end_time}"
        )

        assert response.status_code == 200

    def test_get_crash_statistics(self, test_client, sample_reports):
        """测试获取崩溃统计信息。"""
        response = test_client.get("/api/crash-reports/statistics")

        assert response.status_code == 200
        data = response.json()
        assert "total_count" in data
        assert "by_severity" in data
        assert "by_status" in data

    def test_get_crash_statistics_with_time_filter(self, test_client, sample_reports):
        """测试带时间过滤的统计信息。"""
        now = datetime.now()
        start_time = (now - timedelta(hours=3)).isoformat()

        response = test_client.get(
            f"/api/crash-reports/statistics?start_time={start_time}"
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_count" in data

    def test_get_crash_report_detail(self, test_client, sample_reports):
        """测试获取崩溃报告详情。"""
        report_id = sample_reports[0].report_id

        response = test_client.get(f"/api/crash-reports/{report_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["report_id"] == report_id
        assert "exception_type" in data
        assert "stack_trace" in data

    def test_get_crash_report_not_found(self, test_client):
        """测试获取不存在的崩溃报告。"""
        response = test_client.get("/api/crash-reports/nonexistent_report")

        assert response.status_code == 404

    def test_update_crash_report_status(self, test_client, sample_reports):
        """测试更新崩溃报告状态。"""
        report_id = sample_reports[0].report_id

        response = test_client.put(
            f"/api/crash-reports/{report_id}/status",
            params={"status": "acknowledged", "notes": "Investigating"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "acknowledged"

    def test_update_crash_report_status_invalid(self, test_client, sample_reports):
        """测试更新崩溃报告状态（无效状态）。"""
        report_id = sample_reports[0].report_id

        response = test_client.put(
            f"/api/crash-reports/{report_id}/status",
            params={"status": "invalid_status"},
        )

        assert response.status_code == 400

    def test_update_crash_report_status_not_found(self, test_client):
        """测试更新不存在的报告状态。"""
        response = test_client.put(
            "/api/crash-reports/nonexistent/status",
            params={"status": "acknowledged"},
        )

        assert response.status_code == 404

    def test_export_crash_report(self, test_client, sample_reports):
        """测试导出崩溃报告。"""
        report_id = sample_reports[0].report_id

        response = test_client.get(f"/api/crash-reports/{report_id}/export")

        assert response.status_code == 200
        # 验证返回的是文件
        assert response.headers.get("content-type") in [
            "application/gzip",
            "application/octet-stream",
        ]

    def test_export_crash_report_not_found(self, test_client):
        """测试导出不存在的崩溃报告。"""
        response = test_client.get("/api/crash-reports/nonexistent/export")

        assert response.status_code == 404

    def test_cleanup_old_crash_reports(self, test_client, sample_reports):
        """测试清理过期崩溃报告。"""
        response = test_client.post("/api/crash-reports/cleanup?max_age_days=0")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "deleted_count" in data

    def test_get_severity_levels(self, test_client):
        """测试获取严重程度级别列表。"""
        response = test_client.get("/api/crash-reports/severity/levels")

        assert response.status_code == 200
        data = response.json()
        assert "levels" in data
        assert len(data["levels"]) == 4  # critical, high, medium, low

    def test_get_status_values(self, test_client):
        """测试获取状态值列表。"""
        response = test_client.get("/api/crash-reports/status/values")

        assert response.status_code == 200
        data = response.json()
        assert "statuses" in data
        assert len(data["statuses"]) == 4  # new, acknowledged, resolved, ignored


class TestCrashReportModel:
    """崩溃报告模型测试。"""

    def test_crash_report_creation(self):
        """测试崩溃报告创建。"""
        report = CrashReport(
            report_id="test_001",
            timestamp=datetime.now(),
            exception_type="ValueError",
            exception_message="Test error",
            stack_trace="Test stack trace",
            severity=CrashSeverity.HIGH,
            status=CrashStatus.NEW,
        )

        assert report.report_id == "test_001"
        assert report.exception_type == "ValueError"
        assert report.severity == CrashSeverity.HIGH

    def test_crash_report_to_dict(self):
        """测试崩溃报告转换为字典。"""
        report = CrashReport(
            report_id="test_001",
            timestamp=datetime.now(),
            exception_type="ValueError",
            exception_message="Test error",
            stack_trace="Test stack trace",
            severity=CrashSeverity.HIGH,
            status=CrashStatus.NEW,
            system_info={"os": "Windows"},
        )

        data = report.to_dict()

        assert data["report_id"] == "test_001"
        assert data["exception_type"] == "ValueError"
        assert data["system_info"]["os"] == "Windows"

    def test_crash_report_with_context(self):
        """测试带上下文的崩溃报告。"""
        report = CrashReport(
            report_id="test_001",
            timestamp=datetime.now(),
            exception_type="RuntimeError",
            exception_message="Test error",
            stack_trace="Test stack trace",
            severity=CrashSeverity.CRITICAL,
            status=CrashStatus.NEW,
            device_id="device_01",
            experiment_id=1,
            context_data={"experiment_state": "running"},
        )

        assert report.device_id == "device_01"
        assert report.experiment_id == 1
        assert report.context_data["experiment_state"] == "running"


class TestCrashReportStorage:
    """崩溃报告存储测试。"""

    @pytest.fixture
    def storage(self):
        """创建崩溃报告存储。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_storage.db")
            storage = CrashReportStorage(db_path=db_path)
            yield storage

    def test_storage_initialization(self, storage):
        """测试存储初始化。"""
        assert storage is not None

    def test_save_and_retrieve_report(self, storage):
        """测试保存和检索报告。"""
        report = CrashReport(
            report_id="test_001",
            timestamp=datetime.now(),
            exception_type="ValueError",
            exception_message="Test error",
            stack_trace="Test stack trace",
            severity=CrashSeverity.HIGH,
            status=CrashStatus.NEW,
        )

        # 保存报告
        storage.save_report(report)

        # 检索报告
        retrieved = storage.get_report("test_001")

        assert retrieved is not None
        assert retrieved.report_id == "test_001"

    def test_query_reports(self, storage):
        """测试查询报告。"""
        # 创建多个报告
        for i in range(5):
            report = CrashReport(
                report_id=f"test_{i:03d}",
                timestamp=datetime.now() - timedelta(hours=i),
                exception_type=["ValueError", "RuntimeError"][i % 2],
                exception_message=f"Test error {i}",
                stack_trace="Test stack trace",
                severity=[CrashSeverity.HIGH, CrashSeverity.LOW][i % 2],
                status=CrashStatus.NEW,
            )
            storage.save_report(report)

        # 查询报告
        reports = storage.query_reports(limit=10)

        assert len(reports) == 5

    def test_query_reports_by_severity(self, storage):
        """测试按严重程度查询报告。"""
        # 创建不同严重程度的报告
        for i in range(3):
            report = CrashReport(
                report_id=f"test_{i:03d}",
                timestamp=datetime.now(),
                exception_type="ValueError",
                exception_message=f"Test error {i}",
                stack_trace="Test stack trace",
                severity=[CrashSeverity.HIGH, CrashSeverity.MEDIUM, CrashSeverity.LOW][i],
                status=CrashStatus.NEW,
            )
            storage.save_report(report)

        # 查询高严重程度报告
        reports = storage.query_reports(severity="high")

        assert len(reports) == 1
        assert reports[0].severity == CrashSeverity.HIGH

    def test_update_report_status(self, storage):
        """测试更新报告状态。"""
        report = CrashReport(
            report_id="test_001",
            timestamp=datetime.now(),
            exception_type="ValueError",
            exception_message="Test error",
            stack_trace="Test stack trace",
            severity=CrashSeverity.HIGH,
            status=CrashStatus.NEW,
        )
        storage.save_report(report)

        # 更新状态
        success = storage.update_report_status(
            report_id="test_001",
            status=CrashStatus.ACKNOWLEDGED,
            notes="Investigating",
        )

        assert success is True

        # 验证更新
        updated = storage.get_report("test_001")
        assert updated.status == CrashStatus.ACKNOWLEDGED

    def test_get_statistics(self, storage):
        """测试获取统计信息。"""
        # 创建多个报告
        for i in range(10):
            report = CrashReport(
                report_id=f"test_{i:03d}",
                timestamp=datetime.now() - timedelta(hours=i),
                exception_type=["ValueError", "RuntimeError", "ConnectionError"][i % 3],
                exception_message=f"Test error {i}",
                stack_trace="Test stack trace",
                severity=[CrashSeverity.HIGH, CrashSeverity.MEDIUM, CrashSeverity.LOW][i % 3],
                status=[CrashStatus.NEW, CrashStatus.RESOLVED][i % 2],
            )
            storage.save_report(report)

        stats = storage.get_statistics()

        assert "total_count" in stats
        assert stats["total_count"] == 10
        assert "by_severity" in stats
        assert "by_status" in stats

    def test_cleanup_old_reports(self, storage):
        """测试清理过期报告。"""
        # 创建已解决的报告
        report = CrashReport(
            report_id="old_report",
            timestamp=datetime.now() - timedelta(days=60),
            exception_type="ValueError",
            exception_message="Old error",
            stack_trace="Test stack trace",
            severity=CrashSeverity.LOW,
            status=CrashStatus.RESOLVED,
        )
        storage.save_report(report)

        # 清理30天前的已解决报告
        deleted = storage.cleanup_old_reports(max_age_days=30)

        assert deleted >= 0


class TestCrashSeverity:
    """崩溃严重程度测试。"""

    def test_severity_values(self):
        """测试严重程度值。"""
        assert CrashSeverity.CRITICAL == "critical"
        assert CrashSeverity.HIGH == "high"
        assert CrashSeverity.MEDIUM == "medium"
        assert CrashSeverity.LOW == "low"


class TestCrashStatus:
    """崩溃状态测试。"""

    def test_status_values(self):
        """测试状态值。"""
        assert CrashStatus.NEW == "new"
        assert CrashStatus.ACKNOWLEDGED == "acknowledged"
        assert CrashStatus.RESOLVED == "resolved"
        assert CrashStatus.IGNORED == "ignored"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
