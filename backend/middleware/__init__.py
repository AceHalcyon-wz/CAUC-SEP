"""
中间件模块

功能：
- 审计日志中间件：记录所有API请求和关键操作
- 安全中间件：速率限制、安全响应头
- JWT认证中间件：令牌验证、权限控制
- CORS安全配置：跨域资源共享策略
- 输入验证增强：XSS过滤、SQL注入防护
- 敏感信息脱敏：自动识别和脱敏敏感数据
- 全局异常处理器：统一错误响应格式
- 安全响应头中间件：添加 CSP、X-Frame-Options 等安全头

作者：Backend Engineer Agent
创建日期：2026-03-08
更新日期：2026-03-16
依赖：fastapi, starlette, python-jose, passlib, redis (可选), structlog

使用示例：
    >>> from middleware import setup_cors, RateLimitMiddleware, register_exception_handlers
    >>> app = FastAPI()
    >>> setup_cors(app)
    >>> app.add_middleware(RateLimitMiddleware)
    >>> register_exception_handlers(app)
"""

# 审计模块
from .audit import AuditLogger, AuditMiddleware, audit_logger, log_alarm_event, log_device_event

# CORS配置模块
from .cors_config import (
    DEFAULT_ALLOW_HEADERS,
    DEFAULT_ALLOW_METHODS,
    DEFAULT_EXPOSE_HEADERS,
    CORSConfig,
    CORSEnvironment,
    OriginValidator,
    SecureCORSMiddleware,
    create_cors_middleware,
    get_cors_config,
    log_cors_config,
    setup_cors,
    validate_cors_security,
)

# JWT认证模块
from .jwt_auth import (
    ACCESS_TOKEN_EXPIRE_HOURS,  # 令牌管理; 权限控制; 黑名单; 可选认证; 令牌负载; 日志; 配置
    ALGORITHM,
    REFRESH_TOKEN_EXPIRE_DAYS,
    ROLE_PERMISSIONS,
    SECRET_KEY,
    Permission,
    TokenBlacklist,
    TokenPayload,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user_optional,
    get_password_hash,
    get_token_blacklist,
    has_permission,
    log_auth_event,
    refresh_access_token,
    require_permissions,
    require_role,
    revoke_token,
    verify_password,
)

# 速率限制模块
from .rate_limit import (
    RateLimitConfig,
    RateLimiter,
    RateLimitMiddleware,
    RateLimitScope,
    RateLimitStrategy,
    get_rate_limiter,
    rate_limit,
    reset_rate_limiter,
)

# 安全模块（原有）
from .security import (
    SENSITIVE_FIELDS,
    SENSITIVE_PATTERNS,
    SecurityHeadersMiddleware,
    get_client_ip,
    mask_sensitive_value,
    sanitize_dict,
    sanitize_string,
    validate_array_length,
    validate_device_id,
    validate_experiment_id,
    validate_string_length,
)
from .security import RateLimiter as _RateLimiter
from .security import RateLimitMiddleware as _RateLimitMiddleware
from .security import get_rate_limiter as _get_rate_limiter
from .security import log_security_event as _log_security_event
from .security import sanitize_filename as _sanitize_filename

# 验证模块
from .validation import (
    ValidationResult,  # XSS过滤; SQL注入防护; 路径安全; 敏感数据; 综合验证; 安全日志; Pydantic验证器
    create_pydantic_validator,
    detect_sensitive_data,
    detect_sql_injection,
    log_security_event,
    mask_sensitive_data,
    sanitize_filename,
    sanitize_html,
    sanitize_input,
    sanitize_path,
    sanitize_sql_input,
    strip_xss,
    validate_identifier,
    validate_request_data,
)

# 异常处理模块
from .exception_handler import (
    app_exception_handler,
    generic_exception_handler,
    get_timestamp,
    register_exception_handlers,
    validation_exception_handler,
)

# 安全响应头模块
from .security_headers import (
    SECURITY_HEADERS_CONFIG,
    SecurityHeadersMiddleware,
    create_security_headers_middleware,
    get_csp_policy_for_environment,
    get_security_config,
)

__all__ = [
    # ==================== 审计模块 ====================
    "AuditMiddleware",
    "AuditLogger",
    "audit_logger",
    "log_alarm_event",
    "log_device_event",
    # ==================== 安全响应头 ====================
    "SecurityHeadersMiddleware",
    # ==================== 速率限制 ====================
    "RateLimitMiddleware",
    "RateLimiter",
    "RateLimitConfig",
    "RateLimitStrategy",
    "RateLimitScope",
    "get_rate_limiter",
    "reset_rate_limiter",
    "rate_limit",
    # ==================== JWT认证 ====================
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "verify_password",
    "get_password_hash",
    "refresh_access_token",
    "revoke_token",
    "Permission",
    "ROLE_PERMISSIONS",
    "has_permission",
    "require_permissions",
    "require_role",
    "TokenBlacklist",
    "get_token_blacklist",
    "get_current_user_optional",
    "TokenPayload",
    "log_auth_event",
    "SECRET_KEY",
    "ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_HOURS",
    "REFRESH_TOKEN_EXPIRE_DAYS",
    # ==================== 输入验证 ====================
    "sanitize_html",
    "strip_xss",
    "sanitize_input",
    "detect_sql_injection",
    "sanitize_sql_input",
    "validate_identifier",
    "sanitize_filename",
    "sanitize_path",
    "detect_sensitive_data",
    "mask_sensitive_data",
    "ValidationResult",
    "validate_request_data",
    "log_security_event",
    "create_pydantic_validator",
    # ==================== CORS配置 ====================
    "CORSConfig",
    "CORSEnvironment",
    "OriginValidator",
    "SecureCORSMiddleware",
    "get_cors_config",
    "setup_cors",
    "create_cors_middleware",
    "validate_cors_security",
    "log_cors_config",
    "DEFAULT_ALLOW_METHODS",
    "DEFAULT_ALLOW_HEADERS",
    "DEFAULT_EXPOSE_HEADERS",
    # ==================== 脱敏函数 ====================
    "sanitize_dict",
    "sanitize_string",
    "mask_sensitive_value",
    # ==================== 验证函数 ====================
    "validate_device_id",
    "validate_experiment_id",
    "validate_array_length",
    "validate_string_length",
    # ==================== 辅助函数 ====================
    "get_client_ip",
    # ==================== 常量 ====================
    "SENSITIVE_FIELDS",
    "SENSITIVE_PATTERNS",
    # ==================== 异常处理 ====================
    "register_exception_handlers",
    "app_exception_handler",
    "validation_exception_handler",
    "generic_exception_handler",
    "get_timestamp",
    # ==================== 安全响应头 ====================
    "SecurityHeadersMiddleware",
    "create_security_headers_middleware",
    "get_csp_policy_for_environment",
    "get_security_config",
    "SECURITY_HEADERS_CONFIG",
]
