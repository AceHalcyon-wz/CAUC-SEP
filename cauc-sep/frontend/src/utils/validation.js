/**
 * @file validation.js
 * @path src/utils/
 * @description 统一的参数验证工具模块，提供各类物理参数的验证函数
 * @author Agent
 * @date 2024-03-06
 */

/**
 * 验证结果对象
 * @typedef {Object} ValidationResult
 * @property {boolean} valid - 是否有效
 * @property {string} message - 错误消息
 */

/**
 * 验证位置参数
 * 
 * @param {number} position - 位置值
 * @param {number} min - 最小值，默认为负无穷
 * @param {number} max - 最大值，默认为正无穷
 * @returns {ValidationResult} 验证结果对象
 * 
 * @example
 * const result = validatePosition(50, 0, 100)
 * if (!result.valid) {
 *   console.error(result.message)
 * }
 */
export function validatePosition(position, min = -Infinity, max = Infinity) {
  if (typeof position !== 'number' || isNaN(position)) {
    return { valid: false, message: '位置必须是有效数字' }
  }
  if (position < min || position > max) {
    return { valid: false, message: `位置必须在 ${min} 到 ${max} 之间` }
  }
  return { valid: true, message: '' }
}

/**
 * 验证速度参数
 * 
 * @param {number} velocity - 速度值
 * @param {number} min - 最小值，默认为 0
 * @param {number} max - 最大值，默认为 100000
 * @returns {ValidationResult} 验证结果对象
 * 
 * @example
 * const result = validateVelocity(5000)
 * if (!result.valid) {
 *   console.error(result.message)
 * }
 */
export function validateVelocity(velocity, min = 0, max = 100000) {
  if (typeof velocity !== 'number' || isNaN(velocity)) {
    return { valid: false, message: '速度必须是有效数字' }
  }
  if (velocity < min || velocity > max) {
    return { valid: false, message: `速度必须在 ${min} 到 ${max} 之间` }
  }
  return { valid: true, message: '' }
}

/**
 * 验证电流参数
 * 
 * @param {number} current - 电流值
 * @param {number} min - 最小值，默认为 0
 * @param {number} max - 最大值，默认为 10
 * @returns {ValidationResult} 验证结果对象
 * 
 * @example
 * const result = validateCurrent(5.5, 0, 10)
 * if (!result.valid) {
 *   console.error(result.message)
 * }
 */
export function validateCurrent(current, min = 0, max = 10) {
  if (typeof current !== 'number' || isNaN(current)) {
    return { valid: false, message: '电流必须是有效数字' }
  }
  if (current < min || current > max) {
    return { valid: false, message: `电流必须在 ${min} 到 ${max} A 之间` }
  }
  return { valid: true, message: '' }
}

/**
 * 验证温度参数
 * 
 * @param {number} temperature - 温度值（开尔文）
 * @param {number} min - 最小值，默认为 77（液氮温度）
 * @param {number} max - 最大值，默认为 400
 * @returns {ValidationResult} 验证结果对象
 * 
 * @example
 * const result = validateTemperature(300, 77, 400)
 * if (!result.valid) {
 *   console.error(result.message)
 * }
 */
export function validateTemperature(temperature, min = 77, max = 400) {
  if (typeof temperature !== 'number' || isNaN(temperature)) {
    return { valid: false, message: '温度必须是有效数字' }
  }
  if (temperature < min || temperature > max) {
    return { valid: false, message: `温度必须在 ${min} 到 ${max} K 之间` }
  }
  return { valid: true, message: '' }
}

/**
 * 通用数值范围验证
 * 
 * @param {number} value - 要验证的值
 * @param {string} name - 参数名称
 * @param {number} min - 最小值，默认为负无穷
 * @param {number} max - 最大值，默认为正无穷
 * @returns {ValidationResult} 验证结果对象
 * 
 * @example
 * const result = validateRange(25, '压力', 0, 100)
 * if (!result.valid) {
 *   console.error(result.message)
 * }
 */
export function validateRange(value, name, min = -Infinity, max = Infinity) {
  if (typeof value !== 'number' || isNaN(value)) {
    return { valid: false, message: `${name}必须是有效数字` }
  }
  if (value < min || value > max) {
    return { valid: false, message: `${name}必须在 ${min} 到 ${max} 之间` }
  }
  return { valid: true, message: '' }
}
