"""
设备管理数据模型

文件名: device.py
路径: backend/schemas/
功能: 定义设备管理相关的请求/响应模型，包含设备信息查询和管理
作者: Backend Engineer Agent
创建日期: 2026-03-14
依赖: pydantic

设备类型：
- motor: 电机控制器
- electromagnet: 电磁铁电源
- piezo: 压电陶瓷控制器
- ammeter: 微电流采集器
- temperature: 温度控制器
"""

from pydantic import BaseModel, Field


class DeviceInfo(BaseModel):
    """
    设备信息模型。

    描述系统中已注册设备的基本信息。

    Attributes:
        device_id: 设备唯一标识符，UUID格式
        device_type: 设备类型，如 'motor', 'electromagnet', 'piezo', 'ammeter', 'temperature'
        device_name: 设备名称，用户自定义，可选
        connection_params: 连接参数JSON字符串，包含串口、波特率等信息，可选
        status: 设备状态，如 'connected', 'disconnected', 'error', 'busy'
        created_at: 设备注册时间(ISO格式)

    Example:
        >>> device = DeviceInfo(
        ...     device_id="550e8400-e29b-41d4-a716-446655440000",
        ...     device_type="electromagnet",
        ...     device_name="主电磁铁",
        ...     status="connected",
        ...     created_at="2026-03-14T10:30:00Z"
        ... )
    """

    device_id: str
    device_type: str
    device_name: str | None
    connection_params: str | None
    status: str
    created_at: str
