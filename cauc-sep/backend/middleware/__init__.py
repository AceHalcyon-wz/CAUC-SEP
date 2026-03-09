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
    AuditMiddleware,
    AuditLogger,
    audit_logger,
    log_alarm_event,
    log_device_event,
)

# 安全模块（原有）
from .security import (
    RateLimitMiddleware as _RateLimitMiddleware,
    RateLimiter as _RateLimiter,
    SecurityHeadersMiddleware,
    sanitize_dict,
    sanitize_string,
    sanitize_filename as _sanitize_filename,
    mask_sensitive_value,
    validate_device_id,
    validate_experiment_id,
    validate_array_length,
    validate_string_length,
    get_client_ip,
    get_rate_limiter as _get_rate_limiter,
    log_security_event as _log_security_event,
    SENSITIVE_FIELDS,
    SENSITIVE_PATTERNS,
)

# JWT认证模块
from .jwt_auth import (
    # 令牌管理
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
    get_password_hash,
    refresh_access_token,
    revoke_token,
    # 权限控制
    Permission,
    ROLE_PERMISSIONS,
    has_permission,
    require_permissions,
    require_role,
    # 黑名单
    TokenBlacklist,
    get_token_blacklist,
    # 可选认证
    get_current_user_optional,
    # 令牌负载
    TokenPayload,
    # 日志
    log_auth_event,
    # 配置
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_HOURS,
    REFRESH_TOKEN_EXPIRE_DAYS,
)

# 速率限制模块
from .rate_limit import (
    RateLimitMiddleware,
    RateLimiter,
    RateLimitConfig,
    RateLimitStrategy,
    RateLimitScope,
    get_rate_limiter,
    reset_rate_limiter,
    rate_limit,
)

# 验证模块
from .validation import (
    # XSS过滤
    sanitize_html,
    strip_xss,
    sanitize_input,
    # SQL注入防护
    detect_sql_injection,
    sanitize_sql_input,
    validate_identifier,
    # 路径安全
    sanitize_filename,
    sanitize_path,
    # 敏感数据
    detect_sensitive_data,
    mask_sensitive_data,
    # 综合验证
    ValidationResult,
    validate_request_data,
    # 安全日志
    log_security_event,
    # Pydantic验证器
    create_pydantic_validator,
)

# CORS配置模块
from .cors_config import (
    CORSConfig,
    CORSEnvironment,
    OriginValidator,
    SecureCORSMiddleware,
    get_cors_config,
    setup_cors,
    create_cors_middleware,
    validate_cors_security,
    log_cors_config,
    DEFAULT_ALLOW_METHODS,
    DEFAULT_ALLOW_HEADERS,
    DEFAULT_EXPOSE_HEADERS,
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
