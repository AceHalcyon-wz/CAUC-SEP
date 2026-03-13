/**
 * @file analysis.js
 * @path src/stores/
 * @description 实时数据分析状态管理Store，管理多设备数据同步、通道过滤、统计指标和导出功能
 * @author Agent
 * @date 2024-03-07
 * @dependencies pinia, vue
 */

import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

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
 * 设备通道配置
 * @constant {Object}
 */
const DEVICE_CHANNELS = {
  [DEVICE_TYPES.MOTOR]: [
    { id: 'position', name: '位置', unit: 'mm', color: '#409eff' },
    { id: 'velocity', name: '速度', unit: 'mm/s', color: '#67c23a' },
    { id: 'acceleration', name: '加速度', unit: 'mm/s²', color: '#e6a23c' }
  ],
  [DEVICE_TYPES.ELECTROMAGNET]: [
    { id: 'current', name: '电流', unit: 'A', color: '#409eff' },
    { id: 'field', name: '磁场强度', unit: 'T', color: '#67c23a' },
    { id: 'voltage', name: '电压', unit: 'V', color: '#e6a23c' }
  ],
  [DEVICE_TYPES.TEMPERATURE]: [
    { id: 'temperature', name: '温度', unit: '°C', color: '#f56c6c' },
    { id: 'target', name: '目标温度', unit: '°C', color: '#909399' },
    { id: 'power', name: '功率', unit: 'W', color: '#67c23a' }
  ],
  [DEVICE_TYPES.PIEZO]: [
    { id: 'voltage', name: '电压', unit: 'V', color: '#409eff' },
    { id: 'displacement', name: '位移', unit: 'μm', color: '#67c23a' }
  ],
  [DEVICE_TYPES.AMMETER]: [
    { id: 'current', name: '电流', unit: 'μA', color: '#409eff' },
    { id: 'voltage', name: '电压', unit: 'mV', color: '#67c23a' }
  ]
}

/**
 * 导出格式类型
 * @constant {Object}
 */
const EXPORT_FORMATS = {
  CSV: 'csv',
  JSON: 'json',
  XLSX: 'xlsx'
}

/**
 * 实时数据分析状态管理 Store
 *
 * 提供多设备数据同步、通道过滤、统计计算和导出功能
 */
export const useAnalysisStore = defineStore('analysis', () => {
  // ==================== 响应式状态 ====================

  /**
   * 已选择的设备列表
   * @type {import('vue').Ref<Array<string>>}
   */
  const selectedDevices = ref([])

  /**
   * 已选择的通道列表（按设备分组）
   * @type {import('vue').Ref<Object>}
   * @description 格式: { motor: ['position', 'velocity'], temperature: ['temperature'] }
   */
  const selectedChannels = ref({})

  /**
   * 数据过滤条件
   * @type {import('vue').Ref<Object>}
   */
  const filterConditions = ref({
    timeRange: {
      start: null,
      end: null,
      duration: 60000 // 默认显示最近60秒
    },
    valueRange: {
      min: null,
      max: null
    },
    samplingInterval: 100, // 采样间隔（毫秒）
    enableSmoothing: false,
    smoothingWindow: 5
  })

  /**
   * 实时数据缓冲区
   * @type {import('vue').Ref<Object>}
   * @description 格式: { motor: { position: [{timestamp, value}], velocity: [...] }, ... }
   */
  const dataBuffer = ref({})

  /**
   * 统计指标数据
   * @type {import('vue').Ref<Object>}
   */
  const statistics = ref({})

  /**
   * 同步时间轴配置
   * @type {import('vue').Ref<Object>}
   */
  const timeAxisConfig = ref({
    syncEnabled: true,
    showGrid: true,
    gridInterval: 5000, // 网格间隔（毫秒）
    timeFormat: 'HH:mm:ss',
    autoScroll: true
  })

  /**
   * 对比视图配置
   * @type {import('vue').Ref<Object>}
   */
  const comparisonConfig = ref({
    layout: 'horizontal', // 'horizontal' | 'vertical' | 'grid'
    normalizeData: false,
    showDifference: false,
    overlayMode: false
  })

  /**
   * 导出配置
   * @type {import('vue').Ref<Object>}
   */
  const exportConfig = ref({
    format: EXPORT_FORMATS.CSV,
    includeTimestamp: true,
    includeStatistics: true,
    dateFormat: 'YYYY-MM-DD HH:mm:ss',
    decimalPlaces: 4,
    separator: ',',
    encoding: 'utf-8'
  })

  /**
   * 数据缓冲区最大容量
   * @constant {number}
   */
  const MAX_BUFFER_SIZE = 10000

  /**
   * 统计计算间隔（毫秒）
   * @constant {number}
   */
  const STATISTICS_INTERVAL = 1000

  /**
   * 统计计算定时器
   * @type {number|null}
   */
  let statisticsTimer = null

  // ==================== 计算属性 ====================

  /**
   * 所有可用设备列表
   * @type {import('vue').ComputedRef<Array>}
   */
  const availableDevices = computed(() => {
    return Object.keys(DEVICE_TYPES).map(key => ({
      id: DEVICE_TYPES[key],
      name: DEVICE_NAMES[DEVICE_TYPES[key]],
      channels: DEVICE_CHANNELS[DEVICE_TYPES[key]] || []
    }))
  })

  /**
   * 当前选择的设备数量
   * @type {import('vue').ComputedRef<number>}
   */
  const selectedDeviceCount = computed(() => {
    return selectedDevices.value.length
  })

  /**
   * 当前选择的通道总数
   * @type {import('vue').ComputedRef<number>}
   */
  const selectedChannelCount = computed(() => {
    return Object.values(selectedChannels.value).reduce((sum, channels) => {
      return sum + channels.length
    }, 0)
  })

  /**
   * 是否有数据
   * @type {import('vue').ComputedRef<boolean>}
   */
  const hasData = computed(() => {
    return Object.keys(dataBuffer.value).length > 0
  })

  /**
   * 数据时间范围
   * @type {import('vue').ComputedRef<Object>}
   */
  const dataTimeRange = computed(() => {
    let minTime = Infinity
    let maxTime = -Infinity

    Object.values(dataBuffer.value).forEach(deviceData => {
      Object.values(deviceData).forEach(channelData => {
        if (channelData && channelData.length > 0) {
          const timestamps = channelData.map(d => d.timestamp)
          minTime = Math.min(minTime, ...timestamps)
          maxTime = Math.max(maxTime, ...timestamps)
        }
      })
    })

    return {
      start: minTime === Infinity ? null : minTime,
      end: maxTime === -Infinity ? null : maxTime,
      duration: minTime === Infinity ? 0 : maxTime - minTime
    }
  })

  /**
   * 过滤后的数据
   * @type {import('vue').ComputedRef<Object>}
   */
  const filteredData = computed(() => {
    const { timeRange, valueRange, samplingInterval, enableSmoothing, smoothingWindow } = filterConditions.value
    const filtered = {}

    Object.entries(dataBuffer.value).forEach(([deviceId, deviceData]) => {
      if (!selectedDevices.value.includes(deviceId)) return

      filtered[deviceId] = {}

      Object.entries(deviceData).forEach(([channelId, channelData]) => {
        if (!selectedChannels.value[deviceId]?.includes(channelId)) return

        let data = [...channelData]

        // 时间范围过滤
        if (timeRange.start || timeRange.end) {
          data = data.filter(d => {
            if (timeRange.start && d.timestamp < timeRange.start) return false
            if (timeRange.end && d.timestamp > timeRange.end) return false
            return true
          })
        }

        // 数值范围过滤
        if (valueRange.min !== null || valueRange.max !== null) {
          data = data.filter(d => {
            if (valueRange.min !== null && d.value < valueRange.min) return false
            if (valueRange.max !== null && d.value > valueRange.max) return false
            return true
          })
        }

        // 采样间隔降采样
        if (samplingInterval > 0 && data.length > 0) {
          const sampled = []
          let lastSampleTime = data[0].timestamp
          sampled.push(data[0])

          for (let i = 1; i < data.length; i++) {
            if (data[i].timestamp - lastSampleTime >= samplingInterval) {
              sampled.push(data[i])
              lastSampleTime = data[i].timestamp
            }
          }

          // 确保包含最后一个数据点
          if (data.length > 1 && sampled[sampled.length - 1] !== data[data.length - 1]) {
            sampled.push(data[data.length - 1])
          }

          data = sampled
        }

        // 平滑处理
        if (enableSmoothing && smoothingWindow > 1 && data.length >= smoothingWindow) {
          data = smoothData(data, smoothingWindow)
        }

        filtered[deviceId][channelId] = data
      })
    })

    return filtered
  })

  // ==================== 统计计算方法 ====================

  /**
   * 计算数据统计指标
   *
   * @param {Array} data - 数据数组
   * @returns {Object} 统计指标
   */
  function calculateStatistics(data) {
    if (!data || data.length === 0) {
      return {
        count: 0,
        mean: null,
        std: null,
        min: null,
        max: null,
        range: null,
        median: null,
        variance: null,
        changeRate: null,
        trend: null
      }
    }

    const values = data.map(d => d.value)
    const n = values.length

    // 基本统计
    const sum = values.reduce((a, b) => a + b, 0)
    const mean = sum / n
    const min = Math.min(...values)
    const max = Math.max(...values)
    const range = max - min

    // 方差和标准差
    const variance = values.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / n
    const std = Math.sqrt(variance)

    // 中位数
    const sorted = [...values].sort((a, b) => a - b)
    const median = n % 2 === 0
      ? (sorted[n / 2 - 1] + sorted[n / 2]) / 2
      : sorted[Math.floor(n / 2)]

    // 变化率（最后一个值相对于第一个值的变化百分比）
    const changeRate = n > 1
      ? ((values[n - 1] - values[0]) / Math.abs(values[0])) * 100
      : 0

    // 趋势分析（简单线性回归）
    const trend = calculateTrend(data)

    return {
      count: n,
      mean: mean,
      std: std,
      min: min,
      max: max,
      range: range,
      median: median,
      variance: variance,
      changeRate: changeRate,
      trend: trend
    }
  }

  /**
   * 计算数据趋势
   *
   * @param {Array} data - 数据数组
   * @returns {Object} 趋势信息
   */
  function calculateTrend(data) {
    if (data.length < 2) {
      return { direction: 'stable', slope: 0, r2: 0 }
    }

    const n = data.length
    const timestamps = data.map(d => d.timestamp)
    const values = data.map(d => d.value)

    // 标准化时间戳
    const t0 = timestamps[0]
    const x = timestamps.map(t => (t - t0) / 1000) // 转换为秒

    // 线性回归: y = a + bx
    const sumX = x.reduce((a, b) => a + b, 0)
    const sumY = values.reduce((a, b) => a + b, 0)
    const sumXY = x.reduce((acc, xi, i) => acc + xi * values[i], 0)
    const sumX2 = x.reduce((acc, xi) => acc + xi * xi, 0)

    const denominator = n * sumX2 - sumX * sumX
    const slope = denominator !== 0 ? (n * sumXY - sumX * sumY) / denominator : 0
    const intercept = (sumY - slope * sumX) / n

    // 计算 R²
    const meanY = sumY / n
    const ssTotal = values.reduce((acc, yi) => acc + Math.pow(yi - meanY, 2), 0)
    const ssResidual = values.reduce((acc, yi, i) => {
      const predicted = intercept + slope * x[i]
      return acc + Math.pow(yi - predicted, 2)
    }, 0)
    const r2 = ssTotal !== 0 ? 1 - (ssResidual / ssTotal) : 0

    // 判断趋势方向
    let direction = 'stable'
    if (Math.abs(slope) > 0.0001) {
      direction = slope > 0 ? 'increasing' : 'decreasing'
    }

    return {
      direction,
      slope,
      intercept,
      r2
    }
  }

  /**
   * 平滑数据
   *
   * @param {Array} data - 数据数组
   * @param {number} window - 平滑窗口大小
   * @returns {Array} 平滑后的数据
   */
  function smoothData(data, window) {
    if (data.length < window) return data

    const smoothed = []
    const halfWindow = Math.floor(window / 2)

    for (let i = 0; i < data.length; i++) {
      const start = Math.max(0, i - halfWindow)
      const end = Math.min(data.length, i + halfWindow + 1)
      const windowData = data.slice(start, end)
      const avg = windowData.reduce((sum, d) => sum + d.value, 0) / windowData.length

      smoothed.push({
        timestamp: data[i].timestamp,
        value: avg
      })
    }

    return smoothed
  }

  /**
   * 更新所有统计指标
   */
  function updateAllStatistics() {
    const newStats = {}

    Object.entries(filteredData.value).forEach(([deviceId, deviceData]) => {
      newStats[deviceId] = {}

      Object.entries(deviceData).forEach(([channelId, channelData]) => {
        newStats[deviceId][channelId] = calculateStatistics(channelData)
      })
    })

    statistics.value = newStats
  }

  // ==================== 数据管理方法 ====================

  /**
   * 添加实时数据
   *
   * @param {string} deviceId - 设备ID
   * @param {string} channelId - 通道ID
   * @param {Object} dataPoint - 数据点 {timestamp, value}
   */
  function addDataPoint(deviceId, channelId, dataPoint) {
    if (!dataBuffer.value[deviceId]) {
      dataBuffer.value[deviceId] = {}
    }

    if (!dataBuffer.value[deviceId][channelId]) {
      dataBuffer.value[deviceId][channelId] = []
    }

    const buffer = dataBuffer.value[deviceId][channelId]
    buffer.push({
      timestamp: dataPoint.timestamp || Date.now(),
      value: dataPoint.value
    })

    // 保持缓冲区大小限制
    if (buffer.length > MAX_BUFFER_SIZE) {
      buffer.shift()
    }
  }

  /**
   * 批量添加数据
   *
   * @param {string} deviceId - 设备ID
   * @param {string} channelId - 通道ID
   * @param {Array} dataPoints - 数据点数组
   */
  function addDataPoints(deviceId, channelId, dataPoints) {
    if (!dataBuffer.value[deviceId]) {
      dataBuffer.value[deviceId] = {}
    }

    if (!dataBuffer.value[deviceId][channelId]) {
      dataBuffer.value[deviceId][channelId] = []
    }

    const buffer = dataBuffer.value[deviceId][channelId]
    dataPoints.forEach(point => {
      buffer.push({
        timestamp: point.timestamp || Date.now(),
        value: point.value
      })
    })

    // 保持缓冲区大小限制
    if (buffer.length > MAX_BUFFER_SIZE) {
      dataBuffer.value[deviceId][channelId] = buffer.slice(-MAX_BUFFER_SIZE)
    }
  }

  /**
   * 清除设备数据
   *
   * @param {string} deviceId - 设备ID（可选，不指定则清除所有）
   */
  function clearData(deviceId = null) {
    if (deviceId) {
      delete dataBuffer.value[deviceId]
      delete statistics.value[deviceId]
    } else {
      dataBuffer.value = {}
      statistics.value = {}
    }
  }

  /**
   * 清除通道数据
   *
   * @param {string} deviceId - 设备ID
   * @param {string} channelId - 通道ID
   */
  function clearChannelData(deviceId, channelId) {
    if (dataBuffer.value[deviceId]) {
      delete dataBuffer.value[deviceId][channelId]
    }
    if (statistics.value[deviceId]) {
      delete statistics.value[deviceId][channelId]
    }
  }

  // ==================== 设备和通道选择方法 ====================

  /**
   * 选择设备
   *
   * @param {string} deviceId - 设备ID
   */
  function selectDevice(deviceId) {
    if (!selectedDevices.value.includes(deviceId)) {
      selectedDevices.value.push(deviceId)

      // 默认选择所有通道
      const channels = DEVICE_CHANNELS[deviceId] || []
      selectedChannels.value[deviceId] = channels.map(c => c.id)
    }
  }

  /**
   * 取消选择设备
   *
   * @param {string} deviceId - 设备ID
   */
  function deselectDevice(deviceId) {
    const index = selectedDevices.value.indexOf(deviceId)
    if (index > -1) {
      selectedDevices.value.splice(index, 1)
      delete selectedChannels.value[deviceId]
    }
  }

  /**
   * 切换设备选择状态
   *
   * @param {string} deviceId - 设备ID
   */
  function toggleDevice(deviceId) {
    if (selectedDevices.value.includes(deviceId)) {
      deselectDevice(deviceId)
    } else {
      selectDevice(deviceId)
    }
  }

  /**
   * 选择通道
   *
   * @param {string} deviceId - 设备ID
   * @param {string} channelId - 通道ID
   */
  function selectChannel(deviceId, channelId) {
    if (!selectedChannels.value[deviceId]) {
      selectedChannels.value[deviceId] = []
    }
    if (!selectedChannels.value[deviceId].includes(channelId)) {
      selectedChannels.value[deviceId].push(channelId)
    }
  }

  /**
   * 取消选择通道
   *
   * @param {string} deviceId - 设备ID
   * @param {string} channelId - 通道ID
   */
  function deselectChannel(deviceId, channelId) {
    if (selectedChannels.value[deviceId]) {
      const index = selectedChannels.value[deviceId].indexOf(channelId)
      if (index > -1) {
        selectedChannels.value[deviceId].splice(index, 1)
      }
    }
  }

  /**
   * 切换通道选择状态
   *
   * @param {string} deviceId - 设备ID
   * @param {string} channelId - 通道ID
   */
  function toggleChannel(deviceId, channelId) {
    if (selectedChannels.value[deviceId]?.includes(channelId)) {
      deselectChannel(deviceId, channelId)
    } else {
      selectChannel(deviceId, channelId)
    }
  }

  /**
   * 选择所有设备和通道
   */
  function selectAll() {
    availableDevices.value.forEach(device => {
      selectDevice(device.id)
    })
  }

  /**
   * 取消选择所有设备和通道
   */
  function deselectAll() {
    selectedDevices.value = []
    selectedChannels.value = {}
  }

  // ==================== 过滤条件方法 ====================

  /**
   * 设置时间范围过滤
   *
   * @param {number} start - 开始时间戳
   * @param {number} end - 结束时间戳
   */
  function setTimeRangeFilter(start, end) {
    filterConditions.value.timeRange.start = start
    filterConditions.value.timeRange.end = end
  }

  /**
   * 设置数值范围过滤
   *
   * @param {number} min - 最小值
   * @param {number} max - 最大值
   */
  function setValueRangeFilter(min, max) {
    filterConditions.value.valueRange.min = min
    filterConditions.value.valueRange.max = max
  }

  /**
   * 设置采样间隔
   *
   * @param {number} interval - 采样间隔（毫秒）
   */
  function setSamplingInterval(interval) {
    filterConditions.value.samplingInterval = interval
  }

  /**
   * 启用/禁用平滑
   *
   * @param {boolean} enable - 是否启用
   * @param {number} window - 平滑窗口大小
   */
  function setSmoothing(enable, window = 5) {
    filterConditions.value.enableSmoothing = enable
    filterConditions.value.smoothingWindow = window
  }

  /**
   * 重置所有过滤条件
   */
  function resetFilters() {
    filterConditions.value = {
      timeRange: {
        start: null,
        end: null,
        duration: 60000
      },
      valueRange: {
        min: null,
        max: null
      },
      samplingInterval: 100,
      enableSmoothing: false,
      smoothingWindow: 5
    }
  }

  // ==================== 导出方法 ====================

  /**
   * 导出数据为CSV格式
   *
   * @param {Object} options - 导出选项
   * @returns {string} CSV字符串
   */
  function exportToCSV(options = {}) {
    const config = { ...exportConfig.value, ...options }
    const lines = []

    // 添加标题行
    if (config.includeTimestamp) {
      const headers = ['时间戳']
      Object.entries(filteredData.value).forEach(([deviceId, deviceData]) => {
        Object.entries(deviceData).forEach(([channelId]) => {
          const channel = DEVICE_CHANNELS[deviceId]?.find(c => c.id === channelId)
          headers.push(`${DEVICE_NAMES[deviceId]}-${channel?.name || channelId}(${channel?.unit || ''})`)
        })
      })
      lines.push(headers.join(config.separator))
    }

    // 收集所有时间戳
    const allTimestamps = new Set()
    Object.values(filteredData.value).forEach(deviceData => {
      Object.values(deviceData).forEach(channelData => {
        channelData.forEach(d => allTimestamps.add(d.timestamp))
      })
    })

    const sortedTimestamps = Array.from(allTimestamps).sort((a, b) => a - b)

    // 添加数据行
    sortedTimestamps.forEach(timestamp => {
      const row = [formatTimestamp(timestamp, config.dateFormat)]

      Object.entries(filteredData.value).forEach(([deviceId, deviceData]) => {
        Object.entries(deviceData).forEach(([channelId, channelData]) => {
          const dataPoint = channelData.find(d => d.timestamp === timestamp)
          row.push(dataPoint ? dataPoint.value.toFixed(config.decimalPlaces) : '')
        })
      })

      lines.push(row.join(config.separator))
    })

    // 添加统计信息
    if (config.includeStatistics) {
      lines.push('')
      lines.push('统计信息')
      lines.push(`导出时间,${formatTimestamp(Date.now(), config.dateFormat)}`)
      lines.push(`数据点数,${sortedTimestamps.length}`)
      lines.push(`设备数量,${selectedDeviceCount.value}`)
      lines.push(`通道数量,${selectedChannelCount.value}`)

      Object.entries(statistics.value).forEach(([deviceId, deviceStats]) => {
        Object.entries(deviceStats).forEach(([channelId, stats]) => {
          const channel = DEVICE_CHANNELS[deviceId]?.find(c => c.id === channelId)
          lines.push('')
          lines.push(`${DEVICE_NAMES[deviceId]}-${channel?.name || channelId} 统计`)
          lines.push(`数据点数,${stats.count}`)
          lines.push(`均值,${stats.mean?.toFixed(config.decimalPlaces) || ''}`)
          lines.push(`标准差,${stats.std?.toFixed(config.decimalPlaces) || ''}`)
          lines.push(`最小值,${stats.min?.toFixed(config.decimalPlaces) || ''}`)
          lines.push(`最大值,${stats.max?.toFixed(config.decimalPlaces) || ''}`)
          lines.push(`范围,${stats.range?.toFixed(config.decimalPlaces) || ''}`)
          lines.push(`中位数,${stats.median?.toFixed(config.decimalPlaces) || ''}`)
          lines.push(`变化率,${stats.changeRate?.toFixed(2) || ''}%`)
          lines.push(`趋势,${stats.trend?.direction || ''}`)
        })
      })
    }

    return lines.join('\n')
  }

  /**
   * 导出数据为JSON格式
   *
   * @param {Object} options - 导出选项
   * @returns {string} JSON字符串
   */
  function exportToJSON(options = {}) {
    const config = { ...exportConfig.value, ...options }

    const exportData = {
      metadata: {
        exportedAt: new Date().toISOString(),
        deviceCount: selectedDeviceCount.value,
        channelCount: selectedChannelCount.value,
        timeRange: dataTimeRange.value
      },
      devices: {},
      statistics: config.includeStatistics ? statistics.value : undefined
    }

    Object.entries(filteredData.value).forEach(([deviceId, deviceData]) => {
      exportData.devices[deviceId] = {
        name: DEVICE_NAMES[deviceId],
        channels: {}
      }

      Object.entries(deviceData).forEach(([channelId, channelData]) => {
        const channel = DEVICE_CHANNELS[deviceId]?.find(c => c.id === channelId)
        exportData.devices[deviceId].channels[channelId] = {
          name: channel?.name || channelId,
          unit: channel?.unit || '',
          data: channelData.map(d => ({
            timestamp: d.timestamp,
            time: formatTimestamp(d.timestamp, config.dateFormat),
            value: d.value
          }))
        }
      })
    })

    return JSON.stringify(exportData, null, 2)
  }

  /**
   * 下载导出文件
   *
   * @param {string} format - 导出格式
   * @param {string} filename - 文件名（可选）
   */
  function downloadExport(format = EXPORT_FORMATS.CSV, filename = null) {
    let content = ''
    let mimeType = ''
    let extension = ''

    switch (format) {
      case EXPORT_FORMATS.CSV:
        content = exportToCSV()
        mimeType = 'text/csv;charset=utf-8'
        extension = 'csv'
        break
      case EXPORT_FORMATS.JSON:
        content = exportToJSON()
        mimeType = 'application/json;charset=utf-8'
        extension = 'json'
        break
      default:
        throw new Error(`Unsupported export format: ${format}`)
    }

    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')

    const defaultFilename = `realtime_analysis_${formatTimestamp(Date.now(), 'YYYYMMDD_HHmmss')}.${extension}`
    link.setAttribute('href', url)
    link.setAttribute('download', filename || defaultFilename)
    link.style.visibility = 'hidden'

    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  /**
   * 导出图表截图
   *
   * @param {HTMLElement} chartElement - 图表DOM元素
   * @param {Object} options - 导出选项
   * @returns {Promise<void>}
   */
  async function exportChartScreenshot(chartElement, options = {}) {
    const {
      filename = `chart_${formatTimestamp(Date.now(), 'YYYYMMDD_HHmmss')}.png`,
      backgroundColor = '#ffffff',
      pixelRatio = 2
    } = options

    // 使用 html2canvas 或类似库进行截图
    // 这里提供基本实现，实际使用时需要引入 html2canvas
    try {
      // 动态导入 html2canvas
      const html2canvas = (await import('html2canvas')).default

      const canvas = await html2canvas(chartElement, {
        backgroundColor,
        scale: pixelRatio,
        useCORS: true,
        logging: false
      })

      canvas.toBlob(blob => {
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.setAttribute('href', url)
        link.setAttribute('download', filename)
        link.style.visibility = 'hidden'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
      }, 'image/png')
    } catch (error) {
      console.error('[AnalysisStore] Failed to export chart screenshot:', error)
      throw new Error('图表截图失败，请确保已安装 html2canvas 库')
    }
  }

  // ==================== 辅助方法 ====================

  /**
   * 格式化时间戳
   *
   * @param {number} timestamp - 时间戳
   * @param {string} format - 格式字符串
   * @returns {string} 格式化后的时间字符串
   */
  function formatTimestamp(timestamp, format = 'YYYY-MM-DD HH:mm:ss') {
    const date = new Date(timestamp)
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    const seconds = String(date.getSeconds()).padStart(2, '0')

    return format
      .replace('YYYY', year)
      .replace('MM', month)
      .replace('DD', day)
      .replace('HH', hours)
      .replace('mm', minutes)
      .replace('ss', seconds)
  }

  /**
   * 获取通道配置
   *
   * @param {string} deviceId - 设备ID
   * @param {string} channelId - 通道ID
   * @returns {Object|null} 通道配置
   */
  function getChannelConfig(deviceId, channelId) {
    return DEVICE_CHANNELS[deviceId]?.find(c => c.id === channelId) || null
  }

  /**
   * 获取设备所有通道配置
   *
   * @param {string} deviceId - 设备ID
   * @returns {Array} 通道配置列表
   */
  function getDeviceChannels(deviceId) {
    return DEVICE_CHANNELS[deviceId] || []
  }

  // ==================== 生命周期方法 ====================

  /**
   * 初始化Store
   */
  function init() {
    // 启动统计计算定时器
    startStatisticsTimer()
  }

  /**
   * 清理资源
   */
  function cleanup() {
    // 停止统计计算定时器
    stopStatisticsTimer()
    // 清空数据
    clearData()
  }

  /**
   * 启动统计计算定时器
   */
  function startStatisticsTimer() {
    if (statisticsTimer) return

    statisticsTimer = setInterval(() => {
      updateAllStatistics()
    }, STATISTICS_INTERVAL)
  }

  /**
   * 停止统计计算定时器
   */
  function stopStatisticsTimer() {
    if (statisticsTimer) {
      clearInterval(statisticsTimer)
      statisticsTimer = null
    }
  }

  // ==================== 导出 ====================

  return {
    // 状态
    selectedDevices,
    selectedChannels,
    filterConditions,
    dataBuffer,
    statistics,
    timeAxisConfig,
    comparisonConfig,
    exportConfig,

    // 计算属性
    availableDevices,
    selectedDeviceCount,
    selectedChannelCount,
    hasData,
    dataTimeRange,
    filteredData,

    // 数据管理方法
    addDataPoint,
    addDataPoints,
    clearData,
    clearChannelData,

    // 设备和通道选择方法
    selectDevice,
    deselectDevice,
    toggleDevice,
    selectChannel,
    deselectChannel,
    toggleChannel,
    selectAll,
    deselectAll,

    // 过滤条件方法
    setTimeRangeFilter,
    setValueRangeFilter,
    setSamplingInterval,
    setSmoothing,
    resetFilters,

    // 统计方法
    calculateStatistics,
    updateAllStatistics,

    // 导出方法
    exportToCSV,
    exportToJSON,
    downloadExport,
    exportChartScreenshot,

    // 辅助方法
    formatTimestamp,
    getChannelConfig,
    getDeviceChannels,

    // 生命周期方法
    init,
    cleanup,

    // 常量导出
    DEVICE_TYPES,
    DEVICE_NAMES,
    DEVICE_CHANNELS,
    EXPORT_FORMATS
  }
})
