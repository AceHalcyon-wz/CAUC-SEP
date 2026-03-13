/**
 * @file api.js
 * @path src/config/
 * @description API配置文件，统一管理API基础路径和版本前缀
 * @author Agent
 * @date 2024-03-07
 */

/** API基础URL */
export const API_BASE_URL = 'http://127.0.0.1:8000'

/** API版本前缀 */
export const API_VERSION = '/api/v1'

/** 完整API基础路径（包含版本前缀） */
export const API_BASE = `${API_BASE_URL}${API_VERSION}`

/** WebSocket基础URL */
export const WS_BASE_URL = 'ws://127.0.0.1:8000'

export default {
  API_BASE_URL,
  API_VERSION,
  API_BASE,
  WS_BASE_URL
}
