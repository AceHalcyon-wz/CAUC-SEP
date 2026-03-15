/**
 * @file useOperationFeedback.js
 * @path src/composables/
 * @description 操作反馈组合式函数，封装操作进度、成功/失败提示、撤销等常用操作
 * @author Agent
 * @date 2024-03-07
 * @dependencies vue, stores/operation
 */

import { ref, computed, onUnmounted } from 'vue'
import { useOperationStore, OPERATION_STATUS, OPERATION_TYPE, ERROR_TYPE } from '../stores/operation'

/**
 * 操作反馈组合式函数
 *
 * @param {Object} options - 配置选项
 * @param {string} [options.defaultType] - 默认操作类型
 * @param {number} [options.defaultUndoWindow] - 默认撤销时间窗口（毫秒）
 * @param {boolean} [options.autoNotify] - 是否自动发送通知
 * @returns {Object} 操作反馈方法与状态
 *
 * @example
 * ```javascript
 * const { execute, createProgressUpdater, showSuccess, showError } = useOperationFeedback()
 *
 * // 执行带进度的操作
 * await execute({
 *   type: 'device_connect',
 *   title: '连接设备',
 *   steps: ['初始化', '建立连接', '验证身份'],
 *   action: async (updateProgress) => {
 *     updateProgress(0, 0, '正在初始化...')
 *     await delay(500)
 *     updateProgress(33, 1, '正在建立连接...')
 *     await delay(500)
 *     updateProgress(66, 2, '正在验证身份...')
 *     await delay(500)
 *     updateProgress(100, 2, '连接成功')
 *     return { deviceId: 'motor' }
 *   },
 *   undo: async (metadata) => {
 *     // 撤销逻辑
 *   }
 * })
 * ```
 */
export function useOperationFeedback(options = {}) {
  const {
    defaultType = OPERATION_TYPE.CUSTOM,
    defaultUndoWindow = 10000
  } = options

  // 获取操作Store
  const operationStore = useOperationStore()

  // 当前操作的引用
  const currentOperationId = ref(null)

  /**
   * 当前操作状态
   */
  const currentOperation = computed(() => {
    if (!currentOperationId.value) return null
    return operationStore.activeOperations.find(op => op.id === currentOperationId.value) ||
           operationStore.operationHistory.find(op => op.id === currentOperationId.value)
  })

  /**
   * 是否正在执行操作
   */
  const isOperating = computed(() => {
    return currentOperation.value?.status === OPERATION_STATUS.RUNNING
  })

  /**
   * 操作进度百分比
   */
  const progress = computed(() => {
    return currentOperation.value?.progress || 0
  })

  /**
   * 创建进度更新函数
   *
   * @param {string} operationId - 操作ID
   * @returns {Function} 进度更新函数
   */
  function createProgressUpdater(operationId) {
    return (percentage, step, message) => {
      operationStore.updateOperationProgress(operationId, percentage, step, message)
    }
  }

  /**
   * 执行操作
   *
   * @param {Object} config - 操作配置
   * @param {string} [config.type] - 操作类型
   * @param {string} config.title - 操作标题
   * @param {string} [config.description] - 操作描述
   * @param {Array} [config.steps] - 操作步骤列表
   * @param {Function} config.action - 执行函数
   * @param {Function} [config.undo] - 撤销函数
   * @param {number} [config.undoWindow] - 撤销时间窗口
   * @param {boolean} [config.cancellable] - 是否可取消
   * @param {Object} [config.metadata] - 额外元数据
   * @returns {Promise<Object>} 执行结果
   */
  async function execute(config) {
    const {
      type = defaultType,
      title,
      description = '',
      steps = [],
      action,
      undo,
      undoWindow = defaultUndoWindow,
      cancellable = true,
      metadata = {}
    } = config

    // 创建操作对象
    const operation = operationStore.createOperation({
      type,
      title,
      description,
      steps: steps.map(name => ({ name })),
      onExecute: action,
      onUndo: undo,
      undoWindow,
      cancellable,
      metadata
    })

    currentOperationId.value = operation.id

    // 执行操作
    const result = await operationStore.startOperation(operation.id)

    return result
  }

  /**
   * 取消当前操作
   *
   * @returns {boolean} 是否成功取消
   */
  function cancel() {
    if (currentOperationId.value) {
      return operationStore.cancelOperation(currentOperationId.value)
    }
    return false
  }

  /**
   * 重试操作
   *
   * @param {string} [operationId] - 操作ID，不传则重试当前操作
   * @returns {Promise<Object>} 执行结果
   */
  async function retry(operationId) {
    const id = operationId || currentOperationId.value
    if (id) {
      const result = await operationStore.retryOperation(id)
      if (result.success) {
        currentOperationId.value = result.operationId
      }
      return result
    }
    return { success: false, error: '无操作可重试' }
  }

  /**
   * 撤销操作
   *
   * @param {string} undoId - 撤销项ID
   * @returns {Promise<Object>} 撤销结果
   */
  async function undo(undoId) {
    return await operationStore.executeUndo(undoId)
  }

  /**
   * 显示成功提示
   *
   * @param {Object} options - 提示配置
   * @param {string} options.title - 标题
   * @param {string} [options.message] - 消息
   * @param {number} [options.duration] - 显示时长（毫秒）
   * @param {Object} [options.result] - 操作结果
   */
  function showSuccess(options) {
    operationStore.addSuccessNotification({
      type: OPERATION_TYPE.CUSTOM,
      ...options
    })
  }

  /**
   * 显示错误提示
   *
   * @param {Object} options - 提示配置
   * @param {string} options.title - 标题
   * @param {Error|string} options.error - 错误对象或消息
   * @param {boolean} [options.retryable] - 是否可重试
   */
  function showError(options) {
    const { title, error, retryable = false } = options

    const errorObj = error instanceof Error
      ? {
          type: operationStore.classifyError(error),
          message: error.message,
          details: error.details || null
        }
      : {
          type: ERROR_TYPE.UNKNOWN,
          message: String(error),
          details: null
        }

    operationStore.addErrorNotification({
      type: OPERATION_TYPE.CUSTOM,
      title,
      error: errorObj,
      retryable
    })
  }

  /**
   * 显示警告提示
   *
   * @param {Object} options - 提示配置
   * @param {string} options.title - 标题
   * @param {string} options.message - 消息
   */
  function showWarning(options) {
    operationStore.addErrorNotification({
      type: OPERATION_TYPE.CUSTOM,
      title: options.title,
      error: {
        type: ERROR_TYPE.UNKNOWN,
        message: options.message,
        details: null
      },
      retryable: false
    })
  }

  /**
   * 批量操作包装器
   *
   * @param {Object} config - 批量操作配置
   * @param {string} config.title - 操作标题
   * @param {Array} config.items - 操作项列表
   * @param {Function} config.processItem - 处理单个项的函数
   * @param {Function} [config.onProgress] - 进度回调
   * @param {Function} [config.onItemComplete] - 单项完成回调
   * @param {Function} [config.onItemError] - 单项错误回调
   * @param {boolean} [config.continueOnError] - 出错时是否继续
   * @returns {Promise<Object>} 批量操作结果
   */
  async function executeBatch(config) {
    const {
      title,
      items,
      processItem,
      onProgress,
      onItemComplete,
      onItemError,
      continueOnError = true
    } = config

    const total = items.length
    let completed = 0
    let succeeded = 0
    let failed = 0
    const errors = []
    const results = []

    const operation = operationStore.createOperation({
      type: OPERATION_TYPE.BATCH_OPERATION,
      title,
      steps: [{ name: '批量处理' }],
      cancellable: true,
      metadata: { total }
    })

    currentOperationId.value = operation.id

    for (let i = 0; i < items.length; i++) {
      // 检查是否已取消
      const currentOp = operationStore.activeOperations.find(op => op.id === operation.id)
      if (currentOp?.status === OPERATION_STATUS.CANCELLED) {
        break
      }

      const item = items[i]
      const progress = Math.round(((i + 1) / total) * 100)

      try {
        operationStore.updateOperationProgress(
          operation.id,
          progress,
          0,
          `正在处理 ${i + 1}/${total}`
        )

        const result = await processItem(item, i)
        results.push({ item, result, success: true })
        succeeded++
        onItemComplete?.(item, result, i)
      } catch (error) {
        failed++
        const errorInfo = {
          item,
          index: i,
          error: {
            type: operationStore.classifyError(error),
            message: error.message
          }
        }
        errors.push(errorInfo)
        results.push({ item, error: errorInfo, success: false })
        onItemError?.(item, error, i)

        if (!continueOnError) {
          break
        }
      }

      completed++
      onProgress?.(completed, total, progress)
    }

    // 完成操作
    const finalStatus = failed === 0 ? OPERATION_STATUS.SUCCESS : 
                       succeeded === 0 ? OPERATION_STATUS.FAILED : 
                       OPERATION_STATUS.SUCCESS

    operation.status = finalStatus
    operation.progress = 100
    operation.endTime = Date.now()
    operation.result = {
      total,
      completed,
      succeeded,
      failed,
      errors,
      results
    }

    // 移动到历史
    operationStore.moveToHistory(operation.id)

    // 添加通知
    if (finalStatus === OPERATION_STATUS.SUCCESS) {
      operationStore.addSuccessNotification({
        operationId: operation.id,
        type: OPERATION_TYPE.BATCH_OPERATION,
        title,
        message: `成功处理 ${succeeded}/${total} 项`,
        result: operation.result
      })
    } else {
      operationStore.addErrorNotification({
        operationId: operation.id,
        type: OPERATION_TYPE.BATCH_OPERATION,
        title,
        error: {
          type: ERROR_TYPE.UNKNOWN,
          message: `处理完成，成功 ${succeeded} 项，失败 ${failed} 项`,
          details: errors
        },
        retryable: true
      })
    }

    return {
      success: failed === 0,
      total,
      completed,
      succeeded,
      failed,
      errors,
      results
    }
  }

  /**
   * 创建带确认的操作
   *
   * @param {Object} config - 操作配置
   * @param {string} config.title - 操作标题
   * @param {string} config.confirmMessage - 确认消息
   * @param {Function} config.action - 执行函数
   * @returns {Promise<Object>} 执行结果
   */
  async function executeWithConfirm(config) {
    const { title, action } = config

    // 这里应该调用确认对话框组件
    // 简化实现，直接执行
    return await execute({
      type: OPERATION_TYPE.CUSTOM,
      title,
      action
    })
  }

  /**
   * 创建可撤销的操作
   *
   * @param {Object} config - 操作配置
   * @param {string} config.title - 操作标题
   * @param {Function} config.action - 执行函数
   * @param {Function} config.undo - 撤销函数
   * @param {number} [config.undoWindow] - 撤销时间窗口
   * @returns {Promise<Object>} 执行结果
   */
  async function executeWithUndo(config) {
    const { title, action, undo, undoWindow = defaultUndoWindow } = config

    return await execute({
      type: OPERATION_TYPE.CUSTOM,
      title,
      action,
      undo,
      undoWindow
    })
  }

  /**
   * 包装异步操作，自动处理错误和通知
   *
   * @param {Function} fn - 异步函数
   * @param {Object} options - 配置选项
   * @returns {Function} 包装后的函数
   */
  function wrapAsync(fn, options = {}) {
    const { title = '操作', showErrorNotification = true } = options

    return async (...args) => {
      try {
        const result = await fn(...args)
        return { success: true, result }
      } catch (error) {
        if (showErrorNotification) {
          showError({
            title: `${title}失败`,
            error
          })
        }
        return { success: false, error }
      }
    }
  }

  /**
   * 获取错误帮助链接
   *
   * @param {string} errorType - 错误类型
   * @returns {Object} 帮助链接信息
   */
  function getHelpLink(errorType) {
    return operationStore.getErrorHelpLink(errorType)
  }

  // 组件卸载时清理
  onUnmounted(() => {
    currentOperationId.value = null
  })

  return {
    // 状态
    currentOperation,
    currentOperationId,
    isOperating,
    progress,

    // 核心方法
    execute,
    cancel,
    retry,
    undo,
    createProgressUpdater,

    // 通知方法
    showSuccess,
    showError,
    showWarning,

    // 高级方法
    executeBatch,
    executeWithConfirm,
    executeWithUndo,
    wrapAsync,

    // 辅助方法
    getHelpLink,

    // Store引用
    operationStore
  }
}

/**
 * 创建简单的进度更新器
 *
 * @param {number} total - 总步骤数
 * @param {Function} updateProgress - 进度更新函数
 * @returns {Function} 步骤完成函数
 */
export function createStepProgress(total, updateProgress) {
  let currentStep = 0

  return (message) => {
    currentStep++
    const percentage = Math.round((currentStep / total) * 100)
    updateProgress(percentage, currentStep - 1, message)
  }
}

/**
 * 创建延迟函数
 *
 * @param {number} ms - 延迟毫秒数
 * @returns {Promise<void>}
 */
export function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}
