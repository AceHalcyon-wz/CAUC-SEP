"""
温度控制数据模型

文件名: temperature.py
路径: backend/schemas/
功能: 定义温度控制相关的请求/响应模型，包含温度设定、程序控制、PID参数等
作者: Backend Engineer Agent
创建日期: 2026-03-14
依赖: pydantic, typing

温度范围：
- 最低温度: 77K（液氮温度）
- 最高温度: 400K

控制功能：
- 温度设定点控制
- 温度程序控制（多段升温/降温）
- PID参数调节
- 保护配置（高温/低温/变化率保护）
"""

from typing import Any

from pydantic import BaseModel, Field


# 温度范围常量
TEMP_MIN_K = 77.0
TEMP_MAX_K = 400.0


class TemperatureSetpointRequest(BaseModel):
    """
    温度设定点请求。

    用于设置温度控制器的目标温度。

    Attributes:
        temperature: 目标温度(K)，范围: 77K-400K

    Validation Rules:
        - temperature: 必须在77K-400K范围内

    Note:
        温度范围受液氮釜温控系统限制：
        - 最低温度: 77K（液氮沸点）
        - 最高温度: 400K（加热器限制）

    Example:
        >>> request = TemperatureSetpointRequest(temperature=300.0)
        >>> # 设置目标温度为300K（约27°C）
    """

    temperature: float = Field(
        ...,
        description="目标温度(K)，范围: 77K-400K",
        ge=TEMP_MIN_K,
        le=TEMP_MAX_K,
    )


class TemperatureProgramSegmentRequest(BaseModel):
    """
    温度程序段请求。

    定义温度程序中的单个程序段。

    Attributes:
        target_temperature: 目标温度(K)，范围: 77K-400K
        ramp_rate: 升温/降温速率(K/min)，范围: -10到10
            - 正值: 升温
            - 负值: 降温
            - 0: 立即跳转（不推荐）
            默认1.0
        hold_time: 保持时间(秒)，>= 0，默认0.0

    Validation Rules:
        - target_temperature: 必须在77K-400K范围内
        - ramp_rate: 必须在-10到10范围内
        - hold_time: 不能为负

    Example:
        >>> segment = TemperatureProgramSegmentRequest(
        ...     target_temperature=300.0,
        ...     ramp_rate=2.0,  # 以2K/min升温
        ...     hold_time=600.0  # 保持10分钟
        ... )
    """

    target_temperature: float = Field(
        ...,
        description="目标温度(K)，范围: 77K-400K",
        ge=TEMP_MIN_K,
        le=TEMP_MAX_K,
    )
    ramp_rate: float = Field(
        1.0,
        description="升温/降温速率(K/min)，范围: -10到10，正值升温，负值降温，0表示立即跳转",
        ge=-10.0,
        le=10.0,
    )
    hold_time: float = Field(
        0.0,
        description="保持时间(秒)，>= 0",
        ge=0.0,
    )


class TemperatureProgramRequest(BaseModel):
    """
    温度程序请求。

    用于定义完整的多段温度控制程序。

    Attributes:
        segments: 温度程序段列表，至少1段

    Validation Rules:
        - segments: 至少包含1个程序段
        - 程序段按顺序执行

    Example:
        >>> program = TemperatureProgramRequest(
        ...     segments=[
        ...         TemperatureProgramSegmentRequest(target_temperature=300.0, ramp_rate=2.0, hold_time=600.0),
        ...         TemperatureProgramSegmentRequest(target_temperature=350.0, ramp_rate=1.0, hold_time=300.0),
        ...         TemperatureProgramSegmentRequest(target_temperature=77.0, ramp_rate=-5.0, hold_time=0.0),
        ...     ]
        ... )
    """

    segments: list[TemperatureProgramSegmentRequest] = Field(
        ...,
        description="温度程序段列表",
        min_length=1,
    )


class PIDParametersRequest(BaseModel):
    """
    PID参数请求。

    用于设置温度控制器的PID参数。

    Attributes:
        kp: 比例系数(Kp)，范围: 0.1-100
        ki: 积分系数(Ki)，范围: 0.001-10
        kd: 微分系数(Kd)，范围: 0.001-10
        setpoint: 设定温度(K)，范围: 77K-400K

    Validation Rules:
        - 所有参数必须在指定范围内
        - PID参数需要根据实际系统调优

    Note:
        PID参数调优建议：
        - Kp: 影响响应速度，过大可能导致振荡
        - Ki: 消除稳态误差，过大可能导致超调
        - Kd: 抑制振荡，过大可能导致噪声放大

    Example:
        >>> pid = PIDParametersRequest(
        ...     kp=10.0,
        ...     ki=0.5,
        ...     kd=1.0,
        ...     setpoint=300.0
        ... )
    """

    kp: float = Field(
        ...,
        description="比例系数(Kp)，范围: 0.1-100",
        ge=0.1,
        le=100.0,
    )
    ki: float = Field(
        ...,
        description="积分系数(Ki)，范围: 0.001-10",
        ge=0.001,
        le=10.0,
    )
    kd: float = Field(
        ...,
        description="微分系数(Kd)，范围: 0.001-10",
        ge=0.001,
        le=10.0,
    )
    setpoint: float = Field(
        ...,
        description="设定温度(K)，范围: 77K-400K",
        ge=TEMP_MIN_K,
        le=TEMP_MAX_K,
    )


class ProtectionConfigRequest(BaseModel):
    """
    温度保护配置请求。

    用于设置温度控制器的安全保护阈值。

    Attributes:
        max_temperature: 高温保护阈值(K)，超过此温度触发保护，默认450.0
        min_temperature: 低温保护阈值(K)，低于此温度触发保护，默认70.0
        max_deviation: 最大温度变化率限制(K/min)，超过此速率触发保护，默认20.0

    Validation Rules:
        - max_temperature: 必须>=400K且<=500K
        - min_temperature: 必须>=50K且<=77K
        - max_deviation: 必须>=1.0且<=50.0

    Warning:
        保护触发后会停止加热器，需要手动复位才能继续操作。

    Example:
        >>> protection = ProtectionConfigRequest(
        ...     max_temperature=450.0,
        ...     min_temperature=70.0,
        ...     max_deviation=20.0
        ... )
    """

    max_temperature: float = Field(
        450.0,
        description="高温保护阈值(K)，超过此温度触发保护",
        ge=TEMP_MAX_K,
        le=500.0,
    )
    min_temperature: float = Field(
        70.0,
        description="低温保护阈值(K)，低于此温度触发保护",
        ge=50.0,
        le=TEMP_MIN_K,
    )
    max_deviation: float = Field(
        20.0,
        description="最大温度变化率限制(K/min)，超过此速率触发保护",
        ge=1.0,
        le=50.0,
    )


class TemperatureStatusResponse(BaseModel):
    """
    温度控制器状态响应。

    返回温度控制器的完整状态信息。

    Attributes:
        device_id: 设备唯一标识符
        status: 设备状态，如 'connected', 'disconnected', 'error'
        current_temperature: 当前温度(K)，范围: 77K-400K
        target_temperature: 目标温度(K)，范围: 77K-400K
        heater_power: 加热功率百分比(%)，范围: 0-100
        pid_enabled: PID控制是否启用
        program_running: 温度程序是否运行中
        program_segment: 当前程序段索引，从0开始
        protection_active: 保护是否激活
        protection_type: 保护类型，如 'high_temp', 'low_temp', 'deviation'，可选
        connected: 是否已连接
        simulation: 是否仿真模式

    Example:
        >>> response = await api.get_temperature_status()
        >>> print(f"当前温度: {response.current_temperature}K")
        >>> print(f"目标温度: {response.target_temperature}K")
        >>> if response.protection_active:
        ...     print(f"保护激活: {response.protection_type}")
    """

    device_id: str = Field(..., description="设备ID")
    status: str = Field(..., description="设备状态")
    current_temperature: float = Field(..., description="当前温度(K)，范围: 77K-400K")
    target_temperature: float = Field(..., description="目标温度(K)，范围: 77K-400K")
    heater_power: float = Field(..., description="加热功率百分比(%)")
    pid_enabled: bool = Field(..., description="PID控制是否启用")
    program_running: bool = Field(..., description="温度程序是否运行中")
    program_segment: int = Field(..., description="当前程序段索引")
    protection_active: bool = Field(..., description="保护是否激活")
    protection_type: str | None = Field(None, description="保护类型")
    connected: bool = Field(..., description="是否已连接")
    simulation: bool = Field(..., description="是否仿真模式")


class TemperatureHistoryRequest(BaseModel):
    """
    温度历史记录请求。

    用于查询温度控制的历史数据。

    Attributes:
        duration_seconds: 历史记录时长(秒)，范围: 1-3600，默认60.0

    Validation Rules:
        - duration_seconds: 必须在1-3600秒范围内

    Example:
        >>> request = TemperatureHistoryRequest(duration_seconds=300.0)
        >>> # 查询最近5分钟的温度历史
    """

    duration_seconds: float = Field(
        60.0,
        description="历史记录时长(秒)，默认60秒",
        ge=1.0,
        le=3600.0,
    )


class TemperatureHistoryRecord(BaseModel):
    """
    温度历史记录项。

    单个时间点的温度数据记录。

    Attributes:
        timestamp: 时间戳，相对于记录开始时间(秒)
        temperature: 温度值(K)
        target: 目标温度(K)
        power: 加热功率(%)
    """

    timestamp: float = Field(..., description="时间戳")
    temperature: float = Field(..., description="温度值(K)")
    target: float = Field(..., description="目标温度(K)")
    power: float = Field(..., description="加热功率(%)")


class TemperatureHistoryResponse(BaseModel):
    """
    温度历史记录响应。

    返回温度历史数据。

    Attributes:
        success: 操作是否成功
        message: 操作消息
        timestamps: 时间戳列表(秒)
        temperatures: 温度值列表(K)
        setpoints: 设定温度列表(K)

    Note:
        三个列表长度相同，索引一一对应。
    """

    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作消息")
    timestamps: list[float] = Field(..., description="时间戳列表")
    temperatures: list[float] = Field(..., description="温度值列表(K)")
    setpoints: list[float] = Field(..., description="设定温度列表(K)")
