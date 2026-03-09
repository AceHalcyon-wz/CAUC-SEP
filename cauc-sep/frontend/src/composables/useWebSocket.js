/**
 * @file useWebSocket.js
 * @path src/composables/
 * @description WebSocket连接管理组合式函数，封装连接、重连、心跳检测、推送频率控制、协议协商等逻辑
 * @author Agent
 * @date 2026-03-07
 * @dependencies vue, msgpack-lite
 */

import { ref, computed, watch, onUnmounted } from 'vue'
import msgpack from 'msgpack-lite'
import { usePushFrequency, PUSH_MODE, FREQUENCY_PRESETS } from './usePushFrequency'

/**
 * WebSocket连接状态枚举
 * 
 * @readonly
 * @enum {string}
 */
export const ConnectionState = {
  /** 未连接 */
  DISCONNECTED: 'disconnected',
  /** 正在连接 */
  CONNECTING: 'connecting',
  /** 已连接 */
  CONNECTED: 'connected',
  /** 正在重连 */
  RECONNECTING: 'reconnecting',
  /** 重连失败 */
  RECONNECT_FAILED: 'reconnect_failed',
  /** 连接超时 */
  TIMEOUT: 'timeout'
}

/**
 * WebSocket错误类型枚举
 * 
 * @readonly
 * @enum {string}
 */
export const WSErrorType = {
  /** 连接错误 */
  CONNECTION_ERROR: 'connection_error',
  /** 连接超时 */
  CONNECTION_TIMEOUT: 'connection_timeout',
  /** 认证失败 */
  AUTH_FAILED: 'auth_failed',
  /** 协议错误 */
  PROTOCOL_ERROR: 'protocol_error',
  /** 网络错误 */
  NETWORK_ERROR: 'network_error',
  /** 服务器错误 */
  SERVER_ERROR: 'server_error',
  /** 消息解析错误 */
  MESSAGE_PARSE_ERROR: 'message_parse_error',
  /** 心跳超时 */
  HEARTBEAT_TIMEOUT: 'heartbeat_timeout',
  /** 重连失败 */
  RECONNECT_FAILED: 'reconnect_failed'
}

/**
 * 重连策略枚举
 * 
 * @readonly
 * @enum {string}
 */
export const ReconnectStrategy = {
  /** 固定间隔 */
  FIXED: 'fixed',
  /** 线性递增 */
  LINEAR: 'linear',
  /** 指数退避 */
  EXPONENTIAL: 'exponential',
  /** 斐波那契 */
  FIBONACCI: 'fibonacci'
}

/**
 * WebSocket通信协议类型枚举
 * 
 * @readonly
 * @enum {string}
 */
export const ProtocolType = {
  /** JSON文本协议（默认，兼容性好） */
  JSON: 'json',
  /** MessagePack二进制协议（高性能，体积小） */
  MSGPACK: 'msgpack'
}

/**
 * WebSocket连接管理组合式函数
 *
 * @param {Object} options - 配置选项
 * @param {string} options.url - WebSocket服务器地址
 * @param {Function} [options.onMessage] - 消息接收回调
 * @param {Function} [options.onOpen] - 连接成功回调
 * @param {Function} [options.onClose] - 连接关闭回调
 * @param {Function} [options.onError] - 错误回调
 * @param {Function} [options.onReconnecting] - 重连进度回调
 * @param {Function} [options.onProtocolChange] - 协议切换回调
 * @param {Function} [options.onStateChange] - 连接状态变更回调
 * @param {Function} [options.onSyncComplete] - 数据同步完成回调
 * @param {number} [options.reconnectInterval=3000] - 初始重连间隔（毫秒）
 * @param {number} [options.heartbeatInterval=30000] - 心跳间隔（毫秒）
 * @param {number} [options.heartbeatTimeout=5000] - 心跳超时时间（毫秒）
 * @param {number} [options.maxReconnectAttempts=5] - 最大重连次数
 * @param {number} [options.maxBackoffDelay=30000] - 最大退避延迟（毫秒）
 * @param {number} [options.messageQueueSize=100] - 消息队列最大容量
 * @param {string} [options.defaultPushMode='normal'] - 默认推送模式
 * @param {boolean} [options.enableFrequencyControl=true] - 是否启用频率控制
 * @param {string} [options.preferredProtocol='msgpack'] - 首选协议类型
 * @param {boolean} [options.enableProtocolFallback=true] - 是否启用协议降级
 * @param {boolean} [options.enableMessageQueue=true] - 是否启用消息队列缓存
 * @param {boolean} [options.enableAutoSync=true] - 是否启用自动数据同步
 * @returns {Object} WebSocket状态与操作方法
 *
 * @example
 * ```javascript
 * const { 
 *   connectionState,
 *   wsConnected, 
 *   connect, 
 *   disconnect, 
 *   send, 
 *   currentProtocol,
 *   protocolSupported,
 *   flushMessageQueue
 * } = useWebSocket({
 *   url: 'ws://localhost:8000/ws?protocol=msgpack',
 *   onMessage: (data) => console.log('收到消息:', data),
 *   onOpen: () => console.log('连接成功'),
 *   onClose: () => console.log('连接关闭'),
 *   onError: (error) => console.error('连接错误:', error),
 *   onProtocolChange: (protocol) => console.log('协议切换:', protocol),
 *   onStateChange: (state) => console.log('状态变更:', state),
 *   onSyncComplete: () => console.log('数据同步完成')
 * })
 *
 * // 建立连接
 * connect()
 *
 * // 发送消息
 * send({ type: 'command', data: 'start' })
 *
 * // 断开连接
 * disconnect()
 * ```
 */
export function useWebSocket(options = {}) {
  const {
    url,
    onMessage,
    onOpen,
    onClose,
    onError,
    onReconnecting,
    onProtocolChange,
    onStateChange,
    onSyncComplete,
    reconnectInterval = 3000,
    heartbeatInterval = 30000,
    heartbeatTimeout = 5000,
    maxReconnectAttempts = 5,
    maxBackoffDelay = 30000,
    messageQueueSize = 100,
    defaultPushMode = PUSH_MODE.NORMAL,
    enableFrequencyControl = true,
    preferredProtocol = ProtocolType.MSGPACK,
    enableProtocolFallback = true,
    enableMessageQueue = true,
    enableAutoSync = true,
    // 新增配置选项
    reconnectStrategy = ReconnectStrategy.EXPONENTIAL,
    connectionTimeout = 10000,
    enableMessageDedup = true,
    dedupWindowMs = 5000,
    maxDedupCacheSize = 1000,
    enableHighFrequencyOptimization = true,
    highFrequencyThreshold = 50,
    enableConnectionMonitor = true,
    monitorInterval = 5000
  } = options

  // === 响应式状态 ===
  /** 连接状态（使用枚举） */
  const connectionState = ref(ConnectionState.DISCONNECTED)
  /** WebSocket连接状态（兼容旧API） */
  const wsConnected = computed(() => connectionState.value === ConnectionState.CONNECTED)
  /** WebSocket正在连接状态（兼容旧API） */
  const wsConnecting = computed(() => 
    connectionState.value === ConnectionState.CONNECTING || 
    connectionState.value === ConnectionState.RECONNECTING
  )
  /** 当前重连次数 */
  const reconnectAttempts = ref(0)
  /** 是否已达到最大重连次数 */
  const maxReconnectReached = ref(false)
  /** 推送频率控制 */
  const frequencyControl = enableFrequencyControl 
    ? usePushFrequency({ defaultMode: defaultPushMode }) 
    : null
  /** 推送频率统计（条/秒） */
  const pushFrequency = ref(0)
  /** 数据延迟（毫秒） */
  const dataLatency = ref(0)
  /** 最后接收消息时间戳 */
  const lastMessageTime = ref(null)
  /** 消息计数 */
  const messageCount = ref(0)
  
  // === 协议相关状态 ===
  /** 当前使用的协议类型 */
  const currentProtocol = ref(ProtocolType.JSON)
  /** 服务器支持的协议类型 */
  const serverProtocol = ref(null)
  /** 协议是否受支持（MessagePack） */
  const protocolSupported = computed(() => {
    return currentProtocol.value === ProtocolType.MSGPACK
  })
  /** 协议降级次数 */
  const protocolFallbackCount = ref(0)
  /** 是否正在尝试协议协商 */
  const isProtocolNegotiating = ref(false)
  /** 是否为手动切换协议 */
  const isManualProtocolSwitch = ref(false)

  // === 消息队列缓存 ===
  /** 待发送消息队列 */
  const messageQueue = ref([])
  /** 队列是否已满 */
  const queueFull = computed(() => messageQueue.value.length >= messageQueueSize)
  /** 队列消息数量 */
  const queueLength = computed(() => messageQueue.value.length)

  // === 心跳检测状态 ===
  /** 最后心跳发送时间 */
  const lastHeartbeatTime = ref(null)
  /** 最后心跳响应时间 */
  const lastPongTime = ref(null)
  /** 心跳超时计数 */
  const heartbeatTimeoutCount = ref(0)
  /** 连接质量评分（0-100） */
  const connectionQuality = computed(() => {
    if (!wsConnected.value) return 0
    
    let score = 100
    
    // 延迟惩罚（每10ms延迟扣1分，最多扣30分）
    if (dataLatency.value > 0) {
      score -= Math.min(30, Math.floor(dataLatency.value / 10))
    }
    
    // 心跳超时惩罚（每次超时扣10分，最多扣40分）
    score -= Math.min(40, heartbeatTimeoutCount.value * 10)
    
    // 重连次数惩罚（每次重连扣5分，最多扣30分）
    score -= Math.min(30, reconnectAttempts.value * 5)
    
    return Math.max(0, score)
  })

  // === 消息去重状态 ===
  /** 消息去重缓存 */
  const messageDedupCache = ref(new Map())
  /** 去重命中次数 */
  const dedupHitCount = ref(0)

  // === 高频消息优化状态 ===
  /** 高频消息缓冲区 */
  const highFrequencyBuffer = ref([])
  /** 是否正在处理高频消息 */
  const isProcessingHighFrequency = ref(false)
  /** 高频消息处理定时器ID */
  let highFrequencyTimer = null

  // === 连接监控状态 ===
  /** 连接监控定时器ID */
  let connectionMonitorTimer = null
  /** 连接历史记录 */
  const connectionHistory = ref([])
  /** 最大连接历史记录数 */
  const MAX_CONNECTION_HISTORY = 50

  // === 错误状态 ===
  /** 最后一次错误信息 */
  const lastError = ref(null)
  /** 错误计数 */
  const errorCount = ref(0)
  /** 错误历史记录 */
  const errorHistory = ref([])
  /** 最大错误历史记录数 */
  const MAX_ERROR_HISTORY = 20

  // === 内部变量 ===
  /** WebSocket实例 */
  let ws = null
  /** 重连定时器 */
  let reconnectTimer = null
  /** 心跳定时器 */
  let heartbeatTimer = null
  /** 心跳超时定时器 */
  let heartbeatTimeoutTimer = null
  /** 频率统计定时器 */
  let frequencyTimer = null
  /** 频率控制取消订阅函数 */
  let frequencyUnsubscribe = null
  /** 协议协商超时定时器 */
  let protocolNegotiateTimer = null
  /** 原始URL（不含协议参数） */
  let baseUrl = url
  /** 是否正在等待心跳响应 */
  let waitingForPong = false
  /** 是否正在同步数据 */
  let isSyncing = false

  /**
   * 更新连接状态
   *
   * @param {string} newState - 新的连接状态
   * @internal 内部方法，不对外暴露
   */
  function updateConnectionState(newState) {
    const oldState = connectionState.value
    if (oldState !== newState) {
      connectionState.value = newState
      console.log(`[WebSocket] 状态变更: ${oldState} -> ${newState}`)
      onStateChange?.(newState)
      
      // 记录连接历史
      if (enableConnectionMonitor) {
        recordConnectionHistory(oldState, newState)
      }
    }
  }

  /**
   * 记录连接历史
   *
   * @param {string} fromState - 之前的状态
   * @param {string} toState - 新的状态
   * @internal 内部方法，不对外暴露
   */
  function recordConnectionHistory(fromState, toState) {
    connectionHistory.value.push({
      timestamp: Date.now(),
      from: fromState,
      to: toState,
      reconnectAttempts: reconnectAttempts.value,
      connectionQuality: connectionQuality.value
    })
    
    // 限制历史记录数量
    if (connectionHistory.value.length > MAX_CONNECTION_HISTORY) {
      connectionHistory.value = connectionHistory.value.slice(-MAX_CONNECTION_HISTORY)
    }
  }

  /**
   * 生成消息唯一标识（用于去重）
   *
   * @param {Object} data - 消息数据
   * @returns {string} 消息唯一标识
   * @internal 内部方法，不对外暴露
   */
  function generateMessageId(data) {
    // 使用消息类型、时间戳和关键数据生成唯一ID
    const type = data.type || 'unknown'
    const timestamp = data.timestamp || Date.now()
    const dataHash = JSON.stringify(data).slice(0, 100) // 取前100字符作为特征
    
    // 简单哈希函数
    let hash = 0
    for (let i = 0; i < dataHash.length; i++) {
      const char = dataHash.charCodeAt(i)
      hash = ((hash << 5) - hash) + char
      hash = hash & hash // Convert to 32bit integer
    }
    
    return `${type}_${timestamp}_${Math.abs(hash)}`
  }

  /**
   * 检查消息是否重复
   *
   * @param {Object} data - 消息数据
   * @returns {boolean} 是否为重复消息
   * @internal 内部方法，不对外暴露
   */
  function isDuplicateMessage(data) {
    if (!enableMessageDedup) return false
    
    const messageId = generateMessageId(data)
    const now = Date.now()
    
    // 清理过期的缓存
    cleanupDedupCache(now)
    
    // 检查是否已存在
    if (messageDedupCache.value.has(messageId)) {
      dedupHitCount.value++
      console.log(`[WebSocket] 检测到重复消息: ${messageId}`)
      return true
    }
    
    // 添加到缓存
    messageDedupCache.value.set(messageId, {
      timestamp: now,
      type: data.type
    })
    
    // 限制缓存大小
    if (messageDedupCache.value.size > maxDedupCacheSize) {
      const oldestKey = messageDedupCache.value.keys().next().value
      messageDedupCache.value.delete(oldestKey)
    }
    
    return false
  }

  /**
   * 清理过期的去重缓存
   *
   * @param {number} now - 当前时间戳
   * @internal 内部方法，不对外暴露
   */
  function cleanupDedupCache(now) {
    const expireTime = now - dedupWindowMs
    
    for (const [key, value] of messageDedupCache.value.entries()) {
      if (value.timestamp < expireTime) {
        messageDedupCache.value.delete(key)
      } else {
        // 由于Map按插入顺序迭代，遇到未过期的就可以停止
        break
      }
    }
  }

  /**
   * 处理高频消息
   *
   * @param {Object} data - 消息数据
   * @internal 内部方法，不对外暴露
   */
  function handleHighFrequencyMessage(data) {
    if (!enableHighFrequencyOptimization) {
      return false
    }
    
    // 检查是否为高频消息类型
    const highFrequencyTypes = [
      'waveform_data',
      'realtime_data',
      'sensor_data',
      'position_update',
      'streaming_data'
    ]
    
    if (!highFrequencyTypes.includes(data.type)) {
      return false
    }
    
    // 添加到缓冲区
    highFrequencyBuffer.value.push({
      data,
      timestamp: Date.now()
    })
    
    // 如果缓冲区未启动处理，启动定时处理
    if (!isProcessingHighFrequency.value) {
      startHighFrequencyProcessing()
    }
    
    return true
  }

  /**
   * 启动高频消息处理
   *
   * @internal 内部方法，不对外暴露
   */
  function startHighFrequencyProcessing() {
    if (highFrequencyTimer) return
    
    isProcessingHighFrequency.value = true
    
    highFrequencyTimer = setInterval(() => {
      if (highFrequencyBuffer.value.length === 0) {
        stopHighFrequencyProcessing()
        return
      }
      
      // 批量处理消息
      const batchSize = Math.min(10, highFrequencyBuffer.value.length)
      const batch = highFrequencyBuffer.value.splice(0, batchSize)
      
      // 合并同类型消息
      const mergedData = mergeHighFrequencyMessages(batch)
      
      // 触发消息回调
      if (mergedData && onMessage) {
        onMessage(mergedData)
      }
    }, 100) // 每100ms处理一次
  }

  /**
   * 停止高频消息处理
   *
   * @internal 内部方法，不对外暴露
   */
  function stopHighFrequencyProcessing() {
    if (highFrequencyTimer) {
      clearInterval(highFrequencyTimer)
      highFrequencyTimer = null
    }
    isProcessingHighFrequency.value = false
  }

  /**
   * 合并高频消息
   *
   * @param {Array} messages - 消息数组
   * @returns {Object|null} 合并后的消息
   * @internal 内部方法，不对外暴露
   */
  function mergeHighFrequencyMessages(messages) {
    if (messages.length === 0) return null
    
    if (messages.length === 1) {
      return messages[0].data
    }
    
    // 按类型分组
    const grouped = {}
    messages.forEach(msg => {
      const type = msg.data.type || 'unknown'
      if (!grouped[type]) {
        grouped[type] = []
      }
      grouped[type].push(msg.data)
    })
    
    // 返回合并后的消息
    return {
      type: 'batch_update',
      count: messages.length,
      data: grouped,
      timestamp: Date.now()
    }
  }

  /**
   * 启动连接监控
   *
   * @internal 内部方法，不对外暴露
   */
  function startConnectionMonitor() {
    if (!enableConnectionMonitor || connectionMonitorTimer) return
    
    connectionMonitorTimer = setInterval(() => {
      const stats = getConnectionStats()
      
      // 检查连接健康状态
      if (stats.connected) {
        // 检查心跳是否正常
        const timeSinceLastPong = Date.now() - (lastPongTime.value || 0)
        if (timeSinceLastPong > heartbeatInterval * 2) {
          console.warn('[WebSocket] 连接监控: 长时间未收到心跳响应')
        }
        
        // 检查消息频率
        if (stats.pushFrequency > highFrequencyThreshold) {
          console.log(`[WebSocket] 连接监控: 高频消息模式 (${stats.pushFrequency} msg/s)`)
        }
        
        // 检查延迟
        if (stats.dataLatency > 1000) {
          console.warn(`[WebSocket] 连接监控: 高延迟警告 (${stats.dataLatency}ms)`)
        }
      }
    }, monitorInterval)
  }

  /**
   * 停止连接监控
   *
   * @internal 内部方法，不对外暴露
   */
  function stopConnectionMonitor() {
    if (connectionMonitorTimer) {
      clearInterval(connectionMonitorTimer)
      connectionMonitorTimer = null
    }
  }

  /**
   * 分类并记录错误
   *
   * @param {Error|string} error - 错误对象
   * @param {string} type - 错误类型
   * @param {Object} context - 错误上下文
   * @returns {Object} 分类后的错误信息
   * @internal 内部方法，不对外暴露
   */
  function classifyError(error, type = WSErrorType.CONNECTION_ERROR, context = {}) {
    const errorInfo = {
      id: `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: Date.now(),
      type,
      message: error?.message || error?.toString() || '未知错误',
      name: error?.name || 'Error',
      stack: error?.stack,
      context,
      recoverable: isRecoverableError(type),
      userMessage: getUserFriendlyErrorMessage(type, error),
      suggestion: getErrorSuggestion(type)
    }
    
    // 更新错误状态
    lastError.value = errorInfo
    errorCount.value++
    
    // 添加到错误历史
    errorHistory.value.push(errorInfo)
    if (errorHistory.value.length > MAX_ERROR_HISTORY) {
      errorHistory.value = errorHistory.value.slice(-MAX_ERROR_HISTORY)
    }
    
    console.error(`[WebSocket] 错误 [${type}]:`, errorInfo.message)
    
    return errorInfo
  }

  /**
   * 判断错误是否可恢复
   *
   * @param {string} errorType - 错误类型
   * @returns {boolean} 是否可恢复
   * @internal 内部方法，不对外暴露
   */
  function isRecoverableError(errorType) {
    const recoverableTypes = [
      WSErrorType.CONNECTION_ERROR,
      WSErrorType.NETWORK_ERROR,
      WSErrorType.HEARTBEAT_TIMEOUT,
      WSErrorType.CONNECTION_TIMEOUT
    ]
    return recoverableTypes.includes(errorType)
  }

  /**
   * 获取用户友好的错误消息
   *
   * @param {string} errorType - 错误类型
   * @param {Error} error - 错误对象
   * @returns {string} 用户友好的错误消息
   * @internal 内部方法，不对外暴露
   */
  function getUserFriendlyErrorMessage(errorType, error) {
    const messages = {
      [WSErrorType.CONNECTION_ERROR]: '连接服务器失败，请检查网络连接',
      [WSErrorType.CONNECTION_TIMEOUT]: '连接超时，请检查网络状况',
      [WSErrorType.AUTH_FAILED]: '认证失败，请检查登录状态',
      [WSErrorType.PROTOCOL_ERROR]: '协议错误，正在尝试切换协议',
      [WSErrorType.NETWORK_ERROR]: '网络错误，正在尝试重新连接',
      [WSErrorType.SERVER_ERROR]: '服务器错误，请稍后重试',
      [WSErrorType.MESSAGE_PARSE_ERROR]: '消息解析错误',
      [WSErrorType.HEARTBEAT_TIMEOUT]: '心跳超时，连接可能不稳定',
      [WSErrorType.RECONNECT_FAILED]: '重连失败，请手动重试'
    }
    
    return messages[errorType] || error?.message || '发生未知错误'
  }

  /**
   * 获取错误解决建议
   *
   * @param {string} errorType - 错误类型
   * @returns {string} 解决建议
   * @internal 内部方法，不对外暴露
   */
  function getErrorSuggestion(errorType) {
    const suggestions = {
      [WSErrorType.CONNECTION_ERROR]: '请检查网络连接，确保服务器地址正确',
      [WSErrorType.CONNECTION_TIMEOUT]: '请检查网络延迟，或尝试切换网络环境',
      [WSErrorType.AUTH_FAILED]: '请重新登录或刷新页面',
      [WSErrorType.PROTOCOL_ERROR]: '系统将自动切换到兼容协议',
      [WSErrorType.NETWORK_ERROR]: '系统将自动尝试重新连接',
      [WSErrorType.SERVER_ERROR]: '请联系管理员或稍后重试',
      [WSErrorType.MESSAGE_PARSE_ERROR]: '消息格式可能不兼容，请联系技术支持',
      [WSErrorType.HEARTBEAT_TIMEOUT]: '网络可能不稳定，建议检查网络质量',
      [WSErrorType.RECONNECT_FAILED]: '请点击"重新连接"按钮手动重试'
    }
    
    return suggestions[errorType] || '请刷新页面或联系技术支持'
  }

  /**
   * 计算重连延迟（支持多种策略）
   *
   * @param {number} attempt - 当前重连次数
   * @returns {number} 延迟时间（毫秒）
   * @internal 内部方法，不对外暴露
   */
  function calculateReconnectDelay(attempt) {
    let delay = 0
    
    switch (reconnectStrategy) {
      case ReconnectStrategy.FIXED:
        delay = reconnectInterval
        break
        
      case ReconnectStrategy.LINEAR:
        delay = reconnectInterval * attempt
        break
        
      case ReconnectStrategy.EXPONENTIAL:
        delay = reconnectInterval * Math.pow(2, attempt - 1)
        break
        
      case ReconnectStrategy.FIBONACCI:
        delay = reconnectInterval * fibonacci(attempt)
        break
        
      default:
        delay = reconnectInterval * Math.pow(2, attempt - 1)
    }
    
    // 添加随机抖动（±20%），避免多客户端同时重连
    const jitter = delay * 0.2 * (Math.random() * 2 - 1)
    delay = delay + jitter
    
    // 限制最大延迟
    return Math.min(delay, maxBackoffDelay)
  }

  /**
   * 计算斐波那契数
   *
   * @param {number} n - 斐波那契数列位置
   * @returns {number} 斐波那契数
   * @internal 内部方法，不对外暴露
   */
  function fibonacci(n) {
    if (n <= 1) return 1
    let a = 1, b = 1
    for (let i = 2; i <= n; i++) {
      [a, b] = [b, a + b]
    }
    return b
  }

  /**
   * 将消息添加到队列
   *
   * @param {Object} data - 要发送的数据
   * @returns {boolean} 是否成功加入队列
   * @internal 内部方法，不对外暴露
   */
  function enqueueMessage(data) {
    if (!enableMessageQueue) return false
    
    if (messageQueue.value.length >= messageQueueSize) {
      // 队列已满，移除最旧的消息
      messageQueue.value.shift()
      console.warn('[WebSocket] 消息队列已满，移除最旧消息')
    }
    
    messageQueue.value.push({
      data,
      timestamp: Date.now(),
      attempts: 0
    })
    
    return true
  }

  /**
   * 刷新消息队列（发送所有缓存消息）
   *
   * @returns {Promise<number>} 成功发送的消息数量
   */
  async function flushMessageQueue() {
    if (!wsConnected.value || messageQueue.value.length === 0) {
      return 0
    }

    const queueCopy = [...messageQueue.value]
    messageQueue.value = []
    let successCount = 0

    for (const item of queueCopy) {
      try {
        const sent = send(item.data)
        if (sent) {
          successCount++
        } else {
          // 发送失败，重新加入队列
          item.attempts++
          if (item.attempts < 3) {
            messageQueue.value.push(item)
          }
        }
        // 小延迟避免过快发送
        await new Promise(resolve => setTimeout(resolve, 10))
      } catch (error) {
        console.error('[WebSocket] 队列消息发送失败:', error)
        item.attempts++
        if (item.attempts < 3) {
          messageQueue.value.push(item)
        }
      }
    }

    console.log(`[WebSocket] 队列刷新完成: ${successCount}/${queueCopy.length}`)
    return successCount
  }

  /**
   * 清空消息队列
   */
  function clearMessageQueue() {
    messageQueue.value = []
  }

  /**
   * 请求服务器同步数据
   *
   * @description 重连后请求服务器同步断线期间的数据
   * @internal 内部方法，不对外暴露
   */
  async function requestSync() {
    if (!enableAutoSync || !wsConnected.value || isSyncing) {
      return
    }

    isSyncing = true
    console.log('[WebSocket] 请求服务器同步数据')

    try {
      const lastTime = lastMessageTime.value || Date.now() - 60000 // 默认同步最近1分钟
      
      send({
        type: 'sync_request',
        last_message_time: lastTime,
        client_id: getClientId()
      })

      // 等待同步完成（最多10秒）
      await new Promise((resolve) => {
        const timeout = setTimeout(() => {
          isSyncing = false
          resolve()
        }, 10000)

        // 监听同步完成消息
        const checkSyncComplete = (data) => {
          if (data.type === 'sync_complete') {
            clearTimeout(timeout)
            isSyncing = false
            onSyncComplete?.(data)
            resolve()
          }
        }

        // 临时监听器（需要在onMessage中处理）
        window.__wsSyncHandler = checkSyncComplete
      })
    } catch (error) {
      console.error('[WebSocket] 数据同步失败:', error)
      isSyncing = false
    }
  }

  /**
   * 获取客户端唯一标识
   *
   * @returns {string} 客户端ID
   * @internal 内部方法，不对外暴露
   */
  function getClientId() {
    let clientId = sessionStorage.getItem('ws_client_id')
    if (!clientId) {
      clientId = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      sessionStorage.setItem('ws_client_id', clientId)
    }
    return clientId
  }

  /**
   * 构建带协议参数的WebSocket URL
   *
   * @param {string} protocol - 协议类型
   * @returns {string} 完整的WebSocket URL
   * @internal 内部方法，不对外暴露
   */
  function buildUrlWithProtocol(protocol) {
    if (!baseUrl) return baseUrl
    
    const urlObj = new URL(baseUrl, window.location.origin)
    urlObj.searchParams.set('protocol', protocol)
    return urlObj.toString()
  }

  /**
   * 序列化消息（根据当前协议类型）
   *
   * @param {Object} data - 要序列化的数据对象
   * @returns {string|ArrayBuffer} 序列化后的数据
   * @internal 内部方法，不对外暴露
   */
  function serializeMessage(data) {
    if (currentProtocol.value === ProtocolType.MSGPACK) {
      try {
        // msgpack-lite返回Buffer/Uint8Array，需要转换为ArrayBuffer
        const encoded = msgpack.encode(data)
        // 如果已经是ArrayBuffer，直接返回
        if (encoded instanceof ArrayBuffer) {
          return encoded
        }
        // 否则转换为ArrayBuffer
        return encoded.buffer.slice(encoded.byteOffset, encoded.byteOffset + encoded.byteLength)
      } catch (error) {
        console.warn('[WebSocket] MessagePack序列化失败，降级为JSON:', error)
        fallbackToJSON()
        return JSON.stringify(data)
      }
    }
    return JSON.stringify(data)
  }

  /**
   * 反序列化消息（自动检测协议类型）
   *
   * @param {string|ArrayBuffer|Blob} data - 接收到的消息数据
   * @returns {Promise<Object>} 反序列化后的对象
   * @internal 内部方法，不对外暴露
   */
  async function deserializeMessage(data) {
    // Blob类型需要先转换为ArrayBuffer
    if (data instanceof Blob) {
      const buffer = await data.arrayBuffer()
      return deserializeArrayBuffer(buffer)
    }

    // 二进制数据（MessagePack）
    if (data instanceof ArrayBuffer) {
      return deserializeArrayBuffer(data)
    }

    // 文本数据（JSON）
    if (typeof data === 'string') {
      try {
        return JSON.parse(data)
      } catch (error) {
        console.error('[WebSocket] JSON解析失败:', error)
        throw error
      }
    }

    throw new Error('不支持的消息格式')
  }

  /**
   * 反序列化ArrayBuffer数据
   *
   * @param {ArrayBuffer} buffer - 二进制数据
   * @returns {Object} 反序列化后的对象
   * @internal 内部方法，不对外暴露
   */
  function deserializeArrayBuffer(buffer) {
    try {
      const result = msgpack.decode(new Uint8Array(buffer))
      // 成功解码MessagePack，更新协议状态
      if (currentProtocol.value !== ProtocolType.MSGPACK) {
        updateProtocol(ProtocolType.MSGPACK)
      }
      return result
    } catch (error) {
      console.warn('[WebSocket] MessagePack解码失败，尝试JSON:', error)
      // 尝试将二进制数据作为UTF-8文本解析
      try {
        const text = new TextDecoder().decode(buffer)
        return JSON.parse(text)
      } catch (jsonError) {
        // 解码失败，触发降级
        if (enableProtocolFallback && currentProtocol.value === ProtocolType.MSGPACK) {
          fallbackToJSON()
        }
        throw new Error('消息解码失败：既不是有效的MessagePack也不是JSON')
      }
    }
  }

  /**
   * 更新当前协议类型
   *
   * @param {string} protocol - 新的协议类型
   * @internal 内部方法，不对外暴露
   */
  function updateProtocol(protocol) {
    if (currentProtocol.value !== protocol) {
      const oldProtocol = currentProtocol.value
      currentProtocol.value = protocol
      console.log(`[WebSocket] 协议切换: ${oldProtocol} -> ${protocol}`)
      onProtocolChange?.(protocol)
    }
  }

  /**
   * 降级到JSON协议
   *
   * @description 当MessagePack协议失败时，自动降级到JSON协议
   * @internal 内部方法，不对外暴露
   */
  function fallbackToJSON() {
    if (!enableProtocolFallback || currentProtocol.value === ProtocolType.JSON) {
      return
    }

    protocolFallbackCount.value++
    console.warn(`[WebSocket] 协议降级 (第${protocolFallbackCount.value}次): MessagePack -> JSON`)
    updateProtocol(ProtocolType.JSON)

    // 如果连接仍然活跃，重新建立连接
    if (wsConnected.value && ws) {
      console.log('[WebSocket] 使用JSON协议重新连接')
      reconnect()
    }
  }

  /**
   * 尝试协议协商
   *
   * @description 尝试使用首选协议连接，失败则降级
   * @internal 内部方法，不对外暴露
   */
  function negotiateProtocol() {
    if (!enableProtocolFallback) {
      // 不启用降级，直接使用首选协议
      currentProtocol.value = preferredProtocol
      return buildUrlWithProtocol(preferredProtocol)
    }

    isProtocolNegotiating.value = true
    
    // 如果是手动切换协议，使用当前已设置的协议
    // 如果之前已经降级过（protocolFallbackCount > 0），则使用当前协议
    // 否则使用首选协议
    let protocolToUse
    if (isManualProtocolSwitch.value) {
      protocolToUse = currentProtocol.value
      isManualProtocolSwitch.value = false // 重置标志
    } else if (protocolFallbackCount.value > 0) {
      protocolToUse = currentProtocol.value
    } else {
      protocolToUse = preferredProtocol
    }
    
    if (protocolToUse === ProtocolType.MSGPACK) {
      console.log('[WebSocket] 尝试使用MessagePack协议连接')
      currentProtocol.value = ProtocolType.MSGPACK
      return buildUrlWithProtocol(ProtocolType.MSGPACK)
    } else {
      console.log('[WebSocket] 使用JSON协议连接')
      currentProtocol.value = ProtocolType.JSON
      return buildUrlWithProtocol(ProtocolType.JSON)
    }
  }

  /**
   * 建立WebSocket连接
   *
   * @description 创建新的WebSocket连接，设置事件监听器，
   *              连接成功后自动启动心跳检测和频率统计，
   *              支持协议协商和自动降级
   */
  function connect() {
    // 关闭已有连接
    if (ws) {
      ws.close()
    }

    // 更新连接状态
    updateConnectionState(
      reconnectAttempts.value > 0 
        ? ConnectionState.RECONNECTING 
        : ConnectionState.CONNECTING
    )

    // 协商协议并构建URL
    const wsUrl = negotiateProtocol()
    console.log(`[WebSocket] 连接URL: ${wsUrl}`)

    ws = new WebSocket(wsUrl)

    // 设置二进制类型为arraybuffer
    ws.binaryType = 'arraybuffer'

    // 连接成功事件
    ws.onopen = async () => {
      updateConnectionState(ConnectionState.CONNECTED)
      isProtocolNegotiating.value = false
      
      // 重置重连计数器
      reconnectAttempts.value = 0
      maxReconnectReached.value = false
      
      // 重置心跳超时计数
      heartbeatTimeoutCount.value = 0
      
      // 重置错误计数
      errorCount.value = 0
      
      startHeartbeat()
      startFrequencyMonitor()
      startConnectionMonitor()
      
      // 刷新消息队列
      if (enableMessageQueue && messageQueue.value.length > 0) {
        console.log(`[WebSocket] 刷新消息队列: ${messageQueue.value.length} 条`)
        await flushMessageQueue()
      }
      
      // 请求服务器同步数据
      if (enableAutoSync && reconnectAttempts.value > 0) {
        await requestSync()
      }
      
      onOpen?.()
      
      console.log(`[WebSocket] 连接成功，当前协议: ${currentProtocol.value}`)
    }

    // 消息接收事件
    ws.onmessage = async (event) => {
      try {
        const data = await deserializeMessage(event.data)
        
        // 更新消息统计
        messageCount.value++
        lastMessageTime.value = Date.now()
        
        // 计算延迟（如果消息包含时间戳）
        if (data.timestamp) {
          const msgTime = new Date(data.timestamp).getTime()
          if (!isNaN(msgTime)) {
            dataLatency.value = Date.now() - msgTime
          }
        }
        
        // 处理心跳响应
        if (data.type === 'pong') {
          handlePong()
          return
        }

        // 处理同步完成消息
        if (data.type === 'sync_complete') {
          console.log('[WebSocket] 数据同步完成:', data)
          if (window.__wsSyncHandler) {
            window.__wsSyncHandler(data)
            delete window.__wsSyncHandler
          }
          return
        }

        // 处理订阅确认
        if (data.type === 'subscription_confirmed') {
          console.log('[WebSocket] 订阅确认:', data.subscribed_types)
          return
        }
        
        // 消息去重检查
        if (isDuplicateMessage(data)) {
          return
        }
        
        // 高频消息优化处理
        if (handleHighFrequencyMessage(data)) {
          return
        }
        
        onMessage?.(data)
      } catch (e) {
        console.error('[WebSocket] 消息解析错误:', e)
        
        // 记录错误
        classifyError(e, WSErrorType.MESSAGE_PARSE_ERROR, {
          rawData: event.data?.slice?.(0, 100)
        })
        
        // 如果是MessagePack解码失败，考虑降级
        if (currentProtocol.value === ProtocolType.MSGPACK && enableProtocolFallback) {
          fallbackToJSON()
        }
      }
    }

    // 连接关闭事件
    ws.onclose = (event) => {
      updateConnectionState(ConnectionState.DISCONNECTED)
      stopHeartbeat()
      stopFrequencyMonitor()
      stopConnectionMonitor()
      stopHighFrequencyProcessing()
      
      // 分类错误
      let errorType = WSErrorType.CONNECTION_ERROR
      if (event.code === 1002 || event.code === 1003) {
        errorType = WSErrorType.PROTOCOL_ERROR
      } else if (event.code === 1008) {
        errorType = WSErrorType.AUTH_FAILED
      } else if (event.code === 1011) {
        errorType = WSErrorType.SERVER_ERROR
      }
      
      // 记录错误
      if (event.code !== 1000) {
        classifyError(new Error(`连接关闭: ${event.reason || '未知原因'}`), errorType, {
          code: event.code,
          reason: event.reason,
          wasClean: event.wasClean
        })
      }
      
      // 检查是否是协议不支持导致的关闭
      if (event.code === 1002 || event.code === 1003) {
        console.warn('[WebSocket] 协议错误，尝试降级')
        if (enableProtocolFallback && currentProtocol.value === ProtocolType.MSGPACK) {
          fallbackToJSON()
        }
      }
      
      scheduleReconnect()
      onClose?.({
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean,
        errorType
      })
    }

    // 错误事件
    ws.onerror = (error) => {
      console.error('[WebSocket] 错误:', error)
      
      // 分类错误
      const errorInfo = classifyError(error, WSErrorType.NETWORK_ERROR, {
        protocol: currentProtocol.value
      })
      
      // MessagePack协议错误时降级
      if (currentProtocol.value === ProtocolType.MSGPACK && enableProtocolFallback) {
        console.warn('[WebSocket] MessagePack协议错误，准备降级')
        // 不立即降级，等待onclose事件处理
      }
      
      onError?.(errorInfo)
    }
  }

  /**
   * 断开WebSocket连接
   *
   * @description 关闭连接并清理所有定时器，停止重连尝试
   */
  function disconnect() {
    stopReconnect()
    stopHeartbeat()
    stopFrequencyMonitor()
    stopProtocolNegotiate()
    stopConnectionMonitor()
    stopHighFrequencyProcessing()
    if (ws) {
      ws.close()
      ws = null
    }
    updateConnectionState(ConnectionState.DISCONNECTED)
    reconnectAttempts.value = 0
    maxReconnectReached.value = false
    isProtocolNegotiating.value = false
    isSyncing = false
    waitingForPong = false
    
    // 清理去重缓存
    messageDedupCache.value.clear()
    dedupHitCount.value = 0
    
    // 清理高频消息缓冲区
    highFrequencyBuffer.value = []
  }

  /**
   * 重新连接
   *
   * @description 断开当前连接并重新建立连接
   */
  function reconnect() {
    if (ws) {
      ws.close()
      ws = null
    }
    updateConnectionState(ConnectionState.DISCONNECTED)
    connect()
  }

  /**
   * 发送消息
   *
   * @param {Object} data - 要发送的数据对象
   * @param {Object} options - 发送选项
   * @param {boolean} [options.queue=true] - 断线时是否加入队列
   * @returns {boolean} 发送是否成功
   *
   * @example
   * ```javascript
   * send({ type: 'ping' })
   * send({ type: 'command', action: 'start', params: { speed: 100 } })
   * send({ type: 'important' }, { queue: true }) // 断线时缓存
   * ```
   */
  function send(data, options = {}) {
    const { queue = true } = options
    
    if (ws && wsConnected.value) {
      try {
        const serialized = serializeMessage(data)
        
        // 根据协议类型选择发送方式
        if (serialized instanceof ArrayBuffer) {
          ws.send(serialized)
        } else {
          ws.send(serialized)
        }
        
        return true
      } catch (error) {
        console.error('[WebSocket] 发送消息失败:', error)
        
        // 发送失败，加入队列
        if (queue && enableMessageQueue) {
          enqueueMessage(data)
        }
        
        return false
      }
    } else {
      // 未连接时，加入队列
      if (queue && enableMessageQueue) {
        enqueueMessage(data)
        console.log('[WebSocket] 未连接，消息已加入队列')
      }
      
      return false
    }
  }

  /**
   * 发送订阅请求
   *
   * @param {Array<string>} messageTypes - 要订阅的消息类型列表
   * @returns {boolean} 发送是否成功
   *
   * @example
   * ```javascript
   * subscribe(['device_status', 'waveform_data'])
   * ```
   */
  function subscribe(messageTypes) {
    return send({
      action: 'subscribe',
      types: messageTypes
    })
  }

  /**
   * 取消订阅
   *
   * @param {Array<string>} messageTypes - 要取消订阅的消息类型列表
   * @returns {boolean} 发送是否成功
   */
  function unsubscribe(messageTypes) {
    return send({
      action: 'unsubscribe',
      types: messageTypes
    })
  }

  /**
   * 安排重连任务
   *
   * @description 在连接断开后，延迟指定时间后尝试重新连接
   *              支持多种重连策略（固定、线性、指数退避、斐波那契）
   * @internal 内部方法，不对外暴露
   */
  function scheduleReconnect() {
    // 检查是否已达到最大重连次数
    if (reconnectAttempts.value >= maxReconnectAttempts) {
      maxReconnectReached.value = true
      updateConnectionState(ConnectionState.RECONNECT_FAILED)
      
      // 记录重连失败错误
      const errorInfo = classifyError(
        new Error(`已达到最大重连次数 ${maxReconnectAttempts}`),
        WSErrorType.RECONNECT_FAILED,
        { attempts: reconnectAttempts.value }
      )
      
      console.warn(`[WebSocket] 已达到最大重连次数 ${maxReconnectAttempts}，停止重连`)
      return
    }

    if (reconnectTimer) return

    // 使用配置的重连策略计算延迟
    const delay = calculateReconnectDelay(reconnectAttempts.value + 1)
    
    reconnectAttempts.value++

    // 更新状态为重连中
    updateConnectionState(ConnectionState.RECONNECTING)

    // 触发重连进度回调
    onReconnecting?.({
      attempt: reconnectAttempts.value,
      maxAttempts: maxReconnectAttempts,
      delay: Math.round(delay),
      nextRetryAt: Date.now() + delay,
      strategy: reconnectStrategy
    })

    console.log(`[WebSocket] ${reconnectAttempts.value}/${maxReconnectAttempts} 次重连 (${reconnectStrategy})，延迟 ${Math.round(delay)}ms`)

    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      connect()
    }, delay)
  }

  /**
   * 停止重连任务
   *
   * @description 清除重连定时器，停止自动重连
   * @internal 内部方法，不对外暴露
   */
  function stopReconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  /**
   * 停止协议协商定时器
   *
   * @internal 内部方法，不对外暴露
   */
  function stopProtocolNegotiate() {
    if (protocolNegotiateTimer) {
      clearTimeout(protocolNegotiateTimer)
      protocolNegotiateTimer = null
    }
  }

  /**
   * 启动心跳检测
   *
   * @description 定时发送ping消息保持连接活跃，带超时检测
   * @internal 内部方法，不对外暴露
   */
  function startHeartbeat() {
    stopHeartbeat()
    
    heartbeatTimer = setInterval(() => {
      if (waitingForPong) {
        // 上一次心跳未收到响应
        heartbeatTimeoutCount.value++
        console.warn(`[WebSocket] 心跳超时 (${heartbeatTimeoutCount.value}次)`)
        
        // 连续超时3次，认为连接已断开
        if (heartbeatTimeoutCount.value >= 3) {
          console.error('[WebSocket] 心跳连续超时，断开连接')
          ws?.close()
          return
        }
      }
      
      // 发送心跳
      send({ type: 'ping' }, { queue: false })
      lastHeartbeatTime.value = Date.now()
      waitingForPong = true
      
      // 设置心跳超时定时器
      heartbeatTimeoutTimer = setTimeout(() => {
        if (waitingForPong) {
          console.warn('[WebSocket] 心跳响应超时')
        }
      }, heartbeatTimeout)
      
    }, heartbeatInterval)
  }

  /**
   * 处理心跳响应
   *
   * @description 收到pong消息时调用，重置心跳状态
   * @internal 内部方法，不对外暴露
   */
  function handlePong() {
    waitingForPong = false
    lastPongTime.value = Date.now()
    
    // 清除超时定时器
    if (heartbeatTimeoutTimer) {
      clearTimeout(heartbeatTimeoutTimer)
      heartbeatTimeoutTimer = null
    }
    
    // 计算心跳延迟
    if (lastHeartbeatTime.value) {
      const latency = lastPongTime.value - lastHeartbeatTime.value
      console.log(`[WebSocket] 心跳延迟: ${latency}ms`)
    }
  }

  /**
   * 停止心跳检测
   *
   * @description 清除心跳定时器和超时定时器
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
    waitingForPong = false
  }

  /**
   * 启动频率监控
   *
   * @description 每秒统计一次消息接收频率
   * @internal 内部方法，不对外暴露
   */
  function startFrequencyMonitor() {
    if (!enableFrequencyControl) return
    
    stopFrequencyMonitor()
    messageCount.value = 0
    frequencyTimer = setInterval(() => {
      pushFrequency.value = messageCount.value
      messageCount.value = 0
    }, 1000)
    
    // 订阅频率变更，通知服务器
    if (frequencyControl) {
      frequencyUnsubscribe = frequencyControl.onFrequencyChange((info) => {
        sendFrequencyUpdate(info)
      })
    }
  }

  /**
   * 停止频率监控
   *
   * @description 清除频率统计定时器
   * @internal 内部方法，不对外暴露
   */
  function stopFrequencyMonitor() {
    if (frequencyTimer) {
      clearInterval(frequencyTimer)
      frequencyTimer = null
    }
    if (frequencyUnsubscribe) {
      frequencyUnsubscribe()
      frequencyUnsubscribe = null
    }
    messageCount.value = 0
    pushFrequency.value = 0
  }

  /**
   * 发送频率更新到服务器
   *
   * @param {Object} info - 频率信息
   * @internal 内部方法，不对外暴露
   */
  function sendFrequencyUpdate(info) {
    if (wsConnected.value) {
      send({
        type: 'frequency_update',
        mode: info.mode,
        interval: info.frequency
      })
    }
  }

  /**
   * 设置推送频率模式
   *
   * @param {string} mode - 推送模式
   */
  function setPushMode(mode) {
    if (frequencyControl) {
      frequencyControl.setMode(mode)
    }
  }

  /**
   * 设置自定义推送频率
   *
   * @param {number} frequency - 频率值（毫秒）
   */
  function setCustomPushFrequency(frequency) {
    if (frequencyControl) {
      frequencyControl.setCustomFrequency(frequency)
    }
  }

  /**
   * 手动重连
   *
   * @description 重置重连计数器并尝试重新连接
   */
  function manualReconnect() {
    // 重置重连状态
    reconnectAttempts.value = 0
    maxReconnectReached.value = false
    heartbeatTimeoutCount.value = 0
    stopReconnect()
    // 断开现有连接
    if (ws) {
      ws.close()
      ws = null
    }
    // 重新连接
    connect()
  }

  /**
   * 重置重连状态
   *
   * @description 清除重连计数器，允许再次自动重连
   */
  function resetReconnect() {
    reconnectAttempts.value = 0
    maxReconnectReached.value = false
    heartbeatTimeoutCount.value = 0
    stopReconnect()
  }

  /**
   * 手动切换协议
   *
   * @param {string} protocol - 目标协议类型
   */
  function switchProtocol(protocol) {
    if (protocol === currentProtocol.value) {
      return
    }

    console.log(`[WebSocket] 手动切换协议: ${currentProtocol.value} -> ${protocol}`)
    
    // 更新协议（在断开连接前设置，这样重连时会使用新协议）
    currentProtocol.value = protocol
    isManualProtocolSwitch.value = true // 标记为手动切换
    
    // 如果已连接，先断开再重新连接
    if (wsConnected.value || wsConnecting.value) {
      // 关闭当前连接
      if (ws) {
        ws.onclose = null // 防止触发重连
        ws.close()
        ws = null
      }
      updateConnectionState(ConnectionState.DISCONNECTED)
      
      // 重新连接（会使用上面设置的 currentProtocol）
      connect()
    }
  }

  /**
   * 获取连接统计信息
   *
   * @returns {Object} 连接统计信息
   */
  function getConnectionStats() {
    return {
      // 连接状态
      connectionState: connectionState.value,
      connected: wsConnected.value,
      connecting: wsConnecting.value,
      
      // 协议信息
      protocol: currentProtocol.value,
      protocolSupported: protocolSupported.value,
      fallbackCount: protocolFallbackCount.value,
      
      // 重连信息
      reconnectAttempts: reconnectAttempts.value,
      maxReconnectReached: maxReconnectReached.value,
      reconnectStrategy,
      
      // 性能指标
      pushFrequency: pushFrequency.value,
      dataLatency: dataLatency.value,
      lastMessageTime: lastMessageTime.value,
      connectionQuality: connectionQuality.value,
      
      // 心跳信息
      lastHeartbeatTime: lastHeartbeatTime.value,
      lastPongTime: lastPongTime.value,
      heartbeatTimeoutCount: heartbeatTimeoutCount.value,
      
      // 消息队列
      queueLength: queueLength.value,
      queueFull: queueFull.value,
      
      // 消息去重统计
      dedupStats: {
        enabled: enableMessageDedup,
        cacheSize: messageDedupCache.value.size,
        hitCount: dedupHitCount.value
      },
      
      // 高频消息统计
      highFrequencyStats: {
        enabled: enableHighFrequencyOptimization,
        bufferSize: highFrequencyBuffer.value.length,
        isProcessing: isProcessingHighFrequency.value
      },
      
      // 错误统计
      errorStats: {
        count: errorCount.value,
        lastError: lastError.value,
        historyLength: errorHistory.value.length
      },
      
      // 连接历史
      connectionHistoryLength: connectionHistory.value.length
    }
  }

  /**
   * 检查连接健康状态
   *
   * @returns {Object} 健康状态报告
   */
  function checkHealth() {
    const stats = getConnectionStats()
    const issues = []
    
    // 检查连接状态
    if (!stats.connected) {
      issues.push({
        level: 'error',
        message: 'WebSocket未连接',
        suggestion: '检查网络连接或调用connect()方法'
      })
    }
    
    // 检查心跳
    if (stats.connected && stats.heartbeatTimeoutCount > 0) {
      issues.push({
        level: 'warning',
        message: `心跳超时 ${stats.heartbeatTimeoutCount} 次`,
        suggestion: '网络可能不稳定，考虑检查网络质量'
      })
    }
    
    // 检查延迟
    if (stats.dataLatency > 1000) {
      issues.push({
        level: 'warning',
        message: `数据延迟过高: ${stats.dataLatency}ms`,
        suggestion: '服务器响应缓慢，考虑优化后端性能'
      })
    }
    
    // 检查消息队列
    if (stats.queueLength > 50) {
      issues.push({
        level: 'warning',
        message: `消息队列积压: ${stats.queueLength} 条`,
        suggestion: '消息发送速度超过处理速度，考虑增加处理频率'
      })
    }
    
    // 检查连接质量
    if (stats.connected && stats.connectionQuality < 60) {
      issues.push({
        level: 'warning',
        message: `连接质量较差: ${stats.connectionQuality}分`,
        suggestion: '综合指标显示连接不稳定，建议检查网络环境'
      })
    }
    
    return {
      healthy: issues.filter(i => i.level === 'error').length === 0,
      score: stats.connectionQuality,
      issues,
      stats
    }
  }

  // 组件卸载时自动清理资源
  onUnmounted(() => {
    disconnect()
    // 清理临时监听器
    if (window.__wsSyncHandler) {
      delete window.__wsSyncHandler
    }
  })

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
    lastMessageTime,
    messageCount,
    connectionQuality,
    
    // === 心跳状态 ===
    lastHeartbeatTime,
    lastPongTime,
    heartbeatTimeoutCount,
    
    // === 消息队列 ===
    messageQueue,
    queueLength,
    queueFull,
    
    // === 频率控制 ===
    frequencyControl,
    currentPushMode: frequencyControl?.currentMode,
    currentPushFrequency: frequencyControl?.currentFrequency,
    
    // === 协议相关 ===
    currentProtocol,
    protocolSupported,
    protocolFallbackCount,
    isProtocolNegotiating,
    
    // === 消息去重 ===
    messageDedupCache,
    dedupHitCount,
    
    // === 高频消息优化 ===
    highFrequencyBuffer,
    isProcessingHighFrequency,
    
    // === 错误状态 ===
    lastError,
    errorCount,
    errorHistory,
    
    // === 连接历史 ===
    connectionHistory,
    
    // === 连接方法 ===
    connect,
    disconnect,
    reconnect,
    manualReconnect,
    resetReconnect,
    
    // === 消息方法 ===
    send,
    subscribe,
    unsubscribe,
    flushMessageQueue,
    clearMessageQueue,
    
    // === 频率控制方法 ===
    setPushMode,
    setCustomPushFrequency,
    
    // === 协议方法 ===
    switchProtocol,
    
    // === 监控方法 ===
    getConnectionStats,
    checkHealth,
    
    // === 错误处理方法 ===
    classifyError,
    getUserFriendlyErrorMessage,
    getErrorSuggestion,
    
    // === 枚举导出 ===
    ConnectionState,
    WSErrorType,
    ReconnectStrategy,
    ProtocolType
  }
}
