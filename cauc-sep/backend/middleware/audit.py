"""
审计日志中间件模块

功能：
- 拦截所有 API 请求
- 记录请求方法、路径、参数、响应状态
- 记录用户 ID、设备 ID、时间戳
- 异步写入数据库，不阻塞请求处理
- 敏感信息自动脱敏

关键操作类型：
- 设备连接/断开
- 运动控制命令
- 参数修改
- 校准操作
- 报警事件

安全加固：
- SubTask 13.2: 敏感信息日志脱敏
"""

import json
import logging
import re
import time
from datetime import datetime
from typing import Any, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.data_storage import DataStorage
from middleware.security import sanitize_dict, sanitize_string, SENSITIVE_FIELDS

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    审计日志记录器。

    负责记录和管理审计日志，支持异步批量写入数据库。
    
    特性：
    - 自动识别关键操作类型
    - 敏感信息自动脱敏
    - 批量写入优化性能
    - 支持设备事件和报警事件记录
    
    Example:
        >>> logger = AuditLogger(storage)
        >>> logger.log_request("POST", "/api/motor/move", {"position": 100}, 200)
    """

    # 关键操作路径映射
    KEY_OPERATIONS = {
        # 设备连接/断开
        r"^/api(/v1)?/motor/connect$": {
            "operation_type": "device_connect",
            "category": "device",
        },
        r"^/api(/v1)?/motor/disconnect$": {
            "operation_type": "device_disconnect",
            "category": "device",
        },
        r"^/api(/v1)?/electromagnet/connect$": {
            "operation_type": "device_connect",
            "category": "device",
        },
        r"^/api(/v1)?/electromagnet/disconnect$": {
            "operation_type": "device_disconnect",
            "category": "device",
        },
        r"^/api(/v1)?/temperature/connect$": {
            "operation_type": "device_connect",
            "category": "device",
        },
        r"^/api(/v1)?/temperature/disconnect$": {
            "operation_type": "device_disconnect",
            "category": "device",
        },
        r"^/api(/v1)?/piezo/connect$": {
            "operation_type": "device_connect",
            "category": "device",
        },
        r"^/api(/v1)?/piezo/disconnect$": {
            "operation_type": "device_disconnect",
            "category": "device",
        },
        r"^/api(/v1)?/ammeter/connect$": {
            "operation_type": "device_connect",
            "category": "device",
        },
        r"^/api(/v1)?/ammeter/disconnect$": {
            "operation_type": "device_disconnect",
            "category": "device",
        },
        # 运动控制命令
        r"^/api(/v1)?/motor/move$": {
            "operation_type": "motor_move",
            "category": "motion_control",
        },
        r"^/api(/v1)?/motor/jog$": {
            "operation_type": "motor_jog",
            "category": "motion_control",
        },
        r"^/api(/v1)?/motor/stop$": {
            "operation_type": "motor_stop",
            "category": "motion_control",
        },
        r"^/api(/v1)?/motor/emergency_stop$": {
            "operation_type": "emergency_stop",
            "category": "safety",
        },
        r"^/api(/v1)?/motor/reset$": {
            "operation_type": "emergency_reset",
            "category": "safety",
        },
        r"^/api(/v1)?/motor/home$": {
            "operation_type": "motor_home",
            "category": "motion_control",
        },
        # 参数修改
        r"^/api(/v1)?/motor/limits$": {
            "operation_type": "limit_config",
            "category": "parameter",
        },
        r"^/api(/v1)?/motor/pr-path.*$": {
            "operation_type": "pr_path_config",
            "category": "parameter",
        },
        r"^/api(/v1)?/electromagnet/current$": {
            "operation_type": "electromagnet_set_current",
            "category": "parameter",
        },
        r"^/api(/v1)?/temperature/setpoint$": {
            "operation_type": "temperature_setpoint",
            "category": "parameter",
        },
        r"^/api(/v1)?/temperature/pid$": {
            "operation_type": "pid_config",
            "category": "parameter",
        },
        r"^/api(/v1)?/piezo/voltage$": {
            "operation_type": "piezo_set_voltage",
            "category": "parameter",
        },
        r"^/api(/v1)?/piezo/displacement$": {
            "operation_type": "piezo_set_displacement",
            "category": "parameter",
        },
        # 校准操作
        r"^/api(/v1)?/electromagnet/calibrat.*$": {
            "operation_type": "electromagnet_calibrate",
            "category": "calibration",
        },
        r"^/api(/v1)?/piezo/calibrat.*$": {
            "operation_type": "piezo_calibrate",
            "category": "calibration",
        },
        # 扫描操作
        r"^/api(/v1)?/electromagnet/scan.*$": {
            "operation_type": "electromagnet_scan",
            "category": "experiment",
        },
        r"^/api(/v1)?/ammeter/start$": {
            "operation_type": "ammeter_start",
            "category": "experiment",
        },
        r"^/api(/v1)?/ammeter/stop$": {
            "operation_type": "ammeter_stop",
            "category": "experiment",
        },
        # 实验管理
        r"^/api(/v1)?/experiments/start$": {
            "operation_type": "experiment_start",
            "category": "experiment",
        },
        r"^/api(/v1)?/experiments/\d+/stop$": {
            "operation_type": "experiment_stop",
            "category": "experiment",
        },
        # 温度程序
        r"^/api(/v1)?/temperature/program.*$": {
            "operation_type": "temperature_program",
            "category": "experiment",
        },
    }

    def __init__(self, storage: DataStorage | None = None):
        """
        初始化审计日志记录器。

        Args:
            storage: 数据存储实例，用于持久化日志记录
        """
        self._storage = storage
        self._log_buffer: list[dict[str, Any]] = []
        self._buffer_size = 50

    def set_storage(self, storage: DataStorage) -> None:
        """
        设置数据存储实例。

        Args:
            storage: 数据存储实例
        """
        self._storage = storage

    def _get_operation_info(self, path: str, method: str) -> dict[str, str]:
        """
        根据请求路径获取操作类型和分类。

        Args:
            path: 请求路径
            method: HTTP 方法

        Returns:
            dict: 包含 operation_type 和 category 的字典
        """
        for pattern, info in self.KEY_OPERATIONS.items():
            if re.match(pattern, path):
                return info

        # 默认分类
        if path.startswith("/api/v1/device") or path.startswith("/api/device"):
            return {"operation_type": "device_query", "category": "query"}
        elif path.startswith("/api/v1/motor") or path.startswith("/api/motor"):
            return {"operation_type": "motor_operation", "category": "motor"}
        elif path.startswith("/api/v1/experiment") or path.startswith("/api/experiment"):
            return {"operation_type": "experiment_operation", "category": "experiment"}
        elif path.startswith("/api/v1/analysis") or path.startswith("/api/analysis"):
            return {"operation_type": "data_analysis", "category": "analysis"}
        else:
            return {"operation_type": "api_request", "category": "general"}

    def _extract_device_id(self, path: str, params: dict | None) -> str | None:
        """
        从请求路径或参数中提取设备ID。

        Args:
            path: 请求路径
            params: 请求参数

        Returns:
            str | None: 设备ID，无法提取时返回None
        """
        # 从路径提取
        if "/motor/" in path:
            return "stepper_01"
        elif "/electromagnet/" in path:
            return "electromagnet_01"
        elif "/temperature/" in path:
            return "temp_controller_01"
        elif "/piezo/" in path:
            return "piezo_01"
        elif "/ammeter/" in path:
            return "picoammeter_01"

        # 从参数提取
        if params and isinstance(params, dict):
            return params.get("device_id")

        return None

    def log_request(
        self,
        method: str,
        path: str,
        params: dict | None,
        response_status: int,
        response_message: str | None = None,
        user_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        duration_ms: int | None = None,
        extra_data: dict | None = None,
        device_id: str | None = None,
    ) -> None:
        """
        记录请求日志。

        Args:
            method: HTTP 方法
            path: 请求路径
            params: 请求参数（会自动脱敏）
            response_status: 响应状态码
            response_message: 响应消息
            user_id: 用户ID
            ip_address: IP地址
            user_agent: 用户代理字符串
            duration_ms: 请求处理时间（毫秒）
            extra_data: 额外数据
            device_id: 设备ID（可选，不提供时自动从路径/参数提取）
            
        Note:
            - 敏感字段会自动脱敏
            - 日志先写入缓冲区，满50条时批量写入数据库
        """
        if not self._storage:
            return

        # 获取操作类型和分类
        op_info = self._get_operation_info(path, method)

        # 提取设备ID（优先使用传入的device_id）
        if not device_id:
            device_id = self._extract_device_id(path, params)

        # 构建日志记录
        log_entry = {
            "timestamp": datetime.now(),
            "user_id": user_id,
            "device_id": device_id,
            "operation_type": op_info["operation_type"],
            "operation_category": op_info["category"],
            "request_method": method,
            "request_path": path,
            "request_params": json.dumps(params, ensure_ascii=False) if params else None,
            "response_status": response_status,
            "response_message": response_message,
            "ip_address": ip_address,
            "user_agent": user_agent[:255] if user_agent else None,
            "duration_ms": duration_ms,
            "extra_data": json.dumps(extra_data, ensure_ascii=False) if extra_data else None,
        }

        self._log_buffer.append(log_entry)

        # 缓冲区满时写入数据库
        if len(self._log_buffer) >= self._buffer_size:
            self._flush_buffer()

    def _flush_buffer(self) -> None:
        """
        将缓冲区日志写入数据库。

        批量写入优化数据库性能，失败时记录错误日志。
        """
        if not self._storage or not self._log_buffer:
            return

        try:
            from models import AuditLog

            session = self._storage.Session()
            try:
                for entry in self._log_buffer:
                    log_record = AuditLog(**entry)
                    session.add(log_record)
                session.commit()
                logger.debug(f"Flushed {len(self._log_buffer)} audit logs to database")
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to commit audit logs: {e}")
                raise
            finally:
                session.close()
            self._log_buffer = []
        except ImportError:
            logger.warning("AuditLog model not found, skipping database write")
        except Exception as e:
            logger.error(f"Failed to flush audit logs: {e}")

    def flush(self) -> None:
        """
        手动刷新缓冲区。

        将所有缓存的日志立即写入数据库。
        """
        self._flush_buffer()


# 全局审计日志记录器实例
audit_logger = AuditLogger()


class AuditMiddleware(BaseHTTPMiddleware):
    """
    审计日志中间件。

    拦截所有 HTTP 请求，记录关键操作日志。
    
    特性：
    - 自动记录请求/响应信息
    - 敏感信息自动脱敏
    - 计算请求处理时间
    - 排除静态文件和文档路径
    
    Example:
        >>> app.add_middleware(AuditMiddleware, storage=data_storage)
    """

    # 排除的路径（不记录日志）
    EXCLUDED_PATHS = {
        "/",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/favicon.ico",
    }

    # 排除的路径前缀（不记录日志）
    EXCLUDED_PREFIXES = {
        "/ws/",  # WebSocket 路径
        "/static/",  # 静态文件
    }

    def __init__(self, app: ASGIApp, storage: DataStorage | None = None):
        """
        初始化审计日志中间件。

        Args:
            app: ASGI 应用实例
            storage: 数据存储实例，用于持久化日志
        """
        super().__init__(app)
        if storage:
            audit_logger.set_storage(storage)

    def _should_log(self, path: str) -> bool:
        """
        判断是否应该记录日志。

        Args:
            path: 请求路径

        Returns:
            bool: 是否记录日志
        """
        # 排除特定路径
        if path in self.EXCLUDED_PATHS:
            return False

        # 排除特定前缀
        for prefix in self.EXCLUDED_PREFIXES:
            if path.startswith(prefix):
                return False

        return True

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求并记录日志。

        Args:
            request: FastAPI请求对象
            call_next: 下一个中间件或路由处理器

        Returns:
            Response: 响应对象
            
        Note:
            - POST/PUT/PATCH请求体会被脱敏后记录
            - 响应体中的message/detail字段会被记录
        """
        path = request.url.path
        method = request.method

        # 判断是否需要记录
        if not self._should_log(path):
            return await call_next(request)

        # 记录开始时间
        start_time = time.time()

        # 获取请求参数
        params: dict[str, Any] = {}

        # 从查询参数获取
        if request.query_params:
            params.update(dict(request.query_params))

        # 从路径参数获取
        if request.path_params:
            params.update(request.path_params)

        # 从请求体获取（仅对 POST/PUT/PATCH）
        if method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    body_str = body.decode("utf-8")
                    try:
                        body_json = json.loads(body_str)
                        if isinstance(body_json, dict):
                            # 敏感信息脱敏（使用安全模块的完整脱敏功能）
                            body_json = sanitize_dict(body_json)
                            params.update(body_json)
                    except json.JSONDecodeError:
                        # 对非JSON内容也进行脱敏
                        params["_body"] = sanitize_string(body_str[:500])  # 限制长度
            except (UnicodeDecodeError, AttributeError):
                pass
            except Exception as e:
                logger.debug(f"Failed to read request body: {e}")

        # 获取客户端信息
        ip_address = None
        try:
            ip_address = request.client.host if request.client else None
        except (AttributeError, TypeError):
            pass
            
        user_agent = request.headers.get("user-agent")

        # 获取用户ID（如果存在）
        user_id = None
        # TODO: 从认证信息中获取用户ID

        # 调用下一个处理器
        response = await call_next(request)

        # 计算处理时间
        duration_ms = int((time.time() - start_time) * 1000)

        # 获取响应消息
        response_message = None
        try:
            # 读取响应体
            body_chunks = []
            async for chunk in response.body_iterator:
                body_chunks.append(chunk)
            body = b"".join(body_chunks)

            # 重新设置 body_iterator（使用异步生成器）
            async def async_body_iterator():
                yield body
            response.body_iterator = async_body_iterator()

            try:
                body_json = json.loads(body.decode("utf-8"))
                if isinstance(body_json, dict):
                    response_message = body_json.get("message") or body_json.get("detail")
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        except Exception as e:
            logger.debug(f"Failed to read response body: {e}")

        # 记录日志
        audit_logger.log_request(
            method=method,
            path=path,
            params=params,
            response_status=response.status_code,
            response_message=response_message,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            duration_ms=duration_ms,
        )

        return response


def log_alarm_event(
    device_id: str,
    alarm_code: int,
    alarm_text: str,
    alarm_level: str = "warning",
    extra_data: dict | None = None,
) -> None:
    """
    记录报警事件日志。

    用于记录设备报警、安全事件等需要特别关注的情况。

    Args:
        device_id: 设备ID
        alarm_code: 报警代码
        alarm_text: 报警文本描述
        alarm_level: 报警级别，可选值："info", "warning", "error", "critical"
        extra_data: 额外数据（JSON序列化存储）
        
    Example:
        >>> log_alarm_event("stepper_01", 1001, "Over temperature", "critical")
    """
    audit_logger.log_request(
        method="EVENT",
        path=f"/alarm/{device_id}",
        params={
            "alarm_code": alarm_code,
            "alarm_text": alarm_text,
            "alarm_level": alarm_level,
        },
        response_status=0,
        response_message=alarm_text,
        device_id=device_id,
        extra_data=extra_data,
    )


def log_device_event(
    device_id: str,
    event_type: str,
    event_data: dict | None = None,
) -> None:
    """
    记录设备事件日志。

    用于记录设备状态变化、操作结果等事件。

    Args:
        device_id: 设备ID
        event_type: 事件类型（如 "connected", "disconnected", "error", "calibrated"）
        event_data: 事件数据（JSON序列化存储）
        
    Example:
        >>> log_device_event("stepper_01", "connected", {"port": "COM3"})
    """
    audit_logger.log_request(
        method="EVENT",
        path=f"/device/{device_id}/{event_type}",
        params=event_data,
        response_status=0,
        device_id=device_id,
    )
