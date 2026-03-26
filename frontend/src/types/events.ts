/**
 * @file events.ts
 * @path frontend/src/types/events.ts
 * @description 事件参数类型定义，包含所有组件事件、用户交互事件的参数类型
 * @author Agent
 * @date 2026-03-25
 * @dependencies ./api, ./device, ./forms
 */

import type { ID } from './api'
import type { DeviceType, DeviceStatus } from './device'

// ==================== 设备事件参数 ====================

/** 设备状态变更事件参数 */
export interface DeviceStatusChangeEvent {
  /** 设备ID */
  deviceId: string
  /** 设备类型 */
  deviceType: DeviceType
  /** 旧状态 */
  oldStatus: DeviceStatus
  /** 新状态 */
  newStatus: DeviceStatus
  /** 时间戳 */
  timestamp: string
}

/** 设备连接事件参数 */
export interface DeviceConnectEvent {
  /** 设备ID */
  deviceId: string
  /** 是否成功 */
  success: boolean
  /** 错误消息 */
  errorMessage?: string
  /** 连接时间 */
  connectedAt?: string
}

/** 设备断开连接事件参数 */
export interface DeviceDisconnectEvent {
  /** 设备ID */
  deviceId: string
  /** 断开原因 */
  reason?: 'user' | 'timeout' | 'error' | 'system'
  /** 错误消息 */
  errorMessage?: string
}

/** 设备报警事件参数 */
export interface DeviceAlarmEvent {
  /** 设备ID */
  deviceId: string
  /** 报警代码 */
  alarmCode: number
  /** 报警文本 */
  alarmText: string
  /** 报警级别 */
  level: 'info' | 'warning' | 'error' | 'critical'
  /** 时间戳 */
  timestamp: string
}

/** 设备急停事件参数 */
export interface EmergencyStopEvent {
  /** 设备ID */
  deviceId?: string
  /** 急停来源 */
  source: 'user' | 'hardware' | 'software' | 'system'
  /** 急停原因 */
  reason?: string
  /** 时间戳 */
  timestamp: string
}

// ==================== 电机事件参数 ====================

/** 电机位置变更事件参数 */
export interface MotorPositionChangeEvent {
  /** 电机ID */
  motorId: string
  /** 旧位置 (mm) */
  oldPosition: number
  /** 新位置 (mm) */
  newPosition: number
  /** 时间戳 */
  timestamp: string
}

/** 电机运动完成事件参数 */
export interface MotorMoveCompleteEvent {
  /** 电机ID */
  motorId: string
  /** 目标位置 (mm) */
  targetPosition: number
  /** 实际位置 (mm) */
  actualPosition: number
  /** 是否成功 */
  success: boolean
  /** 错误消息 */
  errorMessage?: string
  /** 运动耗时 (ms) */
  duration?: number
}

/** 电机限位触发事件参数 */
export interface MotorLimitTriggerEvent {
  /** 电机ID */
  motorId: string
  /** 限位类型 */
  limitType: 'positive' | 'negative'
  /** 触发位置 (mm) */
  position: number
  /** 时间戳 */
  timestamp: string
}

/** 电机回零完成事件参数 */
export interface MotorHomeCompleteEvent {
  /** 电机ID */
  motorId: string
  /** 是否成功 */
  success: boolean
  /** 回零位置 (mm) */
  homePosition?: number
  /** 错误消息 */
  errorMessage?: string
}

// ==================== 实验事件参数 ====================

/** 实验状态变更事件参数 */
export interface ExperimentStatusChangeEvent {
  /** 实验ID */
  experimentId: ID
  /** 旧状态 */
  oldStatus: string
  /** 新状态 */
  newStatus: string
  /** 时间戳 */
  timestamp: string
}

/** 实验进度更新事件参数 */
export interface ExperimentProgressEvent {
  /** 实验ID */
  experimentId: ID
  /** 当前进度 (0-100) */
  progress: number
  /** 当前阶段 */
  stage?: string
  /** 已用时间 (s) */
  elapsedTime: number
  /** 预计剩余时间 (s) */
  estimatedTimeRemaining?: number
  /** 已采集数据点数 */
  dataPointsCollected?: number
}

/** 实验数据点事件参数 */
export interface ExperimentDataPointEvent {
  /** 实验ID */
  experimentId: ID
  /** 数据点索引 */
  index: number
  /** 时间戳 */
  timestamp: string
  /** 数据值 */
  values: Record<string, number>
}

/** 实验完成事件参数 */
export interface ExperimentCompleteEvent {
  /** 实验ID */
  experimentId: ID
  /** 是否成功 */
  success: boolean
  /** 总数据点数 */
  totalDataPoints: number
  /** 总耗时 (s) */
  duration: number
  /** 数据文件路径 */
  dataFile?: string
  /** 错误消息 */
  errorMessage?: string
}

// ==================== 数据查询事件参数 ====================

/** 查询条件事件参数 */
export interface QueryConditionsEvent {
  /** 时间范围 */
  timeRange: {
    start: string
    end: string
  }
  /** 设备ID列表 */
  deviceIds?: string[]
  /** 实验ID列表 */
  experimentIds?: ID[]
  /** 数据类型列表 */
  dataTypes?: string[]
  /** 其他筛选条件 */
  filters?: Record<string, unknown>
}

/** 查询模板保存事件参数 */
export interface TemplateSavedEvent {
  /** 模板ID */
  templateId: ID
  /** 模板名称 */
  templateName: string
  /** 模板描述 */
  description?: string
  /** 查询条件 */
  conditions: QueryConditionsEvent
}

/** 查询模板应用事件参数 */
export interface TemplateAppliedEvent {
  /** 模板ID */
  templateId: ID
  /** 模板名称 */
  templateName: string
  /** 应用的条件 */
  conditions: QueryConditionsEvent
}

// ==================== 图表交互事件参数 ====================

/** 图表点击事件参数 */
export interface ChartClickEvent {
  /** 图表实例ID */
  chartId?: string
  /** 数据索引 */
  dataIndex: number
  /** 系列索引 */
  seriesIndex: number
  /** 数据值 */
  value: number | number[]
  /** 数据名称 */
  name?: string
  /** X轴值 */
  xAxisValue?: number | string
  /** Y轴值 */
  yAxisValue?: number | string
  /** 事件对象 */
  event?: MouseEvent
}

/** 图表数据缩放事件参数 */
export interface ChartDataZoomEvent {
  /** 图表实例ID */
  chartId?: string
  /** 缩放类型 */
  type: 'inside' | 'slider'
  /** 缩放起始比例 (0-100) */
  start: number
  /** 缩放结束比例 (0-100) */
  end: number
  /** 缩放起始值 */
  startValue?: number
  /** 缩放结束值 */
  endValue?: number
}

/** 图表选择事件参数 */
export interface ChartSelectEvent {
  /** 图表实例ID */
  chartId?: string
  /** 选中的数据索引列表 */
  selectedDataIndices: number[]
  /** 选中的系列索引列表 */
  selectedSeriesIndices: number[]
  /** 选择范围 */
  range?: {
    xMin?: number
    xMax?: number
    yMin?: number
    yMax?: number
  }
}

// ==================== 用户交互事件参数 ====================

/** 列表项点击事件参数 */
export interface ListItemClickEvent<T = unknown> {
  /** 点击的项数据 */
  item: T
  /** 项索引 */
  index: number
  /** 事件对象 */
  event?: MouseEvent
}

/** 表单验证事件参数 */
export interface FormValidationEvent {
  /** 表单字段名 */
  field: string
  /** 是否有效 */
  valid: boolean
  /** 错误消息 */
  errorMessage?: string
  /** 字段值 */
  value?: unknown
}

/** 表单提交事件参数 */
export interface FormSubmitEvent<T = Record<string, unknown>> {
  /** 表单数据 */
  formData: T
  /** 是否有效 */
  valid: boolean
  /** 错误字段列表 */
  errors?: Array<{
    field: string
    message: string
  }>
}

// ==================== 文件操作事件参数 ====================

/** 文件上传事件参数 */
export interface FileUploadEvent {
  /** 文件对象 */
  file: File
  /** 上传进度 (0-100) */
  progress?: number
  /** 是否成功 */
  success?: boolean
  /** 错误消息 */
  errorMessage?: string
}

/** 文件下载事件参数 */
export interface FileDownloadEvent {
  /** 文件名 */
  fileName: string
  /** 文件URL */
  fileUrl?: string
  /** 文件大小 (bytes) */
  fileSize?: number
  /** 是否成功 */
  success?: boolean
  /** 错误消息 */
  errorMessage?: string
}

// ==================== 通知事件参数 ====================

/** 通知消息事件参数 */
export interface NotificationEvent {
  /** 通知ID */
  id: ID
  /** 通知类型 */
  type: 'info' | 'success' | 'warning' | 'error'
  /** 通知标题 */
  title: string
  /** 通知内容 */
  message?: string
  /** 持续时间 (ms)，0表示不自动关闭 */
  duration?: number
  /** 是否可关闭 */
  closable?: boolean
  /** 关联的操作 */
  action?: {
    /** 操作文本 */
    text: string
    /** 操作回调 */
    handler: () => void
  }
}

// ==================== WebSocket事件参数 ====================

/** WebSocket连接事件参数 */
export interface WebSocketConnectEvent {
  /** 连接URL */
  url: string
  /** 是否成功 */
  success: boolean
  /** 重连次数 */
  retryCount?: number
  /** 错误消息 */
  errorMessage?: string
}

/** WebSocket消息事件参数 */
export interface WebSocketMessageEvent<T = unknown> {
  /** 消息类型 */
  type: string
  /** 消息数据 */
  data: T
  /** 时间戳 */
  timestamp: string
}

/** WebSocket错误事件参数 */
export interface WebSocketErrorEvent {
  /** 错误类型 */
  type: 'connection' | 'message' | 'timeout'
  /** 错误消息 */
  message: string
  /** 是否可重连 */
  retryable: boolean
  /** 重连延迟 (ms) */
  retryDelay?: number
}

// ==================== 操作反馈事件参数 ====================

/** 操作开始事件参数 */
export interface OperationStartEvent {
  /** 操作ID */
  operationId: ID
  /** 操作类型 */
  operationType: string
  /** 操作描述 */
  description?: string
  /** 预计耗时 (ms) */
  estimatedDuration?: number
}

/** 操作进度事件参数 */
export interface OperationProgressEvent {
  /** 操作ID */
  operationId: ID
  /** 进度 (0-100) */
  progress: number
  /** 进度描述 */
  message?: string
  /** 已用时间 (ms) */
  elapsedTime?: number
}

/** 操作完成事件参数 */
export interface OperationCompleteEvent {
  /** 操作ID */
  operationId: ID
  /** 是否成功 */
  success: boolean
  /** 结果数据 */
  result?: unknown
  /** 错误消息 */
  errorMessage?: string
  /** 总耗时 (ms) */
  duration: number
}

// ==================== 键盘快捷键事件参数 ====================

/** 快捷键事件参数 */
export interface ShortcutKeyEvent {
  /** 快捷键组合 */
  key: string
  /** Ctrl键是否按下 */
  ctrl?: boolean
  /** Shift键是否按下 */
  shift?: boolean
  /** Alt键是否按下 */
  alt?: boolean
  /** Meta键是否按下 */
  meta?: boolean
  /** 快捷键功能描述 */
  action: string
  /** 原始事件 */
  event?: KeyboardEvent
}

// ==================== 拖拽事件参数 ====================

/** 拖拽开始事件参数 */
export interface DragStartEvent<T = unknown> {
  /** 拖拽数据 */
  data: T
  /** 拖拽源索引 */
  sourceIndex: number
  /** 拖拽源容器ID */
  sourceContainer?: string
}

/** 拖拽放置事件参数 */
export interface DragDropEvent<T = unknown> {
  /** 拖拽数据 */
  data: T
  /** 拖拽源索引 */
  sourceIndex: number
  /** 放置目标索引 */
  targetIndex: number
  /** 拖拽源容器ID */
  sourceContainer?: string
  /** 放置目标容器ID */
  targetContainer?: string
}

// ==================== 选择事件参数 ====================

/** 选择变更事件参数 */
export interface SelectionChangeEvent<T = unknown> {
  /** 选中的项列表 */
  selected: T[]
  /** 选中的索引列表 */
  selectedIndices: number[]
  /** 是否全选 */
  selectAll?: boolean
}

// ==================== 筛选事件参数 ====================

/** 筛选条件变更事件参数 */
export interface FilterChangeEvent {
  /** 筛选字段 */
  field: string
  /** 筛选值 */
  value: unknown
  /** 筛选操作 */
  operator?: 'eq' | 'ne' | 'gt' | 'lt' | 'gte' | 'lte' | 'contains' | 'in'
}

/** 排序变更事件参数 */
export interface SortChangeEvent {
  /** 排序字段 */
  field: string
  /** 排序方向 */
  order: 'asc' | 'desc' | null
}

/** 分页变更事件参数 */
export interface PaginationChangeEvent {
  /** 当前页码 */
  page: number
  /** 每页数量 */
  pageSize: number
}

// ==================== 导出类型联合 ====================

/** 所有事件参数联合类型 */
export type AnyEvent =
  | DeviceStatusChangeEvent
  | DeviceConnectEvent
  | DeviceDisconnectEvent
  | DeviceAlarmEvent
  | EmergencyStopEvent
  | MotorPositionChangeEvent
  | MotorMoveCompleteEvent
  | MotorLimitTriggerEvent
  | MotorHomeCompleteEvent
  | ExperimentStatusChangeEvent
  | ExperimentProgressEvent
  | ExperimentDataPointEvent
  | ExperimentCompleteEvent
  | QueryConditionsEvent
  | TemplateSavedEvent
  | TemplateAppliedEvent
  | ChartClickEvent
  | ChartDataZoomEvent
  | ChartSelectEvent
  | ListItemClickEvent
  | FormValidationEvent
  | FormSubmitEvent
  | FileUploadEvent
  | FileDownloadEvent
  | NotificationEvent
  | WebSocketConnectEvent
  | WebSocketMessageEvent
  | WebSocketErrorEvent
  | OperationStartEvent
  | OperationProgressEvent
  | OperationCompleteEvent
  | ShortcutKeyEvent
  | DragStartEvent
  | DragDropEvent
  | SelectionChangeEvent
  | FilterChangeEvent
  | SortChangeEvent
  | PaginationChangeEvent
