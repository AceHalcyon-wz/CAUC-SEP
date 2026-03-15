/**
 * @file useOffline.js
 * @path src/composables/
 * @description 离线功能组合式函数，提供统一的离线状态管理和操作接口
 * @author Frontend Engineer Agent
 * @date 2026-03-07
 * @dependencies vue, ../utils/offlineStorage, ../utils/offlineQueue, ../utils/offlineSync, ./useOnlineStatus
 */

import { ref, computed, onMounted, onUnmounted, readonly } from 'vue'
import { initOfflineStorage } from '../utils/offlineStorage'
import { initOfflineQueue, OperationPriority, OperationStatus } from '../utils/offlineQueue'
import { initOfflineSync, SyncStatus, SyncStrategy } from '../utils/offlineSync'
import { useOnlineStatus } from './useOnlineStatus'

/**
 * 离线功能组合式函数
 *
 * @param {Object} options - 配置选项
 * @param {Object} [options.storageOptions] - 存储配置
 * @param {Object} [options.queueOptions] - 队列配置
 * @param {Object} [options.syncOptions] - 同步配置
 * @param {boolean} [options.autoInit=true] - 是否自动初始化
 * @returns {Object} 离线功能状态与方法
 *
 * @example
 * ```javascript
 * const {
 *   isOnline,
 *   isOffline,
 *   storageReady,
 *   pendingOperations,
 *   syncStatus,
 *   saveData,
 *   getData,
 *   enqueueOperation,
 *   syncNow
 * } = useOffline()
 *
 * // 保存数据到本地
 * await saveData('experiments', 'exp_001', experimentData)
 *
 * // 获取本地数据
 * const data = await getData('experiments', 'exp_001')
 *
 * // 离线时添加操作到队列
 * if (isOffline.value) {
 *   await enqueueOperation({
 *     type: 'api_request',
 *     data: { url: '/api/experiments', method: 'POST', body: experimentData }
 *   })
 * }
 *
 * // 手动触发同步
 * await syncNow()
 * ```
 */
export function useOffline(options = {}) {
  const {
    storageOptions = {},
    queueOptions = {},
    syncOptions = {},
    autoInit = true
  } = options

  // === 在线状态 ===
  const onlineStatus = useOnlineStatus({
    onOnline: handleOnline,
    onOffline: handleOffline
  })

  // === 响应式状态 ===
  /** 存储是否就绪 */
  const storageReady = ref(false)
  /** 队列是否就绪 */
  const queueReady = ref(false)
  /** 同步是否就绪 */
  const syncReady = ref(false)
  /** 是否全部就绪 */
  const isReady = computed(() => storageReady.value && queueReady.value && syncReady.value)
  
  /** 待处理操作数量 */
  const pendingOperations = ref(0)
  /** 同步状态 */
  const syncStatus = ref(SyncStatus.IDLE)
  /** 同步进度 */
  const syncProgress = ref(0)
  /** 最后同步时间 */
  const lastSyncTime = ref(null)
  
  /** 存储统计信息 */
  const storageStats = ref(null)
  /** 队列统计信息 */
  const queueStats = ref(null)
  
  /** 离线持续时间 */
  const offlineDuration = onlineStatus.offlineDuration
  /** 格式化的离线持续时间 */
  const formattedOfflineDuration = onlineStatus.formattedOfflineDuration

  // === 内部变量 ===
  let storage = null
  let queue = null
  let sync = null
  let statsTimer = null

  /**
   * 初始化离线功能
   *
   * @returns {Promise<void>}
   */
  async function initialize() {
    try {
      console.log('[useOffline] 开始初始化...')

      // 初始化存储
      storage = await initOfflineStorage(storageOptions)
      storageReady.value = true
      console.log('[useOffline] 存储初始化完成')

      // 初始化队列
      queue = await initOfflineQueue(queueOptions)
      queueReady.value = true
      console.log('[useOffline] 队列初始化完成')

      // 初始化同步
      sync = await initOfflineSync(syncOptions)
      syncReady.value = true
      console.log('[useOffline] 同步初始化完成')

      // 设置回调
      setupCallbacks()

      // 启动统计更新
      startStatsUpdate()

      // 加载初始状态
      await updateStats()

      console.log('[useOffline] 初始化完成')
    } catch (error) {
      console.error('[useOffline] 初始化失败:', error)
      throw error
    }
  }

  /**
   * 设置回调函数
   *
   * @internal 内部方法，不对外暴露
   */
  function setupCallbacks() {
    // 队列变更回调
    queue.onQueueChange = async (_event) => {
      await updateStats()
    }

    // 同步进度回调
    sync.onProgress = (info) => {
      syncProgress.value = info.progress
    }

    // 同步完成回调
    sync.onSyncComplete = async (result) => {
      syncStatus.value = result.failed > 0 ? SyncStatus.PARTIAL : SyncStatus.SYNCED
      lastSyncTime.value = Date.now()
      await updateStats()
    }

    // 同步错误回调
    sync.onSyncError = (_error) => {
      syncStatus.value = SyncStatus.FAILED
    }

    // 冲突回调
    sync.onConflict = (conflict) => {
      console.warn('[useOffline] 检测到数据冲突:', conflict)
    }
  }

  /**
   * 处理网络上线事件
   *
   * @param {Object} info - 上线信息
   */
  function handleOnline(info) {
    console.log('[useOffline] 网络已恢复', info)
    
    // 自动同步
    if (syncReady.value) {
      syncNow().catch(err => {
        console.error('[useOffline] 自动同步失败:', err)
      })
    }
  }

  /**
   * 处理网络离线事件
   *
   * @param {Object} info - 离线信息
   */
  function handleOffline(info) {
    console.log('[useOffline] 网络已断开', info)
  }

  /**
   * 更新统计信息
   *
   * @internal 内部方法，不对外暴露
   */
  async function updateStats() {
    try {
      if (storageReady.value) {
        storageStats.value = await storage.getStats()
      }

      if (queueReady.value) {
        queueStats.value = await queue.getStats()
        pendingOperations.value = queueStats.value.pending
      }

      if (syncReady.value) {
        const syncStatusInfo = sync.getSyncStatus()
        syncStatus.value = syncStatusInfo.status
        lastSyncTime.value = syncStatusInfo.lastSyncTime
      }
    } catch (error) {
      console.error('[useOffline] 更新统计失败:', error)
    }
  }

  /**
   * 启动统计更新定时器
   *
   * @internal 内部方法，不对外暴露
   */
  function startStatsUpdate() {
    stopStatsUpdate()
    statsTimer = setInterval(() => {
      updateStats().catch(err => {
        console.error('[useOffline] 定时更新统计失败:', err)
      })
    }, 10000) // 每10秒更新一次
  }

  /**
   * 停止统计更新定时器
   *
   * @internal 内部方法，不对外暴露
   */
  function stopStatsUpdate() {
    if (statsTimer) {
      clearInterval(statsTimer)
      statsTimer = null
    }
  }

  // ==================== 存储操作 ====================

  /**
   * 保存数据到本地存储
   *
   * @param {string} storeName - 存储名称
   * @param {string|number} key - 数据键
   * @param {any} value - 数据值
   * @param {Object} [options] - 存储选项
   * @returns {Promise<void>}
   */
  async function saveData(storeName, key, value, options = {}) {
    if (!storageReady.value) {
      throw new Error('存储未初始化')
    }

    const data = {
      ...value,
      updatedAt: Date.now()
    }

    await storage.set(storeName, key, data, options)
    await updateStats()
  }

  /**
   * 从本地存储获取数据
   *
   * @param {string} storeName - 存储名称
   * @param {string|number} key - 数据键
   * @returns {Promise<any|null>} 数据值
   */
  async function getData(storeName, key) {
    if (!storageReady.value) {
      throw new Error('存储未初始化')
    }

    return storage.get(storeName, key)
  }

  /**
   * 获取存储中的所有数据
   *
   * @param {string} storeName - 存储名称
   * @returns {Promise<Array<any>>} 数据数组
   */
  async function getAllData(storeName) {
    if (!storageReady.value) {
      throw new Error('存储未初始化')
    }

    return storage.getAll(storeName)
  }

  /**
   * 删除数据
   *
   * @param {string} storeName - 存储名称
   * @param {string|number} key - 数据键
   * @returns {Promise<void>}
   */
  async function deleteData(storeName, key) {
    if (!storageReady.value) {
      throw new Error('存储未初始化')
    }

    await storage.delete(storeName, key)
    await updateStats()
  }

  /**
   * 清空存储
   *
   * @param {string} storeName - 存储名称
   * @returns {Promise<void>}
   */
  async function clearStore(storeName) {
    if (!storageReady.value) {
      throw new Error('存储未初始化')
    }

    await storage.clear(storeName)
    await updateStats()
  }

  // ==================== 队列操作 ====================

  /**
   * 添加操作到队列
   *
   * @param {Object} operation - 操作对象
   * @param {string} operation.type - 操作类型
   * @param {any} operation.data - 操作数据
   * @param {number} [operation.priority=OperationPriority.NORMAL] - 优先级
   * @returns {Promise<number>} 操作ID
   */
  async function enqueueOperation(operation) {
    if (!queueReady.value) {
      throw new Error('队列未初始化')
    }

    const id = await queue.enqueue(operation)
    await updateStats()
    return id
  }

  /**
   * 批量添加操作
   *
   * @param {Array<Object>} operations - 操作数组
   * @returns {Promise<Array<number>>} 操作ID数组
   */
  async function enqueueBatch(operations) {
    if (!queueReady.value) {
      throw new Error('队列未初始化')
    }

    const ids = await queue.enqueueBatch(operations)
    await updateStats()
    return ids
  }

  /**
   * 获取操作列表
   *
   * @param {Object} [options] - 查询选项
   * @returns {Promise<Array<Object>>} 操作列表
   */
  async function getOperations(options = {}) {
    if (!queueReady.value) {
      throw new Error('队列未初始化')
    }

    return queue.getOperations(options)
  }

  /**
   * 取消操作
   *
   * @param {number} id - 操作ID
   * @returns {Promise<void>}
   */
  async function cancelOperation(id) {
    if (!queueReady.value) {
      throw new Error('队列未初始化')
    }

    await queue.cancelOperation(id)
    await updateStats()
  }

  /**
   * 重试失败的操作
   *
   * @param {number} id - 操作ID
   * @returns {Promise<void>}
   */
  async function retryOperation(id) {
    if (!queueReady.value) {
      throw new Error('队列未初始化')
    }

    await queue.retryOperation(id)
    await updateStats()
  }

  /**
   * 注册操作处理器
   *
   * @param {string} type - 操作类型
   * @param {Function} handler - 处理函数
   */
  function registerHandler(type, handler) {
    if (!queueReady.value) {
      throw new Error('队列未初始化')
    }

    queue.registerHandler(type, handler)
  }

  // ==================== 同步操作 ====================

  /**
   * 立即同步
   *
   * @param {Object} [options] - 同步选项
   * @returns {Promise<Object>} 同步结果
   */
  async function syncNow(options = {}) {
    if (!syncReady.value) {
      throw new Error('同步未初始化')
    }

    if (!onlineStatus.isOnline.value) {
      console.warn('[useOffline] 当前离线，无法同步')
      return { success: false, error: '当前离线' }
    }

    syncStatus.value = SyncStatus.SYNCING
    syncProgress.value = 0

    const result = await sync.syncAll(options)
    await updateStats()

    return result
  }

  /**
   * 同步指定类型数据
   *
   * @param {string} dataType - 数据类型
   * @param {Object} [options] - 同步选项
   * @returns {Promise<Object>} 同步结果
   */
  async function syncDataType(dataType, options = {}) {
    if (!syncReady.value) {
      throw new Error('同步未初始化')
    }

    if (!onlineStatus.isOnline.value) {
      console.warn('[useOffline] 当前离线，无法同步')
      return { success: false, error: '当前离线' }
    }

    return sync.syncDataType(dataType, options)
  }

  /**
   * 注册同步处理器
   *
   * @param {string} dataType - 数据类型
   * @param {Object} handler - 处理器对象
   */
  function registerSyncHandler(dataType, handler) {
    if (!syncReady.value) {
      throw new Error('同步未初始化')
    }

    sync.registerSyncHandler(dataType, handler)
  }

  /**
   * 智能请求（在线时直接发送，离线时入队）
   *
   * @param {Object} request - 请求对象
   * @param {number} [priority=OperationPriority.NORMAL] - 优先级
   * @returns {Promise<Object>} 响应或队列信息
   */
  async function smartRequest(request, priority = OperationPriority.NORMAL) {
    if (!syncReady.value) {
      throw new Error('同步未初始化')
    }

    return sync.smartRequest(request, priority)
  }

  // ==================== 工具方法 ====================

  /**
   * 清理过期数据
   *
   * @returns {Promise<number>} 清理数量
   */
  async function cleanup() {
    if (!storageReady.value) {
      throw new Error('存储未初始化')
    }

    const cleaned = await storage.cleanupExpired()
    await queue.cleanupCompleted()
    await updateStats()

    return cleaned
  }

  /**
   * 获取完整状态报告
   *
   * @returns {Object} 状态报告
   */
  function getStatusReport() {
    return {
      online: onlineStatus.isOnline.value,
      ready: isReady.value,
      storage: {
        ready: storageReady.value,
        stats: storageStats.value
      },
      queue: {
        ready: queueReady.value,
        stats: queueStats.value
      },
      sync: {
        ready: syncReady.value,
        status: syncStatus.value,
        progress: syncProgress.value,
        lastSyncTime: lastSyncTime.value
      },
      offline: {
        duration: offlineDuration.value,
        formatted: formattedOfflineDuration.value
      }
    }
  }

  // ==================== 生命周期 ====================

  onMounted(async () => {
    if (autoInit) {
      try {
        await initialize()
      } catch (error) {
        console.error('[useOffline] 自动初始化失败:', error)
      }
    }
  })

  onUnmounted(() => {
    stopStatsUpdate()
  })

  // ==================== 返回 ====================

  return {
    // 状态
    isOnline: onlineStatus.isOnline,
    isOffline: onlineStatus.isOffline,
    isReady: readonly(isReady),
    storageReady: readonly(storageReady),
    queueReady: readonly(queueReady),
    syncReady: readonly(syncReady),
    
    // 统计
    pendingOperations: readonly(pendingOperations),
    syncStatus: readonly(syncStatus),
    syncProgress: readonly(syncProgress),
    lastSyncTime: readonly(lastSyncTime),
    storageStats: readonly(storageStats),
    queueStats: readonly(queueStats),
    offlineDuration: readonly(offlineDuration),
    formattedOfflineDuration,
    
    // 初始化
    initialize,
    
    // 存储操作
    saveData,
    getData,
    getAllData,
    deleteData,
    clearStore,
    
    // 队列操作
    enqueueOperation,
    enqueueBatch,
    getOperations,
    cancelOperation,
    retryOperation,
    registerHandler,
    
    // 同步操作
    syncNow,
    syncDataType,
    registerSyncHandler,
    smartRequest,
    
    // 工具方法
    cleanup,
    getStatusReport,
    updateStats
  }
}

// 导出枚举和常量
export { OperationPriority, OperationStatus, SyncStatus, SyncStrategy }
