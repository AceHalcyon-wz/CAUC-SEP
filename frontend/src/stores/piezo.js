/**
 * @file piezo.js
 * @path src/stores/
 * @description 压电陶瓷控制器状态管理Store，封装校准、控制模式、电压位移等操作
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

export const usePiezoStore = defineStore('piezo', () => {
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
    canControl: _baseCanControl,
    showError,
    clearAlarm,
    setLoading,
    resetState,
    _updateStatus
  } = useDeviceBase('piezo')

  // ==================== 压电陶瓷特有状态 ====================

  /** 当前电压 (V) */
  const currentVoltage = ref(0)

  /** 当前位移 (nm) */
  const currentDisplacement = ref(0)

  /** 目标电压 (V) */
  const targetVoltage = ref(0)

  /** 控制模式 ('voltage' | 'displacement') */
  const controlMode = ref('voltage')

  /** 校准数据 */
  const calibrationData = ref({
    points: [],
    coefficients: null,
    fitted: false,
    lastCalibrated: null
  })

  /** 校准状态 */
  const calibrationStatus = ref('idle')

  /** 电压范围限制 */
  const voltageLimits = ref({
    min: 0,
    max: 150
  })

  /** 位移范围限制 (nm) */
  const displacementLimits = ref({
    min: 0,
    max: 20000
  })

  /** 设备信息 */
  const deviceInfo = ref({
    model: '',
    serialNumber: '',
    firmwareVersion: ''
  })

  /** 历史数据（用于图表） */
  const historyData = ref([])
  const maxHistoryPoints = 500

  /** 校准历史版本 */
  const calibrationHistory = ref([])

  /** 最大历史版本数量 */
  const maxHistoryVersions = 20

  // ==================== 计算属性 ====================

  /**
   * 是否允许控制压电陶瓷
   * 覆盖基础canControl，增加状态检查
   */
  const canControl = computed(() => {
    return isConnected.value && status.value === 'ready'
  })

  /**
   * 是否已校准
   */
  const isCalibrated = computed(() => {
    return calibrationData.value.fitted && calibrationData.value.coefficients !== null
  })

  /**
   * 电压状态类型（用于UI显示）
   */
  const voltageStatusType = computed(() => {
    const voltage = currentVoltage.value
    if (voltage >= voltageLimits.value.max * 0.95) return 'danger'
    if (voltage >= voltageLimits.value.max * 0.8) return 'warning'
    return 'success'
  })

  /**
   * 校准进度（已添加点数/建议点数）
   */
  const calibrationProgress = computed(() => {
    const points = calibrationData.value.points.length
    const recommended = 5
    return Math.min(100, Math.round((points / recommended) * 100))
  })

  /**
   * 是否正在校准
   */
  const isCalibrating = computed(() => {
    return calibrationStatus.value === 'calibrating'
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
      piezoWS.send({ type: 'pong' })
      return
    }

    // 处理设备状态更新
    if (data.voltage !== undefined) {
      currentVoltage.value = data.voltage
      targetVoltage.value = data.target_voltage ?? targetVoltage.value
      status.value = data.status ?? status.value
      isConnected.value = data.status !== 'disconnected'
    }

    // 处理位移更新
    if (data.displacement !== undefined) {
      currentDisplacement.value = data.displacement
    }

    // 处理控制模式更新
    if (data.control_mode !== undefined) {
      controlMode.value = data.control_mode
    }

    // 处理校准状态更新
    if (data.calibration_status !== undefined) {
      calibrationStatus.value = data.calibration_status
    }

    // 添加历史数据
    if (data.voltage !== undefined || data.displacement !== undefined) {
      addHistoryData({
        voltage: data.voltage ?? currentVoltage.value,
        displacement: data.displacement ?? currentDisplacement.value,
        timestamp: data.timestamp || Date.now()
      })
    }

    // 处理错误消息
    if (data.error) {
      console.error('WebSocket error:', data.error)
      showError(data.error)
    }
  }

  /**
   * 添加历史数据
   *
   * @param {Object} data - 数据点
   */
  function addHistoryData(data) {
    historyData.value.push({
      timestamp: data.timestamp || Date.now(),
      voltage: data.voltage,
      displacement: data.displacement
    })

    // 限制历史数据点数量
    if (historyData.value.length > maxHistoryPoints) {
      historyData.value = historyData.value.slice(-maxHistoryPoints)
    }
  }

  /**
   * 初始化WebSocket连接
   */
  const piezoWS = useWebSocket({
    url: `${WS_BASE_URL}/ws/piezo`,
    onMessage: handleWebSocketMessage,
    onOpen: () => {
      console.log('Piezo WebSocket connected')
    },
    onClose: () => {
      console.log('Piezo WebSocket disconnected')
    },
    onError: (error) => {
      console.error('Piezo WebSocket error:', error)
    },
    reconnectInterval: 3000,
    heartbeatInterval: 30000
  })

  // ==================== API 操作方法 ====================

  /**
   * 获取压电陶瓷状态
   *
   * @returns {Promise<Object|null>} 状态数据或null
   */
  async function fetchStatus() {
    const result = await get('/api/v1/piezo/status', null, {
      onError: (msg) => {
        console.error('Failed to fetch piezo status:', msg)
        isConnected.value = false
        status.value = 'disconnected'
      }
    })

    if (result.success && result.data) {
      const data = result.data
      status.value = data.status
      currentVoltage.value = data.voltage ?? 0
      currentDisplacement.value = data.displacement ?? 0
      targetVoltage.value = data.target_voltage ?? 0
      controlMode.value = data.control_mode ?? 'voltage'
      isConnected.value = data.connected
      return data
    }

    return null
  }

  /**
   * 连接压电陶瓷设备
   *
   * @returns {Promise<boolean>} 连接是否成功
   */
  async function connect() {
    isConnecting.value = true

    const result = await post('/api/v1/piezo/connect', null, {
      onError: (msg) => showError('连接错误: ' + msg)
    })

    if (result.success && result.data?.success) {
      isConnected.value = true
      status.value = result.data.status
      await fetchStatus()
      piezoWS.connect()
      isConnecting.value = false
      return true
    }

    isConnecting.value = false
    showError('连接失败: ' + (result.message || '未知错误'))
    return false
  }

  /**
   * 断开压电陶瓷设备连接
   *
   * @returns {Promise<Object|null>} 断开结果
   */
  async function disconnect() {
    piezoWS.disconnect()

    const result = await post('/api/piezo/disconnect', null, {
      onError: (msg) => showError('断开错误: ' + msg)
    })

    isConnected.value = false
    status.value = 'disconnected'

    return result.success ? result.data : null
  }

  /**
   * 获取当前电压
   *
   * @returns {Promise<number|null>} 当前电压值
   */
  async function fetchVoltage() {
    const result = await get('/api/piezo/voltage', null, {
      onError: (msg) => showError('获取电压错误: ' + msg)
    })

    if (result.success && result.data !== undefined) {
      currentVoltage.value = result.data.voltage ?? result.data
      return currentVoltage.value
    }

    return null
  }

  /**
   * 获取当前位移
   *
   * @returns {Promise<number|null>} 当前位移值 (nm)
   */
  async function fetchDisplacement() {
    const result = await get('/api/piezo/displacement', null, {
      onError: (msg) => showError('获取位移错误: ' + msg)
    })

    if (result.success && result.data !== undefined) {
      currentDisplacement.value = result.data.displacement ?? result.data
      return currentDisplacement.value
    }

    return null
  }

  /**
   * 设置电压
   *
   * @param {number} voltage - 目标电压 (V)
   * @returns {Promise<boolean>} 设置是否成功
   */
  async function setVoltage(voltage) {
    if (!canControl.value) {
      showError('压电陶瓷未就绪，无法设置电压')
      return false
    }

    // 电压范围验证
    if (voltage < voltageLimits.value.min || voltage > voltageLimits.value.max) {
      showError(`电压超出范围 (${voltageLimits.value.min}-${voltageLimits.value.max}V)`)
      return false
    }

    const result = await post('/api/piezo/voltage', { voltage }, {
      onLoading: setLoading,
      loadingKey: 'setVoltage',
      onError: (msg) => showError('设置电压错误: ' + msg)
    })

    if (result.success) {
      targetVoltage.value = voltage
      return true
    }

    return false
  }

  /**
   * 设置位移
   *
   * @param {number} displacement - 目标位移 (nm)
   * @returns {Promise<boolean>} 设置是否成功
   */
  async function setDisplacement(displacement) {
    if (!canControl.value) {
      showError('压电陶瓷未就绪，无法设置位移')
      return false
    }

    // 检查是否已校准
    if (!isCalibrated.value) {
      showError('请先完成校准后再设置位移')
      return false
    }

    // 位移范围验证
    if (displacement < displacementLimits.value.min || displacement > displacementLimits.value.max) {
      showError(`位移超出范围 (${displacementLimits.value.min}-${displacementLimits.value.max}nm)`)
      return false
    }

    const result = await post('/api/piezo/displacement', { displacement }, {
      onLoading: setLoading,
      loadingKey: 'setDisplacement',
      onError: (msg) => showError('设置位移错误: ' + msg)
    })

    if (result.success) {
      return true
    }

    return false
  }

  /**
   * 获取控制模式
   *
   * @returns {Promise<string|null>} 控制模式
   */
  async function fetchMode() {
    const result = await get('/api/piezo/mode', null, {
      onError: (msg) => showError('获取控制模式错误: ' + msg)
    })

    if (result.success && result.data) {
      controlMode.value = result.data.mode ?? result.data
      return controlMode.value
    }

    return null
  }

  /**
   * 设置控制模式
   *
   * @param {string} mode - 控制模式 ('voltage' | 'displacement')
   * @returns {Promise<boolean>} 设置是否成功
   */
  async function setMode(mode) {
    if (!canControl.value) {
      showError('压电陶瓷未就绪，无法设置模式')
      return false
    }

    // 位移模式需要先校准
    if (mode === 'displacement' && !isCalibrated.value) {
      showError('切换到位移模式前请先完成校准')
      return false
    }

    const result = await post('/api/piezo/mode', { mode }, {
      onLoading: setLoading,
      loadingKey: 'setMode',
      onError: (msg) => showError('设置控制模式错误: ' + msg)
    })

    if (result.success) {
      controlMode.value = mode
      return true
    }

    return false
  }

  /**
   * 归零操作
   *
   * @returns {Promise<boolean>} 归零是否成功
   */
  async function zero() {
    if (!canControl.value) {
      showError('压电陶瓷未就绪，无法归零')
      return false
    }

    const result = await post('/api/piezo/zero', null, {
      onLoading: setLoading,
      loadingKey: 'zero',
      onError: (msg) => showError('归零错误: ' + msg)
    })

    if (result.success && result.data?.success) {
      currentVoltage.value = 0
      targetVoltage.value = 0
      currentDisplacement.value = 0
      return true
    }

    return false
  }

  /**
   * 最大伸展操作
   *
   * @returns {Promise<boolean>} 操作是否成功
   */
  async function maxExtend() {
    if (!canControl.value) {
      showError('压电陶瓷未就绪，无法执行最大伸展')
      return false
    }

    const result = await post('/api/piezo/max_extend', null, {
      onLoading: setLoading,
      loadingKey: 'maxExtend',
      onError: (msg) => showError('最大伸展错误: ' + msg)
    })

    if (result.success && result.data?.success) {
      currentVoltage.value = voltageLimits.value.max
      targetVoltage.value = voltageLimits.value.max
      return true
    }

    return false
  }

  // ==================== 校准相关方法 ====================

  /**
   * 添加校准点
   *
   * @param {Object} point - 校准点数据
   * @param {number} point.voltage - 电压值 (V)
   * @param {number} point.displacement - 位移值 (nm)
   * @returns {Promise<boolean>} 添加是否成功
   */
  async function addCalibrationPoint(point) {
    if (!canControl.value) {
      showError('压电陶瓷未就绪，无法添加校准点')
      return false
    }

    const result = await post('/api/piezo/calibrate/point', {
      voltage: point.voltage,
      displacement: point.displacement
    }, {
      onLoading: setLoading,
      loadingKey: 'addCalibrationPoint',
      onError: (msg) => showError('添加校准点错误: ' + msg)
    })

    if (result.success && result.data) {
      // 更新本地校准数据
      calibrationData.value.points.push({
        voltage: point.voltage,
        displacement: point.displacement,
        timestamp: Date.now()
      })
      return true
    }

    return false
  }

  /**
   * 执行校准拟合
   *
   * @param {string} fitType - 拟合类型 ('linear' | 'polynomial')
   * @returns {Promise<Object|null>} 拟合结果
   */
  async function performCalibration(fitType = 'linear') {
    if (calibrationData.value.points.length < 2) {
      showError('校准点不足，至少需要2个点')
      return null
    }

    calibrationStatus.value = 'calibrating'

    const result = await post('/api/piezo/calibrate/perform', {
      fit_type: fitType
    }, {
      onLoading: setLoading,
      loadingKey: 'performCalibration',
      onError: (msg) => {
        showError('校准拟合错误: ' + msg)
        calibrationStatus.value = 'error'
      }
    })

    if (result.success && result.data) {
      calibrationData.value.coefficients = result.data.coefficients
      calibrationData.value.fitted = true
      calibrationData.value.lastCalibrated = Date.now()
      calibrationStatus.value = 'completed'
      return result.data
    }

    calibrationStatus.value = 'error'
    return null
  }

  /**
   * 获取校准数据
   *
   * @returns {Promise<Object|null>} 校准数据
   */
  async function fetchCalibrationData() {
    const result = await get('/api/piezo/calibrate/data', null, {
      onError: (msg) => showError('获取校准数据错误: ' + msg)
    })

    if (result.success && result.data) {
      calibrationData.value = {
        points: result.data.points || [],
        coefficients: result.data.coefficients || null,
        fitted: result.data.fitted || false,
        lastCalibrated: result.data.last_calibrated || null
      }
      return calibrationData.value
    }

    return null
  }

  /**
   * 清除校准数据
   *
   * @returns {Promise<boolean>} 清除是否成功
   */
  async function clearCalibration() {
    const result = await del('/api/piezo/calibrate', {
      onLoading: setLoading,
      loadingKey: 'clearCalibration',
      onError: (msg) => showError('清除校准数据错误: ' + msg)
    })

    if (result.success) {
      calibrationData.value = {
        points: [],
        coefficients: null,
        fitted: false,
        lastCalibrated: null
      }
      calibrationStatus.value = 'idle'
      return true
    }

    return false
  }

  /**
   * 删除单个校准点
   *
   * @param {number} index - 校准点索引
   * @returns {boolean} 删除是否成功
   */
  function removeCalibrationPoint(index) {
    if (index >= 0 && index < calibrationData.value.points.length) {
      calibrationData.value.points.splice(index, 1)
      return true
    }
    return false
  }

  // ==================== 辅助方法 ====================

  /**
   * 根据位移计算电压（使用校准系数）
   *
   * @param {number} displacement - 目标位移 (nm)
   * @returns {number|null} 计算得到的电压值
   */
  function calculateVoltageFromDisplacement(displacement) {
    if (!isCalibrated.value) {
      return null
    }

    const coef = calibrationData.value.coefficients
    if (coef.type === 'linear') {
      // linear: displacement = a * voltage + b
      // voltage = (displacement - b) / a
      return (displacement - coef.b) / coef.a
    } else if (coef.type === 'polynomial') {
      // 多项式拟合需要数值求解
      // 简化处理：使用二分法
      let low = voltageLimits.value.min
      let high = voltageLimits.value.max
      const tolerance = 0.01

      for (let i = 0; i < 100; i++) {
        const mid = (low + high) / 2
        const calcDisp = evaluatePolynomial(mid, coef.coefficients)
        if (Math.abs(calcDisp - displacement) < tolerance) {
          return mid
        }
        if (calcDisp < displacement) {
          low = mid
        } else {
          high = mid
        }
      }

      return (low + high) / 2
    }

    return null
  }

  /**
   * 计算多项式值
   *
   * @param {number} x - 输入值
   * @param {Array<number>} coefficients - 多项式系数 [a0, a1, a2, ...]
   * @returns {number} 计算结果
   */
  function evaluatePolynomial(x, coefficients) {
    let result = 0
    for (let i = 0; i < coefficients.length; i++) {
      result += coefficients[i] * Math.pow(x, i)
    }
    return result
  }

  /**
   * 清除历史数据
   */
  function clearHistory() {
    historyData.value = []
  }

  // ==================== 校准数据导入导出 ====================

  /**
   * 导出校准数据为CSV格式
   *
   * @returns {string} CSV格式数据
   */
  function exportCalibrationToCSV() {
    const points = calibrationData.value.points
    if (points.length === 0) {
      return ''
    }

    const lines = [
      '时间戳,电压(V),位移(nm),位移(μm)',
      ...points.map(p =>
        `${p.timestamp || Date.now()},${p.voltage.toFixed(3)},${p.displacement.toFixed(3)},${(p.displacement / 1000).toFixed(6)}`
      )
    ]

    return lines.join('\n')
  }

  /**
   * 导出校准数据为JSON格式
   *
   * @returns {string} JSON格式数据
   */
  function exportCalibrationToJSON() {
    return JSON.stringify({
      metadata: {
        exportTime: new Date().toISOString(),
        pointCount: calibrationData.value.points.length,
        fitted: calibrationData.value.fitted,
        lastCalibrated: calibrationData.value.lastCalibrated,
        coefficients: calibrationData.value.coefficients
      },
      points: calibrationData.value.points.map(p => ({
        voltage: p.voltage,
        displacement: p.displacement,
        displacement_um: p.displacement / 1000,
        timestamp: p.timestamp
      }))
    }, null, 2)
  }

  /**
   * 从CSV数据导入校准数据
   *
   * @param {string} csvContent - CSV格式数据
   * @returns {boolean} 导入是否成功
   */
  function importCalibrationFromCSV(csvContent) {
    try {
      const lines = csvContent.trim().split('\n')
      const points = []

      // 跳过标题行
      const startIndex = lines[0].includes('电压') || lines[0].includes('voltage') ? 1 : 0

      for (let i = startIndex; i < lines.length; i++) {
        const parts = lines[i].split(',').map(s => s.trim())
        if (parts.length >= 2) {
          const voltage = parseFloat(parts[1]) // 第二列是电压
          const displacement = parseFloat(parts[2]) // 第三列是位移(nm)

          if (!isNaN(voltage) && !isNaN(displacement)) {
            points.push({
              voltage: voltage,
              displacement: displacement,
              timestamp: Date.now()
            })
          }
        }
      }

      if (points.length > 0) {
        calibrationData.value.points = points
        calibrationData.value.fitted = false
        calibrationData.value.coefficients = null
        return true
      }

      return false
    } catch (error) {
      console.error('Failed to import calibration from CSV:', error)
      showError('导入CSV失败: ' + error.message)
      return false
    }
  }

  /**
   * 从JSON数据导入校准数据
   *
   * @param {string} jsonContent - JSON格式数据
   * @returns {boolean} 导入是否成功
   */
  function importCalibrationFromJSON(jsonContent) {
    try {
      const data = JSON.parse(jsonContent)

      if (data.points && Array.isArray(data.points)) {
        calibrationData.value.points = data.points.map(p => ({
          voltage: p.voltage,
          displacement: p.displacement,
          timestamp: p.timestamp || Date.now()
        }))

        // 恢复元数据
        if (data.metadata) {
          calibrationData.value.fitted = data.metadata.fitted || false
          calibrationData.value.lastCalibrated = data.metadata.lastCalibrated || null
          calibrationData.value.coefficients = data.metadata.coefficients || null
        }

        return true
      }

      return false
    } catch (error) {
      console.error('Failed to import calibration from JSON:', error)
      showError('导入JSON失败: ' + error.message)
      return false
    }
  }

  /**
   * 下载校准数据文件
   *
   * @param {string} format - 格式 ('csv' | 'json')
   * @param {string} filename - 文件名（不含扩展名）
   */
  function downloadCalibrationFile(format = 'csv', filename = 'calibration') {
    let content = ''
    let mimeType = ''
    let extension = ''

    if (format === 'csv') {
      content = exportCalibrationToCSV()
      mimeType = 'text/csv;charset=utf-8;'
      extension = 'csv'
    } else if (format === 'json') {
      content = exportCalibrationToJSON()
      mimeType = 'application/json;charset=utf-8;'
      extension = 'json'
    }

    if (!content) {
      showError('没有校准数据可导出')
      return
    }

    const blob = new Blob([content], { type: mimeType })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)

    link.setAttribute('href', url)
    link.setAttribute('download', `${filename}.${extension}`)
    link.style.visibility = 'hidden'

    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    URL.revokeObjectURL(url)
  }

  // ==================== 校准历史版本管理 ====================

  /**
   * 保存当前校准到历史版本
   *
   * @param {string} mode - 校准模式
   * @returns {boolean} 保存是否成功
   */
  function saveCalibrationToHistory(mode = 'linear') {
    if (calibrationData.value.points.length === 0) {
      return false
    }

    const historyItem = {
      id: Date.now(),
      timestamp: Date.now(),
      mode: mode,
      points: [...calibrationData.value.points],
      coefficients: calibrationData.value.coefficients ? { ...calibrationData.value.coefficients } : null,
      fitted: calibrationData.value.fitted,
      r2: calculateR2()
    }

    calibrationHistory.value.unshift(historyItem)

    // 限制历史版本数量
    if (calibrationHistory.value.length > maxHistoryVersions) {
      calibrationHistory.value.pop()
    }

    // 保存到本地存储
    saveHistoryToLocalStorage()

    return true
  }

  /**
   * 从历史版本恢复校准数据
   *
   * @param {number} historyId - 历史版本ID
   * @returns {boolean} 恢复是否成功
   */
  function restoreCalibrationFromHistory(historyId) {
    const historyItem = calibrationHistory.value.find(item => item.id === historyId)

    if (!historyItem) {
      showError('未找到历史版本')
      return false
    }

    calibrationData.value.points = [...historyItem.points]
    calibrationData.value.coefficients = historyItem.coefficients ? { ...historyItem.coefficients } : null
    calibrationData.value.fitted = historyItem.fitted
    calibrationData.value.lastCalibrated = historyItem.timestamp

    return true
  }

  /**
   * 删除历史版本
   *
   * @param {number} historyId - 历史版本ID
   * @returns {boolean} 删除是否成功
   */
  function deleteCalibrationHistory(historyId) {
    const index = calibrationHistory.value.findIndex(item => item.id === historyId)

    if (index >= 0) {
      calibrationHistory.value.splice(index, 1)
      saveHistoryToLocalStorage()
      return true
    }

    return false
  }

  /**
   * 清空所有历史版本
   */
  function clearCalibrationHistory() {
    calibrationHistory.value = []
    localStorage.removeItem('piezo_calibration_history')
  }

  /**
   * 计算当前校准的R²值
   *
   * @returns {number} R²值
   */
  function calculateR2() {
    const points = calibrationData.value.points
    if (points.length < 2 || !calibrationData.value.fitted) {
      return 0
    }

    const n = points.length
    const sumY = points.reduce((acc, p) => acc + p.displacement, 0)
    const yMean = sumY / n

    let ssTotal = 0
    let ssResidual = 0

    points.forEach(p => {
      const predicted = calculateDisplacementFromVoltage(p.voltage)
      ssTotal += Math.pow(p.displacement - yMean, 2)
      ssResidual += Math.pow(p.displacement - predicted, 2)
    })

    return ssTotal === 0 ? 1 : 1 - (ssResidual / ssTotal)
  }

  /**
   * 根据电压计算位移（使用校准系数）
   *
   * @param {number} voltage - 电压值 (V)
   * @returns {number} 计算得到的位移值 (nm)
   */
  function calculateDisplacementFromVoltage(voltage) {
    if (!calibrationData.value.fitted || !calibrationData.value.coefficients) {
      return voltage * 100 // 默认线性关系 100nm/V
    }

    const coef = calibrationData.value.coefficients

    if (coef.type === 'linear') {
      // linear: displacement = a * voltage + b
      return coef.a * voltage + coef.b
    } else if (coef.type === 'polynomial') {
      // 多项式拟合
      return evaluatePolynomial(voltage, coef.coefficients)
    }

    return voltage * 100
  }

  /**
   * 保存历史到本地存储
   */
  function saveHistoryToLocalStorage() {
    try {
      localStorage.setItem('piezo_calibration_history', JSON.stringify(calibrationHistory.value))
    } catch (error) {
      console.error('Failed to save calibration history to localStorage:', error)
    }
  }

  /**
   * 从本地存储加载历史
   */
  function loadHistoryFromLocalStorage() {
    try {
      const saved = localStorage.getItem('piezo_calibration_history')
      if (saved) {
        calibrationHistory.value = JSON.parse(saved)
      }
    } catch (error) {
      console.error('Failed to load calibration history from localStorage:', error)
    }
  }

  // ==================== 生命周期方法 ====================

  /**
   * 初始化Store
   */
  function init() {
    fetchStatus()
    fetchCalibrationData()
    loadHistoryFromLocalStorage()
  }

  /**
   * 清理资源
   */
  function cleanup() {
    piezoWS.disconnect()
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

    // 压电陶瓷特有状态
    currentVoltage,
    currentDisplacement,
    targetVoltage,
    controlMode,
    calibrationData,
    calibrationStatus,
    voltageLimits,
    displacementLimits,
    deviceInfo,
    historyData,
    calibrationHistory,

    // 计算属性
    canControl,
    isCalibrated,
    voltageStatusType,
    calibrationProgress,
    isCalibrating,

    // 基础方法（来自 useDeviceBase）
    showError,
    clearAlarm,
    setLoading,

    // 设备操作方法
    fetchStatus,
    connect,
    disconnect,
    fetchVoltage,
    fetchDisplacement,
    setVoltage,
    setDisplacement,
    fetchMode,
    setMode,
    zero,
    maxExtend,

    // 校准方法
    addCalibrationPoint,
    performCalibration,
    fetchCalibrationData,
    clearCalibration,
    removeCalibrationPoint,

    // 校准数据导入导出
    exportCalibrationToCSV,
    exportCalibrationToJSON,
    importCalibrationFromCSV,
    importCalibrationFromJSON,
    downloadCalibrationFile,

    // 校准历史版本管理
    saveCalibrationToHistory,
    restoreCalibrationFromHistory,
    deleteCalibrationHistory,
    clearCalibrationHistory,

    // 辅助方法
    calculateVoltageFromDisplacement,
    calculateDisplacementFromVoltage,
    calculateR2,
    clearHistory,

    // WebSocket方法
    connectWebSocket: piezoWS.connect,
    disconnectWebSocket: piezoWS.disconnect,

    // 生命周期
    init,
    cleanup
  }
})
