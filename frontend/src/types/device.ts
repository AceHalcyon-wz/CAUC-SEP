/**
 * @file device.ts
 * @path src/types/
 * @description 设备相关类型定义
 * @author Agent
 * @date 2024-03-16
 */

/** 设备状态枚举 */
export enum DeviceStatus {
  DISCONNECTED = 'disconnected',
  CONNECTING = 'connecting',
  READY = 'ready',
  RUNNING = 'running',
  ERROR = 'error',
  EMERGENCY_STOP = 'emergency_stop',
  MAINTENANCE = 'maintenance',
}

/** 设备类型枚举 */
export enum DeviceType {
  STEPPER = 'stepper',
  ELECTROMAGNET = 'electromagnet',
  TEMPERATURE = 'temperature',
  PIEZO = 'piezo',
  AMMETER = 'ammeter',
}

/** 设备基础信息 */
export interface DeviceInfo {
  /** 设备唯一标识 */
  id: string
  /** 设备名称 */
  name: string
  /** 设备类型 */
  type: DeviceType
  /** 当前状态 */
  status: DeviceStatus
  /** 是否已连接 */
  connected: boolean
  /** 是否仿真模式 */
  simulation: boolean
  /** 连接时间 */
  connectedAt?: string
  /** 最后活动时间 */
  lastActivity?: string
  /** 错误信息 */
  errorMessage?: string
}

/** 设备连接配置 */
export interface DeviceConnectionConfig {
  /** 通信端口 */
  port: string
  /** 波特率 */
  baudRate?: number
  /** 从站 ID */
  slaveId?: number
  /** 超时时间(ms) */
  timeout?: number
  /** 是否启用仿真模式 */
  simulation?: boolean
}

// ==================== 步进电机相关类型 ====================

/** 步进电机状态 */
export interface StepperMotorStatus extends DeviceInfo {
  type: DeviceType.STEPPER
  /** 当前位置 (mm) */
  position: number
  /** 目标位置 (mm) */
  targetPosition: number
  /** 当前速度 (steps/s) */
  speed: number
  /** 是否正在移动 */
  isMoving: boolean
  /** 正向软限位 (mm) */
  positiveLimit: number
  /** 负向软限位 (mm) */
  negativeLimit: number
  /** 是否使能 */
  enabled: boolean
}

/** 步进电机移动参数 */
export interface StepperMoveParams {
  /** 目标位置 (mm) */
  position: number
  /** 移动速度 (steps/s) */
  speed?: number
  /** 是否相对移动 */
  relative?: boolean
}

/** 电机状态（别名，兼容 MotorStatus） */
export interface MotorStatus {
  /** 设备 ID */
  deviceId: string
  /** 当前位置 (mm) */
  positionMm: number
  /** 当前位置 (steps) */
  positionSteps: number
  /** 是否正在移动 */
  isMoving: boolean
  /** 移动速度 (mm/s) */
  velocityMmS: number
  /** 报警代码 */
  alarmCode: number
  /** 报警文本 */
  alarmText: string
  /** 是否已连接 */
  connected: boolean
  /** 是否仿真模式 */
  simulation: boolean
}

/** 移动请求参数 */
export interface MoveRequest {
  /** 目标位置 (mm) */
  positionMm: number
  /** 移动速度 (mm/s) */
  velocityMmS?: number
}

/** JOG 请求参数 */
export interface JogRequest {
  /** 方向 (1: 正向, -1: 负向) */
  direction: 1 | -1
  /** 移动速度 (mm/s) */
  velocityMmS?: number
}

/** 限位配置 */
export interface PositionLimits {
  /** 正向限位 (mm) */
  positiveMm: number
  /** 负向限位 (mm) */
  negativeMm: number
  /** 是否启用 */
  enabled: boolean
}

/** 电机配置 */
export interface MotorConfig {
  /** 电机 ID */
  motorId: string
  /** 波特率 */
  baudRate: number
  /** 从站地址 */
  slaveId: number
  /** 数据类型 */
  dataType: number
  /** 正向限位 (mm) */
  positiveLimitMm: number
  /** 负向限位 (mm) */
  negativeLimitMm: number
  /** 正向限位 (steps) */
  positiveLimitSteps: number
  /** 负向限位 (steps) */
  negativeLimitSteps: number
}

// ==================== 电磁铁相关类型 ====================

/** 电磁铁状态 */
export interface ElectromagnetStatus extends DeviceInfo {
  type: DeviceType.ELECTROMAGNET
  /** 当前电流 (A) */
  current: number
  /** 目标电流 (A) */
  targetCurrent: number
  /** 最大电流 (A) */
  maxCurrent: number
  /** 是否输出使能 */
  outputEnabled: boolean
}

/** 电磁铁控制参数 */
export interface ElectromagnetParams {
  /** 目标电流 (A) */
  current: number
  /** 是否使能输出 */
  enabled?: boolean
}

// ==================== 温控器相关类型 ====================

/** 温控器状态 */
export interface TemperatureControllerStatus extends DeviceInfo {
  type: DeviceType.TEMPERATURE
  /** 当前温度 (°C) */
  temperature: number
  /** 目标温度 (°C) */
  targetTemperature: number
  /** 是否正在加热 */
  isHeating: boolean
  /** 是否正在冷却 */
  isCooling: boolean
  /** PID 参数 */
  pid: PidParams
  /** 温度上限 */
  maxTemp: number
  /** 温度下限 */
  minTemp: number
}

/** PID 参数 */
export interface PidParams {
  /** 比例系数 */
  kp: number
  /** 积分系数 */
  ki: number
  /** 微分系数 */
  kd: number
}

/** 温控器控制参数 */
export interface TemperatureControlParams {
  /** 目标温度 (°C) */
  temperature: number
  /** PID 参数 */
  pid?: Partial<PidParams>
}

/** 温度状态（简化版） */
export interface TemperatureStatus {
  /** 设备 ID */
  deviceId: string
  /** 当前温度 (°C) */
  currentTemp: number
  /** 目标温度 (°C) */
  targetTemp: number
  /** 是否正在加热 */
  isHeating: boolean
  /** 是否正在冷却 */
  isCooling: boolean
  /** 是否已连接 */
  connected: boolean
}

// ==================== 压电控制器相关类型 ====================

/** 压电控制器状态 */
export interface PiezoControllerStatus extends DeviceInfo {
  type: DeviceType.PIEZO
  /** 各通道电压 (V) */
  voltages: number[]
  /** 各通道位移 (μm) */
  displacements: number[]
  /** 最大电压 (V) */
  maxVoltage: number
  /** 最大位移 (μm) */
  maxDisplacement: number
  /** 通道数 */
  channels: number
}

/** 压电控制参数 */
export interface PiezoControlParams {
  /** 通道索引 */
  channel: number
  /** 目标电压 (V) */
  voltage: number
}

/** 压电状态（简化版） */
export interface PiezoStatus {
  /** 设备 ID */
  deviceId: string
  /** 各通道电压 (V) */
  voltages: number[]
  /** 各通道位移 (μm) */
  displacements: number[]
  /** 是否已连接 */
  connected: boolean
}

// ==================== 皮安表相关类型 ====================

/** 皮安表状态 */
export interface PicoammeterStatus extends DeviceInfo {
  type: DeviceType.AMMETER
  /** 当前电流读数 (A) */
  current: number
  /** 电流范围 */
  range: string
  /** 采样率 (Hz) */
  sampleRate: number
  /** 是否正在采集 */
  isSampling: boolean
}

/** 皮安表采集参数 */
export interface PicoammeterParams {
  /** 采样率 (Hz) */
  sampleRate?: number
  /** 电流范围 */
  range?: string
  /** 是否开始采集 */
  startSampling?: boolean
}

/** 电流表状态（简化版） */
export interface AmmeterStatus {
  /** 设备 ID */
  deviceId: string
  /** 当前电流 (A) */
  current: number
  /** 电流范围 */
  range: string
  /** 采样率 (Hz) */
  sampleRate: number
  /** 是否正在采集 */
  isSampling: boolean
  /** 是否已连接 */
  connected: boolean
}

// ==================== 联合类型 ====================

/** 设备状态联合类型 */
export type AnyDeviceStatus =
  | StepperMotorStatus
  | ElectromagnetStatus
  | TemperatureControllerStatus
  | PiezoControllerStatus
  | PicoammeterStatus

/** 设备状态映射 */
export interface DeviceStatusMap {
  [DeviceType.STEPPER]: StepperMotorStatus
  [DeviceType.ELECTROMAGNET]: ElectromagnetStatus
  [DeviceType.TEMPERATURE]: TemperatureControllerStatus
  [DeviceType.PIEZO]: PiezoControllerStatus
  [DeviceType.AMMETER]: PicoammeterStatus
}
