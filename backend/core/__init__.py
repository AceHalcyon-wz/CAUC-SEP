"""
CAUC-SEP Core Module

文件名: __init__.py
路径: backend/core/
功能: 核心功能模块入口，统一导出所有核心组件和子模块
作者: Backend Engineer Agent
创建日期: 2024-01-15
更新日期: 2026-03-15
版本: 1.0.0

核心功能模块包含：
    - 设备驱动抽象层 (AbstractDevice, AbstractStepper)
    - 数据存储与处理 (DataStorage, DatabaseManager)
    - 缓存系统 (CacheManager, LocalCache)
    - 日志配置 (setup_logging, get_log_stats)
    - 性能监控 (MetricsCollector, Profiler)
    - 链路追踪 (TracingMiddleware, tracer)
    - 崩溃报告 (CrashReportManager)
    - 设备管理 (DeviceRegistry, DriverManager)
    - 统一异常处理 (AppException, ErrorCode, ValidationException)

子模块说明：
    - storage: 数据存储（数据库、时序数据、数据管道、索引优化）
    - cache: 缓存系统（Redis、本地缓存、LRU/TTL缓存策略）
    - monitoring: 监控追踪（链路追踪、性能分析、指标收集、查询监控）
    - logging: 日志管理（日志配置、日志轮转、崩溃报告收集与上传）
    - device_management: 设备管理（注册表、驱动管理、实时调度、设备工具）

依赖：
    - abc: 抽象基类支持
    - enum: 枚举类型支持
    - typing: 类型注解支持
    - sqlalchemy: 数据库ORM
    - redis: Redis客户端（可选）
    - structlog: 结构化日志（可选）

使用示例：
    >>> from backend.core import AbstractDevice, DeviceStatus
    >>> from backend.core import setup_logging, get_cache_manager
    >>> from backend.core import AppException, ErrorCode, device_not_found
    >>> 
    >>> # 初始化日志
    >>> setup_logging(level="INFO")
    >>> 
    >>> # 获取缓存管理器
    >>> cache = get_cache_manager()
    >>> 
    >>> # 抛出统一异常
    >>> raise device_not_found("stepper_01")
"""

from .abstract import (
    AbstractDevice,
    AbstractStepper,
    DeviceStatus,
    SoftwareLimitConfig,
)
from .storage import DataStorage
from .logging import get_log_stats, setup_logging
from .startup_config import check_dependencies, get_system_info, optimize_startup

# 导入统一异常框架
from .exceptions import (
    AppException,
    ErrorCode,
    ValidationErrorDetail,
    ValidationException,
    cache_error,
    database_error,
    device_busy,
    device_connection_failed,
    device_limit_exceeded,
    device_not_connected,
    device_not_found,
    device_timeout,
    experiment_already_running,
    experiment_not_found,
    experiment_not_running,
    internal_error,
    invalid_credentials,
    invalid_token,
    permission_denied,
    service_unavailable,
    token_expired,
)

from . import cache
from . import device_management
from . import logging
from . import monitoring
from . import storage

__all__ = [
    # ==================== 设备抽象层 ====================
    "DeviceStatus",
    "AbstractDevice",
    "AbstractStepper",
    "SoftwareLimitConfig",
    # ==================== 数据存储 ====================
    "DataStorage",
    # ==================== 日志配置 ====================
    "setup_logging",
    "get_log_stats",
    # ==================== 系统配置 ====================
    "get_system_info",
    "check_dependencies",
    "optimize_startup",
    # ==================== 统一异常框架 ====================
    "AppException",
    "ErrorCode",
    "ValidationErrorDetail",
    "ValidationException",
    # ==================== 设备异常工厂函数 ====================
    "device_not_found",
    "device_connection_failed",
    "device_not_connected",
    "device_timeout",
    "device_limit_exceeded",
    "device_busy",
    # ==================== 实验异常工厂函数 ====================
    "experiment_not_found",
    "experiment_already_running",
    "experiment_not_running",
    # ==================== 认证异常工厂函数 ====================
    "invalid_token",
    "token_expired",
    "permission_denied",
    "invalid_credentials",
    # ==================== 系统异常工厂函数 ====================
    "internal_error",
    "database_error",
    "cache_error",
    "service_unavailable",
    # ==================== 子模块 ====================
    "cache",
    "device_management",
    "logging",
    "monitoring",
    "storage",
]
