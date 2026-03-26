"""
数据库优化API接口

文件名: database_optimization.py
路径: backend/api/v1/
功能: 提供数据库优化相关的REST API接口
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: FastAPI, Pydantic

API端点:
    - GET /api/v1/database/health: 数据库健康检查
    - POST /api/v1/database/optimize: 执行数据库优化
    - GET /api/v1/database/statistics: 获取统计信息
    - POST /api/v1/database/indexes/apply: 应用索引优化
    - GET /api/v1/database/schema/analyze: 分析Schema
    - POST /api/v1/database/cache/clear: 清空缓存
    - GET /api/v1/database/checkpoint/{experiment_id}: 获取检查点
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.core.storage.database_optimization_service import (
    DatabaseOptimizationService,
    OptimizationConfig,
    get_optimization_service,
)
from backend.core.storage.schema_optimizer import (
    SchemaOptimizer,
    create_schema_optimizer,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/database", tags=["数据库优化"])


# ==================== 请求/响应模型 ====================


class HealthCheckResponse(BaseModel):
    """健康检查响应模型。"""

    healthy: bool = Field(..., description="数据库是否健康")
    timestamp: str = Field(..., description="检查时间戳")
    db_path: str = Field(..., description="数据库路径")
    checks: dict[str, Any] = Field(default_factory=dict, description="各项检查结果")
    errors: list[str] = Field(default_factory=list, description="错误列表")
    warnings: list[str] = Field(default_factory=list, description="警告列表")


class OptimizeRequest(BaseModel):
    """优化请求模型。"""

    vacuum: bool = Field(default=True, description="是否执行VACUUM")
    analyze: bool = Field(default=True, description="是否执行ANALYZE")
    integrity_check: bool = Field(default=True, description="是否执行完整性检查")


class OptimizeResponse(BaseModel):
    """优化响应模型。"""

    vacuum: bool = Field(..., description="VACUUM是否成功")
    analyze: bool = Field(..., description="ANALYZE是否成功")
    integrity_check: bool = Field(..., description="完整性检查是否通过")
    errors: list[str] = Field(default_factory=list, description="错误列表")
    timestamp: str = Field(..., description="优化时间戳")


class StatisticsResponse(BaseModel):
    """统计信息响应模型。"""

    database: dict[str, Any] = Field(default_factory=dict, description="数据库统计")
    device_status_cache: dict[str, Any] = Field(default_factory=dict, description="设备状态缓存统计")
    experiment_data_cache: dict[str, Any] = Field(default_factory=dict, description="实验数据缓存统计")
    config: dict[str, Any] = Field(default_factory=dict, description="配置信息")


class IndexApplyRequest(BaseModel):
    """索引应用请求模型。"""

    dry_run: bool = Field(default=False, description="是否只分析不执行")


class IndexApplyResponse(BaseModel):
    """索引应用响应模型。"""

    created: list[dict[str, Any]] = Field(default_factory=list, description="创建的索引")
    skipped: list[dict[str, Any]] = Field(default_factory=list, description="跳过的索引")
    failed: list[dict[str, Any]] = Field(default_factory=list, description="失败的索引")
    dry_run: bool = Field(..., description="是否为试运行")


class SchemaAnalyzeResponse(BaseModel):
    """Schema分析响应模型。"""

    tables: dict[str, Any] = Field(default_factory=dict, description="表信息")
    total_tables: int = Field(default=0, description="总表数")
    total_rows: int = Field(default=0, description="总行数")
    total_indexes: int = Field(default=0, description="总索引数")
    total_foreign_keys: int = Field(default=0, description="总外键数")
    recommendations: list[dict[str, Any]] = Field(default_factory=list, description="优化建议")


class CacheClearRequest(BaseModel):
    """缓存清空请求模型。"""

    cache_type: str = Field(
        default="all",
        description="缓存类型: all, device_status, experiment_data",
    )


class CacheClearResponse(BaseModel):
    """缓存清空响应模型。"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="操作消息")
    cleared_at: str = Field(..., description="清空时间")


class CheckpointResponse(BaseModel):
    """检查点响应模型。"""

    experiment_id: int = Field(..., description="实验ID")
    file_path: str = Field(..., description="文件路径")
    last_record_index: int = Field(default=0, description="最后记录索引")
    last_timestamp: float = Field(default=0.0, description="最后时间戳")
    record_count: int = Field(default=0, description="记录数")
    updated_at: str = Field(default="", description="更新时间")


# ==================== 依赖注入 ====================


def get_db_optimization_service() -> DatabaseOptimizationService:
    """
    获取数据库优化服务实例。

    Returns:
        DatabaseOptimizationService: 服务实例
    """
    return get_optimization_service()


def get_schema_optimizer() -> SchemaOptimizer:
    """
    获取Schema优化器实例。

    Returns:
        SchemaOptimizer: 优化器实例
    """
    return create_schema_optimizer("experiments.db")


# ==================== API端点 ====================


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="数据库健康检查",
    description="执行完整的数据库健康检查，包括文件状态、连接状态、完整性、磁盘空间等",
)
async def check_database_health(
    service: DatabaseOptimizationService = Depends(get_db_optimization_service),
) -> HealthCheckResponse:
    """
    执行数据库健康检查。

    检查项目：
    - 数据库文件是否存在
    - 数据库连接是否正常
    - 数据库完整性
    - 磁盘空间
    - WAL模式状态
    - 索引状态

    Returns:
        HealthCheckResponse: 健康检查结果
    """
    try:
        result = service.check_health()
        return HealthCheckResponse(**result)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")


@router.post(
    "/optimize",
    response_model=OptimizeResponse,
    summary="执行数据库优化",
    description="执行VACUUM、ANALYZE等数据库优化操作",
)
async def optimize_database(
    request: OptimizeRequest,
    service: DatabaseOptimizationService = Depends(get_db_optimization_service),
) -> OptimizeResponse:
    """
    执行数据库优化。

    包括：
    - VACUUM：重建数据库，清理碎片
    - ANALYZE：更新统计信息
    - 完整性检查

    Args:
        request: 优化请求参数

    Returns:
        OptimizeResponse: 优化结果
    """
    try:
        result = service.optimize_database()
        return OptimizeResponse(**result)
    except Exception as e:
        logger.error(f"Database optimization failed: {e}")
        raise HTTPException(status_code=500, detail=f"数据库优化失败: {str(e)}")


@router.get(
    "/statistics",
    response_model=StatisticsResponse,
    summary="获取数据库统计信息",
    description="获取数据库操作统计、缓存统计等详细信息",
)
async def get_database_statistics(
    service: DatabaseOptimizationService = Depends(get_db_optimization_service),
) -> StatisticsResponse:
    """
    获取数据库统计信息。

    包括：
    - 数据库操作统计
    - 设备状态缓存统计
    - 实验数据缓存统计
    - 配置信息

    Returns:
        StatisticsResponse: 统计信息
    """
    try:
        result = service.get_all_statistics()
        return StatisticsResponse(**result)
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.post(
    "/indexes/apply",
    response_model=IndexApplyResponse,
    summary="应用索引优化",
    description="根据预定义配置创建数据库索引",
)
async def apply_database_indexes(
    request: IndexApplyRequest,
    optimizer: SchemaOptimizer = Depends(get_schema_optimizer),
) -> IndexApplyResponse:
    """
    应用数据库索引优化。

    根据预定义的索引配置创建索引，支持试运行模式。

    Args:
        request: 索引应用请求

    Returns:
        IndexApplyResponse: 应用结果
    """
    try:
        result = optimizer.get_index_manager().apply_predefined_indexes(
            dry_run=request.dry_run
        )
        return IndexApplyResponse(**result)
    except Exception as e:
        logger.error(f"Failed to apply indexes: {e}")
        raise HTTPException(status_code=500, detail=f"应用索引失败: {str(e)}")


@router.get(
    "/schema/analyze",
    response_model=SchemaAnalyzeResponse,
    summary="分析数据库Schema",
    description="分析数据库表结构，提供优化建议",
)
async def analyze_database_schema(
    optimizer: SchemaOptimizer = Depends(get_schema_optimizer),
) -> SchemaAnalyzeResponse:
    """
    分析数据库Schema。

    分析内容：
    - 所有表的结构信息
    - 索引数量和分布
    - 外键约束
    - 优化建议

    Returns:
        SchemaAnalyzeResponse: 分析结果
    """
    try:
        result = optimizer.analyze_schema()
        return SchemaAnalyzeResponse(**result)
    except Exception as e:
        logger.error(f"Failed to analyze schema: {e}")
        raise HTTPException(status_code=500, detail=f"Schema分析失败: {str(e)}")


@router.post(
    "/cache/clear",
    response_model=CacheClearResponse,
    summary="清空缓存",
    description="清空指定类型或所有缓存",
)
async def clear_cache(
    request: CacheClearRequest,
    service: DatabaseOptimizationService = Depends(get_db_optimization_service),
) -> CacheClearResponse:
    """
    清空缓存。

    支持清空：
    - all: 所有缓存
    - device_status: 设备状态缓存
    - experiment_data: 实验数据缓存

    Args:
        request: 缓存清空请求

    Returns:
        CacheClearResponse: 清空结果
    """
    try:
        cache_type = request.cache_type.lower()

        if cache_type == "all":
            service.clear_all_caches()
            message = "所有缓存已清空"
        elif cache_type == "device_status":
            service.get_device_status_cache().clear_all()
            message = "设备状态缓存已清空"
        elif cache_type == "experiment_data":
            service.get_experiment_data_cache().clear_all()
            message = "实验数据缓存已清空"
        else:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的缓存类型: {cache_type}",
            )

        return CacheClearResponse(
            success=True,
            message=message,
            cleared_at=datetime.now().isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=f"清空缓存失败: {str(e)}")


@router.get(
    "/checkpoint/{experiment_id}",
    response_model=CheckpointResponse | None,
    summary="获取实验检查点",
    description="获取指定实验的最新HDF5存储检查点",
)
async def get_experiment_checkpoint(
    experiment_id: int,
) -> CheckpointResponse | None:
    """
    获取实验检查点。

    用于断点续存，返回实验的最新存储状态。

    Args:
        experiment_id: 实验ID

    Returns:
        CheckpointResponse: 检查点信息，不存在返回None
    """
    try:
        from backend.core.storage.hdf5_resumable_storage import CheckpointManager

        checkpoint_manager = CheckpointManager("data/hdf5/checkpoints.db")
        checkpoint = checkpoint_manager.get_latest_checkpoint(experiment_id)

        if checkpoint is None:
            return None

        return CheckpointResponse(
            experiment_id=checkpoint.experiment_id,
            file_path=checkpoint.file_path,
            last_record_index=checkpoint.last_record_index,
            last_timestamp=checkpoint.last_timestamp,
            record_count=checkpoint.record_count,
            updated_at=checkpoint.updated_at,
        )
    except Exception as e:
        logger.error(f"Failed to get checkpoint: {e}")
        raise HTTPException(status_code=500, detail=f"获取检查点失败: {str(e)}")


@router.get(
    "/constraints/check",
    summary="检查数据库约束",
    description="检查外键约束、唯一约束等",
)
async def check_database_constraints(
    optimizer: SchemaOptimizer = Depends(get_schema_optimizer),
) -> dict[str, Any]:
    """
    检查数据库约束。

    检查内容：
    - 外键约束是否启用
    - 外键违规情况
    - 外键定义列表

    Returns:
        约束检查结果
    """
    try:
        result = optimizer.get_constraint_checker().check_foreign_keys()
        return result
    except Exception as e:
        logger.error(f"Failed to check constraints: {e}")
        raise HTTPException(status_code=500, detail=f"约束检查失败: {str(e)}")


@router.get(
    "/tables",
    summary="获取所有表信息",
    description="获取数据库中所有表的结构信息",
)
async def get_all_tables(
    optimizer: SchemaOptimizer = Depends(get_schema_optimizer),
) -> dict[str, Any]:
    """
    获取所有表信息。

    返回每个表的：
    - 列信息
    - 索引数量
    - 外键数量
    - 行数

    Returns:
        表信息字典
    """
    try:
        schemas = optimizer.get_all_table_schemas()
        return {
            name: {
                "columns": len(schema.columns),
                "indexes": len(schema.indexes),
                "foreign_keys": len(schema.foreign_keys),
                "row_count": schema.row_count,
            }
            for name, schema in schemas.items()
        }
    except Exception as e:
        logger.error(f"Failed to get tables: {e}")
        raise HTTPException(status_code=500, detail=f"获取表信息失败: {str(e)}")


# ==================== 注册路由函数 ====================


def include_database_optimization_routes(app: Any) -> None:
    """
    将数据库优化路由注册到FastAPI应用。

    Args:
        app: FastAPI应用实例
    """
    app.include_router(router)
    logger.info("Database optimization routes registered")
