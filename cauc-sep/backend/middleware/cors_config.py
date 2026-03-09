"""
CORS安全配置模块

功能：
- 安全的CORS策略配置
- 动态源验证
- 预检请求缓存
- 凭证传递控制
- 环境感知配置

安全特性：
- 防止CORS滥用
- 防止CSRF攻击
- 支持白名单验证
- 支持正则匹配

作者: Backend Engineer Agent
创建日期: 2026-03-08
依赖: fastapi
"""

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


# ==================== 配置常量 ====================

# 默认允许的方法
DEFAULT_ALLOW_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]

# 默认允许的头
DEFAULT_ALLOW_HEADERS = [
    "Content-Type",
    "Authorization",
    "X-Requested-With",
    "Accept",
    "Origin",
    "X-RateLimit-Remaining",
    "X-RateLimit-Reset",
    "X-Request-ID",
    "X-API-Key",
]

# 默认暴露的头
DEFAULT_EXPOSE_HEADERS = [
    "X-RateLimit-Remaining",
    "X-RateLimit-Reset",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "X-Request-ID",
]

# 预检请求缓存时间（秒）
DEFAULT_MAX_AGE = 600


class CORSEnvironment(str, Enum):
    """
    CORS环境枚举。
    """
    
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


# ==================== 数据结构 ====================


@dataclass
class CORSConfig:
    """
    CORS配置。
    
    Attributes:
        allow_origins: 允许的源列表
        allow_origin_regex: 允许的源正则表达式
        allow_methods: 允许的HTTP方法
        allow_headers: 允许的请求头
        expose_headers: 暴露的响应头
        allow_credentials: 是否允许凭证
        max_age: 预检请求缓存时间
    """
    
    allow_origins: list[str] = field(default_factory=list)
    allow_origin_regex: str | None = None
    allow_methods: list[str] = field(default_factory=lambda: DEFAULT_ALLOW_METHODS.copy())
    allow_headers: list[str] = field(default_factory=lambda: DEFAULT_ALLOW_HEADERS.copy())
    expose_headers: list[str] = field(default_factory=lambda: DEFAULT_EXPOSE_HEADERS.copy())
    allow_credentials: bool = True
    max_age: int = DEFAULT_MAX_AGE


# ==================== 环境配置 ====================


# 开发环境允许的源
DEV_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",  # Vite默认端口
    "http://localhost:8080",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:8000",
]

# 生产环境示例（应从环境变量读取）
PROD_ORIGINS_EXAMPLE = [
    "https://cauc-sep.example.com",
    "https://api.cauc-sep.example.com",
]


def get_cors_config(environment: CORSEnvironment | None = None) -> CORSConfig:
    """
    根据环境获取CORS配置。
    
    Args:
        environment: 环境类型
    
    Returns:
        CORSConfig: CORS配置对象
    """
    # 从环境变量获取当前环境
    if environment is None:
        env_str = os.environ.get("APP_ENV", "development").lower()
        environment = CORSEnvironment(env_str) if env_str in [e.value for e in CORSEnvironment] else CORSEnvironment.DEVELOPMENT
    
    # 从环境变量获取允许的源
    cors_origins_env = os.environ.get("CORS_ORIGINS", "")
    custom_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
    
    # 从环境变量获取正则表达式
    cors_origin_regex = os.environ.get("CORS_ORIGIN_REGEX", "")
    
    # 是否允许凭证
    allow_credentials = os.environ.get("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
    
    # 预检缓存时间
    max_age = int(os.environ.get("CORS_MAX_AGE", str(DEFAULT_MAX_AGE)))
    
    # 根据环境选择默认源
    if custom_origins:
        allow_origins = custom_origins
    elif environment == CORSEnvironment.PRODUCTION:
        allow_origins = []  # 生产环境必须显式配置
        logger.warning("Production environment without CORS_ORIGINS configured")
    else:
        allow_origins = DEV_ORIGINS
    
    return CORSConfig(
        allow_origins=allow_origins,
        allow_origin_regex=cors_origin_regex if cors_origin_regex else None,
        allow_credentials=allow_credentials,
        max_age=max_age,
    )


# ==================== 源验证 ====================


class OriginValidator:
    """
    源验证器。
    
    支持精确匹配和正则表达式匹配。
    支持动态源验证。
    
    Example:
        >>> validator = OriginValidator(
        ...     allow_origins=["https://example.com"],
        ...     allow_origin_regex=r"https://.*\.example\.com"
        ... )
        >>> validator.is_allowed("https://sub.example.com")
        True
    """
    
    def __init__(
        self,
        allow_origins: list[str] | None = None,
        allow_origin_regex: str | None = None,
        custom_validator: Callable[[str], bool] | None = None,
    ):
        """
        初始化源验证器。
        
        Args:
            allow_origins: 允许的源列表
            allow_origin_regex: 允许的源正则表达式
            custom_validator: 自定义验证函数
        """
        self.allow_origins = set(allow_origins or [])
        self.allow_origin_regex = re.compile(allow_origin_regex) if allow_origin_regex else None
        self.custom_validator = custom_validator
        
        # 预编译常见源模式
        self._compiled_origins = {}
        for origin in self.allow_origins:
            # 支持通配符
            if "*" in origin:
                pattern = origin.replace(".", r"\.").replace("*", ".*")
                self._compiled_origins[origin] = re.compile(f"^{pattern}$")
    
    def is_allowed(self, origin: str) -> bool:
        """
        检查源是否被允许。
        
        Args:
            origin: 请求源
        
        Returns:
            bool: 是否被允许
        """
        if not origin:
            return False
        
        # 精确匹配
        if origin in self.allow_origins:
            return True
        
        # 通配符匹配
        for origin_pattern, compiled in self._compiled_origins.items():
            if compiled.match(origin):
                return True
        
        # 正则匹配
        if self.allow_origin_regex and self.allow_origin_regex.match(origin):
            return True
        
        # 自定义验证
        if self.custom_validator and self.custom_validator(origin):
            return True
        
        return False
    
    def add_origin(self, origin: str) -> None:
        """
        添加允许的源。
        
        Args:
            origin: 源URL
        """
        self.allow_origins.add(origin)
        if "*" in origin:
            pattern = origin.replace(".", r"\.").replace("*", ".*")
            self._compiled_origins[origin] = re.compile(f"^{pattern}$")
    
    def remove_origin(self, origin: str) -> None:
        """
        移除允许的源。
        
        Args:
            origin: 源URL
        """
        self.allow_origins.discard(origin)
        if origin in self._compiled_origins:
            del self._compiled_origins[origin]


# ==================== CORS中间件增强 ====================


class SecureCORSMiddleware(BaseHTTPMiddleware):
    """
    安全CORS中间件。
    
    提供比FastAPI内置CORSMiddleware更细粒度的控制：
    - 动态源验证
    - 请求日志
    - 安全头注入
    - 预检请求缓存
    
    Example:
        >>> app.add_middleware(
        ...     SecureCORSMiddleware,
        ...     config=get_cors_config()
        ... )
    """
    
    def __init__(
        self,
        app: ASGIApp,
        config: CORSConfig | None = None,
        enable_logging: bool = True,
    ):
        """
        初始化安全CORS中间件。
        
        Args:
            app: ASGI应用实例
            config: CORS配置
            enable_logging: 是否启用日志
        """
        super().__init__(app)
        self.config = config or get_cors_config()
        self.enable_logging = enable_logging
        
        # 创建源验证器
        self.validator = OriginValidator(
            allow_origins=self.config.allow_origins,
            allow_origin_regex=self.config.allow_origin_regex,
        )
        
        # 预检请求缓存
        self._preflight_cache: dict[str, tuple[float, dict[str, str]]] = {}
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        处理请求。
        
        Args:
            request: FastAPI请求对象
            call_next: 下一个处理器
        
        Returns:
            Response: 响应对象
        """
        origin = request.headers.get("origin", "")
        
        # 处理预检请求
        if request.method == "OPTIONS":
            return self._handle_preflight(request, origin)
        
        # 处理实际请求
        response = await call_next(request)
        
        # 添加CORS头
        if origin and self.validator.is_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = str(self.config.allow_credentials).lower()
            
            if self.config.expose_headers:
                response.headers["Access-Control-Expose-Headers"] = ", ".join(self.config.expose_headers)
        
        # 记录日志
        if self.enable_logging and origin:
            self._log_request(request, origin)
        
        return response
    
    def _handle_preflight(self, request: Request, origin: str):
        """
        处理预检请求。
        
        Args:
            request: FastAPI请求对象
            origin: 请求源
        
        Returns:
            Response: 预检响应
        """
        from fastapi import Response
        
        # 检查源是否被允许
        if not origin or not self.validator.is_allowed(origin):
            if self.enable_logging:
                logger.warning(f"CORS preflight rejected: origin={origin}")
            return Response(status_code=403, content="Origin not allowed")
        
        # 检查缓存
        cache_key = f"{origin}:{request.headers.get('access-control-request-method', '')}"
        if cache_key in self._preflight_cache:
            cached_time, cached_headers = self._preflight_cache[cache_key]
            if datetime.now().timestamp() - cached_time < self.config.max_age:
                response = Response(status_code=204)
                for key, value in cached_headers.items():
                    response.headers[key] = value
                return response
        
        # 构建响应头
        headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": ", ".join(self.config.allow_methods),
            "Access-Control-Allow-Headers": ", ".join(self.config.allow_headers),
            "Access-Control-Allow-Credentials": str(self.config.allow_credentials).lower(),
            "Access-Control-Max-Age": str(self.config.max_age),
        }
        
        # 缓存响应
        self._preflight_cache[cache_key] = (datetime.now().timestamp(), headers)
        
        # 清理过期缓存
        self._cleanup_cache()
        
        response = Response(status_code=204)
        for key, value in headers.items():
            response.headers[key] = value
        
        return response
    
    def _cleanup_cache(self) -> None:
        """
        清理过期的预检缓存。
        """
        now = datetime.now().timestamp()
        expired_keys = [
            key for key, (time, _) in self._preflight_cache.items()
            if now - time > self.config.max_age
        ]
        for key in expired_keys:
            del self._preflight_cache[key]
    
    def _log_request(self, request: Request, origin: str) -> None:
        """
        记录请求日志。
        
        Args:
            request: FastAPI请求对象
            origin: 请求源
        """
        logger.debug(
            f"CORS request: method={request.method}, "
            f"path={request.url.path}, origin={origin}"
        )


# ==================== 便捷函数 ====================


def setup_cors(
    app: FastAPI,
    environment: CORSEnvironment | None = None,
    custom_origins: list[str] | None = None,
    allow_credentials: bool = True,
    max_age: int = DEFAULT_MAX_AGE,
) -> None:
    """
    配置FastAPI应用的CORS。
    
    Args:
        app: FastAPI应用实例
        environment: 环境类型
        custom_origins: 自定义允许的源
        allow_credentials: 是否允许凭证
        max_age: 预检请求缓存时间
    
    Example:
        >>> app = FastAPI()
        >>> setup_cors(app, environment=CORSEnvironment.DEVELOPMENT)
    """
    config = get_cors_config(environment)
    
    # 覆盖自定义配置
    if custom_origins:
        config.allow_origins = custom_origins
    
    config.allow_credentials = allow_credentials
    config.max_age = max_age
    
    # 添加FastAPI内置CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.allow_origins,
        allow_origin_regex=config.allow_origin_regex,
        allow_methods=config.allow_methods,
        allow_headers=config.allow_headers,
        expose_headers=config.expose_headers,
        allow_credentials=config.allow_credentials,
        max_age=config.max_age,
    )
    
    # 记录配置
    logger.info(
        f"CORS configured: origins={len(config.allow_origins)}, "
        f"credentials={config.allow_credentials}, max_age={config.max_age}"
    )


def create_cors_middleware(
    allow_origins: list[str],
    allow_credentials: bool = True,
    **kwargs,
) -> Callable:
    """
    创建CORS中间件工厂函数。
    
    Args:
        allow_origins: 允许的源列表
        allow_credentials: 是否允许凭证
        **kwargs: 其他配置参数
    
    Returns:
        Callable: 中间件配置函数
    
    Example:
        >>> cors_middleware = create_cors_middleware(
        ...     allow_origins=["https://example.com"],
        ...     allow_credentials=True
        ... )
        >>> app.add_middleware(*cors_middleware())
    """
    def middleware_factory():
        return (
            CORSMiddleware,
            {
                "allow_origins": allow_origins,
                "allow_credentials": allow_credentials,
                "allow_methods": kwargs.get("allow_methods", DEFAULT_ALLOW_METHODS),
                "allow_headers": kwargs.get("allow_headers", DEFAULT_ALLOW_HEADERS),
                "expose_headers": kwargs.get("expose_headers", DEFAULT_EXPOSE_HEADERS),
                "max_age": kwargs.get("max_age", DEFAULT_MAX_AGE),
            },
        )
    
    return middleware_factory


# ==================== 安全检查 ====================


def validate_cors_security(config: CORSConfig) -> list[str]:
    """
    验证CORS配置的安全性。
    
    Args:
        config: CORS配置
    
    Returns:
        list[str]: 安全警告列表
    """
    warnings = []
    
    # 检查是否使用通配符源
    if "*" in config.allow_origins:
        if config.allow_credentials:
            warnings.append(
                "严重: allow_origins=['*'] 与 allow_credentials=True 组合是不安全的，"
                "可能导致CSRF攻击"
            )
        else:
            warnings.append(
                "警告: allow_origins=['*'] 允许任意源访问，仅适用于公开API"
            )
    
    # 检查是否在生产环境使用开发源
    dev_patterns = ["localhost", "127.0.0.1", "0.0.0.0"]
    for origin in config.allow_origins:
        if any(pattern in origin for pattern in dev_patterns):
            warnings.append(
                f"警告: 源 '{origin}' 包含开发环境地址，不应在生产环境使用"
            )
    
    # 检查是否使用HTTP（非HTTPS）
    for origin in config.allow_origins:
        if origin.startswith("http://") and "localhost" not in origin and "127.0.0.1" not in origin:
            warnings.append(
                f"警告: 源 '{origin}' 使用HTTP而非HTTPS，存在中间人攻击风险"
            )
    
    # 检查是否暴露敏感头
    sensitive_headers = {"authorization", "cookie", "set-cookie"}
    for header in config.expose_headers:
        if header.lower() in sensitive_headers:
            warnings.append(
                f"警告: 暴露敏感头 '{header}' 可能导致信息泄露"
            )
    
    return warnings


def log_cors_config(config: CORSConfig) -> None:
    """
    记录CORS配置日志。
    
    Args:
        config: CORS配置
    """
    # 验证安全性
    warnings = validate_cors_security(config)
    
    for warning in warnings:
        logger.warning(warning)
    
    # 记录配置详情
    logger.info(
        f"CORS Configuration: "
        f"origins={config.allow_origins}, "
        f"methods={config.allow_methods}, "
        f"credentials={config.allow_credentials}, "
        f"max_age={config.max_age}"
    )
