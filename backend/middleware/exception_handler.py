"""
文件名: exception_handler.py
路径: backend/middleware/
功能: 全局异常处理器
版本: v1.0
创建日期: 2026-03-15
"""

import logging
from datetime import datetime, timezone, UTC
from typing import Union
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from core.exceptions import AppException, ErrorCode

logger = logging.getLogger(__name__)


def get_timestamp() -> str:
    """
    获取 ISO 格式时间戳。

    Returns:
        str: ISO 格式的 UTC 时间戳
    """
    return datetime.now(UTC).isoformat()


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
    log_data = {
        "error_code": exc.error_code.value,
        "message": exc.message,
        "details": exc.details,
        "path": request.url.path,
        "method": request.method,
        "status_code": exc.status_code,
    }

    if exc.cause:
        log_data["cause"] = str(exc.cause)
        logger.error(
            f"AppException: {exc}",
            extra=log_data,
            exc_info=exc.cause
        )
    else:
        logger.error(f"AppException: {exc}", extra=log_data)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code.value,
                "message": exc.message,
                "details": exc.details,
            },
            "timestamp": get_timestamp(),
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
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })

    logger.warning(
        f"Validation error: {len(errors)} errors on {request.url.path}",
        extra={
            "errors": errors,
            "path": request.url.path,
            "method": request.method,
        }
    )

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
    logger.exception(
        f"Unhandled exception: {type(exc).__name__}: {exc!s}",
        extra={
            "path": request.url.path,
            "method": request.method,
        }
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": ErrorCode.SYSTEM_INTERNAL_ERROR.value,
                "message": "服务器内部错误",
                "details": {},
            },
            "timestamp": get_timestamp(),
        }
    )


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
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(
        RequestValidationError,
        validation_exception_handler
    )
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Exception handlers registered")
