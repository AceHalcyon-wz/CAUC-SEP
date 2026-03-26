"""
文件名: high_risk.py
路径: backend/schemas/
功能: 高危操作防护相关 Pydantic 数据模型
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: pydantic, datetime, typing

包含模型：
- HighRiskOperationType: 高危操作类型枚举
- ConfirmationRequest: 二次确认请求模型
- ConfirmationResponse: 二次确认响应模型
- HighRiskOperationLog: 高危操作日志模型
- SessionLockStatus: 会话锁定状态模型
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class HighRiskOperationType(str, Enum):
    """
    高危操作类型枚举。

    定义所有需要二次确认的高危操作类型。

    Attributes:
        FACTORY_RESET: 恢复出厂设置
        MODIFY_SAFETY_LIMIT: 修改安全限位
        DEVICE_CALIBRATION: 设备校准
        CLEAR_EXPERIMENT_DATA: 清除实验数据
        CLEAR_ALARM_HISTORY: 清除报警历史
        MODIFY_COMMUNICATION_CONFIG: 修改通信配置
        EMERGENCY_RESET: 急停复位
        PARAMETER_INIT: 参数初始化
    """

    FACTORY_RESET = "factory_reset"
    MODIFY_SAFETY_LIMIT = "modify_safety_limit"
    DEVICE_CALIBRATION = "device_calibration"
    CLEAR_EXPERIMENT_DATA = "clear_experiment_data"
    CLEAR_ALARM_HISTORY = "clear_alarm_history"
    MODIFY_COMMUNICATION_CONFIG = "modify_communication_config"
    EMERGENCY_RESET = "emergency_reset"
    PARAMETER_INIT = "parameter_init"


class HighRiskOperationCategory(str, Enum):
    """
    高危操作类别枚举。

    Attributes:
        DEVICE: 设备相关操作
        DATA: 数据相关操作
        SAFETY: 安全相关操作
        CONFIG: 配置相关操作
    """

    DEVICE = "device"
    DATA = "data"
    SAFETY = "safety"
    CONFIG = "config"


# 高危操作类型到类别的映射
HIGH_RISK_OPERATION_CATEGORIES: dict[HighRiskOperationType, HighRiskOperationCategory] = {
    HighRiskOperationType.FACTORY_RESET: HighRiskOperationCategory.DEVICE,
    HighRiskOperationType.MODIFY_SAFETY_LIMIT: HighRiskOperationCategory.SAFETY,
    HighRiskOperationType.DEVICE_CALIBRATION: HighRiskOperationCategory.DEVICE,
    HighRiskOperationType.CLEAR_EXPERIMENT_DATA: HighRiskOperationCategory.DATA,
    HighRiskOperationType.CLEAR_ALARM_HISTORY: HighRiskOperationCategory.DATA,
    HighRiskOperationType.MODIFY_COMMUNICATION_CONFIG: HighRiskOperationCategory.CONFIG,
    HighRiskOperationType.EMERGENCY_RESET: HighRiskOperationCategory.SAFETY,
    HighRiskOperationType.PARAMETER_INIT: HighRiskOperationCategory.CONFIG,
}

# 高危操作描述映射
HIGH_RISK_OPERATION_DESCRIPTIONS: dict[HighRiskOperationType, str] = {
    HighRiskOperationType.FACTORY_RESET: "恢复出厂设置将清除所有用户配置，设备将恢复到初始状态",
    HighRiskOperationType.MODIFY_SAFETY_LIMIT: "修改安全限位可能导致设备超出安全范围，造成机械损坏",
    HighRiskOperationType.DEVICE_CALIBRATION: "设备校准将修改设备参数，可能影响测量精度",
    HighRiskOperationType.CLEAR_EXPERIMENT_DATA: "清除实验数据将永久删除所有实验记录，无法恢复",
    HighRiskOperationType.CLEAR_ALARM_HISTORY: "清除报警历史将删除所有报警记录，可能影响故障排查",
    HighRiskOperationType.MODIFY_COMMUNICATION_CONFIG: "修改通信配置可能导致设备无法连接",
    HighRiskOperationType.EMERGENCY_RESET: "急停复位将解除急停状态，设备可能立即恢复运动",
    HighRiskOperationType.PARAMETER_INIT: "参数初始化将重置部分参数到默认值",
}

# 高危操作风险等级
HIGH_RISK_OPERATION_RISK_LEVELS: dict[HighRiskOperationType, str] = {
    HighRiskOperationType.FACTORY_RESET: "critical",
    HighRiskOperationType.MODIFY_SAFETY_LIMIT: "high",
    HighRiskOperationType.DEVICE_CALIBRATION: "medium",
    HighRiskOperationType.CLEAR_EXPERIMENT_DATA: "high",
    HighRiskOperationType.CLEAR_ALARM_HISTORY: "medium",
    HighRiskOperationType.MODIFY_COMMUNICATION_CONFIG: "medium",
    HighRiskOperationType.EMERGENCY_RESET: "high",
    HighRiskOperationType.PARAMETER_INIT: "medium",
}


class ConfirmationRequest(BaseModel):
    """
    高危操作二次确认请求模型。

    用于请求执行高危操作前的二次确认。

    Attributes:
        operation_type: 高危操作类型
        device_id: 设备ID（可选）
        operation_params: 操作参数（可选）
        confirmation_token: 确认令牌（首次请求为空，二次确认时提供）
        user_remark: 用户备注（可选）
    """

    operation_type: HighRiskOperationType = Field(
        ...,
        description="高危操作类型",
    )
    device_id: str | None = Field(
        default=None,
        description="设备ID",
        max_length=100,
    )
    operation_params: dict[str, Any] | None = Field(
        default=None,
        description="操作参数",
    )
    confirmation_token: str | None = Field(
        default=None,
        description="确认令牌（二次确认时提供）",
        max_length=64,
    )
    user_remark: str | None = Field(
        default=None,
        description="用户备注",
        max_length=500,
    )


class ConfirmationResponse(BaseModel):
    """
    高危操作二次确认响应模型。

    返回确认状态和确认令牌。

    Attributes:
        requires_confirmation: 是否需要二次确认
        confirmation_token: 确认令牌（用于二次确认）
        operation_type: 高危操作类型
        operation_description: 操作描述
        risk_level: 风险等级
        warning_message: 警告消息
        token_expires_at: 令牌过期时间
    """

    requires_confirmation: bool = Field(
        ...,
        description="是否需要二次确认",
    )
    confirmation_token: str | None = Field(
        default=None,
        description="确认令牌",
    )
    operation_type: HighRiskOperationType = Field(
        ...,
        description="高危操作类型",
    )
    operation_description: str = Field(
        ...,
        description="操作描述",
    )
    risk_level: str = Field(
        ...,
        description="风险等级",
    )
    warning_message: str = Field(
        ...,
        description="警告消息",
    )
    token_expires_at: datetime | None = Field(
        default=None,
        description="令牌过期时间",
    )


class HighRiskOperationLogCreate(BaseModel):
    """
    高危操作日志创建模型。

    用于创建高危操作日志记录。

    Attributes:
        operation_type: 高危操作类型
        operation_category: 操作类别
        device_id: 设备ID
        operation_params: 操作参数（脱敏后）
        user_id: 用户ID
        ip_address: IP地址
        user_agent: 用户代理
        confirmation_token: 确认令牌
        execution_result: 执行结果
        error_message: 错误消息
        duration_ms: 执行耗时
    """

    operation_type: HighRiskOperationType = Field(
        ...,
        description="高危操作类型",
    )
    operation_category: HighRiskOperationCategory = Field(
        ...,
        description="操作类别",
    )
    device_id: str | None = Field(
        default=None,
        description="设备ID",
    )
    operation_params: dict[str, Any] | None = Field(
        default=None,
        description="操作参数（脱敏后）",
    )
    user_id: int | None = Field(
        default=None,
        description="用户ID",
    )
    ip_address: str | None = Field(
        default=None,
        description="IP地址",
        max_length=45,
    )
    user_agent: str | None = Field(
        default=None,
        description="用户代理",
        max_length=255,
    )
    confirmation_token: str | None = Field(
        default=None,
        description="确认令牌",
    )
    execution_result: str = Field(
        default="pending",
        description="执行结果",
    )
    error_message: str | None = Field(
        default=None,
        description="错误消息",
    )
    duration_ms: int | None = Field(
        default=None,
        description="执行耗时（毫秒）",
    )


class HighRiskOperationLogResponse(BaseModel):
    """
    高危操作日志响应模型。

    Attributes:
        id: 日志ID
        operation_type: 高危操作类型
        operation_category: 操作类别
        device_id: 设备ID
        operation_params: 操作参数（脱敏后）
        user_id: 用户ID
        ip_address: IP地址
        confirmation_token: 确认令牌
        execution_result: 执行结果
        error_message: 错误消息
        duration_ms: 执行耗时
        created_at: 创建时间
    """

    id: int = Field(..., description="日志ID")
    operation_type: HighRiskOperationType = Field(..., description="高危操作类型")
    operation_category: HighRiskOperationCategory = Field(..., description="操作类别")
    device_id: str | None = Field(default=None, description="设备ID")
    operation_params: dict[str, Any] | None = Field(
        default=None, description="操作参数（脱敏后）"
    )
    user_id: int | None = Field(default=None, description="用户ID")
    ip_address: str | None = Field(default=None, description="IP地址")
    confirmation_token: str | None = Field(default=None, description="确认令牌")
    execution_result: str = Field(..., description="执行结果")
    error_message: str | None = Field(default=None, description="错误消息")
    duration_ms: int | None = Field(default=None, description="执行耗时（毫秒）")
    created_at: datetime = Field(..., description="创建时间")


class SessionLockStatus(BaseModel):
    """
    会话锁定状态模型。

    Attributes:
        is_locked: 是否锁定
        locked_at: 锁定时间
        lock_reason: 锁定原因
        idle_timeout_seconds: 空闲超时时间（秒）
        last_activity_at: 最后活动时间
        remaining_seconds: 剩余锁定时间（秒）
    """

    is_locked: bool = Field(..., description="是否锁定")
    locked_at: datetime | None = Field(default=None, description="锁定时间")
    lock_reason: str | None = Field(default=None, description="锁定原因")
    idle_timeout_seconds: int = Field(
        default=300,
        description="空闲超时时间（秒）",
    )
    last_activity_at: datetime | None = Field(
        default=None,
        description="最后活动时间",
    )
    remaining_seconds: int | None = Field(
        default=None,
        description="剩余锁定时间（秒）",
    )


class SessionUnlockRequest(BaseModel):
    """
    会话解锁请求模型。

    Attributes:
        password: 用户密码（用于重新验证）
        user_id: 用户ID
    """

    password: str = Field(
        ...,
        description="用户密码",
        min_length=6,
        max_length=100,
    )
    user_id: int = Field(
        ...,
        description="用户ID",
    )


class SessionUnlockResponse(BaseModel):
    """
    会话解锁响应模型。

    Attributes:
        success: 是否成功
        message: 消息
        unlocked_at: 解锁时间
    """

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="消息")
    unlocked_at: datetime | None = Field(default=None, description="解锁时间")


class HighRiskOperationAuditQuery(BaseModel):
    """
    高危操作审计查询模型。

    Attributes:
        operation_type: 操作类型筛选
        device_id: 设备ID筛选
        user_id: 用户ID筛选
        execution_result: 执行结果筛选
        start_time: 开始时间
        end_time: 结束时间
        page: 页码
        page_size: 每页数量
    """

    operation_type: HighRiskOperationType | None = Field(
        default=None,
        description="操作类型筛选",
    )
    device_id: str | None = Field(
        default=None,
        description="设备ID筛选",
    )
    user_id: int | None = Field(
        default=None,
        description="用户ID筛选",
    )
    execution_result: str | None = Field(
        default=None,
        description="执行结果筛选",
    )
    start_time: datetime | None = Field(
        default=None,
        description="开始时间",
    )
    end_time: datetime | None = Field(
        default=None,
        description="结束时间",
    )
    page: int = Field(
        default=1,
        ge=1,
        description="页码",
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="每页数量",
    )
