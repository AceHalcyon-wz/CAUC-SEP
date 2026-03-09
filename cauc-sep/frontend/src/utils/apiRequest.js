/**
 * @file apiRequest.js
 * @path src/utils/
 * @description 统一API请求包装模块，提供标准化的HTTP请求方法
 * @author Agent
 * @date 2024-03-06
 * @dependencies axios, config/api
 */

import axios from 'axios'
import { API_BASE } from '../config/api'

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
 */

/**
 * 统一API请求包装函数
 * 
 * @param {RequestOptions} options - 请求选项
 * @returns {Promise<{success: boolean, data?: any, message?: string}>}
 * 
 * @example
 * const result = await request({
 *   method: 'GET',
 *   url: '/api/users',
 *   onLoading: (key, state) => console.log(key, state),
 *   loadingKey: 'fetchUsers'
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
    loadingKey
  } = options

  // 设置加载状态
  if (onLoading && loadingKey) {
    onLoading(loadingKey, true)
  }

  try {
    const config = {
      method,
      url: `${API_BASE}${url}`,
      headers: {
        'Content-Type': 'application/json'
      }
    }

    // 添加请求体数据
    if (data) {
      config.data = data
    }

    // 添加URL查询参数
    if (params) {
      config.params = params
    }

    const response = await axios(config)

    // 处理成功响应
    if (response.data.success) {
      return {
        success: true,
        data: response.data.data,
        message: response.data.message
      }
    } else {
      // 业务逻辑错误
      const errorMessage = response.data.message || '操作失败'
      if (onError) {
        onError(errorMessage)
      }
      return {
        success: false,
        message: errorMessage
      }
    }
  } catch (error) {
    // 网络或服务器错误处理
    const errorMessage = error.response?.data?.detail || error.message || '网络请求失败'
    if (onError) {
      onError(errorMessage)
    }
    return {
      success: false,
      message: errorMessage
    }
  } finally {
    // 清除加载状态
    if (onLoading && loadingKey) {
      onLoading(loadingKey, false)
    }
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
 * const result = await get('/api/users', { page: 1, size: 10 });
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
 * 
 * @example
 * const result = await put('/api/users/123', { name: '李四' });
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
 * 
 * @example
 * const result = await del('/api/users/123');
 */
export async function del(url, options = {}) {
  return request({ ...options, method: 'DELETE', url })
}

export const apiRequest = request
