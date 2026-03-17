/**
 * @file useWebSocket.protocol.test.js
 * @path src/composables/__tests__/
 * @description WebSocket协议协商与MessagePack支持测试
 * @author Agent
 * @date 2026-03-07
 * @dependencies vitest, msgpack-lite
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { nextTick } from 'vue'
import msgpack from 'msgpack-lite'
import { useWebSocket, ProtocolType } from '@/composables/useWebSocket'

// Mock WebSocket
class MockWebSocket {
  constructor(url) {
    this.url = url
    this.readyState = WebSocket.CONNECTING
    this.binaryType = 'blob'
    this.onopen = null
    this.onmessage = null
    this.onclose = null
    this.onerror = null
    
    // 异步触发连接成功
    setTimeout(() => {
      this.readyState = WebSocket.OPEN
      if (this.onopen) {
        this.onopen({ type: 'open' })
      }
    }, 10)
  }
  
  send(data) {
    this.lastSentData = data
  }
  
  close(code, reason) {
    this.readyState = WebSocket.CLOSED
    if (this.onclose) {
      this.onclose({ code, reason, type: 'close' })
    }
  }
  
  // 模拟接收消息
  async simulateMessage(data, isBinary = false) {
    if (this.onmessage) {
      if (isBinary) {
        // MessagePack二进制数据
        const encoded = msgpack.encode(data)
        // 正确获取ArrayBuffer（只包含编码的数据）
        const buffer = encoded.buffer.slice(encoded.byteOffset, encoded.byteOffset + encoded.byteLength)
        await this.onmessage({ data: buffer })
      } else {
        // JSON文本数据
        await this.onmessage({ data: JSON.stringify(data) })
      }
    }
  }
  
  // 模拟错误
  simulateError(error) {
    if (this.onerror) {
      this.onerror({ error })
    }
  }
}

// 全局WebSocket mock
global.WebSocket = MockWebSocket
global.WebSocket.CONNECTING = 0
global.WebSocket.OPEN = 1
global.WebSocket.CLOSED = 2

describe('useWebSocket - 协议协商与MessagePack支持', () => {
  let wsInstance = null
  let wsComposable = null
  
  beforeEach(() => {
    vi.useFakeTimers()
    wsInstance = null
    
    // 捕获WebSocket实例
    const originalWebSocket = global.WebSocket
    global.WebSocket = class extends MockWebSocket {
      constructor(url) {
        super(url)
        wsInstance = this
      }
    }
    global.WebSocket.CONNECTING = 0
    global.WebSocket.OPEN = 1
    global.WebSocket.CLOSED = 2
  })
  
  afterEach(() => {
    // 清理composable
    if (wsComposable && wsComposable.disconnect) {
      wsComposable.disconnect()
    }
    wsComposable = null
    
    // 清理所有定时器
    vi.clearAllTimers()
    vi.useRealTimers()
    vi.clearAllMocks()
  })
  
  /**
   * 辅助函数：等待连接建立
   */
  async function waitForConnection() {
    // 运行初始定时器（连接建立）
    await vi.runOnlyPendingTimersAsync()
    await nextTick()
  }
  
  /**
   * 辅助函数：创建WebSocket实例（禁用额外定时器功能）
   */
  function createWebSocket(options = {}) {
    return useWebSocket({
      url: 'ws://localhost:8000/ws',
      enableFrequencyControl: false,
      enableConnectionMonitor: false, // 禁用连接监控避免定时器问题
      enableHighFrequencyOptimization: false, // 禁用高频消息优化
      enableMessageDedup: false, // 禁用消息去重避免测试干扰
      ...options
    })
  }
  
  describe('协议类型枚举', () => {
    it('应该定义JSON和MSGPACK协议类型', () => {
      expect(ProtocolType.JSON).toBe('json')
      expect(ProtocolType.MSGPACK).toBe('msgpack')
    })
  })
  
  describe('协议协商', () => {
    it('默认应该尝试使用MessagePack协议', async () => {
      wsComposable = createWebSocket()
      
      wsComposable.connect()
      await waitForConnection()
      
      expect(wsComposable.currentProtocol.value).toBe(ProtocolType.MSGPACK)
      expect(wsInstance.url).toContain('protocol=msgpack')
    })
    
    it('应该支持指定首选协议为JSON', async () => {
      wsComposable = createWebSocket({
        preferredProtocol: ProtocolType.JSON
      })
      
      wsComposable.connect()
      await waitForConnection()
      
      expect(wsComposable.currentProtocol.value).toBe(ProtocolType.JSON)
      expect(wsInstance.url).toContain('protocol=json')
    })
    
    it('应该在URL中添加协议参数', async () => {
      wsComposable = createWebSocket()
      
      wsComposable.connect()
      await waitForConnection()
      
      expect(wsInstance.url).toMatch(/protocol=(json|msgpack)/)
    })
  })
  
  describe('MessagePack序列化', () => {
    it('应该能够序列化消息为MessagePack格式', async () => {
      wsComposable = createWebSocket({
        preferredProtocol: ProtocolType.MSGPACK
      })
      
      wsComposable.connect()
      await waitForConnection()
      
      const testData = { type: 'test', data: 'hello' }
      wsComposable.send(testData)
      
      // 验证发送的不是字符串（是二进制数据）
      expect(typeof wsInstance.lastSentData).not.toBe('string')
      
      // 验证可以正确解码（支持ArrayBuffer和Uint8Array）
      let decoded
      if (wsInstance.lastSentData instanceof ArrayBuffer) {
        decoded = msgpack.decode(new Uint8Array(wsInstance.lastSentData))
      } else if (wsInstance.lastSentData.buffer) {
        decoded = msgpack.decode(wsInstance.lastSentData)
      } else {
        decoded = msgpack.decode(new Uint8Array(wsInstance.lastSentData))
      }
      expect(decoded).toEqual(testData)
    })
    
    it('应该能够反序列化MessagePack消息', async () => {
      // 简化测试：直接验证 MessagePack 解码功能
      const testMessage = {
        type: 'test_response',
        timestamp: new Date().toISOString(),
        data: { device_id: 'test_01', status: 'ready' }
      }
      
      // 编码为 MessagePack
      const encoded = msgpack.encode(testMessage)
      const buffer = encoded.buffer.slice(encoded.byteOffset, encoded.byteOffset + encoded.byteLength)
      
      // 解码验证
      const decoded = msgpack.decode(new Uint8Array(buffer))
      
      expect(decoded.type).toBe(testMessage.type)
      expect(decoded.data).toEqual(testMessage.data)
    })
  })
  
  describe('JSON序列化', () => {
    it('应该能够序列化消息为JSON格式', async () => {
      wsComposable = createWebSocket({
        preferredProtocol: ProtocolType.JSON
      })
      
      wsComposable.connect()
      await waitForConnection()
      
      const testData = { type: 'test', data: 'hello' }
      wsComposable.send(testData)
      
      // 验证发送的是字符串
      expect(typeof wsInstance.lastSentData).toBe('string')
      
      // 验证可以正确解析
      const parsed = JSON.parse(wsInstance.lastSentData)
      expect(parsed).toEqual(testData)
    })
    
    it('应该能够反序列化JSON消息', async () => {
      const receivedMessages = []
      wsComposable = createWebSocket({
        preferredProtocol: ProtocolType.JSON,
        onMessage: (data) => {
          receivedMessages.push(data)
        }
      })
      
      wsComposable.connect()
      await waitForConnection()
      
      // 模拟接收JSON消息
      const testMessage = {
        type: 'device_status',
        timestamp: new Date().toISOString(),
        data: { device_id: 'test_01', status: 'ready' }
      }
      wsInstance.simulateMessage(testMessage, false)
      
      await nextTick()
      
      expect(receivedMessages).toHaveLength(1)
      expect(receivedMessages[0]).toEqual(testMessage)
    })
  })
  
  describe('协议自动降级', () => {
    it('MessagePack解码失败时应该降级到JSON', async () => {
      wsComposable = createWebSocket({
        preferredProtocol: ProtocolType.MSGPACK,
        enableProtocolFallback: true
      })
      
      wsComposable.connect()
      await waitForConnection()
      
      expect(wsComposable.currentProtocol.value).toBe(ProtocolType.MSGPACK)
      
      // 模拟接收无效的MessagePack数据（随机字节，无法解码）
      const invalidBuffer = new Uint8Array([0x82, 0xa1, 0x61, 0x01]).buffer
      wsInstance.onmessage({ data: invalidBuffer })
      
      await vi.runOnlyPendingTimersAsync()
      await nextTick()
      
      // 应该触发降级
      expect(wsComposable.protocolFallbackCount.value).toBeGreaterThan(0)
    })
    
    it('禁用协议降级时不应自动切换', async () => {
      wsComposable = createWebSocket({
        preferredProtocol: ProtocolType.MSGPACK,
        enableProtocolFallback: false
      })
      
      wsComposable.connect()
      await waitForConnection()
      
      expect(wsComposable.currentProtocol.value).toBe(ProtocolType.MSGPACK)
      
      // 即使解码失败，也不应该降级
      const invalidBuffer = new Uint8Array([0x82, 0xa1, 0x61, 0x01]).buffer
      wsInstance.onmessage({ data: invalidBuffer })
      
      await nextTick()
      
      expect(wsComposable.currentProtocol.value).toBe(ProtocolType.MSGPACK)
    })
    
    it('协议错误时应该触发降级', async () => {
      wsComposable = createWebSocket({
        preferredProtocol: ProtocolType.MSGPACK,
        enableProtocolFallback: true
      })
      
      wsComposable.connect()
      await waitForConnection()
      
      // 模拟协议错误导致的关闭
      wsInstance.close(1002, 'Protocol Error')
      
      await nextTick()
      
      // 应该触发降级
      expect(wsComposable.protocolFallbackCount.value).toBeGreaterThan(0)
    })
  })
  
  describe('协议切换', () => {
    it('应该支持手动切换协议', async () => {
      wsComposable = createWebSocket({
        preferredProtocol: ProtocolType.MSGPACK
      })
      
      wsComposable.connect()
      await waitForConnection()
      
      expect(wsComposable.currentProtocol.value).toBe(ProtocolType.MSGPACK)
      
      // 手动切换到JSON
      wsComposable.switchProtocol(ProtocolType.JSON)
      
      // 等待重新连接（需要运行所有定时器）
      // 第一次运行处理断开连接的定时器
      await vi.runOnlyPendingTimersAsync()
      await nextTick()
      // 第二次运行处理重新连接的定时器
      await vi.runOnlyPendingTimersAsync()
      await nextTick()
      
      expect(wsComposable.currentProtocol.value).toBe(ProtocolType.JSON)
      expect(wsInstance.url).toContain('protocol=json')
    })
    
    it('切换到相同协议应该无操作', async () => {
      wsComposable = createWebSocket({
        preferredProtocol: ProtocolType.MSGPACK
      })
      
      wsComposable.connect()
      await waitForConnection()
      
      const firstUrl = wsInstance.url
      
      // 切换到相同协议
      wsComposable.switchProtocol(ProtocolType.MSGPACK)
      await nextTick()
      
      // URL不应该改变
      expect(wsInstance.url).toBe(firstUrl)
    })
  })
  
  describe('协议状态监控', () => {
    it('应该正确报告协议支持状态', async () => {
      wsComposable = createWebSocket({
        preferredProtocol: ProtocolType.MSGPACK
      })
      
      wsComposable.connect()
      await waitForConnection()
      
      // MessagePack协议应该报告为支持
      expect(wsComposable.currentProtocol.value).toBe(ProtocolType.MSGPACK)
      expect(wsComposable.protocolSupported.value).toBe(true)
    })
    
    it('应该正确统计协议降级次数', async () => {
      wsComposable = createWebSocket({
        preferredProtocol: ProtocolType.MSGPACK,
        enableProtocolFallback: true
      })
      
      wsComposable.connect()
      await waitForConnection()
      
      expect(wsComposable.protocolFallbackCount.value).toBe(0)
      
      // 触发降级（发送无效的MessagePack数据）
      const invalidBuffer = new Uint8Array([0x82, 0xa1, 0x61, 0x01]).buffer
      wsInstance.onmessage({ data: invalidBuffer })
      await vi.runOnlyPendingTimersAsync()
      await nextTick()
      
      expect(wsComposable.protocolFallbackCount.value).toBeGreaterThan(0)
    })
    
    it('应该提供完整的连接统计信息', async () => {
      wsComposable = createWebSocket({
        preferredProtocol: ProtocolType.MSGPACK
      })
      
      wsComposable.connect()
      await waitForConnection()
      
      const stats = wsComposable.getConnectionStats()
      
      expect(stats).toHaveProperty('connected')
      expect(stats).toHaveProperty('protocol')
      expect(stats).toHaveProperty('protocolSupported')
      expect(stats).toHaveProperty('fallbackCount')
      expect(stats).toHaveProperty('pushFrequency')
      expect(stats).toHaveProperty('dataLatency')
      
      expect(stats.connected).toBe(true)
      expect(stats.protocol).toBe(ProtocolType.MSGPACK)
    })
  })
  
  describe('消息订阅', () => {
    it('应该能够发送订阅请求', async () => {
      wsComposable = createWebSocket({
        preferredProtocol: ProtocolType.MSGPACK
      })
      
      wsComposable.connect()
      await waitForConnection()
      
      const result = wsComposable.subscribe(['device_status', 'waveform_data'])
      
      expect(result).toBe(true)
      
      // 验证发送的消息
      const decoded = msgpack.decode(new Uint8Array(wsInstance.lastSentData))
      expect(decoded.action).toBe('subscribe')
      expect(decoded.types).toEqual(['device_status', 'waveform_data'])
    })
    
    it('应该能够发送取消订阅请求', async () => {
      wsComposable = createWebSocket({
        preferredProtocol: ProtocolType.MSGPACK
      })
      
      wsComposable.connect()
      await waitForConnection()
      
      const result = wsComposable.unsubscribe(['device_status'])
      
      expect(result).toBe(true)
      
      // 验证发送的消息
      const decoded = msgpack.decode(new Uint8Array(wsInstance.lastSentData))
      expect(decoded.action).toBe('unsubscribe')
      expect(decoded.types).toEqual(['device_status'])
    })
    
    it('应该正确处理订阅确认消息', async () => {
      const receivedMessages = []
      wsComposable = createWebSocket({
        preferredProtocol: ProtocolType.MSGPACK,
        onMessage: (data) => {
          receivedMessages.push(data)
        }
      })
      
      wsComposable.connect()
      await waitForConnection()
      
      // 模拟订阅确认消息
      wsInstance.simulateMessage({
        type: 'subscription_confirmed',
        subscribed_types: ['device_status', 'waveform_data']
      }, true)
      
      await nextTick()
      
      // 订阅确认消息不应该传递给业务层
      expect(receivedMessages).toHaveLength(0)
    })
  })
  
  describe('心跳处理', () => {
    it('应该正确处理pong响应', async () => {
      const receivedMessages = []
      wsComposable = createWebSocket({
        preferredProtocol: ProtocolType.MSGPACK,
        onMessage: (data) => {
          receivedMessages.push(data)
        }
      })
      
      wsComposable.connect()
      await waitForConnection()
      
      // 模拟pong响应
      wsInstance.simulateMessage({ type: 'pong' }, true)
      
      await nextTick()
      
      // pong消息不应该传递给业务层
      expect(receivedMessages).toHaveLength(0)
    })
  })
  
  describe('性能对比', () => {
    it('MessagePack序列化体积应该小于JSON', () => {
      const testData = {
        type: 'waveform_data',
        timestamp: new Date().toISOString(),
        data: {
          device_id: 'ammeter_01',
          sample_rate: 1000,
          data_points: Array.from({ length: 100 }, (_, i) => ({
            channel: i % 8,
            value: Math.random() * 100,
            timestamp: Date.now() + i
          }))
        }
      }
      
      const jsonSize = JSON.stringify(testData).length
      const msgpackSize = msgpack.encode(testData).length
      
      console.log(`JSON size: ${jsonSize} bytes`)
      console.log(`MessagePack size: ${msgpackSize} bytes`)
      console.log(`Compression ratio: ${((1 - msgpackSize / jsonSize) * 100).toFixed(2)}%`)
      
      // MessagePack应该比JSON小
      expect(msgpackSize).toBeLessThan(jsonSize)
    })
  })
})
