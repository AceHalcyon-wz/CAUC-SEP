# API 使用指南

## API 响应格式

`apiRequest`（以及 `request`, `get`, `post`, `put`, `del`）返回的格式统一为：

```javascript
{
  success: boolean,    // 请求是否成功
  data?: any,         // 实际数据（在后端返回的数据外层再包装一层）
  message?: string    // 消息提示
}
```

## 后端返回格式示例

后端直接返回业务数据：

```javascript
// GET /api/v1/user/users
{
  "total": 100,
  "page": 1,
  "page_size": 20,
  "items": [...]
}

// GET /api/v1/performance/summary
{
  "system": {...},
  "functions": [...],
  "memory": {...}
}
```

## apiRequest 包装后的格式

```javascript
// 成功响应
{
  success: true,
  data: {
    "total": 100,
    "items": [...]
  },
  message: "操作成功"
}

// 失败响应
{
  success: false,
  message: "错误信息",
  error: {...}
}
```

## 正确的使用方式

### 方式 1：使用 unwrapResponse 工具函数（推荐）

```javascript
import { unwrapResponse } from '@/utils/request'

async function loadData() {
  const response = await request.get('/api/v1/user/users')
  const data = unwrapResponse(response)  // 解包获取实际数据
  
  // 现在 data 就是后端返回的原始数据
  console.log(data.total)
  console.log(data.items)
}
```

### 方式 2：手动解包

```javascript
async function loadData() {
  const response = await request.get('/api/v1/user/users')
  
  // 检查 success 字段
  if (response.success) {
    const data = response.data  // 实际数据在 response.data 中
    console.log(data.total)
    console.log(data.items)
  } else {
    console.error('请求失败:', response.message)
  }
}
```

### 方式 3：使用可选链和默认值

```javascript
async function loadData() {
  const response = await request.get('/api/v1/user/users')
  
  // 安全地访问数据
  const data = response?.data || response
  const items = data?.items || []
  const total = data?.total || 0
}
```

## 错误的使用方式 ❌

```javascript
// 错误：直接访问 response.items
async function loadData() {
  const response = await request.get('/api/v1/user/users')
  console.log(response.items)  // undefined! 因为实际数据在 response.data.items
}

// 错误：没有检查 success
async function loadData() {
  const response = await request.get('/api/v1/user/users')
  const items = response.data.items  // 如果 response.success === false，这里会报错
}
```

## 不同场景的最佳实践

### 1. 获取列表数据

```javascript
import { unwrapResponse } from '@/utils/request'

async function loadUserList() {
  try {
    const response = await request.get('/api/v1/user/users', {
      params: { page: 1, page_size: 20 }
    })
    
    const data = unwrapResponse(response)
    userList.value = data.items || []
    pagination.total = data.total || 0
  } catch (error) {
    console.error('加载失败:', error)
    ElMessage.error('加载用户列表失败')
  }
}
```

### 2. 获取单个对象

```javascript
async function loadUserInfo(userId) {
  try {
    const response = await request.get(`/api/v1/user/users/${userId}`)
    const user = unwrapResponse(response)
    
    // 现在可以直接使用 user 对象
    userInfo.value = user
  } catch (error) {
    console.error('加载失败:', error)
  }
}
```

### 3. POST/PUT/DELETE 操作

```javascript
async function updateUser(userData) {
  try {
    const response = await request.put('/api/v1/user/users/1', userData)
    
    if (response.success) {
      ElMessage.success('更新成功')
      // 如果需要返回的数据
      const data = unwrapResponse(response)
      console.log('更新后的用户:', data)
    } else {
      ElMessage.error(response.message)
    }
  } catch (error) {
    console.error('更新失败:', error)
    ElMessage.error('操作失败')
  }
}
```

### 4. 使用 stores 中的 request 函数

stores 中已经正确使用了 `result.success` 检查：

```javascript
// stores/electromagnet.js
const result = await request({
  method: 'POST',
  url: '/electromagnet/current',
  data: { current },
  loadingKey: 'setCurrent',
  onLoading: setLoading,
  onError: showError
})

if (result.success) {
  // 使用 result.data 获取实际数据
  current.value = result.data?.current || 0
}
```

## 工具函数说明

### unwrapResponse(response)

自动解包 API 响应，智能判断是否需要解包：

```javascript
import { unwrapResponse } from '@/utils/request'

// 如果 response 是 {success: true, data: {...}}
// 返回 {...}

// 如果 response 已经是 {...}
// 直接返回 {...}

const data = unwrapResponse(response)
```

### 其他工具函数

```javascript
import {
  request,      // 基础请求函数
  get,          // GET 请求快捷方法
  post,         // POST 请求快捷方法
  put,          // PUT 请求快捷方法
  del,          // DELETE 请求快捷方法
  unwrapResponse, // 解包响应数据
  clearCache,   // 清除请求缓存
  cancelPendingRequests // 取消待处理请求
} from '@/utils/request'
```

## 迁移指南

如果你的代码中有直接使用 `response.xxx` 的地方，请按以下方式修复：

### 修复前
```javascript
const response = await request.get('/api/users')
userList.value = response.items  // ❌ 错误
```

### 修复后
```javascript
const response = await request.get('/api/users')
const data = unwrapResponse(response)
userList.value = data.items  // ✅ 正确
```

## 已修复的文件

- [x] `src/utils/apiRequest.js` - 添加 unwrapResponse 函数
- [x] `src/utils/request.js` - 导出 unwrapResponse
- [x] `src/views/settings/Performance.vue` - 使用 unwrapResponse
- [x] `src/views/settings/UserManagement.vue` - 使用 unwrapResponse

## 待修复的文件

需要检查以下文件中是否有直接使用 `response.xxx` 的情况：

- `src/stores/*.js` - 大部分已正确使用
- `src/api/*.js` - API 封装层
- `src/components/**/*.vue` - 组件
- `src/views/**/*.vue` - 页面

## 测试验证

修复后请验证：

1. 页面能正常加载数据
2. 控制台没有 `Cannot read properties of undefined` 错误
3. 数据展示正确（不是 0 或 undefined）
4. 错误处理正常工作

## 参考资料

- [apiRequest.js 源码](src/utils/apiRequest.js)
- [后端 API 路由](../backend/api/)
- [Axios 文档](https://axios-http.com/)
