/**
 * @file websocket.ts
 * @path frontend/src/types/websocket.ts
 * @description WebSocket消息类型定义，包含设备状态推送、实验数据流、系统通知等消息类型
 * @author Agent
 * @date 2026-03-25
 * @dependencies ./api, ./device
 */

import type { ID } from './api'
import type { DeviceType, DeviceStatus } from './device'

// ==================== WebSocket消息类型枚举 ====================

/** WebSocket消息类型 */
export enum WSMessageType {
  /** 心跳 */
  PING = 'ping',
  /** 心跳响应 */
  PONG = 'pong',
  /** 设备状态更新 */
  DEVICE_STATUS = 'device_status',
  /** 设备连接 */
  DEVICE_CONNECT = 'device_connect',
  /** 设备断开 */
  DEVICE_DISCONNECT = 'device_disconnect',
  /** 设备报警 */
  DEVICE_ALARM = 'device_alarm',
  /** 实验数据 */
  EXPERIMENT_DATA = 'experiment_data',
  /** 实验状态 */
  EXPERIMENT_STATUS = 'experiment_status',
  /** 系统通知 */
  SYSTEM_NOTIFICATION = 'system_notification',
  /** 错误消息 */
  ERROR = 'error',
}

/** WebSocket基础消息结构 */
export interface WSMessage<T = unknown> {
  /** 消息类型 */
  type: WSMessageType | string
  /** 消息数据 */
  data?: T
  /** 时间戳 */
  timestamp: string
  /** 消息ID */
  messageId?: ID
}

/** WebSocket心跳消息 */
export interface WSPingMessage {
  type: WSMessageType.PING
  timestamp: string
}

/** WebSocket心跳响应消息 */
export interface WSPongMessage {
  type: WSMessageType.PONG
  timestamp: string
}

// ==================== 设备状态消息类型 ====================

/** 电机状态数据 */
export interface MotorStatusData {
  /** 设备ID */
  device_id: string
  /** 设备类型 */
  device_type: 'stepper'
  /** 当前位置（步数） */
  position_steps: number
  /** 当前位置（mm） */
  position_mm: number
  /** 目标位置（mm） */
  target_position_mm?: number
  /** 当前速度（mm/s） */
  velocity_mm_s: number
  /** 是否正在移动 */
  is_moving: boolean
  /** 设备状态 */
  status: DeviceStatus
  /** 是否已连接 */
  connected: boolean
  /** 是否仿真模式 */
  simulation: boolean
  /** 状态字 */
  status_word?: number
  /** 报警代码 */
  alarm_code?: number
  /** 报警文本 */
  alarm_text?: string
}

/** 电磁铁状态数据 */
export interface ElectromagnetStatusData {
  /** 设备ID */
  device_id: string
  /** 设备类型 */
  device_type: 'electromagnet'
  /** 当前电流（A） */
  current: number
  /** 目标电流（A） */
  target_current: number
  /** 最大电流（A） */
  max_current: number
  /** 是否输出使能 */
  output_enabled: boolean
  /** 设备状态 */
  status: DeviceStatus
  /** 是否已连接 */
  connected: boolean
  /** 是否仿真模式 */
  simulation: boolean
}

/** 温度控制器状态数据 */
export interface TemperatureStatusData {
  /** 设备ID */
  device_id: string
  /** 设备类型 */
  device_type: 'temperature'
  /** 当前温度（°C） */
  current_temp: number
  /** 目标温度（°C） */
  target_temp: number
  /** 是否正在加热 */
  is_heating: boolean
  /** 是否正在冷却 */
  is_cooling: boolean
  /** 设备状态 */
  status: DeviceStatus
  /** 是否已连接 */
  connected: boolean
  /** 是否仿真模式 */
  simulation: boolean
}

/** 压电控制器状态数据 */
export interface PiezoStatusData {
  /** 设备ID */
  device_id: string
  /** 设备类型 */
  device_type: 'piezo'
  /** 各通道电压（V） */
  voltages: number[]
  /** 各通道位移（μm） */
  displacements: number[]
  /** 设备状态 */
  status: DeviceStatus
  /** 是否已连接 */
  connected: boolean
  /** 是否仿真模式 */
  simulation: boolean
}

/** 皮安表状态数据 */
export interface AmmeterStatusData {
  /** 设备ID */
  device_id: string
  /** 设备类型 */
  device_type: 'ammeter'
  /** 当前电流（A） */
  current: number
  /** 电流范围 */
  range: string
  /** 采样率（Hz） */
  sample_rate: number
  /** 是否正在采集 */
  is_sampling: boolean
  /** 设备状态 */
  status: DeviceStatus
  /** 是否已连接 */
  connected: boolean
  /** 是否仿真模式 */
  simulation: boolean
  /** 多通道数据 */
  channels?: Array<{
    /** 通道索引 */
    index: number
    /** 通道电流值 */
    current: number
  }>
}

/** 设备状态联合类型 */
export type DeviceStatusData =
  | MotorStatusData
  | ElectromagnetStatusData
  | TemperatureStatusData
  | PiezoStatusData
  | AmmeterStatusData

/** 设备状态更新消息 */
export interface WSDeviceStatusMessage extends WSMessage<DeviceStatusData> {
  type: WSMessageType.DEVICE_STATUS
}

// ==================== 设备连接消息类型 ====================

/** 设备连接成功数据 */
export interface DeviceConnectSuccessData {
  /** 设备ID */
  device_id: string
  /** 设备类型 */
  device_type: DeviceType
  /** 连接时间 */
  connected_at: string
  /** 是否仿真模式 */
  simulation: boolean
}

/** 设备连接失败数据 */
export interface DeviceConnectFailureData {
  /** 设备ID */
  device_id?: string
  /** 设备类型 */
  device_type?: DeviceType
  /** 错误消息 */
  error_message: string
  /** 错误代码 */
  error_code?: string
}

/** 设备连接消息 */
export interface WSDeviceConnectMessage extends WSMessage<DeviceConnectSuccessData | DeviceConnectFailureData> {
  type: WSMessageType.DEVICE_CONNECT
  /** 是否成功 */
  success: boolean
}

/** 设备断开连接数据 */
export interface DeviceDisconnectData {
  /** 设备ID */
  device_id: string
  /** 设备类型 */
  device_type: DeviceType
  /** 断开原因 */
  reason: 'user' | 'timeout' | 'error' | 'system'
  /** 错误消息 */
  error_message?: string
}

/** 设备断开连接消息 */
export interface WSDeviceDisconnectMessage extends WSMessage<DeviceDisconnectData> {
  type: WSMessageType.DEVICE_DISCONNECT
}

// ==================== 设备报警消息类型 ====================

/** 设备报警数据 */
export interface DeviceAlarmData {
  /** 设备ID */
  device_id: string
  /** 设备类型 */
  device_type: DeviceType
  /** 报警代码 */
  alarm_code: number
  /** 报警文本 */
  alarm_text: string
  /** 报警级别 */
  level: 'info' | 'warning' | 'error' | 'critical'
  /** 是否需要处理 */
  requires_action?: boolean
  /** 建议操作 */
  suggested_action?: string
}

/** 设备报警消息 */
export interface WSDeviceAlarmMessage extends WSMessage<DeviceAlarmData> {
  type: WSMessageType.DEVICE_ALARM
}

// ==================== 实验数据消息类型 ====================

/** 实验数据点（WebSocket专用） */
export interface WSExperimentDataPoint {
  /** 时间戳 */
  timestamp: string
  /** 序号 */
  index: number
  /** 磁场强度（T） */
  field?: number
  /** 磁化强度（A/m） */
  magnetization?: number
  /** 电流（A） */
  current?: number
  /** 温度（°C） */
  temperature?: number
  /** 位移（μm） */
  displacement?: number
  /** 电压（V） */
  voltage?: number
  /** 其他数据 */
  extra?: Record<string, number>
}

/** 实验数据消息数据 */
export interface ExperimentDataMessageData {
  /** 实验ID */
  experiment_id: ID
  /** 数据点列表 */
  data_points: WSExperimentDataPoint[]
  /** 是否实时数据 */
  realtime?: boolean
  /** 数据完成标志 */
  complete?: boolean
}

/** 实验数据消息 */
export interface WSExperimentDataMessage extends WSMessage<ExperimentDataMessageData> {
  type: WSMessageType.EXPERIMENT_DATA
}

/** 实验状态数据 */
export interface ExperimentStatusData {
  /** 实验ID */
  experiment_id: ID
  /** 实验状态 */
  status: 'running' | 'paused' | 'completed' | 'failed' | 'cancelled'
  /** 进度（0-100） */
  progress: number
  /** 当前阶段 */
  stage?: string
  /** 已用时间（s） */
  elapsed_time: number
  /** 预计剩余时间（s） */
  estimated_remaining?: number
  /** 已采集数据点数 */
  data_points_collected: number
  /** 错误消息 */
  error_message?: string
}

/** 实验状态消息 */
export interface WSExperimentStatusMessage extends WSMessage<ExperimentStatusData> {
  type: WSMessageType.EXPERIMENT_STATUS
}

// ==================== 系统通知消息类型 ====================

/** 系统通知数据 */
export interface SystemNotificationData {
  /** 通知ID */
  notification_id: ID
  /** 通知类型 */
  notification_type: 'info' | 'success' | 'warning' | 'error'
  /** 通知标题 */
  title: string
  /** 通知内容 */
  message: string
  /** 持续时间（ms），0表示不自动关闭 */
  duration?: number
  /** 是否可关闭 */
  closable?: boolean
  /** 关联操作 */
  action?: {
    /** 操作文本 */
    text: string
    /** 操作类型 */
    type: 'link' | 'callback'
    /** 操作目标 */
    target?: string
  }
}

/** 系统通知消息 */
export interface WSSystemNotificationMessage extends WSMessage<SystemNotificationData> {
  type: WSMessageType.SYSTEM_NOTIFICATION
}

// ==================== 错误消息类型 ====================

/** WebSocket错误数据 */
export interface WSErrorData {
  /** 错误代码 */
  error_code: string
  /** 错误消息 */
  error_message: string
  /** 错误详情 */
  details?: Record<string, unknown>
  /** 是否可重试 */
  retryable?: boolean
  /** 重试延迟（ms） */
  retry_delay?: number
}

/** WebSocket错误消息 */
export interface WSErrorMessage extends WSMessage<WSErrorData> {
  type: WSMessageType.ERROR
}

// ==================== WebSocket连接状态类型 ====================

/** WebSocket连接状态 */
export enum WSConnectionState {
  /** 未连接 */
  DISCONNECTED = 'disconnected',
  /** 连接中 */
  CONNECTING = 'connecting',
  /** 已连接 */
  CONNECTED = 'connected',
  /** 重连中 */
  RECONNECTING = 'reconnecting',
  /** 错误 */
  ERROR = 'error',
}

/** WebSocket连接配置 */
export interface WSConnectionConfig {
  /** WebSocket URL */
  url: string
  /** 是否自动重连 */
  autoReconnect?: boolean
  /** 重连间隔（ms） */
  reconnectInterval?: number
  /** 最大重连次数 */
  maxReconnectAttempts?: number
  /** 心跳间隔（ms） */
  heartbeatInterval?: number
  /** 连接超时（ms） */
  connectionTimeout?: number
  /** 是否启用日志 */
  enableLog?: boolean
  /** 订阅主题列表 */
  subscribeTopics?: string[]
}

/** WebSocket连接状态信息 */
export interface WSConnectionInfo {
  /** 连接状态 */
  state: WSConnectionState
  /** 连接URL */
  url: string
  /** 是否已连接 */
  connected: boolean
  /** 重连次数 */
  reconnectAttempts: number
  /** 最后连接时间 */
  lastConnectedAt?: string
  /** 最后断开时间 */
  lastDisconnectedAt?: string
  /** 错误消息 */
  errorMessage?: string
}

// ==================== WebSocket订阅类型 ====================

/** WebSocket订阅主题 */
export interface WSSubscribeTopic {
  /** 主题名称 */
  topic: string
  /** 订阅参数 */
  params?: Record<string, unknown>
  /** 是否启用 */
  enabled?: boolean
}

/** WebSocket订阅消息 */
export interface WSSubscribeMessage {
  /** 消息类型 */
  type: 'subscribe'
  /** 订阅主题 */
  topics: WSSubscribeTopic[]
}

/** WebSocket取消订阅消息 */
export interface WSUnsubscribeMessage {
  /** 消息类型 */
  type: 'unsubscribe'
  /** 取消订阅的主题 */
  topics: string[]
}

// ==================== WebSocket消息联合类型 ====================

/** 所有WebSocket消息联合类型 */
export type AnyWSMessage =
  | WSPingMessage
  | WSPongMessage
  | WSDeviceStatusMessage
  | WSDeviceConnectMessage
  | WSDeviceDisconnectMessage
  | WSDeviceAlarmMessage
  | WSExperimentDataMessage
  | WSExperimentStatusMessage
  | WSSystemNotificationMessage
  | WSErrorMessage
  | WSMessage

// ==================== WebSocket消息处理器类型 ====================

/** WebSocket消息处理器 */
export type WSMessageHandler<T = unknown> = (message: WSMessage<T>) => void

/** WebSocket事件处理器映射 */
export interface WSHandlerMap {
  [WSMessageType.PING]?: WSMessageHandler<void>
  [WSMessageType.PONG]?: WSMessageHandler<void>
  [WSMessageType.DEVICE_STATUS]?: WSMessageHandler<DeviceStatusData>
  [WSMessageType.DEVICE_CONNECT]?: WSMessageHandler<DeviceConnectSuccessData | DeviceConnectFailureData>
  [WSMessageType.DEVICE_DISCONNECT]?: WSMessageHandler<DeviceDisconnectData>
  [WSMessageType.DEVICE_ALARM]?: WSMessageHandler<DeviceAlarmData>
  [WSMessageType.EXPERIMENT_DATA]?: WSMessageHandler<ExperimentDataMessageData>
  [WSMessageType.EXPERIMENT_STATUS]?: WSMessageHandler<ExperimentStatusData>
  [WSMessageType.SYSTEM_NOTIFICATION]?: WSMessageHandler<SystemNotificationData>
  [WSMessageType.ERROR]?: WSMessageHandler<WSErrorData>
  [key: string]: WSMessageHandler<unknown> | undefined
}
