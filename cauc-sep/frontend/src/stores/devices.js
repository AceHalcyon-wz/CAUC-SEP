/**
 * @file devices.js
 * @path src/stores/
 * @description 统一设备状态管理Store，聚合管理所有设备的连接状态、运行状态、健康状态和告警信息
 * @author Agent
 * @date 2024-03-07
 * @dependencies pinia, vue, composables, utils
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useWebSocket } from '../composables/useWebSocket'
import { get, post } from '../utils/apiRequest'
import { WS_BASE_URL } from '../config/api'

/**
 * 设备类型枚举
 * @constant {Object}
 */
const DEVICE_TYPES = {
  MOTOR: 'motor',
  ELECTROMAGNET: 'electromagnet',
  TEMPERATURE: 'temperature',
  PIEZO: 'piezo',
  AMMETER: 'ammeter'
}

/**
 * 设备显示名称映射
 * @constant {Object}
 */
const DEVICE_NAMES = {
  [DEVICE_TYPES.MOTOR]: '电机',
  [DEVICE_TYPES.ELECTROMAGNET]: '电磁铁',
  [DEVICE_TYPES.TEMPERATURE]: '温控器',
  [DEVICE_TYPES.PIEZO]: '压电陶瓷',
  [DEVICE_TYPES.AMMETER]: '电流表'
}

/**
 * 设备健康状态枚举
 * @constant {Object}
 */
const HEALTH_STATUS = {
  EXCELLENT: 'excellent',  // 优秀：设备运行完美
  GOOD: 'good',           // 良好：设备运行正常
  WARNING: 'warning',     // 警告：设备有潜在问题
  CRITICAL: 'critical',   // 严重：设备需要立即关注
  UNKNOWN: 'unknown'      // 未知：无法获取设备状态
}

/**
 * 健康状态中文映射
 * @constant {Object}
 */
const HEALTH_STATUS_TEXT = {
  [HEALTH_STATUS.EXCELLENT]: '优秀',
  [HEALTH_STATUS.GOOD]: '良好',
  [HEALTH_STATUS.WARNING]: '警告',
  [HEALTH_STATUS.CRITICAL]: '严重',
  [HEALTH_STATUS.UNKNOWN]: '未知'
}

/**
 * 健康状态类型映射（用于UI显示）
 * @constant {Object}
 */
const HEALTH_STATUS_TYPE = {
  [HEALTH_STATUS.EXCELLENT]: 'success',
  [HEALTH_STATUS.GOOD]: 'success',
  [HEALTH_STATUS.WARNING]: 'warning',
  [HEALTH_STATUS.CRITICAL]: 'danger',
  [HEALTH_STATUS.UNKNOWN]: 'info'
}

/**
 * 统一设备状态管理 Store
 *
 * 提供所有设备的聚合状态管理、实时状态推送和系统级状态监控
 */
export const useDevicesStore = defineStore('devices', () => {
  // ==================== 响应式状态 ====================

  /**
   * 设备状态映射表
   * @type {import('vue').Ref<Object>}
   * @description 存储所有设备的状态信息，key为设备ID，value包含status、isConnected、health、alarms等
   */
  const devices = ref({
    [DEVICE_TYPES.MOTOR]: {
      id: DEVICE_TYPES.MOTOR,
      name: DEVICE_NAMES[DEVICE_TYPES.MOTOR],
      status: 'disconnected',
      isConnected: false,
      lastUpdate: null,
      error: null,
      health: HEALTH_STATUS.UNKNOWN,
      healthScore: 0,
      metrics: {
        uptime: 0,
        errorCount: 0,
        warningCount: 0,
        lastErrorTime: null
      },
      alarms: []
    },
    [DEVICE_TYPES.ELECTROMAGNET]: {
      id: DEVICE_TYPES.ELECTROMAGNET,
      name: DEVICE_NAMES[DEVICE_TYPES.ELECTROMAGNET],
      status: 'disconnected',
      isConnected: false,
      lastUpdate: null,
      error: null,
      health: HEALTH_STATUS.UNKNOWN,
      healthScore: 0,
      metrics: {
        uptime: 0,
        errorCount: 0,
        warningCount: 0,
        lastErrorTime: null
      },
      alarms: []
    },
    [DEVICE_TYPES.TEMPERATURE]: {
      id: DEVICE_TYPES.TEMPERATURE,
      name: DEVICE_NAMES[DEVICE_TYPES.TEMPERATURE],
      status: 'disconnected',
      isConnected: false,
      lastUpdate: null,
      error: null,
      health: HEALTH_STATUS.UNKNOWN,
      healthScore: 0,
      metrics: {
        uptime: 0,
        errorCount: 0,
        warningCount: 0,
        lastErrorTime: null
      },
      alarms: []
    },
    [DEVICE_TYPES.PIEZO]: {
      id: DEVICE_TYPES.PIEZO,
      name: DEVICE_NAMES[DEVICE_TYPES.PIEZO],
      status: 'disconnected',
      isConnected: false,
      lastUpdate: null,
      error: null,
      health: HEALTH_STATUS.UNKNOWN,
      healthScore: 0,
      metrics: {
        uptime: 0,
        errorCount: 0,
        warningCount: 0,
        lastErrorTime: null
      },
      alarms: []
    },
    [DEVICE_TYPES.AMMETER]: {
      id: DEVICE_TYPES.AMMETER,
      name: DEVICE_NAMES[DEVICE_TYPES.AMMETER],
      status: 'disconnected',
      isConnected: false,
      lastUpdate: null,
      error: null,
      health: HEALTH_STATUS.UNKNOWN,
      healthScore: 0,
      metrics: {
        uptime: 0,
        errorCount: 0,
        warningCount: 0,
        lastErrorTime: null
      },
      alarms: []
    }
  })

  /**
   * 系统整体状态
   * @type {import('vue').Ref<string>}
   * @description 可能的值: 'normal' | 'warning' | 'error' | 'offline'
   */
  const systemStatus = ref('offline')

  /**
   * WebSocket连接状态
   * @type {import('vue').Ref<boolean>}
   */
  const wsConnected = ref(false)

  /**
   * 加载状态
   * @type {import('vue').Ref<boolean>}
   */
  const loading = ref(false)

  /**
   * 最后一次全量更新时间
   * @type {import('vue').Ref<number|null>}
   */
  const lastRefreshTime = ref(null)

  /**
   * 告警列表
   * @type {import('vue').Ref<Array>}
   * @description 存储所有设备的告警信息，按时间倒序排列
   */
  const alarms = ref([])

  /**
   * 未确认告警列表
   * @type {import('vue').ComputedRef<Array>}
   */
  const unacknowledgedAlarms = computed(() => {
    return alarms.value.filter(alarm => !alarm.acknowledged)
  })

  /**
   * 设备状态变更历史记录
   * @type {import('vue').Ref<Array>}
   * @description 存储设备状态变更历史，最多保留1000条记录
   */
  const statusHistory = ref([])

  /**
   * 最大历史记录数量
   * @constant {number}
   */
  const MAX_HISTORY_SIZE = 1000

  /**
   * 批量操作状态
   * @type {import('vue').Ref<Object>}
   */
  const batchOperation = ref({
    inProgress: false,
    type: null,  // 'connect' | 'disconnect'
    total: 0,
    completed: 0,
    succeeded: 0,
    failed: 0,
    errors: []
  })

  // ==================== 计算属性 ====================

  /**
   * 已连接设备列表
   * @type {import('vue').ComputedRef<Array>}
   */
  const connectedDevices = computed(() => {
    return Object.values(devices.value).filter(device => device.isConnected)
  })

  /**
   * 错误状态设备列表
   * @type {import('vue').ComputedRef<Array>}
   */
  const errorDevices = computed(() => {
    return Object.values(devices.value).filter(
      device => device.status === 'error' || device.error
    )
  })

  /**
   * 断开连接的设备列表
   * @type {import('vue').ComputedRef<Array>}
   */
  const disconnectedDevices = computed(() => {
    return Object.values(devices.value).filter(device => !device.isConnected)
  })

  /**
   * 是否所有设备都已连接
   * @type {import('vue').ComputedRef<boolean>}
   */
  const allConnected = computed(() => {
    return Object.values(devices.value).every(device => device.isConnected)
  })

  /**
   * 是否有设备处于错误状态
   * @type {import('vue').ComputedRef<boolean>}
   */
  const hasErrors = computed(() => {
    return errorDevices.value.length > 0
  })

  /**
   * 已连接设备数量
   * @type {import('vue').ComputedRef<number>}
   */
  const connectedCount = computed(() => {
    return connectedDevices.value.length
  })

  /**
   * 总设备数量
   * @type {import('vue').ComputedRef<number>}
   */
  const totalDevicesCount = computed(() => {
    return Object.keys(devices.value).length
  })

  /**
   * 系统状态描述文本
   * @type {import('vue').ComputedRef<string>}
   */
  const systemStatusText = computed(() => {
    switch (systemStatus.value) {
      case 'normal':
        return '系统正常'
      case 'warning':
        return '系统警告'
      case 'error':
        return '系统异常'
      case 'offline':
        return '系统离线'
      default:
        return '未知状态'
    }
  })

  /**
   * 系统状态类型（用于UI显示）
   * @type {import('vue').ComputedRef<string>}
   */
  const systemStatusType = computed(() => {
    switch (systemStatus.value) {
      case 'normal':
        return 'success'
      case 'warning':
        return 'warning'
      case 'error':
        return 'danger'
      case 'offline':
        return 'info'
      default:
        return 'info'
    }
  })

  /**
   * 系统整体健康状态
   * @type {import('vue').ComputedRef<string>}
   */
  const systemHealth = computed(() => {
    const deviceList = Object.values(devices.value)
    
    // 如果所有设备都离线，返回未知
    if (deviceList.every(d => !d.isConnected)) {
      return HEALTH_STATUS.UNKNOWN
    }
    
    // 计算已连接设备的平均健康分数
    const connectedDeviceList = deviceList.filter(d => d.isConnected)
    const avgHealthScore = connectedDeviceList.reduce((sum, d) => sum + (d.healthScore || 0), 0) / connectedDeviceList.length
    
    // 根据平均健康分数返回状态
    if (avgHealthScore >= 90) return HEALTH_STATUS.EXCELLENT
    if (avgHealthScore >= 70) return HEALTH_STATUS.GOOD
    if (avgHealthScore >= 50) return HEALTH_STATUS.WARNING
    return HEALTH_STATUS.CRITICAL
  })

  /**
   * 系统健康状态文本
   * @type {import('vue').ComputedRef<string>}
   */
  const systemHealthText = computed(() => {
    return HEALTH_STATUS_TEXT[systemHealth.value] || '未知'
  })

  /**
   * 系统健康状态类型
   * @type {import('vue').ComputedRef<string>}
   */
  const systemHealthType = computed(() => {
    return HEALTH_STATUS_TYPE[systemHealth.value] || 'info'
  })

  /**
   * 告警总数
   * @type {import('vue').ComputedRef<number>}
   */
  const totalAlarmsCount = computed(() => {
    return alarms.value.length
  })

  /**
   * 未确认告警数量
   * @type {import('vue').ComputedRef<number>}
   */
  const unacknowledgedAlarmsCount = computed(() => {
    return unacknowledgedAlarms.value.length
  })

  // ==================== WebSocket 管理 ====================

  /**
   * WebSocket消息处理函数
   *
   * @param {Object} data - WebSocket接收到的数据
   */
  function handleWebSocketMessage(data) {
    // 处理心跳消息
    if (data.type === 'ping' || data.ping) {
      devicesWS.send({ type: 'pong', timestamp: Date.now() })
      return
    }

    // 处理设备状态批量更新
    if (data.devices && Array.isArray(data.devices)) {
      updateDevicesStatus(data.devices)
      return
    }

    // 处理单个设备状态更新
    if (data.device_id && devices.value[data.device_id]) {
      updateDeviceStatus(data.device_id, data)
    }

    // 处理系统状态更新
    if (data.system_status) {
      systemStatus.value = data.system_status
    }

    // 处理错误消息
    if (data.error) {
      console.error('[DevicesStore] WebSocket error:', data.error)
    }
  }

  /**
   * WebSocket管理器实例
   */
  const devicesWS = useWebSocket({
    url: `${WS_BASE_URL}/ws/devices`,
    onMessage: handleWebSocketMessage,
    onOpen: () => {
      wsConnected.value = true
      console.log('[DevicesStore] WebSocket connected')
      // 连接成功后立即刷新所有设备状态
      fetchAllDeviceStatus()
    },
    onClose: () => {
      wsConnected.value = false
      console.log('[DevicesStore] WebSocket disconnected')
    },
    onError: (error) => {
      console.error('[DevicesStore] WebSocket error:', error)
    },
    reconnectInterval: 3000,
    heartbeatInterval: 30000
  })

  // ==================== 辅助方法 ====================

  /**
   * 更新单个设备状态
   *
   * @param {string} deviceId - 设备ID
   * @param {Object} data - 设备状态数据
   */
  function updateDeviceStatus(deviceId, data) {
    if (!devices.value[deviceId]) {
      console.warn(`[DevicesStore] Unknown device: ${deviceId}`)
      return
    }

    const device = devices.value[deviceId]
    const previousStatus = device.status
    const previousConnected = device.isConnected

    // 更新设备状态
    if (data.status !== undefined) {
      device.status = data.status
    }

    // 更新连接状态
    if (data.connected !== undefined) {
      device.isConnected = data.connected
    } else if (data.status !== undefined) {
      // 根据状态推断连接状态
      device.isConnected = ['ready', 'busy', 'running'].includes(data.status)
    }

    // 更新时间戳
    device.lastUpdate = data.timestamp || Date.now()

    // 更新错误信息
    if (data.error) {
      device.error = data.error
    } else if (data.status !== 'error') {
      device.error = null
    }

    // 更新健康状态
    if (data.health !== undefined) {
      device.health = data.health
    }
    
    // 更新健康分数
    if (data.healthScore !== undefined) {
      device.healthScore = data.healthScore
    } else {
      // 根据设备状态自动计算健康分数
      device.healthScore = calculateHealthScore(device)
      device.health = getHealthStatusFromScore(device.healthScore)
    }

    // 更新指标数据
    if (data.metrics) {
      device.metrics = { ...device.metrics, ...data.metrics }
    }

    // 处理告警信息
    if (data.alarms && Array.isArray(data.alarms)) {
      data.alarms.forEach(alarm => {
        addAlarm({
          deviceId,
          deviceName: device.name,
          ...alarm
        })
      })
    }

    // 记录状态变更历史
    if (previousStatus !== device.status || previousConnected !== device.isConnected) {
      addStatusHistory({
        deviceId,
        deviceName: device.name,
        previousStatus,
        currentStatus: device.status,
        previousConnected,
        currentConnected: device.isConnected,
        timestamp: device.lastUpdate
      })
    }

    // 更新系统整体状态
    updateSystemStatus()
  }

  /**
   * 计算设备健康分数
   *
   * @param {Object} device - 设备对象
   * @returns {number} 健康分数（0-100）
   */
  function calculateHealthScore(device) {
    if (!device.isConnected) return 0
    
    let score = 100
    
    // 根据设备状态扣分
    if (device.status === 'error') {
      score -= 50
    } else if (device.status === 'busy' || device.status === 'moving') {
      score -= 5
    }
    
    // 根据错误计数扣分
    if (device.metrics) {
      score -= Math.min(device.metrics.errorCount * 5, 30)
      score -= Math.min(device.metrics.warningCount * 2, 20)
    }
    
    // 根据告警数量扣分
    if (device.alarms && device.alarms.length > 0) {
      const activeAlarms = device.alarms.filter(a => !a.cleared)
      score -= Math.min(activeAlarms.length * 10, 30)
    }
    
    return Math.max(0, Math.min(100, score))
  }

  /**
   * 根据健康分数获取健康状态
   *
   * @param {number} score - 健康分数
   * @returns {string} 健康状态
   */
  function getHealthStatusFromScore(score) {
    if (score >= 90) return HEALTH_STATUS.EXCELLENT
    if (score >= 70) return HEALTH_STATUS.GOOD
    if (score >= 50) return HEALTH_STATUS.WARNING
    if (score > 0) return HEALTH_STATUS.CRITICAL
    return HEALTH_STATUS.UNKNOWN
  }

  /**
   * 批量更新设备状态
   *
   * @param {Array} deviceList - 设备状态列表
   */
  function updateDevicesStatus(deviceList) {
    deviceList.forEach(deviceData => {
      if (deviceData.device_id || deviceData.id) {
        const deviceId = deviceData.device_id || deviceData.id
        updateDeviceStatus(deviceId, deviceData)
      }
    })
    lastRefreshTime.value = Date.now()
  }

  /**
   * 更新系统整体状态
   *
   * @description 根据所有设备状态计算系统整体状态
   */
  function updateSystemStatus() {
    const deviceList = Object.values(devices.value)

    // 如果没有设备连接，系统离线
    if (deviceList.every(d => !d.isConnected)) {
      systemStatus.value = 'offline'
      return
    }

    // 如果有设备错误，系统异常
    if (hasErrors.value) {
      systemStatus.value = 'error'
      return
    }

    // 如果有设备断开连接，系统警告
    if (!allConnected.value) {
      systemStatus.value = 'warning'
      return
    }

    // 所有设备正常连接
    systemStatus.value = 'normal'
  }

  // ==================== API 方法 ====================

  /**
   * 获取所有设备状态
   *
   * @returns {Promise<Object|null>} 所有设备状态数据
   */
  async function fetchAllDeviceStatus() {
    loading.value = true

    const result = await get('/api/v1/device/status', null, {
      onError: (msg) => {
        console.error('[DevicesStore] Failed to fetch all device status:', msg)
      }
    })

    loading.value = false

    if (result.success && result.data) {
      // 处理返回的设备状态数据
      if (result.data.devices && Array.isArray(result.data.devices)) {
        updateDevicesStatus(result.data.devices)
      } else {
        // 兼容其他数据格式
        Object.keys(result.data).forEach(deviceId => {
          if (devices.value[deviceId]) {
            updateDeviceStatus(deviceId, result.data[deviceId])
          }
        })
      }

      // 更新系统状态
      if (result.data.system_status) {
        systemStatus.value = result.data.system_status
      }

      lastRefreshTime.value = Date.now()
      return result.data
    }

    return null
  }

  /**
   * 获取指定设备状态
   *
   * @param {string} deviceId - 设备ID
   * @returns {Promise<Object|null>} 设备状态数据
   */
  async function fetchDeviceStatus(deviceId) {
    if (!devices.value[deviceId]) {
      console.error(`[DevicesStore] Invalid device ID: ${deviceId}`)
      return null
    }

    const result = await get(`/api/v1/device/${deviceId}/status`, null, {
      onError: (msg) => {
        console.error(`[DevicesStore] Failed to fetch device ${deviceId} status:`, msg)
      }
    })

    if (result.success && result.data) {
      updateDeviceStatus(deviceId, result.data)
      return result.data
    }

    return null
  }

  /**
   * 刷新所有设备状态
   *
   * @returns {Promise<Object|null>} 刷新结果
   */
  async function refreshAll() {
    return await fetchAllDeviceStatus()
  }

  // ==================== 告警管理方法 ====================

  /**
   * 添加告警
   *
   * @param {Object} alarm - 告警信息
   */
  function addAlarm(alarm) {
    const alarmRecord = {
      id: `${alarm.deviceId}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      deviceId: alarm.deviceId,
      deviceName: alarm.deviceName || devices.value[alarm.deviceId]?.name || '未知设备',
      code: alarm.code || 0,
      message: alarm.message || '未知告警',
      severity: alarm.severity || 'warning',  // 'info' | 'warning' | 'error' | 'critical'
      timestamp: alarm.timestamp || Date.now(),
      acknowledged: false,
      acknowledgedBy: null,
      acknowledgedAt: null,
      cleared: false,
      clearedAt: null,
      ...alarm
    }
    
    alarms.value.unshift(alarmRecord)
    
    // 保持告警列表不超过500条
    if (alarms.value.length > 500) {
      alarms.value = alarms.value.slice(0, 500)
    }
  }

  /**
   * 确认告警
   *
   * @param {string} alarmId - 告警ID
   * @param {string} acknowledgedBy - 确认人
   * @returns {boolean} 是否成功
   */
  function acknowledgeAlarm(alarmId, acknowledgedBy = 'system') {
    const alarm = alarms.value.find(a => a.id === alarmId)
    if (alarm) {
      alarm.acknowledged = true
      alarm.acknowledgedBy = acknowledgedBy
      alarm.acknowledgedAt = Date.now()
      return true
    }
    return false
  }

  /**
   * 批量确认告警
   *
   * @param {Array<string>} alarmIds - 告警ID列表
   * @param {string} acknowledgedBy - 确认人
   * @returns {number} 成功确认的数量
   */
  function acknowledgeAlarms(alarmIds, acknowledgedBy = 'system') {
    let count = 0
    alarmIds.forEach(id => {
      if (acknowledgeAlarm(id, acknowledgedBy)) {
        count++
      }
    })
    return count
  }

  /**
   * 清除告警
   *
   * @param {string} alarmId - 告警ID
   * @returns {boolean} 是否成功
   */
  function clearAlarm(alarmId) {
    const alarm = alarms.value.find(a => a.id === alarmId)
    if (alarm) {
      alarm.cleared = true
      alarm.clearedAt = Date.now()
      return true
    }
    return false
  }

  /**
   * 清除设备的所有告警
   *
   * @param {string} deviceId - 设备ID
   * @returns {number} 清除的告警数量
   */
  function clearDeviceAlarms(deviceId) {
    let count = 0
    alarms.value.forEach(alarm => {
      if (alarm.deviceId === deviceId && !alarm.cleared) {
        alarm.cleared = true
        alarm.clearedAt = Date.now()
        count++
      }
    })
    return count
  }

  /**
   * 清除所有已确认的告警
   *
   * @returns {number} 清除的告警数量
   */
  function clearAcknowledgedAlarms() {
    const initialLength = alarms.value.length
    alarms.value = alarms.value.filter(alarm => !alarm.acknowledged || !alarm.cleared)
    return initialLength - alarms.value.length
  }

  // ==================== 历史记录方法 ====================

  /**
   * 添加状态变更历史记录
   *
   * @param {Object} record - 历史记录
   */
  function addStatusHistory(record) {
    const historyRecord = {
      id: `${record.deviceId}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      ...record,
      timestamp: record.timestamp || Date.now()
    }
    
    statusHistory.value.unshift(historyRecord)
    
    // 保持历史记录不超过最大数量
    if (statusHistory.value.length > MAX_HISTORY_SIZE) {
      statusHistory.value = statusHistory.value.slice(0, MAX_HISTORY_SIZE)
    }
  }

  /**
   * 查询设备状态历史
   *
   * @param {Object} options - 查询选项
   * @param {string} [options.deviceId] - 设备ID（可选，不指定则查询所有设备）
   * @param {number} [options.startTime] - 开始时间戳
   * @param {number} [options.endTime] - 结束时间戳
   * @param {number} [options.limit] - 返回记录数量限制
   * @returns {Array} 历史记录列表
   */
  function queryStatusHistory(options = {}) {
    let result = [...statusHistory.value]
    
    // 按设备ID过滤
    if (options.deviceId) {
      result = result.filter(r => r.deviceId === options.deviceId)
    }
    
    // 按时间范围过滤
    if (options.startTime) {
      result = result.filter(r => r.timestamp >= options.startTime)
    }
    if (options.endTime) {
      result = result.filter(r => r.timestamp <= options.endTime)
    }
    
    // 限制返回数量
    if (options.limit && options.limit > 0) {
      result = result.slice(0, options.limit)
    }
    
    return result
  }

  /**
   * 清除历史记录
   *
   * @param {number} beforeTimestamp - 清除此时间戳之前的记录
   */
  function clearStatusHistory(beforeTimestamp) {
    if (beforeTimestamp) {
      statusHistory.value = statusHistory.value.filter(r => r.timestamp >= beforeTimestamp)
    } else {
      statusHistory.value = []
    }
  }

  // ==================== 批量操作方法 ====================

  /**
   * 批量连接所有设备
   *
   * @returns {Promise<Object>} 操作结果
   */
  async function connectAllDevices() {
    batchOperation.value = {
      inProgress: true,
      type: 'connect',
      total: disconnectedDevices.value.length,
      completed: 0,
      succeeded: 0,
      failed: 0,
      errors: []
    }

    const results = []
    
    for (const device of disconnectedDevices.value) {
      try {
        const result = await post(`/device/${device.id}/connect`)
        
        if (result.success) {
          batchOperation.value.succeeded++
          updateDeviceStatus(device.id, {
            status: 'ready',
            connected: true,
            timestamp: Date.now()
          })
        } else {
          batchOperation.value.failed++
          batchOperation.value.errors.push({
            deviceId: device.id,
            deviceName: device.name,
            error: result.message || '连接失败'
          })
        }
        
        results.push({ deviceId: device.id, success: result.success, message: result.message })
      } catch (error) {
        batchOperation.value.failed++
        batchOperation.value.errors.push({
          deviceId: device.id,
          deviceName: device.name,
          error: error.message || '连接异常'
        })
        results.push({ deviceId: device.id, success: false, message: error.message })
      }
      
      batchOperation.value.completed++
    }

    batchOperation.value.inProgress = false
    
    return {
      success: batchOperation.value.failed === 0,
      total: batchOperation.value.total,
      succeeded: batchOperation.value.succeeded,
      failed: batchOperation.value.failed,
      errors: batchOperation.value.errors
    }
  }

  /**
   * 批量断开所有设备
   *
   * @returns {Promise<Object>} 操作结果
   */
  async function disconnectAllDevices() {
    batchOperation.value = {
      inProgress: true,
      type: 'disconnect',
      total: connectedDevices.value.length,
      completed: 0,
      succeeded: 0,
      failed: 0,
      errors: []
    }

    const results = []
    
    for (const device of connectedDevices.value) {
      try {
        const result = await post(`/device/${device.id}/disconnect`)
        
        if (result.success) {
          batchOperation.value.succeeded++
          updateDeviceStatus(device.id, {
            status: 'disconnected',
            connected: false,
            timestamp: Date.now()
          })
        } else {
          batchOperation.value.failed++
          batchOperation.value.errors.push({
            deviceId: device.id,
            deviceName: device.name,
            error: result.message || '断开失败'
          })
        }
        
        results.push({ deviceId: device.id, success: result.success, message: result.message })
      } catch (error) {
        batchOperation.value.failed++
        batchOperation.value.errors.push({
          deviceId: device.id,
          deviceName: device.name,
          error: error.message || '断开异常'
        })
        results.push({ deviceId: device.id, success: false, message: error.message })
      }
      
      batchOperation.value.completed++
    }

    batchOperation.value.inProgress = false
    
    return {
      success: batchOperation.value.failed === 0,
      total: batchOperation.value.total,
      succeeded: batchOperation.value.succeeded,
      failed: batchOperation.value.failed,
      errors: batchOperation.value.errors
    }
  }

  /**
   * 重置批量操作状态
   */
  function resetBatchOperation() {
    batchOperation.value = {
      inProgress: false,
      type: null,
      total: 0,
      completed: 0,
      succeeded: 0,
      failed: 0,
      errors: []
    }
  }

  // ==================== 连接配置管理 ====================

  /**
   * 设备连接配置映射表
   * @type {import('vue').Ref<Object>}
   */
  const connectionConfigs = ref({})

  /**
   * 配置模板列表
   * @type {import('vue').Ref<Array>}
   */
  const configTemplates = ref([])

  /**
   * 当前激活的配置
   * @type {import('vue').Ref<Object>}
   */
  const activeConfig = ref(null)

  /**
   * localStorage存储键名
   * @constant {string}
   */
  const STORAGE_KEY_CONFIGS = 'device_connection_configs'
  const STORAGE_KEY_TEMPLATES = 'device_config_templates'

  /**
   * 加载连接配置
   *
   * @param {string} deviceId - 设备ID
   * @returns {Object|null} 配置对象
   */
  function loadConnectionConfig(deviceId) {
    if (connectionConfigs.value[deviceId]) {
      return connectionConfigs.value[deviceId]
    }

    // 从localStorage加载
    try {
      const stored = localStorage.getItem(`${STORAGE_KEY_CONFIGS}_${deviceId}`)
      if (stored) {
        const config = JSON.parse(stored)
        connectionConfigs.value[deviceId] = config
        return config
      }
    } catch (error) {
      console.error(`[DevicesStore] Failed to load config for ${deviceId}:`, error)
    }

    return null
  }

  /**
   * 保存连接配置
   *
   * @param {string} deviceId - 设备ID
   * @param {Object} config - 配置对象
   * @returns {boolean} 是否成功
   */
  function saveConnectionConfig(deviceId, config) {
    try {
      const configToSave = {
        ...config,
        deviceId,
        updatedAt: Date.now()
      }

      connectionConfigs.value[deviceId] = configToSave

      // 持久化到localStorage
      localStorage.setItem(
        `${STORAGE_KEY_CONFIGS}_${deviceId}`,
        JSON.stringify(configToSave)
      )

      return true
    } catch (error) {
      console.error(`[DevicesStore] Failed to save config for ${deviceId}:`, error)
      return false
    }
  }

  /**
   * 删除连接配置
   *
   * @param {string} deviceId - 设备ID
   * @returns {boolean} 是否成功
   */
  function deleteConnectionConfig(deviceId) {
    try {
      delete connectionConfigs.value[deviceId]
      localStorage.removeItem(`${STORAGE_KEY_CONFIGS}_${deviceId}`)
      return true
    } catch (error) {
      console.error(`[DevicesStore] Failed to delete config for ${deviceId}:`, error)
      return false
    }
  }

  /**
   * 加载所有配置模板
   *
   * @returns {Array} 模板列表
   */
  function loadConfigTemplates() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_TEMPLATES)
      if (stored) {
        configTemplates.value = JSON.parse(stored)
      }
    } catch (error) {
      console.error('[DevicesStore] Failed to load templates:', error)
    }

    return configTemplates.value
  }

  /**
   * 保存配置模板
   *
   * @param {Object} template - 模板对象
   * @returns {boolean} 是否成功
   */
  function saveConfigTemplate(template) {
    try {
      const templateToSave = {
        id: template.id || `template_${Date.now()}`,
        name: template.name,
        deviceType: template.deviceType,
        description: template.description || '',
        config: { ...template.config },
        isDefault: template.isDefault || false,
        createdAt: template.createdAt || Date.now(),
        updatedAt: Date.now()
      }

      // 检查是否已存在同名模板
      const existingIndex = configTemplates.value.findIndex(
        t => t.id === templateToSave.id || t.name === templateToSave.name
      )

      if (existingIndex >= 0) {
        configTemplates.value[existingIndex] = templateToSave
      } else {
        configTemplates.value.push(templateToSave)
      }

      // 持久化
      localStorage.setItem(STORAGE_KEY_TEMPLATES, JSON.stringify(configTemplates.value))

      return true
    } catch (error) {
      console.error('[DevicesStore] Failed to save template:', error)
      return false
    }
  }

  /**
   * 删除配置模板
   *
   * @param {string} templateId - 模板ID
   * @returns {boolean} 是否成功
   */
  function deleteConfigTemplate(templateId) {
    try {
      const index = configTemplates.value.findIndex(t => t.id === templateId)
      if (index >= 0) {
        configTemplates.value.splice(index, 1)
        localStorage.setItem(STORAGE_KEY_TEMPLATES, JSON.stringify(configTemplates.value))
        return true
      }
      return false
    } catch (error) {
      console.error('[DevicesStore] Failed to delete template:', error)
      return false
    }
  }

  /**
   * 应用模板到设备
   *
   * @param {string} deviceId - 设备ID
   * @param {string} templateId - 模板ID
   * @returns {boolean} 是否成功
   */
  function applyTemplateToDevice(deviceId, templateId) {
    const template = configTemplates.value.find(t => t.id === templateId)
    if (!template) {
      console.error(`[DevicesStore] Template not found: ${templateId}`)
      return false
    }

    return saveConnectionConfig(deviceId, {
      ...template.config,
      deviceId,
      templateId,
      templateName: template.name
    })
  }

  /**
   * 批量应用配置到多个设备
   *
   * @param {Array<string>} deviceIds - 设备ID列表
   * @param {Object} config - 配置对象
   * @returns {Object} 应用结果
   */
  function batchApplyConfig(deviceIds, config) {
    const results = {
      success: 0,
      failed: 0,
      errors: []
    }

    deviceIds.forEach(deviceId => {
      const success = saveConnectionConfig(deviceId, { ...config, deviceId })
      if (success) {
        results.success++
      } else {
        results.failed++
        results.errors.push({
          deviceId,
          error: '保存配置失败'
        })
      }
    })

    return results
  }

  /**
   * 导出所有配置
   *
   * @returns {string} JSON字符串
   */
  function exportAllConfigs() {
    const exportData = {
      configs: connectionConfigs.value,
      templates: configTemplates.value,
      exportedAt: new Date().toISOString()
    }
    return JSON.stringify(exportData, null, 2)
  }

  /**
   * 导入配置
   *
   * @param {string} jsonString - JSON字符串
   * @returns {Object} 导入结果
   */
  function importConfigs(jsonString) {
    try {
      const importData = JSON.parse(jsonString)

      const results = {
        configsImported: 0,
        templatesImported: 0,
        errors: []
      }

      // 导入配置
      if (importData.configs) {
        Object.entries(importData.configs).forEach(([deviceId, config]) => {
          const success = saveConnectionConfig(deviceId, config)
          if (success) {
            results.configsImported++
          } else {
            results.errors.push({
              type: 'config',
              deviceId,
              error: '导入配置失败'
            })
          }
        })
      }

      // 导入模板
      if (importData.templates && Array.isArray(importData.templates)) {
        importData.templates.forEach(template => {
          const success = saveConfigTemplate(template)
          if (success) {
            results.templatesImported++
          } else {
            results.errors.push({
              type: 'template',
              templateId: template.id,
              error: '导入模板失败'
            })
          }
        })
      }

      return results
    } catch (error) {
      console.error('[DevicesStore] Import configs error:', error)
      return {
        configsImported: 0,
        templatesImported: 0,
        errors: [{ type: 'parse', error: error.message }]
      }
    }
  }

  /**
   * 扫描可用串口
   *
   * @returns {Promise<Array>} 串口列表
   */
  async function scanAvailablePorts() {
    const result = await get('/api/v1/device/ports/scan', null, {
      onError: (msg) => {
        console.error('[DevicesStore] Failed to scan ports:', msg)
      }
    })

    if (result.success && result.data) {
      return result.data.ports || []
    }

    return []
  }

  /**
   * 测试设备连接
   *
   * @param {string} deviceId - 设备ID
   * @param {Object} config - 连接配置
   * @returns {Promise<Object>} 测试结果
   */
  async function testDeviceConnection(deviceId, config) {
    const result = await post('/api/v1/device/test_connection', {
      device_type: deviceId,
      config
    }, {
      onError: (msg) => {
        console.error(`[DevicesStore] Test connection failed for ${deviceId}:`, msg)
      }
    })

    if (result.success && result.data) {
      return {
        success: result.data.success,
        diagnostics: result.data.diagnostics || [],
        details: result.data.details || null
      }
    }

    return {
      success: false,
      diagnostics: [{
        level: 'error',
        title: '连接测试失败',
        description: result.message || '未知错误'
      }]
    }
  }

  /**
   * 获取设备配置摘要
   *
   * @returns {Array} 配置摘要列表
   */
  function getConfigSummary() {
    return Object.entries(connectionConfigs.value).map(([deviceId, config]) => ({
      deviceId,
      deviceName: DEVICE_NAMES[deviceId] || deviceId,
      port: config.port,
      baudrate: config.baudrate,
      slaveId: config.slaveId,
      updatedAt: config.updatedAt,
      templateName: config.templateName
    }))
  }

  // ==================== 生命周期方法 ====================

  /**
   * 初始化Store
   *
   * @description 建立WebSocket连接并获取初始设备状态
   */
  function init() {
    // 建立WebSocket连接
    devicesWS.connect()
    // 获取初始状态
    fetchAllDeviceStatus()
    // 加载配置模板
    loadConfigTemplates()
  }

  /**
   * 清理资源
   *
   * @description 断开WebSocket连接，重置所有状态
   */
  function cleanup() {
    devicesWS.disconnect()
    wsConnected.value = false
    lastRefreshTime.value = null
  }

  // ==================== 导出 ====================

  return {
    // 状态
    devices,
    systemStatus,
    wsConnected,
    loading,
    lastRefreshTime,
    alarms,
    unacknowledgedAlarms,
    statusHistory,
    batchOperation,
    connectionConfigs,
    configTemplates,
    activeConfig,

    // 计算属性
    connectedDevices,
    errorDevices,
    disconnectedDevices,
    allConnected,
    hasErrors,
    connectedCount,
    totalDevicesCount,
    systemStatusText,
    systemStatusType,
    systemHealth,
    systemHealthText,
    systemHealthType,
    totalAlarmsCount,
    unacknowledgedAlarmsCount,

    // 方法
    init,
    cleanup,
    fetchAllDeviceStatus,
    fetchDeviceStatus,
    refreshAll,
    updateDeviceStatus,
    
    // 告警管理方法
    addAlarm,
    acknowledgeAlarm,
    acknowledgeAlarms,
    clearAlarm,
    clearDeviceAlarms,
    clearAcknowledgedAlarms,
    
    // 历史记录方法
    addStatusHistory,
    queryStatusHistory,
    clearStatusHistory,
    
    // 批量操作方法
    connectAllDevices,
    disconnectAllDevices,
    resetBatchOperation,
    
    // 连接配置管理方法
    loadConnectionConfig,
    saveConnectionConfig,
    deleteConnectionConfig,
    loadConfigTemplates,
    saveConfigTemplate,
    deleteConfigTemplate,
    applyTemplateToDevice,
    batchApplyConfig,
    exportAllConfigs,
    importConfigs,
    scanAvailablePorts,
    testDeviceConnection,
    getConfigSummary,
    
    // 常量导出
    DEVICE_TYPES,
    DEVICE_NAMES,
    HEALTH_STATUS,
    HEALTH_STATUS_TEXT,
    HEALTH_STATUS_TYPE
  }
})
