/**
 * @file offlineStorage.js
 * @path src/utils/
 * @description IndexedDB数据缓存模块，提供离线数据存储、查询、过期管理等功能
 * @author Frontend Engineer Agent
 * @date 2026-03-07
 * @dependencies idb
 */

/**
 * IndexedDB数据缓存管理器
 * 
 * @description 封装IndexedDB操作，提供统一的数据缓存接口
 * 支持数据过期、自动清理、批量操作等高级功能
 * 
 * @example
 * ```javascript
 * const storage = new OfflineStorage()
 * await storage.init()
 * 
 * // 存储数据
 * await storage.set('experiments', 'exp_001', { name: '实验1', data: [...] })
 * 
 * // 获取数据
 * const experiment = await storage.get('experiments', 'exp_001')
 * 
 * // 查询数据
 * const allExperiments = await storage.getAll('experiments')
 * 
 * // 删除数据
 * await storage.delete('experiments', 'exp_001')
 * ```
 */
export class OfflineStorage {
  /**
   * 构造函数
   * 
   * @param {Object} options - 配置选项
   * @param {string} [options.dbName='CAUC_SEP_Offline'] - 数据库名称
   * @param {number} [options.dbVersion=1] - 数据库版本
   * @param {number} [options.defaultTTL=86400000] - 默认过期时间（毫秒），默认24小时
   * @param {boolean} [options.enableAutoCleanup=true] - 是否启用自动清理过期数据
   * @param {number} [options.cleanupInterval=3600000] - 自动清理间隔（毫秒），默认1小时
   */
  constructor(options = {}) {
    this.dbName = options.dbName || 'CAUC_SEP_Offline'
    this.dbVersion = options.dbVersion || 1
    this.defaultTTL = options.defaultTTL || 86400000 // 24小时
    this.enableAutoCleanup = options.enableAutoCleanup !== false
    this.cleanupInterval = options.cleanupInterval || 3600000 // 1小时
    
    this.db = null
    this.cleanupTimer = null
    
    // 数据库存储配置
    this.stores = {
      experiments: { keyPath: 'id', autoIncrement: false },
      deviceStates: { keyPath: 'id', autoIncrement: false },
      operationQueue: { keyPath: 'id', autoIncrement: true },
      cacheData: { keyPath: 'key', autoIncrement: false },
      userData: { keyPath: 'id', autoIncrement: false },
      analysisResults: { keyPath: 'id', autoIncrement: false },
      configHistory: { keyPath: 'id', autoIncrement: true }
    }
  }
  
  /**
   * 初始化数据库
   * 
   * @returns {Promise<void>}
   */
  async init() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion)
      
      request.onerror = () => {
        console.error('[OfflineStorage] 数据库打开失败:', request.error)
        reject(request.error)
      }
      
      request.onsuccess = () => {
        this.db = request.result
        console.log('[OfflineStorage] 数据库初始化成功')
        
        // 启动自动清理
        if (this.enableAutoCleanup) {
          this.startAutoCleanup()
        }
        
        resolve()
      }
      
      request.onupgradeneeded = (event) => {
        const db = event.target.result
        
        // 创建所有存储对象
        for (const [storeName, config] of Object.entries(this.stores)) {
          if (!db.objectStoreNames.contains(storeName)) {
            const store = db.createObjectStore(storeName, {
              keyPath: config.keyPath,
              autoIncrement: config.autoIncrement
            })
            
            // 创建索引
            if (storeName === 'cacheData') {
              store.createIndex('expiresAt', 'expiresAt', { unique: false })
              store.createIndex('category', 'category', { unique: false })
            } else if (storeName === 'operationQueue') {
              store.createIndex('timestamp', 'timestamp', { unique: false })
              store.createIndex('status', 'status', { unique: false })
            } else if (storeName === 'experiments') {
              store.createIndex('createdAt', 'createdAt', { unique: false })
              store.createIndex('status', 'status', { unique: false })
            }
            
            console.log(`[OfflineStorage] 创建存储对象: ${storeName}`)
          }
        }
      }
    })
  }
  
  /**
   * 存储数据
   * 
   * @param {string} storeName - 存储对象名称
   * @param {string|number} key - 数据键
   * @param {any} value - 数据值
   * @param {Object} options - 可选配置
   * @param {number} [options.ttl] - 过期时间（毫秒）
   * @param {string} [options.category] - 数据分类
   * @returns {Promise<void>}
   */
  async set(storeName, key, value, options = {}) {
    if (!this.db) {
      throw new Error('数据库未初始化')
    }
    
    const ttl = options.ttl !== undefined ? options.ttl : this.defaultTTL
    const now = Date.now()
    
    const data = {
      ...value,
      id: key,
      key: key,
      category: options.category || 'default',
      createdAt: now,
      expiresAt: ttl > 0 ? now + ttl : null
    }
    
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([storeName], 'readwrite')
      const store = transaction.objectStore(storeName)
      const request = store.put(data)
      
      request.onsuccess = () => {
        console.log(`[OfflineStorage] 数据已存储: ${storeName}/${key}`)
        resolve()
      }
      
      request.onerror = () => {
        console.error(`[OfflineStorage] 数据存储失败: ${storeName}/${key}`, request.error)
        reject(request.error)
      }
    })
  }
  
  /**
   * 获取数据
   * 
   * @param {string} storeName - 存储对象名称
   * @param {string|number} key - 数据键
   * @returns {Promise<any|null>} 数据值，不存在或已过期返回null
   */
  async get(storeName, key) {
    if (!this.db) {
      throw new Error('数据库未初始化')
    }
    
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([storeName], 'readonly')
      const store = transaction.objectStore(storeName)
      const request = store.get(key)
      
      request.onsuccess = () => {
        const data = request.result
        
        if (!data) {
          resolve(null)
          return
        }
        
        // 检查是否过期
        if (data.expiresAt && Date.now() > data.expiresAt) {
          // 异步删除过期数据
          this.delete(storeName, key).catch(err => {
            console.warn(`[OfflineStorage] 删除过期数据失败: ${key}`, err)
          })
          resolve(null)
          return
        }
        
        resolve(data)
      }
      
      request.onerror = () => {
        console.error(`[OfflineStorage] 数据获取失败: ${storeName}/${key}`, request.error)
        reject(request.error)
      }
    })
  }
  
  /**
   * 获取所有数据
   * 
   * @param {string} storeName - 存储对象名称
   * @param {Object} options - 查询选项
   * @param {boolean} [options.excludeExpired=true] - 是否排除过期数据
   * @returns {Promise<Array<any>>} 数据数组
   */
  async getAll(storeName, options = {}) {
    if (!this.db) {
      throw new Error('数据库未初始化')
    }
    
    const excludeExpired = options.excludeExpired !== false
    
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([storeName], 'readonly')
      const store = transaction.objectStore(storeName)
      const request = store.getAll()
      
      request.onsuccess = () => {
        let data = request.result || []
        
        // 过滤过期数据
        if (excludeExpired) {
          const now = Date.now()
          data = data.filter(item => !item.expiresAt || item.expiresAt > now)
        }
        
        resolve(data)
      }
      
      request.onerror = () => {
        console.error(`[OfflineStorage] 数据获取失败: ${storeName}`, request.error)
        reject(request.error)
      }
    })
  }
  
  /**
   * 删除数据
   * 
   * @param {string} storeName - 存储对象名称
   * @param {string|number} key - 数据键
   * @returns {Promise<void>}
   */
  async delete(storeName, key) {
    if (!this.db) {
      throw new Error('数据库未初始化')
    }
    
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([storeName], 'readwrite')
      const store = transaction.objectStore(storeName)
      const request = store.delete(key)
      
      request.onsuccess = () => {
        console.log(`[OfflineStorage] 数据已删除: ${storeName}/${key}`)
        resolve()
      }
      
      request.onerror = () => {
        console.error(`[OfflineStorage] 数据删除失败: ${storeName}/${key}`, request.error)
        reject(request.error)
      }
    })
  }
  
  /**
   * 清空存储对象
   * 
   * @param {string} storeName - 存储对象名称
   * @returns {Promise<void>}
   */
  async clear(storeName) {
    if (!this.db) {
      throw new Error('数据库未初始化')
    }
    
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([storeName], 'readwrite')
      const store = transaction.objectStore(storeName)
      const request = store.clear()
      
      request.onsuccess = () => {
        console.log(`[OfflineStorage] 存储对象已清空: ${storeName}`)
        resolve()
      }
      
      request.onerror = () => {
        console.error(`[OfflineStorage] 存储对象清空失败: ${storeName}`, request.error)
        reject(request.error)
      }
    })
  }
  
  /**
   * 批量存储数据
   * 
   * @param {string} storeName - 存储对象名称
   * @param {Array<{key: string|number, value: any, options?: Object}>} items - 数据项数组
   * @returns {Promise<void>}
   */
  async batchSet(storeName, items) {
    if (!this.db) {
      throw new Error('数据库未初始化')
    }
    
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([storeName], 'readwrite')
      const store = transaction.objectStore(storeName)
      const now = Date.now()
      
      let completed = 0
      const total = items.length
      
      items.forEach(item => {
        const ttl = item.options?.ttl !== undefined ? item.options.ttl : this.defaultTTL
        
        const data = {
          ...item.value,
          id: item.key,
          key: item.key,
          category: item.options?.category || 'default',
          createdAt: now,
          expiresAt: ttl > 0 ? now + ttl : null
        }
        
        const request = store.put(data)
        
        request.onsuccess = () => {
          completed++
          if (completed === total) {
            console.log(`[OfflineStorage] 批量存储完成: ${storeName}, ${total}条`)
            resolve()
          }
        }
        
        request.onerror = () => {
          console.error(`[OfflineStorage] 批量存储失败: ${storeName}/${item.key}`, request.error)
          reject(request.error)
        }
      })
      
      if (total === 0) {
        resolve()
      }
    })
  }
  
  /**
   * 按索引查询数据
   * 
   * @param {string} storeName - 存储对象名称
   * @param {string} indexName - 索引名称
   * @param {any} value - 索引值
   * @returns {Promise<Array<any>>} 数据数组
   */
  async getByIndex(storeName, indexName, value) {
    if (!this.db) {
      throw new Error('数据库未初始化')
    }
    
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([storeName], 'readonly')
      const store = transaction.objectStore(storeName)
      const index = store.index(indexName)
      const request = index.getAll(value)
      
      request.onsuccess = () => {
        resolve(request.result || [])
      }
      
      request.onerror = () => {
        console.error(`[OfflineStorage] 索引查询失败: ${storeName}/${indexName}`, request.error)
        reject(request.error)
      }
    })
  }
  
  /**
   * 清理过期数据
   * 
   * @returns {Promise<number>} 清理的数据条数
   */
  async cleanupExpired() {
    if (!this.db) {
      throw new Error('数据库未初始化')
    }
    
    const now = Date.now()
    let totalCleaned = 0
    
    for (const storeName of Object.keys(this.stores)) {
      try {
        const transaction = this.db.transaction([storeName], 'readwrite')
        const store = transaction.objectStore(storeName)
        
        // 检查是否有expiresAt索引
        if (store.indexNames.contains('expiresAt')) {
          const index = store.index('expiresAt')
          const range = IDBKeyRange.upperBound(now)
          const request = index.openCursor(range)
          
          await new Promise((resolve, reject) => {
            request.onsuccess = (event) => {
              const cursor = event.target.result
              if (cursor) {
                cursor.delete()
                totalCleaned++
                cursor.continue()
              } else {
                resolve()
              }
            }
            
            request.onerror = () => {
              reject(request.error)
            }
          })
        }
      } catch (error) {
        console.warn(`[OfflineStorage] 清理过期数据失败: ${storeName}`, error)
      }
    }
    
    if (totalCleaned > 0) {
      console.log(`[OfflineStorage] 已清理 ${totalCleaned} 条过期数据`)
    }
    
    return totalCleaned
  }
  
  /**
   * 启动自动清理
   * 
   * @internal 内部方法，不对外暴露
   */
  startAutoCleanup() {
    this.stopAutoCleanup()
    
    this.cleanupTimer = setInterval(() => {
      this.cleanupExpired().catch(err => {
        console.error('[OfflineStorage] 自动清理失败:', err)
      })
    }, this.cleanupInterval)
    
    console.log(`[OfflineStorage] 自动清理已启动，间隔: ${this.cleanupInterval}ms`)
  }
  
  /**
   * 停止自动清理
   */
  stopAutoCleanup() {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer)
      this.cleanupTimer = null
      console.log('[OfflineStorage] 自动清理已停止')
    }
  }
  
  /**
   * 获取存储统计信息
   * 
   * @returns {Promise<Object>} 统计信息
   */
  async getStats() {
    if (!this.db) {
      throw new Error('数据库未初始化')
    }
    
    const stats = {
      stores: {},
      totalRecords: 0,
      totalSize: 0
    }
    
    for (const storeName of Object.keys(this.stores)) {
      const count = await this.count(storeName)
      stats.stores[storeName] = count
      stats.totalRecords += count
    }
    
    // 估算存储大小（如果支持）
    if (navigator.storage && navigator.storage.estimate) {
      const estimate = await navigator.storage.estimate()
      stats.totalSize = estimate.usage || 0
      stats.quota = estimate.quota || 0
    }
    
    return stats
  }
  
  /**
   * 获取记录数量
   * 
   * @param {string} storeName - 存储对象名称
   * @returns {Promise<number>} 记录数量
   */
  async count(storeName) {
    if (!this.db) {
      throw new Error('数据库未初始化')
    }
    
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([storeName], 'readonly')
      const store = transaction.objectStore(storeName)
      const request = store.count()
      
      request.onsuccess = () => {
        resolve(request.result)
      }
      
      request.onerror = () => {
        reject(request.error)
      }
    })
  }
  
  /**
   * 关闭数据库连接
   */
  close() {
    this.stopAutoCleanup()
    
    if (this.db) {
      this.db.close()
      this.db = null
      console.log('[OfflineStorage] 数据库连接已关闭')
    }
  }
  
  /**
   * 删除整个数据库
   * 
   * @returns {Promise<void>}
   */
  async deleteDatabase() {
    this.close()
    
    return new Promise((resolve, reject) => {
      const request = indexedDB.deleteDatabase(this.dbName)
      
      request.onsuccess = () => {
        console.log(`[OfflineStorage] 数据库已删除: ${this.dbName}`)
        resolve()
      }
      
      request.onerror = () => {
        console.error(`[OfflineStorage] 数据库删除失败: ${this.dbName}`, request.error)
        reject(request.error)
      }
    })
  }
}

// 创建全局单例实例
let globalStorage = null

/**
 * 获取全局存储实例
 * 
 * @param {Object} options - 配置选项
 * @returns {OfflineStorage} 存储实例
 */
export function getOfflineStorage(options = {}) {
  if (!globalStorage) {
    globalStorage = new OfflineStorage(options)
  }
  return globalStorage
}

/**
 * 初始化全局存储实例
 * 
 * @param {Object} options - 配置选项
 * @returns {Promise<OfflineStorage>} 存储实例
 */
export async function initOfflineStorage(options = {}) {
  const storage = getOfflineStorage(options)
  if (!storage.db) {
    await storage.init()
  }
  return storage
}
