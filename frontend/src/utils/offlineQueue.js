/**
 * @file offlineQueue.js
 * @path src/utils/
 * @description 离线操作队列模块，管理离线时的操作请求，支持优先级、重试、持久化
 * @author Frontend Engineer Agent
 * @date 2026-03-07
 * @dependencies ./offlineStorage
 */

import { getOfflineStorage } from './offlineStorage'

/**
 * 操作状态枚举
 * 
 * @readonly
 * @enum {string}
 */
export const OperationStatus = {
  /** 待处理 */
  PENDING: 'pending',
  /** 处理中 */
  PROCESSING: 'processing',
  /** 已完成 */
  COMPLETED: 'completed',
  /** 失败 */
  FAILED: 'failed',
  /** 已取消 */
  CANCELLED: 'cancelled'
}

/**
 * 操作优先级枚举
 * 
 * @readonly
 * @enum {number}
 */
export const OperationPriority = {
  /** 低优先级 */
  LOW: 0,
  /** 普通优先级 */
  NORMAL: 1,
  /** 高优先级 */
  HIGH: 2,
  /** 紧急优先级 */
  URGENT: 3
}

/**
 * 离线操作队列管理器
 * 
 * @description 管理离线时的操作请求，支持优先级队列、自动重试、持久化存储
 * 
 * @example
 * ```javascript
 * const queue = new OfflineQueue()
 * await queue.init()
 * 
 * // 添加操作到队列
 * await queue.enqueue({
 *   type: 'api_request',
 *   data: { url: '/api/experiments', method: 'POST', body: {...} },
 *   priority: OperationPriority.HIGH
 * })
 * 
 * // 处理队列
 * await queue.processAll()
 * 
 * // 获取队列状态
 * const stats = queue.getStats()
 * ```
 */
export class OfflineQueue {
  /**
   * 构造函数
   * 
   * @param {Object} options - 配置选项
   * @param {number} [options.maxRetries=3] - 最大重试次数
   * @param {number} [options.retryDelay=5000] - 重试延迟（毫秒）
   * @param {number} [options.maxQueueSize=100] - 最大队列大小
   * @param {number} [options.processBatchSize=10] - 批量处理大小
   * @param {number} [options.processInterval=30000] - 自动处理间隔（毫秒）
   * @param {boolean} [options.enableAutoProcess=true] - 是否启用自动处理
   */
  constructor(options = {}) {
    this.maxRetries = options.maxRetries || 3
    this.retryDelay = options.retryDelay || 5000
    this.maxQueueSize = options.maxQueueSize || 100
    this.processBatchSize = options.processBatchSize || 10
    this.processInterval = options.processInterval || 30000
    this.enableAutoProcess = options.enableAutoProcess !== false
    
    this.storage = getOfflineStorage()
    this.processTimer = null
    this.isProcessing = false
    
    // 操作处理器映射
    this.handlers = new Map()
    
    // 队列变更回调
    this.onQueueChange = null
    this.onOperationComplete = null
    this.onOperationFailed = null
  }
  
  /**
   * 初始化队列
   * 
   * @returns {Promise<void>}
   */
  async init() {
    // 确保存储已初始化
    if (!this.storage.db) {
      await this.storage.init()
    }
    
    // 加载未处理的操作
    const pendingOps = await this.storage.getByIndex('operationQueue', 'status', OperationStatus.PENDING)
    console.log(`[OfflineQueue] 加载了 ${pendingOps.length} 个待处理操作`)
    
    // 启动自动处理
    if (this.enableAutoProcess) {
      this.startAutoProcess()
    }
  }
  
  /**
   * 注册操作处理器
   * 
   * @param {string} type - 操作类型
   * @param {Function} handler - 处理函数，返回Promise<boolean>
   */
  registerHandler(type, handler) {
    this.handlers.set(type, handler)
    console.log(`[OfflineQueue] 注册处理器: ${type}`)
  }
  
  /**
   * 注销操作处理器
   * 
   * @param {string} type - 操作类型
   */
  unregisterHandler(type) {
    this.handlers.delete(type)
    console.log(`[OfflineQueue] 注销处理器: ${type}`)
  }
  
  /**
   * 添加操作到队列
   * 
   * @param {Object} operation - 操作对象
   * @param {string} operation.type - 操作类型
   * @param {any} operation.data - 操作数据
   * @param {number} [operation.priority=OperationPriority.NORMAL] - 优先级
   * @param {Object} [operation.metadata] - 元数据
   * @returns {Promise<number>} 操作ID
   */
  async enqueue(operation) {
    // 检查队列大小
    const stats = await this.getStats()
    if (stats.pending >= this.maxQueueSize) {
      throw new Error(`队列已满，最大容量: ${this.maxQueueSize}`)
    }
    
    const now = Date.now()
    const op = {
      ...operation,
      status: OperationStatus.PENDING,
      priority: operation.priority || OperationPriority.NORMAL,
      retryCount: 0,
      timestamp: now,
      createdAt: now,
      updatedAt: now,
      metadata: operation.metadata || {}
    }
    
    // 存储到IndexedDB
    const transaction = this.storage.db.transaction(['operationQueue'], 'readwrite')
    const store = transaction.objectStore('operationQueue')
    
    return new Promise((resolve, reject) => {
      const request = store.add(op)
      
      request.onsuccess = () => {
        const id = request.result
        console.log(`[OfflineQueue] 操作已入队: ${op.type}, ID: ${id}`)
        
        // 触发队列变更回调
        this.onQueueChange?.({
          action: 'enqueue',
          operation: { ...op, id }
        })
        
        resolve(id)
      }
      
      request.onerror = () => {
        console.error('[OfflineQueue] 操作入队失败:', request.error)
        reject(request.error)
      }
    })
  }
  
  /**
   * 批量添加操作
   * 
   * @param {Array<Object>} operations - 操作数组
   * @returns {Promise<Array<number>>} 操作ID数组
   */
  async enqueueBatch(operations) {
    const ids = []
    for (const op of operations) {
      const id = await this.enqueue(op)
      ids.push(id)
    }
    return ids
  }
  
  /**
   * 处理单个操作
   * 
   * @param {Object} operation - 操作对象
   * @returns {Promise<boolean>} 是否成功
   */
  async processOperation(operation) {
    const handler = this.handlers.get(operation.type)
    
    if (!handler) {
      console.warn(`[OfflineQueue] 未找到处理器: ${operation.type}`)
      await this.updateOperation(operation.id, {
        status: OperationStatus.FAILED,
        error: `未找到处理器: ${operation.type}`,
        updatedAt: Date.now()
      })
      return false
    }
    
    try {
      // 更新状态为处理中
      await this.updateOperation(operation.id, {
        status: OperationStatus.PROCESSING,
        updatedAt: Date.now()
      })
      
      // 执行处理
      const success = await handler(operation.data, operation)
      
      if (success) {
        // 标记为完成
        await this.updateOperation(operation.id, {
          status: OperationStatus.COMPLETED,
          completedAt: Date.now(),
          updatedAt: Date.now()
        })
        
        // 触发完成回调
        this.onOperationComplete?.(operation)
        
        console.log(`[OfflineQueue] 操作完成: ${operation.type}, ID: ${operation.id}`)
        return true
      } else {
        throw new Error('处理器返回失败')
      }
    } catch (error) {
      console.error(`[OfflineQueue] 操作处理失败: ${operation.type}, ID: ${operation.id}`, error)
      
      // 更新重试次数
      const retryCount = operation.retryCount + 1
      
      if (retryCount >= this.maxRetries) {
        // 达到最大重试次数，标记为失败
        await this.updateOperation(operation.id, {
          status: OperationStatus.FAILED,
          retryCount,
          error: error.message,
          updatedAt: Date.now()
        })
        
        // 触发失败回调
        this.onOperationFailed?.(operation, error)
      } else {
        // 更新重试次数，保持待处理状态
        await this.updateOperation(operation.id, {
          retryCount,
          lastError: error.message,
          nextRetryAt: Date.now() + this.retryDelay * retryCount,
          updatedAt: Date.now()
        })
      }
      
      return false
    }
  }
  
  /**
   * 处理所有待处理操作
   * 
   * @returns {Promise<Object>} 处理结果统计
   */
  async processAll() {
    if (this.isProcessing) {
      console.log('[OfflineQueue] 已有处理任务在运行')
      return { skipped: true }
    }
    
    this.isProcessing = true
    
    try {
      // 获取所有待处理操作
      let pendingOps = await this.storage.getByIndex('operationQueue', 'status', OperationStatus.PENDING)
      
      // 过滤掉还在重试等待期的操作
      const now = Date.now()
      pendingOps = pendingOps.filter(op => !op.nextRetryAt || op.nextRetryAt <= now)
      
      // 按优先级排序（高优先级在前）
      pendingOps.sort((a, b) => b.priority - a.priority)
      
      // 限制批量处理数量
      const toProcess = pendingOps.slice(0, this.processBatchSize)
      
      const stats = {
        total: toProcess.length,
        success: 0,
        failed: 0,
        pending: pendingOps.length - toProcess.length
      }
      
      console.log(`[OfflineQueue] 开始处理 ${toProcess.length} 个操作`)
      
      for (const op of toProcess) {
        const success = await this.processOperation(op)
        if (success) {
          stats.success++
        } else {
          stats.failed++
        }
      }
      
      console.log('[OfflineQueue] 处理完成:', stats)
      return stats
    } finally {
      this.isProcessing = false
    }
  }
  
  /**
   * 更新操作
   * 
   * @param {number} id - 操作ID
   * @param {Object} updates - 更新内容
   * @returns {Promise<void>}
   */
  async updateOperation(id, updates) {
    const transaction = this.storage.db.transaction(['operationQueue'], 'readwrite')
    const store = transaction.objectStore('operationQueue')
    
    return new Promise((resolve, reject) => {
      const getRequest = store.get(id)
      
      getRequest.onsuccess = () => {
        const operation = getRequest.result
        if (!operation) {
          reject(new Error(`操作不存在: ${id}`))
          return
        }
        
        const updated = { ...operation, ...updates }
        const putRequest = store.put(updated)
        
        putRequest.onsuccess = () => {
          // 触发队列变更回调
          this.onQueueChange?.({
            action: 'update',
            operation: updated
          })
          resolve()
        }
        
        putRequest.onerror = () => {
          reject(putRequest.error)
        }
      }
      
      getRequest.onerror = () => {
        reject(getRequest.error)
      }
    })
  }
  
  /**
   * 取消操作
   * 
   * @param {number} id - 操作ID
   * @returns {Promise<void>}
   */
  async cancelOperation(id) {
    await this.updateOperation(id, {
      status: OperationStatus.CANCELLED,
      cancelledAt: Date.now(),
      updatedAt: Date.now()
    })
    
    console.log(`[OfflineQueue] 操作已取消: ${id}`)
  }
  
  /**
   * 重试失败的操作
   * 
   * @param {number} id - 操作ID
   * @returns {Promise<void>}
   */
  async retryOperation(id) {
    await this.updateOperation(id, {
      status: OperationStatus.PENDING,
      retryCount: 0,
      error: null,
      nextRetryAt: null,
      updatedAt: Date.now()
    })
    
    console.log(`[OfflineQueue] 操作已重新入队: ${id}`)
  }
  
  /**
   * 删除操作
   * 
   * @param {number} id - 操作ID
   * @returns {Promise<void>}
   */
  async deleteOperation(id) {
    await this.storage.delete('operationQueue', id)
    
    this.onQueueChange?.({
      action: 'delete',
      operationId: id
    })
    
    console.log(`[OfflineQueue] 操作已删除: ${id}`)
  }
  
  /**
   * 清理已完成的操作
   * 
   * @param {number} [olderThan=86400000] - 清理多久前的操作（毫秒），默认24小时
   * @returns {Promise<number>} 清理数量
   */
  async cleanupCompleted(olderThan = 86400000) {
    const completedOps = await this.storage.getByIndex('operationQueue', 'status', OperationStatus.COMPLETED)
    const cutoff = Date.now() - olderThan
    
    let cleaned = 0
    for (const op of completedOps) {
      if (op.completedAt && op.completedAt < cutoff) {
        await this.deleteOperation(op.id)
        cleaned++
      }
    }
    
    if (cleaned > 0) {
      console.log(`[OfflineQueue] 已清理 ${cleaned} 个已完成操作`)
    }
    
    return cleaned
  }
  
  /**
   * 获取队列统计信息
   * 
   * @returns {Promise<Object>} 统计信息
   */
  async getStats() {
    const all = await this.storage.getAll('operationQueue')
    
    const stats = {
      total: all.length,
      pending: 0,
      processing: 0,
      completed: 0,
      failed: 0,
      cancelled: 0,
      byPriority: {
        urgent: 0,
        high: 0,
        normal: 0,
        low: 0
      },
      byType: {}
    }
    
    for (const op of all) {
      // 按状态统计
      switch (op.status) {
        case OperationStatus.PENDING:
          stats.pending++
          break
        case OperationStatus.PROCESSING:
          stats.processing++
          break
        case OperationStatus.COMPLETED:
          stats.completed++
          break
        case OperationStatus.FAILED:
          stats.failed++
          break
        case OperationStatus.CANCELLED:
          stats.cancelled++
          break
      }
      
      // 按优先级统计
      switch (op.priority) {
        case OperationPriority.URGENT:
          stats.byPriority.urgent++
          break
        case OperationPriority.HIGH:
          stats.byPriority.high++
          break
        case OperationPriority.NORMAL:
          stats.byPriority.normal++
          break
        case OperationPriority.LOW:
          stats.byPriority.low++
          break
      }
      
      // 按类型统计
      if (!stats.byType[op.type]) {
        stats.byType[op.type] = 0
      }
      stats.byType[op.type]++
    }
    
    return stats
  }
  
  /**
   * 获取操作列表
   * 
   * @param {Object} options - 查询选项
   * @param {string} [options.status] - 按状态过滤
   * @param {number} [options.limit] - 限制数量
   * @returns {Promise<Array<Object>>} 操作列表
   */
  async getOperations(options = {}) {
    let operations = await this.storage.getAll('operationQueue')
    
    // 按状态过滤
    if (options.status) {
      operations = operations.filter(op => op.status === options.status)
    }
    
    // 按时间倒序排序
    operations.sort((a, b) => b.timestamp - a.timestamp)
    
    // 限制数量
    if (options.limit) {
      operations = operations.slice(0, options.limit)
    }
    
    return operations
  }
  
  /**
   * 启动自动处理
   * 
   * @internal 内部方法，不对外暴露
   */
  startAutoProcess() {
    this.stopAutoProcess()
    
    this.processTimer = setInterval(() => {
      this.processAll().catch(err => {
        console.error('[OfflineQueue] 自动处理失败:', err)
      })
    }, this.processInterval)
    
    console.log(`[OfflineQueue] 自动处理已启动，间隔: ${this.processInterval}ms`)
  }
  
  /**
   * 停止自动处理
   */
  stopAutoProcess() {
    if (this.processTimer) {
      clearInterval(this.processTimer)
      this.processTimer = null
      console.log('[OfflineQueue] 自动处理已停止')
    }
  }
  
  /**
   * 清空队列
   * 
   * @returns {Promise<void>}
   */
  async clear() {
    await this.storage.clear('operationQueue')
    
    this.onQueueChange?.({
      action: 'clear'
    })
    
    console.log('[OfflineQueue] 队列已清空')
  }
  
  /**
   * 销毁队列
   */
  destroy() {
    this.stopAutoProcess()
    this.handlers.clear()
    this.onQueueChange = null
    this.onOperationComplete = null
    this.onOperationFailed = null
  }
}

// 创建全局单例实例
let globalQueue = null

/**
 * 获取全局队列实例
 * 
 * @param {Object} options - 配置选项
 * @returns {OfflineQueue} 队列实例
 */
export function getOfflineQueue(options = {}) {
  if (!globalQueue) {
    globalQueue = new OfflineQueue(options)
  }
  return globalQueue
}

/**
 * 初始化全局队列实例
 * 
 * @param {Object} options - 配置选项
 * @returns {Promise<OfflineQueue>} 队列实例
 */
export async function initOfflineQueue(options = {}) {
  const queue = getOfflineQueue(options)
  if (!queue.storage.db) {
    await queue.init()
  }
  return queue
}
