"""
API 路由模块

功能：
- motor: 电机控制 API
- device: 设备管理 API
- experiment: 实验管理 API
- analysis: 数据分析 API
- temperature: 温控系统 API
- piezo: 压电陶瓷控制 API
- ammeter: 微电流采集 API
- electromagnet: 电磁铁控制 API
- schemas: Pydantic 数据模型
"""

from api import (
    ammeter,
    analysis,
    device,
    electromagnet,
    experiment,
    motor,
    piezo,
    schemas,
    temperature,
)

__all__ = [
    "motor",
    "device",
    "experiment",
    "analysis",
    "temperature",
    "piezo",
    "ammeter",
    "electromagnet",
    "schemas",
]
