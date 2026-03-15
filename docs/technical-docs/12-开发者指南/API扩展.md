# API扩展指南

<!--
文件名: API扩展.md
路径: docs/technical-docs/12-开发者指南/
功能: API扩展指南，介绍API扩展模式、中间件开发、认证扩展、WebSocket扩展
作者: Tech Writer Agent
创建日期: 2026-03-15
版本: 1.0
-->

**版本**: 1.0
**更新日期**: 2026-03-15
**适用对象**: 后端开发人员、API架构师

---

## 目录

1. [概述](#1-概述)
2. [API扩展模式](#2-api扩展模式)
3. [中间件开发](#3-中间件开发)
4. [认证扩展](#4-认证扩展)
5. [WebSocket扩展](#5-websocket扩展)
6. [最佳实践](#6-最佳实践)

---

## 1. 概述

本文档介绍CAUC-SEP自旋电子器件实验平台API的扩展机制，包括中间件开发、认证扩展、WebSocket扩展等内容。通过合理的扩展设计，可以增强API功能、提升安全性和改善性能。

### 1.1 API架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                        客户端请求                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     中间件层 (Middleware)                    │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐ │
│  │ CORS中间件  │ 认证中间件  │ 限流中间件  │ 审计中间件  │ │
│  └─────────────┴─────────────┴─────────────┴─────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      路由层 (Router)                         │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐ │
│  │ 设备控制API │ 实验管理API │ 数据分析API │ 系统监控API │ │
│  └─────────────┴─────────────┴─────────────┴─────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      服务层 (Service)                        │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐ │
│  │ 设备管理器  │ 实验管理器  │ 分析引擎    │ 监控服务    │ │
│  └─────────────┴─────────────┴─────────────┴─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 扩展点

| 扩展点 | 位置 | 用途 |
|--------|------|------|
| 中间件 | 请求处理管道 | 认证、授权、日志、限流 |
| 依赖注入 | 路由处理函数 | 数据库会话、设备管理器 |
| 路由模块 | API路由 | 新增API端点 |
| WebSocket | 实时通信 | 设备状态推送、数据流 |
| 后台任务 | 异步处理 | 长时间运行的任务 |

---

## 2. API扩展模式

### 2.1 路由模块模式

CAUC-SEP采用模块化路由设计，每个功能模块独立定义路由：

```python
"""
文件名: api/custom_module.py
功能: 自定义模块API路由示例
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field

from core.dependencies import get_db_session, get_current_user
from models.user import User

router = APIRouter(
    prefix="/api/v1/custom",
    tags=["custom"],
    responses={
        400: {"description": "请求参数错误"},
        401: {"description": "未授权"},
        404: {"description": "资源不存在"},
        500: {"description": "服务器内部错误"},
    },
)


# ============== 数据模型 ==============

class CustomItem(BaseModel):
    """自定义项目模型。"""
    id: Optional[int] = Field(None, description="项目ID")
    name: str = Field(..., description="项目名称", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="项目描述")
    value: float = Field(..., description="项目值", ge=0)
    created_at: Optional[str] = Field(None, description="创建时间")


class CustomItemList(BaseModel):
    """项目列表响应模型。"""
    items: List[CustomItem]
    total: int
    page: int
    page_size: int


# ============== API端点 ==============

@router.get(
    "/items",
    response_model=CustomItemList,
    summary="获取项目列表",
    description="分页获取自定义项目列表，支持按名称搜索",
)
async def list_items(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    name: Optional[str] = Query(None, description="名称过滤"),
    db=Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    获取项目列表。

    - **page**: 页码，从1开始
    - **page_size**: 每页数量，最大100
    - **name**: 可选的名称过滤条件
    """
    # 实现列表查询逻辑
    items = []
    total = 0

    return CustomItemList(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/items",
    response_model=CustomItem,
    status_code=201,
    summary="创建项目",
    description="创建新的自定义项目",
)
async def create_item(
    item: CustomItem,
    db=Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """创建新项目。"""
    # 实现创建逻辑
    item.id = 1
    item.created_at = "2026-03-15T10:00:00Z"
    return item


@router.get(
    "/items/{item_id}",
    response_model=CustomItem,
    summary="获取项目详情",
)
async def get_item(
    item_id: int = Path(..., ge=1, description="项目ID"),
    db=Depends(get_db_session),
):
    """获取指定项目的详细信息。"""
    # 实现查询逻辑
    raise HTTPException(status_code=404, detail="项目不存在")


@router.put(
    "/items/{item_id}",
    response_model=CustomItem,
    summary="更新项目",
)
async def update_item(
    item_id: int,
    item: CustomItem,
    db=Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """更新项目信息。"""
    # 实现更新逻辑
    return item


@router.delete(
    "/items/{item_id}",
    status_code=204,
    summary="删除项目",
)
async def delete_item(
    item_id: int,
    db=Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """删除指定项目。"""
    # 实现删除逻辑
    return None
```

### 2.2 依赖注入模式

使用FastAPI的依赖注入系统实现模块解耦：

```python
"""
文件名: core/dependencies.py
功能: 依赖注入定义
"""

from typing import Optional, Generator, AsyncGenerator
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from core.database import SessionLocal
from core.device_manager import DeviceManager
from core.cache import CacheManager
from models.user import User
from services.auth import AuthService


# ============== 数据库依赖 ==============

def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话。

    Yields:
        数据库会话对象
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============== 设备管理器依赖 ==============

_device_manager: Optional[DeviceManager] = None


def get_device_manager() -> DeviceManager:
    """
    获取设备管理器实例（单例）。

    Returns:
        设备管理器实例
    """
    global _device_manager
    if _device_manager is None:
        _device_manager = DeviceManager()
    return _device_manager


# ============== 缓存管理器依赖 ==============

_cache_manager: Optional[CacheManager] = None


async def get_cache_manager() -> CacheManager:
    """
    获取缓存管理器实例（单例）。

    Returns:
        缓存管理器实例
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
        await _cache_manager.initialize()
    return _cache_manager


# ============== 认证依赖 ==============

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    获取当前认证用户。

    Args:
        credentials: Bearer Token凭据
        db: 数据库会话

    Returns:
        当前用户对象

    Raises:
        HTTPException: 认证失败
    """
    token = credentials.credentials

    try:
        auth_service = AuthService(db)
        user = await auth_service.verify_token(token)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"认证失败: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    获取当前活跃用户。

    Args:
        current_user: 当前用户

    Returns:
        活跃用户对象

    Raises:
        HTTPException: 用户未激活
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账户未激活",
        )
    return current_user


async def get_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    获取管理员用户。

    Args:
        current_user: 当前活跃用户

    Returns:
        管理员用户对象

    Raises:
        HTTPException: 权限不足
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return current_user


# ============== 分页依赖 ==============

class PaginationParams:
    """分页参数类。"""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    ):
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size
        self.limit = page_size


def get_pagination(params: PaginationParams = Depends()) -> PaginationParams:
    """获取分页参数。"""
    return params
```

### 2.3 版本控制模式

API版本控制策略：

```python
"""
文件名: main.py
功能: API版本控制示例
"""

from fastapi import FastAPI

# 创建应用
app = FastAPI(title="CAUC-SEP API")

# 导入不同版本的路由
from api.v1 import router as v1_router
from api.v2 import router as v2_router

# 注册不同版本的路由
app.include_router(v1_router, prefix="/api/v1")
app.include_router(v2_router, prefix="/api/v2")

# 版本弃用提示
@app.get("/api/deprecated")
async def deprecated_endpoint():
    """
    已弃用的端点。

    此端点将在下一版本中移除，请使用 /api/v2/xxx 替代。
    """
    return {
        "message": "此端点已弃用",
        "deprecated_since": "v0.2.0",
        "removal_version": "v0.4.0",
        "alternative": "/api/v2/xxx",
    }
```

---

## 3. 中间件开发

### 3.1 中间件架构

CAUC-SEP已实现多层中间件，形成完整的请求处理管道：

```
请求 → CORS → 安全头 → 认证 → 限流 → 审计 → 追踪 → 路由 → 响应
```

### 3.2 自定义中间件开发

#### 3.2.1 请求日志中间件

```python
"""
文件名: middleware/request_logger.py
功能: 请求日志中间件
"""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件。

    记录所有HTTP请求的详细信息，包括请求方法、路径、状态码、处理时间等。
    """

    def __init__(self, app, exclude_paths: list[str] = None):
        """
        初始化中间件。

        Args:
            app: FastAPI应用实例
            exclude_paths: 排除的路径列表（不记录日志）
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/favicon.ico"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求。

        Args:
            request: 请求对象
            call_next: 下一个处理函数

        Returns:
            响应对象
        """
        # 检查是否排除路径
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # 记录请求开始时间
        start_time = time.perf_counter()

        # 获取客户端信息
        client_host = request.client.host if request.client else "unknown"
        client_port = request.client.port if request.client else 0

        # 记录请求信息
        logger.info(
            f"请求开始: {request.method} {request.url.path} "
            f"来自 {client_host}:{client_port}"
        )

        try:
            # 调用下一个处理函数
            response = await call_next(request)

            # 计算处理时间
            process_time = (time.perf_counter() - start_time) * 1000

            # 记录响应信息
            logger.info(
                f"请求完成: {request.method} {request.url.path} "
                f"状态码: {response.status_code} "
                f"耗时: {process_time:.2f}ms"
            )

            # 添加处理时间头
            response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

            return response

        except Exception as e:
            # 记录异常
            process_time = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"请求异常: {request.method} {request.url.path} "
                f"错误: {str(e)} "
                f"耗时: {process_time:.2f}ms"
            )
            raise
```

#### 3.2.2 限流中间件

```python
"""
文件名: middleware/rate_limit.py
功能: API访问频率限制中间件
"""

import time
import asyncio
from typing import Callable, Optional
from collections import defaultdict
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

import logging

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    API访问频率限制中间件。

    基于IP地址或用户ID限制API访问频率，防止滥用。
    """

    def __init__(
        self,
        app,
        default_limit: int = 100,
        window_seconds: int = 60,
        write_limit: int = 30,
    ):
        """
        初始化限流中间件。

        Args:
            app: FastAPI应用实例
            default_limit: 默认请求限制（次/窗口）
            window_seconds: 时间窗口（秒）
            write_limit: 写操作请求限制（次/窗口）
        """
        super().__init__(app)
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self.write_limit = write_limit

        # 请求记录存储
        # 结构: {identifier: [(timestamp, method), ...]}
        self._request_history: dict[str, list[tuple[float, str]]] = defaultdict(list)

        # 清理锁
        self._cleanup_lock = asyncio.Lock()
        self._last_cleanup = time.time()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求。

        Args:
            request: 请求对象
            call_next: 下一个处理函数

        Returns:
            响应对象
        """
        # 获取标识符（IP地址或用户ID）
        identifier = self._get_identifier(request)

        # 获取请求限制
        limit = self._get_limit(request)

        # 检查是否超过限制
        if await self._is_rate_limited(identifier, request.method, limit):
            logger.warning(f"限流触发: {identifier} 超过限制 {limit}次/{self.window_seconds}秒")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "请求过于频繁，请稍后再试",
                    "retry_after": self.window_seconds,
                },
                headers={"Retry-After": str(self.window_seconds)},
            )

        # 记录请求
        await self._record_request(identifier, request.method)

        # 定期清理过期记录
        await self._cleanup_if_needed()

        # 调用下一个处理函数
        return await call_next(request)

    def _get_identifier(self, request: Request) -> str:
        """
        获取请求标识符。

        优先使用用户ID，其次使用IP地址。

        Args:
            request: 请求对象

        Returns:
            标识符字符串
        """
        # 尝试从请求状态获取用户ID
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        # 使用IP地址
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"

    def _get_limit(self, request: Request) -> int:
        """
        获取请求限制。

        写操作使用更严格的限制。

        Args:
            request: 请求对象

        Returns:
            请求限制次数
        """
        # 写操作使用更严格的限制
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            return self.write_limit
        return self.default_limit

    async def _is_rate_limited(
        self, identifier: str, method: str, limit: int
    ) -> bool:
        """
        检查是否超过限制。

        Args:
            identifier: 标识符
            method: 请求方法
            limit: 限制次数

        Returns:
            是否超过限制
        """
        current_time = time.time()
        window_start = current_time - self.window_seconds

        # 获取历史记录
        history = self._request_history.get(identifier, [])

        # 过滤窗口内的请求
        recent_requests = [
            (ts, m) for ts, m in history if ts > window_start
        ]

        # 计算当前窗口内的请求数
        request_count = len(recent_requests)

        return request_count >= limit

    async def _record_request(self, identifier: str, method: str) -> None:
        """
        记录请求。

        Args:
            identifier: 标识符
            method: 请求方法
        """
        current_time = time.time()
        self._request_history[identifier].append((current_time, method))

    async def _cleanup_if_needed(self) -> None:
        """
        定期清理过期记录。
        """
        current_time = time.time()

        # 每5分钟清理一次
        if current_time - self._last_cleanup < 300:
            return

        async with self._cleanup_lock:
            if current_time - self._last_cleanup < 300:
                return

            window_start = current_time - self.window_seconds

            # 清理过期记录
            for identifier in list(self._request_history.keys()):
                history = self._request_history[identifier]
                self._request_history[identifier] = [
                    (ts, m) for ts, m in history if ts > window_start
                ]

                # 移除空记录
                if not self._request_history[identifier]:
                    del self._request_history[identifier]

            self._last_cleanup = current_time
            logger.debug("限流记录清理完成")
```

#### 3.2.3 安全头中间件

```python
"""
文件名: middleware/security.py
功能: 安全响应头中间件
"""

from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    安全响应头中间件。

    为所有响应添加安全相关的HTTP头，防止常见Web攻击。
    """

    def __init__(self, app):
        """初始化中间件。"""
        super().__init__(app)

        # 安全头配置
        self.security_headers = {
            # 防止MIME类型嗅探
            "X-Content-Type-Options": "nosniff",

            # 防止点击劫持
            "X-Frame-Options": "DENY",

            # XSS保护
            "X-XSS-Protection": "1; mode=block",

            # 引用策略
            "Referrer-Policy": "strict-origin-when-cross-origin",

            # 权限策略
            "Permissions-Policy": (
                "accelerometer=(), camera=(), geolocation=(), "
                "gyroscope=(), magnetometer=(), microphone=(), "
                "payment=(), usb=()"
            ),

            # 内容安全策略（根据需要调整）
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' ws: wss:; "
                "frame-ancestors 'none';"
            ),
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求。

        Args:
            request: 请求对象
            call_next: 下一个处理函数

        Returns:
            响应对象
        """
        # 调用下一个处理函数
        response = await call_next(request)

        # 添加安全头
        for header_name, header_value in self.security_headers.items():
            response.headers[header_name] = header_value

        # 移除可能暴露服务器信息的头
        if "Server" in response.headers:
            del response.headers["Server"]
        if "X-Powered-By" in response.headers:
            del response.headers["X-Powered-By"]

        return response
```

### 3.3 注册中间件

在 `main.py` 中注册中间件：

```python
"""
文件名: main.py
功能: FastAPI应用入口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from middleware.request_logger import RequestLoggerMiddleware
from middleware.rate_limit import RateLimitMiddleware
from middleware.security import SecurityHeadersMiddleware
from middleware.tracing import TracingMiddleware
from middleware.audit import AuditMiddleware

app = FastAPI(title="CAUC-SEP API")

# CORS中间件（必须第一个注册）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 安全头中间件
app.add_middleware(SecurityHeadersMiddleware)

# 限流中间件
app.add_middleware(
    RateLimitMiddleware,
    default_limit=100,
    window_seconds=60,
    write_limit=30,
)

# 审计中间件
app.add_middleware(AuditMiddleware)

# 追踪中间件
app.add_middleware(TracingMiddleware)

# 请求日志中间件
app.add_middleware(
    RequestLoggerMiddleware,
    exclude_paths=["/health", "/metrics", "/favicon.ico"],
)
```

---

## 4. 认证扩展

### 4.1 认证系统架构

CAUC-SEP支持多种认证方式：

```
┌─────────────────────────────────────────────────────────────┐
│                      认证系统架构                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ JWT Token   │  │ API Key     │  │ OAuth 2.0   │        │
│  │ 认证        │  │ 认证        │  │ 认证        │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │
│         └────────────────┼────────────────┘                │
│                          │                                 │
│                          ▼                                 │
│                 ┌─────────────────┐                        │
│                 │  认证中间件     │                        │
│                 └─────────────────┘                        │
│                          │                                 │
│                          ▼                                 │
│                 ┌─────────────────┐                        │
│                 │  权限检查       │                        │
│                 └─────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 JWT认证实现

```python
"""
文件名: services/auth.py
功能: 认证服务实现
"""

from datetime import datetime, timedelta
from typing import Optional
import secrets

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from pydantic import BaseModel

from models.user import User
from core.config import settings


# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData(BaseModel):
    """Token数据模型。"""
    user_id: int
    username: str
    exp: datetime
    iat: datetime


class AuthService:
    """
    认证服务类。

    提供用户认证、Token生成和验证功能。
    """

    def __init__(self, db: Session):
        """
        初始化认证服务。

        Args:
            db: 数据库会话
        """
        self.db = db

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        验证密码。

        Args:
            plain_password: 明文密码
            hashed_password: 哈希密码

        Returns:
            密码是否正确
        """
        return pwd_context.verify(plain_password, hashed_password)

    def hash_password(self, password: str) -> str:
        """
        哈希密码。

        Args:
            password: 明文密码

        Returns:
            哈希后的密码
        """
        return pwd_context.hash(password)

    def create_access_token(
        self,
        user: User,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        创建访问令牌。

        Args:
            user: 用户对象
            expires_delta: 过期时间增量

        Returns:
            JWT令牌字符串
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                hours=settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS
            )

        now = datetime.utcnow()

        to_encode = {
            "user_id": user.id,
            "username": user.username,
            "exp": expire,
            "iat": now,
        }

        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        return encoded_jwt

    def create_refresh_token(self, user: User) -> str:
        """
        创建刷新令牌。

        Args:
            user: 用户对象

        Returns:
            刷新令牌字符串
        """
        expire = datetime.utcnow() + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )

        to_encode = {
            "user_id": user.id,
            "type": "refresh",
            "exp": expire,
        }

        return jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

    async def verify_token(self, token: str) -> Optional[User]:
        """
        验证访问令牌。

        Args:
            token: JWT令牌字符串

        Returns:
            用户对象，验证失败返回None
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )

            user_id = payload.get("user_id")
            if user_id is None:
                return None

            # 查询用户
            user = self.db.query(User).filter(User.id == user_id).first()
            return user

        except JWTError:
            return None

    async def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """
        刷新访问令牌。

        Args:
            refresh_token: 刷新令牌

        Returns:
            新的访问令牌，失败返回None
        """
        try:
            payload = jwt.decode(
                refresh_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )

            if payload.get("type") != "refresh":
                return None

            user_id = payload.get("user_id")
            if user_id is None:
                return None

            # 查询用户
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user or not user.is_active:
                return None

            # 创建新的访问令牌
            return self.create_access_token(user)

        except JWTError:
            return None

    async def authenticate_user(
        self, username: str, password: str
    ) -> Optional[User]:
        """
        认证用户。

        Args:
            username: 用户名
            password: 密码

        Returns:
            用户对象，认证失败返回None
        """
        # 查询用户
        user = self.db.query(User).filter(User.username == username).first()

        if not user:
            return None

        if not self.verify_password(password, user.hashed_password):
            return None

        if not user.is_active:
            return None

        return user
```

### 4.3 API Key认证

```python
"""
文件名: middleware/api_key_auth.py
功能: API Key认证中间件
"""

from typing import Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from models.api_key import APIKey
from core.database import SessionLocal


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    API Key认证中间件。

    支持通过X-API-Key头部进行认证。
    """

    # 需要API Key认证的路径前缀
    PROTECTED_PREFIXES = ["/api/v1/"]

    # 排除的路径
    EXCLUDE_PATHS = [
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/health",
        "/metrics",
    ]

    async def dispatch(self, request: Request, call_next):
        """处理请求。"""
        # 检查是否需要认证
        if not self._requires_auth(request):
            return await call_next(request)

        # 获取API Key
        api_key = request.headers.get("X-API-Key")

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少API Key",
            )

        # 验证API Key
        user = await self._verify_api_key(api_key)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的API Key",
            )

        # 将用户信息存储到请求状态
        request.state.user = user
        request.state.user_id = user.id

        return await call_next(request)

    def _requires_auth(self, request: Request) -> bool:
        """
        检查请求是否需要认证。

        Args:
            request: 请求对象

        Returns:
            是否需要认证
        """
        path = request.url.path

        # 检查排除路径
        if path in self.EXCLUDE_PATHS:
            return False

        # 检查保护路径前缀
        for prefix in self.PROTECTED_PREFIXES:
            if path.startswith(prefix):
                return True

        return False

    async def _verify_api_key(self, api_key: str):
        """
        验证API Key。

        Args:
            api_key: API Key字符串

        Returns:
            用户对象，验证失败返回None
        """
        db = SessionLocal()
        try:
            # 查询API Key
            key_obj = db.query(APIKey).filter(
                APIKey.key == api_key,
                APIKey.is_active == True,
            ).first()

            if not key_obj:
                return None

            # 检查是否过期
            if key_obj.is_expired():
                return None

            # 更新最后使用时间
            key_obj.update_last_used()
            db.commit()

            return key_obj.user

        finally:
            db.close()
```

### 4.4 权限控制

```python
"""
文件名: core/permissions.py
功能: 权限控制装饰器
"""

from functools import wraps
from typing import List, Optional
from fastapi import HTTPException, status

from models.user import User


def require_permissions(permissions: List[str]):
    """
    权限检查装饰器。

    Args:
        permissions: 所需权限列表

    Example:
        @router.get("/admin/users")
        @require_permissions(["user:read", "admin:access"])
        async def list_users(current_user: User = Depends(get_current_user)):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User = None, **kwargs):
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="未认证",
                )

            # 检查权限
            user_permissions = current_user.get_permissions()

            for perm in permissions:
                if perm not in user_permissions:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"缺少权限: {perm}",
                    )

            return await func(*args, current_user=current_user, **kwargs)

        return wrapper

    return decorator


def require_roles(roles: List[str]):
    """
    角色检查装饰器。

    Args:
        roles: 所需角色列表

    Example:
        @router.delete("/admin/users/{user_id}")
        @require_roles(["admin", "superuser"])
        async def delete_user(user_id: int, current_user: User = Depends(get_current_user)):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User = None, **kwargs):
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="未认证",
                )

            # 检查角色
            user_roles = current_user.get_roles()

            for role in roles:
                if role not in user_roles:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"缺少角色: {role}",
                    )

            return await func(*args, current_user=current_user, **kwargs)

        return wrapper

    return decorator
```

---

## 5. WebSocket扩展

### 5.1 WebSocket架构

```
┌─────────────────────────────────────────────────────────────┐
│                      WebSocket架构                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  客户端 ←──WebSocket连接──→ 服务端                          │
│     │                          │                            │
│     │                          ▼                            │
│     │                 ┌─────────────────┐                   │
│     │                 │  连接管理器     │                   │
│     │                 └─────────────────┘                   │
│     │                          │                            │
│     │                          ▼                            │
│     │                 ┌─────────────────┐                   │
│     │                 │  消息处理器     │                   │
│     │                 └─────────────────┘                   │
│     │                          │                            │
│     │                          ▼                            │
│     │                 ┌─────────────────┐                   │
│     │                 │  业务处理       │                   │
│     │                 └─────────────────┘                   │
│     │                          │                            │
│     └──────────────────────────┘                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 连接管理器

```python
"""
文件名: core/websocket_manager.py
功能: WebSocket连接管理器
"""

import asyncio
from typing import Dict, List, Optional, Set
from datetime import datetime
import json
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionInfo:
    """连接信息类。"""

    def __init__(self, websocket: WebSocket, user_id: Optional[int] = None):
        """
        初始化连接信息。

        Args:
            websocket: WebSocket连接对象
            user_id: 用户ID（可选）
        """
        self.websocket = websocket
        self.user_id = user_id
        self.connected_at = datetime.utcnow()
        self.subscriptions: Set[str] = set()

    @property
    def connection_id(self) -> str:
        """获取连接ID。"""
        return str(id(self.websocket))


class WebSocketManager:
    """
    WebSocket连接管理器。

    管理所有WebSocket连接，支持消息广播和订阅机制。
    """

    def __init__(self):
        """初始化连接管理器。"""
        # 活跃连接: {connection_id: ConnectionInfo}
        self._connections: Dict[str, ConnectionInfo] = {}

        # 用户连接映射: {user_id: [connection_id, ...]}
        self._user_connections: Dict[int, List[str]] = {}

        # 订阅映射: {channel: [connection_id, ...]}
        self._subscriptions: Dict[str, List[str]] = {}

        # 锁
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        user_id: Optional[int] = None,
    ) -> str:
        """
        接受新的WebSocket连接。

        Args:
            websocket: WebSocket连接对象
            user_id: 用户ID（可选）

        Returns:
            连接ID
        """
        await websocket.accept()

        connection_info = ConnectionInfo(websocket, user_id)
        connection_id = connection_info.connection_id

        async with self._lock:
            # 添加到活跃连接
            self._connections[connection_id] = connection_info

            # 添加到用户连接映射
            if user_id:
                if user_id not in self._user_connections:
                    self._user_connections[user_id] = []
                self._user_connections[user_id].append(connection_id)

        logger.info(
            f"WebSocket连接建立: {connection_id}, "
            f"用户: {user_id or '匿名'}, "
            f"当前连接数: {len(self._connections)}"
        )

        return connection_id

    async def disconnect(self, connection_id: str) -> None:
        """
        断开WebSocket连接。

        Args:
            connection_id: 连接ID
        """
        async with self._lock:
            connection_info = self._connections.pop(connection_id, None)

            if connection_info:
                # 从用户连接映射中移除
                if connection_info.user_id:
                    user_conns = self._user_connections.get(
                        connection_info.user_id, []
                    )
                    if connection_id in user_conns:
                        user_conns.remove(connection_id)

                # 从订阅中移除
                for channel in connection_info.subscriptions:
                    if channel in self._subscriptions:
                        subs = self._subscriptions[channel]
                        if connection_id in subs:
                            subs.remove(connection_id)

        logger.info(
            f"WebSocket连接断开: {connection_id}, "
            f"当前连接数: {len(self._connections)}"
        )

    async def subscribe(self, connection_id: str, channel: str) -> None:
        """
        订阅频道。

        Args:
            connection_id: 连接ID
            channel: 频道名称
        """
        async with self._lock:
            connection_info = self._connections.get(connection_id)
            if connection_info:
                connection_info.subscriptions.add(channel)

                if channel not in self._subscriptions:
                    self._subscriptions[channel] = []
                self._subscriptions[channel].append(connection_id)

        logger.debug(f"连接 {connection_id} 订阅频道: {channel}")

    async def unsubscribe(self, connection_id: str, channel: str) -> None:
        """
        取消订阅频道。

        Args:
            connection_id: 连接ID
            channel: 频道名称
        """
        async with self._lock:
            connection_info = self._connections.get(connection_id)
            if connection_info and channel in connection_info.subscriptions:
                connection_info.subscriptions.remove(channel)

            if channel in self._subscriptions:
                subs = self._subscriptions[channel]
                if connection_id in subs:
                    subs.remove(connection_id)

        logger.debug(f"连接 {connection_id} 取消订阅频道: {channel}")

    async def send_to_connection(
        self,
        connection_id: str,
        message: dict,
    ) -> bool:
        """
        向指定连接发送消息。

        Args:
            connection_id: 连接ID
            message: 消息内容

        Returns:
            发送是否成功
        """
        connection_info = self._connections.get(connection_id)
        if not connection_info:
            return False

        try:
            await connection_info.websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            await self.disconnect(connection_id)
            return False

    async def broadcast(
        self,
        message: dict,
        channel: Optional[str] = None,
    ) -> int:
        """
        广播消息。

        Args:
            message: 消息内容
            channel: 频道名称（可选，不指定则广播到所有连接）

        Returns:
            成功发送的连接数
        """
        if channel:
            # 发送到订阅了指定频道的连接
            connection_ids = self._subscriptions.get(channel, [])
        else:
            # 发送到所有连接
            connection_ids = list(self._connections.keys())

        success_count = 0
        for conn_id in connection_ids:
            if await self.send_to_connection(conn_id, message):
                success_count += 1

        return success_count

    async def send_to_user(self, user_id: int, message: dict) -> int:
        """
        向指定用户的所有连接发送消息。

        Args:
            user_id: 用户ID
            message: 消息内容

        Returns:
            成功发送的连接数
        """
        connection_ids = self._user_connections.get(user_id, [])

        success_count = 0
        for conn_id in connection_ids:
            if await self.send_to_connection(conn_id, message):
                success_count += 1

        return success_count

    def get_connection_count(self) -> int:
        """获取当前连接数。"""
        return len(self._connections)

    def get_channel_subscribers(self, channel: str) -> int:
        """获取频道订阅者数量。"""
        return len(self._subscriptions.get(channel, []))


# 全局连接管理器实例
ws_manager = WebSocketManager()
```

### 5.3 WebSocket路由

```python
"""
文件名: api/websocket.py
功能: WebSocket路由定义
"""

import json
import asyncio
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from core.websocket_manager import ws_manager
from core.dependencies import get_user_from_token
import logging

router = APIRouter(tags=["websocket"])
logger = logging.getLogger(__name__)


@router.websocket("/ws/devices")
async def device_status_websocket(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """
    设备状态WebSocket端点。

    推送设备状态变化、实验进度等实时信息。

    Args:
        websocket: WebSocket连接对象
        token: 认证令牌（可选）
    """
    # 验证用户
    user_id = None
    if token:
        user = await get_user_from_token(token)
        if user:
            user_id = user.id

    # 连接
    connection_id = await ws_manager.connect(websocket, user_id)

    try:
        # 订阅设备状态频道
        await ws_manager.subscribe(connection_id, "device_status")

        # 发送欢迎消息
        await ws_manager.send_to_connection(
            connection_id,
            {
                "type": "connected",
                "connection_id": connection_id,
                "message": "WebSocket连接成功",
            },
        )

        # 消息循环
        while True:
            # 接收消息
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                await handle_message(connection_id, message)
            except json.JSONDecodeError:
                await ws_manager.send_to_connection(
                    connection_id,
                    {"type": "error", "message": "无效的JSON格式"},
                )

    except WebSocketDisconnect:
        logger.info(f"客户端断开连接: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
    finally:
        await ws_manager.disconnect(connection_id)


async def handle_message(connection_id: str, message: dict) -> None:
    """
    处理WebSocket消息。

    Args:
        connection_id: 连接ID
        message: 消息内容
    """
    message_type = message.get("type")

    if message_type == "ping":
        # 心跳响应
        await ws_manager.send_to_connection(
            connection_id,
            {"type": "pong", "timestamp": message.get("timestamp")},
        )

    elif message_type == "subscribe":
        # 订阅频道
        channel = message.get("channel")
        if channel:
            await ws_manager.subscribe(connection_id, channel)
            await ws_manager.send_to_connection(
                connection_id,
                {"type": "subscribed", "channel": channel},
            )

    elif message_type == "unsubscribe":
        # 取消订阅
        channel = message.get("channel")
        if channel:
            await ws_manager.unsubscribe(connection_id, channel)
            await ws_manager.send_to_connection(
                connection_id,
                {"type": "unsubscribed", "channel": channel},
            )

    else:
        # 未知消息类型
        await ws_manager.send_to_connection(
            connection_id,
            {"type": "error", "message": f"未知消息类型: {message_type}"},
        )


@router.websocket("/ws/experiments/{experiment_id}")
async def experiment_progress_websocket(
    websocket: WebSocket,
    experiment_id: str,
    token: Optional[str] = Query(None),
):
    """
    实验进度WebSocket端点。

    推送指定实验的进度和状态变化。

    Args:
        websocket: WebSocket连接对象
        experiment_id: 实验ID
        token: 认证令牌（可选）
    """
    # 验证用户
    user_id = None
    if token:
        user = await get_user_from_token(token)
        if user:
            user_id = user.id

    # 连接
    connection_id = await ws_manager.connect(websocket, user_id)

    try:
        # 订阅实验频道
        channel = f"experiment:{experiment_id}"
        await ws_manager.subscribe(connection_id, channel)

        # 发送欢迎消息
        await ws_manager.send_to_connection(
            connection_id,
            {
                "type": "connected",
                "experiment_id": experiment_id,
                "message": "实验进度WebSocket连接成功",
            },
        )

        # 消息循环
        while True:
            data = await websocket.receive_text()
            # 处理消息...

    except WebSocketDisconnect:
        logger.info(f"实验进度WebSocket断开: {connection_id}")
    finally:
        await ws_manager.disconnect(connection_id)
```

### 5.4 消息推送服务

```python
"""
文件名: services/push_service.py
功能: 消息推送服务
"""

from typing import Optional, Dict, Any
import logging

from core.websocket_manager import ws_manager

logger = logging.getLogger(__name__)


class PushService:
    """
    消息推送服务。

    封装WebSocket消息推送功能，提供便捷的推送方法。
    """

    @staticmethod
    async def push_device_status(
        device_id: str,
        status: Dict[str, Any],
    ) -> int:
        """
        推送设备状态更新。

        Args:
            device_id: 设备ID
            status: 状态信息

        Returns:
            成功推送的连接数
        """
        message = {
            "type": "device_status",
            "device_id": device_id,
            "data": status,
        }

        return await ws_manager.broadcast(message, "device_status")

    @staticmethod
    async def push_experiment_progress(
        experiment_id: str,
        progress: float,
        status: str,
        message: Optional[str] = None,
    ) -> int:
        """
        推送实验进度更新。

        Args:
            experiment_id: 实验ID
            progress: 进度百分比(0-100)
            status: 状态
            message: 消息（可选）

        Returns:
            成功推送的连接数
        """
        data = {
            "type": "experiment_progress",
            "experiment_id": experiment_id,
            "progress": progress,
            "status": status,
        }

        if message:
            data["message"] = message

        channel = f"experiment:{experiment_id}"
        return await ws_manager.broadcast(data, channel)

    @staticmethod
    async def push_data_update(
        experiment_id: str,
        data_points: list,
    ) -> int:
        """
        推送数据更新。

        Args:
            experiment_id: 实验ID
            data_points: 数据点列表

        Returns:
            成功推送的连接数
        """
        message = {
            "type": "data_update",
            "experiment_id": experiment_id,
            "data": data_points,
        }

        channel = f"experiment:{experiment_id}"
        return await ws_manager.broadcast(message, channel)

    @staticmethod
    async def push_alert(
        user_id: int,
        title: str,
        content: str,
        level: str = "info",
    ) -> int:
        """
        推送告警消息。

        Args:
            user_id: 用户ID
            title: 标题
            content: 内容
            level: 级别(info/warning/error)

        Returns:
            成功推送的连接数
        """
        message = {
            "type": "alert",
            "title": title,
            "content": content,
            "level": level,
        }

        return await ws_manager.send_to_user(user_id, message)


# 导出服务实例
push_service = PushService()
```

---

## 6. 最佳实践

### 6.1 API设计原则

1. **RESTful设计**: 遵循REST架构风格
2. **版本控制**: 使用URL路径版本控制（/api/v1/）
3. **统一响应**: 使用统一的响应格式
4. **错误处理**: 提供清晰的错误信息
5. **文档完善**: 使用OpenAPI自动生成文档

### 6.2 安全最佳实践

```python
# 1. 输入验证
from pydantic import BaseModel, Field, validator

class UserInput(BaseModel):
    """用户输入模型。"""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')

    @validator('username')
    def validate_username(cls, v):
        if not v.isalnum():
            raise ValueError('用户名只能包含字母和数字')
        return v

# 2. SQL注入防护
# 使用ORM参数化查询
user = db.query(User).filter(User.username == username).first()

# 3. XSS防护
# 前端使用框架自动转义，后端返回JSON

# 4. CSRF防护
# 使用SameSite Cookie或CSRF Token
```

### 6.3 性能优化

```python
# 1. 响应缓存
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache

@router.get("/devices")
@cache(expire=60)  # 缓存60秒
async def list_devices():
    return await device_service.list_all()

# 2. 分页查询
@router.get("/experiments")
async def list_experiments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
):
    offset = (page - 1) * page_size
    experiments = db.query(Experiment).offset(offset).limit(page_size).all()
    total = db.query(Experiment).count()
    return {"items": experiments, "total": total}

# 3. 异步处理
from fastapi import BackgroundTasks

async def send_email_task(email: str, content: str):
    """后台发送邮件任务。"""
    # 发送邮件逻辑
    pass

@router.post("/notifications")
async def send_notification(
    email: str,
    background_tasks: BackgroundTasks,
):
    background_tasks.add_task(send_email_task, email, "通知内容")
    return {"message": "通知已发送"}
```

---

## 附录

### A. 相关文档

- [模块开发指南](./模块开发.md)
- [性能优化指南](./性能优化.md)
- [REST-API设计](../06-通信协议/REST-API设计.md)
- [WebSocket协议](../06-通信协议/WebSocket协议.md)

### B. 参考资料

- [FastAPI官方文档](https://fastapi.tiangolo.com/)
- [Starlette中间件](https://www.starlette.io/middleware/)
- [OAuth 2.0规范](https://oauth.net/2/)
- [WebSocket协议RFC 6455](https://datatracker.ietf.org/doc/html/rfc6455)

---

**文档修订历史**

| 版本 | 日期 | 修订内容 | 作者 |
|------|------|----------|------|
| v1.0 | 2026-03-15 | 初始版本 | Tech Writer Agent |

---

*CAUC-SEP 自旋电子器件实验平台 | 开发者指南*
*版本 0.3.0 | (c) 2025-2026 版权所有*
