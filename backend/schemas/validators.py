"""
文件名: validators.py
路径: backend/schemas/
功能: 输入验证器和数据清理器，提供设备ID、位置、速度等参数的验证
作者: Backend Engineer Agent
创建日期: 2026-03-16
版本: 1.0.0
依赖: re, typing

验证器：
    - validate_device_id: 设备ID验证器
    - validate_position: 位置参数验证器
    - validate_velocity: 速度参数验证器
    - sanitize_string: 字符串清理器
"""

import re
from typing import Any


# ==================== 常量定义 ====================

DEVICE_ID_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{2,63}$")
"""设备ID正则模式：以字母开头，允许字母、数字、下划线、连字符，长度3-64。"""

MAX_POSITION_MM = 1000.0
"""最大位置限制（毫米）。"""

MIN_POSITION_MM = -1000.0
"""最小位置限制（毫米）。"""

MAX_VELOCITY_MM_S = 500.0
"""最大速度限制（毫米/秒）。"""

MIN_VELOCITY_MM_S = 0.0
"""最小速度限制（毫米/秒）。"""


# ==================== 验证异常 ====================

class ValidationError(ValueError):
    """
    验证错误异常。

    当输入数据验证失败时抛出。

    Attributes:
        field: 字段名称。
        value: 无效值。
        message: 错误消息。
    """

    def __init__(self, field: str, value: Any, message: str) -> None:
        """
        初始化验证错误。

        Args:
            field: 字段名称。
            value: 无效值。
            message: 错误消息。
        """
        self.field = field
        self.value = value
        self.message = message
        super().__init__(f"验证失败 [{field}]: {message} (值: {value})")


# ==================== 设备ID验证器 ====================

def validate_device_id(device_id: str) -> str:
    """
    验证设备ID格式。

    设备ID规则：
        - 以字母开头
        - 仅允许字母、数字、下划线、连字符
        - 长度3-64个字符

    Args:
        device_id: 待验证的设备ID。

    Returns:
        str: 验证通过的设备ID。

    Raises:
        ValidationError: 设备ID格式无效时抛出。

    Example:
        >>> validate_device_id("motor-001")
        'motor-001'
        >>> validate_device_id("123")  # 不以字母开头
        ValidationError: 验证失败 [device_id]: 必须以字母开头
    """
    if not isinstance(device_id, str):
        raise ValidationError("device_id", device_id, "必须是字符串类型")

    if not device_id:
        raise ValidationError("device_id", device_id, "不能为空")

    if len(device_id) < 3:
        raise ValidationError("device_id", device_id, "长度不能少于3个字符")

    if len(device_id) > 64:
        raise ValidationError("device_id", device_id, "长度不能超过64个字符")

    if not DEVICE_ID_PATTERN.match(device_id):
        raise ValidationError(
            "device_id",
            device_id,
            "格式无效：必须以字母开头，仅允许字母、数字、下划线、连字符"
        )

    return device_id


# ==================== 位置验证器 ====================

def validate_position(
    position: float,
    *,
    min_pos: float = MIN_POSITION_MM,
    max_pos: float = MAX_POSITION_MM
) -> float:
    """
    验证位置参数。

    位置参数规则：
        - 必须是数值类型
        - 不能是NaN或无穷大
        - 必须在指定范围内

    Args:
        position: 待验证的位置值（毫米）。
        min_pos: 最小位置限制，默认为-1000.0mm。
        max_pos: 最大位置限制，默认为1000.0mm。

    Returns:
        float: 验证通过的位置值。

    Raises:
        ValidationError: 位置参数无效时抛出。

    Example:
        >>> validate_position(50.5)
        50.5
        >>> validate_position(2000.0)  # 超出范围
        ValidationError: 验证失败 [position]: 超出有效范围
    """
    import math

    if not isinstance(position, (int, float)):
        raise ValidationError("position", position, "必须是数值类型")

    position_float = float(position)

    if math.isnan(position_float):
        raise ValidationError("position", position, "不能是NaN")

    if math.isinf(position_float):
        raise ValidationError("position", position, "不能是无穷大")

    if position_float < min_pos:
        raise ValidationError(
            "position",
            position_float,
            f"小于最小位置限制 ({min_pos}mm)"
        )

    if position_float > max_pos:
        raise ValidationError(
            "position",
            position_float,
            f"大于最大位置限制 ({max_pos}mm)"
        )

    return position_float


# ==================== 速度验证器 ====================

def validate_velocity(
    velocity: float,
    *,
    min_vel: float = MIN_VELOCITY_MM_S,
    max_vel: float = MAX_VELOCITY_MM_S
) -> float:
    """
    验证速度参数。

    速度参数规则：
        - 必须是数值类型
        - 不能是NaN或无穷大
        - 必须是非负数
        - 必须在指定范围内

    Args:
        velocity: 待验证的速度值（毫米/秒）。
        min_vel: 最小速度限制，默认为0.0mm/s。
        max_vel: 最大速度限制，默认为500.0mm/s。

    Returns:
        float: 验证通过的速度值。

    Raises:
        ValidationError: 速度参数无效时抛出。

    Example:
        >>> validate_velocity(100.0)
        100.0
        >>> validate_velocity(-10.0)  # 负速度
        ValidationError: 验证失败 [velocity]: 不能为负数
    """
    import math

    if not isinstance(velocity, (int, float)):
        raise ValidationError("velocity", velocity, "必须是数值类型")

    velocity_float = float(velocity)

    if math.isnan(velocity_float):
        raise ValidationError("velocity", velocity, "不能是NaN")

    if math.isinf(velocity_float):
        raise ValidationError("velocity", velocity, "不能是无穷大")

    if velocity_float < min_vel:
        raise ValidationError(
            "velocity",
            velocity_float,
            f"小于最小速度限制 ({min_vel}mm/s)"
        )

    if velocity_float > max_vel:
        raise ValidationError(
            "velocity",
            velocity_float,
            f"大于最大速度限制 ({max_vel}mm/s)"
        )

    return velocity_float


# ==================== 加速度验证器 ====================

def validate_acceleration(acceleration: float) -> float:
    """
    验证加速度参数。

    加速度参数规则：
        - 必须是数值类型
        - 不能是NaN或无穷大
        - 必须是正数

    Args:
        acceleration: 待验证的加速度值（毫米/秒²）。

    Returns:
        float: 验证通过的加速度值。

    Raises:
        ValidationError: 加速度参数无效时抛出。

    Example:
        >>> validate_acceleration(50.0)
        50.0
    """
    import math

    if not isinstance(acceleration, (int, float)):
        raise ValidationError("acceleration", acceleration, "必须是数值类型")

    accel_float = float(acceleration)

    if math.isnan(accel_float):
        raise ValidationError("acceleration", acceleration, "不能是NaN")

    if math.isinf(accel_float):
        raise ValidationError("acceleration", acceleration, "不能是无穷大")

    if accel_float <= 0:
        raise ValidationError("acceleration", accel_float, "必须是正数")

    return accel_float


# ==================== 字符串清理器 ====================

def sanitize_string(
    value: str,
    *,
    max_length: int = 1000,
    strip_whitespace: bool = True,
    allow_empty: bool = False
) -> str:
    """
    清理字符串输入。

    清理规则：
        - 去除首尾空白（可选）
        - 限制最大长度
        - 检查空字符串

    Args:
        value: 待清理的字符串。
        max_length: 最大长度限制，默认1000。
        strip_whitespace: 是否去除首尾空白，默认True。
        allow_empty: 是否允许空字符串，默认False。

    Returns:
        str: 清理后的字符串。

    Raises:
        ValidationError: 字符串无效时抛出。

    Example:
        >>> sanitize_string("  hello  ")
        'hello'
        >>> sanitize_string("", allow_empty=True)
        ''
    """
    if not isinstance(value, str):
        raise ValidationError("string", value, "必须是字符串类型")

    result = value.strip() if strip_whitespace else value

    if not allow_empty and not result:
        raise ValidationError("string", value, "不能为空字符串")

    if len(result) > max_length:
        raise ValidationError(
            "string",
            f"(长度: {len(result)})",
            f"超过最大长度限制 ({max_length})"
        )

    return result


# ==================== 温度验证器 ====================

def validate_temperature(
    temperature: float,
    *,
    min_temp: float = -273.15,
    max_temp: float = 1000.0
) -> float:
    """
    验证温度参数。

    温度参数规则：
        - 必须是数值类型
        - 不能是NaN或无穷大
        - 必须在绝对零度以上

    Args:
        temperature: 待验证的温度值（摄氏度）。
        min_temp: 最小温度限制，默认为绝对零度。
        max_temp: 最大温度限制，默认为1000.0°C。

    Returns:
        float: 验证通过的温度值。

    Raises:
        ValidationError: 温度参数无效时抛出。
    """
    import math

    if not isinstance(temperature, (int, float)):
        raise ValidationError("temperature", temperature, "必须是数值类型")

    temp_float = float(temperature)

    if math.isnan(temp_float):
        raise ValidationError("temperature", temperature, "不能是NaN")

    if math.isinf(temp_float):
        raise ValidationError("temperature", temperature, "不能是无穷大")

    if temp_float < min_temp:
        raise ValidationError(
            "temperature",
            temp_float,
            f"低于最小温度限制 ({min_temp}°C)"
        )

    if temp_float > max_temp:
        raise ValidationError(
            "temperature",
            temp_float,
            f"超过最大温度限制 ({max_temp}°C)"
        )

    return temp_float


# ==================== 电流验证器 ====================

def validate_current(
    current: float,
    *,
    min_current: float = -10.0,
    max_current: float = 10.0
) -> float:
    """
    验证电流参数。

    电流参数规则：
        - 必须是数值类型
        - 不能是NaN或无穷大
        - 必须在指定范围内

    Args:
        current: 待验证的电流值（安培）。
        min_current: 最小电流限制，默认为-10.0A。
        max_current: 最大电流限制，默认为10.0A。

    Returns:
        float: 验证通过的电流值。

    Raises:
        ValidationError: 电流参数无效时抛出。
    """
    import math

    if not isinstance(current, (int, float)):
        raise ValidationError("current", current, "必须是数值类型")

    current_float = float(current)

    if math.isnan(current_float):
        raise ValidationError("current", current, "不能是NaN")

    if math.isinf(current_float):
        raise ValidationError("current", current, "不能是无穷大")

    if current_float < min_current:
        raise ValidationError(
            "current",
            current_float,
            f"低于最小电流限制 ({min_current}A)"
        )

    if current_float > max_current:
        raise ValidationError(
            "current",
            current_float,
            f"超过最大电流限制 ({max_current}A)"
        )

    return current_float


# ==================== 电压验证器 ====================

def validate_voltage(
    voltage: float,
    *,
    min_voltage: float = 0.0,
    max_voltage: float = 200.0
) -> float:
    """
    验证电压参数。

    电压参数规则：
        - 必须是数值类型
        - 不能是NaN或无穷大
        - 必须在指定范围内

    Args:
        voltage: 待验证的电压值（伏特）。
        min_voltage: 最小电压限制，默认为0.0V。
        max_voltage: 最大电压限制，默认为200.0V。

    Returns:
        float: 验证通过的电压值。

    Raises:
        ValidationError: 电压参数无效时抛出。
    """
    import math

    if not isinstance(voltage, (int, float)):
        raise ValidationError("voltage", voltage, "必须是数值类型")

    voltage_float = float(voltage)

    if math.isnan(voltage_float):
        raise ValidationError("voltage", voltage, "不能是NaN")

    if math.isinf(voltage_float):
        raise ValidationError("voltage", voltage, "不能是无穷大")

    if voltage_float < min_voltage:
        raise ValidationError(
            "voltage",
            voltage_float,
            f"低于最小电压限制 ({min_voltage}V)"
        )

    if voltage_float > max_voltage:
        raise ValidationError(
            "voltage",
            voltage_float,
            f"超过最大电压限制 ({max_voltage}V)"
        )

    return voltage_float
