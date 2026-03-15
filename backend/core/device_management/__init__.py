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
    - DriverProcessManager: 驱动进程管理器
    - create_driver_manager: 创建驱动管理器实例
    - WindowsRTScheduler: Windows实时调度器
    - RealtimeContext: 实时执行上下文
    - high_precision_timer: 高精度定时器
    - check_realtime_capability: 检查系统实时能力
    - set_realtime_priority: 设置实时优先级
    - bind_to_cpu_core: 绑定CPU核心
    - DeviceValidationError: 设备验证异常
    - validate_device_state: 验证设备状态
    - create_device_error_response: 创建设备错误响应

依赖：
    - asyncio: 异步IO支持
    - typing: 类型注解支持
    - backend.core.abstract: 设备抽象基类

使用示例：
    >>> from backend.core.device_management import (
    ...     DeviceRegistry, DriverProcessManager, validate_device_state
    ... )
    >>> 
    >>> # 验证设备配置
    >>> registry = DeviceRegistry()
    >>> await registry.register("motor_1", motor_instance)
"""

from .device_registry import DeviceRegistry
from .driver_manager import DriverProcessManager, create_driver_manager
from .rt_scheduler import (
    WindowsRTScheduler,
    RealtimeContext,
    high_precision_timer,
    check_realtime_capability,
    set_realtime_priority,
    bind_to_cpu_core,
)
from .device_utils import (
    DeviceValidationError,
    validate_device_state,
    create_device_error_response,
)

__all__ = [
    "DeviceRegistry",
    "DriverProcessManager",
    "create_driver_manager",
    "WindowsRTScheduler",
    "RealtimeContext",
    "high_precision_timer",
    "check_realtime_capability",
    "set_realtime_priority",
    "bind_to_cpu_core",
    "DeviceValidationError",
    "validate_device_state",
    "create_device_error_response",
]
