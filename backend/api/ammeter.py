"""
微电流采集 API 路由模块

文件名: ammeter.py
路径: backend/api/
功能: 微电流采集设备控制API，提供采集控制、数据获取、通道配置等接口
作者: CAUC-SEP Team
创建日期: 2024-01-01
依赖: FastAPI, core.picoammeter, core.device_registry, api.schemas

主要功能：
- 采集启动/停止控制（支持采样率配置）
- 实时数据获取（单通道/多通道、缓冲区读取）
- 设备状态查询（采集状态、通道状态）
- 通道配置管理（电流量程、滤波参数、偏移校准）
- 信噪比计算（SNR分析）

API端点：
- POST /start: 启动微电流采集
- POST /stop: 停止微电流采集
- GET /data: 获取实时采集数据
- GET /status: 获取设备状态信息
- POST /channel/config: 配置指定通道参数
- POST /clear_buffer: 清空数据缓冲区
- GET /snr/{channel}: 获取指定通道信噪比

安全特性：
- 设备状态验证（启动前检查设备就绪状态）
- 参数范围校验（通道号、采样率等）
- 异常处理与错误响应
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.schemas import (
    AmmeterChannelConfigRequest,
    AmmeterDataResponse,
    AmmeterStartRequest,
    AmmeterStatusResponse,
    SuccessResponse,
)
from core.device_management.device_registry import DeviceRegistry
from core.device_management.device_utils import DeviceValidationError, validate_device_state
from core.picoammeter import ChannelData, CurrentRange, FilterType, Picoammeter

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/ammeter",
    tags=["ammeter"],
    responses={404: {"description": "Not found"}},
)

# 设备注册表中的设备ID
PICOAMMETER_DEVICE_ID = "picoammeter"


def get_picoammeter() -> Picoammeter:
    """
    获取微电流采集设备实例。

    从设备注册表中获取设备实例。

    Raises:
        HTTPException: 当设备未初始化时抛出 503 错误

    Returns:
        Picoammeter: 微电流采集设备实例
    """
    try:
        return DeviceRegistry.get_device(PICOAMMETER_DEVICE_ID)
    except KeyError:
        raise HTTPException(status_code=503, detail="Picoammeter not initialized")


def set_picoammeter(instance: Picoammeter) -> None:
    """
    设置微电流采集设备实例。

    将设备实例注册到设备注册表。

    Args:
        instance: 微电流采集设备实例
    """
    if DeviceRegistry.has_device(PICOAMMETER_DEVICE_ID):
        DeviceRegistry.unregister(PICOAMMETER_DEVICE_ID)
    DeviceRegistry.register(PICOAMMETER_DEVICE_ID, instance)


@router.post("/start", response_model=SuccessResponse)
async def start_acquisition(
    request: AmmeterStartRequest | None = None,
    device: Picoammeter = Depends(get_picoammeter),
):
    """
    启动微电流采集。

    Args:
        request: 采集启动请求（可选），包含采样率等配置
        device: 微电流采集设备实例

    Returns:
        SuccessResponse: 启动结果

    Raises:
        HTTPException: 设备未就绪或启动失败时抛出
    """
    try:
        validate_device_state(device)
    except DeviceValidationError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Device not ready, current status: {e.status}" if e.status else e.message,
        )

    # 如果请求中包含采样率配置，先设置采样率
    if request and request.sample_rate:
        try:
            device.set_sample_rate(request.sample_rate)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    result = await device.start_acquisition()

    if not result:
        raise HTTPException(status_code=500, detail="Failed to start acquisition")

    logger.info(f"Acquisition started with sample rate {device._acq_config.sample_rate}Hz")

    return SuccessResponse(
        success=True,
        message=f"Acquisition started at {device._acq_config.sample_rate}Hz",
    )


@router.post("/stop", response_model=SuccessResponse)
async def stop_acquisition(device: Picoammeter = Depends(get_picoammeter)):
    """
    停止微电流采集。

    Args:
        device: 微电流采集设备实例

    Returns:
        SuccessResponse: 停止结果
    """
    result = await device.stop_acquisition()

    logger.info("Acquisition stopped")

    return SuccessResponse(
        success=result,
        message="Acquisition stopped" if result else "Failed to stop acquisition",
    )


@router.get("/data", response_model=AmmeterDataResponse)
async def get_realtime_data(
    channel: int | None = None,
    count: int | None = None,
    device: Picoammeter = Depends(get_picoammeter),
):
    """
    获取实时采集数据。

    Args:
        channel: 通道号（0-3），None表示获取所有通道
        count: 获取数据点数量，None表示仅获取最新数据
        device: 微电流采集设备实例

    Returns:
        AmmeterDataResponse: 包含通道数据的响应

    Raises:
        HTTPException: 通道号无效时抛出
    """
    if channel is not None:
        if not 0 <= channel < device.NUM_CHANNELS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid channel: {channel}, must be 0-{device.NUM_CHANNELS - 1}",
            )

        # 获取指定通道数据
        if count is None:
            # 仅获取最新数据
            data = await device.read_channel(channel)
            channel_data = [_channel_data_to_dict(data, channel)] if data else []
        else:
            # 获取缓冲区数据
            buffer_data = await device.read_channel_buffer(channel, count)
            channel_data = [_channel_data_to_dict(d, channel) for d in buffer_data]
    else:
        # 获取所有通道最新数据
        all_data = await device.read_all_channels()
        channel_data = [
            _channel_data_to_dict(d, ch) for ch, d in enumerate(all_data) if d is not None
        ]

    return AmmeterDataResponse(
        success=True,
        message=f"Retrieved {len(channel_data)} data points",
        is_acquiring=device._is_acquiring,
        data=channel_data,
    )


@router.get("/status", response_model=AmmeterStatusResponse)
async def get_device_status(device: Picoammeter = Depends(get_picoammeter)):
    """
    获取设备状态信息。

    Args:
        device: 微电流采集设备实例

    Returns:
        AmmeterStatusResponse: 设备状态响应
    """
    status = await device.read_status()
    return AmmeterStatusResponse(**status)


@router.post("/channel/config", response_model=SuccessResponse)
async def configure_channel(
    request: AmmeterChannelConfigRequest,
    device: Picoammeter = Depends(get_picoammeter),
):
    """
    配置指定通道参数。

    Args:
        request: 通道配置请求
        device: 微电流采集设备实例

    Returns:
        SuccessResponse: 配置结果

    Raises:
        HTTPException: 配置参数无效时抛出
    """
    try:
        # 转换电流量程枚举
        current_range = None
        if request.current_range:
            current_range = CurrentRange(request.current_range)

        # 转换滤波类型枚举
        filter_type = None
        if request.filter_type:
            filter_type = FilterType(request.filter_type)

        result = device.configure_channel(
            channel=request.channel,
            enabled=request.enabled,
            current_range=current_range,
            filter_type=filter_type,
            filter_cutoff=request.filter_cutoff,
            filter_window=request.filter_window,
            offset=request.offset,
        )

        if not result:
            raise HTTPException(status_code=500, detail="Failed to configure channel")

        logger.info(f"Channel {request.channel} configured successfully")

        return SuccessResponse(
            success=True,
            message=f"Channel {request.channel} configured",
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/clear_buffer", response_model=SuccessResponse)
async def clear_buffer(
    channel: int | None = None,
    device: Picoammeter = Depends(get_picoammeter),
):
    """
    清空数据缓冲区。

    Args:
        channel: 通道号（0-3），None表示清空所有通道
        device: 微电流采集设备实例

    Returns:
        SuccessResponse: 清空结果

    Raises:
        HTTPException: 通道号无效时抛出
    """
    try:
        device.clear_buffer(channel)
        message = (
            f"Channel {channel} buffer cleared"
            if channel is not None
            else "All channel buffers cleared"
        )
        return SuccessResponse(success=True, message=message)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/snr/{channel}")
async def get_snr(
    channel: int,
    window_size: int | None = None,
    device: Picoammeter = Depends(get_picoammeter),
):
    """
    获取指定通道的信噪比。

    Args:
        channel: 通道号（0-3）
        window_size: 计算窗口大小
        device: 微电流采集设备实例

    Returns:
        dict: 包含信噪比信息

    Raises:
        HTTPException: 通道号无效时抛出
    """
    if not 0 <= channel < device.NUM_CHANNELS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid channel: {channel}, must be 0-{device.NUM_CHANNELS - 1}",
        )

    try:
        snr = device.calculate_snr(channel, window_size)
        return {
            "success": True,
            "channel": channel,
            "snr_db": snr,
            "window_size": window_size or device._acq_config.snr_calc_window,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _channel_data_to_dict(data: ChannelData | None, channel: int) -> dict[str, Any]:
    """
    将 ChannelData 对象转换为字典。

    Args:
        data: 通道数据对象
        channel: 通道号

    Returns:
        dict: 数据字典
    """
    if not data:
        return {}

    return {
        "channel": channel,
        "current_pa": data.current_pa,
        "timestamp": data.timestamp,
        "snr_db": data.snr_db,
        "raw_current_pa": data.raw_current_pa,
        "noise_rms_pa": data.noise_rms_pa,
        "signal_rms_pa": data.signal_rms_pa,
    }
