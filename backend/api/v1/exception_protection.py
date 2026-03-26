"""
文件名: exception_protection.py
路径: backend/api/v1/
功能: 设备异常分级保护API路由，提供异常事件查询、统计、解决等接口
版本: v1.0
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: fastapi, schemas, core.exception_protection
安全约束: 所有异常操作必须记录审计日志，高危操作必须包含二次校验
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Path, Query, Body

from schemas.api import ApiResponse, ApiError

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== 异常事件查询API ====================

@router.get(
    "/events",
    response_model=ApiResponse[list[dict]],
    summary="查询异常事件列表",
    description="根据条件查询异常事件列表，支持按设备、等级、类型、时间等过滤。",
)
async def query_exception_events(
    device_id: str | None = Query(default=None, description="设备ID过滤"),
    exception_level: str | None = Query(default=None, description="异常等级过滤（warning/alarm/fatal）"),
    exception_type: str | None = Query(default=None, description="异常类型过滤"),
    resolved: bool | None = Query(default=None, description="是否已解决过滤"),
    start_time: float | None = Query(default=None, description="开始时间戳（秒）"),
    end_time: float | None = Query(default=None, description="结束时间戳（秒）"),
    limit: int = Query(default=100, ge=1, le=1000, description="返回记录数限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
) -> ApiResponse[list[dict]]:
    """
    查询异常事件列表。
    
    支持多条件组合查询，返回符合条件的异常事件列表。
    
    Args:
        device_id: 设备ID过滤，None表示不过滤
        exception_level: 异常等级过滤（warning/alarm/fatal）
        exception_type: 异常类型过滤
        resolved: 是否已解决过滤，None表示不过滤
        start_time: 开始时间戳（秒）
        end_time: 结束时间戳（秒）
        limit: 返回记录数限制，默认100，最大1000
        offset: 偏移量，默认0
    
    Returns:
        ApiResponse[List[dict]]: 包含异常事件列表的响应
    
    Example:
        >>> # 查询motor_01设备的未解决异常
        >>> response = await query_exception_events(
        ...     device_id="motor_01",
        ...     resolved=False
        ... )
        >>> for event in response.data:
        ...     print(f"{event['exception_level']}: {event['message']}")
    """
    from core.exception_protection import (
        ExceptionProtectionManager,
        ExceptionLevel,
        ExceptionType,
    )
    
    try:
        # 获取异常保护管理器实例
        manager = ExceptionProtectionManager()
        
        # 转换枚举参数
        level_enum = None
        if exception_level:
            level_enum = ExceptionLevel.from_string(exception_level)
        
        type_enum = None
        if exception_type:
            type_enum = ExceptionType(exception_type)
        
        # 查询事件
        events = manager.query_events(
            device_id=device_id,
            exception_level=level_enum,
            exception_type=type_enum,
            resolved=resolved,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )
        
        # 序列化结果
        events_data = [event.to_dict() for event in events]
        
        return ApiResponse.ok(
            data=events_data,
            message=f"查询到 {len(events_data)} 条异常事件"
        )
        
    except ValueError as e:
        logger.warning(f"参数校验失败: {str(e)}")
        return ApiResponse.error(
            message=f"参数校验失败: {str(e)}",
            error_code="E4001",
            details={"error": str(e)}
        )
    except Exception as e:
        logger.error(f"查询异常事件失败: {str(e)}")
        return ApiResponse.error(
            message=f"查询异常事件失败: {str(e)}",
            error_code="E5001",
            details={"error": str(e)}
        )


@router.get(
    "/events/{event_id}",
    response_model=ApiResponse[dict],
    summary="查询异常事件详情",
    description="根据事件ID获取异常事件的详细信息。",
)
async def get_exception_event(
    event_id: str = Path(..., description="事件唯一标识"),
) -> ApiResponse[dict]:
    """
    获取异常事件详情。
    
    Args:
        event_id: 事件唯一标识
    
    Returns:
        ApiResponse[dict]: 包含异常事件详情的响应
    
    Raises:
        HTTPException: 事件不存在时返回404
    """
    from core.exception_protection import ExceptionProtectionManager
    
    try:
        manager = ExceptionProtectionManager()
        
        # 通过event_id查询（使用offset=0, limit=1000遍历查找）
        # 注意：实际项目中应该添加按event_id查询的方法
        events = manager.query_events(limit=1000)
        
        for event in events:
            if event.event_id == event_id:
                return ApiResponse.ok(data=event.to_dict())
        
        return ApiResponse.error(
            message=f"异常事件不存在: {event_id}",
            error_code="E4004",
            details={"event_id": event_id}
        )
        
    except Exception as e:
        logger.error(f"查询异常事件详情失败: event_id={event_id}, error={str(e)}")
        return ApiResponse.error(
            message=f"查询异常事件详情失败: {str(e)}",
            error_code="E5001",
            details={"event_id": event_id, "error": str(e)}
        )


@router.post(
    "/events/{event_id}/resolve",
    response_model=ApiResponse[dict],
    summary="解决异常事件",
    description="标记异常事件为已解决，需要提供解决方式描述。",
)
async def resolve_exception_event(
    event_id: str = Path(..., description="事件唯一标识"),
    resolved_by: str = Body(..., description="解决方式描述"),
    confirmation: str = Body(..., description="二次确认字符串，必须输入'CONFIRM_RESOLVE'"),
) -> ApiResponse[dict]:
    """
    解决异常事件。
    
    标记异常事件为已解决状态，需要提供解决方式描述和二次确认。
    
    Args:
        event_id: 事件唯一标识
        resolved_by: 解决方式描述
        confirmation: 二次确认字符串，必须输入"CONFIRM_RESOLVE"
    
    Returns:
        ApiResponse[dict]: 包含解决结果的响应
    
    安全约束:
        1. 必须进行二次确认
        2. 所有解决操作记录审计日志
    """
    from core.exception_protection import ExceptionProtectionManager
    
    # 二次确认校验
    if confirmation != "CONFIRM_RESOLVE":
        logger.warning(
            f"[EXCEPTION_RESOLVE] 二次确认失败: event_id={event_id}, "
            f"confirmation={confirmation}"
        )
        return ApiResponse.error(
            message="二次确认失败，请输入'CONFIRM_RESOLVE'",
            error_code="E4002",
            details={"event_id": event_id}
        )
    
    logger.info(
        f"[EXCEPTION_RESOLVE] 收到异常解决请求: event_id={event_id}, "
        f"resolved_by={resolved_by}"
    )
    
    try:
        manager = ExceptionProtectionManager()
        
        success = manager.resolve_event(event_id, resolved_by)
        
        if success:
            logger.info(f"[EXCEPTION_RESOLVE] 异常解决成功: event_id={event_id}")
            return ApiResponse.ok(
                data={
                    "event_id": event_id,
                    "resolved_by": resolved_by,
                    "resolved_at": datetime.utcnow().isoformat(),
                    "message": "异常事件已标记为已解决",
                }
            )
        else:
            logger.warning(f"[EXCEPTION_RESOLVE] 异常解决失败: event_id={event_id}")
            return ApiResponse.error(
                message=f"异常事件不存在或已解决: {event_id}",
                error_code="E4004",
                details={"event_id": event_id}
            )
            
    except Exception as e:
        logger.error(
            f"[EXCEPTION_RESOLVE] 异常解决异常: event_id={event_id}, error={str(e)}"
        )
        return ApiResponse.error(
            message=f"异常解决失败: {str(e)}",
            error_code="E5002",
            details={"event_id": event_id, "error": str(e)}
        )


# ==================== 异常统计API ====================

@router.get(
    "/statistics",
    response_model=ApiResponse[dict],
    summary="获取异常统计信息",
    description="获取异常事件的统计信息，包括总数、按等级/类型/设备分布等。",
)
async def get_exception_statistics(
    start_time: float | None = Query(default=None, description="开始时间戳（秒）"),
    end_time: float | None = Query(default=None, description="结束时间戳（秒）"),
) -> ApiResponse[dict]:
    """
    获取异常统计信息。
    
    返回异常事件的统计数据，包括：
    - 总数统计
    - 按等级分布
    - 按类型分布
    - 按设备分布（Top 10）
    - 未解决数量
    
    Args:
        start_time: 开始时间戳（秒），None表示从最早记录开始
        end_time: 结束时间戳（秒），None表示到当前时间
    
    Returns:
        ApiResponse[dict]: 包含统计信息的响应
    
    Example:
        >>> response = await get_exception_statistics()
        >>> print(f"总异常数: {response.data['total_count']}")
        >>> print(f"未解决数: {response.data['unresolved_count']}")
    """
    from core.exception_protection import ExceptionProtectionManager
    
    try:
        manager = ExceptionProtectionManager()
        statistics = manager.get_statistics(start_time, end_time)
        
        return ApiResponse.ok(data=statistics)
        
    except Exception as e:
        logger.error(f"获取异常统计信息失败: {str(e)}")
        return ApiResponse.error(
            message=f"获取异常统计信息失败: {str(e)}",
            error_code="E5003",
            details={"error": str(e)}
        )


# ==================== 设备异常配置API ====================

@router.get(
    "/devices/{device_id}/config",
    response_model=ApiResponse[dict],
    summary="获取设备异常配置",
    description="获取指定设备的异常检测和保护配置。",
)
async def get_device_exception_config(
    device_id: str = Path(..., description="设备唯一标识"),
) -> ApiResponse[dict]:
    """
    获取设备异常配置。
    
    Args:
        device_id: 设备唯一标识
    
    Returns:
        ApiResponse[dict]: 包含设备异常配置的响应
    """
    from core.exception_protection import ExceptionProtectionManager
    
    try:
        manager = ExceptionProtectionManager()
        config = manager.get_device_config(device_id)
        
        if config is None:
            return ApiResponse.error(
                message=f"设备异常配置不存在: {device_id}",
                error_code="E4004",
                details={"device_id": device_id}
            )
        
        return ApiResponse.ok(data=config.to_dict())
        
    except Exception as e:
        logger.error(f"获取设备异常配置失败: device_id={device_id}, error={str(e)}")
        return ApiResponse.error(
            message=f"获取设备异常配置失败: {str(e)}",
            error_code="E5004",
            details={"device_id": device_id, "error": str(e)}
        )


@router.put(
    "/devices/{device_id}/config",
    response_model=ApiResponse[dict],
    summary="更新设备异常配置",
    description="更新指定设备的异常检测和保护配置。",
)
async def update_device_exception_config(
    device_id: str = Path(..., description="设备唯一标识"),
    enabled: bool = Body(default=True, description="是否启用异常保护"),
    auto_recovery: bool = Body(default=True, description="是否启用自动恢复"),
    recovery_delay: float = Body(default=5.0, ge=0, description="恢复延迟时间（秒）"),
    max_recovery_attempts: int = Body(default=3, ge=1, le=10, description="最大恢复尝试次数"),
    warning_thresholds: dict[str, float] = Body(default_factory=dict, description="预警阈值字典"),
    alarm_thresholds: dict[str, float] = Body(default_factory=dict, description="报警阈值字典"),
    fatal_thresholds: dict[str, float] = Body(default_factory=dict, description="致命故障阈值字典"),
) -> ApiResponse[dict]:
    """
    更新设备异常配置。
    
    Args:
        device_id: 设备唯一标识
        enabled: 是否启用异常保护
        auto_recovery: 是否启用自动恢复
        recovery_delay: 恢复延迟时间（秒）
        max_recovery_attempts: 最大恢复尝试次数
        warning_thresholds: 预警阈值字典
        alarm_thresholds: 报警阈值字典
        fatal_thresholds: 致命故障阈值字典
    
    Returns:
        ApiResponse[dict]: 包含更新结果的响应
    """
    from core.exception_protection import (
        ExceptionProtectionManager,
        DeviceExceptionConfig,
    )
    
    logger.info(f"[EXCEPTION_CONFIG] 更新设备异常配置: device_id={device_id}")
    
    try:
        manager = ExceptionProtectionManager()
        
        # 获取现有配置
        config = manager.get_device_config(device_id)
        if config is None:
            return ApiResponse.error(
                message=f"设备异常配置不存在: {device_id}",
                error_code="E4004",
                details={"device_id": device_id}
            )
        
        # 更新配置
        config.enabled = enabled
        config.auto_recovery = auto_recovery
        config.recovery_delay = recovery_delay
        config.max_recovery_attempts = max_recovery_attempts
        config.warning_thresholds = warning_thresholds
        config.alarm_thresholds = alarm_thresholds
        config.fatal_thresholds = fatal_thresholds
        
        logger.info(
            f"[EXCEPTION_CONFIG] 设备异常配置已更新: device_id={device_id}, "
            f"enabled={enabled}, auto_recovery={auto_recovery}"
        )
        
        return ApiResponse.ok(
            data=config.to_dict(),
            message="设备异常配置更新成功"
        )
        
    except Exception as e:
        logger.error(f"更新设备异常配置失败: device_id={device_id}, error={str(e)}")
        return ApiResponse.error(
            message=f"更新设备异常配置失败: {str(e)}",
            error_code="E5005",
            details={"device_id": device_id, "error": str(e)}
        )


# ==================== 设备重连API ====================

@router.post(
    "/devices/{device_id}/reconnect",
    response_model=ApiResponse[dict],
    summary="触发设备重连",
    description="手动触发设备的重连操作，用于通信中断后的恢复。",
)
async def trigger_device_reconnect(
    device_id: str = Path(..., description="设备唯一标识"),
    delay: float = Query(default=0.0, ge=0, description="延迟时间（秒）"),
    confirmation: str = Body(..., description="二次确认字符串，必须输入'CONFIRM_RECONNECT'"),
) -> ApiResponse[dict]:
    """
    触发设备重连。
    
    手动触发设备的重连操作，用于通信中断后的恢复。
    如果设备配置了自动恢复，系统会自动尝试重连。
    
    Args:
        device_id: 设备唯一标识
        delay: 延迟时间（秒），默认0立即执行
        confirmation: 二次确认字符串，必须输入"CONFIRM_RECONNECT"
    
    Returns:
        ApiResponse[dict]: 包含重连结果的响应
    
    安全约束:
        1. 必须进行二次确认
        2. 重连操作记录审计日志
    """
    from core.exception_protection import ExceptionProtectionManager
    
    # 二次确认校验
    if confirmation != "CONFIRM_RECONNECT":
        logger.warning(
            f"[DEVICE_RECONNECT] 二次确认失败: device_id={device_id}, "
            f"confirmation={confirmation}"
        )
        return ApiResponse.error(
            message="二次确认失败，请输入'CONFIRM_RECONNECT'",
            error_code="E4002",
            details={"device_id": device_id}
        )
    
    logger.info(
        f"[DEVICE_RECONNECT] 收到设备重连请求: device_id={device_id}, delay={delay}"
    )
    
    try:
        manager = ExceptionProtectionManager()
        
        # 调度重连任务
        await manager.schedule_reconnect(device_id, delay)
        
        return ApiResponse.ok(
            data={
                "device_id": device_id,
                "delay": delay,
                "message": "设备重连任务已调度",
            }
        )
        
    except Exception as e:
        logger.error(f"设备重连失败: device_id={device_id}, error={str(e)}")
        return ApiResponse.error(
            message=f"设备重连失败: {str(e)}",
            error_code="E5006",
            details={"device_id": device_id, "error": str(e)}
        )


# ==================== 异常等级与类型定义API ====================

@router.get(
    "/levels",
    response_model=ApiResponse[list[dict]],
    summary="获取异常等级定义",
    description="获取所有异常等级的定义和对应的保护动作。",
)
async def get_exception_levels() -> ApiResponse[list[dict]]:
    """
    获取异常等级定义。
    
    Returns:
        ApiResponse[List[dict]]: 包含异常等级定义的响应
    
    Example:
        >>> response = await get_exception_levels()
        >>> for level in response.data:
        ...     print(f"{level['name']}: {level['description']}")
    """
    from core.exception_protection import ExceptionLevel, ProtectionAction
    
    levels_data = []
    
    for level in ExceptionLevel:
        actions = ProtectionAction.get_actions_for_level(level)
        levels_data.append({
            "name": level.value,
            "description": {
                ExceptionLevel.WARNING: "预警等级，需要关注但不影响设备运行",
                ExceptionLevel.ALARM: "报警等级，需要采取保护措施（降额/停机）",
                ExceptionLevel.FATAL: "致命故障等级，触发全局急停",
            }.get(level, ""),
            "actions": [action.value for action in actions],
        })
    
    return ApiResponse.ok(data=levels_data)


@router.get(
    "/types",
    response_model=ApiResponse[list[dict]],
    summary="获取异常类型定义",
    description="获取所有异常类型的定义和默认等级。",
)
async def get_exception_types() -> ApiResponse[list[dict]]:
    """
    获取异常类型定义。
    
    Returns:
        ApiResponse[List[dict]]: 包含异常类型定义的响应
    """
    from core.exception_protection import ExceptionType
    
    types_data = []
    
    for exc_type in ExceptionType:
        default_level = ExceptionType.get_default_level(exc_type)
        types_data.append({
            "name": exc_type.value,
            "default_level": default_level.value,
            "description": {
                ExceptionType.MOTOR_ALARM: "步进电机报警",
                ExceptionType.ELECTROMAGNET_OVERCURRENT: "电磁铁过流",
                ExceptionType.ELECTROMAGNET_OVERTEMPERATURE: "电磁铁过温",
                ExceptionType.TEMPERATURE_CONTROLLER_OVERTEMP: "温控器超温",
                ExceptionType.PICOAMMETER_COMM_ERROR: "皮安表通信异常",
                ExceptionType.PIEZO_CONTROLLER_FAULT: "压电控制器故障",
                ExceptionType.COMMUNICATION_INTERRUPT: "通信中断",
                ExceptionType.SERIAL_DISCONNECT: "串口断连",
                ExceptionType.DEVICE_TIMEOUT: "设备超时",
                ExceptionType.UNKNOWN: "未知异常",
            }.get(exc_type, ""),
        })
    
    return ApiResponse.ok(data=types_data)


# ==================== 保护动作定义API ====================

@router.get(
    "/actions",
    response_model=ApiResponse[list[dict]],
    summary="获取保护动作定义",
    description="获取所有保护动作的定义和说明。",
)
async def get_protection_actions() -> ApiResponse[list[dict]]:
    """
    获取保护动作定义。
    
    Returns:
        ApiResponse[List[dict]]: 包含保护动作定义的响应
    """
    from core.exception_protection import ProtectionAction
    
    actions_data = []
    
    for action in ProtectionAction:
        actions_data.append({
            "name": action.value,
            "description": {
                ProtectionAction.LOG_ONLY: "仅记录日志，不执行其他动作",
                ProtectionAction.NOTIFY: "发送告警通知",
                ProtectionAction.DERATE: "降额运行（降低设备参数）",
                ProtectionAction.SINGLE_STOP: "单设备停机",
                ProtectionAction.GLOBAL_ESTOP: "全局急停（停止所有设备）",
            }.get(action, ""),
        })
    
    return ApiResponse.ok(data=actions_data)
