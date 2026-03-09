<template>
  <div class="temperature-curve">
    <!-- 图表控制栏 -->
    <div class="curve-header">
      <div class="header-left">
        <h3 class="curve-title">温度曲线实时监控</h3>
        <div class="curve-stats">
          <div class="stat-item">
            <span class="stat-label">当前温度:</span>
            <span class="stat-value mono">{{ currentTempDisplay }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">目标温度:</span>
            <span class="stat-value mono">{{ targetTempDisplay }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">变化率:</span>
            <span class="stat-value mono" :class="rateClass">{{ heatingRateDisplay }}</span>
          </div>
        </div>
      </div>
      <div class="header-right">
        <el-button-group class="time-range-group">
          <el-button
            v-for="range in timeRanges"
            :key="range.value"
            :type="selectedTimeRange === range.value ? 'primary' : ''"
            size="small"
            @click="handleTimeRangeChange(range.value)"
          >
            {{ range.label }}
          </el-button>
        </el-button-group>
        <el-button
          size="small"
          :icon="isAutoRefresh ? 'VideoPause' : 'VideoPlay'"
          @click="toggleAutoRefresh"
        >
          {{ isAutoRefresh ? '暂停' : '播放' }}
        </el-button>
        <el-button size="small" @click="handleExportChart">
          <el-icon><Download /></el-icon>
          导出
        </el-button>
      </div>
    </div>

    <!-- 主图表区域 -->
    <div class="chart-wrapper">
      <v-chart
        ref="mainChart"
        :option="chartOption"
        :autoresize="true"
        class="main-chart"
        @datazoom="handleDataZoom"
      />
      
      <!-- 温度变化率指示器 -->
      <div class="rate-indicator" :class="rateIndicatorClass">
        <div class="rate-arrow">
          <el-icon v-if="heatingRate > 0.1"><Top /></el-icon>
          <el-icon v-else-if="heatingRate < -0.1"><Bottom /></el-icon>
          <el-icon v-else><Minus /></el-icon>
        </div>
        <div class="rate-value">
          <span class="rate-number mono">{{ Math.abs(heatingRate).toFixed(2) }}</span>
          <span class="rate-unit">K/s</span>
        </div>
        <div class="rate-label">{{ rateLabel }}</div>
      </div>
    </div>

    <!-- 历史数据查看面板 -->
    <div v-if="showHistoryPanel" class="history-panel">
      <div class="panel-header">
        <h4 class="panel-title">历史数据查看</h4>
        <el-button text @click="showHistoryPanel = false">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
      <div class="history-controls">
        <el-date-picker
          v-model="historyDateRange"
          type="datetimerange"
          range-separator="至"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          size="small"
          @change="handleHistoryDateChange"
        />
        <el-button size="small" type="primary" @click="handleFetchHistory">
          查询
        </el-button>
      </div>
      <div class="history-stats">
        <el-statistic title="数据点数" :value="historyData.length" />
        <el-statistic title="最高温度" :value="historyMaxTemp" suffix="K" />
        <el-statistic title="最低温度" :value="historyMinTemp" suffix="K" />
        <el-statistic title="平均温度" :value="historyAvgTemp" suffix="K" />
      </div>
    </div>

    <!-- 目标温度线标记 -->
    <div class="target-line-marker">
      <div class="marker-line" :style="{ top: targetLinePosition }"></div>
      <div class="marker-label" :style="{ top: targetLinePosition }">
        目标: {{ targetTempDisplay }}
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * @file TemperatureCurve.vue
 * @path src/components/
 * @description 温度曲线实时绘制组件，提供实时温度监控、历史数据查看等功能
 * @author Agent
 * @date 2024-03-07
 */

import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useTemperatureStore } from '../stores/temperature'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, ScatterChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
  MarkLineComponent,
  MarkPointComponent
} from 'echarts/components'
import VChart from 'vue-echarts'
import { ElMessage } from 'element-plus'

// 注册 ECharts 组件
use([
  CanvasRenderer,
  LineChart,
  ScatterChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
  MarkLineComponent,
  MarkPointComponent
])

// ============ Store ============
const tempStore = useTemperatureStore()

// ============ Refs ============
const mainChart = ref(null)
const showHistoryPanel = ref(false)
const historyDateRange = ref([])
const historyData = ref([])
const selectedTimeRange = ref('5m')
const isAutoRefresh = ref(true)
const chartData = ref([])
const maxDataPoints = 600

// ============ 时间范围选项 ============
const timeRanges = [
  { label: '1分钟', value: '1m' },
  { label: '5分钟', value: '5m' },
  { label: '15分钟', value: '15m' },
  { label: '30分钟', value: '30m' },
  { label: '1小时', value: '1h' }
]

// ============ 计算属性 ============

/** 当前温度显示 */
const currentTempDisplay = computed(() => {
  return `${tempStore.currentTemp.toFixed(2)}K (${tempStore.kelvinToCelsius(tempStore.currentTemp).toFixed(1)}°C)`
})

/** 目标温度显示 */
const targetTempDisplay = computed(() => {
  return `${tempStore.targetTemp.toFixed(2)}K (${tempStore.kelvinToCelsius(tempStore.targetTemp).toFixed(1)}°C)`
})

/** 升温速率显示 */
const heatingRateDisplay = computed(() => {
  const rate = tempStore.heatingRate
  const sign = rate > 0 ? '+' : ''
  return `${sign}${rate.toFixed(3)} K/s`
})

/** 升温速率样式类 */
const rateClass = computed(() => {
  const rate = tempStore.heatingRate
  if (rate > 0.5) return 'rate-heating'
  if (rate < -0.5) return 'rate-cooling'
  return 'rate-stable'
})

/** 升温速率指示器样式类 */
const rateIndicatorClass = computed(() => {
  const rate = tempStore.heatingRate
  if (rate > 0.5) return 'indicator-heating'
  if (rate < -0.5) return 'indicator-cooling'
  return 'indicator-stable'
})

/** 升温速率标签 */
const rateLabel = computed(() => {
  const rate = tempStore.heatingRate
  if (rate > 0.5) return '快速升温'
  if (rate > 0.1) return '升温中'
  if (rate < -0.5) return '快速降温'
  if (rate < -0.1) return '降温中'
  return '温度稳定'
})

/** 目标温度线位置（百分比） */
const targetLinePosition = computed(() => {
  const minTemp = tempStore.tempLimits.min
  const maxTemp = tempStore.tempLimits.max
  const targetTemp = tempStore.targetTemp
  const percentage = ((maxTemp - targetTemp) / (maxTemp - minTemp)) * 100
  return `${Math.max(0, Math.min(100, percentage))}%`
})

/** 历史数据统计 */
const historyMaxTemp = computed(() => {
  if (historyData.value.length === 0) return 0
  return Math.max(...historyData.value.map(d => d.current))
})

const historyMinTemp = computed(() => {
  if (historyData.value.length === 0) return 0
  return Math.min(...historyData.value.map(d => d.current))
})

const historyAvgTemp = computed(() => {
  if (historyData.value.length === 0) return 0
  const sum = historyData.value.reduce((acc, d) => acc + d.current, 0)
  return (sum / historyData.value.length).toFixed(2)
})

/** 图表配置 */
const chartOption = computed(() => {
  const data = chartData.value
  const currentData = data.map(item => [item.timestamp, item.current])
  const targetData = data.map(item => [item.timestamp, item.target])

  return {
    title: {
      show: false
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        crossStyle: {
          color: 'var(--color-neutral-400)'
        }
      },
      backgroundColor: 'var(--color-surface-elevated)',
      borderColor: 'var(--color-border-primary)',
      borderWidth: 1,
      textStyle: {
        color: 'var(--color-text-primary)',
        fontFamily: 'var(--font-family-mono)'
      },
      formatter: (params) => {
        const time = new Date(params[0].value[0]).toLocaleTimeString()
        let result = `<div style="font-weight: 600; margin-bottom: 8px;">${time}</div>`
        
        params.forEach(param => {
          const tempK = param.value[1]
          const tempC = tempStore.kelvinToCelsius(tempK)
          const color = param.seriesName === '当前温度' ? 'var(--color-data-cyan)' : 'var(--color-data-orange)'
          result += `
            <div style="display: flex; align-items: center; gap: 8px; margin: 4px 0;">
              <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: ${color};"></span>
              <span>${param.seriesName}: <span style="font-family: var(--font-family-mono); font-weight: 600;">${tempK.toFixed(2)}K</span></span>
              <span style="color: var(--color-text-tertiary);">(${tempC.toFixed(1)}°C)</span>
            </div>
          `
        })
        
        return result
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'time',
      splitLine: {
        show: false
      },
      axisLine: {
        lineStyle: {
          color: 'var(--color-border-primary)'
        }
      },
      axisLabel: {
        color: 'var(--color-text-secondary)',
        fontFamily: 'var(--font-family-mono)',
        formatter: (value) => {
          const date = new Date(value)
          return `${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`
        }
      }
    },
    yAxis: {
      type: 'value',
      name: '温度 (K)',
      nameTextStyle: {
        color: 'var(--color-text-secondary)',
        fontFamily: 'var(--font-family-sans)'
      },
      min: tempStore.tempLimits.min,
      max: tempStore.tempLimits.max,
      splitLine: {
        lineStyle: {
          color: 'var(--color-border-secondary)',
          type: 'dashed'
        }
      },
      axisLine: {
        show: false
      },
      axisLabel: {
        color: 'var(--color-text-secondary)',
        fontFamily: 'var(--font-family-mono)',
        formatter: (value) => value.toFixed(0)
      }
    },
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100
      },
      {
        type: 'slider',
        start: 0,
        end: 100,
        borderColor: 'var(--color-border-primary)',
        fillerColor: 'var(--color-interactive-selected)',
        handleStyle: {
          color: 'var(--color-primary-500)'
        },
        textStyle: {
          color: 'var(--color-text-secondary)'
        }
      }
    ],
    series: [
      {
        name: '当前温度',
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: {
          width: 2,
          color: 'var(--color-data-cyan)'
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(6, 182, 212, 0.3)' },
              { offset: 1, color: 'rgba(6, 182, 212, 0.02)' }
            ]
          }
        },
        data: currentData,
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: {
            type: 'dashed',
            color: 'var(--color-data-orange)',
            width: 2
          },
          label: {
            show: true,
            position: 'end',
            formatter: '目标温度',
            color: 'var(--color-data-orange)',
            fontFamily: 'var(--font-family-sans)'
          },
          data: [
            {
              yAxis: tempStore.targetTemp
            }
          ]
        },
        markPoint: {
          symbol: 'pin',
          symbolSize: 40,
          itemStyle: {
            color: 'var(--color-primary-500)'
          },
          data: [
            { type: 'max', name: '最大值' },
            { type: 'min', name: '最小值' }
          ],
          label: {
            show: true,
            position: 'inside',
            formatter: (params) => {
              return `${params.value.toFixed(1)}K`
            },
            color: '#fff',
            fontSize: 10
          }
        }
      },
      {
        name: '目标温度',
        type: 'line',
        smooth: false,
        symbol: 'none',
        lineStyle: {
          width: 1,
          color: 'var(--color-data-orange)',
          type: 'dashed'
        },
        data: targetData
      }
    ]
  }
})

// ============ 方法 ============

/**
 * 添加温度数据点
 * @param {Object} data - 温度数据
 */
function addDataPoint(data) {
  chartData.value.push({
    timestamp: data.timestamp || Date.now(),
    current: data.current,
    target: data.target,
    power: data.power
  })

  // 限制数据点数量
  if (chartData.value.length > maxDataPoints) {
    chartData.value = chartData.value.slice(-maxDataPoints)
  }
}

/**
 * 时间范围变化处理
 * @param {string} range - 时间范围
 */
function handleTimeRangeChange(range) {
  selectedTimeRange.value = range
  
  // 根据时间范围过滤数据
  const now = Date.now()
  let startTime
  
  switch (range) {
    case '1m':
      startTime = now - 60 * 1000
      break
    case '5m':
      startTime = now - 5 * 60 * 1000
      break
    case '15m':
      startTime = now - 15 * 60 * 1000
      break
    case '30m':
      startTime = now - 30 * 60 * 1000
      break
    case '1h':
      startTime = now - 60 * 60 * 1000
      break
    default:
      startTime = now - 5 * 60 * 1000
  }
  
  chartData.value = chartData.value.filter(item => item.timestamp >= startTime)
}

/**
 * 切换自动刷新
 */
function toggleAutoRefresh() {
  isAutoRefresh.value = !isAutoRefresh.value
  ElMessage.info(isAutoRefresh.value ? '已恢复实时更新' : '已暂停实时更新')
}

/**
 * 数据缩放处理
 * @param {Object} params - 缩放参数
 */
function handleDataZoom(params) {
  // 可以在这里添加自定义缩放逻辑
}

/**
 * 导出图表
 */
function handleExportChart() {
  if (mainChart.value) {
    const url = mainChart.value.getDataURL({
      type: 'png',
      pixelRatio: 2,
      backgroundColor: '#fff'
    })
    
    const link = document.createElement('a')
    link.download = `temperature_curve_${Date.now()}.png`
    link.href = url
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    ElMessage.success('图表已导出')
  }
}

/**
 * 历史日期范围变化
 */
function handleHistoryDateChange() {
  // 日期范围变化处理
}

/**
 * 获取历史数据
 */
async function handleFetchHistory() {
  if (!historyDateRange.value || historyDateRange.value.length !== 2) {
    ElMessage.warning('请选择时间范围')
    return
  }
  
  const [startTime, endTime] = historyDateRange.value
  const history = await tempStore.fetchTemperatureHistory({
    start_time: startTime.getTime(),
    end_time: endTime.getTime(),
    interval: 1
  })
  
  if (history && history.length > 0) {
    historyData.value = history
    chartData.value = history
    ElMessage.success(`已加载 ${history.length} 条历史数据`)
  } else {
    ElMessage.warning('未找到历史数据')
  }
}

// ============ 生命周期 ============

let updateTimer = null

onMounted(() => {
  // 初始化数据
  if (tempStore.tempHistory.length > 0) {
    chartData.value = [...tempStore.tempHistory]
  }
  
  // 监听温度数据更新
  watch(() => tempStore.currentTemp, (newTemp) => {
    if (isAutoRefresh.value) {
      addDataPoint({
        timestamp: Date.now(),
        current: newTemp,
        target: tempStore.targetTemp,
        power: tempStore.outputPower
      })
    }
  })
})

onUnmounted(() => {
  if (updateTimer) {
    clearInterval(updateTimer)
  }
})
</script>

<style scoped>
.temperature-curve {
  position: relative;
  width: 100%;
  background: var(--color-surface-primary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  overflow: hidden;
}

/* 头部控制栏 */
.curve-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: var(--spacing-4);
  border-bottom: 1px solid var(--color-border-primary);
  background: var(--color-surface-secondary);
}

.header-left {
  flex: 1;
}

.curve-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-2) 0;
}

.curve-stats {
  display: flex;
  gap: var(--spacing-4);
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.stat-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.stat-value {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.rate-heating {
  color: var(--color-error);
}

.rate-cooling {
  color: var(--color-primary-500);
}

.rate-stable {
  color: var(--color-success);
}

.header-right {
  display: flex;
  gap: var(--spacing-2);
  align-items: center;
}

.time-range-group {
  margin-right: var(--spacing-2);
}

/* 图表区域 */
.chart-wrapper {
  position: relative;
  padding: var(--spacing-4);
  min-height: 400px;
}

.main-chart {
  width: 100%;
  height: 400px;
}

/* 温度变化率指示器 */
.rate-indicator {
  position: absolute;
  right: var(--spacing-6);
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--spacing-3);
  border-radius: var(--radius-lg);
  background: var(--color-surface-elevated);
  border: 2px solid var(--color-border-primary);
  box-shadow: var(--shadow-lg);
  transition: var(--transition-all);
  z-index: 10;
}

.indicator-heating {
  border-color: var(--color-error);
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.1), transparent);
}

.indicator-cooling {
  border-color: var(--color-primary-500);
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), transparent);
}

.indicator-stable {
  border-color: var(--color-success);
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.1), transparent);
}

.rate-arrow {
  font-size: var(--font-size-2xl);
  margin-bottom: var(--spacing-1);
}

.indicator-heating .rate-arrow {
  color: var(--color-error);
  animation: bounce-up 1s ease-in-out infinite;
}

.indicator-cooling .rate-arrow {
  color: var(--color-primary-500);
  animation: bounce-down 1s ease-in-out infinite;
}

.indicator-stable .rate-arrow {
  color: var(--color-success);
}

.rate-value {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-1);
  margin-bottom: var(--spacing-1);
}

.rate-number {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
}

.rate-unit {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.rate-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  white-space: nowrap;
}

/* 历史数据面板 */
.history-panel {
  position: absolute;
  top: var(--spacing-4);
  right: var(--spacing-4);
  width: 320px;
  background: var(--color-surface-elevated);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  box-shadow: var(--shadow-xl);
  z-index: 20;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-3) var(--spacing-4);
  border-bottom: 1px solid var(--color-border-primary);
  background: var(--color-surface-secondary);
}

.panel-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.history-controls {
  display: flex;
  gap: var(--spacing-2);
  padding: var(--spacing-3) var(--spacing-4);
  border-bottom: 1px solid var(--color-border-primary);
}

.history-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-2);
  padding: var(--spacing-3) var(--spacing-4);
}

/* 目标温度线标记 */
.target-line-marker {
  position: absolute;
  left: 0;
  right: 0;
  top: var(--spacing-4);
  bottom: calc(var(--spacing-4) + 60px);
  pointer-events: none;
  z-index: 5;
}

.marker-line {
  position: absolute;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--color-data-orange);
  opacity: 0.5;
}

.marker-label {
  position: absolute;
  right: var(--spacing-4);
  padding: var(--spacing-1) var(--spacing-2);
  background: var(--color-data-orange);
  color: white;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  border-radius: var(--radius-sm);
  transform: translateY(-50%);
}

/* 动画 */
@keyframes bounce-up {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-4px);
  }
}

@keyframes bounce-down {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(4px);
  }
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .rate-indicator {
    right: var(--spacing-4);
    padding: var(--spacing-2);
  }
  
  .rate-number {
    font-size: var(--font-size-lg);
  }
}

@media (max-width: 768px) {
  .curve-header {
    flex-direction: column;
    gap: var(--spacing-3);
  }
  
  .header-right {
    width: 100%;
    flex-wrap: wrap;
  }
  
  .curve-stats {
    flex-direction: column;
    gap: var(--spacing-2);
  }
  
  .main-chart {
    height: 300px;
  }
  
  .rate-indicator {
    position: static;
    transform: none;
    margin: var(--spacing-3) auto;
    width: fit-content;
  }
  
  .history-panel {
    position: static;
    width: 100%;
    margin-top: var(--spacing-3);
  }
}
</style>
