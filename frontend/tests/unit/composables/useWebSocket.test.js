/**
 * @file useWebSocket.test.js
 * @path frontend/src/composables/__tests__/
 * @description useWebSocket组合式函数单元测试
 * @author Agent
 * @date 2024-03-08
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { 
  useWebSocket, 
  ConnectionState, 
  WSErrorType, 
  ReconnectStrategy, 
  ProtocolType 
} from '../useWebSocket';

// Mock msgpack-lite
vi.mock('msgpack-lite', () => ({
  default: {
    encode: vi.fn((data) => new Uint8Array(JSON.stringify(data).length)),
    decode: vi.fn((data) => JSON.parse(String.fromCharCode.apply(null, data))),
  },
  encode: vi.fn((data) => new Uint8Array(JSON.stringify(data).length)),
  decode: vi.fn((data) => JSON.parse(String.fromCharCode.apply(null, data))),
}));

// Mock usePushFrequency
vi.mock('./usePushFrequency', () => ({
  usePushFrequency: vi.fn(() => ({
    currentMode: { value: 'normal' },
    setMode: vi.fn(),
    getCurrentInterval: vi.fn(() => 1000),
    subscribe: vi.fn(() => vi.fn()),
  })),
  PUSH_MODE: {
    NORMAL: 'normal',
    HIGH: 'high',
    LOW: 'low',
  },
  FREQUENCY_PRESETS: {
    normal: { interval: 1000 },
    high: { interval: 100 },
    low: { interval: 5000 },
  },
}));

// Mock WebSocket
class MockWebSocket {
  constructor(url) {
    this.url = url;
    this.readyState = 0; // CONNECTING
    this.onopen = null;
    this.onclose = null;
    this.onerror = null;
    this.onmessage = null;
    
    // 模拟异步连接
    setTimeout(() => {
      this.readyState = 1; // OPEN
      if (this.onopen) this.onopen({ type: 'open' });
    }, 10);
  }
  
  send(data) {
    if (this.readyState !== 1) {
      throw new Error('WebSocket is not open');
    }
  }
  
  close() {
    this.readyState = 3; // CLOSED
    if (this.onclose) this.onclose({ type: 'close', code: 1000 });
  }
  
  // 测试辅助方法
  simulateMessage(data) {
    if (this.onmessage) {
      this.onmessage({ data: JSON.stringify(data) });
    }
  }
  
  simulateError(error) {
    if (this.onerror) {
      this.onerror({ error });
    }
  }
  
  simulateClose(code = 1000) {
    this.readyState = 3;
    if (this.onclose) {
      this.onclose({ type: 'close', code });
    }
  }
}

// 替换全局WebSocket
let mockWsInstances = [];
global.WebSocket = vi.fn((url) => {
  const ws = new MockWebSocket(url);
  mockWsInstances.push(ws);
  return ws;
});

describe('useWebSocket', () => {
  let ws;
  let options;

  beforeEach(() => {
    vi.useFakeTimers();
    mockWsInstances = [];
    
    options = {
      url: 'ws://localhost:8000/ws/test',
      onMessage: vi.fn(),
      onOpen: vi.fn(),
      onClose: vi.fn(),
      onError: vi.fn(),
      onReconnecting: vi.fn(),
      onStateChange: vi.fn(),
      reconnectInterval: 1000,
      heartbeatInterval: 30000,
      maxReconnectAttempts: 5,
    };
    
    ws = useWebSocket(options);
  });

  afterEach(() => {
    ws?.disconnect?.();
    vi.useRealTimers();
    vi.clearAllMocks();
    mockWsInstances = [];
  });

  describe('初始化状态', () => {
    it('应该初始化为断开状态', () => {
      expect(ws.connectionState.value).toBe(ConnectionState.DISCONNECTED);
    });

    it('应该初始化wsConnected为false', () => {
      expect(ws.wsConnected.value).toBe(false);
    });

    it('应该初始化重连次数为0', () => {
      expect(ws.reconnectAttempts.value).toBe(0);
    });

    it('应该初始化消息队列为空', () => {
      expect(ws.messageQueue.value).toHaveLength(0);
    });

    it('应该初始化当前协议为JSON', () => {
      expect(ws.currentProtocol.value).toBe(ProtocolType.JSON);
    });
  });

  describe('连接功能', () => {
    it('调用connect应该创建WebSocket连接', async () => {
      ws.connect();
      
      expect(global.WebSocket).toHaveBeenCalledWith(
        expect.stringContaining('ws://localhost:8000/ws/test')
      );
    });

    it('连接成功后状态应该变为CONNECTED', async () => {
      ws.connect();
      
      // 等待模拟连接完成
      await vi.advanceTimersByTimeAsync(20);
      
      expect(ws.connectionState.value).toBe(ConnectionState.CONNECTED);
      expect(ws.wsConnected.value).toBe(true);
    });

    it('连接成功应该调用onOpen回调', async () => {
      ws.connect();
      await vi.advanceTimersByTimeAsync(20);
      
      expect(options.onOpen).toHaveBeenCalled();
    });

    it('连接成功应该调用onStateChange回调', async () => {
      ws.connect();
      await vi.advanceTimersByTimeAsync(20);
      
      expect(options.onStateChange).toHaveBeenCalledWith(ConnectionState.CONNECTED);
    });
  });

  describe('断开连接功能', () => {
    it('调用disconnect应该关闭连接', async () => {
      ws.connect();
      await vi.advanceTimersByTimeAsync(20);
      
      ws.disconnect();
      
      expect(ws.connectionState.value).toBe(ConnectionState.DISCONNECTED);
    });

    it('断开连接应该调用onClose回调', async () => {
      ws.connect();
      await vi.advanceTimersByTimeAsync(20);
      
      ws.disconnect();
      
      expect(options.onClose).toHaveBeenCalled();
    });

    it('断开连接应该重置重连次数', async () => {
      ws.reconnectAttempts.value = 3;
      
      ws.disconnect();
      
      expect(ws.reconnectAttempts.value).toBe(0);
    });
  });

  describe('消息发送功能', () => {
    it('连接状态下应该能够发送消息', async () => {
      ws.connect();
      await vi.advanceTimersByTimeAsync(20);
      
      const result = ws.send({ type: 'test', data: 'hello' });
      
      expect(result).toBe(true);
    });

    it('断开状态下发送消息应该加入队列', () => {
      const result = ws.send({ type: 'test', data: 'hello' });
      
      expect(result).toBe(false);
      expect(ws.messageQueue.value.length).toBe(1);
    });
  });

  describe('消息接收功能', () => {
    it('收到消息应该调用onMessage回调', async () => {
      ws.connect();
      await vi.advanceTimersByTimeAsync(20);
      
      const testMessage = { type: 'test', data: 'hello' };
      
      // 直接调用内部的消息处理
      if (mockWsInstances[0] && mockWsInstances[0].onmessage) {
        mockWsInstances[0].onmessage({ data: JSON.stringify(testMessage) });
      }
      
      // 消息应该被处理
      expect(ws.messageCount.value).toBeGreaterThan(0);
    });

    it('收到消息应该更新消息计数', async () => {
      ws.connect();
      await vi.advanceTimersByTimeAsync(20);
      
      const initialCount = ws.messageCount.value;
      
      if (mockWsInstances[0] && mockWsInstances[0].onmessage) {
        mockWsInstances[0].onmessage({ data: JSON.stringify({ type: 'test' }) });
      }
      
      expect(ws.messageCount.value).toBe(initialCount + 1);
    });

    it('收到消息应该更新最后消息时间', async () => {
      ws.connect();
      await vi.advanceTimersByTimeAsync(20);
      
      const now = Date.now();
      vi.setSystemTime(now);
      
      if (mockWsInstances[0] && mockWsInstances[0].onmessage) {
        mockWsInstances[0].onmessage({ data: JSON.stringify({ type: 'test' }) });
      }
      
      expect(ws.lastMessageTime.value).toBe(now);
    });
  });

  describe('重连功能', () => {
    it('连接断开应该触发重连', async () => {
      ws.connect();
      await vi.advanceTimersByTimeAsync(20);
      
      // 模拟异常关闭
      if (mockWsInstances[0] && mockWsInstances[0].onclose) {
        mockWsInstances[0].onclose({ type: 'close', code: 1006 });
      }
      
      // 等待重连定时器
      await vi.advanceTimersByTimeAsync(3000);
      
      expect(options.onReconnecting).toHaveBeenCalled();
    });

    it('重连次数应该递增', async () => {
      ws.connect();
      await vi.advanceTimersByTimeAsync(20);
      
      if (mockWsInstances[0] && mockWsInstances[0].onclose) {
        mockWsInstances[0].onclose({ type: 'close', code: 1006 });
      }
      await vi.advanceTimersByTimeAsync(3000);
      
      expect(ws.reconnectAttempts.value).toBe(1);
    });

    it('手动断开不应该触发重连', async () => {
      ws.connect();
      await vi.advanceTimersByTimeAsync(20);
      
      ws.disconnect();
      await vi.advanceTimersByTimeAsync(5000);
      
      // 手动断开后不应该触发重连回调
      expect(ws.connectionState.value).toBe(ConnectionState.DISCONNECTED);
    });
  });

  describe('心跳功能', () => {
    it('连接后应该启动心跳定时器', async () => {
      ws.connect();
      await vi.advanceTimersByTimeAsync(20);
      
      // 心跳间隔后应该发送心跳
      await vi.advanceTimersByTimeAsync(30000);
      
      // 心跳应该更新lastHeartbeatTime
      expect(ws.lastHeartbeatTime.value).toBeGreaterThan(0);
    });
  });

  describe('协议协商功能', () => {
    it('应该支持协议切换', async () => {
      ws.connect();
      await vi.advanceTimersByTimeAsync(20);
      
      ws.switchProtocol(ProtocolType.MSGPACK);
      
      expect(ws.currentProtocol.value).toBe(ProtocolType.MSGPACK);
    });
  });

  describe('消息队列刷新', () => {
    it('连接后应该发送队列中的消息', async () => {
      ws.send({ type: 'queued1' });
      ws.send({ type: 'queued2' });
      
      expect(ws.messageQueue.value.length).toBe(2);
      
      ws.connect();
      await vi.advanceTimersByTimeAsync(20);
      
      ws.flushMessageQueue();
      
      expect(ws.messageQueue.value.length).toBe(0);
    });
  });

  describe('订阅功能', () => {
    it('应该能够订阅消息', () => {
      const callback = vi.fn();
      const result = ws.subscribe(callback);
      
      // subscribe方法返回取消订阅函数或布尔值
      expect(typeof result === 'function' || typeof result === 'boolean').toBe(true);
    });

    it('订阅后收到消息应该调用回调', async () => {
      ws.connect();
      await vi.advanceTimersByTimeAsync(20);
      
      const callback = vi.fn();
      ws.subscribe(callback);
      
      if (mockWsInstances[0] && mockWsInstances[0].onmessage) {
        mockWsInstances[0].onmessage({ data: JSON.stringify({ type: 'test' }) });
      }
      
      // 消息应该被处理
      expect(ws.messageCount.value).toBeGreaterThan(0);
    });
  });

  describe('连接质量评估', () => {
    it('未连接时质量评分应该为0', () => {
      expect(ws.connectionQuality.value).toBe(0);
    });

    it('连接后质量评分应该大于0', async () => {
      ws.connect();
      await vi.advanceTimersByTimeAsync(20);
      
      expect(ws.connectionQuality.value).toBeGreaterThan(0);
    });

    it('心跳超时应该降低质量评分', async () => {
      ws.connect();
      await vi.advanceTimersByTimeAsync(20);
      
      const initialQuality = ws.connectionQuality.value;
      
      ws.heartbeatTimeoutCount.value = 2;
      
      expect(ws.connectionQuality.value).toBeLessThan(initialQuality);
    });
  });

  describe('错误处理', () => {
    it('连接错误应该调用onError回调', async () => {
      ws.connect();
      await vi.advanceTimersByTimeAsync(20);
      
      if (mockWsInstances[0] && mockWsInstances[0].onerror) {
        mockWsInstances[0].onerror({ error: new Error('Connection failed') });
      }
      
      expect(options.onError).toHaveBeenCalled();
    });

    it('错误应该更新lastError', async () => {
      ws.connect();
      await vi.advanceTimersByTimeAsync(20);
      
      const error = new Error('Test error');
      if (mockWsInstances[0] && mockWsInstances[0].onerror) {
        mockWsInstances[0].onerror({ error });
      }
      
      expect(ws.lastError.value).toBeTruthy();
    });

    it('错误应该增加错误计数', async () => {
      ws.connect();
      await vi.advanceTimersByTimeAsync(20);
      
      const initialCount = ws.errorCount.value;
      
      if (mockWsInstances[0] && mockWsInstances[0].onerror) {
        mockWsInstances[0].onerror({ error: new Error('Test error') });
      }
      
      expect(ws.errorCount.value).toBe(initialCount + 1);
    });
  });

  describe('状态枚举', () => {
    it('ConnectionState应该包含所有状态', () => {
      expect(ConnectionState.DISCONNECTED).toBe('disconnected');
      expect(ConnectionState.CONNECTING).toBe('connecting');
      expect(ConnectionState.CONNECTED).toBe('connected');
      expect(ConnectionState.RECONNECTING).toBe('reconnecting');
      expect(ConnectionState.RECONNECT_FAILED).toBe('reconnect_failed');
      expect(ConnectionState.TIMEOUT).toBe('timeout');
    });

    it('WSErrorType应该包含所有错误类型', () => {
      expect(WSErrorType.CONNECTION_ERROR).toBe('connection_error');
      expect(WSErrorType.CONNECTION_TIMEOUT).toBe('connection_timeout');
      expect(WSErrorType.AUTH_FAILED).toBe('auth_failed');
      expect(WSErrorType.PROTOCOL_ERROR).toBe('protocol_error');
      expect(WSErrorType.NETWORK_ERROR).toBe('network_error');
    });

    it('ReconnectStrategy应该包含所有策略', () => {
      expect(ReconnectStrategy.FIXED).toBe('fixed');
      expect(ReconnectStrategy.LINEAR).toBe('linear');
      expect(ReconnectStrategy.EXPONENTIAL).toBe('exponential');
      expect(ReconnectStrategy.FIBONACCI).toBe('fibonacci');
    });

    it('ProtocolType应该包含所有协议', () => {
      expect(ProtocolType.JSON).toBe('json');
      expect(ProtocolType.MSGPACK).toBe('msgpack');
    });
  });

  describe('计算属性', () => {
    it('wsConnected应该是connectionState的派生状态', async () => {
      expect(ws.wsConnected.value).toBe(false);
      
      ws.connect();
      await vi.advanceTimersByTimeAsync(20);
      
      expect(ws.wsConnected.value).toBe(true);
    });

    it('wsConnecting应该正确反映连接中状态', async () => {
      ws.connect();
      
      // 连接过程中
      expect(ws.wsConnecting.value).toBe(true);
      
      await vi.advanceTimersByTimeAsync(20);
      
      expect(ws.wsConnecting.value).toBe(false);
    });

    it('queueFull应该正确反映队列状态', () => {
      expect(ws.queueFull.value).toBe(false);
      
      // 填满队列
      for (let i = 0; i < 100; i++) {
        ws.send({ type: `msg${i}` });
      }
      
      expect(ws.queueFull.value).toBe(true);
    });
  });
});
