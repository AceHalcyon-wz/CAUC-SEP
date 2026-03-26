"""
文件名: devices.py
路径: backend/api/v1/
功能: 设备管理API路由，提供单设备急停、状态查询、复位校验等接口
版本: v1.0
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: fastapi, schemas, services
安全约束: 急停指令必须保障最高执行优先级，急停原因未消除时禁止复位
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Path, Query

from schemas.api import ApiResponse, ApiError

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== 急停相关常量 ====================

# 急停错误码定义
EMERGENCY_STOP_ERROR_CODES = {
    "DEVICE_NOT_FOUND": "E3001",
    "DEVICE_NOT_CONNECTED": "E3002",
    "EMERGENCY_STOP_FAILED": "E3003",
    "RESET_CONDITION_NOT_MET": "E3004",
    "ALARM_NOT_CLEARED": "E3005",
    "DEVICE_IN_ERROR_STATE": "E3006",
}


# ==================== 单设备急停API ====================

@router.post(
    "/{device_id}/emergency_stop",
    response_model=ApiResponse[dict],
    summary="单设备紧急停止",
    description="执行指定设备的软件急停操作，急停指令具有最高优先级，跳过普通指令队列。",
)
async def emergency_stop_device(
    device_id: str = Path(..., description="设备唯一标识符"),
    reason: str | None = Query(default=None, description="急停原因，用于审计日志"),
) -> ApiResponse[dict]:
    """
    执行单设备紧急停止。

    此接口用于执行指定设备的独立急停操作，与全局急停接口兼容。
    急停指令具有最高执行优先级，将跳过普通指令队列直接下发。

    Args:
        device_id: 设备唯一标识符，与项目现有设备模块名一致
        reason: 可选的急停原因描述，用于审计日志记录

    Returns:
        ApiResponse[dict]: 包含急停执行结果的响应
            - success: True表示急停指令成功下发
            - device_id: 设备标识
            - timestamp: 急停执行时间戳
            - reason: 急停原因

    Raises:
        HTTPException: 设备不存在、设备未连接或急停执行失败时抛出

    Example:
        >>> response = await emergency_stop_device("motor_1", "限位触发")
        >>> assert response.success is True

    安全约束:
        1. 急停指令必须保障最高执行优先级
        2. 急停执行后设备进入EMERGENCY_STOP状态
        3. 所有急停操作必须记录审计日志
    """
    from core.device_management.emergency_stop_manager import get_emergency_stop_manager

    logger.warning(f"[EMERGENCY_STOP] 收到单设备急停请求: device_id={device_id}, reason={reason}")

    try:
        manager = get_emergency_stop_manager()
        result = await manager.execute_device_emergency_stop(
            device_id=device_id,
            reason=reason or "用户触发急停",
            priority=0  # 最高优先级
        )

        if result["success"]:
            logger.info(
                f"[EMERGENCY_STOP] 设备急停成功: device_id={device_id}, "
                f"timestamp={result['timestamp']}"
            )
            return ApiResponse.ok(
                data={
                    "device_id": device_id,
                    "timestamp": result["timestamp"],
                    "reason": reason,
                    "status": "emergency_stop",
                    "message": "急停指令已成功下发",
                }
            )
        else:
            logger.error(
                f"[EMERGENCY_STOP] 设备急停失败: device_id={device_id}, "
                f"error={result.get('error')}"
            )
            return ApiResponse.error(
                message=result.get("error", "急停执行失败"),
                error_code=EMERGENCY_STOP_ERROR_CODES.get(
                    result.get("error_code"), "E3003"
                ),
                details={"device_id": device_id}
            )

    except Exception as e:
        logger.error(f"[EMERGENCY_STOP] 急停异常: device_id={device_id}, error={str(e)}")
        return ApiResponse.error(
            message=f"急停执行异常: {str(e)}",
            error_code="E3003",
            details={"device_id": device_id, "exception": str(e)}
        )


# ==================== 急停复位API ====================

@router.post(
    "/{device_id}/emergency_reset",
    response_model=ApiResponse[dict],
    summary="急停复位",
    description="复位设备的急停状态，执行安全校验后方可复位。",
)
async def emergency_reset_device(
    device_id: str = Path(..., description="设备唯一标识符"),
    force: bool = Query(default=False, description="是否强制复位（跳过部分校验）"),
    confirmation: str = Query(..., description="二次确认字符串，必须输入'CONFIRM_RESET'"),
) -> ApiResponse[dict]:
    """
    复位设备急停状态。

    执行急停复位前会进行完整的安全校验流程：
    1. 设备状态自检
    2. 报警状态清零
    3. 急停原因确认
    4. 二次确认校验

    Args:
        device_id: 设备唯一标识符
        force: 是否强制复位（仅跳过部分非关键校验）
        confirmation: 二次确认字符串，必须输入"CONFIRM_RESET"

    Returns:
        ApiResponse[dict]: 包含复位结果的响应

    Raises:
        HTTPException: 校验失败或复位失败时抛出

    安全约束:
        1. 急停原因未消除时禁止复位
        2. 设备存在报警时禁止复位
        3. 必须进行二次确认
    """
    from services.emergency_stop_service import EmergencyStopService

    # 二次确认校验
    if confirmation != "CONFIRM_RESET":
        logger.warning(
            f"[EMERGENCY_RESET] 二次确认失败: device_id={device_id}, "
            f"confirmation={confirmation}"
        )
        return ApiResponse.error(
            message="二次确认失败，请输入'CONFIRM_RESET'",
            error_code="E3004",
            details={"device_id": device_id}
        )

    logger.info(
        f"[EMERGENCY_RESET] 收到急停复位请求: device_id={device_id}, force={force}"
    )

    try:
        service = EmergencyStopService()
        result = await service.reset_emergency_stop(
            device_id=device_id,
            force=force
        )

        if result["success"]:
            logger.info(f"[EMERGENCY_RESET] 急停复位成功: device_id={device_id}")
            return ApiResponse.ok(
                data={
                    "device_id": device_id,
                    "timestamp": result["timestamp"],
                    "status": "ready",
                    "checks_passed": result.get("checks_passed", []),
                    "message": "急停复位成功，设备已恢复就绪状态",
                }
            )
        else:
            logger.warning(
                f"[EMERGENCY_RESET] 急停复位失败: device_id={device_id}, "
                f"reason={result.get('reason')}"
            )
            return ApiResponse.error(
                message=result.get("reason", "急停复位失败"),
                error_code=EMERGENCY_STOP_ERROR_CODES.get(
                    result.get("error_code"), "E3004"
                ),
                details={
                    "device_id": device_id,
                    "checks_failed": result.get("checks_failed", []),
                }
            )

    except Exception as e:
        logger.error(
            f"[EMERGENCY_RESET] 急停复位异常: device_id={device_id}, error={str(e)}"
        )
        return ApiResponse.error(
            message=f"急停复位异常: {str(e)}",
            error_code="E3004",
            details={"device_id": device_id, "exception": str(e)}
        )


# ==================== 设备状态查询API ====================

@router.get(
    "/{device_id}/status",
    response_model=ApiResponse[dict],
    summary="设备状态查询",
    description="获取指定设备的完整状态信息，包括急停状态、报警状态等。",
)
async def get_device_status(
    device_id: str = Path(..., description="设备唯一标识符"),
) -> ApiResponse[dict]:
    """
    获取设备状态。

    Args:
        device_id: 设备唯一标识符

    Returns:
        ApiResponse[dict]: 包含设备状态信息的响应

    Example:
        >>> response = await get_device_status("motor_1")
        >>> print(response.data["status"])
    """
    from core.device_management.driver_manager import DriverProcessManager

    try:
        # 获取驱动管理器实例
        manager = DriverProcessManager()
        info = manager.get_driver_info(device_id)

        return ApiResponse.ok(
            data={
                "device_id": device_id,
                "status": info.get("status", "unknown"),
                "is_emergency_stop": info.get("status") == "emergency_stop",
                "last_error": info.get("last_error"),
                "last_heartbeat": info.get("last_heartbeat"),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    except KeyError:
        return ApiResponse.error(
            message=f"设备不存在: {device_id}",
            error_code="E3001",
            details={"device_id": device_id}
        )
    except Exception as e:
        logger.error(f"获取设备状态失败: device_id={device_id}, error={str(e)}")
        return ApiResponse.error(
            message=f"获取设备状态失败: {str(e)}",
            error_code="E3000",
            details={"device_id": device_id}
        )


# ==================== 急停状态检查API ====================

@router.get(
    "/{device_id}/emergency_status",
    response_model=ApiResponse[dict],
    summary="急停状态检查",
    description="检查设备是否处于急停状态，以及急停原因和复位条件。",
)
async def get_emergency_status(
    device_id: str = Path(..., description="设备唯一标识符"),
) -> ApiResponse[dict]:
    """
    获取设备急停状态。

    Args:
        device_id: 设备唯一标识符

    Returns:
        ApiResponse[dict]: 包含急停状态信息的响应
            - is_emergency_stop: 是否处于急停状态
            - can_reset: 是否可以复位
            - reset_conditions: 复位条件列表
            - emergency_reason: 急停原因
    """
    from services.emergency_stop_service import EmergencyStopService

    try:
        service = EmergencyStopService()
        status = await service.get_emergency_status(device_id)

        return ApiResponse.ok(data=status)

    except Exception as e:
        logger.error(
            f"获取急停状态失败: device_id={device_id}, error={str(e)}"
        )
        return ApiResponse.error(
            message=f"获取急停状态失败: {str(e)}",
            error_code="E3000",
            details={"device_id": device_id}
        )
