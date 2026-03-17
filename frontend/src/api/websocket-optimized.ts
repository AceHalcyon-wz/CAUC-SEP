/**
 * @file websocket-optimized.ts
 * @path src/api/
 * @description 优化的 WebSocket 客户端，提供心跳机制、重连机制和类型化消息处理
 * @author Agent
 * @date 2024-03-16
 */

import { ref, computed, onMounted, onUnmounted, type Ref, type ComputedRef } from 'vue'

// ==================== 类型定义 ====================

/** WebSocket 连接状态 */
export type WebSocketConnectionState = 'disconnected' | 'connecting' | 'connected' | 'reconnecting'

/** WebSocket 消息类型 */
export type WebSocketMessageType =
  | 'ping'
  | 'pong'
  | 'subscribe'
  | 'unsubscribe'
  | 'device_status'
  | 'waveform'
  | 'frequency_update'
  | 'error'
  | 'connected'
  | 'disconnected'
  | 'reconnecting'
  | 'reconnect_failed'

/** WebSocket 基础消息 */
export interface WebSocketMessage<T = unknown> {
  /** 消息类型 */
  type: WebSocketMessageType
  /** 消息数据 */
  data?: T
  /** 时间戳 */
  timestamp?: number
  /** 设备 ID */
  device_id?: string
  /** 通道 */
  channel?: string
}

/** 设备状态消息 */
export interface DeviceStatusMessage extends WebSocketMessage {
  type: 'device_status'
  device_id: string
  data: {
    status: string
    connected: boolean
    [key: string]: unknown
  }
}

/** 波形数据消息 */
export interface WaveformMessage extends WebSocketMessage {
  type: 'waveform'
  device_id: string
  data: {
    values: number[]
    timestamp: number
    [key: string]: unknown
  }
}

/** 推送频率模式 */
export type PushFrequencyMode = 'fast' | 'normal' | 'slow'

/** WebSocket 配置 */
export interface WebSocketConfig {
  /** WebSocket URL */
  url?: string
  /** 心跳间隔（毫秒） */
  heartbeatInterval?: number
  /** 最大重连次数 */
  maxReconnectAttempts?: number
  /** 重连延迟基数（毫秒） */
  reconnectDelay?: number
  /** 最大重连延迟（毫秒） */
  maxReconnectDelay?: number
  /** 是否自动连接 */
  autoConnect?: boolean
}

/** WebSocket 状态 */
export interface WebSocketState {
  /** 连接状态 */
  connectionState: Ref<WebSocketConnectionState>
  /** 是否已连接 */
  isConnected: ComputedRef<boolean>
  /** 是否正在连接 */
  isConnecting: ComputedRef<boolean>
  /** 重连次数 */
  reconnectAttempts: Ref<number>
  /** 最后错误 */
  lastError: Ref<string | null>
}

/** WebSocket 操作方法 */
export interface WebSocketActions {
  /** 连接 */
  connect: () => Promise<void>
  /** 断开连接 */
  disconnect: () => void
  /** 发送消息 */
  send: <T = unknown>(data: T) => void
  /** 订阅事件 */
  on: <T = unknown>(event: string, callback: (data: T) => void) => void
  /** 取消订阅 */
  off: <T = unknown>(event: string, callback: (data: T) => void) => void
  /** 订阅设备状态 */
  subscribeDeviceStatus: (deviceId: string) => void
  /** 取消订阅设备状态 */
  unsubscribeDeviceStatus: (deviceId: string) => void
  /** 订阅波形数据 */
  subscribeWaveform: (deviceId: string, dataType?: string) => void
  /** 取消订阅波形数据 */
  unsubscribeWaveform: (deviceId: string) => void
  /** 设置推送频率 */
  setPushFrequency: (mode: PushFrequencyMode, interval?: number) => void
}

/** useOptimizedWebSocket 返回值 */
export type UseOptimizedWebSocketReturn = WebSocketState & WebSocketActions

// ==================== WebSocket 客户端类 ====================

/**
 * 优化的 WebSocket 客户端类
 */
export class OptimizedWebSocketClient {
  private ws: WebSocket | null = null
  public readonly config: Required<WebSocketConfig>
  private listeners: Map<string, Array<(data: unknown) => void>> = new Map()
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private isManualClose = false
  private reconnectAttempts = 0

  /** 连接状态 */
  public connectionState: Ref<WebSocketConnectionState> = ref('disconnected')

  /** 最后错误 */
  public lastError: Ref<string | null> = ref(null)

  constructor(config: WebSocketConfig = {}) {
    this.config = {
      url: config.url || import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000/ws',
      heartbeatInterval: config.heartbeatInterval ?? 30000,
      maxReconnectAttempts: config.maxReconnectAttempts ?? 5,
      reconnectDelay: config.reconnectDelay ?? 1000,
      maxReconnectDelay: config.maxReconnectDelay ?? 30000,
      autoConnect: config.autoConnect ?? false,
    }

    if (this.config.autoConnect) {
      this.connect()
    }
  }

  /**
   * 建立 WebSocket 连接
   */
  async connect(): Promise<void> {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return
    }

    this.connectionState.value = 'connecting'
    this.isManualClose = false

    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.config.url)

        this.ws.onopen = () => {
          console.log('[WebSocket] Connected')
          this.connectionState.value = 'connected'
          this.reconnectAttempts = 0
          this.startHeartbeat()
          this.emit('connected', { timestamp: Date.now() })
          resolve()
        }

        this.ws.onmessage = (event) => {
          this.handleMessage(event.data)
        }

        this.ws.onerror = (error) => {
          console.error('[WebSocket] Error:', error)
          this.lastError.value = 'WebSocket 连接错误'
          this.emit('error', error)
          reject(error)
        }

        this.ws.onclose = () => {
          console.log('[WebSocket] Disconnected')
          this.stopHeartbeat()
          this.connectionState.value = 'disconnected'
          this.emit('disconnected', { timestamp: Date.now() })

          if (!this.isManualClose) {
            this.attemptReconnect()
          }
        }
      } catch (error) {
        this.connectionState.value = 'disconnected'
        reject(error)
      }
    })
  }

  /**
   * 断开 WebSocket 连接
   */
  disconnect(): void {
    this.isManualClose = true
    this.stopHeartbeat()
    this.clearReconnectTimer()

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }

    this.connectionState.value = 'disconnected'
  }

  /**
   * 尝试重新连接
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      console.error('[WebSocket] Max reconnect attempts reached')
      this.connectionState.value = 'disconnected'
      this.emit('reconnect_failed', { attempts: this.reconnectAttempts })
      return
    }

    this.reconnectAttempts++
    this.connectionState.value = 'reconnecting'
    console.log(`[WebSocket] Reconnecting... Attempt ${this.reconnectAttempts}`)
    this.emit('reconnecting', { attempt: this.reconnectAttempts })

    // 指数退避
    const delay = Math.min(
      this.config.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
      this.config.maxReconnectDelay
    )

    this.reconnectTimer = setTimeout(() => {
      this.connect().catch(() => {
        // 连接失败，将在 onclose 中再次尝试
      })
    }, delay)
  }

  /**
   * 清除重连定时器
   */
  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  /**
   * 启动心跳检测
   */
  private startHeartbeat(): void {
    this.stopHeartbeat()
    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.send({ type: 'ping', timestamp: Date.now() })
      }
    }, this.config.heartbeatInterval)
  }

  /**
   * 停止心跳检测
   */
  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  /**
   * 发送消息
   */
  send<T = unknown>(data: T): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    } else {
      console.warn('[WebSocket] Cannot send, connection not open')
    }
  }

  /**
   * 处理收到的消息
   */
  private handleMessage(data: string): void {
    try {
      const message = JSON.parse(data) as WebSocketMessage

      // 处理 pong 响应
      if (message.type === 'pong') {
        return
      }

      this.emit(message.type, message)

      // 同时触发通用消息事件
      this.emit('message', message)
    } catch (error) {
      console.error('[WebSocket] Failed to parse message:', error)
    }
  }

  /**
   * 订阅事件
   */
  on<T = unknown>(event: string, callback: (data: T) => void): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event)?.push(callback as (data: unknown) => void)
  }

  /**
   * 取消订阅
   */
  off<T = unknown>(event: string, callback: (data: T) => void): void {
    const callbacks = this.listeners.get(event)
    if (callbacks) {
      const index = callbacks.indexOf(callback as (data: unknown) => void)
      if (index > -1) {
        callbacks.splice(index, 1)
      }
    }
  }

  /**
   * 触发事件
   */
  private emit(event: string, data: unknown): void {
    const callbacks = this.listeners.get(event)
    if (callbacks) {
      callbacks.forEach((callback) => {
        try {
          callback(data)
        } catch (error) {
          console.error('[WebSocket] Error in event listener:', error)
        }
      })
    }
  }

  /**
   * 订阅设备状态更新
   */
  subscribeDeviceStatus(deviceId: string): void {
    this.send({
      type: 'subscribe',
      channel: 'device_status',
      device_id: deviceId,
    })
  }

  /**
   * 取消订阅设备状态更新
   */
  unsubscribeDeviceStatus(deviceId: string): void {
    this.send({
      type: 'unsubscribe',
      channel: 'device_status',
      device_id: deviceId,
    })
  }

  /**
   * 订阅波形数据
   */
  subscribeWaveform(deviceId: string, dataType = 'current'): void {
    this.send({
      type: 'subscribe',
      channel: 'waveform',
      device_id: deviceId,
      data_type: dataType,
    })
  }

  /**
   * 取消订阅波形数据
   */
  unsubscribeWaveform(deviceId: string): void {
    this.send({
      type: 'unsubscribe',
      channel: 'waveform',
      device_id: deviceId,
    })
  }

  /**
   * 设置推送频率
   */
  setPushFrequency(mode: PushFrequencyMode, interval?: number): void {
    this.send({
      type: 'frequency_update',
      mode,
      interval,
    })
  }
}

// ==================== 组合式函数 ====================

/**
 * 优化的 WebSocket 组合式函数
 *
 * @param config - WebSocket 配置
 * @returns WebSocket 状态和操作方法
 *
 * @example
 * ```typescript
 * const ws = useOptimizedWebSocket({ autoConnect: true })
 *
 * // 监听连接状态
 * watch(ws.isConnected, (connected) => {
 *   console.log('Connected:', connected)
 * })
 *
 * // 订阅设备状态
 * ws.on('device_status', (data) => {
 *   console.log('Device status:', data)
 * })
 *
 * // 组件卸载时自动断开
 * onUnmounted(() => ws.disconnect())
 * ```
 */
export function useOptimizedWebSocket(config: WebSocketConfig = {}): UseOptimizedWebSocketReturn {
  const client = new OptimizedWebSocketClient(config)

  const connectionState = client.connectionState
  const lastError = client.lastError
  const reconnectAttempts = ref(0)

  const isConnected = computed(() => connectionState.value === 'connected')
  const isConnecting = computed(() => connectionState.value === 'connecting' || connectionState.value === 'reconnecting')

  // 监听重连事件
  client.on('reconnecting', (data: { attempt: number }) => {
    reconnectAttempts.value = data.attempt
  })

  client.on('reconnect_failed', () => {
    reconnectAttempts.value = client.config.maxReconnectAttempts
  })

  // 组件挂载时自动连接
  onMounted(() => {
    if (config.autoConnect !== false) {
      client.connect().catch((error) => {
        console.error('[useOptimizedWebSocket] Failed to connect:', error)
      })
    }
  })

  // 组件卸载时断开连接
  onUnmounted(() => {
    client.disconnect()
  })

  return {
    // 状态
    connectionState,
    isConnected,
    isConnecting,
    reconnectAttempts,
    lastError,

    // 操作方法
    connect: () => client.connect(),
    disconnect: () => client.disconnect(),
    send: <T = unknown>(data: T) => client.send(data),
    on: <T = unknown>(event: string, callback: (data: T) => void) => client.on(event, callback),
    off: <T = unknown>(event: string, callback: (data: T) => void) => client.off(event, callback),
    subscribeDeviceStatus: (deviceId: string) => client.subscribeDeviceStatus(deviceId),
    unsubscribeDeviceStatus: (deviceId: string) => client.unsubscribeDeviceStatus(deviceId),
    subscribeWaveform: (deviceId: string, dataType?: string) => client.subscribeWaveform(deviceId, dataType),
    unsubscribeWaveform: (deviceId: string) => client.unsubscribeWaveform(deviceId),
    setPushFrequency: (mode: PushFrequencyMode, interval?: number) => client.setPushFrequency(mode, interval),
  }
}

// ==================== 单例实例 ====================

/** 全局 WebSocket 客户端实例 */
export const wsClient = new OptimizedWebSocketClient()

export default wsClient
