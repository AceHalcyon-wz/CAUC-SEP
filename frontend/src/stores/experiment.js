/**
 * @file experiment.js
 * @path src/stores/
 * @description 实验管理状态管理Store，处理实验创建、控制、数据导出等功能
 * @author Agent
 * @date 2024-03-07
 * @dependencies pinia, vue, composables, utils
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useDeviceBase } from '../composables/useDeviceBase'
import { useWebSocket } from '../composables/useWebSocket'
import { get, post } from '../utils/apiRequest'
import { WS_BASE_URL } from '../config/api'

export const useExperimentStore = defineStore('experiment', () => {
  // ==================== 基础状态（从 useDeviceBase 获取） ====================

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
  } = useDeviceBase('experiment')

  // ==================== 实验特有状态 ====================

  /** 当前实验信息 */
  const currentExperiment = ref(null)

  /** 实验ID */
  const experimentId = ref(null)

  /** 实验名称 */
  const experimentName = ref('')

  /** 实验描述 */
  const experimentDescription = ref('')

  /** 实验状态 */
  const experimentStatus = ref('idle') // 'idle' | 'running' | 'paused' | 'completed' | 'error'

  /** 实验开始时间 */
  const startTime = ref(null)

  /** 实验结束时间 */
  const endTime = ref(null)

  /** 记录时长（秒） */
  const recordDuration = ref(0)

  /** 实验列表 */
  const experimentList = ref([])

  /** 实验详情 */
  const experimentDetail = ref(null)

  /** 实验数据 */
  const experimentData = ref([])

  /** 实验参数配置 */
  const experimentConfig = ref({
    sampleRate: 10,      // 采样率 (Hz)
    duration: 3600,      // 持续时间 (秒)
    autoStop: true,      // 自动停止
    saveInterval: 60     // 自动保存间隔 (秒)
  })

  /** 实验进度 (0-100) */
  const experimentProgress = computed(() => {
    if (!startTime.value || experimentStatus.value !== 'running') return 0
    const elapsed = (Date.now() - startTime.value) / 1000
    return Math.min(100, (elapsed / experimentConfig.value.duration) * 100)
  })

  /** 实验运行时长（格式化） */
  const formattedDuration = computed(() => {
    const duration = recordDuration.value
    const hours = Math.floor(duration / 3600)
    const minutes = Math.floor((duration % 3600) / 60)
    const seconds = Math.floor(duration % 60)
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
  })

  /** 是否正在运行实验 */
  const isRunning = computed(() => experimentStatus.value === 'running')

  /** 是否已暂停 */
  const isPaused = computed(() => experimentStatus.value === 'paused')

  /** 是否有当前实验 */
  const hasActiveExperiment = computed(() => currentExperiment.value !== null)

  // ==================== WebSocket 连接管理 ====================

  /**
   * WebSocket消息处理函数
   * 
   * @param {Object} data - WebSocket接收到的数据
   */
  function handleWebSocketMessage(data) {
    // 处理心跳消息
    if (data.type === 'ping' || data.ping) {
      experimentWS.send({ type: 'pong' })
      return
    }

    // 处理实验状态更新
    if (data.experiment_id !== undefined) {
      experimentId.value = data.experiment_id
      experimentStatus.value = data.status || experimentStatus.value
      recordDuration.value = data.duration || recordDuration.value
    }

    // 处理实验数据更新
    if (data.data !== undefined) {
      experimentData.value.push(data.data)
    }

    // 处理实验完成
    if (data.status === 'completed') {
      endTime.value = Date.now()
      experimentStatus.value = 'completed'
    }

    // 处理错误消息
    if (data.error) {
      console.error('WebSocket error:', data.error)
      showError(data.error)
      experimentStatus.value = 'error'
    }
  }

  /**
   * 初始化WebSocket连接
   */
  const experimentWS = useWebSocket({
    url: `${WS_BASE_URL}/ws/experiment`,
    onMessage: handleWebSocketMessage,
    onOpen: () => {
      console.log('Experiment WebSocket connected')
    },
    onClose: () => {
      console.log('Experiment WebSocket disconnected')
    },
    onError: (error) => {
      console.error('Experiment WebSocket error:', error)
    },
    reconnectInterval: 3000,
    heartbeatInterval: 30000
  })

  // ==================== API 操作方法 ====================

  /**
   * 开始实验
   * 
   * @param {string} name - 实验名称
   * @param {string} description - 实验描述
   * @param {Object} config - 实验配置（可选）
   * @returns {Promise<Object|null>} 实验信息或null
   */
  async function startExperiment(name, description, config = {}) {
    if (isRunning.value) {
      showError('已有实验正在运行')
      return null
    }

    setLoading(true, 'startExperiment')

    const result = await post('/api/experiments/start', {
      name: name,
      description: description,
      config: { ...experimentConfig.value, ...config }
    }, {
      onError: (msg) => showError('开始实验错误: ' + msg)
    })

    if (result.success && result.data) {
      const data = result.data
      currentExperiment.value = data
      experimentId.value = data.experiment_id
      experimentName.value = name
      experimentDescription.value = description
      experimentStatus.value = 'running'
      startTime.value = Date.now()
      endTime.value = null
      recordDuration.value = 0
      experimentData.value = []
      
      // 连接WebSocket
      experimentWS.connect()
      
      setLoading(false, 'startExperiment')
      return data
    }

    setLoading(false, 'startExperiment')
    return null
  }

  /**
   * 停止实验
   * 
   * @returns {Promise<Object|null>} 停止结果或null
   */
  async function stopExperiment() {
    if (!experimentId.value) {
      showError('没有正在运行的实验')
      return null
    }

    setLoading(true, 'stopExperiment')

    const result = await post(`/api/experiments/${experimentId.value}/stop`, null, {
      onError: (msg) => showError('停止实验错误: ' + msg)
    })

    if (result.success && result.data) {
      experimentStatus.value = 'completed'
      endTime.value = Date.now()
      
      // 断开WebSocket
      experimentWS.disconnect()
      
      setLoading(false, 'stopExperiment')
      return result.data
    }

    setLoading(false, 'stopExperiment')
    return null
  }

  /**
   * 暂停实验
   * 
   * @returns {Promise<boolean>} 暂停是否成功
   */
  async function pauseExperiment() {
    if (!experimentId.value || !isRunning.value) {
      showError('没有正在运行的实验')
      return false
    }

    setLoading(true, 'pauseExperiment')

    const result = await post(`/api/experiments/${experimentId.value}/pause`, null, {
      onError: (msg) => showError('暂停实验错误: ' + msg)
    })

    if (result.success) {
      experimentStatus.value = 'paused'
      setLoading(false, 'pauseExperiment')
      return true
    }

    setLoading(false, 'pauseExperiment')
    return false
  }

  /**
   * 恢复实验
   * 
   * @returns {Promise<boolean>} 恢复是否成功
   */
  async function resumeExperiment() {
    if (!experimentId.value || !isPaused.value) {
      showError('没有已暂停的实验')
      return false
    }

    setLoading(true, 'resumeExperiment')

    const result = await post(`/api/experiments/${experimentId.value}/resume`, null, {
      onError: (msg) => showError('恢复实验错误: ' + msg)
    })

    if (result.success) {
      experimentStatus.value = 'running'
      setLoading(false, 'resumeExperiment')
      return true
    }

    setLoading(false, 'resumeExperiment')
    return false
  }

  /**
   * 获取实验列表
   * 
   * @param {number} limit - 限制返回数量（可选，默认50）
   * @param {number} offset - 偏移量（可选，默认0）
   * @returns {Promise<Array>} 实验列表
   */
  async function fetchExperiments(limit = 50, offset = 0) {
    setLoading(true, 'fetchExperiments')

    const result = await get('/api/experiments', { limit, offset }, {
      onError: (msg) => showError('获取实验列表错误: ' + msg)
    })

    if (result.success && result.data) {
      experimentList.value = result.data.experiments || []
      setLoading(false, 'fetchExperiments')
      return experimentList.value
    }

    setLoading(false, 'fetchExperiments')
    return []
  }

  /**
   * 获取实验详情
   * 
   * @param {string} expId - 实验ID
   * @returns {Promise<Object|null>} 实验详情或null
   */
  async function fetchExperimentDetail(expId) {
    if (!expId) {
      showError('实验ID不能为空')
      return null
    }

    setLoading(true, 'fetchExperimentDetail')

    const result = await get(`/api/experiments/${expId}`, null, {
      onError: (msg) => showError('获取实验详情错误: ' + msg)
    })

    if (result.success && result.data) {
      experimentDetail.value = result.data
      setLoading(false, 'fetchExperimentDetail')
      return result.data
    }

    setLoading(false, 'fetchExperimentDetail')
    return null
  }

  /**
   * 导出实验数据
   * 
   * @param {string} expId - 实验ID
   * @param {string} format - 导出格式 ('csv' | 'json' | 'xlsx')
   * @returns {Promise<Blob|null>} 文件Blob对象或null
   */
  async function exportExperiment(expId, format = 'csv') {
    if (!expId) {
      showError('实验ID不能为空')
      return null
    }

    setLoading(true, 'exportExperiment')

    const result = await get(`/api/experiments/${expId}/export`, { format }, {
      onError: (msg) => showError('导出实验数据错误: ' + msg)
    })

    if (result.success && result.data) {
      setLoading(false, 'exportExperiment')
      return result.data
    }

    setLoading(false, 'exportExperiment')
    return null
  }

  /**
   * 删除实验
   * 
   * @param {string} expId - 实验ID
   * @returns {Promise<boolean>} 删除是否成功
   */
  async function deleteExperiment(expId) {
    if (!expId) {
      showError('实验ID不能为空')
      return false
    }

    setLoading(true, 'deleteExperiment')

    const result = await post(`/api/experiments/${expId}/delete`, null, {
      onError: (msg) => showError('删除实验错误: ' + msg)
    })

    if (result.success) {
      // 从列表中移除
      experimentList.value = experimentList.value.filter(exp => exp.experiment_id !== expId)
      
      // 如果删除的是当前实验，清空状态
      if (currentExperiment.value?.experiment_id === expId) {
        clearCurrentExperiment()
      }
      
      setLoading(false, 'deleteExperiment')
      return true
    }

    setLoading(false, 'deleteExperiment')
    return false
  }

  /**
   * 更新实验配置
   * 
   * @param {Object} config - 新的配置
   * @returns {Promise<boolean>} 更新是否成功
   */
  async function updateExperimentConfig(config) {
    if (!experimentId.value) {
      showError('没有正在运行的实验')
      return false
    }

    setLoading(true, 'updateConfig')

    const result = await post(`/api/experiments/${experimentId.value}/config`, config, {
      onError: (msg) => showError('更新配置错误: ' + msg)
    })

    if (result.success) {
      experimentConfig.value = { ...experimentConfig.value, ...config }
      setLoading(false, 'updateConfig')
      return true
    }

    setLoading(false, 'updateConfig')
    return false
  }

  /**
   * 获取实验数据
   * 
   * @param {string} expId - 实验ID
   * @param {Object} params - 查询参数
   * @param {number} params.start_time - 开始时间戳
   * @param {number} params.end_time - 结束时间戳
   * @returns {Promise<Array|null>} 实验数据或null
   */
  async function fetchExperimentData(expId, params = {}) {
    if (!expId) {
      showError('实验ID不能为空')
      return null
    }

    setLoading(true, 'fetchData')

    const result = await get(`/api/experiments/${expId}/data`, params, {
      onError: (msg) => showError('获取实验数据错误: ' + msg)
    })

    if (result.success && result.data) {
      setLoading(false, 'fetchData')
      return result.data.data || []
    }

    setLoading(false, 'fetchData')
    return null
  }

  // ==================== 辅助方法 ====================

  /**
   * 清空当前实验状态
   */
  function clearCurrentExperiment() {
    currentExperiment.value = null
    experimentId.value = null
    experimentName.value = ''
    experimentDescription.value = ''
    experimentStatus.value = 'idle'
    startTime.value = null
    endTime.value = null
    recordDuration.value = 0
    experimentData.value = []
  }

  /**
   * 更新记录时长（定时器调用）
   */
  function updateRecordDuration() {
    if (startTime.value && experimentStatus.value === 'running') {
      recordDuration.value = Math.floor((Date.now() - startTime.value) / 1000)
    }
  }

  /**
   * 设置实验配置
   * 
   * @param {Object} config - 配置对象
   */
  function setExperimentConfig(config) {
    experimentConfig.value = { ...experimentConfig.value, ...config }
  }

  // ==================== 生命周期方法 ====================

  /**
   * 初始化Store
   */
  function init() {
    fetchExperiments()
  }

  /**
   * 清理资源
   */
  function cleanup() {
    experimentWS.disconnect()
    clearCurrentExperiment()
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
    canControl,

    // 实验特有状态
    currentExperiment,
    experimentId,
    experimentName,
    experimentDescription,
    experimentStatus,
    startTime,
    endTime,
    recordDuration,
    experimentList,
    experimentDetail,
    experimentData,
    experimentConfig,

    // 计算属性
    experimentProgress,
    formattedDuration,
    isRunning,
    isPaused,
    hasActiveExperiment,

    // 基础方法（来自 useDeviceBase）
    showError,
    clearAlarm,
    setLoading,

    // 实验操作方法
    startExperiment,
    stopExperiment,
    pauseExperiment,
    resumeExperiment,
    fetchExperiments,
    fetchExperimentDetail,
    exportExperiment,
    deleteExperiment,
    updateExperimentConfig,
    fetchExperimentData,

    // 辅助方法
    clearCurrentExperiment,
    updateRecordDuration,
    setExperimentConfig,

    // WebSocket方法
    connectWebSocket: experimentWS.connect,
    disconnectWebSocket: experimentWS.disconnect,

    // 生命周期
    init,
    cleanup
  }
})
