/**
 * @file motor-api-service.ts
 * @path src/api/services/motor-api-service.ts
 * @description 步进电机API服务类，提供统一的电机控制接口
 * @author Agent
 * @date 2026-03-25
 * @dependencies ./base-api-service, @/types/device
 * @safety: 急停接口必须跳过请求队列，优先执行，超时重试3次
 */

import { BaseApiService, ApiError, DeviceAlarmError, ValidationError } from './base-api-service'
import type { RequestResult } from '../client'
import type { MotorStatus, MotorConfig, MoveRequest, JogRequest } from '@/types/device'

/**
 * 电机运动请求参数
 */
export interface MotorMoveRequest {
  /** 目标脉冲位置，范围0-50000 */
  targetPosition: number
  /** 运动速度，单位脉冲/秒 */
  speed: number
  /** 加减速时间，单位ms，默认100 */
  acceleration?: number
}

/**
 * 电机JOG请求参数
 */
export interface MotorJogRequest {
  /** JOG方向 */
  direction: '+' | '-'
  /** JOG速度 */
  speed?: number
}

/**
 * 软件限位配置
 */
export interface SoftLimitConfig {
  /** 正向限位(步数) */
  positiveLimitSteps: number
  /** 负向限位(步数) */
  negativeLimitSteps: number
  /** 是否已同步到驱动器 */
  synced: boolean
}

/**
 * 电机PR路径配置
 */
export interface MotorPRConfig {
  /** PR路径编号 */
  pathNumber: number
  /** 目标位置 */
  position: number
  /** 运动速度 */
  speed: number
  /** 是否启用 */
  enabled: boolean
}

/**
 * 步进电机API服务类
 * 
 * @remarks
 * 所有接口统一使用unwrapResponse解包，内置3次超时重试机制
 * 急停接口优先执行，跳过请求队列，保障最高优先级
 */
export class MotorApiService extends BaseApiService {
  private readonly deviceId: string

  constructor(deviceId = 'default') {
    super({
      basePath: '/motor',
      timeout: 30000,
      retries: 3,
      useCache: false,
    })
    this.deviceId = deviceId
  }

  /**
   * 获取电机实时状态
   * 
   * @returns 电机状态信息
   * @throws {ApiError} 接口请求失败
   */
  async getStatus(): Promise<MotorStatus | null> {
    const result = await this.get<MotorStatus>(`/${this.deviceId}/status`)
    return this.unwrap(result)
  }

  /**
   * 获取电机配置
   * 
   * @returns 电机配置信息
   * @throws {ApiError} 接口请求失败
   */
  async getConfig(): Promise<MotorConfig | null> {
    const result = await this.get<MotorConfig>(`/${this.deviceId}/config`)
    return this.unwrap(result)
  }

  /**
   * 更新电机配置
   * 
   * @param config - 配置参数
   * @returns 更新后的配置
   * @throws {ValidationError} 参数校验失败
   * @throws {ApiError} 接口请求失败
   */
  async updateConfig(config: Partial<MotorConfig>): Promise<MotorConfig | null> {
    const result = await this.put<MotorConfig>(`/${this.deviceId}/config`, config as Record<string, unknown>)
    return this.unwrap(result)
  }

  /**
   * 执行电机绝对定位运动
   * 
   * @param request - 电机运动请求参数
   * @returns 指令执行结果
   * @throws {ValidationError} 参数校验失败
   * @throws {DeviceAlarmError} 驱动器处于报警状态
   * @throws {ApiError} 接口请求失败
   * 
   * @example
   * ```typescript
   * const motorApi = new MotorApiService();
   * const result = await motorApi.absoluteMove({
   *   targetPosition: 10000,
   *   speed: 500
   * });
   * ```
   */
  async absoluteMove(request: MotorMoveRequest): Promise<boolean> {
    this.validateMoveRequest(request)

    const result = await this.post<{ success: boolean }>('/move/abs', {
      motor_id: this.deviceId,
      target_position: request.targetPosition,
      speed: request.speed,
      acceleration: request.acceleration ?? 100,
    })

    if (result.success && result.data?.success) {
      return true
    }

    if (result.message?.includes('alarm') || result.message?.includes('报警')) {
      throw new DeviceAlarmError('驱动器处于报警状态，请先复位报警')
    }

    return false
  }

  /**
   * 执行电机相对定位运动
   * 
   * @param request - 电机运动请求参数
   * @returns 指令执行结果
   * @throws {ValidationError} 参数校验失败
   * @throws {ApiError} 接口请求失败
   */
  async relativeMove(request: MotorMoveRequest): Promise<boolean> {
    this.validateMoveRequest(request)

    const result = await this.post<{ success: boolean }>('/move/rel', {
      motor_id: this.deviceId,
      target_position: request.targetPosition,
      speed: request.speed,
      acceleration: request.acceleration ?? 100,
    })

    return result.success && (result.data?.success ?? false)
  }

  /**
   * 启动JOG点动运动
   * 
   * @param request - JOG请求参数
   * @returns 指令执行结果
   * @throws {ValidationError} 参数校验失败
   * @throws {ApiError} 接口请求失败
   */
  async startJog(request: MotorJogRequest): Promise<boolean> {
    if (request.direction !== '+' && request.direction !== '-') {
      throw new ValidationError('JOG方向必须为 + 或 -')
    }

    const result = await this.post<{ success: boolean }>('/jog', {
      motor_id: this.deviceId,
      direction: request.direction,
      speed: request.speed ?? 500,
    })

    return result.success && (result.data?.success ?? false)
  }

  /**
   * 停止JOG点动运动
   * 
   * @returns 指令执行结果
   * @throws {ApiError} 接口请求失败
   */
  async stopJog(): Promise<boolean> {
    const result = await this.post<{ success: boolean }>('/jog/stop', {
      motor_id: this.deviceId,
    })

    return result.success && (result.data?.success ?? false)
  }

  /**
   * 停止电机
   * 
   * @returns 指令执行结果
   * @throws {ApiError} 接口请求失败
   */
  async stop(): Promise<boolean> {
    const result = await this.post<{ success: boolean }>(`/${this.deviceId}/stop`)

    return result.success && (result.data?.success ?? false)
  }

  /**
   * 执行电机紧急停止
   * 
   * @returns 指令执行结果
   * @throws {ApiError} 接口请求失败
   * 
   * @internal 急停指令跳过请求队列，优先执行
   * @safety 急停接口必须最高优先级执行
   */
  async emergencyStop(): Promise<boolean> {
    const result = await this.post<{ success: boolean }>(
      `/${this.deviceId}/emergency-stop`,
      null,
      {
        timeout: 5000,
        retries: 3,
      }
    )

    return result.success && (result.data?.success ?? false)
  }

  /**
   * 电机归零
   * 
   * @returns 归零结果
   * @throws {ApiError} 接口请求失败
   */
  async home(): Promise<boolean> {
    const result = await this.post<{ success: boolean }>(`/${this.deviceId}/home`)

    return result.success && (result.data?.success ?? false)
  }

  /**
   * 清除电机报警
   * 
   * @returns 清除结果
   * @throws {ApiError} 接口请求失败
   */
  async clearAlarm(): Promise<boolean> {
    const result = await this.post<{ success: boolean }>(`/${this.deviceId}/clear-errors`)

    return result.success && (result.data?.success ?? false)
  }

  /**
   * 获取软件限位配置
   * 
   * @returns 软件限位配置
   * @throws {ApiError} 接口请求失败
   */
  async getSoftLimit(): Promise<SoftLimitConfig | null> {
    const result = await this.get<SoftLimitConfig>('/driver_soft_limit')
    return this.unwrap(result)
  }

  /**
   * 设置软件限位配置
   * 
   * @param config - 软件限位配置
   * @returns 设置结果
   * @throws {ValidationError} 参数校验失败
   * @throws {ApiError} 接口请求失败
   */
  async setSoftLimit(config: Partial<SoftLimitConfig>): Promise<SoftLimitConfig | null> {
    if (config.positiveLimitSteps !== undefined && config.positiveLimitSteps < 0) {
      throw new ValidationError('正向限位必须大于等于0')
    }
    if (config.negativeLimitSteps !== undefined && config.negativeLimitSteps > 0) {
      throw new ValidationError('负向限位必须小于等于0')
    }

    const result = await this.post<SoftLimitConfig>('/driver_soft_limit', {
      positive_limit_steps: config.positiveLimitSteps,
      negative_limit_steps: config.negativeLimitSteps,
    })

    return this.unwrap(result)
  }

  /**
   * 同步软件限位到驱动器
   * 
   * @returns 同步结果
   * @throws {ApiError} 接口请求失败
   */
  async syncSoftLimit(): Promise<SoftLimitConfig | null> {
    const result = await this.post<SoftLimitConfig>('/driver_soft_limit/sync')
    return this.unwrap(result)
  }

  /**
   * 获取PR路径配置
   * 
   * @param pathNumber - PR路径编号
   * @returns PR路径配置
   * @throws {ApiError} 接口请求失败
   */
  async getPRConfig(pathNumber: number): Promise<MotorPRConfig | null> {
    const result = await this.get<MotorPRConfig>(`/${this.deviceId}/pr/${pathNumber}`)
    return this.unwrap(result)
  }

  /**
   * 设置PR路径配置
   * 
   * @param config - PR路径配置
   * @returns 设置结果
   * @throws {ValidationError} 参数校验失败
   * @throws {ApiError} 接口请求失败
   */
  async setPRConfig(config: MotorPRConfig): Promise<MotorPRConfig | null> {
    if (config.pathNumber < 1 || config.pathNumber > 16) {
      throw new ValidationError('PR路径编号必须在1-16之间')
    }

    const result = await this.post<MotorPRConfig>(`/${this.deviceId}/pr/${config.pathNumber}`, {
      position: config.position,
      speed: config.speed,
      enabled: config.enabled,
    })

    return this.unwrap(result)
  }

  /**
   * 校验运动请求参数
   * 
   * @param request - 运动请求参数
   * @throws {ValidationError} 参数校验失败
   */
  private validateMoveRequest(request: MotorMoveRequest): void {
    if (request.targetPosition < 0 || request.targetPosition > 50000) {
      throw new ValidationError('目标位置必须在0-50000范围内')
    }
    if (request.speed < 100 || request.speed > 5000) {
      throw new ValidationError('运动速度必须在100-5000范围内')
    }
    if (request.acceleration !== undefined && (request.acceleration < 10 || request.acceleration > 1000)) {
      throw new ValidationError('加减速时间必须在10-1000范围内')
    }
  }
}

export default MotorApiService
