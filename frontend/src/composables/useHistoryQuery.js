/**
 * @file useHistoryQuery.js
 * @path src/composables/
 * @description 历史数据查询条件管理组合式函数
 * @author Agent
 * @date 2024-03-07
 * @dependencies vue, pinia
 */

import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'

/**
 * 查询条件模板接口
 * @typedef {Object} QueryTemplate
 * @property {string} id - 模板ID
 * @property {string} name - 模板名称
 * @property {string} description - 模板描述
 * @property {Object} conditions - 查询条件
 * @property {number} createdAt - 创建时间戳
 * @property {number} updatedAt - 更新时间戳
 */

/**
 * 查询历史记录接口
 * @typedef {Object} QueryHistory
 * @property {string} id - 记录ID
 * @property {Object} conditions - 查询条件
 * @property {number} timestamp - 查询时间戳
 * @property {number} resultCount - 结果数量
 */

const STORAGE_KEY_TEMPLATES = 'history_query_templates'
const STORAGE_KEY_HISTORY = 'history_query_history'
const MAX_HISTORY_COUNT = 50

/**
 * 历史数据查询条件管理组合式函数
 * 
 * @param {Object} options - 配置选项
 * @param {boolean} options.autoSave - 是否自动保存查询历史
 * @param {number} options.maxHistory - 最大历史记录数
 * @returns {Object} 查询条件管理方法和状态
 * 
 * @example
 * const {
 *   queryConditions,
 *   templates,
 *   history,
 *   saveTemplate,
 *   applyTemplate,
 *   executeQuery
 * } = useHistoryQuery({ autoSave: true })
 */
export function useHistoryQuery(options = {}) {
  const {
    autoSave = true,
    maxHistory = MAX_HISTORY_COUNT
  } = options

  // ==================== 查询条件状态 ====================

  /** 当前查询条件 */
  const queryConditions = reactive({
    // 时间范围
    timeRange: {
      start: null,
      end: null,
      type: 'absolute' // 'absolute' | 'relative'
    },
    // 相对时间配置
    relativeTime: {
      value: 1,
      unit: 'hour' // 'minute' | 'hour' | 'day' | 'week' | 'month'
    },
    // 设备选择
    devices: [],
    // 实验选择
    experiments: [],
    // 数据类型
    dataTypes: [],
    // 高级选项
    advanced: {
      sampleInterval: 10,
      dataQuality: '', // '' | 'good' | 'normal' | 'poor'
      valueRange: [null, null],
      aggregation: 'none', // 'none' | 'avg' | 'max' | 'min' | 'sum'
      aggregationInterval: 60
    }
  })

  /** 是否正在查询 */
  const isQuerying = ref(false)

  /** 查询结果 */
  const queryResult = ref(null)

  /** 当前选中的模板ID */
  const selectedTemplateId = ref(null)

  // ==================== 查询模板管理 ====================

  /** 查询模板列表 */
  const templates = ref([])

  /** 加载模板列表 */
  function loadTemplates() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_TEMPLATES)
      if (stored) {
        templates.value = JSON.parse(stored)
      }
    } catch (error) {
      console.error('Failed to load templates:', error)
      templates.value = []
    }
  }

  /** 保存模板列表到本地存储 */
  function saveTemplatesToStorage() {
    try {
      localStorage.setItem(STORAGE_KEY_TEMPLATES, JSON.stringify(templates.value))
    } catch (error) {
      console.error('Failed to save templates:', error)
      ElMessage.error('保存模板失败')
    }
  }

  /**
   * 保存当前查询条件为模板
   * 
   * @param {string} name - 模板名称
   * @param {string} description - 模板描述
   * @returns {QueryTemplate|null} 创建的模板或null
   */
  function saveTemplate(name, description = '') {
    if (!name || name.trim() === '') {
      ElMessage.warning('请输入模板名称')
      return null
    }

    // 检查是否已存在同名模板
    const existingIndex = templates.value.findIndex(t => t.name === name.trim())
    if (existingIndex !== -1) {
      ElMessage.warning('模板名称已存在')
      return null
    }

    const template = {
      id: `template_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      name: name.trim(),
      description: description.trim(),
      conditions: JSON.parse(JSON.stringify(queryConditions)),
      createdAt: Date.now(),
      updatedAt: Date.now()
    }

    templates.value.unshift(template)
    saveTemplatesToStorage()
    ElMessage.success('模板保存成功')
    
    return template
  }

  /**
   * 更新模板
   * 
   * @param {string} templateId - 模板ID
   * @param {Object} updates - 更新内容
   * @returns {boolean} 更新是否成功
   */
  function updateTemplate(templateId, updates) {
    const index = templates.value.findIndex(t => t.id === templateId)
    if (index === -1) {
      ElMessage.warning('模板不存在')
      return false
    }

    templates.value[index] = {
      ...templates.value[index],
      ...updates,
      updatedAt: Date.now()
    }

    saveTemplatesToStorage()
    ElMessage.success('模板更新成功')
    return true
  }

  /**
   * 删除模板
   * 
   * @param {string} templateId - 模板ID
   * @returns {boolean} 删除是否成功
   */
  function deleteTemplate(templateId) {
    const index = templates.value.findIndex(t => t.id === templateId)
    if (index === -1) {
      return false
    }

    templates.value.splice(index, 1)
    saveTemplatesToStorage()
    ElMessage.success('模板已删除')
    return true
  }

  /**
   * 应用模板
   * 
   * @param {string} templateId - 模板ID
   * @returns {boolean} 应用是否成功
   */
  function applyTemplate(templateId) {
    const template = templates.value.find(t => t.id === templateId)
    if (!template) {
      ElMessage.warning('模板不存在')
      return false
    }

    // 深拷贝模板条件到当前查询条件
    Object.assign(queryConditions, JSON.parse(JSON.stringify(template.conditions)))
    selectedTemplateId.value = templateId
    ElMessage.success(`已应用模板: ${template.name}`)
    return true
  }

  // ==================== 查询历史管理 ====================

  /** 查询历史记录列表 */
  const history = ref([])

  /** 加载历史记录 */
  function loadHistory() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_HISTORY)
      if (stored) {
        history.value = JSON.parse(stored)
      }
    } catch (error) {
      console.error('Failed to load history:', error)
      history.value = []
    }
  }

  /** 保存历史记录到本地存储 */
  function saveHistoryToStorage() {
    try {
      localStorage.setItem(STORAGE_KEY_HISTORY, JSON.stringify(history.value))
    } catch (error) {
      console.error('Failed to save history:', error)
    }
  }

  /**
   * 添加查询历史记录
   * 
   * @param {Object} conditions - 查询条件
   * @param {number} resultCount - 结果数量
   */
  function addHistory(conditions, resultCount = 0) {
    const record = {
      id: `history_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      conditions: JSON.parse(JSON.stringify(conditions)),
      timestamp: Date.now(),
      resultCount
    }

    history.value.unshift(record)

    // 限制历史记录数量
    if (history.value.length > maxHistory) {
      history.value = history.value.slice(0, maxHistory)
    }

    saveHistoryToStorage()
  }

  /**
   * 应用历史记录
   * 
   * @param {string} historyId - 历史记录ID
   * @returns {boolean} 应用是否成功
   */
  function applyHistory(historyId) {
    const record = history.value.find(h => h.id === historyId)
    if (!record) {
      ElMessage.warning('历史记录不存在')
      return false
    }

    Object.assign(queryConditions, JSON.parse(JSON.stringify(record.conditions)))
    ElMessage.success('已应用历史查询条件')
    return true
  }

  /**
   * 清空历史记录
   */
  function clearHistory() {
    history.value = []
    saveHistoryToStorage()
    ElMessage.success('历史记录已清空')
  }

  /**
   * 删除单条历史记录
   * 
   * @param {string} historyId - 历史记录ID
   * @returns {boolean} 删除是否成功
   */
  function deleteHistory(historyId) {
    const index = history.value.findIndex(h => h.id === historyId)
    if (index === -1) {
      return false
    }

    history.value.splice(index, 1)
    saveHistoryToStorage()
    return true
  }

  // ==================== 查询执行 ====================

  /**
   * 执行查询
   * 
   * @param {Function} queryFn - 查询函数
   * @returns {Promise<Object|null>} 查询结果或null
   */
  async function executeQuery(queryFn) {
    if (isQuerying.value) {
      ElMessage.warning('正在查询中，请稍候')
      return null
    }

    isQuerying.value = true

    try {
      const result = await queryFn(queryConditions)
      queryResult.value = result

      // 自动保存查询历史
      if (autoSave) {
        addHistory(queryConditions, result?.total || 0)
      }

      return result
    } catch (error) {
      console.error('Query failed:', error)
      ElMessage.error('查询失败: ' + (error.message || '未知错误'))
      return null
    } finally {
      isQuerying.value = false
    }
  }

  /**
   * 重置查询条件
   */
  function resetConditions() {
    queryConditions.timeRange = {
      start: null,
      end: null,
      type: 'absolute'
    }
    queryConditions.relativeTime = {
      value: 1,
      unit: 'hour'
    }
    queryConditions.devices = []
    queryConditions.experiments = []
    queryConditions.dataTypes = []
    queryConditions.advanced = {
      sampleInterval: 10,
      dataQuality: '',
      valueRange: [null, null],
      aggregation: 'none',
      aggregationInterval: 60
    }
    selectedTemplateId.value = null
  }

  // ==================== 辅助方法 ====================

  /**
   * 获取相对时间范围
   * 
   * @returns {Object} 包含start和end时间戳的对象
   */
  function getRelativeTimeRange() {
    const now = Date.now()
    const { value, unit } = queryConditions.relativeTime
    let milliseconds = 0

    switch (unit) {
      case 'minute':
        milliseconds = value * 60 * 1000
        break
      case 'hour':
        milliseconds = value * 60 * 60 * 1000
        break
      case 'day':
        milliseconds = value * 24 * 60 * 60 * 1000
        break
      case 'week':
        milliseconds = value * 7 * 24 * 60 * 60 * 1000
        break
      case 'month':
        milliseconds = value * 30 * 24 * 60 * 60 * 1000
        break
      default:
        milliseconds = value * 60 * 60 * 1000
    }

    return {
      start: now - milliseconds,
      end: now
    }
  }

  /**
   * 获取实际查询时间范围
   * 
   * @returns {Object} 包含start和end时间戳的对象
   */
  function getActualTimeRange() {
    if (queryConditions.timeRange.type === 'relative') {
      return getRelativeTimeRange()
    }
    return {
      start: queryConditions.timeRange.start ? new Date(queryConditions.timeRange.start).getTime() : null,
      end: queryConditions.timeRange.end ? new Date(queryConditions.timeRange.end).getTime() : null
    }
  }

  /**
   * 验证查询条件
   * 
   * @returns {Object} 验证结果 { valid: boolean, message: string }
   */
  function validateConditions() {
    const timeRange = getActualTimeRange()

    if (!timeRange.start || !timeRange.end) {
      return { valid: false, message: '请选择时间范围' }
    }

    if (timeRange.start >= timeRange.end) {
      return { valid: false, message: '开始时间必须早于结束时间' }
    }

    if (queryConditions.devices.length === 0 && 
        queryConditions.experiments.length === 0 && 
        queryConditions.dataTypes.length === 0) {
      return { valid: false, message: '请至少选择一个设备、实验或数据类型' }
    }

    return { valid: true, message: '' }
  }

  // ==================== 初始化 ====================

  // 加载模板和历史记录
  loadTemplates()
  loadHistory()

  // ==================== 导出 ====================

  return {
    // 查询条件
    queryConditions,
    isQuerying,
    queryResult,
    selectedTemplateId,

    // 模板管理
    templates,
    saveTemplate,
    updateTemplate,
    deleteTemplate,
    applyTemplate,

    // 历史记录
    history,
    addHistory,
    applyHistory,
    clearHistory,
    deleteHistory,

    // 查询执行
    executeQuery,
    resetConditions,

    // 辅助方法
    getRelativeTimeRange,
    getActualTimeRange,
    validateConditions
  }
}
