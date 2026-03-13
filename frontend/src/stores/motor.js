/**
 * @file motor.js
 * @path src/stores/
 * @description 电机控制状态管理Store，封装电机操作、状态监控、PR路径等功能
 * @author Agent
 * @date 2024-03-07
 * @dependencies pinia, vue, composables, utils
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useDeviceBase } from '../composables/useDeviceBase'
import { useWebSocket } from '../composables/useWebSocket'
import { request, get, post } from '../utils/apiRequest'
import { WS_BASE_URL } from '../config/api'

export const useMotorStore = defineStore('motor', () => {
  // ==================== 组合式函数调用 ====================
  
  /**
   * 使用设备基础状态管理
   * 提供通用的连接状态、告警、加载状态管理
   */
  const {
    isConnected,
    isConnecting,
    status,
    alarmMessage,
    wsConnected,
    loading,
    canControl: baseCanControl,
    showError,
    clearAlarm,
    setLoading,
    resetState,
    updateStatus
  } = useDeviceBase('motor')

  // ==================== 电机特有状态 ====================

  /** 电机位置（步数） */
  const positionSteps = ref(0)

  /** 电机位置（毫米） */
  const positionMm = ref(0)

  /** 电机速度 */
  const velocity = ref(0)

  /** 电机限位配置 */
  const limits = ref({
    positive_mm: 50,
    negative_mm: -50,
    positive_steps: 80000,
    negative_steps: -80000
  })

  /** 状态字 */
  const statusWord = ref(null)

  /** 报警代码 */
  const alarmCode = ref(null)

  /** 报警文本 */
  const alarmText = ref('')

  /** PR路径配置 */
  const prPaths = ref({})

  /** 分析结果 */
  const analysisResult = ref(null)

  /** 位置预设列表 */
  const positionPresets = ref([])

  /** 运动历史记录 */
  const movementHistory = ref([])

  /** 位置历史记录 (用于实时数据分析) */
  const positionHistory = ref([])

  /** 最大历史记录数量 */
  const MAX_HISTORY_COUNT = 100

  /** 最大位置历史记录数量 */
  const MAX_POSITION_HISTORY_COUNT = 500

  /** PR路径模板列表 */
  const pathTemplates = ref([])

  /** 最大模板数量 */
  const MAX_TEMPLATE_COUNT = 50

  // ==================== 计算属性 ====================

  /**
   * 是否允许控制电机
   * 覆盖基础canControl，增加状态检查
   */
  const canControl = computed(() => {
    return isConnected.value && status.value === 'ready'
  })

  /**
   * 是否处于急停状态
   */
  const isEmergencyStopped = computed(() => {
    return status.value === 'emergency_stop'
  })

  /**
   * 限位状态描述
   */
  const limitStatus = computed(() => {
    if (positionMm.value >= limits.value.positive_mm - 1) return '正向限位'
    if (positionMm.value <= limits.value.negative_mm + 1) return '负向限位'
    return '正常'
  })

  /**
   * 限位状态类型（用于UI显示）
   */
  const limitStatusType = computed(() => {
    if (limitStatus.value === '正常') return 'success'
    return 'warning'
  })

  // ==================== WebSocket 连接管理 ====================

  /**
   * WebSocket消息处理函数
   * 
   * @param {Object} data - WebSocket接收到的数据
   */
  function handleWebSocketMessage(data) {
    // 处理心跳消息
    if (data.type === 'ping' || data.ping) {
      motorWS.send({ type: 'pong' })
      return
    }

    // 处理设备状态更新
    if (data.position_steps !== undefined) {
      positionSteps.value = data.position_steps
      positionMm.value = data.position_mm
      status.value = data.status
      isConnected.value = data.status !== 'disconnected'
      
      // 添加到位置历史记录
      if (data.position_mm !== undefined) {
        const positionRecord = {
          timestamp: Date.now(),
          value: data.position_mm,
          steps: data.position_steps
        }
        positionHistory.value.push(positionRecord)
        
        // 限制历史记录长度
        if (positionHistory.value.length > MAX_POSITION_HISTORY_COUNT) {
          positionHistory.value = positionHistory.value.slice(-MAX_POSITION_HISTORY_COUNT)
        }
      }
    }

    // 处理错误消息
    if (data.error) {
      console.error('WebSocket error:', data.error)
      showError(data.error)
    }

    // 处理报警消息
    if (data.alarm_code !== undefined && data.alarm_code !== 0) {
      alarmCode.value = data.alarm_code
      alarmText.value = data.alarm_text || ''
      showError(`报警: ${data.alarm_text || `代码 ${data.alarm_code}`}`)
    }
  }

  /**
   * 初始化WebSocket连接
   */
  const motorWS = useWebSocket({
    url: `${WS_BASE_URL}/ws/motor`,
    onMessage: handleWebSocketMessage,
    onOpen: () => {
      console.log('Motor WebSocket connected')
    },
    onClose: () => {
      console.log('Motor WebSocket disconnected')
    },
    onError: (error) => {
      console.error('Motor WebSocket error:', error)
    },
    reconnectInterval: 3000,
    heartbeatInterval: 30000
  })

  // ==================== API 操作方法 ====================

  /**
   * 获取电机状态
   * 
   * @returns {Promise<Object|null>} 状态数据或null
   */
  async function fetchStatus() {
    const result = await get('/motor/status', null, {
      onError: (msg) => {
        console.error('Failed to fetch status:', msg)
        isConnected.value = false
        status.value = 'disconnected'
      }
    })

    if (result.success && result.data) {
      const data = result.data
      status.value = data.status
      positionSteps.value = data.position_steps
      positionMm.value = data.position_mm
      limits.value.positive_steps = data.limit_positive
      limits.value.negative_steps = data.limit_negative
      limits.value.positive_mm = Math.round(data.limit_positive / 1600 * 100) / 100
      limits.value.negative_mm = Math.round(data.limit_negative / 1600 * 100) / 100
      isConnected.value = data.connected
      return data
    }

    return null
  }

  /**
   * 连接电机
   * 
   * @returns {Promise<boolean>} 连接是否成功
   */
  async function connectMotor() {
    isConnecting.value = true
    
    const result = await post('/motor/connect', null, {
      onError: (msg) => showError('连接错误: ' + msg)
    })

    if (result.success && result.data?.success) {
      isConnected.value = true
      status.value = result.data.status
      await fetchStatus()
      motorWS.connect()
      isConnecting.value = false
      return true
    }

    isConnecting.value = false
    showError('连接失败: ' + (result.message || '未知错误'))
    return false
  }

  /**
   * 断开电机连接
   * 
   * @returns {Promise<Object|null>} 断开结果
   */
  async function disconnectMotor() {
    motorWS.disconnect()
    
    const result = await post('/motor/disconnect', null, {
      onError: (msg) => showError('断开错误: ' + msg)
    })

    isConnected.value = false
    status.value = 'disconnected'
    
    return result.success ? result.data : null
  }

  /**
   * 绝对定位运动
   * 
   * @param {number} positionMm - 目标位置（毫米）
   * @param {number} velocityMmS - 运动速度（毫米/秒）
   * @returns {Promise<boolean>} 运动是否成功
   */
  async function moveAbsolute(positionMm, velocityMmS) {
    if (!canControl.value) {
      showError('电机未就绪，无法运动')
      return false
    }

    const result = await post('/motor/move', {
      position_mm: positionMm,
      velocity_mm_s: velocityMmS
    }, {
      onError: (msg) => showError('运动错误: ' + msg)
    })

    if (result.success && !result.data?.success) {
      showError('运动失败: ' + (result.data?.message || '未知错误'))
    }

    return result.success && result.data?.success
  }

  /**
   * JOG运动
   * 
   * @param {string} direction - 运动方向 ('positive' | 'negative')
   * @param {number} velocityMmS - 运动速度（毫米/秒）
   * @returns {Promise<boolean>} 运动是否成功
   */
  async function jog(direction, velocityMmS) {
    if (!canControl.value) {
      showError('电机未就绪，无法运动')
      return false
    }

    const result = await post('/motor/jog', {
      direction: direction,
      velocity_mm_s: velocityMmS
    }, {
      onError: (msg) => showError('JOG错误: ' + msg)
    })

    return result.success && result.data?.success
  }

  /**
   * 急停
   * 
   * @returns {Promise<boolean>} 急停是否成功
   */
  async function emergencyStop() {
    const result = await post('/motor/emergency_stop', null, {
      onLoading: setLoading,
      loadingKey: 'emergencyStop',
      onError: (msg) => showError('急停错误: ' + msg)
    })

    if (result.success) {
      status.value = 'emergency_stop'
    }

    return result.success && result.data?.success
  }

  /**
   * 复位急停
   * 
   * @returns {Promise<boolean>} 复位是否成功
   */
  async function resetEmergency() {
    const result = await post('/motor/reset', null, {
      onLoading: setLoading,
      loadingKey: 'resetEmergency',
      onError: (msg) => showError('复位错误: ' + msg)
    })

    if (result.success && result.data?.success) {
      status.value = 'ready'
    }

    return result.success && result.data?.success
  }

  /**
   * 设置限位
   * 
   * @param {number} positiveMm - 正向限位（毫米）
   * @param {number} negativeMm - 负向限位（毫米）
   * @returns {Promise<boolean>} 设置是否成功
   */
  async function setLimits(positiveMm, negativeMm) {
    const result = await post('/motor/limits', {
      positive_mm: positiveMm,
      negative_mm: negativeMm
    }, {
      onError: (msg) => showError('设置限位错误: ' + msg)
    })

    if (result.success && result.data?.success) {
      limits.value.positive_mm = positiveMm
      limits.value.negative_mm = negativeMm
    }

    return result.success && result.data?.success
  }

  /**
   * 配置PR路径
   * 
   * @param {Object} config - PR路径配置
   * @returns {Promise<boolean>} 配置是否成功
   */
  async function configurePRPath(config) {
    const result = await post('/motor/pr/config', config, {
      onLoading: setLoading,
      loadingKey: 'prConfig',
      onError: (msg) => showError('PR 路径配置错误: ' + msg)
    })

    if (result.success && !result.data?.success) {
      showError('PR 路径配置失败: ' + (result.data?.message || '未知错误'))
    }

    return result.success && result.data?.success
  }

  /**
   * 触发PR路径
   * 
   * @param {number} pathNumber - 路径编号
   * @returns {Promise<boolean>} 触发是否成功
   */
  async function triggerPRPath(pathNumber) {
    const result = await post('/motor/pr/trigger', {
      path_number: pathNumber
    }, {
      onLoading: setLoading,
      loadingKey: 'prTrigger',
      onError: (msg) => showError('PR 路径触发错误: ' + msg)
    })

    if (result.success && !result.data?.success) {
      showError('PR 路径触发失败: ' + (result.data?.message || '未知错误'))
    }

    return result.success && result.data?.success
  }

  /**
   * 回零操作
   * 
   * @param {number} mode - 回零模式（默认0）
   * @returns {Promise<boolean>} 回零是否成功
   */
  async function home(mode = 0) {
    const result = await post('/motor/home', { mode: mode }, {
      onLoading: setLoading,
      loadingKey: 'home',
      onError: (msg) => showError('回零错误: ' + msg)
    })

    if (result.success && !result.data?.success) {
      showError('回零失败: ' + (result.data?.message || '未知错误'))
    }

    return result.success && result.data?.success
  }

  /**
   * 报警复位
   * 
   * @returns {Promise<boolean>} 复位是否成功
   */
  async function resetAlarm() {
    const result = await post('/motor/reset_alarm', null, {
      onLoading: setLoading,
      loadingKey: 'resetAlarm',
      onError: (msg) => showError('报警复位错误: ' + msg)
    })

    if (result.success && !result.data?.success) {
      showError('报警复位失败: ' + (result.data?.message || '未知错误'))
    }

    return result.success && result.data?.success
  }

  /**
   * 保存参数
   * 
   * @returns {Promise<boolean>} 保存是否成功
   */
  async function saveParams() {
    const result = await post('/motor/save_params', null, {
      onLoading: setLoading,
      loadingKey: 'saveParams',
      onError: (msg) => showError('保存参数错误: ' + msg)
    })

    if (result.success && !result.data?.success) {
      showError('保存参数失败: ' + (result.data?.message || '未知错误'))
    }

    return result.success && result.data?.success
  }

  /**
   * 恢复出厂设置
   * 
   * @returns {Promise<boolean>} 恢复是否成功
   */
  async function factoryReset() {
    const result = await post('/motor/factory_reset', null, {
      onLoading: setLoading,
      loadingKey: 'factoryReset',
      onError: (msg) => showError('恢复出厂设置错误: ' + msg)
    })

    if (result.success && !result.data?.success) {
      showError('恢复出厂设置失败: ' + (result.data?.message || '未知错误'))
    }

    return result.success && result.data?.success
  }

  /**
   * 读取状态字
   * 
   * @returns {Promise<Object|null>} 状态字数据
   */
  async function readStatusWord() {
    const result = await get('/motor/status_word', null, {
      onLoading: setLoading,
      loadingKey: 'statusWord',
      onError: (msg) => showError('读取状态字错误: ' + msg)
    })

    if (result.success && result.data) {
      statusWord.value = result.data
      return result.data
    }

    return null
  }

  /**
   * 读取报警代码
   * 
   * @returns {Promise<Object|null>} 报警代码数据
   */
  async function readAlarmCode() {
    const result = await get('/motor/alarm_code', null, {
      onLoading: setLoading,
      loadingKey: 'alarmCode',
      onError: (msg) => showError('读取报警代码错误: ' + msg)
    })

    if (result.success && result.data) {
      alarmCode.value = result.data.alarm_code
      alarmText.value = result.data.alarm_text
      return result.data
    }

    return null
  }

  // ==================== 数据分析功能 ====================

  /**
   * 信号平滑
   * 
   * @param {Object} data - 待平滑的数据
   * @returns {Promise<Object|null>} 平滑结果
   */
  async function smoothSignal(data) {
    const result = await post('/analysis/smooth', data, {
      onLoading: setLoading,
      loadingKey: 'smooth',
      onError: (msg) => showError('信号平滑错误: ' + msg)
    })

    if (result.success && result.data) {
      analysisResult.value = result.data
      return result.data
    }

    return null
  }

  /**
   * 曲线拟合
   * 
   * @param {Object} data - 待拟合的数据
   * @returns {Promise<Object|null>} 拟合结果
   */
  async function fitCurve(data) {
    const result = await post('/analysis/fit', data, {
      onLoading: setLoading,
      loadingKey: 'fit',
      onError: (msg) => showError('曲线拟合错误: ' + msg)
    })

    if (result.success && result.data) {
      analysisResult.value = result.data
      return result.data
    }

    return null
  }

  /**
   * 磁滞回线分析
   * 
   * @param {Object} data - 待分析的数据
   * @returns {Promise<Object|null>} 分析结果
   */
  async function analyzeHysteresis(data) {
    const result = await post('/analysis/hysteresis', data, {
      onLoading: setLoading,
      loadingKey: 'hysteresis',
      onError: (msg) => showError('磁滞回线分析错误: ' + msg)
    })

    if (result.success && result.data) {
      analysisResult.value = result.data
      return result.data
    }

    return null
  }

  // ==================== 位置预设管理 ====================

  /**
   * 获取当前位置 (用于实时数据分析)
   * 
   * @returns {Promise<Object|null>} 位置数据
   */
  async function fetchCurrentPosition() {
    const result = await get('/motor/status', null, {
      onError: (msg) => {
        console.error('Failed to fetch current position:', msg)
      }
    })

    if (result.success && result.data) {
      const data = result.data
      positionSteps.value = data.position_steps
      positionMm.value = data.position_mm
      
      // 添加到历史记录
      const positionRecord = {
        timestamp: Date.now(),
        value: data.position_mm,
        steps: data.position_steps
      }
      positionHistory.value.push(positionRecord)
      
      // 限制历史记录长度
      if (positionHistory.value.length > MAX_POSITION_HISTORY_COUNT) {
        positionHistory.value = positionHistory.value.slice(-MAX_POSITION_HISTORY_COUNT)
      }
      
      return positionRecord
    }

    return null
  }

  /**
   * 清除位置历史记录
   */
  function clearPositionHistory() {
    positionHistory.value = []
  }

  /**
   * 加载位置预设
   * 从localStorage加载预设配置
   */
  function loadPositionPresets() {
    try {
      const stored = localStorage.getItem('motor_position_presets')
      if (stored) {
        positionPresets.value = JSON.parse(stored)
      }
    } catch (error) {
      console.error('Failed to load position presets:', error)
      positionPresets.value = []
    }
  }

  /**
   * 保存位置预设到localStorage
   */
  function savePositionPresets() {
    try {
      localStorage.setItem('motor_position_presets', JSON.stringify(positionPresets.value))
    } catch (error) {
      console.error('Failed to save position presets:', error)
    }
  }

  /**
   * 添加位置预设
   * 
   * @param {Object} preset - 预设配置
   * @param {string} preset.name - 预设名称
   * @param {number} preset.position - 目标位置
   * @param {number} preset.velocity - 运动速度
   * @param {string} preset.description - 预设描述
   * @returns {boolean} 添加是否成功
   */
  function addPositionPreset(preset) {
    if (!preset.name || preset.position === undefined) {
      return false
    }

    const newPreset = {
      id: Date.now(),
      name: preset.name,
      position: preset.position,
      velocity: preset.velocity || 10,
      description: preset.description || '',
      createdAt: new Date().toISOString()
    }

    positionPresets.value.push(newPreset)
    savePositionPresets()
    return true
  }

  /**
   * 更新位置预设
   * 
   * @param {number} id - 预设ID
   * @param {Object} updates - 更新内容
   * @returns {boolean} 更新是否成功
   */
  function updatePositionPreset(id, updates) {
    const index = positionPresets.value.findIndex(p => p.id === id)
    if (index === -1) {
      return false
    }

    positionPresets.value[index] = {
      ...positionPresets.value[index],
      ...updates,
      updatedAt: new Date().toISOString()
    }

    savePositionPresets()
    return true
  }

  /**
   * 删除位置预设
   * 
   * @param {number} id - 预设ID
   * @returns {boolean} 删除是否成功
   */
  function deletePositionPreset(id) {
    const index = positionPresets.value.findIndex(p => p.id === id)
    if (index === -1) {
      return false
    }

    positionPresets.value.splice(index, 1)
    savePositionPresets()
    return true
  }

  /**
   * 应用位置预设
   * 
   * @param {number} id - 预设ID
   * @returns {Promise<boolean>} 运动是否成功
   */
  async function applyPositionPreset(id) {
    const preset = positionPresets.value.find(p => p.id === id)
    if (!preset) {
      showError('预设不存在')
      return false
    }

    return await moveAbsolute(preset.position, preset.velocity)
  }

  // ==================== 运动历史记录管理 ====================

  /**
   * 加载运动历史
   * 从localStorage加载历史记录
   */
  function loadMovementHistory() {
    try {
      const stored = localStorage.getItem('motor_movement_history')
      if (stored) {
        movementHistory.value = JSON.parse(stored)
      }
    } catch (error) {
      console.error('Failed to load movement history:', error)
      movementHistory.value = []
    }
  }

  /**
   * 保存运动历史到localStorage
   */
  function saveMovementHistory() {
    try {
      localStorage.setItem('motor_movement_history', JSON.stringify(movementHistory.value))
    } catch (error) {
      console.error('Failed to save movement history:', error)
    }
  }

  /**
   * 添加运动历史记录
   * 
   * @param {Object} record - 运动记录
   * @param {string} record.type - 运动类型 (absolute/jog/home/emergency)
   * @param {number} record.startPosition - 起始位置
   * @param {number} record.targetPosition - 目标位置
   * @param {number} record.velocity - 运动速度
   * @param {boolean} record.success - 是否成功
   * @param {string} record.errorMessage - 错误信息
   */
  function addMovementRecord(record) {
    const newRecord = {
      id: Date.now(),
      timestamp: new Date().toISOString(),
      type: record.type || 'unknown',
      startPosition: record.startPosition || positionMm.value,
      targetPosition: record.targetPosition,
      velocity: record.velocity,
      success: record.success !== false,
      errorMessage: record.errorMessage || ''
    }

    movementHistory.value.unshift(newRecord)

    // 限制历史记录数量
    if (movementHistory.value.length > MAX_HISTORY_COUNT) {
      movementHistory.value = movementHistory.value.slice(0, MAX_HISTORY_COUNT)
    }

    saveMovementHistory()
  }

  /**
   * 清空运动历史
   */
  function clearMovementHistory() {
    movementHistory.value = []
    saveMovementHistory()
  }

  /**
   * 导出运动历史
   * 
   * @returns {string} JSON格式的历史数据
   */
  function exportMovementHistory() {
    return JSON.stringify(movementHistory.value, null, 2)
  }

  // ==================== PR路径模板管理 ====================

  /**
   * 加载路径模板
   * 从localStorage加载模板配置
   */
  function loadPathTemplates() {
    try {
      const stored = localStorage.getItem('motor_path_templates')
      if (stored) {
        pathTemplates.value = JSON.parse(stored)
      }
    } catch (error) {
      console.error('Failed to load path templates:', error)
      pathTemplates.value = []
    }
  }

  /**
   * 保存路径模板到localStorage
   */
  function savePathTemplates() {
    try {
      localStorage.setItem('motor_path_templates', JSON.stringify(pathTemplates.value))
    } catch (error) {
      console.error('Failed to save path templates:', error)
    }
  }

  /**
   * 添加路径模板
   * 
   * @param {Object} template - 模板配置
   * @param {string} template.name - 模板名称
   * @param {string} template.description - 模板描述
   * @param {Array} template.points - 路径点数组
   * @returns {boolean} 添加是否成功
   */
  function addPathTemplate(template) {
    if (!template.name || !template.points || template.points.length === 0) {
      return false
    }

    if (pathTemplates.value.length >= MAX_TEMPLATE_COUNT) {
      showError('模板数量已达上限')
      return false
    }

    const newTemplate = {
      id: Date.now(),
      name: template.name,
      description: template.description || '',
      points: JSON.parse(JSON.stringify(template.points)),
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }

    pathTemplates.value.push(newTemplate)
    savePathTemplates()
    return true
  }

  /**
   * 更新路径模板
   * 
   * @param {number} id - 模板ID
   * @param {Object} updates - 更新内容
   * @returns {boolean} 更新是否成功
   */
  function updatePathTemplate(id, updates) {
    const index = pathTemplates.value.findIndex(t => t.id === id)
    if (index === -1) {
      return false
    }

    pathTemplates.value[index] = {
      ...pathTemplates.value[index],
      ...updates,
      updatedAt: new Date().toISOString()
    }

    savePathTemplates()
    return true
  }

  /**
   * 删除路径模板
   * 
   * @param {number} id - 模板ID
   * @returns {boolean} 删除是否成功
   */
  function deletePathTemplate(id) {
    const index = pathTemplates.value.findIndex(t => t.id === id)
    if (index === -1) {
      return false
    }

    pathTemplates.value.splice(index, 1)
    savePathTemplates()
    return true
  }

  /**
   * 应用路径模板到指定路径
   * 
   * @param {number} templateId - 模板ID
   * @param {number} pathNumber - 路径编号（1-16）
   * @returns {Promise<boolean>} 应用是否成功
   */
  async function applyPathTemplate(templateId, pathNumber) {
    const template = pathTemplates.value.find(t => t.id === templateId)
    if (!template || !template.points || template.points.length === 0) {
      showError('模板不存在或无效')
      return false
    }

    // 将模板的第一个点应用到指定路径
    const point = template.points[0]
    const config = {
      path_number: pathNumber,
      mode: point.mode || 0,
      position_mm: point.position_mm || 0,
      velocity_mm_s: point.velocity_mm_s || 10,
      accel_time: point.accel_time || 100,
      decel_time: point.decel_time || 100,
      dwell_time: point.dwell_time || 0,
      special_param: point.special_param || 0
    }

    return await configurePRPath(config)
  }

  /**
   * 导出路径模板
   * 
   * @param {number} id - 模板ID（可选，不传则导出所有）
   * @returns {string} JSON格式的模板数据
   */
  function exportPathTemplate(id) {
    if (id) {
      const template = pathTemplates.value.find(t => t.id === id)
      return template ? JSON.stringify(template, null, 2) : ''
    }
    return JSON.stringify(pathTemplates.value, null, 2)
  }

  /**
   * 导入路径模板
   * 
   * @param {string} jsonData - JSON格式的模板数据
   * @returns {boolean} 导入是否成功
   */
  function importPathTemplate(jsonData) {
    try {
      const data = JSON.parse(jsonData)
      
      // 支持单个模板或模板数组
      const templates = Array.isArray(data) ? data : [data]
      
      let importedCount = 0
      templates.forEach(template => {
        if (template.name && template.points) {
          const success = addPathTemplate({
            name: template.name,
            description: template.description || '',
            points: template.points
          })
          if (success) {
            importedCount++
          }
        }
      })

      if (importedCount > 0) {
        return true
      } else {
        showError('无效的模板数据')
        return false
      }
    } catch (error) {
      console.error('Failed to import path template:', error)
      showError('导入失败：数据格式错误')
      return false
    }
  }

  /**
   * 获取路径模板列表
   * 
   * @param {Object} filters - 过滤条件（可选）
   * @returns {Array} 过滤后的模板列表
   */
  function getPathTemplates(filters) {
    let result = [...pathTemplates.value]

    if (filters) {
      if (filters.name) {
        result = result.filter(t => 
          t.name.toLowerCase().includes(filters.name.toLowerCase())
        )
      }
      if (filters.startDate) {
        result = result.filter(t => 
          new Date(t.createdAt) >= new Date(filters.startDate)
        )
      }
      if (filters.endDate) {
        result = result.filter(t => 
          new Date(t.createdAt) <= new Date(filters.endDate)
        )
      }
    }

    return result.sort((a, b) => 
      new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
    )
  }

  /**
   * 复制路径模板
   * 
   * @param {number} id - 模板ID
   * @returns {boolean} 复制是否成功
   */
  function duplicatePathTemplate(id) {
    const template = pathTemplates.value.find(t => t.id === id)
    if (!template) {
      return false
    }

    return addPathTemplate({
      name: `${template.name} (副本)`,
      description: template.description,
      points: template.points
    })
  }

  // ==================== 生命周期方法 ====================

  /**
   * 初始化Store
   */
  function init() {
    fetchStatus()
    loadPositionPresets()
    loadMovementHistory()
    loadPathTemplates()
  }

  /**
   * 清理资源
   */
  function cleanup() {
    motorWS.disconnect()
    resetState()
  }

  // ==================== 导出 ====================

  return {
    // 基础状态（来自 useDeviceBase）
    isConnected,
    isConnecting,
    status,
    alarmMessage,
    wsConnected,
    loading,

    // 电机特有状态
    positionSteps,
    positionMm,
    velocity,
    limits,
    statusWord,
    alarmCode,
    alarmText,
    prPaths,
    analysisResult,
    positionPresets,
    movementHistory,
    positionHistory,

    // 计算属性
    canControl,
    isEmergencyStopped,
    limitStatus,
    limitStatusType,

    // 基础方法（来自 useDeviceBase）
    showError,
    clearAlarm,
    setLoading,

    // 电机操作方法
    fetchStatus,
    connectMotor,
    disconnectMotor,
    moveAbsolute,
    jog,
    emergencyStop,
    resetEmergency,
    setLimits,
    configurePRPath,
    triggerPRPath,
    home,
    resetAlarm,
    saveParams,
    factoryReset,
    readStatusWord,
    readAlarmCode,

    // 数据分析方法
    smoothSignal,
    fitCurve,
    analyzeHysteresis,

    // 位置数据方法 (用于实时分析)
    fetchCurrentPosition,
    clearPositionHistory,

    // 位置预设管理
    addPositionPreset,
    updatePositionPreset,
    deletePositionPreset,
    applyPositionPreset,

    // 运动历史管理
    addMovementRecord,
    clearMovementHistory,
    exportMovementHistory,

    // PR路径模板管理
    pathTemplates,
    loadPathTemplates,
    addPathTemplate,
    updatePathTemplate,
    deletePathTemplate,
    applyPathTemplate,
    exportPathTemplate,
    importPathTemplate,
    getPathTemplates,
    duplicatePathTemplate,

    // WebSocket方法
    connectWebSocket: motorWS.connect,
    disconnectWebSocket: motorWS.disconnect,

    // 生命周期
    init,
    cleanup
  }
})
