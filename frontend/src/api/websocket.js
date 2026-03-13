/**
 * @file websocket.js
 * @path src/api/
 * @description WebSocket连接管理API接口封装
 * @author Agent
 * @date 2024-03-14
 * @dependencies utils/apiRequest
 */

import { get, post } from '../utils/apiRequest';

/**
 * WebSocket连接状态枚举
 * @enum {string}
 */
export const WebSocketState = {
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  DISCONNECTED: 'disconnected',
  ERROR: 'error',
  RECONNECTING: 'reconnecting'
};

/**
 * 获取WebSocket连接状态
 *
 * @returns {Promise<Object|null>} WebSocket连接状态信息
 */
export async function getWebSocketStatus() {
  const result = await get('/api/v1/websocket/status', null, {
    onError: (msg) => console.error('[WebSocketAPI] Get status error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取WebSocket连接URL
 *
 * @param {Object} params - 连接参数
 * @param {string} [params.channel] - 订阅通道
 * @returns {Promise<Object|null>} 连接URL信息
 */
export async function getWebSocketUrl(params = {}) {
  const result = await get('/api/v1/websocket/url', params, {
    onError: (msg) => console.error('[WebSocketAPI] Get URL error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 订阅数据通道
 *
 * @param {Object} params - 订阅参数
 * @param {string} params.channel - 通道名称
 * @param {Object} [params.filters] - 数据过滤条件
 * @returns {Promise<Object|null>} 订阅结果
 */
export async function subscribeChannel(params) {
  const result = await post('/api/v1/websocket/subscribe', params, {
    onError: (msg) => console.error('[WebSocketAPI] Subscribe error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 取消订阅数据通道
 *
 * @param {Object} params - 取消订阅参数
 * @param {string} params.channel - 通道名称
 * @returns {Promise<boolean>} 是否取消成功
 */
export async function unsubscribeChannel(params) {
  const result = await post('/api/v1/websocket/unsubscribe', params, {
    onError: (msg) => console.error('[WebSocketAPI] Unsubscribe error:', msg)
  });

  return result.success;
}

/**
 * 获取已订阅的通道列表
 *
 * @returns {Promise<Object|null>} 已订阅通道列表
 */
export async function getSubscribedChannels() {
  const result = await get('/api/v1/websocket/channels', null, {
    onError: (msg) => console.error('[WebSocketAPI] Get channels error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取可用的数据通道列表
 *
 * @returns {Promise<Object|null>} 可用通道列表
 */
export async function getAvailableChannels() {
  const result = await get('/api/v1/websocket/channels/available', null, {
    onError: (msg) => console.error('[WebSocketAPI] Get available channels error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 发送WebSocket消息
 *
 * @param {Object} params - 消息参数
 * @param {string} params.channel - 目标通道
 * @param {string} params.type - 消息类型
 * @param {Object} params.payload - 消息内容
 * @returns {Promise<boolean>} 是否发送成功
 */
export async function sendWebSocketMessage(params) {
  const result = await post('/api/v1/websocket/send', params, {
    onError: (msg) => console.error('[WebSocketAPI] Send message error:', msg)
  });

  return result.success;
}

/**
 * 获取WebSocket连接历史
 *
 * @param {Object} params - 查询参数
 * @param {number} [params.limit=10] - 返回记录数量
 * @returns {Promise<Object|null>} 连接历史记录
 */
export async function getConnectionHistory(params = {}) {
  const result = await get('/api/v1/websocket/history', params, {
    onError: (msg) => console.error('[WebSocketAPI] Get history error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 重连WebSocket
 *
 * @returns {Promise<Object|null>} 重连结果
 */
export async function reconnectWebSocket() {
  const result = await post('/api/v1/websocket/reconnect', null, {
    onError: (msg) => console.error('[WebSocketAPI] Reconnect error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 关闭WebSocket连接
 *
 * @returns {Promise<boolean>} 是否关闭成功
 */
export async function closeWebSocket() {
  const result = await post('/api/v1/websocket/close', null, {
    onError: (msg) => console.error('[WebSocketAPI] Close error:', msg)
  });

  return result.success;
}

/**
 * 获取WebSocket配置
 *
 * @returns {Promise<Object|null>} WebSocket配置
 */
export async function getWebSocketConfig() {
  const result = await get('/api/v1/websocket/config', null, {
    onError: (msg) => console.error('[WebSocketAPI] Get config error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 更新WebSocket配置
 *
 * @param {Object} config - 配置参数
 * @param {number} [config.heartbeat_interval] - 心跳间隔（毫秒）
 * @param {number} [config.reconnect_delay] - 重连延迟（毫秒）
 * @param {number} [config.max_reconnect_attempts] - 最大重连次数
 * @returns {Promise<Object|null>} 更新后的配置
 */
export async function updateWebSocketConfig(config) {
  const result = await post('/api/v1/websocket/config', config, {
    onError: (msg) => console.error('[WebSocketAPI] Update config error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取通道统计信息
 *
 * @param {string} channel - 通道名称
 * @returns {Promise<Object|null>} 统计信息
 */
export async function getChannelStatistics(channel) {
  const result = await get(`/api/v1/websocket/channel/${channel}/statistics`, null, {
    onError: (msg) => console.error('[WebSocketAPI] Get channel statistics error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 清除通道缓冲区
 *
 * @param {string} channel - 通道名称
 * @returns {Promise<boolean>} 是否清除成功
 */
export async function clearChannelBuffer(channel) {
  const result = await post(`/api/v1/websocket/channel/${channel}/clear`, null, {
    onError: (msg) => console.error('[WebSocketAPI] Clear buffer error:', msg)
  });

  return result.success;
}

/**
 * 创建WebSocket客户端管理器
 *
 * @param {Object} options - 客户端选项
 * @param {string} options.url - WebSocket服务器URL
 * @param {Function} [options.onMessage] - 消息回调
 * @param {Function} [options.onOpen] - 连接打开回调
 * @param {Function} [options.onClose] - 连接关闭回调
 * @param {Function} [options.onError] - 错误回调
 * @param {number} [options.reconnectInterval=3000] - 重连间隔
 * @param {number} [options.maxReconnectAttempts=5] - 最大重连次数
 * @returns {Object} WebSocket客户端管理器实例
 */
export function createWebSocketManager(options) {
  const {
    url,
    onMessage,
    onOpen,
    onClose,
    onError,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5
  } = options;

  let ws = null;
  let reconnectAttempts = 0;
  let isManualClose = false;
  let messageQueue = [];

  /**
   * 连接WebSocket
   */
  function connect() {
    if (ws && ws.readyState === WebSocket.OPEN) {
      console.warn('[WebSocketManager] Already connected');
      return;
    }

    isManualClose = false;
    ws = new WebSocket(url);

    ws.onopen = () => {
      console.log('[WebSocketManager] Connected');
      reconnectAttempts = 0;

      // 发送队列中的消息
      while (messageQueue.length > 0) {
        const message = messageQueue.shift();
        ws.send(JSON.stringify(message));
      }

      if (onOpen) onOpen();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (onMessage) onMessage(data);
      } catch (error) {
        console.error('[WebSocketManager] Parse message error:', error);
      }
    };

    ws.onclose = (event) => {
      console.log('[WebSocketManager] Closed:', event.code, event.reason);

      if (onClose) onClose(event);

      // 自动重连
      if (!isManualClose && reconnectAttempts < maxReconnectAttempts) {
        reconnectAttempts++;
        console.log(`[WebSocketManager] Reconnecting... (${reconnectAttempts}/${maxReconnectAttempts})`);
        setTimeout(connect, reconnectInterval);
      }
    };

    ws.onerror = (error) => {
      console.error('[WebSocketManager] Error:', error);
      if (onError) onError(error);
    };
  }

  /**
   * 断开连接
   */
  function disconnect() {
    isManualClose = true;
    if (ws) {
      ws.close();
      ws = null;
    }
  }

  /**
   * 发送消息
   *
   * @param {Object} message - 消息内容
   */
  function send(message) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message));
    } else {
      // 连接未就绪，加入队列
      messageQueue.push(message);
      console.warn('[WebSocketManager] Connection not ready, message queued');
    }
  }

  /**
   * 获取连接状态
   *
   * @returns {string} 连接状态
   */
  function getState() {
    if (!ws) return WebSocketState.DISCONNECTED;

    switch (ws.readyState) {
      case WebSocket.CONNECTING:
        return WebSocketState.CONNECTING;
      case WebSocket.OPEN:
        return WebSocketState.CONNECTED;
      case WebSocket.CLOSING:
      case WebSocket.CLOSED:
        return WebSocketState.DISCONNECTED;
      default:
        return WebSocketState.DISCONNECTED;
    }
  }

  /**
   * 检查是否已连接
   *
   * @returns {boolean} 是否已连接
   */
  function isConnected() {
    return ws && ws.readyState === WebSocket.OPEN;
  }

  return {
    connect,
    disconnect,
    send,
    getState,
    isConnected
  };
}
