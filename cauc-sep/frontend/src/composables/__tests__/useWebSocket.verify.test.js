/**
 * @file verify-websocket-enhancements.js
 * @path src/composables/__tests__/
 * @description 简单验证WebSocket增强功能
 * @author Agent
 * @date 2026-03-08
 */

import { describe, it, expect } from 'vitest'
import { useWebSocket, ProtocolType, ConnectionState } from '../useWebSocket'

describe('useWebSocket - 基础功能验证', () => {
  describe('导出验证', () => {
    it('应该导出ConnectionState枚举', () => {
      expect(ConnectionState).toBeDefined()
      expect(ConnectionState.DISCONNECTED).toBe('disconnected')
      expect(ConnectionState.CONNECTING).toBe('connecting')
      expect(ConnectionState.CONNECTED).toBe('connected')
      expect(ConnectionState.RECONNECTING).toBe('reconnecting')
    })
    
    it('应该导出ProtocolType枚举', () => {
      expect(ProtocolType).toBeDefined()
      expect(ProtocolType.JSON).toBe('json')
      expect(ProtocolType.MSGPACK).toBe('msgpack')
    })
  })
  
  describe('API完整性验证', () => {
    it('应该返回所有新增的状态', () => {
      const ws = useWebSocket({ url: 'ws://test' })
      
      // 连接状态
      expect(ws.connectionState).toBeDefined()
      expect(ws.wsConnected).toBeDefined()
      expect(ws.wsConnecting).toBeDefined()
      
      // 性能指标
      expect(ws.pushFrequency).toBeDefined()
      expect(ws.dataLatency).toBeDefined()
      expect(ws.connectionQuality).toBeDefined()
      
      // 心跳状态
      expect(ws.lastHeartbeatTime).toBeDefined()
      expect(ws.lastPongTime).toBeDefined()
      expect(ws.heartbeatTimeoutCount).toBeDefined()
      
      // 消息队列
      expect(ws.messageQueue).toBeDefined()
      expect(ws.queueLength).toBeDefined()
      expect(ws.queueFull).toBeDefined()
      
      // 协议相关
      expect(ws.currentProtocol).toBeDefined()
      expect(ws.protocolSupported).toBeDefined()
    })
    
    it('应该返回所有新增的方法', () => {
      const ws = useWebSocket({ url: 'ws://test' })
      
      // 连接方法
      expect(typeof ws.connect).toBe('function')
      expect(typeof ws.disconnect).toBe('function')
      expect(typeof ws.reconnect).toBe('function')
      expect(typeof ws.manualReconnect).toBe('function')
      expect(typeof ws.resetReconnect).toBe('function')
      
      // 消息方法
      expect(typeof ws.send).toBe('function')
      expect(typeof ws.subscribe).toBe('function')
      expect(typeof ws.unsubscribe).toBe('function')
      expect(typeof ws.flushMessageQueue).toBe('function')
      expect(typeof ws.clearMessageQueue).toBe('function')
      
      // 监控方法
      expect(typeof ws.getConnectionStats).toBe('function')
      expect(typeof ws.checkHealth).toBe('function')
    })
  })
  
  describe('初始状态验证', () => {
    it('初始状态应该是DISCONNECTED', () => {
      const { connectionState } = useWebSocket({ url: 'ws://test' })
      expect(connectionState.value).toBe(ConnectionState.DISCONNECTED)
    })
    
    it('初始消息队列应该为空', () => {
      const { messageQueue, queueLength } = useWebSocket({ url: 'ws://test' })
      expect(messageQueue.value).toEqual([])
      expect(queueLength.value).toBe(0)
    })
    
    it('初始连接质量应该为0', () => {
      const { connectionQuality } = useWebSocket({ url: 'ws://test' })
      expect(connectionQuality.value).toBe(0)
    })
    
    it('初始心跳超时计数应该为0', () => {
      const { heartbeatTimeoutCount } = useWebSocket({ url: 'ws://test' })
      expect(heartbeatTimeoutCount.value).toBe(0)
    })
  })
  
  describe('配置选项验证', () => {
    it('应该支持心跳超时配置', () => {
      const ws = useWebSocket({
        url: 'ws://test',
        heartbeatTimeout: 3000
      })
      expect(ws).toBeDefined()
    })
    
    it('应该支持最大退避延迟配置', () => {
      const ws = useWebSocket({
        url: 'ws://test',
        maxBackoffDelay: 60000
      })
      expect(ws).toBeDefined()
    })
    
    it('应该支持消息队列容量配置', () => {
      const ws = useWebSocket({
        url: 'ws://test',
        messageQueueSize: 200
      })
      expect(ws).toBeDefined()
    })
    
    it('应该支持自动同步配置', () => {
      const ws = useWebSocket({
        url: 'ws://test',
        enableAutoSync: true
      })
      expect(ws).toBeDefined()
    })
  })
  
  describe('健康检查功能', () => {
    it('checkHealth应该返回正确的结构', () => {
      const { checkHealth } = useWebSocket({ url: 'ws://test' })
      const health = checkHealth()
      
      expect(health).toHaveProperty('healthy')
      expect(health).toHaveProperty('score')
      expect(health).toHaveProperty('issues')
      expect(health).toHaveProperty('stats')
      
      expect(typeof health.healthy).toBe('boolean')
      expect(typeof health.score).toBe('number')
      expect(Array.isArray(health.issues)).toBe(true)
      expect(typeof health.stats).toBe('object')
    })
    
    it('未连接时健康检查应该失败', () => {
      const { checkHealth } = useWebSocket({ url: 'ws://test' })
      const health = checkHealth()
      
      expect(health.healthy).toBe(false)
      expect(health.issues.some(i => i.level === 'error')).toBe(true)
    })
  })
  
  describe('统计信息功能', () => {
    it('getConnectionStats应该返回完整的统计信息', () => {
      const { getConnectionStats } = useWebSocket({ url: 'ws://test' })
      const stats = getConnectionStats()
      
      // 连接状态
      expect(stats).toHaveProperty('connectionState')
      expect(stats).toHaveProperty('connected')
      expect(stats).toHaveProperty('connecting')
      
      // 协议信息
      expect(stats).toHaveProperty('protocol')
      expect(stats).toHaveProperty('protocolSupported')
      
      // 性能指标
      expect(stats).toHaveProperty('pushFrequency')
      expect(stats).toHaveProperty('dataLatency')
      expect(stats).toHaveProperty('connectionQuality')
      
      // 心跳信息
      expect(stats).toHaveProperty('lastHeartbeatTime')
      expect(stats).toHaveProperty('lastPongTime')
      expect(stats).toHaveProperty('heartbeatTimeoutCount')
      
      // 消息队列
      expect(stats).toHaveProperty('queueLength')
      expect(stats).toHaveProperty('queueFull')
    })
  })
  
  describe('消息队列功能', () => {
    it('断线时发送消息应该加入队列', () => {
      const { send, messageQueue, queueLength } = useWebSocket({
        url: 'ws://test',
        enableMessageQueue: true
      })
      
      // 未连接时发送消息
      const result = send({ type: 'test', data: 'hello' })
      
      // 应该返回false（未发送成功）
      expect(result).toBe(false)
      
      // 消息应该加入队列
      expect(queueLength.value).toBe(1)
      expect(messageQueue.value[0].data).toEqual({ type: 'test', data: 'hello' })
    })
    
    it('clearMessageQueue应该清空队列', () => {
      const { send, messageQueue, queueLength, clearMessageQueue } = useWebSocket({
        url: 'ws://test',
        enableMessageQueue: true
      })
      
      // 添加消息到队列
      send({ type: 'test1' })
      send({ type: 'test2' })
      expect(queueLength.value).toBe(2)
      
      // 清空队列
      clearMessageQueue()
      expect(queueLength.value).toBe(0)
      expect(messageQueue.value).toEqual([])
    })
    
    it('禁用消息队列时不应该缓存消息', () => {
      const { send, messageQueue, queueLength } = useWebSocket({
        url: 'ws://test',
        enableMessageQueue: false
      })
      
      send({ type: 'test' })
      
      expect(queueLength.value).toBe(0)
      expect(messageQueue.value).toEqual([])
    })
  })
})
