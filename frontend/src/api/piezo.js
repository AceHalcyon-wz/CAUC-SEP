/**
 * @file piezo.js
 * @path src/api/
 * @description 压电陶瓷控制API接口封装
 * @author Agent
 * @date 2024-03-14
 * @dependencies utils/apiRequest
 */

import { get, post, put } from '../utils/apiRequest';

/**
 * 获取压电陶瓷状态
 *
 * @param {string} [piezoId='default'] - 压电陶瓷ID
 * @returns {Promise<Object|null>} 压电陶瓷状态信息
 */
export async function getPiezoStatus(piezoId = 'default') {
  const result = await get(`/api/v1/piezo/${piezoId}/status`, null, {
    onError: (msg) => console.error('[PiezoAPI] Get status error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 设置压电陶瓷电压
 *
 * @param {Object} params - 电压参数
 * @param {string} [params.piezo_id='default'] - 压电陶瓷ID
 * @param {number} params.voltage - 目标电压（V）
 * @param {number} [params.channel] - 通道号（多通道设备）
 * @returns {Promise<Object|null>} 设置结果
 */
export async function setPiezoVoltage(params) {
  const result = await post('/api/v1/piezo/voltage', params, {
    onError: (msg) => console.error('[PiezoAPI] Set voltage error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取当前电压
 *
 * @param {string} [piezoId='default'] - 压电陶瓷ID
 * @param {number} [channel] - 通道号
 * @returns {Promise<Object|null>} 当前电压值
 */
export async function getCurrentVoltage(piezoId = 'default', channel) {
  const params = channel !== undefined ? { channel } : null;
  const result = await get(`/api/v1/piezo/${piezoId}/voltage`, params, {
    onError: (msg) => console.error('[PiezoAPI] Get current voltage error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 设置压电陶瓷位移
 *
 * @param {Object} params - 位移参数
 * @param {string} [params.piezo_id='default'] - 压电陶瓷ID
 * @param {number} params.displacement - 目标位移（μm）
 * @param {number} [params.channel] - 通道号
 * @returns {Promise<Object|null>} 设置结果
 */
export async function setPiezoDisplacement(params) {
  const result = await post('/api/v1/piezo/displacement', params, {
    onError: (msg) => console.error('[PiezoAPI] Set displacement error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取当前位移
 *
 * @param {string} [piezoId='default'] - 压电陶瓷ID
 * @returns {Promise<Object|null>} 当前位移值
 */
export async function getCurrentDisplacement(piezoId = 'default') {
  const result = await get(`/api/v1/piezo/${piezoId}/displacement`, null, {
    onError: (msg) => console.error('[PiezoAPI] Get displacement error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 启用压电陶瓷
 *
 * @param {string} [piezoId='default'] - 压电陶瓷ID
 * @returns {Promise<boolean>} 是否启用成功
 */
export async function enablePiezo(piezoId = 'default') {
  const result = await post(`/api/v1/piezo/${piezoId}/enable`, null, {
    onError: (msg) => console.error('[PiezoAPI] Enable error:', msg)
  });

  return result.success;
}

/**
 * 禁用压电陶瓷
 *
 * @param {string} [piezoId='default'] - 压电陶瓷ID
 * @returns {Promise<boolean>} 是否禁用成功
 */
export async function disablePiezo(piezoId = 'default') {
  const result = await post(`/api/v1/piezo/${piezoId}/disable`, null, {
    onError: (msg) => console.error('[PiezoAPI] Disable error:', msg)
  });

  return result.success;
}

/**
 * 压电陶瓷归零
 *
 * @param {string} [piezoId='default'] - 压电陶瓷ID
 * @returns {Promise<Object|null>} 归零结果
 */
export async function zeroPiezo(piezoId = 'default') {
  const result = await post(`/api/v1/piezo/${piezoId}/zero`, null, {
    onError: (msg) => console.error('[PiezoAPI] Zero error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取压电陶瓷配置
 *
 * @param {string} [piezoId='default'] - 压电陶瓷ID
 * @returns {Promise<Object|null>} 压电陶瓷配置
 */
export async function getPiezoConfig(piezoId = 'default') {
  const result = await get(`/api/v1/piezo/${piezoId}/config`, null, {
    onError: (msg) => console.error('[PiezoAPI] Get config error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 更新压电陶瓷配置
 *
 * @param {string} piezoId - 压电陶瓷ID
 * @param {Object} config - 配置参数
 * @param {number} [config.max_voltage] - 最大电压
 * @param {number} [config.max_displacement] - 最大位移
 * @param {number} [config.sensitivity] - 灵敏度
 * @returns {Promise<Object|null>} 更新后的配置
 */
export async function updatePiezoConfig(piezoId, config) {
  const result = await put(`/api/v1/piezo/${piezoId}/config`, config, {
    onError: (msg) => console.error('[PiezoAPI] Update config error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取通道列表
 *
 * @param {string} [piezoId='default'] - 压电陶瓷ID
 * @returns {Promise<Object|null>} 通道列表
 */
export async function getPiezoChannels(piezoId = 'default') {
  const result = await get(`/api/v1/piezo/${piezoId}/channels`, null, {
    onError: (msg) => console.error('[PiezoAPI] Get channels error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 设置所有通道电压
 *
 * @param {Object} params - 多通道电压参数
 * @param {string} [params.piezo_id='default'] - 压电陶瓷ID
 * @param {Array<number>} params.voltages - 各通道电压数组
 * @returns {Promise<boolean>} 是否设置成功
 */
export async function setAllChannelVoltages(params) {
  const result = await post('/api/v1/piezo/voltages', params, {
    onError: (msg) => console.error('[PiezoAPI] Set all voltages error:', msg)
  });

  return result.success;
}

/**
 * 获取电压历史数据
 *
 * @param {string} [piezoId='default'] - 压电陶瓷ID
 * @param {Object} params - 查询参数
 * @param {number} [params.duration=300] - 查询时长（秒）
 * @param {number} [params.channel] - 通道号
 * @returns {Promise<Object|null>} 电压历史数据
 */
export async function getVoltageHistory(piezoId = 'default', params = {}) {
  const result = await get(`/api/v1/piezo/${piezoId}/history`, params, {
    onError: (msg) => console.error('[PiezoAPI] Get history error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 执行压电陶瓷校准
 *
 * @param {string} [piezoId='default'] - 压电陶瓷ID
 * @param {Object} params - 校准参数
 * @param {number} [params.reference_voltage] - 参考电压
 * @param {number} [params.reference_displacement] - 参考位移
 * @returns {Promise<Object|null>} 校准结果
 */
export async function calibratePiezo(piezoId = 'default', params = {}) {
  const result = await post(`/api/v1/piezo/${piezoId}/calibrate`, params, {
    onError: (msg) => console.error('[PiezoAPI] Calibrate error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取压电陶瓷温度
 *
 * @param {string} [piezoId='default'] - 压电陶瓷ID
 * @returns {Promise<Object|null>} 温度信息
 */
export async function getPiezoTemperature(piezoId = 'default') {
  const result = await get(`/api/v1/piezo/${piezoId}/temperature`, null, {
    onError: (msg) => console.error('[PiezoAPI] Get temperature error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 设置扫描模式
 *
 * @param {Object} params - 扫描参数
 * @param {string} [params.piezo_id='default'] - 压电陶瓷ID
 * @param {string} params.mode - 扫描模式 ('sawtooth' | 'triangle' | 'sine')
 * @param {number} params.amplitude - 扫描幅度
 * @param {number} params.frequency - 扫描频率
 * @returns {Promise<boolean>} 是否设置成功
 */
export async function setPiezoScanMode(params) {
  const result = await post('/api/v1/piezo/scan', params, {
    onError: (msg) => console.error('[PiezoAPI] Set scan mode error:', msg)
  });

  return result.success;
}

/**
 * 停止扫描
 *
 * @param {string} [piezoId='default'] - 压电陶瓷ID
 * @returns {Promise<boolean>} 是否停止成功
 */
export async function stopPiezoScan(piezoId = 'default') {
  const result = await post(`/api/v1/piezo/${piezoId}/scan/stop`, null, {
    onError: (msg) => console.error('[PiezoAPI] Stop scan error:', msg)
  });

  return result.success;
}
