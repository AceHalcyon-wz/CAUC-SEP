"""
文件名: exception_handlers.py
路径: backend/api/
功能: 统一异常处理中间件，捕获所有异常并转换为统一响应格式
版本: v1.0
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: fastapi, starlette, schemas.common, api.response_wrapper

异常处理策略：
1. 捕获所有未处理异常，转换为统一响应格式
2. 区分业务异常和系统异常
3. 记录异常日志，包含完整堆栈信息
4. 生产环境隐藏敏感错误信息

使用示例：
    >>> from api.exception_handlers import setup_exception_handlers
    >>> setup_exception_handlers(app)
"""

import logging
import traceback
from typing import Union

from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from schemas.common import ErrorCode
from api.response_wrapper import error_response
from api.param_validator import ValidationError as ParamValidationError

logger = logging.getLogger(__name__)


class APIException(Exception):
    """
    API业务异常基类。

    所有业务异常应继承此类，提供统一的错误码和消息格式。

    Attributes:
        error_code: 错误码
        message: 错误消息
        details: 错误详情
        status_code: HTTP状态码

    Example:
        >>> raise APIException(
        ...     error_code=ErrorCode.DEVICE_NOT_CONNECTED,
        ...     message="设备未连接",
        ...     status_code=400
        ... )
    """

    def __init__(
        self,
        error_code: str | ErrorCode,
        message: str,
        details: dict | None = None,
        status_code: int = 400
    ):
        """初始化API异常。"""
        self.error_code = error_code.value if isinstance(error_code, ErrorCode) else error_code
        self.message = message
        self.details = details
        self.status_code = status_code
        super().__init__(message)


class DeviceNotFoundError(APIException):
    """设备不存在异常。"""

    def __init__(self, device_id: str):
        """初始化设备不存在异常。"""
        super().__init__(
            error_code=ErrorCode.DEVICE_NOT_INITIALIZED,
            message=f"设备不存在: {device_id}",
            details={"device_id": device_id},
            status_code=404
        )


class DeviceNotConnectedError(APIException):
    """设备未连接异常。"""

    def __init__(self, device_id: str):
        """初始化设备未连接异常。"""
        super().__init__(
            error_code=ErrorCode.DEVICE_NOT_CONNECTED,
            message=f"设备未连接: {device_id}",
            details={"device_id": device_id},
            status_code=400
        )


class DeviceInEmergencyStopError(APIException):
    """设备处于急停状态异常。"""

    def __init__(self, device_id: str):
        """初始化设备急停异常。"""
        super().__init__(
            error_code=ErrorCode.DEVICE_IN_EMERGENCY_STOP,
            message=f"设备处于急停状态: {device_id}",
            details={"device_id": device_id},
            status_code=400
        )


class DeviceBusyError(APIException):
    """设备忙碌异常。"""

    def __init__(self, device_id: str, operation: str = ""):
        """初始化设备忙碌异常。"""
        super().__init__(
            error_code=ErrorCode.DEVICE_BUSY,
            message=f"设备忙碌: {device_id}" + (f"，正在执行: {operation}" if operation else ""),
            details={"device_id": device_id, "operation": operation},
            status_code=400
        )


class LimitExceededError(APIException):
    """限位超限异常。"""

    def __init__(self, position: float, min_limit: float, max_limit: float):
        """初始化限位超限异常。"""
        super().__init__(
            error_code=ErrorCode.SOFT_LIMIT_EXCEEDED,
            message=f"位置 {position} 超出限位范围 [{min_limit}, {max_limit}]",
            details={
                "position": position,
                "min_limit": min_limit,
                "max_limit": max_limit
            },
            status_code=400
        )


class CommunicationError(APIException):
    """通信异常。"""

    def __init__(self, message: str, device_id: str | None = None):
        """初始化通信异常。"""
        super().__init__(
            error_code=ErrorCode.COMMUNICATION_ERROR,
            message=message,
            details={"device_id": device_id} if device_id else None,
            status_code=500
        )


class TimeoutError(APIException):
    """超时异常。"""

    def __init__(self, operation: str, timeout_seconds: float):
        """初始化超时异常。"""
        super().__init__(
            error_code=ErrorCode.TIMEOUT_ERROR,
            message=f"操作超时: {operation}，超时时间: {timeout_seconds}秒",
            details={"operation": operation, "timeout_seconds": timeout_seconds},
            status_code=500
        )


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """
    API业务异常处理器。

    Args:
        request: 请求对象
        exc: API异常

    Returns:
        JSONResponse: 统一格式的错误响应
    """
    logger.warning(
        f"[APIException] {exc.message}",
        extra={
            "error_code": exc.error_code,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method
        }
    )

    response = error_response(
        message=exc.message,
        error_code=exc.error_code,
        details=exc.details
    )

    return JSONResponse(
        content=response.model_dump(),
        status_code=exc.status_code
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    HTTP异常处理器。

    Args:
        request: 请求对象
        exc: HTTP异常

    Returns:
        JSONResponse: 统一格式的错误响应
    """
    # 映射HTTP状态码到错误码
    error_code_map = {
        400: ErrorCode.INVALID_PARAMETER,
        401: ErrorCode.INTERNAL_ERROR,
        403: ErrorCode.INTERNAL_ERROR,
        404: ErrorCode.DEVICE_NOT_INITIALIZED,
        500: ErrorCode.INTERNAL_ERROR,
        503: ErrorCode.DEVICE_NOT_INITIALIZED,
    }

    error_code = error_code_map.get(exc.status_code, ErrorCode.INTERNAL_ERROR)

    logger.warning(
        f"[HTTPException] {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method
        }
    )

    response = error_response(
        message=str(exc.detail),
        error_code=error_code,
        details={
            "status_code": exc.status_code,
            "path": request.url.path
        }
    )

    return JSONResponse(
        content=response.model_dump(),
        status_code=exc.status_code
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    请求验证异常处理器。

    Args:
        request: 请求对象
        exc: 请求验证异常

    Returns:
        JSONResponse: 统一格式的错误响应
    """
    errors = exc.errors()
    first_error = errors[0] if errors else {}

    field = ".".join(str(loc) for loc in first_error.get("loc", []))
    message = first_error.get("msg", "参数验证失败")

    logger.warning(
        f"[ValidationError] {message}",
        extra={
            "field": field,
            "errors": errors,
            "path": request.url.path,
            "method": request.method
        }
    )

    response = error_response(
        message=message,
        error_code=ErrorCode.INVALID_PARAMETER,
        details={
            "field": field,
            "value": str(first_error.get("input", "")),
            "constraint": first_error.get("type", ""),
            "all_errors": errors
        }
    )

    return JSONResponse(
        content=response.model_dump(),
        status_code=422
    )


async def param_validation_exception_handler(request: Request, exc: ParamValidationError) -> JSONResponse:
    """
    参数验证异常处理器。

    Args:
        request: 请求对象
        exc: 参数验证异常

    Returns:
        JSONResponse: 统一格式的错误响应
    """
    logger.warning(
        f"[ParamValidationError] {exc.message}",
        extra={
            "field": exc.field,
            "value": exc.value,
            "constraint": exc.constraint,
            "path": request.url.path,
            "method": request.method
        }
    )

    response = error_response(
        message=exc.message,
        error_code=ErrorCode.INVALID_PARAMETER,
        details={
            "field": exc.field,
            "value": str(exc.value),
            "constraint": exc.constraint
        }
    )

    return JSONResponse(
        content=response.model_dump(),
        status_code=400
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    通用异常处理器。

    捕获所有未处理的异常，记录完整日志，返回统一格式响应。

    Args:
        request: 请求对象
        exc: 异常对象

    Returns:
        JSONResponse: 统一格式的错误响应
    """
    # 记录完整错误日志
    logger.error(
        f"[UnhandledException] {type(exc).__name__}: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "traceback": traceback.format_exc()
        },
        exc_info=True
    )

    # 生产环境不暴露详细错误信息
    response = error_response(
        message="系统内部错误，请稍后重试",
        error_code=ErrorCode.INTERNAL_ERROR,
        details={
            "exception_type": type(exc).__name__,
            "path": request.url.path
        }
    )

    return JSONResponse(
        content=response.model_dump(),
        status_code=500
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """
    配置FastAPI应用的全局异常处理器。

    Args:
        app: FastAPI应用实例

    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> setup_exception_handlers(app)
    """
    # 注册业务异常处理器
    app.add_exception_handler(APIException, api_exception_handler)

    # 注册HTTP异常处理器
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # 注册请求验证异常处理器
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # 注册参数验证异常处理器
    app.add_exception_handler(ParamValidationError, param_validation_exception_handler)

    # 注册通用异常处理器（捕获所有未处理异常）
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("[ExceptionHandler] 全局异常处理器配置完成")
