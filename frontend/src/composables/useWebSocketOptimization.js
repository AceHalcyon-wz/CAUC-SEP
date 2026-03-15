/**
 * @file websocketOptimization.js
 * @path src/composables/
 * @description WebSocket数据优化组合式函数，集成节流、批量更新和数据聚合
 * @author Agent
 * @date 2024-03-08
 */

import { ref, onUnmounted } from 'vue'
import { 
  DataThrottler, 
  BatchUpdater, 
  DataAggregator,
  createStreamProcessor 
} from '@/utils/dataThrottle'

/**
 * WebSocket优化配置
 */
export const WS_OPTIMIZATION_CONFIG = {
  /** 默认节流间隔（毫秒） */
  defaultThrottleInterval: 100,
  /** 默认批量更新间隔（毫秒） */
  defaultBatchInterval: 50,
  /** 默认聚合窗口大小（毫秒） */
  defaultAggregateWindow: 1000,
  /** 默认最大批量大小 */
  defaultMaxBatchSize: 100,
  /** 高频消息类型 */
  highFrequencyTypes: [
    'waveform_data',
    'realtime_data',
    'sensor_data',
    'position_update',
    'streaming_data',
    'temperature_reading',
    'motor_position',
    'piezo_voltage'
  ]
}

/**
 * WebSocket数据优化组合式函数
 * 
 * @param {Object} options - 配置选项
 * @param {number} [options.throttleInterval] - 节流间隔
 * @param {number} [options.batchInterval] - 批量更新间隔
 * @param {number} [options.aggregateWindow] - 聚合窗口大小
 * @param {number} [options.maxBatchSize] - 最大批量大小
 * @param {boolean} [options.enableAggregation] - 是否启用聚合
 * @param {Array<string>} [options.highFrequencyTypes] - 高频消息类型
 * @returns {Object} 优化工具和方法
 */
export function useWebSocketOptimization(options = {}) {
  const config = {
    ...WS_OPTIMIZATION_CONFIG,
    ...options
  }

  // ==================== 响应式状态 ====================

  /** 是否启用优化 */
  const optimizationEnabled = ref(true)

  /** 节流统计 */
  const throttleStats = ref({
    totalMessages: 0,
    throttledMessages: 0,
    batchCount: 0,
    lastBatchSize: 0
  })

  /** 性能指标 */
  const performanceMetrics = ref({
    averageLatency: 0,
    maxLatency: 0,
    minLatency: Infinity,
    throughput: 0, // 消息/秒
    processingTime: 0
  })

  // ==================== 内部变量 ====================

  /** 数据节流器 */
  let throttler = null

  /** 批量更新器 */
  let batchUpdater = null

  /** 数据聚合器 */
  let aggregator = null

  /** 数据流处理器 */
  let streamProcessor = null

  /** 性能监控定时器 */
  let metricsTimer = null

  /** 消息计数器 */
  let messageCount = 0

  /** 延迟记录 */
  const latencyRecords = []

  /** 最大延迟记录数 */
  const MAX_LATENCY_RECORDS = 100

  // ==================== 初始化 ====================

  /**
   * 初始化优化器
   */
  function initOptimizers() {
    // 创建节流器
    throttler = new DataThrottler({
      interval: config.throttleInterval || config.defaultThrottleInterval,
      mode: 'throttle',
      maxBatchSize: config.maxBatchSize || config.defaultMaxBatchSize
    })

    // 创建批量更新器
    batchUpdater = new BatchUpdater({
      batchInterval: config.batchInterval || config.defaultBatchInterval,
      maxBatchSize: config.maxBatchSize || config.defaultMaxBatchSize
    })

    // 创建聚合器（可选）
    if (config.enableAggregation !== false) {
      aggregator = new DataAggregator({
        windowSize: config.aggregateWindow || config.defaultAggregateWindow,
        strategy: 'average'
      })
    }

    // 创建数据流处理器
    streamProcessor = createStreamProcessor({
      throttleInterval: config.throttleInterval || config.defaultThrottleInterval,
      batchInterval: config.batchInterval || config.defaultBatchInterval,
      maxBatchSize: config.maxBatchSize || config.defaultMaxBatchSize,
      aggregateWindow: config.aggregateWindow || config.defaultAggregateWindow,
      enableAggregation: config.enableAggregation !== false
    })

    // 启动性能监控
    startMetricsMonitoring()
  }

  /**
   * 启动性能监控
   */
  function startMetricsMonitoring() {
    if (metricsTimer) return

    const lastCount = messageCount
    metricsTimer = setInterval(() => {
      // 计算吞吐量
      performanceMetrics.value.throughput = messageCount - lastCount
      messageCount = lastCount

      // 计算平均延迟
      if (latencyRecords.length > 0) {
        performanceMetrics.value.averageLatency = 
          latencyRecords.reduce((a, b) => a + b, 0) / latencyRecords.length
        performanceMetrics.value.maxLatency = Math.max(...latencyRecords)
        performanceMetrics.value.minLatency = Math.min(...latencyRecords)
      }
    }, 1000)
  }

  /**
   * 停止性能监控
   */
  function stopMetricsMonitoring() {
    if (metricsTimer) {
      clearInterval(metricsTimer)
      metricsTimer = null
    }
  }

  // ==================== 消息处理 ====================

  /**
   * 处理WebSocket消息
   * 
   * @param {Object} message - WebSocket消息
   * @param {Function} callback - 处理回调
   */
  function processMessage(message, callback) {
    if (!optimizationEnabled.value) {
      callback(message)
      return
    }

    messageCount++
    throttleStats.value.totalMessages++

    // 计算延迟
    if (message.timestamp) {
      const latency = Date.now() - new Date(message.timestamp).getTime()
      recordLatency(latency)
    }

    // 判断是否为高频消息
    const isHighFrequency = isHighFrequencyMessage(message)

    if (isHighFrequency) {
      // 高频消息：使用节流和批量处理
      processHighFrequencyMessage(message, callback)
    } else {
      // 普通消息：直接处理
      callback(message)
    }
  }

  /**
   * 判断是否为高频消息
   * 
   * @param {Object} message - 消息对象
   * @returns {boolean} 是否为高频消息
   */
  function isHighFrequencyMessage(message) {
    const highFreqTypes = config.highFrequencyTypes || config.defaultHighFrequencyTypes
    return highFreqTypes.includes(message.type)
  }

  /**
   * 处理高频消息
   * 
   * @param {Object} message - 消息对象
   * @param {Function} callback - 处理回调
   */
  function processHighFrequencyMessage(message, callback) {
    throttleStats.value.throttledMessages++

    // 使用节流器处理
    if (throttler) {
      throttler.push(message)
      
      // 设置回调（只设置一次）
      if (!throttler.callback) {
        throttler.setCallback((batch) => {
          throttleStats.value.batchCount++
          throttleStats.value.lastBatchSize = batch.length
          
          // 批量处理
          processBatch(batch, callback)
        })
      }
    } else {
      // 降级：直接处理
      callback(message)
    }
  }

  /**
   * 批量处理消息
   * 
   * @param {Array} batch - 消息批次
   * @param {Function} callback - 处理回调
   */
  function processBatch(batch, callback) {
    const startTime = performance.now()

    // 按类型分组
    const grouped = groupMessagesByType(batch)

    // 合并同类型消息
    const merged = mergeMessages(grouped)

    // 执行回调
    callback({
      type: 'batch_update',
      data: merged,
      count: batch.length,
      timestamp: Date.now()
    })

    // 记录处理时间
    performanceMetrics.value.processingTime = performance.now() - startTime
  }

  /**
   * 按类型分组消息
   * 
   * @param {Array} messages - 消息数组
   * @returns {Object} 分组后的消息
   */
  function groupMessagesByType(messages) {
    return messages.reduce((groups, msg) => {
      const type = msg.type || 'unknown'
      if (!groups[type]) {
        groups[type] = []
      }
      groups[type].push(msg)
      return groups
    }, {})
  }

  /**
   * 合并消息
   * 
   * @param {Object} grouped - 分组的消息
   * @returns {Object} 合并后的消息
   */
  function mergeMessages(grouped) {
    const merged = {}

    Object.entries(grouped).forEach(([type, messages]) => {
      // 根据消息类型选择合并策略
      switch (type) {
        case 'waveform_data':
        case 'realtime_data':
          // 波形数据：保留最新的
          merged[type] = messages[messages.length - 1]
          break

        case 'sensor_data':
        case 'temperature_reading':
          // 传感器数据：计算平均值
          merged[type] = aggregateSensorData(messages)
          break

        case 'position_update':
        case 'motor_position':
          // 位置数据：保留最新位置
          merged[type] = messages[messages.length - 1]
          break

        default:
          // 默认：保留所有
          merged[type] = messages
      }
    })

    return merged
  }

  /**
   * 聚合传感器数据
   * 
   * @param {Array} messages - 传感器消息数组
   * @returns {Object} 聚合后的数据
   */
  function aggregateSensorData(messages) {
    if (messages.length === 0) return null
    if (messages.length === 1) return messages[0]

    // 提取数值
    const values = messages
      .map(m => m.data?.value || m.value)
      .filter(v => typeof v === 'number')

    if (values.length === 0) return messages[messages.length - 1]

    // 计算统计数据
    const sum = values.reduce((a, b) => a + b, 0)
    const avg = sum / values.length
    const max = Math.max(...values)
    const min = Math.min(...values)

    return {
      ...messages[messages.length - 1],
      aggregated: true,
      count: messages.length,
      statistics: {
        average: avg,
        max,
        min,
        sum
      }
    }
  }

  /**
   * 记录延迟
   * 
   * @param {number} latency - 延迟值（毫秒）
   */
  function recordLatency(latency) {
    latencyRecords.push(latency)
    
    // 限制记录数量
    if (latencyRecords.length > MAX_LATENCY_RECORDS) {
      latencyRecords.shift()
    }
  }

  // ==================== 配置方法 ====================

  /**
   * 设置节流间隔
   * 
   * @param {number} interval - 间隔（毫秒）
   */
  function setThrottleInterval(interval) {
    if (throttler) {
      throttler.options.interval = interval
    }
    if (streamProcessor) {
      streamProcessor.throttler.options.interval = interval
    }
  }

  /**
   * 设置批量更新间隔
   * 
   * @param {number} interval - 间隔（毫秒）
   */
  function setBatchInterval(interval) {
    if (batchUpdater) {
      batchUpdater.options.batchInterval = interval
    }
    if (streamProcessor) {
      streamProcessor.batchUpdater.options.batchInterval = interval
    }
  }

  /**
   * 启用/禁用优化
   * 
   * @param {boolean} enabled - 是否启用
   */
  function setOptimizationEnabled(enabled) {
    optimizationEnabled.value = enabled
  }

  /**
   * 刷新所有队列
   */
  function flush() {
    if (throttler) throttler.flush()
    if (batchUpdater) batchUpdater.flush()
    if (aggregator) aggregator.flush()
    if (streamProcessor) streamProcessor.flush()
  }

  /**
   * 清空所有队列
   */
  function clear() {
    if (throttler) throttler.clear()
    if (batchUpdater) batchUpdater.clear()
    if (aggregator) aggregator.clear()
    if (streamProcessor) streamProcessor.clear()
    
    latencyRecords.length = 0
    messageCount = 0
  }

  /**
   * 获取优化统计信息
   * 
   * @returns {Object} 统计信息
   */
  function getOptimizationStats() {
    return {
      enabled: optimizationEnabled.value,
      throttle: {
        ...throttleStats.value,
        queueLength: throttler?.queueLength || 0
      },
      performance: {
        ...performanceMetrics.value
      },
      batch: {
        pendingCount: batchUpdater?.pendingCount || 0
      }
    }
  }

  // ==================== 生命周期 ====================

  // 初始化
  initOptimizers()

  // 组件卸载时清理
  onUnmounted(() => {
    stopMetricsMonitoring()
    
    if (throttler) throttler.destroy()
    if (batchUpdater) batchUpdater.destroy()
    if (aggregator) aggregator.destroy()
    if (streamProcessor) streamProcessor.destroy()
  })

  // ==================== 返回值 ====================

  return {
    // 状态
    optimizationEnabled,
    throttleStats,
    performanceMetrics,

    // 方法
    processMessage,
    isHighFrequencyMessage,
    setThrottleInterval,
    setBatchInterval,
    setOptimizationEnabled,
    flush,
    clear,
    getOptimizationStats,

    // 内部实例（高级用法）
    throttler,
    batchUpdater,
    aggregator,
    streamProcessor
  }
}

export default useWebSocketOptimization
