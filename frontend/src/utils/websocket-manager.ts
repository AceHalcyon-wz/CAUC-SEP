/**
 * @file websocket-manager.ts
 * @path frontend/src/utils/websocket-manager.ts
 * @description 全局WebSocket连接管理器，实现连接复用、订阅管理和自动重连
 * @author Agent
 * @date 2026-03-25
 * @dependencies vue
 */

import { ref, computed, readonly } from 'vue'

/**
 * WebSocket连接状态枚举
 */
export enum ConnectionState {
  DISCONNECTED = 'disconnected',
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  RECONNECTING = 'reconnecting',
  ERROR = 'error'
}

/**
 * 订阅配置接口
 */
export interface ISubscription {
  id: string
  topics: string[]
  callback: (data: unknown) => void
  isActive: boolean
  createdAt: number
}

/**
 * WebSocket管理器配置接口
 */
export interface IWebSocketManagerConfig {
  url: string
  reconnectInterval?: number
  maxReconnectAttempts?: number
  heartbeatInterval?: number
  enableAutoReconnect?: boolean
  enableHeartbeat?: boolean
  messageQueueSize?: number
}

/**
 * 连接统计信息接口
 */
export interface IConnectionStats {
  state: ConnectionState
  reconnectAttempts: number
  messageCount: number
  subscriptionCount: number
  lastMessageTime: number | null
  uptime: number
}

/**
 * 全局WebSocket连接管理器类
 * 
 * @description 单例模式，管理全局WebSocket连接，支持多页面复用、订阅管理和自动重连
 */
export class WebSocketManager {
  private static instance: WebSocketManager | null = null

  // WebSocket实例
  private ws: WebSocket | null = null

  // 配置
  private config: Required<IWebSocketManagerConfig> = {
    url: '',
    reconnectInterval: 3000,
    maxReconnectAttempts: 5,
    heartbeatInterval: 30000,
    enableAutoReconnect: true,
    enableHeartbeat: true,
    messageQueueSize: 100
  }

  // 响应式状态
  private connectionState = ref<ConnectionState>(ConnectionState.DISCONNECTED)
  private reconnectAttempts = ref(0)
  private messageCount = ref(0)
  private lastMessageTime = ref<number | null>(null)
  private connectionStartTime = ref<number | null>(null)

  // 订阅管理
  private subscriptions: Map<string, ISubscription> = new Map()
  private subscribedTopics: Set<string> = new Set()

  // 定时器
  private reconnectTimer: number | null = null
  private heartbeatTimer: number | null = null
  private heartbeatTimeoutTimer: number | null = null
  private waitingForPong = false

  // 消息队列
  private messageQueue: Array<{ data: unknown; timestamp: number }> = []

  // 事件监听器
  private stateListeners: Set<(state: ConnectionState) => void> = new Set()
  private messageListeners: Set<(data: unknown) => void> = new Set()

  /**
   * 私有构造函数（单例模式）
   */
  private constructor() {}

  /**
   * 获取单例实例
   */
  public static getInstance(): WebSocketManager {
    if (!WebSocketManager.instance) {
      WebSocketManager.instance = new WebSocketManager()
    }
    return WebSocketManager.instance
  }

  /**
   * 初始化WebSocket连接
   * 
   * @param config - 配置选项
   */
  public init(config: IWebSocketManagerConfig): void {
    if (!config.url) {
      throw new Error('[WebSocketManager] URL is required')
    }

    this.config = { ...this.config, ...config }
    
    // 如果已有连接，先断开
    if (this.ws) {
      this.disconnect()
    }

    this.connect()
  }

  /**
   * 建立连接
   */
  public connect(): void {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }

    this.updateState(ConnectionState.CONNECTING)

    try {
      this.ws = new WebSocket(this.config.url)
      this.setupEventListeners()
    } catch (error) {
      console.error('[WebSocketManager] 连接失败:', error)
      this.updateState(ConnectionState.ERROR)
      this.scheduleReconnect()
    }
  }

  /**
   * 断开连接
   */
  public disconnect(): void {
    this.stopReconnect()
    this.stopHeartbeat()
    
    if (this.ws) {
      // 取消所有订阅
      this.unsubscribeAll()
      
      this.ws.close()
      this.ws = null
    }

    this.updateState(ConnectionState.DISCONNECTED)
    this.connectionStartTime.value = null
  }

  /**
   * 订阅主题
   * 
   * @param topics - 主题列表
   * @param callback - 消息回调
   * @returns 订阅ID
   */
  public subscribe(topics: string[], callback: (data: unknown) => void): string {
    const id = `sub_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    
    const subscription: ISubscription = {
      id,
      topics,
      callback,
      isActive: true,
      createdAt: Date.now()
    }

    this.subscriptions.set(id, subscription)

    // 如果已连接，发送订阅请求
    if (this.isConnected) {
      this.sendSubscribeRequest(topics)
    }

    return id
  }

  /**
   * 取消订阅
   * 
   * @param subscriptionId - 订阅ID
   */
  public unsubscribe(subscriptionId: string): void {
    const subscription = this.subscriptions.get(subscriptionId)
    if (!subscription) return

    subscription.isActive = false
    this.subscriptions.delete(subscriptionId)

    // 检查是否还有其他订阅使用相同主题
    const topicsToUnsubscribe = subscription.topics.filter(topic => {
      let isUsed = false
      this.subscriptions.forEach(sub => {
        if (sub.isActive && sub.topics.includes(topic)) {
          isUsed = true
        }
      })
      return !isUsed
    })

    // 发送取消订阅请求
    if (this.isConnected && topicsToUnsubscribe.length > 0) {
      this.sendUnsubscribeRequest(topicsToUnsubscribe)
    }
  }

  /**
   * 取消所有订阅
   */
  public unsubscribeAll(): void {
    const allTopics = Array.from(this.subscribedTopics)
    
    if (this.isConnected && allTopics.length > 0) {
      this.sendUnsubscribeRequest(allTopics)
    }

    this.subscriptions.clear()
    this.subscribedTopics.clear()
  }

  /**
   * 发送消息
   * 
   * @param data - 消息数据
   * @returns 是否发送成功
   */
  public send(data: unknown): boolean {
    if (!this.isConnected || !this.ws) {
      // 加入队列
      if (this.messageQueue.length < this.config.messageQueueSize) {
        this.messageQueue.push({
          data,
          timestamp: Date.now()
        })
      }
      return false
    }

    try {
      const message = typeof data === 'string' ? data : JSON.stringify(data)
      this.ws.send(message)
      return true
    } catch (error) {
      console.error('[WebSocketManager] 发送消息失败:', error)
      return false
    }
  }

  /**
   * 添加状态监听器
   */
  public onStateChange(callback: (state: ConnectionState) => void): () => void {
    this.stateListeners.add(callback)
    return () => this.stateListeners.delete(callback)
  }

  /**
   * 添加消息监听器
   */
  public onMessage(callback: (data: unknown) => void): () => void {
    this.messageListeners.add(callback)
    return () => this.messageListeners.delete(callback)
  }

  /**
   * 获取连接状态
   */
  public get state(): ConnectionState {
    return this.connectionState.value
  }

  /**
   * 是否已连接
   */
  public get isConnected(): boolean {
    return this.connectionState.value === ConnectionState.CONNECTED
  }

  /**
   * 获取连接统计信息
   */
  public getStats(): IConnectionStats {
    return {
      state: this.connectionState.value,
      reconnectAttempts: this.reconnectAttempts.value,
      messageCount: this.messageCount.value,
      subscriptionCount: this.subscriptions.size,
      lastMessageTime: this.lastMessageTime.value,
      uptime: this.connectionStartTime.value 
        ? Date.now() - this.connectionStartTime.value 
        : 0
    }
  }

  /**
   * 获取响应式状态
   */
  public getReactiveState() {
    return {
      connectionState: readonly(this.connectionState),
      reconnectAttempts: readonly(this.reconnectAttempts),
      messageCount: readonly(this.messageCount),
      lastMessageTime: readonly(this.lastMessageTime),
      isConnected: computed(() => this.isConnected)
    }
  }

  // ==================== 私有方法 ====================

  /**
   * 设置事件监听器
   */
  private setupEventListeners(): void {
    if (!this.ws) return

    this.ws.onopen = () => {
      console.log('[WebSocketManager] 连接成功')
      this.updateState(ConnectionState.CONNECTED)
      this.reconnectAttempts.value = 0
      this.connectionStartTime.value = Date.now()

      // 重新订阅所有主题
      this.resubscribeAll()

      // 刷新消息队列
      this.flushMessageQueue()

      // 启动心跳
      if (this.config.enableHeartbeat) {
        this.startHeartbeat()
      }
    }

    this.ws.onmessage = (event) => {
      this.handleMessage(event.data)
    }

    this.ws.onerror = (error) => {
      console.error('[WebSocketManager] 连接错误:', error)
      this.updateState(ConnectionState.ERROR)
    }

    this.ws.onclose = (event) => {
      console.log('[WebSocketManager] 连接关闭:', event.code, event.reason)
      this.stopHeartbeat()
      this.updateState(ConnectionState.DISCONNECTED)

      // 自动重连
      if (this.config.enableAutoReconnect && !event.wasClean) {
        this.scheduleReconnect()
      }
    }
  }

  /**
   * 处理接收到的消息
   */
  private handleMessage(data: string): void {
    try {
      const message = JSON.parse(data)
      this.messageCount.value++
      this.lastMessageTime.value = Date.now()

      // 处理心跳响应
      if (message.type === 'pong') {
        this.handlePong()
        return
      }

      // 处理订阅确认
      if (message.type === 'subscription_confirmed') {
        console.log('[WebSocketManager] 订阅确认:', message.topics)
        return
      }

      // 分发消息给订阅者
      this.dispatchMessage(message)

      // 通知全局监听器
      this.messageListeners.forEach(callback => {
        try {
          callback(message)
        } catch (error) {
          console.error('[WebSocketManager] 消息监听器错误:', error)
        }
      })
    } catch (error) {
      console.error('[WebSocketManager] 消息解析错误:', error)
    }
  }

  /**
   * 分发消息给订阅者
   */
  private dispatchMessage(message: { type?: string; topic?: string; [key: string]: unknown }): void {
    const topic = message.type || message.topic
    if (!topic) return

    this.subscriptions.forEach(subscription => {
      if (subscription.isActive && subscription.topics.includes(topic)) {
        try {
          subscription.callback(message)
        } catch (error) {
          console.error('[WebSocketManager] 订阅回调错误:', error)
        }
      }
    })
  }

  /**
   * 更新连接状态
   */
  private updateState(state: ConnectionState): void {
    this.connectionState.value = state
    this.stateListeners.forEach(callback => {
      try {
        callback(state)
      } catch (error) {
        console.error('[WebSocketManager] 状态监听器错误:', error)
      }
    })
  }

  /**
   * 安排重连
   */
  private scheduleReconnect(): void {
    if (this.reconnectAttempts.value >= this.config.maxReconnectAttempts) {
      console.warn('[WebSocketManager] 已达到最大重连次数')
      return
    }

    if (this.reconnectTimer) return

    this.reconnectAttempts.value++
    this.updateState(ConnectionState.RECONNECTING)

    const delay = this.config.reconnectInterval * Math.pow(2, this.reconnectAttempts.value - 1)
    
    console.log(`[WebSocketManager] ${this.reconnectAttempts.value}/${this.config.maxReconnectAttempts} 次重连，延迟 ${delay}ms`)

    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null
      this.connect()
    }, delay)
  }

  /**
   * 停止重连
   */
  private stopReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.reconnectAttempts.value = 0
  }

  /**
   * 启动心跳
   */
  private startHeartbeat(): void {
    this.stopHeartbeat()

    this.heartbeatTimer = window.setInterval(() => {
      if (this.waitingForPong) {
        console.warn('[WebSocketManager] 心跳超时')
        this.ws?.close()
        return
      }

      this.send({ type: 'ping' })
      this.waitingForPong = true

      // 设置心跳超时
      this.heartbeatTimeoutTimer = window.setTimeout(() => {
        if (this.waitingForPong) {
          console.warn('[WebSocketManager] 心跳响应超时')
        }
      }, 5000)
    }, this.config.heartbeatInterval)
  }

  /**
   * 停止心跳
   */
  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
    if (this.heartbeatTimeoutTimer) {
      clearTimeout(this.heartbeatTimeoutTimer)
      this.heartbeatTimeoutTimer = null
    }
    this.waitingForPong = false
  }

  /**
   * 处理心跳响应
   */
  private handlePong(): void {
    this.waitingForPong = false
    if (this.heartbeatTimeoutTimer) {
      clearTimeout(this.heartbeatTimeoutTimer)
      this.heartbeatTimeoutTimer = null
    }
  }

  /**
   * 发送订阅请求
   */
  private sendSubscribeRequest(topics: string[]): void {
    this.send({
      action: 'subscribe',
      types: topics
    })
    topics.forEach(topic => this.subscribedTopics.add(topic))
  }

  /**
   * 发送取消订阅请求
   */
  private sendUnsubscribeRequest(topics: string[]): void {
    this.send({
      action: 'unsubscribe',
      types: topics
    })
    topics.forEach(topic => this.subscribedTopics.delete(topic))
  }

  /**
   * 重新订阅所有主题
   */
  private resubscribeAll(): void {
    const allTopics: string[] = []
    this.subscriptions.forEach(subscription => {
      if (subscription.isActive) {
        allTopics.push(...subscription.topics)
      }
    })

    if (allTopics.length > 0) {
      this.sendSubscribeRequest([...new Set(allTopics)])
    }
  }

  /**
   * 刷新消息队列
   */
  private flushMessageQueue(): void {
    while (this.messageQueue.length > 0) {
      const item = this.messageQueue.shift()
      if (item) {
        this.send(item.data)
      }
    }
  }
}

// 导出单例实例
export const wsManager = WebSocketManager.getInstance()

export default WebSocketManager
