/**
 * @file websocket.js
 * @path src/api/
 * @description WebSocket API接口封装
 * @author Agent
 * @date 2024-03-15
 */

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000/ws';

/**
 * WebSocket连接管理类
 */
export class WebSocketClient {
  constructor() {
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 3000;
    this.listeners = new Map();
    this.heartbeatInterval = null;
    this.isManualClose = false;
  }

  /**
   * 建立WebSocket连接
   *
   * @param {string} [url] - WebSocket URL
   * @returns {Promise<void>}
   */
  connect(url = WS_BASE_URL) {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(url);
        this.isManualClose = false;

        this.ws.onopen = () => {
          console.log('[WebSocket] Connected');
          this.reconnectAttempts = 0;
          this.startHeartbeat();
          this.emit('connected');
          resolve();
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event.data);
        };

        this.ws.onerror = (error) => {
          console.error('[WebSocket] Error:', error);
          this.emit('error', error);
          reject(error);
        };

        this.ws.onclose = () => {
          console.log('[WebSocket] Disconnected');
          this.stopHeartbeat();
          this.emit('disconnected');

          if (!this.isManualClose) {
            this.attemptReconnect();
          }
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * 断开WebSocket连接
   */
  disconnect() {
    this.isManualClose = true;
    this.stopHeartbeat();

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * 尝试重新连接
   *
   * @private
   */
  attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WebSocket] Max reconnect attempts reached');
      this.emit('reconnect_failed');
      return;
    }

    this.reconnectAttempts++;
    console.log(`[WebSocket] Reconnecting... Attempt ${this.reconnectAttempts}`);
    this.emit('reconnecting', this.reconnectAttempts);

    setTimeout(() => {
      this.connect().catch(() => {
        // 连接失败，将在onclose中再次尝试
      });
    }, this.reconnectDelay);
  }

  /**
   * 启动心跳检测
   *
   * @private
   */
  startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.send({ type: 'ping', timestamp: Date.now() });
      }
    }, 30000);
  }

  /**
   * 停止心跳检测
   *
   * @private
   */
  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  /**
   * 发送消息
   *
   * @param {Object} data - 要发送的数据
   */
  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('[WebSocket] Cannot send, connection not open');
    }
  }

  /**
   * 处理收到的消息
   *
   * @private
   * @param {string} data - 收到的数据
   */
  handleMessage(data) {
    try {
      const message = JSON.parse(data);
      this.emit(message.type, message);
    } catch (error) {
      console.error('[WebSocket] Failed to parse message:', error);
    }
  }

  /**
   * 订阅消息
   *
   * @param {string} event - 事件类型
   * @param {Function} callback - 回调函数
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  /**
   * 取消订阅
   *
   * @param {string} event - 事件类型
   * @param {Function} callback - 回调函数
   */
  off(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event);
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  /**
   * 触发事件
   *
   * @private
   * @param {string} event - 事件类型
   * @param {*} data - 事件数据
   */
  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error('[WebSocket] Error in event listener:', error);
        }
      });
    }
  }

  /**
   * 订阅设备状态更新
   *
   * @param {string} deviceId - 设备ID
   */
  subscribeDeviceStatus(deviceId) {
    this.send({
      type: 'subscribe',
      channel: 'device_status',
      device_id: deviceId
    });
  }

  /**
   * 取消订阅设备状态更新
   *
   * @param {string} deviceId - 设备ID
   */
  unsubscribeDeviceStatus(deviceId) {
    this.send({
      type: 'unsubscribe',
      channel: 'device_status',
      device_id: deviceId
    });
  }

  /**
   * 订阅波形数据
   *
   * @param {string} deviceId - 设备ID
   * @param {string} [dataType] - 数据类型
   */
  subscribeWaveform(deviceId, dataType = 'current') {
    this.send({
      type: 'subscribe',
      channel: 'waveform',
      device_id: deviceId,
      data_type: dataType
    });
  }

  /**
   * 取消订阅波形数据
   *
   * @param {string} deviceId - 设备ID
   */
  unsubscribeWaveform(deviceId) {
    this.send({
      type: 'unsubscribe',
      channel: 'waveform',
      device_id: deviceId
    });
  }

  /**
   * 设置推送频率
   *
   * @param {string} mode - 频率模式 ('fast' | 'normal' | 'slow')
   * @param {number} [interval] - 自定义间隔(ms)
   */
  setPushFrequency(mode, interval) {
    this.send({
      type: 'frequency_update',
      mode: mode,
      interval: interval
    });
  }
}

// 创建单例实例
export const wsClient = new WebSocketClient();

export default wsClient;
