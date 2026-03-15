/**
 * @file offlineSync.js
 * @path src/utils/
 * @description 网络恢复后数据同步模块，实现离线数据自动同步、冲突解决、同步状态管理
 * @author Frontend Engineer Agent
 * @date 2026-03-07
 * @dependencies ./offlineStorage, ./offlineQueue, axios
 */

import axios from 'axios'
import { getOfflineStorage } from './offlineStorage'
import { getOfflineQueue, OperationPriority } from './offlineQueue'

/**
 * 同步状态枚举
 * 
 * @readonly
 * @enum {string}
 */
export const SyncStatus = {
  /** 空闲 */
  IDLE: 'idle',
  /** 同步中 */
  SYNCING: 'syncing',
  /** 已同步 */
  SYNCED: 'synced',
  /** 同步失败 */
  FAILED: 'failed',
  /** 部分同步 */
  PARTIAL: 'partial'
}

/**
 * 同步策略枚举
 * 
 * @readonly
 * @enum {string}
 */
export const SyncStrategy = {
  /** 服务器优先（服务器数据覆盖本地） */
  SERVER_WINS: 'server_wins',
  /** 本地优先（本地数据覆盖服务器） */
  LOCAL_WINS: 'local_wins',
  /** 合并（尝试合并数据） */
  MERGE: 'merge',
  /** 手动解决（需要用户介入） */
  MANUAL: 'manual'
}

/**
 * 数据同步管理器
 * 
 * @description 管理离线数据的同步，支持自动同步、冲突检测、增量同步
 * 
 * @example
 * ```javascript
 * const sync = new OfflineSync()
 * await sync.init()
 * 
 * // 注册同步处理器
 * sync.registerSyncHandler('experiments', {
 *   pull: async () => { ... },
 *   push: async (data) => { ... },
 *   resolveConflict: (local, remote) => { ... }
 * })
 * 
 * // 网络恢复时触发同步
 * window.addEventListener('online', () => sync.syncAll())
 * 
 * // 手动同步
 * await sync.syncDataType('experiments')
 * ```
 */
export class OfflineSync {
  /**
   * 构造函数
   * 
   * @param {Object} options - 配置选项
   * @param {string} [options.apiBase='/api'] - API基础路径
   * @param {number} [options.syncInterval=60000] - 自动同步间隔（毫秒）
   * @param {number} [options.maxRetries=3] - 最大重试次数
   * @param {number} [options.retryDelay=5000] - 重试延迟（毫秒）
   * @param {SyncStrategy} [options.defaultStrategy=SyncStrategy.SERVER_WINS] - 默认冲突解决策略
   * @param {boolean} [options.enableAutoSync=true] - 是否启用自动同步
   */
  constructor(options = {}) {
    this.apiBase = options.apiBase || '/api'
    this.syncInterval = options.syncInterval || 60000
    this.maxRetries = options.maxRetries || 3
    this.retryDelay = options.retryDelay || 5000
    this.defaultStrategy = options.defaultStrategy || SyncStrategy.SERVER_WINS
    this.enableAutoSync = options.enableAutoSync !== false
    
    this.storage = getOfflineStorage()
    this.queue = getOfflineQueue()
    this.syncTimer = null
    
    // 同步状态
    this.status = SyncStatus.IDLE
    this.lastSyncTime = null
    this.syncProgress = 0
    
    // 同步处理器映射
    this.syncHandlers = new Map()
    
    // 同步统计
    this.stats = {
      totalSyncs: 0,
      successfulSyncs: 0,
      failedSyncs: 0,
      conflicts: 0,
      lastError: null
    }
    
    // 回调函数
    this.onSyncStart = null
    this.onSyncComplete = null
    this.onSyncError = null
    this.onProgress = null
    this.onConflict = null
  }
  
  /**
   * 初始化同步管理器
   * 
   * @returns {Promise<void>}
   */
  async init() {
    // 确保存储和队列已初始化
    if (!this.storage.db) {
      await this.storage.init()
    }
    if (!this.queue.storage.db) {
      await this.queue.init()
    }
    
    // 加载上次同步时间
    const lastSync = await this.storage.get('cacheData', 'lastSyncTime')
    if (lastSync) {
      this.lastSyncTime = lastSync.value
    }
    
    // 注册默认API请求处理器
    this.queue.registerHandler('api_request', this.handleApiRequest.bind(this))
    
    // 监听网络状态
    window.addEventListener('online', this.handleOnline.bind(this))
    window.addEventListener('offline', this.handleOffline.bind(this))
    
    // 启动自动同步
    if (this.enableAutoSync && navigator.onLine) {
      this.startAutoSync()
    }
    
    console.log('[OfflineSync] 初始化完成')
  }
  
  /**
   * 注册同步处理器
   * 
   * @param {string} dataType - 数据类型
   * @param {Object} handler - 处理器对象
   * @param {Function} handler.pull - 从服务器拉取数据
   * @param {Function} handler.push - 推送数据到服务器
   * @param {Function} [handler.resolveConflict] - 冲突解决函数
   * @param {Function} [handler.transform] - 数据转换函数
   */
  registerSyncHandler(dataType, handler) {
    this.syncHandlers.set(dataType, {
      pull: handler.pull,
      push: handler.push,
      resolveConflict: handler.resolveConflict || this.defaultResolveConflict.bind(this),
      transform: handler.transform || ((data) => data)
    })
    
    console.log(`[OfflineSync] 注册同步处理器: ${dataType}`)
  }
  
  /**
   * 注销同步处理器
   * 
   * @param {string} dataType - 数据类型
   */
  unregisterSyncHandler(dataType) {
    this.syncHandlers.delete(dataType)
    console.log(`[OfflineSync] 注销同步处理器: ${dataType}`)
  }
  
  /**
   * 处理API请求（队列处理器）
   * 
   * @param {Object} data - 请求数据
   * @returns {Promise<boolean>} 是否成功
   */
  async handleApiRequest(data) {
    try {
      const response = await axios({
        method: data.method || 'GET',
        url: `${this.apiBase}${data.url}`,
        data: data.body,
        params: data.params,
        headers: data.headers
      })
      
      return response.status >= 200 && response.status < 300
    } catch (error) {
      console.error('[OfflineSync] API请求失败:', error)
      throw error
    }
  }
  
  /**
   * 同步指定类型数据
   * 
   * @param {string} dataType - 数据类型
   * @param {Object} options - 同步选项
   * @param {boolean} [options.force=false] - 是否强制同步
   * @param {SyncStrategy} [options.strategy] - 冲突解决策略
   * @returns {Promise<Object>} 同步结果
   */
  async syncDataType(dataType, options = {}) {
    const handler = this.syncHandlers.get(dataType)
    
    if (!handler) {
      console.warn(`[OfflineSync] 未找到同步处理器: ${dataType}`)
      return { success: false, error: '未找到同步处理器' }
    }
    
    const result = {
      dataType,
      pulled: 0,
      pushed: 0,
      conflicts: 0,
      errors: []
    }
    
    try {
      // 1. 推送本地变更到服务器
      const localChanges = await this.getLocalChanges(dataType)
      
      if (localChanges.length > 0) {
        console.log(`[OfflineSync] 推送 ${localChanges.length} 条本地变更: ${dataType}`)
        
        for (const change of localChanges) {
          try {
            await handler.push(change)
            result.pushed++
            
            // 标记为已同步
            await this.markAsSynced(dataType, change.id)
          } catch (error) {
            console.error(`[OfflineSync] 推送失败: ${change.id}`, error)
            result.errors.push({ id: change.id, error: error.message })
          }
        }
      }
      
      // 2. 从服务器拉取数据
      console.log(`[OfflineSync] 拉取服务器数据: ${dataType}`)
      const remoteData = await handler.pull()
      
      if (remoteData && remoteData.length > 0) {
        result.pulled = remoteData.length
        
        // 3. 检测并解决冲突
        for (const remoteItem of remoteData) {
          const localItem = await this.storage.get(dataType, remoteItem.id)
          
          if (localItem && localItem.updatedAt > remoteItem.updatedAt) {
            // 检测到冲突
            result.conflicts++
            this.stats.conflicts++
            
            const strategy = options.strategy || this.defaultStrategy
            const resolved = await handler.resolveConflict(localItem, remoteItem, strategy)
            
            // 触发冲突回调
            this.onConflict?.({
              dataType,
              local: localItem,
              remote: remoteItem,
              resolved,
              strategy
            })
            
            // 保存解决后的数据
            await this.storage.set(dataType, resolved.id, resolved)
          } else {
            // 无冲突，直接更新本地
            await this.storage.set(dataType, remoteItem.id, remoteItem)
          }
        }
      }
      
      // 更新同步时间
      await this.updateLastSyncTime()
      
      console.log(`[OfflineSync] 同步完成: ${dataType}`, result)
      return { success: true, ...result }
    } catch (error) {
      console.error(`[OfflineSync] 同步失败: ${dataType}`, error)
      result.errors.push({ error: error.message })
      return { success: false, ...result }
    }
  }
  
  /**
   * 同步所有数据
   * 
   * @param {Object} options - 同步选项
   * @returns {Promise<Object>} 同步结果
   */
  async syncAll(options = {}) {
    if (this.status === SyncStatus.SYNCING) {
      console.log('[OfflineSync] 已有同步任务在运行')
      return { skipped: true }
    }
    
    this.status = SyncStatus.SYNCING
    this.syncProgress = 0
    
    this.onSyncStart?.()
    
    const results = {
      total: this.syncHandlers.size,
      success: 0,
      failed: 0,
      details: {}
    }
    
    try {
      // 先处理操作队列
      const queueResult = await this.queue.processAll()
      console.log('[OfflineSync] 队列处理结果:', queueResult)
      
      // 同步各类型数据
      let completed = 0
      for (const [dataType] of this.syncHandlers) {
        const result = await this.syncDataType(dataType, options)
        results.details[dataType] = result
        
        if (result.success) {
          results.success++
        } else {
          results.failed++
        }
        
        completed++
        this.syncProgress = (completed / this.syncHandlers.size) * 100
        this.onProgress?.({
          progress: this.syncProgress,
          current: dataType,
          completed,
          total: this.syncHandlers.size
        })
      }
      
      this.status = results.failed > 0 ? SyncStatus.PARTIAL : SyncStatus.SYNCED
      this.stats.totalSyncs++
      this.stats.successfulSyncs++
      
      this.onSyncComplete?.(results)
      
      console.log('[OfflineSync] 全部同步完成:', results)
      return results
    } catch (error) {
      this.status = SyncStatus.FAILED
      this.stats.totalSyncs++
      this.stats.failedSyncs++
      this.stats.lastError = error.message
      
      this.onSyncError?.(error)
      
      console.error('[OfflineSync] 同步失败:', error)
      return { success: false, error: error.message }
    }
  }
  
  /**
   * 获取本地变更
   * 
   * @param {string} dataType - 数据类型
   * @returns {Promise<Array<Object>>} 变更列表
   */
  async getLocalChanges(dataType) {
    const allData = await this.storage.getAll(dataType)
    
    // 过滤出未同步的数据
    return allData.filter(item => {
      // 如果没有同步标记，或者在上次同步后更新过
      return !item.syncedAt || !this.lastSyncTime || item.updatedAt > this.lastSyncTime
    })
  }
  
  /**
   * 标记数据为已同步
   * 
   * @param {string} dataType - 数据类型
   * @param {string|number} id - 数据ID
   * @returns {Promise<void>}
   */
  async markAsSynced(dataType, id) {
    const item = await this.storage.get(dataType, id)
    if (item) {
      await this.storage.set(dataType, id, {
        ...item,
        syncedAt: Date.now()
      })
    }
  }
  
  /**
   * 更新最后同步时间
   * 
   * @returns {Promise<void>}
   */
  async updateLastSyncTime() {
    this.lastSyncTime = Date.now()
    await this.storage.set('cacheData', 'lastSyncTime', { value: this.lastSyncTime })
  }
  
  /**
   * 默认冲突解决函数
   * 
   * @param {Object} local - 本地数据
   * @param {Object} remote - 远程数据
   * @param {SyncStrategy} strategy - 解决策略
   * @returns {Object} 解决后的数据
   */
  defaultResolveConflict(local, remote, strategy) {
    switch (strategy) {
      case SyncStrategy.SERVER_WINS:
        return { ...remote, _conflictResolved: true }
      
      case SyncStrategy.LOCAL_WINS:
        return { ...local, _conflictResolved: true }
      
      case SyncStrategy.MERGE:
        // 简单合并：优先使用较新的数据
        return local.updatedAt > remote.updatedAt
          ? { ...remote, ...local, _conflictResolved: true }
          : { ...local, ...remote, _conflictResolved: true }
      
      default:
        return remote
    }
  }
  
  /**
   * 处理网络上线事件
   * 
   * @internal 内部方法，不对外暴露
   */
  handleOnline() {
    console.log('[OfflineSync] 网络已恢复，开始同步')
    
    // 延迟一下再同步，确保网络稳定
    setTimeout(() => {
      this.syncAll().catch(err => {
        console.error('[OfflineSync] 自动同步失败:', err)
      })
    }, 1000)
    
    // 启动自动同步
    if (this.enableAutoSync) {
      this.startAutoSync()
    }
  }
  
  /**
   * 处理网络离线事件
   * 
   * @internal 内部方法，不对外暴露
   */
  handleOffline() {
    console.log('[OfflineSync] 网络已断开')
    this.stopAutoSync()
  }
  
  /**
   * 启动自动同步
   * 
   * @internal 内部方法，不对外暴露
   */
  startAutoSync() {
    this.stopAutoSync()
    
    this.syncTimer = setInterval(() => {
      if (navigator.onLine && this.status !== SyncStatus.SYNCING) {
        this.syncAll().catch(err => {
          console.error('[OfflineSync] 自动同步失败:', err)
        })
      }
    }, this.syncInterval)
    
    console.log(`[OfflineSync] 自动同步已启动，间隔: ${this.syncInterval}ms`)
  }
  
  /**
   * 停止自动同步
   */
  stopAutoSync() {
    if (this.syncTimer) {
      clearInterval(this.syncTimer)
      this.syncTimer = null
      console.log('[OfflineSync] 自动同步已停止')
    }
  }
  
  /**
   * 获取同步状态
   * 
   * @returns {Object} 同步状态
   */
  getSyncStatus() {
    return {
      status: this.status,
      lastSyncTime: this.lastSyncTime,
      progress: this.syncProgress,
      stats: { ...this.stats }
    }
  }
  
  /**
   * 添加API请求到队列（离线时使用）
   * 
   * @param {Object} request - 请求对象
   * @param {string} request.url - 请求URL
   * @param {string} [request.method='GET'] - HTTP方法
   * @param {any} [request.body] - 请求体
   * @param {Object} [request.params] - URL参数
   * @param {Object} [request.headers] - 请求头
   * @param {number} [priority=OperationPriority.NORMAL] - 优先级
   * @returns {Promise<number>} 操作ID
   */
  async enqueueRequest(request, priority = OperationPriority.NORMAL) {
    return this.queue.enqueue({
      type: 'api_request',
      data: request,
      priority
    })
  }
  
  /**
   * 智能请求（在线时直接发送，离线时入队）
   * 
   * @param {Object} request - 请求对象
   * @param {number} [priority=OperationPriority.NORMAL] - 优先级
   * @returns {Promise<Object>} 响应或队列ID
   */
  async smartRequest(request, priority = OperationPriority.NORMAL) {
    if (navigator.onLine) {
      try {
        const response = await axios({
          method: request.method || 'GET',
          url: `${this.apiBase}${request.url}`,
          data: request.body,
          params: request.params,
          headers: request.headers
        })
        
        return {
          online: true,
          success: true,
          data: response.data
        }
      } catch (error) {
        // 如果是网络错误，入队
        if (!navigator.onLine || error.message === 'Network Error') {
          const id = await this.enqueueRequest(request, priority)
          return {
            online: false,
            queued: true,
            queueId: id
          }
        }
        
        throw error
      }
    } else {
      // 离线，入队
      const id = await this.enqueueRequest(request, priority)
      return {
        online: false,
        queued: true,
        queueId: id
      }
    }
  }
  
  /**
   * 销毁同步管理器
   */
  destroy() {
    this.stopAutoSync()
    window.removeEventListener('online', this.handleOnline.bind(this))
    window.removeEventListener('offline', this.handleOffline.bind(this))
    this.syncHandlers.clear()
    this.onSyncStart = null
    this.onSyncComplete = null
    this.onSyncError = null
    this.onProgress = null
    this.onConflict = null
  }
}

// 创建全局单例实例
let globalSync = null

/**
 * 获取全局同步实例
 * 
 * @param {Object} options - 配置选项
 * @returns {OfflineSync} 同步实例
 */
export function getOfflineSync(options = {}) {
  if (!globalSync) {
    globalSync = new OfflineSync(options)
  }
  return globalSync
}

/**
 * 初始化全局同步实例
 * 
 * @param {Object} options - 配置选项
 * @returns {Promise<OfflineSync>} 同步实例
 */
export async function initOfflineSync(options = {}) {
  const sync = getOfflineSync(options)
  if (!sync.storage.db) {
    await sync.init()
  }
  return sync
}
