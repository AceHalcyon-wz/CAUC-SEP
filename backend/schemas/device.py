"""
文件名: device.py
路径: backend/schemas/
功能: 设备相关 Schema，定义设备信息、状态、控制请求/响应模型
版本: v1.0
作者: Backend Engineer Agent
创建日期: 2026-03-15
依赖: pydantic, enum, typing, datetime

设备类型：
- STEPPER: 步进电机控制器
- ELECTROMAGNET: 电磁铁电源
- TEMPERATURE: 温度控制器
- PIEZO: 压电陶瓷控制器
- AMMETER: 皮安表/微电流采集器

设备状态：
- DISCONNECTED: 未连接
- CONNECTING: 连接中
- READY: 就绪
- RUNNING: 运行中
- ERROR: 错误
- EMERGENCY_STOP: 急停状态
"""

from enum import Enum
from typing import Optional, List, Any
from datetime import datetime

from pydantic import BaseModel, Field


class DeviceStatus(str, Enum):
    """
    设备状态枚举。

    定义设备可能的状态值。

    Attributes:
        DISCONNECTED: 未连接状态。
        CONNECTING: 连接中状态。
        READY: 就绪状态，已连接但未运行。
        RUNNING: 运行中状态，正在执行操作。
        ERROR: 错误状态，设备发生故障。
        EMERGENCY_STOP: 急停状态，紧急停止触发。
    """

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    READY = "ready"
    RUNNING = "running"
    ERROR = "error"
    EMERGENCY_STOP = "emergency_stop"


class DeviceType(str, Enum):
    """
    设备类型枚举。

    定义系统中支持的设备类型。

    Attributes:
        STEPPER: 步进电机控制器。
        ELECTROMAGNET: 电磁铁电源。
        TEMPERATURE: 温度控制器。
        PIEZO: 压电陶瓷控制器。
        AMMETER: 皮安表/微电流采集器。
    """

    STEPPER = "stepper"
    ELECTROMAGNET = "electromagnet"
    TEMPERATURE = "temperature"
    PIEZO = "piezo"
    AMMETER = "ammeter"


class DeviceInfoResponse(BaseModel):
    """
    设备基本信息响应模型。

    描述设备的基本信息，用于设备列表和状态查询。

    Attributes:
        id: 设备唯一标识符。
        name: 设备名称，用户自定义。
        type: 设备类型。
        status: 当前状态。
        connected: 是否已连接。
        simulation: 是否仿真模式。
        connected_at: 连接时间，未连接时为 None。
        error_message: 错误信息，无错误时为 None。

    Example:
        >>> device = DeviceInfoResponse(
        ...     id="motor-001",
        ...     name="主电机",
        ...     type=DeviceType.STEPPER,
        ...     status=DeviceStatus.READY,
        ...     connected=True,
        ...     simulation=False
        ... )
    """

    id: str = Field(..., description="设备唯一标识")
    name: str = Field(..., description="设备名称")
    type: DeviceType = Field(..., description="设备类型")
    status: DeviceStatus = Field(..., description="当前状态")
    connected: bool = Field(..., description="是否已连接")
    simulation: bool = Field(..., description="是否仿真模式")
    connected_at: datetime | None = Field(default=None, description="连接时间")
    error_message: str | None = Field(default=None, description="错误信息")


class DeviceConnectRequest(BaseModel):
    """
    设备连接请求模型。

    用于建立设备连接时传递连接参数。

    Attributes:
        port: 通信端口，如 'COM3' 或 '/dev/ttyUSB0'。
        baud_rate: 波特率，默认根据设备类型确定。
        slave_id: 从站 ID，用于 Modbus 设备。
        timeout: 超时时间(秒)，默认 1.0。
        simulation: 是否仿真模式，可选。

    Example:
        >>> request = DeviceConnectRequest(
        ...     port="COM3",
        ...     baud_rate=9600,
        ...     slave_id=1
        ... )
    """

    port: str | None = Field(default=None, description="通信端口")
    baud_rate: int | None = Field(default=None, description="波特率")
    slave_id: int | None = Field(default=None, description="从站 ID")
    timeout: float | None = Field(default=1.0, description="超时时间 (s)")
    simulation: bool | None = Field(default=None, description="是否仿真模式")


class DeviceConnectResponse(BaseModel):
    """
    设备连接响应模型。

    描述设备连接操作的结果。

    Attributes:
        device_id: 设备 ID。
        connected: 是否连接成功。
        message: 连接消息，描述连接结果。

    Example:
        >>> response = DeviceConnectResponse(
        ...     device_id="motor-001",
        ...     connected=True,
        ...     message="设备连接成功"
        ... )
    """

    device_id: str = Field(..., description="设备 ID")
    connected: bool = Field(..., description="是否连接成功")
    message: str = Field(..., description="连接消息")


class StepperMotorStatus(DeviceInfoResponse):
    """
    步进电机状态模型。

    继承设备基本信息，增加电机特有属性。

    Attributes:
        type: 设备类型，固定为 STEPPER。
        position: 当前位置(mm)。
        target_position: 目标位置(mm)。
        speed: 当前速度(steps/s)。
        is_moving: 是否正在移动。
        positive_limit: 正向软限位(mm)。
        negative_limit: 负向软限位(mm)。
        enabled: 是否使能。

    Example:
        >>> motor = StepperMotorStatus(
        ...     id="motor-001",
        ...     name="主电机",
        ...     status=DeviceStatus.RUNNING,
        ...     connected=True,
        ...     simulation=False,
        ...     position=50.0,
        ...     target_position=100.0,
        ...     speed=1000,
        ...     is_moving=True,
        ...     positive_limit=200.0,
        ...     negative_limit=-200.0,
        ...     enabled=True
        ... )
    """

    type: DeviceType = DeviceType.STEPPER
    position: float = Field(..., description="当前位置 (mm)")
    target_position: float = Field(..., description="目标位置 (mm)")
    speed: int = Field(..., description="当前速度 (steps/s)")
    is_moving: bool = Field(..., description="是否正在移动")
    positive_limit: float = Field(..., description="正向软限位 (mm)")
    negative_limit: float = Field(..., description="负向软限位 (mm)")
    enabled: bool = Field(..., description="是否使能")


class StepperMoveRequest(BaseModel):
    """
    步进电机移动请求模型。

    用于控制电机移动到指定位置。

    Attributes:
        position: 目标位置(mm)，必填。
        speed: 移动速度(steps/s)，范围1-10000，默认1000。
        relative: 是否相对移动，默认 False(绝对移动)。

    Example:
        >>> request = StepperMoveRequest(
        ...     position=100.0,
        ...     speed=2000,
        ...     relative=False
        ... )
    """

    position: float = Field(..., description="目标位置 (mm)")
    speed: int | None = Field(
        default=1000,
        ge=1,
        le=10000,
        description="移动速度 (steps/s)",
    )
    relative: bool | None = Field(default=False, description="是否相对移动")


class ElectromagnetStatus(DeviceInfoResponse):
    """
    电磁铁状态模型。

    继承设备基本信息，增加电磁铁特有属性。

    Attributes:
        type: 设备类型，固定为 ELECTROMAGNET。
        current: 当前电流(A)。
        target_current: 目标电流(A)。
        max_current: 最大电流(A)。
        output_enabled: 是否输出使能。

    Example:
        >>> em = ElectromagnetStatus(
        ...     id="em-001",
        ...     name="主电磁铁",
        ...     status=DeviceStatus.READY,
        ...     connected=True,
        ...     simulation=False,
        ...     current=5.0,
        ...     target_current=5.0,
        ...     max_current=20.0,
        ...     output_enabled=True
        ... )
    """

    type: DeviceType = DeviceType.ELECTROMAGNET
    current: float = Field(..., description="当前电流 (A)")
    target_current: float = Field(..., description="目标电流 (A)")
    max_current: float = Field(..., description="最大电流 (A)")
    output_enabled: bool = Field(..., description="是否输出使能")


class ElectromagnetControlRequest(BaseModel):
    """
    电磁铁控制请求模型。

    用于控制电磁铁输出电流。

    Attributes:
        current: 目标电流(A)，必须 >= 0。
        enabled: 是否使能输出，默认 True。

    Example:
        >>> request = ElectromagnetControlRequest(
        ...     current=10.0,
        ...     enabled=True
        ... )
    """

    current: float = Field(..., ge=0, description="目标电流 (A)")
    enabled: bool | None = Field(default=True, description="是否使能输出")


class TemperatureControllerStatus(DeviceInfoResponse):
    """
    温控器状态模型。

    继承设备基本信息，增加温控器特有属性。

    Attributes:
        type: 设备类型，固定为 TEMPERATURE。
        temperature: 当前温度(°C)。
        target_temperature: 目标温度(°C)。
        is_heating: 是否正在加热。
        is_cooling: 是否正在冷却。

    Example:
        >>> tc = TemperatureControllerStatus(
        ...     id="tc-001",
        ...     name="主温控器",
        ...     status=DeviceStatus.RUNNING,
        ...     connected=True,
        ...     simulation=False,
        ...     temperature=25.0,
        ...     target_temperature=100.0,
        ...     is_heating=True,
        ...     is_cooling=False
        ... )
    """

    type: DeviceType = DeviceType.TEMPERATURE
    temperature: float = Field(..., description="当前温度 (°C)")
    target_temperature: float = Field(..., description="目标温度 (°C)")
    is_heating: bool = Field(..., description="是否正在加热")
    is_cooling: bool = Field(..., description="是否正在冷却")


class TemperatureControlRequest(BaseModel):
    """
    温控器控制请求模型。

    用于控制温控器设定目标温度。

    Attributes:
        temperature: 目标温度(°C)，必填。
        pid_kp: PID 比例系数，可选。
        pid_ki: PID 积分系数，可选。
        pid_kd: PID 微分系数，可选。

    Example:
        >>> request = TemperatureControlRequest(
        ...     temperature=100.0,
        ...     pid_kp=1.0,
        ...     pid_ki=0.1,
        ...     pid_kd=0.01
        ... )
    """

    temperature: float = Field(..., description="目标温度 (°C)")
    pid_kp: float | None = Field(default=None, description="PID 比例系数")
    pid_ki: float | None = Field(default=None, description="PID 积分系数")
    pid_kd: float | None = Field(default=None, description="PID 微分系数")


class PiezoControllerStatus(DeviceInfoResponse):
    """
    压电控制器状态模型。

    继承设备基本信息，增加压电控制器特有属性。

    Attributes:
        type: 设备类型，固定为 PIEZO。
        voltages: 各通道电压(V)列表。
        displacements: 各通道位移(μm)列表。
        max_voltage: 最大电压(V)。
        channels: 通道数。

    Example:
        >>> piezo = PiezoControllerStatus(
        ...     id="piezo-001",
        ...     name="主压电控制器",
        ...     status=DeviceStatus.READY,
        ...     connected=True,
        ...     simulation=False,
        ...     voltages=[50.0, 50.0, 50.0],
        ...     displacements=[10.0, 10.0, 10.0],
        ...     max_voltage=150.0,
        ...     channels=3
        ... )
    """

    type: DeviceType = DeviceType.PIEZO
    voltages: list[float] = Field(..., description="各通道电压 (V)")
    displacements: list[float] = Field(..., description="各通道位移 (μm)")
    max_voltage: float = Field(..., description="最大电压 (V)")
    channels: int = Field(..., description="通道数")


class PiezoControlRequest(BaseModel):
    """
    压电控制请求模型。

    用于控制压电陶瓷控制器输出电压。

    Attributes:
        channel: 通道索引，从0开始。
        voltage: 目标电压(V)，必须 >= 0。

    Example:
        >>> request = PiezoControlRequest(
        ...     channel=0,
        ...     voltage=100.0
        ... )
    """

    channel: int = Field(..., ge=0, description="通道索引")
    voltage: float = Field(..., ge=0, description="目标电压 (V)")


class PicoammeterStatus(DeviceInfoResponse):
    """
    皮安表状态模型。

    继承设备基本信息，增加皮安表特有属性。

    Attributes:
        type: 设备类型，固定为 AMMETER。
        current: 当前电流读数(A)。
        range: 电流范围，如 '1nA', '10nA', '100nA'。
        sample_rate: 采样率(Hz)。
        is_sampling: 是否正在采集。

    Example:
        >>> ammeter = PicoammeterStatus(
        ...     id="ammeter-001",
        ...     name="主皮安表",
        ...     status=DeviceStatus.RUNNING,
        ...     connected=True,
        ...     simulation=False,
        ...     current=1.5e-9,
        ...     range="10nA",
        ...     sample_rate=100.0,
        ...     is_sampling=True
        ... )
    """

    type: DeviceType = DeviceType.AMMETER
    current: float = Field(..., description="当前电流读数 (A)")
    range: str = Field(..., description="电流范围")
    sample_rate: float = Field(..., description="采样率 (Hz)")
    is_sampling: bool = Field(..., description="是否正在采集")


# 保留原有的 DeviceInfo 以兼容现有代码
class DeviceInfo(BaseModel):
    """
    设备信息模型（兼容旧版）。

    描述系统中已注册设备的基本信息。

    Attributes:
        device_id: 设备唯一标识符，UUID格式。
        device_type: 设备类型。
        device_name: 设备名称，用户自定义，可选。
        connection_params: 连接参数JSON字符串，可选。
        status: 设备状态。
        created_at: 设备注册时间(ISO格式)。

    Deprecated:
        建议使用 DeviceInfoResponse 替代。
    """

    device_id: str
    device_type: str
    device_name: str | None = None
    connection_params: str | None = None
    status: str
    created_at: str
