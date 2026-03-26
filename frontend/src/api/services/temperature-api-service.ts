/**
 * @file temperature-api-service.ts
 * @path src/api/services/temperature-api-service.ts
 * @description 温度控制器API服务类，提供统一的温度控制接口
 * @author Agent
 * @date 2026-03-26
 * @dependencies ./base-api-service, @/types/device
 * @safety: 温度设置必须校验范围，避免超出设备限制
 */

import { BaseApiService, ValidationError } from './base-api-service'
import type { TemperatureControllerStatus, PidParams } from '@/types/device'

/**
 * 目标温度设置参数
 */
export interface SetTargetTempParams {
  /** 目标温度（摄氏度） */
  targetTemp: number
  /** 升降温速率（度/分钟） */
  rampRate?: number
}

/**
 * 温度控制器配置
 */
export interface TemperatureConfig {
  /** PID比例系数 */
  kp?: number
  /** PID积分系数 */
  ki?: number
  /** PID微分系数 */
  kd?: number
  /** 最大功率 */
  maxPower?: number
}

/**
 * 报警阈值设置参数
 */
export interface SetAlarmParams {
  /** 高温报警阈值 */
  highLimit: number
  /** 低温报警阈值 */
  lowLimit: number
}

/**
 * 报警状态信息
 */
export interface AlarmStatus {
  /** 是否报警 */
  isAlarm: boolean
  /** 报警类型 */
  alarmType?: 'high' | 'low' | 'sensor_error'
  /** 报警时间 */
  alarmTime?: string
}

/**
 * 加热器状态信息
 */
export interface HeaterStatus {
  /** 是否启用 */
  enabled: boolean
  /** 当前功率百分比 */
  power: number
  /** 是否正在加热 */
  isHeating: boolean
}

/**
 * 历史数据查询参数
 */
export interface HistoryQueryParams {
  /** 查询时长（秒） */
  duration?: number
  /** 数据间隔 */
  interval?: string
}

/**
 * 温度历史数据点
 */
export interface TemperatureHistoryPoint {
  /** 时间戳 */
  timestamp: string
  /** 温度值（°C） */
  temperature: number
  /** 目标温度 */
  targetTemp: number
  /** 加热器功率 */
  heaterPower: number
}

/**
 * 校准参数
 */
export interface CalibrateParams {
  /** 参考温度 */
  referenceTemp: number
}

/**
 * 加热器功率设置参数
 */
export interface SetHeaterPowerParams {
  /** 功率百分比（0-100） */
  power: number
}

/**
 * 传感器信息
 */
export interface SensorInfo {
  /** 传感器ID */
  id: string
  /** 传感器名称 */
  name: string
  /** 是否已连接 */
  connected: boolean
}

/**
 * 温度控制器API服务类
 * 
 * @remarks
 * 所有接口统一使用unwrapResponse解包，内置3次超时重试机制
 * 温度设置前必须校验范围，避免超出设备限制
 */
export class TemperatureApiService extends BaseApiService {
  private readonly sensorId: string

  constructor(sensorId = 'default') {
    super({
      basePath: '/temperature',
      timeout: 30000,
      retries: 3,
      useCache: false,
    })
    this.sensorId = sensorId
  }

  /**
   * 获取温度状态
   * 
   * @returns 温度状态信息
   * @throws {ApiError} 接口请求失败
   */
  async getStatus(): Promise<TemperatureControllerStatus | null> {
    const result = await this.get<TemperatureControllerStatus>(`/${this.sensorId}/status`)
    return this.unwrap(result)
  }

  /**
   * 获取当前温度值
   * 
   * @returns 当前温度值
   * @throws {ApiError} 接口请求失败
   */
  async getCurrentTemperature(): Promise<{ temperature: number } | null> {
    const result = await this.get<{ temperature: number }>(`/${this.sensorId}/current`)
    return this.unwrap(result)
  }

  /**
   * 设置目标温度
   * 
   * @param params - 温度参数
   * @returns 设置结果
   * @throws {ValidationError} 参数校验失败
   * @throws {ApiError} 接口请求失败
   */
  async setTargetTemperature(params: SetTargetTempParams): Promise<{ targetTemp: number } | null> {
    if (params.targetTemp < -273.15) {
      throw new ValidationError('温度不能低于绝对零度')
    }
    if (params.rampRate !== undefined && params.rampRate <= 0) {
      throw new ValidationError('升降温速率必须大于0')
    }

    const result = await this.post<{ targetTemp: number }>('/target', {
      sensor_id: this.sensorId,
      target_temp: params.targetTemp,
      ramp_rate: params.rampRate,
    })

    return this.unwrap(result)
  }

  /**
   * 启动温度控制
   * 
   * @returns 是否启动成功
   * @throws {ApiError} 接口请求失败
   */
  async start(): Promise<boolean> {
    const result = await this.post<{ success: boolean }>(`/${this.sensorId}/start`)
    return result.success && (result.data?.success ?? false)
  }

  /**
   * 停止温度控制
   * 
   * @returns 是否停止成功
   * @throws {ApiError} 接口请求失败
   */
  async stop(): Promise<boolean> {
    const result = await this.post<{ success: boolean }>(`/${this.sensorId}/stop`)
    return result.success && (result.data?.success ?? false)
  }

  /**
   * 获取温度控制配置
   * 
   * @returns 温度控制配置
   * @throws {ApiError} 接口请求失败
   */
  async getConfig(): Promise<TemperatureConfig | null> {
    const result = await this.get<TemperatureConfig>(`/${this.sensorId}/config`)
    return this.unwrap(result)
  }

  /**
   * 更新温度控制配置
   * 
   * @param config - 配置参数
   * @returns 更新后的配置
   * @throws {ValidationError} 参数校验失败
   * @throws {ApiError} 接口请求失败
   */
  async updateConfig(config: TemperatureConfig): Promise<TemperatureConfig | null> {
    if (config.kp !== undefined && config.kp < 0) {
      throw new ValidationError('PID比例系数必须大于等于0')
    }
    if (config.ki !== undefined && config.ki < 0) {
      throw new ValidationError('PID积分系数必须大于等于0')
    }
    if (config.kd !== undefined && config.kd < 0) {
      throw new ValidationError('PID微分系数必须大于等于0')
    }
    if (config.maxPower !== undefined && (config.maxPower < 0 || config.maxPower > 100)) {
      throw new ValidationError('最大功率必须在0-100范围内')
    }

    const result = await this.put<TemperatureConfig>(
      `/${this.sensorId}/config`,
      config as Record<string, unknown>
    )
    return this.unwrap(result)
  }

  /**
   * 获取温度历史数据
   * 
   * @param params - 查询参数
   * @returns 温度历史数据
   * @throws {ApiError} 接口请求失败
   */
  async getHistory(params: HistoryQueryParams = {}): Promise<TemperatureHistoryPoint[] | null> {
    const result = await this.get<TemperatureHistoryPoint[]>(`/${this.sensorId}/history`, {
      duration: params.duration ?? 300,
      interval: params.interval ?? '1s',
    })
    return this.unwrap(result)
  }

  /**
   * 设置温度报警阈值
   * 
   * @param params - 报警参数
   * @returns 是否设置成功
   * @throws {ValidationError} 参数校验失败
   * @throws {ApiError} 接口请求失败
   */
  async setAlarm(params: SetAlarmParams): Promise<boolean> {
    if (params.highLimit <= params.lowLimit) {
      throw new ValidationError('高温报警阈值必须大于低温报警阈值')
    }

    const result = await this.post<{ success: boolean }>('/alarm', {
      sensor_id: this.sensorId,
      high_limit: params.highLimit,
      low_limit: params.lowLimit,
    })

    return result.success && (result.data?.success ?? false)
  }

  /**
   * 获取温度报警状态
   * 
   * @returns 报警状态
   * @throws {ApiError} 接口请求失败
   */
  async getAlarmStatus(): Promise<AlarmStatus | null> {
    const result = await this.get<AlarmStatus>(`/${this.sensorId}/alarm`)
    return this.unwrap(result)
  }

  /**
   * 清除温度报警
   * 
   * @returns 是否清除成功
   * @throws {ApiError} 接口请求失败
   */
  async clearAlarm(): Promise<boolean> {
    const result = await this.post<{ success: boolean }>(`/${this.sensorId}/alarm/clear`)
    return result.success && (result.data?.success ?? false)
  }

  /**
   * 执行温度校准
   * 
   * @param params - 校准参数
   * @returns 校准结果
   * @throws {ApiError} 接口请求失败
   */
  async calibrate(params: CalibrateParams): Promise<{ success: boolean; offset: number } | null> {
    const result = await this.post<{ success: boolean; offset: number }>(
      `/${this.sensorId}/calibrate`,
      {
        reference_temp: params.referenceTemp,
      }
    )
    return this.unwrap(result)
  }

  /**
   * 获取加热器状态
   * 
   * @returns 加热器状态
   * @throws {ApiError} 接口请求失败
   */
  async getHeaterStatus(): Promise<HeaterStatus | null> {
    const result = await this.get<HeaterStatus>(`/${this.sensorId}/heater`)
    return this.unwrap(result)
  }

  /**
   * 设置加热器功率
   * 
   * @param params - 功率参数
   * @returns 是否设置成功
   * @throws {ValidationError} 参数校验失败
   * @throws {ApiError} 接口请求失败
   */
  async setHeaterPower(params: SetHeaterPowerParams): Promise<boolean> {
    if (params.power < 0 || params.power > 100) {
      throw new ValidationError('功率百分比必须在0-100范围内')
    }

    const result = await this.post<{ success: boolean }>('/heater/power', {
      sensor_id: this.sensorId,
      power: params.power,
    })

    return result.success && (result.data?.success ?? false)
  }

  /**
   * 获取所有温度传感器列表
   * 
   * @returns 传感器列表
   * @throws {ApiError} 接口请求失败
   */
  async getSensorList(): Promise<SensorInfo[] | null> {
    const result = await this.get<SensorInfo[]>('/sensors')
    return this.unwrap(result)
  }
}

export default TemperatureApiService
