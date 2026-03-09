"""
安全中间件模块

功能：
- API访问频率限制（Rate Limiting）
- 输入验证增强
- 安全响应头
- 请求日志脱敏

安全策略：
- 全局速率限制：100次/分钟
- 敏感操作限制：10次/分钟（急停、校准等）
- 数据查询限制：60次/分钟

作者：Performance Optimization Engineer
创建日期：2026-03-07
"""

import hashlib
import logging
import re
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


# ==================== 敏感信息脱敏 ====================

SENSITIVE_FIELDS = {
    # 认证相关
    "password",
    "password_hash",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "apikey",
    "secret",
    "secret_key",
    "private_key",
    "credential",
    "credentials",
    "authorization",
    "auth",
    # 个人信息
    "ssn",
    "social_security_number",
    "credit_card",
    "card_number",
    "cvv",
    # 其他敏感数据
    "session_id",
    "cookie",
    "jwt",
}

SENSITIVE_PATTERNS = [
    # JWT Token
    re.compile(r"eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*"),
    # API Key (常见格式)
    re.compile(r"(?:sk-|pk-|api[_-]?key[_-]?)[A-Za-z0-9]{20,}"),
    # 密码哈希
    re.compile(r"\$2[aby]\$[0-9]{2}\$[A-Za-z0-9./]{53}"),
    # 私钥
    re.compile(r"-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----"),
]


def mask_sensitive_value(value: str, visible_chars: int = 4) -> str:
    """
    脱敏敏感值。

    Args:
        value: 原始值
        visible_chars: 可见字符数

    Returns:
        str: 脱敏后的值
    """
    if not value or len(value) <= visible_chars:
        return "****"

    return f"{value[:visible_chars]}{'*' * (min(len(value) - visible_chars, 20))}"


def sanitize_dict(data: dict[str, Any], depth: int = 0) -> dict[str, Any]:
    """
    递归脱敏字典中的敏感字段。

    Args:
        data: 原始字典
        depth: 当前递归深度（防止无限递归）

    Returns:
        dict: 脱敏后的字典
    """
    if depth > 10:  # 防止无限递归
        return {"_truncated": "max depth exceeded"}

    result = {}
    for key, value in data.items():
        key_lower = key.lower().replace("-", "_")

        # 检查是否为敏感字段
        if key_lower in SENSITIVE_FIELDS:
            if isinstance(value, str):
                result[key] = mask_sensitive_value(value)
            else:
                result[key] = "****"
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value, depth + 1)
        elif isinstance(value, list):
            result[key] = [
                sanitize_dict(item, depth + 1) if isinstance(item, dict) else item
                for item in value[:100]  # 限制列表长度
            ]
        elif isinstance(value, str):
            # 检查是否匹配敏感模式
            sanitized_str = value
            for pattern in SENSITIVE_PATTERNS:
                if pattern.search(value):
                    sanitized_str = pattern.sub("[REDACTED]", value)
                    break
            result[key] = sanitized_str[:500]  # 限制字符串长度
        else:
            result[key] = value

    return result


def sanitize_string(text: str) -> str:
    """
    脱敏字符串中的敏感信息。

    Args:
        text: 原始字符串

    Returns:
        str: 脱敏后的字符串
    """
    sanitized = text
    for pattern in SENSITIVE_PATTERNS:
        sanitized = pattern.sub("[REDACTED]", sanitized)
    return sanitized


# ==================== 速率限制 ====================


@dataclass
class RateLimitConfig:
    """速率限制配置。"""

    requests_per_minute: int = 100
    burst_size: int = 20
    window_seconds: int = 60


@dataclass
class ClientRateLimit:
    """
    客户端速率限制状态。

    跟踪单个客户端的请求历史和阻止状态。
    使用滑动窗口算法记录请求时间戳。
    """

    requests: list[float] = field(default_factory=list)
    blocked_until: float = 0.0

    def is_blocked(self) -> bool:
        """
        检查客户端是否被阻止。

        Returns:
            bool: 如果当前时间小于阻止截止时间，返回True
        """
        return time.time() < self.blocked_until

    def cleanup_old_requests(self, window_seconds: int) -> None:
        """
        清理超出时间窗口的过期请求记录。

        Args:
            window_seconds: 时间窗口大小（秒）
        """
        cutoff = time.time() - window_seconds
        self.requests = [t for t in self.requests if t > cutoff]

    def add_request(self) -> None:
        """
        添加新的请求记录。

        记录当前时间戳到请求列表中。
        """
        self.requests.append(time.time())

    def get_request_count(self) -> int:
        """
        获取当前请求计数。

        Returns:
            int: 请求列表长度
        """
        return len(self.requests)


class RateLimiter:
    """
    速率限制器。

    使用滑动窗口算法实现速率限制，支持按路径配置不同的限制策略。

    特性：
    - 基于客户端IP和User-Agent的标识
    - 可配置的请求限制和突发大小
    - 自动清理不活跃客户端记录
    - 支持敏感操作的严格限制

    Example:
        >>> limiter = RateLimiter()
        >>> allowed, remaining, reset_time = limiter.is_allowed(request)
        >>> if not allowed:
        ...     return Response(status_code=429)
    """

    def __init__(self):
        """
        初始化速率限制器。

        设置默认配置和敏感路径的特殊限制策略。
        """
        self._clients: dict[str, ClientRateLimit] = defaultdict(ClientRateLimit)
        self._path_configs: dict[str, RateLimitConfig] = {}

        # 默认配置
        self._default_config = RateLimitConfig()

        # 敏感操作配置（更严格的限制）
        self._sensitive_paths = {
            "/api/v1/motor/emergency_stop": RateLimitConfig(requests_per_minute=30, burst_size=10),
            "/api/motor/emergency_stop": RateLimitConfig(requests_per_minute=30, burst_size=10),
            "/api/v1/motor/reset": RateLimitConfig(requests_per_minute=30, burst_size=10),
            "/api/motor/reset": RateLimitConfig(requests_per_minute=30, burst_size=10),
            "/api/electromagnet/emergency_stop": RateLimitConfig(
                requests_per_minute=30, burst_size=10
            ),
            "/api/temperature/emergency_stop": RateLimitConfig(
                requests_per_minute=30, burst_size=10
            ),
            # 校准操作
            "/api/electromagnet/calibrate": RateLimitConfig(requests_per_minute=10, burst_size=5),
            "/api/piezo/calibrate/perform": RateLimitConfig(requests_per_minute=10, burst_size=5),
            # 工厂重置
            "/api/v1/motor/factory_reset": RateLimitConfig(requests_per_minute=5, burst_size=2),
        }

        # 数据导出配置
        self._export_paths = {
            "/api/experiments": RateLimitConfig(requests_per_minute=60, burst_size=30),
            "/api/v1/experiment": RateLimitConfig(requests_per_minute=60, burst_size=30),
        }

    def _get_client_key(self, request: Request) -> str:
        """
        获取客户端唯一标识。

        使用IP地址和User-Agent的组合生成哈希标识，避免存储敏感信息。

        Args:
            request: FastAPI请求对象

        Returns:
            str: 32字符的客户端标识哈希值

        Note:
            如果无法获取客户端信息，将使用默认值"unknown"
        """
        try:
            ip = request.client.host if request.client else "unknown"
        except (AttributeError, TypeError):
            ip = "unknown"

        try:
            user_agent = request.headers.get("user-agent", "")[:100]
        except (AttributeError, TypeError):
            user_agent = ""

        # 使用哈希避免存储敏感信息
        key_data = f"{ip}:{user_agent}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]

    def _get_config(self, path: str) -> RateLimitConfig:
        """
        获取路径对应的速率限制配置。

        根据请求路径返回相应的限制配置，敏感路径有更严格的限制。

        Args:
            path: 请求路径

        Returns:
            RateLimitConfig: 速率限制配置对象

        Note:
            配置优先级：敏感路径 > 导出路径 > 默认配置
        """
        # 检查敏感路径
        if path in self._sensitive_paths:
            return self._sensitive_paths[path]

        # 检查导出路径
        for export_path, config in self._export_paths.items():
            if path.startswith(export_path):
                return config

        return self._default_config

    def is_allowed(self, request: Request) -> tuple[bool, int, int]:
        """
        检查请求是否被允许。

        Args:
            request: FastAPI请求对象

        Returns:
            tuple[bool, int, int]:
                - bool: 是否允许请求
                - int: 剩余请求数
                - int: 重置时间（秒）

        Note:
            超过限制时，客户端将被阻止60秒
        """
        try:
            client_key = self._get_client_key(request)
            path = request.url.path
        except (AttributeError, TypeError):
            # 无法获取请求信息时，允许通过
            return (
                True,
                self._default_config.requests_per_minute,
                self._default_config.window_seconds,
            )

        config = self._get_config(path)

        client = self._clients[client_key]

        # 清理过期请求
        client.cleanup_old_requests(config.window_seconds)

        # 检查是否被阻止
        if client.is_blocked():
            remaining_time = int(client.blocked_until - time.time())
            return False, 0, max(remaining_time, 1)

        # 检查是否超过限制
        current_count = len(client.requests)

        if current_count >= config.requests_per_minute:
            # 阻止客户端
            client.blocked_until = time.time() + 60  # 阻止60秒
            logger.warning(
                f"Rate limit exceeded for client {client_key[:8]}... "
                f"on path {path}: {current_count} requests"
            )
            return False, 0, 60

        # 允许请求
        client.add_request()
        remaining = config.requests_per_minute - current_count - 1
        return True, remaining, config.window_seconds

    def cleanup_clients(self, max_age_seconds: int = 3600) -> int:
        """
        清理不活跃的客户端记录。

        定期调用此方法可以防止内存泄漏。

        Args:
            max_age_seconds: 最大不活跃时间（秒），默认1小时

        Returns:
            int: 清理的客户端数量

        Note:
            只清理已解除阻止且无最近请求的客户端
        """
        cutoff = time.time() - max_age_seconds
        inactive_clients = [
            key
            for key, client in self._clients.items()
            if (not client.requests or client.requests[-1] < cutoff)
            and client.blocked_until < time.time()
        ]

        for key in inactive_clients:
            del self._clients[key]

        if inactive_clients:
            logger.debug(f"Cleaned up {len(inactive_clients)} inactive rate limit records")

        return len(inactive_clients)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    速率限制中间件。

    在请求处理前检查速率限制，超过限制时返回429错误。

    特性：
    - 自动跳过静态文件和文档路径
    - 跳过WebSocket连接
    - 添加速率限制响应头
    - 记录阻止日志

    Example:
        >>> app.add_middleware(RateLimitMiddleware, rate_limiter=my_limiter)
    """

    def __init__(
        self,
        app: ASGIApp,
        rate_limiter: RateLimiter | None = None,
    ):
        """
        初始化速率限制中间件。

        Args:
            app: ASGI应用实例
            rate_limiter: 速率限制器实例，如果为None则创建新实例
        """
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimiter()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求并执行速率限制检查。

        Args:
            request: FastAPI请求对象
            call_next: 下一个中间件或路由处理器

        Returns:
            Response: 响应对象，如果被限制则返回429响应

        Note:
            跳过以下路径：
            - /static/ 静态文件
            - /docs, /openapi, /redoc API文档
            - /ws/ WebSocket连接
        """
        # 跳过静态文件和文档
        path = request.url.path
        if path.startswith(("/static/", "/docs", "/openapi", "/redoc", "/favicon")):
            return await call_next(request)

        # 跳过WebSocket
        if path.startswith("/ws/"):
            return await call_next(request)

        # 检查速率限制
        allowed, remaining, reset_time = self.rate_limiter.is_allowed(request)

        if not allowed:
            client_ip = "unknown"
            try:
                client_ip = request.client.host if request.client else "unknown"
            except (AttributeError, TypeError):
                pass

            logger.warning(f"Rate limit blocked: {path} from {client_ip}")
            return Response(
                content='{"detail":"Too many requests. Please try again later.","error_code":"RATE_LIMIT_EXCEEDED"}',
                status_code=429,
                media_type="application/json",
                headers={
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time),
                },
            )

        # 添加速率限制头
        response = await call_next(request)

        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response


# ==================== 安全响应头 ====================


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    安全响应头中间件。

    添加安全相关的HTTP响应头，防止常见Web安全攻击。

    添加的安全头包括：
    - X-Content-Type-Options: 防止MIME类型嗅探
    - X-Frame-Options: 防止点击劫持
    - X-XSS-Protection: XSS保护
    - Referrer-Policy: 引用策略
    - Permissions-Policy: 权限策略
    - Content-Security-Policy: 内容安全策略（仅HTML响应）
    - Cache-Control: 缓存控制（仅API响应）

    Example:
        >>> app.add_middleware(SecurityHeadersMiddleware)
    """

    def __init__(self, app: ASGIApp):
        """
        初始化安全响应头中间件。

        Args:
            app: ASGI应用实例
        """
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求并添加安全响应头。

        Args:
            request: FastAPI请求对象
            call_next: 下一个中间件或路由处理器

        Returns:
            Response: 添加了安全头的响应对象
        """
        response = await call_next(request)

        # 防止MIME类型嗅探
        response.headers["X-Content-Type-Options"] = "nosniff"

        # 防止点击劫持
        response.headers["X-Frame-Options"] = "DENY"

        # XSS保护
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # 引用策略
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 权限策略
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), "
            "gyroscope=(), magnetometer=(), microphone=(), "
            "payment=(), usb=()"
        )

        # 内容安全策略（仅对HTML响应）
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self' ws: wss:; "
                "frame-ancestors 'none';"
            )

        # 缓存控制（对API响应禁用缓存）
        if path_is_api(request.url.path):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"

        return response


def path_is_api(path: str) -> bool:
    """
    检查路径是否为API路径。

    Args:
        path: 请求路径

    Returns:
        bool: 是否为API路径
    """
    return path.startswith("/api/") or path.startswith("/ws/")


# ==================== 输入验证增强 ====================


def validate_device_id(device_id: str) -> bool:
    """
    验证设备ID格式。

    Args:
        device_id: 设备ID字符串

    Returns:
        bool: 如果ID格式有效返回True

    Note:
        有效格式：字母、数字、下划线、连字符，长度1-100
    """
    if not device_id or not isinstance(device_id, str):
        return False

    if len(device_id) > 100 or len(device_id) == 0:
        return False

    # 允许字母、数字、下划线、连字符
    pattern = re.compile(r"^[a-zA-Z0-9_-]+$")
    return bool(pattern.match(device_id))


def validate_experiment_id(exp_id: int) -> bool:
    """
    验证实验ID。

    Args:
        exp_id: 实验ID

    Returns:
        bool: 如果ID有效返回True

    Note:
        有效范围：1 到 2^31-1（正32位整数）
    """
    if not isinstance(exp_id, int):
        return False

    # 排除布尔类型（Python中bool是int的子类）
    if isinstance(exp_id, bool):
        return False

    return exp_id > 0 and exp_id < 2**31


def validate_array_length(data: list, max_length: int = 10000) -> bool:
    """
    验证数组长度。

    Args:
        data: 数据数组
        max_length: 最大允许长度，默认10000

    Returns:
        bool: 如果数组长度有效返回True

    Raises:
        TypeError: 如果max_length不是正整数
    """
    if not isinstance(max_length, int) or max_length <= 0:
        raise TypeError("max_length must be a positive integer")

    return isinstance(data, list) and len(data) <= max_length


def validate_string_length(text: str, max_length: int = 10000) -> bool:
    """
    验证字符串长度。

    Args:
        text: 待验证字符串
        max_length: 最大允许长度，默认10000

    Returns:
        bool: 如果字符串长度有效返回True

    Raises:
        TypeError: 如果max_length不是正整数
    """
    if not isinstance(max_length, int) or max_length <= 0:
        raise TypeError("max_length must be a positive integer")

    return isinstance(text, str) and len(text) <= max_length


def sanitize_filename(filename: str) -> str:
    r"""
    清理文件名，移除危险字符。

    防止路径遍历攻击和文件名注入。

    Args:
        filename: 原始文件名

    Returns:
        str: 安全的文件名

    Note:
        - 移除路径遍历字符（..、/、\）
        - 只保留字母、数字、点、下划线、连字符
        - 限制长度为255字符
    """
    if not filename or not isinstance(filename, str):
        return "unnamed"

    # 移除路径遍历字符
    filename = filename.replace("..", "").replace("/", "").replace("\\", "")

    # 只保留安全字符
    safe_chars = re.compile(r"[^a-zA-Z0-9._-]")
    filename = safe_chars.sub("_", filename)

    # 限制长度
    if len(filename) > 255:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        filename = name[:250] + ("." + ext if ext else "")

    # 确保文件名不为空
    return filename if filename else "unnamed"


# ==================== 全局实例 ====================

# 全局速率限制器实例（单例模式）
_global_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """
    获取全局速率限制器实例。

    使用单例模式确保全局只有一个速率限制器实例。

    Returns:
        RateLimiter: 全局速率限制器实例

    Example:
        >>> limiter = get_rate_limiter()
        >>> allowed, remaining, reset = limiter.is_allowed(request)
    """
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter()
    return _global_rate_limiter


# ==================== 辅助函数 ====================


def get_client_ip(request: Request) -> str:
    """
    获取客户端真实IP地址。

    支持代理服务器场景，按优先级检查多个可能的IP来源。

    Args:
        request: FastAPI请求对象

    Returns:
        str: 客户端IP地址，无法获取时返回"unknown"

    Note:
        检查顺序：
        1. X-Forwarded-For 头（取第一个IP）
        2. X-Real-IP 头
        3. 直接连接的客户端IP
    """
    try:
        # 检查X-Forwarded-For头
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # 取第一个IP（原始客户端）
            return forwarded_for.split(",")[0].strip()

        # 检查X-Real-IP头
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()

        # 使用直接连接的IP
        if request.client:
            return request.client.host
    except (AttributeError, TypeError):
        pass

    return "unknown"


def log_security_event(
    event_type: str,
    request: Request,
    detail: str,
    severity: str = "warning",
) -> None:
    """
    记录安全事件日志。

    用于记录安全相关的事件，如认证失败、权限违规等。

    Args:
        event_type: 事件类型（如 "auth_failure", "rate_limit", "suspicious_request"）
        request: FastAPI请求对象
        detail: 详细描述信息
        severity: 严重程度，可选值："info", "warning", "critical"

    Note:
        日志会自动包含客户端IP、请求路径、方法等信息
        detail参数会自动进行敏感信息脱敏
    """
    client_ip = get_client_ip(request)

    try:
        path = request.url.path
        method = request.method
    except (AttributeError, TypeError):
        path = "unknown"
        method = "unknown"

    log_data = {
        "event_type": event_type,
        "client_ip": client_ip,
        "method": method,
        "path": path,
        "detail": sanitize_string(detail),
        "severity": severity,
        "timestamp": datetime.now().isoformat(),
    }

    if severity == "critical":
        logger.critical(f"Security event: {event_type}", extra=log_data)
    elif severity == "warning":
        logger.warning(f"Security event: {event_type}", extra=log_data)
    else:
        logger.info(f"Security event: {event_type}", extra=log_data)
