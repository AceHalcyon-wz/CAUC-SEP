"""
通用响应模型

文件名: common.py
路径: backend/schemas/
功能: 定义通用的成功/错误响应模型，提供统一的 API 响应格式
作者: Backend Engineer Agent
创建日期: 2026-03-14
依赖: pydantic, enum, typing

错误码分类：
- E1xxx: 设备相关错误（未初始化、未连接、急停、忙碌、设备故障）
- E2xxx: 参数相关错误（无效参数、参数超限、参数缺失）
- E3xxx: 限位相关错误（软限位超限、硬件限位触发）
- E4xxx: 操作相关错误（操作失败、运动失败、连接失败）
- E5xxx: 系统相关错误（内部错误、通信错误、超时错误）
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SuccessResponse(BaseModel):
    """
    通用成功响应。

    所有成功操作的统一响应格式。

    Attributes:
        success: 操作是否成功，始终为True
        message: 操作消息，描述操作结果

    Example:
        >>> response = SuccessResponse(success=True, message="操作成功")
        >>> assert response.success is True
    """

    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作消息")


class ErrorCode(str, Enum):
    """
    API错误代码枚举。

    定义所有可能的错误代码，按类别分组。

    设备错误 (E1xxx):
        - DEVICE_NOT_INITIALIZED: 设备未初始化
        - DEVICE_NOT_CONNECTED: 设备未连接
        - DEVICE_IN_EMERGENCY_STOP: 设备处于急停状态
        - DEVICE_BUSY: 设备忙碌
        - DEVICE_ERROR: 设备故障

    参数错误 (E2xxx):
        - INVALID_PARAMETER: 无效参数
        - PARAM_OUT_OF_RANGE: 参数超限
        - MISSING_PARAMETER: 参数缺失

    限位错误 (E3xxx):
        - SOFT_LIMIT_EXCEEDED: 软限位超限
        - HARDWARE_LIMIT_TRIGGERED: 硬件限位触发

    操作错误 (E4xxx):
        - OPERATION_FAILED: 操作失败
        - MOTION_FAILED: 运动失败
        - CONNECTION_FAILED: 连接失败

    系统错误 (E5xxx):
        - INTERNAL_ERROR: 内部错误
        - COMMUNICATION_ERROR: 通信错误
        - TIMEOUT_ERROR: 超时错误
    """

    DEVICE_NOT_INITIALIZED = "E1001"
    DEVICE_NOT_CONNECTED = "E1002"
    DEVICE_IN_EMERGENCY_STOP = "E1003"
    DEVICE_BUSY = "E1004"
    DEVICE_ERROR = "E1005"

    INVALID_PARAMETER = "E2001"
    PARAM_OUT_OF_RANGE = "E2002"
    MISSING_PARAMETER = "E2003"

    SOFT_LIMIT_EXCEEDED = "E3001"
    HARDWARE_LIMIT_TRIGGERED = "E3002"

    OPERATION_FAILED = "E4001"
    MOTION_FAILED = "E4002"
    CONNECTION_FAILED = "E4003"

    INTERNAL_ERROR = "E5001"
    COMMUNICATION_ERROR = "E5002"
    TIMEOUT_ERROR = "E5003"


class ErrorResponse(BaseModel):
    """
    通用错误响应模型。

    提供统一的错误响应格式，包含错误码、详细信息和时间戳。

    Attributes:
        error_code: 错误代码，如 'E1001', 'E2001' 等
        detail: 错误详情描述，包含具体的错误信息
        timestamp: 错误发生时间戳(ISO格式)，可选
        suggestions: 修复建议列表，帮助用户解决问题，可选

    Example:
        >>> error = ErrorResponse(
        ...     error_code="E1002",
        ...     detail="设备未连接，请检查连接",
        ...     suggestions=["检查USB连接", "确认设备电源已开启"]
        ... )
    """

    error_code: str = Field(..., description="错误代码，如 'INVALID_PARAM', 'DEVICE_ERROR'")
    detail: str = Field(..., description="错误详情描述")
    timestamp: str | None = Field(None, description="错误发生时间戳")
    suggestions: list[str] | None = Field(None, description="修复建议列表")


class ValidationErrorDetail(BaseModel):
    """
    参数验证错误详情。

    描述单个字段的验证失败信息。

    Attributes:
        field: 错误字段名，使用点号表示嵌套字段（如 'config.temperature'）
        value: 错误值，用户提供的原始值
        constraint: 约束条件描述（如 'ge=0', 'max_length=100'）
        message: 错误消息，人类可读的错误描述

    Example:
        >>> detail = ValidationErrorDetail(
        ...     field="temperature",
        ...     value=-10.0,
        ...     constraint="ge=77.0",
        ...     message="温度不能低于77K"
        ... )
    """

    field: str = Field(..., description="错误字段名")
    value: Any = Field(..., description="错误值")
    constraint: str = Field(..., description="约束条件")
    message: str = Field(..., description="错误消息")


class ValidationErrorResponse(BaseModel):
    """
    参数验证错误响应。

    当请求参数验证失败时返回，包含所有验证错误的详细信息。

    Attributes:
        error_code: 错误代码，默认为 'VALIDATION_ERROR'
        detail: 错误概述，描述验证失败的整体情况
        errors: 详细错误列表，包含每个字段的验证错误

    Example:
        >>> response = ValidationErrorResponse(
        ...     detail="参数验证失败",
        ...     errors=[
        ...         ValidationErrorDetail(field="temperature", value=-10.0, ...)
        ...     ]
        ... )
    """

    error_code: str = Field("VALIDATION_ERROR", description="错误代码")
    detail: str = Field(..., description="错误概述")
    errors: list[ValidationErrorDetail] = Field(..., description="详细错误列表")
