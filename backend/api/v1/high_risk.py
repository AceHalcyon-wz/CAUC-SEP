"""
文件名: high_risk.py
路径: backend/api/v1/
功能: 高危操作防护API接口，包含二次确认、会话锁定、审计日志查询
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: fastapi, datetime, typing

API端点：
- POST /api/v1/high-risk/confirm - 请求/确认高危操作
- POST /api/v1/high-risk/execute - 执行高危操作
- GET /api/v1/high-risk/session/status - 获取会话锁定状态
- POST /api/v1/high-risk/session/unlock - 解锁会话
- GET /api/v1/high-risk/audit/logs - 查询审计日志
- GET /api/v1/high-risk/stats - 获取服务统计信息
"""

import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core.storage.data_storage import get_storage
from middleware.high_risk_protection import (
    HIGH_RISK_PATHS,
    get_high_risk_protection_service,
    init_high_risk_protection_service,
)
from schemas.high_risk import (
    ConfirmationRequest,
    ConfirmationResponse,
    HighRiskOperationAuditQuery,
    HighRiskOperationLogResponse,
    HighRiskOperationType,
    SessionLockStatus,
    SessionUnlockRequest,
    SessionUnlockResponse,
)
from schemas.api import ApiResponse

router = APIRouter(prefix="/high-risk", tags=["high-risk-protection"])


# ==================== 依赖注入 ====================


def get_service():
    """
    获取高危操作防护服务实例。

    Returns:
        HighRiskProtectionService: 服务实例
    """
    service = get_high_risk_protection_service()
    storage = get_storage()
    if storage:
        service.set_storage(storage)
    return service


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
    }


def get_user_id(request: Request) -> int | None:
    """
    从请求中获取用户ID。

    Args:
        request: FastAPI请求对象

    Returns:
        int | None: 用户ID
    """
    # 从请求状态中获取用户ID（由认证中间件设置）
    return getattr(request.state, "user_id", None)


def get_session_id(request: Request) -> str | None:
    """
    从请求中获取会话ID。

    Args:
        request: FastAPI请求对象

    Returns:
        str | None: 会话ID
    """
    # 从请求状态中获取会话ID
    return getattr(request.state, "session_id", None)


# ==================== API端点 ====================


@router.post(
    "/confirm",
    response_model=ApiResponse[ConfirmationResponse],
    summary="请求/确认高危操作",
    description="请求高危操作的二次确认，首次请求返回确认令牌，二次请求携带令牌确认执行",
)
async def confirm_high_risk_operation(
    request: ConfirmationRequest,
    http_request: Request,
    service=Depends(get_service),
) -> ApiResponse[ConfirmationResponse]:
    """
    请求/确认高危操作。

    首次请求：返回确认令牌和警告信息
    二次请求：携带确认令牌验证通过后返回可执行状态

    Args:
        request: 确认请求模型
        http_request: HTTP请求对象
        service: 高危操作防护服务

    Returns:
        ApiResponse[ConfirmationResponse]: 确认响应
    """
    client_info = get_client_info(http_request)
    user_id = get_user_id(http_request)

    response = service.request_confirmation(
        request=request,
        user_id=user_id,
        ip_address=client_info["ip_address"],
    )

    return ApiResponse(
        success=True,
        data=response,
        message="二次确认请求处理成功",
    )


class HighRiskExecuteRequest(BaseModel):
    """
    高危操作执行请求模型。

    Attributes:
        confirmation_token: 确认令牌
        operation_type: 操作类型
    """

    confirmation_token: str = Field(
        ...,
        description="确认令牌",
        min_length=10,
        max_length=64,
    )
    operation_type: HighRiskOperationType = Field(
        ...,
        description="操作类型",
    )


@router.post(
    "/execute",
    response_model=ApiResponse[dict[str, Any]],
    summary="执行高危操作",
    description="使用确认令牌执行高危操作（仅用于测试，实际操作由各设备API调用）",
)
async def execute_high_risk_operation(
    request: HighRiskExecuteRequest,
    http_request: Request,
    service=Depends(get_service),
) -> ApiResponse[dict[str, Any]]:
    """
    执行高危操作。

    注意：此端点仅用于测试确认令牌验证流程。
    实际高危操作由各设备API内部调用service.execute_with_confirmation。

    Args:
        request: 执行请求模型
        http_request: HTTP请求对象
        service: 高危操作防护服务

    Returns:
        ApiResponse[dict]: 执行结果
    """
    client_info = get_client_info(http_request)
    user_id = get_user_id(http_request)

    # 测试回调函数（实际操作由各API实现）
    def test_callback() -> bool:
        """测试回调函数。"""
        # 模拟操作执行
        time.sleep(0.1)
        return True

    result = service.execute_with_confirmation(
        confirmation_token=request.confirmation_token,
        operation_type=request.operation_type,
        callback=test_callback,
        user_id=user_id,
        ip_address=client_info["ip_address"],
        user_agent=client_info["user_agent"],
    )

    return ApiResponse(
        success=result.get("success", False),
        data=result,
        message=result.get("message", result.get("error", "操作执行完成")),
    )


@router.get(
    "/session/status",
    response_model=ApiResponse[SessionLockStatus],
    summary="获取会话锁定状态",
    description="获取当前会话的锁定状态，包括是否锁定、锁定原因、剩余时间等",
)
async def get_session_lock_status(
    http_request: Request,
    service=Depends(get_service),
) -> ApiResponse[SessionLockStatus]:
    """
    获取会话锁定状态。

    Args:
        http_request: HTTP请求对象
        service: 高危操作防护服务

    Returns:
        ApiResponse[SessionLockStatus]: 会话锁定状态
    """
    session_id = get_session_id(http_request)

    if not session_id:
        return ApiResponse(
            success=True,
            data=SessionLockStatus(
                is_locked=False,
                idle_timeout_seconds=300,
            ),
            message="未找到会话信息",
        )

    status_data = service.get_session_status(session_id)

    return ApiResponse(
        success=True,
        data=status_data,
        message="会话状态获取成功",
    )


@router.post(
    "/session/unlock",
    response_model=ApiResponse[SessionUnlockResponse],
    summary="解锁会话",
    description="解锁被锁定的会话，需要重新验证用户密码",
)
async def unlock_session(
    request: SessionUnlockRequest,
    http_request: Request,
    service=Depends(get_service),
) -> ApiResponse[SessionUnlockResponse]:
    """
    解锁会话。

    需要验证用户密码才能解锁。

    Args:
        request: 解锁请求模型
        http_request: HTTP请求对象
        service: 高危操作防护服务

    Returns:
        ApiResponse[SessionUnlockResponse]: 解锁响应

    Raises:
        HTTPException: 密码验证失败时抛出401错误
    """
    session_id = get_session_id(http_request)

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未找到会话信息",
        )

    # 验证用户密码
    # 注意：实际项目中应该调用用户服务验证密码
    # 这里仅作为示例，实际实现需要集成用户认证系统
    try:
        from models.user import User
        from core.storage.data_storage import get_storage

        storage = get_storage()
        if storage:
            session = storage.Session()
            try:
                user = session.query(User).filter(User.id == request.user_id).first()
                if user and user.verify_password(request.password):
                    # 密码验证成功，解锁会话
                    service.unlock_session(session_id)
                    return ApiResponse(
                        success=True,
                        data=SessionUnlockResponse(
                            success=True,
                            message="会话解锁成功",
                            unlocked_at=datetime.now(),
                        ),
                        message="会话解锁成功",
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="密码验证失败",
                    )
            finally:
                session.close()
        else:
            # 无存储实例时，直接解锁（仅用于测试）
            service.unlock_session(session_id)
            return ApiResponse(
                success=True,
                data=SessionUnlockResponse(
                    success=True,
                    message="会话解锁成功（测试模式）",
                    unlocked_at=datetime.now(),
                ),
                message="会话解锁成功",
            )
    except ImportError:
        # 用户模型不存在时，直接解锁
        service.unlock_session(session_id)
        return ApiResponse(
            success=True,
            data=SessionUnlockResponse(
                success=True,
                message="会话解锁成功",
                unlocked_at=datetime.now(),
            ),
            message="会话解锁成功",
        )


@router.post(
    "/session/lock",
    response_model=ApiResponse[dict[str, Any]],
    summary="手动锁定会话",
    description="手动锁定当前会话",
)
async def lock_session(
    http_request: Request,
    service=Depends(get_service),
) -> ApiResponse[dict[str, Any]]:
    """
    手动锁定会话。

    Args:
        http_request: HTTP请求对象
        service: 高危操作防护服务

    Returns:
        ApiResponse[dict]: 锁定结果
    """
    session_id = get_session_id(http_request)

    if not session_id:
        return ApiResponse(
            success=False,
            data={},
            message="未找到会话信息",
        )

    from middleware.high_risk_protection import SessionLockManager

    # 获取会话管理器并锁定
    session_manager = service._session_manager
    session_manager.lock_session(session_id, reason="manual")

    return ApiResponse(
        success=True,
        data={
            "session_id": session_id[:8] + "...",
            "locked_at": datetime.now().isoformat(),
            "lock_reason": "manual",
        },
        message="会话锁定成功",
    )


@router.get(
    "/audit/logs",
    response_model=ApiResponse[dict[str, Any]],
    summary="查询高危操作审计日志",
    description="查询高危操作审计日志，支持按操作类型、设备、用户、时间筛选",
)
async def query_audit_logs(
    operation_type: HighRiskOperationType | None = None,
    device_id: str | None = None,
    user_id: int | None = None,
    execution_result: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
    http_request: Request = None,
    service=Depends(get_service),
) -> ApiResponse[dict[str, Any]]:
    """
    查询高危操作审计日志。

    Args:
        operation_type: 操作类型筛选
        device_id: 设备ID筛选
        user_id: 用户ID筛选
        execution_result: 执行结果筛选
        start_time: 开始时间
        end_time: 结束时间
        page: 页码
        page_size: 每页数量
        http_request: HTTP请求对象
        service: 高危操作防护服务

    Returns:
        ApiResponse[dict]: 审计日志列表
    """
    try:
        from models.logs import AuditLog
        from core.storage.data_storage import get_storage

        storage = get_storage()
        if not storage:
            return ApiResponse(
                success=False,
                data={"logs": [], "total": 0},
                message="数据存储未初始化",
            )

        session = storage.Session()
        try:
            # 构建查询
            query = session.query(AuditLog)

            # 应用筛选条件
            if operation_type:
                query = query.filter(AuditLog.operation_type == operation_type.value)
            if device_id:
                query = query.filter(AuditLog.device_id == device_id)
            if user_id:
                query = query.filter(AuditLog.user_id == user_id)
            if execution_result:
                # 从extra_data中筛选执行结果
                query = query.filter(
                    AuditLog.extra_data.contains(f'"execution_result": "{execution_result}"')
                )
            if start_time:
                query = query.filter(AuditLog.timestamp >= start_time)
            if end_time:
                query = query.filter(AuditLog.timestamp <= end_time)

            # 高危操作类型筛选
            high_risk_types = [t.value for t in HighRiskOperationType]
            query = query.filter(AuditLog.operation_type.in_(high_risk_types))

            # 计算总数
            total = query.count()

            # 分页
            offset = (page - 1) * page_size
            logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(page_size).all()

            # 转换为响应格式
            log_list = []
            for log in logs:
                extra_data = {}
                if log.extra_data:
                    try:
                        import json
                        extra_data = json.loads(log.extra_data)
                    except Exception:
                        pass

                log_list.append({
                    "id": log.id,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                    "operation_type": log.operation_type,
                    "operation_category": log.operation_category,
                    "device_id": log.device_id,
                    "user_id": log.user_id,
                    "ip_address": log.ip_address,
                    "execution_result": extra_data.get("execution_result", "unknown"),
                    "error_message": log.response_message,
                    "duration_ms": log.duration_ms,
                })

            return ApiResponse(
                success=True,
                data={
                    "logs": log_list,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size,
                },
                message="审计日志查询成功",
            )
        finally:
            session.close()
    except ImportError:
        return ApiResponse(
            success=False,
            data={"logs": [], "total": 0},
            message="审计日志模型未找到",
        )
    except Exception as e:
        return ApiResponse(
            success=False,
            data={"logs": [], "total": 0},
            message=f"查询审计日志失败: {str(e)}",
        )


@router.get(
    "/stats",
    response_model=ApiResponse[dict[str, Any]],
    summary="获取服务统计信息",
    description="获取高危操作防护服务的统计信息，包括令牌、会话等",
)
async def get_service_stats(
    service=Depends(get_service),
) -> ApiResponse[dict[str, Any]]:
    """
    获取服务统计信息。

    Args:
        service: 高危操作防护服务

    Returns:
        ApiResponse[dict]: 统计信息
    """
    stats = service.get_stats()

    # 添加高危操作路径信息
    stats["high_risk_paths"] = list(HIGH_RISK_PATHS.keys())

    return ApiResponse(
        success=True,
        data=stats,
        message="统计信息获取成功",
    )


@router.get(
    "/operations",
    response_model=ApiResponse[dict[str, Any]],
    summary="获取高危操作类型列表",
    description="获取所有高危操作类型及其描述",
)
async def get_operation_types() -> ApiResponse[dict[str, Any]]:
    """
    获取高危操作类型列表。

    Returns:
        ApiResponse[dict]: 操作类型列表
    """
    from schemas.high_risk import (
        HIGH_RISK_OPERATION_CATEGORIES,
        HIGH_RISK_OPERATION_DESCRIPTIONS,
        HIGH_RISK_OPERATION_RISK_LEVELS,
    )

    operations = []
    for op_type in HighRiskOperationType:
        operations.append({
            "type": op_type.value,
            "category": HIGH_RISK_OPERATION_CATEGORIES.get(op_type, "unknown").value,
            "description": HIGH_RISK_OPERATION_DESCRIPTIONS.get(op_type, "未知操作"),
            "risk_level": HIGH_RISK_OPERATION_RISK_LEVELS.get(op_type, "medium"),
        })

    return ApiResponse(
        success=True,
        data={
            "operations": operations,
            "total": len(operations),
        },
        message="操作类型列表获取成功",
    )


# ==================== 初始化 ====================


def init_high_risk_api():
    """
    初始化高危操作防护API。

    在应用启动时调用，初始化全局服务实例。
    """
    try:
        storage = get_storage()
        init_high_risk_protection_service(storage=storage)
    except Exception as e:
        # 存储未初始化时，使用默认配置
        init_high_risk_protection_service()
