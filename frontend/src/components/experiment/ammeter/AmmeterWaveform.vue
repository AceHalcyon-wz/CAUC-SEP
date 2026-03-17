<template>
  <div class="ammeter-waveform">
    <!-- 波形控制工具栏 -->
    <div class="waveform-toolbar">
      <div class="toolbar-left">
        <div class="channel-selector">
          <span class="selector-label">显示通道:</span>
          <el-checkbox-group
            v-model="visibleChannels"
            size="small"
          >
            <el-checkbox-button
              v-for="channel in channelList"
              :key="channel.id"
              :label="channel.id"
              :disabled="!channel.enabled"
            >
              <span
                class="channel-dot"
                :style="{ background: channel.color }"
              />
              通道 {{ channel.id }}
            </el-checkbox-button>
          </el-checkbox-group>
        </div>
      </div>

      <div class="toolbar-right">
        <div class="display-mode">
          <el-radio-group
            v-model="displayMode"
            size="small"
          >
            <el-radio-button label="overlay">
              叠加显示
            </el-radio-button>
            <el-radio-button label="separate">
              分离显示
            </el-radio-button>
          </el-radio-group>
        </div>

        <div class="zoom-controls">
          <el-button-group>
            <el-button
              size="small"
              :disabled="zoomLevel >= maxZoom"
              @click="zoomIn"
            >
              <el-icon><ZoomIn /></el-icon>
            </el-button>
            <el-button
              size="small"
              :disabled="zoomLevel <= minZoom"
              @click="zoomOut"
            >
              <el-icon><ZoomOut /></el-icon>
            </el-button>
            <el-button
              size="small"
              @click="resetZoom"
            >
              <el-icon><RefreshRight /></el-icon>
            </el-button>
          </el-button-group>
          <span class="zoom-level">{{ Math.round(zoomLevel * 100) }}%</span>
        </div>

        <div class="time-range">
          <span class="range-label">时间范围:</span>
          <el-select
            v-model="timeRange"
            size="small"
            @change="handleTimeRangeChange"
          >
            <el-option
              label="10秒"
              :value="10"
            />
            <el-option
              label="30秒"
              :value="30"
            />
            <el-option
              label="1分钟"
              :value="60"
            />
            <el-option
              label="5分钟"
              :value="300"
            />
          </el-select>
        </div>
      </div>
    </div>

    <!-- 波形图表容器 -->
    <div class="waveform-container">
      <div
        ref="chartContainer"
        class="chart-wrapper"
      />
      
      <!-- 波形信息提示 -->
      <div
        v-if="hoverData"
        class="waveform-tooltip"
        :style="tooltipStyle"
      >
        <div class="tooltip-time">
          {{ hoverData.time }}
        </div>
        <div
          v-for="item in hoverData.values"
          :key="item.channel"
          class="tooltip-item"
        >
          <span
            class="tooltip-dot"
            :style="{ background: item.color }"
          />
          <span class="tooltip-label">通道 {{ item.channel }}:</span>
          <span class="tooltip-value">{{ formatCurrent(item.value) }}</span>
        </div>
      </div>
    </div>

    <!-- 波形统计信息 -->
    <div class="waveform-stats">
      <div
        v-for="channel in activeChannels"
        :key="channel.id"
        class="stat-item"
      >
        <div class="stat-header">
          <span
            class="channel-dot"
            :style="{ background: channel.color }"
          />
          <span class="channel-name">通道 {{ channel.id }}</span>
        </div>
        <div class="stat-values">
          <div class="stat-value">
            <span class="stat-label">最大值</span>
            <span class="stat-number">{{ formatCurrent(channel.stats?.max ?? 0) }}</span>
          </div>
          <div class="stat-value">
            <span class="stat-label">最小值</span>
            <span class="stat-number">{{ formatCurrent(channel.stats?.min ?? 0) }}</span>
          </div>
          <div class="stat-value">
            <span class="stat-label">平均值</span>
            <span class="stat-number">{{ formatCurrent(channel.stats?.avg ?? 0) }}</span>
          </div>
          <div class="stat-value">
            <span class="stat-label">标准差</span>
            <span class="stat-number">{{ formatCurrent(channel.stats?.std ?? 0) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * @file AmmeterWaveform.vue
 * @path src/components/
 * @description 微电流多通道波形显示组件，支持实时波形、缩放、叠加/分离显示
 * @author Agent
 * @date 2024-03-07
 * @dependencies vue, element-plus, echarts
 */

import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'

// ============ Props 定义 ============

const props = defineProps({
  /** 实时数据数组 */
  data: {
    type: Array,
    default: () => []
  },
  /** 通道配置 */
  channelConfig: {
    type: Object,
    default: () => ({})
  },
  /** 通道数量 */
  channelCount: {
    type: Number,
    default: 4
  },
  /** 是否自动更新 */
  autoUpdate: {
    type: Boolean,
    default: true
  },
  /** 更新间隔（毫秒） */
  updateInterval: {
    type: Number,
    default: 200
  }
})

// ============ Emits 定义 ============

const emit = defineEmits(['zoom-change', 'channel-toggle', 'display-mode-change'])

// ============ 常量定义 ============

/** 通道颜色配置 */
const CHANNEL_COLORS = [
  '#3B82F6', // 蓝色
  '#10B981', // 绿色
  '#F59E0B', // 黄色
  '#EF4444'  // 红色
]

/** 缩放限制 */
const minZoom = 0.5
const maxZoom = 5.0
const zoomStep = 0.2

// ============ 响应式状态 ============

/** 图表容器引用 */
const chartContainer = ref(null)

/** 图表实例 */
let chartInstance = null

/** 可见通道列表 */
const visibleChannels = ref([1, 2, 3, 4])

/** 显示模式：overlay(叠加) / separate(分离) */
const displayMode = ref('overlay')

/** 缩放级别 */
const zoomLevel = ref(1.0)

/** 时间范围（秒） */
const timeRange = ref(60)

/** 悬停数据 */
const hoverData = ref(null)

/** 提示框样式 */
const tooltipStyle = ref({})

/** 更新定时器 */
let updateTimer = null

// ============ 计算属性 ============

/**
 * 通道列表（包含颜色和启用状态）
 */
const channelList = computed(() => {
  return Array.from({ length: props.channelCount }, (_, i) => {
    const id = i + 1
    return {
      id,
      color: CHANNEL_COLORS[i % CHANNEL_COLORS.length],
      enabled: props.channelConfig[id]?.enabled ?? true
    }
  })
})

/**
 * 活动通道（已启用且可见）
 */
const activeChannels = computed(() => {
  return channelList.value.filter(ch => 
    visibleChannels.value.includes(ch.id) && ch.enabled
  )
})

/**
 * 计算各通道统计数据
 */
const channelStats = computed(() => {
  const stats = {}
  
  activeChannels.value.forEach(channel => {
    const values = props.data
      .filter(d => d[channel.id] !== undefined)
      .map(d => d[channel.id])
    
    if (values.length > 0) {
      const sum = values.reduce((a, b) => a + b, 0)
      const avg = sum / values.length
      const max = Math.max(...values)
      const min = Math.min(...values)
      const variance = values.reduce((acc, val) => acc + Math.pow(val - avg, 2), 0) / values.length
      const std = Math.sqrt(variance)
      
      stats[channel.id] = {
        max,
        min,
        avg,
        std,
        count: values.length
      }
    } else {
      stats[channel.id] = {
        max: 0,
        min: 0,
        avg: 0,
        std: 0,
        count: 0
      }
    }
  })
  
  return stats
})

/**
 * 增强的活动通道数据（包含统计信息）
 */
const activeChannelsWithStats = computed(() => {
  return activeChannels.value.map(channel => ({
    ...channel,
    stats: channelStats.value[channel.id] || {
      max: 0,
      min: 0,
      avg: 0,
      std: 0,
      count: 0
    }
  }))
})

// ============ 方法 ============

/**
 * 格式化电流值显示
 * 
 * @param {number} value - 电流值（单位：μA）
 * @returns {string} 格式化后的字符串
 */
function formatCurrent(value) {
  if (value === undefined || value === null) return '0 nA'
  
  const absValue = Math.abs(value)
  
  if (absValue < 0.001) {
    return (value * 1000).toFixed(3) + ' nA'
  } else if (absValue < 1) {
    return value.toFixed(4) + ' μA'
  } else if (absValue < 1000) {
    return value.toFixed(3) + ' μA'
  } else {
    return (value / 1000).toFixed(3) + ' mA'
  }
}

/**
 * 初始化图表
 */
function initChart() {
  if (!chartContainer.value) return

  // 销毁旧图表实例
  if (chartInstance) {
    chartInstance.dispose()
  }

  // 创建新图表实例
  chartInstance = echarts.init(chartContainer.value)

  // 设置图表配置
  const option = {
    backgroundColor: 'transparent',
    animation: false,
    grid: {
      left: '60px',
      right: '40px',
      top: '40px',
      bottom: '60px'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        lineStyle: {
          color: '#999'
        }
      },
      formatter: handleTooltipFormat
    },
    axisPointer: {
      link: [{ xAxisIndex: 'all' }],
      label: {
        backgroundColor: '#777'
      }
    },
    xAxis: displayMode.value === 'separate' ? [] : {
      type: 'category',
      boundaryGap: false,
      data: [],
      axisLine: {
        lineStyle: {
          color: '#666'
        }
      },
      axisLabel: {
        color: '#999',
        fontSize: 11
      }
    },
    yAxis: displayMode.value === 'separate' ? [] : {
      type: 'value',
      name: '电流 (μA)',
      nameTextStyle: {
        color: '#999',
        fontSize: 12
      },
      axisLabel: {
        formatter: (value) => {
          if (Math.abs(value) < 0.001) {
            return (value * 1000).toFixed(1) + ' nA'
          } else if (Math.abs(value) < 1) {
            return value.toFixed(3) + ' μA'
          } else {
            return value.toFixed(1) + ' μA'
          }
        },
        color: '#999',
        fontSize: 11
      },
      axisLine: {
        lineStyle: {
          color: '#666'
        }
      },
      splitLine: {
        lineStyle: {
          color: '#333',
          type: 'dashed'
        }
      }
    },
    series: []
  }

  chartInstance.setOption(option)

  // 绑定事件
  chartInstance.on('mousemove', handleMouseMove)
  chartInstance.on('mouseout', handleMouseOut)
}

/**
 * 更新图表数据
 */
function updateChart() {
  if (!chartInstance || props.data.length === 0) return

  // 过滤时间范围内的数据
  const now = Date.now()
  const startTime = now - timeRange.value * 1000
  const filteredData = props.data.filter(d => d.timestamp >= startTime)

  if (filteredData.length === 0) return

  // 生成时间轴数据
  const times = filteredData.map(d => {
    const date = new Date(d.timestamp)
    return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`
  })

  if (displayMode.value === 'overlay') {
    updateOverlayChart(filteredData, times)
  } else {
    updateSeparateChart(filteredData, times)
  }
}

/**
 * 更新叠加显示图表
 * 
 * @param {Array} data - 过滤后的数据
 * @param {Array} times - 时间轴数据
 */
function updateOverlayChart(data, times) {
  const series = activeChannels.value.map(channel => {
    const channelData = data.map(d => d[channel.id] || 0)
    
    return {
      name: `通道 ${channel.id}`,
      type: 'line',
      data: channelData,
      smooth: true,
      symbol: 'none',
      lineStyle: {
        color: channel.color,
        width: 2
      },
      itemStyle: {
        color: channel.color
      },
      emphasis: {
        focus: 'series'
      }
    }
  })

  chartInstance.setOption({
    xAxis: {
      data: times
    },
    yAxis: {
      min: (value) => value?.min ? value.min * 0.95 : 0,
      max: (value) => value?.max ? value.max * 1.05 : 1
    },
    series
  })
}

/**
 * 更新分离显示图表
 * 
 * @param {Array} data - 过滤后的数据
 * @param {Array} times - 时间轴数据
 */
function updateSeparateChart(data, times) {
  const activeCount = activeChannels.value.length
  
  // 构建多个grid和对应的x/y轴
  const grids = []
  const xAxes = []
  const yAxes = []
  const series = []

  activeChannels.value.forEach((channel, index) => {
    // 计算grid位置
    const top = 40 + index * (100 / activeCount) + '%'
    const height = (100 / activeCount - 5) + '%'

    grids.push({
      left: '60px',
      right: '40px',
      top,
      height
    })

    // X轴
    xAxes.push({
      type: 'category',
      gridIndex: index,
      boundaryGap: false,
      data: times,
      axisLine: {
        lineStyle: { color: '#666' }
      },
      axisLabel: {
        color: '#999',
        fontSize: 10,
        show: index === activeCount - 1
      },
      splitLine: {
        show: false
      }
    })

    // Y轴
    yAxes.push({
      type: 'value',
      gridIndex: index,
      name: `通道${channel.id}`,
      nameTextStyle: {
        color: channel.color,
        fontSize: 11
      },
      axisLabel: {
        formatter: (value) => {
          if (Math.abs(value) < 0.001) {
            return (value * 1000).toFixed(1) + ' nA'
          } else if (Math.abs(value) < 1) {
            return value.toFixed(3) + ' μA'
          } else {
            return value.toFixed(1) + ' μA'
          }
        },
        color: '#999',
        fontSize: 10
      },
      axisLine: {
        lineStyle: { color: '#666' }
      },
      splitLine: {
        lineStyle: {
          color: '#333',
          type: 'dashed'
        }
      }
    })

    // 数据系列
    const channelData = data.map(d => d[channel.id] || 0)
    
    series.push({
      name: `通道 ${channel.id}`,
      type: 'line',
      xAxisIndex: index,
      yAxisIndex: index,
      data: channelData,
      smooth: true,
      symbol: 'none',
      lineStyle: {
        color: channel.color,
        width: 2
      },
      itemStyle: {
        color: channel.color
      }
    })
  })

  chartInstance.setOption({
    grid: grids,
    xAxis: xAxes,
    yAxis: yAxes,
    series
  })
}

/**
 * 处理工具提示格式化
 * 
 * @param {Array} params - ECharts tooltip参数
 * @returns {string} 格式化后的HTML字符串
 */
function handleTooltipFormat(params) {
  if (!params || params.length === 0) return ''
  
  let html = `<div style="font-size: 12px; padding: 4px 8px;">
    <div style="font-weight: bold; margin-bottom: 4px;">${params[0].axisValue}</div>`
  
  params.forEach(param => {
    html += `<div style="display: flex; align-items: center; margin: 2px 0;">
      <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: ${param.color}; margin-right: 6px;"></span>
      <span style="flex: 1;">${param.seriesName}:</span>
      <span style="font-weight: bold; margin-left: 8px;">${formatCurrent(param.value)}</span>
    </div>`
  })
  
  html += '</div>'
  return html
}

/**
 * 鼠标移动处理
 * 
 * @param {Object} params - 事件参数
 */
function handleMouseMove(params) {
  if (!params || params.data === undefined) return
  
  const { offsetX, offsetY } = params.event.event
  
  hoverData.value = {
    time: params.name,
    values: []
  }
  
  // 收集所有通道数据
  if (displayMode.value === 'overlay') {
    activeChannels.value.forEach(channel => {
      const dataIndex = params.dataIndex
      if (props.data[dataIndex]) {
        hoverData.value.values.push({
          channel: channel.id,
          value: props.data[dataIndex][channel.id] || 0,
          color: channel.color
        })
      }
    })
  }
  
  // 设置提示框位置
  tooltipStyle.value = {
    left: `${offsetX + 20}px`,
    top: `${offsetY - 20}px`
  }
}

/**
 * 鼠标移出处理
 */
function handleMouseOut() {
  hoverData.value = null
}

/**
 * 放大波形
 */
function zoomIn() {
  if (zoomLevel.value < maxZoom) {
    zoomLevel.value = Math.min(zoomLevel.value + zoomStep, maxZoom)
    applyZoom()
    emit('zoom-change', zoomLevel.value)
  }
}

/**
 * 缩小波形
 */
function zoomOut() {
  if (zoomLevel.value > minZoom) {
    zoomLevel.value = Math.max(zoomLevel.value - zoomStep, minZoom)
    applyZoom()
    emit('zoom-change', zoomLevel.value)
  }
}

/**
 * 重置缩放
 */
function resetZoom() {
  zoomLevel.value = 1.0
  applyZoom()
  emit('zoom-change', zoomLevel.value)
}

/**
 * 应用缩放
 */
function applyZoom() {
  if (!chartInstance) return
  
  // 使用ECharts的dataZoom功能
  chartInstance.dispatchAction({
    type: 'dataZoom',
    start: 0,
    end: 100 / zoomLevel.value
  })
}

/**
 * 处理时间范围变化
 * 
 * @param {number} value - 新的时间范围（秒）
 */
function handleTimeRangeChange(value) {
  updateChart()
}

/**
 * 开始自动更新
 */
function startAutoUpdate() {
  stopAutoUpdate()
  
  updateTimer = setInterval(() => {
    updateChart()
  }, props.updateInterval)
}

/**
 * 停止自动更新
 */
function stopAutoUpdate() {
  if (updateTimer) {
    clearInterval(updateTimer)
    updateTimer = null
  }
}

/**
 * 调整图表大小
 */
function resizeChart() {
  if (chartInstance) {
    chartInstance.resize()
  }
}

// ============ 监听器 ============

// 监听数据变化
watch(() => props.data, () => {
  if (props.autoUpdate) {
    updateChart()
  }
}, { deep: true })

// 监听可见通道变化
watch(visibleChannels, () => {
  updateChart()
  emit('channel-toggle', visibleChannels.value)
}, { deep: true })

// 监听显示模式变化
watch(displayMode, () => {
  nextTick(() => {
    initChart()
    updateChart()
    emit('display-mode-change', displayMode.value)
  })
})

// 监听自动更新状态
watch(() => props.autoUpdate, (newVal) => {
  if (newVal) {
    startAutoUpdate()
  } else {
    stopAutoUpdate()
  }
})

// ============ 生命周期钩子 ============

onMounted(() => {
  nextTick(() => {
    initChart()
    updateChart()
    
    if (props.autoUpdate) {
      startAutoUpdate()
    }
  })
  
  // 监听窗口大小变化
  window.addEventListener('resize', resizeChart)
})

onBeforeUnmount(() => {
  stopAutoUpdate()
  
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  
  window.removeEventListener('resize', resizeChart)
})

// ============ 暴露方法 ============

defineExpose({
  updateChart,
  resizeChart,
  zoomIn,
  zoomOut,
  resetZoom
})
</script>

<style scoped>
.ammeter-waveform {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--color-surface-primary);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

/* 工具栏 */
.waveform-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-3) var(--spacing-4);
  background: var(--color-surface-secondary);
  border-bottom: 1px solid var(--color-border-primary);
  gap: var(--spacing-4);
  flex-wrap: wrap;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
}

.channel-selector {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.selector-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

.channel-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  margin-right: var(--spacing-1);
}

.display-mode {
  display: flex;
  align-items: center;
}

.zoom-controls {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.zoom-level {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-family: var(--font-family-mono);
  min-width: 40px;
}

.time-range {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.range-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

/* 波形容器 */
.waveform-container {
  flex: 1;
  position: relative;
  min-height: 400px;
  padding: var(--spacing-4);
}

.chart-wrapper {
  width: 100%;
  height: 100%;
  min-height: 400px;
}

/* 波形提示框 */
.waveform-tooltip {
  position: absolute;
  background: rgba(0, 0, 0, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-md);
  padding: var(--spacing-2) var(--spacing-3);
  pointer-events: none;
  z-index: 1000;
  box-shadow: var(--shadow-lg);
}

.tooltip-time {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: #fff;
  margin-bottom: var(--spacing-2);
  padding-bottom: var(--spacing-1);
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}

.tooltip-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: var(--font-size-xs);
  color: #e0e0e0;
  margin: var(--spacing-1) 0;
}

.tooltip-dot {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
}

.tooltip-label {
  flex: 1;
}

.tooltip-value {
  font-weight: var(--font-weight-semibold);
  font-family: var(--font-family-mono);
  color: #fff;
}

/* 统计信息 */
.waveform-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--spacing-3);
  padding: var(--spacing-4);
  background: var(--color-surface-secondary);
  border-top: 1px solid var(--color-border-primary);
}

.stat-item {
  background: var(--color-surface-primary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  padding: var(--spacing-3);
}

.stat-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-2);
  padding-bottom: var(--spacing-2);
  border-bottom: 1px solid var(--color-border-primary);
}

.channel-name {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.stat-values {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-2);
}

.stat-value {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.stat-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.stat-number {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  font-family: var(--font-family-mono);
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .waveform-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .toolbar-left,
  .toolbar-right {
    justify-content: space-between;
  }
}

@media (max-width: 768px) {
  .waveform-stats {
    grid-template-columns: 1fr;
  }
  
  .stat-values {
    grid-template-columns: 1fr;
  }
}
</style>
