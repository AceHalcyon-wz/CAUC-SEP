/**
 * @file api.ts
 * @path src/types/
 * @description API 通用类型定义
 * @author Agent
 * @date 2024-03-16
 */

/** API 响应包装 */
export interface ApiResponse<T = unknown> {
  /** 是否成功 */
  success: boolean
  /** 响应数据 */
  data?: T
  /** 响应消息 */
  message?: string
  /** 错误信息 */
  error?: ApiError
  /** 时间戳 */
  timestamp: string
}

/** API 错误信息 */
export interface ApiError {
  /** 错误码 */
  code: string
  /** 错误消息 */
  message: string
  /** 错误详情 */
  details?: Record<string, unknown>
}

/** 分页请求参数 */
export interface PaginationParams {
  /** 页码（从 1 开始） */
  page: number
  /** 每页数量 */
  pageSize: number
  /** 排序字段 */
  sortBy?: string
  /** 排序方向 */
  sortOrder?: 'asc' | 'desc'
}

/** 分页响应数据 */
export interface PaginatedData<T> {
  /** 数据列表 */
  items: T[]
  /** 总数量 */
  total: number
  /** 当前页码 */
  page: number
  /** 每页数量 */
  pageSize: number
  /** 总页数 */
  totalPages: number
}

/** 分页响应（别名，兼容 PaginatedData） */
export type PaginatedResponse<T> = PaginatedData<T>

/** 时间范围 */
export interface TimeRange {
  /** 开始时间 */
  start: string
  /** 结束时间 */
  end: string
}

/** ID 类型 */
export type ID = string | number

/** 设备状态值 */
export type DeviceStatusValue =
  | 'disconnected'
  | 'connecting'
  | 'ready'
  | 'running'
  | 'busy'
  | 'error'
  | 'emergency_stop'
  | 'maintenance'

/** 设备类型 */
export type DeviceTypeValue =
  | 'stepper'
  | 'electromagnet'
  | 'temperature'
  | 'piezo'
  | 'ammeter'

/** 设备状态摘要 */
export interface DeviceStatusSummary {
  /** 设备 ID */
  deviceId: string
  /** 设备类型 */
  deviceType: DeviceTypeValue
  /** 状态值 */
  status: DeviceStatusValue
  /** 是否已连接 */
  connected: boolean
  /** 是否仿真模式 */
  simulation: boolean
  /** 最后更新时间 */
  lastUpdate: string
}

/** 请求选项 */
export interface RequestOptions {
  /** HTTP 方法 */
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  /** 请求 URL */
  url: string
  /** 请求数据 */
  data?: Record<string, unknown> | null
  /** URL 参数 */
  params?: Record<string, unknown> | null
  /** 加载状态回调 */
  onLoading?: (key: string, loading: boolean) => void
  /** 错误回调 */
  onError?: (message: string) => void
  /** 加载状态键名 */
  loadingKey?: string
  /** 请求超时时间 */
  timeout?: number
  /** 是否使用缓存 */
  useCache?: boolean
  /** 缓存有效期 */
  cacheTTL?: number
  /** 是否取消重复请求 */
  cancelDuplicate?: boolean
  /** 重试次数 */
  retries?: number
  /** 是否跳过认证 */
  skipAuth?: boolean
}

/** 请求结果 */
export interface RequestResult<T = unknown> {
  /** 是否成功 */
  success: boolean
  /** 响应数据 */
  data?: T
  /** 响应消息 */
  message?: string
  /** 是否来自缓存 */
  cached?: boolean
  /** 错误信息 */
  error?: {
    status?: number
    code?: string
    type?: string
  }
}
