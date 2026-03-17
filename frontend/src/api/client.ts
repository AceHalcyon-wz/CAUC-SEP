/**
 * @file client.ts
 * @path src/api/
 * @description Axios 类型化客户端，提供统一的 API 请求封装
 * @author Agent
 * @date 2024-03-16
 * @dependencies axios, @/types/api
 */

import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'
import type { ApiResponse, RequestResult, RequestOptions } from '@/types/api'

/** API 基础 URL */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

/** API 版本前缀 */
const API_VERSION = '/api/v1'

/** 完整 API 基础路径 */
const API_BASE = `${API_BASE_URL}${API_VERSION}`

/**
 * 请求缓存配置
 */
interface CacheConfig {
  /** 默认缓存时间（毫秒） */
  defaultTTL: number
  /** 最大缓存条目数 */
  maxSize: number
  /** 缓存键前缀 */
  keyPrefix: string
}

const CACHE_CONFIG: CacheConfig = {
  defaultTTL: 30000,
  maxSize: 100,
  keyPrefix: 'api_cache_',
}

/**
 * 缓存条目
 */
interface CacheEntry<T> {
  data: T
  timestamp: number
  ttl: number
}

/** 请求缓存存储 */
const requestCache = new Map<string, CacheEntry<unknown>>()

/**
 * 待处理请求映射（用于取消重复请求）
 */
interface PendingRequest {
  controller: AbortController
  timestamp: number
}

const pendingRequests = new Map<string, PendingRequest>()

/**
 * 重试配置
 */
interface RetryConfig {
  maxRetries: number
  baseDelay: number
  maxDelay: number
  retryableStatusCodes: number[]
}

const RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  baseDelay: 1000,
  maxDelay: 10000,
  retryableStatusCodes: [408, 429, 500, 502, 503, 504],
}

/**
 * Axios 实例配置
 */
const axiosConfig: AxiosRequestConfig = {
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
}

/**
 * Axios 实例
 */
export const apiClient: AxiosInstance = axios.create(axiosConfig)

/**
 * 请求拦截器
 */
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 添加认证 Token
    const token = localStorage.getItem('auth_token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

/**
 * 响应拦截器
 */
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response
  },
  (error) => {
    // 处理 401 未授权
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      // 可以在这里触发登出逻辑
    }
    return Promise.reject(error)
  }
)

/**
 * 生成缓存键
 *
 * @param method - HTTP 方法
 * @param url - 请求 URL
 * @param params - URL 参数
 * @param data - 请求数据
 * @returns 缓存键
 */
function generateCacheKey(
  method: string,
  url: string,
  params?: Record<string, unknown> | null,
  data?: Record<string, unknown> | null
): string {
  const keyParts = [
    method.toUpperCase(),
    url,
    params ? JSON.stringify(params) : '',
    data ? JSON.stringify(data) : '',
  ]

  let hash = 0
  const str = keyParts.join('|')
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i)
    hash = ((hash << 5) - hash) + char
    hash = hash & hash
  }

  return `${CACHE_CONFIG.keyPrefix}${Math.abs(hash).toString(36)}`
}

/**
 * 从缓存获取数据
 *
 * @param cacheKey - 缓存键
 * @returns 缓存数据或 null
 */
function getFromCache<T>(cacheKey: string): T | null {
  const cached = requestCache.get(cacheKey)

  if (!cached) {
    return null
  }

  const now = Date.now()
  if (now - cached.timestamp > cached.ttl) {
    requestCache.delete(cacheKey)
    return null
  }

  return cached.data as T
}

/**
 * 存储数据到缓存
 *
 * @param cacheKey - 缓存键
 * @param data - 要缓存的数据
 * @param ttl - 缓存有效期
 */
function setToCache<T>(cacheKey: string, data: T, ttl = CACHE_CONFIG.defaultTTL): void {
  if (requestCache.size >= CACHE_CONFIG.maxSize) {
    const oldestKey = requestCache.keys().next().value
    if (oldestKey) {
      requestCache.delete(oldestKey)
    }
  }

  requestCache.set(cacheKey, {
    data,
    timestamp: Date.now(),
    ttl,
  })
}

/**
 * 清除缓存
 *
 * @param pattern - 缓存键模式（可选）
 */
export function clearCache(pattern?: string): void {
  if (pattern) {
    for (const key of requestCache.keys()) {
      if (key.includes(pattern)) {
        requestCache.delete(key)
      }
    }
  } else {
    requestCache.clear()
  }
}

/**
 * 取消待处理请求
 *
 * @param url - 请求 URL（可选，不指定则取消所有）
 */
export function cancelPendingRequests(url?: string): void {
  if (url) {
    const cacheKey = generateCacheKey('GET', url)
    const pending = pendingRequests.get(cacheKey)
    if (pending) {
      pending.controller.abort()
      pendingRequests.delete(cacheKey)
    }
  } else {
    pendingRequests.forEach((pending) => {
      pending.controller.abort()
    })
    pendingRequests.clear()
  }
}

/**
 * 计算重试延迟
 *
 * @param retryCount - 当前重试次数
 * @returns 延迟时间（毫秒）
 */
function calculateRetryDelay(retryCount: number): number {
  const delay = RETRY_CONFIG.baseDelay * Math.pow(2, retryCount - 1)
  const jitter = delay * 0.2 * Math.random()
  return Math.min(delay + jitter, RETRY_CONFIG.maxDelay)
}

/**
 * 判断是否应该重试
 *
 * @param error - 错误对象
 * @param retryCount - 当前重试次数
 * @returns 是否应该重试
 */
function shouldRetry(error: Error & { response?: { status: number }; code?: string }, retryCount: number): boolean {
  if (retryCount >= RETRY_CONFIG.maxRetries) {
    return false
  }

  if (error.name === 'AbortError' || error.name === 'CanceledError') {
    return false
  }

  if (error.response) {
    return RETRY_CONFIG.retryableStatusCodes.includes(error.response.status)
  }

  return error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT' || error.code === 'ERR_NETWORK'
}

/**
 * 延迟执行
 *
 * @param ms - 延迟毫秒数
 */
function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * 统一 API 请求包装函数
 *
 * @param options - 请求选项
 * @returns 请求结果
 *
 * @example
 * const result = await request({
 *   method: 'GET',
 *   url: '/users',
 *   useCache: true,
 *   cacheTTL: 60000,
 *   retries: 2
 * });
 */
export async function request<T = unknown>(options: RequestOptions): Promise<RequestResult<T>> {
  const {
    method = 'GET',
    url,
    data = null,
    params = null,
    onLoading,
    onError,
    loadingKey,
    timeout = 30000,
    useCache = false,
    cacheTTL = CACHE_CONFIG.defaultTTL,
    cancelDuplicate = true,
    retries = 0,
    skipAuth = false,
  } = options

  const methodUpper = method.toUpperCase()
  const cacheKey = generateCacheKey(methodUpper, url, params, data)

  // 检查缓存
  if (useCache && methodUpper === 'GET') {
    const cachedData = getFromCache<T>(cacheKey)
    if (cachedData !== null) {
      return {
        success: true,
        data: cachedData,
        cached: true,
      }
    }
  }

  // 取消重复请求
  if (cancelDuplicate && methodUpper === 'GET') {
    const existing = pendingRequests.get(cacheKey)
    if (existing && Date.now() - existing.timestamp < 5000) {
      existing.controller.abort()
    }
  }

  const controller = new AbortController()
  if (cancelDuplicate && methodUpper === 'GET') {
    pendingRequests.set(cacheKey, {
      controller,
      timestamp: Date.now(),
    })
  }

  // 触发加载状态
  if (onLoading && loadingKey) {
    onLoading(loadingKey, true)
  }

  let lastError: Error | null = null
  let retryCount = 0

  while (retryCount <= retries) {
    try {
      const config: AxiosRequestConfig = {
        method,
        url,
        timeout,
        signal: controller.signal,
        headers: {},
      }

      // 添加认证 Token
      if (!skipAuth) {
        const token = localStorage.getItem('auth_token')
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`
        }
      }

      if (data) {
        config.data = data
      }

      if (params) {
        config.params = params
      }

      const response = await apiClient.request<ApiResponse<T>>(config)

      pendingRequests.delete(cacheKey)

      if (response.data.success === true) {
        if (useCache && methodUpper === 'GET' && response.data.data) {
          setToCache(cacheKey, response.data.data, cacheTTL)
        }

        return {
          success: true,
          data: response.data.data,
          message: response.data.message,
        }
      } else if ((response.data as { access_token?: string }).access_token) {
        // 登录响应特殊处理
        return {
          success: true,
          data: response.data as T,
          message: '登录成功',
        }
      } else {
        const errorMessage = response.data.message || '操作失败'
        if (onError) {
          onError(errorMessage)
        }
        return {
          success: false,
          message: errorMessage,
        }
      }
    } catch (error) {
      const err = error as Error & { response?: { status: number; data?: { detail?: string; message?: string }; code?: string } }
      lastError = err

      if (err.name === 'AbortError' || err.name === 'CanceledError') {
        return {
          success: false,
          message: '请求已取消',
        }
      }

      if (shouldRetry(err, retryCount) && retryCount < retries) {
        retryCount++
        const retryDelay = calculateRetryDelay(retryCount)
        console.log(`[API] 重试请求 ${url} (${retryCount}/${retries})，延迟 ${Math.round(retryDelay)}ms`)
        await delay(retryDelay)
        continue
      }

      pendingRequests.delete(cacheKey)

      const errorMessage =
        err.response?.data?.detail || err.response?.data?.message || err.message || '网络请求失败'

      if (onError) {
        onError(errorMessage)
      }

      const errWithCode = err as Error & { code?: string }
      return {
        success: false,
        message: errorMessage,
        error: {
          status: err.response?.status,
          code: errWithCode.code,
          type: err.name,
        },
      }
    }
  }

  pendingRequests.delete(cacheKey)

  const errorMessage = (lastError as Error & { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
    (lastError as Error)?.message ||
    '请求失败'

  if (onError) {
    onError(errorMessage)
  }

  return {
    success: false,
    message: errorMessage,
  }
}

/**
 * GET 请求快捷方法
 *
 * @param url - 请求 URL 路径
 * @param params - URL 查询参数
 * @param options - 其他请求选项
 * @returns 请求结果
 *
 * @example
 * const result = await get<UserInfo>('/users/1');
 */
export async function get<T = unknown>(
  url: string,
  params: Record<string, unknown> | null = null,
  options: Partial<RequestOptions> = {}
): Promise<RequestResult<T>> {
  return request<T>({ ...options, method: 'GET', url, params })
}

/**
 * POST 请求快捷方法
 *
 * @param url - 请求 URL 路径
 * @param data - 请求体数据
 * @param options - 其他请求选项
 * @returns 请求结果
 *
 * @example
 * const result = await post<UserInfo>('/users', { name: '张三' });
 */
export async function post<T = unknown>(
  url: string,
  data: Record<string, unknown> | null = null,
  options: Partial<RequestOptions> = {}
): Promise<RequestResult<T>> {
  return request<T>({ ...options, method: 'POST', url, data })
}

/**
 * PUT 请求快捷方法
 *
 * @param url - 请求 URL 路径
 * @param data - 请求体数据
 * @param options - 其他请求选项
 * @returns 请求结果
 */
export async function put<T = unknown>(
  url: string,
  data: Record<string, unknown> | null = null,
  options: Partial<RequestOptions> = {}
): Promise<RequestResult<T>> {
  return request<T>({ ...options, method: 'PUT', url, data })
}

/**
 * DELETE 请求快捷方法
 *
 * @param url - 请求 URL 路径
 * @param options - 其他请求选项
 * @returns 请求结果
 */
export async function del<T = unknown>(
  url: string,
  options: Partial<RequestOptions> = {}
): Promise<RequestResult<T>> {
  return request<T>({ ...options, method: 'DELETE', url })
}

/**
 * 批量请求方法
 *
 * @param requests - 请求配置数组
 * @param options - 批量选项
 * @returns 请求结果数组
 */
export async function batchRequest<T = unknown>(
  requests: RequestOptions[],
  options: { continueOnError?: boolean } = {}
): Promise<RequestResult<T>[]> {
  const { continueOnError = true } = options
  const results: RequestResult<T>[] = []

  for (const req of requests) {
    try {
      const result = await request<T>(req)
      results.push(result)

      if (!result.success && !continueOnError) {
        break
      }
    } catch (error) {
      results.push({
        success: false,
        message: (error as Error).message || '请求异常',
      })

      if (!continueOnError) {
        break
      }
    }
  }

  return results
}

/**
 * 并行请求方法
 *
 * @param requests - 请求配置数组
 * @returns 请求结果数组
 */
export async function parallelRequest<T = unknown>(requests: RequestOptions[]): Promise<RequestResult<T>[]> {
  const promises = requests.map((req) => request<T>(req))
  return Promise.all(promises)
}

/** 导出默认请求方法 */
export default request
