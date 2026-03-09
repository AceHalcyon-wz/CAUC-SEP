# WebSocket连接状态可视化功能使用指南

## 功能概述

本次更新实现了完整的WebSocket连接状态可视化功能，包括：

1. **连接状态指示器** - 实时显示WebSocket连接状态
2. **自动断线重连** - 智能重连机制，支持指数退避
3. **推送频率监控** - 实时显示数据推送频率
4. **数据延迟统计** - 显示数据从产生到显示的时间差
5. **手动重连按钮** - 允许用户手动触发重连

## 文件结构

```
src/
├── composables/
│   ├── useWebSocket.js              # WebSocket核心功能（已增强）
│   └── useWebSocketIntegration.js   # WebSocket集成示例（新增）
├── stores/
│   └── layout.js                    # 布局状态管理（已更新）
├── components/
│   └── layout/
│       └── StatusBar.vue            # 状态栏组件（已更新）
└── App.vue                          # 主应用组件（已更新）
```

## 核心功能说明

### 1. WebSocket连接状态指示器

状态栏左侧显示连接状态，包含三种状态：

- **已连接**：绿色圆点 + "已连接" 文字
- **连接中**：黄色闪烁圆点 + "连接中..." 文字
- **已断开**：红色圆点 + "未连接" 文字

### 2. 自动断线重连

**特性：**
- 最大重连次数：3次（可配置）
- 重连间隔：指数退避算法（3秒 → 6秒 → 12秒）
- 重连进度显示：显示当前重连次数和总次数

**重连流程：**
```
断开 → 等待3秒 → 第1次重连
     ↓ 失败
     等待6秒 → 第2次重连
     ↓ 失败
     等待12秒 → 第3次重连
     ↓ 失败
     显示手动重连按钮
```

### 3. 推送频率和延迟监控

**推送频率：**
- 实时计算每秒接收的消息数量
- 显示格式：`频率: X 条/s`

**数据延迟：**
- 计算消息时间戳与接收时间的差值
- 显示格式：`延迟: X ms`
- 颜色编码：
  - 绿色：< 100ms（优秀）
  - 黄色：100-300ms（正常）
  - 红色：> 300ms（较差）

### 4. 手动重连按钮

当连接断开或达到最大重连次数时，状态栏显示"重连"按钮，用户可手动触发重连。

## 使用方法

### 基础集成（推荐）

在 `App.vue` 或主布局组件中：

```vue
<script setup>
import { useWebSocketIntegration } from '@/composables/useWebSocketIntegration'

// WebSocket配置
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'

// 初始化WebSocket连接
const { connect, disconnect, send } = useWebSocketIntegration({
  url: WS_URL
})

// 组件挂载时连接
onMounted(() => {
  connect()
})

// 组件卸载时断开
onUnmounted(() => {
  disconnect()
})
</script>
```

### 自定义配置

```javascript
const { connect, disconnect } = useWebSocketIntegration({
  url: 'ws://your-server:port/ws',
  reconnectInterval: 5000,      // 初始重连间隔（毫秒）
  maxReconnectAttempts: 5,      // 最大重连次数
  heartbeatInterval: 30000      // 心跳间隔（毫秒）
})
```

### 直接使用useWebSocket

如果需要更细粒度的控制：

```javascript
import { useWebSocket } from '@/composables/useWebSocket'

const {
  wsConnected,           // 连接状态
  wsConnecting,          // 连接中状态
  reconnectAttempts,     // 当前重连次数
  maxReconnectReached,   // 是否达到最大重连次数
  pushFrequency,         // 推送频率
  dataLatency,           // 数据延迟
  connect,
  disconnect,
  send,
  manualReconnect,       // 手动重连
  resetReconnect         // 重置重连状态
} = useWebSocket({
  url: 'ws://localhost:8000/ws',
  onMessage: (data) => {
    // 处理接收到的消息
    console.log('收到消息:', data)
  },
  onOpen: () => {
    console.log('连接成功')
  },
  onClose: () => {
    console.log('连接关闭')
  },
  onError: (error) => {
    console.error('连接错误:', error)
  },
  onReconnecting: (progress) => {
    console.log(`重连中: ${progress.attempt}/${progress.maxAttempts}`)
  }
})
```

## 环境变量配置

在项目根目录创建 `.env` 文件：

```env
# WebSocket服务器地址
VITE_WS_URL=ws://localhost:8000/ws
```

## 消息格式要求

为了正确计算数据延迟，WebSocket消息应包含时间戳：

```json
{
  "type": "data",
  "timestamp": 1709827200000,
  "payload": {
    "temperature": 25.5,
    "humidity": 60
  }
}
```

## 状态栏API

### Store方法

```javascript
import { useLayoutStore } from '@/stores/layout'

const layoutStore = useLayoutStore()

// 更新连接状态
layoutStore.setConnectionStatus('connected') // 'disconnected' | 'connecting' | 'connected'

// 更新重连进度
layoutStore.updateWsReconnectProgress({
  attempt: 2,
  maxAttempts: 3,
  delay: 6000
})

// 重置重连进度
layoutStore.resetWsReconnectProgress()

// 更新推送频率
layoutStore.updateWsPushFrequency(15)

// 更新数据延迟
layoutStore.updateWsDataLatency(120)

// 设置最大重连状态
layoutStore.setWsMaxReconnectReached(true)
```

## 故障排查

### 1. 连接一直显示"连接中"

**可能原因：**
- WebSocket服务器未启动
- 网络连接问题
- 防火墙阻止连接

**解决方法：**
```javascript
// 检查WebSocket URL是否正确
console.log('WebSocket URL:', import.meta.env.VITE_WS_URL)

// 查看浏览器控制台的WebSocket错误
```

### 2. 重连失败

**可能原因：**
- 服务器持续不可用
- 达到最大重连次数

**解决方法：**
- 点击状态栏的"重连"按钮手动重连
- 检查服务器状态
- 查看控制台日志

### 3. 延迟显示为0

**可能原因：**
- 消息中未包含 `timestamp` 字段

**解决方法：**
确保服务器发送的消息包含时间戳：
```json
{
  "timestamp": Date.now(),
  "data": "..."
}
```

## 最佳实践

1. **环境变量管理**
   - 使用 `.env` 文件配置WebSocket URL
   - 不同环境使用不同的配置文件（`.env.development`, `.env.production`）

2. **错误处理**
   - 监听 `onError` 回调
   - 使用 `layoutStore.addWarning()` 显示错误提示

3. **性能优化**
   - 合理设置心跳间隔（默认30秒）
   - 避免频繁发送大消息

4. **用户体验**
   - 在关键操作前检查连接状态
   - 提供清晰的状态反馈

## 示例项目

完整示例请参考：
- [App.vue](file:///c:\Users\15272\Downloads\kimiOKC\cauc-sep\frontend\src\App.vue) - 主应用集成
- [StatusBar.vue](file:///c:\Users\15272\Downloads\kimiOKC\cauc-sep\frontend\src\components\layout\StatusBar.vue) - 状态栏组件
- [useWebSocketIntegration.js](file:///c:\Users\15272\Downloads\kimiOKC\cauc-sep\frontend\src\composables\useWebSocketIntegration.js) - 集成示例

## 技术细节

### 指数退避算法

重连间隔计算公式：
```
delay = baseInterval * 2^(attempt - 1)
```

示例：
- 第1次：3000ms * 2^0 = 3000ms
- 第2次：3000ms * 2^1 = 6000ms
- 第3次：3000ms * 2^2 = 12000ms

### 频率统计

每秒统计一次接收的消息数量：
```javascript
setInterval(() => {
  pushFrequency.value = messageCount
  messageCount = 0
}, 1000)
```

### 延迟计算

```javascript
// 客户端接收时间 - 服务器发送时间
dataLatency = Date.now() - message.timestamp
```

## 更新日志

### v1.1.0 (2026-03-08)
- 📝 更新文档日期和版本信息
- 🔧 优化WebSocket连接稳定性

### v1.0.0 (2024-03-07)

**新增功能：**
- WebSocket连接状态可视化
- 自动断线重连（指数退避）
- 推送频率监控
- 数据延迟统计
- 手动重连按钮
- 重连进度显示

**改进：**
- 增强useWebSocket组合式函数
- 优化状态栏UI布局
- 完善错误处理机制

**技术栈：**
- Vue 3 Composition API
- Pinia状态管理
- Element Plus UI组件
- 原生WebSocket API

---

**更新日期**: 2026-03-08  
**维护者**: Agent
