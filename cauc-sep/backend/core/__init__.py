"""
CAUC-SEP Core Module

核心功能模块，包含：
- 设备驱动抽象层
- 数据存储与处理
- 缓存系统
- 日志配置
- 性能监控
- 链路追踪
- 崩溃报告
"""

from core.abstract import DeviceStatus, DeviceBase
from core.database import DataStorage
from core.logging_config import setup_logging, get_log_stats
from core.startup_config import get_system_info, check_dependencies, optimize_startup

__all__ = [
    "DeviceStatus",
    "DeviceBase",
    "DataStorage",
    "setup_logging",
    "get_log_stats",
    "get_system_info",
    "check_dependencies",
    "optimize_startup",
]
