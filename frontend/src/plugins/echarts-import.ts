/**
 * @file echarts-import.ts
 * @path frontend/src/plugins/echarts-import.ts
 * @description ECharts按需引入配置，优化打包体积
 * @author Agent
 * @date 2026-03-25
 * @dependencies echarts
 */

import * as echarts from 'echarts/core'

// 引入图表类型
import {
  BarChart,
  LineChart,
  PieChart,
  ScatterChart,
  RadarChart,
  GaugeChart,
  HeatmapChart
} from 'echarts/charts'

// 引入组件
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DatasetComponent,
  TransformComponent,
  ToolboxComponent,
  DataZoomComponent,
  VisualMapComponent,
  MarkPointComponent,
  MarkLineComponent
} from 'echarts/components'

// 引入渲染器
import { CanvasRenderer } from 'echarts/renderers'

// 注册组件
echarts.use([
  // 图表类型
  BarChart,
  LineChart,
  PieChart,
  ScatterChart,
  RadarChart,
  GaugeChart,
  HeatmapChart,
  
  // 组件
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DatasetComponent,
  TransformComponent,
  ToolboxComponent,
  DataZoomComponent,
  VisualMapComponent,
  MarkPointComponent,
  MarkLineComponent,
  
  // 渲染器
  CanvasRenderer
])

/**
 * 创建ECharts实例
 * 
 * @param dom - DOM元素
 * @param theme - 主题
 * @param opts - 配置选项
 * @returns ECharts实例
 */
export function createChart(
  dom: HTMLElement,
  theme?: string | object,
  opts?: {
    devicePixelRatio?: number
    renderer?: 'canvas' | 'svg'
    width?: number | 'auto'
    height?: number | 'auto'
    locale?: string
  }
) {
  return echarts.init(dom, theme, {
    renderer: 'canvas',
    devicePixelRatio: window.devicePixelRatio || 1,
    ...opts
  })
}

/**
 * 响应式图表尺寸调整
 * 
 * @param chart - ECharts实例
 * @param options - 配置选项
 * @returns 清理函数
 */
export function useChartResize(
  chart: echarts.ECharts,
  options: {
    debounce?: number
    container?: HTMLElement | null
  } = {}
) {
  const { debounce: debounceTime = 300, container = null } = options
  
  let resizeTimer: number | null = null
  
  const handleResize = () => {
    if (resizeTimer) {
      clearTimeout(resizeTimer)
    }
    
    resizeTimer = window.setTimeout(() => {
      if (chart && !chart.isDisposed()) {
        chart.resize()
      }
    }, debounceTime)
  }
  
  // 监听窗口大小变化
  window.addEventListener('resize', handleResize)
  
  // 监听容器大小变化（如果提供了容器）
  let resizeObserver: ResizeObserver | null = null
  if (container && typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(handleResize)
    resizeObserver.observe(container)
  }
  
  // 返回清理函数
  return () => {
    window.removeEventListener('resize', handleResize)
    if (resizeTimer) {
      clearTimeout(resizeTimer)
    }
    if (resizeObserver) {
      resizeObserver.disconnect()
    }
  }
}

/**
 * 销毁ECharts实例
 * 
 * @param chart - ECharts实例
 */
export function disposeChart(chart: echarts.ECharts | null) {
  if (chart && !chart.isDisposed()) {
    chart.dispose()
  }
}

export { echarts }
export default echarts
