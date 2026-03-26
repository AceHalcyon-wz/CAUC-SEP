"""
文件名: validation_utils.py
路径: backend/core/utils/validation_utils.py
功能: 设备参数校验通用工具类，提供统一的参数校验、范围检查、合法性验证
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: Python 3.11+, typing, logging

安全约束:
- 所有外部输入必须做合法性校验
- 非法参数必须拦截并返回明确错误信息
- 校验失败不得抛出异常，应返回校验结果
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Tuple

logger = logging.getLogger(__name__)


# ==================== 校验结果类 ====================


@dataclass
class ValidationResult:
    """
    校验结果数据类。

    Attributes:
        is_valid: 是否有效
        error_message: 错误信息
        error_code: 错误代码
        details: 详细信息
    """

    is_valid: bool
    error_message: str | None = None
    error_code: int | None = None
    details: dict[str, Any] | None = None

    def __bool__(self) -> bool:
        """
        布尔转换。

        Returns:
            bool: 是否有效
        """
        return self.is_valid

    def to_dict(self) -> dict[str, Any]:
        """
        转换为字典。

        Returns:
            Dict[str, Any]: 字典格式
        """
        return {
            "is_valid": self.is_valid,
            "error_message": self.error_message,
            "error_code": self.error_code,
            "details": self.details,
        }


# ==================== 通用校验函数 ====================


def validate_range(
    value: float | int,
    min_value: float | int,
    max_value: float | int,
    name: str = "value",
    include_min: bool = True,
    include_max: bool = True,
) -> ValidationResult:
    """
    校验数值是否在指定范围内。

    Args:
        value: 要校验的值
        min_value: 最小值
        max_value: 最大值
        name: 参数名称
        include_min: 是否包含最小值
        include_max: 是否包含最大值

    Returns:
        ValidationResult: 校验结果

    Example:
        >>> result = validate_range(50, 0, 100, "speed")
        >>> if not result:
        ...     print(result.error_message)
    """
    # 检查最小值
    if include_min:
        min_check = value >= min_value
        min_operator = ">="
    else:
        min_check = value > min_value
        min_operator = ">"

    # 检查最大值
    if include_max:
        max_check = value <= max_value
        max_operator = "<="
    else:
        max_check = value < max_value
        max_operator = "<"

    if min_check and max_check:
        return ValidationResult(is_valid=True)

    # 构建错误信息
    error_message = (
        f"{name}={value} 超出有效范围 "
        f"[{min_value}, {max_value}] "
        f"(需要满足: {name} {min_operator} {min_value} 且 {name} {max_operator} {max_value})"
    )

    return ValidationResult(
        is_valid=False,
        error_message=error_message,
        error_code=1001,
        details={
            "parameter_name": name,
            "actual_value": value,
            "min_value": min_value,
            "max_value": max_value,
            "include_min": include_min,
            "include_max": include_max,
        },
    )


def validate_device_id(device_id: str | None) -> ValidationResult:
    """
    校验设备ID是否有效。

    Args:
        device_id: 设备ID

    Returns:
        ValidationResult: 校验结果

    校验规则:
        - 不能为None或空字符串
        - 只能包含字母、数字、下划线、连字符
        - 长度在1-64个字符之间
    """
    if device_id is None or device_id == "":
        return ValidationResult(
            is_valid=False,
            error_message="设备ID不能为空",
            error_code=1002,
        )

    # 长度检查
    if len(device_id) > 64:
        return ValidationResult(
            is_valid=False,
            error_message=f"设备ID长度超过限制（最大64字符）: {len(device_id)}",
            error_code=1002,
        )

    # 格式检查
    pattern = r"^[a-zA-Z0-9_-]+$"
    if not re.match(pattern, device_id):
        return ValidationResult(
            is_valid=False,
            error_message=f"设备ID格式无效，只能包含字母、数字、下划线、连字符: {device_id}",
            error_code=1002,
        )

    return ValidationResult(is_valid=True)


def validate_modbus_address(address: int) -> ValidationResult:
    """
    校验Modbus寄存器地址是否有效。

    Args:
        address: 寄存器地址

    Returns:
        ValidationResult: 校验结果

    校验规则:
        - 地址范围: 0-65535
    """
    if not isinstance(address, int):
        return ValidationResult(
            is_valid=False,
            error_message=f"寄存器地址必须是整数: {type(address).__name__}",
            error_code=1003,
        )

    if not (0 <= address <= 65535):
        return ValidationResult(
            is_valid=False,
            error_message=f"寄存器地址超出有效范围 [0, 65535]: {address}",
            error_code=1003,
        )

    return ValidationResult(is_valid=True)


def validate_current_value(
    current: float,
    min_current: float = 0.0,
    max_current: float = 10.0,
    device_id: str | None = None,
) -> ValidationResult:
    """
    校验电流值是否有效。

    Args:
        current: 电流值（A）
        min_current: 最小电流（A）
        max_current: 最大电流（A）
        device_id: 设备ID（用于日志）

    Returns:
        ValidationResult: 校验结果

    安全约束:
        - 电流值必须在设备允许范围内
        - 超过过流保护阈值必须告警
    """
    result = validate_range(current, min_current, max_current, "电流")

    if not result:
        logger.warning(
            f"电流值校验失败: current={current}A, "
            f"range=[{min_current}, {max_current}]A, device_id={device_id}"
        )

    return result


def validate_temperature_value(
    temperature: float,
    min_temp: float = 0.0,
    max_temp: float = 500.0,
    device_id: str | None = None,
) -> ValidationResult:
    """
    校验温度值是否有效。

    Args:
        temperature: 温度值（K）
        min_temp: 最低温度（K）
        max_temp: 最高温度（K）
        device_id: 设备ID（用于日志）

    Returns:
        ValidationResult: 校验结果

    安全约束:
        - 温度值必须在设备允许范围内
        - 超出范围可能导致设备损坏
    """
    result = validate_range(temperature, min_temp, max_temp, "温度")

    if not result:
        logger.warning(
            f"温度值校验失败: temperature={temperature}K, "
            f"range=[{min_temp}, {max_temp}]K, device_id={device_id}"
        )

    return result


def validate_voltage_value(
    voltage: float,
    min_voltage: float = 0.0,
    max_voltage: float = 150.0,
    device_id: str | None = None,
) -> ValidationResult:
    """
    校验电压值是否有效。

    Args:
        voltage: 电压值（V）
        min_voltage: 最小电压（V）
        max_voltage: 最大电压（V）
        device_id: 设备ID（用于日志）

    Returns:
        ValidationResult: 校验结果

    安全约束:
        - 电压值必须在设备允许范围内
        - 超出范围可能导致设备损坏
    """
    result = validate_range(voltage, min_voltage, max_voltage, "电压")

    if not result:
        logger.warning(
            f"电压值校验失败: voltage={voltage}V, "
            f"range=[{min_voltage}, {max_voltage}]V, device_id={device_id}"
        )

    return result


def validate_position_value(
    position: float,
    min_position: float,
    max_position: float,
    device_id: str | None = None,
) -> ValidationResult:
    """
    校验位置值是否有效（软件限位校验）。

    Args:
        position: 位置值（mm）
        min_position: 最小位置（mm）
        max_position: 最大位置（mm）
        device_id: 设备ID（用于日志）

    Returns:
        ValidationResult: 校验结果

    安全约束:
        - 位置必须在软件限位范围内
        - 超出限位可能导致机械撞机
    """
    result = validate_range(position, min_position, max_position, "位置")

    if not result:
        logger.warning(
            f"位置值校验失败（超限位）: position={position}mm, "
            f"range=[{min_position}, {max_position}]mm, device_id={device_id}"
        )

    return result


def validate_speed_value(
    speed: float,
    min_speed: float = 100.0,
    max_speed: float = 5000.0,
    device_id: str | None = None,
) -> ValidationResult:
    """
    校验速度值是否有效。

    Args:
        speed: 速度值（脉冲/秒或Hz）
        min_speed: 最小速度
        max_speed: 最大速度
        device_id: 设备ID（用于日志）

    Returns:
        ValidationResult: 校验结果
    """
    result = validate_range(speed, min_speed, max_speed, "速度")

    if not result:
        logger.warning(
            f"速度值校验失败: speed={speed}, "
            f"range=[{min_speed}, {max_speed}], device_id={device_id}"
        )

    return result


# ==================== 批量校验函数 ====================


def validate_all(
    validations: list[Tuple[str, Any, Any, Any]],
) -> Tuple[bool, list[ValidationResult]]:
    """
    批量校验多个参数。

    Args:
        validations: 校验列表，每个元素为 (参数名, 值, 最小值, 最大值)

    Returns:
        Tuple[bool, List[ValidationResult]]: (是否全部有效, 校验结果列表)

    Example:
        >>> results = validate_all([
        ...     ("speed", 500, 100, 5000),
        ...     ("position", 10000, 0, 50000),
        ... ])
        >>> if not results[0]:
        ...     for r in results[1]:
        ...         if not r:
        ...             print(r.error_message)
    """
    results = []

    for name, value, min_val, max_val in validations:
        result = validate_range(value, min_val, max_val, name)
        results.append(result)

    all_valid = all(r.is_valid for r in results)

    return all_valid, results


def validate_required_fields(
    data: dict[str, Any],
    required_fields: list[str],
) -> ValidationResult:
    """
    校验必填字段是否存在。

    Args:
        data: 数据字典
        required_fields: 必填字段列表

    Returns:
        ValidationResult: 校验结果
    """
    missing_fields = []

    for field in required_fields:
        if field not in data or data[field] is None:
            missing_fields.append(field)

    if missing_fields:
        return ValidationResult(
            is_valid=False,
            error_message=f"缺少必填字段: {', '.join(missing_fields)}",
            error_code=1004,
            details={"missing_fields": missing_fields},
        )

    return ValidationResult(is_valid=True)


# ==================== 类型校验函数 ====================


def validate_type(value: Any, expected_type: type, name: str = "value") -> ValidationResult:
    """
    校验值是否为指定类型。

    Args:
        value: 要校验的值
        expected_type: 期望类型
        name: 参数名称

    Returns:
        ValidationResult: 校验结果
    """
    if not isinstance(value, expected_type):
        return ValidationResult(
            is_valid=False,
            error_message=f"{name}类型错误: 期望{expected_type.__name__}, 实际{type(value).__name__}",
            error_code=1005,
            details={
                "parameter_name": name,
                "expected_type": expected_type.__name__,
                "actual_type": type(value).__name__,
            },
        )

    return ValidationResult(is_valid=True)


def validate_positive_number(value: float | int, name: str = "value") -> ValidationResult:
    """
    校验是否为正数。

    Args:
        value: 要校验的值
        name: 参数名称

    Returns:
        ValidationResult: 校验结果
    """
    if not isinstance(value, (int, float)):
        return ValidationResult(
            is_valid=False,
            error_message=f"{name}必须是数值类型",
            error_code=1005,
        )

    if value <= 0:
        return ValidationResult(
            is_valid=False,
            error_message=f"{name}必须是正数: {value}",
            error_code=1006,
        )

    return ValidationResult(is_valid=True)


def validate_non_negative_number(value: float | int, name: str = "value") -> ValidationResult:
    """
    校验是否为非负数。

    Args:
        value: 要校验的值
        name: 参数名称

    Returns:
        ValidationResult: 校验结果
    """
    if not isinstance(value, (int, float)):
        return ValidationResult(
            is_valid=False,
            error_message=f"{name}必须是数值类型",
            error_code=1005,
        )

    if value < 0:
        return ValidationResult(
            is_valid=False,
            error_message=f"{name}必须是非负数: {value}",
            error_code=1006,
        )

    return ValidationResult(is_valid=True)
