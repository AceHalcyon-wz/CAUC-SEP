# WebSocket 组合式函数使用指南

**文件路径**: `frontend/src/composables/useWebSocket.js`  
**版本**: v1.0  
**更新日期**: 2026-03-08

---

## 概述

`useWebSocket` 是一个功能完整的 WebSocket 组合式函数，提供：

- 自动连接管理与重连机制
- 心跳检测保持连接活跃
- 消息队列与离线缓存
- 连接状态监控
- 订阅/取消订阅管理
- 类型安全的消息处理

---

## 快速开始

### 基本使用

```vue
<script setup>
import { useWebSocket } from '@/composables/useWebSocket'

// 创建WebSocket连接
const { 
  isConnected, 
  sendMessage, 
  subscribe, 
  disconnect 
} = useWebSocket('ws://localhost:8000/ws')

// 订阅消息
const unsubscribe = subscribe('device_status', (data) => {
  console.log('设备状态更新:', data)
})

// 发送消息
sendMessage({
  type: 'command',
  action: 'start',
  device_id: 'stepper_01'
})

// 组件卸载时自动断开连接
onUnmounted(() => {
  unsubscribe()
})
</script>

<template>
  <div>
    <span>连接状态: {{ isConnected ? '已连接' : '已断开' }}</span>
  </div>
</template>
```

---

## API 参考

### 配置选项

```typescript
interface WebSocketOptions {
  // 是否自动连接，默认true
  autoConnect?: boolean
  
  // 重连配置
  reconnect?: {
    enabled: boolean      // 是否启用重连，默认true
    maxAttempts: number   // 最大重试次数，默认5
    delay: number         // 初始重连延迟(ms)，默认1000
    maxDelay: number      // 最大重连延迟(ms)，默认30000
    backoffMultiplier: number  // 退避乘数，默认2
  }
  
  // 心跳配置
  heartbeat?: {
    enabled: boolean      // 是否启用心跳，默认true
    interval: number      // 心跳间隔(ms)，默认30000
    timeout: number       // 心跳超时(ms)，默认5000
  }
  
  // 消息队列配置
  messageQueue?: {
    enabled: boolean      // 是否启用消息队列，默认true
    maxSize: number       // 队列最大长度，默认100
    persistOffline: boolean  // 是否持久化离线消息，默认true
  }
  
  // 连接超时(ms)，默认10000
  connectionTimeout?: number
  
  // 调试模式，默认false
  debug?: boolean
}
```

### 返回值

```typescript
interface WebSocketReturn {
  // 状态
  isConnected: Ref<boolean>           // 是否已连接
  isConnecting: Ref<boolean>          // 是否正在连接
  connectionState: Ref<string>        // 连接状态字符串
  reconnectAttempts: Ref<number>      // 当前重连次数
  lastMessage: Ref<object | null>     // 最后收到的消息
  messageQueue: Ref<Array>            // 待发送消息队列
  
  // 方法
  connect: () => void                 // 建立连接
  disconnect: () => void              // 断开连接
  reconnect: () => void               // 重新连接
  sendMessage: (data: any) => boolean // 发送消息
  subscribe: (type: string, callback: Function) => Function  // 订阅消息
  unsubscribe: (type: string) => void // 取消订阅
  clearQueue: () => void              // 清空消息队列
  
  // 统计
  stats: ComputedRef<{
    messagesSent: number
    messagesReceived: number
    reconnectCount: number
    uptime: number
  }>
}
```

---

## 使用示例

### 1. 设备状态监控

```vue
<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'

// 设备状态数据
const devices = ref({})

// 创建WebSocket连接
const { 
  isConnected, 
  subscribe, 
  sendMessage 
} = useWebSocket('ws://localhost:8000/ws/devices', {
  heartbeat: {
    enabled: true,
    interval: 15000
  }
})

// 订阅设备状态更新
const unsubscribeDeviceStatus = subscribe('device_status', (data) => {
  // 更新设备状态
  devices.value[data.device_id] = {
    ...devices.value[data.device_id],
    ...data
  }
})

// 订阅设备连接事件
const unsubscribeDeviceConnect = subscribe('device_connected', (data) => {
  console.log(`设备 ${data.device_id} 已连接`)
  devices.value[data.device_id] = {
    ...devices.value[data.device_id],
    connected: true
  }
})

// 订阅设备断开事件
const unsubscribeDeviceDisconnect = subscribe('device_disconnected', (data) => {
  console.log(`设备 ${data.device_id} 已断开`)
  devices.value[data.device_id] = {
    ...devices.value[data.device_id],
    connected: false
  }
})

// 发送命令
function sendCommand(deviceId, command) {
  sendMessage({
    type: 'device_command',
    device_id: deviceId,
    command: command
  })
}

// 清理订阅
onUnmounted(() => {
  unsubscribeDeviceStatus()
  unsubscribeDeviceConnect()
  unsubscribeDeviceDisconnect()
})
</script>

<template>
  <div class="device-monitor">
    <div class="connection-status">
      <span :class="{ connected: isConnected, disconnected: !isConnected }">
        {{ isConnected ? '已连接' : '已断开' }}
      </span>
    </div>
    
    <div v-for="(device, id) in devices" :key="id" class="device-card">
      <h3>{{ device.name || id }}</h3>
      <p>状态: {{ device.status }}</p>
      <button @click="sendCommand(id, 'start')">启动</button>
      <button @click="sendCommand(id, 'stop')">停止</button>
    </div>
  </div>
</template>
```

### 2. 实时数据流处理

```vue
<script setup>
import { ref, computed } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'

// 数据缓冲区
const dataBuffer = ref([])
const MAX_BUFFER_SIZE = 100

// 创建WebSocket连接
const { 
  isConnected, 
  subscribe, 
  stats 
} = useWebSocket('ws://localhost:8000/ws/stream', {
  messageQueue: {
    enabled: true,
    maxSize: 50
  }
})

// 订阅数据流
subscribe('data_point', (data) => {
  // 添加到缓冲区
  dataBuffer.value.push(data)
  
  // 限制缓冲区大小
  if (dataBuffer.value.length > MAX_BUFFER_SIZE) {
    dataBuffer.value.shift()
  }
})

// 计算统计信息
const statistics = computed(() => {
  if (dataBuffer.value.length === 0) return null
  
  const values = dataBuffer.value.map(d => d.value)
  return {
    min: Math.min(...values),
    max: Math.max(...values),
    avg: values.reduce((a, b) => a + b, 0) / values.length,
    count: values.length
  }
})

// 连接统计
const connectionStats = computed(() => stats.value)
</script>

<template>
  <div class="data-stream">
    <div class="stats">
      <p>已接收: {{ connectionStats.messagesReceived }} 条消息</p>
      <p>缓冲区: {{ dataBuffer.length }} / {{ MAX_BUFFER_SIZE }}</p>
    </div>
    
    <div v-if="statistics" class="statistics">
      <p>最小值: {{ statistics.min.toFixed(2) }}</p>
      <p>最大值: {{ statistics.max.toFixed(2) }}</p>
      <p>平均值: {{ statistics.avg.toFixed(2) }}</p>
    </div>
  </div>
</template>
```

### 3. 告警通知系统

```vue
<script setup>
import { ref } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'
import { useNotification } from '@/composables/useNotification'

const notifications = useNotification()
const alerts = ref([])

// 创建WebSocket连接
const { isConnected, subscribe } = useWebSocket('ws://localhost:8000/ws/alerts', {
  reconnect: {
    enabled: true,
    maxAttempts: 10
  }
})

// 订阅告警创建
subscribe('alert_created', (alert) => {
  // 添加到告警列表
  alerts.value.unshift(alert)
  
  // 显示通知
  notifications.show({
    type: alert.level,
    title: alert.title,
    message: alert.message,
    duration: alert.level === 'critical' ? 0 : 5000
  })
})

// 订阅告警更新
subscribe('alert_updated', (alert) => {
  const index = alerts.value.findIndex(a => a.id === alert.id)
  if (index !== -1) {
    alerts.value[index] = alert
  }
})

// 订阅告警解决
subscribe('alert_resolved', (alert) => {
  const index = alerts.value.findIndex(a => a.id === alert.id)
  if (index !== -1) {
    alerts.value[index].status = 'resolved'
  }
})
</script>

<template>
  <div class="alert-panel">
    <h2>告警通知</h2>
    <div class="connection">
      <span :class="isConnected ? 'online' : 'offline'">
        {{ isConnected ? '在线' : '离线' }}
      </span>
    </div>
    
    <div class="alert-list">
      <div 
        v-for="alert in alerts" 
        :key="alert.id"
        :class="['alert-item', alert.level]"
      >
        <span class="title">{{ alert.title }}</span>
        <span class="message">{{ alert.message }}</span>
        <span class="time">{{ formatTime(alert.created_at) }}</span>
      </div>
    </div>
  </div>
</template>
```

### 4. 多连接管理

```javascript
// composables/useMultiWebSocket.js
import { ref, computed } from 'vue'
import { useWebSocket } from './useWebSocket'

/**
 * 多WebSocket连接管理器
 */
export function useMultiWebSocket(connections) {
  const instances = ref({})
  const connectionStates = ref({})

  // 创建多个连接
  connections.forEach(({ name, url, options }) => {
    const instance = useWebSocket(url, options)
    instances.value[name] = instance
    connectionStates.value[name] = instance.isConnected
  })

  // 所有连接状态
  const allConnected = computed(() => {
    return Object.values(connectionStates.value).every(state => state)
  })

  // 任一连接状态
  const anyConnected = computed(() => {
    return Object.values(connectionStates.value).some(state => state)
  })

  /**
   * 向指定连接发送消息
   */
  function sendTo(connectionName, data) {
    const instance = instances.value[connectionName]
    if (instance && instance.isConnected.value) {
      return instance.sendMessage(data)
    }
    return false
  }

  /**
   * 向所有连接广播消息
   */
  function broadcast(data) {
    Object.values(instances.value).forEach(instance => {
      if (instance.isConnected.value) {
        instance.sendMessage(data)
      }
    })
  }

  /**
   * 断开所有连接
   */
  function disconnectAll() {
    Object.values(instances.value).forEach(instance => {
      instance.disconnect()
    })
  }

  return {
    instances,
    connectionStates,
    allConnected,
    anyConnected,
    sendTo,
    broadcast,
    disconnectAll
  }
}

// 使用示例
const { instances, allConnected, sendTo } = useMultiWebSocket([
  { name: 'devices', url: 'ws://localhost:8000/ws/devices' },
  { name: 'alerts', url: 'ws://localhost:8000/ws/alerts' },
  { name: 'metrics', url: 'ws://localhost:8000/ws/metrics' }
])

// 发送消息到特定连接
sendTo('devices', { type: 'command', action: 'start' })

// 检查所有连接状态
console.log('所有连接就绪:', allConnected.value)
```

---

## 高级功能

### 消息过滤器

```javascript
// 创建带过滤器的WebSocket连接
const { subscribe } = useWebSocket('ws://localhost:8000/ws')

// 只处理特定设备的消息
const deviceFilter = (deviceId) => (data) => {
  return data.device_id === deviceId
}

// 使用过滤器订阅
subscribe('device_status', (data) => {
  console.log('设备状态:', data)
}, { filter: deviceFilter('stepper_01') })
```

### 消息转换器

```javascript
// 消息转换器
const messageTransformer = {
  // 发送前转换
  outgoing: (data) => ({
    ...data,
    timestamp: Date.now(),
    client_id: getClientId()
  }),
  
  // 接收后转换
  incoming: (data) => {
    // 解析JSON字符串
    if (typeof data === 'string') {
      return JSON.parse(data)
    }
    return data
  }
}

const { sendMessage, subscribe } = useWebSocket('ws://localhost:8000/ws', {
  transformer: messageTransformer
})
```

### 离线消息处理

```javascript
const { 
  isConnected, 
  sendMessage, 
  messageQueue,
  clearQueue 
} = useWebSocket('ws://localhost:8000/ws', {
  messageQueue: {
    enabled: true,
    maxSize: 100,
    persistOffline: true  // 离线时持久化到localStorage
  }
})

// 离线时发送的消息会进入队列
function sendCommand(command) {
  if (!isConnected.value) {
    console.log('当前离线，消息已加入队列')
  }
  sendMessage({ type: 'command', ...command })
}

// 查看待发送消息
console.log('待发送消息:', messageQueue.value.length)

// 清空队列
clearQueue()
```

---

## 错误处理

### 连接错误

```javascript
const { 
  isConnected, 
  connectionState,
  reconnectAttempts 
} = useWebSocket('ws://localhost:8000/ws', {
  reconnect: {
    enabled: true,
    maxAttempts: 5
  }
})

// 监听连接状态变化
watch(connectionState, (state) => {
  switch (state) {
    case 'connecting':
      console.log('正在连接...')
      break
    case 'connected':
      console.log('连接成功')
      break
    case 'disconnected':
      console.log('连接断开')
      break
    case 'error':
      console.error('连接错误')
      break
    case 'reconnecting':
      console.log(`正在重连 (${reconnectAttempts.value}次)`)
      break
  }
})
```

### 消息处理错误

```javascript
const { subscribe } = useWebSocket('ws://localhost:8000/ws')

// 带错误处理的订阅
subscribe('data', (data) => {
  try {
    // 处理数据
    processData(data)
  } catch (error) {
    console.error('消息处理错误:', error)
    // 可以选择上报错误
    reportError(error, { context: 'websocket_message', data })
  }
})
```

---

## 性能优化

### 消息节流

```javascript
import { throttle } from 'lodash-es'

const { subscribe } = useWebSocket('ws://localhost:8000/ws')

// 节流处理高频消息
const throttledHandler = throttle((data) => {
  updateUI(data)
}, 100) // 每100ms最多处理一次

subscribe('high_frequency_data', throttledHandler)
```

### 按需订阅

```javascript
// 只在组件可见时订阅
import { usePageVisibility } from '@/composables/usePageVisibility'

const { isVisible } = usePageVisibility()
let unsubscribe = null

watch(isVisible, (visible) => {
  if (visible && !unsubscribe) {
    unsubscribe = subscribe('updates', handleUpdate)
  } else if (!visible && unsubscribe) {
    unsubscribe()
    unsubscribe = null
  }
}, { immediate: true })
```

---

## 调试

### 启用调试模式

```javascript
const { subscribe } = useWebSocket('ws://localhost:8000/ws', {
  debug: true
})

// 控制台会输出:
// [WebSocket] Connecting to ws://localhost:8000/ws
// [WebSocket] Connected
// [WebSocket] <- Received: {"type":"data",...}
// [WebSocket] -> Sending: {"type":"command",...}
```

### 查看统计信息

```javascript
const { stats } = useWebSocket('ws://localhost:8000/ws')

// 定期打印统计
setInterval(() => {
  console.log('WebSocket统计:', {
    发送消息数: stats.value.messagesSent,
    接收消息数: stats.value.messagesReceived,
    重连次数: stats.value.reconnectCount,
    连接时长: stats.value.uptime
  })
}, 60000)
```

---

## 相关文档

- [错误处理组合式函数使用指南](./error-handler-composable.md)
- [健康监控API文档](../api/health-api.md)
- [告警系统API文档](../api/alerts-api.md)
