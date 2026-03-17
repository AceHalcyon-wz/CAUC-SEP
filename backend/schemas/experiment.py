"""
文件名: experiment.py
路径: backend/schemas/
功能: 实验相关 Schema，定义实验信息、参数、数据请求/响应模型
版本: v1.0
作者: Backend Engineer Agent
创建日期: 2026-03-15
依赖: pydantic, typing, datetime

实验状态：
- created: 已创建，未开始
- running: 运行中
- paused: 已暂停
- completed: 已完成
- cancelled: 已取消
"""

from enum import Enum
from typing import Optional, List, Any
from datetime import datetime

from pydantic import BaseModel, Field


class ExperimentStatus(str, Enum):
    """
    实验状态枚举。

    定义实验可能的状态值。

    Attributes:
        CREATED: 已创建，未开始。
        RUNNING: 运行中。
        PAUSED: 已暂停。
        COMPLETED: 已完成。
        CANCELLED: 已取消。
    """

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ExperimentResponse(BaseModel):
    """
    实验信息响应模型。

    描述实验的完整信息，包括状态和时间戳。

    Attributes:
        id: 实验唯一标识符，自增整数。
        name: 实验名称。
        description: 实验描述。
        status: 实验状态。
        created_at: 创建时间。
        started_at: 开始时间，未开始时为 None。
        completed_at: 完成时间，未完成时为 None。
        parameters: 实验参数，可选。

    Example:
        >>> experiment = ExperimentResponse(
        ...     id=1,
        ...     name="磁滞回线测量实验#1",
        ...     description="室温下Fe3O4样品的磁滞回线测量",
        ...     status=ExperimentStatus.RUNNING,
        ...     created_at=datetime.utcnow(),
        ...     started_at=datetime.utcnow()
        ... )
    """

    id: int = Field(..., description="实验唯一标识")
    name: str = Field(..., description="实验名称")
    description: str = Field(default="", description="实验描述")
    status: ExperimentStatus = Field(..., description="实验状态")
    created_at: datetime = Field(..., description="创建时间")
    started_at: datetime | None = Field(default=None, description="开始时间")
    completed_at: datetime | None = Field(default=None, description="完成时间")
    parameters: dict[str, Any] | None = Field(default=None, description="实验参数")


class ExperimentCreateRequest(BaseModel):
    """
    实验创建请求模型。

    用于创建新的实验记录。

    Attributes:
        name: 实验名称，长度1-100字符。
        description: 实验描述，可选。
        parameters: 实验参数，可选。

    Example:
        >>> request = ExperimentCreateRequest(
        ...     name="磁滞回线测量实验#1",
        ...     description="室温下Fe3O4样品的磁滞回线测量"
        ... )
    """

    name: str = Field(..., description="实验名称", min_length=1, max_length=100)
    description: str = Field(default="", description="实验描述")
    parameters: dict[str, Any] | None = Field(default=None, description="实验参数")


class ExperimentUpdateRequest(BaseModel):
    """
    实验更新请求模型。

    用于更新实验的基本信息。

    Attributes:
        name: 实验名称，可选。
        description: 实验描述，可选。

    Example:
        >>> request = ExperimentUpdateRequest(
        ...     name="更新后的实验名称",
        ...     description="更新后的描述"
        ... )
    """

    name: str | None = Field(
        default=None, description="实验名称", min_length=1, max_length=100
    )
    description: str | None = Field(default=None, description="实验描述")


class ExperimentParameters(BaseModel):
    """
    实验参数模型。

    定义实验运行时的参数配置。

    Attributes:
        motor_start: 电机起始位置(mm)。
        motor_end: 电机结束位置(mm)。
        motor_speed: 电机移动速度(steps/s)。
        electromagnet_max_current: 电磁铁最大电流(A)。
        electromagnet_min_current: 电磁铁最小电流(A)。
        current_step: 电流步进值(A)。
        sample_rate: 数据采样率(Hz)。
        temperature: 目标温度(°C)，可选。

    Example:
        >>> params = ExperimentParameters(
        ...     motor_start=0.0,
        ...     motor_end=100.0,
        ...     motor_speed=1000,
        ...     electromagnet_max_current=10.0,
        ...     electromagnet_min_current=0.0,
        ...     current_step=0.5,
        ...     sample_rate=100.0
        ... )
    """

    motor_start: float = Field(..., description="电机起始位置 (mm)")
    motor_end: float = Field(..., description="电机结束位置 (mm)")
    motor_speed: int = Field(default=1000, description="电机移动速度 (steps/s)")
    electromagnet_max_current: float = Field(..., description="电磁铁最大电流 (A)")
    electromagnet_min_current: float = Field(default=0.0, description="电磁铁最小电流 (A)")
    current_step: float = Field(default=0.5, description="电流步进值 (A)")
    sample_rate: float = Field(default=100.0, description="数据采样率 (Hz)")
    temperature: float | None = Field(default=None, description="目标温度 (°C)")


class ExperimentDataPoint(BaseModel):
    """
    实验数据点模型。

    描述单个数据采集点的数据。

    Attributes:
        timestamp: 时间戳。
        position: 位置(mm)。
        current: 电流(A)。
        voltage: 电压(V)，可选。
        temperature: 温度(°C)，可选。
        magnetic_field: 磁场强度(T)，可选。

    Example:
        >>> point = ExperimentDataPoint(
        ...     timestamp=datetime.utcnow(),
        ...     position=50.0,
        ...     current=5.0,
        ...     voltage=0.1
        ... )
    """

    timestamp: datetime = Field(..., description="时间戳")
    position: float = Field(..., description="位置 (mm)")
    current: float = Field(..., description="电流 (A)")
    voltage: float | None = Field(default=None, description="电压 (V)")
    temperature: float | None = Field(default=None, description="温度 (°C)")
    magnetic_field: float | None = Field(default=None, description="磁场强度 (T)")


class ExperimentDataResponse(BaseModel):
    """
    实验数据响应模型。

    描述实验数据的响应结构。

    Attributes:
        experiment_id: 实验ID。
        total_points: 数据点总数。
        data: 数据点列表。

    Example:
        >>> response = ExperimentDataResponse(
        ...     experiment_id=1,
        ...     total_points=1000,
        ...     data=[]
        ... )
    """

    experiment_id: int = Field(..., description="实验ID")
    total_points: int = Field(..., description="数据点总数")
    data: list[ExperimentDataPoint] = Field(default_factory=list, description="数据点列表")


# 保留原有的 ExperimentInfo 和 ExperimentRequest 以兼容现有代码
class ExperimentRequest(BaseModel):
    """
    实验创建请求（兼容旧版）。

    用于创建新的实验记录。

    Attributes:
        name: 实验名称，长度1-100字符。
        description: 实验描述，可选。

    Deprecated:
        建议使用 ExperimentCreateRequest 替代。
    """

    name: str = Field(..., description="实验名称", min_length=1, max_length=100)
    description: str = Field(default="", description="实验描述")


class ExperimentInfo(BaseModel):
    """
    实验信息模型（兼容旧版）。

    描述实验的完整信息。

    Attributes:
        id: 实验唯一标识符。
        name: 实验名称。
        description: 实验描述。
        status: 实验状态。
        created_at: 创建时间(ISO格式)。
        started_at: 开始时间，未开始时为 None。
        completed_at: 完成时间，未完成时为 None。

    Deprecated:
        建议使用 ExperimentResponse 替代。
    """

    id: int
    name: str
    description: str
    status: str
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
