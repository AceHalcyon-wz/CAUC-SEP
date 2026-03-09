"""
日志配置模块。

支持日志轮转、归档和多级别日志输出，提供完整的日志管理功能。

功能：
    - 按大小轮转日志文件
    - 按时间轮转日志文件
    - 分级别日志输出（INFO/ERROR分离）
    - JSON格式日志支持
    - 日志压缩归档

作者：运维工程师 Agent
创建日期：2026-03-07
"""

import gzip
import json
import logging
import os
import shutil
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Optional


class JsonFormatter(logging.Formatter):
    """JSON格式日志格式化器。

    将日志记录格式化为JSON字符串，便于日志聚合系统解析。
    """

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为JSON。

        Args:
            record: 日志记录对象

        Returns:
            str: JSON格式的日志字符串
        """
        log_data: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # 添加额外字段
        if hasattr(record, "device_id"):
            log_data["device_id"] = record.device_id
        if hasattr(record, "experiment_id"):
            log_data["experiment_id"] = record.experiment_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id

        return json.dumps(log_data, ensure_ascii=False)


class CompressedRotatingFileHandler(RotatingFileHandler):
    """支持压缩的轮转文件处理器。

    在日志轮转时自动压缩旧日志文件，节省存储空间。
    """

    def doRollover(self) -> None:
        """执行日志轮转并压缩旧文件。"""
        if self.stream:
            self.stream.close()
            self.stream = None

        # 压缩并重命名旧日志文件
        for i in range(self.backupCount - 1, 0, -1):
            source = f"{self.baseFilename}.{i}.gz"
            dest = f"{self.baseFilename}.{i + 1}.gz"

            if os.path.exists(source):
                if os.path.exists(dest):
                    os.remove(dest)
                os.rename(source, dest)

        # 压缩当前日志文件
        if os.path.exists(self.baseFilename):
            compressed_file = f"{self.baseFilename}.1.gz"
            with open(self.baseFilename, "rb") as f_in:
                with gzip.open(compressed_file, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(self.baseFilename)

        # 创建新日志文件
        self.stream = self._open()


class DeviceLogFilter(logging.Filter):
    """设备日志过滤器。

    为日志记录添加设备相关上下文信息。
    """

    def __init__(self, device_id: Optional[str] = None):
        """初始化过滤器。

        Args:
            device_id: 设备ID，用于标识日志来源
        """
        super().__init__()
        self.device_id = device_id

    def filter(self, record: logging.LogRecord) -> bool:
        """过滤并增强日志记录。

        Args:
            record: 日志记录对象

        Returns:
            bool: 总是返回True，允许所有记录通过
        """
        if self.device_id and not hasattr(record, "device_id"):
            record.device_id = self.device_id
        return True


def setup_logging(
    log_dir: str = "logs",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    level: int = logging.INFO,
    json_format: bool = False,
    compress_logs: bool = True,
) -> logging.Logger:
    """配置日志轮转系统。

    创建完整的日志配置，包括控制台输出、文件轮转和错误日志分离。

    Args:
        log_dir: 日志目录路径
        max_bytes: 单个日志文件最大大小（字节）
        backup_count: 保留的日志文件数量
        level: 日志级别
        json_format: 是否使用JSON格式
        compress_logs: 是否压缩旧日志文件

    Returns:
        logging.Logger: 配置好的根日志器

    Example:
        >>> logger = setup_logging(log_dir="logs", max_bytes=10*1024*1024)
        >>> logger.info("服务启动完成")
    """
    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # 获取根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 清除现有处理器（避免重复添加）
    root_logger.handlers.clear()

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_format)

    # 主日志文件处理器
    if compress_logs:
        file_handler = CompressedRotatingFileHandler(
            log_path / "cauc_sep.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
    else:
        file_handler = RotatingFileHandler(
            log_path / "cauc_sep.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
    file_handler.setLevel(level)

    if json_format:
        file_handler.setFormatter(JsonFormatter())
    else:
        file_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_format)

    # 错误日志单独记录
    error_handler = RotatingFileHandler(
        log_path / "error.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_handler.formatter)

    # WebSocket日志（用于实时日志推送）
    ws_handler = RotatingFileHandler(
        log_path / "websocket.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    ws_handler.setLevel(logging.DEBUG)
    ws_handler.setFormatter(file_handler.formatter)

    # 添加处理器
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)

    # 配置第三方库日志级别（减少噪音）
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return root_logger


def setup_device_logging(
    device_id: str,
    log_dir: str = "logs",
    max_bytes: int = 5 * 1024 * 1024,  # 5MB
    backup_count: int = 3,
) -> logging.Logger:
    """为特定设备创建专用日志器。

    Args:
        device_id: 设备唯一标识
        log_dir: 日志目录路径
        max_bytes: 单个日志文件最大大小
        backup_count: 保留的日志文件数量

    Returns:
        logging.Logger: 设备专用日志器

    Example:
        >>> device_logger = setup_device_logging("stepper_01")
        >>> device_logger.info("电机启动")
    """
    # 创建设备日志目录
    device_log_path = Path(log_dir) / "devices"
    device_log_path.mkdir(parents=True, exist_ok=True)

    # 创建设备专用日志器
    logger = logging.getLogger(f"device.{device_id}")
    logger.setLevel(logging.DEBUG)

    # 添加设备过滤器
    logger.addFilter(DeviceLogFilter(device_id))

    # 设备日志文件处理器
    handler = RotatingFileHandler(
        device_log_path / f"{device_id}.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(logging.DEBUG)

    format_str = (
        f"%(asctime)s - [{device_id}] - %(levelname)s - " f"%(filename)s:%(lineno)d - %(message)s"
    )
    handler.setFormatter(logging.Formatter(format_str, datefmt="%Y-%m-%d %H:%M:%S"))

    logger.addHandler(handler)

    return logger


def cleanup_old_logs(
    log_dir: str = "logs",
    max_age_days: int = 30,
) -> int:
    """清理过期日志文件。

    删除超过指定天数的日志文件，包括压缩的日志文件。

    Args:
        log_dir: 日志目录路径
        max_age_days: 日志保留天数

    Returns:
        int: 删除的文件数量

    Example:
        >>> deleted_count = cleanup_old_logs(max_age_days=30)
        >>> print(f"删除了 {deleted_count} 个过期日志文件")
    """
    log_path = Path(log_dir)
    if not log_path.exists():
        return 0

    cutoff_date = datetime.now() - timedelta(days=max_age_days)
    deleted_count = 0

    for log_file in log_path.rglob("*.log*"):
        try:
            # 获取文件修改时间
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)

            if mtime < cutoff_date:
                log_file.unlink()
                deleted_count += 1
        except OSError:
            # 忽略无法访问的文件
            continue

    return deleted_count


def get_log_stats(log_dir: str = "logs") -> dict[str, Any]:
    """获取日志目录统计信息。

    Args:
        log_dir: 日志目录路径

    Returns:
        dict: 包含日志文件数量、总大小等统计信息

    Example:
        >>> stats = get_log_stats()
        >>> print(f"日志总大小: {stats['total_size_mb']:.2f} MB")
    """
    log_path = Path(log_dir)
    if not log_path.exists():
        return {
            "exists": False,
            "file_count": 0,
            "total_size_bytes": 0,
            "total_size_mb": 0.0,
        }

    total_size = 0
    file_count = 0
    files_by_type: dict[str, int] = {}

    for log_file in log_path.rglob("*.log*"):
        try:
            total_size += log_file.stat().st_size
            file_count += 1

            # 按类型统计
            ext = log_file.suffix
            files_by_type[ext] = files_by_type.get(ext, 0) + 1
        except OSError:
            continue

    return {
        "exists": True,
        "file_count": file_count,
        "total_size_bytes": total_size,
        "total_size_mb": total_size / (1024 * 1024),
        "files_by_type": files_by_type,
        "log_dir": str(log_path.absolute()),
    }
