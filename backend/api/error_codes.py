"""
文件名: error_codes.py
路径: backend/api/
功能: 统一业务错误码定义，提供完整的错误码分类和映射
版本: v1.0
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: schemas.common, enum, typing

错误码分类规范：
- E0xxx: 通用错误（未知错误、系统错误）
- E1xxx: 设备相关错误（未初始化、未连接、急停、忙碌、设备故障）
- E2xxx: 参数相关错误（无效参数、参数超限、参数缺失、格式错误）
- E3xxx: 限位相关错误（软限位超限、硬件限位触发、限位锁定）
- E4xxx: 操作相关错误（操作失败、运动失败、连接失败、权限不足）
- E5xxx: 系统相关错误（内部错误、通信错误、超时错误、服务不可用）
- E6xxx: 数据相关错误（数据不存在、数据格式错误、数据冲突）
- E7xxx: 认证授权错误（未认证、认证失败、权限不足、令牌过期）

使用示例：
    >>> from api.error_codes import BusinessErrorCode, get_error_message
    >>> error_code = BusinessErrorCode.DEVICE_NOT_CONNECTED
    >>> message = get_error_message(error_code)
"""

from enum import Enum
from typing import Dict

from schemas.common import ErrorCode


class BusinessErrorCode(str, Enum):
    """
    业务错误码枚举。

    继承自 schemas.common.ErrorCode 并扩展更多业务场景。

    错误码分类：
        - E0xxx: 通用错误
        - E1xxx: 设备错误
        - E2xxx: 参数错误
        - E3xxx: 限位错误
        - E4xxx: 操作错误
        - E5xxx: 系统错误
        - E6xxx: 数据错误
        - E7xxx: 认证授权错误
    """

    # ==================== E0xxx: 通用错误 ====================
    UNKNOWN_ERROR = "E0000"
    SUCCESS = "E0001"  # 用于表示成功状态

    # ==================== E1xxx: 设备相关错误 ====================
    # 继承自 ErrorCode
    DEVICE_NOT_INITIALIZED = "E1001"
    DEVICE_NOT_CONNECTED = "E1002"
    DEVICE_IN_EMERGENCY_STOP = "E1003"
    DEVICE_BUSY = "E1004"
    DEVICE_ERROR = "E1005"
    DEVICE_NOT_FOUND = "E1006"
    DEVICE_TIMEOUT = "E1007"
    DEVICE_ALREADY_CONNECTED = "E1008"
    DEVICE_SIMULATION_MODE = "E1009"

    # ==================== E2xxx: 参数相关错误 ====================
    # 继承自 ErrorCode
    INVALID_PARAMETER = "E2001"
    PARAM_OUT_OF_RANGE = "E2002"
    MISSING_PARAMETER = "E2003"
    PARAM_FORMAT_ERROR = "E2004"
    PARAM_TYPE_ERROR = "E2005"
    PARAM_VALUE_EMPTY = "E2006"
    PARAM_VALIDATION_FAILED = "E2007"

    # ==================== E3xxx: 限位相关错误 ====================
    # 继承自 ErrorCode
    SOFT_LIMIT_EXCEEDED = "E3001"
    HARDWARE_LIMIT_TRIGGERED = "E3002"
    LIMIT_LOCKOUT_ACTIVE = "E3003"
    LIMIT_VERIFICATION_FAILED = "E3004"
    LIMIT_SYNC_FAILED = "E3005"
    LIMIT_CONFIG_INVALID = "E3006"

    # ==================== E4xxx: 操作相关错误 ====================
    # 继承自 ErrorCode
    OPERATION_FAILED = "E4001"
    MOTION_FAILED = "E4002"
    CONNECTION_FAILED = "E4003"
    OPERATION_NOT_ALLOWED = "E4004"
    OPERATION_TIMEOUT = "E4005"
    OPERATION_CANCELLED = "E4006"
    PERMISSION_DENIED = "E4007"
    RESOURCE_LOCKED = "E4008"

    # ==================== E5xxx: 系统相关错误 ====================
    # 继承自 ErrorCode
    INTERNAL_ERROR = "E5001"
    COMMUNICATION_ERROR = "E5002"
    TIMEOUT_ERROR = "E5003"
    SERVICE_UNAVAILABLE = "E5004"
    DATABASE_ERROR = "E5005"
    CACHE_ERROR = "E5006"
    FILE_SYSTEM_ERROR = "E5007"
    CONFIG_ERROR = "E5008"

    # ==================== E6xxx: 数据相关错误 ====================
    DATA_NOT_FOUND = "E6001"
    DATA_ALREADY_EXISTS = "E6002"
    DATA_FORMAT_ERROR = "E6003"
    DATA_INTEGRITY_ERROR = "E6004"
    DATA_EXPORT_FAILED = "E6005"
    DATA_IMPORT_FAILED = "E6006"

    # ==================== E7xxx: 认证授权错误 ====================
    UNAUTHORIZED = "E7001"
    AUTHENTICATION_FAILED = "E7002"
    TOKEN_EXPIRED = "E7003"
    TOKEN_INVALID = "E7004"
    INSUFFICIENT_PERMISSIONS = "E7005"
    ACCOUNT_DISABLED = "E7006"
    ACCOUNT_LOCKED = "E7007"


# 错误码到错误消息的映射
ERROR_MESSAGES: Dict[str, str] = {
    # E0xxx: 通用错误
    "E0000": "未知错误",
    "E0001": "操作成功",

    # E1xxx: 设备错误
    "E1001": "设备未初始化",
    "E1002": "设备未连接",
    "E1003": "设备处于急停状态",
    "E1004": "设备忙碌中",
    "E1005": "设备故障",
    "E1006": "设备不存在",
    "E1007": "设备响应超时",
    "E1008": "设备已连接",
    "E1009": "设备处于仿真模式",

    # E2xxx: 参数错误
    "E2001": "无效参数",
    "E2002": "参数超出范围",
    "E2003": "缺少必要参数",
    "E2004": "参数格式错误",
    "E2005": "参数类型错误",
    "E2006": "参数值为空",
    "E2007": "参数验证失败",

    # E3xxx: 限位错误
    "E3001": "超出软件限位范围",
    "E3002": "硬件限位触发",
    "E3003": "限位锁定激活",
    "E3004": "限位验证失败",
    "E3005": "限位同步失败",
    "E3006": "限位配置无效",

    # E4xxx: 操作错误
    "E4001": "操作失败",
    "E4002": "运动执行失败",
    "E4003": "连接失败",
    "E4004": "操作不允许",
    "E4005": "操作超时",
    "E4006": "操作已取消",
    "E4007": "权限不足",
    "E4008": "资源已锁定",

    # E5xxx: 系统错误
    "E5001": "系统内部错误",
    "E5002": "通信错误",
    "E5003": "请求超时",
    "E5004": "服务不可用",
    "E5005": "数据库错误",
    "E5006": "缓存错误",
    "E5007": "文件系统错误",
    "E5008": "配置错误",

    # E6xxx: 数据错误
    "E6001": "数据不存在",
    "E6002": "数据已存在",
    "E6003": "数据格式错误",
    "E6004": "数据完整性错误",
    "E6005": "数据导出失败",
    "E6006": "数据导入失败",

    # E7xxx: 认证授权错误
    "E7001": "未认证",
    "E7002": "认证失败",
    "E7003": "令牌已过期",
    "E7004": "令牌无效",
    "E7005": "权限不足",
    "E7006": "账户已禁用",
    "E7007": "账户已锁定",
}


def get_error_message(error_code: str | BusinessErrorCode | ErrorCode) -> str:
    """
    根据错误码获取错误消息。

    Args:
        error_code: 错误码，支持字符串、BusinessErrorCode 或 ErrorCode

    Returns:
        str: 错误消息，如果未找到则返回"未知错误"

    Example:
        >>> message = get_error_message("E1002")
        >>> print(message)  # "设备未连接"
    """
    code = error_code.value if isinstance(error_code, Enum) else error_code
    return ERROR_MESSAGES.get(code, "未知错误")


def get_error_suggestions(error_code: str | BusinessErrorCode | ErrorCode) -> list[str]:
    """
    根据错误码获取修复建议。

    Args:
        error_code: 错误码

    Returns:
        list[str]: 修复建议列表

    Example:
        >>> suggestions = get_error_suggestions("E1002")
        >>> print(suggestions)  # ["检查设备连接", "确认设备电源已开启"]
    """
    code = error_code.value if isinstance(error_code, Enum) else error_code

    suggestions_map: Dict[str, list[str]] = {
        "E1001": ["检查系统启动日志", "确认设备初始化配置正确"],
        "E1002": ["检查设备连接", "确认设备电源已开启", "检查通信线缆"],
        "E1003": ["检查急停原因", "清除急停状态后重试", "确认安全后复位急停"],
        "E1004": ["等待当前操作完成", "检查设备状态", "必要时执行急停"],
        "E1005": ["检查设备故障代码", "查看设备日志", "联系技术支持"],
        "E1006": ["确认设备ID正确", "检查设备是否已注册", "查看设备列表"],
        "E2001": ["检查参数格式", "确认参数类型正确", "查看API文档"],
        "E2002": ["检查参数范围", "确认参数值在有效范围内", "查看参数约束说明"],
        "E2003": ["检查必填参数", "确认请求体完整", "查看API文档"],
        "E3001": ["检查目标位置", "确认在软件限位范围内", "调整限位配置"],
        "E3002": ["检查硬件限位开关", "确认设备位置", "清除限位触发"],
        "E4001": ["检查操作条件", "确认设备状态", "查看错误日志"],
        "E4002": ["检查运动参数", "确认限位设置", "检查设备状态"],
        "E4003": ["检查网络连接", "确认服务地址正确", "检查防火墙设置"],
        "E5001": ["查看系统日志", "联系技术支持", "重启服务"],
        "E5002": ["检查通信配置", "确认通信参数正确", "检查硬件连接"],
        "E5003": ["增加超时时间", "检查网络状况", "减少数据量"],
        "E6001": ["确认数据ID正确", "检查数据是否已删除", "刷新数据列表"],
        "E7001": ["先进行登录认证", "检查认证令牌", "重新登录"],
        "E7002": ["检查用户名密码", "确认账户状态", "联系管理员"],
        "E7003": ["刷新认证令牌", "重新登录", "检查令牌有效期"],
    }

    return suggestions_map.get(code, ["查看错误日志", "联系技术支持"])


def is_device_error(error_code: str | BusinessErrorCode | ErrorCode) -> bool:
    """
    判断是否为设备相关错误。

    Args:
        error_code: 错误码

    Returns:
        bool: 是否为设备错误

    Example:
        >>> is_device_error("E1002")
        True
    """
    code = error_code.value if isinstance(error_code, Enum) else error_code
    return code.startswith("E1")


def is_param_error(error_code: str | BusinessErrorCode | ErrorCode) -> bool:
    """
    判断是否为参数相关错误。

    Args:
        error_code: 错误码

    Returns:
        bool: 是否为参数错误
    """
    code = error_code.value if isinstance(error_code, Enum) else error_code
    return code.startswith("E2")


def is_limit_error(error_code: str | BusinessErrorCode | ErrorCode) -> bool:
    """
    判断是否为限位相关错误。

    Args:
        error_code: 错误码

    Returns:
        bool: 是否为限位错误
    """
    code = error_code.value if isinstance(error_code, Enum) else error_code
    return code.startswith("E3")


def is_system_error(error_code: str | BusinessErrorCode | ErrorCode) -> bool:
    """
    判断是否为系统相关错误。

    Args:
        error_code: 错误码

    Returns:
        bool: 是否为系统错误
    """
    code = error_code.value if isinstance(error_code, Enum) else error_code
    return code.startswith("E5")
