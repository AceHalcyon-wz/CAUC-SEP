"""
文件名: __init__.py
路径: backend/core/services/__init__.py
功能: 业务逻辑服务模块初始化文件
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: Python 3.11+

模块说明:
    本模块按设备类型封装业务逻辑，提供统一的服务层接口。
    服务层负责：
    - 业务规则校验
    - 跨设备协调
    - 状态管理
    - 异常处理
"""

from .motor_service import MotorControlService
from .electromagnet_service import ElectromagnetControlService
from .base_service import BaseDeviceService

__all__ = [
    "MotorControlService",
    "ElectromagnetControlService",
    "BaseDeviceService",
]
