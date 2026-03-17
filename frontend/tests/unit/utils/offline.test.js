/**
 * @file offline.test.js
 * @path src/utils/__tests__/
 * @description 离线功能测试文件，测试IndexedDB存储、操作队列、数据同步等功能
 * @author Frontend Engineer Agent
 * @date 2026-03-07
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { OfflineStorage, getOfflineStorage, initOfflineStorage } from '@/utils/offlineStorage'
import { OfflineQueue, getOfflineQueue, initOfflineQueue, OperationStatus, OperationPriority } from '@/utils/offlineQueue'
import { OfflineSync, getOfflineSync, initOfflineSync, SyncStatus, SyncStrategy } from '@/utils/offlineSync'

// 注意：IndexedDB由fake-indexeddb提供，已在setup.js中配置

describe('OfflineStorage', () => {
  let storage
  
  beforeEach(() => {
    storage = new OfflineStorage({ dbName: 'TestDB' })
  })
  
  afterEach(() => {
    if (storage) {
      storage.close()
    }
  })
  
  describe('初始化', () => {
    it('应该成功初始化数据库', async () => {
      await storage.init()
      expect(storage.db).toBeDefined()
    })
    
    it('应该创建所有存储对象', async () => {
      await storage.init()
      expect(Object.keys(storage.stores)).toContain('experiments')
      expect(Object.keys(storage.stores)).toContain('deviceStates')
      expect(Object.keys(storage.stores)).toContain('operationQueue')
    })
  })
  
  describe('数据存储', () => {
    beforeEach(async () => {
      await storage.init()
    })
    
    it('应该成功存储数据', async () => {
      await storage.set('experiments', 'exp_001', { name: '实验1', data: [] })
      const data = await storage.get('experiments', 'exp_001')
      expect(data).toBeDefined()
      expect(data.name).toBe('实验1')
    })
    
    it('应该成功获取数据', async () => {
      await storage.set('experiments', 'exp_002', { name: '实验2' })
      const data = await storage.get('experiments', 'exp_002')
      expect(data).not.toBeNull()
      expect(data.name).toBe('实验2')
    })
    
    it('应该返回null当数据不存在时', async () => {
      const data = await storage.get('experiments', 'nonexistent')
      expect(data).toBeNull()
    })
    
    it('应该成功删除数据', async () => {
      await storage.set('experiments', 'exp_003', { name: '实验3' })
      await storage.delete('experiments', 'exp_003')
      const data = await storage.get('experiments', 'exp_003')
      expect(data).toBeNull()
    })
    
    it('应该成功获取所有数据', async () => {
      await storage.set('experiments', 'exp_004', { name: '实验4' })
      await storage.set('experiments', 'exp_005', { name: '实验5' })
      const allData = await storage.getAll('experiments')
      expect(allData.length).toBeGreaterThanOrEqual(2)
    })
    
    it('应该支持批量存储', async () => {
      const items = [
        { key: 'exp_006', value: { name: '实验6' } },
        { key: 'exp_007', value: { name: '实验7' } }
      ]
      await storage.batchSet('experiments', items)
      const data1 = await storage.get('experiments', 'exp_006')
      const data2 = await storage.get('experiments', 'exp_007')
      expect(data1).toBeDefined()
      expect(data2).toBeDefined()
    })
  })
  
  describe('过期管理', () => {
    beforeEach(async () => {
      await storage.init()
    })
    
    it('应该设置过期时间', async () => {
      const ttl = 1000 // 1秒
      await storage.set('experiments', 'exp_expired', { name: '过期实验' }, { ttl })
      const data = await storage.get('experiments', 'exp_expired')
      expect(data.expiresAt).toBeGreaterThan(Date.now())
    })
    
    it('应该清理过期数据', async () => {
      // 存储一个已过期的数据
      const pastTime = Date.now() - 10000
      await storage.set('experiments', 'exp_old', { name: '旧实验', expiresAt: pastTime })
      
      const cleaned = await storage.cleanupExpired()
      expect(cleaned).toBeGreaterThanOrEqual(0)
    })
  })
  
  describe('统计信息', () => {
    beforeEach(async () => {
      await storage.init()
    })
    
    it('应该返回存储统计信息', async () => {
      await storage.set('experiments', 'exp_stat', { name: '统计测试' })
      const stats = await storage.getStats()
      expect(stats).toHaveProperty('stores')
      expect(stats).toHaveProperty('totalRecords')
    })
  })
})

describe('OfflineQueue', () => {
  let queue
  
  beforeEach(async () => {
    queue = new OfflineQueue({ enableAutoProcess: false })
    await queue.init()
  })
  
  afterEach(async () => {
    if (queue) {
      await queue.clear()
      queue.destroy()
    }
  })
  
  describe('操作入队', () => {
    it('应该成功添加操作到队列', async () => {
      const id = await queue.enqueue({
        type: 'test_operation',
        data: { value: 'test' }
      })
      expect(id).toBeDefined()
      expect(typeof id).toBe('number')
    })
    
    it('应该设置默认优先级', async () => {
      const id = await queue.enqueue({
        type: 'test_operation',
        data: { value: 'test' }
      })
      const operations = await queue.getOperations()
      const op = operations.find(o => o.id === id)
      expect(op.priority).toBe(OperationPriority.NORMAL)
    })
    
    it('应该支持自定义优先级', async () => {
      const id = await queue.enqueue({
        type: 'test_operation',
        data: { value: 'test' },
        priority: OperationPriority.HIGH
      })
      const operations = await queue.getOperations()
      const op = operations.find(o => o.id === id)
      expect(op.priority).toBe(OperationPriority.HIGH)
    })
    
    it('应该批量添加操作', async () => {
      const ids = await queue.enqueueBatch([
        { type: 'op1', data: {} },
        { type: 'op2', data: {} }
      ])
      expect(ids.length).toBe(2)
    })
  })
  
  describe('操作处理', () => {
    it('应该调用注册的处理器', async () => {
      const handler = vi.fn(() => Promise.resolve(true))
      queue.registerHandler('test_op', handler)
      
      const id = await queue.enqueue({
        type: 'test_op',
        data: { value: 'test' }
      })
      
      await queue.processAll()
      expect(handler).toHaveBeenCalled()
    })
    
    it('应该标记完成的操作', async () => {
      queue.registerHandler('complete_op', () => Promise.resolve(true))
      
      const id = await queue.enqueue({
        type: 'complete_op',
        data: {}
      })
      
      await queue.processAll()
      const operations = await queue.getOperations()
      const op = operations.find(o => o.id === id)
      expect(op.status).toBe(OperationStatus.COMPLETED)
    })
    
    it('应该重试失败的操作', async () => {
      let failCount = 0
      queue.registerHandler('retry_op', () => {
        failCount++
        if (failCount < 2) {
          return Promise.reject(new Error('临时失败'))
        }
        return Promise.resolve(true)
      })
      
      const id = await queue.enqueue({
        type: 'retry_op',
        data: {}
      })
      
      // 第一次处理应该失败
      await queue.processAll()
      const operations = await queue.getOperations()
      const op = operations.find(o => o.id === id)
      expect(op.retryCount).toBe(1)
      expect(op.status).toBe(OperationStatus.PENDING)
    })
  })
  
  describe('队列管理', () => {
    it('应该取消操作', async () => {
      const id = await queue.enqueue({
        type: 'cancel_op',
        data: {}
      })
      
      await queue.cancelOperation(id)
      const operations = await queue.getOperations()
      const op = operations.find(o => o.id === id)
      expect(op.status).toBe(OperationStatus.CANCELLED)
    })
    
    it('应该重试失败的操作', async () => {
      queue.registerHandler('fail_op', () => Promise.reject(new Error('失败')))
      
      const id = await queue.enqueue({
        type: 'fail_op',
        data: {}
      })
      
      // 处理直到失败
      for (let i = 0; i < queue.maxRetries; i++) {
        await queue.processAll()
      }
      
      let operations = await queue.getOperations()
      let op = operations.find(o => o.id === id)
      expect(op.status).toBe(OperationStatus.FAILED)
      
      // 重试
      await queue.retryOperation(id)
      operations = await queue.getOperations()
      op = operations.find(o => o.id === id)
      expect(op.status).toBe(OperationStatus.PENDING)
      expect(op.retryCount).toBe(0)
    })
    
    it('应该返回队列统计信息', async () => {
      await queue.enqueue({ type: 'op1', data: {} })
      await queue.enqueue({ type: 'op2', data: {}, priority: OperationPriority.HIGH })
      
      const stats = await queue.getStats()
      expect(stats.total).toBe(2)
      expect(stats.pending).toBe(2)
      expect(stats.byPriority.high).toBe(1)
      expect(stats.byPriority.normal).toBe(1)
    })
  })
})

describe('OfflineSync', () => {
  let sync
  
  beforeEach(async () => {
    // Mock axios
    vi.mock('axios', () => ({
      default: vi.fn(() => Promise.resolve({ status: 200, data: {} }))
    }))
    
    sync = new OfflineSync({ enableAutoSync: false })
    await sync.init()
  })
  
  afterEach(() => {
    if (sync) {
      sync.destroy()
    }
  })
  
  describe('同步处理器', () => {
    it('应该注册同步处理器', () => {
      const handler = {
        pull: vi.fn(() => Promise.resolve([])),
        push: vi.fn(() => Promise.resolve())
      }
      
      sync.registerSyncHandler('test_data', handler)
      expect(sync.syncHandlers.has('test_data')).toBe(true)
    })
    
    it('应该注销同步处理器', () => {
      sync.registerSyncHandler('test_data', {
        pull: vi.fn(),
        push: vi.fn()
      })
      
      sync.unregisterSyncHandler('test_data')
      expect(sync.syncHandlers.has('test_data')).toBe(false)
    })
  })
  
  describe('数据同步', () => {
    it('应该拉取远程数据', async () => {
      const remoteData = [
        { id: '1', name: '数据1', updatedAt: Date.now() },
        { id: '2', name: '数据2', updatedAt: Date.now() }
      ]
      
      sync.registerSyncHandler('test_data', {
        pull: vi.fn(() => Promise.resolve(remoteData)),
        push: vi.fn(() => Promise.resolve())
      })
      
      const result = await sync.syncDataType('test_data')
      expect(result.success).toBe(true)
      expect(result.pulled).toBe(2)
    })
    
    it('应该推送本地变更', async () => {
      const pushHandler = vi.fn(() => Promise.resolve())
      
      sync.registerSyncHandler('test_data', {
        pull: vi.fn(() => Promise.resolve([])),
        push: pushHandler
      })
      
      // 添加本地数据
      await sync.storage.set('test_data', 'local_1', {
        name: '本地数据',
        updatedAt: Date.now()
      })
      
      const result = await sync.syncDataType('test_data')
      expect(result.success).toBe(true)
      expect(result.pushed).toBe(1)
    })
  })
  
  describe('冲突解决', () => {
    it('应该使用默认策略解决冲突', async () => {
      const localData = {
        id: '1',
        name: '本地数据',
        updatedAt: Date.now() + 1000
      }
      
      const remoteData = {
        id: '1',
        name: '远程数据',
        updatedAt: Date.now()
      }
      
      const resolved = sync.defaultResolveConflict(localData, remoteData, SyncStrategy.SERVER_WINS)
      expect(resolved.name).toBe('远程数据')
    })
    
    it('应该使用本地优先策略', () => {
      const localData = { id: '1', name: '本地', updatedAt: Date.now() + 1000 }
      const remoteData = { id: '1', name: '远程', updatedAt: Date.now() }
      
      const resolved = sync.defaultResolveConflict(localData, remoteData, SyncStrategy.LOCAL_WINS)
      expect(resolved.name).toBe('本地')
    })
  })
  
  describe('智能请求', () => {
    it('在线时应该直接发送请求', async () => {
      const result = await sync.smartRequest({
        url: '/test',
        method: 'GET'
      })
      
      expect(result.online).toBe(true)
    })
    
    it('离线时应该将请求加入队列', async () => {
      // Mock离线状态
      Object.defineProperty(window.navigator, 'onLine', {
        value: false,
        writable: true
      })
      
      const result = await sync.smartRequest({
        url: '/test',
        method: 'POST'
      })
      
      expect(result.online).toBe(false)
      expect(result.queued).toBe(true)
      expect(result.queueId).toBeDefined()
    })
  })
  
  describe('同步状态', () => {
    it('应该返回同步状态', () => {
      const status = sync.getSyncStatus()
      expect(status).toHaveProperty('status')
      expect(status).toHaveProperty('lastSyncTime')
      expect(status).toHaveProperty('progress')
      expect(status).toHaveProperty('stats')
    })
  })
})

describe('集成测试', () => {
  it('应该完整执行离线工作流', async () => {
    // 1. 初始化所有模块
    const storage = await initOfflineStorage()
    const queue = await initOfflineQueue({ enableAutoProcess: false })
    const sync = await initOfflineSync({ enableAutoSync: false })
    
    // 2. 存储数据
    await storage.set('experiments', 'exp_001', {
      name: '测试实验',
      data: [1, 2, 3],
      updatedAt: Date.now()
    })
    
    // 3. 验证数据已存储
    const data = await storage.get('experiments', 'exp_001')
    expect(data).toBeDefined()
    expect(data.name).toBe('测试实验')
    
    // 4. 添加操作到队列
    const opId = await queue.enqueue({
      type: 'api_request',
      data: {
        url: '/api/experiments',
        method: 'POST',
        body: { name: '新实验' }
      },
      priority: OperationPriority.HIGH
    })
    
    // 5. 验证操作已入队
    const stats = await queue.getStats()
    expect(stats.pending).toBe(1)
    
    // 6. 清理
    storage.close()
    queue.destroy()
    sync.destroy()
  })
})
