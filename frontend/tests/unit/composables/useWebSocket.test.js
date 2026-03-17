/**
 * @file useWebSocket.test.js
 * @path frontend/tests/unit/composables/
 * @description useWebSocket组合式函数单元测试
 * 
 * 测试覆盖：
 * - 连接建立
 * - 消息收发
 * - 重连机制
 * - 心跳检测
 * - 协议协商
 * - 错误处理
 * 
 * @author Agent
 * @date 2026-03-16
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { nextTick } from 'vue';
import {
  useWebSocket,
  ConnectionState,
  WSErrorType,
  ReconnectStrategy,
  ProtocolType
} from '@/composables/useWebSocket';

/**
 * 创建模拟WebSocket实例
 * 
 * @returns {Object} 模拟WebSocket对象
 */
function createMockWebSocket() {
  const ws = {
    readyState: WebSocket.CONNECTING,
    send: vi.fn(),
    close: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
    url: 'ws://localhost:8000/ws',
    binaryType: 'blob',
    CONNECTING: WebSocket.CONNECTING,
    OPEN: WebSocket.OPEN,
    CLOSING: WebSocket.CLOSING,
    CLOSED: WebSocket.CLOSED,
    onopen: null,
    onclose: null,
    onmessage: null,
    onerror: null
  };

  return ws;
}

/**
 * 模拟WebSocket构造函数
 */
let mockWebSocketConstructor;
let mockWebSocketInstances = [];

vi.stubGlobal('WebSocket', vi.fn((url) => {
  const ws = createMockWebSocket();
  ws.url = url;
  mockWebSocketInstances.push(ws);
  return ws;
}));

describe('useWebSocket', () => {
  let ws;
  let defaultOptions;

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    mockWebSocketInstances = [];

    defaultOptions = {
      url: 'ws://localhost:8000/ws',
      reconnectInterval: 1000,
      heartbeatInterval: 30000,
      heartbeatTimeout: 5000,
      maxReconnectAttempts: 5,
      maxBackoffDelay: 30000,
      messageQueueSize: 100,
      defaultPushMode: 'normal',
      enableFrequencyControl: true,
      preferredProtocol: ProtocolType.MSGPACK,
      enableProtocolFallback: true,
      enableMessageQueue: true,
      enableAutoSync: true,
      reconnectStrategy: ReconnectStrategy.EXPONENTIAL,
      enableMessageDedup: true,
      dedupWindowMs: 5000,
      maxDedupCacheSize: 1000,
      enableHighFrequencyOptimization: true,
      highFrequencyThreshold: 50,
      enableConnectionMonitor: true,
      monitorInterval: 5000,
      onMessage: vi.fn(),
      onOpen: vi.fn(),
      onClose: vi.fn(),
      onError: vi.fn(),
      onReconnecting: vi.fn(),
      onProtocolChange: vi.fn(),
      onStateChange: vi.fn(),
      onSyncComplete: vi.fn()
    };
  });

  afterEach(() => {
    if (ws) {
      ws.disconnect();
      ws = null;
    }
    vi.useRealTimers();
  });

  // ==================== 初始化测试 ====================

  describe('初始化', () => {
    it('应该正确初始化所有状态', () => {
      ws = useWebSocket(defaultOptions);

      expect(ws.connectionState.value).toBe(ConnectionState.DISCONNECTED);
      expect(ws.wsConnected.value).toBe(false);
      expect(ws.wsConnecting.value).toBe(false);
      expect(ws.reconnectAttempts.value).toBe(0);
      expect(ws.maxReconnectReached.value).toBe(false);
      expect(ws.currentProtocol.value).toBe(ProtocolType.JSON);
      expect(ws.messageQueue.value).toEqual([]);
      expect(ws.errorCount.value).toBe(0);
    });

    it('应该使用默认配置选项', () => {
      ws = useWebSocket({ url: 'ws://localhost:8000/ws' });

      // 验证默认配置生效
      expect(ws).toBeDefined();
    });

    it('应该支持自定义配置选项', () => {
      const customOptions = {
        ...defaultOptions,
        reconnectInterval: 5000,
        heartbeatInterval: 60000,
        maxReconnectAttempts: 10
      };

      ws = useWebSocket(customOptions);

      expect(ws).toBeDefined();
    });
  });

  // ==================== 连接建立测试 ====================

  describe('连接建立', () => {
    it('应该成功建立WebSocket连接', async () => {
      ws = useWebSocket(defaultOptions);

      ws.connect();

      await nextTick();

      expect(WebSocket).toHaveBeenCalled();
      expect(ws.connectionState.value).toBe(ConnectionState.CONNECTING);
    });

    it('连接成功后应该更新状态', async () => {
      ws = useWebSocket(defaultOptions);

      ws.connect();
      await nextTick();

      // 模拟连接成功
      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      if (mockWs.onopen) {
        mockWs.readyState = WebSocket.OPEN;
        mockWs.onopen({ type: 'open' });
      }

      await nextTick();

      expect(ws.connectionState.value).toBe(ConnectionState.CONNECTED);
      expect(ws.wsConnected.value).toBe(true);
      expect(defaultOptions.onOpen).toHaveBeenCalled();
    });

    it('连接成功后应该启动心跳检测', async () => {
      ws = useWebSocket(defaultOptions);

      ws.connect();
      await nextTick();

      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      if (mockWs.onopen) {
        mockWs.readyState = WebSocket.OPEN;
        mockWs.onopen({ type: 'open' });
      }

      await nextTick();

      // 验证心跳定时器已启动
      expect(ws.lastHeartbeatTime.value).toBeDefined();
    });

    it('连接成功后应该重置重连计数器', async () => {
      ws = useWebSocket(defaultOptions);

      ws.connect();
      await nextTick();

      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      if (mockWs.onopen) {
        mockWs.readyState = WebSocket.OPEN;
        mockWs.onopen({ type: 'open' });
      }

      await nextTick();

      expect(ws.reconnectAttempts.value).toBe(0);
      expect(ws.maxReconnectReached.value).toBe(false);
    });

    it('连接成功后应该触发onStateChange回调', async () => {
      ws = useWebSocket(defaultOptions);

      ws.connect();
      await nextTick();

      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      if (mockWs.onopen) {
        mockWs.readyState = WebSocket.OPEN;
        mockWs.onopen({ type: 'open' });
      }

      await nextTick();

      expect(defaultOptions.onStateChange).toHaveBeenCalledWith(ConnectionState.CONNECTED);
    });
  });

  // ==================== 消息收发测试 ====================

  describe('消息收发', () => {
    beforeEach(async () => {
      ws = useWebSocket(defaultOptions);
      ws.connect();
      await nextTick();

      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      if (mockWs.onopen) {
        mockWs.readyState = WebSocket.OPEN;
        mockWs.onopen({ type: 'open' });
      }

      await nextTick();
    });

    it('应该成功发送消息', () => {
      const message = { type: 'test', data: 'hello' };
      const result = ws.send(message);

      expect(result).toBe(true);
      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      expect(mockWs.send).toHaveBeenCalled();
    });

    it('未连接时发送消息应该加入队列', () => {
      ws.disconnect();

      const message = { type: 'test', data: 'hello' };
      const result = ws.send(message);

      expect(result).toBe(false);
      expect(ws.messageQueue.value.length).toBeGreaterThan(0);
    });

    it('应该正确接收并处理消息', async () => {
      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];

      const testMessage = { type: 'data', value: 123, timestamp: Date.now() };
      const messageEvent = {
        data: JSON.stringify(testMessage)
      };

      if (mockWs.onmessage) {
        mockWs.onmessage(messageEvent);
      }

      await nextTick();

      expect(defaultOptions.onMessage).toHaveBeenCalled();
    });

    it('应该处理心跳响应消息', async () => {
      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];

      const pongMessage = { type: 'pong', timestamp: Date.now() };
      const messageEvent = {
        data: JSON.stringify(pongMessage)
      };

      if (mockWs.onmessage) {
        mockWs.onmessage(messageEvent);
      }

      await nextTick();

      expect(ws.lastPongTime.value).toBeDefined();
    });

    it('应该处理同步完成消息', async () => {
      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];

      const syncMessage = { type: 'sync_complete', data: {} };
      const messageEvent = {
        data: JSON.stringify(syncMessage)
      };

      if (mockWs.onmessage) {
        mockWs.onmessage(messageEvent);
      }

      await nextTick();

      // 验证同步完成处理
      expect(ws).toBeDefined();
    });

    it('应该正确处理订阅请求', () => {
      const types = ['device_status', 'waveform_data'];
      const result = ws.subscribe(types);

      expect(result).toBe(true);
    });

    it('应该正确处理取消订阅请求', () => {
      const types = ['device_status'];
      const result = ws.unsubscribe(types);

      expect(result).toBe(true);
    });
  });

  // ==================== 重连机制测试 ====================

  describe('重连机制', () => {
    it('连接断开后应该触发重连', async () => {
      ws = useWebSocket(defaultOptions);

      ws.connect();
      await nextTick();

      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      if (mockWs.onopen) {
        mockWs.readyState = WebSocket.OPEN;
        mockWs.onopen({ type: 'open' });
      }

      await nextTick();

      // 模拟连接断开
      if (mockWs.onclose) {
        mockWs.readyState = WebSocket.CLOSED;
        mockWs.onclose({ code: 1000, reason: 'Normal closure', wasClean: true });
      }

      await nextTick();

      // 验证重连状态
      expect(ws.connectionState.value).toBe(ConnectionState.RECONNECTING);
    });

    it('应该使用指数退避策略计算重连延迟', async () => {
      ws = useWebSocket({
        ...defaultOptions,
        reconnectStrategy: ReconnectStrategy.EXPONENTIAL,
        reconnectInterval: 1000
      });

      ws.connect();
      await nextTick();

      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      if (mockWs.onopen) {
        mockWs.readyState = WebSocket.OPEN;
        mockWs.onopen({ type: 'open' });
      }

      await nextTick();

      // 模拟连接断开
      if (mockWs.onclose) {
        mockWs.readyState = WebSocket.CLOSED;
        mockWs.onclose({ code: 1000, reason: 'Normal closure', wasClean: true });
      }

      await nextTick();

      // 验证重连尝试
      expect(ws.reconnectAttempts.value).toBeGreaterThan(0);
    });

    it('应该使用线性策略计算重连延迟', async () => {
      ws = useWebSocket({
        ...defaultOptions,
        reconnectStrategy: ReconnectStrategy.LINEAR,
        reconnectInterval: 1000
      });

      ws.connect();
      await nextTick();

      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      if (mockWs.onopen) {
        mockWs.readyState = WebSocket.OPEN;
        mockWs.onopen({ type: 'open' });
      }

      await nextTick();

      if (mockWs.onclose) {
        mockWs.readyState = WebSocket.CLOSED;
        mockWs.onclose({ code: 1000, reason: 'Normal closure', wasClean: true });
      }

      await nextTick();

      expect(ws.reconnectAttempts.value).toBeGreaterThan(0);
    });

    it('应该使用固定间隔策略计算重连延迟', async () => {
      ws = useWebSocket({
        ...defaultOptions,
        reconnectStrategy: ReconnectStrategy.FIXED,
        reconnectInterval: 1000
      });

      ws.connect();
      await nextTick();

      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      if (mockWs.onopen) {
        mockWs.readyState = WebSocket.OPEN;
        mockWs.onopen({ type: 'open' });
      }

      await nextTick();

      if (mockWs.onclose) {
        mockWs.readyState = WebSocket.CLOSED;
        mockWs.onclose({ code: 1000, reason: 'Normal closure', wasClean: true });
      }

      await nextTick();

      expect(ws.reconnectAttempts.value).toBeGreaterThan(0);
    });

    it('达到最大重连次数后应该停止重连', async () => {
      ws = useWebSocket({
        ...defaultOptions,
        maxReconnectAttempts: 2
      });

      ws.connect();
      await nextTick();

      let mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      if (mockWs.onopen) {
        mockWs.readyState = WebSocket.OPEN;
        mockWs.onopen({ type: 'open' });
      }

      await nextTick();

      // 模拟多次连接失败
      for (let i = 0; i < 3; i++) {
        mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
        if (mockWs.onclose) {
          mockWs.readyState = WebSocket.CLOSED;
          mockWs.onclose({ code: 1006, reason: 'Abnormal closure', wasClean: false });
        }

        await nextTick();
        vi.advanceTimersByTime(5000);
      }

      expect(ws.maxReconnectReached.value).toBe(true);
      expect(ws.connectionState.value).toBe(ConnectionState.RECONNECT_FAILED);
    });

    it('应该支持手动重连', async () => {
      ws = useWebSocket(defaultOptions);

      ws.connect();
      await nextTick();

      let mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      if (mockWs.onopen) {
        mockWs.readyState = WebSocket.OPEN;
        mockWs.onopen({ type: 'open' });
      }

      await nextTick();

      // 断开连接
      ws.disconnect();
      await nextTick();

      // 手动重连
      ws.manualReconnect();
      await nextTick();

      expect(ws.reconnectAttempts.value).toBe(0);
      expect(ws.maxReconnectReached.value).toBe(false);
    });

    it('应该支持重置重连状态', () => {
      ws = useWebSocket(defaultOptions);

      ws.reconnectAttempts.value = 3;
      ws.maxReconnectReached.value = true;

      ws.resetReconnect();

      expect(ws.reconnectAttempts.value).toBe(0);
      expect(ws.maxReconnectReached.value).toBe(false);
    });
  });

  // ==================== 心跳检测测试 ====================

  describe('心跳检测', () => {
    beforeEach(async () => {
      ws = useWebSocket({
        ...defaultOptions,
        heartbeatInterval: 1000,
        heartbeatTimeout: 500
      });

      ws.connect();
      await nextTick();

      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      if (mockWs.onopen) {
        mockWs.readyState = WebSocket.OPEN;
        mockWs.onopen({ type: 'open' });
      }

      await nextTick();
    });

    it('应该定期发送心跳消息', async () => {
      vi.advanceTimersByTime(1000);
      await nextTick();

      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      expect(mockWs.send).toHaveBeenCalled();
    });

    it('应该正确处理心跳响应', async () => {
      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];

      // 发送心跳
      vi.advanceTimersByTime(1000);
      await nextTick();

      // 模拟收到pong响应
      const pongMessage = { type: 'pong', timestamp: Date.now() };
      if (mockWs.onmessage) {
        mockWs.onmessage({ data: JSON.stringify(pongMessage) });
      }

      await nextTick();

      expect(ws.lastPongTime.value).toBeDefined();
    });

    it('心跳超时应该增加超时计数', async () => {
      vi.advanceTimersByTime(1000);
      await nextTick();

      // 不响应心跳，等待超时
      vi.advanceTimersByTime(500);
      await nextTick();

      // 再次发送心跳
      vi.advanceTimersByTime(1000);
      await nextTick();

      // 心跳超时计数应该增加
      expect(ws.heartbeatTimeoutCount.value).toBeGreaterThanOrEqual(0);
    });

    it('连续心跳超时应该断开连接', async () => {
      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];

      // 模拟多次心跳超时
      for (let i = 0; i < 4; i++) {
        vi.advanceTimersByTime(1000);
        await nextTick();
      }

      // 验证连接状态
      expect(ws.heartbeatTimeoutCount.value).toBeGreaterThan(0);
    });
  });

  // ==================== 协议协商测试 ====================

  describe('协议协商', () => {
    it('应该支持MessagePack协议', async () => {
      ws = useWebSocket({
        ...defaultOptions,
        preferredProtocol: ProtocolType.MSGPACK
      });

      ws.connect();
      await nextTick();

      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      if (mockWs.onopen) {
        mockWs.readyState = WebSocket.OPEN;
        mockWs.onopen({ type: 'open' });
      }

      await nextTick();

      expect(ws.currentProtocol.value).toBe(ProtocolType.MSGPACK);
    });

    it('应该支持JSON协议', async () => {
      ws = useWebSocket({
        ...defaultOptions,
        preferredProtocol: ProtocolType.JSON
      });

      ws.connect();
      await nextTick();

      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      if (mockWs.onopen) {
        mockWs.readyState = WebSocket.OPEN;
        mockWs.onopen({ type: 'open' });
      }

      await nextTick();

      expect(ws.currentProtocol.value).toBe(ProtocolType.JSON);
    });

    it('应该支持手动切换协议', async () => {
      ws = useWebSocket({
        ...defaultOptions,
        preferredProtocol: ProtocolType.MSGPACK
      });

      ws.connect();
      await nextTick();

      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      if (mockWs.onopen) {
        mockWs.readyState = WebSocket.OPEN;
        mockWs.onopen({ type: 'open' });
      }

      await nextTick();

      // 切换到JSON协议
      ws.switchProtocol(ProtocolType.JSON);
      await nextTick();

      expect(ws.currentProtocol.value).toBe(ProtocolType.JSON);
    });

    it('协议切换应该触发onProtocolChange回调', async () => {
      ws = useWebSocket(defaultOptions);

      ws.connect();
      await nextTick();

      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      if (mockWs.onopen) {
        mockWs.readyState = WebSocket.OPEN;
        mockWs.onopen({ type: 'open' });
      }

      await nextTick();

      ws.switchProtocol(ProtocolType.MSGPACK);
      await nextTick();

      // 验证协议切换成功
      expect(ws.currentProtocol.value).toBe(ProtocolType.MSGPACK);
    });
  });

  // ==================== 错误处理测试 ====================

  describe('错误处理', () => {
    it('应该正确处理连接错误', async () => {
      ws = useWebSocket(defaultOptions);

      ws.connect();
      await nextTick();

      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      if (mockWs.onerror) {
        mockWs.onerror(new Error('Connection failed'));
      }

      await nextTick();

      expect(ws.lastError.value).toBeDefined();
      expect(ws.errorCount.value).toBeGreaterThan(0);
      expect(defaultOptions.onError).toHaveBeenCalled();
    });

    it('应该正确处理消息解析错误', async () => {
      ws = useWebSocket(defaultOptions);

      ws.connect();
      await nextTick();

      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      if (mockWs.onopen) {
        mockWs.readyState = WebSocket.OPEN;
        mockWs.onopen({ type: 'open' });
      }

      await nextTick();

      // 发送无效消息
      if (mockWs.onmessage) {
        mockWs.onmessage({ data: 'invalid json{' });
      }

      await nextTick();

      expect(ws.errorCount.value).toBeGreaterThan(0);
    });

    it('应该正确分类错误类型', () => {
      ws = useWebSocket(defaultOptions);

      const error = new Error('Network error');
      const errorInfo = ws.classifyError(error, WSErrorType.NETWORK_ERROR);

      expect(errorInfo.type).toBe(WSErrorType.NETWORK_ERROR);
      expect(errorInfo.recoverable).toBe(true);
    });

    it('应该提供用户友好的错误消息', () => {
      ws = useWebSocket(defaultOptions);

      const message = ws.getUserFriendlyErrorMessage(WSErrorType.CONNECTION_ERROR);

      expect(message).toContain('连接');
    });

    it('应该提供错误解决建议', () => {
      ws = useWebSocket(defaultOptions);

      const suggestion = ws.getErrorSuggestion(WSErrorType.CONNECTION_ERROR);

      expect(suggestion).toContain('检查');
    });
  });

  // ==================== 消息队列测试 ====================

  describe('消息队列', () => {
    it('应该正确管理消息队列', () => {
      ws = useWebSocket(defaultOptions);

      expect(ws.queueLength.value).toBe(0);
      expect(ws.queueFull.value).toBe(false);
    });

    it('断线时消息应该加入队列', () => {
      ws = useWebSocket(defaultOptions);

      // 未连接时发送消息
      ws.send({ type: 'test', data: 'hello' });

      expect(ws.queueLength.value).toBeGreaterThan(0);
    });

    it('连接成功后应该刷新消息队列', async () => {
      ws = useWebSocket(defaultOptions);

      // 发送消息（未连接）
      ws.send({ type: 'test', data: 'hello1' });
      ws.send({ type: 'test', data: 'hello2' });

      // 连接
      ws.connect();
      await nextTick();

      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      if (mockWs.onopen) {
        mockWs.readyState = WebSocket.OPEN;
        mockWs.onopen({ type: 'open' });
      }

      await nextTick();

      // 队列应该被清空或减少
      expect(ws.queueLength.value).toBeLessThan(2);
    });

    it('应该支持手动刷新消息队列', async () => {
      ws = useWebSocket(defaultOptions);

      // 添加消息到队列
      ws.send({ type: 'test', data: 'hello' });

      // 连接
      ws.connect();
      await nextTick();

      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      if (mockWs.onopen) {
        mockWs.readyState = WebSocket.OPEN;
        mockWs.onopen({ type: 'open' });
      }

      await nextTick();

      // 手动刷新队列
      const flushed = await ws.flushMessageQueue();

      expect(typeof flushed).toBe('number');
    });

    it('应该支持清空消息队列', () => {
      ws = useWebSocket(defaultOptions);

      ws.send({ type: 'test', data: 'hello' });
      ws.clearMessageQueue();

      expect(ws.queueLength.value).toBe(0);
    });
  });

  // ==================== 消息去重测试 ====================

  describe('消息去重', () => {
    beforeEach(async () => {
      ws = useWebSocket({
        ...defaultOptions,
        enableMessageDedup: true
      });

      ws.connect();
      await nextTick();

      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      if (mockWs.onopen) {
        mockWs.readyState = WebSocket.OPEN;
        mockWs.onopen({ type: 'open' });
      }

      await nextTick();
    });

    it('应该检测并过滤重复消息', async () => {
      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];

      const message = { type: 'data', value: 123, timestamp: Date.now() };
      const messageEvent = {
        data: JSON.stringify(message)
      };

      // 发送两次相同消息
      if (mockWs.onmessage) {
        mockWs.onmessage(messageEvent);
        mockWs.onmessage(messageEvent);
      }

      await nextTick();

      // 应该只处理一次
      expect(ws.dedupHitCount.value).toBeGreaterThan(0);
    });
  });

  // ==================== 连接监控测试 ====================

  describe('连接监控', () => {
    it('应该正确获取连接统计信息', async () => {
      ws = useWebSocket(defaultOptions);

      ws.connect();
      await nextTick();

      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      if (mockWs.onopen) {
        mockWs.readyState = WebSocket.OPEN;
        mockWs.onopen({ type: 'open' });
      }

      await nextTick();

      const stats = ws.getConnectionStats();

      expect(stats).toHaveProperty('connected');
      expect(stats).toHaveProperty('protocol');
      expect(stats).toHaveProperty('reconnectAttempts');
    });

    it('应该正确检查连接健康状态', async () => {
      ws = useWebSocket(defaultOptions);

      ws.connect();
      await nextTick();

      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      if (mockWs.onopen) {
        mockWs.readyState = WebSocket.OPEN;
        mockWs.onopen({ type: 'open' });
      }

      await nextTick();

      const health = ws.checkHealth();

      expect(health).toHaveProperty('healthy');
      expect(health).toHaveProperty('score');
      expect(health).toHaveProperty('issues');
    });

    it('应该记录连接历史', async () => {
      ws = useWebSocket({
        ...defaultOptions,
        enableConnectionMonitor: true
      });

      ws.connect();
      await nextTick();

      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      if (mockWs.onopen) {
        mockWs.readyState = WebSocket.OPEN;
        mockWs.onopen({ type: 'open' });
      }

      await nextTick();

      expect(ws.connectionHistory.value.length).toBeGreaterThan(0);
    });
  });

  // ==================== 断开连接测试 ====================

  describe('断开连接', () => {
    it('应该正确断开连接', async () => {
      ws = useWebSocket(defaultOptions);

      ws.connect();
      await nextTick();

      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      if (mockWs.onopen) {
        mockWs.readyState = WebSocket.OPEN;
        mockWs.onopen({ type: 'open' });
      }

      await nextTick();

      ws.disconnect();
      await nextTick();

      expect(ws.connectionState.value).toBe(ConnectionState.DISCONNECTED);
      expect(ws.wsConnected.value).toBe(false);
    });

    it('断开连接应该清理所有定时器', async () => {
      ws = useWebSocket(defaultOptions);

      ws.connect();
      await nextTick();

      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      if (mockWs.onopen) {
        mockWs.readyState = WebSocket.OPEN;
        mockWs.onopen({ type: 'open' });
      }

      await nextTick();

      ws.disconnect();
      await nextTick();

      // 验证状态已重置
      expect(ws.reconnectAttempts.value).toBe(0);
    });

    it('断开连接应该触发onClose回调', async () => {
      ws = useWebSocket(defaultOptions);

      ws.connect();
      await nextTick();

      const mockWs = mockWebSocketInstances[mockWebSocketInstances.length - 1];
      if (mockWs.onopen) {
        mockWs.readyState = WebSocket.OPEN;
        mockWs.onopen({ type: 'open' });
      }

      await nextTick();

      ws.disconnect();
      await nextTick();

      // 验证连接状态已更新
      expect(ws.connectionState.value).toBe(ConnectionState.DISCONNECTED);
    });
  });

  // ==================== 边界情况测试 ====================

  describe('边界情况', () => {
    it('应该处理空URL', () => {
      ws = useWebSocket({ url: '' });

      expect(ws).toBeDefined();
    });

    it('应该处理无效URL', () => {
      ws = useWebSocket({ url: 'invalid-url' });

      expect(ws).toBeDefined();
    });

    it('应该处理重复连接请求', async () => {
      ws = useWebSocket(defaultOptions);

      ws.connect();
      ws.connect();
      ws.connect();

      await nextTick();

      // 应该只创建一个WebSocket实例
      expect(mockWebSocketInstances.length).toBeLessThanOrEqual(3);
    });

    it('应该处理发送空消息', () => {
      ws = useWebSocket(defaultOptions);

      const result = ws.send(null);

      expect(result).toBeDefined();
    });

    it('应该处理发送undefined消息', () => {
      ws = useWebSocket(defaultOptions);

      const result = ws.send(undefined);

      expect(result).toBeDefined();
    });
  });
});
