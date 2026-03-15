/**
 * @file useLoading.js
 * @path src/composables/
 * @description 全局加载状态管理组合式函数，提供统一的加载状态控制和进度显示
 * @author Agent
 * @date 2024-03-15
 * @version 3.5.1
 */

import { ref, computed, readonly } from 'vue'

/**
 * 加载状态存储
 * @type {Map<string, {loading: boolean, progress: number, message: string, startTime: number}>}
 */
const loadingStates = new Map()

/**
 * 全局加载计数
 * @type {import('vue').Ref<number>}
 */
const globalLoadingCount = ref(0)

/**
 * 当前加载消息
 * @type {import('vue').Ref<string>}
 */
const currentLoadingMessage = ref('')

/**
 * 加载进度（0-100）
 * @type {import('vue').Ref<number>}
 */
const loadingProgress = ref(0)

/**
 * 是否显示全局加载遮罩
 * @type {import('vue').Ref<boolean>}
 */
const showGlobalOverlay = ref(false)

/**
 * 加载历史记录
 * @type {import('vue').Ref<Array>}
 */
const loadingHistory = ref([])

/**
 * 最大历史记录数
 * @constant {number}
 */
const MAX_HISTORY = 100

/**
 * 全局加载状态管理组合式函数
 *
 * @returns {Object} 加载状态和方法
 *
 * @example
 * ```javascript
 * const { startLoading, stopLoading, isLoading } = useLoading()
 *
 * // 开始加载
 * startLoading('fetchData', { message: '正在获取数据...' })
 *
 * // 更新进度
 * updateProgress('fetchData', 50)
 *
 * // 停止加载
 * stopLoading('fetchData')
 * ```
 */
export function useLoading() {
  /**
   * 是否有任何加载中的任务
   * @type {import('vue').ComputedRef<boolean>}
   */
  const isLoading = computed(() => globalLoadingCount.value > 0)

  /**
   * 当前加载任务数量
   * @type {import('vue').ComputedRef<number>}
   */
  const loadingTaskCount = computed(() => globalLoadingCount.value)

  /**
   * 所有加载中的任务键列表
   * @type {import('vue').ComputedRef<Array<string>>}
   */
  const loadingKeys = computed(() => {
    return Array.from(loadingStates.entries())
      .filter(([_, state]) => state.loading)
      .map(([key]) => key)
  })

  /**
   * 开始加载
   *
   * @param {string} key - 加载任务键
   * @param {Object} options - 选项
   * @param {string} [options.message] - 加载消息
   * @param {number} [options.progress] - 初始进度
   * @param {boolean} [options.showOverlay] - 是否显示全局遮罩
   */
  function startLoading(key, options = {}) {
    const { message = '', progress = 0, showOverlay = false } = options

    const existingState = loadingStates.get(key)
    if (existingState && existingState.loading) {
      return
    }

    loadingStates.set(key, {
      loading: true,
      progress,
      message,
      startTime: Date.now()
    })

    globalLoadingCount.value++
    currentLoadingMessage.value = message
    loadingProgress.value = progress

    if (showOverlay) {
      showGlobalOverlay.value = true
    }

    console.log(`[Loading] 开始: ${key}`, { message, progress })
  }

  /**
   * 停止加载
   *
   * @param {string} key - 加载任务键
   * @param {Object} [result] - 加载结果（用于记录历史）
   */
  function stopLoading(key, result = null) {
    const state = loadingStates.get(key)
    if (!state || !state.loading) {
      return
    }

    const duration = Date.now() - state.startTime

    loadingStates.set(key, {
      ...state,
      loading: false,
      progress: 100
    })

    globalLoadingCount.value = Math.max(0, globalLoadingCount.value - 1)

    if (globalLoadingCount.value === 0) {
      currentLoadingMessage.value = ''
      loadingProgress.value = 0
      showGlobalOverlay.value = false
    } else {
      const nextLoading = Array.from(loadingStates.entries())
        .find(([_, s]) => s.loading)
      if (nextLoading) {
        currentLoadingMessage.value = nextLoading[1].message
        loadingProgress.value = nextLoading[1].progress
      }
    }

    addToHistory({
      key,
      message: state.message,
      duration,
      result: result ? 'success' : 'failed',
      timestamp: Date.now()
    })

    console.log(`[Loading] 完成: ${key}`, { duration: `${duration}ms` })
  }

  /**
   * 更新加载进度
   *
   * @param {string} key - 加载任务键
   * @param {number} progress - 进度值（0-100）
   * @param {string} [message] - 更新的消息
   */
  function updateProgress(key, progress, message) {
    const state = loadingStates.get(key)
    if (!state || !state.loading) {
      return
    }

    const newProgress = Math.min(100, Math.max(0, progress))
    loadingStates.set(key, {
      ...state,
      progress: newProgress,
      message: message !== undefined ? message : state.message
    })

    const currentTask = Array.from(loadingStates.entries())
      .find(([k, s]) => k === key && s.loading)
    
    if (currentTask) {
      loadingProgress.value = newProgress
      if (message !== undefined) {
        currentLoadingMessage.value = message
      }
    }
  }

  /**
   * 更新加载消息
   *
   * @param {string} key - 加载任务键
   * @param {string} message - 新消息
   */
  function updateMessage(key, message) {
    const state = loadingStates.get(key)
    if (!state || !state.loading) {
      return
    }

    loadingStates.set(key, {
      ...state,
      message
    })

    const currentTask = Array.from(loadingStates.entries())
      .find(([k, s]) => k === key && s.loading)
    
    if (currentTask) {
      currentLoadingMessage.value = message
    }
  }

  /**
   * 检查指定任务是否正在加载
   *
   * @param {string} key - 加载任务键
   * @returns {boolean} 是否正在加载
   */
  function isLoadingKey(key) {
    const state = loadingStates.get(key)
    return state ? state.loading : false
  }

  /**
   * 获取指定任务的加载状态
   *
   * @param {string} key - 加载任务键
   * @returns {Object|null} 加载状态
   */
  function getLoadingState(key) {
    const state = loadingStates.get(key)
    return state ? { ...state } : null
  }

  /**
   * 包装异步函数，自动管理加载状态
   *
   * @param {string} key - 加载任务键
   * @param {Function} asyncFn - 异步函数
   * @param {Object} options - 选项
   * @returns {Promise<any>} 异步函数结果
   *
   * @example
   * const result = await withLoading('fetchData', async () => {
   *   return await fetchData()
   * }, { message: '正在获取数据...' })
   */
  async function withLoading(key, asyncFn, options = {}) {
    startLoading(key, options)
    try {
      const result = await asyncFn()
      stopLoading(key, true)
      return result
    } catch (error) {
      stopLoading(key, false)
      throw error
    }
  }

  /**
   * 批量加载多个任务
   *
   * @param {Array<{key: string, fn: Function, options: Object}>} tasks - 任务列表
   * @param {Object} options - 全局选项
   * @returns {Promise<Array>} 所有任务结果
   */
  async function batchLoading(tasks, options = {}) {
    const { parallel = true } = options
    const results = []

    if (parallel) {
      const promises = tasks.map(({ key, fn, options: taskOptions }) =>
        withLoading(key, fn, taskOptions)
      )
      return Promise.all(promises)
    } else {
      for (const { key, fn, options: taskOptions } of tasks) {
        const result = await withLoading(key, fn, taskOptions)
        results.push(result)
      }
      return results
    }
  }

  /**
   * 添加到历史记录
   *
   * @param {Object} record - 历史记录
   */
  function addToHistory(record) {
    loadingHistory.value.unshift(record)
    if (loadingHistory.value.length > MAX_HISTORY) {
      loadingHistory.value = loadingHistory.value.slice(0, MAX_HISTORY)
    }
  }

  /**
   * 清除所有加载状态
   */
  function clearAll() {
    loadingStates.clear()
    globalLoadingCount.value = 0
    currentLoadingMessage.value = ''
    loadingProgress.value = 0
    showGlobalOverlay.value = false
  }

  /**
   * 重置加载状态
   */
  function reset() {
    clearAll()
    loadingHistory.value = []
  }

  return {
    isLoading: readonly(isLoading),
    loadingTaskCount: readonly(loadingTaskCount),
    loadingKeys: readonly(loadingKeys),
    currentLoadingMessage: readonly(currentLoadingMessage),
    loadingProgress: readonly(loadingProgress),
    showGlobalOverlay: readonly(showGlobalOverlay),
    loadingHistory: readonly(loadingHistory),

    startLoading,
    stopLoading,
    updateProgress,
    updateMessage,
    isLoadingKey,
    getLoadingState,
    withLoading,
    batchLoading,
    clearAll,
    reset
  }
}

/**
 * 创建加载状态组合式函数（独立实例）
 *
 * @param {string} namespace - 命名空间
 * @returns {Object} 加载状态和方法
 */
export function createLoadingStore(namespace = 'default') {
  const prefix = `${namespace}:`
  const { 
    startLoading: baseStart,
    stopLoading: baseStop,
    isLoadingKey: baseIsLoading,
    getLoadingState: baseGetState,
    updateProgress: baseUpdateProgress,
    updateMessage: baseUpdateMessage,
    ...rest
  } = useLoading()

  function startLoading(key, options) {
    return baseStart(prefix + key, options)
  }

  function stopLoading(key, result) {
    return baseStop(prefix + key, result)
  }

  function isLoadingKey(key) {
    return baseIsLoading(prefix + key)
  }

  function getLoadingState(key) {
    return baseGetState(prefix + key)
  }

  function updateProgress(key, progress, message) {
    return baseUpdateProgress(prefix + key, progress, message)
  }

  function updateMessage(key, message) {
    return baseUpdateMessage(prefix + key, message)
  }

  async function withLoading(key, asyncFn, options) {
    return rest.withLoading(prefix + key, asyncFn, options)
  }

  return {
    ...rest,
    startLoading,
    stopLoading,
    isLoadingKey,
    getLoadingState,
    updateProgress,
    updateMessage,
    withLoading
  }
}

export default useLoading
