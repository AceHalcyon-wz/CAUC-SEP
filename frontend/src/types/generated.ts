/**
 * @file generated.ts
 * @path src/types/
 * @description OpenAPI 自动生成的类型定义文件
 * @author Backend Engineer Agent
 * @date 2026-03-15
 *
 * ⚠️ 此文件由 openapi-typescript 自动生成，请勿手动编辑！
 *
 * 生成方式：
 * 1. 确保后端服务运行中：cd backend && uvicorn main:app --reload
 * 2. 运行生成命令：cd frontend && npm run generate:types
 *
 * 使用示例：
 * ```typescript
 * import type { components } from '@/types/generated'
 *
 * type DeviceInfo = components['schemas']['DeviceInfoResponse']
 * type ApiResponse = components['schemas']['ApiResponse']
 *
 * async function getDevices(): Promise<DeviceInfo[]> {
 *   const response = await fetch('/api/v1/devices')
 *   const data: ApiResponse = await response.json()
 *   return data.data ?? []
 * }
 * ```
 *
 * 注意事项：
 * - 后端 Schema 变更后需要重新生成
 * - 此文件应提交到 Git，便于代码审查
 * - 生产环境部署前确保类型已同步
 */

// 占位类型定义，实际类型由 openapi-typescript 生成
// 当后端 API 完成后，运行 npm run generate:types 生成实际类型

export interface components {
  schemas: {
    // ==================== API 通用响应 ====================
    ApiError: {
      code: string
      message: string
      details?: Record<string, unknown>
    }

    ApiResponse: {
      success: boolean
      data?: unknown
      error?: components['schemas']['ApiError']
      timestamp: string
    }

    PaginatedData: {
      items: unknown[]
      total: number
      page: number
      page_size: number
      total_pages: number
    }

    PaginationParams: {
      page?: number
      page_size?: number
      sort_by?: string
      sort_order?: 'asc' | 'desc'
    }

    // ==================== 设备管理 ====================
    DeviceStatus:
      | 'disconnected'
      | 'connecting'
      | 'ready'
      | 'running'
      | 'error'
      | 'emergency_stop'

    DeviceType: 'stepper' | 'electromagnet' | 'temperature' | 'piezo' | 'ammeter'

    DeviceInfoResponse: {
      id: string
      name: string
      type: components['schemas']['DeviceType']
      status: components['schemas']['DeviceStatus']
      connected: boolean
      simulation: boolean
      connected_at?: string
      error_message?: string
    }

    DeviceConnectRequest: {
      port?: string
      baud_rate?: number
      slave_id?: number
      timeout?: number
      simulation?: boolean
    }

    DeviceConnectResponse: {
      device_id: string
      connected: boolean
      message: string
    }

    StepperMotorStatus: components['schemas']['DeviceInfoResponse'] & {
      type: 'stepper'
      position: number
      target_position: number
      speed: number
      is_moving: boolean
      positive_limit: number
      negative_limit: number
      enabled: boolean
    }

    StepperMoveRequest: {
      position: number
      speed?: number
      relative?: boolean
    }

    ElectromagnetStatus: components['schemas']['DeviceInfoResponse'] & {
      type: 'electromagnet'
      current: number
      target_current: number
      max_current: number
      output_enabled: boolean
    }

    ElectromagnetControlRequest: {
      current: number
      enabled?: boolean
    }

    TemperatureControllerStatus: components['schemas']['DeviceInfoResponse'] & {
      type: 'temperature'
      temperature: number
      target_temperature: number
      is_heating: boolean
      is_cooling: boolean
    }

    TemperatureControlRequest: {
      temperature: number
      pid_kp?: number
      pid_ki?: number
      pid_kd?: number
    }

    PiezoControllerStatus: components['schemas']['DeviceInfoResponse'] & {
      type: 'piezo'
      voltages: number[]
      displacements: number[]
      max_voltage: number
      channels: number
    }

    PiezoControlRequest: {
      channel: number
      voltage: number
    }

    PicoammeterStatus: components['schemas']['DeviceInfoResponse'] & {
      type: 'ammeter'
      current: number
      range: string
      sample_rate: number
      is_sampling: boolean
    }

    // ==================== 实验管理 ====================
    ExperimentStatus: 'created' | 'running' | 'paused' | 'completed' | 'cancelled'

    ExperimentResponse: {
      id: number
      name: string
      description: string
      status: components['schemas']['ExperimentStatus']
      created_at: string
      started_at?: string
      completed_at?: string
      parameters?: Record<string, unknown>
    }

    ExperimentCreateRequest: {
      name: string
      description?: string
      parameters?: Record<string, unknown>
    }

    ExperimentUpdateRequest: {
      name?: string
      description?: string
    }

    ExperimentParameters: {
      motor_start: number
      motor_end: number
      motor_speed?: number
      electromagnet_max_current: number
      electromagnet_min_current?: number
      current_step?: number
      sample_rate?: number
      temperature?: number
    }

    ExperimentDataPoint: {
      timestamp: string
      position: number
      current: number
      voltage?: number
      temperature?: number
      magnetic_field?: number
    }

    ExperimentDataResponse: {
      experiment_id: number
      total_points: number
      data: components['schemas']['ExperimentDataPoint'][]
    }

    // ==================== 认证 ====================
    LoginRequest: {
      username: string
      password: string
    }

    LoginResponse: {
      access_token: string
      refresh_token: string
      token_type: string
      expires_in: number
    }

    UserInfoResponse: {
      id: number
      username: string
      email?: string
      role: string
      created_at: string
    }

    PasswordChangeRequest: {
      old_password: string
      new_password: string
    }
  }
}

// 常用类型别名
export type DeviceInfo = components['schemas']['DeviceInfoResponse']
export type Experiment = components['schemas']['ExperimentResponse']
export type ApiSuccessResponse<T> = {
  success: true
  data: T
  error?: never
  timestamp: string
}
export type ApiErrorResponse = {
  success: false
  data?: never
  error: components['schemas']['ApiError']
  timestamp: string
}
