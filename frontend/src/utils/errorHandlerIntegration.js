/**
 * @file errorHandlerIntegration.js
 * @path src/utils/
 * @description 错误处理系统集成指南，提供全局错误处理器设置和最佳实践
 *              支持离线错误缓存、自动同步和智能错误上报
 * @author Agent
 * @date 2024-03-07
 */

import { useErrorHandler, setupGlobalErrorHandler } from '../composables/useErrorHandler'
import { initOfflineStorage } from './offlineStorage'
import { useOnlineStatus } from '../composables/useOnlineStatus'

/**
 * 全局错误处理器实例
 */
let globalErrorHandler = null

/**
 * 在线状态监听器
 */
let onlineStatusWatcher = null

/**
 * 错误上报队列（用于批量上报）
 */
const reportQueue = []

/**
 * 批量上报定时器
 */
let batchReportTimer = null

/**
 * 批量上报间隔（毫秒）
 */
const BATCH_REPORT_INTERVAL = 5000

/**
 * 初始化全局错误处理器
 *
 * @param {Object} options - 配置选项
 * @param {boolean} [options.enableHistory=true] - 是否启用错误历史
 * @param {boolean} [options.enableAutoReport=false] - 是否自动上报
 * @param {boolean} [options.enableOfflineCache=true] - 是否启用离线缓存
 * @param {boolean} [options.enableBatchReport=false] - 是否启用批量上报
 * @param {number} [options.batchInterval=5000] - 批量上报间隔（毫秒）
 * @param {Function} [options.onReport] - 错误上报回调
 * @param {Function} [options.onError] - 错误处理回调
 * @param {Function} [options.onOfflineSync] - 离线同步回调
 * @returns {Object} 错误处理器实例
 *
 * @example
 * ```javascript
 * // 在 main.js 中调用
 * import { initializeErrorHandler } from './utils/errorHandlerIntegration'
 *
 * const errorHandler = initializeErrorHandler({
 *   enableAutoReport: true,
 *   enableOfflineCache: true,
 *   enableBatchReport: true,
 *   onReport: async (report) => {
 *     // 发送错误报告到服务器
 *     await fetch('/api/errors/report', {
 *       method: 'POST',
 *       body: JSON.stringify(report)
 *     })
 *   },
 *   onError: (errorInfo) => {
 *     // 自定义错误处理逻辑
 *     console.error('全局错误:', errorInfo)
 *   },
 *   onOfflineSync: (result) => {
 *     console.log('离线错误同步完成:', result)
 *   }
 * })
 * ```
 */
export function initializeErrorHandler(options = {}) {
  const {
    enableBatchReport = false,
    batchInterval = BATCH_REPORT_INTERVAL,
    onOfflineSync
  } = options

  // 创建全局错误处理器实例
  globalErrorHandler = useErrorHandler({
    enableHistory: options.enableHistory !== false,
    enableAutoReport: options.enableAutoReport || false,
    enableOfflineCache: options.enableOfflineCache !== false,
    enableErrorLog: options.enableErrorLog !== false,
    onReport: enableBatchReport
      ? (report) => addToReportQueue(report, options.onReport)
      : options.onReport
  })

  // 设置全局错误监听
  const cleanup = setupGlobalErrorHandler({
    onUnhandledError: (error) => {
      console.error('[全局错误]', error)
      globalErrorHandler.handleError(error, {
        component: 'Global',
        action: 'Unhandled Error',
        userMessage: '应用程序发生错误'
      })
      options.onError?.(globalErrorHandler.currentError.value)
    },
    onUnhandledRejection: (error) => {
      console.error('[未处理的Promise Rejection]', error)
      globalErrorHandler.handleError(error, {
        component: 'Global',
        action: 'Unhandled Promise Rejection',
        userMessage: '异步操作发生错误'
      })
      options.onError?.(globalErrorHandler.currentError.value)
    }
  })

  // 将清理函数附加到实例
  globalErrorHandler.cleanup = cleanup

  // 初始化在线状态监听
  initOnlineStatusListener(onOfflineSync)

  // 启动批量上报定时器
  if (enableBatchReport && options.onReport) {
    startBatchReportTimer(options.onReport, batchInterval)
  }

  return globalErrorHandler
}

/**
 * 初始化在线状态监听器
 *
 * @param {Function} onOfflineSync - 离线同步回调
 * @internal 内部方法，不对外暴露
 */
function initOnlineStatusListener(onOfflineSync) {
  if (onlineStatusWatcher) {
    onlineStatusWatcher()
  }

  const onlineStatus = useOnlineStatus({
    onOnline: async (info) => {
      console.log('[ErrorHandler] 网络已恢复，开始同步离线错误...', info)

      // 自动同步离线错误
      if (globalErrorHandler && globalErrorHandler.syncOfflineErrors) {
        try {
          const result = await globalErrorHandler.syncOfflineErrors()
          console.log('[ErrorHandler] 离线错误同步结果:', result)
          onOfflineSync?.(result)
        } catch (error) {
          console.error('[ErrorHandler] 离线错误同步失败:', error)
        }
      }
    },
    onOffline: (info) => {
      console.log('[ErrorHandler] 网络已断开，错误将被缓存', info)
    }
  })

  onlineStatusWatcher = onlineStatus
}

/**
 * 添加错误报告到队列
 *
 * @param {Object} report - 错误报告
 * @param {Function} onReport - 上报回调
 * @internal 内部方法，不对外暴露
 */
function addToReportQueue(report, onReport) {
  reportQueue.push({
    report,
    timestamp: Date.now()
  })

  // 如果队列超过10个，立即上报
  if (reportQueue.length >= 10) {
    flushReportQueue(onReport)
  }
}

/**
 * 启动批量上报定时器
 *
 * @param {Function} onReport - 上报回调
 * @param {number} interval - 间隔时间
 * @internal 内部方法，不对外暴露
 */
function startBatchReportTimer(onReport, interval) {
  stopBatchReportTimer()

  batchReportTimer = setInterval(() => {
    if (reportQueue.length > 0) {
      flushReportQueue(onReport)
    }
  }, interval)
}

/**
 * 停止批量上报定时器
 *
 * @internal 内部方法，不对外暴露
 */
function stopBatchReportTimer() {
  if (batchReportTimer) {
    clearInterval(batchReportTimer)
    batchReportTimer = null
  }
}

/**
 * 刷新报告队列
 *
 * @param {Function} onReport - 上报回调
 * @returns {Promise<void>}
 * @internal 内部方法，不对外暴露
 */
async function flushReportQueue(onReport) {
  if (reportQueue.length === 0 || !onReport) {
    return
  }

  const reports = [...reportQueue]
  reportQueue.length = 0

  try {
    // 批量上报
    await onReport({
      type: 'batch',
      count: reports.length,
      reports: reports.map(r => r.report),
      timestamp: new Date().toISOString()
    })

    console.log(`[ErrorHandler] 批量上报成功: ${reports.length} 个错误`)
  } catch (error) {
    console.error('[ErrorHandler] 批量上报失败:', error)

    // 上报失败，将报告放回队列
    reportQueue.unshift(...reports)
  }
}

/**
 * 获取全局错误处理器实例
 *
 * @returns {Object|null} 错误处理器实例
 */
export function getGlobalErrorHandler() {
  return globalErrorHandler
}

/**
 * Vue应用错误处理器
 * 用于Vue应用配置中的errorHandler
 *
 * @param {Error} error - 错误对象
 * @param {Object} instance - Vue组件实例
 * @param {string} info - 错误信息
 *
 * @example
 * ```javascript
 * // 在 main.js 中
 * import { vueErrorHandler } from './utils/errorHandlerIntegration'
 *
 * app.config.errorHandler = vueErrorHandler
 * ```
 */
export function vueErrorHandler(error, instance, info) {
  console.error('[Vue错误]', error, info)

  if (globalErrorHandler) {
    globalErrorHandler.handleError(error, {
      component: instance?.$options?.name || instance?.$?.type?.name || 'Unknown',
      action: info || 'Vue Error',
      userMessage: '组件发生错误'
    })
  }
}

/**
 * API请求错误处理器
 * 用于统一处理API请求错误
 *
 * @param {Error} error - 错误对象
 * @param {Object} config - 请求配置
 * @returns {Object} 错误信息对象
 *
 * @example
 * ```javascript
 * // 在 apiRequest.js 中使用
 * import { handleApiError } from './errorHandlerIntegration'
 *
 * try {
 *   const response = await fetch(url, options)
 *   return await response.json()
 * } catch (error) {
 *   return handleApiError(error, { url, method })
 * }
 * ```
 */
export function handleApiError(error, config = {}) {
  if (globalErrorHandler) {
    return globalErrorHandler.handleError(error, {
      component: 'API',
      action: `${config.method || 'GET'} ${config.url || 'unknown'}`,
      userMessage: getApiErrorMessage(error),
      data: config
    })
  }

  // 如果全局处理器未初始化，返回基本错误信息
  return {
    message: error.message,
    type: 'network',
    severity: 'high'
  }
}

/**
 * 获取API错误消息
 *
 * @param {Error} error - 错误对象
 * @returns {string} 用户友好的错误消息
 * @internal 内部方法，不对外暴露
 */
function getApiErrorMessage(error) {
  // 根据HTTP状态码返回友好消息
  if (error.response) {
    const status = error.response.status
    const messages = {
      400: '请求参数错误',
      401: '未授权，请重新登录',
      403: '权限不足',
      404: '请求的资源不存在',
      500: '服务器内部错误',
      502: '网关错误',
      503: '服务不可用',
      504: '网关超时'
    }
    return messages[status] || `请求失败 (${status})`
  }

  // 网络错误
  if (error.message.includes('Network Error') || error.message.includes('Failed to fetch')) {
    return '网络连接失败，请检查网络'
  }

  // 超时错误
  if (error.message.includes('timeout')) {
    return '请求超时，请稍后重试'
  }

  // 默认消息
  return '请求失败，请稍后重试'
}

/**
 * WebSocket错误处理器
 * 用于统一处理WebSocket错误
 *
 * @param {Error} error - 错误对象
 * @param {Object} context - 错误上下文
 * @returns {Object} 错误信息对象
 *
 * @example
 * ```javascript
 * // 在 useWebSocket.js 中使用
 * import { handleWebSocketError } from './errorHandlerIntegration'
 *
 * ws.onerror = (error) => {
 *   handleWebSocketError(error, { url: wsUrl })
 * }
 * ```
 */
export function handleWebSocketError(error, context = {}) {
  if (globalErrorHandler) {
    return globalErrorHandler.handleError(error, {
      component: 'WebSocket',
      action: context.action || 'WebSocket Connection',
      userMessage: '实时数据连接失败',
      data: context
    })
  }

  return {
    message: error.message,
    type: 'websocket',
    severity: 'high'
  }
}

/**
 * 设备错误处理器
 * 用于统一处理设备连接和通信错误
 *
 * @param {Error} error - 错误对象
 * @param {Object} device - 设备信息
 * @returns {Object} 错误信息对象
 *
 * @example
 * ```javascript
 * // 在设备store中使用
 * import { handleDeviceError } from '../utils/errorHandlerIntegration'
 *
 * try {
 *   await device.connect()
 * } catch (error) {
 *   handleDeviceError(error, { name: 'Motor', port: 'COM3' })
 *   throw error
 * }
 * ```
 */
export function handleDeviceError(error, device = {}) {
  if (globalErrorHandler) {
    return globalErrorHandler.handleError(error, {
      component: device.name || 'Device',
      action: device.action || 'Device Operation',
      userMessage: getDeviceErrorMessage(error, device),
      data: device
    })
  }

  return {
    message: error.message,
    type: 'device',
    severity: 'high'
  }
}

/**
 * 获取设备错误消息
 *
 * @param {Error} error - 错误对象
 * @param {Object} device - 设备信息
 * @returns {string} 用户友好的错误消息
 * @internal 内部方法，不对外暴露
 */
function getDeviceErrorMessage(error, device) {
  const message = error.message.toLowerCase()

  if (message.includes('not found') || message.includes('not connected')) {
    return `${device.name || '设备'}未连接`
  }

  if (message.includes('busy') || message.includes('in use')) {
    return `${device.name || '设备'}端口被占用`
  }

  if (message.includes('permission') || message.includes('access denied')) {
    return `${device.name || '设备'}访问权限不足`
  }

  if (message.includes('timeout')) {
    return `${device.name || '设备'}通信超时`
  }

  return `${device.name || '设备'}操作失败`
}

/**
 * 表单验证错误处理器
 * 用于统一处理表单验证错误
 *
 * @param {Error|Object} error - 错误对象或验证结果
 * @param {Object} form - 表单信息
 * @returns {Object} 错误信息对象
 *
 * @example
 * ```javascript
 * // 在表单提交中使用
 * import { handleValidationError } from '../utils/errorHandlerIntegration'
 *
 * const validateForm = () => {
 *   const errors = validate(formData)
 *   if (errors.length > 0) {
 *     handleValidationError(errors, { formName: 'userForm' })
 *     return false
 *   }
 *   return true
 * }
 * ```
 */
export function handleValidationError(error, form = {}) {
  const errorMessage = Array.isArray(error)
    ? error.map(e => e.message).join('; ')
    : error.message || '验证失败'

  if (globalErrorHandler) {
    return globalErrorHandler.handleError(new Error(errorMessage), {
      component: form.formName || 'Form',
      action: 'Form Validation',
      userMessage: '表单验证失败，请检查输入',
      data: { errors: error, form }
    })
  }

  return {
    message: errorMessage,
    type: 'validation',
    severity: 'medium'
  }
}

/**
 * 获取错误统计信息
 *
 * @returns {Object} 错误统计信息
 */
export function getErrorStatistics() {
  if (!globalErrorHandler) {
    return {
      total: 0,
      byType: {},
      bySeverity: {},
      offlineQueue: 0
    }
  }

  const stats = globalErrorHandler.errorStats.value
  const offlineStats = globalErrorHandler.getOfflineErrorStats()

  return {
    ...stats,
    offlineQueue: offlineStats.queueLength,
    isSyncing: offlineStats.isSyncing
  }
}

/**
 * 手动同步离线错误
 *
 * @returns {Promise<Object>} 同步结果
 */
export async function syncOfflineErrorsNow() {
  if (!globalErrorHandler || !globalErrorHandler.syncOfflineErrors) {
    return { success: false, message: '错误处理器未初始化' }
  }

  return globalErrorHandler.syncOfflineErrors()
}

/**
 * 清理所有错误数据
 *
 * @returns {Promise<void>}
 */
export async function clearAllErrors() {
  if (!globalErrorHandler) {
    return
  }

  // 清除内存中的错误历史
  globalErrorHandler.clearHistory()

  // 清除离线错误缓存
  if (globalErrorHandler.clearOfflineErrors) {
    await globalErrorHandler.clearOfflineErrors()
  }

  // 清除本地存储的错误日志
  try {
    localStorage.removeItem('error_logs')
  } catch (err) {
    console.warn('[ErrorHandler] 清除本地错误日志失败:', err)
  }

  console.log('[ErrorHandler] 所有错误数据已清理')
}

/**
 * 导出错误报告（用于用户下载）
 *
 * @param {Object} errorInfo - 错误信息对象
 * @returns {string} JSON格式的错误报告
 */
export function exportErrorReport(errorInfo) {
  if (!errorInfo) {
    return ''
  }

  const report = {
    exportTime: new Date().toISOString(),
    application: 'CAUC-SEP',
    version: import.meta.env?.VITE_APP_VERSION || '1.0.0',
    error: {
      id: errorInfo.id,
      timestamp: errorInfo.timestamp,
      type: errorInfo.type,
      severity: errorInfo.severity,
      message: errorInfo.message,
      context: errorInfo.context,
      system: errorInfo.system,
      solution: errorInfo.solution ? {
        title: errorInfo.solution.title,
        description: errorInfo.solution.description,
        solutions: errorInfo.solution.solutions
      } : null
    }
  }

  return JSON.stringify(report, null, 2)
}

/**
 * 下载错误报告文件
 *
 * @param {Object} errorInfo - 错误信息对象
 * @param {string} [filename] - 文件名
 */
export function downloadErrorReport(errorInfo, filename) {
  const report = exportErrorReport(errorInfo)
  if (!report) {
    return
  }

  const blob = new Blob([report], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename || `error_report_${Date.now()}.json`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * 销毁错误处理器
 */
export function destroyErrorHandler() {
  // 停止批量上报定时器
  stopBatchReportTimer()

  // 清理全局错误监听
  if (globalErrorHandler && globalErrorHandler.cleanup) {
    globalErrorHandler.cleanup()
  }

  // 清理在线状态监听
  if (onlineStatusWatcher && typeof onlineStatusWatcher === 'function') {
    onlineStatusWatcher()
  }

  // 刷新剩余的报告队列
  if (reportQueue.length > 0) {
    console.warn(`[ErrorHandler] 还有 ${reportQueue.length} 个错误报告未上报`)
  }

  // 清空队列
  reportQueue.length = 0

  // 重置实例
  globalErrorHandler = null
  onlineStatusWatcher = null

  console.log('[ErrorHandler] 错误处理器已销毁')
}

/**
 * 导出所有错误处理函数
 */
export default {
  initializeErrorHandler,
  getGlobalErrorHandler,
  vueErrorHandler,
  handleApiError,
  handleWebSocketError,
  handleDeviceError,
  handleValidationError,
  getErrorStatistics,
  syncOfflineErrorsNow,
  clearAllErrors,
  exportErrorReport,
  downloadErrorReport,
  destroyErrorHandler
}
