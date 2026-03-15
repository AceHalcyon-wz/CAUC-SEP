# 用户管理API

## 概述

用户管理API提供用户认证、信息管理、权限控制和偏好设置功能。所有API均基于RESTful设计，使用JWT进行身份验证。

**基础路径**: `/api/user`

**认证方式**: JWT Bearer Token（Header: `Authorization: Bearer <token>`）

---

## 认证API

### 用户登录

用户通过用户名和密码进行身份验证，成功后返回JWT令牌。

**端点**: `POST /api/user/login`

**请求体**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名（3-50字符） |
| password | string | 是 | 用户密码（6-100字符） |

**请求示例**:

```json
{
    "username": "admin",
    "password": "secure_password_123"
}
```

**成功响应** (200 OK):

```json
{
    "success": true,
    "message": "登录成功",
    "data": {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer",
        "expires_in": 86400,
        "user": {
            "id": 1,
            "username": "admin",
            "email": "admin@cauc-sep.edu.cn",
            "role": "admin",
            "permissions": [
                "device:control",
                "data:read",
                "data:write",
                "user:manage",
                "system:config"
            ],
            "last_login": "2024-03-15T10:30:00Z"
        }
    }
}
```

**错误响应**:

| 状态码 | 错误码 | 说明 |
|--------|--------|------|
| 401 | AUTH_FAILED | 用户名或密码错误 |
| 403 | ACCOUNT_DISABLED | 账户已被禁用 |
| 429 | TOO_MANY_ATTEMPTS | 登录尝试次数过多，请稍后重试 |

```json
{
    "success": false,
    "error": {
        "code": "AUTH_FAILED",
        "message": "用户名或密码错误",
        "details": {
            "remaining_attempts": 3
        }
    }
}
```

---

### 用户登出

注销当前用户会话，使JWT令牌失效。

**端点**: `POST /api/user/logout`

**认证**: 需要

**请求头**:

```
Authorization: Bearer <access_token>
```

**成功响应** (200 OK):

```json
{
    "success": true,
    "message": "登出成功"
}
```

---

### 刷新令牌

在令牌即将过期时，使用当前令牌获取新的访问令牌。

**端点**: `POST /api/user/refresh`

**认证**: 需要

**成功响应** (200 OK):

```json
{
    "success": true,
    "data": {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer",
        "expires_in": 86400
    }
}
```

**错误响应**:

| 状态码 | 错误码 | 说明 |
|--------|--------|------|
| 401 | TOKEN_EXPIRED | 令牌已过期，请重新登录 |
| 401 | TOKEN_INVALID | 无效的令牌 |

---

### 修改密码

用户修改自己的登录密码。

**端点**: `POST /api/user/change-password`

**认证**: 需要

**请求体**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| old_password | string | 是 | 当前密码 |
| new_password | string | 是 | 新密码（6-100字符） |
| confirm_password | string | 是 | 确认新密码 |

**请求示例**:

```json
{
    "old_password": "current_password",
    "new_password": "new_secure_password",
    "confirm_password": "new_secure_password"
}
```

**成功响应** (200 OK):

```json
{
    "success": true,
    "message": "密码修改成功，请重新登录"
}
```

---

## 用户信息API

### 获取当前用户信息

获取当前登录用户的详细信息。

**端点**: `GET /api/user/me`

**认证**: 需要

**成功响应** (200 OK):

```json
{
    "success": true,
    "data": {
        "id": 1,
        "username": "admin",
        "email": "admin@cauc-sep.edu.cn",
        "real_name": "系统管理员",
        "role": "admin",
        "department": "自旋电子实验室",
        "permissions": [
            "device:control",
            "data:read",
            "data:write",
            "user:manage",
            "system:config"
        ],
        "preferences": {
            "language": "zh-CN",
            "theme": "light",
            "notifications_enabled": true
        },
        "created_at": "2024-01-01T00:00:00Z",
        "last_login": "2024-03-15T10:30:00Z",
        "login_count": 156
    }
}
```

---

### 更新用户信息

更新当前用户的个人信息。

**端点**: `PUT /api/user/me`

**认证**: 需要

**请求体**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| real_name | string | 否 | 真实姓名 |
| email | string | 否 | 电子邮箱 |
| department | string | 否 | 所属部门 |

**请求示例**:

```json
{
    "real_name": "张三",
    "email": "zhangsan@cauc-sep.edu.cn",
    "department": "自旋电子实验室"
}
```

**成功响应** (200 OK):

```json
{
    "success": true,
    "message": "用户信息更新成功",
    "data": {
        "id": 1,
        "username": "admin",
        "email": "zhangsan@cauc-sep.edu.cn",
        "real_name": "张三",
        "department": "自旋电子实验室"
    }
}
```

---

### 获取用户列表

管理员获取系统用户列表。

**端点**: `GET /api/user/users`

**认证**: 需要（需要 `user:manage` 权限）

**查询参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| page | integer | 否 | 1 | 页码 |
| page_size | integer | 否 | 20 | 每页数量（最大100） |
| role | string | 否 | - | 按角色筛选 |
| status | string | 否 | - | 按状态筛选（active/disabled） |
| keyword | string | 否 | - | 搜索关键词（用户名/邮箱） |

**请求示例**:

```
GET /api/user/users?page=1&page_size=20&role=researcher&status=active
```

**成功响应** (200 OK):

```json
{
    "success": true,
    "data": {
        "users": [
            {
                "id": 2,
                "username": "researcher01",
                "email": "researcher01@cauc-sep.edu.cn",
                "real_name": "研究员A",
                "role": "researcher",
                "department": "自旋电子实验室",
                "status": "active",
                "created_at": "2024-02-01T00:00:00Z",
                "last_login": "2024-03-14T15:20:00Z"
            }
        ],
        "pagination": {
            "page": 1,
            "page_size": 20,
            "total": 15,
            "total_pages": 1
        }
    }
}
```

---

### 创建用户

管理员创建新用户账户。

**端点**: `POST /api/user/users`

**认证**: 需要（需要 `user:manage` 权限）

**请求体**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名（3-50字符，仅字母数字下划线） |
| password | string | 是 | 初始密码（6-100字符） |
| email | string | 是 | 电子邮箱 |
| real_name | string | 否 | 真实姓名 |
| role | string | 是 | 角色（admin/researcher/operator/viewer） |
| department | string | 否 | 所属部门 |
| permissions | array | 否 | 权限列表 |

**请求示例**:

```json
{
    "username": "new_researcher",
    "password": "initial_password_123",
    "email": "new@cauc-sep.edu.cn",
    "real_name": "新研究员",
    "role": "researcher",
    "department": "自旋电子实验室",
    "permissions": [
        "device:control",
        "data:read",
        "data:write"
    ]
}
```

**成功响应** (201 Created):

```json
{
    "success": true,
    "message": "用户创建成功",
    "data": {
        "id": 10,
        "username": "new_researcher",
        "email": "new@cauc-sep.edu.cn",
        "role": "researcher",
        "created_at": "2024-03-15T10:30:00Z"
    }
}
```

---

### 更新用户

管理员更新指定用户信息。

**端点**: `PUT /api/user/users/{user_id}`

**认证**: 需要（需要 `user:manage` 权限）

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| user_id | integer | 用户ID |

**请求体**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| email | string | 否 | 电子邮箱 |
| real_name | string | 否 | 真实姓名 |
| role | string | 否 | 角色 |
| department | string | 否 | 所属部门 |
| permissions | array | 否 | 权限列表 |
| status | string | 否 | 状态（active/disabled） |

**请求示例**:

```json
{
    "real_name": "更新后的姓名",
    "department": "新材料实验室",
    "permissions": [
        "device:control",
        "data:read",
        "data:write",
        "data:export"
    ]
}
```

**成功响应** (200 OK):

```json
{
    "success": true,
    "message": "用户信息更新成功",
    "data": {
        "id": 10,
        "username": "new_researcher",
        "real_name": "更新后的姓名",
        "department": "新材料实验室",
        "permissions": [
            "device:control",
            "data:read",
            "data:write",
            "data:export"
        ]
    }
}
```

---

### 删除用户

管理员删除指定用户账户。

**端点**: `DELETE /api/user/users/{user_id}`

**认证**: 需要（需要 `user:manage` 权限）

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| user_id | integer | 用户ID |

**成功响应** (200 OK):

```json
{
    "success": true,
    "message": "用户删除成功"
}
```

**错误响应**:

| 状态码 | 错误码 | 说明 |
|--------|--------|------|
| 400 | CANNOT_DELETE_SELF | 不能删除自己的账户 |
| 404 | USER_NOT_FOUND | 用户不存在 |

---

### 重置用户密码

管理员重置指定用户的密码。

**端点**: `POST /api/user/users/{user_id}/reset-password`

**认证**: 需要（需要 `user:manage` 权限）

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| user_id | integer | 用户ID |

**请求体**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| new_password | string | 是 | 新密码（6-100字符） |

**请求示例**:

```json
{
    "new_password": "reset_password_456"
}
```

**成功响应** (200 OK):

```json
{
    "success": true,
    "message": "密码重置成功"
}
```

---

## 权限管理API

### 获取权限列表

获取系统所有可用权限。

**端点**: `GET /api/user/permissions`

**认证**: 需要

**成功响应** (200 OK):

```json
{
    "success": true,
    "data": {
        "permissions": [
            {
                "code": "device:control",
                "name": "设备控制",
                "description": "控制实验设备的权限",
                "category": "device"
            },
            {
                "code": "device:config",
                "name": "设备配置",
                "description": "修改设备配置的权限",
                "category": "device"
            },
            {
                "code": "data:read",
                "name": "数据读取",
                "description": "读取实验数据的权限",
                "category": "data"
            },
            {
                "code": "data:write",
                "name": "数据写入",
                "description": "创建和修改实验数据的权限",
                "category": "data"
            },
            {
                "code": "data:export",
                "name": "数据导出",
                "description": "导出实验数据的权限",
                "category": "data"
            },
            {
                "code": "data:delete",
                "name": "数据删除",
                "description": "删除实验数据的权限",
                "category": "data"
            },
            {
                "code": "user:manage",
                "name": "用户管理",
                "description": "管理用户账户的权限",
                "category": "admin"
            },
            {
                "code": "system:config",
                "name": "系统配置",
                "description": "修改系统配置的权限",
                "category": "admin"
            },
            {
                "code": "system:monitor",
                "name": "系统监控",
                "description": "查看系统监控信息的权限",
                "category": "admin"
            }
        ],
        "categories": [
            {
                "code": "device",
                "name": "设备管理",
                "description": "设备相关权限"
            },
            {
                "code": "data",
                "name": "数据管理",
                "description": "数据相关权限"
            },
            {
                "code": "admin",
                "name": "系统管理",
                "description": "系统管理相关权限"
            }
        ]
    }
}
```

---

### 获取角色列表

获取系统所有角色及其默认权限。

**端点**: `GET /api/user/roles`

**认证**: 需要

**成功响应** (200 OK):

```json
{
    "success": true,
    "data": {
        "roles": [
            {
                "code": "admin",
                "name": "系统管理员",
                "description": "拥有所有权限",
                "permissions": [
                    "device:control",
                    "device:config",
                    "data:read",
                    "data:write",
                    "data:export",
                    "data:delete",
                    "user:manage",
                    "system:config",
                    "system:monitor"
                ],
                "user_count": 2
            },
            {
                "code": "researcher",
                "name": "研究员",
                "description": "可以进行实验和数据分析",
                "permissions": [
                    "device:control",
                    "data:read",
                    "data:write",
                    "data:export"
                ],
                "user_count": 10
            },
            {
                "code": "operator",
                "name": "操作员",
                "description": "可以进行设备操作",
                "permissions": [
                    "device:control",
                    "data:read"
                ],
                "user_count": 5
            },
            {
                "code": "viewer",
                "name": "观察者",
                "description": "只能查看数据",
                "permissions": [
                    "data:read"
                ],
                "user_count": 20
            }
        ]
    }
}
```

---

### 检查权限

检查当前用户是否拥有指定权限。

**端点**: `POST /api/user/check-permission`

**认证**: 需要

**请求体**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| permissions | array | 是 | 需要检查的权限列表 |

**请求示例**:

```json
{
    "permissions": [
        "device:control",
        "data:export"
    ]
}
```

**成功响应** (200 OK):

```json
{
    "success": true,
    "data": {
        "device:control": true,
        "data:export": false,
        "all_granted": false
    }
}
```

---

## 偏好设置API

### 获取用户偏好设置

获取当前用户的偏好设置。

**端点**: `GET /api/user/preferences`

**认证**: 需要

**成功响应** (200 OK):

```json
{
    "success": true,
    "data": {
        "general": {
            "language": "zh-CN",
            "theme": "light",
            "timezone": "Asia/Shanghai",
            "date_format": "YYYY-MM-DD",
            "time_format": "HH:mm:ss"
        },
        "notifications": {
            "email_enabled": true,
            "browser_enabled": true,
            "experiment_complete": true,
            "device_alert": true,
            "system_alert": true
        },
        "experiment": {
            "default_sample_rate": 10,
            "auto_save_interval": 60,
            "data_backup_enabled": true,
            "chart_animation": true
        },
        "display": {
            "chart_theme": "scientific",
            "color_scheme": "default",
            "decimal_places": 4,
            "scientific_notation": true
        }
    }
}
```

---

### 更新用户偏好设置

更新当前用户的偏好设置。

**端点**: `PUT /api/user/preferences`

**认证**: 需要

**请求体**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| general | object | 否 | 通用设置 |
| notifications | object | 否 | 通知设置 |
| experiment | object | 否 | 实验设置 |
| display | object | 否 | 显示设置 |

**请求示例**:

```json
{
    "general": {
        "language": "en-US",
        "theme": "dark"
    },
    "notifications": {
        "email_enabled": false,
        "device_alert": true
    },
    "experiment": {
        "default_sample_rate": 20,
        "auto_save_interval": 30
    }
}
```

**成功响应** (200 OK):

```json
{
    "success": true,
    "message": "偏好设置更新成功",
    "data": {
        "general": {
            "language": "en-US",
            "theme": "dark",
            "timezone": "Asia/Shanghai",
            "date_format": "YYYY-MM-DD",
            "time_format": "HH:mm:ss"
        },
        "notifications": {
            "email_enabled": false,
            "browser_enabled": true,
            "experiment_complete": true,
            "device_alert": true,
            "system_alert": true
        },
        "experiment": {
            "default_sample_rate": 20,
            "auto_save_interval": 30,
            "data_backup_enabled": true,
            "chart_animation": true
        },
        "display": {
            "chart_theme": "scientific",
            "color_scheme": "default",
            "decimal_places": 4,
            "scientific_notation": true
        }
    }
}
```

---

### 重置偏好设置

将用户偏好设置重置为默认值。

**端点**: `POST /api/user/preferences/reset`

**认证**: 需要

**请求体**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| category | string | 否 | 要重置的分类（general/notifications/experiment/display），不指定则重置全部 |

**请求示例**:

```json
{
    "category": "display"
}
```

**成功响应** (200 OK):

```json
{
    "success": true,
    "message": "显示设置已重置为默认值",
    "data": {
        "display": {
            "chart_theme": "scientific",
            "color_scheme": "default",
            "decimal_places": 4,
            "scientific_notation": true
        }
    }
}
```

---

## 登录历史API

### 获取登录历史

获取当前用户的登录历史记录。

**端点**: `GET /api/user/login-history`

**认证**: 需要

**查询参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| page | integer | 否 | 1 | 页码 |
| page_size | integer | 否 | 20 | 每页数量 |
| start_date | string | 否 | - | 开始日期（YYYY-MM-DD） |
| end_date | string | 否 | - | 结束日期（YYYY-MM-DD） |

**请求示例**:

```
GET /api/user/login-history?page=1&page_size=10
```

**成功响应** (200 OK):

```json
{
    "success": true,
    "data": {
        "history": [
            {
                "id": 1001,
                "login_time": "2024-03-15T10:30:00Z",
                "logout_time": null,
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "location": "北京市",
                "status": "success"
            },
            {
                "id": 1000,
                "login_time": "2024-03-14T09:00:00Z",
                "logout_time": "2024-03-14T18:30:00Z",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "location": "北京市",
                "status": "success"
            }
        ],
        "pagination": {
            "page": 1,
            "page_size": 10,
            "total": 156,
            "total_pages": 16
        },
        "statistics": {
            "total_logins": 156,
            "unique_ips": 3,
            "last_login": "2024-03-15T10:30:00Z",
            "average_session_duration": 28800
        }
    }
}
```

---

## 错误码参考

### 认证错误

| 错误码 | HTTP状态码 | 说明 |
|--------|------------|------|
| AUTH_FAILED | 401 | 用户名或密码错误 |
| TOKEN_EXPIRED | 401 | 令牌已过期 |
| TOKEN_INVALID | 401 | 无效的令牌 |
| TOKEN_MISSING | 401 | 缺少认证令牌 |
| ACCOUNT_DISABLED | 403 | 账户已被禁用 |
| ACCOUNT_LOCKED | 403 | 账户已被锁定 |
| TOO_MANY_ATTEMPTS | 429 | 登录尝试次数过多 |

### 权限错误

| 错误码 | HTTP状态码 | 说明 |
|--------|------------|------|
| PERMISSION_DENIED | 403 | 权限不足 |
| ROLE_NOT_FOUND | 404 | 角色不存在 |
| PERMISSION_NOT_FOUND | 404 | 权限不存在 |

### 用户错误

| 错误码 | HTTP状态码 | 说明 |
|--------|------------|------|
| USER_NOT_FOUND | 404 | 用户不存在 |
| USERNAME_EXISTS | 400 | 用户名已存在 |
| EMAIL_EXISTS | 400 | 邮箱已存在 |
| INVALID_USERNAME | 400 | 用户名格式无效 |
| INVALID_EMAIL | 400 | 邮箱格式无效 |
| INVALID_PASSWORD | 400 | 密码格式无效 |
| PASSWORD_MISMATCH | 400 | 密码不匹配 |
| CANNOT_DELETE_SELF | 400 | 不能删除自己的账户 |

### 系统错误

| 错误码 | HTTP状态码 | 说明 |
|--------|------------|------|
| INTERNAL_ERROR | 500 | 内部服务器错误 |
| DATABASE_ERROR | 500 | 数据库错误 |

---

## 数据模型

### User 用户模型

```typescript
interface User {
    id: number;                    // 用户ID
    username: string;              // 用户名
    email: string;                 // 电子邮箱
    real_name?: string;            // 真实姓名
    role: UserRole;                // 角色
    department?: string;           // 所属部门
    permissions: string[];         // 权限列表
    preferences: UserPreferences;  // 偏好设置
    status: UserStatus;            // 账户状态
    created_at: string;            // 创建时间（ISO 8601）
    last_login?: string;           // 最后登录时间（ISO 8601）
    login_count: number;           // 登录次数
}

type UserRole = 'admin' | 'researcher' | 'operator' | 'viewer';
type UserStatus = 'active' | 'disabled' | 'locked';
```

### Permission 权限模型

```typescript
interface Permission {
    code: string;           // 权限代码
    name: string;           // 权限名称
    description: string;    // 权限描述
    category: string;       // 权限分类
}
```

### Role 角色模型

```typescript
interface Role {
    code: string;           // 角色代码
    name: string;           // 角色名称
    description: string;    // 角色描述
    permissions: string[];  // 默认权限列表
    user_count: number;     // 用户数量
}
```

### UserPreferences 偏好设置模型

```typescript
interface UserPreferences {
    general: {
        language: string;           // 语言（zh-CN, en-US）
        theme: string;              // 主题（light, dark）
        timezone: string;           // 时区
        date_format: string;        // 日期格式
        time_format: string;        // 时间格式
    };
    notifications: {
        email_enabled: boolean;     // 邮件通知
        browser_enabled: boolean;   // 浏览器通知
        experiment_complete: boolean;  // 实验完成通知
        device_alert: boolean;      // 设备告警通知
        system_alert: boolean;      // 系统告警通知
    };
    experiment: {
        default_sample_rate: number;   // 默认采样率
        auto_save_interval: number;    // 自动保存间隔（秒）
        data_backup_enabled: boolean;  // 数据备份开关
        chart_animation: boolean;      // 图表动画
    };
    display: {
        chart_theme: string;        // 图表主题
        color_scheme: string;       // 配色方案
        decimal_places: number;     // 小数位数
        scientific_notation: boolean;  // 科学计数法
    };
}
```

---

## 使用示例

### 登录并获取用户信息

```python
import requests

# 登录
login_response = requests.post(
    'http://localhost:8000/api/user/login',
    json={
        'username': 'admin',
        'password': 'secure_password'
    }
)

token = login_response.json()['data']['access_token']

# 获取用户信息
headers = {'Authorization': f'Bearer {token}'}
user_info = requests.get(
    'http://localhost:8000/api/user/me',
    headers=headers
)

print(user_info.json())
```

### 检查权限并执行操作

```python
# 检查权限
check_response = requests.post(
    'http://localhost:8000/api/user/check-permission',
    headers=headers,
    json={'permissions': ['device:control']}
)

if check_response.json()['data']['device:control']:
    # 执行设备控制操作
    control_response = requests.post(
        'http://localhost:8000/api/motor/move',
        headers=headers,
        json={'target_position': 1000}
    )
    print(control_response.json())
else:
    print('没有设备控制权限')
```

### 更新偏好设置

```python
# 更新主题和语言
preferences_response = requests.put(
    'http://localhost:8000/api/user/preferences',
    headers=headers,
    json={
        'general': {
            'language': 'en-US',
            'theme': 'dark'
        }
    }
)

print(preferences_response.json())
```

---

## 注意事项

1. **令牌有效期**: JWT令牌默认有效期为24小时，建议在过期前调用刷新接口
2. **密码策略**: 密码长度6-100字符，建议包含大小写字母、数字和特殊字符
3. **权限继承**: 用户权限 = 角色默认权限 + 自定义权限
4. **并发登录**: 系统默认允许多设备同时登录，可在系统配置中修改
5. **审计日志**: 所有用户操作都会记录到审计日志中
