"""
文件名: system.py
路径: backend/api/v1/
功能: 系统 API 路由，提供系统状态、健康检查、指标、日志、全局急停等接口
版本: v1.1
作者: Backend Engineer Agent
创建日期: 2026-03-15
更新日期: 2026-03-25
依赖: fastapi, schemas
安全约束: 全局急停必须保障最高执行优先级，与单设备急停接口兼容
"""

import logging
import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query

from schemas.api import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== 急停相关常量 ====================

EMERGENCY_STOP_ERROR_CODES = {
    "NO_DEVICES": "E2001",
    "PARTIAL_FAILURE": "E2002",
    "ALL_FAILED": "E2003",
}


# ==================== 全局急停API ====================

@router.post(
    "/emergency_stop",
    response_model=ApiResponse[dict],
    summary="全局紧急停止",
    description="执行所有已连接设备的紧急停止操作，急停指令具有最高优先级。",
)
async def global_emergency_stop(
    reason: str | None = Query(default=None, description="急停原因，用于审计日志"),
) -> ApiResponse[dict]:
    """
    执行全局紧急停止。

    此接口用于执行所有已连接设备的急停操作。
    急停指令具有最高执行优先级，将跳过普通指令队列直接下发。

    Args:
        reason: 可选的急停原因描述，用于审计日志记录

    Returns:
        ApiResponse[dict]: 包含急停执行结果的响应
            - total_devices: 总设备数
            - success_count: 成功执行急停的设备数
            - failed_devices: 失败的设备列表
            - timestamp: 急停执行时间戳

    安全约束:
        1. 急停指令必须保障最高执行优先级
        2. 所有急停操作必须记录审计日志
        3. 部分失败时仍返回成功，但记录失败设备

    Example:
        >>> response = await global_emergency_stop("系统异常")
        >>> print(f"成功急停设备数: {response.data['success_count']}")
    """
    from core.device_management.emergency_stop_manager import get_emergency_stop_manager
    from core.device_management.driver_manager import DriverProcessManager

    logger.critical(
        f"[GLOBAL_EMERGENCY_STOP] 收到全局急停请求: reason={reason}"
    )

    try:
        # 获取所有设备
        driver_manager = DriverProcessManager()
        devices = driver_manager.get_all_drivers()

        if not devices:
            logger.warning("[GLOBAL_EMERGENCY_STOP] 无已连接设备")
            return ApiResponse.ok(
                data={
                    "total_devices": 0,
                    "success_count": 0,
                    "failed_devices": [],
                    "timestamp": time.time(),
                    "message": "无已连接设备",
                }
            )

        # 执行急停
        es_manager = get_emergency_stop_manager()
        success_count = 0
        failed_devices: list[dict[str, Any]] = []

        for device_id, device_info in devices.items():
            try:
                result = await es_manager.execute_device_emergency_stop(
                    device_id=device_id,
                    reason=reason or "全局急停",
                    priority=0,
                    level="global",
                )
                if result.get("success"):
                    success_count += 1
                else:
                    failed_devices.append({
                        "device_id": device_id,
                        "error": result.get("error", "未知错误"),
                    })
            except Exception as e:
                logger.error(
                    f"[GLOBAL_EMERGENCY_STOP] 设备急停异常: device_id={device_id}, "
                    f"error={str(e)}"
                )
                failed_devices.append({
                    "device_id": device_id,
                    "error": str(e),
                })

        # 记录审计日志
        logger.critical(
            f"[AUDIT] 全局急停执行完成: total={len(devices)}, "
            f"success={success_count}, failed={len(failed_devices)}, "
            f"reason={reason}"
        )

        return ApiResponse.ok(
            data={
                "total_devices": len(devices),
                "success_count": success_count,
                "failed_devices": failed_devices,
                "timestamp": time.time(),
                "reason": reason,
            }
        )

    except Exception as e:
        logger.error(f"[GLOBAL_EMERGENCY_STOP] 全局急停异常: {str(e)}")
        return ApiResponse.error(
            message=f"全局急停执行异常: {str(e)}",
            error_code="E2003",
            details={"exception": str(e)}
        )


# ==================== 系统状态API ====================

@router.get(
    "/status",
    response_model=ApiResponse[dict],
    summary="系统状态",
    description="获取系统整体运行状态。",
)
async def get_system_status() -> ApiResponse[dict]:
    """
    获取系统状态。

    Returns:
        ApiResponse[dict]: 系统状态响应，包含CPU、内存、设备连接等信息。

    Example:
        >>> response = await get_system_status()
        >>> print(f"CPU使用率: {response.data['cpu_usage']}%")
    """
    # TODO: 实现系统状态查询逻辑
    status = {
        "version": "0.4.0",
        "uptime_seconds": 0,
        "cpu_usage": 0.0,
        "memory_usage": 0.0,
        "disk_usage": 0.0,
        "connected_devices": 0,
        "active_experiments": 0,
        "last_updated": datetime.utcnow().isoformat(),
    }
    return ApiResponse(
        success=True,
        data=status,
    )


@router.get(
    "/health",
    response_model=ApiResponse[dict],
    summary="健康检查",
    description="检查系统各组件的健康状态。",
)
async def health_check() -> ApiResponse[dict]:
    """
    健康检查。

    Returns:
        ApiResponse[dict]: 健康状态响应，包含各组件状态。

    Example:
        >>> response = await health_check()
        >>> assert response.data["status"] == "healthy"
    """
    # TODO: 实现健康检查逻辑
    health = {
        "status": "healthy",
        "components": {
            "database": "healthy",
            "cache": "healthy",
            "devices": "healthy",
            "api": "healthy",
        },
        "checked_at": datetime.utcnow().isoformat(),
    }
    return ApiResponse(
        success=True,
        data=health,
    )


@router.get(
    "/metrics",
    response_model=ApiResponse[dict],
    summary="系统指标",
    description="获取系统性能指标数据。",
)
async def get_metrics() -> ApiResponse[dict]:
    """
    获取系统指标。

    Returns:
        ApiResponse[dict]: 系统指标响应，包含性能计数器等。

    Example:
        >>> response = await get_metrics()
        >>> print(f"请求总数: {response.data['requests_total']}")
    """
    # TODO: 实现指标获取逻辑
    metrics = {
        "requests_total": 0,
        "requests_per_second": 0.0,
        "average_response_time_ms": 0.0,
        "error_rate": 0.0,
        "websocket_connections": 0,
        "cache_hit_rate": 0.0,
        "collected_at": datetime.utcnow().isoformat(),
    }
    return ApiResponse(
        success=True,
        data=metrics,
    )


@router.get(
    "/logs",
    response_model=ApiResponse[list[dict]],
    summary="系统日志",
    description="获取系统日志记录。",
)
async def get_logs(
    level: str | None = Query(default=None, description="日志级别筛选: debug, info, warning, error"),
    limit: int = Query(default=100, ge=1, le=1000, description="返回条数限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
) -> ApiResponse[list[dict]]:
    """
    获取系统日志。

    Args:
        level: 可选的日志级别筛选。
        limit: 返回条数限制，最大1000。
        offset: 偏移量，用于分页。

    Returns:
        ApiResponse[List[dict]]: 日志列表响应。

    Example:
        >>> response = await get_logs(level="error", limit=10)
        >>> for log in response.data:
        ...     print(f"[{log['timestamp']}] {log['message']}")
    """
    # TODO: 实现日志查询逻辑
    return ApiResponse(
        success=True,
        data=[],
    )
