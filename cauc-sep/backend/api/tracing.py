"""
链路追踪可视化API路由模块。

功能：
    - 追踪列表查询
    - 追踪详情查询
    - 追踪统计分析
    - 追踪数据清理

作者：Backend Engineer Agent
创建日期：2026-03-07
"""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query

from core.tracing import (
    TraceDetailResponse,
    TraceListResponse,
    TraceStatisticsResponse,
    get_trace_storage,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/tracing",
    tags=["tracing"],
    responses={404: {"description": "Not found"}},
)


@router.get("/traces", response_model=TraceListResponse)
async def list_traces(
    service_name: str | None = Query(None, description="服务名称过滤"),
    start_time: datetime | None = Query(None, description="开始时间过滤"),
    end_time: datetime | None = Query(None, description="结束时间过滤"),
    status: str | None = Query(None, description="状态过滤 (ok/error)"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
):
    """
    查询追踪列表。

    Args:
        service_name: 服务名称过滤（可选）
        start_time: 开始时间过滤（可选）
        end_time: 结束时间过滤（可选）
        status: 状态过滤（可选，可选值：ok/error）
        limit: 返回数量限制，范围1-1000

    Returns:
        TraceListResponse: 追踪列表响应

    Example:
        GET /api/v1/tracing/traces?service_name=cauc-sep&limit=50
    """
    storage = get_trace_storage()
    if not storage:
        raise HTTPException(
            status_code=503,
            detail="Trace storage not initialized",
        )

    traces = storage.query_traces(
        service_name=service_name,
        start_time=start_time,
        end_time=end_time,
        status=status,
        limit=limit,
    )

    return TraceListResponse(
        total=len(traces),
        traces=traces,
    )


@router.get("/traces/{trace_id}", response_model=TraceDetailResponse)
async def get_trace_detail(trace_id: str):
    """
    获取追踪详情。

    Args:
        trace_id: Trace ID（32位十六进制字符串）

    Returns:
        TraceDetailResponse: 追踪详情响应

    Raises:
        HTTPException: 追踪不存在时返回404错误

    Example:
        GET /api/v1/tracing/traces/abc123def456...
    """
    storage = get_trace_storage()
    if not storage:
        raise HTTPException(
            status_code=503,
            detail="Trace storage not initialized",
        )

    # 验证trace_id格式
    if not trace_id or len(trace_id) != 32:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid trace_id format: {trace_id}. Expected 32-character hex string.",
        )

    trace_detail = storage.get_trace_detail(trace_id)

    if not trace_detail:
        raise HTTPException(
            status_code=404,
            detail=f"Trace not found: {trace_id}",
        )

    return TraceDetailResponse(**trace_detail)


@router.get("/statistics", response_model=TraceStatisticsResponse)
async def get_trace_statistics(
    start_time: datetime | None = Query(None, description="开始时间"),
    end_time: datetime | None = Query(None, description="结束时间"),
    hours: int | None = Query(None, ge=1, le=720, description="最近N小时"),
):
    """
    获取追踪统计信息。

    Args:
        start_time: 开始时间（可选）
        end_time: 结束时间（可选）
        hours: 最近N小时（可选，优先级高于start_time/end_time）

    Returns:
        TraceStatisticsResponse: 追踪统计响应

    Example:
        GET /api/v1/tracing/statistics?hours=24
    """
    storage = get_trace_storage()
    if not storage:
        raise HTTPException(
            status_code=503,
            detail="Trace storage not initialized",
        )

    # 如果指定了hours参数，自动计算时间范围
    if hours:
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

    stats = storage.get_statistics(
        start_time=start_time,
        end_time=end_time,
    )

    return TraceStatisticsResponse(**stats)


@router.delete("/traces/cleanup")
async def cleanup_old_traces(
    max_age_days: int = Query(30, ge=1, le=365, description="保留天数"),
):
    """
    清理过期追踪数据。

    Args:
        max_age_days: 保留天数，范围1-365

    Returns:
        dict: 清理结果

    Example:
        DELETE /api/v1/tracing/traces/cleanup?max_age_days=30
    """
    storage = get_trace_storage()
    if not storage:
        raise HTTPException(
            status_code=503,
            detail="Trace storage not initialized",
        )

    deleted_count = storage.cleanup_old_traces(max_age_days=max_age_days)

    logger.info(f"[Tracing] Cleaned up {deleted_count} old traces (max_age_days={max_age_days})")

    return {
        "success": True,
        "deleted_count": deleted_count,
        "message": f"Cleaned up {deleted_count} traces older than {max_age_days} days",
    }


@router.get("/health")
async def tracing_health_check():
    """
    追踪系统健康检查。

    Returns:
        dict: 健康状态

    Example:
        GET /api/v1/tracing/health
    """
    storage = get_trace_storage()

    if not storage:
        return {
            "status": "unhealthy",
            "message": "Trace storage not initialized",
        }

    try:
        # 尝试查询最近的追踪记录
        recent_traces = storage.query_traces(limit=1)

        # 获取统计信息
        stats = storage.get_statistics()

        return {
            "status": "healthy",
            "message": "Tracing system is operational",
            "total_traces": stats["total_traces"],
            "error_rate": stats["error_rate"],
        }
    except Exception as e:
        logger.error(f"[Tracing] Health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": f"Health check failed: {str(e)}",
        }


@router.get("/spans/{span_id}")
async def get_span_detail(span_id: str):
    """
    获取Span详情。

    Args:
        span_id: Span ID（16位十六进制字符串）

    Returns:
        dict: Span详情

    Raises:
        HTTPException: Span不存在时返回404错误

    Example:
        GET /api/v1/tracing/spans/abc123def456...
    """
    storage = get_trace_storage()
    if not storage:
        raise HTTPException(
            status_code=503,
            detail="Trace storage not initialized",
        )

    # 验证span_id格式
    if not span_id or len(span_id) != 16:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid span_id format: {span_id}. Expected 16-character hex string.",
        )

    # 查询Span（需要通过trace_id查询）
    # 注意：这里需要扩展TraceStorage来支持直接查询Span
    # 暂时返回提示信息
    raise HTTPException(
        status_code=501,
        detail="Span query by ID not implemented yet. Please query by trace_id.",
    )


@router.get("/search")
async def search_traces(
    query: str = Query(..., min_length=1, max_length=100, description="搜索关键词"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
):
    """
    搜索追踪记录。

    Args:
        query: 搜索关键词（在span名称和属性中搜索）
        limit: 返回数量限制，范围1-200

    Returns:
        dict: 搜索结果

    Example:
        GET /api/v1/tracing/search?query=motor&limit=50
    """
    storage = get_trace_storage()
    if not storage:
        raise HTTPException(
            status_code=503,
            detail="Trace storage not initialized",
        )

    # 搜索功能（简化实现：在root_span_name中搜索）
    # 注意：完整实现需要使用数据库全文搜索或专门的搜索引擎
    all_traces = storage.query_traces(limit=1000)

    # 过滤匹配的追踪记录
    matched_traces = [
        trace
        for trace in all_traces
        if query.lower() in (trace.get("root_span_name") or "").lower()
    ][:limit]

    return {
        "query": query,
        "total": len(matched_traces),
        "traces": matched_traces,
    }
