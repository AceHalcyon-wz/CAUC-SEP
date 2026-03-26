"""
文件名: example_api.py
路径: backend/api/v1/
功能: API规范优化示例，展示统一响应格式、参数校验、异常处理的标准用法
版本: v1.0
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: fastapi, api.response_wrapper, api.param_validator, api.exception_handlers

示例说明：
本文件展示如何使用新的API规范工具：
1. 统一响应格式：使用 success_response, error_response
2. 参数校验：使用 @validate_params 装饰器
3. 异常处理：抛出 APIException 异常
4. RESTful规范：GET用于查询，POST用于操作
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, Path

from api.response_wrapper import success_response, error_response, paginated_response
from api.param_validator import ParamValidator, validate_params
from api.exception_handlers import (
    APIException,
    DeviceNotFoundError,
    DeviceNotConnectedError,
    LimitExceededError
)
from schemas.api import ApiResponse
from schemas.common import ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/example", tags=["example"])


# ==================== 示例1: 基础查询接口（GET方法） ====================


@router.get(
    "/devices/{device_id}",
    response_model=ApiResponse[dict],
    summary="获取设备信息",
    description="根据设备ID获取设备详细信息，使用GET方法进行查询操作"
)
async def get_device_info(
    device_id: str = Path(..., description="设备唯一标识符")
) -> ApiResponse[dict]:
    """
    获取设备信息示例。

    展示：
    1. 使用GET方法进行查询操作
    2. 使用统一响应格式
    3. 抛出业务异常

    Args:
        device_id: 设备唯一标识符

    Returns:
        ApiResponse[dict]: 包含设备信息的响应

    Raises:
        DeviceNotFoundError: 设备不存在时抛出
        DeviceNotConnectedError: 设备未连接时抛出

    Example:
        >>> response = await get_device_info("motor_001")
        >>> assert response.success is True
        >>> assert response.data["device_id"] == "motor_001"
    """
    # 模拟设备查询逻辑
    if device_id == "not_found":
        raise DeviceNotFoundError(device_id)

    if device_id == "not_connected":
        raise DeviceNotConnectedError(device_id)

    # 返回统一格式的成功响应
    return success_response(
        data={
            "device_id": device_id,
            "device_type": "stepper_motor",
            "device_name": "步进电机",
            "status": "ready",
            "connected": True,
            "position_mm": 25.5,
            "velocity_mm_s": 10.0
        },
        message="设备信息查询成功"
    )


# ==================== 示例2: 带参数校验的查询接口 ====================


@router.get(
    "/devices",
    response_model=ApiResponse[dict],
    summary="查询设备列表",
    description="分页查询设备列表，支持状态过滤和排序"
)
@validate_params(
    ParamValidator.range("page", min_val=1, max_val=1000),
    ParamValidator.range("page_size", min_val=1, max_val=100),
    ParamValidator.enum("status", ["all", "ready", "busy", "error", "disconnected"])
)
async def list_devices(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: str = Query("all", description="设备状态过滤")
) -> ApiResponse[dict]:
    """
    查询设备列表示例。

    展示：
    1. 使用 @validate_params 装饰器进行参数校验
    2. 使用 paginated_response 返回分页数据
    3. GET方法用于查询操作

    Args:
        page: 页码，范围1-1000
        page_size: 每页数量，范围1-100
        status: 设备状态过滤，可选值: all, ready, busy, error, disconnected

    Returns:
        ApiResponse[dict]: 包含分页设备列表的响应

    Example:
        >>> response = await list_devices(page=1, page_size=10, status="ready")
        >>> assert response.success is True
        >>> assert "items" in response.data
    """
    # 模拟设备列表查询
    devices = [
        {
            "device_id": "motor_001",
            "device_type": "stepper_motor",
            "status": "ready",
            "connected": True
        },
        {
            "device_id": "electromagnet_001",
            "device_type": "electromagnet",
            "status": "ready",
            "connected": True
        }
    ]

    # 返回统一格式的分页响应
    return paginated_response(
        items=devices,
        total=2,
        page=page,
        page_size=page_size,
        message="设备列表查询成功"
    )


# ==================== 示例3: 操作接口（POST方法） ====================


@router.post(
    "/devices/{device_id}/move",
    response_model=ApiResponse[dict],
    summary="执行设备运动",
    description="执行设备定位运动操作，使用POST方法进行操作类请求"
)
@validate_params(
    ParamValidator.required("target_position"),
    ParamValidator.range("target_position", min_val=-50.0, max_val=50.0),
    ParamValidator.range("velocity", min_val=1.0, max_val=50.0)
)
async def move_device(
    device_id: str = Path(..., description="设备唯一标识符"),
    target_position: float = Query(..., description="目标位置(mm)"),
    velocity: float = Query(10.0, description="运动速度(mm/s)")
) -> ApiResponse[dict]:
    """
    执行设备运动示例。

    展示：
    1. 使用POST方法进行操作类请求
    2. 参数校验失败自动返回错误响应
    3. 业务异常处理

    Args:
        device_id: 设备唯一标识符
        target_position: 目标位置，范围-50.0到50.0
        velocity: 运动速度，范围1.0到50.0

    Returns:
        ApiResponse[dict]: 包含运动结果的响应

    Raises:
        DeviceNotFoundError: 设备不存在
        DeviceNotConnectedError: 设备未连接
        LimitExceededError: 位置超限

    Example:
        >>> response = await move_device("motor_001", 25.0, 10.0)
        >>> assert response.success is True
        >>> assert response.data["motion_started"] is True
    """
    # 模拟设备检查
    if device_id == "not_found":
        raise DeviceNotFoundError(device_id)

    if device_id == "not_connected":
        raise DeviceNotConnectedError(device_id)

    # 模拟限位检查
    if abs(target_position) > 50.0:
        raise LimitExceededError(target_position, -50.0, 50.0)

    # 记录操作日志
    logger.info(
        f"[DeviceMove] 设备运动: device_id={device_id}, "
        f"target={target_position}mm, velocity={velocity}mm/s"
    )

    # 返回统一格式的成功响应
    return success_response(
        data={
            "device_id": device_id,
            "motion_started": True,
            "target_position_mm": target_position,
            "velocity_mm_s": velocity,
            "estimated_time_s": abs(target_position) / velocity
        },
        message="运动指令已下发"
    )


# ==================== 示例4: 批量操作接口 ====================


@router.post(
    "/devices/batch/status",
    response_model=ApiResponse[dict],
    summary="批量查询设备状态",
    description="批量查询多个设备的状态信息"
)
async def batch_get_device_status(
    device_ids: list[str] = Query(..., description="设备ID列表")
) -> ApiResponse[dict]:
    """
    批量查询设备状态示例。

    展示：
    1. 批量操作接口设计
    2. 错误处理和部分成功响应

    Args:
        device_ids: 设备ID列表

    Returns:
        ApiResponse[dict]: 包含批量查询结果的响应

    Example:
        >>> response = await batch_get_device_status(["motor_001", "motor_002"])
        >>> assert response.success is True
        >>> assert "results" in response.data
    """
    results = []
    errors = []

    for device_id in device_ids:
        try:
            # 模拟设备查询
            if device_id == "not_found":
                errors.append({
                    "device_id": device_id,
                    "error": "设备不存在"
                })
            else:
                results.append({
                    "device_id": device_id,
                    "status": "ready",
                    "connected": True
                })
        except Exception as e:
            errors.append({
                "device_id": device_id,
                "error": str(e)
            })

    # 返回统一格式的响应
    return success_response(
        data={
            "results": results,
            "errors": errors,
            "total": len(device_ids),
            "success_count": len(results),
            "error_count": len(errors)
        },
        message=f"批量查询完成: 成功{len(results)}个, 失败{len(errors)}个"
    )


# ==================== 示例5: 错误响应示例 ====================


@router.get(
    "/error/{error_type}",
    response_model=ApiResponse[dict],
    summary="错误响应示例",
    description="展示不同类型的错误响应格式"
)
async def error_example(
    error_type: str = Path(..., description="错误类型: device_not_found, device_not_connected, limit_exceeded, internal")
) -> ApiResponse[dict]:
    """
    错误响应示例。

    展示不同类型的错误响应格式。

    Args:
        error_type: 错误类型

    Returns:
        ApiResponse[dict]: 错误响应

    Example:
        >>> response = await error_example("device_not_found")
        >>> assert response.success is False
    """
    if error_type == "device_not_found":
        raise DeviceNotFoundError("example_device")

    elif error_type == "device_not_connected":
        raise DeviceNotConnectedError("example_device")

    elif error_type == "limit_exceeded":
        raise LimitExceededError(100.0, -50.0, 50.0)

    elif error_type == "internal":
        raise APIException(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="系统内部错误示例",
            details={"error_type": "internal"},
            status_code=500
        )

    else:
        return error_response(
            message=f"未知的错误类型: {error_type}",
            error_code=ErrorCode.INVALID_PARAMETER,
            details={"error_type": error_type}
        )
