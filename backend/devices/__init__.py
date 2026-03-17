"""
设备驱动模块

功能：
- 提供统一的设备驱动接口
- 包含所有硬件设备的驱动实现
- 支持仿真模式和实际硬件连接

设备类型：
- stepper: 步进电机驱动 (DM2C)
- electromagnet: 电磁铁驱动
- temperature: 温控系统驱动
- piezo: 压电陶瓷驱动
- ammeter: 微电流计驱动

作者：Backend Engineer Agent
创建日期：2026-03-14
"""

from core.abstract import AbstractDevice, AbstractStepper, DeviceStatus, SoftwareLimitConfig
from devices.ammeter import (
    AcquisitionConfig,
    ChannelConfig,
    ChannelData,
    CurrentRange,
    FilterType,
    Picoammeter,
)
from devices.electromagnet import (
    CalibrationPoint,
    ElectromagnetDriver,
    ElectromagnetStatus,
    MAX_CURRENT,
    MAX_FIELD,
    MAX_SCAN_RATE,
    MAX_TEMPERATURE,
    MIN_CURRENT,
    MIN_SCAN_RATE,
    OVERCURRENT_THRESHOLD,
    ScanMode,
    ScanParameters,
)
from devices.piezo import (
    CalibrationData,
    CalibrationPoint as PiezoCalibrationPoint,
    CalibrationType,
    ControlMode,
    PiezoConfig,
    PiezoController,
)
from devices.stepper import (
    ALARM_CODES,
    ALARM_INFO_MAP,
    AlarmInfo,
    AlarmSeverity,
    LeadshineDM2C,
    mm_to_steps,
    steps_to_mm,
)
from devices.temperature import (
    NUM_SENSOR_CHANNELS,
    PIDParameters,
    ProtectionCallback,
    RATE_CALCULATION_WINDOW_SIZE,
    SensorChannel,
    TemperatureController,
    TemperatureControllerMode,
    TemperatureProtectionType,
)

__all__ = [
    "ALARM_CODES",
    "ALARM_INFO_MAP",
    "MAX_CURRENT",
    "MAX_FIELD",
    "MAX_SCAN_RATE",
    "MAX_TEMPERATURE",
    "MIN_CURRENT",
    "MIN_SCAN_RATE",
    "NUM_SENSOR_CHANNELS",
    "OVERCURRENT_THRESHOLD",
    "RATE_CALCULATION_WINDOW_SIZE",
    "AbstractDevice",
    "AbstractStepper",
    "AcquisitionConfig",
    "AlarmInfo",
    "AlarmSeverity",
    "CalibrationData",
    "CalibrationPoint",
    "CalibrationType",
    "ChannelConfig",
    "ChannelData",
    "ControlMode",
    "CurrentRange",
    "DeviceStatus",
    "ElectromagnetDriver",
    "ElectromagnetStatus",
    "FilterType",
    "LeadshineDM2C",
    "PIDParameters",
    "Picoammeter",
    "PiezoCalibrationPoint",
    "PiezoConfig",
    "PiezoController",
    "ProtectionCallback",
    "ScanMode",
    "ScanParameters",
    "SensorChannel",
    "SoftwareLimitConfig",
    "TemperatureController",
    "TemperatureControllerMode",
    "TemperatureProtectionType",
    "mm_to_steps",
    "steps_to_mm",
]
