/**
 * @file apiRequest.js
 * @path src/utils/
 * @description 统一API请求包装模块，提供标准化的HTTP请求方法，支持缓存、重试、取消等功能
 * @author Agent
 * @date 2024-03-06
 * @version 3.5.1
 * @dependencies axios, config/api
 */

import axios from 'axios'
import { API_BASE_URL } from '../config/api'

/**
 * 请求缓存配置
 * @constant {Object}
 */
const CACHE_CONFIG = {
  /** 默认缓存时间（毫秒） */
  defaultTTL: 30000,
  /** 最大缓存条目数 */
  maxSize: 100,
  /** 缓存键前缀 */
  keyPrefix: 'api_cache_'
}

/**
 * 请求缓存存储
 * @type {Map<string, {data: any, timestamp: number, ttl: number}>}
 */
const requestCache = new Map()

/**
 * 待处理请求映射（用于取消重复请求）
 * @type {Map<string, {controller: AbortController, timestamp: number}>}
 */
const pendingRequests = new Map()

/**
 * 请求重试配置
 * @constant {Object}
 */
const RETRY_CONFIG = {
  /** 最大重试次数 */
  maxRetries: 3,
  /** 重试延迟基数（毫秒） */
  baseDelay: 1000,
  /** 重试延迟最大值（毫秒） */
  maxDelay: 10000,
  /** 需要重试的HTTP状态码 */
  retryableStatusCodes: [408, 429, 500, 502, 503, 504]
}

/**
 * API请求选项
 * @typedef {Object} RequestOptions
 * @property {string} method - HTTP方法
 * @property {string} url - 请求URL
 * @property {Object} [data] - 请求数据
 * @property {Object} [params] - URL参数
 * @property {Function} [onLoading] - 加载状态回调
 * @property {Function} [onError] - 错误回调
 * @property {string} [loadingKey] - 加载状态键名
 * @property {number} [timeout] - 请求超时时间
 * @property {boolean} [useCache] - 是否使用缓存
 * @property {number} [cacheTTL] - 缓存有效期
 * @property {boolean} [cancelDuplicate] - 是否取消重复请求
 * @property {number} [retries] - 重试次数
 * @property {boolean} [skipAuth] - 是否跳过认证
 */

/**
 * 生成缓存键
 *
 * @param {string} method - HTTP方法
 * @param {string} url - 请求URL
 * @param {Object} [params] - URL参数
 * @param {Object} [data] - 请求数据
 * @returns {string} 缓存键
 */
function generateCacheKey(method, url, params, data) {
  const keyParts = [
    method.toUpperCase(),
    url,
    params ? JSON.stringify(params) : '',
    data ? JSON.stringify(data) : ''
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
 * @param {string} cacheKey - 缓存键
 * @returns {Object|null} 缓存数据或null
 */
function getFromCache(cacheKey) {
  const cached = requestCache.get(cacheKey)
  
  if (!cached) {
    return null
  }
  
  const now = Date.now()
  if (now - cached.timestamp > cached.ttl) {
    requestCache.delete(cacheKey)
    return null
  }
  
  return cached.data
}

/**
 * 存储数据到缓存
 *
 * @param {string} cacheKey - 缓存键
 * @param {Object} data - 要缓存的数据
 * @param {number} [ttl] - 缓存有效期
 */
function setToCache(cacheKey, data, ttl = CACHE_CONFIG.defaultTTL) {
  if (requestCache.size >= CACHE_CONFIG.maxSize) {
    const oldestKey = requestCache.keys().next().value
    requestCache.delete(oldestKey)
  }
  
  requestCache.set(cacheKey, {
    data,
    timestamp: Date.now(),
    ttl
  })
}

/**
 * 清除缓存
 *
 * @param {string} [pattern] - 缓存键模式（可选）
 */
export function clearCache(pattern) {
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
 * @param {string} [url] - 请求URL（可选，不指定则取消所有）
 */
export function cancelPendingRequests(url) {
  if (url) {
    const cacheKey = generateCacheKey('GET', url)
    const pending = pendingRequests.get(cacheKey)
    if (pending) {
      pending.controller.abort()
      pendingRequests.delete(cacheKey)
    }
  } else {
    pendingRequests.forEach(pending => {
      pending.controller.abort()
    })
    pendingRequests.clear()
  }
}

/**
 * 计算重试延迟
 *
 * @param {number} retryCount - 当前重试次数
 * @returns {number} 延迟时间（毫秒）
 */
function calculateRetryDelay(retryCount) {
  const delay = RETRY_CONFIG.baseDelay * Math.pow(2, retryCount - 1)
  const jitter = delay * 0.2 * Math.random()
  return Math.min(delay + jitter, RETRY_CONFIG.maxDelay)
}

/**
 * 判断是否应该重试
 *
 * @param {Error} error - 错误对象
 * @param {number} retryCount - 当前重试次数
 * @returns {boolean} 是否应该重试
 */
function shouldRetry(error, retryCount) {
  if (retryCount >= RETRY_CONFIG.maxRetries) {
    return false
  }
  
  if (error.name === 'AbortError' || error.name === 'CanceledError') {
    return false
  }
  
  if (error.response) {
    return RETRY_CONFIG.retryableStatusCodes.includes(error.response.status)
  }
  
  return error.code === 'ECONNABORTED' ||
         error.code === 'ETIMEDOUT' ||
         error.code === 'ERR_NETWORK'
}

/**
 * 延迟执行
 *
 * @param {number} ms - 延迟毫秒数
 * @returns {Promise<void>}
 */
function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * 统一API请求包装函数
 *
 * @param {RequestOptions} options - 请求选项
 * @returns {Promise<{success: boolean, data?: any, message?: string, cached?: boolean}>}
 *
 * @example
 * const result = await request({
 *   method: 'GET',
 *   url: '/api/users',
 *   useCache: true,
 *   cacheTTL: 60000,
 *   retries: 2
 * });
 */
export async function request(options) {
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
    skipAuth = false
  } = options

  const methodUpper = method.toUpperCase()
  const cacheKey = generateCacheKey(methodUpper, url, params, data)

  if (useCache && methodUpper === 'GET') {
    const cachedData = getFromCache(cacheKey)
    if (cachedData) {
      return {
        success: true,
        data: cachedData,
        cached: true
      }
    }
  }

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
      timestamp: Date.now()
    })
  }

  if (onLoading && loadingKey) {
    onLoading(loadingKey, true)
  }

  let lastError = null
  let retryCount = 0

  while (retryCount <= retries) {
    try {
      const config = {
        method,
        url: `${API_BASE_URL}${url}`,
        headers: {
          'Content-Type': 'application/json'
        },
        timeout,
        signal: controller.signal
      }

      // 验证 URL 格式
      try {
        new URL(config.url)
      } catch (urlError) {
        console.error('[API] Invalid URL:', config.url, 'Base:', API_BASE_URL, 'Path:', url)
        throw new Error(`Invalid URL: ${config.url}`)
      }

      if (!skipAuth) {
        const token = localStorage.getItem('auth_token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
      }

      if (data) {
        config.data = data
      }

      if (params) {
        config.params = params
      }

      const response = await axios(config)

      pendingRequests.delete(cacheKey)

      if (response.data.success === true) {
        if (useCache && methodUpper === 'GET') {
          setToCache(cacheKey, response.data.data, cacheTTL)
        }
        
        return {
          success: true,
          data: response.data.data,
          message: response.data.message
        }
      } else if (response.data.access_token) {
        return {
          success: true,
          data: response.data,
          message: '登录成功'
        }
      } else {
        const errorMessage = response.data.message || response.data.detail || '操作失败'
        if (onError) {
          onError(errorMessage)
        }
        return {
          success: false,
          message: errorMessage
        }
      }
    } catch (error) {
      lastError = error
      
      if (error.name === 'AbortError' || error.name === 'CanceledError') {
        return {
          success: false,
          message: '请求已取消'
        }
      }

      if (shouldRetry(error, retryCount) && retryCount < retries) {
        retryCount++
        const retryDelay = calculateRetryDelay(retryCount)
        console.log(`[API] 重试请求 ${url} (${retryCount}/${retries})，延迟 ${Math.round(retryDelay)}ms`)
        await delay(retryDelay)
        continue
      }

      pendingRequests.delete(cacheKey)

      const errorMessage = error.response?.data?.detail || 
                          error.response?.data?.message ||
                          error.message || 
                          '网络请求失败'
      
      if (onError) {
        onError(errorMessage)
      }
      
      return {
        success: false,
        message: errorMessage,
        error: {
          status: error.response?.status,
          code: error.code,
          type: error.name
        }
      }
    }
  }

  pendingRequests.delete(cacheKey)
  
  const errorMessage = lastError?.response?.data?.detail || 
                      lastError?.message || 
                      '请求失败'
  
  if (onError) {
    onError(errorMessage)
  }
  
  return {
    success: false,
    message: errorMessage
  }
}

/**
 * GET请求快捷方法
 *
 * @param {string} url - 请求URL路径
 * @param {Object|null} [params=null] - URL查询参数
 * @param {Object} [options={}] - 其他请求选项
 * @returns {Promise<{success: boolean, data?: any, message?: string}>}
 *
 * @example
 * const result = await get('/api/users', { page: 1, size: 10 }, { useCache: true });
 */
export async function get(url, params = null, options = {}) {
  return request({ ...options, method: 'GET', url, params })
}

/**
 * POST请求快捷方法
 *
 * @param {string} url - 请求URL路径
 * @param {Object|null} [data=null] - 请求体数据
 * @param {Object} [options={}] - 其他请求选项
 * @returns {Promise<{success: boolean, data?: any, message?: string}>}
 *
 * @example
 * const result = await post('/api/users', { name: '张三', email: 'test@example.com' });
 */
export async function post(url, data = null, options = {}) {
  return request({ ...options, method: 'POST', url, data })
}

/**
 * PUT请求快捷方法
 *
 * @param {string} url - 请求URL路径
 * @param {Object|null} [data=null] - 请求体数据
 * @param {Object} [options={}] - 其他请求选项
 * @returns {Promise<{success: boolean, data?: any, message?: string}>}
 */
export async function put(url, data = null, options = {}) {
  return request({ ...options, method: 'PUT', url, data })
}

/**
 * DELETE请求快捷方法
 *
 * @param {string} url - 请求URL路径
 * @param {Object} [options={}] - 其他请求选项
 * @returns {Promise<{success: boolean, data?: any, message?: string}>}
 */
export async function del(url, options = {}) {
  return request({ ...options, method: 'DELETE', url })
}

/**
 * 批量请求方法
 *
 * @param {Array<RequestOptions>} requests - 请求配置数组
 * @param {Object} [options={}] - 批量选项
 * @param {boolean} [options.continueOnError=true] - 出错时是否继续
 * @returns {Promise<Array<{success: boolean, data?: any, message?: string}>>}
 */
export async function batchRequest(requests, options = {}) {
  const { continueOnError = true } = options
  const results = []

  for (const req of requests) {
    try {
      const result = await request(req)
      results.push(result)
      
      if (!result.success && !continueOnError) {
        break
      }
    } catch (error) {
      results.push({
        success: false,
        message: error.message || '请求异常'
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
 * @param {Array<RequestOptions>} requests - 请求配置数组
 * @returns {Promise<Array<{success: boolean, data?: any, message?: string}>>}
 */
export async function parallelRequest(requests) {
  const promises = requests.map(req => request(req))
  return Promise.all(promises)
}

export const apiRequest = request

/**
 * 解包 API 响应数据
 * 
 * @param {Object} response - apiRequest 返回的响应对象
 * @returns {any} 实际的数据
 * 
 * @description
 * apiRequest 返回的格式是 {success: boolean, data?: any, message?: string}
 * 这个函数帮助解包出实际的数据
 * 
 * @example
 * const response = await get('/api/users')
 * const data = unwrapResponse(response) // 直接获取实际数据
 */
export function unwrapResponse(response) {
  if (!response) {
    return null
  }
  // 如果已经是解包后的数据（直接是对象且有 items 等字段）
  if (response.items || response.total || response.id) {
    return response
  }
  // 如果是 apiRequest 包装的格式
  return response.data || response
}
