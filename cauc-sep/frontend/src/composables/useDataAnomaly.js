/**
 * @file useDataAnomaly.js
 * @path src/composables/
 * @description 数据异常检测组合式函数，检测数据超出范围、突变等异常情况
 * @author Agent
 * @date 2024-03-07
 * @dependencies vue
 */

import { ref, computed, onUnmounted } from 'vue'

/**
 * 异常类型枚举
 */
export const ANOMALY_TYPE = {
  OUT_OF_RANGE: 'out_of_range',     // 超出范围
  SUDDEN_CHANGE: 'sudden_change',   // 突变
  STUCK_VALUE: 'stuck_value',       // 数值卡死
  NOISE: 'noise',                   // 噪声异常
  TREND_ANOMALY: 'trend_anomaly'    // 趋势异常
}

/**
 * 异常级别枚举
 */
export const ANOMALY_LEVEL = {
  INFO: 'info',       // 提示
  WARNING: 'warning', // 警告
  ERROR: 'error',     // 错误
  CRITICAL: 'critical' // 严重
}

/**
 * 默认检测配置
 */
const DEFAULT_DETECTION_CONFIG = {
  // 范围检测
  rangeCheck: {
    enabled: true,
    min: -Infinity,
    max: Infinity,
    warningMargin: 0.1  // 警告边界（相对于范围的百分比）
  },
  
  // 突变检测
  suddenChangeCheck: {
    enabled: true,
    threshold: 0.5,     // 突变阈值（相对于当前值的百分比）
    timeWindow: 1000    // 时间窗口（毫秒）
  },
  
  // 卡死检测
  stuckCheck: {
    enabled: true,
    threshold: 0.001,   // 变化阈值
    timeWindow: 5000    // 时间窗口（毫秒）
  },
  
  // 噪声检测
  noiseCheck: {
    enabled: true,
    windowSize: 10,     // 滑动窗口大小
    threshold: 0.3      // 噪声阈值（标准差/均值）
  },
  
  // 趋势检测
  trendCheck: {
    enabled: true,
    windowSize: 20,     // 趋势窗口大小
    threshold: 0.1      // 趋势阈值
  }
}

/**
 * 数据异常检测组合式函数
 * 
 * @param {Object} options - 配置选项
 * @param {Object} [options.config] - 检测配置
 * @param {Function} [options.onAnomaly] - 异常回调
 * @param {Function} [options.onAnomalyClear] - 异常清除回调
 * @returns {Object} 异常检测控制对象
 * 
 * @example
 * ```javascript
 * const anomaly = useDataAnomaly({
 *   config: {
 *     rangeCheck: { min: 0, max: 100 }
 *   },
 *   onAnomaly: (anomaly) => console.log('异常:', anomaly)
 * })
 * 
 * // 检测数据
 * anomaly.check(42)
 * ```
 */
export function useDataAnomaly(options = {}) {
  const {
    config: userConfig = {},
    onAnomaly,
    onAnomalyClear
  } = options

  // 合并配置
  const config = {
    rangeCheck: { ...DEFAULT_DETECTION_CONFIG.rangeCheck, ...userConfig.rangeCheck },
    suddenChangeCheck: { ...DEFAULT_DETECTION_CONFIG.suddenChangeCheck, ...userConfig.suddenChangeCheck },
    stuckCheck: { ...DEFAULT_DETECTION_CONFIG.stuckCheck, ...userConfig.stuckCheck },
    noiseCheck: { ...DEFAULT_DETECTION_CONFIG.noiseCheck, ...userConfig.noiseCheck },
    trendCheck: { ...DEFAULT_DETECTION_CONFIG.trendCheck, ...userConfig.trendCheck }
  }

  // ==================== 响应式状态 ====================

  /** 当前异常列表 */
  const anomalies = ref([])

  /** 历史数据缓冲区 */
  const dataBuffer = ref([])

  /** 上一次检测的值 */
  const lastValue = ref(null)

  /** 上一次检测的时间戳 */
  const lastTimestamp = ref(null)

  /** 是否有异常 */
  const hasAnomaly = computed(() => anomalies.value.length > 0)

  /** 是否有严重异常 */
  const hasCriticalAnomaly = computed(() => {
    return anomalies.value.some(a => a.level === ANOMALY_LEVEL.CRITICAL)
  })

  /** 是否有错误级别异常 */
  const hasErrorAnomaly = computed(() => {
    return anomalies.value.some(a => 
      a.level === ANOMALY_LEVEL.ERROR || a.level === ANOMALY_LEVEL.CRITICAL
    )
  })

  /** 最高异常级别 */
  const highestAnomalyLevel = computed(() => {
    if (anomalies.value.length === 0) return null
    
    const levelPriority = {
      [ANOMALY_LEVEL.INFO]: 0,
      [ANOMALY_LEVEL.WARNING]: 1,
      [ANOMALY_LEVEL.ERROR]: 2,
      [ANOMALY_LEVEL.CRITICAL]: 3
    }
    
    return anomalies.value.reduce((highest, anomaly) => {
      return levelPriority[anomaly.level] > levelPriority[highest] 
        ? anomaly.level 
        : highest
    }, ANOMALY_LEVEL.INFO)
  })

  // ==================== 方法 ====================

  /**
   * 检测数据异常
   * 
   * @param {number} value - 待检测的值
   * @param {number} [timestamp] - 可选的时间戳
   */
  function check(value, timestamp = Date.now()) {
    // 添加到数据缓冲区
    addToBuffer(value, timestamp)
    
    // 执行各项检测
    const detectedAnomalies = []
    
    // 范围检测
    if (config.rangeCheck.enabled) {
      const rangeAnomaly = checkRange(value)
      if (rangeAnomaly) detectedAnomalies.push(rangeAnomaly)
    }
    
    // 突变检测
    if (config.suddenChangeCheck.enabled && lastValue.value !== null) {
      const suddenAnomaly = checkSuddenChange(value, timestamp)
      if (suddenAnomaly) detectedAnomalies.push(suddenAnomaly)
    }
    
    // 卡死检测
    if (config.stuckCheck.enabled && dataBuffer.value.length >= 3) {
      const stuckAnomaly = checkStuck(timestamp)
      if (stuckAnomaly) detectedAnomalies.push(stuckAnomaly)
    }
    
    // 噪声检测
    if (config.noiseCheck.enabled && dataBuffer.value.length >= config.noiseCheck.windowSize) {
      const noiseAnomaly = checkNoise()
      if (noiseAnomaly) detectedAnomalies.push(noiseAnomaly)
    }
    
    // 趋势检测
    if (config.trendCheck.enabled && dataBuffer.value.length >= config.trendCheck.windowSize) {
      const trendAnomaly = checkTrend()
      if (trendAnomaly) detectedAnomalies.push(trendAnomaly)
    }
    
    // 更新状态
    lastValue.value = value
    lastTimestamp.value = timestamp
    
    // 处理检测到的异常
    if (detectedAnomalies.length > 0) {
      handleDetectedAnomalies(detectedAnomalies)
    }
  }

  /**
   * 范围检测
   * 
   * @param {number} value - 待检测的值
   * @returns {Object|null} 异常对象或null
   * @internal 内部方法
   */
  function checkRange(value) {
    const { min, max, warningMargin } = config.rangeCheck
    const range = max - min
    
    // 超出范围
    if (value < min || value > max) {
      return {
        id: `range_${Date.now()}`,
        type: ANOMALY_TYPE.OUT_OF_RANGE,
        level: ANOMALY_LEVEL.ERROR,
        message: `数值 ${value.toFixed(2)} 超出有效范围 [${min}, ${max}]`,
        value,
        timestamp: Date.now(),
        details: {
          min,
          max,
          actual: value
        }
      }
    }
    
    // 接近边界警告
    const warningMin = min + range * warningMargin
    const warningMax = max - range * warningMargin
    
    if (value < warningMin || value > warningMax) {
      return {
        id: `range_warning_${Date.now()}`,
        type: ANOMALY_TYPE.OUT_OF_RANGE,
        level: ANOMALY_LEVEL.WARNING,
        message: `数值 ${value.toFixed(2)} 接近边界`,
        value,
        timestamp: Date.now(),
        details: {
          min,
          max,
          warningMin,
          warningMax,
          actual: value
        }
      }
    }
    
    return null
  }

  /**
   * 突变检测
   * 
   * @param {number} value - 当前值
   * @param {number} timestamp - 当前时间戳
   * @returns {Object|null} 异常对象或null
   * @internal 内部方法
   */
  function checkSuddenChange(value, timestamp) {
    const { threshold, timeWindow } = config.suddenChangeCheck
    const timeDiff = timestamp - lastTimestamp.value
    
    // 检查时间窗口
    if (timeDiff > timeWindow) return null
    
    // 计算变化率
    const change = Math.abs(value - lastValue.value)
    const changeRate = lastValue.value !== 0 
      ? change / Math.abs(lastValue.value) 
      : change
    
    if (changeRate > threshold) {
      return {
        id: `sudden_${Date.now()}`,
        type: ANOMALY_TYPE.SUDDEN_CHANGE,
        level: ANOMALY_LEVEL.WARNING,
        message: `数值突变 ${(changeRate * 100).toFixed(1)}%`,
        value,
        timestamp,
        details: {
          previousValue: lastValue.value,
          currentValue: value,
          changeRate,
          threshold
        }
      }
    }
    
    return null
  }

  /**
   * 卡死检测
   * 
   * @param {number} timestamp - 当前时间戳
   * @returns {Object|null} 异常对象或null
   * @internal 内部方法
   */
  function checkStuck(timestamp) {
    const { threshold, timeWindow } = config.stuckCheck
    
    // 获取时间窗口内的数据
    const windowData = dataBuffer.value.filter(
      d => timestamp - d.timestamp <= timeWindow
    )
    
    if (windowData.length < 3) return null
    
    // 检查是否所有值都相同
    const values = windowData.map(d => d.value)
    const maxDiff = Math.max(...values) - Math.min(...values)
    
    if (maxDiff < threshold) {
      return {
        id: `stuck_${Date.now()}`,
        type: ANOMALY_TYPE.STUCK_VALUE,
        level: ANOMALY_LEVEL.WARNING,
        message: `数值卡死，${timeWindow / 1000}秒内无有效变化`,
        value: lastValue.value,
        timestamp,
        details: {
          duration: timeWindow,
          threshold,
          maxDiff
        }
      }
    }
    
    return null
  }

  /**
   * 噪声检测
   * 
   * @returns {Object|null} 异常对象或null
   * @internal 内部方法
   */
  function checkNoise() {
    const { windowSize, threshold } = config.noiseCheck
    
    const windowData = dataBuffer.value.slice(-windowSize)
    const values = windowData.map(d => d.value)
    
    // 计算均值和标准差
    const mean = values.reduce((a, b) => a + b, 0) / values.length
    const variance = values.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / values.length
    const stdDev = Math.sqrt(variance)
    
    // 计算噪声比
    const noiseRatio = mean !== 0 ? stdDev / Math.abs(mean) : stdDev
    
    if (noiseRatio > threshold) {
      return {
        id: `noise_${Date.now()}`,
        type: ANOMALY_TYPE.NOISE,
        level: ANOMALY_LEVEL.INFO,
        message: `信号噪声异常，噪声比 ${(noiseRatio * 100).toFixed(1)}%`,
        value: mean,
        timestamp: Date.now(),
        details: {
          mean,
          stdDev,
          noiseRatio,
          threshold
        }
      }
    }
    
    return null
  }

  /**
   * 趋势检测
   * 
   * @returns {Object|null} 异常对象或null
   * @internal 内部方法
   */
  function checkTrend() {
    const { windowSize, threshold } = config.trendCheck
    
    const windowData = dataBuffer.value.slice(-windowSize)
    const values = windowData.map(d => d.value)
    
    // 简单线性回归计算趋势
    const n = values.length
    const xMean = (n - 1) / 2
    const yMean = values.reduce((a, b) => a + b, 0) / n
    
    let numerator = 0
    let denominator = 0
    
    for (let i = 0; i < n; i++) {
      numerator += (i - xMean) * (values[i] - yMean)
      denominator += Math.pow(i - xMean, 2)
    }
    
    const slope = denominator !== 0 ? numerator / denominator : 0
    const trendRate = Math.abs(slope / yMean)  // 相对趋势率
    
    if (trendRate > threshold) {
      return {
        id: `trend_${Date.now()}`,
        type: ANOMALY_TYPE.TREND_ANOMALY,
        level: ANOMALY_LEVEL.INFO,
        message: `检测到异常趋势，趋势率 ${(trendRate * 100).toFixed(1)}%/样本`,
        value: yMean,
        timestamp: Date.now(),
        details: {
          slope,
          trendRate,
          threshold,
          direction: slope > 0 ? '上升' : '下降'
        }
      }
    }
    
    return null
  }

  /**
   * 添加数据到缓冲区
   * 
   * @param {number} value - 数据值
   * @param {number} timestamp - 时间戳
   * @internal 内部方法
   */
  function addToBuffer(value, timestamp) {
    dataBuffer.value.push({ value, timestamp })
    
    // 限制缓冲区大小
    const maxSize = Math.max(
      config.noiseCheck.windowSize,
      config.trendCheck.windowSize,
      50
    )
    
    if (dataBuffer.value.length > maxSize) {
      dataBuffer.value = dataBuffer.value.slice(-maxSize)
    }
  }

  /**
   * 处理检测到的异常
   * 
   * @param {Array} detectedAnomalies - 检测到的异常列表
   * @internal 内部方法
   */
  function handleDetectedAnomalies(detectedAnomalies) {
    // 添加到异常列表
    anomalies.value.push(...detectedAnomalies)
    
    // 限制异常列表大小
    if (anomalies.value.length > 20) {
      anomalies.value = anomalies.value.slice(-20)
    }
    
    // 触发回调
    detectedAnomalies.forEach(anomaly => {
      onAnomaly?.(anomaly)
    })
  }

  /**
   * 确认异常
   * 
   * @param {string} anomalyId - 异常ID
   */
  function acknowledgeAnomaly(anomalyId) {
    const index = anomalies.value.findIndex(a => a.id === anomalyId)
    if (index !== -1) {
      anomalies.value[index].acknowledged = true
    }
  }

  /**
   * 清除异常
   * 
   * @param {string} [anomalyId] - 可选的异常ID，不提供则清除所有
   */
  function clearAnomaly(anomalyId) {
    if (anomalyId) {
      const index = anomalies.value.findIndex(a => a.id === anomalyId)
      if (index !== -1) {
        const cleared = anomalies.value.splice(index, 1)[0]
        onAnomalyClear?.(cleared)
      }
    } else {
      anomalies.value = []
      onAnomalyClear?.(null)
    }
  }

  /**
   * 清除已确认的异常
   */
  function clearAcknowledged() {
    anomalies.value = anomalies.value.filter(a => !a.acknowledged)
  }

  /**
   * 重置检测器
   */
  function reset() {
    anomalies.value = []
    dataBuffer.value = []
    lastValue.value = null
    lastTimestamp.value = null
  }

  /**
   * 更新检测配置
   * 
   * @param {Object} newConfig - 新配置
   */
  function updateConfig(newConfig) {
    Object.keys(newConfig).forEach(key => {
      if (config[key]) {
        config[key] = { ...config[key], ...newConfig[key] }
      }
    })
  }

  /**
   * 获取异常统计
   * 
   * @returns {Object} 异常统计对象
   */
  function getStatistics() {
    const stats = {
      total: anomalies.value.length,
      byType: {},
      byLevel: {},
      acknowledged: anomalies.value.filter(a => a.acknowledged).length
    }
    
    anomalies.value.forEach(anomaly => {
      // 按类型统计
      if (!stats.byType[anomaly.type]) {
        stats.byType[anomaly.type] = 0
      }
      stats.byType[anomaly.type]++
      
      // 按级别统计
      if (!stats.byLevel[anomaly.level]) {
        stats.byLevel[anomaly.level] = 0
      }
      stats.byLevel[anomaly.level]++
    })
    
    return stats
  }

  // ==================== 生命周期 ====================

  onUnmounted(() => {
    reset()
  })

  // ==================== 返回值 ====================

  return {
    // 状态
    anomalies,
    dataBuffer,
    lastValue,
    lastTimestamp,
    
    // 计算属性
    hasAnomaly,
    hasCriticalAnomaly,
    hasErrorAnomaly,
    highestAnomalyLevel,
    
    // 方法
    check,
    acknowledgeAnomaly,
    clearAnomaly,
    clearAcknowledged,
    reset,
    updateConfig,
    getStatistics
  }
}

/**
 * 创建多数据源异常检测管理器
 * 
 * @param {Object} dataSourceConfigs - 数据源配置映射
 * @param {Object} defaultConfig - 默认检测配置
 * @returns {Object} 多数据源异常检测管理器
 * 
 * @example
 * ```javascript
 * const manager = createAnomalyManager({
 *   temperature: { rangeCheck: { min: 77, max: 400 } },
 *   position: { rangeCheck: { min: -50, max: 50 } }
 * })
 * 
 * manager.check('temperature', 300)
 * ```
 */
export function createAnomalyManager(dataSourceConfigs, defaultConfig = {}) {
  const detectors = {}
  const allAnomalies = ref([])
  
  // 为每个数据源创建检测器
  Object.keys(dataSourceConfigs).forEach(key => {
    const sourceConfig = dataSourceConfigs[key]
    
    detectors[key] = useDataAnomaly({
      config: { ...defaultConfig, ...sourceConfig },
      onAnomaly: (anomaly) => {
        // 添加数据源标识
        anomaly.source = key
        allAnomalies.value.push(anomaly)
        
        // 限制列表大小
        if (allAnomalies.value.length > 50) {
          allAnomalies.value = allAnomalies.value.slice(-50)
        }
      }
    })
  })

  /**
   * 检测指定数据源
   * 
   * @param {string} source - 数据源键名
   * @param {number} value - 待检测的值
   * @param {number} [timestamp] - 可选的时间戳
   */
  function check(source, value, timestamp) {
    if (detectors[source]) {
      detectors[source].check(value, timestamp)
    }
  }

  /**
   * 清除指定数据源的异常
   * 
   * @param {string} source - 数据源键名
   */
  function clearSourceAnomalies(source) {
    allAnomalies.value = allAnomalies.value.filter(a => a.source !== source)
    detectors[source]?.reset()
  }

  /**
   * 清除所有异常
   */
  function clearAll() {
    allAnomalies.value = []
    Object.values(detectors).forEach(detector => detector.reset())
  }

  /**
   * 获取指定数据源的异常
   * 
   * @param {string} source - 数据源键名
   * @returns {Array} 异常列表
   */
  function getSourceAnomalies(source) {
    return allAnomalies.value.filter(a => a.source === source)
  }

  /**
   * 是否有任何异常
   */
  const hasAnyAnomaly = computed(() => allAnomalies.value.length > 0)

  /**
   * 是否有严重异常
   */
  const hasAnyCriticalAnomaly = computed(() => {
    return allAnomalies.value.some(a => a.level === ANOMALY_LEVEL.CRITICAL)
  })

  return {
    // 状态
    allAnomalies,
    hasAnyAnomaly,
    hasAnyCriticalAnomaly,
    
    // 方法
    check,
    clearSourceAnomalies,
    clearAll,
    getSourceAnomalies,
    
    // 单个检测器访问
    detectors
  }
}
