/**
 * @file ammeter.js
 * @path src/api/
 * @description 微电流计API接口封装
 * @author Agent
 * @date 2024-03-14
 * @dependencies utils/apiRequest
 */

import { get, post, put } from '../utils/apiRequest';

/**
 * 获取微电流计状态
 *
 * @param {string} [ammeterId='default'] - 微电流计ID
 * @returns {Promise<Object|null>} 微电流计状态信息
 */
export async function getAmmeterStatus(ammeterId = 'default') {
  const result = await get(`/api/v1/ammeter/${ammeterId}/status`, null, {
    onError: (msg) => console.error('[AmmeterAPI] Get status error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取当前电流值
 *
 * @param {string} [ammeterId='default'] - 微电流计ID
 * @returns {Promise<Object|null>} 当前电流值
 */
export async function getCurrentValue(ammeterId = 'default') {
  const result = await get(`/api/v1/ammeter/${ammeterId}/current`, null, {
    onError: (msg) => console.error('[AmmeterAPI] Get current value error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 设置量程
 *
 * @param {Object} params - 量程参数
 * @param {string} [params.ammeter_id='default'] - 微电流计ID
 * @param {string} params.range - 量程 ('auto' | '1nA' | '10nA' | '100nA' | '1uA' | '10uA')
 * @returns {Promise<boolean>} 是否设置成功
 */
export async function setCurrentRange(params) {
  const result = await post('/api/v1/ammeter/range', params, {
    onError: (msg) => console.error('[AmmeterAPI] Set range error:', msg)
  });

  return result.success;
}

/**
 * 获取当前量程
 *
 * @param {string} [ammeterId='default'] - 微电流计ID
 * @returns {Promise<Object|null>} 当前量程
 */
export async function getCurrentRange(ammeterId = 'default') {
  const result = await get(`/api/v1/ammeter/${ammeterId}/range`, null, {
    onError: (msg) => console.error('[AmmeterAPI] Get range error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 启动测量
 *
 * @param {string} [ammeterId='default'] - 微电流计ID
 * @returns {Promise<boolean>} 是否启动成功
 */
export async function startMeasurement(ammeterId = 'default') {
  const result = await post(`/api/v1/ammeter/${ammeterId}/start`, null, {
    onError: (msg) => console.error('[AmmeterAPI] Start measurement error:', msg)
  });

  return result.success;
}

/**
 * 停止测量
 *
 * @param {string} [ammeterId='default'] - 微电流计ID
 * @returns {Promise<boolean>} 是否停止成功
 */
export async function stopMeasurement(ammeterId = 'default') {
  const result = await post(`/api/v1/ammeter/${ammeterId}/stop`, null, {
    onError: (msg) => console.error('[AmmeterAPI] Stop measurement error:', msg)
  });

  return result.success;
}

/**
 * 执行零点校准
 *
 * @param {string} [ammeterId='default'] - 微电流计ID
 * @returns {Promise<Object|null>} 校准结果
 */
export async function zeroCalibrate(ammeterId = 'default') {
  const result = await post(`/api/v1/ammeter/${ammeterId}/zero`, null, {
    onError: (msg) => console.error('[AmmeterAPI] Zero calibrate error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取微电流计配置
 *
 * @param {string} [ammeterId='default'] - 微电流计ID
 * @returns {Promise<Object|null>} 微电流计配置
 */
export async function getAmmeterConfig(ammeterId = 'default') {
  const result = await get(`/api/v1/ammeter/${ammeterId}/config`, null, {
    onError: (msg) => console.error('[AmmeterAPI] Get config error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 更新微电流计配置
 *
 * @param {string} ammeterId - 微电流计ID
 * @param {Object} config - 配置参数
 * @param {number} [config.sample_rate] - 采样率
 * @param {number} [config.filter_time] - 滤波时间常数
 * @param {boolean} [config.auto_range] - 是否自动量程
 * @returns {Promise<Object|null>} 更新后的配置
 */
export async function updateAmmeterConfig(ammeterId, config) {
  const result = await put(`/api/v1/ammeter/${ammeterId}/config`, config, {
    onError: (msg) => console.error('[AmmeterAPI] Update config error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取测量历史数据
 *
 * @param {string} [ammeterId='default'] - 微电流计ID
 * @param {Object} params - 查询参数
 * @param {number} [params.duration=300] - 查询时长（秒）
 * @param {string} [params.interval='1s'] - 数据间隔
 * @returns {Promise<Object|null>} 测量历史数据
 */
export async function getMeasurementHistory(ammeterId = 'default', params = {}) {
  const result = await get(`/api/v1/ammeter/${ammeterId}/history`, params, {
    onError: (msg) => console.error('[AmmeterAPI] Get history error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 设置积分时间
 *
 * @param {Object} params - 积分参数
 * @param {string} [params.ammeter_id='default'] - 微电流计ID
 * @param {number} params.integration_time - 积分时间（ms）
 * @returns {Promise<boolean>} 是否设置成功
 */
export async function setIntegrationTime(params) {
  const result = await post('/api/v1/ammeter/integration', params, {
    onError: (msg) => console.error('[AmmeterAPI] Set integration time error:', msg)
  });

  return result.success;
}

/**
 * 设置滤波器
 *
 * @param {Object} params - 滤波参数
 * @param {string} [params.ammeter_id='default'] - 微电流计ID
 * @param {string} params.filter_type - 滤波类型 ('none' | 'low_pass' | 'moving_avg')
 * @param {number} [params.cutoff_frequency] - 截止频率
 * @returns {Promise<boolean>} 是否设置成功
 */
export async function setFilter(params) {
  const result = await post('/api/v1/ammeter/filter', params, {
    onError: (msg) => console.error('[AmmeterAPI] Set filter error:', msg)
  });

  return result.success;
}

/**
 * 获取统计数据
 *
 * @param {string} [ammeterId='default'] - 微电流计ID
 * @param {Object} params - 统计参数
 * @param {number} [params.window=60] - 统计窗口（秒）
 * @returns {Promise<Object|null>} 统计数据（最大、最小、平均、标准差等）
 */
export async function getStatistics(ammeterId = 'default', params = {}) {
  const result = await get(`/api/v1/ammeter/${ammeterId}/statistics`, params, {
    onError: (msg) => console.error('[AmmeterAPI] Get statistics error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 设置电流报警阈值
 *
 * @param {Object} params - 报警参数
 * @param {string} [params.ammeter_id='default'] - 微电流计ID
 * @param {number} params.high_limit - 高限报警值
 * @param {number} params.low_limit - 低限报警值
 * @returns {Promise<boolean>} 是否设置成功
 */
export async function setCurrentAlarm(params) {
  const result = await post('/api/v1/ammeter/alarm', params, {
    onError: (msg) => console.error('[AmmeterAPI] Set alarm error:', msg)
  });

  return result.success;
}

/**
 * 获取报警状态
 *
 * @param {string} [ammeterId='default'] - 微电流计ID
 * @returns {Promise<Object|null>} 报警状态
 */
export async function getAlarmStatus(ammeterId = 'default') {
  const result = await get(`/api/v1/ammeter/${ammeterId}/alarm`, null, {
    onError: (msg) => console.error('[AmmeterAPI] Get alarm status error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 清除报警
 *
 * @param {string} [ammeterId='default'] - 微电流计ID
 * @returns {Promise<boolean>} 是否清除成功
 */
export async function clearAlarm(ammeterId = 'default') {
  const result = await post(`/api/v1/ammeter/${ammeterId}/alarm/clear`, null, {
    onError: (msg) => console.error('[AmmeterAPI] Clear alarm error:', msg)
  });

  return result.success;
}

/**
 * 导出测量数据
 *
 * @param {string} [ammeterId='default'] - 微电流计ID
 * @param {Object} params - 导出参数
 * @param {string} params.format - 导出格式 ('csv' | 'json' | 'excel')
 * @param {number} [params.start_time] - 开始时间戳
 * @param {number} [params.end_time] - 结束时间戳
 * @returns {Promise<Blob>} 文件Blob对象
 */
export async function exportMeasurementData(ammeterId = 'default', params) {
  try {
    const response = await fetch(`/api/v1/ammeter/${ammeterId}/export`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(params),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.blob();
  } catch (error) {
    console.error('[AmmeterAPI] Export data error:', error);
    throw error;
  }
}
