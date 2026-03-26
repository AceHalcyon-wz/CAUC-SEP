"""
文件名: __init__.py
路径: backend/core/hardware/__init__.py
功能: 硬件抽象层模块，导出统一的设备抽象接口
作者: Backend Engineer Agent
创建日期: 2026-03-26
依赖: Python 3.11+

模块内容：
    - BaseDevice: 统一的设备抽象基类
    - ModbusDeviceBase: Modbus设备抽象基类
    - AsyncDeviceBase: 异步设备抽象基类
    - DeviceStatus: 设备状态枚举
    - DeviceType: 设备类型枚举
    - SoftwareLimitConfig: 软件限位配置类
    - DeviceInfo/DeviceConfig/DeviceAlarm/DeviceParameter: 设备数据类

设计参考：CAUC-SEP项目架构重构与Agent驱动开发专属提示词文件
"""

from backend.core.hardware.base_device import BaseDevice
from backend.core.hardware.device_types import (
    ConnectionType,
    DeviceAlarm,
    DeviceConfig,
    DeviceInfo,
    DeviceParameter,
    DeviceStatus,
    DeviceType,
)
from backend.core.hardware.modbus_device import ModbusDeviceBase
from backend.core.hardware.software_limit import SoftwareLimitConfig

__all__ = [
    # 核心抽象基类
    "BaseDevice",
    "ModbusDeviceBase",
    # 设备类型与状态
    "DeviceStatus",
    "DeviceType",
    "ConnectionType",
    # 设备数据类
    "DeviceInfo",
    "DeviceConfig",
    "DeviceAlarm",
    "DeviceParameter",
    # 软件限位
    "SoftwareLimitConfig",
]
