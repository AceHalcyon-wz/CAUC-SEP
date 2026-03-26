"""
文件名: exception_handler.py
路径: backend/middleware/
功能: 全局异常处理器，全链路异常捕获、分级日志记录
版本: v2.0
创建日期: 2026-03-15
最后更新: 2026-03-25
作者: Backend Engineer Agent

依赖:
    - fastapi>=0.109.0
    - pydantic>=2.5.0
    - core.exceptions
    - core.logging_config

安全约束:
    - 生产环境不暴露敏感错误信息
    - 所有异常必须记录完整日志
    - 设备通信异常必须触发安全兜底逻辑
"""

import logging
import traceback
from datetime import datetime, timezone, UTC
from typing import Union, Dict, Any, Optional
from enum import Enum
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.middleware.base import BaseHTTPMiddleware

from core.exceptions import AppException, ErrorCode

try:
    from core.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)


class ExceptionSeverity(str, Enum):
    """异常严重程度枚举。"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ExceptionCategory(str, Enum):
    """异常分类枚举。"""
    SYSTEM = "system"  # 系统异常
    DEVICE = "device"  # 设备异常
    COMMUNICATION = "communication"  # 通信异常
    VALIDATION = "validation"  # 验证异常
    AUTHENTICATION = "authentication"  # 认证异常
    AUTHORIZATION = "authorization"  # 授权异常
    BUSINESS = "business"  # 业务异常
    UNKNOWN = "unknown"  # 未知异常



def get_timestamp() -> str:
    """
    获取 ISO 格式时间戳。

    Returns:
        str: ISO 格式的 UTC 时间戳
    """
    return datetime.now(UTC).isoformat()


def get_client_ip(request: Request) -> str:
    """
    获取客户端IP地址。

    Args:
        request: 请求对象

    Returns:
        str: 客户端IP地址
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def mask_sensitive_data(data: Dict[str, Any], sensitive_keys: set = None) -> Dict[str, Any]:
    """
    脱敏敏感数据。

    Args:
        data: 原始数据字典
        sensitive_keys: 敏感字段名集合

    Returns:
        Dict[str, Any]: 脱敏后的数据字典
    """
    if sensitive_keys is None:
        sensitive_keys = {
            "password", "token", "secret", "key", "authorization",
            "jwt", "credential", "api_key", "access_token"
        }
    
    masked_data = {}
    for key, value in data.items():
        if key.lower() in sensitive_keys:
            masked_data[key] = "***MASKED***"
        elif isinstance(value, dict):
            masked_data[key] = mask_sensitive_data(value, sensitive_keys)
        elif isinstance(value, list):
            masked_data[key] = [
                mask_sensitive_data(item, sensitive_keys) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            masked_data[key] = value
    
    return masked_data


def classify_exception(exc: Exception) -> ExceptionCategory:
    """
    分类异常类型。

    Args:
        exc: 异常实例

    Returns:
        ExceptionCategory: 异常分类
    """
    if isinstance(exc, AppException):
        error_code = exc.error_code.value
        if error_code.startswith("DEVICE"):
            return ExceptionCategory.DEVICE
        elif error_code.startswith("COMM"):
            return ExceptionCategory.COMMUNICATION
        elif error_code.startswith("AUTH"):
            if "TOKEN" in error_code or "CREDENTIAL" in error_code:
                return ExceptionCategory.AUTHENTICATION
            else:
                return ExceptionCategory.AUTHORIZATION
        elif error_code.startswith("VAL"):
            return ExceptionCategory.VALIDATION
        elif error_code.startswith("EXP"):
            return ExceptionCategory.BUSINESS
        else:
            return ExceptionCategory.SYSTEM
    elif isinstance(exc, (RequestValidationError, ValidationError)):
        return ExceptionCategory.VALIDATION
    else:
        return ExceptionCategory.UNKNOWN


def get_exception_severity(exc: Exception) -> ExceptionSeverity:
    """
    获取异常严重程度。

    Args:
        exc: 异常实例

    Returns:
        ExceptionSeverity: 异常严重程度
    """
    if isinstance(exc, AppException):
        error_code = exc.error_code.value
        if error_code.startswith(("DEVICE_HARDWARE", "DEVICE_EMERGENCY")):
            return ExceptionSeverity.CRITICAL
        elif error_code.startswith(("DEVICE", "COMM")):
            return ExceptionSeverity.ERROR
        elif error_code.startswith(("AUTH", "VAL")):
            return ExceptionSeverity.WARNING
        else:
            return ExceptionSeverity.ERROR
    elif isinstance(exc, (RequestValidationError, ValidationError)):
        return ExceptionSeverity.WARNING
    else:
        return ExceptionSeverity.ERROR


def build_error_context(
    request: Request,
    exc: Exception,
    additional_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    构建错误上下文信息。

    Args:
        request: 请求对象
        exc: 异常实例
        additional_context: 额外上下文信息

    Returns:
        Dict[str, Any]: 错误上下文字典
    """
    context = {
        "timestamp": get_timestamp(),
        "request_id": request.headers.get("X-Request-ID", "unknown"),
        "client_ip": get_client_ip(request),
        "method": request.method,
        "path": request.url.path,
        "query_params": dict(request.query_params),
        "exception_type": type(exc).__name__,
        "exception_category": classify_exception(exc).value,
        "severity": get_exception_severity(exc).value,
    }
    
    # 添加请求体信息（仅对POST/PUT/PATCH请求）
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            # 注意：这里不实际读取请求体，避免影响后续处理
            context["has_body"] = True
        except Exception:
            context["has_body"] = False
    
    # 添加用户信息（如果已认证）
    user = getattr(request.state, "user", None)
    if user:
        context["user_id"] = getattr(user, "id", "unknown")
        context["username"] = getattr(user, "username", "unknown")
    
    # 添加额外上下文
    if additional_context:
        context.update(additional_context)
    
    return context


def log_exception(
    exc: Exception,
    context: Dict[str, Any],
    severity: ExceptionSeverity
) -> None:
    """
    记录异常日志。

    Args:
        exc: 异常实例
        context: 错误上下文
        severity: 异常严重程度
    """
    # 脱敏上下文数据
    safe_context = mask_sensitive_data(context)
    
    # 构建日志消息
    log_message = (
        f"Exception occurred: {type(exc).__name__} - {str(exc)} "
        f"[{context['exception_category']}] "
        f"[{severity.value}] "
        f"path={context['path']} "
        f"method={context['method']} "
        f"client_ip={context['client_ip']}"
    )
    
    # 根据严重程度选择日志级别
    if severity == ExceptionSeverity.DEBUG:
        logger.debug(log_message, extra=safe_context, exc_info=True)
    elif severity == ExceptionSeverity.INFO:
        logger.info(log_message, extra=safe_context, exc_info=True)
    elif severity == ExceptionSeverity.WARNING:
        logger.warning(log_message, extra=safe_context, exc_info=True)
    elif severity == ExceptionSeverity.ERROR:
        logger.error(log_message, extra=safe_context, exc_info=True)
    elif severity == ExceptionSeverity.CRITICAL:
        logger.critical(log_message, extra=safe_context, exc_info=True)


async def app_exception_handler(
    request: Request,
    exc: AppException
) -> JSONResponse:
    """
    处理 AppException 异常。

    记录错误日志并返回统一格式的错误响应。

    Args:
        request: 请求对象
        exc: 异常实例

    Returns:
        JSONResponse: 统一格式的错误响应

    Example:
        当 API 抛出 AppException 时，自动捕获并返回：
        {
            "success": false,
            "error": {
                "code": "DEVICE_001",
                "message": "设备未找到: stepper_01",
                "details": {"device_id": "stepper_01"}
            },
            "timestamp": "2026-03-15T10:30:00+00:00"
        }
    """
    # 构建错误上下文
    context = build_error_context(
        request,
        exc,
        {
            "error_code": exc.error_code.value,
            "message": exc.message,
            "details": exc.details,
            "status_code": exc.status_code,
        }
    )
    
    # 如果有原始异常，添加堆栈信息
    if exc.cause:
        context["cause"] = str(exc.cause)
        context["cause_type"] = type(exc.cause).__name__
    
    # 记录异常日志
    severity = get_exception_severity(exc)
    log_exception(exc, context, severity)
    
    # 构建响应（生产环境不暴露敏感信息）
    from core.config import settings
    
    response_details = exc.details
    if settings.is_production:
        # 生产环境脱敏details
        response_details = mask_sensitive_data(exc.details)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code.value,
                "message": exc.message,
                "details": response_details,
            },
            "timestamp": get_timestamp(),
            "request_id": context.get("request_id", "unknown"),
        }
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError | ValidationError
) -> JSONResponse:
    """
    处理验证异常。

    将 Pydantic 验证错误转换为统一格式。

    Args:
        request: 请求对象
        exc: 异常实例

    Returns:
        JSONResponse: 统一格式的验证错误响应

    Example:
        当请求参数验证失败时，返回：
        {
            "success": false,
            "error": {
                "code": "VAL_001",
                "message": "请求参数验证失败",
                "details": {
                    "errors": [
                        {
                            "field": "position",
                            "message": "ensure this value is greater than 0",
                            "type": "value_error.number.not_gt"
                        }
                    ]
                }
            },
            "timestamp": "2026-03-15T10:30:00+00:00"
        }
    """
    # 解析验证错误
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })
    
    # 构建错误上下文
    context = build_error_context(
        request,
        exc,
        {
            "error_count": len(errors),
            "errors": errors,
        }
    )
    
    # 记录验证错误日志
    severity = get_exception_severity(exc)
    log_exception(exc, context, severity)
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": ErrorCode.VALIDATION_ERROR.value,
                "message": "请求参数验证失败",
                "details": {"errors": errors},
            },
            "timestamp": get_timestamp(),
            "request_id": context.get("request_id", "unknown"),
        }
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    处理未捕获的异常。

    作为最后的异常处理器，捕获所有未被其他处理器处理的异常。

    Args:
        request: 请求对象
        exc: 异常实例

    Returns:
        JSONResponse: 统一格式的服务器错误响应

    Note:
        生产环境中不会暴露具体错误信息，仅返回通用错误消息。
        详细错误信息会记录到日志中供排查。
    """
    # 构建错误上下文
    context = build_error_context(
        request,
        exc,
        {
            "traceback": traceback.format_exc(),
        }
    )
    
    # 记录未捕获异常日志（CRITICAL级别）
    log_exception(exc, context, ExceptionSeverity.CRITICAL)
    
    # 生产环境不暴露错误详情
    from core.config import settings
    
    if settings.is_production:
        error_message = "服务器内部错误"
        error_details = {}
    else:
        error_message = f"未捕获的异常: {type(exc).__name__}"
        error_details = {
            "exception_type": type(exc).__name__,
            "message": str(exc),
        }
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": ErrorCode.SYSTEM_INTERNAL_ERROR.value,
                "message": error_message,
                "details": error_details,
            },
            "timestamp": get_timestamp(),
            "request_id": context.get("request_id", "unknown"),
        }
    )


class ExceptionMiddleware(BaseHTTPMiddleware):
    """
    异常处理中间件。
    
    捕获所有未处理的异常，确保所有请求都有统一的错误响应格式。
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        中间件调度方法。

        Args:
            request: 请求对象
            call_next: 下一个中间件或路由处理器

        Returns:
            Response: 响应对象
        """
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            # 如果是AppException，使用app_exception_handler
            if isinstance(exc, AppException):
                return await app_exception_handler(request, exc)
            # 如果是验证异常，使用validation_exception_handler
            elif isinstance(exc, (RequestValidationError, ValidationError)):
                return await validation_exception_handler(request, exc)
            # 其他异常使用generic_exception_handler
            else:
                return await generic_exception_handler(request, exc)


def register_exception_handlers(app) -> None:
    """
    注册异常处理器到 FastAPI 应用。

    按优先级注册异常处理器：
    1. AppException - 应用自定义异常
    2. RequestValidationError - FastAPI 请求验证异常
    3. ValidationError - Pydantic 验证异常
    4. Exception - 所有其他异常（兜底）

    Args:
        app: FastAPI 应用实例

    Example:
        >>> from fastapi import FastAPI
        >>> from middleware.exception_handler import register_exception_handlers
        >>> app = FastAPI()
        >>> register_exception_handlers(app)
    """
    # 注册异常处理器
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(
        RequestValidationError,
        validation_exception_handler
    )
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    # 添加异常处理中间件（可选，作为双重保障）
    # app.add_middleware(ExceptionMiddleware)
    
    logger.info(
        "Exception handlers registered",
        extra={
            "handlers": [
                "AppException",
                "RequestValidationError",
                "ValidationError",
                "Exception"
            ]
        }
    )
