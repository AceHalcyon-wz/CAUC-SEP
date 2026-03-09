/**
 * @file operation.js
 * @path src/stores/
 * @description 操作反馈系统状态管理Store，管理操作进度、成功/失败提示、撤销队列等状态
 * @author Agent
 * @date 2024-03-07
 * @dependencies pinia, vue
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/**
 * 操作状态枚举
 * @constant {Object}
 */
export const OPERATION_STATUS = {
  PENDING: 'pending',
  RUNNING: 'running',
  SUCCESS: 'success',
  FAILED: 'failed',
  CANCELLED: 'cancelled',
  UNDONE: 'undone'
}

/**
 * 操作类型枚举
 * @constant {Object}
 */
export const OPERATION_TYPE = {
  DEVICE_CONNECT: 'device_connect',
  DEVICE_DISCONNECT: 'device_disconnect',
  DEVICE_COMMAND: 'device_command',
  DATA_EXPORT: 'data_export',
  DATA_IMPORT: 'data_import',
  CONFIG_SAVE: 'config_save',
  EXPERIMENT_START: 'experiment_start',
  EXPERIMENT_STOP: 'experiment_stop',
  BATCH_OPERATION: 'batch_operation',
  CUSTOM: 'custom'
}

/**
 * 错误类型枚举
 * @constant {Object}
 */
export const ERROR_TYPE = {
  NETWORK: 'network',
  TIMEOUT: 'timeout',
  VALIDATION: 'validation',
  PERMISSION: 'permission',
  DEVICE: 'device',
  SYSTEM: 'system',
  UNKNOWN: 'unknown'
}

/**
 * 错误类型中文映射
 * @constant {Object}
 */
export const ERROR_TYPE_TEXT = {
  [ERROR_TYPE.NETWORK]: '网络错误',
  [ERROR_TYPE.TIMEOUT]: '操作超时',
  [ERROR_TYPE.VALIDATION]: '参数校验失败',
  [ERROR_TYPE.PERMISSION]: '权限不足',
  [ERROR_TYPE.DEVICE]: '设备错误',
  [ERROR_TYPE.SYSTEM]: '系统错误',
  [ERROR_TYPE.UNKNOWN]: '未知错误'
}

/**
 * 操作类型中文映射
 * @constant {Object}
 */
export const OPERATION_TYPE_TEXT = {
  [OPERATION_TYPE.DEVICE_CONNECT]: '连接设备',
  [OPERATION_TYPE.DEVICE_DISCONNECT]: '断开设备',
  [OPERATION_TYPE.DEVICE_COMMAND]: '设备指令',
  [OPERATION_TYPE.DATA_EXPORT]: '数据导出',
  [OPERATION_TYPE.DATA_IMPORT]: '数据导入',
  [OPERATION_TYPE.CONFIG_SAVE]: '保存配置',
  [OPERATION_TYPE.EXPERIMENT_START]: '开始实验',
  [OPERATION_TYPE.EXPERIMENT_STOP]: '停止实验',
  [OPERATION_TYPE.BATCH_OPERATION]: '批量操作',
  [OPERATION_TYPE.CUSTOM]: '自定义操作'
}

/**
 * 默认撤销时间窗口（毫秒）
 * @constant {number}
 */
const DEFAULT_UNDO_WINDOW = 10000

/**
 * 最大撤销队列长度
 * @constant {number}
 */
const MAX_UNDO_QUEUE_SIZE = 20

/**
 * 操作反馈管理 Store
 *
 * 提供操作进度跟踪、成功/失败提示、撤销功能等
 */
export const useOperationStore = defineStore('operation', () => {
  // ==================== 响应式状态 ====================

  /**
   * 当前活跃的操作列表
   * @type {import('vue').Ref<Array>}
   */
  const activeOperations = ref([])

  /**
   * 操作历史记录
   * @type {import('vue').Ref<Array>}
   */
  const operationHistory = ref([])

  /**
   * 撤销队列
   * @type {import('vue').Ref<Array>}
   */
  const undoQueue = ref([])

  /**
   * 成功提示队列
   * @type {import('vue').Ref<Array>}
   */
  const successNotifications = ref([])

  /**
   * 错误提示队列
   * @type {import('vue').Ref<Array>}
   */
  const errorNotifications = ref([])

  /**
   * 全局进度条状态
   * @type {import('vue').Ref<Object>}
   */
  const globalProgress = ref({
    visible: false,
    percentage: 0,
    status: '',
    message: '',
    cancellable: false
  })

  /**
   * 操作ID计数器
   * @type {number}
   */
  let operationIdCounter = 0

  // ==================== 计算属性 ====================

  /**
   * 是否有正在进行的操作
   * @type {import('vue').ComputedRef<boolean>}
   */
  const hasActiveOperations = computed(() => {
    return activeOperations.value.some(op => 
      op.status === OPERATION_STATUS.RUNNING || op.status === OPERATION_STATUS.PENDING
    )
  })

  /**
   * 正在运行的操作数量
   * @type {import('vue').ComputedRef<number>}
   */
  const runningOperationsCount = computed(() => {
    return activeOperations.value.filter(op => op.status === OPERATION_STATUS.RUNNING).length
  })

  /**
   * 可撤销的操作数量
   * @type {import('vue').ComputedRef<number>}
   */
  const undoableCount = computed(() => {
    return undoQueue.value.filter(item => item.canUndo && !item.undone).length
  })

  /**
   * 未读成功提示数量
   * @type {import('vue').ComputedRef<number>}
   */
  const unreadSuccessCount = computed(() => {
    return successNotifications.value.filter(n => !n.read).length
  })

  /**
   * 未读错误提示数量
   * @type {import('vue').ComputedRef<number>}
   */
  const unreadErrorCount = computed(() => {
    return errorNotifications.value.filter(n => !n.read).length
  })

  // ==================== 操作管理方法 ====================

  /**
   * 生成唯一操作ID
   *
   * @returns {string} 操作ID
   */
  function generateOperationId() {
    return `op_${Date.now()}_${++operationIdCounter}`
  }

  /**
   * 创建新操作
   *
   * @param {Object} options - 操作配置
   * @param {string} options.type - 操作类型
   * @param {string} options.title - 操作标题
   * @param {string} [options.description] - 操作描述
   * @param {Array} [options.steps] - 操作步骤列表
   * @param {Function} [options.onExecute] - 执行函数
   * @param {Function} [options.onUndo] - 撤销函数
   * @param {number} [options.undoWindow] - 撤销时间窗口（毫秒）
   * @param {boolean} [options.cancellable] - 是否可取消
   * @param {Object} [options.metadata] - 额外元数据
   * @returns {Object} 操作对象
   */
  function createOperation(options) {
    const {
      type,
      title,
      description = '',
      steps = [],
      onExecute,
      onUndo,
      undoWindow = DEFAULT_UNDO_WINDOW,
      cancellable = true,
      metadata = {}
    } = options

    const operation = {
      id: generateOperationId(),
      type,
      title,
      description,
      status: OPERATION_STATUS.PENDING,
      progress: 0,
      currentStep: 0,
      steps: steps.map((step, index) => ({
        id: index,
        name: step.name || `步骤 ${index + 1}`,
        status: index === 0 ? OPERATION_STATUS.RUNNING : OPERATION_STATUS.PENDING,
        message: ''
      })),
      startTime: null,
      endTime: null,
      error: null,
      result: null,
      onExecute,
      onUndo,
      undoWindow,
      cancellable,
      canUndo: !!onUndo,
      undone: false,
      metadata,
      createdAt: Date.now()
    }

    activeOperations.value.push(operation)
    return operation
  }

  /**
   * 开始执行操作
   *
   * @param {string} operationId - 操作ID
   * @returns {Promise<Object>} 执行结果
   */
  async function startOperation(operationId) {
    const operation = activeOperations.value.find(op => op.id === operationId)
    if (!operation) {
      console.error(`[OperationStore] Operation not found: ${operationId}`)
      return { success: false, error: '操作不存在' }
    }

    operation.status = OPERATION_STATUS.RUNNING
    operation.startTime = Date.now()

    // 更新全局进度
    updateGlobalProgress(operation)

    try {
      if (operation.onExecute) {
        const result = await operation.onExecute((progress, step, message) => {
          updateOperationProgress(operationId, progress, step, message)
        })
        
        operation.result = result
        operation.status = OPERATION_STATUS.SUCCESS
        operation.endTime = Date.now()
        
        // 添加成功提示
        addSuccessNotification({
          operationId: operation.id,
          type: operation.type,
          title: operation.title,
          message: `${operation.title} 完成`,
          result: result,
          duration: 5000
        })

        // 如果可撤销，添加到撤销队列
        if (operation.canUndo && operation.onUndo) {
          addToUndoQueue(operation)
        }

        // 移动到历史记录
        moveToHistory(operationId)
        
        return { success: true, result }
      }
    } catch (error) {
      operation.status = OPERATION_STATUS.FAILED
      operation.endTime = Date.now()
      operation.error = {
        type: classifyError(error),
        message: error.message || '操作失败',
        details: error.details || null,
        stack: error.stack
      }

      // 添加错误提示
      addErrorNotification({
        operationId: operation.id,
        type: operation.type,
        title: operation.title,
        error: operation.error,
        retryable: true
      })

      // 移动到历史记录
      moveToHistory(operationId)
      
      return { success: false, error: operation.error }
    } finally {
      updateGlobalProgress(null)
    }
  }

  /**
   * 更新操作进度
   *
   * @param {string} operationId - 操作ID
   * @param {number} progress - 进度百分比（0-100）
   * @param {number} [step] - 当前步骤索引
   * @param {string} [message] - 进度消息
   */
  function updateOperationProgress(operationId, progress, step, message) {
    const operation = activeOperations.value.find(op => op.id === operationId)
    if (!operation) return

    operation.progress = Math.min(100, Math.max(0, progress))
    
    if (step !== undefined && operation.steps[step]) {
      // 更新步骤状态
      operation.steps.forEach((s, index) => {
        if (index < step) {
          s.status = OPERATION_STATUS.SUCCESS
        } else if (index === step) {
          s.status = OPERATION_STATUS.RUNNING
          s.message = message || ''
        } else {
          s.status = OPERATION_STATUS.PENDING
        }
      })
      operation.currentStep = step
    }

    // 更新全局进度
    updateGlobalProgress(operation)
  }

  /**
   * 取消操作
   *
   * @param {string} operationId - 操作ID
   * @returns {boolean} 是否成功取消
   */
  function cancelOperation(operationId) {
    const operation = activeOperations.value.find(op => op.id === operationId)
    if (!operation || !operation.cancellable) return false

    if (operation.status === OPERATION_STATUS.RUNNING) {
      operation.status = OPERATION_STATUS.CANCELLED
      operation.endTime = Date.now()
      
      // 移动到历史记录
      moveToHistory(operationId)
      
      updateGlobalProgress(null)
      return true
    }
    
    return false
  }

  /**
   * 重试操作
   *
   * @param {string} operationId - 操作ID（历史记录中的）
   * @returns {Promise<Object>} 执行结果
   */
  async function retryOperation(operationId) {
    const historyOp = operationHistory.value.find(op => op.id === operationId)
    if (!historyOp) {
      return { success: false, error: '操作不存在' }
    }

    // 创建新操作
    const newOperation = createOperation({
      type: historyOp.type,
      title: historyOp.title,
      description: historyOp.description,
      steps: historyOp.steps.map(s => ({ name: s.name })),
      onExecute: historyOp.onExecute,
      onUndo: historyOp.onUndo,
      undoWindow: historyOp.undoWindow,
      cancellable: historyOp.cancellable,
      metadata: historyOp.metadata
    })

    return await startOperation(newOperation.id)
  }

  /**
   * 移动操作到历史记录
   *
   * @param {string} operationId - 操作ID
   */
  function moveToHistory(operationId) {
    const index = activeOperations.value.findIndex(op => op.id === operationId)
    if (index >= 0) {
      const [operation] = activeOperations.value.splice(index, 1)
      // 不保存函数引用
      const historyRecord = {
        ...operation,
        onExecute: null,
        onUndo: null
      }
      operationHistory.value.unshift(historyRecord)
      
      // 保持历史记录不超过100条
      if (operationHistory.value.length > 100) {
        operationHistory.value = operationHistory.value.slice(0, 100)
      }
    }
  }

  // ==================== 全局进度条方法 ====================

  /**
   * 更新全局进度条状态
   *
   * @param {Object|null} operation - 当前操作对象，null表示隐藏
   */
  function updateGlobalProgress(operation) {
    if (!operation) {
      globalProgress.value = {
        visible: false,
        percentage: 0,
        status: '',
        message: '',
        cancellable: false
      }
      return
    }

    globalProgress.value = {
      visible: true,
      percentage: operation.progress,
      status: operation.status,
      message: operation.steps[operation.currentStep]?.message || operation.title,
      cancellable: operation.cancellable && operation.status === OPERATION_STATUS.RUNNING
    }
  }

  // ==================== 撤销功能方法 ====================

  /**
   * 添加操作到撤销队列
   *
   * @param {Object} operation - 操作对象
   */
  function addToUndoQueue(operation) {
    const undoItem = {
      id: `undo_${operation.id}`,
      operationId: operation.id,
      type: operation.type,
      title: operation.title,
      onUndo: operation.onUndo,
      addedAt: Date.now(),
      expiresAt: Date.now() + operation.undoWindow,
      canUndo: true,
      undone: false,
      metadata: operation.metadata
    }

    undoQueue.value.unshift(undoItem)

    // 保持队列不超过最大长度
    if (undoQueue.value.length > MAX_UNDO_QUEUE_SIZE) {
      undoQueue.value = undoQueue.value.slice(0, MAX_UNDO_QUEUE_SIZE)
    }

    // 设置过期定时器
    setTimeout(() => {
      expireUndoItem(undoItem.id)
    }, operation.undoWindow)
  }

  /**
   * 执行撤销
   *
   * @param {string} undoId - 撤销项ID
   * @returns {Promise<Object>} 撤销结果
   */
  async function executeUndo(undoId) {
    const undoItem = undoQueue.value.find(item => item.id === undoId)
    if (!undoItem || undoItem.undone || !undoItem.canUndo) {
      return { success: false, error: '无法撤销此操作' }
    }

    try {
      if (undoItem.onUndo) {
        const result = await undoItem.onUndo(undoItem.metadata)
        
        undoItem.undone = true
        undoItem.canUndo = false

        // 更新历史记录
        const historyOp = operationHistory.value.find(op => op.id === undoItem.operationId)
        if (historyOp) {
          historyOp.undone = true
        }

        // 添加成功提示
        addSuccessNotification({
          type: 'undo',
          title: '撤销成功',
          message: `已撤销: ${undoItem.title}`,
          duration: 3000
        })

        return { success: true, result }
      }
    } catch (error) {
      addErrorNotification({
        type: 'undo',
        title: '撤销失败',
        error: {
          type: ERROR_TYPE.UNKNOWN,
          message: error.message || '撤销操作失败'
        }
      })
      
      return { success: false, error }
    }

    return { success: false, error: '撤销函数不存在' }
  }

  /**
   * 撤销项过期处理
   *
   * @param {string} undoId - 撤销项ID
   */
  function expireUndoItem(undoId) {
    const undoItem = undoQueue.value.find(item => item.id === undoId)
    if (undoItem && !undoItem.undone) {
      undoItem.canUndo = false
    }
  }

  /**
   * 清理撤销队列
   */
  function cleanupUndoQueue() {
    const now = Date.now()
    undoQueue.value = undoQueue.value.filter(item => 
      item.canUndo || item.expiresAt > now - 60000
    )
  }

  // ==================== 通知管理方法 ====================

  /**
   * 添加成功通知
   *
   * @param {Object} notification - 通知配置
   */
  function addSuccessNotification(notification) {
    const successNotification = {
      id: `success_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      type: notification.type,
      title: notification.title,
      message: notification.message,
      operationId: notification.operationId,
      result: notification.result,
      duration: notification.duration || 5000,
      read: false,
      createdAt: Date.now(),
      showHistoryLink: !!notification.operationId
    }

    successNotifications.value.unshift(successNotification)

    // 自动移除
    if (successNotification.duration > 0) {
      setTimeout(() => {
        removeSuccessNotification(successNotification.id)
      }, successNotification.duration)
    }

    // 保持队列不超过50条
    if (successNotifications.value.length > 50) {
      successNotifications.value = successNotifications.value.slice(0, 50)
    }
  }

  /**
   * 添加错误通知
   *
   * @param {Object} notification - 通知配置
   */
  function addErrorNotification(notification) {
    const errorNotification = {
      id: `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      type: notification.type,
      title: notification.title,
      error: notification.error,
      operationId: notification.operationId,
      retryable: notification.retryable || false,
      expanded: false,
      read: false,
      createdAt: Date.now()
    }

    errorNotifications.value.unshift(errorNotification)

    // 保持队列不超过30条
    if (errorNotifications.value.length > 30) {
      errorNotifications.value = errorNotifications.value.slice(0, 30)
    }
  }

  /**
   * 移除成功通知
   *
   * @param {string} notificationId - 通知ID
   */
  function removeSuccessNotification(notificationId) {
    const index = successNotifications.value.findIndex(n => n.id === notificationId)
    if (index >= 0) {
      successNotifications.value.splice(index, 1)
    }
  }

  /**
   * 移除错误通知
   *
   * @param {string} notificationId - 通知ID
   */
  function removeErrorNotification(notificationId) {
    const index = errorNotifications.value.findIndex(n => n.id === notificationId)
    if (index >= 0) {
      errorNotifications.value.splice(index, 1)
    }
  }

  /**
   * 标记通知为已读
   *
   * @param {string} notificationId - 通知ID
   * @param {string} type - 通知类型 ('success' | 'error')
   */
  function markNotificationRead(notificationId, type) {
    if (type === 'success') {
      const notification = successNotifications.value.find(n => n.id === notificationId)
      if (notification) notification.read = true
    } else if (type === 'error') {
      const notification = errorNotifications.value.find(n => n.id === notificationId)
      if (notification) notification.read = true
    }
  }

  /**
   * 切换错误详情展开状态
   *
   * @param {string} notificationId - 通知ID
   */
  function toggleErrorExpanded(notificationId) {
    const notification = errorNotifications.value.find(n => n.id === notificationId)
    if (notification) {
      notification.expanded = !notification.expanded
    }
  }

  /**
   * 清除所有通知
   */
  function clearAllNotifications() {
    successNotifications.value = []
    errorNotifications.value = []
  }

  // ==================== 辅助方法 ====================

  /**
   * 分类错误类型
   *
   * @param {Error} error - 错误对象
   * @returns {string} 错误类型
   */
  function classifyError(error) {
    if (error.name === 'NetworkError' || error.code === 'NETWORK_ERROR') {
      return ERROR_TYPE.NETWORK
    }
    if (error.name === 'TimeoutError' || error.code === 'ETIMEDOUT') {
      return ERROR_TYPE.TIMEOUT
    }
    if (error.name === 'ValidationError' || error.code === 'VALIDATION_ERROR') {
      return ERROR_TYPE.VALIDATION
    }
    if (error.name === 'PermissionError' || error.code === 'PERMISSION_DENIED') {
      return ERROR_TYPE.PERMISSION
    }
    if (error.code?.startsWith('DEVICE_')) {
      return ERROR_TYPE.DEVICE
    }
    if (error.code?.startsWith('SYSTEM_')) {
      return ERROR_TYPE.SYSTEM
    }
    return ERROR_TYPE.UNKNOWN
  }

  /**
   * 获取错误帮助链接
   *
   * @param {string} errorType - 错误类型
   * @returns {Object} 帮助链接信息
   */
  function getErrorHelpLink(errorType) {
    const helpLinks = {
      [ERROR_TYPE.NETWORK]: {
        text: '网络问题排查指南',
        url: '/help/network-troubleshooting'
      },
      [ERROR_TYPE.TIMEOUT]: {
        text: '超时问题解决方案',
        url: '/help/timeout-solutions'
      },
      [ERROR_TYPE.VALIDATION]: {
        text: '参数校验说明',
        url: '/help/validation-rules'
      },
      [ERROR_TYPE.PERMISSION]: {
        text: '权限管理说明',
        url: '/help/permissions'
      },
      [ERROR_TYPE.DEVICE]: {
        text: '设备故障排查',
        url: '/help/device-troubleshooting'
      },
      [ERROR_TYPE.SYSTEM]: {
        text: '系统错误处理',
        url: '/help/system-errors'
      },
      [ERROR_TYPE.UNKNOWN]: {
        text: '常见问题解答',
        url: '/help/faq'
      }
    }
    return helpLinks[errorType] || helpLinks[ERROR_TYPE.UNKNOWN]
  }

  /**
   * 清理资源
   */
  function cleanup() {
    activeOperations.value = []
    operationHistory.value = []
    undoQueue.value = []
    successNotifications.value = []
    errorNotifications.value = []
    globalProgress.value = {
      visible: false,
      percentage: 0,
      status: '',
      message: '',
      cancellable: false
    }
  }

  // ==================== 导出 ====================

  return {
    // 状态
    activeOperations,
    operationHistory,
    undoQueue,
    successNotifications,
    errorNotifications,
    globalProgress,

    // 计算属性
    hasActiveOperations,
    runningOperationsCount,
    undoableCount,
    unreadSuccessCount,
    unreadErrorCount,

    // 操作管理方法
    createOperation,
    startOperation,
    updateOperationProgress,
    cancelOperation,
    retryOperation,
    moveToHistory,

    // 全局进度条方法
    updateGlobalProgress,

    // 撤销功能方法
    executeUndo,
    expireUndoItem,
    cleanupUndoQueue,

    // 通知管理方法
    addSuccessNotification,
    addErrorNotification,
    removeSuccessNotification,
    removeErrorNotification,
    markNotificationRead,
    toggleErrorExpanded,
    clearAllNotifications,

    // 辅助方法
    classifyError,
    getErrorHelpLink,
    cleanup,

    // 常量导出
    OPERATION_STATUS,
    OPERATION_TYPE,
    OPERATION_TYPE_TEXT,
    ERROR_TYPE,
    ERROR_TYPE_TEXT
  }
})
