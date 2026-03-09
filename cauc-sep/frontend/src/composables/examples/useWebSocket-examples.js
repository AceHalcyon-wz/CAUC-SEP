/**
 * @file useWebSocket-examples.js
 * @path src/composables/examples/
 * @description WebSocket增强功能使用示例
 * @author Agent
 * @date 2026-03-08
 */

// ==================== 基础使用 ====================

import { watch } from 'vue'
import { useWebSocket, ConnectionState } from '@/composables/useWebSocket'

/**
 * 示例1: 基础连接管理
 */
export function basicUsage() {
  const {
    connectionState,
    wsConnected,
    connect,
    disconnect,
    send
  } = useWebSocket({
    url: 'ws://localhost:8000/ws',
    
    // 连接状态变更回调
    onStateChange: (state) => {
      console.log('连接状态:', state)
      switch (state) {
        case ConnectionState.CONNECTED:
          console.log('✓ 已连接')
          break
        case ConnectionState.CONNECTING:
          console.log('⏳ 正在连接...')
          break
        case ConnectionState.RECONNECTING:
          console.log('🔄 正在重连...')
          break
        case ConnectionState.DISCONNECTED:
          console.log('✗ 已断开')
          break
      }
    },
    
    // 消息接收回调
    onMessage: (data) => {
      console.log('收到消息:', data)
    },
    
    // 错误回调
    onError: (error) => {
      console.error('连接错误:', error)
    }
  })
  
  // 建立连接
  connect()
  
  // 发送消息
  send({ type: 'ping' })
  
  // 断开连接
  // disconnect()
  
  return { connectionState, wsConnected }
}

/**
 * 示例2: 增强的心跳检测
 */
export function enhancedHeartbeat() {
  const {
    connectionState,
    lastHeartbeatTime,
    lastPongTime,
    heartbeatTimeoutCount,
    connectionQuality,
    connect
  } = useWebSocket({
    url: 'ws://localhost:8000/ws',
    
    // 心跳配置
    heartbeatInterval: 30000,  // 每30秒发送一次心跳
    heartbeatTimeout: 5000,    // 5秒内未收到响应视为超时
    
    // 心跳超时时的处理
    onStateChange: (state) => {
      if (heartbeatTimeoutCount.value >= 3) {
        console.warn('心跳连续超时3次，连接可能不稳定')
      }
    }
  })
  
  connect()
  
  // 监控连接质量
  setInterval(() => {
    console.log('连接质量评分:', connectionQuality.value)
    console.log('心跳超时次数:', heartbeatTimeoutCount.value)
    
    if (lastHeartbeatTime.value && lastPongTime.value) {
      const latency = lastPongTime.value - lastHeartbeatTime.value
      console.log('心跳延迟:', latency, 'ms')
    }
  }, 5000)
}

/**
 * 示例3: 消息队列缓存
 */
export function messageQueueUsage() {
  const {
    connectionState,
    messageQueue,
    queueLength,
    queueFull,
    send,
    flushMessageQueue,
    clearMessageQueue,
    connect
  } = useWebSocket({
    url: 'ws://localhost:8000/ws',
    
    // 启用消息队列
    enableMessageQueue: true,
    messageQueueSize: 100,  // 最多缓存100条消息
    
    onMessage: (data) => {
      console.log('收到消息:', data)
    }
  })
  
  // 即使未连接，消息也会被缓存
  send({ type: 'command', action: 'start' })
  send({ type: 'command', action: 'stop' })
  
  console.log('队列中的消息数:', queueLength.value)
  console.log('队列是否已满:', queueFull.value)
  
  // 连接后，队列中的消息会自动发送
  connect()
  
  // 手动清空队列
  // clearMessageQueue()
  
  // 手动刷新队列（发送所有缓存消息）
  // flushMessageQueue()
}

/**
 * 示例4: 自动数据同步
 */
export function autoSyncUsage() {
  const {
    connectionState,
    lastMessageTime,
    connect
  } = useWebSocket({
    url: 'ws://localhost:8000/ws',
    
    // 启用自动同步
    enableAutoSync: true,
    
    // 数据同步完成回调
    onSyncComplete: (data) => {
      console.log('数据同步完成:', data)
      console.log('同步的消息数:', data.message_count)
      console.log('同步的时间范围:', data.time_range)
    },
    
    onMessage: (data) => {
      // 处理接收到的数据
      console.log('收到数据:', data)
    }
  })
  
  connect()
  
  // 重连时会自动请求同步断线期间的数据
  // 服务器会根据 lastMessageTime 发送缺失的数据
}

/**
 * 示例5: 连接健康检查
 */
export function healthCheckUsage() {
  const {
    connectionState,
    connectionQuality,
    checkHealth,
    getConnectionStats,
    connect
  } = useWebSocket({
    url: 'ws://localhost:8000/ws',
    
    onStateChange: (state) => {
      if (state === ConnectionState.CONNECTED) {
        // 连接成功后定期检查健康状态
        setInterval(() => {
          const health = checkHealth()
          
          console.log('=== 连接健康报告 ===')
          console.log('健康状态:', health.healthy ? '✓ 健康' : '✗ 异常')
          console.log('质量评分:', health.score)
          
          if (health.issues.length > 0) {
            console.log('发现的问题:')
            health.issues.forEach(issue => {
              console.log(`  [${issue.level}] ${issue.message}`)
              console.log(`  建议: ${issue.suggestion}`)
            })
          }
          
          // 获取详细统计信息
          const stats = getConnectionStats()
          console.log('详细统计:', stats)
        }, 10000)
      }
    }
  })
  
  connect()
}

/**
 * 示例6: 指数退避重连策略
 */
export function reconnectStrategy() {
  const {
    connectionState,
    reconnectAttempts,
    maxReconnectReached,
    manualReconnect,
    resetReconnect,
    connect
  } = useWebSocket({
    url: 'ws://localhost:8000/ws',
    
    // 重连配置
    reconnectInterval: 1000,      // 初始重连间隔1秒
    maxReconnectAttempts: 5,      // 最多重连5次
    maxBackoffDelay: 30000,       // 最大退避延迟30秒
    
    // 重连进度回调
    onReconnecting: (progress) => {
      console.log(`正在重连 (${progress.attempt}/${progress.maxAttempts})`)
      console.log(`下次重连时间: ${progress.delay}ms 后`)
      console.log(`预计重连时刻: ${new Date(progress.nextRetryAt).toLocaleTimeString()}`)
    },
    
    // 达到最大重连次数
    onStateChange: (state) => {
      if (maxReconnectReached.value) {
        console.error('已达到最大重连次数，请手动重连')
        // 可以在UI上显示重连按钮
      }
    }
  })
  
  connect()
  
  // 手动重连（重置重连计数器）
  function handleManualReconnect() {
    manualReconnect()
  }
  
  // 重置重连状态（不清除连接）
  function handleResetReconnect() {
    resetReconnect()
  }
  
  return { handleManualReconnect, handleResetReconnect }
}

/**
 * 示例7: 完整的生产环境配置
 */
export function productionConfig() {
  const {
    connectionState,
    connectionQuality,
    messageQueue,
    queueLength,
    checkHealth,
    getConnectionStats,
    connect,
    disconnect,
    send,
    manualReconnect,
    flushMessageQueue
  } = useWebSocket({
    url: import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws',
    
    // === 连接配置 ===
    reconnectInterval: 2000,
    maxReconnectAttempts: 10,
    maxBackoffDelay: 60000,
    
    // === 心跳配置 ===
    heartbeatInterval: 25000,
    heartbeatTimeout: 5000,
    
    // === 消息队列配置 ===
    enableMessageQueue: true,
    messageQueueSize: 200,
    
    // === 数据同步配置 ===
    enableAutoSync: true,
    
    // === 协议配置 ===
    preferredProtocol: 'msgpack',
    enableProtocolFallback: true,
    
    // === 回调函数 ===
    onStateChange: (state) => {
      // 更新UI状态
      updateConnectionUI(state)
      
      // 记录日志
      logConnectionState(state)
    },
    
    onMessage: (data) => {
      // 处理业务数据
      handleBusinessData(data)
    },
    
    onError: (error) => {
      // 错误上报
      reportError(error)
    },
    
    onReconnecting: (progress) => {
      // 显示重连进度
      showReconnectProgress(progress)
    },
    
    onSyncComplete: (data) => {
      // 同步完成通知
      notifySyncComplete(data)
    }
  })
  
  // 启动连接
  connect()
  
  // 定期健康检查
  setInterval(() => {
    const health = checkHealth()
    if (!health.healthy) {
      console.warn('连接健康检查失败:', health.issues)
      
      // 如果连接质量过低，考虑重连
      if (health.score < 40) {
        console.log('连接质量过低，尝试重连...')
        manualReconnect()
      }
    }
  }, 30000)
  
  // 监控消息队列
  watch(queueLength, (length) => {
    if (length > 100) {
      console.warn('消息队列积压:', length)
      // 可以考虑增加处理频率或优化后端
    }
  })
  
  return {
    connectionState,
    connectionQuality,
    connect,
    disconnect,
    send,
    manualReconnect,
    flushMessageQueue,
    checkHealth,
    getConnectionStats
  }
}

// ==================== 辅助函数 ====================

function updateConnectionUI(state) {
  // 更新UI显示连接状态
}

function logConnectionState(state) {
  // 记录连接状态日志
}

function handleBusinessData(data) {
  // 处理业务数据
}

function reportError(error) {
  // 错误上报
}

function showReconnectProgress(progress) {
  // 显示重连进度
}

function notifySyncComplete(data) {
  // 同步完成通知
}
