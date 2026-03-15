/**
 * @file temperature.js
 * @path src/stores/
 * @description 温度控制状态管理，处理温控器连接、PID参数配置、程序控温等
 * @author Agent
 * @date 2024-03-07
 * @dependencies pinia, vue, composables, utils
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useDeviceBase } from '../composables/useDeviceBase'
import { useWebSocket } from '../composables/useWebSocket'
import { get, post, del } from '../utils/apiRequest'
import { WS_BASE_URL } from '../config/api'

export const useTemperatureStore = defineStore('temperature', () => {
  // ============ 基础状态（从 useDeviceBase 获取） ============

  const {
    isConnected,
    isConnecting,
    status,
    alarmMessage,
    wsConnected,
    loading,
    canControl,
    showError,
    clearAlarm,
    setLoading,
    resetState,
    _updateStatus
  } = useDeviceBase('temperature')

  // ============ 温度特有状态 ============

  /** 当前温度数据 */
  const currentTemp = ref(25.0)
  const targetTemp = ref(25.0)
  const outputPower = ref(0)
  const heatingRate = ref(0)

  /** PID 参数 */
  const pidParams = ref({
    kp: 10.0,
    ki: 0.5,
    kd: 2.0,
    setpoint: 25.0
  })

  /** 温度限制 (单位: K, 基于液氮釜温控范围 77K-400K) */
  const tempLimits = ref({
    min: 77,    // 液氮温度
    max: 400,   // 最高温度
    warning_high: 380,
    warning_low: 85
  })

  /** 温度单位 ('K' 或 'C') */
  const tempUnit = ref('K')

  /** 程序控温曲线 */
  const programCurves = ref([])

  /** 当前运行的程序 */
  const activeProgram = ref(null)
  const programStatus = ref('idle')
  const programProgress = ref(0)

  /** 温度历史数据（用于图表） */
  const tempHistory = ref([])
  const maxHistoryPoints = 500

  /** 报警代码 */
  const alarmCode = ref(null)

  /** PID 参数预设 */
  const pidPresets = ref([
    {
      id: 'default',
      name: '默认参数',
      description: '适用于一般温控场景',
      params: { kp: 10.0, ki: 0.5, kd: 2.0 }
    },
    {
      id: 'fast_response',
      name: '快速响应',
      description: '适用于需要快速升温的场景',
      params: { kp: 20.0, ki: 1.0, kd: 5.0 }
    },
    {
      id: 'stable',
      name: '稳定控制',
      description: '适用于需要高精度恒温的场景',
      params: { kp: 8.0, ki: 0.3, kd: 1.5 }
    },
    {
      id: 'slow_heating',
      name: '缓慢升温',
      description: '适用于需要缓慢升温的场景',
      params: { kp: 5.0, ki: 0.2, kd: 1.0 }
    }
  ])

  /** 温度保护配置 */
  const protectionConfig = ref({
    maxTemp: 380,
    minTemp: 85,
    enableShutdown: true,
    warningThreshold: 10, // 警告阈值（距离限制温度的度数）
    alarmThreshold: 5     // 报警阈值（距离限制温度的度数）
  })

  /** PID 控制是否激活 */
  const pidControlActive = ref(false)

  /** PID 参数验证结果 */
  const pidValidationResult = ref(null)

  /** 温度保护状态 */
  const protectionStatus = ref({
    isProtected: false,
    protectionType: null,
    message: ''
  })

  // ============ Getters ============

  /** 温度状态类型 */
  const tempStatusType = computed(() => {
    if (currentTemp.value >= tempLimits.value.warning_high) return 'danger'
    if (currentTemp.value <= tempLimits.value.warning_low) return 'warning'
    // 检查是否接近液氮温度（可能导致设备问题）
    if (currentTemp.value <= 80) return 'warning'
    return 'success'
  })

  /** 温度状态文本 */
  const tempStatusText = computed(() => {
    if (currentTemp.value >= tempLimits.value.warning_high) return '温度过高'
    if (currentTemp.value <= tempLimits.value.warning_low) return '温度过低'
    if (currentTemp.value <= 80) return '接近液氮温度'
    return '温度正常'
  })

  /** 是否正在加热 */
  const isHeating = computed(() => outputPower.value > 0)

  /** 是否正在运行程序 */
  const isProgramRunning = computed(() => programStatus.value === 'running')

  // ============ Helper Functions ============

  /**
   * 温度单位转换: K -> °C
   * @param {number} kelvin - 开尔文温度
   * @returns {number} 摄氏温度
   */
  function kelvinToCelsius(kelvin) {
    return kelvin - 273.15
  }

  /**
   * 温度单位转换: °C -> K
   * @param {number} celsius - 摄氏温度
   * @returns {number} 开尔文温度
   */
  function celsiusToKelvin(celsius) {
    return celsius + 273.15
  }

  /**
   * 格式化温度显示
   * @param {number} temp - 温度值
   * @param {string} unit - 目标单位 ('K' 或 'C')
   * @returns {string} 格式化后的温度字符串
   */
  function formatTemperature(temp, unit = tempUnit.value) {
    const displayTemp = unit === 'C' ? kelvinToCelsius(temp) : temp
    return `${displayTemp.toFixed(1)}${unit === 'K' ? 'K' : '°C'}`
  }

  /**
   * 验证温度是否在有效范围内 (77K-400K)
   * @param {number} temperature - 温度值 (K)
   * @returns {Object} 验证结果 { valid: boolean, message: string }
   */
  function validateTemperature(temperature) {
    if (typeof temperature !== 'number' || isNaN(temperature)) {
      return { valid: false, message: '温度值无效' }
    }
    if (temperature < tempLimits.value.min) {
      return { 
        valid: false, 
        message: `温度不能低于 ${tempLimits.value.min}K (${kelvinToCelsius(tempLimits.value.min).toFixed(1)}°C)` 
      }
    }
    if (temperature > tempLimits.value.max) {
      return { 
        valid: false, 
        message: `温度不能高于 ${tempLimits.value.max}K (${kelvinToCelsius(tempLimits.value.max).toFixed(1)}°C)` 
      }
    }
    return { valid: true, message: '' }
  }

  /**
   * 添加温度历史数据
   * @param {Object} data - 温度数据点
   */
  function addTempHistory(data) {
    tempHistory.value.push({
      timestamp: data.timestamp || Date.now(),
      current: data.current,
      target: data.target,
      power: data.power
    })

    // 限制历史数据点数量
    if (tempHistory.value.length > maxHistoryPoints) {
      tempHistory.value = tempHistory.value.slice(-maxHistoryPoints)
    }
  }

  // ============ WebSocket 管理 ============

  /**
   * WebSocket 消息处理器
   * @param {Object} data - 接收到的消息数据
   */
  function handleWebSocketMessage(data) {
    // 响应心跳 ping 消息
    if (data.type === 'ping') {
      wsSend({ type: 'pong', timestamp: Date.now() })
      return
    }

    // 更新温度数据
    if (data.current_temp !== undefined) {
      currentTemp.value = data.current_temp
      targetTemp.value = data.target_temp
      outputPower.value = data.output_power
      heatingRate.value = data.heating_rate || 0
      status.value = data.status

      // 添加到历史数据
      addTempHistory({
        timestamp: data.timestamp,
        current: data.current_temp,
        target: data.target_temp,
        power: data.output_power
      })
    }

    // 更新程序状态
    if (data.program_status !== undefined) {
      programStatus.value = data.program_status
      programProgress.value = data.program_progress || 0
    }

    // 处理错误
    if (data.error) {
      console.error('WebSocket error:', data.error)
      showError(data.error)
    }
  }

  // 创建 WebSocket 实例
  const { connect: wsConnect, disconnect: wsDisconnect, send: wsSend } = useWebSocket({
    url: `${WS_BASE_URL}/ws/temperature`,
    onMessage: handleWebSocketMessage,
    onOpen: () => {
      console.log('Temperature WebSocket connected')
    },
    onClose: () => {
      console.log('Temperature WebSocket disconnected')
    },
    onError: (error) => {
      console.error('Temperature WebSocket error:', error)
    }
  })

  // ============ Actions ============

  /**
   * 获取温度状态
   * @returns {Promise<Object|null>} 温度状态数据
   */
  async function fetchStatus() {
    const result = await get('/api/v1/temperature/status', null, {
      onError: (msg) => {
        console.error('Failed to fetch temperature status:', msg)
        isConnected.value = false
        status.value = 'disconnected'
      }
    })

    if (result.success && result.data) {
      const data = result.data
      status.value = data.status
      currentTemp.value = data.current_temp
      targetTemp.value = data.target_temp
      outputPower.value = data.output_power
      heatingRate.value = data.heating_rate || 0
      isConnected.value = data.connected

      // 添加到历史数据
      addTempHistory({
        current: data.current_temp,
        target: data.target_temp,
        power: data.output_power
      })

      return data
    }
    return null
  }

  /**
   * 连接温控器
   * @returns {Promise<boolean>} 连接是否成功
   */
  async function connect() {
    isConnecting.value = true
    const result = await post('/temperature/connect', null, {
      onError: (msg) => showError('连接错误: ' + msg)
    })

    if (result.success && result.data) {
      isConnected.value = true
      status.value = result.data.status
      await fetchStatus()
      wsConnect()
      isConnecting.value = false
      return true
    }

    isConnecting.value = false
    return false
  }

  /**
   * 断开温控器
   * @returns {Promise<Object|null>} 断开结果
   */
  async function disconnect() {
    wsDisconnect()
    const result = await post('/temperature/disconnect', null, {
      onError: (msg) => showError('断开错误: ' + msg)
    })

    resetState()
    return result.success ? result.data : null
  }

  /**
   * 设置目标温度
   * @param {number} temperature - 目标温度（开尔文）
   * @returns {Promise<boolean>} 设置是否成功
   */
  async function setTargetTemp(temperature) {
    if (!canControl.value) {
      showError('温控器未就绪')
      return false
    }

    // 温度范围验证 (77K-400K)
    const validation = validateTemperature(temperature)
    if (!validation.valid) {
      showError(validation.message)
      return false
    }

    const result = await post('/temperature/setpoint', { temperature }, {
      onLoading: setLoading,
      loadingKey: 'setTemp',
      onError: (msg) => showError('设置温度错误: ' + msg)
    })

    if (result.success) {
      targetTemp.value = temperature
      pidParams.value.setpoint = temperature
      return true
    }

    return false
  }

  /**
   * 配置 PID 参数
   * @param {Object} params - PID 参数
   * @param {number} params.kp - 比例系数
   * @param {number} params.ki - 积分系数
   * @param {number} params.kd - 微分系数
   * @returns {Promise<boolean>} 配置是否成功
   */
  async function configurePID(params) {
    if (!canControl.value) {
      showError('温控器未就绪')
      return false
    }

    const result = await post('/temperature/pid', {
      kp: params.kp,
      ki: params.ki,
      kd: params.kd
    }, {
      onLoading: setLoading,
      loadingKey: 'pidConfig',
      onError: (msg) => showError('PID 配置错误: ' + msg)
    })

    if (result.success) {
      pidParams.value = { ...pidParams.value, ...params }
      return true
    }

    return false
  }

  /**
   * 获取 PID 参数
   * @returns {Promise<Object|null>} PID 参数对象
   */
  async function fetchPIDParams() {
    const result = await get('/temperature/pid', null, {
      onError: (msg) => showError('获取PID参数错误: ' + msg)
    })

    if (result.success && result.data) {
      pidParams.value = { ...pidParams.value, ...result.data }
      return result.data
    }
    return null
  }

  /**
   * 验证 PID 参数
   * @param {Object} params - PID 参数
   * @param {number} params.kp - 比例系数
   * @param {number} params.ki - 积分系数
   * @param {number} params.kd - 微分系数
   * @returns {Promise<Object|null>} 验证结果
   */
  async function validatePIDParams(params) {
    const result = await post('/temperature/pid/validate', {
      kp: params.kp,
      ki: params.ki,
      kd: params.kd
    }, {
      onError: (msg) => showError('PID参数验证错误: ' + msg)
    })

    return result.success ? result.data : null
  }

  /**
   * 启动 PID 控制
   * @returns {Promise<boolean>} 启动是否成功
   */
  async function startPIDControl() {
    if (!canControl.value) {
      showError('温控器未就绪')
      return false
    }

    const result = await post('/temperature/pid/start', null, {
      onLoading: setLoading,
      loadingKey: 'startPID',
      onError: (msg) => showError('启动PID控制错误: ' + msg)
    })

    return result.success
  }

  /**
   * 停止 PID 控制
   * @returns {Promise<boolean>} 停止是否成功
   */
  async function stopPIDControl() {
    const result = await post('/temperature/pid/stop', null, {
      onLoading: setLoading,
      loadingKey: 'stopPID',
      onError: (msg) => showError('停止PID控制错误: ' + msg)
    })

    return result.success
  }

  /**
   * 创建程序控温曲线
   * @param {Object} program - 程序配置
   * @param {string} program.name - 程序名称
   * @param {Array} program.segments - 温度段列表
   * @returns {Promise<boolean>} 创建是否成功
   */
  async function createProgram(program) {
    const result = await post('/temperature/program/create', program, {
      onLoading: setLoading,
      loadingKey: 'createProgram',
      onError: (msg) => showError('创建程序错误: ' + msg)
    })

    if (result.success) {
      // 刷新程序列表
      await fetchPrograms()
      return true
    }

    return false
  }

  /**
   * 获取程序列表
   * @returns {Promise<Array>} 程序列表
   */
  async function fetchPrograms() {
    const result = await get('/temperature/programs', null, {
      onError: (msg) => console.error('Failed to fetch programs:', msg)
    })

    if (result.success && result.data) {
      programCurves.value = result.data.programs || []
      return result.data.programs
    }
    return []
  }

  /**
   * 启动程序控温
   * @param {string} programId - 程序ID
   * @returns {Promise<boolean>} 启动是否成功
   */
  async function startProgram(programId) {
    if (!canControl.value) {
      showError('温控器未就绪')
      return false
    }

    const result = await post('/temperature/program', { program_id: programId }, {
      onLoading: setLoading,
      loadingKey: 'startProgram',
      onError: (msg) => showError('启动程序错误: ' + msg)
    })

    if (result.success) {
      programStatus.value = 'running'
      activeProgram.value = programId
      return true
    }

    return false
  }

  /**
   * 暂停程序控温
   * @returns {Promise<boolean>} 暂停是否成功
   */
  async function pauseProgram() {
    const result = await post('/temperature/program/pause', null, {
      onLoading: setLoading,
      loadingKey: 'pauseProgram',
      onError: (msg) => showError('暂停程序错误: ' + msg)
    })

    if (result.success) {
      programStatus.value = 'paused'
      return true
    }

    return false
  }

  /**
   * 恢复程序控温
   * @returns {Promise<boolean>} 恢复是否成功
   */
  async function resumeProgram() {
    const result = await post('/temperature/program/resume', null, {
      onLoading: setLoading,
      loadingKey: 'resumeProgram',
      onError: (msg) => showError('恢复程序错误: ' + msg)
    })

    if (result.success) {
      programStatus.value = 'running'
      return true
    }

    return false
  }

  /**
   * 停止程序控温
   * @returns {Promise<boolean>} 停止是否成功
   */
  async function stopProgram() {
    const result = await post('/temperature/program/stop', null, {
      onLoading: setLoading,
      loadingKey: 'stopProgram',
      onError: (msg) => showError('停止程序错误: ' + msg)
    })

    if (result.success) {
      programStatus.value = 'idle'
      activeProgram.value = null
      programProgress.value = 0
      return true
    }

    return false
  }

  /**
   * 删除程序
   * @param {string} programId - 程序ID
   * @returns {Promise<boolean>} 删除是否成功
   */
  async function deleteProgram(programId) {
    const result = await del(`/temperature/program/${programId}`, {
      onLoading: setLoading,
      loadingKey: 'deleteProgram',
      onError: (msg) => showError('删除程序错误: ' + msg)
    })

    if (result.success) {
      await fetchPrograms()
      return true
    }

    return false
  }

  /**
   * 设置温度保护配置
   * @param {Object} config - 保护配置
   * @param {number} config.max_temp - 最高温度限制
   * @param {number} config.min_temp - 最低温度限制
   * @param {boolean} config.enable_shutdown - 超温是否自动关机
   * @returns {Promise<boolean>} 设置是否成功
   */
  async function setProtectionConfig(config) {
    const result = await post('/temperature/protection', config, {
      onLoading: setLoading,
      loadingKey: 'setProtection',
      onError: (msg) => showError('设置保护配置错误: ' + msg)
    })

    return result.success
  }

  /**
   * 清除温度保护状态
   * @returns {Promise<boolean>} 清除是否成功
   */
  async function clearProtectionStatus() {
    const result = await post('/temperature/protection/clear', null, {
      onError: (msg) => showError('清除保护状态错误: ' + msg)
    })

    return result.success
  }

  /**
   * 获取温度历史记录
   * @param {Object} params - 查询参数
   * @param {number} params.start_time - 开始时间戳
   * @param {number} params.end_time - 结束时间戳
   * @param {number} params.interval - 数据间隔（秒）
   * @returns {Promise<Array|null>} 历史记录数组
   */
  async function fetchTemperatureHistory(params = {}) {
    const result = await post('/temperature/history', params, {
      onError: (msg) => showError('获取历史记录错误: ' + msg)
    })

    if (result.success && result.data) {
      return result.data.history || []
    }
    return null
  }

  /**
   * 清除温度历史记录
   * @returns {Promise<boolean>} 清除是否成功
   */
  async function clearTemperatureHistory() {
    const result = await post('/temperature/history/clear', null, {
      onError: (msg) => showError('清除历史记录错误: ' + msg)
    })

    if (result.success) {
      tempHistory.value = []
      return true
    }
    return false
  }

  /**
   * 导出温度历史记录
   * @param {string} format - 导出格式 ('csv' 或 'json')
   * @returns {Promise<Blob|null>} 文件Blob对象
   */
  async function exportTemperatureHistory(format = 'csv') {
    const result = await get('/temperature/history/export', { format }, {
      onError: (msg) => showError('导出历史记录错误: ' + msg)
    })

    return result.success ? result.data : null
  }

  /**
   * 紧急停止
   * @returns {Promise<boolean>} 急停是否成功
   */
  async function emergencyStop() {
    const result = await post('/temperature/emergency_stop', null, {
      onLoading: setLoading,
      loadingKey: 'emergencyStop',
      onError: (msg) => showError('紧急停止错误: ' + msg)
    })

    if (result.success) {
      status.value = 'emergency_stop'
      programStatus.value = 'stopped'
      outputPower.value = 0
      return true
    }
    return false
  }

  /**
   * 复位急停状态
   * @returns {Promise<boolean>} 复位是否成功
   */
  async function resetEmergencyStop() {
    const result = await post('/temperature/reset', null, {
      onLoading: setLoading,
      loadingKey: 'resetEmergency',
      onError: (msg) => showError('复位急停状态错误: ' + msg)
    })

    if (result.success) {
      status.value = 'idle'
      return true
    }
    return false
  }

  /**
   * 清除温度历史数据（本地）
   */
  function clearHistory() {
    tempHistory.value = []
  }

  /**
   * 应用 PID 预设参数
   * @param {string} presetId - 预设ID
   * @returns {Promise<boolean>} 应用是否成功
   */
  async function applyPIDPreset(presetId) {
    const preset = pidPresets.value.find(p => p.id === presetId)
    if (!preset) {
      showError('未找到指定的PID预设')
      return false
    }

    const success = await configurePID(preset.params)
    if (success) {
      pidParams.value = { ...pidParams.value, ...preset.params }
      return true
    }
    return false
  }

  /**
   * 验证温度保护配置
   * @param {Object} config - 保护配置
   * @returns {Object} 验证结果
   */
  function validateProtectionConfig(config) {
    const errors = []

    if (config.minTemp >= config.maxTemp) {
      errors.push('最低温度限制必须小于最高温度限制')
    }

    if (config.minTemp < tempLimits.value.min) {
      errors.push(`最低温度限制不能低于 ${tempLimits.value.min}K`)
    }

    if (config.maxTemp > tempLimits.value.max) {
      errors.push(`最高温度限制不能高于 ${tempLimits.value.max}K`)
    }

    if (config.warningThreshold <= 0 || config.warningThreshold > 50) {
      errors.push('警告阈值必须在 1-50K 之间')
    }

    if (config.alarmThreshold <= 0 || config.alarmThreshold >= config.warningThreshold) {
      errors.push('报警阈值必须大于0且小于警告阈值')
    }

    return {
      valid: errors.length === 0,
      errors: errors,
      message: errors.join('; ')
    }
  }

  /**
   * 检查温度是否触发保护
   * @param {number} temperature - 当前温度
   * @returns {Object} 保护检查结果
   */
  function checkProtection(temperature) {
    const config = protectionConfig.value
    const result = {
      isProtected: false,
      protectionType: null,
      message: '',
      action: null
    }

    // 检查是否超过最高温度限制
    if (temperature >= config.maxTemp - config.alarmThreshold) {
      result.isProtected = true
      result.protectionType = 'overheat'
      result.message = `温度过高！当前 ${temperature.toFixed(1)}K 接近最高限制 ${config.maxTemp}K`
      result.action = config.enableShutdown ? 'shutdown' : 'alarm'
    }
    // 检查是否低于最低温度限制
    else if (temperature <= config.minTemp + config.alarmThreshold) {
      result.isProtected = true
      result.protectionType = 'undercool'
      result.message = `温度过低！当前 ${temperature.toFixed(1)}K 接近最低限制 ${config.minTemp}K`
      result.action = 'alarm'
    }
    // 检查警告阈值
    else if (temperature >= config.maxTemp - config.warningThreshold) {
      result.protectionType = 'warning_high'
      result.message = `温度偏高警告：当前 ${temperature.toFixed(1)}K`
      result.action = 'warning'
    }
    else if (temperature <= config.minTemp + config.warningThreshold) {
      result.protectionType = 'warning_low'
      result.message = `温度偏低警告：当前 ${temperature.toFixed(1)}K`
      result.action = 'warning'
    }

    protectionStatus.value = result
    return result
  }

  /**
   * 模拟 PID 控制效果（用于预览）
   * @param {Object} params - PID 参数
   * @param {number} targetTemp - 目标温度
   * @param {number} duration - 模拟时长（秒）
   * @returns {Array} 模拟结果数据
   */
  function simulatePIDEffect(params, targetTemp, duration = 60) {
    const { kp, ki, kd } = params
    const data = []
    
    let temp = currentTemp.value
    let integral = 0
    let lastError = 0
    const dt = 0.1 // 时间步长（秒）
    
    for (let t = 0; t <= duration; t += dt) {
      const error = targetTemp - temp
      integral += error * dt
      const derivative = (error - lastError) / dt
      
      // PID 控制输出
      const output = kp * error + ki * integral + kd * derivative
      
      // 简化的温度变化模型（假设输出功率直接影响温度变化）
      const tempChange = output * 0.1 * dt
      temp += tempChange
      
      // 添加一些噪声模拟真实情况
      temp += (Math.random() - 0.5) * 0.01
      
      data.push({
        time: t,
        temperature: temp,
        error: error,
        output: output
      })
      
      lastError = error
    }
    
    return data
  }

  /**
   * 获取 PID 参数优化建议
   * @param {Object} currentParams - 当前 PID 参数
   * @returns {Object} 优化建议
   */
  function getPIDOptimizationSuggestions(currentParams) {
    const suggestions = []
    const { kp, ki, kd } = currentParams

    // 检查比例系数
    if (kp < 5) {
      suggestions.push({
        type: 'warning',
        param: 'kp',
        message: '比例系数较小，可能导致响应速度慢',
        suggestion: '建议增加到 8-15 之间以提高响应速度'
      })
    } else if (kp > 30) {
      suggestions.push({
        type: 'warning',
        param: 'kp',
        message: '比例系数过大，可能导致超调和振荡',
        suggestion: '建议降低到 10-20 之间以减少超调'
      })
    }

    // 检查积分系数
    if (ki < 0.1) {
      suggestions.push({
        type: 'info',
        param: 'ki',
        message: '积分系数较小，可能存在稳态误差',
        suggestion: '建议增加到 0.3-1.0 之间以消除稳态误差'
      })
    } else if (ki > 2) {
      suggestions.push({
        type: 'warning',
        param: 'ki',
        message: '积分系数过大，可能导致积分饱和',
        suggestion: '建议降低到 0.5-1.5 之间'
      })
    }

    // 检查微分系数
    if (kd < 0.5) {
      suggestions.push({
        type: 'info',
        param: 'kd',
        message: '微分系数较小，对干扰抑制能力弱',
        suggestion: '建议增加到 1.0-3.0 之间以提高稳定性'
      })
    } else if (kd > 10) {
      suggestions.push({
        type: 'warning',
        param: 'kd',
        message: '微分系数过大，可能放大噪声',
        suggestion: '建议降低到 2-5 之间'
      })
    }

    // 检查参数比例关系
    const kd_kp_ratio = kd / kp
    if (kd_kp_ratio < 0.1 || kd_kp_ratio > 0.5) {
      suggestions.push({
        type: 'info',
        param: 'ratio',
        message: 'Kd/Kp 比例不在推荐范围（0.1-0.5）',
        suggestion: '建议调整参数使 Kd/Kp 比例在 0.2-0.3 之间'
      })
    }

    return {
      hasSuggestions: suggestions.length > 0,
      suggestions: suggestions,
      overallScore: calculatePIDScore(currentParams)
    }
  }

  /**
   * 计算 PID 参数评分（用于优化建议）
   * @param {Object} params - PID 参数
   * @returns {number} 评分（0-100）
   */
  function calculatePIDScore(params) {
    const { kp, ki, kd } = params
    let score = 100

    // 比例系数评分（理想范围：10-20）
    if (kp >= 10 && kp <= 20) {
      score -= 0
    } else if (kp >= 8 && kp <= 25) {
      score -= 10
    } else {
      score -= 20
    }

    // 积分系数评分（理想范围：0.3-1.0）
    if (ki >= 0.3 && ki <= 1.0) {
      score -= 0
    } else if (ki >= 0.2 && ki <= 1.5) {
      score -= 10
    } else {
      score -= 20
    }

    // 微分系数评分（理想范围：2-5）
    if (kd >= 2 && kd <= 5) {
      score -= 0
    } else if (kd >= 1 && kd <= 8) {
      score -= 10
    } else {
      score -= 20
    }

    // 参数比例评分
    const kd_kp_ratio = kd / kp
    if (kd_kp_ratio >= 0.2 && kd_kp_ratio <= 0.3) {
      score -= 0
    } else if (kd_kp_ratio >= 0.1 && kd_kp_ratio <= 0.5) {
      score -= 10
    } else {
      score -= 15
    }

    return Math.max(0, score)
  }

  /**
   * 初始化
   */
  function init() {
    fetchStatus()
    fetchPrograms()
  }

  /**
   * 清理资源
   */
  function cleanup() {
    wsDisconnect()
  }

  return {
    // 基础状态（来自 useDeviceBase）
    isConnected,
    isConnecting,
    status,
    alarmMessage,
    wsConnected,
    loading,
    canControl,

    // 温度特有状态
    currentTemp,
    targetTemp,
    outputPower,
    heatingRate,
    pidParams,
    tempLimits,
    tempUnit,
    programCurves,
    activeProgram,
    programStatus,
    programProgress,
    tempHistory,
    alarmCode,
    pidPresets,
    protectionConfig,
    pidControlActive,
    pidValidationResult,
    protectionStatus,

    // Getters
    tempStatusType,
    tempStatusText,
    isHeating,
    isProgramRunning,

    // Helper Functions
    kelvinToCelsius,
    celsiusToKelvin,
    formatTemperature,
    validateTemperature,

    // Actions
    clearAlarm,
    showError,
    fetchStatus,
    connect,
    disconnect,
    setTargetTemp,
    configurePID,
    fetchPIDParams,
    validatePIDParams,
    startPIDControl,
    stopPIDControl,
    createProgram,
    fetchPrograms,
    startProgram,
    pauseProgram,
    resumeProgram,
    stopProgram,
    deleteProgram,
    setProtectionConfig,
    clearProtectionStatus,
    fetchTemperatureHistory,
    clearTemperatureHistory,
    exportTemperatureHistory,
    emergencyStop,
    resetEmergencyStop,
    clearHistory,
    applyPIDPreset,
    validateProtectionConfig,
    checkProtection,
    simulatePIDEffect,
    getPIDOptimizationSuggestions,
    calculatePIDScore,
    init,
    cleanup
  }
})
