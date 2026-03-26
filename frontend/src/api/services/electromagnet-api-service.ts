/**
 * @file electromagnet-api-service.ts
 * @path src/api/services/electromagnet-api-service.ts
 * @description 电磁铁API服务类，提供统一的电磁铁控制接口
 * @author Agent
 * @date 2026-03-26
 * @dependencies ./base-api-service, @/types/device
 * @safety: 磁场强度设置必须校验范围，避免超出设备限制
 */

import { BaseApiService, ValidationError } from './base-api-service'
import type { ElectromagnetStatus, ElectromagnetParams } from '@/types/device'

/**
 * 磁场强度设置参数
 */
export interface SetFieldParams {
  /** 磁场强度（mT或A） */
  fieldStrength: number
  /** 变化速率 */
  rampRate?: number
}

/**
 * 电流设置参数
 */
export interface SetCurrentParams {
  /** 电流值（A） */
  current: number
}

/**
 * 极性设置参数
 */
export interface SetPolarityParams {
  /** 极性 ('positive' | 'negative') */
  polarity: 'positive' | 'negative'
}

/**
 * 电磁铁配置参数
 */
export interface ElectromagnetConfig {
  /** 最大电流 */
  maxCurrent?: number
  /** 最大磁场强度 */
  maxField?: number
  /** 最大变化速率 */
  rampRateLimit?: number
}

/**
 * 历史数据查询参数
 */
export interface HistoryQueryParams {
  /** 查询时长（秒） */
  duration?: number
}

/**
 * 磁场历史数据点
 */
export interface FieldHistoryPoint {
  /** 时间戳 */
  timestamp: string
  /** 磁场强度 */
  fieldStrength: number
  /** 电流值 */
  current: number
}

/**
 * 温度信息
 */
export interface TemperatureInfo {
  /** 当前温度（°C） */
  temperature: number
  /** 是否过热 */
  isOverheated: boolean
}

/**
 * 安全状态信息
 */
export interface SafetyStatus {
  /** 是否安全 */
  isSafe: boolean
  /** 报警信息 */
  alarms: string[]
  /** 是否过温 */
  overTemperature: boolean
  /** 是否过流 */
  overCurrent: boolean
}

/**
 * 电磁铁API服务类
 * 
 * @remarks
 * 所有接口统一使用unwrapResponse解包，内置3次超时重试机制
 * 磁场强度设置前必须校验范围，避免超出设备限制
 */
export class ElectromagnetApiService extends BaseApiService {
  private readonly deviceId: string

  constructor(deviceId = 'default') {
    super({
      basePath: '/electromagnet',
      timeout: 30000,
      retries: 3,
      useCache: false,
    })
    this.deviceId = deviceId
  }

  /**
   * 获取电磁铁状态
   * 
   * @returns 电磁铁状态信息
   * @throws {ApiError} 接口请求失败
   */
  async getStatus(): Promise<ElectromagnetStatus | null> {
    const result = await this.get<ElectromagnetStatus>(`/${this.deviceId}/status`)
    return this.unwrap(result)
  }

  /**
   * 设置磁场强度
   * 
   * @param params - 磁场参数
   * @returns 设置结果
   * @throws {ValidationError} 参数校验失败
   * @throws {ApiError} 接口请求失败
   */
  async setField(params: SetFieldParams): Promise<{ fieldStrength: number } | null> {
    if (params.fieldStrength < 0) {
      throw new ValidationError('磁场强度必须大于等于0')
    }
    if (params.rampRate !== undefined && params.rampRate <= 0) {
      throw new ValidationError('变化速率必须大于0')
    }

    const result = await this.post<{ fieldStrength: number }>('/field', {
      magnet_id: this.deviceId,
      field_strength: params.fieldStrength,
      ramp_rate: params.rampRate,
    })

    return this.unwrap(result)
  }

  /**
   * 获取当前磁场强度
   * 
   * @returns 当前磁场强度
   * @throws {ApiError} 接口请求失败
   */
  async getCurrentField(): Promise<{ fieldStrength: number; current: number } | null> {
    const result = await this.get<{ fieldStrength: number; current: number }>(
      `/${this.deviceId}/field/current`
    )
    return this.unwrap(result)
  }

  /**
   * 启用电磁铁
   * 
   * @returns 是否启用成功
   * @throws {ApiError} 接口请求失败
   */
  async enable(): Promise<boolean> {
    const result = await this.post<{ success: boolean }>(`/${this.deviceId}/enable`)
    return result.success && (result.data?.success ?? false)
  }

  /**
   * 禁用电磁铁
   * 
   * @returns 是否禁用成功
   * @throws {ApiError} 接口请求失败
   */
  async disable(): Promise<boolean> {
    const result = await this.post<{ success: boolean }>(`/${this.deviceId}/disable`)
    return result.success && (result.data?.success ?? false)
  }

  /**
   * 设置电磁铁电流
   * 
   * @param params - 电流参数
   * @returns 是否设置成功
   * @throws {ValidationError} 参数校验失败
   * @throws {ApiError} 接口请求失败
   */
  async setCurrent(params: SetCurrentParams): Promise<boolean> {
    if (params.current < 0) {
      throw new ValidationError('电流值必须大于等于0')
    }

    const result = await this.post<{ success: boolean }>('/current', {
      magnet_id: this.deviceId,
      current: params.current,
    })

    return result.success && (result.data?.success ?? false)
  }

  /**
   * 获取电磁铁电流
   * 
   * @returns 当前电流值
   * @throws {ApiError} 接口请求失败
   */
  async getCurrent(): Promise<{ current: number } | null> {
    const result = await this.get<{ current: number }>(`/${this.deviceId}/current`)
    return this.unwrap(result)
  }

  /**
   * 获取电磁铁配置
   * 
   * @returns 电磁铁配置
   * @throws {ApiError} 接口请求失败
   */
  async getConfig(): Promise<ElectromagnetConfig | null> {
    const result = await this.get<ElectromagnetConfig>(`/${this.deviceId}/config`)
    return this.unwrap(result)
  }

  /**
   * 更新电磁铁配置
   * 
   * @param config - 配置参数
   * @returns 更新后的配置
   * @throws {ValidationError} 参数校验失败
   * @throws {ApiError} 接口请求失败
   */
  async updateConfig(config: ElectromagnetConfig): Promise<ElectromagnetConfig | null> {
    if (config.maxCurrent !== undefined && config.maxCurrent <= 0) {
      throw new ValidationError('最大电流必须大于0')
    }
    if (config.maxField !== undefined && config.maxField <= 0) {
      throw new ValidationError('最大磁场强度必须大于0')
    }

    const result = await this.put<ElectromagnetConfig>(
      `/${this.deviceId}/config`,
      config as Record<string, unknown>
    )
    return this.unwrap(result)
  }

  /**
   * 磁场归零
   * 
   * @returns 归零结果
   * @throws {ApiError} 接口请求失败
   */
  async zero(): Promise<{ success: boolean } | null> {
    const result = await this.post<{ success: boolean }>(`/${this.deviceId}/zero`)
    return this.unwrap(result)
  }

  /**
   * 获取磁场历史数据
   * 
   * @param params - 查询参数
   * @returns 磁场历史数据
   * @throws {ApiError} 接口请求失败
   */
  async getHistory(params: HistoryQueryParams = {}): Promise<FieldHistoryPoint[] | null> {
    const result = await this.get<FieldHistoryPoint[]>(`/${this.deviceId}/history`, {
      duration: params.duration ?? 300,
    })
    return this.unwrap(result)
  }

  /**
   * 设置磁场极性
   * 
   * @param params - 极性参数
   * @returns 是否设置成功
   * @throws {ValidationError} 参数校验失败
   * @throws {ApiError} 接口请求失败
   */
  async setPolarity(params: SetPolarityParams): Promise<boolean> {
    if (params.polarity !== 'positive' && params.polarity !== 'negative') {
      throw new ValidationError('极性必须为 positive 或 negative')
    }

    const result = await this.post<{ success: boolean }>('/polarity', {
      magnet_id: this.deviceId,
      polarity: params.polarity,
    })

    return result.success && (result.data?.success ?? false)
  }

  /**
   * 反转磁场极性
   * 
   * @returns 是否反转成功
   * @throws {ApiError} 接口请求失败
   */
  async reversePolarity(): Promise<boolean> {
    const result = await this.post<{ success: boolean }>(`/${this.deviceId}/reverse`)
    return result.success && (result.data?.success ?? false)
  }

  /**
   * 获取电磁铁温度
   * 
   * @returns 温度信息
   * @throws {ApiError} 接口请求失败
   */
  async getTemperature(): Promise<TemperatureInfo | null> {
    const result = await this.get<TemperatureInfo>(`/${this.deviceId}/temperature`)
    return this.unwrap(result)
  }

  /**
   * 执行电磁铁校准
   * 
   * @returns 校准结果
   * @throws {ApiError} 接口请求失败
   */
  async calibrate(): Promise<{ success: boolean; message: string } | null> {
    const result = await this.post<{ success: boolean; message: string }>(
      `/${this.deviceId}/calibrate`
    )
    return this.unwrap(result)
  }

  /**
   * 获取电磁铁安全状态
   * 
   * @returns 安全状态信息
   * @throws {ApiError} 接口请求失败
   */
  async getSafetyStatus(): Promise<SafetyStatus | null> {
    const result = await this.get<SafetyStatus>(`/${this.deviceId}/safety`)
    return this.unwrap(result)
  }
}

export default ElectromagnetApiService
