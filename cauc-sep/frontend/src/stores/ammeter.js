/**
 * @file ammeter.js
 * @path src/stores/
 * @description 微电流采集状态管理Store，封装数据采集、通道配置、实时监控等功能
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

export const useAmmeterStore = defineStore('ammeter', () => {
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
  } = useDeviceBase('ammeter')

  // ==================== 微电流采集特有状态 ====================

  /** 采集状态 */
  const isCollecting = ref(false)

  /** 采样率 */
  const sampleRate = ref(1000)

  /** 通道数量 */
  const channelCount = ref(4)

  /** 通道数据 */
  const channelData = ref({})

  /** 通道配置 */
  const channelConfig = ref({
    1: { enabled: true, range: 'auto', filter: 'low' },
    2: { enabled: true, range: 'auto', filter: 'low' },
    3: { enabled: true, range: 'auto', filter: 'low' },
    4: { enabled: true, range: 'auto', filter: 'low' }
  })

  /** 缓冲区状态 */
  const bufferStatus = ref({
    size: 0,
    max_size: 10000,
    usage: 0
  })

  /** 信噪比数据 */
  const snrData = ref({})

  /** 实时数据历史（用于图表） */
  const realtimeData = ref([])
  const maxRealtimePoints = 500

  /** 采集统计信息 */
  const collectionStats = ref({
    start_time: null,
    duration: 0,
    samples_collected: 0,
    data_rate: 0
  })

  /** SNR实时计算数据 */
  const snrHistory = ref({})
  const maxSNRHistoryPoints = 100

  /** SNR阈值配置 */
  const snrThresholds = ref({
    warning: 20,  // dB
    critical: 10  // dB
  })

  /** SNR告警状态 */
  const snrAlarms = ref({})

  /** 采集参数模板 */
  const collectionTemplates = ref([])

  /** 当前应用的模板ID */
  const activeTemplateId = ref(null)

  /** 数据缓冲管理 */
  const bufferConfig = ref({
    maxSize: 10000,
    warningThreshold: 0.7,
    criticalThreshold: 0.9,
    autoClear: false,
    autoClearThreshold: 0.95
  })

  // ==================== 计算属性 ====================

  /**
   * 是否允许控制采集
   * 覆盖基础canControl，增加采集状态检查
   */
  const canControl = computed(() => {
    return isConnected.value && status.value === 'ready'
  })

  /**
   * 是否正在采集
   */
  const isCollectingData = computed(() => {
    return isCollecting.value
  })

  /**
   * 缓冲区使用百分比
   */
  const bufferUsagePercent = computed(() => {
    if (bufferStatus.value.max_size === 0) return 0
    return Math.round((bufferStatus.value.size / bufferStatus.value.max_size) * 100)
  })

  /**
   * 缓冲区状态类型（用于UI显示）
   */
  const bufferStatusType = computed(() => {
    const usage = bufferUsagePercent.value
    if (usage >= 90) return 'danger'
    if (usage >= 70) return 'warning'
    return 'success'
  })

  /**
   * 缓冲区状态文本
   */
  const bufferStatusText = computed(() => {
    const usage = bufferUsagePercent.value
    if (usage >= 90) return '缓冲区即将满'
    if (usage >= 70) return '缓冲区使用较高'
    return '缓冲区正常'
  })

  /**
   * 当前应用的模板
   */
  const activeTemplate = computed(() => {
    if (!activeTemplateId.value) return null
    return collectionTemplates.value.find(t => t.id === activeTemplateId.value)
  })

  /**
   * 是否有SNR告警
   */
  const hasSNRAlarm = computed(() => {
    return Object.values(snrAlarms.value).some(alarm => alarm.active)
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
      ammeterWS.send({ type: 'pong' })
      return
    }

    // 处理实时数据更新
    if (data.channel_data !== undefined) {
      channelData.value = data.channel_data
      isCollecting.value = data.is_collecting || false

      // 添加到实时数据历史
      addRealtimeData(data.channel_data)
    }

    // 处理缓冲区状态更新
    if (data.buffer_status !== undefined) {
      bufferStatus.value = data.buffer_status
    }

    // 处理采集统计更新
    if (data.stats !== undefined) {
      collectionStats.value = data.stats
    }

    // 处理错误消息
    if (data.error) {
      console.error('WebSocket error:', data.error)
      showError(data.error)
    }

    // 处理状态更新
    if (data.status !== undefined) {
      status.value = data.status
      isConnected.value = data.status !== 'disconnected'
    }
  }

  /**
   * 添加实时数据到历史记录
   *
   * @param {Object} data - 通道数据
   */
  function addRealtimeData(data) {
    realtimeData.value.push({
      timestamp: Date.now(),
      ...data
    })

    // 限制历史数据点数量
    if (realtimeData.value.length > maxRealtimePoints) {
      realtimeData.value = realtimeData.value.slice(-maxRealtimePoints)
    }

    // 实时计算SNR
    calculateRealtimeSNR(data)

    // 检查缓冲区并自动清理
    checkAndAutoClearBuffer()
  }

  /**
   * 实时计算信噪比
   * 
   * @param {Object} data - 通道数据
   */
  function calculateRealtimeSNR(data) {
    for (let channel = 1; channel <= channelCount.value; channel++) {
      if (!channelConfig.value[channel]?.enabled) continue

      const value = data[channel]
      if (value === undefined || value === null) continue

      // 初始化通道SNR历史
      if (!snrHistory.value[channel]) {
        snrHistory.value[channel] = []
      }

      // 计算信号和噪声
      // 使用滑动窗口计算信号均值和噪声标准差
      const history = snrHistory.value[channel]
      const windowSize = 20

      // 添加当前值到历史
      history.push({
        timestamp: Date.now(),
        value: value
      })

      // 限制历史长度
      if (history.length > maxSNRHistoryPoints) {
        history.shift()
      }

      // 计算信号（均值）和噪声（标准差）
      const recentValues = history.slice(-windowSize).map(h => h.value)
      const signal = recentValues.reduce((a, b) => a + b, 0) / recentValues.length
      const variance = recentValues.reduce((acc, val) => acc + Math.pow(val - signal, 2), 0) / recentValues.length
      const noise = Math.sqrt(variance)

      // 计算SNR (dB)
      // SNR = 20 * log10(signal / noise)
      let snr = 0
      if (noise > 0 && signal > 0) {
        snr = 20 * Math.log10(signal / noise)
      } else if (signal > 0) {
        snr = 100 // 信号存在但无噪声，SNR设为最大值
      } else {
        snr = 0 // 无信号
      }

      // 更新SNR数据
      snrData.value[channel] = {
        snr: snr,
        signal: signal,
        noise: noise,
        timestamp: Date.now()
      }

      // 检查SNR告警
      checkSNRAlarm(channel, snr)
    }
  }

  /**
   * 检查SNR告警
   * 
   * @param {number} channel - 通道编号
   * @param {number} snr - 信噪比 (dB)
   */
  function checkSNRAlarm(channel, snr) {
    const thresholds = snrThresholds.value
    const currentAlarm = snrAlarms.value[channel]

    // 临界告警
    if (snr < thresholds.critical) {
      if (!currentAlarm || currentAlarm.level !== 'critical') {
        snrAlarms.value[channel] = {
          active: true,
          level: 'critical',
          message: `通道${channel} SNR过低 (${snr.toFixed(1)} dB < ${thresholds.critical} dB)`,
          timestamp: Date.now()
        }
        showError(`通道${channel}信噪比过低: ${snr.toFixed(1)} dB`)
      }
    }
    // 警告告警
    else if (snr < thresholds.warning) {
      if (!currentAlarm || currentAlarm.level !== 'warning') {
        snrAlarms.value[channel] = {
          active: true,
          level: 'warning',
          message: `通道${channel} SNR较低 (${snr.toFixed(1)} dB < ${thresholds.warning} dB)`,
          timestamp: Date.now()
        }
      }
    }
    // 清除告警
    else {
      if (currentAlarm?.active) {
        snrAlarms.value[channel] = {
          active: false,
          level: 'normal',
          message: `通道${channel} SNR恢复正常`,
          timestamp: Date.now()
        }
      }
    }
  }

  /**
   * 检查并自动清理缓冲区
   */
  function checkAndAutoClearBuffer() {
    if (!bufferConfig.value.autoClear) return

    const usage = bufferUsagePercent.value / 100

    if (usage >= bufferConfig.value.autoClearThreshold) {
      // 保留最近的数据，清理旧数据
      const keepCount = Math.floor(bufferStatus.value.max_size * 0.3)
      if (realtimeData.value.length > keepCount) {
        realtimeData.value = realtimeData.value.slice(-keepCount)
        console.log(`[Ammeter] Auto-cleared buffer, kept ${keepCount} points`)
      }
    }
  }

  /**
   * 初始化WebSocket连接
   */
  const ammeterWS = useWebSocket({
    url: `${WS_BASE_URL}/ws/ammeter`,
    onMessage: handleWebSocketMessage,
    onOpen: () => {
      console.log('Ammeter WebSocket connected')
    },
    onClose: () => {
      console.log('Ammeter WebSocket disconnected')
    },
    onError: (error) => {
      console.error('Ammeter WebSocket error:', error)
    },
    reconnectInterval: 3000,
    heartbeatInterval: 30000
  })

  // ==================== API 操作方法 ====================

  /**
   * 获取设备状态
   *
   * @returns {Promise<Object|null>} 状态数据或null
   */
  async function fetchStatus() {
    const result = await get('/api/ammeter/status', null, {
      onError: (msg) => {
        console.error('Failed to fetch status:', msg)
        isConnected.value = false
        status.value = 'disconnected'
      }
    })

    if (result.success && result.data) {
      const data = result.data
      status.value = data.status
      isCollecting.value = data.is_collecting || false
      sampleRate.value = data.sample_rate || 1000
      channelCount.value = data.channel_count || 4
      bufferStatus.value = data.buffer_status || bufferStatus.value
      isConnected.value = data.connected
      return data
    }

    return null
  }

  /**
   * 启动数据采集
   *
   * @returns {Promise<boolean>} 启动是否成功
   */
  async function startCollection() {
    if (!canControl.value) {
      showError('设备未就绪，无法启动采集')
      return false
    }

    const result = await post('/api/ammeter/start', null, {
      onLoading: setLoading,
      loadingKey: 'startCollection',
      onError: (msg) => showError('启动采集错误: ' + msg)
    })

    if (result.success && result.data?.success) {
      isCollecting.value = true
      collectionStats.value.start_time = Date.now()
      ammeterWS.connect()
      return true
    }

    if (result.success && !result.data?.success) {
      showError('启动采集失败: ' + (result.data?.message || '未知错误'))
    }

    return false
  }

  /**
   * 停止数据采集
   *
   * @returns {Promise<boolean>} 停止是否成功
   */
  async function stopCollection() {
    const result = await post('/api/ammeter/stop', null, {
      onLoading: setLoading,
      loadingKey: 'stopCollection',
      onError: (msg) => showError('停止采集错误: ' + msg)
    })

    if (result.success && result.data?.success) {
      isCollecting.value = false
      collectionStats.value.duration = Date.now() - (collectionStats.value.start_time || Date.now())
      return true
    }

    if (result.success && !result.data?.success) {
      showError('停止采集失败: ' + (result.data?.message || '未知错误'))
    }

    return false
  }

  /**
   * 获取实时数据
   *
   * @returns {Promise<Object|null>} 实时数据或null
   */
  async function fetchRealtimeData() {
    const result = await get('/api/ammeter/data', null, {
      onError: (msg) => showError('获取数据错误: ' + msg)
    })

    if (result.success && result.data) {
      channelData.value = result.data.channel_data || {}
      bufferStatus.value = result.data.buffer_status || bufferStatus.value
      return result.data
    }

    return null
  }

  /**
   * 配置通道参数
   *
   * @param {number} channel - 通道编号 (1-4)
   * @param {Object} config - 通道配置
   * @param {boolean} config.enabled - 是否启用
   * @param {string} config.range - 量程 ('auto' | 'low' | 'medium' | 'high')
   * @param {string} config.filter - 滤波设置 ('low' | 'medium' | 'high')
   * @returns {Promise<boolean>} 配置是否成功
   */
  async function configureChannel(channel, config) {
    if (!canControl.value) {
      showError('设备未就绪')
      return false
    }

    // 验证通道编号
    if (channel < 1 || channel > channelCount.value) {
      showError(`通道编号无效，有效范围: 1-${channelCount.value}`)
      return false
    }

    const result = await post('/api/ammeter/channel/config', {
      channel: channel,
      ...config
    }, {
      onLoading: setLoading,
      loadingKey: 'configureChannel',
      onError: (msg) => showError('配置通道错误: ' + msg)
    })

    if (result.success && result.data?.success) {
      channelConfig.value[channel] = { ...channelConfig.value[channel], ...config }
      return true
    }

    if (result.success && !result.data?.success) {
      showError('配置通道失败: ' + (result.data?.message || '未知错误'))
    }

    return false
  }

  /**
   * 清空数据缓冲区
   *
   * @returns {Promise<boolean>} 清空是否成功
   */
  async function clearBuffer() {
    const result = await post('/api/ammeter/clear_buffer', null, {
      onLoading: setLoading,
      loadingKey: 'clearBuffer',
      onError: (msg) => showError('清空缓冲区错误: ' + msg)
    })

    if (result.success && result.data?.success) {
      bufferStatus.value.size = 0
      bufferStatus.value.usage = 0
      realtimeData.value = []
      return true
    }

    if (result.success && !result.data?.success) {
      showError('清空缓冲区失败: ' + (result.data?.message || '未知错误'))
    }

    return false
  }

  /**
   * 获取信噪比
   *
   * @param {number} channel - 通道编号 (1-4)
   * @returns {Promise<Object|null>} 信噪比数据或null
   */
  async function fetchSNR(channel) {
    // 验证通道编号
    if (channel < 1 || channel > channelCount.value) {
      showError(`通道编号无效，有效范围: 1-${channelCount.value}`)
      return null
    }

    const result = await get(`/api/ammeter/snr/${channel}`, null, {
      onLoading: setLoading,
      loadingKey: 'fetchSNR',
      onError: (msg) => showError('获取信噪比错误: ' + msg)
    })

    if (result.success && result.data) {
      snrData.value[channel] = result.data
      return result.data
    }

    return null
  }

  /**
   * 批量配置所有通道
   *
   * @param {Object} configs - 通道配置映射 { channel: config }
   * @returns {Promise<boolean>} 配置是否成功
   */
  async function configureAllChannels(configs) {
    if (!canControl.value) {
      showError('设备未就绪')
      return false
    }

    let allSuccess = true

    for (const [channel, config] of Object.entries(configs)) {
      const success = await configureChannel(parseInt(channel), config)
      if (!success) {
        allSuccess = false
      }
    }

    return allSuccess
  }

  /**
   * 设置采样率
   *
   * @param {number} rate - 采样率 (Hz)
   * @returns {Promise<boolean>} 设置是否成功
   */
  async function setSampleRate(rate) {
    if (!canControl.value) {
      showError('设备未就绪')
      return false
    }

    // 验证采样率范围
    if (rate < 1 || rate > 10000) {
      showError('采样率范围: 1-10000 Hz')
      return false
    }

    const result = await post('/api/ammeter/config', {
      sample_rate: rate
    }, {
      onLoading: setLoading,
      loadingKey: 'setSampleRate',
      onError: (msg) => showError('设置采样率错误: ' + msg)
    })

    if (result.success && result.data?.success) {
      sampleRate.value = rate
      return true
    }

    return false
  }

  /**
   * 获取所有通道的信噪比
   *
   * @returns {Promise<Object>} 所有通道的信噪比数据
   */
  async function fetchAllSNR() {
    const results = {}

    for (let i = 1; i <= channelCount.value; i++) {
      const data = await fetchSNR(i)
      if (data) {
        results[i] = data
      }
    }

    return results
  }

  // ==================== 采集模板管理 ====================

  /**
   * 保存采集参数模板
   *
   * @param {string} name - 模板名称
   * @param {Object} config - 模板配置
   * @returns {string} 模板ID
   */
  function saveTemplate(name, config) {
    const template = {
      id: `template_${Date.now()}`,
      name: name,
      config: {
        sampleRate: config.sampleRate || sampleRate.value,
        channelConfig: { ...config.channelConfig } || { ...channelConfig.value },
        bufferConfig: { ...config.bufferConfig } || { ...bufferConfig.value },
        snrThresholds: { ...config.snrThresholds } || { ...snrThresholds.value }
      },
      createdAt: Date.now(),
      updatedAt: Date.now()
    }

    collectionTemplates.value.push(template)
    saveTemplatesToStorage()

    return template.id
  }

  /**
   * 加载采集参数模板
   *
   * @param {string} templateId - 模板ID
   * @returns {boolean} 加载是否成功
   */
  function loadTemplate(templateId) {
    const template = collectionTemplates.value.find(t => t.id === templateId)
    if (!template) {
      showError('模板不存在')
      return false
    }

    const config = template.config

    // 应用采样率
    if (config.sampleRate) {
      sampleRate.value = config.sampleRate
    }

    // 应用通道配置
    if (config.channelConfig) {
      Object.assign(channelConfig.value, config.channelConfig)
    }

    // 应用缓冲配置
    if (config.bufferConfig) {
      Object.assign(bufferConfig.value, config.bufferConfig)
    }

    // 应用SNR阈值
    if (config.snrThresholds) {
      Object.assign(snrThresholds.value, config.snrThresholds)
    }

    activeTemplateId.value = templateId

    return true
  }

  /**
   * 删除采集参数模板
   *
   * @param {string} templateId - 模板ID
   * @returns {boolean} 删除是否成功
   */
  function deleteTemplate(templateId) {
    const index = collectionTemplates.value.findIndex(t => t.id === templateId)
    if (index === -1) {
      showError('模板不存在')
      return false
    }

    collectionTemplates.value.splice(index, 1)
    saveTemplatesToStorage()

    if (activeTemplateId.value === templateId) {
      activeTemplateId.value = null
    }

    return true
  }

  /**
   * 更新采集参数模板
   *
   * @param {string} templateId - 模板ID
   * @param {Object} updates - 更新内容
   * @returns {boolean} 更新是否成功
   */
  function updateTemplate(templateId, updates) {
    const template = collectionTemplates.value.find(t => t.id === templateId)
    if (!template) {
      showError('模板不存在')
      return false
    }

    if (updates.name) {
      template.name = updates.name
    }

    if (updates.config) {
      template.config = {
        ...template.config,
        ...updates.config
      }
    }

    template.updatedAt = Date.now()
    saveTemplatesToStorage()

    return true
  }

  /**
   * 验证模板配置
   *
   * @param {Object} config - 模板配置
   * @returns {Object} 验证结果 { valid: boolean, errors: string[] }
   */
  function validateTemplateConfig(config) {
    const errors = []

    // 验证采样率
    if (config.sampleRate !== undefined) {
      if (config.sampleRate < 1 || config.sampleRate > 10000) {
        errors.push('采样率范围: 1-10000 Hz')
      }
    }

    // 验证通道配置
    if (config.channelConfig) {
      for (const [channel, chConfig] of Object.entries(config.channelConfig)) {
        const chNum = parseInt(channel)
        if (chNum < 1 || chNum > channelCount.value) {
          errors.push(`通道编号无效: ${channel}`)
        }

        if (chConfig.range && !['auto', 'low', 'medium', 'high'].includes(chConfig.range)) {
          errors.push(`通道${channel}量程配置无效`)
        }

        if (chConfig.filter && !['low', 'medium', 'high'].includes(chConfig.filter)) {
          errors.push(`通道${channel}滤波配置无效`)
        }
      }
    }

    // 验证缓冲配置
    if (config.bufferConfig) {
      if (config.bufferConfig.maxSize && config.bufferConfig.maxSize < 100) {
        errors.push('缓冲区最大值不能小于100')
      }

      if (config.bufferConfig.warningThreshold && 
          (config.bufferConfig.warningThreshold < 0 || config.bufferConfig.warningThreshold > 1)) {
        errors.push('警告阈值范围: 0-1')
      }

      if (config.bufferConfig.criticalThreshold && 
          (config.bufferConfig.criticalThreshold < 0 || config.bufferConfig.criticalThreshold > 1)) {
        errors.push('临界阈值范围: 0-1')
      }
    }

    // 验证SNR阈值
    if (config.snrThresholds) {
      if (config.snrThresholds.warning && config.snrThresholds.warning < 0) {
        errors.push('SNR警告阈值不能为负数')
      }

      if (config.snrThresholds.critical && config.snrThresholds.critical < 0) {
        errors.push('SNR临界阈值不能为负数')
      }

      if (config.snrThresholds.warning && config.snrThresholds.critical &&
          config.snrThresholds.warning <= config.snrThresholds.critical) {
        errors.push('SNR警告阈值应大于临界阈值')
      }
    }

    return {
      valid: errors.length === 0,
      errors: errors
    }
  }

  /**
   * 保存模板到本地存储
   */
  function saveTemplatesToStorage() {
    try {
      localStorage.setItem('ammeter_templates', JSON.stringify(collectionTemplates.value))
    } catch (error) {
      console.error('Failed to save templates:', error)
    }
  }

  /**
   * 从本地存储加载模板
   */
  function loadTemplatesFromStorage() {
    try {
      const stored = localStorage.getItem('ammeter_templates')
      if (stored) {
        collectionTemplates.value = JSON.parse(stored)
      }
    } catch (error) {
      console.error('Failed to load templates:', error)
      collectionTemplates.value = []
    }
  }

  // ==================== 数据缓冲管理 ====================

  /**
   * 更新缓冲配置
   *
   * @param {Object} config - 缓冲配置
   * @returns {boolean} 更新是否成功
   */
  function updateBufferConfig(config) {
    Object.assign(bufferConfig.value, config)
    return true
  }

  /**
   * 获取缓冲区使用趋势
   *
   * @param {number} duration - 时间范围（秒）
   * @returns {Array} 缓冲区使用趋势数据
   */
  function getBufferUsageTrend(duration = 60) {
    const now = Date.now()
    const startTime = now - duration * 1000

    // 从实时数据中提取缓冲区使用情况
    // 这里简化处理，实际应该记录缓冲区使用历史
    return realtimeData.value
      .filter(d => d.timestamp >= startTime)
      .map(d => ({
        timestamp: d.timestamp,
        usage: bufferUsagePercent.value
      }))
  }

  /**
   * 优化缓冲区大小
   *
   * @returns {Object} 优化建议
   */
  function optimizeBufferSize() {
    const stats = {
      currentSize: bufferStatus.value.max_size,
      averageUsage: 0,
      peakUsage: 0,
      recommendation: null
    }

    // 计算平均和峰值使用率
    if (realtimeData.value.length > 0) {
      const usageHistory = realtimeData.value.map(() => bufferUsagePercent.value)
      stats.averageUsage = usageHistory.reduce((a, b) => a + b, 0) / usageHistory.length
      stats.peakUsage = Math.max(...usageHistory)
    }

    // 生成优化建议
    if (stats.peakUsage > 90) {
      stats.recommendation = {
        action: 'increase',
        suggestedSize: Math.ceil(bufferStatus.value.max_size * 1.5),
        reason: '缓冲区峰值使用率过高，建议增加缓冲区大小'
      }
    } else if (stats.averageUsage < 30 && bufferStatus.value.max_size > 5000) {
      stats.recommendation = {
        action: 'decrease',
        suggestedSize: Math.ceil(bufferStatus.value.max_size * 0.7),
        reason: '缓冲区平均使用率较低，可以适当减小缓冲区大小以节省内存'
      }
    } else {
      stats.recommendation = {
        action: 'maintain',
        suggestedSize: bufferStatus.value.max_size,
        reason: '缓冲区大小适中，无需调整'
      }
    }

    return stats
  }

  // ==================== 辅助方法 ====================

  /**
   * 清除实时数据历史
   */
  function clearRealtimeData() {
    realtimeData.value = []
  }

  /**
   * 重置采集统计
   */
  function resetStats() {
    collectionStats.value = {
      start_time: null,
      duration: 0,
      samples_collected: 0,
      data_rate: 0
    }
  }

  // ==================== 生命周期方法 ====================

  /**
   * 初始化Store
   */
  function init() {
    fetchStatus()
    loadTemplatesFromStorage()
  }

  /**
   * 清理资源
   */
  function cleanup() {
    ammeterWS.disconnect()
    resetState()
    clearRealtimeData()
    resetStats()
    snrHistory.value = {}
    snrAlarms.value = {}
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

    // 微电流采集特有状态
    isCollecting,
    sampleRate,
    channelCount,
    channelData,
    channelConfig,
    bufferStatus,
    snrData,
    realtimeData,
    collectionStats,

    // 新增状态
    snrHistory,
    snrThresholds,
    snrAlarms,
    collectionTemplates,
    activeTemplateId,
    activeTemplate,
    bufferConfig,
    hasSNRAlarm,

    // 计算属性
    canControl,
    isCollectingData,
    bufferUsagePercent,
    bufferStatusType,
    bufferStatusText,

    // 基础方法（来自 useDeviceBase）
    showError,
    clearAlarm,
    setLoading,

    // API操作方法
    fetchStatus,
    startCollection,
    stopCollection,
    fetchRealtimeData,
    configureChannel,
    clearBuffer,
    fetchSNR,
    configureAllChannels,
    setSampleRate,
    fetchAllSNR,

    // SNR相关方法
    calculateRealtimeSNR,
    checkSNRAlarm,

    // 模板管理方法
    saveTemplate,
    loadTemplate,
    deleteTemplate,
    updateTemplate,
    validateTemplateConfig,

    // 缓冲管理方法
    updateBufferConfig,
    getBufferUsageTrend,
    optimizeBufferSize,
    checkAndAutoClearBuffer,

    // 辅助方法
    clearRealtimeData,
    resetStats,

    // WebSocket方法
    connectWebSocket: ammeterWS.connect,
    disconnectWebSocket: ammeterWS.disconnect,

    // 生命周期
    init,
    cleanup
  }
})
