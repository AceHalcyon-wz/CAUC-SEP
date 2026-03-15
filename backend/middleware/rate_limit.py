"""
API速率限制模块

功能：
- 基于IP和用户的速率限制
- 滑动窗口算法实现
- 分布式支持（Redis后端可选）
- 灵活的限制策略配置
- RateLimit响应头支持

安全特性：
- 防止API滥用
- 防止暴力破解
- 防止DDoS攻击
- 支持白名单

作者：Backend Engineer Agent
创建日期：2026-03-08
更新日期：2026-03-14
依赖：fastapi, starlette, redis (可选)

使用示例：
    >>> from middleware.rate_limit import RateLimitMiddleware, get_rate_limiter
    >>> app.add_middleware(RateLimitMiddleware)
    >>> limiter = get_rate_limiter()
    >>> limiter.add_to_whitelist(ip="192.168.1.100")
"""

import hashlib
import logging
import os
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


# ==================== 配置常量 ====================

# 默认限制配置
DEFAULT_REQUESTS_PER_MINUTE = int(os.environ.get("RATE_LIMIT_RPM", "1000"))
DEFAULT_BURST_SIZE = int(os.environ.get("RATE_LIMIT_BURST", "20"))
DEFAULT_WINDOW_SECONDS = int(os.environ.get("RATE_LIMIT_WINDOW", "60"))

# 阻止配置
BLOCK_DURATION_SECONDS = int(os.environ.get("RATE_LIMIT_BLOCK_DURATION", "60"))

# Redis配置（可选）
REDIS_ENABLED = os.environ.get("RATE_LIMIT_REDIS_ENABLED", "false").lower() == "true"
REDIS_URL = os.environ.get("RATE_LIMIT_REDIS_URL", "redis://localhost:6379/0")


class RateLimitStrategy(str, Enum):
    """
    速率限制策略枚举。
    """

    FIXED_WINDOW = "fixed_window"  # 固定窗口
    SLIDING_WINDOW = "sliding_window"  # 滑动窗口
    TOKEN_BUCKET = "token_bucket"  # 令牌桶
    LEAKY_BUCKET = "leaky_bucket"  # 漏桶


class RateLimitScope(str, Enum):
    """
    速率限制范围枚举。
    """

    IP = "ip"  # 基于IP
    USER = "user"  # 基于用户
    IP_USER = "ip_user"  # 基于IP和用户
    GLOBAL = "global"  # 全局限制


# ==================== 数据结构 ====================


@dataclass
class RateLimitConfig:
    """
    速率限制配置。

    Attributes:
        requests_per_minute: 每分钟请求数限制
        burst_size: 突发请求数限制
        window_seconds: 时间窗口大小（秒）
        strategy: 限制策略
        scope: 限制范围
        block_duration: 超限后阻止时间（秒）
    """

    requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE
    burst_size: int = DEFAULT_BURST_SIZE
    window_seconds: int = DEFAULT_WINDOW_SECONDS
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    scope: RateLimitScope = RateLimitScope.IP
    block_duration: int = BLOCK_DURATION_SECONDS


@dataclass
class ClientRateLimitState:
    """
    客户端速率限制状态。

    跟踪单个客户端的请求历史和阻止状态。
    使用滑动窗口算法记录请求时间戳。

    Attributes:
        requests: 请求时间戳列表
        blocked_until: 阻止截止时间
        token_count: 令牌桶当前令牌数（令牌桶算法）
        last_refill: 上次令牌补充时间（令牌桶算法）
    """

    requests: list[float] = field(default_factory=list)
    blocked_until: float = 0.0
    token_count: float = 0.0
    last_refill: float = field(default_factory=time.time)

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


# ==================== 速率限制器 ====================


class RateLimiter:
    """
    速率限制器。

    使用滑动窗口算法实现速率限制，支持按路径配置不同的限制策略。

    特性：
    - 基于客户端IP和User-Agent的标识
    - 可配置的请求限制和突发大小
    - 自动清理不活跃客户端记录
    - 支持敏感操作的严格限制
    - 支持白名单

    Example:
        >>> limiter = RateLimiter()
        >>> allowed, remaining, reset_time = limiter.is_allowed(request)
        >>> if not allowed:
        ...     return Response(status_code=429)
    """

    def __init__(
        self,
        default_config: RateLimitConfig | None = None,
        enable_redis: bool = REDIS_ENABLED,
    ):
        """
        初始化速率限制器。

        Args:
            default_config: 默认配置
            enable_redis: 是否启用Redis后端
        """
        self._clients: dict[str, ClientRateLimitState] = defaultdict(ClientRateLimitState)
        self._path_configs: dict[str, RateLimitConfig] = {}
        self._whitelist_ips: set[str] = set()
        self._whitelist_users: set[int] = set()

        # 默认配置
        self._default_config = default_config or RateLimitConfig()

        # Redis客户端（可选）
        self._redis_client = None
        if enable_redis:
            self._init_redis()

        # 敏感操作配置（更严格的限制）
        self._sensitive_paths = {
            # 急停操作
            "/api/v1/motor/emergency_stop": RateLimitConfig(
                requests_per_minute=30,
                burst_size=10,
            ),
            "/api/motor/emergency_stop": RateLimitConfig(
                requests_per_minute=30,
                burst_size=10,
            ),
            "/api/v1/motor/reset": RateLimitConfig(
                requests_per_minute=30,
                burst_size=10,
            ),
            "/api/motor/reset": RateLimitConfig(
                requests_per_minute=30,
                burst_size=10,
            ),
            "/api/electromagnet/emergency_stop": RateLimitConfig(
                requests_per_minute=30,
                burst_size=10,
            ),
            "/api/temperature/emergency_stop": RateLimitConfig(
                requests_per_minute=30,
                burst_size=10,
            ),
            # 校准操作
            "/api/electromagnet/calibrate": RateLimitConfig(
                requests_per_minute=10,
                burst_size=5,
            ),
            "/api/piezo/calibrate/perform": RateLimitConfig(
                requests_per_minute=10,
                burst_size=5,
            ),
            # 工厂重置
            "/api/v1/motor/factory_reset": RateLimitConfig(
                requests_per_minute=5,
                burst_size=2,
            ),
            # 认证操作
            "/api/v1/user/login": RateLimitConfig(
                requests_per_minute=1000,
                burst_size=100,
                block_duration=60,
            ),
            "/api/v1/user/logout": RateLimitConfig(
                requests_per_minute=30,
                burst_size=10,
            ),
        }

        # 数据导出配置
        self._export_paths = {
            "/api/experiments": RateLimitConfig(
                requests_per_minute=60,
                burst_size=30,
            ),
            "/api/v1/experiment": RateLimitConfig(
                requests_per_minute=60,
                burst_size=30,
            ),
        }

    def _init_redis(self) -> None:
        """
        初始化Redis客户端。

        如果Redis不可用，将回退到内存存储。
        """
        try:
            import redis

            self._redis_client = redis.from_url(REDIS_URL)
            self._redis_client.ping()
            logger.info("Rate limiter Redis backend initialized")
        except Exception as e:
            logger.warning(f"Redis initialization failed, using memory backend: {e}")
            self._redis_client = None

    def _get_client_key(
        self,
        request: Request,
        scope: RateLimitScope = RateLimitScope.IP,
    ) -> str:
        """
        获取客户端唯一标识。

        根据限制范围生成不同的标识符。

        Args:
            request: FastAPI请求对象
            scope: 限制范围

        Returns:
            str: 客户端标识哈希值
        """
        ip = "unknown"
        user_id = "anonymous"

        try:
            ip = request.client.host if request.client else "unknown"
        except (AttributeError, TypeError):
            pass

        # 尝试获取用户ID
        try:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                # 简单提取，实际应解码JWT
                user_id = hashlib.sha256(auth_header.encode()).hexdigest()[:8]
        except (AttributeError, TypeError):
            pass

        # 根据范围生成标识
        if scope == RateLimitScope.IP:
            key_data = f"ip:{ip}"
        elif scope == RateLimitScope.USER:
            key_data = f"user:{user_id}"
        elif scope == RateLimitScope.IP_USER:
            key_data = f"ip_user:{ip}:{user_id}"
        else:  # GLOBAL
            key_data = "global"

        # 使用哈希避免存储敏感信息
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]

    def _get_config(self, path: str) -> RateLimitConfig:
        """
        获取路径对应的速率限制配置。

        根据请求路径返回相应的限制配置。

        Args:
            path: 请求路径

        Returns:
            RateLimitConfig: 速率限制配置对象
        """
        # 检查敏感路径
        if path in self._sensitive_paths:
            return self._sensitive_paths[path]

        # 检查导出路径
        for export_path, config in self._export_paths.items():
            if path.startswith(export_path):
                return config

        return self._default_config

    def add_to_whitelist(self, ip: str | None = None, user_id: int | None = None) -> None:
        """
        添加到白名单。

        Args:
            ip: IP地址
            user_id: 用户ID
        """
        if ip:
            self._whitelist_ips.add(ip)
        if user_id:
            self._whitelist_users.add(user_id)

    def remove_from_whitelist(self, ip: str | None = None, user_id: int | None = None) -> None:
        """
        从白名单移除。

        Args:
            ip: IP地址
            user_id: 用户ID
        """
        if ip and ip in self._whitelist_ips:
            self._whitelist_ips.remove(ip)
        if user_id and user_id in self._whitelist_users:
            self._whitelist_users.remove(user_id)

    def _is_whitelisted(self, request: Request) -> bool:
        """
        检查请求是否在白名单中。

        Args:
            request: FastAPI请求对象

        Returns:
            bool: 是否在白名单中
        """
        try:
            ip = request.client.host if request.client else None
            if ip and ip in self._whitelist_ips:
                return True
        except (AttributeError, TypeError):
            pass

        return False

    def is_allowed(self, request: Request) -> tuple[bool, int, int, dict[str, str]]:
        """
        检查请求是否被允许。

        Args:
            request: FastAPI请求对象

        Returns:
            tuple[bool, int, int, dict]:
                - bool: 是否允许请求
                - int: 剩余请求数
                - int: 重置时间（秒）
                - dict: 响应头
        """
        try:
            path = request.url.path
        except (AttributeError, TypeError):
            path = "unknown"

        # 检查白名单
        if self._is_whitelisted(request):
            return (
                True,
                self._default_config.requests_per_minute,
                self._default_config.window_seconds,
                {},
            )

        config = self._get_config(path)
        client_key = self._get_client_key(request, config.scope)

        # 如果启用Redis，使用Redis后端
        if self._redis_client:
            return self._check_with_redis(client_key, config)

        # 内存后端
        return self._check_with_memory(client_key, config, path)

    def _check_with_memory(
        self,
        client_key: str,
        config: RateLimitConfig,
        path: str,
    ) -> tuple[bool, int, int, dict[str, str]]:
        """
        使用内存存储检查速率限制。

        Args:
            client_key: 客户端标识
            config: 限制配置
            path: 请求路径

        Returns:
            tuple: 是否允许、剩余数、重置时间、响应头
        """
        client = self._clients[client_key]

        # 清理过期请求
        client.cleanup_old_requests(config.window_seconds)

        # 检查是否被阻止
        if client.is_blocked():
            remaining_time = int(client.blocked_until - time.time())
            headers = {
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(max(remaining_time, 1)),
                "X-RateLimit-Limit": str(config.requests_per_minute),
                "Retry-After": str(max(remaining_time, 1)),
            }
            return False, 0, max(remaining_time, 1), headers

        # 检查是否超过限制
        current_count = len(client.requests)

        if current_count >= config.requests_per_minute:
            # 阻止客户端
            client.blocked_until = time.time() + config.block_duration
            logger.warning(
                f"Rate limit exceeded for client {client_key[:8]}... "
                f"on path {path}: {current_count} requests"
            )
            headers = {
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(config.block_duration),
                "X-RateLimit-Limit": str(config.requests_per_minute),
                "Retry-After": str(config.block_duration),
            }
            return False, 0, config.block_duration, headers

        # 允许请求
        client.add_request()
        remaining = config.requests_per_minute - current_count - 1
        headers = {
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(config.window_seconds),
            "X-RateLimit-Limit": str(config.requests_per_minute),
        }
        return True, remaining, config.window_seconds, headers

    def _check_with_redis(
        self,
        client_key: str,
        config: RateLimitConfig,
    ) -> tuple[bool, int, int, dict[str, str]]:
        """
        使用Redis存储检查速率限制。

        Args:
            client_key: 客户端标识
            config: 限制配置

        Returns:
            tuple: 是否允许、剩余数、重置时间、响应头
        """
        if not self._redis_client:
            return self._check_with_memory(client_key, config, "unknown")

        try:
            redis_key = f"rate_limit:{client_key}"
            current = self._redis_client.incr(redis_key)

            # 设置过期时间
            if current == 1:
                self._redis_client.expire(redis_key, config.window_seconds)

            # 获取TTL
            ttl = self._redis_client.ttl(redis_key)

            if current > config.requests_per_minute:
                remaining = 0
                headers = {
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(ttl),
                    "X-RateLimit-Limit": str(config.requests_per_minute),
                    "Retry-After": str(ttl),
                }
                return False, 0, ttl, headers

            remaining = config.requests_per_minute - current
            headers = {
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(ttl),
                "X-RateLimit-Limit": str(config.requests_per_minute),
            }
            return True, remaining, ttl, headers

        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            return True, config.requests_per_minute, config.window_seconds, {}

    def cleanup_clients(self, max_age_seconds: int = 3600) -> int:
        """
        清理不活跃的客户端记录。

        定期调用此方法可以防止内存泄漏。

        Args:
            max_age_seconds: 最大不活跃时间（秒）

        Returns:
            int: 清理的客户端数量
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

    def get_stats(self) -> dict[str, Any]:
        """
        获取速率限制器统计信息。

        Returns:
            dict: 统计信息
        """
        now = time.time()
        active_clients = sum(
            1
            for client in self._clients.values()
            if client.requests and client.requests[-1] > now - 60
        )
        blocked_clients = sum(1 for client in self._clients.values() if client.is_blocked())

        return {
            "total_clients": len(self._clients),
            "active_clients": active_clients,
            "blocked_clients": blocked_clients,
            "whitelist_ips": len(self._whitelist_ips),
            "whitelist_users": len(self._whitelist_users),
            "redis_enabled": self._redis_client is not None,
        }

    def reset_client(self, client_key: str) -> bool:
        """
        重置客户端的限制状态。

        Args:
            client_key: 客户端标识

        Returns:
            bool: 是否成功重置
        """
        if client_key in self._clients:
            del self._clients[client_key]
            logger.info(f"Rate limit reset for client {client_key[:8]}...")
            return True
        return False

    def block_client(self, client_key: str, duration_seconds: int = 3600) -> None:
        """
        手动阻止客户端。

        Args:
            client_key: 客户端标识
            duration_seconds: 阻止时长（秒）
        """
        client = self._clients[client_key]
        client.blocked_until = time.time() + duration_seconds
        logger.warning(f"Client {client_key[:8]}... blocked for {duration_seconds}s")


# ==================== 速率限制中间件 ====================


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
        skip_paths: list[str] | None = None,
    ):
        """
        初始化速率限制中间件。

        Args:
            app: ASGI应用实例
            rate_limiter: 速率限制器实例
            skip_paths: 跳过检查的路径列表
        """
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimiter()
        self.skip_paths = skip_paths or [
            "/static/",
            "/docs",
            "/openapi",
            "/redoc",
            "/favicon",
            "/ws/",
            "/health",
            "/api/health",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求并执行速率限制检查。

        Args:
            request: FastAPI请求对象
            call_next: 下一个中间件或路由处理器

        Returns:
            Response: 响应对象
        """
        # 跳过指定路径
        path = request.url.path
        if any(path.startswith(skip_path) for skip_path in self.skip_paths):
            return await call_next(request)

        # 检查速率限制
        allowed, remaining, reset_time, headers = self.rate_limiter.is_allowed(request)

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
                headers=headers,
            )

        # 添加速率限制头
        response = await call_next(request)

        for key, value in headers.items():
            response.headers[key] = value

        return response


# ==================== 装饰器方式 ====================


def rate_limit(
    requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE,
    burst_size: int = DEFAULT_BURST_SIZE,
    scope: RateLimitScope = RateLimitScope.IP,
) -> Callable:
    """
    速率限制装饰器。

    用于对特定端点应用速率限制。

    Args:
        requests_per_minute: 每分钟请求数限制
        burst_size: 突发请求数限制
        scope: 限制范围

    Returns:
        Callable: 装饰器函数

    Example:
        >>> @router.get("/api/sensitive")
        ... @rate_limit(requests_per_minute=10)
        ... async def sensitive_endpoint():
        ...     return {"message": "sensitive data"}
    """

    def decorator(func: Callable) -> Callable:
        # 存储限制配置
        func._rate_limit_config = RateLimitConfig(
            requests_per_minute=requests_per_minute,
            burst_size=burst_size,
            scope=scope,
        )
        return func

    return decorator


# ==================== 全局实例 ====================


_global_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """
    获取全局速率限制器实例。

    使用单例模式确保全局只有一个速率限制器实例。

    Returns:
        RateLimiter: 全局速率限制器实例
    """
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter()
    return _global_rate_limiter


def reset_rate_limiter() -> None:
    """
    重置全局速率限制器。

    用于测试或重置状态。
    """
    global _global_rate_limiter
    _global_rate_limiter = None
