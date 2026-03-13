/**
 * @file useOnlineStatus.js
 * @path src/composables/
 * @description 在线状态检测组合式函数，提供网络连接状态监控、离线持续时间统计等功能
 * @author Agent
 * @date 2024-03-07
 * @dependencies vue
 */

import { ref, computed, onMounted, onUnmounted, readonly } from 'vue'

/**
 * 在线状态检测组合式函数
 *
 * @param {Object} options - 配置选项
 * @param {number} [options.checkInterval=30000] - 主动检测间隔（毫秒）
 * @param {string} [options.checkUrl='/api/health'] - 健康检查URL
 * @param {number} [options.timeout=5000] - 健康检查超时时间（毫秒）
 * @param {Function} [options.onOnline] - 上线回调
 * @param {Function} [options.onOffline] - 离线回调
 * @param {Function} [options.onStatusChange] - 状态变更回调
 * @returns {Object} 在线状态与相关方法
 *
 * @example
 * ```javascript
 * const { isOnline, isOffline, offlineDuration } = useOnlineStatus({
 *   onOnline: () => console.log('网络已恢复'),
 *   onOffline: () => console.log('网络已断开')
 * })
 *
 * // 检查在线状态
 * if (isOffline.value) {
 *   showToast('您当前处于离线状态')
 * }
 *
 * // 显示离线时长
 * console.log(`已离线 ${formattedOfflineDuration.value}`)
 * ```
 */
export function useOnlineStatus(options = {}) {
  const {
    checkInterval = 30000,
    checkUrl = '/api/health',
    timeout = 5000,
    onOnline,
    onOffline,
    onStatusChange
  } = options

  // === 响应式状态 ===
  /** 是否在线 */
  const isOnline = ref(navigator.onLine)
  /** 是否离线 */
  const isOffline = computed(() => !isOnline.value)
  /** 最后在线时间 */
  const lastOnlineTime = ref(isOnline.value ? new Date() : null)
  /** 最后离线时间 */
  const lastOfflineTime = ref(isOnline.value ? null : new Date())
  /** 离线持续时间（毫秒） */
  const offlineDuration = ref(0)
  /** 网络连接类型 */
  const connectionType = ref(getConnectionType())
  /** 下行速度（Mbps） */
  const downlinkSpeed = ref(getDownlinkSpeed())
  /** 网络质量评分 (0-100) */
  const networkQuality = ref(100)
  /** 是否正在进行健康检查 */
  const isChecking = ref(false)
  /** 上次健康检查时间 */
  const lastCheckTime = ref(null)
  /** 健康检查结果 */
  const lastCheckResult = ref(null)
  /** 网络状态历史 */
  const statusHistory = ref([])
  /** 最大历史记录数 */
  const MAX_HISTORY = 50

  // === 内部变量 ===
  let checkTimer = null
  let durationTimer = null

  /**
   * 获取连接类型
   *
   * @returns {string} 连接类型
   * @internal 内部方法，不对外暴露
   */
  function getConnectionType() {
    if (navigator.connection) {
      return navigator.connection.effectiveType || 'unknown'
    }
    return 'unknown'
  }

  /**
   * 获取下行速度
   *
   * @returns {number} 下行速度（Mbps）
   * @internal 内部方法，不对外暴露
   */
  function getDownlinkSpeed() {
    if (navigator.connection && navigator.connection.downlink) {
      return navigator.connection.downlink
    }
    return 0
  }

  /**
   * 更新网络信息
   *
   * @internal 内部方法，不对外暴露
   */
  function updateNetworkInfo() {
    connectionType.value = getConnectionType()
    downlinkSpeed.value = getDownlinkSpeed()

    // 计算网络质量评分
    if (connectionType.value === '4g') {
      networkQuality.value = Math.min(100, downlinkSpeed.value * 10)
    } else if (connectionType.value === '3g') {
      networkQuality.value = 50
    } else if (connectionType.value === '2g') {
      networkQuality.value = 25
    } else if (connectionType.value === 'slow-2g') {
      networkQuality.value = 10
    } else {
      networkQuality.value = 100
    }
  }

  /**
   * 添加状态到历史记录
   *
   * @param {string} status - 状态类型
   * @internal 内部方法，不对外暴露
   */
  function addToHistory(status) {
    statusHistory.value.unshift({
      timestamp: new Date().toISOString(),
      status,
      connectionType: connectionType.value,
      downlinkSpeed: downlinkSpeed.value
    })

    // 限制历史记录数量
    if (statusHistory.value.length > MAX_HISTORY) {
      statusHistory.value = statusHistory.value.slice(0, MAX_HISTORY)
    }
  }

  /**
   * 处理上线事件
   */
  function handleOnline() {
    const wasOffline = !isOnline.value
    isOnline.value = true
    lastOnlineTime.value = new Date()

    if (wasOffline) {
      addToHistory('online')
      onOnline?.({
        offlineDuration: offlineDuration.value,
        lastOfflineTime: lastOfflineTime.value
      })
      onStatusChange?.({
        status: 'online',
        previousStatus: 'offline',
        offlineDuration: offlineDuration.value
      })
    }

    // 停止离线持续时间计时
    stopDurationTimer()

    // 重置离线持续时间
    offlineDuration.value = 0

    // 更新网络信息
    updateNetworkInfo()

    // 启动健康检查
    startHealthCheck()
  }

  /**
   * 处理离线事件
   */
  function handleOffline() {
    const wasOnline = isOnline.value
    isOnline.value = false
    lastOfflineTime.value = new Date()

    if (wasOnline) {
      addToHistory('offline')
      onOffline?.({
        lastOnlineTime: lastOnlineTime.value
      })
      onStatusChange?.({
        status: 'offline',
        previousStatus: 'online'
      })
    }

    // 启动离线持续时间计时
    startDurationTimer()

    // 停止健康检查
    stopHealthCheck()
  }

  /**
   * 启动离线持续时间计时
   *
   * @internal 内部方法，不对外暴露
   */
  function startDurationTimer() {
    stopDurationTimer()
    durationTimer = setInterval(() => {
      if (lastOfflineTime.value) {
        offlineDuration.value = Date.now() - lastOfflineTime.value.getTime()
      }
    }, 1000)
  }

  /**
   * 停止离线持续时间计时
   *
   * @internal 内部方法，不对外暴露
   */
  function stopDurationTimer() {
    if (durationTimer) {
      clearInterval(durationTimer)
      durationTimer = null
    }
  }

  /**
   * 执行健康检查
   *
   * @returns {Promise<Object>} 检查结果
   */
  async function performHealthCheck() {
    if (isChecking.value) {
      return lastCheckResult.value
    }

    isChecking.value = true
    lastCheckTime.value = new Date()

    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), timeout)

      const response = await fetch(checkUrl, {
        method: 'HEAD',
        mode: 'no-cors',
        signal: controller.signal
      })

      clearTimeout(timeoutId)

      lastCheckResult.value = {
        success: true,
        timestamp: lastCheckTime.value,
        status: response.status || 200
      }

      return lastCheckResult.value
    } catch (error) {
      lastCheckResult.value = {
        success: false,
        timestamp: lastCheckTime.value,
        error: error.message
      }

      return lastCheckResult.value
    } finally {
      isChecking.value = false
    }
  }

  /**
   * 启动定期健康检查
   *
   * @internal 内部方法，不对外暴露
   */
  function startHealthCheck() {
    stopHealthCheck()
    checkTimer = setInterval(() => {
      if (isOnline.value) {
        performHealthCheck()
      }
    }, checkInterval)
  }

  /**
   * 停止健康检查
   *
   * @internal 内部方法，不对外暴露
   */
  function stopHealthCheck() {
    if (checkTimer) {
      clearInterval(checkTimer)
      checkTimer = null
    }
  }

  /**
   * 格式化离线持续时间
   */
  const formattedOfflineDuration = computed(() => {
    const ms = offlineDuration.value
    if (ms === 0) return '0秒'

    const seconds = Math.floor(ms / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)

    if (days > 0) {
      return `${days}天 ${hours % 24}小时`
    }
    if (hours > 0) {
      return `${hours}小时 ${minutes % 60}分钟`
    }
    if (minutes > 0) {
      return `${minutes}分钟 ${seconds % 60}秒`
    }
    return `${seconds}秒`
  })

  /**
   * 网络质量等级
   */
  const networkQualityLevel = computed(() => {
    const quality = networkQuality.value
    if (quality >= 80) return 'excellent'
    if (quality >= 60) return 'good'
    if (quality >= 40) return 'fair'
    if (quality >= 20) return 'poor'
    return 'very-poor'
  })

  /**
   * 网络质量标签
   */
  const networkQualityLabel = computed(() => {
    const level = networkQualityLevel.value
    const labels = {
      'excellent': '优秀',
      'good': '良好',
      'fair': '一般',
      'poor': '较差',
      'very-poor': '很差'
    }
    return labels[level]
  })

  /**
   * 离线统计信息
   */
  const offlineStats = computed(() => {
    const offlineEvents = statusHistory.value.filter(s => s.status === 'offline')
    const totalOfflineCount = offlineEvents.length

    if (totalOfflineCount === 0) {
      return {
        totalOfflineCount: 0,
        averageOfflineDuration: 0,
        longestOfflineDuration: 0
      }
    }

    // 计算平均离线时长
    let totalDuration = 0
    let longestDuration = 0

    for (let i = 0; i < offlineEvents.length - 1; i++) {
      const offlineEvent = offlineEvents[i]
      const nextOnlineEvent = statusHistory.value.find(
        s => s.status === 'online' && s.timestamp > offlineEvent.timestamp
      )

      if (nextOnlineEvent) {
        const duration = new Date(nextOnlineEvent.timestamp) - new Date(offlineEvent.timestamp)
        totalDuration += duration
        longestDuration = Math.max(longestDuration, duration)
      }
    }

    return {
      totalOfflineCount,
      averageOfflineDuration: totalOfflineCount > 1 ? totalDuration / (totalOfflineCount - 1) : 0,
      longestOfflineDuration: longestDuration
    }
  })

  // === 生命周期 ===
  onMounted(() => {
    // 监听网络状态变化
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    // 监听网络连接信息变化
    if (navigator.connection) {
      navigator.connection.addEventListener('change', updateNetworkInfo)
    }

    // 初始化网络信息
    updateNetworkInfo()

    // 如果当前离线，启动持续时间计时
    if (!isOnline.value) {
      startDurationTimer()
    }

    // 启动健康检查
    if (isOnline.value) {
      startHealthCheck()
    }

    // 添加初始状态到历史
    addToHistory(isOnline.value ? 'online' : 'offline')
  })

  onUnmounted(() => {
    window.removeEventListener('online', handleOnline)
    window.removeEventListener('offline', handleOffline)

    if (navigator.connection) {
      navigator.connection.removeEventListener('change', updateNetworkInfo)
    }

    stopHealthCheck()
    stopDurationTimer()
  })

  return {
    // 状态
    isOnline: readonly(isOnline),
    isOffline,
    lastOnlineTime: readonly(lastOnlineTime),
    lastOfflineTime: readonly(lastOfflineTime),
    offlineDuration: readonly(offlineDuration),
    connectionType: readonly(connectionType),
    downlinkSpeed: readonly(downlinkSpeed),
    networkQuality: readonly(networkQuality),
    isChecking: readonly(isChecking),
    lastCheckTime: readonly(lastCheckTime),
    lastCheckResult: readonly(lastCheckResult),
    statusHistory: readonly(statusHistory),

    // 计算属性
    formattedOfflineDuration,
    networkQualityLevel,
    networkQualityLabel,
    offlineStats,

    // 方法
    performHealthCheck
  }
}

/**
 * 网络连接类型枚举
 */
export const CONNECTION_TYPES = {
  WIFI: 'wifi',
  CELLULAR: 'cellular',
  ETHERNET: 'ethernet',
  UNKNOWN: 'unknown'
}

/**
 * 获取详细的网络连接信息
 *
 * @returns {Object} 网络连接信息
 */
export function getNetworkConnectionInfo() {
  const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection

  if (!connection) {
    return {
      available: false,
      type: CONNECTION_TYPES.UNKNOWN,
      effectiveType: 'unknown',
      downlink: 0,
      rtt: 0,
      saveData: false
    }
  }

  return {
    available: true,
    type: connection.type || CONNECTION_TYPES.UNKNOWN,
    effectiveType: connection.effectiveType || 'unknown',
    downlink: connection.downlink || 0,
    rtt: connection.rtt || 0,
    saveData: connection.saveData || false
  }
}

/**
 * 检查是否支持网络信息API
 *
 * @returns {boolean} 是否支持
 */
export function isNetworkInformationSupported() {
  return !!(navigator.connection || navigator.mozConnection || navigator.webkitConnection)
}
