# REST API 设计规范

**版本**: v1.0  
**创建日期**: 2026-03-15  
**最后更新**: 2026-03-15  
**适用范围**: CAUC-SEP后端API

---

## 概述

CAUC-SEP自旋电子器件实验平台采用RESTful API设计风格，提供设备控制、数据管理、用户认证等接口。本文档定义API设计原则、统一响应格式、错误码规范等内容。

### API特点

- **RESTful风格**: 遵循REST架构约束
- **统一响应格式**: 标准化的响应结构
- **完善的错误处理**: 详细的错误码和描述
- **JWT认证**: 安全的令牌认证机制
- **速率限制**: 防止API滥用
- **版本管理**: 支持多版本共存

---

## API设计原则

### RESTful约束

1. **资源导向**: URL表示资源，HTTP方法表示操作
2. **无状态**: 每个请求包含所有必要信息
3. **统一接口**: 标准化的资源操作方式
4. **分层系统**: 支持中间层代理和缓存

### URL设计规范

#### 基础URL

```
http://localhost:8000/api/v1
```

#### 资源命名规则

| 规则 | 示例 |
|------|------|
| 使用名词复数 | `/api/v1/motors` |
| 使用小写字母 | `/api/v1/experiments` |
| 使用连字符分隔 | `/api/v1/device-types` |
| 避免嵌套过深 | 最多2层嵌套 |

#### URL示例

```
# 设备资源
GET    /api/v1/devices              # 获取设备列表
GET    /api/v1/devices/{id}         # 获取单个设备
POST   /api/v1/devices/{id}/connect # 连接设备
POST   /api/v1/devices/{id}/disconnect # 断开设备

# 电机控制
POST   /api/v1/motor/move           # 电机运动
POST   /api/v1/motor/stop           # 电机停止
POST   /api/v1/motor/home           # 电机回零
GET    /api/v1/motor/status         # 电机状态

# 实验管理
GET    /api/v1/experiments          # 实验列表
POST   /api/v1/experiments          # 创建实验
GET    /api/v1/experiments/{id}     # 实验详情
PUT    /api/v1/experiments/{id}     # 更新实验
DELETE /api/v1/experiments/{id}     # 删除实验
```

### HTTP方法语义

| 方法 | 语义 | 幂等性 | 安全性 |
|------|------|--------|--------|
| GET | 获取资源 | 是 | 是 |
| POST | 创建资源/执行操作 | 否 | 否 |
| PUT | 更新资源（完整） | 是 | 否 |
| PATCH | 更新资源（部分） | 否 | 否 |
| DELETE | 删除资源 | 是 | 否 |

### HTTP状态码

| 状态码 | 说明 | 使用场景 |
|--------|------|----------|
| 200 | OK | 成功响应 |
| 201 | Created | 资源创建成功 |
| 204 | No Content | 成功但无返回内容 |
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未认证 |
| 403 | Forbidden | 无权限 |
| 404 | Not Found | 资源不存在 |
| 409 | Conflict | 资源冲突 |
| 422 | Unprocessable Entity | 语义错误 |
| 429 | Too Many Requests | 请求过于频繁 |
| 500 | Internal Server Error | 服务器内部错误 |
| 503 | Service Unavailable | 服务不可用 |

---

## 统一响应格式

### 成功响应

#### 单个资源

```json
{
    "success": true,
    "message": "操作成功",
    "data": {
        "id": "stepper_01",
        "type": "stepper",
        "status": "ready",
        "position_mm": 10.5
    }
}
```

#### 资源列表

```json
{
    "success": true,
    "message": "查询成功",
    "data": [
        {"id": "stepper_01", "type": "stepper"},
        {"id": "temp_01", "type": "temperature"}
    ],
    "pagination": {
        "page": 1,
        "page_size": 20,
        "total": 100,
        "total_pages": 5
    }
}
```

#### 创建资源

```json
{
    "success": true,
    "message": "创建成功",
    "data": {
        "id": 123,
        "name": "新实验"
    }
}
```

### 错误响应

```json
{
    "success": false,
    "message": "请求参数错误",
    "error": {
        "code": "VALIDATION_ERROR",
        "detail": "参数验证失败",
        "fields": [
            {
                "field": "position",
                "message": "位置值超出范围"
            }
        ]
    }
}
```

### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | boolean | 操作是否成功 |
| `message` | string | 人类可读的消息 |
| `data` | any | 响应数据（成功时） |
| `error` | object | 错误详情（失败时） |
| `pagination` | object | 分页信息（列表时） |

---

## 错误码定义

### 错误码格式

错误码采用大写字母和下划线组成，格式为：`{类别}_{具体错误}`

### 通用错误码

| 错误码 | HTTP状态码 | 说明 |
|--------|------------|------|
| `VALIDATION_ERROR` | 400 | 参数验证失败 |
| `INVALID_JSON` | 400 | JSON格式错误 |
| `MISSING_PARAMETER` | 400 | 缺少必要参数 |
| `INVALID_PARAMETER` | 400 | 参数值无效 |

### 认证错误码

| 错误码 | HTTP状态码 | 说明 |
|--------|------------|------|
| `UNAUTHORIZED` | 401 | 未认证 |
| `TOKEN_EXPIRED` | 401 | 令牌已过期 |
| `TOKEN_INVALID` | 401 | 令牌无效 |
| `TOKEN_REVOKED` | 401 | 令牌已撤销 |
| `PERMISSION_DENIED` | 403 | 权限不足 |
| `ROLE_INSUFFICIENT` | 403 | 角色权限不足 |

### 设备错误码

| 错误码 | HTTP状态码 | 说明 |
|--------|------------|------|
| `DEVICE_NOT_FOUND` | 404 | 设备不存在 |
| `DEVICE_NOT_CONNECTED` | 400 | 设备未连接 |
| `DEVICE_BUSY` | 409 | 设备忙碌中 |
| `DEVICE_ERROR` | 500 | 设备错误 |
| `DEVICE_ALARM` | 500 | 设备报警 |
| `DEVICE_TIMEOUT` | 504 | 设备响应超时 |
| `SOFT_LIMIT_EXCEEDED` | 400 | 软件限位超出 |
| `HARD_LIMIT_TRIGGERED` | 400 | 硬件限位触发 |

### 实验错误码

| 错误码 | HTTP状态码 | 说明 |
|--------|------------|------|
| `EXPERIMENT_NOT_FOUND` | 404 | 实验不存在 |
| `EXPERIMENT_RUNNING` | 409 | 实验正在运行 |
| `EXPERIMENT_COMPLETED` | 409 | 实验已完成 |
| `EXPERIMENT_FAILED` | 500 | 实验执行失败 |

### 速率限制错误码

| 错误码 | HTTP状态码 | 说明 |
|--------|------------|------|
| `RATE_LIMIT_EXCEEDED` | 429 | 请求过于频繁 |
| `RATE_LIMIT_BLOCKED` | 429 | 已被临时阻止 |

### 系统错误码

| 错误码 | HTTP状态码 | 说明 |
|--------|------------|------|
| `INTERNAL_ERROR` | 500 | 内部服务器错误 |
| `DATABASE_ERROR` | 500 | 数据库错误 |
| `SERVICE_UNAVAILABLE` | 503 | 服务不可用 |

### 错误码使用示例

```python
from fastapi import HTTPException

class APIError(HTTPException):
    """API错误基类。"""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        detail: str | None = None,
        fields: list | None = None
    ):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.detail = detail
        self.fields = fields or []

        super().__init__(
            status_code=status_code,
            detail={
                "success": False,
                "message": message,
                "error": {
                    "code": code,
                    "detail": detail or message,
                    "fields": fields
                }
            }
        )


# 使用示例
raise APIError(
    status_code=400,
    code="DEVICE_NOT_CONNECTED",
    message="设备未连接",
    detail="请先连接设备后再执行操作"
)
```

---

## 认证授权

### JWT认证机制

系统采用JWT（JSON Web Token）进行身份认证。

#### 令牌类型

| 类型 | 有效期 | 用途 |
|------|--------|------|
| Access Token | 24小时 | API访问认证 |
| Refresh Token | 7天 | 刷新访问令牌 |

#### 获取令牌

**请求**:

```http
POST /api/v1/user/login
Content-Type: application/json

{
    "username": "admin",
    "password": "password123"
}
```

**响应**:

```json
{
    "success": true,
    "message": "登录成功",
    "data": {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer",
        "expires_in": 86400
    }
}
```

#### 使用令牌

在请求头中添加Authorization字段：

```http
GET /api/v1/devices
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### 刷新令牌

```http
POST /api/v1/user/refresh
Content-Type: application/json

{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### 角色权限控制

#### 角色定义

| 角色 | 说明 |
|------|------|
| `admin` | 管理员，拥有所有权限 |
| `user` | 普通用户，拥有基本操作权限 |
| `guest` | 访客，只读权限 |

#### 权限定义

```python
class Permission(str, Enum):
    """权限枚举。"""

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
```

#### 角色权限映射

```python
ROLE_PERMISSIONS = {
    "admin": {
        # 所有权限
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
```

#### 权限检查装饰器

```python
from fastapi import Depends

@router.get("/admin/users")
async def list_users(
    user = Depends(require_permissions(Permission.USER_READ))
):
    """列出所有用户（需要USER_READ权限）。"""
    return {"users": [...]}

@router.post("/motor/emergency_stop")
async def emergency_stop(
    user = Depends(require_permissions(Permission.EMERGENCY_STOP))
):
    """紧急停止（需要EMERGENCY_STOP权限）。"""
    return {"success": True}
```

---

## 速率限制

### 限制策略

| 端点类型 | 每分钟请求数 | 突发大小 | 说明 |
|----------|--------------|----------|------|
| 默认 | 1000 | 20 | 普通API |
| 敏感操作 | 30 | 10 | 急停、重置等 |
| 认证操作 | 1000 | 100 | 登录、登出 |
| 数据导出 | 60 | 30 | 实验数据导出 |

### 敏感路径配置

```python
SENSITIVE_PATHS = {
    "/api/v1/motor/emergency_stop": RateLimitConfig(
        requests_per_minute=30,
        burst_size=10,
    ),
    "/api/v1/motor/reset": RateLimitConfig(
        requests_per_minute=30,
        burst_size=10,
    ),
    "/api/v1/motor/factory_reset": RateLimitConfig(
        requests_per_minute=5,
        burst_size=2,
    ),
}
```

### 响应头

速率限制信息通过响应头返回：

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 995
X-RateLimit-Reset: 60
```

### 超限响应

```json
{
    "success": false,
    "message": "请求过于频繁，请稍后再试",
    "error": {
        "code": "RATE_LIMIT_EXCEEDED",
        "detail": "已达到请求限制",
        "retry_after": 45
    }
}
```

### 白名单

支持IP和用户白名单：

```python
# 添加白名单
limiter.add_to_whitelist(ip="192.168.1.100")
limiter.add_to_whitelist(user_id=1)
```

---

## API版本管理

### 版本策略

采用URL路径版本控制：

```
/api/v1/devices    # 版本1
/api/v2/devices    # 版本2
```

### 版本生命周期

| 阶段 | 持续时间 | 说明 |
|------|----------|------|
| Current | - | 当前活跃版本 |
| Deprecated | 6个月 | 已弃用但仍可用 |
| Sunset | - | 已下线，不可用 |

### 弃用通知

在响应头中添加弃用信息：

```
Deprecation: true
Sunset: Sat, 01 Sep 2026 00:00:00 GMT
Link: </api/v2/devices>; rel="successor-version"
```

### 版本兼容性

- **向后兼容**: 新版本必须兼容旧版本客户端
- **破坏性变更**: 仅在新主版本中引入
- **弃用流程**: 提前6个月通知，提供迁移指南

---

## 请求参数验证

### 输入验证

系统对输入参数进行严格验证，防止XSS、SQL注入等攻击。

#### XSS过滤

```python
def sanitize_input(
    text: str,
    max_length: int = 10000,
    allow_html: bool = False
) -> ValidationResult:
    """
    清理输入文本，防止XSS攻击。

    Args:
        text: 原始文本
        max_length: 最大长度
        allow_html: 是否允许HTML

    Returns:
        ValidationResult: 验证结果
    """
    # 移除危险标签和属性
    sanitized = strip_xss(text)
    # 限制长度
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    return ValidationResult(is_valid=True, sanitized_value=sanitized)
```

#### SQL注入防护

```python
def detect_sql_injection(text: str) -> tuple[bool, list[str]]:
    """
    检测SQL注入攻击。

    Args:
        text: 待检测文本

    Returns:
        tuple: 是否检测到注入、匹配的模式列表
    """
    detected_patterns = []
    for pattern in SQL_INJECTION_PATTERNS:
        if pattern.search(text):
            detected_patterns.append(pattern.pattern)
    return len(detected_patterns) > 0, detected_patterns
```

### Pydantic模型验证

```python
from pydantic import BaseModel, Field, field_validator

class MotorMoveRequest(BaseModel):
    """电机运动请求模型。"""

    device_id: str = Field(..., min_length=1, max_length=64)
    mode: str = Field(..., pattern="^(abs|rel)$")
    position: float = Field(..., ge=-1000, le=1000)
    velocity: float = Field(default=100, ge=1, le=1000)
    acceleration: float = Field(default=100, ge=1, le=1000)
    deceleration: float = Field(default=100, ge=1, le=1000)

    @field_validator("device_id")
    @classmethod
    def validate_device_id(cls, v: str) -> str:
        """验证设备ID。"""
        result = sanitize_input(v, max_length=64)
        if not result.is_valid:
            raise ValueError(result.errors[0])
        return result.sanitized_value
```

---

## API接口示例

### 设备管理

#### 获取设备列表

```http
GET /api/v1/devices
Authorization: Bearer {token}
```

**响应**:

```json
{
    "success": true,
    "message": "查询成功",
    "data": [
        {
            "id": "stepper_01",
            "type": "stepper",
            "status": "ready",
            "connected": true
        }
    ]
}
```

#### 连接设备

```http
POST /api/v1/device/connect
Authorization: Bearer {token}
Content-Type: application/json

{
    "device_id": "stepper_01",
    "params": {
        "port": "COM3",
        "baudrate": 115200,
        "slave_id": 1
    }
}
```

**响应**:

```json
{
    "success": true,
    "message": "设备连接成功",
    "data": {
        "device_id": "stepper_01",
        "connected": true
    }
}
```

### 电机控制

#### 绝对位置运动

```http
POST /api/v1/motor/move
Authorization: Bearer {token}
Content-Type: application/json

{
    "device_id": "stepper_01",
    "mode": "abs",
    "position": 50000,
    "velocity": 10000,
    "acceleration": 5000,
    "deceleration": 5000
}
```

**响应**:

```json
{
    "success": true,
    "message": "运动已启动",
    "data": {
        "task_id": "task_001",
        "target_position": 50000
    }
}
```

#### 紧急停止

```http
POST /api/v1/motor/emergency_stop
Authorization: Bearer {token}
Content-Type: application/json

{
    "device_id": "stepper_01"
}
```

**响应**:

```json
{
    "success": true,
    "message": "紧急停止已执行",
    "data": {
        "device_id": "stepper_01",
        "stopped": true
    }
}
```

### PR路径配置

```http
POST /api/v1/motor/pr/config
Authorization: Bearer {token}
Content-Type: application/json

{
    "device_id": "stepper_01",
    "path_number": 0,
    "mode": 1,
    "position": 200000,
    "velocity": 600,
    "acceleration": 50,
    "deceleration": 50,
    "dwell_time": 0
}
```

**响应**:

```json
{
    "success": true,
    "message": "PR路径配置成功",
    "data": {
        "path_number": 0,
        "configured": true
    }
}
```

---

## 通信故障排除指南

### 常见问题诊断

#### 1. 认证失败

**症状**: 返回401错误

**排查步骤**:

1. 检查Authorization头格式
2. 确认令牌未过期
3. 检查令牌是否被撤销

**解决方案**:

```python
# 检查令牌状态
def check_token_status(token: str) -> dict:
    try:
        payload = decode_token(token)
        return {
            "valid": True,
            "user_id": payload.sub,
            "role": payload.role,
            "expires_at": payload.exp
        }
    except HTTPException as e:
        return {"valid": False, "error": e.detail}
```

#### 2. 权限不足

**症状**: 返回403错误

**排查步骤**:

1. 确认用户角色
2. 检查所需权限
3. 查看权限映射

**解决方案**:

```python
# 检查用户权限
def check_user_permissions(user_id: int, required_permission: Permission) -> bool:
    user = get_user(user_id)
    role_permissions = ROLE_PERMISSIONS.get(user.role, set())
    return required_permission in role_permissions
```

#### 3. 请求参数错误

**症状**: 返回400错误

**排查步骤**:

1. 检查请求体格式
2. 验证参数类型
3. 检查必填字段

**解决方案**:

```python
# 参数验证示例
from pydantic import ValidationError

try:
    request = MotorMoveRequest(**request_data)
except ValidationError as e:
    errors = [{"field": err["loc"][0], "message": err["msg"]} for err in e.errors()]
    raise APIError(
        status_code=400,
        code="VALIDATION_ERROR",
        message="参数验证失败",
        fields=errors
    )
```

#### 4. 速率限制触发

**症状**: 返回429错误

**排查步骤**:

1. 检查请求频率
2. 查看剩余配额
3. 确认是否在白名单

**解决方案**:

```python
# 获取速率限制状态
def get_rate_limit_status(request: Request) -> dict:
    limiter = get_rate_limiter()
    allowed, remaining, reset_time, headers = limiter.is_allowed(request)
    return {
        "allowed": allowed,
        "remaining": remaining,
        "reset_time": reset_time,
        "headers": headers
    }
```

### API调试工具

#### cURL示例

```bash
# 登录获取令牌
curl -X POST http://localhost:8000/api/v1/user/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password123"}'

# 使用令牌访问API
curl -X GET http://localhost:8000/api/v1/devices \
  -H "Authorization: Bearer {token}"

# 电机运动
curl -X POST http://localhost:8000/api/v1/motor/move \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"device_id":"stepper_01","mode":"abs","position":50000}'
```

#### Python请求示例

```python
import requests

class APIClient:
    """API客户端。"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.token = None

    def login(self, username: str, password: str) -> dict:
        """登录获取令牌。"""
        response = requests.post(
            f"{self.base_url}/api/v1/user/login",
            json={"username": username, "password": password}
        )
        data = response.json()
        if data["success"]:
            self.token = data["data"]["access_token"]
        return data

    def get_headers(self) -> dict:
        """获取请求头。"""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    def get_devices(self) -> dict:
        """获取设备列表。"""
        response = requests.get(
            f"{self.base_url}/api/v1/devices",
            headers=self.get_headers()
        )
        return response.json()

    def motor_move(self, device_id: str, position: float) -> dict:
        """电机运动。"""
        response = requests.post(
            f"{self.base_url}/api/v1/motor/move",
            headers=self.get_headers(),
            json={
                "device_id": device_id,
                "mode": "abs",
                "position": position
            }
        )
        return response.json()


# 使用示例
client = APIClient("http://localhost:8000")
client.login("admin", "password123")
devices = client.get_devices()
```

---

## 参考资料

- RESTful API设计指南
- OpenAPI规范
- JWT RFC 7519
- HTTP语义 RFC 7231

---

## 更新日志

### v1.0 (2026-03-15)
- 初始版本
- API设计原则
- 统一响应格式
- 错误码定义
- 认证授权机制
- 速率限制策略
- API版本管理
- 参数验证规范
- 代码示例
- 故障排除指南
