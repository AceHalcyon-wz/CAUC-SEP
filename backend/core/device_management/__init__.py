"""
设备管理子模块

文件名: __init__.py
路径: backend/core/device_management/
功能: 提供硬件设备的注册、驱动管理、实时调度和串口通信管理能力
作者: Backend Engineer Agent
创建日期: 2024-01-15
更新日期: 2026-03-25
版本: 1.1.0

核心功能：
    - 设备注册表（设备发现与生命周期管理）
    - 驱动管理器（驱动加载与版本管理）
    - 实时调度器（任务优先级调度）
    - 设备工具函数（配置验证、状态格式化）
    - 统一串口管理器（单串口多设备队列调度、优先级调度、超时中断、急停重发）

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
    - UnifiedSerialManager: 统一串口通信管理器
    - SerialPortManager: 单串口管理器
    - SerialPortConfig: 串口配置
    - SerialCommand: 串口指令
    - CommandResult: 指令执行结果
    - CommandPriority: 指令优先级枚举
    - CommandType: 指令类型枚举
    - SerialCommunicationError: 串口通信异常
    - create_emergency_stop_command: 创建急停指令
    - create_read_command: 创建读指令
    - create_write_command: 创建写指令

依赖：
    - asyncio: 异步IO支持
    - typing: 类型注解支持
    - backend.core.abstract: 设备抽象基类

使用示例：
    >>> from backend.core.device_management import (
    ...     DeviceRegistry, DriverProcessManager, validate_device_state,
    ...     UnifiedSerialManager, SerialPortConfig, CommandPriority
    ... )
    >>> 
    >>> # 验证设备配置
    >>> registry = DeviceRegistry()
    >>> await registry.register("motor_1", motor_instance)
    >>> 
    >>> # 使用统一串口管理器
    >>> serial_manager = UnifiedSerialManager()
    >>> config = SerialPortConfig(port="COM1", baudrate=38400)
    >>> await serial_manager.register_port("COM1", config)
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
# 文件路径: backend/core/device_management/serial_manager.py
# 功能: 统一串口通信管理器，实现单串口多设备队列调度、优先级调度、超时中断、急停重发机制
# 作者: Backend Engineer Agent
# 创建日期: 2026-03-25
# 依赖: PyModbus 3.5+, asyncio, threading, logging
# 安全约束: 急停指令最高优先级执行，通信失败自动触发安全兜底逻辑

__all__ = [
    # 设备注册表
    "DeviceRegistry",
    "DeviceValidationError",
    # 驱动管理器
    "DriverProcessManager",
    "create_driver_manager",
    # 实时调度器
    "RealtimeContext",
    "WindowsRTScheduler",
    "bind_to_cpu_core",
    "check_realtime_capability",
    "high_precision_timer",
    "set_realtime_priority",
    # 设备工具函数
    "create_device_error_response",
    "validate_device_state",
    # 统一串口管理器
    "UnifiedSerialManager",
    "SerialPortManager",
    "SerialPortConfig",
    "SerialCommand",
    "CommandResult",
    "CommandPriority",
    "CommandType",
    "SerialCommunicationError",
    "create_emergency_stop_command",
    "create_read_command",
    "create_write_command",
]
