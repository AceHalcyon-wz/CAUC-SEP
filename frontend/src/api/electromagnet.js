/**
 * @file electromagnet.js
 * @path src/api/
 * @description 电磁铁控制API接口封装
 * @author Agent
 * @date 2024-03-14
 * @dependencies utils/apiRequest
 */

import { get, post, put } from '../utils/apiRequest';

/**
 * 获取电磁铁状态
 *
 * @param {string} [magnetId='default'] - 电磁铁ID
 * @returns {Promise<Object|null>} 电磁铁状态信息
 */
export async function getElectromagnetStatus(magnetId = 'default') {
  const result = await get(`/api/v1/electromagnet/${magnetId}/status`, null, {
    onError: (msg) => console.error('[ElectromagnetAPI] Get status error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 设置磁场强度
 *
 * @param {Object} params - 磁场参数
 * @param {string} [params.magnet_id='default'] - 电磁铁ID
 * @param {number} params.field_strength - 磁场强度（mT或A）
 * @param {number} [params.ramp_rate] - 变化速率
 * @returns {Promise<Object|null>} 设置结果
 */
export async function setMagneticField(params) {
  const result = await post('/api/v1/electromagnet/field', params, {
    onError: (msg) => console.error('[ElectromagnetAPI] Set field error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取当前磁场强度
 *
 * @param {string} [magnetId='default'] - 电磁铁ID
 * @returns {Promise<Object|null>} 当前磁场强度
 */
export async function getCurrentField(magnetId = 'default') {
  const result = await get(`/api/v1/electromagnet/${magnetId}/field/current`, null, {
    onError: (msg) => console.error('[ElectromagnetAPI] Get current field error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 启用电磁铁
 *
 * @param {string} [magnetId='default'] - 电磁铁ID
 * @returns {Promise<boolean>} 是否启用成功
 */
export async function enableElectromagnet(magnetId = 'default') {
  const result = await post(`/api/v1/electromagnet/${magnetId}/enable`, null, {
    onError: (msg) => console.error('[ElectromagnetAPI] Enable error:', msg)
  });

  return result.success;
}

/**
 * 禁用电磁铁
 *
 * @param {string} [magnetId='default'] - 电磁铁ID
 * @returns {Promise<boolean>} 是否禁用成功
 */
export async function disableElectromagnet(magnetId = 'default') {
  const result = await post(`/api/v1/electromagnet/${magnetId}/disable`, null, {
    onError: (msg) => console.error('[ElectromagnetAPI] Disable error:', msg)
  });

  return result.success;
}

/**
 * 设置电磁铁电流
 *
 * @param {Object} params - 电流参数
 * @param {string} [params.magnet_id='default'] - 电磁铁ID
 * @param {number} params.current - 电流值（A）
 * @returns {Promise<boolean>} 是否设置成功
 */
export async function setElectromagnetCurrent(params) {
  const result = await post('/api/v1/electromagnet/current', params, {
    onError: (msg) => console.error('[ElectromagnetAPI] Set current error:', msg)
  });

  return result.success;
}

/**
 * 获取电磁铁电流
 *
 * @param {string} [magnetId='default'] - 电磁铁ID
 * @returns {Promise<Object|null>} 当前电流值
 */
export async function getElectromagnetCurrent(magnetId = 'default') {
  const result = await get(`/api/v1/electromagnet/${magnetId}/current`, null, {
    onError: (msg) => console.error('[ElectromagnetAPI] Get current error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取电磁铁配置
 *
 * @param {string} [magnetId='default'] - 电磁铁ID
 * @returns {Promise<Object|null>} 电磁铁配置
 */
export async function getElectromagnetConfig(magnetId = 'default') {
  const result = await get(`/api/v1/electromagnet/${magnetId}/config`, null, {
    onError: (msg) => console.error('[ElectromagnetAPI] Get config error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 更新电磁铁配置
 *
 * @param {string} magnetId - 电磁铁ID
 * @param {Object} config - 配置参数
 * @param {number} [config.max_current] - 最大电流
 * @param {number} [config.max_field] - 最大磁场强度
 * @param {number} [config.ramp_rate_limit] - 最大变化速率
 * @returns {Promise<Object|null>} 更新后的配置
 */
export async function updateElectromagnetConfig(magnetId, config) {
  const result = await put(`/api/v1/electromagnet/${magnetId}/config`, config, {
    onError: (msg) => console.error('[ElectromagnetAPI] Update config error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 磁场归零
 *
 * @param {string} [magnetId='default'] - 电磁铁ID
 * @returns {Promise<Object|null>} 归零结果
 */
export async function zeroMagneticField(magnetId = 'default') {
  const result = await post(`/api/v1/electromagnet/${magnetId}/zero`, null, {
    onError: (msg) => console.error('[ElectromagnetAPI] Zero field error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取磁场历史数据
 *
 * @param {string} [magnetId='default'] - 电磁铁ID
 * @param {Object} params - 查询参数
 * @param {number} [params.duration=300] - 查询时长（秒）
 * @returns {Promise<Object|null>} 磁场历史数据
 */
export async function getFieldHistory(magnetId = 'default', params = {}) {
  const result = await get(`/api/v1/electromagnet/${magnetId}/history`, params, {
    onError: (msg) => console.error('[ElectromagnetAPI] Get history error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 设置磁场极性
 *
 * @param {Object} params - 极性参数
 * @param {string} [params.magnet_id='default'] - 电磁铁ID
 * @param {string} params.polarity - 极性 ('positive' | 'negative')
 * @returns {Promise<boolean>} 是否设置成功
 */
export async function setFieldPolarity(params) {
  const result = await post('/api/v1/electromagnet/polarity', params, {
    onError: (msg) => console.error('[ElectromagnetAPI] Set polarity error:', msg)
  });

  return result.success;
}

/**
 * 反转磁场极性
 *
 * @param {string} [magnetId='default'] - 电磁铁ID
 * @returns {Promise<boolean>} 是否反转成功
 */
export async function reverseFieldPolarity(magnetId = 'default') {
  const result = await post(`/api/v1/electromagnet/${magnetId}/reverse`, null, {
    onError: (msg) => console.error('[ElectromagnetAPI] Reverse polarity error:', msg)
  });

  return result.success;
}

/**
 * 获取电磁铁温度
 *
 * @param {string} [magnetId='default'] - 电磁铁ID
 * @returns {Promise<Object|null>} 温度信息
 */
export async function getElectromagnetTemperature(magnetId = 'default') {
  const result = await get(`/api/v1/electromagnet/${magnetId}/temperature`, null, {
    onError: (msg) => console.error('[ElectromagnetAPI] Get temperature error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 执行电磁铁校准
 *
 * @param {string} [magnetId='default'] - 电磁铁ID
 * @returns {Promise<Object|null>} 校准结果
 */
export async function calibrateElectromagnet(magnetId = 'default') {
  const result = await post(`/api/v1/electromagnet/${magnetId}/calibrate`, null, {
    onError: (msg) => console.error('[ElectromagnetAPI] Calibrate error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取电磁铁安全状态
 *
 * @param {string} [magnetId='default'] - 电磁铁ID
 * @returns {Promise<Object|null>} 安全状态信息
 */
export async function getElectromagnetSafetyStatus(magnetId = 'default') {
  const result = await get(`/api/v1/electromagnet/${magnetId}/safety`, null, {
    onError: (msg) => console.error('[ElectromagnetAPI] Get safety status error:', msg)
  });

  return result.success ? result.data : null;
}
