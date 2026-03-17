"""
安全响应头中间件模块

文件名: security_headers.py
路径: backend/middleware/
功能: 添加安全相关的 HTTP 响应头，防止常见 Web 安全攻击
作者: Backend Engineer Agent
创建日期: 2026-03-16
依赖: fastapi, starlette

安全头说明：
- X-Content-Type-Options: 防止 MIME 类型嗅探
- X-Frame-Options: 防止点击劫持
- X-XSS-Protection: XSS 过滤器（旧浏览器）
- Content-Security-Policy: 内容安全策略
- Referrer-Policy: 引用策略
- Permissions-Policy: 权限策略
- Strict-Transport-Security: HSTS（生产环境）

注意事项：
- CSP 配置需要根据实际前端需求调整
- HSTS 仅在 HTTPS 环境下启用
- 生产环境应使用更严格的 CSP 策略
"""

import logging
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    安全响应头中间件。

    为所有 HTTP 响应添加安全相关的响应头，防止常见 Web 安全攻击。

    添加的安全头：
        - X-Content-Type-Options: nosniff
        - X-Frame-Options: DENY
        - X-XSS-Protection: 1; mode=block
        - Referrer-Policy: strict-origin-when-cross-origin
        - Permissions-Policy: 禁用不必要的浏览器功能
        - Content-Security-Policy: 仅对 HTML 响应添加

    Attributes:
        app: ASGI 应用实例
        csp_policy: 自定义 CSP 策略（可选）
        hsts_max_age: HSTS 最大年龄（秒）

    Example:
        >>> app.add_middleware(SecurityHeadersMiddleware)
        >>> # 或使用自定义 CSP
        >>> app.add_middleware(
        ...     SecurityHeadersMiddleware,
        ...     csp_policy="default-src 'self'; script-src 'self'"
        ... )
    """

    # 默认 CSP 策略
    DEFAULT_CSP_POLICY = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self' ws: wss:; "
        "frame-ancestors 'none';"
    )

    # 默认权限策略
    DEFAULT_PERMISSIONS_POLICY = (
        "accelerometer=(), "
        "camera=(), "
        "geolocation=(), "
        "gyroscope=(), "
        "magnetometer=(), "
        "microphone=(), "
        "payment=(), "
        "usb=()"
    )

    def __init__(
        self,
        app: ASGIApp,
        csp_policy: str | None = None,
        hsts_max_age: int = 31536000,  # 1 year
        enable_hsts: bool = False,
    ):
        """
        初始化安全响应头中间件。

        Args:
            app: ASGI 应用实例
            csp_policy: 自定义 CSP 策略，为 None 时使用默认策略
            hsts_max_age: HSTS 最大年龄（秒），默认 1 年
            enable_hsts: 是否启用 HSTS，默认 False（仅 HTTPS 环境启用）
        """
        super().__init__(app)
        self.csp_policy = csp_policy or self.DEFAULT_CSP_POLICY
        self.hsts_max_age = hsts_max_age
        self.enable_hsts = enable_hsts

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求并添加安全响应头。

        Args:
            request: FastAPI 请求对象
            call_next: 下一个中间件或路由处理器

        Returns:
            Response: 添加了安全头的响应对象
        """
        response = await call_next(request)

        # 防止 MIME 类型嗅探
        response.headers["X-Content-Type-Options"] = "nosniff"

        # 防止点击劫持
        response.headers["X-Frame-Options"] = "DENY"

        # XSS 保护（主要针对旧浏览器）
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # 引用策略
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 权限策略
        response.headers["Permissions-Policy"] = self.DEFAULT_PERMISSIONS_POLICY

        # 内容安全策略（仅对 HTML 响应）
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            response.headers["Content-Security-Policy"] = self.csp_policy

        # HSTS（仅 HTTPS 环境）
        if self.enable_hsts and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                f"max-age={self.hsts_max_age}; includeSubDomains; preload"
            )

        # API 响应禁用缓存
        if self._is_api_path(request.url.path):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"

        return response

    @staticmethod
    def _is_api_path(path: str) -> bool:
        """
        检查路径是否为 API 路径。

        Args:
            path: 请求路径

        Returns:
            bool: 是否为 API 路径
        """
        return path.startswith("/api/") or path.startswith("/ws/")


def get_csp_policy_for_environment(env: str = "development") -> str:
    """
    根据环境获取 CSP 策略。

    Args:
        env: 环境名称（development/staging/production）

    Returns:
        str: CSP 策略字符串

    Note:
        开发环境允许更多来源以便调试
        生产环境使用更严格的策略
    """
    if env == "production":
        return (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self' wss:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
    elif env == "staging":
        return (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none';"
        )
    else:  # development
        return (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self' ws: wss: http://localhost:* http://127.0.0.1:*; "
            "frame-ancestors 'none';"
        )


def create_security_headers_middleware(
    env: str = "development",
    enable_hsts: bool = False,
) -> type[SecurityHeadersMiddleware]:
    """
    创建配置好的安全头中间件类。

    Args:
        env: 环境名称
        enable_hsts: 是否启用 HSTS

    Returns:
        type[SecurityHeadersMiddleware]: 配置好的中间件类

    Example:
        >>> middleware = create_security_headers_middleware("production", True)
        >>> app.add_middleware(middleware)
    """
    csp_policy = get_csp_policy_for_environment(env)

    class ConfiguredSecurityHeadersMiddleware(SecurityHeadersMiddleware):
        """配置好的安全头中间件。"""

        def __init__(self, app: ASGIApp):
            super().__init__(
                app,
                csp_policy=csp_policy,
                enable_hsts=enable_hsts,
            )

    return ConfiguredSecurityHeadersMiddleware


# 预定义的安全头配置
SECURITY_HEADERS_CONFIG: dict[str, dict[str, Any]] = {
    "development": {
        "csp_policy": get_csp_policy_for_environment("development"),
        "enable_hsts": False,
    },
    "staging": {
        "csp_policy": get_csp_policy_for_environment("staging"),
        "enable_hsts": False,
    },
    "production": {
        "csp_policy": get_csp_policy_for_environment("production"),
        "enable_hsts": True,
    },
}


def get_security_config(env: str = "development") -> dict[str, Any]:
    """
    获取指定环境的安全配置。

    Args:
        env: 环境名称

    Returns:
        dict: 安全配置字典
    """
    return SECURITY_HEADERS_CONFIG.get(env, SECURITY_HEADERS_CONFIG["development"])
