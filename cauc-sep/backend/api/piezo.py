"""
压电陶瓷控制 API 路由模块

功能：
- 电压控制（开环模式）
- 位移控制（闭环模式）
- 校准管理
- 控制模式切换
- 状态查询

技术规格：
- 电压范围：0-150V
- 位移范围：0-100μm
- 支持线性/多项式/分段校准
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from api.schemas import (
    CalibrationDataResponse,
    CalibrationPerformRequest,
    CalibrationPointRequest,
    CalibrationPointResponse,
    ControlModeRequest,
    DisplacementResponse,
    DisplacementSetRequest,
    PiezoStatusResponse,
    SuccessResponse,
    VoltageResponse,
    VoltageSetRequest,
)
from core.device_registry import DeviceRegistry
from core.device_utils import DeviceValidationError, validate_device_state
from core.piezo_controller import CalibrationType, ControlMode as PiezoControlMode, PiezoController

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/piezo",
    tags=["piezo"],
    responses={404: {"description": "Not found"}},
)

# 设备注册表中的设备ID
PIEZO_DEVICE_ID = "piezo"


def get_piezo() -> PiezoController:
    """
    获取压电陶瓷控制器实例。

    从设备注册表中获取控制器实例。

    Raises:
        HTTPException: 当控制器未初始化时抛出 503 错误

    Returns:
        PiezoController: 控制器实例
    """
    try:
        return DeviceRegistry.get_device(PIEZO_DEVICE_ID)
    except KeyError:
        raise HTTPException(status_code=503, detail="Piezo controller not initialized")


def set_piezo(instance: PiezoController) -> None:
    """
    设置压电陶瓷控制器实例。

    将控制器实例注册到设备注册表。

    Args:
        instance: 控制器实例
    """
    if DeviceRegistry.has_device(PIEZO_DEVICE_ID):
        DeviceRegistry.unregister(PIEZO_DEVICE_ID)
    DeviceRegistry.register(PIEZO_DEVICE_ID, instance)


# ==================== 状态查询端点 ====================


@router.get("/status", response_model=PiezoStatusResponse)
async def get_piezo_status(controller: PiezoController = Depends(get_piezo)):
    """
    获取压电陶瓷控制器完整状态。

    Returns:
        PiezoStatusResponse: 包含电压、位移、校准状态等完整信息
    """
    status = await controller.read_status()
    return PiezoStatusResponse(**status)


# ==================== 电压控制端点 ====================


@router.post("/voltage", response_model=VoltageResponse)
async def set_voltage(
    request: VoltageSetRequest,
    controller: PiezoController = Depends(get_piezo),
):
    """
    设置压电陶瓷电压（开环控制）。

    电压将被自动量化到最接近的分辨率值（1mV），
    并限制在有效范围内（0-150V）。

    Args:
        request: 电压设置请求，包含目标电压值
        controller: 控制器实例

    Returns:
        VoltageResponse: 设置结果和当前状态

    Raises:
        HTTPException: 设备未连接或处于错误状态
    """
    try:
        validate_device_state(controller)
    except DeviceValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    try:
        result = await controller.set_voltage(request.voltage_v)

        if not result:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to set voltage: {controller.last_error}",
            )

        current_voltage = await controller.get_voltage()
        current_displacement = await controller.get_displacement()

        return VoltageResponse(
            success=True,
            message=f"Voltage set to {request.voltage_v:.3f}V",
            current_voltage_v=current_voltage,
            current_displacement_um=current_displacement,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to set voltage: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/voltage", response_model=VoltageResponse)
async def get_voltage(controller: PiezoController = Depends(get_piezo)):
    """
    获取当前电压值。

    Returns:
        VoltageResponse: 当前电压和位移信息
    """
    try:
        validate_device_state(controller)
    except DeviceValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    current_voltage = await controller.get_voltage()
    current_displacement = await controller.get_displacement()

    return VoltageResponse(
        success=True,
        message="Current voltage reading",
        current_voltage_v=current_voltage,
        current_displacement_um=current_displacement,
    )


# ==================== 位移控制端点 ====================


@router.post("/displacement", response_model=DisplacementResponse)
async def set_displacement(
    request: DisplacementSetRequest,
    controller: PiezoController = Depends(get_piezo),
):
    """
    设置压电陶瓷位移（闭环控制）。

    根据校准数据将位移转换为电压，
    并应用非线性补偿和磁滞补偿。

    Args:
        request: 位移设置请求，包含目标位移值
        controller: 控制器实例

    Returns:
        DisplacementResponse: 设置结果和当前状态

    Raises:
        HTTPException: 设备未连接或处于错误状态
    """
    try:
        validate_device_state(controller)
    except DeviceValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    try:
        result = await controller.set_displacement(request.displacement_um)

        if not result:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to set displacement: {controller.last_error}",
            )

        current_displacement = await controller.get_displacement()
        current_voltage = await controller.get_voltage()

        return DisplacementResponse(
            success=True,
            message=f"Displacement set to {request.displacement_um:.3f}μm",
            current_displacement_um=current_displacement,
            current_voltage_v=current_voltage,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to set displacement: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/displacement", response_model=DisplacementResponse)
async def get_displacement(controller: PiezoController = Depends(get_piezo)):
    """
    获取当前位移值。

    Returns:
        DisplacementResponse: 当前位移和电压信息
    """
    try:
        validate_device_state(controller)
    except DeviceValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    current_displacement = await controller.get_displacement()
    current_voltage = await controller.get_voltage()

    return DisplacementResponse(
        success=True,
        message="Current displacement reading",
        current_displacement_um=current_displacement,
        current_voltage_v=current_voltage,
    )


# ==================== 校准端点 ====================


@router.post("/calibrate/point", response_model=CalibrationPointResponse)
async def add_calibration_point(
    request: CalibrationPointRequest,
    controller: PiezoController = Depends(get_piezo),
):
    """
    添加校准点。

    校准点用于建立电压-位移的映射关系，
    支持多点校准以提高精度。

    Args:
        request: 校准点请求，包含电压和位移值
        controller: 控制器实例

    Returns:
        CalibrationPointResponse: 添加结果和当前校准点数量

    Raises:
        HTTPException: 参数超出有效范围
    """
    try:
        result = await controller.add_calibration_point(
            voltage_v=request.voltage_v,
            displacement_um=request.displacement_um,
        )

        if not result:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to add calibration point: {controller.last_error}",
            )

        calibration_data = controller.get_calibration_data()

        return CalibrationPointResponse(
            success=True,
            message=f"Calibration point added: {request.voltage_v:.3f}V -> {request.displacement_um:.3f}μm",
            point_count=calibration_data["point_count"],
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add calibration point: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/calibrate/perform", response_model=SuccessResponse)
async def perform_calibration(
    request: CalibrationPerformRequest,
    controller: PiezoController = Depends(get_piezo),
):
    """
    执行校准拟合。

    根据已添加的校准点，计算位移-电压转换系数。
    至少需要2个校准点才能执行校准。

    Args:
        request: 校准请求，指定校准类型
        controller: 控制器实例

    Returns:
        SuccessResponse: 校准结果

    Raises:
        HTTPException: 校准点数量不足或校准失败
    """
    try:
        # 转换校准类型
        calibration_type_map = {
            "linear": CalibrationType.LINEAR,
            "polynomial": CalibrationType.POLYNOMIAL,
            "piecewise": CalibrationType.PIECEWISE,
        }

        if request.calibration_type not in calibration_type_map:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid calibration type: {request.calibration_type}",
            )

        calibration_type = calibration_type_map[request.calibration_type]

        result = await controller.perform_calibration(calibration_type)

        if not result:
            raise HTTPException(
                status_code=500,
                detail=f"Calibration failed: {controller.last_error}",
            )

        return SuccessResponse(
            success=True,
            message=f"Calibration completed using {request.calibration_type} method",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to perform calibration: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/calibrate/data", response_model=CalibrationDataResponse)
async def get_calibration_data(controller: PiezoController = Depends(get_piezo)):
    """
    获取校准数据。

    Returns:
        CalibrationDataResponse: 校准数据详情
    """
    data = controller.get_calibration_data()
    return CalibrationDataResponse(**data)


@router.delete("/calibrate", response_model=SuccessResponse)
async def clear_calibration(controller: PiezoController = Depends(get_piezo)):
    """
    清除所有校准数据。

    Returns:
        SuccessResponse: 清除结果
    """
    result = await controller.clear_calibration()

    return SuccessResponse(
        success=result,
        message="Calibration data cleared" if result else "Failed to clear calibration",
    )


# ==================== 控制模式端点 ====================


@router.post("/mode", response_model=SuccessResponse)
async def set_control_mode(
    request: ControlModeRequest,
    controller: PiezoController = Depends(get_piezo),
):
    """
    设置控制模式。

    Args:
        request: 控制模式请求
        controller: 控制器实例

    Returns:
        SuccessResponse: 设置结果

    Raises:
        HTTPException: 无效的控制模式
    """
    try:
        # 转换控制模式
        mode_map = {
            "open_loop": PiezoControlMode.OPEN_LOOP,
            "closed_loop": PiezoControlMode.CLOSED_LOOP,
        }

        if request.mode not in mode_map:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid control mode: {request.mode}",
            )

        mode = mode_map[request.mode]
        result = await controller.set_control_mode(mode)

        return SuccessResponse(
            success=result,
            message=f"Control mode set to {request.mode}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set control mode: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/mode")
async def get_control_mode(controller: PiezoController = Depends(get_piezo)):
    """
    获取当前控制模式。

    Returns:
        dict: 包含当前控制模式
    """
    mode = controller.get_control_mode()
    return {
        "mode": mode.value,
        "description": "Open loop (voltage control)" if mode == PiezoControlMode.OPEN_LOOP else "Closed loop (displacement control)",
    }


# ==================== 便捷操作端点 ====================


@router.post("/zero", response_model=SuccessResponse)
async def zero_position(controller: PiezoController = Depends(get_piezo)):
    """
    归零操作（电压设为0V）。

    Returns:
        SuccessResponse: 操作结果
    """
    try:
        validate_device_state(controller)
    except DeviceValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    result = await controller.zero()

    return SuccessResponse(
        success=result,
        message="Position zeroed (voltage set to 0V)" if result else "Failed to zero position",
    )


@router.post("/max_extend", response_model=SuccessResponse)
async def max_extend(controller: PiezoController = Depends(get_piezo)):
    """
    最大伸展操作（电压设为最大值）。

    Returns:
        SuccessResponse: 操作结果
    """
    try:
        validate_device_state(controller)
    except DeviceValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    result = await controller.max_extend()

    return SuccessResponse(
        success=result,
        message="Maximum extension reached" if result else "Failed to extend",
    )


@router.post("/connect", response_model=SuccessResponse)
async def connect_piezo(controller: PiezoController = Depends(get_piezo)):
    """
    连接压电陶瓷控制器。

    Returns:
        SuccessResponse: 连接结果
    """
    result = await controller.connect()
    return SuccessResponse(
        success=result,
        message="Connected" if result else "Failed to connect",
    )


@router.post("/disconnect", response_model=SuccessResponse)
async def disconnect_piezo(controller: PiezoController = Depends(get_piezo)):
    """
    断开压电陶瓷控制器。

    Returns:
        SuccessResponse: 断开结果
    """
    result = await controller.disconnect()
    return SuccessResponse(
        success=result,
        message="Disconnected",
    )
