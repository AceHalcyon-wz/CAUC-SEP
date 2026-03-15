"""
电磁铁控制 API 路由模块

文件名: electromagnet.py
路径: backend/api/
功能: 电磁铁控制API，提供电流设置、扫描模式、校准管理等接口
作者: CAUC-SEP Team
创建日期: 2024-01-01
依赖: FastAPI, core.electromagnet_driver, core.device_registry, api.schemas

主要功能：
- 恒流模式电流设置（动态范围验证）
- 扫描模式控制（正向/反向/三角波）
- 扫描参数预验证
- 磁场-电流校准管理
- 状态查询
- 过流保护复位
- 紧急停止

API端点：
- GET /status: 获取电磁铁完整状态
- POST /current: 设置恒流模式电流值
- POST /scan: 启动扫描模式
- POST /scan/validate: 预验证扫描参数
- POST /scan/stop: 停止扫描模式
- POST /calibrate: 执行磁场-电流校准
- GET /calibration: 获取校准数据
- DELETE /calibration: 清除所有校准数据
- POST /calibration/validate: 预验证校准数据
- POST /connect: 连接电磁铁驱动器
- POST /disconnect: 断开电磁铁驱动器
- POST /emergency_stop: 紧急停止
- POST /reset_emergency: 复位紧急停止状态
- POST /reset_overcurrent: 复位过流保护状态
- POST /field: 设置目标磁场值（自动转换为电流）

安全警告：
- 实验时必须有人值守
- 首次使用前验证电流限制参数
- 过流保护触发后需手动复位
- 动态验证电流范围（使用设备配置的max_current_limit）
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.schemas import (
    ElectromagnetCalibrateRequest,
    ElectromagnetScanRequest,
    ElectromagnetScanValidateRequest,
    ElectromagnetScanValidateResponse,
    ElectromagnetSetCurrentRequest,
    ElectromagnetStatusResponse,
    ScanMode,
    SuccessResponse,
)
from core.device_management.device_registry import DeviceRegistry
from core.device_management.device_utils import DeviceValidationError, validate_device_state
from core.electromagnet_driver import (
    OVERCURRENT_THRESHOLD,
    ElectromagnetDriver,
    ElectromagnetStatus,
)
from core.electromagnet_driver import ScanMode as DriverScanMode

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/electromagnet",
    tags=["electromagnet"],
    responses={404: {"description": "Not found"}},
)


def get_electromagnet() -> ElectromagnetDriver:
    """
    获取电磁铁驱动器实例。

    Raises:
        HTTPException: 当驱动器未初始化时抛出 503 错误

    Returns:
        ElectromagnetDriver: 驱动器实例
    """
    try:
        return DeviceRegistry.get_device("electromagnet")
    except KeyError:
        raise HTTPException(status_code=503, detail="Electromagnet not initialized")


def set_electromagnet(instance: ElectromagnetDriver) -> None:
    """
    设置电磁铁驱动器实例。

    Args:
        instance: 驱动器实例
    """
    DeviceRegistry.register("electromagnet", instance)


def _validate_current_range(driver: ElectromagnetDriver, current: float) -> None:
    """
    验证电流值是否在设备允许的范围内。

    使用设备配置的max_current_limit进行动态验证，
    而非硬编码的最大值。

    Args:
        driver: 驱动器实例
        current: 待验证的电流值

    Raises:
        HTTPException: 电流超出范围时抛出 400 错误
    """
    max_limit = driver.max_current_limit

    if current < 0:
        raise HTTPException(status_code=400, detail=f"Current {current}A is below minimum 0A")

    if current > max_limit:
        raise HTTPException(
            status_code=400, detail=f"Current {current}A exceeds device limit {max_limit}A"
        )

    # 过流保护阈值警告
    if current > OVERCURRENT_THRESHOLD:
        raise HTTPException(
            status_code=400,
            detail=f"Current {current}A exceeds overcurrent threshold {OVERCURRENT_THRESHOLD}A",
        )


@router.get("/status", response_model=ElectromagnetStatusResponse)
async def get_electromagnet_status(
    driver: ElectromagnetDriver = Depends(get_electromagnet),
):
    """
    获取电磁铁完整状态。

    Returns:
        ElectromagnetStatusResponse: 包含电流、磁场、状态等完整信息
    """
    status = await driver.read_status()
    return ElectromagnetStatusResponse(**status)


@router.post("/current", response_model=SuccessResponse)
async def set_current(
    request: ElectromagnetSetCurrentRequest,
    driver: ElectromagnetDriver = Depends(get_electromagnet),
):
    """
    设置恒流模式电流值。

    使用设备配置的max_current_limit进行动态范围验证，
    而非硬编码的最大值。

    Args:
        request: 电流设置请求，包含目标电流值
        driver: 驱动器实例

    Returns:
        SuccessResponse: 设置结果

    Raises:
        HTTPException: 设备未连接、参数无效或超出设备限制
    """
    # 验证设备状态
    try:
        validate_device_state(driver)
    except DeviceValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    # 检查过流保护状态
    if driver.electromagnet_status == ElectromagnetStatus.OVERCURRENT:
        raise HTTPException(
            status_code=400, detail="Overcurrent protection triggered, please reset first"
        )

    # 动态验证电流范围
    _validate_current_range(driver, request.current)

    try:
        result = await driver.set_current(request.current)
        return SuccessResponse(
            success=result,
            message=(
                f"Current set to {request.current}A (limit: {driver.max_current_limit}A)"
                if result
                else "Failed to set current"
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/scan", response_model=SuccessResponse)
async def start_scan(
    request: ElectromagnetScanRequest,
    driver: ElectromagnetDriver = Depends(get_electromagnet),
):
    """
    启动扫描模式。

    使用设备配置的max_current_limit进行动态范围验证。
    支持可选的步进间隔参数用于精细控制。

    Args:
        request: 扫描请求，包含模式、起始电流、目标电流、扫描速率等
        driver: 驱动器实例

    Returns:
        SuccessResponse: 启动结果

    Raises:
        HTTPException: 设备未连接、参数无效或超出设备限制
    """
    # 验证设备状态
    try:
        validate_device_state(driver)
    except DeviceValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    # 检查过流保护状态
    if driver.electromagnet_status == ElectromagnetStatus.OVERCURRENT:
        raise HTTPException(
            status_code=400, detail="Overcurrent protection triggered, please reset first"
        )

    # 动态验证电流范围
    _validate_current_range(driver, request.start_current)
    _validate_current_range(driver, request.end_current)

    try:
        # 转换扫描模式
        mode_map = {
            ScanMode.FORWARD: DriverScanMode.FORWARD,
            ScanMode.REVERSE: DriverScanMode.REVERSE,
            ScanMode.TRIANGULAR: DriverScanMode.TRIANGULAR,
        }
        driver_mode = mode_map[request.mode]

        result = await driver.start_scan(
            mode=driver_mode,
            start_current=request.start_current,
            end_current=request.end_current,
            scan_rate=request.scan_rate,
            cycles=request.cycles,
            step_interval_ms=request.step_interval_ms,
        )
        return SuccessResponse(
            success=result,
            message=(
                (
                    f"Scan started: {request.mode.value} mode, "
                    f"{request.start_current}A -> {request.end_current}A "
                    f"(limit: {driver.max_current_limit}A)"
                )
                if result
                else "Failed to start scan"
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/scan/validate", response_model=ElectromagnetScanValidateResponse)
async def validate_scan_params(
    request: ElectromagnetScanValidateRequest,
    driver: ElectromagnetDriver = Depends(get_electromagnet),
):
    """
    预验证扫描参数。

    在启动扫描前验证参数有效性，返回详细的错误和警告信息。
    用于前端实时反馈。

    Args:
        request: 扫描参数验证请求
        driver: 驱动器实例

    Returns:
        ElectromagnetScanValidateResponse: 验证结果
    """
    # 转换扫描模式
    mode_map = {
        ScanMode.FORWARD: DriverScanMode.FORWARD,
        ScanMode.REVERSE: DriverScanMode.REVERSE,
        ScanMode.TRIANGULAR: DriverScanMode.TRIANGULAR,
    }
    driver_mode = mode_map[request.mode]

    # 使用驱动器的验证方法
    valid, errors = driver.validate_scan_params(
        mode=driver_mode,
        start_current=request.start_current,
        end_current=request.end_current,
        scan_rate=request.scan_rate,
        cycles=request.cycles,
    )

    # 计算预估时间
    estimated_duration = driver._estimate_scan_duration(
        mode=driver_mode,
        start_current=request.start_current,
        end_current=request.end_current,
        scan_rate=request.scan_rate,
        cycles=request.cycles,
    )

    # 生成警告信息
    warnings = []
    max_limit = driver.max_current_limit

    if request.start_current > max_limit * 0.9:
        warnings.append(f"Start current {request.start_current}A is close to limit {max_limit}A")
    if request.end_current > max_limit * 0.9:
        warnings.append(f"End current {request.end_current}A is close to limit {max_limit}A")
    if estimated_duration > 3600:
        warnings.append(f"Long scan duration: {estimated_duration/60:.1f} minutes")

    return ElectromagnetScanValidateResponse(
        valid=valid,
        errors=errors,
        warnings=warnings,
        estimated_duration_s=round(estimated_duration, 2) if valid else None,
    )


@router.post("/scan/stop", response_model=SuccessResponse)
async def stop_scan(driver: ElectromagnetDriver = Depends(get_electromagnet)):
    """
    停止扫描模式。

    Args:
        driver: 驱动器实例

    Returns:
        SuccessResponse: 停止结果
    """
    result = await driver.stop_scan()
    return SuccessResponse(
        success=result,
        message="Scan stopped" if result else "Failed to stop scan",
    )


@router.post("/calibrate", response_model=SuccessResponse)
async def calibrate(
    request: ElectromagnetCalibrateRequest,
    driver: ElectromagnetDriver = Depends(get_electromagnet),
):
    """
    执行磁场-电流校准。

    Args:
        request: 校准请求，包含校准点列表
        driver: 驱动器实例

    Returns:
        SuccessResponse: 校准结果

    Raises:
        HTTPException: 设备未连接或参数无效
    """
    # 验证设备状态
    try:
        validate_device_state(driver)
    except DeviceValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    try:
        calibration_points = [
            {"current": point.current, "field": point.field} for point in request.calibration_points
        ]
        result = await driver.calibrate(calibration_points)
        return SuccessResponse(
            success=result,
            message=(
                (f"Calibration completed with {len(request.calibration_points)} points")
                if result
                else "Calibration failed"
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/calibration")
async def get_calibration_data(
    driver: ElectromagnetDriver = Depends(get_electromagnet),
) -> dict[str, Any]:
    """
    获取校准数据。

    Args:
        driver: 驱动器实例

    Returns:
        dict: 校准数据，包含校准点和系数
    """
    return driver.get_calibration_data()


@router.delete("/calibration", response_model=SuccessResponse)
async def clear_calibration_data(
    driver: ElectromagnetDriver = Depends(get_electromagnet),
):
    """
    清除所有校准数据。

    重置为默认校准系数（0.2 T/A）。

    Args:
        driver: 驱动器实例

    Returns:
        SuccessResponse: 清除结果
    """
    result = await driver.clear_calibration()
    return SuccessResponse(
        success=result,
        message="Calibration data cleared, reset to default coefficient (0.2 T/A)",
    )


@router.post("/calibration/validate", response_model=ElectromagnetScanValidateResponse)
async def validate_calibration_data(
    request: ElectromagnetCalibrateRequest,
    driver: ElectromagnetDriver = Depends(get_electromagnet),
):
    """
    预验证校准数据。

    在执行校准前验证数据有效性，返回详细的错误和警告信息。

    Args:
        request: 校准请求
        driver: 驱动器实例

    Returns:
        ElectromagnetScanValidateResponse: 验证结果
    """
    errors = []
    warnings = []

    # 检查校准点数量
    if len(request.calibration_points) < 2:
        errors.append("At least 2 calibration points required")

    # 检查每个校准点
    currents = []
    for i, point in enumerate(request.calibration_points):
        # 电流范围检查
        if point.current < 0:
            errors.append(f"Point {i+1}: Current {point.current}A is negative")
        elif point.current > driver.max_current_limit:
            errors.append(
                f"Point {i+1}: Current {point.current}A exceeds limit {driver.max_current_limit}A"
            )

        # 磁场范围检查
        if point.field < 0:
            errors.append(f"Point {i+1}: Field {point.field}T is negative")
        elif point.field > 2.0:
            errors.append(f"Point {i+1}: Field {point.field}T exceeds maximum 2.0T")

        currents.append(point.current)

    # 检查电流分布
    if len(currents) >= 2:
        current_range = max(currents) - min(currents)
        if current_range < 1.0:
            warnings.append(
                f"Calibration current range ({current_range:.2f}A) is narrow, "
                "consider using a wider range for better accuracy"
            )

        # 检查是否有重复的电流值
        if len(set(currents)) < len(currents):
            warnings.append("Duplicate current values detected in calibration points")

    return ElectromagnetScanValidateResponse(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        estimated_duration_s=None,
    )


@router.post("/connect", response_model=SuccessResponse)
async def connect_electromagnet(driver: ElectromagnetDriver = Depends(get_electromagnet)):
    """
    连接电磁铁驱动器。

    Returns:
        SuccessResponse: 连接结果
    """
    result = await driver.connect()
    return SuccessResponse(
        success=result,
        message="Connected" if result else "Failed to connect",
    )


@router.post("/disconnect", response_model=SuccessResponse)
async def disconnect_electromagnet(driver: ElectromagnetDriver = Depends(get_electromagnet)):
    """
    断开电磁铁驱动器。

    Returns:
        SuccessResponse: 断开结果
    """
    result = await driver.disconnect()
    return SuccessResponse(
        success=result,
        message="Disconnected",
    )


@router.post("/emergency_stop", response_model=SuccessResponse)
async def emergency_stop(driver: ElectromagnetDriver = Depends(get_electromagnet)):
    """
    紧急停止。

    立即将电流归零并停止所有操作。

    Returns:
        SuccessResponse: 急停结果
    """
    result = await driver.emergency_stop()
    return SuccessResponse(
        success=result,
        message="Emergency stop triggered",
    )


@router.post("/reset_emergency", response_model=SuccessResponse)
async def reset_emergency(driver: ElectromagnetDriver = Depends(get_electromagnet)):
    """
    复位紧急停止状态。

    Returns:
        SuccessResponse: 复位结果
    """
    result = await driver.reset_emergency()
    return SuccessResponse(
        success=result,
        message="Emergency stop reset",
    )


@router.post("/reset_overcurrent", response_model=SuccessResponse)
async def reset_overcurrent_protection(
    driver: ElectromagnetDriver = Depends(get_electromagnet),
):
    """
    复位过流保护状态。

    Returns:
        SuccessResponse: 复位结果
    """
    result = await driver.reset_overcurrent_protection()
    return SuccessResponse(
        success=result,
        message="Overcurrent protection reset",
    )


@router.post("/field", response_model=SuccessResponse)
async def set_field(
    request: ElectromagnetSetCurrentRequest,
    driver: ElectromagnetDriver = Depends(get_electromagnet),
):
    """
    设置目标磁场值（自动转换为电流）。

    Args:
        request: 磁场设置请求（使用 current 字段传递磁场值）
        driver: 驱动器实例

    Returns:
        SuccessResponse: 设置结果

    Raises:
        HTTPException: 设备未连接或参数无效

    Note:
        此端点使用 current 字段传递磁场值（T），以便复用现有的请求模型
    """
    # 验证设备状态
    try:
        validate_device_state(driver)
    except DeviceValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    try:
        # 使用 current 字段传递磁场值
        result = await driver.set_field(request.current)
        return SuccessResponse(
            success=result,
            message=f"Field set to {request.current}T" if result else "Failed to set field",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
