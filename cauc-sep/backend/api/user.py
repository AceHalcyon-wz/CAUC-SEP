"""
用户认证与管理 API 路由模块

功能：
- 用户登录/登出（JWT认证）
- 用户信息管理
- 密码修改
- 用户偏好设置
- 头像上传
- 操作历史记录

安全特性：
- JWT令牌认证
- 密码bcrypt哈希
- 令牌黑名单（登出）
- 输入验证

作者: Backend Engineer Agent
创建日期: 2026-03-07
依赖: fastapi, python-jose, passlib
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base
from models.operation_history import OperationHistory, VALID_OPERATION_TYPES
from models.user import User, VALID_USER_ROLES, DEFAULT_PREFERENCES

logger = logging.getLogger(__name__)

# ==================== 配置常量 ====================

# JWT配置
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "cauc-sep-jwt-secret-key-change-in-production-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# 密码哈希配置
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 数据库配置
DB_PATH = "experiments.db"

# 头像上传配置
AVATAR_UPLOAD_DIR = "uploads/avatars"
MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2MB
ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}

# ==================== 数据库初始化 ====================

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建表
Base.metadata.create_all(bind=engine)

# JWT令牌黑名单（内存存储，生产环境应使用Redis）
_token_blacklist: set[str] = set()

# HTTP Bearer认证
security = HTTPBearer()

# ==================== Pydantic 模型 ====================


class LoginRequest(BaseModel):
    """登录请求模型。"""

    username: str = Field(..., description="用户名", min_length=3, max_length=50)
    password: str = Field(..., description="密码", min_length=6, max_length=100)


class TokenResponse(BaseModel):
    """令牌响应模型。"""

    access_token: str = Field(..., description="JWT访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")
    user: dict[str, Any] = Field(..., description="用户信息")


class UserResponse(BaseModel):
    """用户信息响应模型。"""

    id: int
    username: str
    email: str
    role: str
    avatar: str | None
    preferences: dict[str, Any]
    created_at: str
    updated_at: str


class ProfileUpdateRequest(BaseModel):
    """用户资料更新请求模型。"""

    username: str | None = Field(None, description="用户名", min_length=3, max_length=50)
    email: EmailStr | None = Field(None, description="邮箱地址")


class PasswordChangeRequest(BaseModel):
    """密码修改请求模型。"""

    old_password: str = Field(..., description="原密码", min_length=6, max_length=100)
    new_password: str = Field(..., description="新密码", min_length=6, max_length=100)


class PreferencesUpdateRequest(BaseModel):
    """偏好设置更新请求模型。"""

    theme: str | None = Field(None, description="主题: light/dark")
    language: str | None = Field(None, description="语言: zh-CN/en-US")
    notifications: dict[str, bool] | None = Field(None, description="通知设置")
    display_options: dict[str, Any] | None = Field(None, description="显示选项")


class OperationHistoryCreate(BaseModel):
    """操作历史创建请求模型。"""

    operation_type: str = Field(..., description="操作类型")
    operation_detail: dict[str, Any] | None = Field(None, description="操作详情")
    device_id: str | None = Field(None, description="相关设备ID")


class OperationHistoryResponse(BaseModel):
    """操作历史响应模型。"""

    id: int
    user_id: int
    operation_type: str
    operation_detail: dict[str, Any]
    device_id: str | None
    created_at: str


class SuccessResponse(BaseModel):
    """通用成功响应模型。"""

    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作消息")


class ErrorResponse(BaseModel):
    """错误响应模型。"""

    error_code: str = Field(..., description="错误代码")
    detail: str = Field(..., description="错误详情")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# ==================== 路由器定义 ====================

router = APIRouter(
    prefix="/api/v1/user",
    tags=["user"],
    responses={
        400: {"model": ErrorResponse, "description": "请求参数错误"},
        401: {"model": ErrorResponse, "description": "未授权"},
        403: {"model": ErrorResponse, "description": "权限不足"},
        404: {"model": ErrorResponse, "description": "资源不存在"},
        500: {"model": ErrorResponse, "description": "服务器内部错误"},
    },
)


# ==================== 辅助函数 ====================


def get_db():
    """
    获取数据库会话。

    Yields:
        Session: SQLAlchemy会话对象
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    创建JWT访问令牌。

    Args:
        data: 令牌负载数据
        expires_delta: 过期时间增量

    Returns:
        str: JWT令牌
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire, "jti": str(uuid.uuid4())})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict[str, Any]:
    """
    解码JWT令牌。

    Args:
        token: JWT令牌

    Returns:
        dict: 令牌负载

    Raises:
        HTTPException: 令牌无效或已过期
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        if jti and jti in _token_blacklist:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌已失效",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_db),
) -> User:
    """
    获取当前认证用户。

    Args:
        credentials: HTTP Bearer认证凭据
        db: 数据库会话

    Returns:
        User: 当前用户对象

    Raises:
        HTTPException: 认证失败
    """
    token = credentials.credentials
    payload = decode_token(token)
    user_id: int = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌负载",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    return user


def create_default_admin():
    """
    创建默认管理员用户。

    如果数据库中没有用户，则创建默认管理员。
    """
    db = SessionLocal()
    try:
        # 检查是否已有用户
        existing_user = db.query(User).first()
        if existing_user:
            return

        # 创建默认管理员
        admin = User(
            username="admin",
            email="admin@cauc-sep.local",
            password_hash=get_password_hash("admin123"),
            role="admin",
            preferences=json.dumps(DEFAULT_PREFERENCES, ensure_ascii=False),
        )
        db.add(admin)
        db.commit()
        logger.info("Default admin user created: admin / admin123")
    except Exception as e:
        logger.error(f"Failed to create default admin: {e}")
        db.rollback()
    finally:
        db.close()


def record_operation(
    db,
    user_id: int,
    operation_type: str,
    operation_detail: dict[str, Any] | None = None,
    device_id: str | None = None,
) -> None:
    """
    记录操作历史。

    Args:
        db: 数据库会话
        user_id: 用户ID
        operation_type: 操作类型
        operation_detail: 操作详情
        device_id: 设备ID
    """
    try:
        history = OperationHistory(
            user_id=user_id,
            operation_type=operation_type,
            operation_detail=json.dumps(operation_detail, ensure_ascii=False) if operation_detail else None,
            device_id=device_id,
        )
        db.add(history)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to record operation: {e}")
        db.rollback()


# ==================== API端点 ====================


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db=Depends(get_db)):
    """
    用户登录。

    验证用户名和密码，返回JWT令牌。

    Args:
        request: 登录请求
        db: 数据库会话

    Returns:
        TokenResponse: JWT令牌和用户信息

    Raises:
        HTTPException: 用户名或密码错误
    """
    # 查询用户
    user = db.query(User).filter(User.username == request.username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    # 验证密码
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # 更新最后登录时间
    user.updated_at = datetime.now()
    db.commit()

    # 创建令牌
    access_token = create_access_token(data={"sub": user.id})

    # 记录登录操作
    record_operation(db, user.id, "login", {"ip": "unknown"})

    logger.info(f"User logged in: {user.username}")

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "avatar": user.avatar,
        },
    )


@router.post("/logout", response_model=SuccessResponse)
async def logout(
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_db),
):
    """
    用户登出。

    将当前令牌加入黑名单。

    Args:
        current_user: 当前用户
        credentials: 认证凭据
        db: 数据库会话

    Returns:
        SuccessResponse: 登出结果
    """
    token = credentials.credentials
    payload = decode_token(token)
    jti = payload.get("jti")

    if jti:
        _token_blacklist.add(jti)

    # 记录登出操作
    record_operation(db, current_user.id, "logout")

    logger.info(f"User logged out: {current_user.username}")

    return SuccessResponse(success=True, message="登出成功")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    获取当前用户信息。

    Args:
        current_user: 当前用户

    Returns:
        UserResponse: 用户信息
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        avatar=current_user.avatar,
        preferences=current_user.get_preferences(),
        created_at=current_user.created_at.isoformat() if current_user.created_at else None,
        updated_at=current_user.updated_at.isoformat() if current_user.updated_at else None,
    )


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    更新用户资料。

    Args:
        request: 更新请求
        current_user: 当前用户
        db: 数据库会话

    Returns:
        UserResponse: 更新后的用户信息

    Raises:
        HTTPException: 用户名或邮箱已被使用
    """
    # 检查用户名是否已被使用
    if request.username and request.username != current_user.username:
        existing = db.query(User).filter(User.username == request.username).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已被使用",
            )
        current_user.username = request.username

    # 检查邮箱是否已被使用
    if request.email and request.email != current_user.email:
        existing = db.query(User).filter(User.email == request.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被使用",
            )
        current_user.email = request.email

    current_user.updated_at = datetime.now()
    db.commit()

    # 记录操作
    record_operation(
        db,
        current_user.id,
        "config_change",
        {"action": "update_profile", "fields": list(request.model_dump(exclude_none=True).keys())},
    )

    logger.info(f"User profile updated: {current_user.username}")

    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        avatar=current_user.avatar,
        preferences=current_user.get_preferences(),
        created_at=current_user.created_at.isoformat() if current_user.created_at else None,
        updated_at=current_user.updated_at.isoformat() if current_user.updated_at else None,
    )


@router.put("/password", response_model=SuccessResponse)
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    修改密码。

    Args:
        request: 密码修改请求
        current_user: 当前用户
        db: 数据库会话

    Returns:
        SuccessResponse: 修改结果

    Raises:
        HTTPException: 原密码错误
    """
    # 验证原密码
    if not verify_password(request.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误",
        )

    # 更新密码
    current_user.password_hash = get_password_hash(request.new_password)
    current_user.updated_at = datetime.now()
    db.commit()

    # 记录操作
    record_operation(db, current_user.id, "config_change", {"action": "change_password"})

    logger.info(f"User password changed: {current_user.username}")

    return SuccessResponse(success=True, message="密码修改成功")


@router.get("/preferences")
async def get_preferences(current_user: User = Depends(get_current_user)):
    """
    获取用户偏好设置。

    Args:
        current_user: 当前用户

    Returns:
        dict: 用户偏好设置
    """
    return current_user.get_preferences()


@router.put("/preferences", response_model=SuccessResponse)
async def update_preferences(
    request: PreferencesUpdateRequest,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    更新用户偏好设置。

    Args:
        request: 偏好设置更新请求
        current_user: 当前用户
        db: 数据库会话

    Returns:
        SuccessResponse: 更新结果
    """
    # 获取当前偏好设置
    preferences = current_user.get_preferences()

    # 更新偏好设置
    if request.theme is not None:
        preferences["theme"] = request.theme
    if request.language is not None:
        preferences["language"] = request.language
    if request.notifications is not None:
        preferences["notifications"] = {**preferences.get("notifications", {}), **request.notifications}
    if request.display_options is not None:
        preferences["display_options"] = {**preferences.get("display_options", {}), **request.display_options}

    # 保存偏好设置
    current_user.set_preferences(preferences)
    current_user.updated_at = datetime.now()
    db.commit()

    # 记录操作
    record_operation(
        db,
        current_user.id,
        "config_change",
        {"action": "update_preferences", "fields": list(request.model_dump(exclude_none=True).keys())},
    )

    logger.info(f"User preferences updated: {current_user.username}")

    return SuccessResponse(success=True, message="偏好设置已更新")


@router.post("/avatar", response_model=SuccessResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    上传头像。

    Args:
        file: 上传的文件
        current_user: 当前用户
        db: 数据库会话

    Returns:
        SuccessResponse: 上传结果

    Raises:
        HTTPException: 文件类型不支持或文件过大
    """
    # 检查文件类型
    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {file.content_type}",
        )

    # 读取文件内容检查大小
    content = await file.read()
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件过大，最大支持 {MAX_AVATAR_SIZE // 1024 // 1024}MB",
        )

    # 创建上传目录
    os.makedirs(AVATAR_UPLOAD_DIR, exist_ok=True)

    # 生成文件名
    file_ext = file.filename.split(".")[-1] if file.filename else "png"
    filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}.{file_ext}"
    filepath = os.path.join(AVATAR_UPLOAD_DIR, filename)

    # 保存文件
    with open(filepath, "wb") as f:
        f.write(content)

    # 更新用户头像URL
    avatar_url = f"/uploads/avatars/{filename}"
    current_user.avatar = avatar_url
    current_user.updated_at = datetime.now()
    db.commit()

    # 记录操作
    record_operation(db, current_user.id, "config_change", {"action": "upload_avatar"})

    logger.info(f"User avatar uploaded: {current_user.username}")

    return SuccessResponse(success=True, message="头像上传成功")


@router.post("/history", response_model=SuccessResponse)
async def create_history(
    request: OperationHistoryCreate,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    记录操作历史。

    Args:
        request: 操作历史创建请求
        current_user: 当前用户
        db: 数据库会话

    Returns:
        SuccessResponse: 创建结果

    Raises:
        HTTPException: 操作类型无效
    """
    # 验证操作类型
    if request.operation_type not in VALID_OPERATION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的操作类型: {request.operation_type}",
        )

    # 记录操作
    record_operation(
        db,
        current_user.id,
        request.operation_type,
        request.operation_detail,
        request.device_id,
    )

    return SuccessResponse(success=True, message="操作历史已记录")


@router.get("/history")
async def get_history(
    limit: int = 100,
    offset: int = 0,
    operation_type: str | None = None,
    device_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    获取操作历史。

    Args:
        limit: 返回数量限制
        offset: 偏移量
        operation_type: 操作类型过滤
        device_id: 设备ID过滤
        current_user: 当前用户
        db: 数据库会话

    Returns:
        dict: 操作历史列表和总数
    """
    query = db.query(OperationHistory).filter(OperationHistory.user_id == current_user.id)

    if operation_type:
        query = query.filter(OperationHistory.operation_type == operation_type)
    if device_id:
        query = query.filter(OperationHistory.device_id == device_id)

    total = query.count()
    histories = query.order_by(OperationHistory.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            OperationHistoryResponse(
                id=h.id,
                user_id=h.user_id,
                operation_type=h.operation_type,
                operation_detail=h.get_detail(),
                device_id=h.device_id,
                created_at=h.created_at.isoformat() if h.created_at else None,
            )
            for h in histories
        ],
    }


@router.delete("/history", response_model=SuccessResponse)
async def clear_history(
    operation_type: str | None = None,
    device_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    清除操作历史。

    Args:
        operation_type: 操作类型过滤（可选）
        device_id: 设备ID过滤（可选）
        current_user: 当前用户
        db: 数据库会话

    Returns:
        SuccessResponse: 清除结果
    """
    query = db.query(OperationHistory).filter(OperationHistory.user_id == current_user.id)

    if operation_type:
        query = query.filter(OperationHistory.operation_type == operation_type)
    if device_id:
        query = query.filter(OperationHistory.device_id == device_id)

    deleted_count = query.delete()
    db.commit()

    logger.info(f"User history cleared: {current_user.username}, deleted={deleted_count}")

    return SuccessResponse(success=True, message=f"已清除 {deleted_count} 条操作历史")


# ==================== 初始化函数 ====================


def init_user_system():
    """
    初始化用户系统。

    创建数据库表和默认管理员用户。
    """
    # 创建上传目录
    os.makedirs(AVATAR_UPLOAD_DIR, exist_ok=True)

    # 创建默认管理员
    create_default_admin()

    logger.info("User system initialized")
