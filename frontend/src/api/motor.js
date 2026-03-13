/**
 * @file motor.js
 * @path src/api/
 * @description 电机控制API接口封装
 * @author Agent
 * @date 2024-03-14
 * @dependencies utils/apiRequest
 */

import { get, post, put } from '../utils/apiRequest';

/**
 * 获取电机状态
 *
 * @param {string} [motorId='default'] - 电机ID
 * @returns {Promise<Object|null>} 电机状态信息
 */
export async function getMotorStatus(motorId = 'default') {
  const result = await get(`/api/v1/motor/${motorId}/status`, null, {
    onError: (msg) => console.error('[MotorAPI] Get status error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 设置电机位置
 *
 * @param {Object} params - 位置参数
 * @param {string} [params.motor_id='default'] - 电机ID
 * @param {number} params.position - 目标位置（角度或步数）
 * @param {number} [params.speed=100] - 移动速度
 * @param {boolean} [params.absolute=true] - 是否绝对定位
 * @returns {Promise<Object|null>} 设置结果
 */
export async function setMotorPosition(params) {
  const result = await post('/api/v1/motor/position', params, {
    onError: (msg) => console.error('[MotorAPI] Set position error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 设置电机速度
 *
 * @param {Object} params - 速度参数
 * @param {string} [params.motor_id='default'] - 电机ID
 * @param {number} params.speed - 目标速度
 * @returns {Promise<boolean>} 是否设置成功
 */
export async function setMotorSpeed(params) {
  const result = await post('/api/v1/motor/speed', params, {
    onError: (msg) => console.error('[MotorAPI] Set speed error:', msg)
  });

  return result.success;
}

/**
 * 启动电机
 *
 * @param {string} [motorId='default'] - 电机ID
 * @returns {Promise<boolean>} 是否启动成功
 */
export async function startMotor(motorId = 'default') {
  const result = await post(`/api/v1/motor/${motorId}/start`, null, {
    onError: (msg) => console.error('[MotorAPI] Start motor error:', msg)
  });

  return result.success;
}

/**
 * 停止电机
 *
 * @param {string} [motorId='default'] - 电机ID
 * @returns {Promise<boolean>} 是否停止成功
 */
export async function stopMotor(motorId = 'default') {
  const result = await post(`/api/v1/motor/${motorId}/stop`, null, {
    onError: (msg) => console.error('[MotorAPI] Stop motor error:', msg)
  });

  return result.success;
}

/**
 * 紧急停止电机
 *
 * @param {string} [motorId='default'] - 电机ID
 * @returns {Promise<boolean>} 是否停止成功
 */
export async function emergencyStopMotor(motorId = 'default') {
  const result = await post(`/api/v1/motor/${motorId}/emergency-stop`, null, {
    onError: (msg) => console.error('[MotorAPI] Emergency stop error:', msg)
  });

  return result.success;
}

/**
 * 电机归零
 *
 * @param {string} [motorId='default'] - 电机ID
 * @returns {Promise<Object|null>} 归零结果
 */
export async function homeMotor(motorId = 'default') {
  const result = await post(`/api/v1/motor/${motorId}/home`, null, {
    onError: (msg) => console.error('[MotorAPI] Home motor error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取电机配置
 *
 * @param {string} [motorId='default'] - 电机ID
 * @returns {Promise<Object|null>} 电机配置
 */
export async function getMotorConfig(motorId = 'default') {
  const result = await get(`/api/v1/motor/${motorId}/config`, null, {
    onError: (msg) => console.error('[MotorAPI] Get config error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 更新电机配置
 *
 * @param {string} motorId - 电机ID
 * @param {Object} config - 配置参数
 * @returns {Promise<Object|null>} 更新后的配置
 */
export async function updateMotorConfig(motorId, config) {
  const result = await put(`/api/v1/motor/${motorId}/config`, config, {
    onError: (msg) => console.error('[MotorAPI] Update config error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 设置电机方向
 *
 * @param {Object} params - 方向参数
 * @param {string} [params.motor_id='default'] - 电机ID
 * @param {string} params.direction - 方向 ('cw' | 'ccw')
 * @returns {Promise<boolean>} 是否设置成功
 */
export async function setMotorDirection(params) {
  const result = await post('/api/v1/motor/direction', params, {
    onError: (msg) => console.error('[MotorAPI] Set direction error:', msg)
  });

  return result.success;
}

/**
 * 获取电机运动轨迹
 *
 * @param {string} [motorId='default'] - 电机ID
 * @param {Object} params - 查询参数
 * @param {number} [params.duration=60] - 查询时长（秒）
 * @returns {Promise<Object|null>} 运动轨迹数据
 */
export async function getMotorTrajectory(motorId = 'default', params = {}) {
  const result = await get(`/api/v1/motor/${motorId}/trajectory`, params, {
    onError: (msg) => console.error('[MotorAPI] Get trajectory error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 执行电机校准
 *
 * @param {string} [motorId='default'] - 电机ID
 * @returns {Promise<Object|null>} 校准结果
 */
export async function calibrateMotor(motorId = 'default') {
  const result = await post(`/api/v1/motor/${motorId}/calibrate`, null, {
    onError: (msg) => console.error('[MotorAPI] Calibrate error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取电机错误信息
 *
 * @param {string} [motorId='default'] - 电机ID
 * @returns {Promise<Object|null>} 错误信息
 */
export async function getMotorErrors(motorId = 'default') {
  const result = await get(`/api/v1/motor/${motorId}/errors`, null, {
    onError: (msg) => console.error('[MotorAPI] Get errors error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 清除电机错误
 *
 * @param {string} [motorId='default'] - 电机ID
 * @returns {Promise<boolean>} 是否清除成功
 */
export async function clearMotorErrors(motorId = 'default') {
  const result = await post(`/api/v1/motor/${motorId}/clear-errors`, null, {
    onError: (msg) => console.error('[MotorAPI] Clear errors error:', msg)
  });

  return result.success;
}
