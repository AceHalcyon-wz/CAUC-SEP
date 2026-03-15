/**
 * @file useErrorHandler.js
 * @path src/composables/
 * @description 错误处理组合式函数，提供统一的错误捕获、记录、分析和报告功能
 *              支持错误日志持久化存储、离线缓存、智能错误分析、错误聚合和上报机制
 * @author Agent
 * @date 2024-03-07
 * @dependencies vue, ../utils/offlineStorage
 */

import { ref, computed, readonly } from 'vue'
import {
  matchSolution,
  ERROR_TYPES,
  ERROR_SEVERITY,
  ERROR_SEVERITY_WEIGHT,
  getErrorIcon,
  getSeverityColor,
  getErrorTypeLabel,
  inferErrorType,
  inferErrorSeverity
} from '../utils/errorSolutions'
import { getOfflineStorage } from '../utils/offlineStorage'

/**
 * 错误历史记录最大数量
 */
const MAX_ERROR_HISTORY = 50

/**
 * 全局错误历史记录
 */
const errorHistory = ref([])

/**
 * 用户操作历史记录
 */
const userActionHistory = ref([])

/**
 * 最大操作历史记录数
 */
const MAX_ACTION_HISTORY = 100

/**
 * 错误聚合窗口时间（毫秒）
 */
const AGGREGATION_WINDOW = 5000

/**
 * 错误聚合映射
 */
const errorAggregationMap = new Map()

/**
 * 上报队列
 */
const reportQueue = ref([])

/**
 * 是否正在上报
 */
const isReporting = ref(false)

/**
 * 错误处理组合式函数
 *
 * @param {Object} options - 配置选项
 * @param {boolean} [options.enableHistory=true] - 是否启用错误历史记录
 * @param {boolean} [options.enableAutoReport=false] - 是否自动上报错误
 * @param {boolean} [options.enableOfflineCache=true] - 是否启用离线错误缓存
 * @param {boolean} [options.enableErrorLog=true] - 是否启用错误日志记录
 * @param {number} [options.maxOfflineErrors=100] - 离线缓存最大错误数量
 * @param {Function} [options.onReport] - 错误上报回调函数
 * @returns {Object} 错误处理方法和状态
 *
 * @example
 * ```javascript
 * const { handleError, getErrorReport, copyErrorInfo } = useErrorHandler({
 *   enableHistory: true,
 *   enableOfflineCache: true,
 *   onReport: (report) => sendToServer(report)
 * })
 *
 * try {
 *   await riskyOperation()
 * } catch (error) {
 *   const errorInfo = handleError(error, { context: '数据加载' })
 *   console.log(errorInfo.solution.title)
 * }
 * ```
 */
export function useErrorHandler(options = {}) {
  const {
    enableHistory = true,
    enableAutoReport = false,
    enableOfflineCache = true,
    enableErrorLog = true,
    maxOfflineErrors = 100,
    onReport
  } = options

  /**
   * 当前错误信息
   */
  const currentError = ref(null)

  /**
   * 错误可见性
   */
  const errorVisible = ref(false)

  /**
   * 是否正在生成报告
   */
  const isGeneratingReport = ref(false)

  /**
   * 离线存储实例
   */
  let offlineStorage = null

  /**
   * 离线错误队列（待上报）
   */
  const offlineErrorQueue = ref([])

  /**
   * 是否正在同步离线错误
   */
  const isSyncingOffline = ref(false)

  /**
   * 处理错误
   *
   * @param {Error|string} error - 错误对象或错误消息
   * @param {Object} context - 错误上下文信息
   * @param {string} [context.component] - 发生错误的组件名称
   * @param {string} [context.action] - 正在执行的操作
   * @param {Object} [context.data] - 相关数据
   * @param {string} [context.userMessage] - 用户友好的错误消息
   * @returns {Object} 错误信息对象
   */
  function handleError(error, context = {}) {
    // 解析错误信息
    const errorInfo = parseError(error, context)

    // 匹配解决方案
    errorInfo.solution = matchSolution(error)

    // 错误聚合处理
    const aggregatedError = aggregateError(errorInfo)
    if (aggregatedError.isAggregated) {
      errorInfo.aggregated = true
      errorInfo.occurrenceCount = aggregatedError.count
      errorInfo.firstOccurrence = aggregatedError.firstOccurrence
    }

    // 记录到历史
    if (enableHistory) {
      addToHistory(errorInfo)
    }

    // 记录错误日志
    if (enableErrorLog) {
      logError(errorInfo)
    }

    // 离线缓存错误
    if (enableOfflineCache) {
      cacheErrorOffline(errorInfo)
    }

    // 添加到上报队列
    if (onReport) {
      addToReportQueue(errorInfo)
    }

    // 自动上报
    if (enableAutoReport && onReport) {
      reportError(errorInfo)
    }

    // 设置当前错误
    currentError.value = errorInfo
    errorVisible.value = true

    return errorInfo
  }

  /**
   * 解析错误对象
   *
   * @param {Error|string} error - 错误对象或错误消息
   * @param {Object} context - 错误上下文
   * @returns {Object} 标准化的错误信息对象
   * @internal 内部方法，不对外暴露
   */
  function parseError(error, context) {
    const timestamp = new Date().toISOString()
    const id = `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

    // 提取错误堆栈
    const stack = error?.stack || new Error().stack
    const stackLines = stack ? stack.split('\n').slice(0, 10) : []

    // 系统状态快照
    const systemSnapshot = captureSystemSnapshot()

    return {
      id,
      timestamp,
      message: error?.message || error?.toString() || '未知错误',
      name: error?.name || 'Error',
      stack: stackLines,
      fullStack: stack,
      type: error?.type || ERROR_TYPES.UNKNOWN,
      severity: error?.severity || ERROR_SEVERITY.MEDIUM,
      context: {
        component: context.component || 'Unknown',
        action: context.action || 'Unknown',
        data: context.data || null,
        userMessage: context.userMessage || null,
        route: window.location.pathname,
        url: window.location.href
      },
      system: systemSnapshot,
      userActions: getUserActionsSnapshot(),
      solution: null
    }
  }

  /**
   * 捕获系统状态快照
   *
   * @returns {Object} 系统状态快照
   * @internal 内部方法，不对外暴露
   */
  function captureSystemSnapshot() {
    return {
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      platform: navigator.platform,
      language: navigator.language,
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight
      },
      screen: {
        width: window.screen.width,
        height: window.screen.height
      },
      memory: performance.memory ? {
        usedJSHeapSize: formatBytes(performance.memory.usedJSHeapSize),
        totalJSHeapSize: formatBytes(performance.memory.totalJSHeapSize),
        jsHeapSizeLimit: formatBytes(performance.memory.jsHeapSizeLimit)
      } : null,
      connection: navigator.connection ? {
        effectiveType: navigator.connection.effectiveType,
        downlink: navigator.connection.downlink,
        rtt: navigator.connection.rtt
      } : null,
      online: navigator.onLine
    }
  }

  /**
   * 获取用户操作历史快照
   *
   * @returns {Array} 最近10条用户操作
   * @internal 内部方法，不对外暴露
   */
  function getUserActionsSnapshot() {
    return userActionHistory.value.slice(-10)
  }

  /**
   * 添加错误到历史记录
   *
   * @param {Object} errorInfo - 错误信息对象
   * @internal 内部方法，不对外暴露
   */
  function addToHistory(errorInfo) {
    errorHistory.value.unshift(errorInfo)
    // 限制历史记录数量
    if (errorHistory.value.length > MAX_ERROR_HISTORY) {
      errorHistory.value = errorHistory.value.slice(0, MAX_ERROR_HISTORY)
    }
  }

  /**
   * 记录错误日志到控制台和本地存储
   *
   * @param {Object} errorInfo - 错误信息对象
   * @internal 内部方法，不对外暴露
   */
  function logError(errorInfo) {
    // 控制台日志（带颜色和格式）
    const logStyle = {
      [ERROR_SEVERITY.LOW]: 'color: #67C23A',
      [ERROR_SEVERITY.MEDIUM]: 'color: #E6A23C',
      [ERROR_SEVERITY.HIGH]: 'color: #F56C6C',
      [ERROR_SEVERITY.CRITICAL]: 'color: #F56C6C; font-weight: bold'
    }

    console.group(
      `%c[${errorInfo.severity.toUpperCase()}] ${getErrorTypeLabel(errorInfo.type)}`,
      logStyle[errorInfo.severity] || logStyle[ERROR_SEVERITY.MEDIUM]
    )
    console.error('错误消息:', errorInfo.message)
    console.error('错误ID:', errorInfo.id)
    console.error('发生时间:', errorInfo.timestamp)
    console.error('组件:', errorInfo.context.component)
    console.error('操作:', errorInfo.context.action)
    if (errorInfo.context.userMessage) {
      console.warn('用户提示:', errorInfo.context.userMessage)
    }
    if (errorInfo.solution) {
      console.info('解决方案:', errorInfo.solution.title)
    }
    console.groupEnd()

    // 保存到本地存储（localStorage作为备份）
    try {
      const errorLogs = JSON.parse(localStorage.getItem('error_logs') || '[]')
      errorLogs.unshift({
        id: errorInfo.id,
        timestamp: errorInfo.timestamp,
        type: errorInfo.type,
        severity: errorInfo.severity,
        message: errorInfo.message,
        component: errorInfo.context.component,
        action: errorInfo.context.action
      })
      // 只保留最近50条
      localStorage.setItem('error_logs', JSON.stringify(errorLogs.slice(0, 50)))
    } catch (err) {
      console.warn('[ErrorHandler] 保存错误日志失败:', err)
    }
  }

  /**
   * 离线缓存错误（用于离线时暂存，在线后上报）
   *
   * @param {Object} errorInfo - 错误信息对象
   * @internal 内部方法，不对外暴露
   */
  async function cacheErrorOffline(errorInfo) {
    try {
      // 如果离线存储未初始化，尝试初始化
      if (!offlineStorage) {
        offlineStorage = getOfflineStorage()
      }

      // 如果存储已初始化，保存错误
      if (offlineStorage && offlineStorage.db) {
        const errorData = {
          ...errorInfo,
          cachedAt: Date.now(),
          synced: false
        }

        await offlineStorage.set('cacheData', `error_${errorInfo.id}`, errorData, {
          ttl: 7 * 24 * 60 * 60 * 1000, // 7天过期
          category: 'error_log'
        })

        // 添加到离线队列
        offlineErrorQueue.value.push({
          id: errorInfo.id,
          timestamp: errorInfo.timestamp,
          type: errorInfo.type,
          severity: errorInfo.severity
        })

        // 限制队列大小
        if (offlineErrorQueue.value.length > maxOfflineErrors) {
          offlineErrorQueue.value = offlineErrorQueue.value.slice(-maxOfflineErrors)
        }

        console.log('[ErrorHandler] 错误已缓存到离线存储:', errorInfo.id)
      }
    } catch (err) {
      console.warn('[ErrorHandler] 离线缓存失败:', err)
    }
  }

  /**
   * 同步离线错误（在线时调用）
   *
   * @returns {Promise<Object>} 同步结果
   */
  async function syncOfflineErrors() {
    if (isSyncingOffline.value) {
      return { success: false, message: '正在同步中' }
    }

    if (!onReport) {
      return { success: false, message: '未配置上报回调' }
    }

    isSyncingOffline.value = true
    const result = {
      total: 0,
      synced: 0,
      failed: 0,
      errors: []
    }

    try {
      if (!offlineStorage || !offlineStorage.db) {
        offlineStorage = getOfflineStorage()
      }

      if (!offlineStorage || !offlineStorage.db) {
        return { success: false, message: '离线存储未初始化' }
      }

      // 获取所有未同步的错误
      const cachedErrors = await offlineStorage.getByIndex('cacheData', 'category', 'error_log')
      const unsyncedErrors = cachedErrors.filter(e => !e.synced && e.id)

      result.total = unsyncedErrors.length

      // 逐个上报
      for (const errorData of unsyncedErrors) {
        try {
          const report = generateReport(errorData)
          await onReport(report)

          // 标记为已同步
          errorData.synced = true
          errorData.syncedAt = Date.now()
          await offlineStorage.set('cacheData', `error_${errorData.id}`, errorData, {
            ttl: 7 * 24 * 60 * 60 * 1000,
            category: 'error_log'
          })

          result.synced++
        } catch (err) {
          result.failed++
          result.errors.push({
            id: errorData.id,
            error: err.message
          })
        }
      }

      // 更新离线队列
      offlineErrorQueue.value = offlineErrorQueue.value.filter(e => {
        return !unsyncedErrors.find(ue => ue.id === e.id && ue.synced)
      })

      console.log(`[ErrorHandler] 离线错误同步完成: ${result.synced}/${result.total}`)

      return {
        success: true,
        ...result
      }
    } catch (err) {
      console.error('[ErrorHandler] 同步离线错误失败:', err)
      return {
        success: false,
        error: err.message,
        ...result
      }
    } finally {
      isSyncingOffline.value = false
    }
  }

  /**
   * 获取离线错误统计
   *
   * @returns {Object} 离线错误统计信息
   */
  function getOfflineErrorStats() {
    return {
      queueLength: offlineErrorQueue.value.length,
      isSyncing: isSyncingOffline.value,
      errors: offlineErrorQueue.value
    }
  }

  /**
   * 清除离线错误缓存
   *
   * @returns {Promise<void>}
   */
  async function clearOfflineErrors() {
    try {
      if (!offlineStorage || !offlineStorage.db) {
        offlineStorage = getOfflineStorage()
      }

      if (offlineStorage && offlineStorage.db) {
        const cachedErrors = await offlineStorage.getByIndex('cacheData', 'category', 'error_log')
        for (const error of cachedErrors) {
          if (error.key) {
            await offlineStorage.delete('cacheData', error.key)
          }
        }
      }

      offlineErrorQueue.value = []
      console.log('[ErrorHandler] 离线错误缓存已清除')
    } catch (err) {
      console.error('[ErrorHandler] 清除离线错误失败:', err)
    }
  }

  /**
   * 记录用户操作
   *
   * @param {string} action - 操作名称
   * @param {Object} [data] - 操作数据
   */
  function recordAction(action, data = null) {
    userActionHistory.value.push({
      timestamp: new Date().toISOString(),
      action,
      data,
      route: window.location.pathname
    })

    // 限制历史记录数量
    if (userActionHistory.value.length > MAX_ACTION_HISTORY) {
      userActionHistory.value = userActionHistory.value.slice(-MAX_ACTION_HISTORY)
    }
  }

  /**
   * 生成错误报告
   *
   * @param {Object} [errorInfo] - 错误信息对象，不传则使用当前错误
   * @returns {Object} 错误报告对象
   */
  function generateReport(errorInfo = null) {
    const targetError = errorInfo || currentError.value
    if (!targetError) {
      return null
    }

    isGeneratingReport.value = true

    try {
      const report = {
        reportId: targetError.id,
        reportTime: new Date().toISOString(),
        error: {
          message: targetError.message,
          name: targetError.name,
          type: targetError.type,
          severity: targetError.severity,
          stack: targetError.fullStack
        },
        context: targetError.context,
        system: targetError.system,
        userActions: targetError.userActions,
        solution: targetError.solution ? {
          title: targetError.solution.title,
          type: targetError.solution.type,
          severity: targetError.solution.severity
        } : null
      }

      return report
    } finally {
      isGeneratingReport.value = false
    }
  }

  /**
   * 上报错误
   *
   * @param {Object} errorInfo - 错误信息对象
   */
  async function reportError(errorInfo) {
    const report = generateReport(errorInfo)
    if (report && onReport) {
      try {
        await onReport(report)
      } catch (err) {
        console.error('[ErrorHandler] 上报错误失败:', err)
      }
    }
  }

  /**
   * 复制错误信息到剪贴板
   *
   * @param {string} type - 复制类型：'detail' | 'stack' | 'report'
   * @param {Object} [errorInfo] - 错误信息对象，不传则使用当前错误
   * @returns {Promise<boolean>} 是否复制成功
   */
  async function copyErrorInfo(type = 'detail', errorInfo = null) {
    const targetError = errorInfo || currentError.value
    if (!targetError) {
      return false
    }

    let content = ''

    switch (type) {
      case 'detail':
        content = formatErrorDetail(targetError)
        break
      case 'stack':
        content = formatErrorStack(targetError)
        break
      case 'report':
        content = formatErrorReport(targetError)
        break
      default:
        content = formatErrorDetail(targetError)
    }

    try {
      await navigator.clipboard.writeText(content)
      return true
    } catch (err) {
      console.error('[ErrorHandler] 复制失败:', err)
      // 降级方案：使用传统复制方法
      return fallbackCopy(content)
    }
  }

  /**
   * 格式化错误详情（用于复制）
   *
   * @param {Object} errorInfo - 错误信息对象
   * @returns {string} 格式化后的文本
   * @internal 内部方法，不对外暴露
   */
  function formatErrorDetail(errorInfo) {
    const lines = [
      `错误ID: ${errorInfo.id}`,
      `时间: ${errorInfo.timestamp}`,
      `类型: ${getErrorTypeLabel(errorInfo.type)}`,
      `严重程度: ${errorInfo.severity}`,
      `消息: ${errorInfo.message}`,
      '',
      '上下文信息:',
      `  组件: ${errorInfo.context.component}`,
      `  操作: ${errorInfo.context.action}`,
      `  路由: ${errorInfo.context.route}`,
      errorInfo.context.userMessage ? `  提示: ${errorInfo.context.userMessage}` : '',
      '',
      '解决方案:',
      errorInfo.solution ? `  ${errorInfo.solution.title}` : '  未找到解决方案'
    ]

    return lines.filter(Boolean).join('\n')
  }

  /**
   * 格式化错误堆栈（用于复制）
   *
   * @param {Object} errorInfo - 错误信息对象
   * @returns {string} 格式化后的文本
   * @internal 内部方法，不对外暴露
   */
  function formatErrorStack(errorInfo) {
    const lines = [
      `错误: ${errorInfo.name}: ${errorInfo.message}`,
      '',
      '堆栈跟踪:',
      ...errorInfo.stack
    ]

    return lines.join('\n')
  }

  /**
   * 格式化错误报告（用于复制）
   *
   * @param {Object} errorInfo - 错误信息对象
   * @returns {string} 格式化后的JSON文本
   * @internal 内部方法，不对外暴露
   */
  function formatErrorReport(errorInfo) {
    const report = generateReport(errorInfo)
    return JSON.stringify(report, null, 2)
  }

  /**
   * 降级复制方法
   *
   * @param {string} content - 要复制的内容
   * @returns {boolean} 是否复制成功
   * @internal 内部方法，不对外暴露
   */
  function fallbackCopy(content) {
    try {
      const textarea = document.createElement('textarea')
      textarea.value = content
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      const success = document.execCommand('copy')
      document.body.removeChild(textarea)
      return success
    } catch (err) {
      console.error('[ErrorHandler] 降级复制失败:', err)
      return false
    }
  }

  /**
   * 清除当前错误
   */
  function clearError() {
    currentError.value = null
    errorVisible.value = false
  }

  /**
   * 清除错误历史
   */
  function clearHistory() {
    errorHistory.value = []
    userActionHistory.value = []
  }

  /**
   * 格式化字节大小
   *
   * @param {number} bytes - 字节数
   * @returns {string} 格式化后的字符串
   * @internal 内部方法，不对外暴露
   */
  function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  /**
   * 错误统计信息
   */
  const errorStats = computed(() => {
    const total = errorHistory.value.length
    const byType = {}
    const bySeverity = {}
    const byComponent = {}
    const recentCount = {
      lastHour: 0,
      lastDay: 0,
      lastWeek: 0
    }

    const now = Date.now()
    const oneHour = 60 * 60 * 1000
    const oneDay = 24 * oneHour
    const oneWeek = 7 * oneDay

    errorHistory.value.forEach(err => {
      // 按类型统计
      byType[err.type] = (byType[err.type] || 0) + 1
      
      // 按严重程度统计
      bySeverity[err.severity] = (bySeverity[err.severity] || 0) + 1
      
      // 按组件统计
      if (err.context?.component) {
        byComponent[err.context.component] = (byComponent[err.context.component] || 0) + 1
      }

      // 时间段统计
      const errorTime = new Date(err.timestamp).getTime()
      if (now - errorTime <= oneHour) recentCount.lastHour++
      if (now - errorTime <= oneDay) recentCount.lastDay++
      if (now - errorTime <= oneWeek) recentCount.lastWeek++
    })

    return {
      total,
      byType,
      bySeverity,
      byComponent,
      recentCount
    }
  })

  /**
   * 错误聚合处理
   *
   * @param {Object} errorInfo - 错误信息对象
   * @returns {Object} 聚合结果
   * @internal 内部方法，不对外暴露
   */
  function aggregateError(errorInfo) {
    const fingerprint = generateErrorFingerprint(errorInfo)
    const now = Date.now()

    if (errorAggregationMap.has(fingerprint)) {
      const record = errorAggregationMap.get(fingerprint)
      
      // 检查是否在聚合窗口内
      if (now - record.lastOccurrence <= AGGREGATION_WINDOW) {
        record.count++
        record.lastOccurrence = now
        return {
          isAggregated: true,
          count: record.count,
          firstOccurrence: record.firstOccurrence
        }
      } else {
        // 超出窗口，重置计数
        record.count = 1
        record.firstOccurrence = now
        record.lastOccurrence = now
      }
    } else {
      // 新错误，创建聚合记录
      errorAggregationMap.set(fingerprint, {
        count: 1,
        firstOccurrence: now,
        lastOccurrence: now
      })
    }

    return { isAggregated: false }
  }

  /**
   * 生成错误指纹（用于聚合识别）
   *
   * @param {Object} errorInfo - 错误信息对象
   * @returns {string} 错误指纹
   * @internal 内部方法，不对外暴露
   */
  function generateErrorFingerprint(errorInfo) {
    const parts = [
      errorInfo.type,
      errorInfo.message?.substring(0, 100),
      errorInfo.context?.component,
      errorInfo.context?.action
    ]
    return parts.filter(Boolean).join('::')
  }

  /**
   * 添加到上报队列
   *
   * @param {Object} errorInfo - 错误信息对象
   * @internal 内部方法，不对外暴露
   */
  function addToReportQueue(errorInfo) {
    reportQueue.value.push({
      id: errorInfo.id,
      timestamp: errorInfo.timestamp,
      retryCount: 0,
      error: errorInfo
    })
  }

  /**
   * 批量上报错误
   *
   * @param {Object} options - 上报选项
   * @param {number} [options.batchSize=10] - 每批上报数量
   * @param {number} [options.maxRetries=3] - 最大重试次数
   * @returns {Promise<Object>} 上报结果
   */
  async function batchReportErrors(options = {}) {
    const { batchSize = 10, maxRetries = 3 } = options

    if (isReporting.value || !onReport) {
      return { success: false, message: '无法上报' }
    }

    isReporting.value = true
    const result = {
      total: reportQueue.value.length,
      reported: 0,
      failed: 0,
      errors: []
    }

    try {
      const batch = reportQueue.value.slice(0, batchSize)
      
      for (const item of batch) {
        try {
          const report = generateReport(item.error)
          await onReport(report)
          
          // 上报成功，从队列移除
          const index = reportQueue.value.findIndex(i => i.id === item.id)
          if (index !== -1) {
            reportQueue.value.splice(index, 1)
          }
          result.reported++
        } catch (err) {
          item.retryCount++
          
          if (item.retryCount >= maxRetries) {
            // 超过重试次数，移除并记录失败
            const index = reportQueue.value.findIndex(i => i.id === item.id)
            if (index !== -1) {
              reportQueue.value.splice(index, 1)
            }
            result.failed++
            result.errors.push({
              id: item.id,
              error: err.message
            })
          }
        }
      }

      return { success: true, ...result }
    } catch (err) {
      console.error('[ErrorHandler] 批量上报失败:', err)
      return { success: false, error: err.message, ...result }
    } finally {
      isReporting.value = false
    }
  }

  /**
   * 获取上报队列状态
   *
   * @returns {Object} 队列状态
   */
  function getReportQueueStatus() {
    return {
      queueLength: reportQueue.value.length,
      isReporting: isReporting.value,
      pendingItems: reportQueue.value.map(item => ({
        id: item.id,
        timestamp: item.timestamp,
        retryCount: item.retryCount
      }))
    }
  }

  /**
   * 清空上报队列
   */
  function clearReportQueue() {
    reportQueue.value = []
  }

  /**
   * 获取错误趋势分析
   *
   * @param {number} [days=7] - 分析天数
   * @returns {Object} 趋势分析结果
   */
  function getErrorTrends(days = 7) {
    const now = Date.now()
    const dayMs = 24 * 60 * 60 * 1000
    const trends = []

    for (let i = 0; i < days; i++) {
      const dayStart = now - (i + 1) * dayMs
      const dayEnd = now - i * dayMs
      
      const dayErrors = errorHistory.value.filter(err => {
        const errorTime = new Date(err.timestamp).getTime()
        return errorTime >= dayStart && errorTime < dayEnd
      })

      trends.push({
        date: new Date(dayStart).toLocaleDateString('zh-CN'),
        total: dayErrors.length,
        bySeverity: {
          low: dayErrors.filter(e => e.severity === ERROR_SEVERITY.LOW).length,
          medium: dayErrors.filter(e => e.severity === ERROR_SEVERITY.MEDIUM).length,
          high: dayErrors.filter(e => e.severity === ERROR_SEVERITY.HIGH).length,
          critical: dayErrors.filter(e => e.severity === ERROR_SEVERITY.CRITICAL).length
        },
        byType: dayErrors.reduce((acc, err) => {
          acc[err.type] = (acc[err.type] || 0) + 1
          return acc
        }, {})
      })
    }

    return trends.reverse()
  }

  return {
    // 状态
    currentError: readonly(currentError),
    errorVisible: readonly(errorVisible),
    errorHistory: readonly(errorHistory),
    errorStats,
    isGeneratingReport: readonly(isGeneratingReport),
    offlineErrorQueue: readonly(offlineErrorQueue),
    isSyncingOffline: readonly(isSyncingOffline),
    reportQueue: readonly(reportQueue),
    isReporting: readonly(isReporting),

    // 方法
    handleError,
    clearError,
    clearHistory,
    recordAction,
    generateReport,
    reportError,
    copyErrorInfo,

    // 离线相关方法
    syncOfflineErrors,
    getOfflineErrorStats,
    clearOfflineErrors,

    // 上报相关方法
    batchReportErrors,
    getReportQueueStatus,
    clearReportQueue,

    // 分析方法
    getErrorTrends,

    // 工具函数
    getErrorIcon,
    getSeverityColor,
    getErrorTypeLabel
  }
}

/**
 * 全局错误处理器
 * 用于捕获未处理的Promise rejection和全局错误
 *
 * @param {Object} options - 配置选项
 * @returns {Function} 清理函数
 *
 * @example
 * ```javascript
 * // 在main.js中调用
 * const cleanup = setupGlobalErrorHandler({
 *   onUnhandledError: (error) => console.error('全局错误:', error)
 * })
 *
 * // 应用卸载时清理
 * cleanup()
 * ```
 */
export function setupGlobalErrorHandler(options = {}) {
  const { onUnhandledError, onUnhandledRejection } = options

  /**
   * 处理未捕获的错误
   */
  function handleGlobalError(event) {
    event.preventDefault()
    const error = event.error || new Error(event.message)
    onUnhandledError?.(error)
  }

  /**
   * 处理未处理的Promise rejection
   */
  function handleUnhandledRejection(event) {
    event.preventDefault()
    const error = event.reason instanceof Error
      ? event.reason
      : new Error(String(event.reason))
    onUnhandledRejection?.(error)
  }

  // 注册全局事件监听
  window.addEventListener('error', handleGlobalError)
  window.addEventListener('unhandledrejection', handleUnhandledRejection)

  // 返回清理函数
  return () => {
    window.removeEventListener('error', handleGlobalError)
    window.removeEventListener('unhandledrejection', handleUnhandledRejection)
  }
}

/**
 * 导出工具函数和常量
 */
export {
  ERROR_TYPES,
  ERROR_SEVERITY,
  ERROR_SEVERITY_WEIGHT,
  getErrorIcon,
  getSeverityColor,
  getErrorTypeLabel,
  inferErrorType,
  inferErrorSeverity
}
