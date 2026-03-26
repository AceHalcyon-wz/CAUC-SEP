"""
文件名: device_types.py
路径: backend/core/hardware/device_types.py
功能: 设备类型、状态、配置等数据类定义
作者: Backend Engineer Agent
创建日期: 2026-03-26
依赖: Python 3.11+, dataclasses, enum, typing

安全约束:
- 所有设备状态必须使用DeviceStatus枚举
- 设备配置参数必须通过DeviceConfig数据类管理
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DeviceStatus(Enum):
    """
    设备状态枚举。

    定义设备的标准状态，所有设备驱动必须使用此枚举。

    状态机说明：
        DISCONNECTED → CONNECTING → READY ↔ BUSY
                                  ↓         ↓
                               ERROR ← EMERGENCY_STOP
                                  ↑
                              ALARM/INITIALIZING/CALIBRATING

    状态转换规则：
        - DISCONNECTED: 初始状态，只能转换到 CONNECTING
        - CONNECTING: 连接中，可转换到 READY, ERROR, DISCONNECTED, INITIALIZING
        - INITIALIZING: 初始化中，可转换到 READY, ERROR, CALIBRATING
        - CALIBRATING: 校准中，可转换到 READY, ERROR
        - READY: 就绪状态，可转换到 BUSY, ERROR, EMERGENCY_STOP, ALARM, DISCONNECTED
        - BUSY: 忙碌状态，可转换到 READY, ERROR, EMERGENCY_STOP, ALARM
        - ERROR: 错误状态，可转换到 DISCONNECTED, READY（复位后）
        - EMERGENCY_STOP: 急停状态，可转换到 DISCONNECTED, READY（复位后）
        - ALARM: 报警状态，可转换到 DISCONNECTED, READY（清除报警后）

    Attributes:
        DISCONNECTED: 未连接状态
        CONNECTING: 连接中状态
        READY: 就绪状态，可接收指令
        BUSY: 忙碌状态，正在执行指令
        ERROR: 错误状态
        EMERGENCY_STOP: 急停状态
        ALARM: 报警状态
        INITIALIZING: 初始化中状态
        CALIBRATING: 校准中状态
    """

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    EMERGENCY_STOP = "emergency_stop"
    ALARM = "alarm"
    INITIALIZING = "initializing"
    CALIBRATING = "calibrating"

    @classmethod
    def get_valid_transitions(cls) -> dict[DeviceStatus, set[DeviceStatus]]:
        """获取合法的状态转换映射。

        Returns:
            Dict[DeviceStatus, Set[DeviceStatus]]: 从每个状态可以转换到的目标状态集合
        """
        return {
            cls.DISCONNECTED: {cls.CONNECTING},
            cls.CONNECTING: {cls.READY, cls.ERROR, cls.DISCONNECTED, cls.INITIALIZING},
            cls.INITIALIZING: {cls.READY, cls.ERROR, cls.CALIBRATING},
            cls.CALIBRATING: {cls.READY, cls.ERROR},
            cls.READY: {cls.BUSY, cls.ERROR, cls.EMERGENCY_STOP, cls.ALARM, cls.DISCONNECTED},
            cls.BUSY: {cls.READY, cls.ERROR, cls.EMERGENCY_STOP, cls.ALARM},
            cls.ERROR: {cls.DISCONNECTED, cls.READY},
            cls.EMERGENCY_STOP: {cls.DISCONNECTED, cls.READY},
            cls.ALARM: {cls.DISCONNECTED, cls.READY},
        }

    def can_transition_to(self, target: DeviceStatus) -> bool:
        """检查是否可以转换到目标状态。

        Args:
            target: 目标状态

        Returns:
            bool: 是否允许转换
        """
        valid_targets = self.get_valid_transitions().get(self, set())
        return target in valid_targets


class DeviceType(Enum):
    """
    设备类型枚举。

    定义系统中支持的设备类型。

    Attributes:
        MOTOR: 步进电机
        ELECTROMAGNET: 电磁铁
        TEMPERATURE_CONTROLLER: 温控器
        PIEZO_CONTROLLER: 压电控制器
        POWER_SUPPLY: 电源
        SENSOR: 传感器
        UNKNOWN: 未知设备
    """

    MOTOR = "motor"
    ELECTROMAGNET = "electromagnet"
    TEMPERATURE_CONTROLLER = "temperature_controller"
    PIEZO_CONTROLLER = "piezo_controller"
    POWER_SUPPLY = "power_supply"
    SENSOR = "sensor"
    UNKNOWN = "unknown"


class ConnectionType(Enum):
    """
    连接类型枚举。

    Attributes:
        SERIAL: 串口连接（RS232/RS485）
        ETHERNET: 以太网连接（TCP/IP）
        USB: USB连接
        GPIB: GPIB连接
        SIMULATION: 仿真模式
    """

    SERIAL = "serial"
    ETHERNET = "ethernet"
    USB = "usb"
    GPIB = "gpib"
    SIMULATION = "simulation"


@dataclass
class DeviceInfo:
    """
    设备信息数据类。

    存储设备的基本信息。

    Attributes:
        device_id: 设备唯一标识
        device_name: 设备名称
        device_type: 设备类型
        manufacturer: 制造商
        model: 型号
        serial_number: 序列号
        firmware_version: 固件版本
        connection_type: 连接类型
    """

    device_id: str
    device_name: str = "Unknown Device"
    device_type: DeviceType = DeviceType.UNKNOWN
    manufacturer: str = "Unknown"
    model: str = "Unknown"
    serial_number: str | None = None
    firmware_version: str | None = None
    connection_type: ConnectionType = ConnectionType.SIMULATION


@dataclass
class DeviceConfig:
    """
    设备配置数据类。

    存储设备的配置参数。

    Attributes:
        device_id: 设备唯一标识
        connection_params: 连接参数字典
        simulation: 是否仿真模式
        auto_reconnect: 是否自动重连
        reconnect_interval: 重连间隔（秒）
        timeout: 通信超时时间（秒）
        max_retries: 最大重试次数
    """

    device_id: str
    connection_params: dict[str, Any] = field(default_factory=dict)
    simulation: bool = True
    auto_reconnect: bool = True
    reconnect_interval: float = 5.0
    timeout: float = 1.0
    max_retries: int = 3


@dataclass
class DeviceAlarm:
    """
    设备报警数据类。

    存储设备的报警信息。

    Attributes:
        alarm_code: 报警代码
        alarm_message: 报警消息
        alarm_level: 报警级别（0=信息, 1=警告, 2=错误, 3=严重）
        timestamp: 报警时间戳
        is_active: 是否活动报警
    """

    alarm_code: int
    alarm_message: str
    alarm_level: int = 1
    timestamp: float = field(default_factory=time.time)
    is_active: bool = True


@dataclass
class DeviceParameter:
    """
    设备参数数据类。

    存储设备的可配置参数。

    Attributes:
        name: 参数名称
        value: 参数值
        min_value: 最小值
        max_value: 最大值
        unit: 单位
        description: 描述
        is_readonly: 是否只读
    """

    name: str
    value: Any
    min_value: Any | None = None
    max_value: Any | None = None
    unit: str = ""
    description: str = ""
    is_readonly: bool = False
