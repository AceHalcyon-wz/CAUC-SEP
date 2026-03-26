"""
文件名: high_risk_utils.py
路径: backend/utils/
功能: 高危操作防护工具函数，简化API集成
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: fastapi, typing

工具函数：
- require_confirmation: 装饰器，为API端点添加二次确认
- get_confirmation_token: 从请求中获取确认令牌
- validate_confirmation: 验证确认令牌
- execute_high_risk_operation: 执行高危操作（带二次确认）
- log_high_risk_operation: 记录高危操作日志
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


def validate_confirmation(
    request: Request,
    operation_type: HighRiskOperationType,
) -> dict[str, Any]:
    """
    验证确认令牌并返回客户端信息。

    Args:
        request: FastAPI请求对象
        operation_type: 操作类型

    Returns:
        dict: 客户端信息，包含 user_id, ip_address, user_agent

    Raises:
        HTTPException: 确认令牌无效或缺失时抛出

    Example:
        >>> client_info = validate_confirmation(request, HighRiskOperationType.FACTORY_RESET)
        >>> print(client_info["ip_address"])
    """
    confirmation_token = get_confirmation_token(request)

    if not confirmation_token:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail={
                "error_code": "CONFIRMATION_REQUIRED",
                "message": "此操作需要二次确认",
                "detail": "请先调用 /api/v1/high-risk/confirm 获取确认令牌，"
                "然后在请求头中携带 X-Confirmation-Token 执行操作",
            },
        )

    # 获取高危操作防护服务
    service = get_high_risk_protection_service()

    # 验证令牌
    user_id = getattr(request.state, "user_id", None)
    is_valid = service._token_manager.validate_token(
        confirmation_token, operation_type, user_id
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_CONFIRMATION_TOKEN",
                "message": "确认令牌无效或已过期",
                "detail": "请重新获取确认令牌",
            },
        )

    # 返回客户端信息
    return {
        "user_id": user_id,
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent", ""),
        "confirmation_token": confirmation_token,
    }


def execute_high_risk_operation(
    request: Request,
    operation_type: HighRiskOperationType,
    callback: Callable[[], bool],
    device_id: str | None = None,
    operation_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    执行高危操作（带二次确认验证）。

    集成二次确认验证、审计日志记录、错误处理。

    Args:
        request: FastAPI请求对象
        operation_type: 操作类型
        callback: 实际执行操作的回调函数
        device_id: 设备ID
        operation_params: 操作参数

    Returns:
        dict: 执行结果

    Raises:
        HTTPException: 确认令牌无效或操作失败时抛出

    Example:
        >>> result = execute_high_risk_operation(
        ...     request=request,
        ...     operation_type=HighRiskOperationType.FACTORY_RESET,
        ...     callback=lambda: driver.factory_reset_sync(),
        ...     device_id="dm2c_main",
        ... )
    """
    # 验证确认令牌
    client_info = validate_confirmation(request, operation_type)

    # 获取高危操作防护服务
    service = get_high_risk_protection_service()

    # 执行操作
    start_time = time.time()

    result = service.execute_with_confirmation(
        confirmation_token=client_info["confirmation_token"],
        operation_type=operation_type,
        callback=callback,
        user_id=client_info["user_id"],
        ip_address=client_info["ip_address"],
        user_agent=client_info["user_agent"],
    )

    duration_ms = int((time.time() - start_time) * 1000)

    if not result.get("success", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": result.get("error_code", "OPERATION_FAILED"),
                "message": result.get("error", "操作执行失败"),
                "duration_ms": duration_ms,
            },
        )

    # 添加执行耗时到结果
    result["duration_ms"] = duration_ms
    result["device_id"] = device_id

    return result


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

            # 验证确认令牌
            client_info = validate_confirmation(request, operation_type)

            # 获取设备ID
            device_id = None
            if device_id_param:
                device_id = kwargs.get(device_id_param)

            # 执行原函数
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)

                # 记录成功日志
                duration_ms = int((time.time() - start_time) * 1000)
                log_high_risk_operation(
                    operation_type=operation_type,
                    execution_result="success",
                    device_id=device_id,
                    user_id=client_info["user_id"],
                    ip_address=client_info["ip_address"],
                    user_agent=client_info["user_agent"],
                    confirmation_token=client_info["confirmation_token"],
                    duration_ms=duration_ms,
                )

                return result

            except Exception as e:
                # 记录失败日志
                duration_ms = int((time.time() - start_time) * 1000)
                log_high_risk_operation(
                    operation_type=operation_type,
                    execution_result="failed",
                    error_message=str(e),
                    device_id=device_id,
                    user_id=client_info["user_id"],
                    ip_address=client_info["ip_address"],
                    user_agent=client_info["user_agent"],
                    confirmation_token=client_info["confirmation_token"],
                    duration_ms=duration_ms,
                )
                raise

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

            # 验证确认令牌
            client_info = validate_confirmation(request, operation_type)

            # 获取设备ID
            device_id = None
            if device_id_param:
                device_id = kwargs.get(device_id_param)

            # 执行原函数
            start_time = time.time()

            try:
                result = func(*args, **kwargs)

                # 记录成功日志
                duration_ms = int((time.time() - start_time) * 1000)
                log_high_risk_operation(
                    operation_type=operation_type,
                    execution_result="success",
                    device_id=device_id,
                    user_id=client_info["user_id"],
                    ip_address=client_info["ip_address"],
                    user_agent=client_info["user_agent"],
                    confirmation_token=client_info["confirmation_token"],
                    duration_ms=duration_ms,
                )

                return result

            except Exception as e:
                # 记录失败日志
                duration_ms = int((time.time() - start_time) * 1000)
                log_high_risk_operation(
                    operation_type=operation_type,
                    execution_result="failed",
                    error_message=str(e),
                    device_id=device_id,
                    user_id=client_info["user_id"],
                    ip_address=client_info["ip_address"],
                    user_agent=client_info["user_agent"],
                    confirmation_token=client_info["confirmation_token"],
                    duration_ms=duration_ms,
                )
                raise

        # 根据函数类型返回不同的包装器
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def log_high_risk_operation(
    operation_type: HighRiskOperationType,
    execution_result: str,
    device_id: str | None = None,
    operation_params: dict[str, Any] | None = None,
    user_id: int | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    confirmation_token: str | None = None,
    error_message: str | None = None,
    duration_ms: int | None = None,
) -> None:
    """
    记录高危操作日志。

    Args:
        operation_type: 操作类型
        execution_result: 执行结果
        device_id: 设备ID
        operation_params: 操作参数
        user_id: 用户ID
        ip_address: IP地址
        user_agent: 用户代理
        confirmation_token: 确认令牌
        error_message: 错误消息
        duration_ms: 执行耗时（毫秒）
    """
    service = get_high_risk_protection_service()

    service._audit_logger.log_operation(
        operation_type=operation_type,
        device_id=device_id,
        operation_params=operation_params,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        confirmation_token=confirmation_token,
        execution_result=execution_result,
        error_message=error_message,
        duration_ms=duration_ms,
    )


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
    user_id = getattr(request.state, "user_id", None)
    ip_address = request.client.host if request.client else None

    service.update_session_activity(session_id, user_id, ip_address)
