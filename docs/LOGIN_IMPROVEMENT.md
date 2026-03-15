# 登录系统改进方案

## 📋 概述

本次改进将原有的**硬编码账号密码登录**方案升级为**多模式登录系统**，包括：
- ✅ **快速登录模式** - 前端生成临时令牌，无需调用后端 API
- ✅ **传统登录模式** - 保留原有 API 接口登录方式（兼容）
- ✅ **访客模式** - 无需密码，仅查看权限

## 🎯 解决的问题

### 原有问题
1. ❌ **API 接口依赖** - 必须后端服务正常才能登录
2. ❌ **硬编码密码** - 账号密码直接写在代码中
3. ❌ **网络问题影响** - 网络故障导致无法登录
4. ❌ **数据库初始化** - 依赖后端创建默认用户

### 改进方案优势
1. ✅ **离线登录** - 快速登录模式不依赖后端 API
2. ✅ **配置外置** - 账号配置集中管理，支持环境变量
3. ✅ **多模式选择** - 用户可根据场景选择登录方式
4. ✅ **更安全** - 使用令牌机制，密码不暴露

## 📁 新增文件

### 1. 配置文件
- `frontend/src/config/loginConfig.js` - 登录配置和账号管理

### 2. 工具模块
- `frontend/src/utils/tokenAuth.js` - 令牌生成、验证和管理
- `frontend/src/utils/healthCheck.js` - 后端服务健康检查

### 3. 组件更新
- `frontend/src/views/Login.vue` - 登录页面（支持多模式切换）

## 🚀 使用方式

### 快速登录模式（默认）
```javascript
import { quickLogin } from '@/utils/tokenAuth'
import { PRESET_ACCOUNTS } from '@/config/loginConfig'

// 用户点击账号卡片
const account = PRESET_ACCOUNTS[0] // admin 账号
const result = quickLogin(account)

if (result.success) {
  // 令牌已保存到 localStorage
  // 用户已登录
}
```

### 传统登录模式（兼容）
```javascript
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const result = await userStore.login({
  username: 'admin',
  password: 'admin123'
})
```

### 访客模式
```javascript
import { guestLogin } from '@/utils/tokenAuth'

const result = guestLogin()
// 生成访客令牌，有效期 2 小时
```

## 🔧 配置说明

### 账号配置
```javascript
// frontend/src/config/loginConfig.js
export const PRESET_ACCOUNTS = [
  {
    id: 'admin',
    username: 'admin',
    displayName: '管理员',
    role: 'admin',
    // 生产环境应从环境变量读取
    password: import.meta.env.VITE_ADMIN_PASSWORD || 'admin123',
    quickToken: 'quick_admin_token_2026',
    permissions: ['all']
  }
  // ...
]
```

### 环境变量（可选）
```bash
# .env
VITE_ADMIN_PASSWORD=admin123
VITE_USER_PASSWORD=123456
```

### 令牌配置
```javascript
export const LOGIN_CONFIG = {
  defaultMode: 'quick',          // 默认登录模式
  enableQuickLogin: true,        // 启用快速登录
  enableRemember: true,          // 记住登录状态
  tokenExpiresIn: 24,            // 令牌有效期（小时）
  enableGuestMode: true          // 启用访客模式
}
```

## 🔐 安全机制

### 临时令牌
- 前端生成的临时令牌格式：`temp_token.{payload}.{signature}`
- 包含用户信息、权限、过期时间
- 有效期默认 24 小时
- 不支持跨域使用

### 访客令牌
- 访客令牌格式：`guest_token.{payload}.{signature}`
- 仅包含只读权限
- 有效期 2 小时
- 适合临时访问

### 令牌存储
```javascript
// 保存令牌
localStorage.setItem('auth_token', token)
localStorage.setItem('token_type', 'temp')
localStorage.setItem('token_expiry', expiry)

// 获取令牌
const { token, type, isExpired } = getToken()

// 验证令牌
const isValid = validateToken(token)
```

## 📊 登录流程

### 快速登录流程
```
用户点击账号
  ↓
生成临时令牌（前端）
  ↓
保存令牌到 localStorage
  ↓
跳转到首页
```

### 传统登录流程
```
用户点击账号
  ↓
调用后端 API（/api/v1/user/login）
  ↓
后端验证并返回 JWT 令牌
  ↓
保存令牌到 localStorage
  ↓
跳转到首页
```

### 访客登录流程
```
用户点击访客模式
  ↓
生成访客令牌（前端）
  ↓
保存令牌到 localStorage
  ↓
跳转到首页（只读权限）
```

## 🛠️ API 健康检查

### 手动检查
```javascript
import { checkHealth, HealthStatus } from '@/utils/healthCheck'

const result = await checkHealth()

if (result.healthy) {
  console.log('后端服务正常')
} else {
  console.log('后端服务异常:', result.error)
}
```

### 自动检查
```javascript
import { shouldUseQuickLogin } from '@/utils/healthCheck'

const { shouldUseQuickLogin: useQuick, reason } = await shouldUseQuickLogin()

if (!useQuick) {
  message.info(reason)
  // 建议用户使用快速登录模式
}
```

## 🎨 UI 交互

### 登录模式切换
- **快速登录** - 蓝色主题，闪电图标
- **账号密码** - 灰色主题，用户图标
- **访客模式** - 黄色主题，眼睛图标

### 状态反馈
- ✅ 选中状态 - 卡片边框高亮
- ⏳ 加载状态 - 旋转动画
- ✔️ 成功状态 - 对勾图标

## 📝 迁移指南

### 从旧版本迁移

1. **保留原有 API 登录**
   - 传统登录模式完全兼容原有逻辑
   - 无需修改后端代码

2. **更新前端配置**
   ```javascript
   // 旧代码
   const accounts = [...] // 硬编码在 Login.vue
   
   // 新代码
   import { PRESET_ACCOUNTS } from '@/config/loginConfig'
   ```

3. **更新登录逻辑**
   ```javascript
   // 旧代码
   await userStore.login({ username, password })
   
   // 新代码（快速登录）
   quickLogin(account)
   
   // 新代码（传统登录）
   await userStore.login({ username, password })
   ```

## 🔍 调试技巧

### 查看令牌信息
```javascript
import { getToken, decodeToken } from '@/utils/tokenAuth'

const { token, type } = getToken()
const payload = decodeToken(token)

console.log('令牌类型:', type)
console.log('用户信息:', payload)
console.log('过期时间:', new Date(payload.exp))
```

### 清除登录状态
```javascript
import { clearToken } from '@/utils/tokenAuth'

clearToken()
// 清除所有令牌，用户需重新登录
```

### 模拟后端异常
```javascript
// 临时禁用 API 登录，测试快速登录
import { clearHealthCache } from '@/utils/healthCheck'
clearHealthCache()

// 强制使用快速登录
```

## 📈 性能优化

### 缓存策略
- 健康检查结果缓存 30 秒
- 避免频繁请求后端

### 令牌续期
```javascript
import { refreshToken } from '@/utils/tokenAuth'

// 令牌过期前自动续期
refreshToken()
```

## 🚨 错误处理

### 常见错误
```javascript
// 令牌过期
{
  success: false,
  message: '令牌已过期，请重新登录'
}

// 后端服务不可用
{
  success: false,
  message: '后端服务不可用，已切换到快速登录模式'
}

// 无效令牌
{
  success: false,
  message: '无效的令牌格式'
}
```

## 📚 相关文档

- [API 接口文档](/docs/api.md)
- [用户认证指南](/docs/auth.md)
- [安全最佳实践](/docs/security.md)

## 🤝 贡献指南

如需添加新的登录模式或修改配置，请参考：
1. `frontend/src/config/loginConfig.js` - 添加配置
2. `frontend/src/utils/tokenAuth.js` - 实现令牌逻辑
3. `frontend/src/views/Login.vue` - 更新 UI

## 📄 许可证

© 2024-2026 CAUC-SEP 自旋电子器件实验平台
