"""
文件名: types.py
路径: backend/core/
功能: 项目通用类型定义，提供类型别名、TypedDict 和回调类型
作者: Backend Engineer Agent
创建日期: 2026-03-16
版本: 1.0.0
依赖: typing

类型定义：
    - DeviceStatusValue: 设备状态值类型别名
    - DeviceConfig: 设备配置类型别名
    - PositionData: 位置数据 TypedDict
    - ExperimentData: 实验数据 TypedDict
    - StatusCallback: 状态回调类型别名
    - DataCallback: 数据回调类型别名
"""

from typing import TypeAlias, TypedDict, NotRequired, Required, Any
from collections.abc import Callable, Awaitable


# ==================== 设备类型 ====================

DeviceStatusValue: TypeAlias = str
"""设备状态值类型，如 'disconnected', 'ready', 'busy' 等。"""

DeviceConfig: TypeAlias = dict[str, "str | int | float | bool"]
"""设备配置类型，支持字符串、整数、浮点数和布尔值。"""


# ==================== 位置数据类型 ====================

class PositionData(TypedDict):
    """
    位置数据类型。

    用于表示步进电机或运动设备的位置信息。

    Attributes:
        position_mm: 位置（毫米），浮点数。
        position_steps: 位置（步数），整数。
        timestamp: 时间戳（Unix 时间戳），浮点数。

    Example:
        >>> data: PositionData = {
        ...     "position_mm": 50.5,
        ...     "position_steps": 80800,
        ...     "timestamp": 1710576000.0
        ... }
    """
    position_mm: float
    position_steps: int
    timestamp: float


# ==================== 实验数据类型 ====================

class ExperimentData(TypedDict, total=False):
    """
    实验数据类型。

    用于表示实验记录的数据结构，支持可选字段。

    Attributes:
        experiment_id: 实验唯一标识（必填）。
        name: 实验名称（必填）。
        description: 实验描述（可选）。
        created_at: 创建时间（必填）。
        status: 实验状态（必填）。
        data_points: 数据点列表（可选）。

    Example:
        >>> data: ExperimentData = {
        ...     "experiment_id": 1,
        ...     "name": "磁性测量实验",
        ...     "created_at": "2026-03-16T10:00:00Z",
        ...     "status": "running"
        ... }
    """
    experiment_id: Required[int]
    name: Required[str]
    description: str
    created_at: Required[str]
    status: Required[str]
    data_points: list[dict[str, float]]


# ==================== 回调类型 ====================

StatusCallback: TypeAlias = Callable[[DeviceStatusValue], None]
"""
状态回调函数类型。

用于设备状态变化时的回调通知。

Args:
    status: 设备状态值

Example:
    >>> def on_status_change(status: DeviceStatusValue) -> None:
    ...     print(f"设备状态变更: {status}")
"""

DataCallback: TypeAlias = Callable[[dict[str, Any]], Awaitable[None]]
"""
数据回调函数类型（异步）。

用于设备数据更新时的异步回调处理。

Args:
    data: 设备数据字典

Example:
    >>> async def on_data_update(data: dict[str, Any]) -> None:
    ...     await process_data(data)
"""


# ==================== 速度数据类型 ====================

class VelocityData(TypedDict):
    """
    速度数据类型。

    用于表示运动设备的速度信息。

    Attributes:
        velocity_mm_s: 速度（毫米/秒）。
        direction: 方向（1 为正向，-1 为负向）。
        timestamp: 时间戳。
    """
    velocity_mm_s: float
    direction: int
    timestamp: float


# ==================== 温度数据类型 ====================

class TemperatureData(TypedDict):
    """
    温度数据类型。

    用于表示温度控制器的温度信息。

    Attributes:
        temperature_c: 当前温度（摄氏度）。
        setpoint_c: 设定温度（摄氏度）。
        is_stable: 温度是否稳定。
        timestamp: 时间戳。
    """
    temperature_c: float
    setpoint_c: float
    is_stable: bool
    timestamp: float


# ==================== 电流数据类型 ====================

class CurrentData(TypedDict):
    """
    电流数据类型。

    用于表示皮安计的电流测量数据。

    Attributes:
        current_a: 电流值（安培）。
        range_a: 量程（安培）。
        is_overrange: 是否超量程。
        timestamp: 时间戳。
    """
    current_a: float
    range_a: float
    is_overrange: bool
    timestamp: float


# ==================== 电压数据类型 ====================

class VoltageData(TypedDict):
    """
    电压数据类型。

    用于表示压电陶瓷控制器的电压信息。

    Attributes:
        voltage_v: 当前电压（伏特）。
        setpoint_v: 设定电压（伏特）。
        is_enabled: 是否启用输出。
        timestamp: 时间戳。
    """
    voltage_v: float
    setpoint_v: float
    is_enabled: bool
    timestamp: float


# ==================== 磁场数据类型 ====================

class MagneticFieldData(TypedDict):
    """
    磁场数据类型。

    用于表示电磁铁的磁场信息。

    Attributes:
        field_mt: 磁场强度（毫特斯拉）。
        current_a: 励磁电流（安培）。
        is_enabled: 是否启用输出。
        timestamp: 时间戳。
    """
    field_mt: float
    current_a: float
    is_enabled: bool
    timestamp: float


# ==================== 设备信息类型 ====================

class DeviceInfo(TypedDict):
    """
    设备信息类型。

    用于表示设备的基本信息。

    Attributes:
        device_id: 设备唯一标识。
        device_type: 设备类型。
        status: 设备状态。
        is_connected: 是否已连接。
        firmware_version: 固件版本（可选）。
        serial_number: 序列号（可选）。
    """
    device_id: str
    device_type: str
    status: DeviceStatusValue
    is_connected: bool
    firmware_version: NotRequired[str]
    serial_number: NotRequired[str]


# ==================== 错误信息类型 ====================

class ErrorInfo(TypedDict):
    """
    错误信息类型。

    用于表示设备或操作错误信息。

    Attributes:
        error_code: 错误码。
        error_message: 错误消息。
        timestamp: 错误发生时间戳。
        details: 错误详情（可选）。
    """
    error_code: str
    error_message: str
    timestamp: float
    details: NotRequired[dict[str, Any]]
