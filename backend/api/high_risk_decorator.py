"""
文件名: high_risk_decorator.py
路径: backend/api/
功能: 高危操作装饰器，用于API端点的二次确认验证
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: fastapi, functools, typing

使用方法：
    from api.high_risk_decorator import require_confirmation

    @router.post("/factory_reset")
    @require_confirmation(HighRiskOperationType.FACTORY_RESET)
    async def factory_reset(request: Request, driver = Depends(get_driver)):
        # 执行实际操作
        return {"success": True}
"""

import functools
import time
from typing import Any, Callable, TypeVar

from fastapi import HTTPException, Request, status

from middleware.high_risk_protection import get_high_risk_protection_service
from schemas.high_risk import HighRiskOperationType

F = TypeVar("F", bound=Callable[..., Any])


def get_confirmation_token(request: Request) -> str | None:
    """
    从请求中获取确认令牌。

    优先从请求头获取，其次从查询参数获取。

    Args:
        request: FastAPI请求对象

    Returns:
        str | None: 确认令牌

    Example:
        >>> token = get_confirmation_token(request)
        >>> if not token:
        ...     raise HTTPException(status_code=428, detail="需要二次确认")
    """
    # 从请求头获取
    token = request.headers.get("X-Confirmation-Token")

    # 从查询参数获取
    if not token:
        token = request.query_params.get("confirmation_token")

    return token


def require_confirmation(
    operation_type: HighRiskOperationType,
    device_id_param: str | None = None,
):
    """
    装饰器：为API端点添加二次确认验证。

    Args:
        operation_type: 操作类型
        device_id_param: 设备ID参数名（从函数参数中获取）

    Returns:
        装饰器函数

    Example:
        >>> @router.post("/factory_reset")
        ... @require_confirmation(HighRiskOperationType.FACTORY_RESET)
        ... async def factory_reset(request: Request, driver = Depends(get_driver)):
        ...     return {"success": await driver.factory_reset()}
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 从参数中获取request对象
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if request is None:
                request = kwargs.get("request")

            if request is None:
                raise ValueError("Request object not found in function arguments")

            # 获取确认令牌
            confirmation_token = get_confirmation_token(request)

            if not confirmation_token:
                raise HTTPException(
                    status_code=428,
                    detail={
                        "success": False,
                        "error_code": "CONFIRMATION_REQUIRED",
                        "message": "此操作需要二次确认",
                        "detail": "请先调用 /api/v1/high-risk/confirm 获取确认令牌，"
                        "然后在请求头中携带 X-Confirmation-Token 执行操作",
                    },
                )

            # 获取高危操作防护服务
            service = get_high_risk_protection_service()

            # 获取客户端信息
            client_info = get_client_info(request)

            # 获取设备ID
            device_id = None
            if device_id_param:
                device_id = kwargs.get(device_id_param)

            # 执行二次确认验证
            start_time = time.time()

            result = service.execute_with_confirmation(
                confirmation_token=confirmation_token,
                operation_type=operation_type,
                callback=lambda: True,  # 验证通过即可，实际操作由原函数执行
                user_id=client_info["user_id"],
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
            )

            duration_ms = int((time.time() - start_time) * 1000)

            if not result.get("success", False):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "error_code": result.get("error_code", "CONFIRMATION_FAILED"),
                        "message": result.get("error", "二次确认验证失败"),
                        "duration_ms": duration_ms,
                    },
                )

            # 添加执行耗时到kwargs
            kwargs["_confirmation_duration_ms"] = duration_ms
            kwargs["_confirmation_token"] = confirmation_token

            # 执行原函数
            return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 从参数中获取request对象
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if request is None:
                request = kwargs.get("request")

            if request is None:
                raise ValueError("Request object not found in function arguments")

            # 获取确认令牌
            confirmation_token = get_confirmation_token(request)

            if not confirmation_token:
                raise HTTPException(
                    status_code=428,
                    detail={
                        "success": False,
                        "error_code": "CONFIRMATION_REQUIRED",
                        "message": "此操作需要二次确认",
                        "detail": "请先调用 /api/v1/high-risk/confirm 获取确认令牌，"
                        "然后在请求头中携带 X-Confirmation-Token 执行操作",
                    },
                )

            # 获取高危操作防护服务
            service = get_high_risk_protection_service()

            # 获取客户端信息
            client_info = get_client_info(request)

            # 执行二次确认验证
            start_time = time.time()

            result = service.execute_with_confirmation(
                confirmation_token=confirmation_token,
                operation_type=operation_type,
                callback=lambda: True,
                user_id=client_info["user_id"],
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
            )

            duration_ms = int((time.time() - start_time) * 1000)

            if not result.get("success", False):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "error_code": result.get("error_code", "CONFIRMATION_FAILED"),
                        "message": result.get("error", "二次确认验证失败"),
                        "duration_ms": duration_ms,
                    },
                )

            # 添加执行耗时到kwargs
            kwargs["_confirmation_duration_ms"] = duration_ms
            kwargs["_confirmation_token"] = confirmation_token

            # 执行原函数
            return func(*args, **kwargs)

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def get_client_info(request: Request) -> dict[str, Any]:
    """
    从请求中获取客户端信息。

    Args:
        request: FastAPI请求对象

    Returns:
        dict: 客户端信息
    """
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent", ""),
        "user_id": getattr(request.state, "user_id", None),
    }


def check_session_lock(request: Request) -> None:
    """
    检查会话是否被锁定。

    Args:
        request: FastAPI请求对象

    Raises:
        HTTPException: 会话被锁定时抛出

    Example:
        >>> check_session_lock(request)  # 如果锁定则抛出异常
    """
    import hashlib

    # 获取会话ID
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        session_id = hashlib.sha256(token.encode()).hexdigest()[:32]
    else:
        session_cookie = request.cookies.get("session_id")
        session_id = session_cookie if session_cookie else None

    if not session_id:
        return

    # 检查锁定状态
    service = get_high_risk_protection_service()

    if service.check_session_lock(session_id):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail={
                "success": False,
                "error_code": "SESSION_LOCKED",
                "message": "会话已锁定，请重新验证身份",
                "detail": "由于长时间未操作，会话已自动锁定。请重新输入密码解锁。",
            },
        )


def update_session_activity(request: Request) -> None:
    """
    更新会话活动时间。

    Args:
        request: FastAPI请求对象

    Example:
        >>> update_session_activity(request)
    """
    import hashlib

    # 获取会话ID
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        session_id = hashlib.sha256(token.encode()).hexdigest()[:32]
    else:
        session_cookie = request.cookies.get("session_id")
        session_id = session_cookie if session_cookie else None

    if not session_id:
        return

    # 更新活动时间
    service = get_high_risk_protection_service()
    service.update_session_activity(session_id)


def log_high_risk_operation(
    operation_type: HighRiskOperationType,
    device_id: str | None = None,
    operation_params: dict[str, Any] | None = None,
    execution_result: str = "success",
    error_message: str | None = None,
    duration_ms: int | None = None,
    request: Request | None = None,
) -> None:
    """
    手动记录高危操作日志。

    用于在无法使用装饰器的场景下手动记录日志。

    Args:
        operation_type: 操作类型
        device_id: 设备ID
        operation_params: 操作参数（会自动脱敏）
        execution_result: 执行结果
        error_message: 错误消息
        duration_ms: 执行耗时（毫秒）
        request: FastAPI请求对象

    Example:
        >>> log_high_risk_operation(
        ...     operation_type=HighRiskOperationType.FACTORY_RESET,
        ...     execution_result="success",
        ...     request=request
        ... )
    """
    service = get_high_risk_protection_service()

    client_info = {}
    if request:
        client_info = get_client_info(request)

    from middleware.high_risk_protection import HighRiskOperationAuditLogger
    from schemas.high_risk import HIGH_RISK_OPERATION_CATEGORIES

    audit_logger = service._audit_logger

    audit_logger.log_operation(
        operation_type=operation_type,
        operation_category=HIGH_RISK_OPERATION_CATEGORIES.get(operation_type),
        device_id=device_id,
        operation_params=operation_params,
        user_id=client_info.get("user_id"),
        ip_address=client_info.get("ip_address"),
        user_agent=client_info.get("user_agent"),
        execution_result=execution_result,
        error_message=error_message,
        duration_ms=duration_ms,
    )
