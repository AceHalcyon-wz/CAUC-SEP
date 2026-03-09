"""
JWT认证中间件模块

功能：
- JWT令牌验证与解析
- 令牌刷新机制
- 角色权限控制（RBAC）
- 令牌黑名单管理
- 安全事件日志

安全特性：
- 支持访问令牌和刷新令牌
- 令牌过期自动刷新
- 基于角色的访问控制
- 防止令牌重放攻击

作者: Backend Engineer Agent
创建日期: 2026-03-08
依赖: python-jose, passlib
"""

import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)


# ==================== 配置常量 ====================

# JWT配置
SECRET_KEY = os.environ.get(
    "JWT_SECRET_KEY",
    "cauc-sep-jwt-secret-key-change-in-production-2026-secure"
)
ALGORITHM = "HS256"

# 令牌过期时间
ACCESS_TOKEN_EXPIRE_HOURS = int(os.environ.get("ACCESS_TOKEN_EXPIRE_HOURS", "24"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# 密码哈希配置
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer认证
security = HTTPBearer()


# ==================== 角色权限定义 ====================


class Permission(str, Enum):
    """
    权限枚举。
    
    定义系统中所有可用的权限。
    """
    
    # 设备控制权限
    DEVICE_READ = "device:read"
    DEVICE_WRITE = "device:write"
    DEVICE_CONTROL = "device:control"
    DEVICE_CALIBRATE = "device:calibrate"
    
    # 实验管理权限
    EXPERIMENT_READ = "experiment:read"
    EXPERIMENT_WRITE = "experiment:write"
    EXPERIMENT_DELETE = "experiment:delete"
    EXPERIMENT_EXPORT = "experiment:export"
    
    # 数据分析权限
    ANALYSIS_READ = "analysis:read"
    ANALYSIS_WRITE = "analysis:write"
    
    # 用户管理权限
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    
    # 系统管理权限
    SYSTEM_CONFIG = "system:config"
    SYSTEM_LOGS = "system:logs"
    SYSTEM_HEALTH = "system:health"
    
    # 敏感操作权限
    EMERGENCY_STOP = "operation:emergency_stop"
    FACTORY_RESET = "operation:factory_reset"


# 角色权限映射
ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    "admin": {
        # 管理员拥有所有权限
        Permission.DEVICE_READ,
        Permission.DEVICE_WRITE,
        Permission.DEVICE_CONTROL,
        Permission.DEVICE_CALIBRATE,
        Permission.EXPERIMENT_READ,
        Permission.EXPERIMENT_WRITE,
        Permission.EXPERIMENT_DELETE,
        Permission.EXPERIMENT_EXPORT,
        Permission.ANALYSIS_READ,
        Permission.ANALYSIS_WRITE,
        Permission.USER_READ,
        Permission.USER_WRITE,
        Permission.USER_DELETE,
        Permission.SYSTEM_CONFIG,
        Permission.SYSTEM_LOGS,
        Permission.SYSTEM_HEALTH,
        Permission.EMERGENCY_STOP,
        Permission.FACTORY_RESET,
    },
    "user": {
        # 普通用户权限
        Permission.DEVICE_READ,
        Permission.DEVICE_WRITE,
        Permission.DEVICE_CONTROL,
        Permission.EXPERIMENT_READ,
        Permission.EXPERIMENT_WRITE,
        Permission.EXPERIMENT_EXPORT,
        Permission.ANALYSIS_READ,
        Permission.ANALYSIS_WRITE,
        Permission.SYSTEM_HEALTH,
        Permission.EMERGENCY_STOP,
    },
    "guest": {
        # 访客权限（只读）
        Permission.DEVICE_READ,
        Permission.EXPERIMENT_READ,
        Permission.ANALYSIS_READ,
        Permission.SYSTEM_HEALTH,
    },
}


# ==================== 令牌黑名单管理 ====================


@dataclass
class TokenBlacklistEntry:
    """
    令牌黑名单条目。
    
    Attributes:
        jti: 令牌唯一标识
        reason: 加入黑名单的原因
        expires_at: 过期时间
        created_at: 创建时间
    """
    
    jti: str
    reason: str
    expires_at: datetime
    created_at: datetime = field(default_factory=datetime.now)


class TokenBlacklist:
    """
    令牌黑名单管理器。
    
    内存存储实现，生产环境建议使用Redis。
    支持自动清理过期条目。
    
    Example:
        >>> blacklist = TokenBlacklist()
        >>> blacklist.add(jti="abc123", reason="logout", expires_in=3600)
        >>> blacklist.contains("abc123")
        True
    """
    
    def __init__(self, cleanup_interval: int = 3600):
        """
        初始化令牌黑名单。
        
        Args:
            cleanup_interval: 清理间隔（秒），默认1小时
        """
        self._entries: dict[str, TokenBlacklistEntry] = {}
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = datetime.now()
    
    def add(
        self,
        jti: str,
        reason: str = "logout",
        expires_in: int | None = None,
    ) -> None:
        """
        添加令牌到黑名单。
        
        Args:
            jti: 令牌唯一标识
            reason: 加入原因
            expires_in: 过期时间（秒），默认使用刷新令牌过期时间
        """
        if expires_in is None:
            expires_in = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
        
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        self._entries[jti] = TokenBlacklistEntry(
            jti=jti,
            reason=reason,
            expires_at=expires_at,
        )
        
        logger.debug(f"Token added to blacklist: jti={jti[:8]}..., reason={reason}")
        
        # 自动清理
        self._maybe_cleanup()
    
    def contains(self, jti: str) -> bool:
        """
        检查令牌是否在黑名单中。
        
        Args:
            jti: 令牌唯一标识
        
        Returns:
            bool: 是否在黑名单中
        """
        entry = self._entries.get(jti)
        if entry is None:
            return False
        
        # 检查是否过期
        if entry.expires_at < datetime.now():
            del self._entries[jti]
            return False
        
        return True
    
    def remove(self, jti: str) -> bool:
        """
        从黑名单移除令牌。
        
        Args:
            jti: 令牌唯一标识
        
        Returns:
            bool: 是否成功移除
        """
        if jti in self._entries:
            del self._entries[jti]
            return True
        return False
    
    def _maybe_cleanup(self) -> int:
        """
        如果需要，清理过期条目。
        
        Returns:
            int: 清理的条目数量
        """
        now = datetime.now()
        
        # 检查是否需要清理
        if (now - self._last_cleanup).total_seconds() < self._cleanup_interval:
            return 0
        
        self._last_cleanup = now
        
        # 清理过期条目
        expired_jtis = [
            jti for jti, entry in self._entries.items()
            if entry.expires_at < now
        ]
        
        for jti in expired_jtis:
            del self._entries[jti]
        
        if expired_jtis:
            logger.debug(f"Cleaned up {len(expired_jtis)} expired blacklist entries")
        
        return len(expired_jtis)
    
    def get_stats(self) -> dict[str, Any]:
        """
        获取黑名单统计信息。
        
        Returns:
            dict: 统计信息
        """
        now = datetime.now()
        active_count = sum(
            1 for entry in self._entries.values()
            if entry.expires_at >= now
        )
        
        return {
            "total_entries": len(self._entries),
            "active_entries": active_count,
            "last_cleanup": self._last_cleanup.isoformat(),
        }


# 全局令牌黑名单实例
_token_blacklist = TokenBlacklist()


def get_token_blacklist() -> TokenBlacklist:
    """
    获取全局令牌黑名单实例。
    
    Returns:
        TokenBlacklist: 黑名单实例
    """
    return _token_blacklist


# ==================== 令牌管理 ====================


@dataclass
class TokenPayload:
    """
    令牌负载数据。
    
    Attributes:
        sub: 用户ID
        jti: 令牌唯一标识
        exp: 过期时间
        iat: 签发时间
        type: 令牌类型（access/refresh）
        role: 用户角色
        permissions: 权限列表
    """
    
    sub: int
    jti: str
    exp: datetime
    iat: datetime
    type: str = "access"
    role: str = "user"
    permissions: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "sub": self.sub,
            "jti": self.jti,
            "exp": self.exp.timestamp(),
            "iat": self.iat.timestamp(),
            "type": self.type,
            "role": self.role,
            "permissions": self.permissions,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TokenPayload":
        """从字典创建。"""
        return cls(
            sub=data["sub"],
            jti=data["jti"],
            exp=datetime.fromtimestamp(data["exp"]),
            iat=datetime.fromtimestamp(data["iat"]),
            type=data.get("type", "access"),
            role=data.get("role", "user"),
            permissions=data.get("permissions", []),
        )


def create_access_token(
    user_id: int,
    role: str = "user",
    expires_delta: timedelta | None = None,
) -> str:
    """
    创建访问令牌。
    
    Args:
        user_id: 用户ID
        role: 用户角色
        expires_delta: 过期时间增量
    
    Returns:
        str: JWT访问令牌
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    now = datetime.utcnow()
    expire = now + expires_delta
    
    # 获取角色权限
    permissions = [
        p.value for p in ROLE_PERMISSIONS.get(role, set())
    ]
    
    payload = {
        "sub": user_id,
        "jti": str(uuid.uuid4()),
        "exp": expire,
        "iat": now,
        "type": "access",
        "role": role,
        "permissions": permissions,
    }
    
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(
    user_id: int,
    role: str = "user",
    expires_delta: timedelta | None = None,
) -> str:
    """
    创建刷新令牌。
    
    Args:
        user_id: 用户ID
        role: 用户角色
        expires_delta: 过期时间增量
    
    Returns:
        str: JWT刷新令牌
    """
    if expires_delta is None:
        expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    now = datetime.utcnow()
    expire = now + expires_delta
    
    payload = {
        "sub": user_id,
        "jti": str(uuid.uuid4()),
        "exp": expire,
        "iat": now,
        "type": "refresh",
        "role": role,
    }
    
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> TokenPayload:
    """
    解码JWT令牌。
    
    Args:
        token: JWT令牌
    
    Returns:
        TokenPayload: 令牌负载
    
    Raises:
        HTTPException: 令牌无效或已过期
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # 检查黑名单
        jti = payload.get("jti")
        if jti and _token_blacklist.contains(jti):
            logger.warning(f"Token in blacklist: jti={jti[:8]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌已失效",
                headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
            )
        
        return TokenPayload.from_dict(payload)
    
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码。
    
    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码
    
    Returns:
        bool: 密码是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    生成密码哈希。
    
    Args:
        password: 明文密码
    
    Returns:
        str: 哈希密码
    """
    return pwd_context.hash(password)


# ==================== 权限检查 ====================


def has_permission(role: str, permission: Permission) -> bool:
    """
    检查角色是否拥有指定权限。
    
    Args:
        role: 用户角色
        permission: 需要的权限
    
    Returns:
        bool: 是否拥有权限
    """
    role_perms = ROLE_PERMISSIONS.get(role, set())
    return permission in role_perms


def require_permissions(
    *required_permissions: Permission,
) -> Callable:
    """
    权限检查依赖工厂。
    
    创建一个FastAPI依赖，用于检查用户是否拥有所需权限。
    
    Args:
        *required_permissions: 需要的权限列表
    
    Returns:
        Callable: FastAPI依赖函数
    
    Example:
        >>> @router.get("/admin")
        ... async def admin_endpoint(
        ...     user = Depends(require_permissions(Permission.USER_READ))
        ... ):
        ...     return {"message": "Admin access"}
    """
    async def permission_checker(
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ) -> dict[str, Any]:
        """
        权限检查器。
        
        Args:
            credentials: HTTP Bearer认证凭据
        
        Returns:
            dict: 用户信息
        
        Raises:
            HTTPException: 权限不足
        """
        token = credentials.credentials
        payload = decode_token(token)
        
        # 检查令牌类型
        if payload.type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="需要访问令牌",
                headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
            )
        
        # 检查权限
        user_permissions = set(payload.permissions)
        missing_permissions = [
            p.value for p in required_permissions
            if p.value not in user_permissions
        ]
        
        if missing_permissions:
            logger.warning(
                f"Permission denied: user={payload.sub}, "
                f"missing={missing_permissions}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足: 缺少 {', '.join(missing_permissions)}",
            )
        
        return {
            "user_id": payload.sub,
            "role": payload.role,
            "permissions": payload.permissions,
            "jti": payload.jti,
        }
    
    return permission_checker


def require_role(*allowed_roles: str) -> Callable:
    """
    角色检查依赖工厂。
    
    创建一个FastAPI依赖，用于检查用户是否拥有所需角色。
    
    Args:
        *allowed_roles: 允许的角色列表
    
    Returns:
        Callable: FastAPI依赖函数
    
    Example:
        >>> @router.get("/admin")
        ... async def admin_endpoint(
        ...     user = Depends(require_role("admin"))
        ... ):
        ...     return {"message": "Admin access"}
    """
    async def role_checker(
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ) -> dict[str, Any]:
        """
        角色检查器。
        
        Args:
            credentials: HTTP Bearer认证凭据
        
        Returns:
            dict: 用户信息
        
        Raises:
            HTTPException: 角色不足
        """
        token = credentials.credentials
        payload = decode_token(token)
        
        # 检查令牌类型
        if payload.type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="需要访问令牌",
                headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
            )
        
        # 检查角色
        if payload.role not in allowed_roles:
            logger.warning(
                f"Role denied: user={payload.sub}, "
                f"role={payload.role}, required={allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"角色不足: 需要 {', '.join(allowed_roles)}",
            )
        
        return {
            "user_id": payload.sub,
            "role": payload.role,
            "permissions": payload.permissions,
            "jti": payload.jti,
        }
    
    return role_checker


# ==================== 可选认证 ====================


async def get_current_user_optional(
    request: Request,
) -> dict[str, Any] | None:
    """
    获取当前用户（可选）。
    
    如果请求包含有效令牌，返回用户信息；否则返回None。
    
    Args:
        request: FastAPI请求对象
    
    Returns:
        dict | None: 用户信息或None
    """
    # 尝试从Authorization头获取令牌
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header[7:]  # 移除 "Bearer " 前缀
    
    try:
        payload = decode_token(token)
        return {
            "user_id": payload.sub,
            "role": payload.role,
            "permissions": payload.permissions,
            "jti": payload.jti,
        }
    except HTTPException:
        return None


# ==================== 令牌刷新端点辅助 ====================


def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    """
    使用刷新令牌获取新的访问令牌。
    
    Args:
        refresh_token: 刷新令牌
    
    Returns:
        dict: 包含新访问令牌的响应
    
    Raises:
        HTTPException: 刷新令牌无效
    """
    payload = decode_token(refresh_token)
    
    # 检查令牌类型
    if payload.type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="需要刷新令牌",
        )
    
    # 创建新的访问令牌
    new_access_token = create_access_token(
        user_id=payload.sub,
        role=payload.role,
    )
    
    logger.info(f"Token refreshed: user={payload.sub}")
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_HOURS * 3600,
    }


def revoke_token(token: str, reason: str = "logout") -> bool:
    """
    撤销令牌。
    
    将令牌加入黑名单。
    
    Args:
        token: 要撤销的令牌
        reason: 撤销原因
    
    Returns:
        bool: 是否成功撤销
    """
    try:
        payload = decode_token(token)
        _token_blacklist.add(
            jti=payload.jti,
            reason=reason,
            expires_in=int((payload.exp - datetime.now()).total_seconds()),
        )
        logger.info(f"Token revoked: user={payload.sub}, reason={reason}")
        return True
    except HTTPException:
        return False


# ==================== 安全事件日志 ====================


def log_auth_event(
    event_type: str,
    user_id: int | None,
    detail: str,
    request: Request | None = None,
    severity: str = "info",
) -> None:
    """
    记录认证事件日志。
    
    Args:
        event_type: 事件类型
        user_id: 用户ID
        detail: 详细描述
        request: FastAPI请求对象
        severity: 严重程度
    """
    client_ip = "unknown"
    path = "unknown"
    method = "unknown"
    
    if request:
        try:
            client_ip = request.client.host if request.client else "unknown"
            path = request.url.path
            method = request.method
        except (AttributeError, TypeError):
            pass
    
    log_data = {
        "event_type": event_type,
        "user_id": user_id,
        "client_ip": client_ip,
        "method": method,
        "path": path,
        "detail": detail,
        "severity": severity,
        "timestamp": datetime.now().isoformat(),
    }
    
    if severity == "critical":
        logger.critical(f"Auth event: {event_type}", extra=log_data)
    elif severity == "warning":
        logger.warning(f"Auth event: {event_type}", extra=log_data)
    else:
        logger.info(f"Auth event: {event_type}", extra=log_data)
