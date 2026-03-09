/**
 * @file useProgress.js
 * @path src/composables/
 * @description 操作进度管理组合式函数，提供操作状态跟踪、进度更新、取消操作等功能
 * @author Agent
 * @date 2024-03-07
 * @dependencies vue
 */

import { ref, computed, readonly } from 'vue'

/**
 * 操作状态枚举
 */
export const OPERATION_STATUS = {
  IDLE: 'idle',
  RUNNING: 'running',
  PAUSED: 'paused',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled'
}

/**
 * 操作进度管理组合式函数
 *
 * @param {Object} options - 配置选项
 * @param {number} [options.autoResetDelay=3000] - 操作完成后自动重置延迟（毫秒）
 * @param {boolean} [options.enableAutoReset=true] - 是否在操作完成后自动重置
 * @param {Function} [options.onComplete] - 操作完成回调
 * @param {Function} [options.onFail] - 操作失败回调
 * @param {Function} [options.onCancel] - 操作取消回调
 * @returns {Object} 进度状态与操作方法
 *
 * @example
 * ```javascript
 * const { startOperation, updateProgress, cancelOperation } = useProgress({
 *   onComplete: () => console.log('操作完成'),
 *   onFail: (error) => console.error('操作失败:', error)
 * })
 *
 * // 开始操作
 * startOperation('数据采集', { total: 100 })
 *
 * // 更新进度
 * updateProgress(50, '正在处理第50个数据点...')
 *
 * // 完成操作
 * completeOperation('数据采集完成')
 *
 * // 取消操作
 * cancelOperation()
 * ```
 */
export function useProgress(options = {}) {
  const {
    autoResetDelay = 3000,
    enableAutoReset = true,
    onComplete,
    onFail,
    onCancel
  } = options

  // === 响应式状态 ===
  /** 是否正在运行 */
  const isRunning = ref(false)
  /** 进度百分比 (0-100) */
  const progress = ref(0)
  /** 操作状态 */
  const status = ref(OPERATION_STATUS.IDLE)
  /** 操作名称 */
  const operationName = ref('')
  /** 状态消息 */
  const message = ref('')
  /** 错误信息 */
  const error = ref(null)
  /** 开始时间 */
  const startTime = ref(null)
  /** 结束时间 */
  const endTime = ref(null)
  /** AbortController实例 */
  const abortController = ref(null)
  /** 操作元数据 */
  const metadata = ref({})
  /** 子任务列表 */
  const subtasks = ref([])
  /** 当前活跃子任务索引 */
  const activeSubtaskIndex = ref(-1)

  // === 计算属性 ===
  /** 操作是否已完成（成功或失败） */
  const isCompleted = computed(() =>
    status.value === OPERATION_STATUS.COMPLETED ||
    status.value === OPERATION_STATUS.FAILED ||
    status.value === OPERATION_STATUS.CANCELLED
  )

  /** 操作是否可以取消 */
  const isCancellable = computed(() =>
    status.value === OPERATION_STATUS.RUNNING ||
    status.value === OPERATION_STATUS.PAUSED
  )

  /** 操作是否可以暂停 */
  const isPausable = computed(() =>
    status.value === OPERATION_STATUS.RUNNING
  )

  /** 操作是否可以恢复 */
  const isResumable = computed(() =>
    status.value === OPERATION_STATUS.PAUSED
  )

  /** 操作持续时间（毫秒） */
  const duration = computed(() => {
    if (!startTime.value) return 0
    const end = endTime.value || Date.now()
    return end - startTime.value
  })

  /** 格式化的持续时间 */
  const formattedDuration = computed(() => {
    const ms = duration.value
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`
  })

  /** 预计剩余时间（基于当前进度） */
  const estimatedTimeRemaining = computed(() => {
    if (!startTime.value || progress.value === 0 || progress.value >= 100) return 0
    const elapsed = duration.value
    const estimatedTotal = elapsed / (progress.value / 100)
    return Math.max(0, estimatedTotal - elapsed)
  })

  /** 格式化的预计剩余时间 */
  const formattedEstimatedTime = computed(() => {
    const ms = estimatedTimeRemaining.value
    if (ms === 0) return '--'
    if (ms < 1000) return `${Math.round(ms)}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`
  })

  /**
   * 开始操作
   *
   * @param {string} name - 操作名称
   * @param {Object} [meta] - 操作元数据
   * @param {number} [meta.total] - 总任务数
   * @param {string} [meta.description] - 操作描述
   * @param {Array} [meta.subtasks] - 子任务列表
   * @returns {AbortController} 可用于取消操作的控制器
   */
  function startOperation(name, meta = {}) {
    // 重置状态
    resetProgress()

    // 设置新操作
    operationName.value = name
    isRunning.value = true
    status.value = OPERATION_STATUS.RUNNING
    progress.value = 0
    startTime.value = Date.now()
    endTime.value = null
    message.value = meta.description || `正在执行: ${name}`
    metadata.value = meta
    subtasks.value = meta.subtasks || []
    activeSubtaskIndex.value = subtasks.value.length > 0 ? 0 : -1

    // 创建AbortController
    abortController.value = new AbortController()

    return abortController.value
  }

  /**
   * 更新进度
   *
   * @param {number} value - 进度值 (0-100)
   * @param {string} [statusMessage] - 状态消息
   * @param {Object} [details] - 额外详情
   */
  function updateProgress(value, statusMessage, details = {}) {
    progress.value = Math.min(100, Math.max(0, value))
    if (statusMessage) {
      message.value = statusMessage
    }

    // 更新子任务进度
    if (details.subtaskIndex !== undefined && details.subtaskIndex >= 0) {
      activeSubtaskIndex.value = details.subtaskIndex
    }
  }

  /**
   * 增加进度
   *
   * @param {number} increment - 增量值
   * @param {string} [statusMessage] - 状态消息
   */
  function incrementProgress(increment, statusMessage) {
    updateProgress(progress.value + increment, statusMessage)
  }

  /**
   * 更新子任务状态
   *
   * @param {number} index - 子任务索引
   * @param {string} taskStatus - 子任务状态
   * @param {string} [taskMessage] - 子任务消息
   */
  function updateSubtask(index, taskStatus, taskMessage) {
    if (index >= 0 && index < subtasks.value.length) {
      subtasks.value[index] = {
        ...subtasks.value[index],
        status: taskStatus,
        message: taskMessage
      }
      activeSubtaskIndex.value = index
    }
  }

  /**
   * 完成操作
   *
   * @param {string} [completionMessage] - 完成消息
   */
  function completeOperation(completionMessage) {
    isRunning.value = false
    status.value = OPERATION_STATUS.COMPLETED
    progress.value = 100
    endTime.value = Date.now()
    message.value = completionMessage || `${operationName.value} 完成`
    abortController.value = null

    // 触发完成回调
    onComplete?.({
      name: operationName.value,
      duration: duration.value,
      metadata: metadata.value
    })

    // 自动重置
    if (enableAutoReset) {
      scheduleAutoReset()
    }
  }

  /**
   * 失败操作
   *
   * @param {Error|string} errorInfo - 错误信息
   * @param {string} [failureMessage] - 失败消息
   */
  function failOperation(errorInfo, failureMessage) {
    isRunning.value = false
    status.value = OPERATION_STATUS.FAILED
    endTime.value = Date.now()
    error.value = errorInfo
    message.value = failureMessage || `${operationName.value} 失败`
    abortController.value = null

    // 触发失败回调
    onFail?.({
      name: operationName.value,
      error: errorInfo,
      duration: duration.value,
      metadata: metadata.value
    })

    // 自动重置
    if (enableAutoReset) {
      scheduleAutoReset()
    }
  }

  /**
   * 取消操作
   *
   * @param {string} [cancelReason] - 取消原因
   */
  function cancelOperation(cancelReason) {
    if (!isCancellable.value) return

    // 触发AbortController
    if (abortController.value) {
      abortController.value.abort(cancelReason || 'Operation cancelled by user')
    }

    isRunning.value = false
    status.value = OPERATION_STATUS.CANCELLED
    endTime.value = Date.now()
    message.value = cancelReason || `${operationName.value} 已取消`
    abortController.value = null

    // 触发取消回调
    onCancel?.({
      name: operationName.value,
      reason: cancelReason,
      duration: duration.value,
      metadata: metadata.value
    })

    // 自动重置
    if (enableAutoReset) {
      scheduleAutoReset()
    }
  }

  /**
   * 暂停操作
   */
  function pauseOperation() {
    if (!isPausable.value) return
    status.value = OPERATION_STATUS.PAUSED
    message.value = `${operationName.value} 已暂停`
  }

  /**
   * 恢复操作
   */
  function resumeOperation() {
    if (!isResumable.value) return
    status.value = OPERATION_STATUS.RUNNING
    message.value = `${operationName.value} 正在继续...`
  }

  /**
   * 重置进度
   */
  function resetProgress() {
    isRunning.value = false
    progress.value = 0
    status.value = OPERATION_STATUS.IDLE
    operationName.value = ''
    message.value = ''
    error.value = null
    startTime.value = null
    endTime.value = null
    abortController.value = null
    metadata.value = {}
    subtasks.value = []
    activeSubtaskIndex.value = -1
  }

  /**
   * 安排自动重置
   *
   * @internal 内部方法，不对外暴露
   */
  let autoResetTimer = null
  function scheduleAutoReset() {
    if (autoResetTimer) {
      clearTimeout(autoResetTimer)
    }
    autoResetTimer = setTimeout(() => {
      resetProgress()
      autoResetTimer = null
    }, autoResetDelay)
  }

  /**
   * 获取进度快照
   *
   * @returns {Object} 进度状态快照
   */
  function getSnapshot() {
    return {
      isRunning: isRunning.value,
      progress: progress.value,
      status: status.value,
      operationName: operationName.value,
      message: message.value,
      error: error.value,
      startTime: startTime.value,
      endTime: endTime.value,
      duration: duration.value,
      estimatedTimeRemaining: estimatedTimeRemaining.value,
      metadata: metadata.value,
      subtasks: subtasks.value.map(task => ({ ...task })),
      activeSubtaskIndex: activeSubtaskIndex.value
    }
  }

  /**
   * 从快照恢复进度
   *
   * @param {Object} snapshot - 进度快照
   */
  function restoreFromSnapshot(snapshot) {
    isRunning.value = snapshot.isRunning
    progress.value = snapshot.progress
    status.value = snapshot.status
    operationName.value = snapshot.operationName
    message.value = snapshot.message
    error.value = snapshot.error
    startTime.value = snapshot.startTime
    endTime.value = snapshot.endTime
    metadata.value = snapshot.metadata
    subtasks.value = snapshot.subtasks
    activeSubtaskIndex.value = snapshot.activeSubtaskIndex
  }

  return {
    // 状态
    isRunning: readonly(isRunning),
    progress: readonly(progress),
    status: readonly(status),
    operationName: readonly(operationName),
    message: readonly(message),
    error: readonly(error),
    startTime: readonly(startTime),
    endTime: readonly(endTime),
    abortController: readonly(abortController),
    metadata: readonly(metadata),
    subtasks: readonly(subtasks),
    activeSubtaskIndex: readonly(activeSubtaskIndex),

    // 计算属性
    isCompleted,
    isCancellable,
    isPausable,
    isResumable,
    duration,
    formattedDuration,
    estimatedTimeRemaining,
    formattedEstimatedTime,

    // 方法
    startOperation,
    updateProgress,
    incrementProgress,
    updateSubtask,
    completeOperation,
    failOperation,
    cancelOperation,
    pauseOperation,
    resumeOperation,
    resetProgress,
    getSnapshot,
    restoreFromSnapshot
  }
}

/**
 * 创建进度跟踪器
 *
 * @param {Function} progressUpdater - 进度更新函数
 * @returns {Object} 进度跟踪器对象
 *
 * @example
 * ```javascript
 * const tracker = createProgressTracker((progress, message) => {
 *   updateProgress(progress, message)
 * })
 *
 * tracker.report(50, '处理中...')
 * tracker.complete('完成')
 * ```
 */
export function createProgressTracker(progressUpdater) {
  let currentProgress = 0
  let isCompleted = false

  return {
    /**
     * 报告进度
     */
    report(progress, message) {
      if (isCompleted) return
      currentProgress = Math.min(100, Math.max(0, progress))
      progressUpdater(currentProgress, message)
    },

    /**
     * 增加进度
     */
    increment(delta, message) {
      this.report(currentProgress + delta, message)
    },

    /**
     * 完成进度
     */
    complete(message) {
      isCompleted = true
      progressUpdater(100, message)
    },

    /**
     * 获取当前进度
     */
    getProgress() {
      return currentProgress
    },

    /**
     * 是否已完成
     */
    isCompleted() {
      return isCompleted
    }
  }
}
