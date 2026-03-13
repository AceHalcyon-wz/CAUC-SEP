/**
 * @file device.js
 * @path src/api/
 * @description 设备控制相关API接口封装
 * @author Agent
 * @date 2024-03-14
 * @dependencies utils/apiRequest
 */

import { get, post, put, del } from '../utils/apiRequest';

/**
 * 获取设备连接状态
 *
 * @returns {Promise<Object|null>} 设备连接状态信息
 */
export async function getConnectionStatus() {
  const result = await get('/api/v1/device/connection/status', null, {
    onError: (msg) => console.error('[DeviceAPI] Get connection status error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 连接设备
 *
 * @param {Object} params - 连接参数
 * @param {string} params.device_type - 设备类型
 * @param {string} params.port - 端口号
 * @param {number} [params.baud_rate=9600] - 波特率
 * @returns {Promise<Object|null>} 连接结果
 */
export async function connectDevice(params) {
  const result = await post('/api/v1/device/connection/connect', params, {
    onError: (msg) => console.error('[DeviceAPI] Connect device error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 断开设备连接
 *
 * @param {string} deviceId - 设备ID
 * @returns {Promise<boolean>} 是否断开成功
 */
export async function disconnectDevice(deviceId) {
  const result = await post('/api/v1/device/connection/disconnect', { device_id: deviceId }, {
    onError: (msg) => console.error('[DeviceAPI] Disconnect device error:', msg)
  });

  return result.success;
}

/**
 * 获取所有设备列表
 *
 * @returns {Promise<Object|null>} 设备列表
 */
export async function getDeviceList() {
  const result = await get('/api/v1/device/list', null, {
    onError: (msg) => console.error('[DeviceAPI] Get device list error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取设备详情
 *
 * @param {string} deviceId - 设备ID
 * @returns {Promise<Object|null>} 设备详情
 */
export async function getDeviceDetail(deviceId) {
  const result = await get(`/api/v1/device/${deviceId}`, null, {
    onError: (msg) => console.error('[DeviceAPI] Get device detail error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取设备状态
 *
 * @param {string} deviceId - 设备ID
 * @returns {Promise<Object|null>} 设备状态
 */
export async function getDeviceStatus(deviceId) {
  const result = await get(`/api/v1/device/${deviceId}/status`, null, {
    onError: (msg) => console.error('[DeviceAPI] Get device status error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 更新设备配置
 *
 * @param {string} deviceId - 设备ID
 * @param {Object} config - 配置参数
 * @returns {Promise<Object|null>} 更新结果
 */
export async function updateDeviceConfig(deviceId, config) {
  const result = await put(`/api/v1/device/${deviceId}/config`, config, {
    onError: (msg) => console.error('[DeviceAPI] Update device config error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 扫描可用设备
 *
 * @param {Object} params - 扫描参数
 * @param {string} [params.device_type] - 设备类型过滤
 * @returns {Promise<Object|null>} 扫描结果
 */
export async function scanDevices(params = {}) {
  const result = await post('/api/v1/device/scan', params, {
    onError: (msg) => console.error('[DeviceAPI] Scan devices error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取设备诊断信息
 *
 * @param {string} deviceId - 设备ID
 * @returns {Promise<Object|null>} 诊断信息
 */
export async function getDeviceDiagnostics(deviceId) {
  const result = await get(`/api/v1/device/${deviceId}/diagnostics`, null, {
    onError: (msg) => console.error('[DeviceAPI] Get diagnostics error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 重启设备
 *
 * @param {string} deviceId - 设备ID
 * @returns {Promise<boolean>} 是否重启成功
 */
export async function restartDevice(deviceId) {
  const result = await post(`/api/v1/device/${deviceId}/restart`, null, {
    onError: (msg) => console.error('[DeviceAPI] Restart device error:', msg)
  });

  return result.success;
}

/**
 * 获取PR路径配置
 *
 * @returns {Promise<Object|null>} PR路径配置
 */
export async function getPRPathConfig() {
  const result = await get('/api/v1/device/pr-path/config', null, {
    onError: (msg) => console.error('[DeviceAPI] Get PR path config error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 保存PR路径配置
 *
 * @param {Object} config - PR路径配置
 * @returns {Promise<boolean>} 是否保存成功
 */
export async function savePRPathConfig(config) {
  const result = await post('/api/v1/device/pr-path/config', config, {
    onError: (msg) => console.error('[DeviceAPI] Save PR path config error:', msg)
  });

  return result.success;
}

/**
 * 执行PR路径
 *
 * @param {Object} params - 执行参数
 * @param {string} params.path_id - 路径ID
 * @param {number} [params.speed=1] - 执行速度倍率
 * @returns {Promise<Object|null>} 执行结果
 */
export async function executePRPath(params) {
  const result = await post('/api/v1/device/pr-path/execute', params, {
    onError: (msg) => console.error('[DeviceAPI] Execute PR path error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 停止PR路径执行
 *
 * @returns {Promise<boolean>} 是否停止成功
 */
export async function stopPRPath() {
  const result = await post('/api/v1/device/pr-path/stop', null, {
    onError: (msg) => console.error('[DeviceAPI] Stop PR path error:', msg)
  });

  return result.success;
}
