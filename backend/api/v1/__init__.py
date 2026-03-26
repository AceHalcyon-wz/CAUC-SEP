"""
文件名: __init__.py
路径: backend/api/v1/
功能: API v1 版本路由入口，统一管理所有 v1 版本 API
版本: v1.0
作者: Backend Engineer Agent
创建日期: 2026-03-15
依赖: fastapi
"""

from fastapi import APIRouter

api_v1 = APIRouter(prefix="/api/v1")

from api.v1 import devices, experiments, analysis, system, auth, exception_protection

api_v1.include_router(devices.router, prefix="/devices", tags=["devices"])
api_v1.include_router(experiments.router, prefix="/experiments", tags=["experiments"])
api_v1.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_v1.include_router(system.router, prefix="/system", tags=["system"])
api_v1.include_router(auth.router, prefix="/auth", tags=["auth"])
api_v1.include_router(
    exception_protection.router, 
    prefix="/exception_protection", 
    tags=["exception_protection"]
)
