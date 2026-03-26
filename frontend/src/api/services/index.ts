/**
 * @file index.ts
 * @path src/api/services/
 * @description API服务统一导出
 * @author Agent
 * @date 2026-03-26
 */

// ==================== 基础服务类 ====================
export { BaseApiService, ApiError, DeviceCommunicationError, DeviceAlarmError, ValidationError } from './base-api-service'
export type { ApiServiceConfig } from './base-api-service'

// ==================== 设备API服务类 ====================
export { MotorApiService } from './motor-api-service'
export type { MotorMoveRequest, MotorJogRequest, SoftLimitConfig, MotorPRConfig } from './motor-api-service'

export { DeviceApiService } from './device-api-service'

export { ElectromagnetApiService } from './electromagnet-api-service'
export type { 
  SetFieldParams, 
  SetCurrentParams, 
  SetPolarityParams, 
  ElectromagnetConfig,
  HistoryQueryParams as ElectromagnetHistoryParams,
  FieldHistoryPoint,
  TemperatureInfo as ElectromagnetTemperatureInfo,
  SafetyStatus
} from './electromagnet-api-service'

export { TemperatureApiService } from './temperature-api-service'
export type { 
  SetTargetTempParams, 
  TemperatureConfig, 
  SetAlarmParams as TemperatureAlarmParams,
  AlarmStatus as TemperatureAlarmStatus,
  HeaterStatus,
  HistoryQueryParams as TemperatureHistoryParams,
  TemperatureHistoryPoint,
  CalibrateParams as TemperatureCalibrateParams,
  SetHeaterPowerParams,
  SensorInfo
} from './temperature-api-service'

export { PiezoApiService } from './piezo-api-service'
export type { 
  SetVoltageParams, 
  SetDisplacementParams, 
  PiezoConfig,
  SetScanModeParams,
  HistoryQueryParams as PiezoHistoryParams,
  VoltageHistoryPoint,
  CalibrateParams as PiezoCalibrateParams,
  TemperatureInfo as PiezoTemperatureInfo,
  ChannelInfo
} from './piezo-api-service'

export { AmmeterApiService } from './ammeter-api-service'
export type { 
  SetRangeParams, 
  AmmeterConfig,
  SetIntegrationTimeParams,
  SetFilterParams,
  SetAlarmParams as AmmeterAlarmParams,
  AlarmStatus as AmmeterAlarmStatus,
  HistoryQueryParams as AmmeterHistoryParams,
  MeasurementHistoryPoint,
  StatisticsQueryParams,
  StatisticsData,
  ExportParams
} from './ammeter-api-service'

// ==================== 服务工厂函数 ====================

/**
 * 创建电机API服务实例
 * @param deviceId - 设备ID
 * @returns 电机API服务实例
 */
export function createMotorApi(deviceId = 'default'): MotorApiService {
  return new MotorApiService(deviceId)
}

/**
 * 创建设备API服务实例
 * @returns 设备API服务实例
 */
export function createDeviceApi(): DeviceApiService {
  return new DeviceApiService()
}

/**
 * 创建电磁铁API服务实例
 * @param deviceId - 设备ID
 * @returns 电磁铁API服务实例
 */
export function createElectromagnetApi(deviceId = 'default'): ElectromagnetApiService {
  return new ElectromagnetApiService(deviceId)
}

/**
 * 创建温度控制器API服务实例
 * @param sensorId - 传感器ID
 * @returns 温度控制器API服务实例
 */
export function createTemperatureApi(sensorId = 'default'): TemperatureApiService {
  return new TemperatureApiService(sensorId)
}

/**
 * 创建压电控制器API服务实例
 * @param deviceId - 设备ID
 * @returns 压电控制器API服务实例
 */
export function createPiezoApi(deviceId = 'default'): PiezoApiService {
  return new PiezoApiService(deviceId)
}

/**
 * 创建皮安表API服务实例
 * @param deviceId - 设备ID
 * @returns 皮安表API服务实例
 */
export function createAmmeterApi(deviceId = 'default'): AmmeterApiService {
  return new AmmeterApiService(deviceId)
}
