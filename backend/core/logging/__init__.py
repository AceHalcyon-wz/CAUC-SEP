"""
日志和崩溃报告子模块

文件名: __init__.py
路径: backend/core/logging/
功能: 提供日志配置、日志轮转和崩溃报告收集上传能力
作者: Backend Engineer Agent
创建日期: 2024-01-15
更新日期: 2026-03-14
版本: 1.0.0

核心功能：
    - 日志配置和管理（结构化日志）
    - 日志轮转和归档（自动清理旧日志）
    - 崩溃报告收集（异常捕获与堆栈记录）
    - 崩溃报告上传（远程服务器同步）

导出组件：
    - setup_logging: 初始化日志配置
    - get_log_stats: 获取日志统计信息
    - cleanup_old_logs: 清理旧日志文件
    - CrashReportManager: 崩溃报告管理器
    - get_crash_report_storage: 获取崩溃报告存储
    - init_crash_report_manager: 初始化崩溃报告管理器
    - CrashUploader: 崩溃报告上传器
    - upload_crash_report: 上传崩溃报告

依赖：
    - logging: Python标准日志库
    - logging.handlers: 日志处理器
    - asyncio: 异步IO支持
    - json: JSON序列化
    - typing: 类型注解支持

使用示例：
    >>> from backend.core.logging import setup_logging, get_log_stats
    >>> 
    >>> # 初始化日志
    >>> setup_logging(
    ...     level="INFO",
    ...     log_dir="logs",
    ...     max_bytes=10 * 1024 * 1024,  # 10MB
    ...     backup_count=5
    ... )
    >>> 
    >>> # 获取日志统计
    >>> stats = get_log_stats()
    >>> print(f"日志文件数量: {stats['file_count']}")
"""

from .logging_config import (
    cleanup_old_logs,
    get_log_stats,
    setup_logging,
)
from .crash_report import (
    CrashReportManager,
    get_crash_report_storage,
    init_crash_report_manager,
)
from .crash_upload import (
    CrashReportUploader,
    upload_crash_report,
    init_crash_uploader,
    get_crash_uploader,
)

__all__ = [
    "CrashReportManager",
    "CrashReportUploader",
    "cleanup_old_logs",
    "get_crash_report_storage",
    "get_crash_uploader",
    "get_log_stats",
    "init_crash_report_manager",
    "init_crash_uploader",
    "setup_logging",
    "upload_crash_report",
]
