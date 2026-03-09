"""
崩溃报告管理 API 路由模块。

提供崩溃报告的查询、统计、更新和导出接口。

功能：
    - 崩溃报告列表查询
    - 崩溃报告详情查看
    - 崩溃报告状态更新
    - 崩溃报告统计分析
    - 崩溃报告导出

作者：Backend Engineer Agent
创建日期：2026-03-07
依赖：fastapi, pydantic
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from core.crash_report import (
    CrashReportStorage,
    CrashSeverity,
    CrashStatus,
    get_crash_report_storage,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/crash-reports", tags=["crash-reports"])


# ==================== Pydantic 模型定义 ====================


class CrashReportListResponse:
    """崩溃报告列表响应模型。"""

    pass


# ==================== 存储实例设置 ====================

# 全局存储实例引用
_crash_storage: Optional[CrashReportStorage] = None


def set_crash_storage(storage: CrashReportStorage) -> None:
    """
    设置崩溃报告存储实例引用。

    Args:
        storage: 崩溃报告存储实例
    """
    global _crash_storage
    _crash_storage = storage
    logger.info("Crash report API: Storage reference updated")


def _get_storage() -> CrashReportStorage:
    """
    获取崩溃报告存储实例。

    Returns:
        CrashReportStorage: 崩溃报告存储实例

    Raises:
        HTTPException: 存储未初始化时抛出503错误
    """
    storage = _crash_storage or get_crash_report_storage()
    if not storage:
        raise HTTPException(status_code=503, detail="Crash report storage not initialized")
    return storage


# ==================== API 端点 ====================


@router.get("")
async def list_crash_reports(
    severity: Optional[str] = Query(None, description="严重程度过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    exception_type: Optional[str] = Query(None, description="异常类型过滤"),
    device_id: Optional[str] = Query(None, description="设备ID过滤"),
    experiment_id: Optional[int] = Query(None, description="实验ID过滤"),
    user_id: Optional[str] = Query(None, description="用户ID过滤"),
    start_time: Optional[str] = Query(None, description="开始时间(ISO格式)"),
    end_time: Optional[str] = Query(None, description="结束时间(ISO格式)"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """
    查询崩溃报告列表。

    支持多种过滤条件，返回简化的报告列表。

    Args:
        severity: 严重程度过滤（critical/high/medium/low）
        status: 状态过滤（new/acknowledged/resolved/ignored）
        exception_type: 异常类型过滤（模糊匹配）
        device_id: 设备ID过滤
        experiment_id: 实验ID过滤
        user_id: 用户ID过滤
        start_time: 开始时间过滤（ISO格式）
        end_time: 结束时间过滤（ISO格式）
        limit: 返回数量限制（1-1000）
        offset: 偏移量（分页）

    Returns:
        dict: 包含总数和报告列表

    Example:
        ```bash
        # 查询最近的高严重程度崩溃
        curl "http://localhost:8000/api/crash-reports?severity=high&limit=10"

        # 查询特定设备的崩溃报告
        curl "http://localhost:8000/api/crash-reports?device_id=stepper_01"
        ```
    """
    try:
        storage = _get_storage()

        # 解析时间参数
        start_dt = None
        end_dt = None
        if start_time:
            start_dt = datetime.fromisoformat(start_time)
        if end_time:
            end_dt = datetime.fromisoformat(end_time)

        # 查询报告
        reports = storage.query_reports(
            severity=severity,
            status=status,
            exception_type=exception_type,
            device_id=device_id,
            experiment_id=experiment_id,
            user_id=user_id,
            start_time=start_dt,
            end_time=end_dt,
            limit=limit,
            offset=offset,
        )

        return {
            "total": len(reports),
            "limit": limit,
            "offset": offset,
            "reports": reports,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to list crash reports: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list crash reports: {str(e)}")


@router.get("/statistics")
async def get_crash_statistics(
    start_time: Optional[str] = Query(None, description="开始时间(ISO格式)"),
    end_time: Optional[str] = Query(None, description="结束时间(ISO格式)"),
):
    """
    获取崩溃报告统计信息。

    返回崩溃报告的统计数据，包括按严重程度、状态、异常类型的分布。

    Args:
        start_time: 开始时间过滤（ISO格式）
        end_time: 结束时间过滤（ISO格式）

    Returns:
        dict: 统计信息

    Example:
        ```bash
        curl "http://localhost:8000/api/crash-reports/statistics"
        ```
    """
    try:
        storage = _get_storage()

        # 解析时间参数
        start_dt = None
        end_dt = None
        if start_time:
            start_dt = datetime.fromisoformat(start_time)
        if end_time:
            end_dt = datetime.fromisoformat(end_time)

        # 获取统计信息
        stats = storage.get_statistics(start_time=start_dt, end_time=end_dt)

        return stats

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to get crash statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get crash statistics: {str(e)}")


@router.get("/{report_id}")
async def get_crash_report(report_id: str):
    """
    获取崩溃报告详情。

    返回完整的崩溃报告信息，包括系统环境、异常堆栈等。

    Args:
        report_id: 报告ID

    Returns:
        dict: 完整的崩溃报告信息

    Raises:
        HTTPException: 报告不存在时返回404

    Example:
        ```bash
        curl "http://localhost:8000/api/crash-reports/abc123..."
        ```
    """
    try:
        storage = _get_storage()

        report = storage.get_report(report_id)

        if not report:
            raise HTTPException(status_code=404, detail=f"Crash report not found: {report_id}")

        return report.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get crash report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get crash report: {str(e)}")


@router.put("/{report_id}/status")
async def update_crash_report_status(
    report_id: str,
    status: str = Query(..., description="新状态"),
    notes: Optional[str] = Query(None, description="处理备注"),
    resolved_by: Optional[str] = Query(None, description="解决人"),
):
    """
    更新崩溃报告状态。

    更新崩溃报告的处理状态，支持添加处理备注。

    Args:
        report_id: 报告ID
        status: 新状态（new/acknowledged/resolved/ignored）
        notes: 处理备注（可选）
        resolved_by: 解决人（可选）

    Returns:
        dict: 更新结果

    Raises:
        HTTPException: 报告不存在或状态无效时返回错误

    Example:
        ```bash
        # 标记为已确认
        curl -X PUT "http://localhost:8000/api/crash-reports/abc123/status?status=acknowledged&notes=正在调查"

        # 标记为已解决
        curl -X PUT "http://localhost:8000/api/crash-reports/abc123/status?status=resolved&resolved_by=admin"
        ```
    """
    try:
        storage = _get_storage()

        # 验证状态值
        valid_statuses = [
            CrashStatus.NEW,
            CrashStatus.ACKNOWLEDGED,
            CrashStatus.RESOLVED,
            CrashStatus.IGNORED,
        ]
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400, detail=f"Invalid status: {status}. Valid values: {valid_statuses}"
            )

        # 更新状态
        success = storage.update_report_status(
            report_id=report_id,
            status=status,
            notes=notes,
            resolved_by=resolved_by,
        )

        if not success:
            raise HTTPException(status_code=404, detail=f"Crash report not found: {report_id}")

        return {
            "success": True,
            "report_id": report_id,
            "status": status,
            "message": f"Report status updated to {status}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update crash report status: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update crash report status: {str(e)}"
        )


@router.get("/{report_id}/export")
async def export_crash_report(report_id: str):
    """
    导出崩溃报告到文件。

    将崩溃报告导出为压缩的JSON文件，便于分享和归档。

    Args:
        report_id: 报告ID

    Returns:
        FileResponse: 压缩的JSON文件

    Raises:
        HTTPException: 报告不存在时返回404

    Example:
        ```bash
        curl -O "http://localhost:8000/api/crash-reports/abc123/export"
        ```
    """
    try:
        storage = _get_storage()

        # 导出报告
        filepath = storage.export_report(report_id, output_dir="crash_exports")

        if not filepath:
            raise HTTPException(
                status_code=404, detail=f"Crash report not found or export failed: {report_id}"
            )

        return FileResponse(
            path=filepath,
            media_type="application/gzip",
            filename=f"crash_report_{report_id}.json.gz",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export crash report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export crash report: {str(e)}")


@router.post("/cleanup")
async def cleanup_old_crash_reports(
    max_age_days: int = Query(30, ge=1, le=365, description="保留天数"),
):
    """
    清理过期崩溃报告。

    删除已解决且超过保留天数的崩溃报告。

    Args:
        max_age_days: 保留天数（1-365）

    Returns:
        dict: 清理结果

    Example:
        ```bash
        # 清理30天前的已解决报告
        curl -X POST "http://localhost:8000/api/crash-reports/cleanup?max_age_days=30"
        ```
    """
    try:
        storage = _get_storage()

        # 执行清理
        deleted_count = storage.cleanup_old_reports(max_age_days=max_age_days)

        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Cleaned up {deleted_count} old crash reports",
        }

    except Exception as e:
        logger.error(f"Failed to cleanup crash reports: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup crash reports: {str(e)}")


# ==================== 辅助端点 ====================


@router.get("/severity/levels")
async def get_severity_levels():
    """
    获取严重程度级别列表。

    Returns:
        dict: 严重程度级别及其描述

    Example:
        ```bash
        curl "http://localhost:8000/api/crash-reports/severity/levels"
        ```
    """
    return {
        "levels": [
            {
                "value": CrashSeverity.CRITICAL,
                "label": "致命",
                "description": "致命错误，系统无法继续运行",
                "color": "#ff0000",
            },
            {
                "value": CrashSeverity.HIGH,
                "label": "严重",
                "description": "严重错误，影响核心功能",
                "color": "#ff6600",
            },
            {
                "value": CrashSeverity.MEDIUM,
                "label": "中等",
                "description": "中等错误，影响部分功能",
                "color": "#ffcc00",
            },
            {
                "value": CrashSeverity.LOW,
                "label": "轻微",
                "description": "轻微错误，不影响核心功能",
                "color": "#00cc00",
            },
        ]
    }


@router.get("/status/values")
async def get_status_values():
    """
    获取状态值列表。

    Returns:
        dict: 状态值及其描述

    Example:
        ```bash
        curl "http://localhost:8000/api/crash-reports/status/values"
        ```
    """
    return {
        "statuses": [
            {
                "value": CrashStatus.NEW,
                "label": "新报告",
                "description": "新报告，未处理",
                "color": "#0066ff",
            },
            {
                "value": CrashStatus.ACKNOWLEDGED,
                "label": "已确认",
                "description": "已确认，待处理",
                "color": "#ffcc00",
            },
            {
                "value": CrashStatus.RESOLVED,
                "label": "已解决",
                "description": "已解决",
                "color": "#00cc00",
            },
            {
                "value": CrashStatus.IGNORED,
                "label": "已忽略",
                "description": "已忽略",
                "color": "#999999",
            },
        ]
    }
