"""
温控系统 API 路由模块

功能：
- 温度设定点控制
- PID参数配置
- 程序控温
- 温度保护配置
- 状态查询
- 历史记录管理

作者：Backend Engineer Agent
创建日期：2026-03-07
"""

import logging
import time

from fastapi import APIRouter, Depends, HTTPException

from api.schemas import (
    PIDParametersRequest,
    ProtectionConfigRequest,
    SuccessResponse,
    TemperatureHistoryRequest,
    TemperatureHistoryResponse,
    TemperatureProgramRequest,
    TemperatureSetpointRequest,
    TemperatureStatusResponse,
)
from core.device_registry import DeviceRegistry
from core.device_utils import DeviceValidationError, validate_device_state
from core.temperature_controller import (
    TemperatureController,
    TemperatureProgramSegment,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/temperature",
    tags=["temperature"],
    responses={404: {"description": "Not found"}},
)

# 设备注册表中的设备ID常量
TEMPERATURE_CONTROLLER_ID = "temperature_controller"


def get_temperature_controller() -> TemperatureController:
    """
    获取温度控制器实例。

    通过 DeviceRegistry 获取已注册的温度控制器实例。

    Raises:
        HTTPException: 当控制器未初始化时抛出 503 错误

    Returns:
        TemperatureController: 温度控制器实例
    """
    try:
        return DeviceRegistry.get_device(TEMPERATURE_CONTROLLER_ID)
    except KeyError:
        raise HTTPException(
            status_code=503,
            detail="Temperature controller not initialized"
        )


def set_temperature_controller(instance: TemperatureController) -> None:
    """
    设置温度控制器实例。

    通过 DeviceRegistry 注册温度控制器实例。

    Args:
        instance: 温度控制器实例

    Raises:
        ValueError: 设备ID已存在时抛出
    """
    if DeviceRegistry.has_device(TEMPERATURE_CONTROLLER_ID):
        DeviceRegistry.unregister(TEMPERATURE_CONTROLLER_ID)
    DeviceRegistry.register(TEMPERATURE_CONTROLLER_ID, instance)


@router.post("/setpoint", response_model=SuccessResponse)
async def set_temperature_setpoint(
    request: TemperatureSetpointRequest,
    controller: TemperatureController = Depends(get_temperature_controller),
):
    """
    设置温度设定点。

    Args:
        request: 温度设定点请求
        controller: 温度控制器实例

    Returns:
        SuccessResponse: 设置结果

    Raises:
        HTTPException: 设备未连接、保护触发或温度超出范围时抛出错误
    """
    # 验证设备状态
    try:
        validate_device_state(controller)
    except DeviceValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    # 温度范围验证（77K-400K）
    if not (controller.MIN_TEMPERATURE <= request.temperature <= controller.MAX_TEMPERATURE):
        raise HTTPException(
            status_code=400,
            detail=f"Temperature {request.temperature}K out of range. "
                   f"Valid range: {controller.MIN_TEMPERATURE}K-{controller.MAX_TEMPERATURE}K"
        )

    try:
        # 温度单位转换：°C -> K（注意：schema中temperature已经是K）
        temperature_k = request.temperature
        result = await controller.set_temperature(temperature_k)
        return SuccessResponse(
            success=result,
            message=f"Setpoint set to {request.temperature}K ({request.temperature - 273.15:.1f}°C)" if result else "Failed to set setpoint",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/program", response_model=SuccessResponse)
async def set_temperature_program(
    request: TemperatureProgramRequest,
    controller: TemperatureController = Depends(get_temperature_controller),
):
    """
    设置并启动温度程序。

    Args:
        request: 温度程序请求
        controller: 温度控制器实例

    Returns:
        SuccessResponse: 设置结果

    Raises:
        HTTPException: 设备未连接、保护触发或参数无效时抛出错误
    """
    # 验证设备状态
    try:
        validate_device_state(controller)
    except DeviceValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    # 验证所有程序段参数
    validation_errors = []
    for i, seg in enumerate(request.segments):
        # 验证目标温度范围
        if not (controller.MIN_TEMPERATURE <= seg.target_temperature <= controller.MAX_TEMPERATURE):
            validation_errors.append(
                f"Segment {i}: target_temperature {seg.target_temperature}K "
                f"out of range [{controller.MIN_TEMPERATURE}K, {controller.MAX_TEMPERATURE}K]"
            )
        # 验证升降温速率
        if abs(seg.ramp_rate) > 10:
            validation_errors.append(
                f"Segment {i}: ramp_rate {seg.ramp_rate}K/min exceeds limit (±10 K/min)"
            )
        # 验证保持时间
        if seg.hold_time < 0:
            validation_errors.append(
                f"Segment {i}: hold_time {seg.hold_time}s must be >= 0"
            )

    if validation_errors:
        raise HTTPException(
            status_code=400,
            detail="Program validation failed: " + "; ".join(validation_errors)
        )

    # 转换请求为程序段（schema中已经是K单位）
    segments = [
        TemperatureProgramSegment(
            target_temperature=seg.target_temperature,
            ramp_rate=seg.ramp_rate,
            hold_time=seg.hold_time,
            segment_id=i,
        )
        for i, seg in enumerate(request.segments)
    ]

    # 加载程序
    result = await controller.load_program(segments)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to load temperature program")

    # 启动程序
    result = await controller.start_program()
    return SuccessResponse(
        success=result,
        message=f"Temperature program started with {len(segments)} segments" if result else "Failed to start program",
    )


@router.post("/program/stop", response_model=SuccessResponse)
async def stop_temperature_program(
    controller: TemperatureController = Depends(get_temperature_controller),
):
    """
    停止温度程序。

    Args:
        controller: 温度控制器实例

    Returns:
        SuccessResponse: 停止结果
    """
    result = await controller.stop_program()
    return SuccessResponse(
        success=result,
        message="Temperature program stopped" if result else "Failed to stop program",
    )


@router.post("/pid", response_model=SuccessResponse)
async def set_pid_parameters(
    request: PIDParametersRequest,
    controller: TemperatureController = Depends(get_temperature_controller),
):
    """
    设置PID参数。

    Args:
        request: PID参数请求
        controller: 温度控制器实例

    Returns:
        SuccessResponse: 设置结果

    Raises:
        HTTPException: 设备未连接或参数无效时抛出错误
    """
    # 验证设备状态
    try:
        validate_device_state(controller)
    except DeviceValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    # 验证PID参数范围
    if not (0.1 <= request.kp <= 100):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Kp: {request.kp}, must be 0.1-100"
        )
    if not (0.001 <= request.ki <= 10):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Ki: {request.ki}, must be 0.001-10"
        )
    if not (0.001 <= request.kd <= 10):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Kd: {request.kd}, must be 0.001-10"
        )
    if not (controller.MIN_TEMPERATURE <= request.setpoint <= controller.MAX_TEMPERATURE):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid setpoint: {request.setpoint}K, must be {controller.MIN_TEMPERATURE}K-{controller.MAX_TEMPERATURE}K"
        )

    result = await controller.set_pid_parameters(
        kp=request.kp,
        ki=request.ki,
        kd=request.kd,
        setpoint=request.setpoint,
    )

    return SuccessResponse(
        success=result,
        message=f"PID parameters updated: Kp={request.kp}, Ki={request.ki}, Kd={request.kd}, setpoint={request.setpoint}K" if result else "Failed to update PID parameters",
    )


@router.get("/pid")
async def get_pid_parameters(
    controller: TemperatureController = Depends(get_temperature_controller),
):
    """
    获取当前PID参数。

    Args:
        controller: 温度控制器实例

    Returns:
        dict: 当前PID参数配置
    """
    return {
        "kp": controller.pid_params.kp,
        "ki": controller.pid_params.ki,
        "kd": controller.pid_params.kd,
        "setpoint": controller.pid_params.setpoint,
        "setpoint_celsius": round(controller.pid_params.setpoint - 273.15, 2),
        "output_min": controller.pid_params.output_min,
        "output_max": controller.pid_params.output_max,
        "valid_ranges": {
            "kp": "0.1-100",
            "ki": "0.001-10",
            "kd": "0.001-10",
            "setpoint": f"{controller.MIN_TEMPERATURE}K-{controller.MAX_TEMPERATURE}K",
        },
    }


@router.post("/pid/validate")
async def validate_pid_parameters(
    request: PIDParametersRequest,
    controller: TemperatureController = Depends(get_temperature_controller),
):
    """
    验证PID参数是否有效（不实际应用）。

    Args:
        request: PID参数请求
        controller: 温度控制器实例

    Returns:
        dict: 验证结果
    """
    errors = []
    warnings = []

    # 验证Kp
    if not (0.1 <= request.kp <= 100):
        errors.append(f"Kp={request.kp} 超出有效范围 [0.1, 100]")
    elif request.kp > 50:
        warnings.append(f"Kp={request.kp} 较大，可能导致系统震荡")

    # 验证Ki
    if not (0.001 <= request.ki <= 10):
        errors.append(f"Ki={request.ki} 超出有效范围 [0.001, 10]")
    elif request.ki > 5:
        warnings.append(f"Ki={request.ki} 较大，可能导致积分饱和")

    # 验证Kd
    if not (0.001 <= request.kd <= 10):
        errors.append(f"Kd={request.kd} 超出有效范围 [0.001, 10]")

    # 验证setpoint
    if not (controller.MIN_TEMPERATURE <= request.setpoint <= controller.MAX_TEMPERATURE):
        errors.append(
            f"setpoint={request.setpoint}K 超出有效范围 "
            f"[{controller.MIN_TEMPERATURE}K, {controller.MAX_TEMPERATURE}K]"
        )

    # 检查参数组合是否合理
    if request.kp > 10 and request.ki > 1:
        warnings.append("Kp和Ki同时较大，建议降低其中之一以避免超调")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "parameters": {
            "kp": request.kp,
            "ki": request.ki,
            "kd": request.kd,
            "setpoint_k": request.setpoint,
            "setpoint_c": round(request.setpoint - 273.15, 2),
        },
    }


@router.post("/pid/start", response_model=SuccessResponse)
async def start_pid_control(
    controller: TemperatureController = Depends(get_temperature_controller),
):
    """
    启动PID控制。

    Args:
        controller: 温度控制器实例

    Returns:
        SuccessResponse: 启动结果

    Raises:
        HTTPException: 设备未连接或保护触发时抛出错误
    """
    # 验证设备状态
    try:
        validate_device_state(controller)
    except DeviceValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    result = await controller.start_pid_control()
    setpoint_c = controller.pid_params.setpoint - 273.15
    return SuccessResponse(
        success=result,
        message=f"PID control started (setpoint={setpoint_c:.1f}°C)" if result else "Failed to start PID control",
    )


@router.post("/pid/stop", response_model=SuccessResponse)
async def stop_pid_control(
    controller: TemperatureController = Depends(get_temperature_controller),
):
    """
    停止PID控制。

    Args:
        controller: 温度控制器实例

    Returns:
        SuccessResponse: 停止结果
    """
    result = await controller.stop_pid_control()
    return SuccessResponse(
        success=result,
        message="PID control stopped" if result else "Failed to stop PID control",
    )


@router.get("/status", response_model=TemperatureStatusResponse)
async def get_temperature_status(
    controller: TemperatureController = Depends(get_temperature_controller),
):
    """
    获取温度控制器状态。

    Args:
        controller: 温度控制器实例

    Returns:
        TemperatureStatusResponse: 完整状态信息（温度单位：K）
    """
    status = await controller.read_status()

    # 温度单位：K（与schema定义一致）
    current_temp_k = status["current_temperature"]
    target_temp_k = status["setpoint"]

    # 计算程序段索引
    program_info = status.get("program", {})
    current_segment = program_info.get("current_segment", 0)

    # 保护状态
    protection_info = status.get("protection", {})
    protection_active = protection_info.get("triggered", False)
    protection_type = protection_info.get("type", None)

    # 程序运行状态
    program_running = program_info.get("running", False)

    return TemperatureStatusResponse(
        device_id=status["device_id"],
        status=status["status"],
        current_temperature=round(current_temp_k, 2),
        target_temperature=round(target_temp_k, 2),
        heater_power=round(status["current_output"], 2),
        pid_enabled=status["pid_running"],
        program_running=program_running,
        program_segment=current_segment,
        protection_active=protection_active,
        protection_type=protection_type,
        connected=status["connected"],
        simulation=controller.simulation_mode,
    )


@router.post("/protection", response_model=SuccessResponse)
async def set_protection_config(
    request: ProtectionConfigRequest,
    controller: TemperatureController = Depends(get_temperature_controller),
):
    """
    设置温度保护配置。

    温度单位：开尔文(K)，与schema定义一致。

    Args:
        request: 保护配置请求（温度单位：K）
        controller: 温度控制器实例

    Returns:
        SuccessResponse: 设置结果
    """
    # 温度单位已为开尔文(K)，无需转换
    result = await controller.set_protection_config(
        high_temp_limit=request.max_temperature,
        low_temp_limit=request.min_temperature,
        max_rate_limit=request.max_deviation,
        enable_high_temp=True,
        enable_low_temp=True,
        enable_rate_limit=True,
    )

    return SuccessResponse(
        success=result,
        message=f"Protection config updated: high={request.max_temperature}K, low={request.min_temperature}K" if result else "Failed to update protection config",
    )


@router.post("/protection/clear", response_model=SuccessResponse)
async def clear_protection(
    controller: TemperatureController = Depends(get_temperature_controller),
):
    """
    清除温度保护状态。

    Args:
        controller: 温度控制器实例

    Returns:
        SuccessResponse: 清除结果

    Raises:
        HTTPException: 温度不在安全范围时抛出错误
    """
    result = await controller.clear_protection()
    if not result:
        raise HTTPException(
            status_code=400,
            detail="Cannot clear protection: temperature still out of range",
        )

    return SuccessResponse(
        success=True,
        message="Temperature protection cleared",
    )


@router.post("/emergency_stop", response_model=SuccessResponse)
async def emergency_stop(
    controller: TemperatureController = Depends(get_temperature_controller),
):
    """
    紧急停止。

    Args:
        controller: 温度控制器实例

    Returns:
        SuccessResponse: 急停结果
    """
    result = await controller.emergency_stop()
    return SuccessResponse(
        success=result,
        message="Emergency stop triggered",
    )


@router.post("/reset", response_model=SuccessResponse)
async def reset_emergency(
    controller: TemperatureController = Depends(get_temperature_controller),
):
    """
    复位急停状态。

    Args:
        controller: 温度控制器实例

    Returns:
        SuccessResponse: 复位结果
    """
    result = await controller.reset_emergency()
    return SuccessResponse(
        success=result,
        message="Emergency stop reset",
    )


@router.post("/history", response_model=TemperatureHistoryResponse)
async def get_temperature_history(
    request: TemperatureHistoryRequest,
    controller: TemperatureController = Depends(get_temperature_controller),
):
    """
    获取温度历史记录。

    温度单位：开尔文(K)，与schema定义一致。

    Args:
        request: 历史记录请求
        controller: 温度控制器实例

    Returns:
        TemperatureHistoryResponse: 历史记录（温度单位：K）
    """
    end_time = time.time()
    start_time = end_time - request.duration_seconds

    history = await controller.get_temperature_history(
        start_time=start_time,
        end_time=end_time,
        limit=None,
    )

    # 提取数据（温度单位：K，与schema定义一致）
    timestamps = [dp["timestamp"] for dp in history]
    temperatures = [dp["temperature"] for dp in history]
    setpoints = [dp["setpoint"] for dp in history]

    return TemperatureHistoryResponse(
        success=True,
        message=f"Retrieved {len(history)} records",
        timestamps=timestamps,
        temperatures=temperatures,
        setpoints=setpoints,
    )


@router.post("/history/clear", response_model=SuccessResponse)
async def clear_temperature_history(
    controller: TemperatureController = Depends(get_temperature_controller),
):
    """
    清除温度历史记录。

    Args:
        controller: 温度控制器实例

    Returns:
        SuccessResponse: 清除结果
    """
    await controller.clear_temperature_history()
    return SuccessResponse(
        success=True,
        message="Temperature history cleared",
    )


@router.get("/history/export")
async def export_temperature_history(
    format: str = "csv",
    controller: TemperatureController = Depends(get_temperature_controller),
):
    """
    导出温度历史记录。

    Args:
        format: 导出格式（csv或json）
        controller: 温度控制器实例

    Returns:
        dict: 导出的数据

    Raises:
        HTTPException: 不支持的格式时抛出错误
    """
    try:
        data = await controller.export_temperature_history(format)
        return {
            "success": True,
            "format": format,
            "data": data,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/connect", response_model=SuccessResponse)
async def connect_temperature_controller(
    controller: TemperatureController = Depends(get_temperature_controller),
):
    """
    连接温度控制器。

    Args:
        controller: 温度控制器实例

    Returns:
        SuccessResponse: 连接结果
    """
    result = await controller.connect()
    return SuccessResponse(
        success=result,
        message="Connected" if result else "Failed to connect",
    )


@router.post("/disconnect", response_model=SuccessResponse)
async def disconnect_temperature_controller(
    controller: TemperatureController = Depends(get_temperature_controller),
):
    """
    断开温度控制器。

    Args:
        controller: 温度控制器实例

    Returns:
        SuccessResponse: 断开结果
    """
    result = await controller.disconnect()
    return SuccessResponse(
        success=result,
        message="Disconnected",
    )
