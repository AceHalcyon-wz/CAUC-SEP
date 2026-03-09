/**
 * @file composables-usage-examples.js
 * @path src/composables/
 * @description 组合式函数使用示例，展示如何在实际组件中集成错误处理、进度指示和离线状态检测
 * @author Agent
 * @date 2024-03-07
 */

import { useErrorHandler, useProgress, useOnlineStatus, useWebSocketReconnect } from './index'
import { OPERATION_STATUS } from './useProgress'
import { RECONNECT_STRATEGY } from './useWebSocketReconnect'

/**
 * 示例1: 基础错误处理
 */
export function exampleBasicErrorHandling() {
  const { handleError, currentError, clearError, copyErrorInfo } = useErrorHandler({
    enableHistory: true,
    enableAutoReport: false
  })

  // 模拟一个可能失败的操作
  async function fetchData() {
    try {
      const response = await fetch('/api/data')
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      return await response.json()
    } catch (error) {
      const errorInfo = handleError(error, {
        component: 'DataComponent',
        action: 'fetchData',
        userMessage: '数据加载失败，请稍后重试'
      })
      console.log('错误解决方案:', errorInfo.solution.title)
      throw error
    }
  }

  return { fetchData, currentError, clearError, copyErrorInfo }
}

/**
 * 示例2: 操作进度管理
 */
export function exampleProgressManagement() {
  const {
    isRunning,
    progress,
    status,
    message,
    startOperation,
    updateProgress,
    completeOperation,
    failOperation,
    cancelOperation,
    formattedDuration,
    formattedEstimatedTime
  } = useProgress({
    autoResetDelay: 5000,
    enableAutoReset: true,
    onComplete: (info) => {
      console.log('操作完成:', info.name, '耗时:', info.duration)
    },
    onFail: (info) => {
      console.error('操作失败:', info.name, info.error)
    }
  })

  // 模拟数据采集操作
  async function collectData(totalPoints = 100) {
    const abortController = startOperation('数据采集', {
      total: totalPoints,
      description: '正在采集磁滞回线数据...',
      subtasks: [
        { name: '初始化设备', status: 'pending' },
        { name: '采集数据', status: 'pending' },
        { name: '处理数据', status: 'pending' }
      ]
    })

    try {
      // 子任务1: 初始化设备
      updateSubtask(0, 'running', '正在初始化设备...')
      await initializeDevice()
      updateSubtask(0, 'completed', '设备初始化完成')

      // 子任务2: 采集数据
      updateSubtask(1, 'running', '正在采集数据...')
      for (let i = 0; i < totalPoints; i++) {
        // 检查是否被取消
        if (abortController.signal.aborted) {
          throw new Error('Operation cancelled')
        }

        // 采集单个数据点
        await collectDataPoint(i)
        updateProgress((i + 1) / totalPoints * 100, `已采集 ${i + 1}/${totalPoints} 个数据点`)
      }
      updateSubtask(1, 'completed', '数据采集完成')

      // 子任务3: 处理数据
      updateSubtask(2, 'running', '正在处理数据...')
      await processData()
      updateSubtask(2, 'completed', '数据处理完成')

      completeOperation('数据采集成功完成')
    } catch (error) {
      if (error.message === 'Operation cancelled') {
        // 操作被用户取消
        return
      }
      failOperation(error, '数据采集失败')
    }
  }

  // 模拟函数
  async function initializeDevice() {
    await new Promise(resolve => setTimeout(resolve, 500))
  }

  async function collectDataPoint(index) {
    await new Promise(resolve => setTimeout(resolve, 50))
  }

  async function processData() {
    await new Promise(resolve => setTimeout(resolve, 300))
  }

  return {
    isRunning,
    progress,
    status,
    message,
    formattedDuration,
    formattedEstimatedTime,
    collectData,
    cancelOperation
  }
}

/**
 * 示例3: 离线状态检测
 */
export function exampleOnlineStatusDetection() {
  const {
    isOnline,
    isOffline,
    offlineDuration,
    formattedOfflineDuration,
    connectionType,
    networkQuality,
    networkQualityLabel,
    performHealthCheck,
    offlineStats
  } = useOnlineStatus({
    checkInterval: 15000,
    checkUrl: '/api/health',
    timeout: 3000,
    onOnline: (info) => {
      console.log('网络已恢复，离线时长:', info.offlineDuration)
      // 可以在这里重新连接WebSocket或重试失败的请求
    },
    onOffline: () => {
      console.log('网络已断开')
      // 可以在这里暂停实时数据推送
    },
    onStatusChange: (info) => {
      console.log('网络状态变更:', info.status)
    }
  })

  // 在发送请求前检查网络状态
  async function safeFetch(url, options) {
    if (isOffline.value) {
      throw new Error('当前处于离线状态，无法发送请求')
    }

    try {
      const response = await fetch(url, options)
      return response
    } catch (error) {
      // 如果请求失败，可能是网络问题，主动检查网络状态
      await performHealthCheck()
      throw error
    }
  }

  // 根据网络质量调整数据推送频率
  function getOptimalPushFrequency() {
    if (isOffline.value) return 0

    const quality = networkQuality.value
    if (quality >= 80) return 100 // 高质量网络：100ms
    if (quality >= 60) return 200 // 良好网络：200ms
    if (quality >= 40) return 500 // 一般网络：500ms
    return 1000 // 较差网络：1000ms
  }

  return {
    isOnline,
    isOffline,
    offlineDuration,
    formattedOfflineDuration,
    connectionType,
    networkQuality,
    networkQualityLabel,
    offlineStats,
    safeFetch,
    getOptimalPushFrequency,
    performHealthCheck
  }
}

/**
 * 示例4: WebSocket自动重连
 */
export function exampleWebSocketReconnect() {
  const {
    isConnected,
    isReconnecting,
    retryCount,
    connectionStatus,
    connectionStats,
    connect,
    disconnect,
    send,
    manualReconnect
  } = useWebSocketReconnect('ws://localhost:8000/ws', {
    maxRetries: 10,
    retryInterval: 1000,
    maxRetryInterval: 30000,
    strategy: RECONNECT_STRATEGY.EXPONENTIAL,
    heartbeatInterval: 30000,
    heartbeatTimeout: 5000,
    enableMessageQueue: true,
    maxQueueSize: 100,
    onMessage: (data) => {
      console.log('收到消息:', data)
      // 处理接收到的数据
      handleIncomingData(data)
    },
    onOpen: () => {
      console.log('WebSocket连接成功')
      // 连接成功后发送初始化消息
      send({ type: 'init', timestamp: Date.now() })
    },
    onClose: (event) => {
      console.log('WebSocket连接关闭:', event.code, event.reason)
    },
    onError: (error) => {
      console.error('WebSocket错误:', error)
    },
    onReconnecting: (info) => {
      console.log(`正在重连 (${info.attempt}/${info.maxAttempts})，${info.delay}ms后重试`)
    },
    onMaxRetriesReached: (info) => {
      console.error('已达到最大重连次数，请检查网络连接')
    }
  })

  // 处理接收到的数据
  function handleIncomingData(data) {
    switch (data.type) {
      case 'measurement':
        // 处理测量数据
        console.log('测量数据:', data.payload)
        break
      case 'status':
        // 处理状态更新
        console.log('状态更新:', data.status)
        break
      case 'error':
        // 处理服务器错误
        console.error('服务器错误:', data.message)
        break
      default:
        console.log('未知消息类型:', data.type)
    }
  }

  // 发送测量命令
  function startMeasurement(params) {
    send({
      type: 'command',
      action: 'start_measurement',
      params,
      timestamp: Date.now()
    })
  }

  // 停止测量
  function stopMeasurement() {
    send({
      type: 'command',
      action: 'stop_measurement',
      timestamp: Date.now()
    })
  }

  return {
    isConnected,
    isReconnecting,
    retryCount,
    connectionStatus,
    connectionStats,
    connect,
    disconnect,
    send,
    manualReconnect,
    startMeasurement,
    stopMeasurement
  }
}

/**
 * 示例5: 完整集成示例 - 数据采集组件
 */
export function useDataCollectionComponent() {
  // 初始化所有组合式函数
  const errorHandler = useErrorHandler({
    enableHistory: true,
    onReport: (report) => {
      // 可以在这里将错误报告发送到服务器
      console.log('错误报告:', report)
    }
  })

  const progress = useProgress({
    autoResetDelay: 3000,
    onComplete: () => {
      console.log('采集完成')
    }
  })

  const onlineStatus = useOnlineStatus({
    onOffline: () => {
      // 离线时暂停采集
      if (progress.isRunning.value) {
        progress.pauseOperation()
      }
    },
    onOnline: () => {
      // 恢复在线时继续采集
      if (progress.status.value === OPERATION_STATUS.PAUSED) {
        progress.resumeOperation()
      }
    }
  })

  const websocket = useWebSocketReconnect('ws://localhost:8000/ws', {
    onMessage: (data) => {
      if (data.type === 'measurement') {
        // 更新进度
        progress.updateProgress(
          data.progress,
          `正在采集: ${data.current}/${data.total}`
        )
      }
    }
  })

  /**
   * 开始数据采集
   */
  async function startCollection(params) {
    // 检查网络状态
    if (onlineStatus.isOffline.value) {
      errorHandler.handleError(
        new Error('当前处于离线状态，无法开始采集'),
        { component: 'DataCollection', action: 'startCollection' }
      )
      return
    }

    // 检查WebSocket连接
    if (!websocket.isConnected.value) {
      errorHandler.handleError(
        new Error('WebSocket未连接，请稍后重试'),
        { component: 'DataCollection', action: 'startCollection' }
      )
      return
    }

    try {
      // 开始进度跟踪
      const abortController = progress.startOperation('磁滞回线采集', {
        total: params.points || 100,
        description: '正在采集磁滞回线数据...'
      })

      // 发送采集命令
      websocket.send({
        type: 'command',
        action: 'start_measurement',
        params,
        timestamp: Date.now()
      })

      // 监听取消信号
      abortController.signal.addEventListener('abort', () => {
        websocket.send({
          type: 'command',
          action: 'stop_measurement',
          timestamp: Date.now()
        })
      })
    } catch (error) {
      errorHandler.handleError(error, {
        component: 'DataCollection',
        action: 'startCollection'
      })
      progress.failOperation(error)
    }
  }

  /**
   * 停止数据采集
   */
  function stopCollection() {
    if (progress.isRunning.value) {
      progress.cancelOperation('用户手动停止')
      websocket.send({
        type: 'command',
        action: 'stop_measurement',
        timestamp: Date.now()
      })
    }
  }

  return {
    // 错误处理
    currentError: errorHandler.currentError,
    errorVisible: errorHandler.errorVisible,
    clearError: errorHandler.clearError,

    // 进度管理
    isRunning: progress.isRunning,
    progress: progress.progress,
    status: progress.status,
    message: progress.message,
    formattedDuration: progress.formattedDuration,
    formattedEstimatedTime: progress.formattedEstimatedTime,

    // 网络状态
    isOnline: onlineStatus.isOnline,
    isOffline: onlineStatus.isOffline,
    networkQuality: onlineStatus.networkQuality,
    networkQualityLabel: onlineStatus.networkQualityLabel,

    // WebSocket状态
    isConnected: websocket.isConnected,
    isReconnecting: websocket.isReconnecting,
    retryCount: websocket.retryCount,

    // 操作方法
    startCollection,
    stopCollection,
    manualReconnect: websocket.manualReconnect
  }
}

/**
 * 使用建议：
 *
 * 1. 在组件中使用时，建议按照以下顺序初始化：
 *    - 先初始化错误处理（useErrorHandler）
 *    - 再初始化进度管理（useProgress）
 *    - 然后初始化网络状态（useOnlineStatus）
 *    - 最后初始化WebSocket（useWebSocketReconnect）
 *
 * 2. 错误处理最佳实践：
 *    - 为每个操作提供清晰的上下文信息
 *    - 使用用户友好的错误消息
 *    - 记录关键操作以便错误追踪
 *
 * 3. 进度管理最佳实践：
 *    - 为长时间操作提供进度反馈
 *    - 支持取消操作
 *    - 提供预计剩余时间
 *
 * 4. 离线状态最佳实践：
 *    - 在发送请求前检查网络状态
 *    - 根据网络质量调整应用行为
 *    - 提供离线缓存和同步机制
 *
 * 5. WebSocket最佳实践：
 *    - 使用消息队列处理离线期间的消息
 *    - 实现心跳机制保持连接活跃
 *    - 提供手动重连选项
 */
