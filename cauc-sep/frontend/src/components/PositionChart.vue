<template>
  <el-card class="position-chart">
    <template #header>
      <div class="card-header">
        <div class="header-title">
          <el-icon><TrendCharts /></el-icon>
          <span>位置曲线</span>
        </div>
        <el-button
          v-if="dataPoints.length > 0"
          type="danger"
          size="small"
          link
          @click="clearData"
        >
          清除
        </el-button>
      </div>
    </template>

    <div class="chart-content">
      <div
        ref="chartRef"
        class="chart-container"
      />
      
      <transition name="fade">
        <div
          v-if="dataPoints.length === 0"
          class="empty-state"
        >
          <el-icon :size="48">
            <TrendCharts />
          </el-icon>
          <p>等待数据...</p>
          <p class="hint">
            连接设备后将显示实时位置曲线
          </p>
        </div>
      </transition>
    </div>
  </el-card>
</template>

<script setup>
/**
 * @file PositionChart.vue
 * @path src/components/
 * @description 实时位置曲线图表组件，支持主题切换和动画效果
 * @author Agent
 * @date 2024-03-07
 */

import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useMotorStore } from '../stores/motor'
import * as echarts from 'echarts'

const motorStore = useMotorStore()
const chartRef = ref(null)
let chart = null

/** 数据点数组 */
const dataPoints = ref([])

/** 最大数据点数量 */
const maxPoints = 100

/**
 * 获取图表颜色配置
 * 返回图表使用的颜色方案
 */
function getChartThemeColors() {
  return {
    // 线条颜色
    lineColor: '#409eff',
    
    // 区域渐变
    areaGradientStart: 'rgba(64, 158, 255, 0.35)',
    areaGradientEnd: 'rgba(64, 158, 255, 0.05)',
    
    // 背景色
    backgroundColor: '#ffffff',
    
    // 文字颜色
    textPrimary: '#1a202c',
    textSecondary: '#4a5568',
    textTertiary: '#718096',
    
    // 坐标轴颜色
    axisLine: '#e2e8f0',
    splitLine: '#edf2f7',
    
    // 工具提示
    tooltipBg: '#ffffff',
    tooltipBorder: '#e2e8f0',
    tooltipText: '#1a202c',
    
    // 空状态颜色
    emptyIcon: '#dcdfe6',
    emptyText: '#909399',
    emptyHint: '#c0c4cc'
  }
}

/**
 * 初始化图表
 * 配置图表基础选项和主题样式
 */
function initChart() {
  if (!chartRef.value) return
  
  const themeColors = getChartThemeColors()
  
  chart = echarts.init(chartRef.value)
  
  const option = {
    backgroundColor: themeColors.backgroundColor,
    grid: {
      left: '10%',
      right: '5%',
      top: '10%',
      bottom: '15%'
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: themeColors.tooltipBg,
      borderColor: themeColors.tooltipBorder,
      borderWidth: 1,
      textStyle: {
        color: themeColors.tooltipText,
        fontSize: 13
      },
      formatter: (params) => {
        const data = params[0]
        return `<div style="padding: 4px 0;">
          <div style="margin-bottom: 4px; color: ${themeColors.textSecondary};">时间: ${data.axisValue}</div>
          <div style="font-family: var(--font-family-mono); font-weight: 600;">位置: ${data.value[1].toFixed(3)} mm</div>
        </div>`
      },
      extraCssText: 'border-radius: 8px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);'
    },
    xAxis: {
      type: 'time',
      name: '时间',
      nameLocation: 'middle',
      nameGap: 30,
      nameTextStyle: {
        color: themeColors.textSecondary,
        fontSize: 12
      },
      axisLine: {
        lineStyle: {
          color: themeColors.axisLine
        }
      },
      axisLabel: {
        color: themeColors.textSecondary,
        formatter: (value) => {
          const date = new Date(value)
          return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`
        }
      },
      splitLine: {
        lineStyle: {
          color: themeColors.splitLine
        }
      }
    },
    yAxis: {
      type: 'value',
      name: '位置 (mm)',
      nameLocation: 'middle',
      nameGap: 40,
      nameTextStyle: {
        color: themeColors.textSecondary,
        fontSize: 12
      },
      axisLine: {
        lineStyle: {
          color: themeColors.axisLine
        }
      },
      axisLabel: {
        color: themeColors.textSecondary,
        formatter: (value) => value.toFixed(2)
      },
      splitLine: {
        lineStyle: {
          color: themeColors.splitLine
        }
      },
      scale: true
    },
    series: [{
      name: '位置',
      type: 'line',
      smooth: true,
      symbol: 'none',
      data: [],
      lineStyle: {
        color: themeColors.lineColor,
        width: 2.5,
        shadowColor: themeColors.lineColor,
        shadowBlur: 8,
        shadowOffsetY: 2
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: themeColors.areaGradientStart },
          { offset: 1, color: themeColors.areaGradientEnd }
        ])
      },
      emphasis: {
        lineStyle: {
          width: 3
        }
      }
    }],
    animation: true,
    animationDuration: 300,
    animationEasing: 'cubicOut'
  }
  
  chart.setOption(option)
}

/**
 * 更新图表数据
 * 添加平滑过渡动画
 */
function updateChart() {
  if (!chart) return
  
  const themeColors = getChartThemeColors()
  
  chart.setOption({
    backgroundColor: themeColors.backgroundColor,
    xAxis: {
      nameTextStyle: { color: themeColors.textSecondary },
      axisLine: { lineStyle: { color: themeColors.axisLine } },
      axisLabel: { color: themeColors.textSecondary },
      splitLine: { lineStyle: { color: themeColors.splitLine } }
    },
    yAxis: {
      nameTextStyle: { color: themeColors.textSecondary },
      axisLine: { lineStyle: { color: themeColors.axisLine } },
      axisLabel: { color: themeColors.textSecondary },
      splitLine: { lineStyle: { color: themeColors.splitLine } }
    },
    series: [{
      lineStyle: {
        color: themeColors.lineColor,
        shadowColor: themeColors.lineColor
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: themeColors.areaGradientStart },
          { offset: 1, color: themeColors.areaGradientEnd }
        ])
      },
      data: dataPoints.value
    }]
  })
}

/**
 * 清除图表数据
 */
function clearData() {
  dataPoints.value = []
  updateChart()
}

/**
 * 监听位置变化
 * 实时更新图表数据
 */
watch(() => motorStore.positionMm, (newVal) => {
  if (!motorStore.isConnected) return
  
  dataPoints.value.push([Date.now(), newVal])
  
  // 限制数据点数量
  if (dataPoints.value.length > maxPoints) {
    dataPoints.value.shift()
  }
  
  updateChart()
})

/**
 * 监听连接状态
 */
watch(() => motorStore.isConnected, (connected) => {
  if (!connected) {
    // 断开连接时不清除数据，保留历史
  }
})

/**
 * 处理窗口大小变化
 */
function handleResize() {
  chart?.resize()
}

const themeObserver = null

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>

<style scoped>
.position-chart {
  margin-bottom: var(--spacing-5);
  background-color: var(--color-surface-primary);
  border-color: var(--color-border-primary);
  border-radius: var(--radius-lg);
  transition: var(--transition-all);
}

.position-chart:hover {
  box-shadow: var(--shadow-lg);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.header-title .el-icon {
  color: var(--color-primary-500);
}

.chart-content {
  position: relative;
  height: 300px;
}

.chart-container {
  width: 100%;
  height: 100%;
  border-radius: var(--radius-md);
  transition: var(--transition-opacity);
}

.empty-state {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--color-text-tertiary);
  background-color: var(--color-surface-primary);
  border-radius: var(--radius-md);
}

.empty-state .el-icon {
  color: var(--color-neutral-400);
  margin-bottom: var(--spacing-3);
  opacity: 0.6;
}

.empty-state p {
  margin: var(--spacing-1) 0;
  font-size: var(--font-size-base);
}

.empty-state .hint {
  font-size: var(--font-size-sm);
  color: var(--color-text-disabled);
}

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-base);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 响应式优化 */
@media (max-width: 768px) {
  .chart-content {
    height: 250px;
  }
}
</style>
