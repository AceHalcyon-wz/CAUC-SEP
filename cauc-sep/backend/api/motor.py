"""
电机控制 API 路由模块

功能：
- 电机连接/断开
- 绝对/相对定位
- JOG 点动
- 急停和复位
- 限位配置
- PR 路径配置和触发
- 回零
- 报警复位
- 参数保存/恢复
- 状态字和报警代码读取

修复记录：
- SubTask 5.1: 统一错误响应格式（HTTP状态码、错误代码、描述）
- SubTask 5.2: 添加请求参数验证（Pydantic模型）
- SubTask 5.3: 完善软件限位验证逻辑
- SubTask 5.4: 添加操作日志记录
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from api.schemas import (
    AlarmCodeResponse,
    ErrorCode,
    ErrorResponse,
    HomeRequest,
    JogRequest,
    LimitConfigRequest,
    MotorStatusResponse,
    MoveRequest,
    MoveResponse,
    PRPathConfigRequest,
    PRPathTriggerRequest,
    StatusWordResponse,
    SuccessResponse,
)
from core.abstract import DeviceStatus
from core.device_registry import DeviceRegistry
from core.device_utils import DeviceValidationError, validate_device_state
from core.dm2c_driver import ALARM_CODES, LeadshineDM2C, mm_to_steps, steps_to_mm
from middleware.audit import audit_logger

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/motor",
    tags=["motor"],
    responses={
        400: {"model": ErrorResponse, "description": "请求参数错误或设备状态异常"},
        422: {"model": ErrorResponse, "description": "参数验证失败"},
        500: {"model": ErrorResponse, "description": "设备内部错误"},
        503: {"model": ErrorResponse, "description": "服务不可用"},
    },
)

# 设备注册表中的设备ID常量
DM2C_DEVICE_ID = "dm2c_main"


# ==================== 异常处理器 ====================


class MotorAPIException(Exception):
    """
    电机API异常类。

    用于统一处理API层的错误响应，扩展自 DeviceValidationError。

    Attributes:
        status_code: HTTP状态码
        error_code: 业务错误代码
        message: 错误简要描述
        detail: 错误详细信息
    """

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        detail: str | None = None,
    ):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.detail = detail
        super().__init__(message)


def create_error_response(
    error_code: str,
    message: str,
    detail: str | None = None,
) -> dict[str, Any]:
    """
    创建统一格式的错误响应。

    Args:
        error_code: 错误代码
        message: 错误简要描述
        detail: 错误详细信息

    Returns:
        Dict[str, Any]: 统一格式的错误响应字典
    """
    return {
        "success": False,
        "error_code": error_code,
        "message": message,
        "detail": detail,
        "timestamp": datetime.now().isoformat(),
    }


# ==================== 依赖注入 ====================


def get_dm2c() -> LeadshineDM2C:
    """
    获取电机驱动器实例。

    从设备注册表中获取驱动器实例。

    Raises:
        HTTPException: 当驱动器未初始化时抛出503错误

    Returns:
        LeadshineDM2C: 驱动器实例
    """
    if not DeviceRegistry.has_device(DM2C_DEVICE_ID):
        raise MotorAPIException(
            status_code=503,
            error_code=ErrorCode.DEVICE_NOT_INITIALIZED,
            message="电机驱动器未初始化",
            detail="请检查系统启动日志，确认驱动器初始化成功",
        )
    return DeviceRegistry.get_device(DM2C_DEVICE_ID)


def set_dm2c(instance: LeadshineDM2C) -> None:
    """
    设置电机驱动器实例。

    将驱动器实例注册到设备注册表。

    Args:
        instance: 驱动器实例
    """
    DeviceRegistry.register(DM2C_DEVICE_ID, instance)


# ==================== 操作日志记录 ====================


def log_motor_operation(
    operation: str,
    params: dict[str, Any] | None = None,
    result: str = "success",
    extra_data: dict[str, Any] | None = None,
) -> None:
    """
    记录电机操作日志。

    Args:
        operation: 操作类型
        params: 操作参数
        result: 操作结果
        extra_data: 额外数据
    """
    log_data = {
        "operation": operation,
        "result": result,
        "timestamp": datetime.now().isoformat(),
    }
    if params:
        log_data["params"] = params
    if extra_data:
        log_data.update(extra_data)

    logger.info(f"[Motor] {operation}: {result}", extra=log_data)

    # 写入审计日志
    audit_logger.log_request(
        method="MOTOR_OP",
        path=f"/api/v1/motor/{operation}",
        params=params,
        response_status=200 if result == "success" else 400,
        response_message=result,
        extra_data=extra_data,
    )


# ==================== 软件限位验证 ====================


def validate_soft_limit(
    driver: LeadshineDM2C,
    position_mm: float,
) -> tuple[bool, str | None]:
    """
    验证目标位置是否在软件限位范围内。

    Args:
        driver: 驱动器实例
        position_mm: 目标位置（毫米）

    Returns:
        Tuple[bool, Optional[str]]: (是否有效, 错误消息)
    """
    if not driver.limit_config.enable:
        return True, None

    if not driver.limit_config.is_within_limits(position_mm):
        error_msg = (
            f"目标位置 {position_mm:.3f}mm 超出软件限位范围 "
            f"[{driver.limit_config.negative_limit}mm, "
            f"{driver.limit_config.positive_limit}mm]"
        )
        return False, error_msg

    return True, None


def validate_device_state_with_exception(
    driver: LeadshineDM2C,
    require_ready: bool = True,
) -> None:
    """
    验证设备状态是否允许操作（包装器）。

    调用 core.device_utils.validate_device_state 并捕获异常，
    将 DeviceValidationError 转换为 MotorAPIException。

    Args:
        driver: 驱动器实例
        require_ready: 是否要求设备处于就绪状态

    Raises:
        MotorAPIException: 设备状态不允许操作时抛出
    """
    try:
        validate_device_state(driver, require_ready=require_ready)
    except DeviceValidationError as e:
        # 根据设备状态映射到对应的错误代码
        error_code_map = {
            DeviceStatus.DISCONNECTED.value: ErrorCode.DEVICE_NOT_CONNECTED,
            DeviceStatus.EMERGENCY_STOP.value: ErrorCode.DEVICE_IN_EMERGENCY_STOP,
            DeviceStatus.ERROR.value: ErrorCode.DEVICE_ERROR,
            DeviceStatus.BUSY.value: ErrorCode.DEVICE_BUSY,
        }

        # 根据状态确定HTTP状态码
        status_code_map = {
            DeviceStatus.DISCONNECTED.value: 400,
            DeviceStatus.EMERGENCY_STOP.value: 400,
            DeviceStatus.ERROR.value: 500,
            DeviceStatus.BUSY.value: 400,
        }

        # 构建详细错误信息
        detail_map = {
            DeviceStatus.DISCONNECTED.value: "请先调用 /api/v1/motor/connect 连接电机",
            DeviceStatus.EMERGENCY_STOP.value: "请先调用 /api/v1/motor/reset 复位急停状态",
            DeviceStatus.ERROR.value: f"设备错误: {getattr(driver, 'last_error', None) or '未知错误'}",
            DeviceStatus.BUSY.value: "请等待当前运动完成后再执行新操作",
        }

        status_value = e.status or DeviceStatus.DISCONNECTED.value

        raise MotorAPIException(
            status_code=status_code_map.get(status_value, 400),
            error_code=error_code_map.get(status_value, ErrorCode.DEVICE_ERROR),
            message=e.message,
            detail=detail_map.get(status_value),
        )


# ==================== API端点 ====================


@router.get("/status", response_model=MotorStatusResponse)
async def get_motor_status(driver: LeadshineDM2C = Depends(get_dm2c)):
    """
    获取电机完整状态。

    Returns:
        MotorStatusResponse: 包含位置、状态字、报警代码等完整信息
    """
    log_motor_operation("status_query", result="success")
    status = await driver.read_status()
    return MotorStatusResponse(**status)


@router.post("/connect", response_model=SuccessResponse)
async def connect_motor(driver: LeadshineDM2C = Depends(get_dm2c)):
    """
    连接电机驱动器。

    Returns:
        SuccessResponse: 连接结果
    """
    log_motor_operation("connect", result="pending")

    result = await driver.connect()

    if result:
        log_motor_operation(
            "connect",
            result="success",
            extra_data={"status": driver.status.value},
        )
    else:
        log_motor_operation(
            "connect",
            result="failed",
            extra_data={"error": driver.last_error},
        )

    return SuccessResponse(
        success=result,
        message="电机已连接" if result else "电机连接失败",
    )


@router.post("/disconnect", response_model=SuccessResponse)
async def disconnect_motor(driver: LeadshineDM2C = Depends(get_dm2c)):
    """
    断开电机驱动器。

    Returns:
        SuccessResponse: 断开结果
    """
    log_motor_operation("disconnect", result="pending")

    result = await driver.disconnect()

    log_motor_operation(
        "disconnect",
        result="success" if result else "failed",
    )

    return SuccessResponse(
        success=result,
        message="电机已断开",
    )


@router.post("/move", response_model=MoveResponse)
async def motor_move(
    request: MoveRequest,
    driver: LeadshineDM2C = Depends(get_dm2c),
):
    """
    电机绝对定位。

    Args:
        request: 运动请求，包含目标位置、速度和加速度
        driver: 驱动器实例

    Returns:
        MoveResponse: 运动启动结果

    Raises:
        MotorAPIException: 设备状态异常或位置超出限位时抛出
    """
    # 验证设备状态
    validate_device_state_with_exception(driver, require_ready=False)

    # 验证软件限位
    is_valid, error_msg = validate_soft_limit(driver, request.position_mm)
    if not is_valid:
        log_motor_operation(
            "move",
            params={
                "position_mm": request.position_mm,
                "velocity_mm_s": request.velocity_mm_s,
            },
            result="rejected",
            extra_data={"reason": error_msg},
        )
        raise MotorAPIException(
            status_code=400,
            error_code=ErrorCode.SOFT_LIMIT_EXCEEDED,
            message="目标位置超出软件限位",
            detail=error_msg,
        )

    # 记录操作日志
    log_motor_operation(
        "move",
        params={
            "position_mm": request.position_mm,
            "velocity_mm_s": request.velocity_mm_s,
            "accel_mm_s2": request.accel_mm_s2,
            "decel_mm_s2": request.decel_mm_s2,
        },
        result="pending",
    )

    # 执行运动
    position_steps = mm_to_steps(request.position_mm, driver.steps_per_mm)

    result = await driver.move_abs(
        request.position_mm,
        request.velocity_mm_s,
        request.accel_mm_s2,
        request.decel_mm_s2,
    )

    if result:
        log_motor_operation(
            "move",
            params={"position_mm": request.position_mm},
            result="started",
            extra_data={"target_steps": position_steps},
        )
    else:
        log_motor_operation(
            "move",
            params={"position_mm": request.position_mm},
            result="failed",
            extra_data={"error": driver.last_error},
        )

    return MoveResponse(
        success=result,
        message="运动已启动" if result else "运动启动失败（请检查限位设置）",
        target_position_steps=position_steps,
        target_position_mm=request.position_mm,
    )


@router.post("/jog", response_model=SuccessResponse)
async def motor_jog(
    request: JogRequest,
    driver: LeadshineDM2C = Depends(get_dm2c),
):
    """
    JOG 点动。

    Args:
        request: JOG 请求，包含方向和速度
        driver: 驱动器实例

    Returns:
        SuccessResponse: JOG 启动结果
    """
    # 验证设备状态
    validate_device_state_with_exception(driver, require_ready=False)

    # 验证方向参数
    if request.direction not in (1, -1):
        raise MotorAPIException(
            status_code=422,
            error_code=ErrorCode.INVALID_PARAMETER,
            message="方向参数无效",
            detail="direction 必须为 1（正向）或 -1（负向）",
        )

    # 记录操作日志
    log_motor_operation(
        "jog",
        params={
            "direction": request.direction,
            "velocity_mm_s": request.velocity_mm_s,
        },
        result="pending",
    )

    # 从驱动器配置中获取 steps_per_mm 进行速度转换
    velocity_steps = int(request.velocity_mm_s * driver.steps_per_mm)
    result = await driver.jog(request.direction, velocity_steps)

    if result:
        log_motor_operation(
            "jog",
            params={"direction": request.direction},
            result="started",
        )
    else:
        log_motor_operation(
            "jog",
            params={"direction": request.direction},
            result="failed",
        )

    return SuccessResponse(
        success=result,
        message=f"JOG {'正向' if request.direction > 0 else '负向'}已启动",
    )


@router.post("/emergency_stop", response_model=SuccessResponse)
async def emergency_stop(driver: LeadshineDM2C = Depends(get_dm2c)):
    """
    软件急停。

    Returns:
        SuccessResponse: 急停结果
    """
    log_motor_operation("emergency_stop", result="pending", extra_data={"severity": "critical"})

    result = await driver.emergency_stop()

    log_motor_operation(
        "emergency_stop",
        result="success" if result else "failed",
        extra_data={"severity": "critical"},
    )

    return SuccessResponse(
        success=result,
        message="急停已触发",
    )


@router.post("/reset", response_model=SuccessResponse)
async def reset_emergency(driver: LeadshineDM2C = Depends(get_dm2c)):
    """
    复位急停状态。

    Returns:
        SuccessResponse: 复位结果
    """
    log_motor_operation("reset_emergency", result="pending")

    result = await driver.reset_emergency()

    log_motor_operation(
        "reset_emergency",
        result="success" if result else "failed",
    )

    return SuccessResponse(
        success=result,
        message="急停状态已复位",
    )


@router.get("/limits")
async def get_limits(driver: LeadshineDM2C = Depends(get_dm2c)):
    """
    获取限位配置。

    Returns:
        dict: 包含正负限位毫米值
    """
    log_motor_operation("get_limits", result="success")
    return {
        "positive_mm": driver.limit_config.positive_limit,
        "negative_mm": driver.limit_config.negative_limit,
        "enabled": driver.limit_config.enable,
    }


@router.post("/limits", response_model=SuccessResponse)
async def set_limits(
    request: LimitConfigRequest,
    driver: LeadshineDM2C = Depends(get_dm2c),
):
    """
    设置限位。

    Args:
        request: 限位配置请求
        driver: 驱动器实例

    Returns:
        SuccessResponse: 设置结果

    Raises:
        MotorAPIException: 限位参数无效时抛出
    """
    # 验证限位参数
    if request.negative_mm >= request.positive_mm:
        raise MotorAPIException(
            status_code=422,
            error_code=ErrorCode.INVALID_PARAMETER,
            message="限位参数无效",
            detail=f"负向限位({request.negative_mm}mm)必须小于正向限位({request.positive_mm}mm)",
        )

    log_motor_operation(
        "set_limits",
        params={
            "positive_mm": request.positive_mm,
            "negative_mm": request.negative_mm,
        },
        result="pending",
    )

    driver.set_soft_limits(request.positive_mm, request.negative_mm)

    log_motor_operation(
        "set_limits",
        params={
            "positive_mm": request.positive_mm,
            "negative_mm": request.negative_mm,
        },
        result="success",
    )

    return SuccessResponse(
        success=True,
        message=f"限位已更新: [{request.negative_mm}mm, {request.positive_mm}mm]",
    )


@router.post("/pr/config", response_model=SuccessResponse)
async def configure_pr_path(
    request: PRPathConfigRequest,
    driver: LeadshineDM2C = Depends(get_dm2c),
):
    """
    配置 PR 路径。

    Args:
        request: PR 路径配置请求
        driver: 驱动器实例

    Returns:
        SuccessResponse: 配置结果
    """
    # 验证设备状态
    validate_device_state_with_exception(driver, require_ready=False)

    # 验证路径编号
    if not 0 <= request.path_number <= 15:
        raise MotorAPIException(
            status_code=422,
            error_code=ErrorCode.PARAM_OUT_OF_RANGE,
            message="路径编号超出范围",
            detail="路径编号必须在 0-15 之间",
        )

    # 验证软件限位（仅对位置定位模式）
    if request.mode in (1, 0x41):  # 绝对位置或相对位置
        is_valid, error_msg = validate_soft_limit(driver, request.position_mm)
        if not is_valid:
            log_motor_operation(
                "pr_config",
                params={"path_number": request.path_number, "position_mm": request.position_mm},
                result="rejected",
                extra_data={"reason": error_msg},
            )
            raise MotorAPIException(
                status_code=400,
                error_code=ErrorCode.SOFT_LIMIT_EXCEEDED,
                message="目标位置超出软件限位",
                detail=error_msg,
            )

    log_motor_operation(
        "pr_config",
        params={
            "path_number": request.path_number,
            "mode": request.mode,
            "position_mm": request.position_mm,
        },
        result="pending",
    )

    position_steps = mm_to_steps(request.position_mm, driver.steps_per_mm)
    result = await driver.configure_pr_path(
        path_number=request.path_number,
        mode=request.mode,
        position=position_steps,
        velocity=request.velocity_mm_s,
        accel_time=request.accel_time,
        decel_time=request.decel_time,
        dwell_time=request.dwell_time,
        special_param=request.special_param,
    )

    log_motor_operation(
        "pr_config",
        params={"path_number": request.path_number},
        result="success" if result else "failed",
    )

    return SuccessResponse(
        success=result,
        message=f"PR路径 {request.path_number} 已配置" if result else "PR路径配置失败",
    )


@router.post("/pr/trigger", response_model=SuccessResponse)
async def trigger_pr_path(
    request: PRPathTriggerRequest,
    driver: LeadshineDM2C = Depends(get_dm2c),
):
    """
    触发 PR 路径运行。

    Args:
        request: PR 路径触发请求
        driver: 驱动器实例

    Returns:
        SuccessResponse: 触发结果
    """
    # 验证设备状态
    validate_device_state_with_exception(driver, require_ready=False)

    # 验证路径编号
    if not 0 <= request.path_number <= 15:
        raise MotorAPIException(
            status_code=422,
            error_code=ErrorCode.PARAM_OUT_OF_RANGE,
            message="路径编号超出范围",
            detail="路径编号必须在 0-15 之间",
        )

    log_motor_operation(
        "pr_trigger",
        params={"path_number": request.path_number},
        result="pending",
    )

    result = await driver.trigger_pr_path(request.path_number)

    log_motor_operation(
        "pr_trigger",
        params={"path_number": request.path_number},
        result="success" if result else "failed",
    )

    return SuccessResponse(
        success=result,
        message=f"PR路径 {request.path_number} 已触发" if result else "PR路径触发失败",
    )


@router.post("/home", response_model=SuccessResponse)
async def home(
    request: HomeRequest,
    driver: LeadshineDM2C = Depends(get_dm2c),
):
    """
    回零操作。

    Args:
        request: 回零请求
        driver: 驱动器实例

    Returns:
        SuccessResponse: 回零结果
    """
    # 验证设备状态
    validate_device_state_with_exception(driver, require_ready=False)

    log_motor_operation(
        "home",
        params={"mode": request.mode},
        result="pending",
    )

    result = await driver.home(mode=request.mode)

    log_motor_operation(
        "home",
        params={"mode": request.mode},
        result="started" if result else "failed",
    )

    return SuccessResponse(
        success=result,
        message="回零已启动" if result else "回零启动失败",
    )


@router.post("/reset_alarm", response_model=SuccessResponse)
async def reset_alarm(driver: LeadshineDM2C = Depends(get_dm2c)):
    """
    报警复位。

    Returns:
        SuccessResponse: 复位结果
    """
    # 验证设备状态
    validate_device_state_with_exception(driver, require_ready=False)

    log_motor_operation("reset_alarm", result="pending")

    result = await driver.reset_alarm()

    log_motor_operation(
        "reset_alarm",
        result="success" if result else "failed",
    )

    return SuccessResponse(
        success=result,
        message="报警已复位" if result else "报警复位失败",
    )


@router.post("/save_params", response_model=SuccessResponse)
async def save_params(driver: LeadshineDM2C = Depends(get_dm2c)):
    """
    保存参数到 EEPROM。

    Returns:
        SuccessResponse: 保存结果
    """
    # 验证设备状态
    validate_device_state_with_exception(driver, require_ready=False)

    log_motor_operation("save_params", result="pending")

    result = await driver.save_parameters()

    log_motor_operation(
        "save_params",
        result="success" if result else "failed",
    )

    return SuccessResponse(
        success=result,
        message="参数已保存到EEPROM" if result else "参数保存失败",
    )


@router.post("/factory_reset", response_model=SuccessResponse)
async def factory_reset(driver: LeadshineDM2C = Depends(get_dm2c)):
    """
    恢复出厂设置。

    Returns:
        SuccessResponse: 恢复结果
    """
    # 验证设备状态
    validate_device_state_with_exception(driver, require_ready=False)

    log_motor_operation("factory_reset", result="pending", extra_data={"severity": "warning"})

    result = await driver.factory_reset()

    log_motor_operation(
        "factory_reset",
        result="success" if result else "failed",
        extra_data={"severity": "warning"},
    )

    return SuccessResponse(
        success=result,
        message="已恢复出厂设置" if result else "恢复出厂设置失败",
    )


@router.get("/status_word", response_model=StatusWordResponse)
async def read_status_word(driver: LeadshineDM2C = Depends(get_dm2c)):
    """
    读取状态字。

    Returns:
        StatusWordResponse: 解析后的状态字信息
    """
    log_motor_operation("read_status_word", result="success")
    status_word = await driver.read_status_word()
    return StatusWordResponse(**status_word)


@router.get("/alarm_code", response_model=AlarmCodeResponse)
async def read_alarm_code(driver: LeadshineDM2C = Depends(get_dm2c)):
    """
    读取报警代码。

    Returns:
        AlarmCodeResponse: 报警代码和描述
    """
    log_motor_operation("read_alarm_code", result="success")
    alarm_code = await driver.read_alarm_code()
    return AlarmCodeResponse(
        alarm_code=alarm_code,
        alarm_text=ALARM_CODES.get(alarm_code, "未知故障"),
    )
