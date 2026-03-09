# 错误处理优化系统 - 功能说明文档

## 📋 概述

本系统为自旋电子实验平台前端应用提供了完整的错误处理解决方案，包括错误捕获、智能解决方案匹配、详情记录和一键复制功能。

## 🎯 核心功能

### 1. 错误类型分类

系统支持以下错误类型：

- **网络错误 (NETWORK)**: 网络连接失败、请求超时等
- **权限错误 (PERMISSION)**: 权限不足、未授权访问等
- **验证错误 (VALIDATION)**: 参数验证失败、数据格式错误等
- **设备错误 (DEVICE)**: 设备连接失败、串口通信错误等
- **WebSocket错误 (WEBSOCKET)**: 实时数据连接失败等
- **超时错误 (TIMEOUT)**: 操作超时、请求超时等
- **未知错误 (UNKNOWN)**: 其他未分类错误

### 2. 错误严重程度

- **低 (LOW)**: 轻微问题，不影响主要功能
- **中 (MEDIUM)**: 一般问题，影响部分功能
- **高 (HIGH)**: 严重问题，影响核心功能
- **严重 (CRITICAL)**: 致命问题，应用无法继续运行

### 3. 智能解决方案匹配

系统内置了常见错误的解决方案库，能够根据错误消息自动匹配最佳解决方案：

- 错误模式匹配
- 解决步骤指引
- 快捷操作按钮
- 相关文档链接

### 4. 错误详情记录

每个错误都会记录以下信息：

- **错误基本信息**: ID、时间戳、消息、类型、严重程度
- **错误上下文**: 组件名称、操作名称、路由、用户提示
- **错误堆栈**: 完整的错误堆栈跟踪
- **系统状态**: 平台、浏览器、内存、网络连接等
- **用户操作历史**: 最近10条用户操作记录

### 5. 一键复制功能

支持复制以下内容到剪贴板：

- **错误详情**: 包含错误消息、上下文和解决方案
- **错误堆栈**: 完整的错误堆栈跟踪
- **诊断报告**: JSON格式的完整错误报告

## 📁 文件结构

```
src/
├── components/
│   ├── ErrorDisplay.vue          # 错误显示对话框组件
│   ├── ErrorSolution.vue         # 解决方案显示组件
│   └── ErrorHandlerExample.vue   # 使用示例组件
├── composables/
│   └── useErrorHandler.js        # 错误处理组合式函数
└── utils/
    ├── errorSolutions.js         # 错误解决方案库
    └── errorHandlerIntegration.js # 错误处理系统集成工具
```

## 🚀 快速开始

### 1. 在 main.js 中初始化

```javascript
import {
  initializeErrorHandler,
  vueErrorHandler
} from './utils/errorHandlerIntegration'

// 初始化错误处理器
const errorHandler = initializeErrorHandler({
  enableHistory: true,
  enableAutoReport: false,
  onReport: async (report) => {
    // 发送错误报告到服务器
    await fetch('/api/errors/report', {
      method: 'POST',
      body: JSON.stringify(report)
    })
  }
})

// 设置Vue错误处理器
app.config.errorHandler = vueErrorHandler
```

### 2. 在组件中使用

```vue
<script setup>
import { useErrorHandler } from '@/composables/useErrorHandler'
import ErrorDisplay from '@/components/ErrorDisplay.vue'

const {
  currentError,
  errorVisible,
  handleError,
  clearError,
  copyErrorInfo
} = useErrorHandler()

async function fetchData() {
  try {
    const response = await fetch('/api/data')
    return await response.json()
  } catch (error) {
    handleError(error, {
      component: 'MyComponent',
      action: 'fetchData',
      userMessage: '数据加载失败'
    })
  }
}

async function handleCopy(type) {
  const success = await copyErrorInfo(type)
  if (success) {
    ElMessage.success('已复制到剪贴板')
  }
}
</script>

<template>
  <ErrorDisplay
    v-model="errorVisible"
    :error-info="currentError"
    @copy="handleCopy"
    @close="clearError"
  />
</template>
```

### 3. 使用专用错误处理器

```javascript
import {
  handleApiError,
  handleDeviceError,
  handleWebSocketError
} from '@/utils/errorHandlerIntegration'

// API错误
try {
  await api.getData()
} catch (error) {
  handleApiError(error, { url: '/api/data', method: 'GET' })
}

// 设备错误
try {
  await device.connect()
} catch (error) {
  handleDeviceError(error, { name: 'Motor', port: 'COM3' })
}

// WebSocket错误
ws.onerror = (error) => {
  handleWebSocketError(error, { url: wsUrl })
}
```

## 📖 API 文档

### useErrorHandler(options)

错误处理组合式函数。

**参数:**

- `options.enableHistory` (boolean): 是否启用错误历史记录，默认 `true`
- `options.enableAutoReport` (boolean): 是否自动上报错误，默认 `false`
- `options.onReport` (Function): 错误上报回调函数

**返回值:**

- `currentError` (Ref): 当前错误信息对象
- `errorVisible` (Ref): 错误对话框可见性
- `errorHistory` (Ref): 错误历史记录数组
- `errorStats` (Computed): 错误统计信息
- `handleError(error, context)`: 处理错误方法
- `clearError()`: 清除当前错误
- `clearHistory()`: 清空错误历史
- `recordAction(action, data)`: 记录用户操作
- `generateReport(errorInfo)`: 生成错误报告
- `copyErrorInfo(type)`: 复制错误信息到剪贴板

### ErrorDisplay 组件

错误显示对话框组件。

**Props:**

- `modelValue` (boolean): 对话框可见性（双向绑定）
- `errorInfo` (Object): 错误信息对象
- `isGeneratingReport` (boolean): 是否正在生成报告

**Events:**

- `update:modelValue`: 更新对话框可见性
- `auto-action`: 自动操作事件
- `export-report`: 导出错误报告事件
- `copy`: 复制事件
- `close`: 关闭事件

### ErrorSolution 组件

解决方案显示组件。

**Props:**

- `solution` (Object): 解决方案对象

**Events:**

- `auto-action`: 自动操作事件

## 🎨 设计特点

### 1. 用户友好的界面

- 清晰的错误分类和严重程度标识
- 折叠式错误堆栈显示
- 时间线式的解决步骤指引
- 一键复制和导出功能

### 2. 开发者友好的功能

- 完整的错误上下文记录
- 系统状态快照
- 用户操作历史追踪
- JSON格式的错误报告

### 3. 智能化解决方案

- 基于错误模式的自动匹配
- 分步骤操作指引
- 快捷操作按钮
- 相关文档链接

## 🔧 高级配置

### 自定义错误上报

```javascript
const errorHandler = initializeErrorHandler({
  enableAutoReport: true,
  onReport: async (report) => {
    // 发送到错误监控服务
    await fetch('https://errors.example.com/report', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer YOUR_TOKEN'
      },
      body: JSON.stringify(report)
    })
  }
})
```

### 自定义错误处理逻辑

```javascript
const errorHandler = initializeErrorHandler({
  onError: (errorInfo) => {
    // 根据错误类型执行特定操作
    if (errorInfo.type === 'permission') {
      router.push('/login')
    } else if (errorInfo.type === 'network') {
      // 显示离线提示
      showOfflineNotification()
    }
  }
})
```

### 扩展解决方案库

在 `src/utils/errorSolutions.js` 中添加新的解决方案：

```javascript
const SOLUTION_DATABASE = [
  {
    errorPatterns: ['custom error pattern'],
    type: ERROR_TYPES.CUSTOM,
    severity: ERROR_SEVERITY.MEDIUM,
    title: '自定义错误',
    description: '错误描述',
    solutions: [
      {
        step: 1,
        action: '操作步骤',
        description: '详细说明',
        icon: 'Setting'
      }
    ],
    autoActions: [
      { label: '执行操作', action: 'customAction' }
    ]
  }
]
```

## 📊 性能优化

### 1. 错误历史限制

- 最大保存 50 条错误记录
- 最大保存 100 条用户操作记录
- 自动清理过期记录

### 2. 懒加载

- 错误堆栈默认折叠
- 系统信息按需加载
- 大文件延迟加载

### 3. 内存优化

- 使用 `readonly` 包装响应式数据
- 及时清理不需要的引用
- 避免内存泄漏

## 🐛 调试技巧

### 开发环境调试

```javascript
// 在控制台访问全局错误处理器
window.__ERROR_HANDLER__.errorHistory.value
window.__ERROR_HANDLER__.errorStats.value

// 手动触发错误
window.__ERROR_HANDLER__.handleError(
  new Error('测试错误'),
  { component: 'Console', action: 'Debug' }
)
```

### 查看错误报告

```javascript
// 生成错误报告
const report = window.__ERROR_HANDLER__.generateReport()
console.log(JSON.stringify(report, null, 2))
```

## 📝 最佳实践

### 1. 错误处理原则

- 及时捕获错误，避免错误扩散
- 提供有意义的错误上下文
- 记录用户友好的错误消息
- 区分业务错误和系统错误

### 2. 用户体验优化

- 避免技术术语，使用通俗语言
- 提供明确的解决步骤
- 支持一键操作，减少用户负担
- 保留错误详情供技术人员分析

### 3. 错误上报策略

- 区分开发环境和生产环境
- 过滤敏感信息
- 控制上报频率
- 提供用户选择权

## 🔄 更新日志

### v1.1.0 (2026-03-08)
- 📝 更新文档日期和版本信息
- 🔧 优化错误处理性能

### v1.0.0 (2024-03-07)

- ✨ 初始版本发布
- ✨ 支持错误类型分类
- ✨ 智能解决方案匹配
- ✨ 错误详情记录
- ✨ 一键复制功能
- ✨ 错误报告导出

## 📞 技术支持

如有问题或建议，请联系开发团队或提交 Issue。

---

**文档版本**: v1.1.0  
**最后更新**: 2026-03-08  
**维护者**: Agent
