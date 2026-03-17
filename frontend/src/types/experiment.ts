/**
 * @file experiment.ts
 * @path src/types/
 * @description 实验相关类型定义
 */

import type { ID, TimeRange } from './api'

/** 实验状态枚举 */
export enum ExperimentStatus {
  DRAFT = 'draft',
  RUNNING = 'running',
  PAUSED = 'paused',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

/** 实验类型枚举 */
export enum ExperimentType {
  MH_LOOP = 'mh_loop',
  TIME_DECAY = 'time_decay',
  TEMPERATURE_SWEEP = 'temp_sweep',
  FIELD_SWEEP = 'field_sweep',
  CUSTOM = 'custom',
}

/** 实验基础信息 */
export interface Experiment {
  /** 实验 ID */
  id: ID
  /** 实验名称 */
  name: string
  /** 实验类型 */
  type: ExperimentType
  /** 实验状态 */
  status: ExperimentStatus
  /** 创建时间 */
  createdAt: string
  /** 更新时间 */
  updatedAt: string
  /** 开始时间 */
  startedAt?: string
  /** 结束时间 */
  endedAt?: string
  /** 实验描述 */
  description?: string
  /** 实验参数 */
  parameters: ExperimentParameters
  /** 实验结果 */
  results?: ExperimentResults
  /** 创建者 ID */
  createdBy: ID
  /** 标签 */
  tags?: string[]
}

/** 实验参数基础接口 */
export interface ExperimentParameters {
  /** 采样间隔 (ms) */
  sampleInterval: number
  /** 是否自动保存 */
  autoSave: boolean
  /** 自动保存间隔 (s) */
  autoSaveInterval?: number
}

/** 磁滞回线实验参数 */
export interface MhLoopParameters extends ExperimentParameters {
  type: ExperimentType.MH_LOOP
  /** 磁场范围 (T) */
  fieldRange: number
  /** 磁场步长 (T) */
  fieldStep: number
  /** 循环次数 */
  cycles: number
  /** 扫描速率 (T/s) */
  sweepRate: number
}

/** 时间衰减实验参数 */
export interface TimeDecayParameters extends ExperimentParameters {
  type: ExperimentType.TIME_DECAY
  /** 总时长 (s) */
  duration: number
  /** 初始磁场 (T) */
  initialField: number
  /** 数据点数量 */
  dataPoints: number
}

/** 温度扫描实验参数 */
export interface TemperatureSweepParameters extends ExperimentParameters {
  type: ExperimentType.TEMPERATURE_SWEEP
  /** 起始温度 (°C) */
  startTemp: number
  /** 结束温度 (°C) */
  endTemp: number
  /** 升温速率 (°C/min) */
  rampRate: number
  /** 保持时间 (s) */
  holdTime: number
}

/** 磁场扫描实验参数 */
export interface FieldSweepParameters extends ExperimentParameters {
  type: ExperimentType.FIELD_SWEEP
  /** 起始磁场 (T) */
  startField: number
  /** 结束磁场 (T) */
  endField: number
  /** 扫描速率 (T/s) */
  sweepRate: number
  /** 固定温度 (°C) */
  temperature?: number
}

/** 实验参数联合类型 */
export type AnyExperimentParameters =
  | MhLoopParameters
  | TimeDecayParameters
  | TemperatureSweepParameters
  | FieldSweepParameters
  | ExperimentParameters

/** 实验数据点 */
export interface ExperimentDataPoint {
  /** 时间戳 */
  timestamp: string
  /** 序号 */
  index: number
  /** 磁场强度 (T) */
  field?: number
  /** 磁化强度 (A/m) */
  magnetization?: number
  /** 电流 (A) */
  current?: number
  /** 温度 (°C) */
  temperature?: number
  /** 位移 (μm) */
  displacement?: number
  /** 原始数据 */
  raw?: Record<string, number>
}

/** 实验结果 */
export interface ExperimentResults {
  /** 数据点数量 */
  dataPoints: number
  /** 数据文件路径 */
  dataFile?: string
  /** 拟合参数 */
  fitParams?: FitParameters
  /** 统计信息 */
  statistics?: ExperimentStatistics
}

/** 拟合参数 */
export interface FitParameters {
  /** 饱和磁化强度 (A/m) */
  Ms?: number
  /** 剩余磁化强度 (A/m) */
  Mr?: number
  /** 矫顽力 (T) */
  Hc?: number
  /** 拟合优度 R² */
  rSquared?: number
  /** 拟合参数字典 */
  params?: Record<string, number>
}

/** 实验统计信息 */
export interface ExperimentStatistics {
  /** 平均值 */
  mean?: number
  /** 标准差 */
  std?: number
  /** 最大值 */
  max?: number
  /** 最小值 */
  min?: number
  /** 峰峰值 */
  peakToPeak?: number
}

/** 实验创建请求 */
export interface CreateExperimentRequest {
  name: string
  type: ExperimentType
  description?: string
  parameters: AnyExperimentParameters
  tags?: string[]
}

/** 实验更新请求 */
export interface UpdateExperimentRequest {
  name?: string
  description?: string
  parameters?: Partial<AnyExperimentParameters>
  tags?: string[]
}

/** 实验查询参数 */
export interface ExperimentQueryParams {
  status?: ExperimentStatus
  type?: ExperimentType
  timeRange?: TimeRange
  search?: string
  tags?: string[]
}
