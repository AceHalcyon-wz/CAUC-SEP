"""
文件名: logging_config.py
路径: backend/core/
功能: 结构化日志配置
版本: v1.0
创建日期: 2026-03-15

依赖:
    - structlog>=24.0.0
    - core.config (settings)
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import structlog
    from structlog.types import Processor
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False

from core.config import settings


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


def setup_logging() -> Any:
    """
    配置结构化日志。

    创建完整的日志配置，包括：
    - 控制台输出（开发环境彩色，生产环境JSON）
    - 应用日志文件（所有级别）
    - 错误日志文件（ERROR及以上）
    - 第三方库日志级别控制

    Returns:
        配置好的日志器实例

    Example:
        >>> logger = setup_logging()
        >>> logger.info("device_connected", device_id="stepper_01", port="COM3")
    """
    if not STRUCTLOG_AVAILABLE:
        # 如果 structlog 不可用，回退到标准日志
        logging.warning(
            "structlog not available, falling back to standard logging"
        )
        return logging.getLogger()

    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        add_app_context,
    ]

    # 根据环境选择渲染器
    if settings.log_json_format or settings.is_production:
        renderer = structlog.processors.JSONRenderer(ensure_ascii=False)
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

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

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # 应用日志文件处理器
    file_handler = logging.FileHandler(
        log_dir / "app.log",
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    # 错误日志文件处理器
    error_handler = logging.FileHandler(
        log_dir / "error.log",
        encoding="utf-8",
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)

    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))

    # 降低第三方库日志级别
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)

    return structlog.get_logger()


def get_logger(name: str | None = None) -> Any:
    """
    获取日志器。

    如果 structlog 可用，返回 structlog 日志器；
    否则返回标准 logging 日志器。

    Args:
        name: 日志器名称，通常使用 __name__

    Returns:
        日志器实例

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("operation_started", operation="move_motor")
    """
    if STRUCTLOG_AVAILABLE:
        return structlog.get_logger(name)
    else:
        return logging.getLogger(name)


# 初始化日志器
logger = setup_logging()
