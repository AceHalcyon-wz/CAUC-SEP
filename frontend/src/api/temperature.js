/**
 * @file temperature.js
 * @path src/api/
 * @description 温度控制API接口封装
 * @author Agent
 * @date 2024-03-14
 * @dependencies utils/apiRequest
 */

import { get, post, put } from '../utils/apiRequest';

/**
 * 获取温度状态
 *
 * @param {string} [sensorId='default'] - 传感器ID
 * @returns {Promise<Object|null>} 温度状态信息
 */
export async function getTemperatureStatus(sensorId = 'default') {
  const result = await get(`/api/v1/temperature/${sensorId}/status`, null, {
    onError: (msg) => console.error('[TemperatureAPI] Get status error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取当前温度值
 *
 * @param {string} [sensorId='default'] - 传感器ID
 * @returns {Promise<Object|null>} 当前温度值
 */
export async function getCurrentTemperature(sensorId = 'default') {
  const result = await get(`/api/v1/temperature/${sensorId}/current`, null, {
    onError: (msg) => console.error('[TemperatureAPI] Get current temperature error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 设置目标温度
 *
 * @param {Object} params - 温度参数
 * @param {string} [params.sensor_id='default'] - 传感器ID
 * @param {number} params.target_temp - 目标温度（摄氏度）
 * @param {number} [params.ramp_rate] - 升降温速率（度/分钟）
 * @returns {Promise<Object|null>} 设置结果
 */
export async function setTargetTemperature(params) {
  const result = await post('/api/v1/temperature/target', params, {
    onError: (msg) => console.error('[TemperatureAPI] Set target temperature error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 启动温度控制
 *
 * @param {string} [sensorId='default'] - 传感器ID
 * @returns {Promise<boolean>} 是否启动成功
 */
export async function startTemperatureControl(sensorId = 'default') {
  const result = await post(`/api/v1/temperature/${sensorId}/start`, null, {
    onError: (msg) => console.error('[TemperatureAPI] Start control error:', msg)
  });

  return result.success;
}

/**
 * 停止温度控制
 *
 * @param {string} [sensorId='default'] - 传感器ID
 * @returns {Promise<boolean>} 是否停止成功
 */
export async function stopTemperatureControl(sensorId = 'default') {
  const result = await post(`/api/v1/temperature/${sensorId}/stop`, null, {
    onError: (msg) => console.error('[TemperatureAPI] Stop control error:', msg)
  });

  return result.success;
}

/**
 * 获取温度控制配置
 *
 * @param {string} [sensorId='default'] - 传感器ID
 * @returns {Promise<Object|null>} 温度控制配置
 */
export async function getTemperatureConfig(sensorId = 'default') {
  const result = await get(`/api/v1/temperature/${sensorId}/config`, null, {
    onError: (msg) => console.error('[TemperatureAPI] Get config error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 更新温度控制配置
 *
 * @param {string} sensorId - 传感器ID
 * @param {Object} config - 配置参数
 * @param {number} [config.kp] - PID比例系数
 * @param {number} [config.ki] - PID积分系数
 * @param {number} [config.kd] - PID微分系数
 * @param {number} [config.max_power] - 最大功率
 * @returns {Promise<Object|null>} 更新后的配置
 */
export async function updateTemperatureConfig(sensorId, config) {
  const result = await put(`/api/v1/temperature/${sensorId}/config`, config, {
    onError: (msg) => console.error('[TemperatureAPI] Update config error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取温度历史数据
 *
 * @param {string} [sensorId='default'] - 传感器ID
 * @param {Object} params - 查询参数
 * @param {number} [params.duration=300] - 查询时长（秒）
 * @param {string} [params.interval='1s'] - 数据间隔
 * @returns {Promise<Object|null>} 温度历史数据
 */
export async function getTemperatureHistory(sensorId = 'default', params = {}) {
  const result = await get(`/api/v1/temperature/${sensorId}/history`, params, {
    onError: (msg) => console.error('[TemperatureAPI] Get history error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 设置温度报警阈值
 *
 * @param {Object} params - 报警参数
 * @param {string} [params.sensor_id='default'] - 传感器ID
 * @param {number} params.high_limit - 高温报警阈值
 * @param {number} params.low_limit - 低温报警阈值
 * @returns {Promise<boolean>} 是否设置成功
 */
export async function setTemperatureAlarm(params) {
  const result = await post('/api/v1/temperature/alarm', params, {
    onError: (msg) => console.error('[TemperatureAPI] Set alarm error:', msg)
  });

  return result.success;
}

/**
 * 获取温度报警状态
 *
 * @param {string} [sensorId='default'] - 传感器ID
 * @returns {Promise<Object|null>} 报警状态
 */
export async function getTemperatureAlarmStatus(sensorId = 'default') {
  const result = await get(`/api/v1/temperature/${sensorId}/alarm`, null, {
    onError: (msg) => console.error('[TemperatureAPI] Get alarm status error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 清除温度报警
 *
 * @param {string} [sensorId='default'] - 传感器ID
 * @returns {Promise<boolean>} 是否清除成功
 */
export async function clearTemperatureAlarm(sensorId = 'default') {
  const result = await post(`/api/v1/temperature/${sensorId}/alarm/clear`, null, {
    onError: (msg) => console.error('[TemperatureAPI] Clear alarm error:', msg)
  });

  return result.success;
}

/**
 * 执行温度校准
 *
 * @param {string} [sensorId='default'] - 传感器ID
 * @param {Object} params - 校准参数
 * @param {number} params.reference_temp - 参考温度
 * @returns {Promise<Object|null>} 校准结果
 */
export async function calibrateTemperature(sensorId = 'default', params = {}) {
  const result = await post(`/api/v1/temperature/${sensorId}/calibrate`, params, {
    onError: (msg) => console.error('[TemperatureAPI] Calibrate error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取加热器状态
 *
 * @param {string} [sensorId='default'] - 传感器ID
 * @returns {Promise<Object|null>} 加热器状态
 */
export async function getHeaterStatus(sensorId = 'default') {
  const result = await get(`/api/v1/temperature/${sensorId}/heater`, null, {
    onError: (msg) => console.error('[TemperatureAPI] Get heater status error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 设置加热器功率
 *
 * @param {Object} params - 功率参数
 * @param {string} [params.sensor_id='default'] - 传感器ID
 * @param {number} params.power - 功率百分比（0-100）
 * @returns {Promise<boolean>} 是否设置成功
 */
export async function setHeaterPower(params) {
  const result = await post('/api/v1/temperature/heater/power', params, {
    onError: (msg) => console.error('[TemperatureAPI] Set heater power error:', msg)
  });

  return result.success;
}

/**
 * 获取所有温度传感器列表
 *
 * @returns {Promise<Object|null>} 传感器列表
 */
export async function getTemperatureSensorList() {
  const result = await get('/api/v1/temperature/sensors', null, {
    onError: (msg) => console.error('[TemperatureAPI] Get sensor list error:', msg)
  });

  return result.success ? result.data : null;
}
