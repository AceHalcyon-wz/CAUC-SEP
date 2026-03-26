/**
 * @file device-api-service.ts
 * @path src/api/services/device-api-service.ts
 * @description 设备管理API服务类，提供统一的设备连接、状态管理接口
 * @author Agent
 * @date 2026-03-25
 * @dependencies ./base-api-service, @/types/device
 */

import { BaseApiService, ApiError, DeviceCommunicationError } from './base-api-service'
import type { DeviceInfo, DeviceStatus, DeviceConnectionStatus } from '@/types/device'

/**
 * 设备连接请求参数
 */
export interface DeviceConnectRequest {
  /** 设备ID */
  deviceId: string
  /** 连接参数 */
  params?: Record<string, unknown>
}

/**
 * 设备列表响应
 */
export interface DeviceListResponse {
  /** 设备列表 */
  devices: DeviceInfo[]
  /** 总数 */
  total: number
}

/**
 * 设备状态响应
 */
export interface DeviceStatusResponse {
  /** 设备ID */
  deviceId: string
  /** 连接状态 */
  connectionStatus: DeviceConnectionStatus
  /** 设备状态 */
  status: DeviceStatus
}

/**
 * 设备管理API服务类
 * 
 * @remarks
 * 提供设备连接、断开、状态查询等统一接口
 */
export class DeviceApiService extends BaseApiService {
  constructor() {
    super({
      basePath: '/device',
      timeout: 30000,
      retries: 3,
      useCache: false,
    })
  }

  /**
   * 获取所有设备列表
   * 
   * @returns 设备列表
   * @throws {ApiError} 接口请求失败
   */
  async getDevices(): Promise<DeviceInfo[]> {
    const result = await this.get<DeviceListResponse>('/list')
    return this.unwrap(result)?.devices ?? []
  }

  /**
   * 获取设备状态
   * 
   * @param deviceId - 设备ID
   * @returns 设备状态
   * @throws {ApiError} 接口请求失败
   */
  async getDeviceStatus(deviceId: string): Promise<DeviceStatusResponse | null> {
    const result = await this.get<DeviceStatusResponse>(`/${deviceId}/status`)
    return this.unwrap(result)
  }

  /**
   * 连接设备
   * 
   * @param deviceId - 设备ID
   * @param params - 连接参数
   * @returns 连接结果
   * @throws {DeviceCommunicationError} 设备通信失败
   * @throws {ApiError} 接口请求失败
   */
  async connectDevice(deviceId: string, params?: Record<string, unknown>): Promise<boolean> {
    const result = await this.post<{ success: boolean }>(`/${deviceId}/connect`, params ?? {})

    if (!result.success) {
      throw new DeviceCommunicationError(`设备 ${deviceId} 连接失败: ${result.message}`)
    }

    return result.data?.success ?? false
  }

  /**
   * 断开设备连接
   * 
   * @param deviceId - 设备ID
   * @returns 断开结果
   * @throws {ApiError} 接口请求失败
   */
  async disconnectDevice(deviceId: string): Promise<boolean> {
    const result = await this.post<{ success: boolean }>(`/${deviceId}/disconnect`)

    return result.success && (result.data?.success ?? false)
  }

  /**
   * 连接所有设备
   * 
   * @returns 连接结果
   * @throws {ApiError} 接口请求失败
   */
  async connectAllDevices(): Promise<boolean> {
    const result = await this.post<{ success: boolean }>('/connect-all')

    return result.success && (result.data?.success ?? false)
  }

  /**
   * 断开所有设备连接
   * 
   * @returns 断开结果
   * @throws {ApiError} 接口请求失败
   */
  async disconnectAllDevices(): Promise<boolean> {
    const result = await this.post<{ success: boolean }>('/disconnect-all')

    return result.success && (result.data?.success ?? false)
  }

  /**
   * 执行所有设备紧急停止
   * 
   * @returns 急停结果
   * @throws {ApiError} 接口请求失败
   * 
   * @safety 急停接口必须最高优先级执行
   */
  async emergencyStopAll(): Promise<boolean> {
    const result = await this.post<{ success: boolean }>('/emergency-stop-all', null, {
      timeout: 5000,
      retries: 3,
    })

    return result.success && (result.data?.success ?? false)
  }

  /**
   * 刷新设备状态
   * 
   * @returns 刷新结果
   * @throws {ApiError} 接口请求失败
   */
  async refreshStatus(): Promise<boolean> {
    const result = await this.post<{ success: boolean }>('/refresh-status')

    return result.success && (result.data?.success ?? false)
  }
}

export default DeviceApiService
