"""
审计日志查询 API 路由模块

功能：
- 支持按时间范围查询
- 支持按设备 ID 查询
- 支持按操作类型查询
- 支持分页
- 支持统计信息查询
"""

import json
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core.data_storage import DataStorage
from middleware.audit import audit_logger
from models import AuditLog

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/logs",
    tags=["audit-logs"],
    responses={404: {"description": "Not found"}},
)

storage: DataStorage | None = None


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
    audit_logger.set_storage(instance)


# ==================== 请求/响应模型 ====================


class LogQueryRequest(BaseModel):
    """日志查询请求"""

    start_time: datetime | None = Field(None, description="起始时间")
    end_time: datetime | None = Field(None, description="结束时间")
    device_id: str | None = Field(None, description="设备ID")
    operation_type: str | None = Field(None, description="操作类型")
    operation_category: str | None = Field(None, description="操作分类")
    user_id: int | None = Field(None, description="用户ID")
    response_status: int | None = Field(None, description="响应状态码")
    page: int = Field(1, description="页码", ge=1)
    page_size: int = Field(20, description="每页数量", ge=1, le=100)


class AuditLogResponse(BaseModel):
    """审计日志响应"""

    id: int = Field(..., description="日志ID")
    timestamp: str = Field(..., description="时间戳")
    user_id: int | None = Field(None, description="用户ID")
    device_id: str | None = Field(None, description="设备ID")
    operation_type: str = Field(..., description="操作类型")
    operation_category: str = Field(..., description="操作分类")
    request_method: str = Field(..., description="请求方法")
    request_path: str = Field(..., description="请求路径")
    request_params: dict | None = Field(None, description="请求参数")
    response_status: int | None = Field(None, description="响应状态码")
    response_message: str | None = Field(None, description="响应消息")
    ip_address: str | None = Field(None, description="IP地址")
    user_agent: str | None = Field(None, description="用户代理")
    duration_ms: int | None = Field(None, description="处理时间(毫秒)")


class LogListResponse(BaseModel):
    """日志列表响应"""

    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="每页数量")
    total_pages: int = Field(..., description="总页数")
    logs: list[AuditLogResponse] = Field(..., description="日志列表")


class LogStatisticsResponse(BaseModel):
    """日志统计响应"""

    total_count: int = Field(..., description="总记录数")
    by_category: dict[str, int] = Field(..., description="按分类统计")
    by_operation_type: dict[str, int] = Field(..., description="按操作类型统计")
    by_device: dict[str, int] = Field(..., description="按设备统计")
    by_status: dict[str, int] = Field(..., description="按响应状态统计")


class OperationTypeInfo(BaseModel):
    """操作类型信息"""

    type: str = Field(..., description="操作类型")
    category: str = Field(..., description="操作分类")
    description: str = Field(..., description="操作描述")


# ==================== API 端点 ====================


@router.get("/query", response_model=LogListResponse)
async def query_logs(
    start_time: datetime | None = Query(None, description="起始时间 (ISO格式)"),
    end_time: datetime | None = Query(None, description="结束时间 (ISO格式)"),
    device_id: str | None = Query(None, description="设备ID"),
    operation_type: str | None = Query(None, description="操作类型"),
    operation_category: str | None = Query(None, description="操作分类"),
    user_id: int | None = Query(None, description="用户ID"),
    response_status: int | None = Query(None, description="响应状态码"),
    page: int = Query(1, description="页码", ge=1),
    page_size: int = Query(20, description="每页数量", ge=1, le=100),
):
    """
    查询审计日志

    支持多条件组合查询，返回分页结果。

    Args:
        start_time: 起始时间
        end_time: 结束时间
        device_id: 设备ID
        operation_type: 操作类型
        operation_category: 操作分类
        user_id: 用户ID
        response_status: 响应状态码
        page: 页码
        page_size: 每页数量

    Returns:
        LogListResponse: 分页日志列表
    """
    db = get_storage()
    session = db.Session()

    try:
        # 刷新缓冲区
        audit_logger.flush()

        # 构建查询
        query = session.query(AuditLog)

        # 应用过滤条件
        if start_time:
            query = query.filter(AuditLog.timestamp >= start_time)
        if end_time:
            query = query.filter(AuditLog.timestamp <= end_time)
        if device_id:
            query = query.filter(AuditLog.device_id == device_id)
        if operation_type:
            query = query.filter(AuditLog.operation_type == operation_type)
        if operation_category:
            query = query.filter(AuditLog.operation_category == operation_category)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if response_status:
            query = query.filter(AuditLog.response_status == response_status)

        # 获取总数
        total = query.count()

        # 计算总页数
        total_pages = (total + page_size - 1) // page_size

        # 分页查询
        logs = (
            query.order_by(AuditLog.timestamp.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        # 转换为响应格式
        log_responses = []
        for log in logs:
            params = None
            if log.request_params:
                try:
                    params = json.loads(log.request_params)
                except json.JSONDecodeError:
                    params = {"raw": log.request_params}

            log_responses.append(
                AuditLogResponse(
                    id=log.id,
                    timestamp=log.timestamp.isoformat() if log.timestamp else "",
                    user_id=log.user_id,
                    device_id=log.device_id,
                    operation_type=log.operation_type,
                    operation_category=log.operation_category,
                    request_method=log.request_method,
                    request_path=log.request_path,
                    request_params=params,
                    response_status=log.response_status,
                    response_message=log.response_message,
                    ip_address=log.ip_address,
                    user_agent=log.user_agent,
                    duration_ms=log.duration_ms,
                )
            )

        return LogListResponse(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            logs=log_responses,
        )

    finally:
        session.close()


@router.get("/statistics", response_model=LogStatisticsResponse)
async def get_log_statistics(
    start_time: datetime | None = Query(None, description="起始时间"),
    end_time: datetime | None = Query(None, description="结束时间"),
    device_id: str | None = Query(None, description="设备ID"),
):
    """
    获取日志统计信息

    返回按分类、操作类型、设备、响应状态的统计数据。

    Args:
        start_time: 起始时间
        end_time: 结束时间
        device_id: 设备ID

    Returns:
        LogStatisticsResponse: 统计信息
    """
    from sqlalchemy import func

    db = get_storage()
    session = db.Session()

    try:
        # 刷新缓冲区
        audit_logger.flush()

        # 构建基础查询
        base_query = session.query(AuditLog)

        if start_time:
            base_query = base_query.filter(AuditLog.timestamp >= start_time)
        if end_time:
            base_query = base_query.filter(AuditLog.timestamp <= end_time)
        if device_id:
            base_query = base_query.filter(AuditLog.device_id == device_id)

        # 总数
        total_count = base_query.count()

        # 按分类统计
        by_category = {}
        category_results = (
            session.query(
                AuditLog.operation_category,
                func.count(AuditLog.id).label("count"),
            )
            .filter(*[getattr(AuditLog, col) == val for col, val in locals().items()
                     if col in ["start_time", "end_time", "device_id"] and val is not None]
                    if any([start_time, end_time, device_id]) else [True])
            .group_by(AuditLog.operation_category)
            .all()
        )

        # 重新构建正确的查询
        category_query = session.query(
            AuditLog.operation_category,
            func.count(AuditLog.id).label("count"),
        )
        if start_time:
            category_query = category_query.filter(AuditLog.timestamp >= start_time)
        if end_time:
            category_query = category_query.filter(AuditLog.timestamp <= end_time)
        if device_id:
            category_query = category_query.filter(AuditLog.device_id == device_id)
        by_category = {r[0]: r[1] for r in category_query.group_by(AuditLog.operation_category).all()}

        # 按操作类型统计
        type_query = session.query(
            AuditLog.operation_type,
            func.count(AuditLog.id).label("count"),
        )
        if start_time:
            type_query = type_query.filter(AuditLog.timestamp >= start_time)
        if end_time:
            type_query = type_query.filter(AuditLog.timestamp <= end_time)
        if device_id:
            type_query = type_query.filter(AuditLog.device_id == device_id)
        by_operation_type = {r[0]: r[1] for r in type_query.group_by(AuditLog.operation_type).all()}

        # 按设备统计
        device_query = session.query(
            AuditLog.device_id,
            func.count(AuditLog.id).label("count"),
        )
        if start_time:
            device_query = device_query.filter(AuditLog.timestamp >= start_time)
        if end_time:
            device_query = device_query.filter(AuditLog.timestamp <= end_time)
        by_device = {r[0] or "unknown": r[1] for r in device_query.group_by(AuditLog.device_id).all()}

        # 按响应状态统计
        status_query = session.query(
            AuditLog.response_status,
            func.count(AuditLog.id).label("count"),
        )
        if start_time:
            status_query = status_query.filter(AuditLog.timestamp >= start_time)
        if end_time:
            status_query = status_query.filter(AuditLog.timestamp <= end_time)
        if device_id:
            status_query = status_query.filter(AuditLog.device_id == device_id)
        by_status = {str(r[0] or "N/A"): r[1] for r in status_query.group_by(AuditLog.response_status).all()}

        return LogStatisticsResponse(
            total_count=total_count,
            by_category=by_category,
            by_operation_type=by_operation_type,
            by_device=by_device,
            by_status=by_status,
        )

    finally:
        session.close()


@router.get("/operation-types", response_model=list[OperationTypeInfo])
async def get_operation_types():
    """
    获取所有操作类型列表

    Returns:
        List[OperationTypeInfo]: 操作类型列表
    """
    operation_types = [
        OperationTypeInfo(type="device_connect", category="device", description="设备连接"),
        OperationTypeInfo(type="device_disconnect", category="device", description="设备断开"),
        OperationTypeInfo(type="motor_move", category="motion_control", description="电机移动"),
        OperationTypeInfo(type="motor_jog", category="motion_control", description="电机点动"),
        OperationTypeInfo(type="motor_stop", category="motion_control", description="电机停止"),
        OperationTypeInfo(type="motor_home", category="motion_control", description="电机回零"),
        OperationTypeInfo(type="emergency_stop", category="safety", description="紧急停止"),
        OperationTypeInfo(type="emergency_reset", category="safety", description="紧急停止复位"),
        OperationTypeInfo(type="limit_config", category="parameter", description="限位配置"),
        OperationTypeInfo(type="pr_path_config", category="parameter", description="PR路径配置"),
        OperationTypeInfo(type="electromagnet_set_current", category="parameter", description="电磁铁电流设置"),
        OperationTypeInfo(type="electromagnet_scan", category="experiment", description="电磁铁扫描"),
        OperationTypeInfo(type="electromagnet_calibrate", category="calibration", description="电磁铁校准"),
        OperationTypeInfo(type="temperature_setpoint", category="parameter", description="温度设定"),
        OperationTypeInfo(type="pid_config", category="parameter", description="PID参数配置"),
        OperationTypeInfo(type="temperature_program", category="experiment", description="温度程序"),
        OperationTypeInfo(type="piezo_set_voltage", category="parameter", description="压电电压设置"),
        OperationTypeInfo(type="piezo_set_displacement", category="parameter", description="压电位移设置"),
        OperationTypeInfo(type="piezo_calibrate", category="calibration", description="压电校准"),
        OperationTypeInfo(type="ammeter_start", category="experiment", description="微电流采集启动"),
        OperationTypeInfo(type="ammeter_stop", category="experiment", description="微电流采集停止"),
        OperationTypeInfo(type="experiment_start", category="experiment", description="实验开始"),
        OperationTypeInfo(type="experiment_stop", category="experiment", description="实验停止"),
        OperationTypeInfo(type="device_query", category="query", description="设备查询"),
        OperationTypeInfo(type="motor_operation", category="motor", description="电机操作"),
        OperationTypeInfo(type="data_analysis", category="analysis", description="数据分析"),
        OperationTypeInfo(type="api_request", category="general", description="API请求"),
    ]
    return operation_types


@router.get("/categories", response_model=list[str])
async def get_categories():
    """
    获取所有操作分类列表

    Returns:
        List[str]: 分类列表
    """
    return [
        "device",
        "motion_control",
        "safety",
        "parameter",
        "calibration",
        "experiment",
        "query",
        "motor",
        "analysis",
        "general",
    ]


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_log_detail(log_id: int):
    """
    获取日志详情

    Args:
        log_id: 日志ID

    Returns:
        AuditLogResponse: 日志详情
    """
    db = get_storage()
    session = db.Session()

    try:
        log = session.query(AuditLog).get(log_id)
        if not log:
            raise HTTPException(status_code=404, detail="Log not found")

        params = None
        if log.request_params:
            try:
                params = json.loads(log.request_params)
            except json.JSONDecodeError:
                params = {"raw": log.request_params}

        return AuditLogResponse(
            id=log.id,
            timestamp=log.timestamp.isoformat() if log.timestamp else "",
            user_id=log.user_id,
            device_id=log.device_id,
            operation_type=log.operation_type,
            operation_category=log.operation_category,
            request_method=log.request_method,
            request_path=log.request_path,
            request_params=params,
            response_status=log.response_status,
            response_message=log.response_message,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            duration_ms=log.duration_ms,
        )

    finally:
        session.close()


@router.delete("/{log_id}")
async def delete_log(log_id: int):
    """
    删除单条日志

    Args:
        log_id: 日志ID

    Returns:
        dict: 删除结果
    """
    db = get_storage()
    session = db.Session()

    try:
        log = session.query(AuditLog).get(log_id)
        if not log:
            raise HTTPException(status_code=404, detail="Log not found")

        session.delete(log)
        session.commit()

        return {"success": True, "message": f"Log {log_id} deleted"}

    finally:
        session.close()


@router.post("/bulk/delete")
async def delete_logs_bulk(
    start_time: datetime | None = Query(None, description="起始时间"),
    end_time: datetime | None = Query(None, description="结束时间"),
    device_id: str | None = Query(None, description="设备ID"),
    operation_type: str | None = Query(None, description="操作类型"),
):
    """
    批量删除日志

    使用POST方法而非DELETE，因为DELETE方法不应包含请求体。
    符合RESTful最佳实践。

    Args:
        start_time: 起始时间
        end_time: 结束时间
        device_id: 设备ID
        operation_type: 操作类型

    Returns:
        dict: 删除结果
    """
    db = get_storage()
    session = db.Session()

    try:
        query = session.query(AuditLog)

        if start_time:
            query = query.filter(AuditLog.timestamp >= start_time)
        if end_time:
            query = query.filter(AuditLog.timestamp <= end_time)
        if device_id:
            query = query.filter(AuditLog.device_id == device_id)
        if operation_type:
            query = query.filter(AuditLog.operation_type == operation_type)

        count = query.count()
        query.delete()
        session.commit()

        return {"success": True, "message": f"Deleted {count} logs"}

    finally:
        session.close()


@router.post("/export")
async def export_logs(
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    device_id: str | None = None,
    operation_type: str | None = None,
    format: str = Query("json", description="导出格式: json 或 csv"),
):
    """
    导出日志

    Args:
        start_time: 起始时间
        end_time: 结束时间
        device_id: 设备ID
        operation_type: 操作类型
        format: 导出格式

    Returns:
        dict: 导出结果
    """
    import csv
    import os

    db = get_storage()
    session = db.Session()

    try:
        query = session.query(AuditLog)

        if start_time:
            query = query.filter(AuditLog.timestamp >= start_time)
        if end_time:
            query = query.filter(AuditLog.timestamp <= end_time)
        if device_id:
            query = query.filter(AuditLog.device_id == device_id)
        if operation_type:
            query = query.filter(AuditLog.operation_type == operation_type)

        logs = query.order_by(AuditLog.timestamp.desc()).limit(10000).all()

        if not logs:
            return {"success": False, "message": "No logs to export"}

        export_dir = "exports"
        os.makedirs(export_dir, exist_ok=True)

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format == "csv":
            filepath = f"{export_dir}/audit_logs_{timestamp_str}.csv"
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "id", "timestamp", "user_id", "device_id",
                    "operation_type", "operation_category",
                    "request_method", "request_path", "request_params",
                    "response_status", "response_message",
                    "ip_address", "duration_ms",
                ])

                for log in logs:
                    writer.writerow([
                        log.id,
                        log.timestamp.isoformat() if log.timestamp else "",
                        log.user_id or "",
                        log.device_id or "",
                        log.operation_type,
                        log.operation_category,
                        log.request_method,
                        log.request_path,
                        log.request_params or "",
                        log.response_status or "",
                        log.response_message or "",
                        log.ip_address or "",
                        log.duration_ms or "",
                    ])
        else:
            filepath = f"{export_dir}/audit_logs_{timestamp_str}.json"
            logs_data = []
            for log in logs:
                logs_data.append({
                    "id": log.id,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                    "user_id": log.user_id,
                    "device_id": log.device_id,
                    "operation_type": log.operation_type,
                    "operation_category": log.operation_category,
                    "request_method": log.request_method,
                    "request_path": log.request_path,
                    "request_params": log.request_params,
                    "response_status": log.response_status,
                    "response_message": log.response_message,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "duration_ms": log.duration_ms,
                })

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(logs_data, f, ensure_ascii=False, indent=2)

        return {
            "success": True,
            "filepath": filepath,
            "count": len(logs),
            "message": f"Exported {len(logs)} logs to {filepath}",
        }

    finally:
        session.close()
