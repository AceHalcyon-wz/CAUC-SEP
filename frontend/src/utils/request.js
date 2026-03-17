/**
 * @file request.js
 * @path src/utils/
 * @description HTTP 请求工具模块 - 重新导出 apiRequest
 * @author Agent
 * @date 2024-03-17
 */

export { request, get, post, put, del, batchRequest, parallelRequest, clearCache, cancelPendingRequests, apiRequest, unwrapResponse } from './apiRequest'
export default (await import('./apiRequest')).request
