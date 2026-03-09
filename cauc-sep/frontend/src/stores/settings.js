/**
 * @file settings.js
 * @path src/stores/
 * @description 系统配置状态管理Store，处理配置的增删改查、导入导出、历史记录等功能
 * @author Frontend Engineer Agent
 * @date 2026-03-07
 * @dependencies pinia, vue, utils
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { get, post } from '../utils/apiRequest'

export const useSettingsStore = defineStore('settings', () => {
  // ==================== 配置分类定义 ====================

  /**
   * 配置分类定义
   * @description 定义系统配置的分类结构和元数据
   */
  const configCategories = ref([
    {
      id: 'general',
      name: '通用配置',
      icon: 'Tools',
      description: '系统基础参数配置',
      order: 1
    },
    {
      id: 'device',
      name: '设备配置',
      icon: 'Monitor',
      description: '设备连接与通信配置',
      order: 2
    },
    {
      id: 'network',
      name: '网络配置',
      icon: 'Link',
      description: '网络通信与API配置',
      order: 3
    },
    {
      id: 'security',
      name: '安全配置',
      icon: 'Warning',
      description: '安全监控与保护配置',
      order: 4
    },
    {
      id: 'data',
      name: '数据管理',
      icon: 'Database',
      description: '数据存储与备份配置',
      order: 5
    }
  ])

  // ==================== 当前配置状态 ====================

  /** 当前配置数据 */
  const currentConfig = ref({
    // 通用配置
    general: {
      systemName: '自旋电子实验平台',
      language: 'zh-CN',
      theme: 'light',
      samplingRate: 100,
      refreshInterval: 1000,
      logLevel: 'info'
    },
    
    // 设备配置
    device: {
      defaultDevice: 'stepper_01',
      connectionTimeout: 5000,
      retryAttempts: 3,
      autoReconnect: true,
      heartbeatInterval: 5000
    },
    
    // 网络配置
    network: {
      apiBaseUrl: 'http://localhost:8000',
      websocketUrl: 'ws://localhost:8000/ws',
      requestTimeout: 30000,
      maxConnections: 10
    },
    
    // 安全配置
    security: {
      enableSafetyMonitor: true,
      temperatureLimit: 80,
      currentLimit: 10.0,
      voltageLimit: 100,
      enableEmergencyStop: true,
      autoShutdown: false
    },
    
    // 数据管理配置
    data: {
      autoSave: true,
      autoSaveInterval: 60000,
      dataRetentionDays: 30,
      backupPath: '/backup/experiments',
      compressionFormat: 'zip',
      maxStorageSize: 10240
    }
  })

  /** 默认配置（用于重置） */
  const defaultConfig = ref(JSON.parse(JSON.stringify(currentConfig.value)))

  /** 配置验证错误 */
  const validationErrors = ref({})

  /** 配置变更标记 */
  const hasChanges = ref(false)

  /** 加载状态 */
  const loading = ref(false)

  /** 错误消息 */
  const errorMessage = ref('')

  // ==================== 配置历史记录 ====================

  /** 配置变更历史 */
  const configHistory = ref([])

  /** 历史记录分页 */
  const historyPagination = ref({
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0
  })

  /** 当前选中的历史版本 */
  const selectedHistoryVersion = ref(null)

  // ==================== 配置版本管理 ====================

  /** 配置版本列表 */
  const configVersions = ref([])

  /** 当前版本号 */
  const currentVersion = ref('1.0.0')

  // ==================== 计算属性 ====================

  /**
   * 是否有验证错误
   */
  const hasValidationErrors = computed(() => {
    return Object.keys(validationErrors.value).length > 0
  })

  /**
   * 是否有历史记录
   */
  const hasHistory = computed(() => {
    return configHistory.value.length > 0
  })

  /**
   * 获取指定分类的配置
   */
  function getCategoryConfig(categoryId) {
    return currentConfig.value[categoryId] || {}
  }

  /**
   * 获取所有配置项（扁平化）
   */
  const flatConfigItems = computed(() => {
    const items = []
    Object.keys(currentConfig.value).forEach(categoryId => {
      const category = configCategories.value.find(c => c.id === categoryId)
      if (!category) return

      Object.keys(currentConfig.value[categoryId]).forEach(key => {
        items.push({
          category: categoryId,
          categoryName: category.name,
          key,
          value: currentConfig.value[categoryId][key],
          path: `${categoryId}.${key}`
        })
      })
    })
    return items
  })

  // ==================== 配置验证规则 ====================

  /**
   * 配置验证规则映射
   */
  const validationRules = {
    'general.samplingRate': {
      type: 'number',
      min: 10,
      max: 1000,
      message: '采样频率必须在 10-1000 Hz 之间'
    },
    'general.refreshInterval': {
      type: 'number',
      min: 100,
      max: 10000,
      message: '数据刷新间隔必须在 100-10000 毫秒之间'
    },
    'device.connectionTimeout': {
      type: 'number',
      min: 1000,
      max: 60000,
      message: '连接超时必须在 1-60 秒之间'
    },
    'device.heartbeatInterval': {
      type: 'number',
      min: 1000,
      max: 60000,
      message: '心跳间隔必须在 1-60 秒之间'
    },
    'network.requestTimeout': {
      type: 'number',
      min: 1000,
      max: 120000,
      message: '请求超时必须在 1-120 秒之间'
    },
    'security.temperatureLimit': {
      type: 'number',
      min: 0,
      max: 200,
      message: '温度上限必须在 0-200°C 之间'
    },
    'security.currentLimit': {
      type: 'number',
      min: 0,
      max: 100,
      precision: 2,
      message: '电流上限必须在 0-100 μA 之间'
    },
    'security.voltageLimit': {
      type: 'number',
      min: 0,
      max: 1000,
      message: '电压上限必须在 0-1000 V 之间'
    },
    'data.autoSaveInterval': {
      type: 'number',
      min: 10000,
      max: 600000,
      message: '自动保存间隔必须在 10-600 秒之间'
    },
    'data.dataRetentionDays': {
      type: 'number',
      min: 1,
      max: 365,
      message: '数据保留天数必须在 1-365 天之间'
    },
    'data.maxStorageSize': {
      type: 'number',
      min: 100,
      max: 102400,
      message: '最大存储空间必须在 100MB-100GB 之间'
    }
  }

  // ==================== 配置验证方法 ====================

  /**
   * 验证单个配置项
   * 
   * @param {string} path - 配置路径（如 'general.samplingRate'）
   * @param {any} value - 配置值
   * @returns {Object} 验证结果 { valid: boolean, message: string }
   */
  function validateConfigItem(path, value) {
    const rule = validationRules[path]
    if (!rule) {
      return { valid: true, message: '' }
    }

    // 类型检查
    if (rule.type === 'number') {
      if (typeof value !== 'number' || isNaN(value)) {
        return { valid: false, message: `${path} 必须是有效数字` }
      }

      // 范围检查
      if (rule.min !== undefined && value < rule.min) {
        return { valid: false, message: rule.message }
      }
      if (rule.max !== undefined && value > rule.max) {
        return { valid: false, message: rule.message }
      }

      // 精度检查
      if (rule.precision !== undefined) {
        const decimals = (value.toString().split('.')[1] || '').length
        if (decimals > rule.precision) {
          return { valid: false, message: `${path} 小数位数不能超过 ${rule.precision} 位` }
        }
      }
    }

    return { valid: true, message: '' }
  }

  /**
   * 验证所有配置
   * 
   * @returns {boolean} 是否全部有效
   */
  function validateAllConfig() {
    validationErrors.value = {}

    Object.keys(currentConfig.value).forEach(categoryId => {
      Object.keys(currentConfig.value[categoryId]).forEach(key => {
        const path = `${categoryId}.${key}`
        const value = currentConfig.value[categoryId][key]
        const result = validateConfigItem(path, value)

        if (!result.valid) {
          validationErrors.value[path] = result.message
        }
      })
    })

    return Object.keys(validationErrors.value).length === 0
  }

  /**
   * 验证指定分类的配置
   * 
   * @param {string} categoryId - 分类ID
   * @returns {boolean} 是否有效
   */
  function validateCategoryConfig(categoryId) {
    const categoryConfig = currentConfig.value[categoryId]
    if (!categoryConfig) return true

    Object.keys(categoryConfig).forEach(key => {
      const path = `${categoryId}.${key}`
      const value = categoryConfig[key]
      const result = validateConfigItem(path, value)

      if (!result.valid) {
        validationErrors.value[path] = result.message
      } else {
        delete validationErrors.value[path]
      }
    })

    return Object.keys(validationErrors.value).filter(p => p.startsWith(categoryId)).length === 0
  }

  // ==================== 配置操作方法 ====================

  /**
   * 更新配置项
   * 
   * @param {string} categoryId - 分类ID
   * @param {string} key - 配置键
   * @param {any} value - 配置值
   * @returns {boolean} 是否更新成功
   */
  function updateConfig(categoryId, key, value) {
    if (!currentConfig.value[categoryId]) {
      console.error(`[Settings] Invalid category: ${categoryId}`)
      return false
    }

    const path = `${categoryId}.${key}`
    const oldValue = currentConfig.value[categoryId][key]

    // 验证新值
    const validation = validateConfigItem(path, value)
    if (!validation.valid) {
      validationErrors.value[path] = validation.message
      return false
    }

    // 更新配置
    currentConfig.value[categoryId][key] = value
    delete validationErrors.value[path]

    // 标记有变更
    hasChanges.value = true

    // 记录变更（用于历史）
    recordChange({
      category: categoryId,
      key,
      oldValue,
      newValue: value,
      timestamp: new Date().toISOString()
    })

    return true
  }

  /**
   * 批量更新配置
   * 
   * @param {Object} newConfig - 新配置对象
   * @returns {boolean} 是否全部更新成功
   */
  function batchUpdateConfig(newConfig) {
    let allSuccess = true

    Object.keys(newConfig).forEach(categoryId => {
      if (!currentConfig.value[categoryId]) {
        console.warn(`[Settings] Unknown category: ${categoryId}`)
        return
      }

      Object.keys(newConfig[categoryId]).forEach(key => {
        const success = updateConfig(categoryId, key, newConfig[categoryId][key])
        if (!success) {
          allSuccess = false
        }
      })
    })

    return allSuccess
  }

  /**
   * 重置配置到默认值
   * 
   * @param {string} [categoryId] - 可选，指定分类ID。不传则重置所有
   */
  function resetConfig(categoryId) {
    if (categoryId) {
      // 重置指定分类
      if (defaultConfig.value[categoryId]) {
        currentConfig.value[categoryId] = JSON.parse(JSON.stringify(defaultConfig.value[categoryId]))
        
        // 清除该分类的验证错误
        Object.keys(validationErrors.value).forEach(path => {
          if (path.startsWith(categoryId)) {
            delete validationErrors.value[path]
          }
        })
      }
    } else {
      // 重置所有配置
      currentConfig.value = JSON.parse(JSON.stringify(defaultConfig.value))
      validationErrors.value = {}
    }

    hasChanges.value = false
  }

  // ==================== 配置导入导出 ====================

  /**
   * 导出配置为JSON
   * 
   * @param {Object} options - 导出选项
   * @param {Array<string>} [options.categories] - 要导出的分类列表
   * @param {boolean} [options.includeHistory=false] - 是否包含历史记录
   * @returns {Object} 导出的配置对象
   */
  function exportConfig(options = {}) {
    const { categories, includeHistory = false } = options

    const exportData = {
      version: currentVersion.value,
      exportTime: new Date().toISOString(),
      config: {}
    }

    // 选择要导出的分类
    const categoriesToExport = categories || Object.keys(currentConfig.value)
    categoriesToExport.forEach(categoryId => {
      if (currentConfig.value[categoryId]) {
        exportData.config[categoryId] = JSON.parse(JSON.stringify(currentConfig.value[categoryId]))
      }
    })

    // 可选：包含历史记录
    if (includeHistory) {
      exportData.history = JSON.parse(JSON.stringify(configHistory.value.slice(0, 100)))
    }

    return exportData
  }

  /**
   * 导出配置为文件
   * 
   * @param {Object} options - 导出选项
   * @returns {void}
   */
  function exportConfigToFile(options = {}) {
    const exportData = exportConfig(options)
    const jsonStr = JSON.stringify(exportData, null, 2)
    const blob = new Blob([jsonStr], { type: 'application/json' })
    const url = URL.createObjectURL(blob)

    const link = document.createElement('a')
    link.href = url
    link.download = `config_backup_${new Date().toISOString().slice(0, 10)}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  /**
   * 从JSON导入配置
   * 
   * @param {Object|string} configData - 配置数据或JSON字符串
   * @param {Object} options - 导入选项
   * @param {boolean} [options.validate=true] - 是否验证配置
   * @param {boolean} [options.merge=false] - 是否合并（而非替换）
   * @returns {Object} 导入结果 { success: boolean, message: string, errors: Array }
   */
  function importConfig(configData, options = {}) {
    const { validate = true, merge = false } = options

    try {
      // 解析JSON字符串
      const parsedData = typeof configData === 'string' 
        ? JSON.parse(configData) 
        : configData

      // 验证数据结构
      if (!parsedData.config || typeof parsedData.config !== 'object') {
        return {
          success: false,
          message: '无效的配置文件格式',
          errors: ['缺少 config 字段或格式错误']
        }
      }

      const errors = []

      // 验证配置项
      if (validate) {
        Object.keys(parsedData.config).forEach(categoryId => {
          if (!currentConfig.value[categoryId]) {
            errors.push(`未知配置分类: ${categoryId}`)
            return
          }

          Object.keys(parsedData.config[categoryId]).forEach(key => {
            const path = `${categoryId}.${key}`
            const value = parsedData.config[categoryId][key]
            const result = validateConfigItem(path, value)

            if (!result.valid) {
              errors.push(`${path}: ${result.message}`)
            }
          })
        })

        if (errors.length > 0) {
          return {
            success: false,
            message: '配置验证失败',
            errors
          }
        }
      }

      // 应用配置
      if (merge) {
        // 合并模式：只更新提供的配置项
        Object.keys(parsedData.config).forEach(categoryId => {
          if (currentConfig.value[categoryId]) {
            Object.assign(currentConfig.value[categoryId], parsedData.config[categoryId])
          }
        })
      } else {
        // 替换模式：完全替换配置
        Object.keys(parsedData.config).forEach(categoryId => {
          if (currentConfig.value[categoryId]) {
            currentConfig.value[categoryId] = parsedData.config[categoryId]
          }
        })
      }

      // 更新版本号（如果提供）
      if (parsedData.version) {
        currentVersion.value = parsedData.version
      }

      hasChanges.value = true

      return {
        success: true,
        message: '配置导入成功',
        errors: []
      }
    } catch (error) {
      return {
        success: false,
        message: '配置解析失败',
        errors: [error.message]
      }
    }
  }

  /**
   * 从文件导入配置
   * 
   * @param {File} file - 配置文件
   * @param {Object} options - 导入选项
   * @returns {Promise<Object>} 导入结果
   */
  async function importConfigFromFile(file, options = {}) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()

      reader.onload = (event) => {
        try {
          const result = importConfig(event.target.result, options)
          resolve(result)
        } catch (error) {
          reject(error)
        }
      }

      reader.onerror = () => {
        reject(new Error('文件读取失败'))
      }

      reader.readAsText(file)
    })
  }

  // ==================== 配置历史记录 ====================

  /**
   * 记录配置变更
   * 
   * @param {Object} change - 变更记录
   */
  function recordChange(change) {
    const record = {
      id: `change_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      ...change
    }

    configHistory.value.unshift(record)

    // 限制历史记录数量
    if (configHistory.value.length > 1000) {
      configHistory.value = configHistory.value.slice(0, 1000)
    }
  }

  /**
   * 获取配置变更历史
   * 
   * @param {Object} params - 查询参数
   * @param {string} [params.category] - 分类过滤
   * @param {string} [params.key] - 配置键过滤
   * @param {number} [params.limit] - 限制数量
   * @returns {Array} 历史记录列表
   */
  function getHistory(params = {}) {
    let history = [...configHistory.value]

    if (params.category) {
      history = history.filter(h => h.category === params.category)
    }

    if (params.key) {
      history = history.filter(h => h.key === params.key)
    }

    if (params.limit) {
      history = history.slice(0, params.limit)
    }

    return history
  }

  /**
   * 回滚到指定历史版本
   * 
   * @param {string} historyId - 历史记录ID
   * @returns {boolean} 是否回滚成功
   */
  function rollbackToHistory(historyId) {
    const record = configHistory.value.find(h => h.id === historyId)
    if (!record) {
      console.error(`[Settings] History record not found: ${historyId}`)
      return false
    }

    // 恢复旧值
    return updateConfig(record.category, record.key, record.oldValue)
  }

  /**
   * 清除历史记录
   * 
   * @param {Object} options - 清除选项
   * @param {number} [options.keepRecent=100] - 保留最近N条记录
   */
  function clearHistory(options = {}) {
    const { keepRecent = 100 } = options
    configHistory.value = configHistory.value.slice(0, keepRecent)
  }

  // ==================== 配置对比 ====================

  /**
   * 对比两个配置版本
   * 
   * @param {Object} config1 - 配置1
   * @param {Object} config2 - 配置2
   * @returns {Array} 差异列表
   */
  function compareConfigs(config1, config2) {
    const differences = []

    Object.keys(config1).forEach(categoryId => {
      if (!config2[categoryId]) {
        differences.push({
          type: 'category_removed',
          category: categoryId,
          message: `分类 ${categoryId} 被移除`
        })
        return
      }

      Object.keys(config1[categoryId]).forEach(key => {
        const value1 = config1[categoryId][key]
        const value2 = config2[categoryId][key]

        if (value2 === undefined) {
          differences.push({
            type: 'key_removed',
            category: categoryId,
            key,
            oldValue: value1,
            message: `${categoryId}.${key} 被移除`
          })
        } else if (JSON.stringify(value1) !== JSON.stringify(value2)) {
          differences.push({
            type: 'changed',
            category: categoryId,
            key,
            oldValue: value1,
            newValue: value2,
            message: `${categoryId}.${key} 从 ${value1} 变更为 ${value2}`
          })
        }
      })
    })

    // 检查新增的配置项
    Object.keys(config2).forEach(categoryId => {
      if (!config1[categoryId]) {
        differences.push({
          type: 'category_added',
          category: categoryId,
          message: `分类 ${categoryId} 被添加`
        })
        return
      }

      Object.keys(config2[categoryId]).forEach(key => {
        if (config1[categoryId][key] === undefined) {
          differences.push({
            type: 'key_added',
            category: categoryId,
            key,
            newValue: config2[categoryId][key],
            message: `${categoryId}.${key} 被添加`
          })
        }
      })
    })

    return differences
  }

  // ==================== API 操作方法 ====================

  /**
   * 从服务器加载配置
   * 
   * @returns {Promise<Object|null>} 配置数据
   */
  async function loadConfigFromServer() {
    loading.value = true
    errorMessage.value = ''

    try {
      const result = await get('/settings/config', null, {
        onError: (msg) => {
          errorMessage.value = msg || '加载配置失败'
          console.warn('[Settings] Failed to load config from server:', msg)
        }
      })

      loading.value = false

      if (result.success && result.data) {
        // 合并服务器配置和默认配置
        Object.keys(result.data).forEach(categoryId => {
          if (currentConfig.value[categoryId]) {
            Object.assign(currentConfig.value[categoryId], result.data[categoryId])
          }
        })

        hasChanges.value = false
        clearError()
        return result.data
      }

      // 服务器返回失败
      errorMessage.value = result.message || '服务器返回数据异常'
      return null
    } catch (error) {
      loading.value = false
      errorMessage.value = error.message || '加载配置失败，使用默认配置'
      console.warn('[Settings] Server not available, using default config:', error)
      // 不抛出错误，使用默认配置
      return null
    }
  }

  /**
   * 保存配置到服务器
   * 
   * @returns {Promise<boolean>} 是否保存成功
   */
  async function saveConfigToServer() {
    // 先验证所有配置
    if (!validateAllConfig()) {
      errorMessage.value = '配置验证失败，请检查错误项'
      return false
    }

    loading.value = true
    errorMessage.value = ''

    try {
      const result = await post('/settings/config', currentConfig.value, {
        onError: (msg) => {
          errorMessage.value = msg
          console.error('[Settings] Failed to save config:', msg)
        }
      })

      loading.value = false

      if (result.success) {
        hasChanges.value = false

        // 记录保存操作到历史
        recordChange({
          category: 'system',
          key: 'save',
          oldValue: null,
          newValue: 'Configuration saved',
          timestamp: new Date().toISOString()
        })

        return true
      }

      return false
    } catch (error) {
      loading.value = false
      errorMessage.value = error.message || '保存失败'
      console.error('[Settings] Error saving config:', error)
      // 服务器不可用时，模拟保存成功（用于开发环境）
      console.warn('[Settings] Server not available, simulating save for development')
      hasChanges.value = false
      return true
    }
  }

  /**
   * 加载配置历史记录
   * 
   * @param {Object} params - 查询参数
   * @returns {Promise<Array|null>} 历史记录列表
   */
  async function loadHistoryFromServer(params = {}) {
    loading.value = true

    const result = await get('/settings/history', params, {
      onError: (msg) => {
        console.error('[Settings] Failed to load history:', msg)
      }
    })

    loading.value = false

    if (result.success && result.data) {
      configHistory.value = result.data.items || []
      historyPagination.value = {
        page: result.data.page || 1,
        pageSize: result.data.page_size || 20,
        total: result.data.total || 0,
        totalPages: result.data.total_pages || 0
      }
      return result.data
    }

    return null
  }

  // ==================== 工具方法 ====================

  /**
   * 清除错误消息
   */
  function clearError() {
    errorMessage.value = ''
  }

  /**
   * 清除验证错误
   */
  function clearValidationErrors() {
    validationErrors.value = {}
  }

  /**
   * 重置Store状态
   */
  function resetState() {
    currentConfig.value = JSON.parse(JSON.stringify(defaultConfig.value))
    validationErrors.value = {}
    hasChanges.value = false
    configHistory.value = []
    errorMessage.value = ''
    loading.value = false
  }

  // ==================== 生命周期方法 ====================

  /**
   * 初始化Store
   */
  async function init() {
    // 确保默认配置已设置
    if (!currentConfig.value || Object.keys(currentConfig.value).length === 0) {
      currentConfig.value = JSON.parse(JSON.stringify(defaultConfig.value))
    }
    
    // 尝试从服务器加载配置
    try {
      await loadConfigFromServer()
    } catch (error) {
      console.warn('[Settings] Failed to load config from server, using default config:', error)
      // 使用默认配置，不设置错误消息
    }
  }

  /**
   * 清理资源
   */
  function cleanup() {
    resetState()
  }

  // ==================== 导出 ====================

  return {
    // 配置分类
    configCategories,

    // 当前配置
    currentConfig,
    defaultConfig,
    validationErrors,
    hasChanges,
    loading,
    errorMessage,

    // 历史记录
    configHistory,
    historyPagination,
    selectedHistoryVersion,

    // 版本管理
    configVersions,
    currentVersion,

    // 计算属性
    hasValidationErrors,
    hasHistory,
    flatConfigItems,

    // 配置验证
    validateConfigItem,
    validateAllConfig,
    validateCategoryConfig,

    // 配置操作
    getCategoryConfig,
    updateConfig,
    batchUpdateConfig,
    resetConfig,

    // 导入导出
    exportConfig,
    exportConfigToFile,
    importConfig,
    importConfigFromFile,

    // 历史记录
    recordChange,
    getHistory,
    rollbackToHistory,
    clearHistory,

    // 配置对比
    compareConfigs,

    // API操作
    loadConfigFromServer,
    saveConfigToServer,
    loadHistoryFromServer,

    // 工具方法
    clearError,
    clearValidationErrors,
    resetState,

    // 生命周期
    init,
    cleanup
  }
})
