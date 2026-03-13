"""
性能分析 API 路由模块

文件名: performance.py
路径: backend/api/
功能: 性能分析API，提供系统监控、函数分析、内存追踪等接口
作者: CAUC-SEP Team
创建日期: 2024-01-01
依赖: FastAPI, core.profiler

主要功能：
- 系统资源监控（CPU、内存、磁盘、网络）
- 函数性能分析（执行时间、调用次数）
- 内存使用追踪（内存快照、内存泄漏检测）
- 性能报告生成（综合性能分析报告）
- 性能数据导出（JSON、CSV格式）

API端点：
- GET /system: 获取系统资源信息
- GET /system/history: 获取系统资源历史数据
- GET /functions: 获取函数性能分析数据
- POST /functions/profile: 开始函数性能分析
- GET /memory: 获取内存使用信息
- GET /memory/snapshot: 获取内存快照
- POST /memory/track: 开始内存追踪
- GET /report: 生成性能报告
- GET /export: 导出性能数据

性能指标：
- CPU使用率、核心数、负载
- 内存使用量、可用量、使用率
- 磁盘读写速度、使用率
- 网络流量、连接数
- 函数执行时间、调用次数、平均时间
"""

import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from core.profiler import (
    FunctionProfileResponse,
    MemorySnapshotResponse,
    PerformanceMetricsResponse,
    PerformanceReport,
    SystemInfoResponse,
    get_profiler,
    get_system_monitor,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/performance",
    tags=["performance"],
    responses={404: {"description": "Not found"}},
)


# ============================================================================
# 系统资源监控API
# ============================================================================


@router.get("/system", response_model=SystemInfoResponse)
async def get_system_info():
    """
    获取系统资源信息。

    Returns:
        SystemInfoResponse: 系统资源信息

    Example:
        GET /api/v1/performance/system
    """
    monitor = get_system_monitor()

    return SystemInfoResponse(
        cpu={"percent": monitor.get_cpu_percent(interval=0.0)},
        memory=monitor.get_memory_info(),
        disk=monitor.get_disk_info(),
        process=monitor.get_process_info(),
    )


@router.get("/metrics", response_model=PerformanceMetricsResponse)
async def get_performance_metrics():
    """
    获取性能指标。

    Returns:
        PerformanceMetricsResponse: 性能指标列表

    Example:
        GET /api/v1/performance/metrics
    """
    monitor = get_system_monitor()
    metrics = monitor.collect_metrics()

    return PerformanceMetricsResponse(
        metrics=[metric.to_dict() for metric in metrics],
        timestamp=datetime.now().isoformat(),
    )


@router.get("/cpu")
async def get_cpu_stats():
    """
    获取CPU统计信息。

    Returns:
        dict: CPU统计信息

    Example:
        GET /api/v1/performance/cpu
    """
    monitor = get_system_monitor()

    return {
        "cpu_percent": monitor.get_cpu_percent(interval=0.1),
        "cpu_count": monitor._psutil.cpu_count() if monitor._available else 0,
        "cpu_freq": (
            monitor._psutil.cpu_freq()._asdict()
            if monitor._available and monitor._psutil.cpu_freq()
            else {}
        ),
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/memory")
async def get_memory_stats():
    """
    获取内存统计信息。

    Returns:
        dict: 内存统计信息

    Example:
        GET /api/v1/performance/memory
    """
    monitor = get_system_monitor()
    mem_info = monitor.get_memory_info()

    return {
        "total_mb": mem_info["total_mb"],
        "available_mb": mem_info["available_mb"],
        "used_mb": mem_info["used_mb"],
        "percent": mem_info["percent"],
        "process_memory_mb": monitor.get_process_info()["memory_mb"],
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================================
# 函数性能分析API
# ============================================================================


@router.get("/functions", response_model=FunctionProfileResponse)
async def get_function_profiles():
    """
    获取函数性能分析数据。

    Returns:
        FunctionProfileResponse: 函数性能数据

    Example:
        GET /api/v1/performance/functions
    """
    profiler = get_profiler()
    function_stats = profiler.get_function_stats()

    return FunctionProfileResponse(
        function_profiles=function_stats,
        total_functions=len(function_stats),
    )


@router.post("/profile/start")
async def start_profiling(background_tasks: BackgroundTasks):
    """
    开始性能分析会话。

    Args:
        background_tasks: FastAPI后台任务

    Returns:
        dict: 操作结果

    Example:
        POST /api/v1/performance/profile/start
    """
    profiler = get_profiler()

    try:
        profiler.start_profiling()
        return {
            "success": True,
            "message": "Profiling started",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"[Performance] Failed to start profiling: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start profiling: {str(e)}",
        )


@router.post("/profile/stop")
async def stop_profiling():
    """
    停止性能分析会话。

    Returns:
        dict: 分析结果

    Example:
        POST /api/v1/performance/profile/stop
    """
    profiler = get_profiler()

    try:
        result = profiler.stop_profiling()
        return {
            "success": True,
            "message": "Profiling stopped",
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"[Performance] Failed to stop profiling: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop profiling: {str(e)}",
        )


@router.get("/profile/snapshot")
async def take_profile_snapshot():
    """
    获取当前性能快照。

    Returns:
        dict: 性能快照数据

    Example:
        GET /api/v1/performance/profile/snapshot
    """
    profiler = get_profiler()

    # 收集系统指标
    system_metrics = profiler.get_system_metrics()

    # 收集函数统计
    function_stats = profiler.get_function_stats()

    # 收集内存快照
    memory_snapshots = profiler.get_memory_snapshots()

    return {
        "timestamp": datetime.now().isoformat(),
        "system_metrics": system_metrics,
        "function_stats": function_stats[:50],  # TOP 50
        "memory_snapshots": memory_snapshots,
    }


# ============================================================================
# 内存追踪API
# ============================================================================


@router.get("/memory/snapshots")
async def get_memory_snapshots():
    """
    获取内存快照列表。

    Returns:
        dict: 内存快照列表

    Example:
        GET /api/v1/performance/memory/snapshots
    """
    profiler = get_profiler()
    snapshots = profiler.get_memory_snapshots()

    return {
        "total": len(snapshots),
        "snapshots": snapshots,
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/memory/track/start")
async def start_memory_tracking():
    """
    开始内存追踪。

    Returns:
        dict: 操作结果

    Example:
        POST /api/v1/performance/memory/track/start
    """
    profiler = get_profiler()

    try:
        profiler.start_memory_tracking()
        return {
            "success": True,
            "message": "Memory tracking started",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"[Performance] Failed to start memory tracking: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start memory tracking: {str(e)}",
        )


@router.post("/memory/track/stop", response_model=MemorySnapshotResponse)
async def stop_memory_tracking():
    """
    停止内存追踪。

    Returns:
        MemorySnapshotResponse: 内存快照

    Example:
        POST /api/v1/performance/memory/track/stop
    """
    profiler = get_profiler()

    try:
        snapshot = profiler.stop_memory_tracking()

        return MemorySnapshotResponse(
            current_memory_mb=snapshot.current_memory_mb,
            peak_memory_mb=snapshot.peak_memory_mb,
            memory_blocks=snapshot.memory_blocks,
            top_allocations=snapshot.top_allocations,
        )
    except Exception as e:
        logger.error(f"[Performance] Failed to stop memory tracking: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop memory tracking: {str(e)}",
        )


# ============================================================================
# 性能报告API
# ============================================================================


@router.post("/report/generate")
async def generate_performance_report(
    include_functions: bool = Query(True, description="包含函数性能数据"),
    include_memory: bool = Query(True, description="包含内存数据"),
    include_system: bool = Query(True, description="包含系统数据"),
):
    """
    生成性能分析报告。

    Args:
        include_functions: 是否包含函数性能数据
        include_memory: 是否包含内存数据
        include_system: 是否包含系统数据

    Returns:
        dict: 性能报告

    Example:
        POST /api/v1/performance/report/generate?include_functions=true
    """
    profiler = get_profiler()
    monitor = get_system_monitor()

    report = PerformanceReport()

    # 添加系统资源章节
    if include_system:
        system_data = {
            "cpu_percent": monitor.get_cpu_percent(interval=0.0),
            **monitor.get_memory_info(),
        }
        report.add_section("系统资源", system_data)

    # 添加函数性能章节
    if include_functions:
        function_stats = profiler.get_function_stats()
        report.add_section("函数性能", {"function_profiles": function_stats})

    # 添加内存章节
    if include_memory:
        memory_snapshots = profiler.get_memory_snapshots()
        if memory_snapshots:
            report.add_section("内存分析", memory_snapshots[0])

    return {
        "success": True,
        "report": report.generate_full_report(),
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/report/html")
async def generate_html_report():
    """
    生成HTML格式性能报告。

    Returns:
        dict: HTML报告内容

    Example:
        GET /api/v1/performance/report/html
    """
    profiler = get_profiler()
    monitor = get_system_monitor()

    report = PerformanceReport()

    # 添加系统资源章节
    system_data = {
        "cpu_percent": monitor.get_cpu_percent(interval=0.0),
        **monitor.get_memory_info(),
    }
    report.add_section("系统资源", system_data)

    # 添加函数性能章节
    function_stats = profiler.get_function_stats()
    if function_stats:
        report.add_section("函数性能", {"function_profiles": function_stats})

    # 添加内存章节
    memory_snapshots = profiler.get_memory_snapshots()
    if memory_snapshots:
        report.add_section("内存分析", memory_snapshots[0])

    html_content = report.generate_html()

    return {
        "success": True,
        "html": html_content,
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================================
# 性能数据管理API
# ============================================================================


@router.delete("/data/clear")
async def clear_performance_data():
    """
    清空性能数据。

    Returns:
        dict: 操作结果

    Example:
        DELETE /api/v1/performance/data/clear
    """
    profiler = get_profiler()

    try:
        profiler.clear()
        return {
            "success": True,
            "message": "Performance data cleared",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"[Performance] Failed to clear data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear data: {str(e)}",
        )


@router.get("/health")
async def performance_health_check():
    """
    性能监控系统健康检查。

    Returns:
        dict: 健康状态

    Example:
        GET /api/v1/performance/health
    """
    monitor = get_system_monitor()
    profiler = get_profiler()

    try:
        # 检查系统监控
        cpu_percent = monitor.get_cpu_percent(interval=0.0)
        mem_info = monitor.get_memory_info()

        # 检查性能分析器
        function_count = len(profiler.get_function_stats())
        snapshot_count = len(profiler.get_memory_snapshots())

        # 判断健康状态
        is_healthy = True
        warnings = []

        if cpu_percent > 90:
            warnings.append(f"High CPU usage: {cpu_percent:.1f}%")
            is_healthy = False

        if mem_info["percent"] > 90:
            warnings.append(f"High memory usage: {mem_info['percent']:.1f}%")
            is_healthy = False

        return {
            "status": "healthy" if is_healthy else "warning",
            "message": "Performance monitoring is operational",
            "cpu_percent": cpu_percent,
            "memory_percent": mem_info["percent"],
            "tracked_functions": function_count,
            "memory_snapshots": snapshot_count,
            "warnings": warnings,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"[Performance] Health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": f"Health check failed: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


# ============================================================================
# 性能热点分析API
# ============================================================================


@router.get("/hotspots")
async def get_performance_hotspots(
    threshold_ms: float = Query(10.0, description="时间阈值(毫秒)"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
):
    """
    获取性能热点。

    Args:
        threshold_ms: 时间阈值（毫秒）
        limit: 返回数量限制

    Returns:
        dict: 性能热点列表

    Example:
        GET /api/v1/performance/hotspots?threshold_ms=10&limit=20
    """
    profiler = get_profiler()
    function_stats = profiler.get_function_stats()

    # 过滤超过阈值的函数
    threshold_sec = threshold_ms / 1000.0
    hotspots = [
        func
        for func in function_stats
        if func.get("avg_time", 0) >= threshold_sec or func.get("total_time", 0) >= threshold_sec
    ]

    # 按总时间排序
    hotspots.sort(key=lambda x: x.get("total_time", 0), reverse=True)

    return {
        "threshold_ms": threshold_ms,
        "total_hotspots": len(hotspots),
        "hotspots": hotspots[:limit],
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/summary")
async def get_performance_summary():
    """
    获取性能摘要。

    Returns:
        dict: 性能摘要数据

    Example:
        GET /api/v1/performance/summary
    """
    monitor = get_system_monitor()
    profiler = get_profiler()

    # 系统资源
    cpu_percent = monitor.get_cpu_percent(interval=0.0)
    mem_info = monitor.get_memory_info()
    proc_info = monitor.get_process_info()

    # 函数统计
    function_stats = profiler.get_function_stats()
    total_calls = sum(f.get("total_calls", 0) for f in function_stats)
    total_time = sum(f.get("total_time", 0) for f in function_stats)

    # 内存快照
    memory_snapshots = profiler.get_memory_snapshots()
    peak_memory = max((s.get("peak_memory_mb", 0) for s in memory_snapshots), default=0)

    return {
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": mem_info["percent"],
            "process_memory_mb": proc_info["memory_mb"],
        },
        "functions": {
            "tracked_count": len(function_stats),
            "total_calls": total_calls,
            "total_time_sec": round(total_time, 3),
        },
        "memory": {
            "snapshots_count": len(memory_snapshots),
            "peak_memory_mb": round(peak_memory, 2),
        },
        "timestamp": datetime.now().isoformat(),
    }
