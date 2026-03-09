"""
设备管理 API 路由模块

功能：
- 设备列表
- 设备状态查询
- 设备连接管理
- IO端口配置（DI/DO）

安全加固：
- SubTask 13.1: 输入验证增强（device_id格式验证）
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.abstract import DeviceStatus
from core.data_storage import DataStorage
from core.dm2c_driver import DI_FUNCTIONS, DO_FUNCTIONS, LeadshineDM2C
from core.electromagnet_driver import ElectromagnetDriver
from core.picoammeter import Picoammeter
from core.piezo_controller import PiezoController
from core.temperature_controller import TemperatureController
from middleware.security import validate_device_id

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/device",
    tags=["device"],
    responses={404: {"description": "Not found"}},
)

# 全局设备实例引用
storage: DataStorage | None = None
dm2c: LeadshineDM2C | None = None
electromagnet_driver: ElectromagnetDriver | None = None
temp_controller: TemperatureController | None = None
piezo_controller: PiezoController | None = None
picoammeter: Picoammeter | None = None


def get_storage() -> DataStorage:
    """
    获取数据存储实例

    Raises:
        HTTPException: 当存储未初始化时抛出 503 错误

    Returns:
        DataStorage: 数据存储实例
    """
    if not storage:
        raise HTTPException(status_code=503, detail="Storage not initialized")
    return storage


def set_storage(instance: DataStorage) -> None:
    """
    设置数据存储实例

    Args:
        instance: 数据存储实例
    """
    global storage
    storage = instance


def set_devices(
    motor: LeadshineDM2C | None,
    electromagnet: ElectromagnetDriver | None,
    temperature: TemperatureController | None,
    piezo: PiezoController | None,
    ammeter: Picoammeter | None,
) -> None:
    """
    设置所有设备实例引用

    Args:
        motor: 步进电机驱动器实例
        electromagnet: 电磁铁驱动器实例
        temperature: 温控系统实例
        piezo: 压电陶瓷控制器实例
        ammeter: 微电流计实例
    """
    global dm2c, electromagnet_driver, temp_controller, piezo_controller, picoammeter
    dm2c = motor
    electromagnet_driver = electromagnet
    temp_controller = temperature
    piezo_controller = piezo
    picoammeter = ammeter


def _get_device_info(device_id: str) -> dict[str, Any] | None:
    """
    根据设备ID获取设备信息和状态

    Args:
        device_id: 设备ID

    Returns:
        dict | None: 设备信息字典，未找到返回None
    """
    device_map = {
        "stepper_01": {
            "instance": dm2c,
            "device_type": "stepper_motor",
            "device_name": "雷赛DM2C步进电机",
        },
        "electromagnet_01": {
            "instance": electromagnet_driver,
            "device_type": "electromagnet",
            "device_name": "电磁铁控制器",
        },
        "temp_controller_01": {
            "instance": temp_controller,
            "device_type": "temperature_controller",
            "device_name": "温控系统",
        },
        "piezo_01": {
            "instance": piezo_controller,
            "device_type": "piezo_controller",
            "device_name": "压电陶瓷控制器",
        },
        "picoammeter_01": {
            "instance": picoammeter,
            "device_type": "picoammeter",
            "device_name": "微电流计",
        },
    }
    return device_map.get(device_id)


@router.get("/list")
async def list_devices():
    """
    获取设备列表

    从实际设备驱动获取状态，而非硬编码数据。

    Returns:
        dict: 设备列表
    """
    devices = []

    # 步进电机
    if dm2c:
        devices.append(
            {
                "device_id": dm2c.device_id,
                "device_type": "stepper_motor",
                "device_name": "雷赛DM2C步进电机",
                "status": dm2c.status.value,
                "connected": dm2c.status != DeviceStatus.DISCONNECTED,
            }
        )

    # 电磁铁
    if electromagnet_driver:
        status_data = await electromagnet_driver.read_status()
        devices.append(
            {
                "device_id": electromagnet_driver.device_id,
                "device_type": "electromagnet",
                "device_name": "电磁铁控制器",
                "status": status_data.get("electromagnet_status", "unknown"),
                "connected": status_data.get("connected", False),
            }
        )

    # 温控系统
    if temp_controller:
        status_data = await temp_controller.read_status()
        devices.append(
            {
                "device_id": temp_controller.device_id,
                "device_type": "temperature_controller",
                "device_name": "温控系统",
                "status": status_data.get("status", "unknown"),
                "connected": status_data.get("connected", False),
            }
        )

    # 压电陶瓷控制器
    if piezo_controller:
        status_data = await piezo_controller.read_status()
        devices.append(
            {
                "device_id": piezo_controller.device_id,
                "device_type": "piezo_controller",
                "device_name": "压电陶瓷控制器",
                "status": status_data.get("status", "unknown"),
                "connected": True,
            }
        )

    # 微电流计
    if picoammeter:
        status_data = await picoammeter.read_status()
        devices.append(
            {
                "device_id": picoammeter.device_id,
                "device_type": "picoammeter",
                "device_name": "微电流计",
                "status": status_data.get("status", "unknown"),
                "connected": picoammeter.status != DeviceStatus.DISCONNECTED,
            }
        )

    return {
        "count": len(devices),
        "devices": devices,
    }


@router.get("/{device_id}/status")
async def get_device_status(device_id: str):
    """
    获取指定设备状态

    根据device_id路由到对应设备驱动获取实时状态。

    Args:
        device_id: 设备ID

    Returns:
        dict: 设备状态

    Raises:
        HTTPException: 设备未找到时返回404错误
    """
    # SubTask 13.1: 输入验证 - 验证device_id格式
    if not validate_device_id(device_id):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid device_id format: '{device_id}'. Must contain only letters, numbers, underscores, and hyphens.",
        )

    device_info = _get_device_info(device_id)

    if not device_info:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")

    instance = device_info["instance"]
    if not instance:
        raise HTTPException(status_code=503, detail=f"Device '{device_id}' not initialized")

    # 从设备驱动获取实时状态
    status_data = await instance.read_status()

    return {
        "device_id": device_id,
        "device_type": device_info["device_type"],
        "device_name": device_info["device_name"],
        "status": status_data.get("status", instance.status.value),
        "connected": instance.status != DeviceStatus.DISCONNECTED,
        "details": status_data,
    }


# ==================== IO配置请求模型 ====================


class DIConfigRequest(BaseModel):
    """DI端口配置请求模型"""

    di_number: int = Field(..., ge=1, le=7, description="DI端口号(1-7)")
    function: int = Field(..., ge=0, le=0xAC, description="功能代码")


class DOConfigRequest(BaseModel):
    """DO端口配置请求模型"""

    do_number: int = Field(..., ge=1, le=3, description="DO端口号(1-3)")
    function: int = Field(..., ge=0, le=0xA5, description="功能代码")


# ==================== IO配置API端点 ====================


@router.get("/{device_id}/io/di/functions")
async def get_di_functions(device_id: str):
    """
    获取DI功能代码列表

    Args:
        device_id: 设备ID

    Returns:
        dict: DI功能代码映射表
    """
    if not validate_device_id(device_id):
        raise HTTPException(status_code=400, detail=f"Invalid device_id format: '{device_id}'")

    return {
        "device_id": device_id,
        "functions": {f"0x{k:02X}": v for k, v in DI_FUNCTIONS.items()},
        "description": "常开模式: 功能代码 | 常闭模式: 功能代码 + 0x80",
    }


@router.get("/{device_id}/io/do/functions")
async def get_do_functions(device_id: str):
    """
    获取DO功能代码列表

    Args:
        device_id: 设备ID

    Returns:
        dict: DO功能代码映射表
    """
    if not validate_device_id(device_id):
        raise HTTPException(status_code=400, detail=f"Invalid device_id format: '{device_id}'")

    return {
        "device_id": device_id,
        "functions": {f"0x{k:02X}": v for k, v in DO_FUNCTIONS.items()},
        "description": "常开模式: 功能代码 | 常闭模式: 功能代码 + 0x80",
    }


@router.post("/{device_id}/io/di/configure")
async def configure_di(device_id: str, request: DIConfigRequest):
    """
    配置DI端口功能

    Args:
        device_id: 设备ID
        request: DI配置请求

    Returns:
        dict: 配置结果
    """
    if not validate_device_id(device_id):
        raise HTTPException(status_code=400, detail=f"Invalid device_id format: '{device_id}'")

    if not dm2c:
        raise HTTPException(status_code=503, detail="DM2C driver not initialized")

    if dm2c.device_id != device_id and device_id != "stepper_01":
        raise HTTPException(
            status_code=404, detail=f"Device '{device_id}' not found or not a stepper motor"
        )

    success = await dm2c.configure_di(request.di_number, request.function)

    if success:
        base_function = request.function & 0x7F
        polarity = "常闭" if request.function & 0x80 else "常开"
        func_name = DI_FUNCTIONS.get(base_function, "Unknown")
        return {
            "success": True,
            "device_id": device_id,
            "di_number": request.di_number,
            "function": request.function,
            "function_name": func_name,
            "polarity": polarity,
            "message": f"DI{request.di_number} configured as {func_name} ({polarity})",
        }
    else:
        raise HTTPException(status_code=500, detail=f"Failed to configure DI{request.di_number}")


@router.post("/{device_id}/io/do/configure")
async def configure_do(device_id: str, request: DOConfigRequest):
    """
    配置DO端口功能

    Args:
        device_id: 设备ID
        request: DO配置请求

    Returns:
        dict: 配置结果
    """
    if not validate_device_id(device_id):
        raise HTTPException(status_code=400, detail=f"Invalid device_id format: '{device_id}'")

    if not dm2c:
        raise HTTPException(status_code=503, detail="DM2C driver not initialized")

    if dm2c.device_id != device_id and device_id != "stepper_01":
        raise HTTPException(
            status_code=404, detail=f"Device '{device_id}' not found or not a stepper motor"
        )

    success = await dm2c.configure_do(request.do_number, request.function)

    if success:
        base_function = request.function & 0x7F
        polarity = "常闭" if request.function & 0x80 else "常开"
        func_name = DO_FUNCTIONS.get(base_function, "Unknown")
        return {
            "success": True,
            "device_id": device_id,
            "do_number": request.do_number,
            "function": request.function,
            "function_name": func_name,
            "polarity": polarity,
            "message": f"DO{request.do_number} configured as {func_name} ({polarity})",
        }
    else:
        raise HTTPException(status_code=500, detail=f"Failed to configure DO{request.do_number}")


@router.get("/{device_id}/io/di/status")
async def read_di_status(device_id: str):
    """
    读取所有DI端口状态

    Args:
        device_id: 设备ID

    Returns:
        dict: DI端口状态
    """
    if not validate_device_id(device_id):
        raise HTTPException(status_code=400, detail=f"Invalid device_id format: '{device_id}'")

    if not dm2c:
        raise HTTPException(status_code=503, detail="DM2C driver not initialized")

    if dm2c.device_id != device_id and device_id != "stepper_01":
        raise HTTPException(
            status_code=404, detail=f"Device '{device_id}' not found or not a stepper motor"
        )

    status = await dm2c.read_di_status()
    return {"success": True, "device_id": device_id, **status}


@router.get("/{device_id}/io/do/status")
async def read_do_status(device_id: str):
    """
    读取所有DO端口状态

    Args:
        device_id: 设备ID

    Returns:
        dict: DO端口状态
    """
    if not validate_device_id(device_id):
        raise HTTPException(status_code=400, detail=f"Invalid device_id format: '{device_id}'")

    if not dm2c:
        raise HTTPException(status_code=503, detail="DM2C driver not initialized")

    if dm2c.device_id != device_id and device_id != "stepper_01":
        raise HTTPException(
            status_code=404, detail=f"Device '{device_id}' not found or not a stepper motor"
        )

    status = await dm2c.read_do_status()
    return {"success": True, "device_id": device_id, **status}


@router.get("/{device_id}/io/di/{di_number}/config")
async def read_di_config(device_id: str, di_number: int):
    """
    读取指定DI端口配置

    Args:
        device_id: 设备ID
        di_number: DI端口号(1-7)

    Returns:
        dict: DI端口配置
    """
    if not validate_device_id(device_id):
        raise HTTPException(status_code=400, detail=f"Invalid device_id format: '{device_id}'")

    if not dm2c:
        raise HTTPException(status_code=503, detail="DM2C driver not initialized")

    if di_number < 1 or di_number > 7:
        raise HTTPException(status_code=400, detail=f"Invalid DI number: {di_number}, must be 1-7")

    function = await dm2c.read_di_config(di_number)

    if function >= 0:
        base_function = function & 0x7F
        polarity = "常闭" if function & 0x80 else "常开"
        func_name = DI_FUNCTIONS.get(base_function, "Unknown")
        return {
            "success": True,
            "device_id": device_id,
            "di_number": di_number,
            "function": function,
            "function_name": func_name,
            "polarity": polarity,
        }
    else:
        raise HTTPException(status_code=500, detail=f"Failed to read DI{di_number} config")


@router.get("/{device_id}/io/do/{do_number}/config")
async def read_do_config(device_id: str, do_number: int):
    """
    读取指定DO端口配置

    Args:
        device_id: 设备ID
        do_number: DO端口号(1-3)

    Returns:
        dict: DO端口配置
    """
    if not validate_device_id(device_id):
        raise HTTPException(status_code=400, detail=f"Invalid device_id format: '{device_id}'")

    if not dm2c:
        raise HTTPException(status_code=503, detail="DM2C driver not initialized")

    if do_number < 1 or do_number > 3:
        raise HTTPException(status_code=400, detail=f"Invalid DO number: {do_number}, must be 1-3")

    function = await dm2c.read_do_config(do_number)

    if function >= 0:
        base_function = function & 0x7F
        polarity = "常闭" if function & 0x80 else "常开"
        func_name = DO_FUNCTIONS.get(base_function, "Unknown")
        return {
            "success": True,
            "device_id": device_id,
            "do_number": do_number,
            "function": function,
            "function_name": func_name,
            "polarity": polarity,
        }
    else:
        raise HTTPException(status_code=500, detail=f"Failed to read DO{do_number} config")
