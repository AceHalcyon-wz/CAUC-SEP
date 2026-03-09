"""
中间件模块

功能：
- 审计日志中间件
- 安全中间件（速率限制、安全响应头）
- JWT认证中间件
- CORS安全配置
- 输入验证增强
- 敏感信息脱敏

作者：Backend Engineer Agent
更新日期：2026-03-08
"""

# 审计模块
from .audit import (
    AuditLogger,
    AuditMiddleware,
    audit_logger,
    log_alarm_event,
    log_device_event,
)

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
from .jwt_auth import (  # 令牌管理; 权限控制; 黑名单; 可选认证; 令牌负载; 日志; 配置
    ACCESS_TOKEN_EXPIRE_HOURS,
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
)
from .security import RateLimiter as _RateLimiter
from .security import RateLimitMiddleware as _RateLimitMiddleware
from .security import (
    SecurityHeadersMiddleware,
    get_client_ip,
)
from .security import get_rate_limiter as _get_rate_limiter
from .security import log_security_event as _log_security_event
from .security import (
    mask_sensitive_value,
    sanitize_dict,
)
from .security import sanitize_filename as _sanitize_filename
from .security import (
    sanitize_string,
    validate_array_length,
    validate_device_id,
    validate_experiment_id,
    validate_string_length,
)

# 验证模块
from .validation import (  # XSS过滤; SQL注入防护; 路径安全; 敏感数据; 综合验证; 安全日志; Pydantic验证器
    ValidationResult,
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
]
