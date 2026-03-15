/**
 * @file healthCheck.js
 * @path src/utils/
 * @description 后端服务健康检查工具
 * @author Agent
 * @date 2026-03-15
 * @version 1.0.0
 */

import { API_BASE_URL } from '../config/api'

/**
 * 健康检查配置
 */
const HEALTH_CHECK_CONFIG = {
  /** 超时时间（毫秒） */
  timeout: 5000,
  /** 重试次数 */
  maxRetries: 2,
  /** 重试间隔（毫秒） */
  retryInterval: 1000,
  /** 健康检查端点 */
  endpoint: '/api/v1/health'
}

/**
 * 服务健康状态
 */
export const HealthStatus = {
  /** 健康 */
  HEALTHY: 'healthy',
  /** 不健康 */
  UNHEALTHY: 'unhealthy',
  /** 未知 */
  UNKNOWN: 'unknown',
  /** 超时 */
  TIMEOUT: 'timeout'
}

/**
 * 延迟执行
 */
function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * 执行单次健康检查
 */
async function checkOnce() {
  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), HEALTH_CHECK_CONFIG.timeout)

    const response = await fetch(`${API_BASE_URL}${HEALTH_CHECK_CONFIG.endpoint}`, {
      method: 'GET',
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json'
      }
    })

    clearTimeout(timeoutId)

    if (response.ok) {
      const data = await response.json()
      return {
        status: HealthStatus.HEALTHY,
        data,
        responseTime: Date.now()
      }
    } else {
      return {
        status: HealthStatus.UNHEALTHY,
        error: `HTTP ${response.status}`,
        responseTime: Date.now()
      }
    }
  } catch (error) {
    if (error.name === 'AbortError') {
      return {
        status: HealthStatus.TIMEOUT,
        error: '请求超时',
        responseTime: Date.now()
      }
    }

    return {
      status: HealthStatus.UNHEALTHY,
      error: error.message || '网络错误',
      responseTime: Date.now()
    }
  }
}

/**
 * 执行健康检查（带重试机制）
 * 
 * @param {Object} [options] - 选项
 * @param {boolean} [options.useCache=true] - 是否使用缓存结果
 * @param {number} [options.cacheTTL=30000] - 缓存有效期（毫秒）
 * @returns {Promise<{status: string, healthy: boolean, data?: Object, error?: string, responseTime?: number}>}
 */
let lastCheckResult = null
let lastCheckTime = 0

export async function checkHealth(options = {}) {
  const {
    useCache = true,
    cacheTTL = 30000
  } = options

  // 检查缓存
  const now = Date.now()
  if (useCache && lastCheckResult && (now - lastCheckTime) < cacheTTL) {
    return {
      ...lastCheckResult,
      cached: true
    }
  }

  let lastError = null
  let retryCount = 0

  while (retryCount <= HEALTH_CHECK_CONFIG.maxRetries) {
    const result = await checkOnce()
    
    if (result.status === HealthStatus.HEALTHY) {
      lastCheckResult = result
      lastCheckTime = now
      
      return {
        status: HealthStatus.HEALTHY,
        healthy: true,
        data: result.data,
        responseTime: result.responseTime,
        cached: false
      }
    }

    lastError = result.error
    
    if (retryCount < HEALTH_CHECK_CONFIG.maxRetries) {
      retryCount++
      await delay(HEALTH_CHECK_CONFIG.retryInterval)
      continue
    }

    break
  }

  const failureResult = {
    status: HealthStatus.UNHEALTHY,
    healthy: false,
    error: lastError || '健康检查失败',
    responseTime: Date.now(),
    cached: false
  }

  lastCheckResult = failureResult
  lastCheckTime = now
  
  return failureResult
}

/**
 * 快速检查（仅检查网络连通性）
 * 
 * @returns {Promise<boolean>}
 */
export async function quickCheck() {
  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 2000)

    const response = await fetch(`${API_BASE_URL}/`, {
      method: 'HEAD',
      signal: controller.signal
    })

    clearTimeout(timeoutId)
    return response.ok || response.status === 404
  } catch {
    return false
  }
}

/**
 * 清除健康检查缓存
 */
export function clearHealthCache() {
  lastCheckResult = null
  lastCheckTime = 0
}

/**
 * 获取上次检查结果
 * 
 * @returns {{status: string, healthy: boolean, error?: string, responseTime?: number}|null}
 */
export function getLastCheckResult() {
  return lastCheckResult
}

/**
 * 自动登录前检查
 * 
 * @returns {Promise<{shouldUseQuickLogin: boolean, reason?: string}>}
 */
export async function shouldUseQuickLogin() {
  const health = await checkHealth()
  
  if (health.healthy) {
    return {
      shouldUseQuickLogin: true,
      reason: '后端服务正常'
    }
  }

  return {
    shouldUseQuickLogin: false,
    reason: health.error || '后端服务不可用，建议使用快速登录模式'
  }
}
