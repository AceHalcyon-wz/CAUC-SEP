/**
 * @file useWebSocketReconnect.js
 * @path src/composables/
 * @description WebSocket自动重连组合式函数，提供智能重连策略、连接状态管理、消息队列等功能
 * @author Agent
 * @date 2024-03-07
 * @dependencies vue
 */

import { ref, computed, onUnmounted, readonly } from 'vue'

/**
 * 重连策略枚举
 */
export const RECONNECT_STRATEGY = {
  LINEAR: 'linear',
  EXPONENTIAL: 'exponential',
  FIBONACCI: 'fibonacci',
  FIXED: 'fixed'
}

/**
 * 连接状态枚举
 */
export const CONNECTION_STATUS = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  RECONNECTING: 'reconnecting',
  FAILED: 'failed'
}

/**
 * WebSocket自动重连组合式函数
 *
 * @param {string} url - WebSocket服务器地址
 * @param {Object} options - 配置选项
 * @param {number} [options.maxRetries=10] - 最大重连次数
 * @param {number} [options.retryInterval=1000] - 初始重连间隔（毫秒）
 * @param {number} [options.maxRetryInterval=30000] - 最大重连间隔（毫秒）
 * @param {string} [options.strategy=RECONNECT_STRATEGY.EXPONENTIAL] - 重连策略
 * @param {number} [options.heartbeatInterval=30000] - 心跳间隔（毫秒）
 * @param {number} [options.heartbeatTimeout=5000] - 心跳超时时间（毫秒）
 * @param {boolean} [options.enableMessageQueue=true] - 是否启用消息队列
 * @param {number} [options.maxQueueSize=100] - 最大消息队列大小
 * @param {Function} [options.onMessage] - 消息接收回调
 * @param {Function} [options.onOpen] - 连接成功回调
 * @param {Function} [options.onClose] - 连接关闭回调
 * @param {Function} [options.onError] - 错误回调
 * @param {Function} [options.onReconnecting] - 重连进度回调
 * @param {Function} [options.onMaxRetriesReached] - 达到最大重连次数回调
 * @returns {Object} WebSocket状态与操作方法
 *
 * @example
 * ```javascript
 * const { connect, disconnect, send, isConnected } = useWebSocketReconnect(
 *   'ws://localhost:8000/ws',
 *   {
 *     maxRetries: 5,
 *     strategy: RECONNECT_STRATEGY.EXPONENTIAL,
 *     onMessage: (data) => console.log('收到消息:', data),
 *     onReconnecting: (info) => console.log(`重连中: ${info.attempt}/${info.maxAttempts}`)
 *   }
 * )
 *
 * // 建立连接
 * connect()
 *
 * // 发送消息
 * send({ type: 'ping' })
 *
 * // 断开连接
 * disconnect()
 * ```
 */
export function useWebSocketReconnect(url, options = {}) {
  const {
    maxRetries = 10,
    retryInterval = 1000,
    maxRetryInterval = 30000,
    strategy = RECONNECT_STRATEGY.EXPONENTIAL,
    heartbeatInterval = 30000,
    heartbeatTimeout = 5000,
    enableMessageQueue = true,
    maxQueueSize = 100,
    onMessage,
    onOpen,
    onClose,
    onError,
    onReconnecting,
    onMaxRetriesReached
  } = options

  // === 响应式状态 ===
  /** WebSocket实例 */
  const ws = ref(null)
  /** 连接状态 */
  const connectionStatus = ref(CONNECTION_STATUS.DISCONNECTED)
  /** 是否已连接 */
  const isConnected = computed(() => connectionStatus.value === CONNECTION_STATUS.CONNECTED)
  /** 是否正在连接 */
  const isConnecting = computed(() => connectionStatus.value === CONNECTION_STATUS.CONNECTING)
  /** 是否正在重连 */
  const isReconnecting = computed(() => connectionStatus.value === CONNECTION_STATUS.RECONNECTING)
  /** 重连次数 */
  const retryCount = ref(0)
  /** 下次重连等待时间 */
  const nextRetryDelay = ref(0)
  /** 消息队列 */
  const messageQueue = ref([])
  /** 最后接收消息时间 */
  const lastMessageTime = ref(null)
  /** 最后发送消息时间 */
  const lastSendTime = ref(null)
  /** 连接建立时间 */
  const connectedTime = ref(null)
  /** 消息统计 */
  const messageStats = ref({
    sent: 0,
    received: 0,
    queued: 0
  })
  /** 心跳状态 */
  const heartbeatStatus = ref({
    lastPingTime: null,
    lastPongTime: null,
    latency: 0
  })

  // === 内部变量 ===
  let reconnectTimer = null
  let heartbeatTimer = null
  let heartbeatTimeoutTimer = null
  let fibonacciSequence = [1, 1]

  /**
   * 计算重连延迟
   *
   * @param {number} attempt - 当前重连次数
   * @returns {number} 延迟时间（毫秒）
   * @internal 内部方法，不对外暴露
   */
  function calculateRetryDelay(attempt) {
    let delay = 0

    switch (strategy) {
      case RECONNECT_STRATEGY.LINEAR:
        delay = retryInterval * attempt
        break

      case RECONNECT_STRATEGY.EXPONENTIAL:
        delay = retryInterval * Math.pow(2, attempt - 1)
        break

      case RECONNECT_STRATEGY.FIBONACCI:
        // 计算斐波那契数列
        while (fibonacciSequence.length <= attempt) {
          const next = fibonacciSequence[fibonacciSequence.length - 1] +
                       fibonacciSequence[fibonacciSequence.length - 2]
          fibonacciSequence.push(next)
        }
        delay = retryInterval * fibonacciSequence[attempt]
        break

      case RECONNECT_STRATEGY.FIXED:
      default:
        delay = retryInterval
        break
    }

    // 限制最大延迟
    return Math.min(delay, maxRetryInterval)
  }

  /**
   * 建立WebSocket连接
   */
  function connect() {
    // 如果已经连接或正在连接，先断开
    if (ws.value) {
      disconnect()
    }

    connectionStatus.value = CONNECTION_STATUS.CONNECTING

    try {
      ws.value = new WebSocket(url)

      // 连接成功
      ws.value.onopen = () => {
        connectionStatus.value = CONNECTION_STATUS.CONNECTED
        retryCount.value = 0
        nextRetryDelay.value = 0
        connectedTime.value = Date.now()
        fibonacciSequence = [1, 1]

        // 启动心跳
        startHeartbeat()

        // 发送队列中的消息
        flushMessageQueue()

        // 触发回调
        onOpen?.()
      }

      // 接收消息
      ws.value.onmessage = (event) => {
        lastMessageTime.value = Date.now()
        messageStats.value.received++

        try {
          const data = JSON.parse(event.data)

          // 处理心跳响应
          if (data.type === 'pong') {
            handlePong(data)
          } else {
            onMessage?.(data)
          }
        } catch (error) {
          console.error('[WebSocket] 消息解析错误:', error)
          onMessage?.(event.data)
        }
      }

      // 连接关闭
      ws.value.onclose = (event) => {
        connectionStatus.value = CONNECTION_STATUS.DISCONNECTED
        stopHeartbeat()

        // 触发回调
        onClose?.({
          code: event.code,
          reason: event.reason,
          wasClean: event.wasClean
        })

        // 自动重连
        if (connectionStatus.value !== CONNECTION_STATUS.FAILED) {
          scheduleReconnect()
        }
      }

      // 连接错误
      ws.value.onerror = (error) => {
        console.error('[WebSocket] 连接错误:', error)
        onError?.(error)
      }
    } catch (error) {
      console.error('[WebSocket] 创建连接失败:', error)
      connectionStatus.value = CONNECTION_STATUS.FAILED
      onError?.(error)
    }
  }

  /**
   * 断开WebSocket连接
   */
  function disconnect() {
    stopReconnect()
    stopHeartbeat()

    if (ws.value) {
      ws.value.close()
      ws.value = null
    }

    connectionStatus.value = CONNECTION_STATUS.DISCONNECTED
    retryCount.value = 0
    nextRetryDelay.value = 0
  }

  /**
   * 安排重连任务
   *
   * @internal 内部方法，不对外暴露
   */
  function scheduleReconnect() {
    // 检查是否已达到最大重连次数
    if (retryCount.value >= maxRetries) {
      connectionStatus.value = CONNECTION_STATUS.FAILED
      onMaxRetriesReached?.({
        attempts: retryCount.value,
        maxAttempts: maxRetries
      })
      return
    }

    connectionStatus.value = CONNECTION_STATUS.RECONNECTING

    // 计算重连延迟
    const delay = calculateRetryDelay(retryCount.value + 1)
    nextRetryDelay.value = delay
    retryCount.value++

    // 触发重连进度回调
    onReconnecting?.({
      attempt: retryCount.value,
      maxAttempts: maxRetries,
      delay,
      nextRetryDelay: delay
    })

    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      connect()
    }, delay)
  }

  /**
   * 停止重连任务
   *
   * @internal 内部方法，不对外暴露
   */
  function stopReconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  /**
   * 手动重连
   */
  function manualReconnect() {
    retryCount.value = 0
    fibonacciSequence = [1, 1]
    stopReconnect()
    disconnect()
    connect()
  }

  /**
   * 发送消息
   *
   * @param {Object|string} data - 要发送的数据
   * @returns {boolean} 发送是否成功
   */
  function send(data) {
    const message = typeof data === 'string' ? data : JSON.stringify(data)

    // 如果未连接且启用了消息队列，将消息加入队列
    if (!isConnected.value && enableMessageQueue) {
      if (messageQueue.value.length < maxQueueSize) {
        messageQueue.value.push(message)
        messageStats.value.queued++
        return true
      }
      console.warn('[WebSocket] 消息队列已满，丢弃消息')
      return false
    }

    // 直接发送
    if (ws.value && isConnected.value) {
      try {
        ws.value.send(message)
        lastSendTime.value = Date.now()
        messageStats.value.sent++
        return true
      } catch (error) {
        console.error('[WebSocket] 发送消息失败:', error)
        return false
      }
    }

    return false
  }

  /**
   * 发送队列中的消息
   *
   * @internal 内部方法，不对外暴露
   */
  function flushMessageQueue() {
    if (!isConnected.value || messageQueue.value.length === 0) return

    const queue = [...messageQueue.value]
    messageQueue.value = []

    queue.forEach(message => {
      send(message)
    })
  }

  /**
   * 启动心跳检测
   *
   * @internal 内部方法，不对外暴露
   */
  function startHeartbeat() {
    stopHeartbeat()

    heartbeatTimer = setInterval(() => {
      if (isConnected.value) {
        sendHeartbeat()
      }
    }, heartbeatInterval)
  }

  /**
   * 停止心跳检测
   *
   * @internal 内部方法，不对外暴露
   */
  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
    if (heartbeatTimeoutTimer) {
      clearTimeout(heartbeatTimeoutTimer)
      heartbeatTimeoutTimer = null
    }
  }

  /**
   * 发送心跳
   *
   * @internal 内部方法，不对外暴露
   */
  function sendHeartbeat() {
    heartbeatStatus.value.lastPingTime = Date.now()
    send({ type: 'ping', timestamp: Date.now() })

    // 设置心跳超时
    heartbeatTimeoutTimer = setTimeout(() => {
      console.warn('[WebSocket] 心跳超时，断开连接')
      disconnect()
      scheduleReconnect()
    }, heartbeatTimeout)
  }

  /**
   * 处理心跳响应
   *
   * @param {Object} data - 响应数据
   * @internal 内部方法，不对外暴露
   */
  function handlePong(data) {
    heartbeatStatus.value.lastPongTime = Date.now()
    heartbeatStatus.value.latency = Date.now() - (data.timestamp || heartbeatStatus.value.lastPingTime)

    // 清除心跳超时定时器
    if (heartbeatTimeoutTimer) {
      clearTimeout(heartbeatTimeoutTimer)
      heartbeatTimeoutTimer = null
    }
  }

  /**
   * 重置重连计数器
   */
  function resetRetryCount() {
    retryCount.value = 0
    fibonacciSequence = [1, 1]
  }

  /**
   * 清空消息队列
   */
  function clearMessageQueue() {
    messageQueue.value = []
    messageStats.value.queued = 0
  }

  /**
   * 获取连接统计信息
   */
  const connectionStats = computed(() => ({
    status: connectionStatus.value,
    retryCount: retryCount.value,
    maxRetries,
    nextRetryDelay: nextRetryDelay.value,
    connectedTime: connectedTime.value,
    uptime: connectedTime.value ? Date.now() - connectedTime.value : 0,
    messageStats: { ...messageStats.value },
    heartbeat: { ...heartbeatStatus.value },
    queueSize: messageQueue.value.length
  }))

  // 组件卸载时自动清理
  onUnmounted(() => {
    disconnect()
  })

  return {
    // 状态
    ws: readonly(ws),
    connectionStatus: readonly(connectionStatus),
    isConnected,
    isConnecting,
    isReconnecting,
    retryCount: readonly(retryCount),
    nextRetryDelay: readonly(nextRetryDelay),
    messageQueue: readonly(messageQueue),
    lastMessageTime: readonly(lastMessageTime),
    lastSendTime: readonly(lastSendTime),
    connectedTime: readonly(connectedTime),
    messageStats: readonly(messageStats),
    heartbeatStatus: readonly(heartbeatStatus),

    // 计算属性
    connectionStats,

    // 方法
    connect,
    disconnect,
    send,
    manualReconnect,
    resetRetryCount,
    clearMessageQueue
  }
}

/**
 * 创建WebSocket管理器
 *
 * @param {Object} config - 配置对象
 * @returns {Object} 管理器实例
 */
export function createWebSocketManager(config) {
  const connections = new Map()

  return {
    /**
     * 创建或获取WebSocket连接
     */
    getConnection(name, url, options) {
      if (connections.has(name)) {
        return connections.get(name)
      }

      const connection = useWebSocketReconnect(url, { ...config, ...options })
      connections.set(name, connection)
      return connection
    },

    /**
     * 关闭指定连接
     */
    closeConnection(name) {
      const connection = connections.get(name)
      if (connection) {
        connection.disconnect()
        connections.delete(name)
      }
    },

    /**
     * 关闭所有连接
     */
    closeAll() {
      connections.forEach(connection => connection.disconnect())
      connections.clear()
    },

    /**
     * 获取所有连接状态
     */
    getAllStatus() {
      const status = {}
      connections.forEach((connection, name) => {
        status[name] = connection.connectionStatus.value
      })
      return status
    }
  }
}
