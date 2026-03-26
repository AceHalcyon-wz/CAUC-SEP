/**
 * @file piezo-api-service.ts
 * @path src/api/services/piezo-api-service.ts
 * @description 压电控制器API服务类，提供统一的压电控制接口
 * @author Agent
 * @date 2026-03-26
 * @dependencies ./base-api-service, @/types/device
 * @safety: 电压设置必须校验范围，避免超出设备限制
 */

import { BaseApiService, ValidationError } from './base-api-service'
import type { PiezoControllerStatus, PiezoControlParams } from '@/types/device'

/**
 * 电压设置参数
 */
export interface SetVoltageParams {
  /** 目标电压（V） */
  voltage: number
  /** 通道号（多通道设备） */
  channel?: number
}

/**
 * 位移设置参数
 */
export interface SetDisplacementParams {
  /** 目标位移（μm） */
  displacement: number
  /** 通道号 */
  channel?: number
}

/**
 * 压电控制器配置
 */
export interface PiezoConfig {
  /** 最大电压 */
  maxVoltage?: number
  /** 最大位移 */
  maxDisplacement?: number
  /** 灵敏度 */
  sensitivity?: number
}

/**
 * 扫描模式参数
 */
export interface SetScanModeParams {
  /** 扫描模式 ('sawtooth' | 'triangle' | 'sine') */
  mode: 'sawtooth' | 'triangle' | 'sine'
  /** 扫描幅度 */
  amplitude: number
  /** 扫描频率 */
  frequency: number
}

/**
 * 历史数据查询参数
 */
export interface HistoryQueryParams {
  /** 查询时长（秒） */
  duration?: number
  /** 通道号 */
  channel?: number
}

/**
 * 电压历史数据点
 */
export interface VoltageHistoryPoint {
  /** 时间戳 */
  timestamp: string
  /** 电压值（V） */
  voltage: number
  /** 位移值（μm） */
  displacement: number
}

/**
 * 校准参数
 */
export interface CalibrateParams {
  /** 参考电压 */
  referenceVoltage?: number
  /** 参考位移 */
  referenceDisplacement?: number
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
 * 通道信息
 */
export interface ChannelInfo {
  /** 通道号 */
  channel: number
  /** 当前电压 */
  voltage: number
  /** 当前位移 */
  displacement: number
  /** 是否启用 */
  enabled: boolean
}

/**
 * 压电控制器API服务类
 * 
 * @remarks
 * 所有接口统一使用unwrapResponse解包，内置3次超时重试机制
 * 电压设置前必须校验范围，避免超出设备限制
 */
export class PiezoApiService extends BaseApiService {
  private readonly deviceId: string

  constructor(deviceId = 'default') {
    super({
      basePath: '/piezo',
      timeout: 30000,
      retries: 3,
      useCache: false,
    })
    this.deviceId = deviceId
  }

  /**
   * 获取压电控制器状态
   * 
   * @returns 压电控制器状态信息
   * @throws {ApiError} 接口请求失败
   */
  async getStatus(): Promise<PiezoControllerStatus | null> {
    const result = await this.get<PiezoControllerStatus>(`/${this.deviceId}/status`)
    return this.unwrap(result)
  }

  /**
   * 设置压电陶瓷电压
   * 
   * @param params - 电压参数
   * @returns 设置结果
   * @throws {ValidationError} 参数校验失败
   * @throws {ApiError} 接口请求失败
   */
  async setVoltage(params: SetVoltageParams): Promise<{ voltage: number } | null> {
    if (params.voltage < 0) {
      throw new ValidationError('电压必须大于等于0')
    }
    if (params.channel !== undefined && params.channel < 0) {
      throw new ValidationError('通道号必须大于等于0')
    }

    const result = await this.post<{ voltage: number }>('/voltage', {
      piezo_id: this.deviceId,
      voltage: params.voltage,
      channel: params.channel,
    })

    return this.unwrap(result)
  }

  /**
   * 获取当前电压
   * 
   * @param channel - 通道号
   * @returns 当前电压值
   * @throws {ApiError} 接口请求失败
   */
  async getCurrentVoltage(channel?: number): Promise<{ voltage: number; channel: number } | null> {
    const params = channel !== undefined ? { channel } : null
    const result = await this.get<{ voltage: number; channel: number }>(
      `/${this.deviceId}/voltage`,
      params as Record<string, unknown>
    )
    return this.unwrap(result)
  }

  /**
   * 设置压电陶瓷位移
   * 
   * @param params - 位移参数
   * @returns 设置结果
   * @throws {ValidationError} 参数校验失败
   * @throws {ApiError} 接口请求失败
   */
  async setDisplacement(params: SetDisplacementParams): Promise<{ displacement: number } | null> {
    if (params.displacement < 0) {
      throw new ValidationError('位移必须大于等于0')
    }

    const result = await this.post<{ displacement: number }>('/displacement', {
      piezo_id: this.deviceId,
      displacement: params.displacement,
      channel: params.channel,
    })

    return this.unwrap(result)
  }

  /**
   * 获取当前位移
   * 
   * @returns 当前位移值
   * @throws {ApiError} 接口请求失败
   */
  async getCurrentDisplacement(): Promise<{ displacement: number } | null> {
    const result = await this.get<{ displacement: number }>(`/${this.deviceId}/displacement`)
    return this.unwrap(result)
  }

  /**
   * 启用压电陶瓷
   * 
   * @returns 是否启用成功
   * @throws {ApiError} 接口请求失败
   */
  async enable(): Promise<boolean> {
    const result = await this.post<{ success: boolean }>(`/${this.deviceId}/enable`)
    return result.success && (result.data?.success ?? false)
  }

  /**
   * 禁用压电陶瓷
   * 
   * @returns 是否禁用成功
   * @throws {ApiError} 接口请求失败
   */
  async disable(): Promise<boolean> {
    const result = await this.post<{ success: boolean }>(`/${this.deviceId}/disable`)
    return result.success && (result.data?.success ?? false)
  }

  /**
   * 压电陶瓷归零
   * 
   * @returns 归零结果
   * @throws {ApiError} 接口请求失败
   */
  async zero(): Promise<{ success: boolean } | null> {
    const result = await this.post<{ success: boolean }>(`/${this.deviceId}/zero`)
    return this.unwrap(result)
  }

  /**
   * 获取压电陶瓷配置
   * 
   * @returns 压电陶瓷配置
   * @throws {ApiError} 接口请求失败
   */
  async getConfig(): Promise<PiezoConfig | null> {
    const result = await this.get<PiezoConfig>(`/${this.deviceId}/config`)
    return this.unwrap(result)
  }

  /**
   * 更新压电陶瓷配置
   * 
   * @param config - 配置参数
   * @returns 更新后的配置
   * @throws {ValidationError} 参数校验失败
   * @throws {ApiError} 接口请求失败
   */
  async updateConfig(config: PiezoConfig): Promise<PiezoConfig | null> {
    if (config.maxVoltage !== undefined && config.maxVoltage <= 0) {
      throw new ValidationError('最大电压必须大于0')
    }
    if (config.maxDisplacement !== undefined && config.maxDisplacement <= 0) {
      throw new ValidationError('最大位移必须大于0')
    }
    if (config.sensitivity !== undefined && config.sensitivity <= 0) {
      throw new ValidationError('灵敏度必须大于0')
    }

    const result = await this.put<PiezoConfig>(
      `/${this.deviceId}/config`,
      config as Record<string, unknown>
    )
    return this.unwrap(result)
  }

  /**
   * 获取通道列表
   * 
   * @returns 通道列表
   * @throws {ApiError} 接口请求失败
   */
  async getChannels(): Promise<ChannelInfo[] | null> {
    const result = await this.get<ChannelInfo[]>(`/${this.deviceId}/channels`)
    return this.unwrap(result)
  }

  /**
   * 设置所有通道电压
   * 
   * @param voltages - 各通道电压数组
   * @returns 是否设置成功
   * @throws {ValidationError} 参数校验失败
   * @throws {ApiError} 接口请求失败
   */
  async setAllChannelVoltages(voltages: number[]): Promise<boolean> {
    if (voltages.length === 0) {
      throw new ValidationError('电压数组不能为空')
    }
    for (const v of voltages) {
      if (v < 0) {
        throw new ValidationError('所有电压值必须大于等于0')
      }
    }

    const result = await this.post<{ success: boolean }>('/voltages', {
      piezo_id: this.deviceId,
      voltages,
    })

    return result.success && (result.data?.success ?? false)
  }

  /**
   * 获取电压历史数据
   * 
   * @param params - 查询参数
   * @returns 电压历史数据
   * @throws {ApiError} 接口请求失败
   */
  async getHistory(params: HistoryQueryParams = {}): Promise<VoltageHistoryPoint[] | null> {
    const result = await this.get<VoltageHistoryPoint[]>(`/${this.deviceId}/history`, {
      duration: params.duration ?? 300,
      channel: params.channel,
    })
    return this.unwrap(result)
  }

  /**
   * 执行压电陶瓷校准
   * 
   * @param params - 校准参数
   * @returns 校准结果
   * @throws {ApiError} 接口请求失败
   */
  async calibrate(params: CalibrateParams = {}): Promise<{ success: boolean; message: string } | null> {
    const result = await this.post<{ success: boolean; message: string }>(
      `/${this.deviceId}/calibrate`,
      {
        reference_voltage: params.referenceVoltage,
        reference_displacement: params.referenceDisplacement,
      }
    )
    return this.unwrap(result)
  }

  /**
   * 获取压电陶瓷温度
   * 
   * @returns 温度信息
   * @throws {ApiError} 接口请求失败
   */
  async getTemperature(): Promise<TemperatureInfo | null> {
    const result = await this.get<TemperatureInfo>(`/${this.deviceId}/temperature`)
    return this.unwrap(result)
  }

  /**
   * 设置扫描模式
   * 
   * @param params - 扫描参数
   * @returns 是否设置成功
   * @throws {ValidationError} 参数校验失败
   * @throws {ApiError} 接口请求失败
   */
  async setScanMode(params: SetScanModeParams): Promise<boolean> {
    const validModes = ['sawtooth', 'triangle', 'sine']
    if (!validModes.includes(params.mode)) {
      throw new ValidationError(`扫描模式必须为 ${validModes.join('、')} 之一`)
    }
    if (params.amplitude <= 0) {
      throw new ValidationError('扫描幅度必须大于0')
    }
    if (params.frequency <= 0) {
      throw new ValidationError('扫描频率必须大于0')
    }

    const result = await this.post<{ success: boolean }>('/scan', {
      piezo_id: this.deviceId,
      mode: params.mode,
      amplitude: params.amplitude,
      frequency: params.frequency,
    })

    return result.success && (result.data?.success ?? false)
  }

  /**
   * 停止扫描
   * 
   * @returns 是否停止成功
   * @throws {ApiError} 接口请求失败
   */
  async stopScan(): Promise<boolean> {
    const result = await this.post<{ success: boolean }>(`/${this.deviceId}/scan/stop`)
    return result.success && (result.data?.success ?? false)
  }
}

export default PiezoApiService
