/**
 * @file ammeter-api-service.ts
 * @path src/api/services/ammeter-api-service.ts
 * @description 皮安表API服务类，提供统一的微电流测量接口
 * @author Agent
 * @date 2026-03-26
 * @dependencies ./base-api-service, @/types/device
 * @safety: 量程设置必须校验，避免超出设备限制
 */

import { BaseApiService, ValidationError } from './base-api-service'
import type { PicoammeterStatus, PicoammeterParams } from '@/types/device'

/**
 * 量程设置参数
 */
export interface SetRangeParams {
  /** 量程 ('auto' | '1nA' | '10nA' | '100nA' | '1uA' | '10uA') */
  range: 'auto' | '1nA' | '10nA' | '100nA' | '1uA' | '10uA'
}

/**
 * 皮安表配置
 */
export interface AmmeterConfig {
  /** 采样率 */
  sampleRate?: number
  /** 滤波时间常数 */
  filterTime?: number
  /** 是否自动量程 */
  autoRange?: boolean
}

/**
 * 积分时间设置参数
 */
export interface SetIntegrationTimeParams {
  /** 积分时间（ms） */
  integrationTime: number
}

/**
 * 滤波器设置参数
 */
export interface SetFilterParams {
  /** 滤波类型 ('none' | 'low_pass' | 'moving_avg') */
  filterType: 'none' | 'low_pass' | 'moving_avg'
  /** 截止频率 */
  cutoffFrequency?: number
}

/**
 * 报警阈值设置参数
 */
export interface SetAlarmParams {
  /** 高限报警值 */
  highLimit: number
  /** 低限报警值 */
  lowLimit: number
}

/**
 * 报警状态信息
 */
export interface AlarmStatus {
  /** 是否报警 */
  isAlarm: boolean
  /** 报警类型 */
  alarmType?: 'high' | 'low' | 'overload'
  /** 报警时间 */
  alarmTime?: string
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
 * 测量历史数据点
 */
export interface MeasurementHistoryPoint {
  /** 时间戳 */
  timestamp: string
  /** 电流值（A） */
  current: number
  /** 量程 */
  range: string
}

/**
 * 统计数据查询参数
 */
export interface StatisticsQueryParams {
  /** 统计窗口（秒） */
  window?: number
}

/**
 * 统计数据
 */
export interface StatisticsData {
  /** 最大值 */
  max: number
  /** 最小值 */
  min: number
  /** 平均值 */
  mean: number
  /** 标准差 */
  std: number
  /** 采样点数 */
  count: number
}

/**
 * 导出参数
 */
export interface ExportParams {
  /** 导出格式 ('csv' | 'json' | 'excel') */
  format: 'csv' | 'json' | 'excel'
  /** 开始时间戳 */
  startTime?: number
  /** 结束时间戳 */
  endTime?: number
}

/**
 * 皮安表API服务类
 * 
 * @remarks
 * 所有接口统一使用unwrapResponse解包，内置3次超时重试机制
 * 量程设置前必须校验，避免超出设备限制
 */
export class AmmeterApiService extends BaseApiService {
  private readonly deviceId: string

  constructor(deviceId = 'default') {
    super({
      basePath: '/ammeter',
      timeout: 30000,
      retries: 3,
      useCache: false,
    })
    this.deviceId = deviceId
  }

  /**
   * 获取微电流计状态
   * 
   * @returns 微电流计状态信息
   * @throws {ApiError} 接口请求失败
   */
  async getStatus(): Promise<PicoammeterStatus | null> {
    const result = await this.get<PicoammeterStatus>(`/${this.deviceId}/status`)
    return this.unwrap(result)
  }

  /**
   * 获取当前电流值
   * 
   * @returns 当前电流值
   * @throws {ApiError} 接口请求失败
   */
  async getCurrentValue(): Promise<{ current: number; range: string } | null> {
    const result = await this.get<{ current: number; range: string }>(`/${this.deviceId}/current`)
    return this.unwrap(result)
  }

  /**
   * 设置量程
   * 
   * @param params - 量程参数
   * @returns 是否设置成功
   * @throws {ValidationError} 参数校验失败
   * @throws {ApiError} 接口请求失败
   */
  async setRange(params: SetRangeParams): Promise<boolean> {
    const validRanges = ['auto', '1nA', '10nA', '100nA', '1uA', '10uA']
    if (!validRanges.includes(params.range)) {
      throw new ValidationError(`量程必须为 ${validRanges.join('、')} 之一`)
    }

    const result = await this.post<{ success: boolean }>('/range', {
      ammeter_id: this.deviceId,
      range: params.range,
    })

    return result.success && (result.data?.success ?? false)
  }

  /**
   * 获取当前量程
   * 
   * @returns 当前量程
   * @throws {ApiError} 接口请求失败
   */
  async getCurrentRange(): Promise<{ range: string } | null> {
    const result = await this.get<{ range: string }>(`/${this.deviceId}/range`)
    return this.unwrap(result)
  }

  /**
   * 启动测量
   * 
   * @returns 是否启动成功
   * @throws {ApiError} 接口请求失败
   */
  async start(): Promise<boolean> {
    const result = await this.post<{ success: boolean }>(`/${this.deviceId}/start`)
    return result.success && (result.data?.success ?? false)
  }

  /**
   * 停止测量
   * 
   * @returns 是否停止成功
   * @throws {ApiError} 接口请求失败
   */
  async stop(): Promise<boolean> {
    const result = await this.post<{ success: boolean }>(`/${this.deviceId}/stop`)
    return result.success && (result.data?.success ?? false)
  }

  /**
   * 执行零点校准
   * 
   * @returns 校准结果
   * @throws {ApiError} 接口请求失败
   */
  async zeroCalibrate(): Promise<{ success: boolean; offset: number } | null> {
    const result = await this.post<{ success: boolean; offset: number }>(`/${this.deviceId}/zero`)
    return this.unwrap(result)
  }

  /**
   * 获取微电流计配置
   * 
   * @returns 微电流计配置
   * @throws {ApiError} 接口请求失败
   */
  async getConfig(): Promise<AmmeterConfig | null> {
    const result = await this.get<AmmeterConfig>(`/${this.deviceId}/config`)
    return this.unwrap(result)
  }

  /**
   * 更新微电流计配置
   * 
   * @param config - 配置参数
   * @returns 更新后的配置
   * @throws {ValidationError} 参数校验失败
   * @throws {ApiError} 接口请求失败
   */
  async updateConfig(config: AmmeterConfig): Promise<AmmeterConfig | null> {
    if (config.sampleRate !== undefined && config.sampleRate <= 0) {
      throw new ValidationError('采样率必须大于0')
    }
    if (config.filterTime !== undefined && config.filterTime < 0) {
      throw new ValidationError('滤波时间常数必须大于等于0')
    }

    const result = await this.put<AmmeterConfig>(
      `/${this.deviceId}/config`,
      config as Record<string, unknown>
    )
    return this.unwrap(result)
  }

  /**
   * 获取测量历史数据
   * 
   * @param params - 查询参数
   * @returns 测量历史数据
   * @throws {ApiError} 接口请求失败
   */
  async getHistory(params: HistoryQueryParams = {}): Promise<MeasurementHistoryPoint[] | null> {
    const result = await this.get<MeasurementHistoryPoint[]>(`/${this.deviceId}/history`, {
      duration: params.duration ?? 300,
      interval: params.interval ?? '1s',
    })
    return this.unwrap(result)
  }

  /**
   * 设置积分时间
   * 
   * @param params - 积分参数
   * @returns 是否设置成功
   * @throws {ValidationError} 参数校验失败
   * @throws {ApiError} 接口请求失败
   */
  async setIntegrationTime(params: SetIntegrationTimeParams): Promise<boolean> {
    if (params.integrationTime <= 0) {
      throw new ValidationError('积分时间必须大于0')
    }

    const result = await this.post<{ success: boolean }>('/integration', {
      ammeter_id: this.deviceId,
      integration_time: params.integrationTime,
    })

    return result.success && (result.data?.success ?? false)
  }

  /**
   * 设置滤波器
   * 
   * @param params - 滤波参数
   * @returns 是否设置成功
   * @throws {ValidationError} 参数校验失败
   * @throws {ApiError} 接口请求失败
   */
  async setFilter(params: SetFilterParams): Promise<boolean> {
    const validTypes = ['none', 'low_pass', 'moving_avg']
    if (!validTypes.includes(params.filterType)) {
      throw new ValidationError(`滤波类型必须为 ${validTypes.join('、')} 之一`)
    }
    if (params.cutoffFrequency !== undefined && params.cutoffFrequency <= 0) {
      throw new ValidationError('截止频率必须大于0')
    }

    const result = await this.post<{ success: boolean }>('/filter', {
      ammeter_id: this.deviceId,
      filter_type: params.filterType,
      cutoff_frequency: params.cutoffFrequency,
    })

    return result.success && (result.data?.success ?? false)
  }

  /**
   * 获取统计数据
   * 
   * @param params - 统计参数
   * @returns 统计数据
   * @throws {ApiError} 接口请求失败
   */
  async getStatistics(params: StatisticsQueryParams = {}): Promise<StatisticsData | null> {
    const result = await this.get<StatisticsData>(`/${this.deviceId}/statistics`, {
      window: params.window ?? 60,
    })
    return this.unwrap(result)
  }

  /**
   * 设置电流报警阈值
   * 
   * @param params - 报警参数
   * @returns 是否设置成功
   * @throws {ValidationError} 参数校验失败
   * @throws {ApiError} 接口请求失败
   */
  async setAlarm(params: SetAlarmParams): Promise<boolean> {
    if (params.highLimit <= params.lowLimit) {
      throw new ValidationError('高限报警值必须大于低限报警值')
    }

    const result = await this.post<{ success: boolean }>('/alarm', {
      ammeter_id: this.deviceId,
      high_limit: params.highLimit,
      low_limit: params.lowLimit,
    })

    return result.success && (result.data?.success ?? false)
  }

  /**
   * 获取报警状态
   * 
   * @returns 报警状态
   * @throws {ApiError} 接口请求失败
   */
  async getAlarmStatus(): Promise<AlarmStatus | null> {
    const result = await this.get<AlarmStatus>(`/${this.deviceId}/alarm`)
    return this.unwrap(result)
  }

  /**
   * 清除报警
   * 
   * @returns 是否清除成功
   * @throws {ApiError} 接口请求失败
   */
  async clearAlarm(): Promise<boolean> {
    const result = await this.post<{ success: boolean }>(`/${this.deviceId}/alarm/clear`)
    return result.success && (result.data?.success ?? false)
  }

  /**
   * 导出测量数据
   * 
   * @param params - 导出参数
   * @returns 文件Blob对象
   * @throws {ApiError} 接口请求失败
   */
  async exportData(params: ExportParams): Promise<Blob> {
    const validFormats = ['csv', 'json', 'excel']
    if (!validFormats.includes(params.format)) {
      throw new ValidationError(`导出格式必须为 ${validFormats.join('、')} 之一`)
    }

    try {
      const response = await fetch(`${this.buildUrl(`/${this.deviceId}/export`)}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(params),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      return await response.blob()
    } catch (error) {
      console.error('[AmmeterAPI] Export data error:', error)
      throw error
    }
  }
}

export default AmmeterApiService
