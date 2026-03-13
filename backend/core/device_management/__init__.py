"""
设备管理子模块

文件名: __init__.py
路径: backend/core/device_management/
功能: 提供硬件设备的注册、驱动管理和实时调度能力
作者: Backend Engineer Agent
创建日期: 2024-01-15
更新日期: 2026-03-14
版本: 1.0.0

核心功能：
    - 设备注册表（设备发现与生命周期管理）
    - 驱动管理器（驱动加载与版本管理）
    - 实时调度器（任务优先级调度）
    - 设备工具函数（配置验证、状态格式化）

导出组件：
    - DeviceRegistry: 设备注册表
    - get_device_registry: 获取设备注册表实例
    - DriverManager: 驱动管理器
    - get_driver_manager: 获取驱动管理器实例
    - RTScheduler: 实时调度器
    - get_rt_scheduler: 获取调度器实例
    - validate_device_config: 验证设备配置
    - get_device_type: 获取设备类型
    - format_device_status: 格式化设备状态

依赖：
    - asyncio: 异步IO支持
    - typing: 类型注解支持
    - backend.core.abstract: 设备抽象基类

使用示例：
    >>> from backend.core.device_management import (
    ...     DeviceRegistry, DriverManager, validate_device_config
    ... )
    >>> 
    >>> # 验证设备配置
    >>> config = {"device_id": "stepper_1", "type": "stepper"}
    >>> is_valid = validate_device_config(config)
    >>> 
    >>> # 注册设备
    >>> registry = get_device_registry()
    >>> await registry.register(device)
"""

from .device_registry import DeviceRegistry, get_device_registry
from .driver_manager import DriverManager, get_driver_manager
from .rt_scheduler import RTScheduler, get_rt_scheduler
from .device_utils import (
    validate_device_config,
    get_device_type,
    format_device_status,
)

__all__ = [
    "DeviceRegistry",
    "get_device_registry",
    "DriverManager",
    "get_driver_manager",
    "RTScheduler",
    "get_rt_scheduler",
    "validate_device_config",
    "get_device_type",
    "format_device_status",
]
