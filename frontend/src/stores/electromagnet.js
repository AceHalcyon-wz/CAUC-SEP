/**
 * @file electromagnet.js
 * @path src/stores/
 * @description 电磁铁控制状态管理，处理电流设置、扫描模式、磁场强度监控及校准曲线
 * @author Agent
 * @date 2024-03-06
 * @dependencies pinia, vue, composables/useDeviceBase, composables/useWebSocket, utils/apiRequest
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useDeviceBase } from '../composables/useDeviceBase'
import { useWebSocket } from '../composables/useWebSocket'
import { request } from '../utils/apiRequest'
import { WS_BASE_URL } from '../config/api'

/**
 * 电磁铁控制 Store
 *
 * 提供电磁铁的电流控制、扫描模式配置、磁场强度监控及校准曲线管理
 */
export const useElectromagnetStore = defineStore('electromagnet', () => {
  // ============ 基础状态（从 useDeviceBase 获取） ============

  const {
    isConnected,
    isConnecting,
    status,
    alarmMessage,
    loading,
    canControl,
    showError,
    clearAlarm,
    setLoading,
    updateStatus
  } = useDeviceBase('electromagnet')

  // ============ 电磁铁特有状态 ============

  /** 当前电流值 (A) */
  const currentCurrent = ref(0)

  /** 当前磁场强度 (mT) */
  const currentField = ref(0)

  /** 目标电流值 (A) */
  const targetCurrent = ref(0)

  /** 电流限制 */
  const currentLimits = ref({
    min: -10,
    max: 10
  })

  /** 扫描模式配置 */
  const scanConfig = ref({
    mode: 'linear', // 'linear' | 'step' | 'custom'
    startCurrent: 0,
    endCurrent: 5,
    stepCount: 10,
    stepDelay: 0.5,
    scanRate: 0.1 // A/s
  })

  /** 扫描状态 */
  const scanStatus = ref({
    isScanning: false,
    isPaused: false,
    currentStep: 0,
    totalSteps: 0,
    progress: 0,
    startTime: null,
    estimatedEndTime: null,
    currentCurrent: 0,
    currentField: 0,
    scanDirection: 'forward', // 'forward' | 'backward'
    scanPath: [] // 扫描路径可视化数据
  })

  /** 实时扫描数据 */
  const scanData = ref({
    current: [], // 电流数据数组
    field: [], // 磁场数据数组
    timestamps: [], // 时间戳数组
    maxPoints: 1000 // 最大数据点数
  })

  /** 扫描预设参数模板 */
  const scanPresets = ref([
    {
      id: 'quick_scan',
      name: '快速扫描',
      description: '快速扫描模式，适用于初步测试',
      config: {
        mode: 'linear',
        startCurrent: 0,
        endCurrent: 5,
        scanRate: 0.5
      }
    },
    {
      id: 'precise_scan',
      name: '精密扫描',
      description: '精密扫描模式，适用于精确测量',
      config: {
        mode: 'step',
        startCurrent: 0,
        endCurrent: 5,
        stepSize: 0.05,
        stepDelay: 1.0
      }
    },
    {
      id: 'full_range',
      name: '全量程扫描',
      description: '全量程扫描模式',
      config: {
        mode: 'linear',
        startCurrent: -10,
        endCurrent: 10,
        scanRate: 0.2
      }
    },
    {
      id: 'hysteresis',
      name: '磁滞回线',
      description: '磁滞回线扫描模式',
      config: {
        mode: 'custom',
        startCurrent: -10,
        endCurrent: 10,
        scanRate: 0.1,
        cycles: 3
      }
    }
  ])

  /** 自定义预设列表 */
  const customPresets = ref([])

  /** 校准曲线数据 */
  const calibrationCurve = ref({
    points: [], // [{current: number, field: number}]
    coefficients: null, // 拟合系数
    lastCalibrated: null
  })

  // ============ Getters ============

  /** 是否正在扫描 */
  const isScanning = computed(() => scanStatus.value.isScanning)

  /** 是否暂停 */
  const isPaused = computed(() => scanStatus.value.isPaused)

  /** 扫描剩余时间（秒） */
  const estimatedRemainingTime = computed(() => {
    if (!scanStatus.value.startTime || !scanStatus.value.progress) {
      return 0
    }

    const elapsed = (Date.now() - scanStatus.value.startTime) / 1000
    const totalEstimated = elapsed / (scanStatus.value.progress / 100)
    return Math.max(0, totalEstimated - elapsed)
  })

  /** 扫描进度百分比 */
  const scanProgressPercent = computed(() => {
    return scanStatus.value.progress.toFixed(1)
  })

  /** 所有预设（系统 + 自定义） */
  const allPresets = computed(() => {
    return [...scanPresets.value, ...customPresets.value]
  })

  /** 校准状态 */
  const calibrationStatus = computed(() => {
    if (!calibrationCurve.value.points || calibrationCurve.value.points.length === 0) {
      return '未校准'
    }
    if (calibrationCurve.value.coefficients) {
      return '已校准'
    }
    return '校准中'
  })

  /** 磁场强度格式化 */
  const formattedField = computed(() => {
    return `${currentField.value.toFixed(2)} mT`
  })

  /** 电流格式化 */
  const formattedCurrent = computed(() => {
    return `${currentCurrent.value.toFixed(3)} A`
  })

  // ============ WebSocket 管理 ============

  /**
   * 处理WebSocket消息
   * @param {Object} data - 接收到的消息数据
   */
  function handleWebSocketMessage(data) {
    // 处理心跳响应
    if (data.type === 'pong') {
      return
    }

    // 处理心跳请求（服务器发起的ping）
    if (data.type === 'ping') {
      wsManager.send({ type: 'pong', timestamp: Date.now() })
      return
    }

    // 更新电流和磁场强度
    if (data.current !== undefined) {
      currentCurrent.value = data.current
    }
    if (data.field !== undefined) {
      currentField.value = data.field
    }
    if (data.status !== undefined) {
      updateStatus(data.status)
    }

    // 更新扫描状态
    if (data.scan_status) {
      scanStatus.value = {
        ...scanStatus.value,
        isScanning: data.scan_status.is_scanning || false,
        isPaused: data.scan_status.is_paused || false,
        currentStep: data.scan_status.current_step || 0,
        totalSteps: data.scan_status.total_steps || 0,
        progress: data.scan_status.progress || 0,
        currentCurrent: data.scan_status.current_current || 0,
        currentField: data.scan_status.current_field || 0,
        scanDirection: data.scan_status.direction || 'forward'
      }

      // 如果扫描完成，记录结束时间
      if (data.scan_status.completed) {
        scanStatus.value.estimatedEndTime = Date.now()
      }
    }

    // 更新实时扫描数据
    if (data.scan_data && scanStatus.value.isScanning) {
      addScanDataPoint(data.scan_data.current, data.scan_data.field)
    }

    if (data.error) {
      console.error('WebSocket error:', data.error)
      showError(data.error)
    }
  }

  /** WebSocket管理器 */
  const wsManager = useWebSocket({
    url: `${WS_BASE_URL}/ws/electromagnet`,
    onMessage: handleWebSocketMessage,
    onOpen: () => {
      console.log('Electromagnet WebSocket connected')
    },
    onClose: () => {
      console.log('Electromagnet WebSocket disconnected')
    },
    onError: (error) => {
      console.error('WebSocket error:', error)
    }
  })

  // ============ Actions ============

  /**
   * 获取电磁铁状态
   * @returns {Promise<Object|null>} 状态数据
   */
  async function fetchStatus() {
    const result = await request({
      method: 'GET',
      url: '/electromagnet/status',
      onError: (msg) => {
        console.error('Failed to fetch electromagnet status:', msg)
        isConnected.value = false
        status.value = 'disconnected'
      }
    })

    if (result.success && result.data) {
      const data = result.data
      status.value = data.status
      currentCurrent.value = data.current || 0
      currentField.value = data.field || 0
      isConnected.value = data.connected

      if (data.limits) {
        currentLimits.value = data.limits
      }

      return data
    }

    return null
  }

  /**
   * 连接电磁铁
   * @returns {Promise<boolean>} 连接是否成功
   */
  async function connectElectromagnet() {
    isConnecting.value = true
    const result = await request({
      method: 'POST',
      url: '/electromagnet/connect',
      onError: showError
    })

    if (result.success) {
      isConnected.value = true
      status.value = result.data?.status || 'ready'
      await fetchStatus()
      wsManager.connect()
      return true
    }

    isConnecting.value = false
    return false
  }

  /**
   * 断开电磁铁
   * @returns {Promise<Object|null>} 断开结果
   */
  async function disconnectElectromagnet() {
    wsManager.disconnect()
    const result = await request({
      method: 'POST',
      url: '/electromagnet/disconnect',
      onError: showError
    })

    isConnected.value = false
    status.value = 'disconnected'
    return result.success ? result.data : null
  }

  /**
   * 设置电流
   * @param {number} current - 目标电流值 (A)
   * @returns {Promise<boolean>} 设置是否成功
   */
  async function setCurrent(current) {
    if (!canControl.value) {
      showError('电磁铁未就绪，无法设置电流')
      return false
    }

    // 电流范围检查
    if (current < currentLimits.value.min || current > currentLimits.value.max) {
      showError(`电流超出范围: ${currentLimits.value.min}A ~ ${currentLimits.value.max}A`)
      return false
    }

    const result = await request({
      method: 'POST',
      url: '/electromagnet/current',
      data: { current },
      loadingKey: 'setCurrent',
      onLoading: setLoading,
      onError: showError
    })

    if (result.success) {
      targetCurrent.value = current
      return true
    }

    return false
  }

  /**
   * 设置磁场强度
   * @param {number} field - 目标磁场强度 (mT)
   * @returns {Promise<boolean>} 设置是否成功
   */
  async function setField(field) {
    if (!canControl.value) {
      showError('电磁铁未就绪，无法设置磁场')
      return false
    }

    const result = await request({
      method: 'POST',
      url: '/electromagnet/field',
      data: { field },
      loadingKey: 'setField',
      onLoading: setLoading,
      onError: showError
    })

    if (result.success) {
      return true
    }

    return false
  }

  /**
   * 急停
   * @returns {Promise<boolean>} 急停是否成功
   */
  async function emergencyStop() {
    const result = await request({
      method: 'POST',
      url: '/electromagnet/emergency_stop',
      onError: showError
    })

    if (result.success) {
      status.value = 'emergency_stop'
      scanStatus.value.isScanning = false
      return true
    }

    return false
  }

  /**
   * 复位急停
   * @returns {Promise<boolean>} 复位是否成功
   */
  async function resetEmergency() {
    const result = await request({
      method: 'POST',
      url: '/electromagnet/reset_emergency',
      onError: showError
    })

    if (result.success) {
      status.value = 'ready'
      return true
    }

    return false
  }

  /**
   * 过流保护复位
   * @returns {Promise<boolean>} 复位是否成功
   */
  async function resetOvercurrent() {
    const result = await request({
      method: 'POST',
      url: '/electromagnet/reset_overcurrent',
      onError: showError
    })

    if (result.success) {
      status.value = 'ready'
      return true
    }

    return false
  }

  /**
   * 配置扫描模式
   * @param {Object} config - 扫描配置
   * @returns {Promise<boolean>} 配置是否成功
   */
  async function configureScan(config) {
    const result = await request({
      method: 'POST',
      url: '/electromagnet/scan',
      data: config,
      loadingKey: 'configScan',
      onLoading: setLoading,
      onError: showError
    })

    if (result.success) {
      scanConfig.value = { ...scanConfig.value, ...config }
      return true
    }

    return false
  }

  /**
   * 扫描参数预验证
   * @param {Object} config - 扫描配置
   * @returns {Promise<Object|null>} 验证结果
   */
  async function validateScanConfig(config) {
    const result = await request({
      method: 'POST',
      url: '/electromagnet/scan/validate',
      data: config,
      loadingKey: 'validateScanConfig',
      onLoading: setLoading,
      onError: showError
    })

    return result.success ? result.data : null
  }

  /**
   * 开始扫描
   * @returns {Promise<boolean>} 启动是否成功
   */
  async function startScan() {
    if (!canControl.value) {
      showError('电磁铁未就绪，无法开始扫描')
      return false
    }

    const result = await request({
      method: 'POST',
      url: '/electromagnet/scan',
      loadingKey: 'startScan',
      onLoading: setLoading,
      onError: showError
    })

    if (result.success) {
      scanStatus.value.isScanning = true
      scanStatus.value.currentStep = 0
      scanStatus.value.totalSteps = result.data?.total_steps || 0
      return true
    }

    return false
  }

  /**
   * 停止扫描
   * @returns {Promise<boolean>} 停止是否成功
   */
  async function stopScan() {
    const result = await request({
      method: 'POST',
      url: '/electromagnet/scan/stop',
      loadingKey: 'stopScan',
      onLoading: setLoading,
      onError: showError
    })

    if (result.success) {
      scanStatus.value.isScanning = false
      return true
    }

    return false
  }

  /**
   * 暂停扫描
   * @returns {Promise<boolean>} 暂停是否成功
   */
  async function pauseScan() {
    const result = await request({
      method: 'POST',
      url: '/electromagnet/scan/pause',
      onError: showError
    })

    if (result.success) {
      scanStatus.value.isPaused = true
      return true
    }

    return false
  }

  /**
   * 恢复扫描
   * @returns {Promise<boolean>} 恢复是否成功
   */
  async function resumeScan() {
    const result = await request({
      method: 'POST',
      url: '/electromagnet/scan/resume',
      onError: showError
    })

    if (result.success) {
      scanStatus.value.isPaused = false
      return true
    }

    return false
  }

  /**
   * 添加扫描数据点
   * @param {number} current - 电流值
   * @param {number} field - 磁场值
   */
  function addScanDataPoint(current, field) {
    const maxPoints = scanData.value.maxPoints

    // 添加新数据点
    scanData.value.current.push(current)
    scanData.value.field.push(field)
    scanData.value.timestamps.push(Date.now())

    // 如果超过最大点数，移除旧数据
    if (scanData.value.current.length > maxPoints) {
      scanData.value.current.shift()
      scanData.value.field.shift()
      scanData.value.timestamps.shift()
    }
  }

  /**
   * 清除扫描数据
   */
  function clearScanData() {
    scanData.value.current = []
    scanData.value.field = []
    scanData.value.timestamps = []
  }

  /**
   * 导出扫描数据为CSV
   * @returns {string} CSV格式数据
   */
  function exportScanData() {
    const headers = ['时间戳', '电流(A)', '磁场(mT)']
    const rows = scanData.value.current.map((current, index) => {
      const timestamp = new Date(scanData.value.timestamps[index]).toISOString()
      const field = scanData.value.field[index]
      return [timestamp, current.toFixed(4), field.toFixed(2)]
    })

    return [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n')
  }

  /**
   * 保存自定义预设
   * @param {Object} preset - 预设配置
   * @returns {boolean} 保存是否成功
   */
  function savePreset(preset) {
    // 验证预设
    if (!preset.name || !preset.config) {
      showError('预设配置不完整')
      return false
    }

    // 检查是否已存在同名预设
    const existingIndex = customPresets.value.findIndex(p => p.name === preset.name)
    if (existingIndex >= 0) {
      // 更新现有预设
      customPresets.value[existingIndex] = {
        ...customPresets.value[existingIndex],
        ...preset,
        updatedAt: new Date().toISOString()
      }
    } else {
      // 添加新预设
      customPresets.value.push({
        ...preset,
        id: `custom_${Date.now()}`,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      })
    }

    // 保存到 localStorage
    savePresetsToStorage()
    return true
  }

  /**
   * 加载预设
   * @param {string} presetId - 预设ID
   * @returns {Object|null} 预设配置
   */
  function loadPreset(presetId) {
    const preset = allPresets.value.find(p => p.id === presetId)
    if (!preset) {
      showError('预设不存在')
      return null
    }

    // 应用预设配置
    scanConfig.value = { ...scanConfig.value, ...preset.config }
    return preset
  }

  /**
   * 删除自定义预设
   * @param {string} presetId - 预设ID
   * @returns {boolean} 删除是否成功
   */
  function deletePreset(presetId) {
    const index = customPresets.value.findIndex(p => p.id === presetId)
    if (index < 0) {
      showError('预设不存在')
      return false
    }

    customPresets.value.splice(index, 1)
    savePresetsToStorage()
    return true
  }

  /**
   * 保存预设到 localStorage
   */
  function savePresetsToStorage() {
    try {
      localStorage.setItem('electromagnet_presets', JSON.stringify(customPresets.value))
    } catch (error) {
      console.error('Failed to save presets:', error)
    }
  }

  /**
   * 从 localStorage 加载预设
   */
  function loadPresetsFromStorage() {
    try {
      const stored = localStorage.getItem('electromagnet_presets')
      if (stored) {
        customPresets.value = JSON.parse(stored)
      }
    } catch (error) {
      console.error('Failed to load presets:', error)
    }
  }

  /**
   * 计算扫描路径
   * @param {Object} config - 扫描配置
   * @returns {Array} 扫描路径点数组
   */
  function calculateScanPath(config) {
    const path = []
    const { mode, startCurrent, endCurrent, stepCount, stepSize, scanRate } = config

    if (mode === 'linear') {
      // 线性扫描路径
      const steps = Math.abs(endCurrent - startCurrent) / scanRate
      const direction = endCurrent > startCurrent ? 1 : -1

      for (let i = 0; i <= steps; i++) {
        const current = startCurrent + direction * scanRate * i
        path.push({
          step: i,
          current: current,
          field: calculateField(current),
          time: i * (1 / scanRate) // 假设每步1秒
        })
      }
    } else if (mode === 'step') {
      // 步进扫描路径
      const totalSteps = stepCount || Math.ceil(Math.abs(endCurrent - startCurrent) / stepSize)
      const step = (endCurrent - startCurrent) / (totalSteps - 1)

      for (let i = 0; i < totalSteps; i++) {
        const current = startCurrent + step * i
        path.push({
          step: i,
          current: current,
          field: calculateField(current),
          time: i * (config.stepDelay || 0.5)
        })
      }
    } else if (mode === 'custom') {
      // 自定义扫描路径（如磁滞回线）
      const cycles = config.cycles || 1
      const stepsPerCycle = 100
      const step = (endCurrent - startCurrent) / stepsPerCycle

      for (let cycle = 0; cycle < cycles; cycle++) {
        // 正向扫描
        for (let i = 0; i <= stepsPerCycle; i++) {
          const current = startCurrent + step * i
          path.push({
            step: path.length,
            current: current,
            field: calculateField(current),
            time: path.length * 0.1,
            cycle: cycle + 1,
            direction: 'forward'
          })
        }

        // 反向扫描
        for (let i = stepsPerCycle; i >= 0; i--) {
          const current = startCurrent + step * i
          path.push({
            step: path.length,
            current: current,
            field: calculateField(current),
            time: path.length * 0.1,
            cycle: cycle + 1,
            direction: 'backward'
          })
        }
      }
    }

    return path
  }

  /**
   * 验证扫描参数
   * @param {Object} config - 扫描配置
   * @returns {Object} 验证结果 {valid: boolean, errors: string[]}
   */
  function validateScanParameters(config) {
    const errors = []

    // 检查起始电流范围
    if (config.startCurrent < currentLimits.value.min || config.startCurrent > currentLimits.value.max) {
      errors.push(`起始电流超出范围 (${currentLimits.value.min}A ~ ${currentLimits.value.max}A)`)
    }

    // 检查终止电流范围
    if (config.endCurrent < currentLimits.value.min || config.endCurrent > currentLimits.value.max) {
      errors.push(`终止电流超出范围 (${currentLimits.value.min}A ~ ${currentLimits.value.max}A)`)
    }

    // 检查起始和终止电流是否相同
    if (Math.abs(config.startCurrent - config.endCurrent) < 0.001) {
      errors.push('终止电流不能等于起始电流')
    }

    // 线性扫描模式验证
    if (config.mode === 'linear') {
      if (!config.scanRate || config.scanRate <= 0) {
        errors.push('扫描速率必须大于0')
      } else if (config.scanRate > 1) {
        errors.push('扫描速率过高，建议不超过1A/s')
      }
    }

    // 步进扫描模式验证
    if (config.mode === 'step') {
      if (!config.stepCount || config.stepCount < 2) {
        errors.push('步数至少为2')
      } else if (config.stepCount > 1000) {
        errors.push('步数过多，建议不超过1000')
      }

      if (!config.stepDelay || config.stepDelay < 0.1) {
        errors.push('步间延时不小于0.1s')
      }
    }

    // 自定义扫描模式验证
    if (config.mode === 'custom') {
      if (!config.cycles || config.cycles < 1) {
        errors.push('循环次数至少为1')
      }
    }

    return {
      valid: errors.length === 0,
      errors
    }
  }

  /**
   * 上传校准曲线
   * @param {Array} points - 校准点数组 [{current, field}]
   * @returns {Promise<boolean>} 上传是否成功
   */
  async function uploadCalibration(points) {
    const result = await request({
      method: 'POST',
      url: '/electromagnet/calibrate',
      data: { points },
      loadingKey: 'uploadCalibration',
      onLoading: setLoading,
      onError: showError
    })

    if (result.success) {
      calibrationCurve.value.points = points
      calibrationCurve.value.coefficients = result.data?.coefficients
      calibrationCurve.value.lastCalibrated = new Date().toISOString()
      return true
    }

    return false
  }

  /**
   * 获取校准曲线
   * @returns {Promise<Object|null>} 校准曲线数据
   */
  async function fetchCalibration() {
    const result = await request({
      method: 'GET',
      url: '/electromagnet/calibration',
      loadingKey: 'fetchCalibration',
      onLoading: setLoading,
      onError: showError
    })

    if (result.success && result.data) {
      calibrationCurve.value = {
        points: result.data.points || [],
        coefficients: result.data.coefficients,
        lastCalibrated: result.data.last_calibrated
      }
      return result.data
    }

    return null
  }

  /**
   * 校准数据验证
   * @param {Array} points - 校准点数组
   * @returns {Promise<Object|null>} 验证结果
   */
  async function validateCalibration(points) {
    const result = await request({
      method: 'POST',
      url: '/electromagnet/calibration/validate',
      data: { points },
      loadingKey: 'validateCalibration',
      onLoading: setLoading,
      onError: showError
    })

    return result.success ? result.data : null
  }

  /**
   * 清除校准数据
   * @returns {Promise<boolean>} 清除是否成功
   */
  async function clearCalibration() {
    const result = await request({
      method: 'DELETE',
      url: '/electromagnet/calibration',
      loadingKey: 'clearCalibration',
      onLoading: setLoading,
      onError: showError
    })

    if (result.success) {
      calibrationCurve.value = {
        points: [],
        coefficients: null,
        lastCalibrated: null
      }
      return true
    }

    return false
  }

  /**
   * 执行校准
   * @param {Array} points - 校准点数组
   * @returns {Promise<Object|null>} 校准结果
   */
  async function performCalibration(points) {
    const result = await request({
      method: 'POST',
      url: '/electromagnet/calibration/perform',
      data: { points },
      loadingKey: 'performCalibration',
      onLoading: setLoading,
      onError: showError
    })

    if (result.success) {
      calibrationCurve.value.coefficients = result.data?.coefficients
      calibrationCurve.value.lastCalibrated = new Date().toISOString()
      return result.data
    }

    return null
  }

  /**
   * 根据电流计算磁场强度
   * @param {number} current - 电流值
   * @returns {number} 磁场强度 (mT)
   */
  function calculateField(current) {
    if (!calibrationCurve.value.coefficients) {
      // 如果没有校准系数，使用线性近似
      return current * 100 // 假设 1A = 100mT
    }

    const coefs = calibrationCurve.value.coefficients
    // 假设使用二次多项式拟合: field = a*current^2 + b*current + c
    return coefs.a * current * current + coefs.b * current + coefs.c
  }

  /**
   * 根据磁场强度计算电流
   * @param {number} field - 磁场强度 (mT)
   * @returns {number} 电流值 (A)
   */
  function calculateCurrent(field) {
    if (!calibrationCurve.value.coefficients) {
      // 如果没有校准系数，使用线性近似
      return field / 100 // 假设 1A = 100mT
    }

    const coefs = calibrationCurve.value.coefficients
    // 求解二次方程: a*current^2 + b*current + (c - field) = 0
    const a = coefs.a
    const b = coefs.b
    const c = coefs.c - field

    if (Math.abs(a) < 1e-10) {
      // 线性情况
      return -c / b
    }

    // 二次方程求根
    const discriminant = b * b - 4 * a * c
    if (discriminant < 0) {
      return NaN
    }

    const sqrtDisc = Math.sqrt(discriminant)
    const root1 = (-b + sqrtDisc) / (2 * a)
    const root2 = (-b - sqrtDisc) / (2 * a)

    // 选择在合理范围内的根
    if (root1 >= currentLimits.value.min && root1 <= currentLimits.value.max) {
      return root1
    }
    if (root2 >= currentLimits.value.min && root2 <= currentLimits.value.max) {
      return root2
    }

    return NaN
  }

  /**
   * 初始化
   */
  function init() {
    fetchStatus()
    fetchCalibration()
    loadPresetsFromStorage()
  }

  /**
   * 清理
   */
  function cleanup() {
    wsManager.disconnect()
    clearScanData()
  }

  return {
    // 基础状态（从 useDeviceBase）
    isConnected,
    isConnecting,
    status,
    alarmMessage,
    loading,
    canControl,

    // 电磁铁特有状态
    currentCurrent,
    currentField,
    targetCurrent,
    currentLimits,
    scanConfig,
    scanStatus,
    scanData,
    scanPresets,
    customPresets,
    calibrationCurve,

    // WebSocket 状态
    wsConnected: wsManager.wsConnected,

    // Getters
    isScanning,
    isPaused,
    estimatedRemainingTime,
    scanProgressPercent,
    allPresets,
    calibrationStatus,
    formattedField,
    formattedCurrent,

    // Actions
    clearAlarm,
    showError,
    fetchStatus,
    connectElectromagnet,
    disconnectElectromagnet,
    setCurrent,
    setField,
    emergencyStop,
    resetEmergency,
    resetOvercurrent,
    configureScan,
    validateScanConfig,
    startScan,
    stopScan,
    pauseScan,
    resumeScan,
    addScanDataPoint,
    clearScanData,
    exportScanData,
    savePreset,
    loadPreset,
    deletePreset,
    calculateScanPath,
    validateScanParameters,
    uploadCalibration,
    fetchCalibration,
    validateCalibration,
    clearCalibration,
    performCalibration,
    calculateField,
    calculateCurrent,
    init,
    cleanup
  }
})
