/**
 * @file device.js
 * @path src/api/
 * @description 设备管理API接口封装
 * @author Agent
 * @date 2024-03-15
 * @dependencies utils/apiRequest
 */

import { get, post, put, del } from '../utils/apiRequest';

/**
 * 获取设备列表
 *
 * @returns {Promise<Array|null>} 设备列表
 */
export async function getDeviceList() {
  const result = await get('/api/v1/device/list', null, {
    onError: (msg) => console.error('[DeviceAPI] Get device list error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取指定设备状态
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
 * 连接设备
 *
 * @param {string} deviceId - 设备ID
 * @param {Object} params - 连接参数
 * @returns {Promise<Object|null>} 连接结果
 */
export async function connectDevice(deviceId, params) {
  const result = await post(`/api/v1/device/${deviceId}/connect`, params, {
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
  const result = await post(`/api/v1/device/${deviceId}/disconnect`, null, {
    onError: (msg) => console.error('[DeviceAPI] Disconnect device error:', msg)
  });

  return result.success;
}

/**
 * 获取DI功能代码列表
 *
 * @param {string} deviceId - 设备ID
 * @returns {Promise<Object|null>} DI功能代码列表
 */
export async function getDIFunctions(deviceId) {
  const result = await get(`/api/v1/device/${deviceId}/io/di/functions`, null, {
    onError: (msg) => console.error('[DeviceAPI] Get DI functions error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取DO功能代码列表
 *
 * @param {string} deviceId - 设备ID
 * @returns {Promise<Object|null>} DO功能代码列表
 */
export async function getDOFunctions(deviceId) {
  const result = await get(`/api/v1/device/${deviceId}/io/do/functions`, null, {
    onError: (msg) => console.error('[DeviceAPI] Get DO functions error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 配置DI端口功能
 *
 * @param {string} deviceId - 设备ID
 * @param {Object} params - 配置参数
 * @param {number} params.di_number - DI端口号
 * @param {number} params.function_code - 功能代码
 * @returns {Promise<boolean>} 是否配置成功
 */
export async function configureDI(deviceId, params) {
  const result = await post(`/api/v1/device/${deviceId}/io/di/configure`, params, {
    onError: (msg) => console.error('[DeviceAPI] Configure DI error:', msg)
  });

  return result.success;
}

/**
 * 配置DO端口功能
 *
 * @param {string} deviceId - 设备ID
 * @param {Object} params - 配置参数
 * @param {number} params.do_number - DO端口号
 * @param {number} params.function_code - 功能代码
 * @returns {Promise<boolean>} 是否配置成功
 */
export async function configureDO(deviceId, params) {
  const result = await post(`/api/v1/device/${deviceId}/io/do/configure`, params, {
    onError: (msg) => console.error('[DeviceAPI] Configure DO error:', msg)
  });

  return result.success;
}

/**
 * 读取所有DI端口状态
 *
 * @param {string} deviceId - 设备ID
 * @returns {Promise<Object|null>} DI端口状态
 */
export async function getDIStatus(deviceId) {
  const result = await get(`/api/v1/device/${deviceId}/io/di/status`, null, {
    onError: (msg) => console.error('[DeviceAPI] Get DI status error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 读取所有DO端口状态
 *
 * @param {string} deviceId - 设备ID
 * @returns {Promise<Object|null>} DO端口状态
 */
export async function getDOStatus(deviceId) {
  const result = await get(`/api/v1/device/${deviceId}/io/do/status`, null, {
    onError: (msg) => console.error('[DeviceAPI] Get DO status error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 读取指定DI端口配置
 *
 * @param {string} deviceId - 设备ID
 * @param {number} diNumber - DI端口号
 * @returns {Promise<Object|null>} DI端口配置
 */
export async function getDIConfig(deviceId, diNumber) {
  const result = await get(`/api/v1/device/${deviceId}/io/di/${diNumber}/config`, null, {
    onError: (msg) => console.error('[DeviceAPI] Get DI config error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 读取指定DO端口配置
 *
 * @param {string} deviceId - 设备ID
 * @param {number} doNumber - DO端口号
 * @returns {Promise<Object|null>} DO端口配置
 */
export async function getDOConfig(deviceId, doNumber) {
  const result = await get(`/api/v1/device/${deviceId}/io/do/${doNumber}/config`, null, {
    onError: (msg) => console.error('[DeviceAPI] Get DO config error:', msg)
  });

  return result.success ? result.data : null;
}
