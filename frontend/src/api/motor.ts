/**
 * @file motor.ts
 * @path src/api/
 * @description 电机控制 API 接口封装，提供类型化的电机操作方法
 * @author Agent
 * @date 2024-03-16
 * @dependencies ./client, @/types/api, @/types/device
 */

import { get, post, put } from './client'
import type { RequestResult } from '@/types/api'
import type { MotorStatus, MoveRequest, JogRequest, MotorConfig } from '@/types/device'

// ==================== 电机状态 API ====================

/**
 * 获取电机状态
 *
 * @param motorId - 电机 ID
 * @returns 电机状态信息
 */
export async function getMotorStatus(motorId = 'default'): Promise<MotorStatus | null> {
  const result = await get<MotorStatus>(`/motor/${motorId}/status`, null, {
    onError: (msg) => console.error('[MotorAPI] Get status error:', msg),
  })

  return result.success ? result.data ?? null : null
}

/**
 * 获取电机配置
 *
 * @param motorId - 电机 ID
 * @returns 电机配置信息
 */
export async function getMotorConfig(motorId = 'default'): Promise<MotorConfig | null> {
  const result = await get<MotorConfig>(`/motor/${motorId}/config`, null, {
    onError: (msg) => console.error('[MotorAPI] Get config error:', msg),
  })

  return result.success ? result.data ?? null : null
}

/**
 * 更新电机配置
 *
 * @param motorId - 电机 ID
 * @param config - 配置参数
 * @returns 更新后的配置
 */
export async function updateMotorConfig(motorId: string, config: Partial<MotorConfig>): Promise<MotorConfig | null> {
  const result = await put<MotorConfig>(`/motor/${motorId}/config`, config as Record<string, unknown>, {
    onError: (msg) => console.error('[MotorAPI] Update config error:', msg),
  })

  return result.success ? result.data ?? null : null
}

// ==================== 电机控制 API ====================

/**
 * 设置电机位置参数
 */
export interface SetPositionParams {
  /** 电机 ID */
  motor_id?: string
  /** 目标位置（角度或步数） */
  position: number
  /** 移动速度 */
  speed?: number
  /** 是否绝对定位 */
  absolute?: boolean
}

/**
 * 设置电机位置
 *
 * @param params - 位置参数
 * @returns 设置结果
 */
export async function setMotorPosition(params: SetPositionParams): Promise<unknown | null> {
  const result = await post<unknown>('/motor/position', params as unknown as Record<string, unknown>, {
    onError: (msg) => console.error('[MotorAPI] Set position error:', msg),
  })

  return result.success ? result.data ?? null : null
}

/**
 * 设置电机速度参数
 */
export interface SetSpeedParams {
  /** 电机 ID */
  motor_id?: string
  /** 目标速度 */
  speed: number
}

/**
 * 设置电机速度
 *
 * @param params - 速度参数
 * @returns 是否设置成功
 */
export async function setMotorSpeed(params: SetSpeedParams): Promise<boolean> {
  const result = await post('/motor/speed', params as unknown as Record<string, unknown>, {
    onError: (msg) => console.error('[MotorAPI] Set speed error:', msg),
  })

  return result.success
}

/**
 * 启动电机
 *
 * @param motorId - 电机 ID
 * @returns 是否启动成功
 */
export async function startMotor(motorId = 'default'): Promise<boolean> {
  const result = await post(`/motor/${motorId}/start`, null, {
    onError: (msg) => console.error('[MotorAPI] Start motor error:', msg),
  })

  return result.success
}

/**
 * 停止电机
 *
 * @param motorId - 电机 ID
 * @returns 是否停止成功
 */
export async function stopMotor(motorId = 'default'): Promise<boolean> {
  const result = await post(`/motor/${motorId}/stop`, null, {
    onError: (msg) => console.error('[MotorAPI] Stop motor error:', msg),
  })

  return result.success
}

/**
 * 紧急停止电机
 *
 * @param motorId - 电机 ID
 * @returns 是否停止成功
 */
export async function emergencyStopMotor(motorId = 'default'): Promise<boolean> {
  const result = await post(`/motor/${motorId}/emergency-stop`, null, {
    onError: (msg) => console.error('[MotorAPI] Emergency stop error:', msg),
  })

  return result.success
}

/**
 * 电机归零
 *
 * @param motorId - 电机 ID
 * @returns 归零结果
 */
export async function homeMotor(motorId = 'default'): Promise<unknown | null> {
  const result = await post<unknown>(`/motor/${motorId}/home`, null, {
    onError: (msg) => console.error('[MotorAPI] Home motor error:', msg),
  })

  return result.success ? result.data ?? null : null
}

/**
 * 设置电机方向参数
 */
export interface SetDirectionParams {
  /** 电机 ID */
  motor_id?: string
  /** 方向 ('cw' | 'ccw') */
  direction: 'cw' | 'ccw'
}

/**
 * 设置电机方向
 *
 * @param params - 方向参数
 * @returns 是否设置成功
 */
export async function setMotorDirection(params: SetDirectionParams): Promise<boolean> {
  const result = await post('/motor/direction', params as unknown as Record<string, unknown>, {
    onError: (msg) => console.error('[MotorAPI] Set direction error:', msg),
  })

  return result.success
}

/**
 * 执行电机校准
 *
 * @param motorId - 电机 ID
 * @returns 校准结果
 */
export async function calibrateMotor(motorId = 'default'): Promise<unknown | null> {
  const result = await post<unknown>(`/motor/${motorId}/calibrate`, null, {
    onError: (msg) => console.error('[MotorAPI] Calibrate error:', msg),
  })

  return result.success ? result.data ?? null : null
}

// ==================== 电机错误 API ====================

/**
 * 电机错误信息
 */
export interface MotorError {
  /** 错误码 */
  code: number
  /** 错误消息 */
  message: string
  /** 错误时间 */
  timestamp?: string
}

/**
 * 获取电机错误信息
 *
 * @param motorId - 电机 ID
 * @returns 错误信息
 */
export async function getMotorErrors(motorId = 'default'): Promise<MotorError[] | null> {
  const result = await get<MotorError[]>(`/motor/${motorId}/errors`, null, {
    onError: (msg) => console.error('[MotorAPI] Get errors error:', msg),
  })

  return result.success ? result.data ?? null : null
}

/**
 * 清除电机错误
 *
 * @param motorId - 电机 ID
 * @returns 是否清除成功
 */
export async function clearMotorErrors(motorId = 'default'): Promise<boolean> {
  const result = await post(`/motor/${motorId}/clear-errors`, null, {
    onError: (msg) => console.error('[MotorAPI] Clear errors error:', msg),
  })

  return result.success
}

// ==================== 电机轨迹 API ====================

/**
 * 轨迹查询参数
 */
export interface TrajectoryParams {
  /** 查询时长（秒） */
  duration?: number
}

/**
 * 轨迹数据点
 */
export interface TrajectoryPoint {
  /** 时间戳 */
  timestamp: string
  /** 位置 (mm) */
  position: number
  /** 速度 (steps/s) */
  speed: number
}

/**
 * 获取电机运动轨迹
 *
 * @param motorId - 电机 ID
 * @param params - 查询参数
 * @returns 运动轨迹数据
 */
export async function getMotorTrajectory(
  motorId = 'default',
  params: TrajectoryParams = {}
): Promise<TrajectoryPoint[] | null> {
  const result = await get<TrajectoryPoint[]>(`/motor/${motorId}/trajectory`, params as Record<string, unknown>, {
    onError: (msg) => console.error('[MotorAPI] Get trajectory error:', msg),
  })

  return result.success ? result.data ?? null : null
}

// ==================== RS232 专用通信模式 API ====================

/**
 * 串口模式参数
 */
export interface SerialModeParams {
  /** 串口模式 ('rs485' | 'rs232') */
  mode: 'rs485' | 'rs232'
  /** 串口号 */
  port: string
}

/**
 * 串口模式信息
 */
export interface SerialModeInfo {
  /** 当前模式 */
  mode: 'rs485' | 'rs232'
  /** 串口号 */
  port: string
  /** 是否已连接 */
  connected: boolean
}

/**
 * 设置串口通信模式
 *
 * @param params - 模式参数
 * @returns 设置结果
 */
export async function setSerialMode(params: SerialModeParams): Promise<SerialModeInfo | null> {
  const result = await post<SerialModeInfo>('/motor/serial_mode', params as unknown as Record<string, unknown>, {
    onError: (msg) => console.error('[MotorAPI] Set serial mode error:', msg),
  })

  return result.success ? result.data ?? null : null
}

/**
 * 获取当前串口通信模式
 *
 * @returns 当前串口模式信息
 */
export async function getSerialMode(): Promise<SerialModeInfo | null> {
  const result = await get<SerialModeInfo>('/motor/serial_mode', null, {
    onError: (msg) => console.error('[MotorAPI] Get serial mode error:', msg),
  })

  return result.success ? result.data ?? null : null
}

// ==================== 通信参数配置 API ====================

/**
 * 通信参数配置
 */
export interface CommunicationConfig {
  /** 波特率 */
  baudrate?: number
  /** 从站地址 */
  slave_id?: number
  /** 数据类型 */
  data_type?: number
}

/**
 * 支持的波特率列表响应
 */
export interface BaudratesResponse {
  /** 波特率列表 */
  baudrates: number[]
}

/**
 * 支持的数据类型列表响应
 */
export interface DataTypesResponse {
  /** 数据类型列表 */
  data_types: Array<{
    value: number
    label: string
  }>
}

/**
 * 读取通信参数配置
 *
 * @returns 当前通信参数配置
 */
export async function getCommunicationConfig(): Promise<CommunicationConfig | null> {
  const result = await get<CommunicationConfig>('/motor/communication/config', null, {
    onError: (msg) => console.error('[MotorAPI] Get communication config error:', msg),
  })

  return result.success ? result.data ?? null : null
}

/**
 * 修改通信参数配置
 *
 * @param params - 通信参数
 * @returns 配置结果
 */
export async function setCommunicationConfig(params: CommunicationConfig): Promise<CommunicationConfig | null> {
  const result = await post<CommunicationConfig>('/motor/communication/config', params as Record<string, unknown>, {
    onError: (msg) => console.error('[MotorAPI] Set communication config error:', msg),
  })

  return result.success ? result.data ?? null : null
}

/**
 * 获取支持的波特率列表
 *
 * @returns 支持的波特率列表
 */
export async function getSupportedBaudrates(): Promise<number[] | null> {
  const result = await get<BaudratesResponse>('/motor/communication/baudrates', null, {
    onError: (msg) => console.error('[MotorAPI] Get baudrates error:', msg),
  })

  return result.success ? result.data?.baudrates ?? null : null
}

/**
 * 获取支持的数据类型列表
 *
 * @returns 支持的数据类型列表
 */
export async function getSupportedDataTypes(): Promise<DataTypesResponse['data_types'] | null> {
  const result = await get<DataTypesResponse>('/motor/communication/data_types', null, {
    onError: (msg) => console.error('[MotorAPI] Get data types error:', msg),
  })

  return result.success ? result.data?.data_types ?? null : null
}

// ==================== 驱动器软件限位 API ====================

/**
 * 软件限位参数
 */
export interface SoftLimitParams {
  /** 正向限位(mm) */
  positive_limit_mm?: number
  /** 负向限位(mm) */
  negative_limit_mm?: number
  /** 正向限位(步数) */
  positive_limit_steps?: number
  /** 负向限位(步数) */
  negative_limit_steps?: number
}

/**
 * 软件限位配置
 */
export interface SoftLimitConfig extends SoftLimitParams {
  /** 是否已同步到驱动器 */
  synced: boolean
}

/**
 * 读取驱动器软件限位
 *
 * @returns 当前软件限位配置
 */
export async function getDriverSoftLimit(): Promise<SoftLimitConfig | null> {
  const result = await get<SoftLimitConfig>('/motor/driver_soft_limit', null, {
    onError: (msg) => console.error('[MotorAPI] Get driver soft limit error:', msg),
  })

  return result.success ? result.data ?? null : null
}

/**
 * 设置驱动器软件限位
 *
 * @param params - 软件限位参数
 * @returns 设置结果
 */
export async function setDriverSoftLimit(params: SoftLimitParams): Promise<SoftLimitConfig | null> {
  const result = await post<SoftLimitConfig>('/motor/driver_soft_limit', params as Record<string, unknown>, {
    onError: (msg) => console.error('[MotorAPI] Set driver soft limit error:', msg),
  })

  return result.success ? result.data ?? null : null
}

/**
 * 同步软件限位到驱动器
 *
 * @returns 同步结果
 */
export async function syncSoftLimitsToDriver(): Promise<SoftLimitConfig | null> {
  const result = await post<SoftLimitConfig>('/motor/driver_soft_limit/sync', null, {
    onError: (msg) => console.error('[MotorAPI] Sync soft limits error:', msg),
  })

  return result.success ? result.data ?? null : null
}

// ==================== 电机 API 对象（推荐使用方式） ====================

/**
 * 电机 API 对象
 *
 * 提供统一的电机操作接口
 */
export const motorApi = {
  // 状态查询
  getStatus: getMotorStatus,
  getConfig: getMotorConfig,
  updateConfig: updateMotorConfig,

  // 位置控制
  setPosition: setMotorPosition,
  moveAbs: async (params: MoveRequest): Promise<RequestResult> => {
    return post('/motor/move/abs', { ...params })
  },
  moveRel: async (params: MoveRequest): Promise<RequestResult> => {
    return post('/motor/move/rel', { ...params })
  },
  jog: async (params: JogRequest): Promise<RequestResult> => {
    return post('/motor/jog', { ...params })
  },

  // 速度控制
  setSpeed: setMotorSpeed,

  // 运动控制
  start: startMotor,
  stop: stopMotor,
  emergencyStop: emergencyStopMotor,
  home: homeMotor,
  calibrate: calibrateMotor,

  // 方向控制
  setDirection: setMotorDirection,

  // 错误管理
  getErrors: getMotorErrors,
  clearErrors: clearMotorErrors,

  // 轨迹查询
  getTrajectory: getMotorTrajectory,

  // 串口通信
  setSerialMode,
  getSerialMode,

  // 通信配置
  getCommunicationConfig,
  setCommunicationConfig,
  getSupportedBaudrates,
  getSupportedDataTypes,

  // 软件限位
  getDriverSoftLimit,
  setDriverSoftLimit,
  syncSoftLimitsToDriver,
}

export default motorApi
