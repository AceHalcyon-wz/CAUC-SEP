/**
 * @file useWebSocketIntegration.js
 * @path src/composables/
 * @description WebSocket集成示例，展示如何在应用中集成WebSocket功能与状态栏显示
 * @author Agent
 * @date 2024-03-07
 * @dependencies vue, ./useWebSocket, @/stores/layout
 */

import { watch, onMounted, onUnmounted } from 'vue'
import { useWebSocket, ConnectionState } from './useWebSocket'
import { useLayoutStore } from '@/stores/layout'

/**
 * WebSocket集成组合式函数
 * 
 * @param {Object} options - 配置选项
 * @param {string} options.url - WebSocket服务器地址
 * @returns {Object} WebSocket实例和方法
 * 
 * @example
 * ```javascript
 * // 在App.vue或主布局组件中使用
 * import { useWebSocketIntegration } from '@/composables/useWebSocketIntegration'
 * 
 * const { connect, disconnect } = useWebSocketIntegration({
 *   url: 'ws://localhost:8000/ws'
 * })
 * 
 * onMounted(() => {
 *   connect()
 * })
 * ```
 */
export function useWebSocketIntegration(options = {}) {
  const { url } = options
  const layoutStore = useLayoutStore()

  /**
   * WebSocket实例
   */
  const {
    connectionState,
    wsConnected,
    wsConnecting,
    reconnectAttempts,
    maxReconnectReached,
    pushFrequency,
    dataLatency,
    connectionQuality,
    lastHeartbeatTime,
    lastPongTime,
    heartbeatTimeoutCount,
    messageQueue,
    queueLength,
    queueFull,
    currentProtocol,
    protocolSupported,
    connect,
    disconnect,
    send,
    manualReconnect,
    resetReconnect,
    flushMessageQueue,
    clearMessageQueue,
    getConnectionStats,
    checkHealth
  } = useWebSocket({
    url,
    
    /**
     * 消息接收处理
     */
    onMessage: (data) => {
      // 处理接收到的数据
      console.log('[WebSocket] Received:', data)
      
      // 根据消息类型分发处理
      if (data.type === 'data') {
        // 更新数据到相应的store
        // 例如：experimentStore.updateData(data.payload)
      }
    },
    
    /**
     * 连接成功处理
     */
    onOpen: () => {
      console.log('[WebSocket] Connected successfully')
      layoutStore.setConnectionStatus('connected')
      layoutStore.resetWsReconnectProgress()
      layoutStore.setWsMaxReconnectReached(false)
      layoutStore.setOperationTip('WebSocket已连接')
    },
    
    /**
     * 连接关闭处理
     */
    onClose: () => {
      console.log('[WebSocket] Connection closed')
      layoutStore.setConnectionStatus('disconnected')
      layoutStore.setOperationTip('WebSocket已断开')
    },
    
    /**
     * 错误处理
     */
    onError: (error) => {
      console.error('[WebSocket] Error:', error)
      layoutStore.addWarning('WebSocket连接错误', 'error')
    },
    
    /**
     * 重连进度回调
     */
    onReconnecting: (progress) => {
      console.log('[WebSocket] Reconnecting:', progress)
      layoutStore.setConnectionStatus('connecting')
      layoutStore.updateWsReconnectProgress(progress)
      layoutStore.setOperationTip(
        `正在重连 (${progress.attempt}/${progress.maxAttempts})...`
      )
    },
    
    /**
     * 连接状态变更回调
     */
    onStateChange: (state) => {
      console.log('[WebSocket] State changed:', state)
      
      // 根据状态更新UI
      switch (state) {
        case ConnectionState.CONNECTED:
          layoutStore.setConnectionStatus('connected')
          break
        case ConnectionState.CONNECTING:
          layoutStore.setConnectionStatus('connecting')
          break
        case ConnectionState.RECONNECTING:
          layoutStore.setConnectionStatus('connecting')
          break
        case ConnectionState.DISCONNECTED:
          layoutStore.setConnectionStatus('disconnected')
          break
      }
    },
    
    /**
     * 数据同步完成回调
     */
    onSyncComplete: (data) => {
      console.log('[WebSocket] Sync complete:', data)
      layoutStore.setOperationTip('数据同步完成')
    },
    
    // 重连配置
    reconnectInterval: 3000, // 初始重连间隔3秒
    maxReconnectAttempts: 5, // 最多重连5次
    maxBackoffDelay: 30000, // 最大退避延迟30秒
    heartbeatInterval: 30000, // 心跳间隔30秒
    heartbeatTimeout: 5000, // 心跳超时5秒
    messageQueueSize: 100, // 消息队列容量
    enableMessageQueue: true, // 启用消息队列
    enableAutoSync: true // 启用自动同步
  })

  // ==================== 监听状态变化并同步到Store ====================

  /**
   * 监听连接状态变化
   */
  watch(connectionState, (state) => {
    const statusMap = {
      [ConnectionState.CONNECTED]: 'connected',
      [ConnectionState.CONNECTING]: 'connecting',
      [ConnectionState.RECONNECTING]: 'connecting',
      [ConnectionState.DISCONNECTED]: 'disconnected'
    }
    layoutStore.setConnectionStatus(statusMap[state] || 'disconnected')
  })

  /**
   * 监听连接质量变化
   */
  watch(connectionQuality, (quality) => {
    // 可以在状态栏显示连接质量
    if (quality < 60) {
      layoutStore.addWarning(`连接质量较差: ${quality}分`, 'warning')
    }
  })

  /**
   * 监听推送频率变化
   */
  watch(pushFrequency, (frequency) => {
    layoutStore.updateWsPushFrequency(frequency)
  })

  /**
   * 监听数据延迟变化
   */
  watch(dataLatency, (latency) => {
    layoutStore.updateWsDataLatency(latency)
  })

  /**
   * 监听最大重连状态
   */
  watch(maxReconnectReached, (reached) => {
    layoutStore.setWsMaxReconnectReached(reached)
    if (reached) {
      layoutStore.addWarning(
        'WebSocket已达到最大重连次数，请手动重连',
        'error'
      )
    }
  })

  /**
   * 监听消息队列状态
   */
  watch(queueLength, (length) => {
    if (length > 50) {
      layoutStore.addWarning(`消息队列积压: ${length}条`, 'warning')
    }
  })

  // ==================== 监听手动重连事件 ====================

  /**
   * 手动重连事件处理器
   */
  function handleManualReconnect() {
    console.log('[WebSocket] Manual reconnect triggered')
    manualReconnect()
  }

  onMounted(() => {
    // 监听全局手动重连事件
    window.addEventListener('ws-manual-reconnect', handleManualReconnect)
  })

  onUnmounted(() => {
    // 清理事件监听器
    window.removeEventListener('ws-manual-reconnect', handleManualReconnect)
  })

  // ==================== 导出 ====================

  return {
    // === 连接状态 ===
    connectionState,
    wsConnected,
    wsConnecting,
    reconnectAttempts,
    maxReconnectReached,
    
    // === 性能指标 ===
    pushFrequency,
    dataLatency,
    connectionQuality,
    
    // === 心跳状态 ===
    lastHeartbeatTime,
    lastPongTime,
    heartbeatTimeoutCount,
    
    // === 消息队列 ===
    messageQueue,
    queueLength,
    queueFull,
    
    // === 协议信息 ===
    currentProtocol,
    protocolSupported,
    
    // === 方法 ===
    connect,
    disconnect,
    send,
    manualReconnect,
    resetReconnect,
    flushMessageQueue,
    clearMessageQueue,
    getConnectionStats,
    checkHealth
  }
}
