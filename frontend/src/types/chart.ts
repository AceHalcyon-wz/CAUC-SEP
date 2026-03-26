/**
 * @file chart.ts
 * @path frontend/src/types/chart.ts
 * @description 图表相关类型定义，包含ECharts配置、数据系列、图表工具栏等类型
 * @author Agent
 * @date 2026-03-25
 * @dependencies ./api
 */

import type { ID } from './api'

// ==================== 图表基础类型 ====================

/** 图表类型枚举 */
export enum ChartType {
  /** 折线图 */
  LINE = 'line',
  /** 柱状图 */
  BAR = 'bar',
  /** 散点图 */
  SCATTER = 'scatter',
  /** 饼图 */
  PIE = 'pie',
  /** 面积图 */
  AREA = 'area',
  /** 热力图 */
  HEATMAP = 'heatmap',
  /** 仪表盘 */
  GAUGE = 'gauge',
  /** 雷达图 */
  RADAR = 'radar',
}

/** 图表主题 */
export type ChartTheme = 'light' | 'dark' | 'default'

/** 图表尺寸 */
export interface ChartSize {
  /** 宽度 */
  width: number | string
  /** 高度 */
  height: number | string
}

// ==================== 数据系列类型 ====================

/** 数据点类型 */
export interface ChartDataPoint {
  /** 数据值 */
  value: number | number[]
  /** 数据名称 */
  name?: string
  /** 数据项样式 */
  itemStyle?: ChartItemStyle
  /** 额外数据 */
  extra?: Record<string, unknown>
}

/** 数据系列基础配置 */
export interface ChartSeriesBase {
  /** 系列名称 */
  name: string
  /** 系列类型 */
  type: ChartType | string
  /** 数据 */
  data: ChartDataPoint[] | number[] | number[][]
  /** 是否显示 */
  show?: boolean
  /** 系列样式 */
  itemStyle?: ChartItemStyle
  /** 线条样式 */
  lineStyle?: ChartLineStyle
  /** 区域样式 */
  areaStyle?: ChartAreaStyle
  /** 是否平滑曲线 */
  smooth?: boolean
  /** 是否堆叠 */
  stack?: string
  /** Y轴索引 */
  yAxisIndex?: number
  /** X轴索引 */
  xAxisIndex?: number
}

/** 折线图系列 */
export interface LineSeries extends ChartSeriesBase {
  type: ChartType.LINE
  /** 是否显示符号 */
  showSymbol?: boolean
  /** 符号大小 */
  symbolSize?: number | number[]
  /** 符号形状 */
  symbol?: 'circle' | 'rect' | 'triangle' | 'diamond' | 'pin' | 'arrow'
  /** 采样策略 */
  sampling?: 'lttb' | 'average' | 'max' | 'min' | 'sum'
}

/** 柱状图系列 */
export interface BarSeries extends ChartSeriesBase {
  type: ChartType.BAR
  /** 柱子宽度 */
  barWidth?: number | string
  /** 柱子最大宽度 */
  barMaxWidth?: number | string
  /** 柱子最小宽度 */
  barMinWidth?: number | string
  /** 柱子间距 */
  barGap?: string
}

/** 散点图系列 */
export interface ScatterSeries extends ChartSeriesBase {
  type: ChartType.SCATTER
  /** 符号大小 */
  symbolSize?: number | number[] | ((value: number[]) => number)
  /** 符号形状 */
  symbol?: string
}

/** 面积图系列 */
export interface AreaSeries extends LineSeries {
  type: ChartType.AREA
  /** 面积样式 */
  areaStyle: ChartAreaStyle
}

/** 数据系列联合类型 */
export type ChartSeries = LineSeries | BarSeries | ScatterSeries | AreaSeries | ChartSeriesBase

// ==================== 坐标轴类型 ====================

/** 坐标轴类型 */
export type AxisType = 'value' | 'category' | 'time' | 'log'

/** 坐标轴位置 */
export type AxisPosition = 'top' | 'bottom' | 'left' | 'right'

/** 坐标轴标签配置 */
export interface AxisLabel {
  /** 是否显示 */
  show?: boolean
  /** 标签间隔 */
  interval?: number | 'auto'
  /** 标签旋转角度 */
  rotate?: number
  /** 标签格式化函数 */
  formatter?: string | ((value: number | string, index: number) => string)
  /** 字体大小 */
  fontSize?: number
  /** 字体颜色 */
  color?: string
  /** 字体粗细 */
  fontWeight?: 'normal' | 'bold' | 'bolder' | 'lighter'
}

/** 坐标轴线配置 */
export interface AxisLine {
  /** 是否显示 */
  show?: boolean
  /** 线条样式 */
  lineStyle?: ChartLineStyle
  /** 是否在坐标轴两侧 */
  onZero?: boolean
}

/** 坐标轴刻度配置 */
export interface AxisTick {
  /** 是否显示 */
  show?: boolean
  /** 刻度间隔 */
  interval?: number | 'auto'
  /** 刻度线长度 */
  length?: number
  /** 刻度线样式 */
  lineStyle?: ChartLineStyle
}

/** 分割线配置 */
export interface SplitLine {
  /** 是否显示 */
  show?: boolean
  /** 线条样式 */
  lineStyle?: ChartLineStyle
}

/** 坐标轴基础配置 */
export interface AxisBase {
  /** 坐标轴类型 */
  type?: AxisType
  /** 坐标轴名称 */
  name?: string
  /** 坐标轴名称位置 */
  nameLocation?: 'start' | 'middle' | 'end'
  /** 坐标轴名称文本样式 */
  nameTextStyle?: {
    fontSize?: number
    color?: string
    fontWeight?: string
    padding?: number | number[]
  }
  /** 是否反向坐标轴 */
  inverse?: boolean
  /** 坐标轴位置 */
  position?: AxisPosition
  /** 坐标轴标签 */
  axisLabel?: AxisLabel
  /** 坐标轴线 */
  axisLine?: AxisLine
  /** 坐标轴刻度 */
  axisTick?: AxisTick
  /** 分割线 */
  splitLine?: SplitLine
  /** 最小值 */
  min?: number | 'dataMin' | ((value: { min: number; max: number }) => number)
  /** 最大值 */
  max?: number | 'dataMax' | ((value: { min: number; max: number }) => number)
  /** 分割段数 */
  splitNumber?: number
  /** 类目数据 */
  data?: (string | number)[]
}

/** X轴配置 */
export interface XAxis extends AxisBase {
  /** 坐标轴位置 */
  position?: 'top' | 'bottom'
}

/** Y轴配置 */
export interface YAxis extends AxisBase {
  /** 坐标轴位置 */
  position?: 'left' | 'right'
}

// ==================== 图例类型 ====================

/** 图例配置 */
export interface Legend {
  /** 是否显示 */
  show?: boolean
  /** 图例类型 */
  type?: 'plain' | 'scroll'
  /** 图例位置 */
  position?: 'top' | 'bottom' | 'left' | 'right'
  /** 图例布局朝向 */
  orient?: 'horizontal' | 'vertical'
  /** 图例项间距 */
  itemGap?: number
  /** 图例项宽度 */
  itemWidth?: number
  /** 图例项高度 */
  itemHeight?: number
  /** 图例数据 */
  data?: string[]
  /** 图例文本样式 */
  textStyle?: ChartTextStyle
  /** 选中状态 */
  selected?: Record<string, boolean>
}

// ==================== 提示框类型 ====================

/** 提示框触发类型 */
export type TooltipTrigger = 'item' | 'axis' | 'none'

/** 提示框配置 */
export interface Tooltip {
  /** 是否显示 */
  show?: boolean
  /** 触发类型 */
  trigger?: TooltipTrigger
  /** 提示框内容格式化 */
  formatter?: string | ((params: TooltipParam | TooltipParam[]) => string)
  /** 背景色 */
  backgroundColor?: string
  /** 边框颜色 */
  borderColor?: string
  /** 边框宽度 */
  borderWidth?: number
  /** 内边距 */
  padding?: number | number[]
  /** 文本样式 */
  textStyle?: ChartTextStyle
  /** 是否显示提示框浮层 */
  showContent?: boolean
  /** 是否始终显示 */
  alwaysShowContent?: boolean
  /** 触发延迟 */
  triggerOn?: 'mousemove' | 'click' | 'mousemove|click'
}

/** 提示框参数 */
export interface TooltipParam {
  /** 组件类型 */
  componentType: string
  /** 系列类型 */
  seriesType: string
  /** 系列索引 */
  seriesIndex: number
  /** 系列名称 */
  seriesName: string
  /** 数据名称 */
  name: string
  /** 数据索引 */
  dataIndex: number
  /** 数据值 */
  value: number | number[]
  /** 数据颜色 */
  color: string
  /** 百分比（饼图等） */
  percent?: number
  /** 数据项 */
  data?: ChartDataPoint
  /** 标记类型 */
  marker?: string
}

// ==================== 数据缩放类型 ====================

/** 数据缩放类型 */
export type DataZoomType = 'inside' | 'slider'

/** 数据缩放基础配置 */
export interface DataZoomBase {
  /** 缩放类型 */
  type: DataZoomType
  /** X轴索引 */
  xAxisIndex?: number | number[]
  /** Y轴索引 */
  yAxisIndex?: number | number[]
  /** 过滤模式 */
  filterMode?: 'filter' | 'weakFilter' | 'empty' | 'none'
  /** 起始百分比 (0-100) */
  start?: number
  /** 结束百分比 (0-100) */
  end?: number
  /** 起始值 */
  startValue?: number | string
  /** 结束值 */
  endValue?: number | string
  /** 最小缩放比例 */
  minSpan?: number
  /** 最大缩放比例 */
  maxSpan?: number
}

/** 内置数据缩放 */
export interface InsideDataZoom extends DataZoomBase {
  type: 'inside'
  /** 是否开启缩放 */
  zoomOnMouseWheel?: boolean
  /** 是否开启平移 */
  moveOnMouseMove?: boolean
  /** 是否开启平移 */
  moveOnMouseWheel?: boolean
  /** 是否禁止缩放 */
  disabled?: boolean
}

/** 滑动条数据缩放 */
export interface SliderDataZoom extends DataZoomBase {
  type: 'slider'
  /** 是否显示 */
  show?: boolean
  /** 位置 */
  position?: 'top' | 'bottom' | 'left' | 'right'
  /** 高度 */
  height?: number
  /** 宽度 */
  width?: number
  /** 背景色 */
  backgroundColor?: string
  /** 数据背景样式 */
  dataBackground?: {
    lineStyle?: ChartLineStyle
    areaStyle?: ChartAreaStyle
  }
  /** 选中区域样式 */
  selectedDataBackground?: {
    lineStyle?: ChartLineStyle
    areaStyle?: ChartAreaStyle
  }
  /** 填充器样式 */
  fillerColor?: string
  /** 边框颜色 */
  borderColor?: string
  /** 是否显示详情 */
  showDetail?: boolean
  /** 是否显示数据阴影 */
  showDataShadow?: boolean
  /** 是否实时更新 */
  realtime?: boolean
}

/** 数据缩放联合类型 */
export type DataZoom = InsideDataZoom | SliderDataZoom

// ==================== 标注类型 ====================

/** 标注点配置 */
export interface MarkPoint {
  /** 标注数据 */
  data: Array<{
    /** 标注名称 */
    name?: string
    /** 标注类型 */
    type?: 'min' | 'max' | 'average'
    /** 坐标 */
    coord?: [number | string, number | string]
    /** 标注值 */
    value?: number | string
    /** 符号 */
    symbol?: string
    /** 符号大小 */
    symbolSize?: number | number[]
    /** 标注样式 */
    itemStyle?: ChartItemStyle
    /** 标签 */
    label?: ChartLabel
  }>
  /** 标注样式 */
  symbol?: string
  /** 标注大小 */
  symbolSize?: number | number[]
  /** 标注样式 */
  itemStyle?: ChartItemStyle
}

/** 标注线配置 */
export interface MarkLine {
  /** 标注线数据 */
  data: Array<{
    /** 标注线名称 */
    name?: string
    /** 标注线类型 */
    type?: 'min' | 'max' | 'average'
    /** 起点坐标 */
    coord?: [number | string, number | string]
    /** 终点坐标 */
    endCoord?: [number | string, number | string]
    /** X轴坐标 */
    xAxis?: number | string
    /** Y轴坐标 */
    yAxis?: number | string
    /** 标注线样式 */
    lineStyle?: ChartLineStyle
    /** 标签 */
    label?: ChartLabel
  }>
  /** 是否显示 */
  show?: boolean
  /** 标注线样式 */
  lineStyle?: ChartLineStyle
  /** 标签 */
  label?: ChartLabel
  /** 标注线动画 */
  animation?: boolean
}

/** 标注区域配置 */
export interface MarkArea {
  /** 标注区域数据 */
  data: Array<{
    /** 区域名称 */
    name?: string
    /** 区域坐标 */
    coord?: [[number | string, number | string], [number | string, number | string]]
    /** X轴坐标范围 */
    xAxis?: [number | string, number | string]
    /** Y轴坐标范围 */
    yAxis?: [number | string, number | string]
    /** 区域样式 */
    itemStyle?: ChartItemStyle
    /** 标签 */
    label?: ChartLabel
  }>
  /** 是否显示 */
  show?: boolean
  /** 区域样式 */
  itemStyle?: ChartItemStyle
  /** 标签 */
  label?: ChartLabel
}

// ==================== 样式类型 ====================

/** 文本样式 */
export interface ChartTextStyle {
  /** 字体颜色 */
  color?: string
  /** 字体样式 */
  fontStyle?: 'normal' | 'italic' | 'oblique'
  /** 字体粗细 */
  fontWeight?: 'normal' | 'bold' | 'bolder' | 'lighter' | number
  /** 字体大小 */
  fontSize?: number
  /** 字体 */
  fontFamily?: string
  /** 行高 */
  lineHeight?: number
  /** 文本宽度 */
  width?: number
  /** 文本高度 */
  height?: number
  /** 文本溢出 */
  overflow?: 'truncate' | 'break' | 'breakAll'
  /** 溢出文本 */
  ellipsis?: string
}

/** 标签样式 */
export interface ChartLabel extends ChartTextStyle {
  /** 是否显示 */
  show?: boolean
  /** 标签位置 */
  position?: 'top' | 'left' | 'right' | 'bottom' | 'inside' | 'insideLeft' | 'insideRight' | 'insideTop' | 'insideBottom'
  /** 标签距离 */
  distance?: number
  /** 标签旋转角度 */
  rotate?: number
  /** 标签格式化 */
  formatter?: string | ((params: TooltipParam) => string)
  /** 背景色 */
  backgroundColor?: string
  /** 边框颜色 */
  borderColor?: string
  /** 边框宽度 */
  borderWidth?: number
  /** 边框圆角 */
  borderRadius?: number
  /** 内边距 */
  padding?: number | number[]
}

/** 图形项样式 */
export interface ChartItemStyle {
  /** 颜色 */
  color?: string | string[] | ((params: TooltipParam) => string)
  /** 边框颜色 */
  borderColor?: string
  /** 边框宽度 */
  borderWidth?: number
  /** 边框类型 */
  borderType?: 'solid' | 'dashed' | 'dotted'
  /** 圆角 */
  borderRadius?: number | number[]
  /** 透明度 */
  opacity?: number
  /** 阴影 */
  shadowBlur?: number
  shadowColor?: string
  shadowOffsetX?: number
  shadowOffsetY?: number
}

/** 线条样式 */
export interface ChartLineStyle {
  /** 线条颜色 */
  color?: string
  /** 线条宽度 */
  width?: number
  /** 线条类型 */
  type?: 'solid' | 'dashed' | 'dotted'
  /** 透明度 */
  opacity?: number
  /** 阴影 */
  shadowBlur?: number
  shadowColor?: string
  shadowOffsetX?: number
  shadowOffsetY?: number
}

/** 区域样式 */
export interface ChartAreaStyle {
  /** 填充颜色 */
  color?: string | string[]
  /** 原点位置 */
  origin?: 'auto' | 'start' | 'end'
  /** 透明度 */
  opacity?: number
  /** 阴影 */
  shadowBlur?: number
  shadowColor?: string
  shadowOffsetX?: number
  shadowOffsetY?: number
}

// ==================== 图表配置类型 ====================

/** 图表标题配置 */
export interface ChartTitle {
  /** 是否显示 */
  show?: boolean
  /** 标题文本 */
  text?: string
  /** 副标题文本 */
  subtext?: string
  /** 标题位置 */
  left?: 'left' | 'center' | 'right' | number | string
  top?: 'top' | 'middle' | 'bottom' | number | string
  /** 文本样式 */
  textStyle?: ChartTextStyle
  /** 副标题文本样式 */
  subtextStyle?: ChartTextStyle
  /** 间距 */
  itemGap?: number
  /** 背景色 */
  backgroundColor?: string
  /** 边框 */
  borderColor?: string
  borderWidth?: number
  borderRadius?: number
  padding?: number | number[]
}

/** 图表网格配置 */
export interface ChartGrid {
  /** 是否显示 */
  show?: boolean
  /** 左边距 */
  left?: number | string
  /** 右边距 */
  right?: number | string
  /** 上边距 */
  top?: number | string
  /** 下边距 */
  bottom?: number | string
  /** 是否包含坐标轴 */
  containLabel?: boolean
  /** 背景色 */
  backgroundColor?: string
  /** 边框 */
  borderColor?: string
  borderWidth?: number
}

/** 图表工具箱配置 */
export interface ChartToolbox {
  /** 是否显示 */
  show?: boolean
  /** 功能配置 */
  feature: {
    /** 保存为图片 */
    saveAsImage?: {
      show?: boolean
      title?: string
      type?: 'png' | 'jpeg' | 'svg'
      name?: string
      pixelRatio?: number
      backgroundColor?: string
    }
    /** 数据视图 */
    dataView?: {
      show?: boolean
      title?: string
      lang?: string[]
      backgroundColor?: string
      textareaColor?: string
      textareaBorderColor?: string
      textColor?: string
    }
    /** 数据缩放 */
    dataZoom?: {
      show?: boolean
      title?: string
      xAxisIndex?: number | number[]
      yAxisIndex?: number | number[]
    }
    /** 还原 */
    restore?: {
      show?: boolean
      title?: string
    }
    /** 动态类型切换 */
    magicType?: {
      show?: boolean
      type?: ('line' | 'bar' | 'stack')[]
      title?: Record<string, string>
    }
  }
  /** 位置 */
  left?: number | string
  top?: number | string
  right?: number | string
  bottom?: number | string
  /** 布局朝向 */
  orient?: 'horizontal' | 'vertical'
  /** 图标样式 */
  iconStyle?: ChartItemStyle
}

/** 动画配置 */
export interface ChartAnimation {
  /** 是否开启动画 */
  enabled?: boolean
  /** 动画阈值 */
  threshold?: number
  /** 初始动画时长 */
  duration?: number
  /** 数据更新动画时长 */
  durationUpdate?: number
  /** 缓动效果 */
  easing?: string
  /** 数据更新动画缓动效果 */
  easingUpdate?: string
  /** 延迟 */
  delay?: number | ((idx: number) => number)
  /** 数据更新动画延迟 */
  delayUpdate?: number | ((idx: number) => number)
}

/** 完整图表配置 */
export interface ChartOption {
  /** 图表标题 */
  title?: ChartTitle
  /** 图例 */
  legend?: Legend
  /** 网格 */
  grid?: ChartGrid | ChartGrid[]
  /** X轴 */
  xAxis?: XAxis | XAxis[]
  /** Y轴 */
  yAxis?: YAxis | YAxis[]
  /** 数据系列 */
  series: ChartSeries[]
  /** 提示框 */
  tooltip?: Tooltip
  /** 数据缩放 */
  dataZoom?: DataZoom | DataZoom[]
  /** 工具箱 */
  toolbox?: ChartToolbox
  /** 颜色列表 */
  color?: string[]
  /** 背景色 */
  backgroundColor?: string
  /** 动画配置 */
  animation?: ChartAnimation
  /** 是否渲染模式 */
  renderer?: 'canvas' | 'svg'
}

// ==================== 图表工具栏类型 ====================

/** 工具栏按钮配置 */
export interface ChartToolbarButton {
  /** 按钮唯一标识 */
  id: string
  /** 按钮图标 */
  icon: string
  /** 按钮文本 */
  label?: string
  /** 是否激活 */
  active?: boolean
  /** 是否禁用 */
  disabled?: boolean
  /** 点击回调 */
  handler: () => void
}

/** 图表工具栏配置 */
export interface ChartToolbarConfig {
  /** 是否显示 */
  show?: boolean
  /** 位置 */
  position?: 'top' | 'bottom' | 'left' | 'right'
  /** 按钮列表 */
  buttons: ChartToolbarButton[]
  /** 是否显示标签 */
  showLabel?: boolean
}

// ==================== 图表实例类型 ====================

/** 图表实例接口 */
export interface ChartInstance {
  /** 图表ID */
  id: ID
  /** 图表类型 */
  type: ChartType
  /** 图表配置 */
  option: ChartOption
  /** 图表尺寸 */
  size?: ChartSize
  /** 图表主题 */
  theme?: ChartTheme
  /** 是否已渲染 */
  rendered?: boolean
  /** 渲染时间 */
  renderTime?: number
}

/** 图表数据源 */
export interface ChartDataSource {
  /** 数据源ID */
  id: ID
  /** 数据源名称 */
  name: string
  /** 数据源类型 */
  type: 'api' | 'websocket' | 'static' | 'file'
  /** 数据源URL */
  url?: string
  /** 数据 */
  data?: unknown
  /** 刷新间隔 (ms) */
  refreshInterval?: number
  /** 最后更新时间 */
  lastUpdate?: string
}

// ==================== 图表导出类型 ====================

/** 图表导出配置 */
export interface ChartExportConfig {
  /** 导出类型 */
  type: 'png' | 'jpeg' | 'svg' | 'pdf'
  /** 文件名 */
  fileName?: string
  /** 像素比 */
  pixelRatio?: number
  /** 背景色 */
  backgroundColor?: string
  /** 图片宽度 */
  width?: number
  /** 图片高度 */
  height?: number
}

/** 图表导出结果 */
export interface ChartExportResult {
  /** 是否成功 */
  success: boolean
  /** 文件URL */
  url?: string
  /** 文件大小 (bytes) */
  size?: number
  /** 错误消息 */
  errorMessage?: string
}
