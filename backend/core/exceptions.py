"""
文件名: exceptions.py
路径: backend/core/
功能: 统一异常处理框架
版本: v1.0
创建日期: 2026-03-15
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status


class ErrorCode(str, Enum):
    """统一错误码枚举。"""

    # ==================== 设备错误 (DEVICE_XXX) ====================
    DEVICE_NOT_FOUND = "DEVICE_001"
    DEVICE_CONNECTION_FAILED = "DEVICE_002"
    DEVICE_TIMEOUT = "DEVICE_003"
    DEVICE_NOT_CONNECTED = "DEVICE_004"
    DEVICE_ALREADY_CONNECTED = "DEVICE_005"
    DEVICE_OPERATION_FAILED = "DEVICE_006"
    DEVICE_EMERGENCY_STOP = "DEVICE_007"
    DEVICE_LIMIT_EXCEEDED = "DEVICE_008"
    DEVICE_CALIBRATION_REQUIRED = "DEVICE_009"
    DEVICE_BUSY = "DEVICE_010"
    DEVICE_HARDWARE_ERROR = "DEVICE_011"
    DEVICE_SIMULATION_MODE = "DEVICE_012"

    # ==================== 实验错误 (EXP_XXX) ====================
    EXPERIMENT_NOT_FOUND = "EXP_001"
    EXPERIMENT_ALREADY_RUNNING = "EXP_002"
    EXPERIMENT_NOT_RUNNING = "EXP_003"
    EXPERIMENT_CREATION_FAILED = "EXP_004"
    EXPERIMENT_DATA_INVALID = "EXP_005"
    EXPERIMENT_TIMEOUT = "EXP_006"
    EXPERIMENT_CANCELLATION_FAILED = "EXP_007"
    EXPERIMENT_SAVE_FAILED = "EXP_008"
    EXPERIMENT_LOAD_FAILED = "EXP_009"

    # ==================== 认证错误 (AUTH_XXX) ====================
    AUTH_INVALID_TOKEN = "AUTH_001"
    AUTH_TOKEN_EXPIRED = "AUTH_002"
    AUTH_PERMISSION_DENIED = "AUTH_003"
    AUTH_INVALID_CREDENTIALS = "AUTH_004"
    AUTH_USER_NOT_FOUND = "AUTH_005"
    AUTH_USER_ALREADY_EXISTS = "AUTH_006"
    AUTH_WEAK_PASSWORD = "AUTH_007"
    AUTH_ACCOUNT_LOCKED = "AUTH_008"
    AUTH_SESSION_EXPIRED = "AUTH_009"

    # ==================== 验证错误 (VAL_XXX) ====================
    VALIDATION_ERROR = "VAL_001"
    INVALID_PARAMETER = "VAL_002"
    MISSING_PARAMETER = "VAL_003"
    PARAMETER_OUT_OF_RANGE = "VAL_004"
    INVALID_FORMAT = "VAL_005"
    DUPLICATE_ENTRY = "VAL_006"

    # ==================== 系统错误 (SYS_XXX) ====================
    SYSTEM_INTERNAL_ERROR = "SYS_001"
    SYSTEM_DATABASE_ERROR = "SYS_002"
    SYSTEM_CACHE_ERROR = "SYS_003"
    SYSTEM_CONFIGURATION_ERROR = "SYS_004"
    SYSTEM_RESOURCE_EXHAUSTED = "SYS_005"
    SYSTEM_SERVICE_UNAVAILABLE = "SYS_006"

    # ==================== 通信错误 (COMM_XXX) ====================
    COMM_CONNECTION_ERROR = "COMM_001"
    COMM_TIMEOUT = "COMM_002"
    COMM_PROTOCOL_ERROR = "COMM_003"
    COMM_SERIAL_ERROR = "COMM_004"
    COMM_MODBUS_ERROR = "COMM_005"
    COMM_WEBSOCKET_ERROR = "COMM_006"

    # ==================== 文件错误 (FILE_XXX) ====================
    FILE_NOT_FOUND = "FILE_001"
    FILE_READ_ERROR = "FILE_002"
    FILE_WRITE_ERROR = "FILE_003"
    FILE_INVALID_FORMAT = "FILE_004"
    FILE_TOO_LARGE = "FILE_005"


class AppException(HTTPException):
    """
    应用统一异常类。

    所有业务异常都应使用此类，确保错误响应格式一致。

    Attributes:
        error_code: 错误码枚举
        message: 错误消息
        details: 错误详情字典
        cause: 原始异常

    Example:
        >>> raise AppException(
        ...     error_code=ErrorCode.DEVICE_NOT_FOUND,
        ...     message="设备未找到: stepper_01",
        ...     status_code=404,
        ...     details={"device_id": "stepper_01"}
        ... )
    """

    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ):
        """
        初始化异常。

        Args:
            error_code: 错误码枚举
            message: 错误消息
            status_code: HTTP 状态码，默认 400
            details: 错误详情字典，可选
            cause: 原始异常，可选
        """
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.cause = cause

        super().__init__(
            status_code=status_code,
            detail={
                "code": error_code.value,
                "message": message,
                "details": self.details,
            }
        )

    def __str__(self) -> str:
        """返回异常字符串表示。"""
        return f"[{self.error_code.value}] {self.message}"


class ValidationErrorDetail:
    """
    验证错误详情。

    用于描述单个字段的验证错误。

    Attributes:
        field: 字段名
        message: 错误消息
        value: 字段值（可选）
        constraint: 约束条件（可选）

    Example:
        >>> error = ValidationErrorDetail(
        ...     field="position",
        ...     message="值必须大于0",
        ...     value=-1,
        ...     constraint="gt:0"
        ... )
    """

    def __init__(
        self,
        field: str,
        message: str,
        value: Any | None = None,
        constraint: str | None = None,
    ):
        """
        初始化验证错误详情。

        Args:
            field: 字段名
            message: 错误消息
            value: 字段值，可选
            constraint: 约束条件，可选
        """
        self.field = field
        self.message = message
        self.value = value
        self.constraint = constraint

    def to_dict(self) -> dict[str, Any]:
        """
        转换为字典格式。

        Returns:
            Dict[str, Any]: 包含字段名、消息、值和约束的字典
        """
        result = {
            "field": self.field,
            "message": self.message,
        }
        if self.value is not None:
            result["value"] = self.value
        if self.constraint is not None:
            result["constraint"] = self.constraint
        return result


class ValidationException(AppException):
    """
    验证异常（支持多个错误）。

    用于请求参数验证失败时返回多个错误信息。

    Attributes:
        errors: 验证错误详情列表

    Example:
        >>> errors = [
        ...     ValidationErrorDetail("position", "值必须大于0", -1),
        ...     ValidationErrorDetail("speed", "值超出范围", 100)
        ... ]
        >>> raise ValidationException(errors)
    """

    def __init__(
        self,
        errors: list[ValidationErrorDetail],
        message: str = "请求参数验证失败",
    ):
        """
        初始化验证异常。

        Args:
            errors: 验证错误详情列表
            message: 错误消息，默认为"请求参数验证失败"
        """
        self.errors = errors
        super().__init__(
            error_code=ErrorCode.VALIDATION_ERROR,
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"errors": [e.to_dict() for e in errors]},
        )


# ==================== 设备异常工厂函数 ====================

def device_not_found(device_id: str) -> AppException:
    """
    设备未找到异常。

    Args:
        device_id: 设备ID

    Returns:
        AppException: 设备未找到异常实例

    Example:
        >>> raise device_not_found("stepper_01")
    """
    return AppException(
        error_code=ErrorCode.DEVICE_NOT_FOUND,
        message=f"设备未找到: {device_id}",
        status_code=status.HTTP_404_NOT_FOUND,
        details={"device_id": device_id},
    )


def device_connection_failed(
    device_id: str,
    reason: str,
    cause: Exception | None = None
) -> AppException:
    """
    设备连接失败异常。

    Args:
        device_id: 设备ID
        reason: 失败原因
        cause: 原始异常，可选

    Returns:
        AppException: 设备连接失败异常实例

    Example:
        >>> raise device_connection_failed("stepper_01", "串口打开失败")
    """
    return AppException(
        error_code=ErrorCode.DEVICE_CONNECTION_FAILED,
        message=f"设备连接失败: {device_id}",
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        details={"device_id": device_id, "reason": reason},
        cause=cause,
    )


def device_not_connected(device_id: str) -> AppException:
    """
    设备未连接异常。

    Args:
        device_id: 设备ID

    Returns:
        AppException: 设备未连接异常实例

    Example:
        >>> raise device_not_connected("stepper_01")
    """
    return AppException(
        error_code=ErrorCode.DEVICE_NOT_CONNECTED,
        message=f"设备未连接: {device_id}",
        status_code=status.HTTP_400_BAD_REQUEST,
        details={"device_id": device_id},
    )


def device_timeout(
    device_id: str,
    operation: str,
    timeout_ms: int
) -> AppException:
    """
    设备操作超时异常。

    Args:
        device_id: 设备ID
        operation: 操作名称
        timeout_ms: 超时时间（毫秒）

    Returns:
        AppException: 设备操作超时异常实例

    Example:
        >>> raise device_timeout("stepper_01", "move", 5000)
    """
    return AppException(
        error_code=ErrorCode.DEVICE_TIMEOUT,
        message=f"设备操作超时: {device_id}",
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        details={
            "device_id": device_id,
            "operation": operation,
            "timeout_ms": timeout_ms,
        },
    )


def device_limit_exceeded(
    device_id: str,
    limit_type: str,
    value: float,
    limit: float
) -> AppException:
    """
    设备限位超出异常。

    Args:
        device_id: 设备ID
        limit_type: 限位类型（positive/negative）
        value: 当前值
        limit: 限位值

    Returns:
        AppException: 设备限位超出异常实例

    Example:
        >>> raise device_limit_exceeded("stepper_01", "positive", 55.0, 50.0)
    """
    return AppException(
        error_code=ErrorCode.DEVICE_LIMIT_EXCEEDED,
        message=f"设备限位超出: {device_id}",
        status_code=status.HTTP_400_BAD_REQUEST,
        details={
            "device_id": device_id,
            "limit_type": limit_type,
            "value": value,
            "limit": limit,
        },
    )


def device_busy(device_id: str, current_operation: str) -> AppException:
    """
    设备忙碌异常。

    Args:
        device_id: 设备ID
        current_operation: 当前正在执行的操作

    Returns:
        AppException: 设备忙碌异常实例

    Example:
        >>> raise device_busy("stepper_01", "moving")
    """
    return AppException(
        error_code=ErrorCode.DEVICE_BUSY,
        message=f"设备正在执行其他操作: {device_id}",
        status_code=status.HTTP_409_CONFLICT,
        details={
            "device_id": device_id,
            "current_operation": current_operation,
        },
    )


# ==================== 实验异常工厂函数 ====================

def experiment_not_found(experiment_id: int) -> AppException:
    """
    实验未找到异常。

    Args:
        experiment_id: 实验ID

    Returns:
        AppException: 实验未找到异常实例

    Example:
        >>> raise experiment_not_found(123)
    """
    return AppException(
        error_code=ErrorCode.EXPERIMENT_NOT_FOUND,
        message=f"实验未找到: {experiment_id}",
        status_code=status.HTTP_404_NOT_FOUND,
        details={"experiment_id": experiment_id},
    )


def experiment_already_running(experiment_id: int) -> AppException:
    """
    实验已在运行异常。

    Args:
        experiment_id: 实验ID

    Returns:
        AppException: 实验已在运行异常实例

    Example:
        >>> raise experiment_already_running(123)
    """
    return AppException(
        error_code=ErrorCode.EXPERIMENT_ALREADY_RUNNING,
        message=f"实验已在运行: {experiment_id}",
        status_code=status.HTTP_409_CONFLICT,
        details={"experiment_id": experiment_id},
    )


def experiment_not_running(experiment_id: int) -> AppException:
    """
    实验未在运行异常。

    Args:
        experiment_id: 实验ID

    Returns:
        AppException: 实验未在运行异常实例

    Example:
        >>> raise experiment_not_running(123)
    """
    return AppException(
        error_code=ErrorCode.EXPERIMENT_NOT_RUNNING,
        message=f"实验未在运行: {experiment_id}",
        status_code=status.HTTP_400_BAD_REQUEST,
        details={"experiment_id": experiment_id},
    )


# ==================== 认证异常工厂函数 ====================

def invalid_token(reason: str = "令牌无效") -> AppException:
    """
    无效令牌异常。

    Args:
        reason: 错误原因，默认为"令牌无效"

    Returns:
        AppException: 无效令牌异常实例

    Example:
        >>> raise invalid_token("令牌格式错误")
    """
    return AppException(
        error_code=ErrorCode.AUTH_INVALID_TOKEN,
        message=reason,
        status_code=status.HTTP_401_UNAUTHORIZED,
        details={"reason": reason},
    )


def token_expired() -> AppException:
    """
    令牌过期异常。

    Returns:
        AppException: 令牌过期异常实例

    Example:
        >>> raise token_expired()
    """
    return AppException(
        error_code=ErrorCode.AUTH_TOKEN_EXPIRED,
        message="令牌已过期，请重新登录",
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


def permission_denied(
    action: str,
    resource: str | None = None
) -> AppException:
    """
    权限拒绝异常。

    Args:
        action: 尝试执行的操作
        resource: 操作的资源，可选

    Returns:
        AppException: 权限拒绝异常实例

    Example:
        >>> raise permission_denied("delete", "experiment_123")
    """
    details: dict[str, Any] = {"action": action}
    if resource:
        details["resource"] = resource
    return AppException(
        error_code=ErrorCode.AUTH_PERMISSION_DENIED,
        message=f"权限不足，无法执行: {action}",
        status_code=status.HTTP_403_FORBIDDEN,
        details=details,
    )


def invalid_credentials() -> AppException:
    """
    无效凭证异常。

    Returns:
        AppException: 无效凭证异常实例

    Example:
        >>> raise invalid_credentials()
    """
    return AppException(
        error_code=ErrorCode.AUTH_INVALID_CREDENTIALS,
        message="用户名或密码错误",
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


# ==================== 系统异常工厂函数 ====================

def internal_error(
    message: str = "服务器内部错误",
    cause: Exception | None = None
) -> AppException:
    """
    内部错误异常。

    Args:
        message: 错误消息，默认为"服务器内部错误"
        cause: 原始异常，可选

    Returns:
        AppException: 内部错误异常实例

    Example:
        >>> raise internal_error("数据库连接失败")
    """
    return AppException(
        error_code=ErrorCode.SYSTEM_INTERNAL_ERROR,
        message=message,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        cause=cause,
    )


def database_error(
    operation: str,
    cause: Exception | None = None
) -> AppException:
    """
    数据库错误异常。

    Args:
        operation: 数据库操作名称
        cause: 原始异常，可选

    Returns:
        AppException: 数据库错误异常实例

    Example:
        >>> raise database_error("insert_experiment")
    """
    return AppException(
        error_code=ErrorCode.SYSTEM_DATABASE_ERROR,
        message=f"数据库操作失败: {operation}",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details={"operation": operation},
        cause=cause,
    )


def cache_error(
    operation: str,
    cause: Exception | None = None
) -> AppException:
    """
    缓存错误异常。

    Args:
        operation: 缓存操作名称
        cause: 原始异常，可选

    Returns:
        AppException: 缓存错误异常实例

    Example:
        >>> raise cache_error("get_user_cache")
    """
    return AppException(
        error_code=ErrorCode.SYSTEM_CACHE_ERROR,
        message=f"缓存操作失败: {operation}",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details={"operation": operation},
        cause=cause,
    )


def service_unavailable(service_name: str, reason: str) -> AppException:
    """
    服务不可用异常。

    Args:
        service_name: 服务名称
        reason: 不可用原因

    Returns:
        AppException: 服务不可用异常实例

    Example:
        >>> raise service_unavailable("Redis", "连接超时")
    """
    return AppException(
        error_code=ErrorCode.SYSTEM_SERVICE_UNAVAILABLE,
        message=f"服务不可用: {service_name}",
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        details={"service": service_name, "reason": reason},
    )
