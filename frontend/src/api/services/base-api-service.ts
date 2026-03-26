/**
 * @file base-api-service.ts
 * @path src/api/services/base-api-service.ts
 * @description API服务基础类，提供统一的请求处理、错误处理、重试机制
 * @author Agent
 * @date 2026-03-25
 * @dependencies ../client, @/types/api
 */

import { request, type RequestResult, type RequestOptions } from '../client'
import type { AxiosResponse } from 'axios'

/**
 * API服务配置
 */
export interface ApiServiceConfig {
  /** API基础路径 */
  basePath: string
  /** 默认超时时间 */
  timeout?: number
  /** 默认重试次数 */
  retries?: number
  /** 是否使用缓存 */
  useCache?: boolean
  /** 缓存TTL */
  cacheTTL?: number
}

/**
 * API服务基础类
 * 
 * @remarks
 * 所有设备API服务类应继承此类，提供统一的请求处理、错误处理、重试机制
 * 子类应实现具体的业务方法
 */
export abstract class BaseApiService {
  protected readonly basePath: string
  protected readonly timeout: number
  protected readonly retries: number
  protected readonly useCache: boolean
  protected readonly cacheTTL: number

  constructor(config: ApiServiceConfig) {
    this.basePath = config.basePath
    this.timeout = config.timeout ?? 30000
    this.retries = config.retries ?? 3
    this.useCache = config.useCache ?? false
    this.cacheTTL = config.cacheTTL ?? 30000
  }

  /**
   * 发送GET请求
   * 
   * @param path - 请求路径（相对于basePath）
   * @param params - 查询参数
   * @param options - 额外请求选项
   * @returns 请求结果
   */
  protected async get<T>(
    path: string,
    params: Record<string, unknown> | null = null,
    options: Partial<RequestOptions> = {}
  ): Promise<RequestResult<T>> {
    return request<T>({
      method: 'GET',
      url: this.buildUrl(path),
      params,
      timeout: this.timeout,
      retries: this.retries,
      useCache: this.useCache,
      cacheTTL: this.cacheTTL,
      ...options,
    })
  }

  /**
   * 发送POST请求
   * 
   * @param path - 请求路径（相对于basePath）
   * @param data - 请求体数据
   * @param options - 额外请求选项
   * @returns 请求结果
   */
  protected async post<T>(
    path: string,
    data: Record<string, unknown> | null = null,
    options: Partial<RequestOptions> = {}
  ): Promise<RequestResult<T>> {
    return request<T>({
      method: 'POST',
      url: this.buildUrl(path),
      data,
      timeout: this.timeout,
      retries: this.retries,
      ...options,
    })
  }

  /**
   * 发送PUT请求
   * 
   * @param path - 请求路径（相对于basePath）
   * @param data - 请求体数据
   * @param options - 额外请求选项
   * @returns 请求结果
   */
  protected async put<T>(
    path: string,
    data: Record<string, unknown> | null = null,
    options: Partial<RequestOptions> = {}
  ): Promise<RequestResult<T>> {
    return request<T>({
      method: 'PUT',
      url: this.buildUrl(path),
      data,
      timeout: this.timeout,
      retries: this.retries,
      ...options,
    })
  }

  /**
   * 发送DELETE请求
   * 
   * @param path - 请求路径（相对于basePath）
   * @param options - 额外请求选项
   * @returns 请求结果
   */
  protected async del<T>(
    path: string,
    options: Partial<RequestOptions> = {}
  ): Promise<RequestResult<T>> {
    return request<T>({
      method: 'DELETE',
      url: this.buildUrl(path),
      timeout: this.timeout,
      retries: this.retries,
      ...options,
    })
  }

  /**
   * 构建完整URL
   * 
   * @param path - 相对路径
   * @returns 完整URL
   */
  protected buildUrl(path: string): string {
    const normalizedBase = this.basePath.endsWith('/')
      ? this.basePath.slice(0, -1)
      : this.basePath
    const normalizedPath = path.startsWith('/') ? path : `/${path}`
    return `${normalizedBase}${normalizedPath}`
  }

  /**
   * 解包响应数据
   * 
   * @param result - 请求结果
   * @returns 解包后的数据或null
   * @throws Error 当请求失败时抛出错误
   */
  protected unwrap<T>(result: RequestResult<T>): T | null {
    if (result.success) {
      return result.data ?? null
    }
    throw new ApiError(result.message || '请求失败', result.error)
  }

  /**
   * 检查请求是否成功
   * 
   * @param result - 请求结果
   * @returns 是否成功
   */
  protected isSuccess<T>(result: RequestResult<T>): boolean {
    return result.success
  }
}

/**
 * API错误类
 */
export class ApiError extends Error {
  public readonly errorInfo?: {
    status?: number
    code?: string
    type?: string
  }

  constructor(message: string, errorInfo?: { status?: number; code?: string; type?: string }) {
    super(message)
    this.name = 'ApiError'
    this.errorInfo = errorInfo
  }
}

/**
 * 设备通信错误类
 */
export class DeviceCommunicationError extends ApiError {
  constructor(message: string, deviceId?: string) {
    super(message, { code: 'DEVICE_COMMUNICATION_ERROR' })
    this.name = 'DeviceCommunicationError'
  }
}

/**
 * 设备报警错误类
 */
export class DeviceAlarmError extends ApiError {
  public readonly alarmCode?: number

  constructor(message: string, alarmCode?: number) {
    super(message, { code: 'DEVICE_ALARM' })
    this.name = 'DeviceAlarmError'
    this.alarmCode = alarmCode
  }
}

/**
 * 参数校验错误类
 */
export class ValidationError extends ApiError {
  constructor(message: string) {
    super(message, { code: 'VALIDATION_ERROR' })
    this.name = 'ValidationError'
  }
}

export default BaseApiService
