"""
文件名: api_examples.py
路径: backend/api/
功能: API规范示例代码，展示统一响应格式、参数校验、异常处理的最佳实践
版本: v1.0
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: fastapi, api.response_wrapper, api.param_validator, api.exception_handlers

示例内容：
1. 查询接口使用GET方法，返回统一格式响应
2. 操作接口使用POST方法，参数校验失败返回统一错误格式
3. 业务异常自动转换为统一错误响应
4. 分页查询使用统一分页响应格式
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
    LimitExceededError,
)
from schemas.api import ApiResponse
from schemas.common import ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/example", tags=["example"])


# ==================== 示例1: 基础查询接口（GET方法） ====================


@router.get(
    "/devices",
    response_model=ApiResponse[dict],
    summary="设备列表查询",
    description="查询设备列表，使用GET方法，返回统一格式的分页响应",
)
async def list_devices(
    page: int = Query(1, ge=1, le=100, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    status: str | None = Query(None, description="设备状态筛选"),
) -> ApiResponse[dict]:
    """
    设备列表查询示例。

    展示：
    1. 使用GET方法进行查询操作
    2. 使用Query参数进行分页和筛选
    3. 返回统一格式的分页响应
    4. 参数范围校验通过Query装饰器实现

    Args:
        page: 页码，范围1-100
        page_size: 每页数量，范围1-100
        status: 设备状态筛选，可选

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


@router.get(
    "/devices/{device_id}",
    response_model=ApiResponse[dict],
    summary="设备详情查询",
    description="查询单个设备详情，使用GET方法，返回统一格式的响应",
)
async def get_device(
    device_id: str = Path(..., description="设备唯一标识符")
) -> ApiResponse[dict]:
    """
    设备详情查询示例。

    展示：
    1. 使用GET方法进行单个资源查询
    2. 使用Path参数传递资源ID
    3. 返回统一格式的成功响应
    4. 资源不存在时抛出业务异常

    Args:
        device_id: 设备唯一标识符

    Returns:
        ApiResponse[dict]: 包含设备详情的响应

    Raises:
        DeviceNotFoundError: 设备不存在

    Example:
        >>> response = await get_device("motor_001")
        >>> assert response.success is True
        >>> assert response.data["device_id"] == "motor_001"
    """
    # 模拟设备查询
    if device_id == "not_found":
        raise DeviceNotFoundError(device_id)

    # 返回统一格式的成功响应
    return success_response(
        data={
            "device_id": device_id,
            "device_type": "stepper_motor",
            "status": "ready",
            "connected": True,
            "position_mm": 25.5,
            "velocity_mm_s": 10.0
        },
        message="设备详情查询成功"
    )


# ==================== 示例2: 操作接口（POST方法） ====================


@router.post(
    "/devices/{device_id}/move",
    response_model=ApiResponse[dict],
    summary="执行设备运动",
    description="执行设备定位运动操作，使用POST方法，参数校验失败返回统一错误格式",
)
@validate_params(
    ParamValidator.range("target_position", min_val=-50.0, max_val=50.0),
    ParamValidator.range("velocity", min_val=1.0, max_val=50.0)
)
async def move_device(
    device_id: str = Path(..., description="设备唯一标识符"),
    target_position: float = Query(..., description="目标位置(mm)"),
    velocity: float = Query(10.0, description="运动速度(mm/s)"),
) -> ApiResponse[dict]:
    """
    执行设备运动示例。

    展示：
    1. 使用POST方法进行操作类请求
    2. 使用装饰器进行参数校验
    3. 参数校验失败自动返回统一错误格式
    4. 业务异常自动转换为统一错误响应

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


# ==================== 示例3: 错误响应示例 ====================


@router.get(
    "/error/{error_type}",
    response_model=ApiResponse[dict],
    summary="错误响应示例",
    description="展示不同类型的错误响应格式",
)
async def error_example(
    error_type: str = Path(..., description="错误类型: device_not_found, device_not_connected, limit_exceeded, internal")
) -> ApiResponse[dict]:
    """
    错误响应示例。

    展示：
    1. 不同类型的业务异常
    2. 异常自动转换为统一错误响应
    3. 错误响应包含错误码、消息、详情

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
            message="系统内部错误",
            details={"error_type": "internal"},
            status_code=500
        )

    # 默认返回成功响应
    return success_response(
        data={"message": "无错误发生"},
        message="请求成功"
    )
