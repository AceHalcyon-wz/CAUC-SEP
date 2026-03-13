"""
API 路由模块

文件名: __init__.py
路径: backend/api/
功能: API路由模块入口，统一导出所有子模块路由
作者: CAUC-SEP Team
创建日期: 2024-01-01
依赖: FastAPI

子模块说明：
- motor: 电机控制 API（步进电机定位、JOG运动、限位配置）
- device: 设备管理 API（设备列表、状态查询、IO端口配置）
- experiment: 实验管理 API（创建、启动、停止、导出实验）
- analysis: 数据分析 API（信号平滑、曲线拟合、磁滞回线分析）
- temperature: 温控系统 API（温度设定、PID配置、程序控温）
- piezo: 压电陶瓷控制 API（电压/位移控制、校准管理）
- ammeter: 微电流采集 API（采集控制、数据获取、通道配置）
- electromagnet: 电磁铁控制 API（电流设置、扫描模式、校准管理）
- cache_api: 缓存管理 API（Redis缓存、本地缓存操作）
- crash_report: 崩溃报告 API（崩溃日志收集与分析）
- health: 系统健康监控 API（健康检查、告警系统）
- logs: 审计日志 API（日志查询、统计分析）
- performance: 性能分析 API（系统监控、函数分析）
- tracing: 链路追踪 API（追踪查询、可视化分析）
- user: 用户认证 API（JWT认证、用户信息管理）
- schemas: Pydantic 数据模型（从 schemas 模块导入）
"""

from api import (
    ammeter,
    analysis,
    cache_api,
    crash_report,
    device,
    electromagnet,
    experiment,
    health,
    logs,
    motor,
    performance,
    piezo,
    temperature,
    tracing,
    user,
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
    "cache_api",
    "crash_report",
    "health",
    "logs",
    "performance",
    "tracing",
    "user",
]
