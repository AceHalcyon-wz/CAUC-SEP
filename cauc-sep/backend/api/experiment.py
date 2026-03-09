"""
实验管理 API 路由模块

功能：
- 实验创建
- 实验启动/停止
- 实验列表查询
- 实验数据导出

安全加固：
- SubTask 13.1: 输入验证增强（exp_id范围验证、limit参数验证）

链路追踪：
- 关键操作自动追踪
"""

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Query

from api.schemas import ExperimentRequest, SuccessResponse
from core.data_storage import DataStorage
from core.tracing import traced, SpanKind, get_current_span
from middleware.security import validate_experiment_id

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/experiment",
    tags=["experiment"],
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


@router.post("/start", response_model=SuccessResponse)
@traced(name="experiment.start", kind=SpanKind.INTERNAL)
async def start_experiment(
    request: ExperimentRequest,
    db: DataStorage = Depends(get_storage),
):
    """
    开始实验

    Args:
        request: 实验请求
        db: 数据存储实例

    Returns:
        SuccessResponse: 实验启动结果
    """
    # 添加追踪属性
    span = get_current_span()
    if span:
        span.set_attribute("experiment.name", request.name)

    exp_id = db.start_experiment(
        name=request.name,
        description=request.description,
    )

    # 记录实验ID到追踪
    if span:
        span.set_attribute("experiment.id", exp_id)

    return {
        "success": True,
        "message": f"Experiment '{request.name}' started",
        "experiment_id": exp_id,
    }


@router.post("/{exp_id}/stop", response_model=SuccessResponse)
async def stop_experiment(
    exp_id: int,
    db: DataStorage = Depends(get_storage),
):
    """
    停止实验

    Args:
        exp_id: 实验ID
        db: 数据存储实例

    Returns:
        SuccessResponse: 实验停止结果

    Raises:
        HTTPException: exp_id无效时返回400错误
    """
    # SubTask 13.1: 输入验证 - 验证exp_id范围
    if not validate_experiment_id(exp_id):
        raise HTTPException(
            status_code=400, detail=f"Invalid experiment ID: {exp_id}. Must be a positive integer."
        )

    db.stop_experiment()
    return {
        "success": True,
        "message": "Experiment stopped",
        "experiment_id": exp_id,
    }


@router.get("/")
async def list_experiments(
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制，范围1-1000"),
    db: DataStorage = Depends(get_storage),
):
    """
    列出实验

    Args:
        limit: 返回数量限制，范围1-1000
        db: 数据存储实例

    Returns:
        dict: 实验列表
    """
    # SubTask 13.1: 输入验证 - limit已通过Query验证
    experiments = db.list_experiments(limit)
    return {
        "count": len(experiments),
        "experiments": experiments,
    }


@router.get("/{exp_id}")
async def get_experiment(
    exp_id: int,
    db: DataStorage = Depends(get_storage),
):
    """
    获取实验详情

    Args:
        exp_id: 实验ID
        db: 数据存储实例

    Returns:
        dict: 实验详情

    Raises:
        HTTPException: exp_id无效时返回400错误，实验不存在返回404错误
    """
    # SubTask 13.1: 输入验证 - 验证exp_id范围
    if not validate_experiment_id(exp_id):
        raise HTTPException(
            status_code=400, detail=f"Invalid experiment ID: {exp_id}. Must be a positive integer."
        )

    experiment = db.get_experiment(exp_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment


@router.get("/{exp_id}/export")
async def export_experiment(
    exp_id: int,
    db: DataStorage = Depends(get_storage),
):
    """
    导出实验数据（CSV）

    Args:
        exp_id: 实验ID
        db: 数据存储实例

    Returns:
        dict: 导出结果

    Raises:
        HTTPException: exp_id无效时返回400错误，导出失败返回500错误
    """
    # SubTask 13.1: 输入验证 - 验证exp_id范围
    if not validate_experiment_id(exp_id):
        raise HTTPException(
            status_code=400, detail=f"Invalid experiment ID: {exp_id}. Must be a positive integer."
        )

    export_dir = "exports"
    os.makedirs(export_dir, exist_ok=True)

    # 使用安全的文件名格式（避免路径遍历攻击）
    safe_filename = f"experiment_{exp_id}.csv"
    filepath = os.path.join(export_dir, safe_filename)

    # 确保文件路径在导出目录内（防止路径遍历）
    real_export_dir = os.path.realpath(export_dir)
    real_filepath = os.path.realpath(filepath)
    if not real_filepath.startswith(real_export_dir):
        raise HTTPException(status_code=400, detail="Invalid file path")

    result = db.export_to_csv(exp_id, filepath)

    if result:
        return {
            "success": True,
            "filepath": filepath,
            "message": f"Exported to {filepath}",
        }
    else:
        raise HTTPException(status_code=500, detail="Export failed")
