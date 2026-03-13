"""
微电流采集数据模型

文件名: ammeter.py
路径: backend/schemas/
功能: 定义微电流采集相关的请求/响应模型，包含采集控制、通道配置、数据读取等
作者: Backend Engineer Agent
创建日期: 2026-03-14
依赖: pydantic

设备说明：
- 支持4通道微电流采集（通道0-3）
- 电流测量范围：1nA ~ 1mA
- 支持多种滤波方式：无滤波、低通滤波、移动平均、中值滤波
"""

from pydantic import BaseModel, Field


class AmmeterStartRequest(BaseModel):
    """
    微电流采集启动请求。

    用于启动微电流采集设备的数据采集任务。

    Attributes:
        sample_rate: 采样率(Hz)，范围1-1000，默认使用设备配置值

    Example:
        >>> request = AmmeterStartRequest(sample_rate=100.0)
        >>> # 以100Hz采样率启动采集
    """

    sample_rate: float | None = Field(
        None,
        description="采样率(Hz)，范围1-1000",
        ge=1.0,
        le=1000.0,
    )


class AmmeterChannelConfigRequest(BaseModel):
    """
    微电流采集通道配置请求。

    用于配置单个采集通道的参数，包括量程、滤波和偏移校准。

    Attributes:
        channel: 通道号，范围0-3
        enabled: 是否启用该通道
        current_range: 电流量程，可选值: 1nA, 10nA, 100nA, 1uA, 10uA, 100uA, 1mA
        filter_type: 滤波类型，可选值: none, lowpass, moving_average, median
        filter_cutoff: 低通滤波截止频率(Hz)，范围0.1-500.0
        filter_window: 移动平均/中值滤波窗口大小，范围1-100
        offset: 电流偏移校准值(pA)，用于消除系统偏移

    Validation Rules:
        - channel: 必须在0-3范围内
        - filter_cutoff: 仅在filter_type为lowpass时有效
        - filter_window: 仅在filter_type为moving_average或median时有效
    """

    channel: int = Field(..., description="通道号(0-3)", ge=0, le=3)
    enabled: bool | None = Field(None, description="是否启用通道")
    current_range: str | None = Field(
        None,
        description="电流量程: 1nA, 10nA, 100nA, 1uA, 10uA, 100uA, 1mA",
    )
    filter_type: str | None = Field(
        None,
        description="滤波类型: none, lowpass, moving_average, median",
    )
    filter_cutoff: float | None = Field(
        None,
        description="低通滤波截止频率(Hz)",
        ge=0.1,
        le=500.0,
    )
    filter_window: int | None = Field(
        None,
        description="移动平均/中值滤波窗口大小",
        ge=1,
        le=100,
    )
    offset: float | None = Field(None, description="电流偏移校准值(pA)")


class AmmeterChannelData(BaseModel):
    """
    微电流采集通道数据。

    单次采样的通道数据，包含电流值、时间戳和信号质量指标。

    Attributes:
        channel: 通道号
        current_pa: 电流值(pA)，经过滤波和校准后的值
        timestamp: 时间戳(秒)，相对于采集开始时间
        snr_db: 信噪比(dB)，衡量信号质量
        raw_current_pa: 原始电流值(pA)，未经滤波处理
        noise_rms_pa: 噪声RMS值(pA)，噪声均方根
        signal_rms_pa: 信号RMS值(pA)，信号均方根
    """

    channel: int = Field(..., description="通道号")
    current_pa: float = Field(..., description="电流值(pA)")
    timestamp: float = Field(..., description="时间戳(秒)")
    snr_db: float = Field(..., description="信噪比(dB)")
    raw_current_pa: float = Field(..., description="原始电流值(pA)")
    noise_rms_pa: float = Field(..., description="噪声RMS值(pA)")
    signal_rms_pa: float = Field(..., description="信号RMS值(pA)")


class AmmeterDataResponse(BaseModel):
    """
    微电流采集数据响应。

    返回采集数据和当前采集状态。

    Attributes:
        success: 操作是否成功
        message: 操作消息，包含错误信息或状态描述
        is_acquiring: 是否正在采集
        data: 通道数据列表，包含所有启用通道的采样数据
    """

    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作消息")
    is_acquiring: bool = Field(..., description="是否正在采集")
    data: list[AmmeterChannelData] = Field(..., description="通道数据列表")


class AmmeterChannelStatus(BaseModel):
    """
    微电流采集通道状态。

    描述单个通道的当前配置状态。

    Attributes:
        enabled: 是否启用
        range: 电流量程
        filter: 滤波类型
        offset: 偏移校准值(pA)
    """

    enabled: bool = Field(..., description="是否启用")
    range: str = Field(..., description="电流量程")
    filter: str = Field(..., description="滤波类型")
    offset: float = Field(..., description="偏移校准值")


class AmmeterStatusResponse(BaseModel):
    """
    微电流采集设备状态响应。

    返回设备的完整状态信息，包括采集状态和各通道配置。

    Attributes:
        device_id: 设备唯一标识符
        status: 设备状态，如 'connected', 'disconnected', 'error'
        simulation: 是否仿真模式
        sample_rate: 当前采样率(Hz)
        is_acquiring: 是否正在采集
        buffer_usage: 各通道缓冲区使用情况(百分比列表)
        channel_configs: 通道配置列表

    Example:
        >>> response = await api.get_ammeter_status()
        >>> print(f"采集状态: {'采集中' if response.is_acquiring else '空闲'}")
    """

    device_id: str = Field(..., description="设备ID")
    status: str = Field(..., description="设备状态")
    simulation: bool = Field(..., description="是否仿真模式")
    sample_rate: float = Field(..., description="采样率(Hz)")
    is_acquiring: bool = Field(..., description="是否正在采集")
    buffer_usage: list[int] = Field(..., description="各通道缓冲区使用情况")
    channel_configs: list[AmmeterChannelStatus] = Field(..., description="通道配置列表")
