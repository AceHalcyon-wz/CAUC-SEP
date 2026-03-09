<template>
  <el-card class="field-map-card">
    <template #header>
      <div class="card-header">
        <div class="header-title">
          <el-icon class="header-icon">
            <TrendCharts />
          </el-icon>
          <span>电流-磁场映射曲线</span>
        </div>
        <div class="header-actions">
          <el-button
            type="primary"
            size="small"
            :icon="Download"
            :disabled="mapData.length === 0"
            @click="handleExportMap"
          >
            导出映射
          </el-button>
          <el-button
            type="info"
            size="small"
            :icon="Refresh"
            @click="handleRefreshMap"
          >
            刷新
          </el-button>
        </div>
      </div>
    </template>

    <div class="field-map-content">
      <!-- 实时数据显示 -->
      <div class="realtime-info">
        <el-row :gutter="16">
          <el-col :span="6">
            <div class="info-item">
              <div class="info-label">
                当前电流
              </div>
              <div class="info-value mono">
                {{ currentCurrent.toFixed(3) }} A
              </div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="info-item">
              <div class="info-label">
                当前磁场
              </div>
              <div class="info-value mono">
                {{ currentField.toFixed(2) }} mT
              </div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="info-item">
              <div class="info-label">
                工作点标记
              </div>
              <div class="info-value">
                <el-tag
                  :type="isWorkingPointValid ? 'success' : 'warning'"
                  size="small"
                >
                  {{ isWorkingPointValid ? '有效' : '偏离' }}
                </el-tag>
              </div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="info-item">
              <div class="info-label">
                数据点数
              </div>
              <div class="info-value mono">
                {{ mapData.length }}
              </div>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- 图表控制 -->
      <div class="chart-controls">
        <el-checkbox v-model="chartConfig.showCalibration">
          显示校准曲线
        </el-checkbox>
        <el-checkbox v-model="chartConfig.showWorkingPoint">
          显示工作点
        </el-checkbox>
        <el-checkbox v-model="chartConfig.showGrid">
          显示网格
        </el-checkbox>
        <el-checkbox v-model="chartConfig.autoUpdate">
          实时更新
        </el-checkbox>
        <el-button
          size="small"
          :icon="Delete"
          :disabled="mapData.length === 0"
          @click="handleClearData"
        >
          清除数据
        </el-button>
      </div>

      <!-- 映射图表 -->
      <div
        ref="chartRef"
        class="field-chart"
      />

      <!-- 图表统计信息 -->
      <div
        v-if="mapData.length > 0"
        class="chart-stats"
      >
        <el-row :gutter="16">
          <el-col :span="8">
            <div class="stat-item">
              <div class="stat-label">
                电流范围
              </div>
              <div class="stat-value mono">
                {{ currentRange }}
              </div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="stat-item">
              <div class="stat-label">
                磁场范围
              </div>
              <div class="stat-value mono">
                {{ fieldRange }}
              </div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="stat-item">
              <div class="stat-label">
                平均磁场/电流比
              </div>
              <div class="stat-value mono">
                {{ avgFieldCurrentRatio }}
              </div>
            </div>
          </el-col>
        </el-row>
      </div>
    </div>
  </el-card>
</template>

<script setup>
/**
 * @file ElectromagnetFieldMap.vue
 * @path src/components/
 * @description 电流-磁场实时映射显示组件，提供映射曲线可视化、工作点标记和数据导出功能
 * @author Agent
 * @date 2024-03-06
 */

import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useElectromagnetStore } from '../stores/electromagnet'
import { ElMessage } from 'element-plus'
import { TrendCharts, Download, Refresh, Delete } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

const electromagnetStore = useElectromagnetStore()

// ============ 响应式状态 ============

/** 图表引用 */
const chartRef = ref(null)
let chartInstance = null

/** 图表配置 */
const chartConfig = reactive({
  showCalibration: true,
  showWorkingPoint: true,
  showGrid: true,
  autoUpdate: true
})

/** 映射数据 */
const mapData = ref([])

/** 最大数据点数 */
const MAX_DATA_POINTS = 500

// ============ 计算属性 ============

/** 当前电流 */
const currentCurrent = computed(() => electromagnetStore.currentCurrent)

/** 当前磁场 */
const currentField = computed(() => electromagnetStore.currentField)

/** 工作点是否有效（在校准曲线附近） */
const isWorkingPointValid = computed(() => {
  if (!electromagnetStore.calibrationCurve.coefficients) {
    return true
  }

  const predictedField = electromagnetStore.calculateField(currentCurrent.value)
  const deviation = Math.abs(currentField.value - predictedField)
  return deviation < 5 // 偏差小于5mT视为有效
})

/** 电流范围 */
const currentRange = computed(() => {
  if (mapData.value.length === 0) return '-'
  const currents = mapData.value.map(d => d.current)
  const min = Math.min(...currents)
  const max = Math.max(...currents)
  return `${min.toFixed(3)} ~ ${max.toFixed(3)} A`
})

/** 磁场范围 */
const fieldRange = computed(() => {
  if (mapData.value.length === 0) return '-'
  const fields = mapData.value.map(d => d.field)
  const min = Math.min(...fields)
  const max = Math.max(...fields)
  return `${min.toFixed(2)} ~ ${max.toFixed(2)} mT`
})

/** 平均磁场/电流比 */
const avgFieldCurrentRatio = computed(() => {
  if (mapData.value.length === 0) return '-'
  const ratios = mapData.value
    .filter(d => Math.abs(d.current) > 0.01)
    .map(d => d.field / d.current)
  if (ratios.length === 0) return '-'
  const avg = ratios.reduce((sum, r) => sum + r, 0) / ratios.length
  return `${avg.toFixed(2)} mT/A`
})

// ============ 方法 ============

/**
 * 初始化图表
 */
function initChart() {
  if (!chartRef.value) return

  chartInstance = echarts.init(chartRef.value)

  const option = {
    grid: {
      left: '12%',
      right: '5%',
      top: '10%',
      bottom: '12%'
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'var(--color-surface-elevated)',
      borderColor: 'var(--color-border-primary)',
      textStyle: {
        color: 'var(--color-text-primary)'
      },
      formatter: (params) => {
        if (params.length === 0) return ''
        const point = params[0]
        return `电流: ${point.value[0].toFixed(3)} A<br/>磁场: ${point.value[1].toFixed(2)} mT`
      }
    },
    legend: {
      data: ['映射数据', '校准曲线', '工作点'],
      top: 0,
      right: 10,
      textStyle: {
        color: 'var(--color-text-secondary)'
      }
    },
    xAxis: {
      type: 'value',
      name: '电流 (A)',
      nameLocation: 'middle',
      nameGap: 30,
      nameTextStyle: {
        color: 'var(--color-text-secondary)'
      },
      min: electromagnetStore.currentLimits.min,
      max: electromagnetStore.currentLimits.max,
      axisLine: {
        lineStyle: {
          color: 'var(--color-border-primary)'
        }
      },
      splitLine: {
        show: chartConfig.showGrid,
        lineStyle: {
          color: 'var(--color-border-secondary)',
          type: 'dashed'
        }
      }
    },
    yAxis: {
      type: 'value',
      name: '磁场 (mT)',
      nameLocation: 'middle',
      nameGap: 40,
      nameTextStyle: {
        color: 'var(--color-text-secondary)'
      },
      axisLine: {
        lineStyle: {
          color: 'var(--color-border-primary)'
        }
      },
      splitLine: {
        show: chartConfig.showGrid,
        lineStyle: {
          color: 'var(--color-border-secondary)',
          type: 'dashed'
        }
      }
    },
    series: [
      {
        name: '映射数据',
        type: 'scatter',
        data: [],
        symbolSize: 6,
        itemStyle: {
          color: 'var(--color-data-blue)'
        },
        emphasis: {
          itemStyle: {
            borderColor: 'var(--color-text-primary)',
            borderWidth: 2
          }
        }
      },
      {
        name: '校准曲线',
        type: 'line',
        data: [],
        smooth: true,
        lineStyle: {
          color: 'var(--color-data-green)',
          width: 2
        },
        symbol: 'none'
      },
      {
        name: '工作点',
        type: 'scatter',
        data: [],
        symbolSize: 15,
        itemStyle: {
          color: 'var(--color-data-red)',
          borderColor: 'var(--color-text-primary)',
          borderWidth: 2
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'var(--color-data-red)'
          }
        }
      }
    ]
  }

  chartInstance.setOption(option)
}

/**
 * 更新图表
 */
function updateChart() {
  if (!chartInstance) return

  // 映射数据
  const mapDataPoints = mapData.value.map(d => [d.current, d.field])

  // 校准曲线数据
  const calibrationData = []
  if (chartConfig.showCalibration && electromagnetStore.calibrationCurve.coefficients) {
    const min = electromagnetStore.currentLimits.min
    const max = electromagnetStore.currentLimits.max
    const step = (max - min) / 100

    for (let current = min; current <= max; current += step) {
      const field = electromagnetStore.calculateField(current)
      calibrationData.push([current, field])
    }
  }

  // 工作点数据
  let workingPointData = []
  if (chartConfig.showWorkingPoint && currentCurrent.value !== 0) {
    workingPointData = [[currentCurrent.value, currentField.value]]
  }

  chartInstance.setOption({
    xAxis: {
      splitLine: {
        show: chartConfig.showGrid
      }
    },
    yAxis: {
      splitLine: {
        show: chartConfig.showGrid
      }
    },
    series: [
      { data: mapDataPoints },
      { data: calibrationData },
      { data: workingPointData }
    ]
  })
}

/**
 * 添加数据点
 * @param {number} current - 电流值
 * @param {number} field - 磁场值
 */
function addDataPoint(current, field) {
  mapData.value.push({
    current,
    field,
    timestamp: Date.now()
  })

  // 限制数据点数量
  if (mapData.value.length > MAX_DATA_POINTS) {
    mapData.value.shift()
  }

  updateChart()
}

/**
 * 导出映射数据
 */
function handleExportMap() {
  if (mapData.value.length === 0) {
    ElMessage.warning('没有映射数据可导出')
    return
  }

  const headers = ['时间戳', '电流(A)', '磁场(mT)']
  const rows = mapData.value.map(d => {
    const timestamp = new Date(d.timestamp).toISOString()
    return [timestamp, d.current.toFixed(4), d.field.toFixed(2)]
  })

  const csvContent = [
    headers.join(','),
    ...rows.map(row => row.join(','))
  ].join('\n')

  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', `field_map_${new Date().toISOString().slice(0, 10)}.csv`)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)

  ElMessage.success('映射数据已导出')
}

/**
 * 刷新映射
 */
function handleRefreshMap() {
  updateChart()
  ElMessage.success('映射已刷新')
}

/**
 * 清除数据
 */
function handleClearData() {
  mapData.value = []
  updateChart()
  ElMessage.info('数据已清除')
}

/**
 * 窗口大小变化处理
 */
function handleResize() {
  chartInstance?.resize()
}

// ============ 监听器 ============

// 监听当前电流和磁场变化，自动添加数据点
watch([currentCurrent, currentField], ([newCurrent, newField]) => {
  if (chartConfig.autoUpdate && Math.abs(newCurrent) > 0.01) {
    addDataPoint(newCurrent, newField)
  }
})

// 监听图表配置变化
watch(chartConfig, () => {
  updateChart()
}, { deep: true })

// 监听校准系数变化
watch(() => electromagnetStore.calibrationCurve.coefficients, () => {
  updateChart()
}, { deep: true })

// ============ 生命周期 ============

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
})
</script>

<style scoped>
.field-map-card {
  margin-bottom: var(--spacing-4);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  transition: var(--transition-all);
}

.field-map-card:hover {
  box-shadow: var(--shadow-lg);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-2);
}

.header-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
}

.header-icon {
  font-size: var(--font-size-xl);
  color: var(--color-primary-500);
}

.header-actions {
  display: flex;
  gap: var(--spacing-2);
}

.field-map-content {
  padding: var(--spacing-3) 0;
}

/* 实时信息 */
.realtime-info {
  padding: var(--spacing-3);
  background-color: var(--color-surface-secondary);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-3);
  border: 1px solid var(--color-border-primary);
}

.info-item {
  text-align: center;
  padding: var(--spacing-2);
}

.info-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-bottom: var(--spacing-1);
}

.info-value {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

/* 图表控制 */
.chart-controls {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
  padding: var(--spacing-2);
  background-color: var(--color-surface-secondary);
  border-radius: var(--radius-sm);
  margin-bottom: var(--spacing-3);
}

/* 映射图表 */
.field-chart {
  width: 100%;
  height: 400px;
  margin-bottom: var(--spacing-3);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
}

/* 图表统计 */
.chart-stats {
  padding: var(--spacing-3);
  background-color: var(--color-surface-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
}

.stat-item {
  text-align: center;
  padding: var(--spacing-2);
}

.stat-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-bottom: var(--spacing-1);
}

.stat-value {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

/* 工具类 */
.mono {
  font-family: var(--font-family-mono);
}

/* Element Plus 样式覆盖 */
:deep(.el-card__header) {
  background-color: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border-primary);
}

:deep(.el-checkbox__label) {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .chart-controls {
    flex-wrap: wrap;
  }

  .field-chart {
    height: 300px;
  }

  .realtime-info .el-col,
  .chart-stats .el-col {
    margin-bottom: var(--spacing-2);
  }
}
</style>
