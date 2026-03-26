"""
文件名: __init__.py
路径: backend/core/utils/__init__.py
功能: 公共工具模块初始化文件
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: Python 3.11+
"""

from .modbus_utils import (
    ModbusDataConverter,
    ModbusCommunicationHelper,
    convert_signed_32bit,
    convert_unsigned_32bit,
)
from .exception_utils import (
    DeviceException,
    DeviceCommunicationError,
    DeviceParameterError,
    DeviceAlarmError,
    DeviceTimeoutError,
    handle_device_exception,
    retry_with_backoff,
)
from .validation_utils import (
    validate_range,
    validate_device_id,
    validate_modbus_address,
    validate_current_value,
    validate_temperature_value,
    validate_voltage_value,
)

__all__ = [
    "ModbusDataConverter",
    "ModbusCommunicationHelper",
    "convert_signed_32bit",
    "convert_unsigned_32bit",
    "DeviceException",
    "DeviceCommunicationError",
    "DeviceParameterError",
    "DeviceAlarmError",
    "DeviceTimeoutError",
    "handle_device_exception",
    "retry_with_backoff",
    "validate_range",
    "validate_device_id",
    "validate_modbus_address",
    "validate_current_value",
    "validate_temperature_value",
    "validate_voltage_value",
]
