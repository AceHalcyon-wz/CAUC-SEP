# 错误处理组合式函数使用指南

**文件路径**: `frontend/src/composables/useErrorHandler.js`  
**版本**: v1.0  
**更新日期**: 2026-03-08

---

## 概述

`useErrorHandler` 是一个功能完整的错误处理组合式函数，提供：

- 统一的错误捕获与记录
- 智能错误分析与解决方案匹配
- 错误历史记录与统计
- 离线错误缓存与同步
- 错误报告生成与上报
- 用户操作追踪

---

## 快速开始

### 基本使用

```vue
<script setup>
import { useErrorHandler } from '@/composables/useErrorHandler'

// 创建错误处理器
const { 
  handleError, 
  currentError, 
  errorVisible,
  clearError 
} = useErrorHandler({
  enableHistory: true,
  enableOfflineCache: true
})

// 执行可能出错的操作
async function fetchData() {
  try {
    const response = await fetch('/api/data')
    return await response.json()
  } catch (error) {
    // 处理错误
    const errorInfo = handleError(error, {
      component: 'DataComponent',
      action: 'fetchData',
      userMessage: '数据加载失败，请稍后重试'
    })
    
    // errorInfo 包含错误详情和解决方案
    console.log('解决方案:', errorInfo.solution?.title)
  }
}
</script>

<template>
  <div v-if="errorVisible && currentError" class="error-modal">
    <h3>{{ currentError.solution?.title || '发生错误' }}</h3>
    <p>{{ currentError.context.userMessage || currentError.message }}</p>
    <button @click="clearError">关闭</button>
  </div>
</template>
```

---

## API 参考

### 配置选项

```typescript
interface ErrorHandlerOptions {
  // 是否启用错误历史记录，默认true
  enableHistory?: boolean
  
  // 是否自动上报错误，默认false
  enableAutoReport?: boolean
  
  // 是否启用离线错误缓存，默认true
  enableOfflineCache?: boolean
  
  // 是否启用错误日志记录，默认true
  enableErrorLog?: boolean
  
  // 离线缓存最大错误数量，默认100
  maxOfflineErrors?: number
  
  // 错误上报回调函数
  onReport?: (report: ErrorReport) => Promise<void>
}
```

### 返回值

```typescript
interface ErrorHandlerReturn {
  // 状态
  currentError: Ref<ErrorInfo | null>      // 当前错误
  errorVisible: Ref<boolean>               // 错误是否可见
  errorHistory: Ref<ErrorInfo[]>           // 错误历史
  errorStats: ComputedRef<ErrorStats>      // 错误统计
  isGeneratingReport: Ref<boolean>         // 是否正在生成报告
  offlineErrorQueue: Ref<OfflineError[]>   // 离线错误队列
  isSyncingOffline: Ref<boolean>           // 是否正在同步
  reportQueue: Ref<ReportItem[]>           // 上报队列
  isReporting: Ref<boolean>                // 是否正在上报
  
  // 方法
  handleError: (error: Error | string, context?: ErrorContext) => ErrorInfo
  clearError: () => void
  clearHistory: () => void
  recordAction: (action: string, data?: any) => void
  generateReport: (errorInfo?: ErrorInfo) => ErrorReport | null
  reportError: (errorInfo: ErrorInfo) => Promise<void>
  copyErrorInfo: (type: 'detail' | 'stack' | 'report', errorInfo?: ErrorInfo) => Promise<boolean>
  
  // 离线相关
  syncOfflineErrors: () => Promise<SyncResult>
  getOfflineErrorStats: () => OfflineStats
  clearOfflineErrors: () => Promise<void>
  
  // 上报相关
  batchReportErrors: (options?: BatchReportOptions) => Promise<BatchReportResult>
  getReportQueueStatus: () => ReportQueueStatus
  clearReportQueue: () => void
  
  // 分析
  getErrorTrends: (days?: number) => ErrorTrend[]
  
  // 工具函数
  getErrorIcon: (type: string) => string
  getSeverityColor: (severity: string) => string
  getErrorTypeLabel: (type: string) => string
}
```

---

## 错误类型与严重程度

### 错误类型

```typescript
enum ERROR_TYPES {
  NETWORK = 'network',           // 网络错误
  TIMEOUT = 'timeout',           // 超时错误
  VALIDATION = 'validation',     // 验证错误
  PERMISSION = 'permission',     // 权限错误
  NOT_FOUND = 'not_found',       // 资源未找到
  SERVER = 'server',             // 服务器错误
  CLIENT = 'client',             // 客户端错误
  WEBSOCKET = 'websocket',       // WebSocket错误
  DEVICE = 'device',             // 设备错误
  UNKNOWN = 'unknown'            // 未知错误
}
```

### 严重程度

```typescript
enum ERROR_SEVERITY {
  LOW = 'low',           // 低 - 不影响主要功能
  MEDIUM = 'medium',     // 中 - 影响部分功能
  HIGH = 'high',         // 高 - 影响主要功能
  CRITICAL = 'critical'  // 严重 - 系统不可用
}
```

---

## 使用示例

### 1. 基本错误处理

```vue
<script setup>
import { useErrorHandler, ERROR_TYPES, ERROR_SEVERITY } from '@/composables/useErrorHandler'

const { 
  handleError, 
  currentError, 
  errorVisible,
  clearError,
  getErrorIcon,
  getSeverityColor 
} = useErrorHandler()

// 处理异步操作错误
async function loadUserData(userId) {
  try {
    const response = await fetch(`/api/users/${userId}`)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    return await response.json()
  } catch (error) {
    handleError(error, {
      component: 'UserProfile',
      action: 'loadUserData',
      userMessage: '无法加载用户数据'
    })
    return null
  }
}

// 处理表单验证错误
function validateForm(formData) {
  const errors = []
  
  if (!formData.email) {
    errors.push({ field: 'email', message: '邮箱不能为空' })
  }
  
  if (!formData.password) {
    errors.push({ field: 'password', message: '密码不能为空' })
  }
  
  if (errors.length > 0) {
    handleError(new Error('表单验证失败'), {
      component: 'LoginForm',
      action: 'validateForm',
      data: { errors },
      userMessage: '请检查表单填写是否正确'
    })
    return false
  }
  
  return true
}
</script>

<template>
  <div v-if="errorVisible && currentError" 
       class="error-alert"
       :style="{ borderColor: getSeverityColor(currentError.severity) }">
    <div class="error-header">
      <span class="error-icon">{{ getErrorIcon(currentError.type) }}</span>
      <span class="error-title">{{ currentError.solution?.title || '操作失败' }}</span>
    </div>
    <p class="error-message">
      {{ currentError.context.userMessage || currentError.message }}
    </p>
    <div v-if="currentError.solution" class="error-solution">
      <p>{{ currentError.solution.description }}</p>
    </div>
    <button @click="clearError">知道了</button>
  </div>
</template>
```

### 2. 错误上报

```vue
<script setup>
import { useErrorHandler } from '@/composables/useErrorHandler'

// 配置错误上报
const { handleError, syncOfflineErrors, batchReportErrors } = useErrorHandler({
  enableAutoReport: false,  // 手动控制上报
  enableOfflineCache: true,
  onReport: async (report) => {
    // 发送到错误监控服务
    await fetch('/api/errors/report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(report)
    })
  }
})

// 手动上报错误
async function reportCurrentError() {
  const result = await batchReportErrors({
    batchSize: 10,
    maxRetries: 3
  })
  
  console.log(`上报完成: ${result.reported}/${result.total}`)
}

// 同步离线错误
async function syncErrors() {
  if (navigator.onLine) {
    const result = await syncOfflineErrors()
    console.log(`同步完成: ${result.synced} 条`)
  }
}

// 监听网络状态
window.addEventListener('online', syncErrors)
</script>
```

### 3. 错误统计与趋势分析

```vue
<script setup>
import { useErrorHandler } from '@/composables/useErrorHandler'
import { computed } from 'vue'

const { errorStats, errorHistory, getErrorTrends } = useErrorHandler()

// 错误统计
const stats = computed(() => errorStats.value)

// 获取趋势数据
const trends = computed(() => getErrorTrends(7))

// 按类型统计
const byType = computed(() => {
  const result = {}
  Object.entries(stats.value.byType).forEach(([type, count]) => {
    result[type] = {
      count,
      percentage: ((count / stats.value.total) * 100).toFixed(1)
    }
  })
  return result
})

// 按严重程度统计
const bySeverity = computed(() => stats.value.bySeverity)
</script>

<template>
  <div class="error-dashboard">
    <h2>错误统计</h2>
    
    <div class="stats-overview">
      <div class="stat-card">
        <span class="stat-value">{{ stats.total }}</span>
        <span class="stat-label">总错误数</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{{ stats.recentCount.lastHour }}</span>
        <span class="stat-label">最近1小时</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{{ stats.recentCount.lastDay }}</span>
        <span class="stat-label">最近24小时</span>
      </div>
    </div>
    
    <div class="error-trends">
      <h3>错误趋势（最近7天）</h3>
      <div class="trend-chart">
        <div v-for="day in trends" :key="day.date" class="trend-bar">
          <div class="bar" :style="{ height: `${day.total * 5}px` }"></div>
          <span class="date">{{ day.date }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
```

### 4. 全局错误处理

```javascript
// main.js
import { createApp } from 'vue'
import { setupGlobalErrorHandler, useErrorHandler } from '@/composables/useErrorHandler'
import App from './App.vue'

const app = createApp(App)

// 设置全局错误处理器
const cleanup = setupGlobalErrorHandler({
  onUnhandledError: (error) => {
    const { handleError } = useErrorHandler()
    handleError(error, {
      component: 'Global',
      action: 'unhandled_error',
      userMessage: '程序发生未知错误'
    })
  },
  onUnhandledRejection: (error) => {
    const { handleError } = useErrorHandler()
    handleError(error, {
      component: 'Global',
      action: 'unhandled_rejection',
      userMessage: '异步操作发生错误'
    })
  }
})

app.mount('#app')

// 应用卸载时清理
window.addEventListener('beforeunload', cleanup)
```

### 5. 用户操作追踪

```vue
<script setup>
import { useErrorHandler } from '@/composables/useErrorHandler'

const { handleError, recordAction } = useErrorHandler()

// 记录用户操作
function handleClick() {
  recordAction('button_click', { buttonId: 'submit' })
  // 执行操作...
}

function handleNavigation(to) {
  recordAction('navigation', { from: currentRoute, to })
}

// 错误发生时，用户操作历史会自动包含在错误报告中
async function riskyOperation() {
  recordAction('start_operation', { operation: 'data_sync' })
  
  try {
    await performSync()
    recordAction('complete_operation', { operation: 'data_sync' })
  } catch (error) {
    // 错误报告会包含最近的用户操作
    handleError(error, {
      component: 'SyncManager',
      action: 'data_sync'
    })
  }
}
</script>
```

### 6. 错误报告复制

```vue
<script setup>
import { useErrorHandler } from '@/composables/useErrorHandler'

const { 
  handleError, 
  currentError, 
  copyErrorInfo,
  generateReport 
} = useErrorHandler()

// 复制错误详情
async function copyDetails() {
  const success = await copyErrorInfo('detail')
  if (success) {
    alert('错误详情已复制到剪贴板')
  }
}

// 复制错误堆栈
async function copyStack() {
  const success = await copyErrorInfo('stack')
  if (success) {
    alert('错误堆栈已复制到剪贴板')
  }
}

// 复制完整报告
async function copyReport() {
  const success = await copyErrorInfo('report')
  if (success) {
    alert('错误报告已复制到剪贴板')
  }
}

// 下载报告文件
function downloadReport() {
  const report = generateReport()
  if (!report) return
  
  const blob = new Blob([JSON.stringify(report, null, 2)], { 
    type: 'application/json' 
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `error-report-${report.reportId}.json`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <div class="error-actions">
    <button @click="copyDetails">复制详情</button>
    <button @click="copyStack">复制堆栈</button>
    <button @click="copyReport">复制报告</button>
    <button @click="downloadReport">下载报告</button>
  </div>
</template>
```

---

## 高级功能

### 错误聚合

相似错误会自动聚合，避免重复处理：

```javascript
const { handleError } = useErrorHandler()

// 相同错误在5秒窗口内会被聚合
for (let i = 0; i < 10; i++) {
  handleError(new Error('网络连接失败'), {
    component: 'NetworkManager',
    action: 'connect'
  })
}

// 错误信息会包含聚合计数
// errorInfo.aggregated = true
// errorInfo.occurrenceCount = 10
```

### 离线缓存

离线时错误会缓存到 IndexedDB，在线后自动同步：

```javascript
const { 
  syncOfflineErrors, 
  getOfflineErrorStats,
  clearOfflineErrors 
} = useErrorHandler({
  enableOfflineCache: true,
  maxOfflineErrors: 100,
  onReport: sendToServer
})

// 查看离线错误状态
const offlineStats = getOfflineErrorStats()
console.log(`待同步错误: ${offlineStats.queueLength}`)

// 手动同步
if (navigator.onLine) {
  const result = await syncOfflineErrors()
  console.log(`已同步 ${result.synced} 条错误`)
}

// 清除离线缓存
await clearOfflineErrors()
```

### 批量上报

支持批量上报错误，提高效率：

```javascript
const { batchReportErrors, getReportQueueStatus } = useErrorHandler({
  onReport: sendToServer
})

// 查看上报队列状态
const status = getReportQueueStatus()
console.log(`队列长度: ${status.queueLength}`)

// 批量上报
const result = await batchReportErrors({
  batchSize: 10,
  maxRetries: 3
})

console.log(`成功: ${result.reported}, 失败: ${result.failed}`)
```

---

## 错误解决方案

系统内置常见错误的解决方案：

| 错误类型 | 解决方案 |
|----------|----------|
| `network` | 检查网络连接，稍后重试 |
| `timeout` | 请求超时，请检查网络或增加超时时间 |
| `validation` | 输入数据格式不正确，请检查后重试 |
| `permission` | 权限不足，请联系管理员 |
| `not_found` | 请求的资源不存在 |
| `server` | 服务器错误，请稍后重试 |
| `websocket` | WebSocket连接断开，正在重连... |
| `device` | 设备通信异常，请检查设备连接 |

---

## 最佳实践

### 1. 错误分类处理

```javascript
const { handleError, ERROR_TYPES, ERROR_SEVERITY } = useErrorHandler()

function handleApiError(error, response) {
  // 根据HTTP状态码分类
  let type = ERROR_TYPES.UNKNOWN
  let severity = ERROR_SEVERITY.MEDIUM
  let userMessage = '操作失败'
  
  if (response.status === 401) {
    type = ERROR_TYPES.PERMISSION
    severity = ERROR_SEVERITY.HIGH
    userMessage = '登录已过期，请重新登录'
  } else if (response.status === 404) {
    type = ERROR_TYPES.NOT_FOUND
    severity = ERROR_SEVERITY.LOW
    userMessage = '请求的资源不存在'
  } else if (response.status >= 500) {
    type = ERROR_TYPES.SERVER
    severity = ERROR_SEVERITY.HIGH
    userMessage = '服务器错误，请稍后重试'
  }
  
  handleError(error, {
    component: 'ApiClient',
    action: 'request',
    data: { status: response.status },
    userMessage
  })
}
```

### 2. 错误恢复

```javascript
const { handleError, clearError } = useErrorHandler()

async function withRetry(operation, maxRetries = 3) {
  let lastError = null
  
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await operation()
    } catch (error) {
      lastError = error
      if (i < maxRetries - 1) {
        await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)))
      }
    }
  }
  
  // 所有重试都失败，处理错误
  handleError(lastError, {
    component: 'RetryHandler',
    action: 'withRetry',
    data: { retries: maxRetries },
    userMessage: `操作失败，已重试 ${maxRetries} 次`
  })
  
  throw lastError
}
```

### 3. 错误边界组件

```vue
<!-- ErrorBoundary.vue -->
<script setup>
import { ref, onErrorCaptured } from 'vue'
import { useErrorHandler } from '@/composables/useErrorHandler'

const { handleError, clearError, currentError } = useErrorHandler()
const hasError = ref(false)

// 捕获子组件错误
onErrorCaptured((error, instance, info) => {
  handleError(error, {
    component: instance?.$options?.name || 'Unknown',
    action: 'render',
    data: { info }
  })
  
  hasError.value = true
  return false  // 阻止错误继续传播
})

function retry() {
  hasError.value = false
  clearError()
}
</script>

<template>
  <slot v-if="!hasError" />
  <div v-else class="error-boundary">
    <h3>组件加载失败</h3>
    <p>{{ currentError?.message }}</p>
    <button @click="retry">重试</button>
  </div>
</template>
```

---

## 相关文档

- [WebSocket组合式函数使用指南](./websocket-composable.md)
- [健康监控API文档](../api/health-api.md)
- [故障排除指南](../troubleshooting.md)
