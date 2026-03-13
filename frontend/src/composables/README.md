# 组合式函数使用指南

## 概述

本目录包含了一系列用于Vue 3应用的组合式函数（Composables），提供了错误处理、进度管理、在线状态检测、WebSocket连接管理等功能。

## 新增组合式函数

### 1. useProgress - 操作进度管理

提供完整的操作进度跟踪功能，支持进度更新、取消操作、子任务管理等功能。

#### 基本用法

```javascript
import { useProgress } from '@/composables'

const {
  isRunning,
  progress,
  status,
  message,
  startOperation,
  updateProgress,
  completeOperation,
  cancelOperation
} = useProgress({
  autoResetDelay: 3000,
  onComplete: (info) => console.log('操作完成:', info)
})

// 开始操作
startOperation('数据采集', { total: 100 })

// 更新进度
updateProgress(50, '已处理50%')

// 完成操作
completeOperation('操作成功完成')

// 取消操作
cancelOperation('用户取消')
```

#### 主要功能

- ✅ 进度跟踪（0-100%）
- ✅ 操作状态管理（idle/running/paused/completed/failed/cancelled）
- ✅ 子任务支持
- ✅ 自动重置
- ✅ 预计剩余时间计算
- ✅ AbortController集成（支持取消操作）

#### API

**状态**

- `isRunning` - 是否正在运行
- `progress` - 进度值（0-100）
- `status` - 操作状态
- `message` - 状态消息
- `duration` - 已持续时间
- `estimatedTimeRemaining` - 预计剩余时间

**方法**

- `startOperation(name, meta)` - 开始操作
- `updateProgress(value, message)` - 更新进度
- `completeOperation(message)` - 完成操作
- `failOperation(error, message)` - 失败操作
- `cancelOperation(reason)` - 取消操作
- `pauseOperation()` - 暂停操作
- `resumeOperation()` - 恢复操作
- `resetProgress()` - 重置进度

---

### 2. useOnlineStatus - 在线状态检测

提供网络连接状态监控、离线持续时间统计、网络质量评估等功能。

#### 基本用法

```javascript
import { useOnlineStatus } from '@/composables'

const {
  isOnline,
  isOffline,
  offlineDuration,
  formattedOfflineDuration,
  networkQuality,
  networkQualityLabel,
  performHealthCheck
} = useOnlineStatus({
  checkInterval: 15000,
  onOnline: () => console.log('网络已恢复'),
  onOffline: () => console.log('网络已断开')
})

// 检查网络状态
if (isOffline.value) {
  showToast('当前处于离线状态')
}

// 显示离线时长
console.log(`已离线 ${formattedOfflineDuration.value}`)

// 主动健康检查
await performHealthCheck()
```

#### 主要功能

- ✅ 实时在线/离线状态检测
- ✅ 离线持续时间统计
- ✅ 网络连接类型识别（4G/3G/WiFi等）
- ✅ 网络质量评估
- ✅ 定期健康检查
- ✅ 网络状态历史记录

#### API

**状态**

- `isOnline` - 是否在线
- `isOffline` - 是否离线
- `offlineDuration` - 离线持续时间（毫秒）
- `formattedOfflineDuration` - 格式化的离线时长
- `connectionType` - 连接类型
- `networkQuality` - 网络质量评分（0-100）
- `networkQualityLabel` - 网络质量标签（优秀/良好/一般/较差/很差）

**方法**

- `performHealthCheck()` - 执行健康检查

---

### 3. useWebSocketReconnect - WebSocket自动重连

提供智能的WebSocket重连策略、消息队列管理、心跳检测等功能。

#### 基本用法

```javascript
import { useWebSocketReconnect, RECONNECT_STRATEGY } from '@/composables'

const {
  isConnected,
  isReconnecting,
  retryCount,
  connect,
  disconnect,
  send,
  manualReconnect
} = useWebSocketReconnect('ws://localhost:8000/ws', {
  maxRetries: 10,
  strategy: RECONNECT_STRATEGY.EXPONENTIAL,
  onMessage: (data) => console.log('收到消息:', data),
  onOpen: () => console.log('连接成功'),
  onReconnecting: (info) => console.log(`重连中: ${info.attempt}/${info.maxAttempts}`)
})

// 建立连接
connect()

// 发送消息
send({ type: 'ping' })

// 手动重连
manualReconnect()

// 断开连接
disconnect()
```

#### 主要功能

- ✅ 多种重连策略（线性/指数/斐波那契/固定）
- ✅ 消息队列（离线期间缓存消息）
- ✅ 心跳检测
- ✅ 连接状态管理
- ✅ 延迟统计
- ✅ 自动重连

#### 重连策略

```javascript
// 线性增长：delay = baseInterval * attempt
RECONNECT_STRATEGY.LINEAR

// 指数增长：delay = baseInterval * 2^(attempt-1)
RECONNECT_STRATEGY.EXPONENTIAL

// 斐波那契：delay = baseInterval * fibonacci(attempt)
RECONNECT_STRATEGY.FIBONACCI

// 固定间隔：delay = baseInterval
RECONNECT_STRATEGY.FIXED
```

#### API

**状态**

- `isConnected` - 是否已连接
- `isReconnecting` - 是否正在重连
- `retryCount` - 重连次数
- `connectionStatus` - 连接状态
- `messageQueue` - 消息队列
- `heartbeatStatus` - 心跳状态

**方法**

- `connect()` - 建立连接
- `disconnect()` - 断开连接
- `send(data)` - 发送消息
- `manualReconnect()` - 手动重连
- `resetRetryCount()` - 重置重连计数
- `clearMessageQueue()` - 清空消息队列

---

### 4. useErrorHandler - 错误处理（已完善）

提供统一的错误捕获、记录、分析和报告功能。

#### 基本用法

```javascript
import { useErrorHandler } from '@/composables'

const { handleError, currentError, clearError, copyErrorInfo } = useErrorHandler({
  enableHistory: true,
  onReport: (report) => sendToServer(report)
})

try {
  await riskyOperation()
} catch (error) {
  const errorInfo = handleError(error, {
    component: 'DataComponent',
    action: 'fetchData',
    userMessage: '数据加载失败，请稍后重试'
  })
  console.log('解决方案:', errorInfo.solution.title)
}
```

#### 主要功能

- ✅ 错误智能分类（网络/设备/权限/验证等）
- ✅ 自动匹配解决方案
- ✅ 错误历史记录
- ✅ 用户操作追踪
- ✅ 系统状态快照
- ✅ 错误报告生成
- ✅ 一键复制错误信息

---

## 完整集成示例

```vue
<template>
  <div class="data-collection">
    <!-- 网络状态提示 -->
    <el-alert
      v-if="isOffline"
      title="当前处于离线状态"
      type="warning"
      :closable="false"
    />

    <!-- 进度显示 -->
    <div v-if="isRunning" class="progress-section">
      <el-progress :percentage="progress" :status="progressStatus" />
      <p>{{ message }}</p>
      <p>已耗时: {{ formattedDuration }}</p>
      <p>预计剩余: {{ formattedEstimatedTime }}</p>
      <el-button @click="cancelOperation">取消</el-button>
    </div>

    <!-- 错误提示 -->
    <el-dialog v-model="errorVisible" title="错误">
      <error-display :error="currentError" />
      <template #footer>
        <el-button @click="copyError">复制错误信息</el-button>
        <el-button type="primary" @click="clearError">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 操作按钮 -->
    <el-button
      :disabled="isOffline || !isConnected"
      @click="startCollection"
    >
      开始采集
    </el-button>
  </div>
</template>

<script setup>
import { useErrorHandler, useProgress, useOnlineStatus, useWebSocketReconnect } from '@/composables'

// 初始化错误处理
const { handleError, currentError, errorVisible, clearError, copyErrorInfo } = useErrorHandler()

// 初始化进度管理
const {
  isRunning,
  progress,
  message,
  formattedDuration,
  formattedEstimatedTime,
  startOperation,
  updateProgress,
  completeOperation,
  cancelOperation
} = useProgress()

// 初始化网络状态
const { isOffline, networkQuality } = useOnlineStatus()

// 初始化WebSocket
const { isConnected, connect, send } = useWebSocketReconnect('ws://localhost:8000/ws', {
  onMessage: (data) => {
    if (data.type === 'progress') {
      updateProgress(data.progress, data.message)
    }
  }
})

// 开始采集
async function startCollection() {
  try {
    startOperation('数据采集', { total: 100 })
    send({ type: 'start_measurement' })
  } catch (error) {
    handleError(error, { component: 'DataCollection', action: 'startCollection' })
  }
}

// 复制错误
async function copyError() {
  await copyErrorInfo('detail')
}

// 计算进度状态
const progressStatus = computed(() => {
  if (progress.value === 100) return 'success'
  return ''
})

// 连接WebSocket
onMounted(() => {
  connect()
})
</script>
```

## 最佳实践

### 1. 错误处理

- ✅ 为每个操作提供清晰的上下文信息
- ✅ 使用用户友好的错误消息
- ✅ 记录关键操作以便错误追踪
- ✅ 定期清理错误历史

### 2. 进度管理

- ✅ 为长时间操作提供进度反馈
- ✅ 支持取消操作
- ✅ 提供预计剩余时间
- ✅ 使用子任务分解复杂操作

### 3. 离线状态

- ✅ 在发送请求前检查网络状态
- ✅ 根据网络质量调整应用行为
- ✅ 提供离线缓存和同步机制
- ✅ 显示网络质量提示

### 4. WebSocket

- ✅ 使用消息队列处理离线期间的消息
- ✅ 实现心跳机制保持连接活跃
- ✅ 提供手动重连选项
- ✅ 根据网络状态调整重连策略

## 文件结构

```
src/composables/
├── index.js                          # 统一导出
├── useErrorHandler.js                # 错误处理
├── useProgress.js                    # 进度管理
├── useOnlineStatus.js                # 在线状态检测
├── useWebSocketReconnect.js          # WebSocket自动重连
├── useWebSocket.js                   # WebSocket基础功能
├── useDeviceBase.js                  # 设备管理
├── useDataAnimation.js               # 数据动画
├── useDataAnomaly.js                 # 数据异常检测
├── useDataFreshness.js               # 数据新鲜度
├── useHistoryQuery.js                # 历史查询
├── useOperationHistory.js            # 操作历史
├── useKeyboardShortcuts.js           # 键盘快捷键
├── useOperationFeedback.js           # 操作反馈
├── useUserPreferences.js             # 用户偏好
├── usePushFrequency.js               # 推送频率控制
├── useWebSocketIntegration.js        # WebSocket集成
└── composables-usage-examples.js     # 使用示例
```

## 相关文档

- [Vue 3 Composition API](https://vuejs.org/guide/reusability/composables.html)
- [错误解决方案库](../utils/errorSolutions.js)
- [项目整体架构](../../docs/architecture.md)

---

**更新日期**: 2026-03-08  
**维护者**: Agent
