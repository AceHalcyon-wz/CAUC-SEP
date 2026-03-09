"""
崩溃报告收集与管理核心模块。

实现完整的崩溃报告系统，支持异常捕获、报告生成、本地存储和上传机制。

功能：
    - 全局异常捕获与报告生成
    - 崩溃报告本地持久化存储
    - 崩溃报告上传机制（可选）
    - 崩溃报告查询与统计
    - 自动清理过期报告

技术栈：
    - Python 3.11+
    - SQLite 持久化存储
    - FastAPI 集成

作者：Backend Engineer Agent
创建日期：2026-03-07
依赖：sqlalchemy, pydantic, fastapi, psutil
"""

import functools
import gzip
import json
import logging
import os
import platform
import sys
import time
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional

import psutil
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# 崩溃报告数据模型
# ============================================================================


class CrashSeverity(str):
    """崩溃严重程度枚举。"""

    CRITICAL = "critical"  # 致命错误，系统无法继续运行
    HIGH = "high"  # 严重错误，影响核心功能
    MEDIUM = "medium"  # 中等错误，影响部分功能
    LOW = "low"  # 轻微错误，不影响核心功能


class CrashStatus(str):
    """崩溃报告状态枚举。"""

    NEW = "new"  # 新报告，未处理
    ACKNOWLEDGED = "acknowledged"  # 已确认，待处理
    RESOLVED = "resolved"  # 已解决
    IGNORED = "ignored"  # 已忽略


@dataclass
class SystemInfo:
    """系统信息数据结构。

    收集崩溃发生时的系统环境信息，用于问题诊断。

    Attributes:
        python_version: Python版本
        platform_system: 操作系统类型
        platform_release: 操作系统版本
        platform_version: 操作系统详细版本
        architecture: 系统架构
        cpu_count: CPU核心数
        memory_total_mb: 总内存（MB）
        memory_available_mb: 可用内存（MB）
        disk_total_gb: 磁盘总空间（GB）
        disk_free_gb: 磁盘可用空间（GB）
        hostname: 主机名
        process_id: 进程ID
        process_memory_mb: 进程内存使用（MB）
        process_cpu_percent: 进程CPU使用率
        app_version: 应用版本
        uptime_seconds: 应用运行时长（秒）
    """

    python_version: str = ""
    platform_system: str = ""
    platform_release: str = ""
    platform_version: str = ""
    architecture: str = ""
    cpu_count: int = 0
    memory_total_mb: float = 0.0
    memory_available_mb: float = 0.0
    disk_total_gb: float = 0.0
    disk_free_gb: float = 0.0
    hostname: str = ""
    process_id: int = 0
    process_memory_mb: float = 0.0
    process_cpu_percent: float = 0.0
    app_version: str = "0.3.0"
    uptime_seconds: float = 0.0

    @classmethod
    def collect(cls, app_start_time: float, app_version: str = "0.3.0") -> "SystemInfo":
        """收集当前系统信息。

        Args:
            app_start_time: 应用启动时间戳
            app_version: 应用版本号

        Returns:
            SystemInfo: 系统信息实例
        """
        try:
            process = psutil.Process()

            # 内存信息
            memory = psutil.virtual_memory()

            # 磁盘信息
            try:
                disk = psutil.disk_usage("/")
            except Exception:
                disk = psutil.disk_usage("C:\\")

            return cls(
                python_version=platform.python_version(),
                platform_system=platform.system(),
                platform_release=platform.release(),
                platform_version=platform.version(),
                architecture=platform.machine(),
                cpu_count=psutil.cpu_count(logical=True),
                memory_total_mb=round(memory.total / (1024 ** 2), 2),
                memory_available_mb=round(memory.available / (1024 ** 2), 2),
                disk_total_gb=round(disk.total / (1024 ** 3), 2),
                disk_free_gb=round(disk.free / (1024 ** 3), 2),
                hostname=platform.node(),
                process_id=process.pid,
                process_memory_mb=round(process.memory_info().rss / (1024 ** 2), 2),
                process_cpu_percent=round(process.cpu_percent(interval=0.1), 2),
                app_version=app_version,
                uptime_seconds=round(time.time() - app_start_time, 2),
            )
        except Exception as e:
            logger.warning(f"Failed to collect system info: {e}")
            return cls()

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式。

        Returns:
            dict: 系统信息字典
        """
        return {
            "python_version": self.python_version,
            "platform_system": self.platform_system,
            "platform_release": self.platform_release,
            "platform_version": self.platform_version,
            "architecture": self.architecture,
            "cpu_count": self.cpu_count,
            "memory_total_mb": self.memory_total_mb,
            "memory_available_mb": self.memory_available_mb,
            "disk_total_gb": self.disk_total_gb,
            "disk_free_gb": self.disk_free_gb,
            "hostname": self.hostname,
            "process_id": self.process_id,
            "process_memory_mb": self.process_memory_mb,
            "process_cpu_percent": self.process_cpu_percent,
            "app_version": self.app_version,
            "uptime_seconds": self.uptime_seconds,
        }


@dataclass
class CrashReport:
    """崩溃报告数据结构。

    完整的崩溃报告，包含异常信息、系统环境、上下文数据等。

    Attributes:
        report_id: 报告唯一标识
        timestamp: 崩溃发生时间
        severity: 严重程度
        status: 报告状态
        exception_type: 异常类型
        exception_message: 异常消息
        exception_traceback: 异常堆栈
        exception_module: 异常所在模块
        exception_function: 异常所在函数
        exception_line: 异常所在行号
        system_info: 系统信息
        context_data: 上下文数据（请求信息、用户信息等）
        device_id: 相关设备ID（可选）
        experiment_id: 相关实验ID（可选）
        user_id: 相关用户ID（可选）
        tags: 标签列表
        notes: 处理备注
        resolved_at: 解决时间（可选）
        resolved_by: 解决人（可选）
    """

    report_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: datetime = field(default_factory=datetime.now)
    severity: str = CrashSeverity.HIGH
    status: str = CrashStatus.NEW
    exception_type: str = ""
    exception_message: str = ""
    exception_traceback: str = ""
    exception_module: str = ""
    exception_function: str = ""
    exception_line: int = 0
    system_info: SystemInfo = field(default_factory=SystemInfo)
    context_data: dict[str, Any] = field(default_factory=dict)
    device_id: Optional[str] = None
    experiment_id: Optional[int] = None
    user_id: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式。

        Returns:
            dict: 崩溃报告字典
        """
        return {
            "report_id": self.report_id,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity,
            "status": self.status,
            "exception_type": self.exception_type,
            "exception_message": self.exception_message,
            "exception_traceback": self.exception_traceback,
            "exception_module": self.exception_module,
            "exception_function": self.exception_function,
            "exception_line": self.exception_line,
            "system_info": self.system_info.to_dict(),
            "context_data": self.context_data,
            "device_id": self.device_id,
            "experiment_id": self.experiment_id,
            "user_id": self.user_id,
            "tags": self.tags,
            "notes": self.notes,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
        }


# ============================================================================
# 崩溃报告存储
# ============================================================================


class CrashReportStorage:
    """崩溃报告持久化存储。

    使用SQLite数据库存储崩溃报告，支持查询、统计和清理。

    Example:
        >>> storage = CrashReportStorage(db_path="crash_reports.db")
        >>> report = storage.save_report(crash_report)
        >>> reports = storage.query_reports(severity="high")
    """

    def __init__(self, db_path: str = "crash_reports.db"):
        """初始化崩溃报告存储。

        Args:
            db_path: 数据库文件路径
        """
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )

        # 创建表
        self._create_tables()

        self.Session = sessionmaker(bind=self.engine)
        logger.info(f"CrashReportStorage initialized: {db_path}")

    def _create_tables(self) -> None:
        """创建数据库表。"""
        from sqlalchemy import Column, DateTime, Integer, String, Text
        from sqlalchemy.ext.declarative import declarative_base

        Base = declarative_base()

        class CrashReportRecord(Base):
            """崩溃报告记录表。"""

            __tablename__ = "crash_reports"

            id = Column(Integer, primary_key=True, autoincrement=True)
            report_id = Column(String(32), unique=True, nullable=False, index=True)
            timestamp = Column(DateTime, nullable=False, index=True)
            severity = Column(String(20), nullable=False, index=True)
            status = Column(String(20), nullable=False, index=True)
            exception_type = Column(String(200), nullable=False, index=True)
            exception_message = Column(Text)
            exception_traceback = Column(Text)
            exception_module = Column(String(200))
            exception_function = Column(String(200))
            exception_line = Column(Integer)
            system_info = Column(Text)  # JSON
            context_data = Column(Text)  # JSON
            device_id = Column(String(100), index=True)
            experiment_id = Column(Integer, index=True)
            user_id = Column(String(100), index=True)
            tags = Column(Text)  # JSON
            notes = Column(Text)
            resolved_at = Column(DateTime)
            resolved_by = Column(String(100))
            created_at = Column(DateTime, default=datetime.now)

        Base.metadata.create_all(self.engine)

        self.CrashReportRecord = CrashReportRecord

    def save_report(self, report: CrashReport) -> CrashReport:
        """保存崩溃报告。

        Args:
            report: 崩溃报告对象

        Returns:
            CrashReport: 保存后的崩溃报告（包含report_id）

        Raises:
            Exception: 保存失败时抛出异常
        """
        session = self.Session()
        try:
            record = self.CrashReportRecord(
                report_id=report.report_id,
                timestamp=report.timestamp,
                severity=report.severity,
                status=report.status,
                exception_type=report.exception_type,
                exception_message=report.exception_message,
                exception_traceback=report.exception_traceback,
                exception_module=report.exception_module,
                exception_function=report.exception_function,
                exception_line=report.exception_line,
                system_info=json.dumps(report.system_info.to_dict()),
                context_data=json.dumps(report.context_data),
                device_id=report.device_id,
                experiment_id=report.experiment_id,
                user_id=report.user_id,
                tags=json.dumps(report.tags),
                notes=report.notes,
                resolved_at=report.resolved_at,
                resolved_by=report.resolved_by,
            )

            session.add(record)
            session.commit()

            logger.info(f"[CrashReport] Saved report: {report.report_id}")
            return report

        except Exception as e:
            session.rollback()
            logger.error(f"[CrashReport] Failed to save report: {e}")
            raise
        finally:
            session.close()

    def get_report(self, report_id: str) -> Optional[CrashReport]:
        """获取崩溃报告详情。

        Args:
            report_id: 报告ID

        Returns:
            Optional[CrashReport]: 崩溃报告对象，不存在时返回None
        """
        session = self.Session()
        try:
            record = (
                session.query(self.CrashReportRecord)
                .filter(self.CrashReportRecord.report_id == report_id)
                .first()
            )

            if not record:
                return None

            return self._record_to_report(record)

        finally:
            session.close()

    def query_reports(
        self,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        exception_type: Optional[str] = None,
        device_id: Optional[str] = None,
        experiment_id: Optional[int] = None,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """查询崩溃报告列表。

        Args:
            severity: 严重程度过滤（可选）
            status: 状态过滤（可选）
            exception_type: 异常类型过滤（可选）
            device_id: 设备ID过滤（可选）
            experiment_id: 实验ID过滤（可选）
            user_id: 用户ID过滤（可选）
            start_time: 开始时间过滤（可选）
            end_time: 结束时间过滤（可选）
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            list: 崩溃报告列表（简化格式）
        """
        session = self.Session()
        try:
            query = session.query(self.CrashReportRecord)

            if severity:
                query = query.filter(self.CrashReportRecord.severity == severity)
            if status:
                query = query.filter(self.CrashReportRecord.status == status)
            if exception_type:
                query = query.filter(
                    self.CrashReportRecord.exception_type.like(f"%{exception_type}%")
                )
            if device_id:
                query = query.filter(self.CrashReportRecord.device_id == device_id)
            if experiment_id:
                query = query.filter(
                    self.CrashReportRecord.experiment_id == experiment_id
                )
            if user_id:
                query = query.filter(self.CrashReportRecord.user_id == user_id)
            if start_time:
                query = query.filter(self.CrashReportRecord.timestamp >= start_time)
            if end_time:
                query = query.filter(self.CrashReportRecord.timestamp <= end_time)

            records = (
                query.order_by(self.CrashReportRecord.timestamp.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )

            return [
                {
                    "report_id": r.report_id,
                    "timestamp": r.timestamp.isoformat(),
                    "severity": r.severity,
                    "status": r.status,
                    "exception_type": r.exception_type,
                    "exception_message": r.exception_message[:200] if r.exception_message else "",
                    "exception_module": r.exception_module,
                    "exception_function": r.exception_function,
                    "device_id": r.device_id,
                    "experiment_id": r.experiment_id,
                    "user_id": r.user_id,
                    "tags": json.loads(r.tags) if r.tags else [],
                }
                for r in records
            ]

        finally:
            session.close()

    def update_report_status(
        self,
        report_id: str,
        status: str,
        notes: Optional[str] = None,
        resolved_by: Optional[str] = None,
    ) -> bool:
        """更新崩溃报告状态。

        Args:
            report_id: 报告ID
            status: 新状态
            notes: 处理备注（可选）
            resolved_by: 解决人（可选）

        Returns:
            bool: 是否更新成功
        """
        session = self.Session()
        try:
            record = (
                session.query(self.CrashReportRecord)
                .filter(self.CrashReportRecord.report_id == report_id)
                .first()
            )

            if not record:
                return False

            record.status = status
            if notes:
                record.notes = notes
            if status == CrashStatus.RESOLVED:
                record.resolved_at = datetime.now()
                record.resolved_by = resolved_by

            session.commit()
            logger.info(f"[CrashReport] Updated report {report_id} to status: {status}")
            return True

        except Exception as e:
            session.rollback()
            logger.error(f"[CrashReport] Failed to update report: {e}")
            return False
        finally:
            session.close()

    def get_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """获取崩溃报告统计信息。

        Args:
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）

        Returns:
            dict: 统计信息
        """
        session = self.Session()
        try:
            query = session.query(self.CrashReportRecord)

            if start_time:
                query = query.filter(self.CrashReportRecord.timestamp >= start_time)
            if end_time:
                query = query.filter(self.CrashReportRecord.timestamp <= end_time)

            records = query.all()

            if not records:
                return {
                    "total_reports": 0,
                    "by_severity": {},
                    "by_status": {},
                    "by_exception_type": {},
                    "recent_24h_count": 0,
                }

            # 按严重程度统计
            by_severity: dict[str, int] = {}
            for r in records:
                by_severity[r.severity] = by_severity.get(r.severity, 0) + 1

            # 按状态统计
            by_status: dict[str, int] = {}
            for r in records:
                by_status[r.status] = by_status.get(r.status, 0) + 1

            # 按异常类型统计（Top 10）
            by_exception: dict[str, int] = {}
            for r in records:
                by_exception[r.exception_type] = by_exception.get(r.exception_type, 0) + 1

            # 最近24小时数量
            recent_24h = datetime.now() - timedelta(hours=24)
            recent_24h_count = sum(1 for r in records if r.timestamp >= recent_24h)

            return {
                "total_reports": len(records),
                "by_severity": by_severity,
                "by_status": by_status,
                "by_exception_type": dict(
                    sorted(by_exception.items(), key=lambda x: x[1], reverse=True)[:10]
                ),
                "recent_24h_count": recent_24h_count,
            }

        finally:
            session.close()

    def cleanup_old_reports(self, max_age_days: int = 30) -> int:
        """清理过期崩溃报告。

        Args:
            max_age_days: 保留天数

        Returns:
            int: 删除的记录数
        """
        session = self.Session()
        try:
            cutoff_date = datetime.now() - timedelta(days=max_age_days)

            # 只删除已解决的报告
            count = (
                session.query(self.CrashReportRecord)
                .filter(
                    self.CrashReportRecord.timestamp < cutoff_date,
                    self.CrashReportRecord.status == CrashStatus.RESOLVED,
                )
                .delete()
            )

            session.commit()
            logger.info(f"[CrashReport] Cleaned up {count} old reports")
            return count

        except Exception as e:
            session.rollback()
            logger.error(f"[CrashReport] Cleanup failed: {e}")
            return 0
        finally:
            session.close()

    def export_report(self, report_id: str, output_dir: str = "crash_exports") -> Optional[str]:
        """导出崩溃报告到文件。

        Args:
            report_id: 报告ID
            output_dir: 输出目录

        Returns:
            Optional[str]: 导出文件路径，失败时返回None
        """
        report = self.get_report(report_id)
        if not report:
            return None

        # 创建输出目录
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 生成文件名
        filename = f"crash_report_{report_id}_{report.timestamp.strftime('%Y%m%d_%H%M%S')}.json.gz"
        filepath = output_path / filename

        try:
            # 压缩并保存
            with gzip.open(filepath, "wt", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)

            logger.info(f"[CrashReport] Exported report to: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"[CrashReport] Failed to export report: {e}")
            return None

    def _record_to_report(self, record) -> CrashReport:
        """将数据库记录转换为CrashReport对象。

        Args:
            record: 数据库记录

        Returns:
            CrashReport: 崩溃报告对象
        """
        system_info_data = json.loads(record.system_info) if record.system_info else {}
        system_info = SystemInfo(**system_info_data)

        return CrashReport(
            report_id=record.report_id,
            timestamp=record.timestamp,
            severity=record.severity,
            status=record.status,
            exception_type=record.exception_type,
            exception_message=record.exception_message,
            exception_traceback=record.exception_traceback,
            exception_module=record.exception_module,
            exception_function=record.exception_function,
            exception_line=record.exception_line,
            system_info=system_info,
            context_data=json.loads(record.context_data) if record.context_data else {},
            device_id=record.device_id,
            experiment_id=record.experiment_id,
            user_id=record.user_id,
            tags=json.loads(record.tags) if record.tags else [],
            notes=record.notes or "",
            resolved_at=record.resolved_at,
            resolved_by=record.resolved_by,
        )

    def close(self) -> None:
        """关闭数据库连接。

        释放数据库资源，确保文件可以被删除。
        """
        try:
            self.engine.dispose()
            logger.info("[CrashReportStorage] Database connection closed")
        except Exception as e:
            logger.warning(f"[CrashReportStorage] Failed to close database: {e}")


# ============================================================================
# 崩溃报告管理器
# ============================================================================


class CrashReportManager:
    """崩溃报告管理器。

    提供统一的崩溃报告管理接口，包括异常捕获、报告生成和存储。

    Example:
        >>> manager = CrashReportManager(app_start_time=time.time())
        >>> manager.install_exception_hook()
        >>> report = manager.capture_exception(exc_info, context_data={})
    """

    def __init__(
        self,
        app_start_time: float,
        app_version: str = "0.3.0",
        db_path: str = "crash_reports.db",
        auto_cleanup: bool = True,
        cleanup_days: int = 30,
    ):
        """初始化崩溃报告管理器。

        Args:
            app_start_time: 应用启动时间戳
            app_version: 应用版本号
            db_path: 数据库文件路径
            auto_cleanup: 是否自动清理过期报告
            cleanup_days: 清理保留天数
        """
        self.app_start_time = app_start_time
        self.app_version = app_version
        self.storage = CrashReportStorage(db_path=db_path)
        self.auto_cleanup = auto_cleanup
        self.cleanup_days = cleanup_days

        # 原始异常钩子（用于链式调用）
        self._original_excepthook = None
        self._original_async_exception_handler = None

        logger.info("[CrashReportManager] Initialized")

    def install_exception_hook(self) -> None:
        """安装全局异常钩子。

        替换sys.excepthook，捕获所有未处理异常。
        """
        self._original_excepthook = sys.excepthook
        sys.excepthook = self._handle_exception

        # 安装异步异常处理器
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            self._original_async_exception_handler = loop.get_exception_handler()
            loop.set_exception_handler(self._handle_async_exception)
        except RuntimeError:
            # 没有事件循环，跳过
            pass

        logger.info("[CrashReportManager] Exception hooks installed")

    def uninstall_exception_hook(self) -> None:
        """卸载全局异常钩子。

        恢复原始异常处理钩子。
        """
        if self._original_excepthook:
            sys.excepthook = self._original_excepthook

        if self._original_async_exception_handler:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                loop.set_exception_handler(self._original_async_exception_handler)
            except RuntimeError:
                pass

        logger.info("[CrashReportManager] Exception hooks uninstalled")

    def _handle_exception(self, exc_type, exc_value, exc_traceback) -> None:
        """处理未捕获异常。

        Args:
            exc_type: 异常类型
            exc_value: 异常值
            exc_traceback: 异常堆栈
        """
        # 生成崩溃报告
        try:
            report = self.capture_exception(
                exc_info=(exc_type, exc_value, exc_traceback),
                severity=self._determine_severity(exc_value),
            )
            logger.critical(
                f"[CrashReport] Unhandled exception captured: {report.report_id}"
            )
        except Exception as e:
            logger.error(f"[CrashReport] Failed to capture exception: {e}")

        # 调用原始异常钩子
        if self._original_excepthook:
            self._original_excepthook(exc_type, exc_value, exc_traceback)

    def _handle_async_exception(self, loop, context: dict) -> None:
        """处理异步异常。

        Args:
            loop: 事件循环
            context: 异常上下文
        """
        # 提取异常信息
        exception = context.get("exception")
        if exception:
            try:
                report = self.capture_exception(
                    exc_info=(type(exception), exception, exception.__traceback__),
                    severity=self._determine_severity(exception),
                    context_data={"async_context": context.get("message", "")},
                )
                logger.critical(
                    f"[CrashReport] Async exception captured: {report.report_id}"
                )
            except Exception as e:
                logger.error(f"[CrashReport] Failed to capture async exception: {e}")

        # 调用原始处理器
        if self._original_async_exception_handler:
            self._original_async_exception_handler(loop, context)

    def capture_exception(
        self,
        exc_info: Optional[tuple] = None,
        severity: str = CrashSeverity.HIGH,
        context_data: Optional[dict] = None,
        device_id: Optional[str] = None,
        experiment_id: Optional[int] = None,
        user_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> CrashReport:
        """捕获异常并生成崩溃报告。

        Args:
            exc_info: 异常信息元组 (type, value, traceback)，默认使用当前异常
            severity: 严重程度
            context_data: 上下文数据
            device_id: 相关设备ID
            experiment_id: 相关实验ID
            user_id: 相关用户ID
            tags: 标签列表

        Returns:
            CrashReport: 生成的崩溃报告
        """
        # 获取异常信息
        if exc_info is None:
            exc_info = sys.exc_info()

        exc_type, exc_value, exc_tb = exc_info

        if exc_type is None:
            raise ValueError("No exception information available")

        # 提取异常位置信息
        exception_module = ""
        exception_function = ""
        exception_line = 0

        if exc_tb:
            tb_frame = exc_tb.tb_frame
            exception_module = tb_frame.f_globals.get("__name__", "")
            exception_function = tb_frame.f_code.co_name
            exception_line = exc_tb.tb_lineno

        # 生成堆栈跟踪
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
        exception_traceback = "".join(tb_lines)

        # 收集系统信息
        system_info = SystemInfo.collect(
            app_start_time=self.app_start_time,
            app_version=self.app_version,
        )

        # 创建崩溃报告
        report = CrashReport(
            severity=severity,
            status=CrashStatus.NEW,
            exception_type=exc_type.__name__,
            exception_message=str(exc_value),
            exception_traceback=exception_traceback,
            exception_module=exception_module,
            exception_function=exception_function,
            exception_line=exception_line,
            system_info=system_info,
            context_data=context_data or {},
            device_id=device_id,
            experiment_id=experiment_id,
            user_id=user_id,
            tags=tags or [],
        )

        # 保存报告
        self.storage.save_report(report)

        return report

    def _determine_severity(self, exc_value: Exception) -> str:
        """根据异常类型判断严重程度。

        Args:
            exc_value: 异常值

        Returns:
            str: 严重程度
        """
        # 致命错误
        if isinstance(exc_value, (SystemExit, KeyboardInterrupt, MemoryError)):
            return CrashSeverity.CRITICAL

        # 严重错误
        if isinstance(
            exc_value,
            (
                OSError,
                IOError,
                ConnectionError,
                TimeoutError,
                PermissionError,
            ),
        ):
            return CrashSeverity.HIGH

        # 中等错误
        if isinstance(
            exc_value,
            (
                ValueError,
                TypeError,
                KeyError,
                AttributeError,
                IndexError,
            ),
        ):
            return CrashSeverity.MEDIUM

        # 轻微错误
        return CrashSeverity.LOW

    def cleanup(self) -> int:
        """清理过期崩溃报告。

        Returns:
            int: 删除的记录数
        """
        if self.auto_cleanup:
            return self.storage.cleanup_old_reports(max_age_days=self.cleanup_days)
        return 0

    def close(self) -> None:
        """关闭崩溃报告管理器。

        释放资源，关闭数据库连接。
        """
        self.uninstall_exception_hook()
        if self.storage:
            self.storage.close()
        logger.info("[CrashReportManager] Closed")


# ============================================================================
# 装饰器
# ============================================================================


def capture_crashes(
    severity: str = CrashSeverity.HIGH,
    reraise: bool = True,
    context_data: Optional[dict] = None,
):
    """崩溃捕获装饰器。

    自动捕获函数执行中的异常并生成崩溃报告。

    Args:
        severity: 严重程度
        reraise: 是否重新抛出异常
        context_data: 额外上下文数据

    Returns:
        Callable: 装饰器函数

    Example:
        >>> @capture_crashes(severity="high", reraise=False)
        ... def risky_operation():
        ...     # 可能抛出异常的代码
        ...     pass
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 获取全局崩溃报告管理器
                manager = get_crash_report_manager()
                if manager:
                    manager.capture_exception(
                        severity=severity,
                        context_data={
                            "function": func.__name__,
                            "args": str(args[:3]),  # 限制长度
                            "kwargs": str(list(kwargs.keys())[:5]),
                            **(context_data or {}),
                        },
                    )
                if reraise:
                    raise

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                manager = get_crash_report_manager()
                if manager:
                    manager.capture_exception(
                        severity=severity,
                        context_data={
                            "function": func.__name__,
                            "args": str(args[:3]),
                            "kwargs": str(list(kwargs.keys())[:5]),
                            **(context_data or {}),
                        },
                    )
                if reraise:
                    raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============================================================================
# 全局实例
# ============================================================================

# 全局崩溃报告管理器实例
_crash_report_manager: Optional[CrashReportManager] = None


def init_crash_report_manager(
    app_start_time: float,
    app_version: str = "0.3.0",
    db_path: str = "crash_reports.db",
    auto_cleanup: bool = True,
    cleanup_days: int = 30,
    install_hook: bool = True,
) -> CrashReportManager:
    """初始化全局崩溃报告管理器。

    Args:
        app_start_time: 应用启动时间戳
        app_version: 应用版本号
        db_path: 数据库文件路径
        auto_cleanup: 是否自动清理过期报告
        cleanup_days: 清理保留天数
        install_hook: 是否安装异常钩子

    Returns:
        CrashReportManager: 崩溃报告管理器实例

    Example:
        >>> manager = init_crash_report_manager(
        ...     app_start_time=time.time(),
        ...     app_version="0.3.0",
        ... )
    """
    global _crash_report_manager

    _crash_report_manager = CrashReportManager(
        app_start_time=app_start_time,
        app_version=app_version,
        db_path=db_path,
        auto_cleanup=auto_cleanup,
        cleanup_days=cleanup_days,
    )

    if install_hook:
        _crash_report_manager.install_exception_hook()

    logger.info("[CrashReport] Global manager initialized")
    return _crash_report_manager


def get_crash_report_manager() -> Optional[CrashReportManager]:
    """获取全局崩溃报告管理器实例。

    Returns:
        Optional[CrashReportManager]: 崩溃报告管理器实例
    """
    return _crash_report_manager


def get_crash_report_storage() -> Optional[CrashReportStorage]:
    """获取崩溃报告存储实例。

    Returns:
        Optional[CrashReportStorage]: 崩溃报告存储实例
    """
    if _crash_report_manager:
        return _crash_report_manager.storage
    return None


# ============================================================================
# API响应模型
# ============================================================================


class CrashReportListResponse(BaseModel):
    """崩溃报告列表响应模型。"""

    total: int = Field(..., description="总数量")
    reports: list[dict[str, Any]] = Field(..., description="报告列表")


class CrashReportDetailResponse(BaseModel):
    """崩溃报告详情响应模型。"""

    report_id: str = Field(..., description="报告ID")
    timestamp: str = Field(..., description="崩溃时间")
    severity: str = Field(..., description="严重程度")
    status: str = Field(..., description="状态")
    exception_type: str = Field(..., description="异常类型")
    exception_message: str = Field(..., description="异常消息")
    exception_traceback: str = Field(..., description="异常堆栈")
    exception_module: str = Field(..., description="异常所在模块")
    exception_function: str = Field(..., description="异常所在函数")
    exception_line: int = Field(..., description="异常所在行号")
    system_info: dict[str, Any] = Field(..., description="系统信息")
    context_data: dict[str, Any] = Field(..., description="上下文数据")
    device_id: Optional[str] = Field(None, description="设备ID")
    experiment_id: Optional[int] = Field(None, description="实验ID")
    user_id: Optional[str] = Field(None, description="用户ID")
    tags: list[str] = Field(default_factory=list, description="标签列表")
    notes: str = Field("", description="处理备注")
    resolved_at: Optional[str] = Field(None, description="解决时间")
    resolved_by: Optional[str] = Field(None, description="解决人")


class CrashReportStatisticsResponse(BaseModel):
    """崩溃报告统计响应模型。"""

    total_reports: int = Field(0, description="总报告数")
    by_severity: dict[str, int] = Field(default_factory=dict, description="按严重程度统计")
    by_status: dict[str, int] = Field(default_factory=dict, description="按状态统计")
    by_exception_type: dict[str, int] = Field(default_factory=dict, description="按异常类型统计")
    recent_24h_count: int = Field(0, description="最近24小时数量")


class CrashReportUpdateRequest(BaseModel):
    """崩溃报告更新请求模型。"""

    status: str = Field(..., description="新状态")
    notes: Optional[str] = Field(None, description="处理备注")
    resolved_by: Optional[str] = Field(None, description="解决人")
