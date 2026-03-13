/**
 * @file constants.js
 * @path src/config/
 * @description 设备限制常量定义，统一管理所有物理参数范围
 * @author Agent
 * @date 2024-03-07
 */

// ============ 电磁铁常量 ============
export const ELECTROMAGNET = {
  /** 最大电流 (A) */
  MAX_CURRENT: 10.0,
  /** 最小电流 (A) */
  MIN_CURRENT: 0.0,
  /** 电流精度 (A) */
  CURRENT_PRECISION: 0.001,
  /** 最大磁场 (T) */
  MAX_FIELD: 2.0,
  /** 最小扫描速率 (A/s) */
  MIN_SCAN_RATE: 0.01,
  /** 最大扫描速率 (A/s) */
  MAX_SCAN_RATE: 1.0,
  /** 过流保护阈值 (A) */
  OVERCURRENT_THRESHOLD: 10.5,
  /** 过温保护阈值 (°C) */
  MAX_TEMPERATURE: 80.0
}

// ============ 温度控制器常量 ============
export const TEMPERATURE = {
  /** 最小温度 (K) - 液氮温度 */
  MIN_TEMPERATURE: 77.0,
  /** 最大温度 (K) */
  MAX_TEMPERATURE: 400.0,
  /** 温度容差 (K) */
  TEMPERATURE_TOLERANCE: 0.1,
  /** PID控制周期 (秒) */
  PID_CONTROL_INTERVAL: 1.0,
  /** 历史记录最大长度 */
  MAX_HISTORY_LENGTH: 10000,
  /** 高温保护限制 (K) */
  HIGH_TEMP_LIMIT: 450.0,
  /** 低温保护限制 (K) */
  LOW_TEMP_LIMIT: 70.0,
  /** 最大温度变化速率 (K/min) */
  MAX_RATE_LIMIT: 20.0
}

// ============ 微电流计常量 ============
export const AMMETER = {
  /** 通道数量 */
  NUM_CHANNELS: 4,
  /** 最小采样率 (Hz) */
  MIN_SAMPLE_RATE: 1.0,
  /** 最大采样率 (Hz) */
  MAX_SAMPLE_RATE: 1000.0,
  /** 最小电流 (pA) */
  MIN_CURRENT_PA: 1.0,
  /** 最大电流 (pA) - 1mA */
  MAX_CURRENT_PA: 1_000_000_000.0,
  /** 默认采样率 (Hz) */
  DEFAULT_SAMPLE_RATE: 100,
  /** 默认缓冲区大小 */
  DEFAULT_BUFFER_SIZE: 1000
}

// ============ 电机常量 ============
export const MOTOR = {
  /** 最小速度 (mm/s) */
  MIN_VELOCITY: 1,
  /** 最大速度 (mm/s) */
  MAX_VELOCITY: 50,
  /** 默认速度 (mm/s) */
  DEFAULT_VELOCITY: 10,
  /** 默认正向限位 (mm) */
  DEFAULT_POSITIVE_LIMIT: 50,
  /** 默认负向限位 (mm) */
  DEFAULT_NEGATIVE_LIMIT: -50,
  /** 最大限位范围 (mm) */
  MAX_LIMIT_RANGE: 100,
  /** 最小限位范围 (mm) */
  MIN_LIMIT_RANGE: -100
}

// ============ 压电陶瓷常量 ============
export const PIEZO = {
  /** 最大电压 (V) */
  MAX_VOLTAGE: 150,
  /** 最小电压 (V) */
  MIN_VOLTAGE: 0,
  /** 电压步进 (V) */
  VOLTAGE_STEP: 0.1,
  /** 校准点数 */
  CALIBRATION_POINTS: 11
}

// ============ 通用常量 ============
export const GENERAL = {
  /** WebSocket重连间隔 (ms) */
  WS_RECONNECT_INTERVAL: 3000,
  /** WebSocket最大重连次数 */
  WS_MAX_RECONNECT_ATTEMPTS: 5,
  /** API请求超时时间 (ms) */
  API_TIMEOUT: 10000,
  /** 数据刷新间隔 (ms) */
  DATA_REFRESH_INTERVAL: 1000,
  /** 历史数据最大点数 */
  MAX_HISTORY_POINTS: 1000
}

export default {
  ELECTROMAGNET,
  TEMPERATURE,
  AMMETER,
  MOTOR,
  PIEZO,
  GENERAL
}
