"""
文件名: logging_config.py
路径: backend/core/logging/
功能: 分级日志体系，支持系统运行日志、硬件通信日志、设备操作日志、安全事件日志
版本: v2.0
创建日期: 2026-03-15
最后更新: 2026-03-25
作者: Backend Engineer Agent

依赖:
    - structlog>=24.0.0
    - core.config (settings)

安全约束:
    - 敏感信息自动脱敏
    - 日志文件权限控制
    - 日志轮转防止磁盘占满
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Set
from datetime import datetime, UTC
from enum import Enum

try:
    import structlog
    from structlog.types import Processor
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False

from core.config import settings


class LogCategory(str, Enum):
    """日志分类枚举。"""
    SYSTEM = "system"  # 系统运行日志
    DEVICE = "device"  # 设备操作日志
    COMMUNICATION = "communication"  # 硬件通信日志
    SECURITY = "security"  # 安全事件日志
    PERFORMANCE = "performance"  # 性能监控日志
    AUDIT = "audit"  # 审计日志


class LogLevel(str, Enum):
    """日志级别枚举。"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    FATAL = "FATAL"


# 敏感字段集合
SENSITIVE_FIELDS: Set[str] = {
    "password", "token", "secret", "key", "authorization",
    "jwt", "credential", "api_key", "access_token", "refresh_token",
    "private_key", "session_id", "cookie"
}


def mask_sensitive_data(data: Any, sensitive_fields: Set[str] = None) -> Any:
    """
    脱敏敏感数据。

    Args:
        data: 原始数据
        sensitive_fields: 敏感字段名集合

    Returns:
        Any: 脱敏后的数据
    """
    if sensitive_fields is None:
        sensitive_fields = SENSITIVE_FIELDS
    
    if isinstance(data, dict):
        masked_dict = {}
        for key, value in data.items():
            if key.lower() in sensitive_fields:
                masked_dict[key] = "***MASKED***"
            elif isinstance(value, (dict, list)):
                masked_dict[key] = mask_sensitive_data(value, sensitive_fields)
            else:
                masked_dict[key] = value
        return masked_dict
    elif isinstance(data, list):
        return [mask_sensitive_data(item, sensitive_fields) for item in data]
    elif isinstance(data, str):
        # 检查字符串中是否包含敏感信息
        for field in sensitive_fields:
            if field in data.lower():
                return "***MASKED***"
        return data
    else:
        return data


def add_app_context(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any]
) -> dict[str, Any]:
    """
    添加应用上下文信息。

    为每条日志记录添加应用名称、版本和环境信息。

    Args:
        logger: 日志器实例
        method_name: 方法名称
        event_dict: 事件字典

    Returns:
        Dict[str, Any]: 添加了上下文信息的事件字典

    Example:
        日志输出将包含：
        {
            "event": "device_connected",
            "app": "CAUC-SEP",
            "version": "0.4.0",
            "env": "development",
            ...
        }
    """
    event_dict["app"] = settings.app_name
    event_dict["version"] = settings.app_version
    event_dict["env"] = settings.app_env
    return event_dict


def add_log_category(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any]
) -> dict[str, Any]:
    """
    添加日志分类信息。

    Args:
        logger: 日志器实例
        method_name: 方法名称
        event_dict: 事件字典

    Returns:
        Dict[str, Any]: 添加了分类信息的事件字典
    """
    # 从logger名称推断分类
    logger_name = event_dict.get("logger", "")
    
    if "device" in logger_name.lower() or "motor" in logger_name.lower():
        event_dict["category"] = LogCategory.DEVICE.value
    elif "comm" in logger_name.lower() or "modbus" in logger_name.lower() or "serial" in logger_name.lower():
        event_dict["category"] = LogCategory.COMMUNICATION.value
    elif "security" in logger_name.lower() or "auth" in logger_name.lower():
        event_dict["category"] = LogCategory.SECURITY.value
    elif "performance" in logger_name.lower():
        event_dict["category"] = LogCategory.PERFORMANCE.value
    elif "audit" in logger_name.lower():
        event_dict["category"] = LogCategory.AUDIT.value
    else:
        event_dict["category"] = LogCategory.SYSTEM.value
    
    return event_dict


def mask_sensitive_processor(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any]
) -> dict[str, Any]:
    """
    敏感信息脱敏处理器。

    Args:
        logger: 日志器实例
        method_name: 方法名称
        event_dict: 事件字典

    Returns:
        Dict[str, Any]: 脱敏后的事件字典
    """
    return mask_sensitive_data(event_dict)


class CategoryBasedFormatter(logging.Formatter):
    """
    基于分类的日志格式化器。
    
    根据日志分类使用不同的格式和输出目标。
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        格式化日志记录。

        Args:
            record: 日志记录对象

        Returns:
            str: 格式化后的日志字符串
        """
        # 添加分类信息
        if not hasattr(record, 'category'):
            record.category = LogCategory.SYSTEM.value
        
        # 调用父类格式化方法
        return super().format(record)


def setup_logging(
    log_dir: str = None,
    max_bytes: int = None,
    backup_count: int = None,
    level: int = None,
    json_format: bool = None,
    compress_logs: bool = False,
) -> Any:
    """
    配置分级日志体系。

    Args:
        log_dir: 日志目录路径，默认使用settings配置
        max_bytes: 单个日志文件最大字节数，默认使用settings配置
        backup_count: 备份文件数量，默认使用settings配置
        level: 日志级别，默认使用settings配置
        json_format: 是否使用JSON格式，默认使用settings配置
        compress_logs: 是否压缩旧日志文件

    Returns:
        配置好的日志器实例

    Example:
        >>> logger = setup_logging()
        >>> logger.info("device_connected", device_id="stepper_01", port="COM3")
    """
    if not STRUCTLOG_AVAILABLE:
        logging.warning(
            "structlog not available, falling back to standard logging"
        )
        return setup_standard_logging(
            log_dir=log_dir or settings.log_dir,
            max_bytes=max_bytes or settings.log_max_bytes,
            backup_count=backup_count or settings.log_backup_count,
            level=level or getattr(logging, settings.log_level.upper()),
        )
    
    _log_dir = Path(log_dir or settings.log_dir)
    _log_dir.mkdir(parents=True, exist_ok=True)
    
    _max_bytes = max_bytes or settings.log_max_bytes
    _backup_count = backup_count or settings.log_backup_count
    _level = level or getattr(logging, settings.log_level.upper())
    _json_format = json_format if json_format is not None else settings.log_json_format
    
    # 共享处理器
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        add_app_context,
        add_log_category,
        mask_sensitive_processor,  # 敏感信息脱敏
    ]
    
    # 根据环境选择渲染器
    if _json_format or settings.is_production:
        renderer = structlog.processors.JSONRenderer(ensure_ascii=False)
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    
    # 配置structlog
    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )
    
    # ==================== 创建分类日志文件处理器 ====================
    
    # 1. 系统运行日志（所有级别）
    system_handler = logging.handlers.RotatingFileHandler(
        _log_dir / "system.log",
        maxBytes=_max_bytes,
        backupCount=_backup_count,
        encoding="utf-8",
    )
    system_handler.setFormatter(formatter)
    system_handler.setLevel(logging.DEBUG)
    
    # 2. 设备操作日志
    device_handler = logging.handlers.RotatingFileHandler(
        _log_dir / "device.log",
        maxBytes=_max_bytes,
        backupCount=_backup_count,
        encoding="utf-8",
    )
    device_handler.setFormatter(formatter)
    device_handler.setLevel(logging.DEBUG)
    # 添加分类过滤器
    device_handler.addFilter(lambda record: getattr(record, 'category', '') == LogCategory.DEVICE.value)
    
    # 3. 硬件通信日志
    comm_handler = logging.handlers.RotatingFileHandler(
        _log_dir / "communication.log",
        maxBytes=_max_bytes,
        backupCount=_backup_count,
        encoding="utf-8",
    )
    comm_handler.setFormatter(formatter)
    comm_handler.setLevel(logging.DEBUG)
    comm_handler.addFilter(lambda record: getattr(record, 'category', '') == LogCategory.COMMUNICATION.value)
    
    # 4. 安全事件日志
    security_handler = logging.handlers.RotatingFileHandler(
        _log_dir / "security.log",
        maxBytes=_max_bytes,
        backupCount=_backup_count,
        encoding="utf-8",
    )
    security_handler.setFormatter(formatter)
    security_handler.setLevel(logging.INFO)  # 安全日志从INFO级别开始
    security_handler.addFilter(lambda record: getattr(record, 'category', '') == LogCategory.SECURITY.value)
    
    # 5. 性能监控日志
    performance_handler = logging.handlers.RotatingFileHandler(
        _log_dir / "performance.log",
        maxBytes=_max_bytes,
        backupCount=_backup_count,
        encoding="utf-8",
    )
    performance_handler.setFormatter(formatter)
    performance_handler.setLevel(logging.INFO)
    performance_handler.addFilter(lambda record: getattr(record, 'category', '') == LogCategory.PERFORMANCE.value)
    
    # 6. 审计日志
    audit_handler = logging.handlers.RotatingFileHandler(
        _log_dir / "audit.log",
        maxBytes=_max_bytes,
        backupCount=_backup_count,
        encoding="utf-8",
    )
    audit_handler.setFormatter(formatter)
    audit_handler.setLevel(logging.INFO)
    audit_handler.addFilter(lambda record: getattr(record, 'category', '') == LogCategory.AUDIT.value)
    
    # 7. 错误日志（ERROR及以上）
    error_handler = logging.handlers.RotatingFileHandler(
        _log_dir / "error.log",
        maxBytes=_max_bytes,
        backupCount=_backup_count,
        encoding="utf-8",
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    
    # 8. 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # ==================== 配置根日志器 ====================
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # 添加所有处理器
    root_logger.addHandler(console_handler)
    root_logger.addHandler(system_handler)
    root_logger.addHandler(device_handler)
    root_logger.addHandler(comm_handler)
    root_logger.addHandler(security_handler)
    root_logger.addHandler(performance_handler)
    root_logger.addHandler(audit_handler)
    root_logger.addHandler(error_handler)
    
    # 设置日志级别
    root_logger.setLevel(_level)
    
    # 降低第三方库日志级别
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    return structlog.get_logger()


def setup_standard_logging(
    log_dir: str = None,
    max_bytes: int = None,
    backup_count: int = None,
    level: int = None,
) -> logging.Logger:
    """
    配置标准日志（structlog不可用时的回退方案）。

    Args:
        log_dir: 日志目录路径
        max_bytes: 单个日志文件最大字节数
        backup_count: 备份文件数量
        level: 日志级别

    Returns:
        logging.Logger: 标准日志器实例
    """
    _log_dir = Path(log_dir or settings.log_dir)
    _log_dir.mkdir(parents=True, exist_ok=True)
    
    _max_bytes = max_bytes or settings.log_max_bytes
    _backup_count = backup_count or settings.log_backup_count
    _level = level or getattr(logging, settings.log_level.upper())
    
    # 创建格式化器
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # 创建文件处理器
    file_handler = logging.handlers.RotatingFileHandler(
        _log_dir / "app.log",
        maxBytes=_max_bytes,
        backupCount=_backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(_level)
    
    return root_logger


def get_logger(name: str | None = None, category: LogCategory = None) -> Any:
    """
    获取日志器。

    如果 structlog 可用，返回 structlog 日志器；
    否则返回标准 logging 日志器。

    Args:
        name: 日志器名称，通常使用 __name__
        category: 日志分类，可选

    Returns:
        日志器实例

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("operation_started", operation="move_motor")
        
        >>> # 指定日志分类
        >>> device_logger = get_logger(__name__, category=LogCategory.DEVICE)
        >>> device_logger.info("motor_moved", position=1000)
    """
    if STRUCTLOG_AVAILABLE:
        logger_instance = structlog.get_logger(name)
        if category:
            # 绑定分类信息
            return logger_instance.bind(category=category.value)
        return logger_instance
    else:
        logger_instance = logging.getLogger(name)
        if category:
            # 为标准日志器添加分类属性
            old_factory = logging.getLogRecordFactory()
            
            def record_factory(*args, **kwargs):
                record = old_factory(*args, **kwargs)
                record.category = category.value
                return record
            
            logging.setLogRecordFactory(record_factory)
        
        return logger_instance


def log_device_operation(
    device_id: str,
    operation: str,
    params: Dict[str, Any] = None,
    result: str = "success",
    error: str = None
) -> None:
    """
    记录设备操作日志。

    Args:
        device_id: 设备ID
        operation: 操作名称
        params: 操作参数
        result: 操作结果
        error: 错误信息（可选）
    """
    logger = get_logger("device", category=LogCategory.DEVICE)
    
    log_data = {
        "device_id": device_id,
        "operation": operation,
        "result": result,
    }
    
    if params:
        log_data["params"] = mask_sensitive_data(params)
    
    if error:
        log_data["error"] = error
        logger.error("device_operation_failed", **log_data)
    else:
        logger.info("device_operation_completed", **log_data)


def log_communication(
    device_id: str,
    direction: str,
    data: Any,
    protocol: str = "modbus",
    success: bool = True
) -> None:
    """
    记录硬件通信日志。

    Args:
        device_id: 设备ID
        direction: 通信方向（send/receive）
        data: 通信数据
        protocol: 通信协议
        success: 是否成功
    """
    logger = get_logger("communication", category=LogCategory.COMMUNICATION)
    
    log_data = {
        "device_id": device_id,
        "direction": direction,
        "protocol": protocol,
        "success": success,
        "data": mask_sensitive_data(data),
    }
    
    if success:
        logger.debug("communication_success", **log_data)
    else:
        logger.warning("communication_failed", **log_data)


def log_security_event(
    event_type: str,
    user_id: str = None,
    ip_address: str = None,
    details: Dict[str, Any] = None,
    severity: LogLevel = LogLevel.INFO
) -> None:
    """
    记录安全事件日志。

    Args:
        event_type: 事件类型
        user_id: 用户ID（可选）
        ip_address: IP地址（可选）
        details: 事件详情
        severity: 严重程度
    """
    logger = get_logger("security", category=LogCategory.SECURITY)
    
    log_data = {
        "event_type": event_type,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    
    if user_id:
        log_data["user_id"] = user_id
    
    if ip_address:
        log_data["ip_address"] = ip_address
    
    if details:
        log_data["details"] = mask_sensitive_data(details)
    
    # 根据严重程度选择日志方法
    if severity == LogLevel.DEBUG:
        logger.debug("security_event", **log_data)
    elif severity == LogLevel.INFO:
        logger.info("security_event", **log_data)
    elif severity == LogLevel.WARNING:
        logger.warning("security_event", **log_data)
    elif severity == LogLevel.ERROR:
        logger.error("security_event", **log_data)
    elif severity in (LogLevel.CRITICAL, LogLevel.FATAL):
        logger.critical("security_event", **log_data)


def log_performance_metric(
    metric_name: str,
    value: float,
    unit: str = None,
    tags: Dict[str, str] = None
) -> None:
    """
    记录性能监控日志。

    Args:
        metric_name: 指标名称
        value: 指标值
        unit: 单位（可选）
        tags: 标签（可选）
    """
    logger = get_logger("performance", category=LogCategory.PERFORMANCE)
    
    log_data = {
        "metric_name": metric_name,
        "value": value,
    }
    
    if unit:
        log_data["unit"] = unit
    
    if tags:
        log_data["tags"] = tags
    
    logger.info("performance_metric", **log_data)


def log_audit_trail(
    action: str,
    resource_type: str,
    resource_id: str,
    user_id: str = None,
    changes: Dict[str, Any] = None
) -> None:
    """
    记录审计日志。

    Args:
        action: 操作类型（create/update/delete）
        resource_type: 资源类型
        resource_id: 资源ID
        user_id: 用户ID（可选）
        changes: 变更内容（可选）
    """
    logger = get_logger("audit", category=LogCategory.AUDIT)
    
    log_data = {
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    
    if user_id:
        log_data["user_id"] = user_id
    
    if changes:
        log_data["changes"] = mask_sensitive_data(changes)
    
    logger.info("audit_trail", **log_data)


def get_log_stats(log_dir: str = "logs") -> Dict[str, Any]:
    """
    获取日志统计信息。

    Args:
        log_dir: 日志目录路径

    Returns:
        Dict[str, Any]: 包含日志文件数量、总大小等统计信息
    """
    log_path = Path(log_dir)
    if not log_path.exists():
        return {
            "file_count": 0,
            "total_size_bytes": 0,
            "total_size_mb": 0.0,
            "files": [],
        }

    log_files = list(log_path.glob("*.log*"))
    total_size = sum(f.stat().st_size for f in log_files if f.is_file())

    return {
        "file_count": len(log_files),
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "files": [
            {
                "name": f.name,
                "size_bytes": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime, UTC).isoformat(),
            }
            for f in sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)
        ],
    }


def cleanup_old_logs(log_dir: str = "logs", max_age_days: int = 30) -> int:
    """
    清理过期的日志文件。

    Args:
        log_dir: 日志目录路径
        max_age_days: 最大保留天数

    Returns:
        int: 删除的文件数量
    """
    log_path = Path(log_dir)
    if not log_path.exists():
        return 0

    deleted_count = 0
    cutoff_time = datetime.now(UTC).timestamp() - (max_age_days * 24 * 60 * 60)

    for log_file in log_path.glob("*.log.*"):
        if log_file.is_file():
            try:
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    deleted_count += 1
            except OSError:
                pass

    return deleted_count


# 初始化日志器
logger = setup_logging()
