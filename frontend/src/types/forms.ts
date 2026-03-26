/**
 * @file forms.ts
 * @path frontend/src/types/forms.ts
 * @description 表单参数类型定义，包含所有设备控制、实验配置的表单参数类型
 * @author Agent
 * @date 2026-03-25
 * @dependencies ./api, ./device
 */

import type { ID } from './api'

// ==================== 电机控制表单参数 ====================

/** 电机移动表单参数 */
export interface MotorMoveForm {
  /** 目标位置 (mm) */
  position: number
  /** 移动速度 (mm/s) */
  velocity: number
  /** 是否相对移动 */
  relative?: boolean
}

/** 电机回零表单参数 */
export interface MotorHomeForm {
  /** 回零模式 */
  mode: 'auto' | 'positive' | 'negative' | 'current'
  /** 回零速度 (mm/s) */
  speed?: number
}

/** 电机JOG控制表单参数 */
export interface MotorJogForm {
  /** JOG方向 */
  direction: 'positive' | 'negative'
  /** JOG速度 (mm/s) */
  velocity: number
}

/** 电机限位配置表单 */
export interface MotorLimitConfigForm {
  /** 正向限位 (mm) */
  positiveLimitMm: number
  /** 负向限位 (mm) */
  negativeLimitMm: number
  /** 是否启用限位 */
  enabled: boolean
}

/** 电机通信配置表单 */
export interface MotorCommunicationForm {
  /** 波特率 */
  baudRate: number
  /** 从站地址 */
  slaveId: number
  /** 数据类型 */
  dataType: number
}

// ==================== 电磁铁控制表单参数 ====================

/** 电磁铁电流设置表单 */
export interface ElectromagnetCurrentForm {
  /** 目标电流 (A) */
  current: number
  /** 是否使能输出 */
  enabled: boolean
}

/** 电磁铁扫描配置表单 */
export interface ElectromagnetScanForm {
  /** 起始电流 (A) */
  startCurrent: number
  /** 结束电流 (A) */
  endCurrent: number
  /** 扫描步长 (A) */
  stepCurrent: number
  /** 扫描速度 (A/s) */
  scanRate: number
  /** 循环次数 */
  cycles?: number
}

// ==================== 温度控制表单参数 ====================

/** 温度设置表单 */
export interface TemperatureSetForm {
  /** 目标温度 (°C) */
  temperature: number
  /** 是否使能加热 */
  enabled: boolean
}

/** PID参数配置表单 */
export interface PidConfigForm {
  /** 比例系数 */
  kp: number
  /** 积分系数 */
  ki: number
  /** 微分系数 */
  kd: number
}

/** 温度程序段配置 */
export interface TemperatureProgramSegment {
  /** 目标温度 (°C) */
  targetTemp: number
  /** 升温速率 (°C/min) */
  rampRate: number
  /** 保持时间 (s) */
  holdTime: number
}

/** 温度程序配置表单 */
export interface TemperatureProgramForm {
  /** 程序段列表 */
  segments: TemperatureProgramSegment[]
  /** 是否循环 */
  loop?: boolean
  /** 循环次数 */
  loopCount?: number
}

// ==================== 压电控制表单参数 ====================

/** 压电电压设置表单 */
export interface PiezoVoltageForm {
  /** 通道索引 */
  channel: number
  /** 目标电压 (V) */
  voltage: number
}

/** 压电校准配置表单 */
export interface PiezoCalibrationForm {
  /** 通道索引 */
  channel: number
  /** 校准点列表 */
  calibrationPoints: Array<{
    /** 电压值 (V) */
    voltage: number
    /** 位移值 (μm) */
    displacement: number
  }>
}

// ==================== 皮安表控制表单参数 ====================

/** 皮安表采集配置表单 */
export interface AmmeterAcquisitionForm {
  /** 采样率 (Hz) */
  sampleRate: number
  /** 电流范围 */
  currentRange: string
  /** 采集时长 (s) */
  duration?: number
  /** 是否连续采集 */
  continuous?: boolean
}

/** 皮安表通道配置表单 */
export interface AmmeterChannelConfigForm {
  /** 通道索引 */
  channel: number
  /** 是否启用 */
  enabled: boolean
  /** 通道名称 */
  name?: string
  /** 电流范围 */
  range?: string
}

// ==================== 实验配置表单参数 ====================

/** 实验基础配置表单 */
export interface ExperimentBaseForm {
  /** 实验名称 */
  name: string
  /** 实验描述 */
  description?: string
  /** 采样间隔 (ms) */
  sampleInterval: number
  /** 是否自动保存 */
  autoSave: boolean
  /** 自动保存间隔 (s) */
  autoSaveInterval?: number
}

/** 磁滞回线实验配置表单 */
export interface MhLoopExperimentForm extends ExperimentBaseForm {
  /** 磁场范围 (T) */
  fieldRange: number
  /** 磁场步长 (T) */
  fieldStep: number
  /** 循环次数 */
  cycles: number
  /** 扫描速率 (T/s) */
  sweepRate: number
}

/** 时间衰减实验配置表单 */
export interface TimeDecayExperimentForm extends ExperimentBaseForm {
  /** 总时长 (s) */
  duration: number
  /** 初始磁场 (T) */
  initialField: number
  /** 数据点数量 */
  dataPoints: number
}

/** 温度扫描实验配置表单 */
export interface TempSweepExperimentForm extends ExperimentBaseForm {
  /** 起始温度 (°C) */
  startTemp: number
  /** 结束温度 (°C) */
  endTemp: number
  /** 升温速率 (°C/min) */
  rampRate: number
  /** 保持时间 (s) */
  holdTime: number
}

/** 磁场扫描实验配置表单 */
export interface FieldSweepExperimentForm extends ExperimentBaseForm {
  /** 起始磁场 (T) */
  startField: number
  /** 结束磁场 (T) */
  endField: number
  /** 扫描速率 (T/s) */
  sweepRate: number
  /** 固定温度 (°C) */
  temperature?: number
}

// ==================== 查询与筛选表单参数 ====================

/** 时间范围选择 */
export interface TimeRangeForm {
  /** 开始时间 */
  startTime: string
  /** 结束时间 */
  endTime: string
  /** 快捷时间选项 */
  quickOption?: '1h' | '6h' | '12h' | '24h' | '3d' | '7d' | '30d'
}

/** 历史数据查询表单 */
export interface HistoryQueryForm {
  /** 时间范围 */
  timeRange: TimeRangeForm
  /** 设备ID列表 */
  deviceIds?: string[]
  /** 实验ID列表 */
  experimentIds?: ID[]
  /** 数据类型列表 */
  dataTypes?: string[]
  /** 数据质量筛选 */
  quality?: 'good' | 'normal' | 'poor' | ''
  /** 聚合方式 */
  aggregation?: 'none' | 'avg' | 'max' | 'min' | 'sum'
  /** 聚合间隔 (s) */
  aggregationInterval?: number
}

/** 查询模板 */
export interface QueryTemplate {
  /** 模板ID */
  id: ID
  /** 模板名称 */
  name: string
  /** 模板描述 */
  description?: string
  /** 查询条件 */
  conditions: HistoryQueryForm
  /** 创建时间 */
  createdAt: string
  /** 是否收藏 */
  starred?: boolean
}

// ==================== 用户配置表单参数 ====================

/** 用户配置表单 */
export interface UserConfigForm {
  /** 用户名 */
  username: string
  /** 邮箱 */
  email?: string
  /** 主题 */
  theme?: 'light' | 'dark' | 'auto'
  /** 语言 */
  language?: 'zh-CN' | 'en-US'
  /** 通知设置 */
  notifications?: {
    /** 是否启用声音通知 */
    sound?: boolean
    /** 是否启用桌面通知 */
    desktop?: boolean
    /** 是否启用邮件通知 */
    email?: boolean
  }
}

/** 登录表单 */
export interface LoginForm {
  /** 用户名 */
  username: string
  /** 密码 */
  password: string
  /** 是否记住登录 */
  remember?: boolean
}

/** 密码修改表单 */
export interface PasswordChangeForm {
  /** 旧密码 */
  oldPassword: string
  /** 新密码 */
  newPassword: string
  /** 确认新密码 */
  confirmPassword: string
}

// ==================== 设备连接表单参数 ====================

/** 设备连接表单 */
export interface DeviceConnectForm {
  /** 通信端口 */
  port: string
  /** 波特率 */
  baudRate?: number
  /** 从站ID */
  slaveId?: number
  /** 超时时间 (ms) */
  timeout?: number
  /** 是否仿真模式 */
  simulation?: boolean
}

/** 串口配置表单 */
export interface SerialConfigForm {
  /** 串口模式 */
  mode: 'rs485' | 'rs232'
  /** 串口号 */
  port: string
  /** 波特率 */
  baudRate: number
  /** 数据位 */
  dataBits?: 7 | 8
  /** 停止位 */
  stopBits?: 1 | 2
  /** 校验位 */
  parity?: 'none' | 'even' | 'odd'
}

// ==================== PR路径配置表单参数 ====================

/** PR路径点配置 */
export interface PRPathPoint {
  /** 路径点序号 */
  index: number
  /** 目标位置 (mm) */
  position: number
  /** 移动速度 (mm/s) */
  velocity: number
  /** 停留时间 (ms) */
  dwellTime?: number
  /** 是否启用 */
  enabled: boolean
}

/** PR路径配置表单 */
export interface PRPathConfigForm {
  /** 路径ID */
  pathId: number
  /** 路径名称 */
  name?: string
  /** 路径点列表 */
  points: PRPathPoint[]
  /** 是否循环执行 */
  loop?: boolean
  /** 循环次数 */
  loopCount?: number
}

// ==================== 位置预设表单参数 ====================

/** 位置预设配置 */
export interface PositionPresetForm {
  /** 预设ID */
  id: ID
  /** 预设名称 */
  name: string
  /** 目标位置 (mm) */
  position: number
  /** 移动速度 (mm/s) */
  velocity?: number
  /** 备注 */
  description?: string
}

// ==================== IO端口配置表单参数 ====================

/** IO端口配置表单 */
export interface IOPortConfigForm {
  /** 端口号 */
  port: number
  /** 端口模式 */
  mode: 'input' | 'output'
  /** 端口功能 */
  function?: 'limit_positive' | 'limit_negative' | 'home' | 'alarm' | 'custom'
  /** 是否启用 */
  enabled: boolean
  /** 逻辑电平 */
  activeLevel?: 'high' | 'low'
}

// ==================== 审计日志查询表单参数 ====================

/** 审计日志查询表单 */
export interface AuditLogQueryForm {
  /** 时间范围 */
  timeRange?: TimeRangeForm
  /** 用户ID */
  userId?: ID
  /** 操作类型 */
  operationType?: string
  /** 操作模块 */
  module?: string
  /** 操作结果 */
  result?: 'success' | 'failure' | ''
  /** 关键字搜索 */
  keyword?: string
}

// ==================== 系统配置表单参数 ====================

/** 系统配置表单 */
export interface SystemConfigForm {
  /** 数据保存路径 */
  dataPath?: string
  /** 日志级别 */
  logLevel?: 'debug' | 'info' | 'warn' | 'error'
  /** 最大日志文件大小 (MB) */
  maxLogSize?: number
  /** 日志保留天数 */
  logRetentionDays?: number
  /** 是否启用自动备份 */
  autoBackup?: boolean
  /** 备份间隔 (天) */
  backupInterval?: number
  /** 最大备份数量 */
  maxBackupCount?: number
}
