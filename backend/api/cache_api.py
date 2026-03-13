"""
缓存管理 API 路由模块

文件名: cache_api.py
路径: backend/api/
功能: 缓存系统管理API，提供Redis缓存、本地缓存的状态查询与管理接口
作者: CAUC-SEP Team
创建日期: 2024-01-01
依赖: FastAPI, core.cache, core.local_cache, core.cache_strategy

主要功能：
- 缓存状态查询（Redis、本地缓存、设备缓存）
- 缓存统计信息（命中率、内存使用、键数量）
- 缓存管理操作（清理、失效、刷新）
- 穿透保护统计（布隆过滤器、空值缓存）
- 失效事件追踪（事件日志、失效原因）

API端点：
- GET /status: 获取缓存系统状态
- GET /statistics: 获取详细缓存统计信息
- GET /redis/health: 检查Redis健康状态
- GET /redis/statistics: 获取Redis缓存统计信息
- GET /local/statistics: 获取本地缓存统计信息
- POST /local/cleanup: 手动清理本地缓存过期条目
- POST /device/{device_id}/invalidate: 失效指定设备的所有缓存
- POST /device/{device_id}/status/refresh: 刷新设备状态缓存
- POST /device/{device_id}/config/invalidate: 失效设备配置缓存
- GET /invalidation/events: 获取最近的缓存失效事件
- GET /penetration/statistics: 获取缓存穿透保护统计信息
- POST /clear: 清空所有缓存（谨慎使用）

安全特性：
- 缓存操作日志记录
- 危险操作（清空缓存）需谨慎使用
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from core.cache import get_cache_manager
from core.cache_strategy import (
    get_all_cache_stats,
    get_device_cache_manager,
    get_invalidation_manager,
    get_penetration_protector,
)
from core.local_cache import get_all_local_cache_stats

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/cache",
    tags=["cache"],
    responses={404: {"description": "Not found"}},
)


@router.get("/status")
async def get_cache_status() -> dict[str, Any]:
    """
    获取缓存系统状态。

    Returns:
        dict: 缓存状态信息
    """
    status = {
        "redis_cache": None,
        "local_cache": get_all_local_cache_stats(),
        "device_cache": None,
        "penetration_protector": None,
        "invalidation": None,
    }

    # Redis缓存状态
    redis_manager = get_cache_manager()
    if redis_manager:
        status["redis_cache"] = redis_manager.get_statistics()
        health = redis_manager.health_check()
        status["redis_cache"]["healthy"] = health.get("healthy", False)

    # 设备缓存状态
    try:
        device_cache = get_device_cache_manager()
        status["device_cache"] = device_cache.get_statistics()
    except Exception as e:
        logger.error(f"Failed to get device cache stats: {e}")

    # 穿透保护状态
    try:
        protector = get_penetration_protector()
        status["penetration_protector"] = protector.get_statistics()
    except Exception as e:
        logger.error(f"Failed to get penetration protector stats: {e}")

    # 失效管理状态
    try:
        invalidation = get_invalidation_manager()
        status["invalidation"] = invalidation.get_statistics()
    except Exception as e:
        logger.error(f"Failed to get invalidation stats: {e}")

    return status


@router.get("/statistics")
async def get_cache_statistics() -> dict[str, Any]:
    """
    获取详细缓存统计信息。

    Returns:
        dict: 详细统计信息
    """
    try:
        return get_all_cache_stats()
    except Exception as e:
        logger.error(f"Failed to get cache statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/redis/health")
async def check_redis_health() -> dict[str, Any]:
    """
    检查Redis健康状态。

    Returns:
        dict: 健康检查结果
    """
    redis_manager = get_cache_manager()
    if not redis_manager:
        return {
            "healthy": False,
            "message": "Redis cache manager not initialized",
        }

    return redis_manager.health_check()


@router.get("/redis/statistics")
async def get_redis_statistics() -> dict[str, Any]:
    """
    获取Redis缓存统计信息。

    Returns:
        dict: Redis统计信息
    """
    redis_manager = get_cache_manager()
    if not redis_manager:
        raise HTTPException(status_code=503, detail="Redis cache not initialized")

    return redis_manager.get_statistics()


@router.get("/local/statistics")
async def get_local_cache_statistics() -> dict[str, Any]:
    """
    获取本地缓存统计信息。

    Returns:
        dict: 本地缓存统计
    """
    return get_all_local_cache_stats()


@router.post("/local/cleanup")
async def cleanup_local_cache() -> dict[str, Any]:
    """
    手动清理本地缓存过期条目。

    Returns:
        dict: 清理结果
    """
    from core.local_cache import (
        get_device_config_cache,
        get_device_status_cache,
        get_user_session_cache,
    )

    results = {
        "device_status": get_device_status_cache().cleanup(),
        "device_config": get_device_config_cache().cleanup(),
        "user_session": get_user_session_cache().cleanup(),
    }

    total_evicted = sum(results.values())
    logger.info(f"Manual cache cleanup: evicted {total_evicted} entries")

    return {
        "success": True,
        "evicted": results,
        "total_evicted": total_evicted,
    }


@router.post("/device/{device_id}/invalidate")
async def invalidate_device_cache(device_id: str) -> dict[str, Any]:
    """
    失效指定设备的所有缓存。

    Args:
        device_id: 设备ID

    Returns:
        dict: 操作结果
    """
    try:
        device_cache = get_device_cache_manager()
        await device_cache.invalidate_all_device_cache(device_id)

        logger.info(f"Invalidated all cache for device: {device_id}")

        return {
            "success": True,
            "device_id": device_id,
            "message": f"All cache invalidated for device {device_id}",
        }

    except Exception as e:
        logger.error(f"Failed to invalidate device cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/device/{device_id}/status/refresh")
async def refresh_device_status_cache(device_id: str) -> dict[str, Any]:
    """
    刷新设备状态缓存（标记为需要更新）。

    Args:
        device_id: 设备ID

    Returns:
        dict: 操作结果
    """
    try:
        device_cache = get_device_cache_manager()
        await device_cache.invalidate_device_status(device_id)

        return {
            "success": True,
            "device_id": device_id,
            "message": f"Device status cache refreshed for {device_id}",
        }

    except Exception as e:
        logger.error(f"Failed to refresh device status cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/device/{device_id}/config/invalidate")
async def invalidate_device_config_cache(device_id: str) -> dict[str, Any]:
    """
    失效设备配置缓存。

    Args:
        device_id: 设备ID

    Returns:
        dict: 操作结果
    """
    try:
        device_cache = get_device_cache_manager()
        await device_cache.invalidate_device_config(device_id)

        logger.info(f"Invalidated config cache for device: {device_id}")

        return {
            "success": True,
            "device_id": device_id,
            "message": f"Config cache invalidated for device {device_id}",
        }

    except Exception as e:
        logger.error(f"Failed to invalidate device config cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/invalidation/events")
async def get_invalidation_events(count: int = 100) -> dict[str, Any]:
    """
    获取最近的缓存失效事件。

    Args:
        count: 返回事件数量

    Returns:
        dict: 失效事件列表
    """
    try:
        manager = get_invalidation_manager()
        events = manager.get_recent_events(count)

        return {
            "count": len(events),
            "events": [
                {
                    "event_type": e.event_type.value,
                    "cache_key": e.cache_key,
                    "device_id": e.device_id,
                    "timestamp": e.timestamp.isoformat(),
                    "reason": e.reason,
                }
                for e in events
            ],
        }

    except Exception as e:
        logger.error(f"Failed to get invalidation events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/penetration/statistics")
async def get_penetration_statistics() -> dict[str, Any]:
    """
    获取缓存穿透保护统计信息。

    Returns:
        dict: 穿透保护统计
    """
    try:
        protector = get_penetration_protector()
        return protector.get_statistics()
    except Exception as e:
        logger.error(f"Failed to get penetration statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear")
async def clear_all_cache() -> dict[str, Any]:
    """
    清空所有缓存（谨慎使用）。

    Returns:
        dict: 操作结果
    """
    from core.local_cache import (
        get_device_config_cache,
        get_device_status_cache,
        get_user_session_cache,
    )

    results = {
        "redis": False,
        "local_device_status": False,
        "local_device_config": False,
        "local_user_session": False,
    }

    # 清空Redis缓存
    redis_manager = get_cache_manager()
    if redis_manager:
        results["redis"] = redis_manager.clear()

    # 清空本地缓存
    get_device_status_cache().clear()
    results["local_device_status"] = True

    get_device_config_cache().clear()
    results["local_device_config"] = True

    get_user_session_cache().clear()
    results["local_user_session"] = True

    logger.warning("All cache cleared")

    return {
        "success": True,
        "results": results,
        "message": "All cache cleared successfully",
    }
