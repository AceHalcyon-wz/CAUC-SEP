<template>
  <div class="analysis-history-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <el-icon class="header-icon">
          <Clock />
        </el-icon>
        <div class="header-content">
          <h1 class="page-title">
            历史数据分析
          </h1>
          <p class="page-subtitle">
            查询历史实验数据，支持多维度对比分析
          </p>
        </div>
      </div>
      <div class="header-right">
        <el-button 
          v-if="activeTab === 'compare'"
          type="primary" 
          :icon="Plus"
          :disabled="compareDatasets.length >= 4"
          @click="addCompareDataset"
        >
          添加对比数据
        </el-button>
        <el-button
          type="success"
          :icon="Download"
          @click="exportHistoryData"
        >
          导出数据
        </el-button>
      </div>
    </div>

    <!-- 标签页切换 -->
    <el-tabs
      v-model="activeTab"
      class="main-tabs"
    >
      <!-- 查询标签页 -->
      <el-tab-pane
        label="数据查询"
        name="query"
      >
        <!-- 查询条件面板 -->
        <HistoryQuery
          ref="queryRef"
          :show-advanced="false"
          :experiment-options="experimentOptions"
          @query="handleQuery"
          @reset="handleReset"
        />

        <!-- 数据展示区域 -->
        <el-row
          :gutter="24"
          class="content-row"
        >
          <!-- 左侧：数据列表 -->
          <el-col
            :xs="24"
            :sm="24"
            :md="10"
            :lg="8"
          >
            <el-card class="data-list-card">
              <template #header>
                <div class="card-header">
                  <el-icon><List /></el-icon>
                  <span>数据记录</span>
                  <el-tag
                    type="info"
                    size="small"
                  >
                    {{ totalRecords }} 条
                  </el-tag>
                </div>
              </template>
              
              <!-- 使用虚拟滚动列表 -->
              <VirtualScrollList
                ref="scrollListRef"
                :items="tableData"
                :item-height="56"
                :height="500"
                :enable-lazy-load="true"
                @lazy-load="handleLazyLoad"
                @item-click="handleRowClick"
              >
                <template #default="{ item }">
                  <div class="data-item">
                    <div class="item-main">
                      <div class="item-time">
                        {{ item.timestamp }}
                      </div>
                      <div class="item-device">
                        {{ item.device }}
                      </div>
                    </div>
                    <div class="item-value">
                      <span class="value-number mono">{{ item.value.toFixed(3) }}</span>
                      <span class="value-unit">{{ item.unit }}</span>
                    </div>
                  </div>
                </template>
              </VirtualScrollList>
              
              <!-- 空状态 -->
              <div
                v-if="!isLoading && tableData.length === 0"
                class="empty-list"
              >
                <el-icon class="empty-icon">
                  <Document />
                </el-icon>
                <p>暂无历史数据</p>
                <p class="empty-hint">
                  请使用上方查询条件获取数据
                </p>
              </div>
              
              <!-- 分页控制 -->
              <div class="pagination-wrapper">
                <el-pagination
                  v-model:current-page="currentPage"
                  v-model:page-size="pageSize"
                  :total="totalRecords"
                  :page-sizes="[20, 50, 100, 200]"
                  layout="total, sizes, prev, pager, next"
                  @size-change="handleSizeChange"
                  @current-change="handlePageChange"
                />
              </div>
            </el-card>
          </el-col>

          <!-- 右侧：数据图表 -->
          <el-col
            :xs="24"
            :sm="24"
            :md="14"
            :lg="16"
          >
            <el-card class="chart-card">
              <template #header>
                <div class="card-header">
                  <el-icon><TrendCharts /></el-icon>
                  <span>数据趋势</span>
                  <div class="chart-actions">
                    <el-button-group size="small">
                      <el-button 
                        :type="chartType === 'line' ? 'primary' : ''"
                        @click="chartType = 'line'"
                      >
                        折线图
                      </el-button>
                      <el-button 
                        :type="chartType === 'bar' ? 'primary' : ''"
                        @click="chartType = 'bar'"
                      >
                        柱状图
                      </el-button>
                      <el-button 
                        :type="chartType === 'scatter' ? 'primary' : ''"
                        @click="chartType = 'scatter'"
                      >
                        散点图
                      </el-button>
                    </el-button-group>
                  </div>
                </div>
              </template>
              
              <div
                v-if="isLoading"
                class="chart-loading"
              >
                <el-icon class="loading-icon">
                  <Loading />
                </el-icon>
                <p>正在加载数据...</p>
              </div>
              <div
                v-else-if="tableData.length === 0"
                class="chart-empty"
              >
                <el-icon class="empty-icon">
                  <Document />
                </el-icon>
                <p>暂无数据，请先查询历史数据</p>
              </div>
              <div
                v-else
                ref="chartRef"
                class="chart-container"
              />
            </el-card>

            <!-- 数据统计 -->
            <el-card class="stats-card">
              <template #header>
                <div class="card-header">
                  <el-icon><DataAnalysis /></el-icon>
                  <span>统计分析</span>
                </div>
              </template>
              
              <el-row :gutter="20">
                <el-col
                  :xs="12"
                  :sm="6"
                >
                  <div class="stat-item">
                    <div class="stat-label">
                      数据总量
                    </div>
                    <div class="stat-value mono">
                      {{ statistics.total }}
                    </div>
                  </div>
                </el-col>
                <el-col
                  :xs="12"
                  :sm="6"
                >
                  <div class="stat-item">
                    <div class="stat-label">
                      平均值
                    </div>
                    <div class="stat-value mono">
                      {{ statistics.avg.toFixed(3) }}
                    </div>
                  </div>
                </el-col>
                <el-col
                  :xs="12"
                  :sm="6"
                >
                  <div class="stat-item">
                    <div class="stat-label">
                      最大值
                    </div>
                    <div class="stat-value mono">
                      {{ statistics.max.toFixed(3) }}
                    </div>
                  </div>
                </el-col>
                <el-col
                  :xs="12"
                  :sm="6"
                >
                  <div class="stat-item">
                    <div class="stat-label">
                      最小值
                    </div>
                    <div class="stat-value mono">
                      {{ statistics.min.toFixed(3) }}
                    </div>
                  </div>
                </el-col>
              </el-row>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- 数据对比标签页 -->
      <el-tab-pane
        label="数据对比"
        name="compare"
      >
        <el-card class="compare-card">
          <template #header>
            <div class="card-header">
              <el-icon><Connection /></el-icon>
              <span>多数据集对比分析</span>
              <el-tag
                type="info"
                size="small"
              >
                {{ compareDatasets.length }} / 4 个数据集
              </el-tag>
            </div>
          </template>

          <!-- 对比数据集列表 -->
          <div
            v-if="compareDatasets.length > 0"
            class="compare-datasets"
          >
            <el-row :gutter="16">
              <el-col
                v-for="(dataset, index) in compareDatasets"
                :key="dataset.id"
                :xs="24"
                :sm="12"
                :md="6"
              >
                <div
                  class="dataset-card"
                  :class="`dataset-color-${index}`"
                >
                  <div class="dataset-header">
                    <span class="dataset-name">{{ dataset.name }}</span>
                    <el-button
                      type="danger"
                      size="small"
                      :icon="Close"
                      circle
                      @click="removeCompareDataset(index)"
                    />
                  </div>
                  <div class="dataset-info">
                    <div class="info-item">
                      <span class="info-label">数据点:</span>
                      <span class="info-value">{{ dataset.data.length }}</span>
                    </div>
                    <div class="info-item">
                      <span class="info-label">时间范围:</span>
                      <span class="info-value">{{ dataset.timeRange }}</span>
                    </div>
                  </div>
                </div>
              </el-col>
            </el-row>
          </div>

          <!-- 空状态 -->
          <el-empty
            v-else
            description="暂无对比数据，请点击'添加对比数据'按钮"
            :image-size="200"
          />

          <!-- 对比图表 -->
          <div
            v-if="compareDatasets.length > 0"
            ref="compareChartRef"
            class="compare-chart"
          />

          <!-- 差异分析 -->
          <div
            v-if="compareDatasets.length >= 2"
            class="difference-analysis"
          >
            <div class="analysis-header">
              <el-icon><DataAnalysis /></el-icon>
              <span>差异分析</span>
            </div>
            <el-table
              :data="differenceData"
              style="width: 100%"
            >
              <el-table-column
                prop="metric"
                label="指标"
                width="150"
              />
              <el-table-column
                v-for="(dataset, index) in compareDatasets"
                :key="dataset.id"
                :label="dataset.name"
                align="center"
              >
                <template #default="{ row }">
                  <span class="mono">{{ row.values[index].toFixed(3) }}</span>
                </template>
              </el-table-column>
              <el-table-column
                label="差异"
                align="center"
                width="150"
              >
                <template #default="{ row }">
                  <span :class="getDifferenceClass(row.difference)">
                    {{ row.difference > 0 ? '+' : '' }}{{ row.difference.toFixed(3) }}
                  </span>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-tab-pane>

      <!-- 数据叠加标签页 -->
      <el-tab-pane
        label="数据叠加"
        name="overlay"
      >
        <el-card class="overlay-card">
          <template #header>
            <div class="card-header">
              <el-icon><Grid /></el-icon>
              <span>数据叠加分析</span>
            </div>
          </template>

          <!-- 叠加配置 -->
          <div class="overlay-config">
            <el-form :inline="true">
              <el-form-item label="叠加方式">
                <el-select
                  v-model="overlayMode"
                  style="width: 150px"
                >
                  <el-option
                    label="时间对齐"
                    value="time"
                  />
                  <el-option
                    label="数值对齐"
                    value="value"
                  />
                  <el-option
                    label="归一化"
                    value="normalize"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="显示模式">
                <el-select
                  v-model="overlayDisplay"
                  style="width: 150px"
                >
                  <el-option
                    label="叠加显示"
                    value="overlay"
                  />
                  <el-option
                    label="差值显示"
                    value="difference"
                  />
                  <el-option
                    label="比值显示"
                    value="ratio"
                  />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button
                  type="primary"
                  :icon="Refresh"
                  @click="updateOverlayChart"
                >
                  更新图表
                </el-button>
              </el-form-item>
            </el-form>
          </div>

          <!-- 叠加图表 -->
          <div
            ref="overlayChartRef"
            class="overlay-chart"
          />
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
/**
 * @file History.vue
 * @path src/views/analysis/
 * @description 历史数据分析页面，提供历史数据查询、对比和叠加分析功能
 * @author Agent
 * @date 2024-03-07
 */

import { ref, reactive, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import {
  Clock,
  Search,
  Download,
  List,
  TrendCharts,
  DataAnalysis,
  Plus,
  Close,
  Refresh,
  Connection,
  Grid,
  Loading,
  Document
} from '@element-plus/icons-vue'
import HistoryQuery from '@/components/HistoryQuery.vue'
import VirtualScrollList from '@/components/VirtualScrollList.vue'
import { useExperimentStore } from '@/stores/experiment'
import { get, post } from '@/utils/apiRequest'
import { API_BASE } from '@/config/api'

// ==================== 组合式函数调用 ====================

const experimentStore = useExperimentStore()

// ==================== 响应式状态 ====================

/** 当前标签页 */
const activeTab = ref('query')

/** 图表类型 */
const chartType = ref('line')

/** 图表容器引用 */
const chartRef = ref(null)
const compareChartRef = ref(null)
const overlayChartRef = ref(null)

/** 图表实例 */
let chart = null
let compareChart = null
let overlayChart = null

/** 当前页码 */
const currentPage = ref(1)

/** 每页大小 */
const pageSize = ref(50)

/** 总记录数 */
const totalRecords = ref(0)

/** 是否正在加载 */
const isLoading = ref(false)

/** 表格数据 */
const tableData = ref([])

/** 查询条件 */
const currentQueryConditions = ref(null)

/** 对比数据集 */
const compareDatasets = ref([])

/** 叠加模式 */
const overlayMode = ref('time')

/** 叠加显示模式 */
const overlayDisplay = ref('overlay')

/** 组件引用 */
const queryRef = ref(null)
const scrollListRef = ref(null)

/** 实验选项 */
const experimentOptions = computed(() => {
  return experimentStore.experimentList.map(exp => ({
    label: exp.name || `实验 ${exp.experiment_id}`,
    value: exp.experiment_id
  }))
})

/** 统计数据 */
const statistics = computed(() => {
  const values = tableData.value.map(d => d.value)
  if (values.length === 0) {
    return { total: 0, avg: 0, max: 0, min: 0 }
  }
  
  return {
    total: values.length,
    avg: values.reduce((a, b) => a + b, 0) / values.length,
    max: Math.max(...values),
    min: Math.min(...values)
  }
})

/** 差异分析数据 */
const differenceData = computed(() => {
  if (compareDatasets.value.length < 2) return []

  const metrics = ['平均值', '最大值', '最小值', '标准差']
  
  return metrics.map(metric => {
    const values = compareDatasets.value.map(dataset => {
      const data = dataset.data.map(d => d.value)
      let avg
      switch (metric) {
        case '平均值':
          return data.reduce((a, b) => a + b, 0) / data.length
        case '最大值':
          return Math.max(...data)
        case '最小值':
          return Math.min(...data)
        case '标准差':
          avg = data.reduce((a, b) => a + b, 0) / data.length
          return Math.sqrt(data.reduce((sum, val) => sum + Math.pow(val - avg, 2), 0) / data.length)
        default:
          return 0
      }
    })

    const difference = values.length >= 2 ? values[1] - values[0] : 0

    return {
      metric,
      values,
      difference
    }
  })
})

// ==================== 图表初始化 ====================

/**
 * 初始化主图表
 */
function initChart() {
  if (!chartRef.value) {
    console.warn('[History] Chart container not ready')
    return
  }
  
  // 销毁旧图表实例
  if (chart) {
    chart.dispose()
    chart = null
  }
  
  try {
    chart = echarts.init(chartRef.value)
    
    // 如果有数据，立即更新图表
    if (tableData.value.length > 0) {
      updateChart()
    } else {
      // 显示空状态
      chart.setOption({
        title: {
          text: '暂无数据',
          left: 'center',
          top: 'center',
          textStyle: {
            color: '#999',
            fontSize: 14
          }
        }
      })
    }
  } catch (error) {
    console.error('[History] Failed to initialize chart:', error)
  }
}

/**
 * 初始化对比图表
 */
function initCompareChart() {
  if (!compareChartRef.value) return
  
  compareChart = echarts.init(compareChartRef.value)
  updateCompareChart()
}

/**
 * 初始化叠加图表
 */
function initOverlayChart() {
  if (!overlayChartRef.value) return
  
  overlayChart = echarts.init(overlayChartRef.value)
  updateOverlayChart()
}

// ==================== 图表更新 ====================

/**
 * 更新主图表
 */
function updateChart() {
  if (!chart) {
    console.warn('[History] Chart instance not initialized')
    return
  }
  
  try {
    if (tableData.value.length === 0) {
      // 显示空状态
      chart.setOption({
        title: {
          text: '暂无数据',
          left: 'center',
          top: 'center',
          textStyle: {
            color: '#999',
            fontSize: 14
          }
        }
      })
      return
    }
    
    const xData = tableData.value.map(d => {
      // 提取时间部分
      const ts = d.timestamp
      if (typeof ts === 'string' && ts.includes(' ')) {
        return ts.split(' ')[1] || ts.split('T')[1]?.substring(0, 8) || ts
      }
      return ts
    })
    const yData = tableData.value.map(d => d.value)
    
    const option = {
      backgroundColor: '#ffffff',
      grid: {
        left: '10%',
        right: '5%',
        top: '10%',
        bottom: '15%'
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#ffffff',
        borderColor: '#e2e8f0',
        borderWidth: 1,
        textStyle: {
          color: '#1a202c',
          fontSize: 13
        }
      },
      xAxis: {
        type: 'category',
        data: xData,
        name: '时间',
        nameTextStyle: { color: '#4a5568' },
        axisLine: { lineStyle: { color: '#e2e8f0' } },
        axisLabel: { color: '#4a5568', rotate: 45 },
        splitLine: { lineStyle: { color: '#edf2f7' } }
      },
      yAxis: {
        type: 'value',
        name: '数值',
        nameTextStyle: { color: '#4a5568' },
        axisLine: { lineStyle: { color: '#e2e8f0' } },
        axisLabel: { color: '#4a5568' },
        splitLine: { lineStyle: { color: '#edf2f7' } }
      },
      series: [{
        name: '数值',
        type: chartType.value,
        data: yData,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: {
          color: '#409eff',
          width: 2
        },
        itemStyle: {
          color: '#409eff'
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.05)' }
          ])
        }
      }],
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
          bottom: 10
        }
      ]
    }
    
    chart.setOption(option, true)
  } catch (error) {
    console.error('[History] Failed to update chart:', error)
  }
}

/**
 * 更新对比图表
 */
function updateCompareChart() {
  if (!compareChart || compareDatasets.value.length === 0) return

  const colors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c']
  const series = compareDatasets.value.map((dataset, index) => ({
    name: dataset.name,
    type: 'line',
    data: dataset.data.map(d => d.value),
    smooth: true,
    symbol: 'circle',
    symbolSize: 6,
    lineStyle: {
      color: colors[index],
      width: 2
    },
    itemStyle: {
      color: colors[index]
    }
  }))

  const option = {
    backgroundColor: '#ffffff',
    grid: {
      left: '10%',
      right: '5%',
      top: '15%',
      bottom: '15%'
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#ffffff',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      textStyle: {
        color: '#1a202c',
        fontSize: 13
      }
    },
    legend: {
      data: compareDatasets.value.map(d => d.name),
      top: 10
    },
    xAxis: {
      type: 'category',
      data: compareDatasets.value[0]?.data.map((d, i) => i) || [],
      name: '数据点',
      nameTextStyle: { color: '#4a5568' },
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { color: '#4a5568' },
      splitLine: { lineStyle: { color: '#edf2f7' } }
    },
    yAxis: {
      type: 'value',
      name: '数值',
      nameTextStyle: { color: '#4a5568' },
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { color: '#4a5568' },
      splitLine: { lineStyle: { color: '#edf2f7' } }
    },
    series,
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
        bottom: 10
      }
    ]
  }

  compareChart.setOption(option, true)
}

/**
 * 更新叠加图表
 */
function updateOverlayChart() {
  if (!overlayChart || compareDatasets.value.length === 0) return

  const colors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c']
  let series = []

  if (overlayDisplay.value === 'overlay') {
    // 叠加显示
    series = compareDatasets.value.map((dataset, index) => ({
      name: dataset.name,
      type: 'line',
      data: dataset.data.map(d => d.value),
      smooth: true,
      lineStyle: { color: colors[index], width: 2 },
      itemStyle: { color: colors[index] }
    }))
  } else if (overlayDisplay.value === 'difference' && compareDatasets.value.length >= 2) {
    // 差值显示
    const data1 = compareDatasets.value[0].data.map(d => d.value)
    const data2 = compareDatasets.value[1].data.map(d => d.value)
    const diffData = data1.map((val, i) => val - data2[i])

    series = [{
      name: '差值',
      type: 'line',
      data: diffData,
      smooth: true,
      lineStyle: { color: '#f56c6c', width: 2 },
      itemStyle: { color: '#f56c6c' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(245, 108, 108, 0.3)' },
          { offset: 1, color: 'rgba(245, 108, 108, 0.05)' }
        ])
      }
    }]
  } else if (overlayDisplay.value === 'ratio' && compareDatasets.value.length >= 2) {
    // 比值显示
    const data1 = compareDatasets.value[0].data.map(d => d.value)
    const data2 = compareDatasets.value[1].data.map(d => d.value)
    const ratioData = data1.map((val, i) => data2[i] !== 0 ? val / data2[i] : 0)

    series = [{
      name: '比值',
      type: 'line',
      data: ratioData,
      smooth: true,
      lineStyle: { color: '#67c23a', width: 2 },
      itemStyle: { color: '#67c23a' }
    }]
  }

  const option = {
    backgroundColor: '#ffffff',
    grid: {
      left: '10%',
      right: '5%',
      top: '15%',
      bottom: '15%'
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#ffffff',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      textStyle: {
        color: '#1a202c',
        fontSize: 13
      }
    },
    legend: {
      data: series.map(s => s.name),
      top: 10
    },
    xAxis: {
      type: 'category',
      data: compareDatasets.value[0]?.data.map((d, i) => i) || [],
      name: '数据点',
      nameTextStyle: { color: '#4a5568' },
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { color: '#4a5568' },
      splitLine: { lineStyle: { color: '#edf2f7' } }
    },
    yAxis: {
      type: 'value',
      name: overlayDisplay.value === 'ratio' ? '比值' : '数值',
      nameTextStyle: { color: '#4a5568' },
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { color: '#4a5568' },
      splitLine: { lineStyle: { color: '#edf2f7' } }
    },
    series,
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
        bottom: 10
      }
    ]
  }

  overlayChart.setOption(option, true)
}

// ==================== 查询处理 ====================

/**
 * 处理查询
 */
async function handleQuery(conditions) {
  currentQueryConditions.value = conditions
  isLoading.value = true

  try {
    // 构建查询参数
    const params = new URLSearchParams()
    
    // 修复字段名映射
    if (conditions.experiments && conditions.experiments.length > 0) {
      params.append('experiment_ids', conditions.experiments.join(','))
    }
    
    if (conditions.devices && conditions.devices.length > 0) {
      params.append('devices', conditions.devices.join(','))
    }
    
    if (conditions.timeRange) {
      if (conditions.timeRange.start) {
        params.append('start_time', conditions.timeRange.start)
      }
      if (conditions.timeRange.end) {
        params.append('end_time', conditions.timeRange.end)
      }
    }
    
    if (conditions.dataTypes && conditions.dataTypes.length > 0) {
      params.append('data_types', conditions.dataTypes.join(','))
    }
    
    params.append('limit', pageSize.value.toString())
    params.append('offset', ((currentPage.value - 1) * pageSize.value).toString())

    // 调用后端API
    const result = await get('/analysis/history', params, {
      onError: (msg) => {
        console.warn('[History] Failed to load history data:', msg)
      }
    })

    if (result.success && result.data) {
      // 处理返回的数据
      tableData.value = result.data.map(item => ({
        timestamp: item.timestamp,
        device: item.device || '未知设备',
        value: item.value,
        unit: item.unit,
        experiment_id: item.experiment_id,
        position_mm: item.position_mm,
        field_value: item.field_value,
        current_value: item.current_value,
        temperature: item.temperature
      }))
      
      totalRecords.value = result.total || tableData.value.length
      
      ElMessage.success(result.message || '查询成功')

      // 更新图表
      nextTick(() => {
        updateChart()
      })
    } else {
      // API调用失败，使用模拟数据作为后备
      ElMessage.warning('后端服务未启动，使用模拟数据')
      const mockData = generateMockData(conditions)
      tableData.value = mockData
      totalRecords.value = mockData.length
      
      nextTick(() => {
        updateChart()
      })
    }
  } catch (error) {
    console.error('Query failed:', error)
    ElMessage.error('查询失败: ' + error.message)
  } finally {
    isLoading.value = false
  }
}

/**
 * 处理重置
 */
function handleReset() {
  tableData.value = []
  totalRecords.value = 0
  currentQueryConditions.value = null
  currentPage.value = 1
}

/**
 * 生成模拟数据
 */
function generateMockData(conditions) {
  const count = 100
  const data = []
  const now = new Date()

  for (let i = 0; i < count; i++) {
    const timestamp = new Date(now.getTime() - i * 60000)
    data.push({
      timestamp: timestamp.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      }).replace(/\//g, '-'),
      device: conditions.devices[0] || '电机',
      value: 12 + Math.random() * 2,
      unit: 'mm'
    })
  }

  return data.reverse()
}

// ==================== 分页处理 ====================

/**
 * 处理页大小变化
 */
function handleSizeChange(size) {
  pageSize.value = size
  currentPage.value = 1
  if (currentQueryConditions.value) {
    handleQuery(currentQueryConditions.value)
  }
}

/**
 * 处理页码变化
 */
function handlePageChange(page) {
  currentPage.value = page
  if (currentQueryConditions.value) {
    handleQuery(currentQueryConditions.value)
  }
}

/**
 * 处理懒加载
 */
function handleLazyLoad() {
  if (!currentQueryConditions.value) return

  // 加载更多数据
  ElMessage.info('加载更多数据...')
  
  setTimeout(() => {
    const moreData = generateMockData(currentQueryConditions.value)
    tableData.value = [...tableData.value, ...moreData]
    totalRecords.value = tableData.value.length
    scrollListRef.value?.resetLoading()
  }, 500)
}

/**
 * 处理行点击
 */
function handleRowClick(item, index) {
  console.log('Selected row:', item, index)
}

// ==================== 数据对比 ====================

/**
 * 添加对比数据集
 */
async function addCompareDataset() {
  if (compareDatasets.value.length >= 4) {
    ElMessage.warning('最多只能对比4个数据集')
    return
  }

  try {
    const { value: name } = await ElMessageBox.prompt('请输入数据集名称', '添加对比数据', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputPattern: /\S+/,
      inputErrorMessage: '名称不能为空'
    })

    // 获取当前实验ID
    const experimentId = currentQueryConditions.value?.experiment_ids?.[0] || 1
    
    // 调用后端API获取对比数据
    const result = await post('/analysis/compare', {
      datasets: [
        ...compareDatasets.value.map(d => ({
          experiment_id: d.experiment_id,
          name: d.name,
          data_type: 'field'
        })),
        {
          experiment_id: experimentId,
          name: name,
          data_type: 'field'
        }
      ],
      align_mode: 'time',
      normalize: false
    }, {
      onError: (msg) => {
        console.warn('[History] Failed to load compare data:', msg)
      }
    })

    if (result.success && result.datasets) {
      // 更新对比数据集
      const newDataset = result.datasets[result.datasets.length - 1]
      compareDatasets.value.push({
        id: `dataset_${Date.now()}`,
        name: newDataset.name,
        experiment_id: newDataset.experiment_id,
        data: newDataset.data,
        timeRange: '最近数据',
        statistics: newDataset.statistics
      })

      ElMessage.success('数据集添加成功')

      // 更新图表
      nextTick(() => {
        if (!compareChart) {
          initCompareChart()
        }
        updateCompareChart()
      })
    } else {
      // API调用失败，使用模拟数据
      ElMessage.warning('后端服务未启动，使用模拟数据')
      
      const mockData = []
      const count = 50
      for (let i = 0; i < count; i++) {
        mockData.push({
          timestamp: new Date(Date.now() - i * 60000).toISOString(),
          value: 10 + Math.random() * 5
        })
      }

      compareDatasets.value.push({
        id: `dataset_${Date.now()}`,
        name,
        experiment_id: experimentId,
        data: mockData.reverse(),
        timeRange: '最近1小时'
      })

      ElMessage.success('数据集添加成功（模拟数据）')

      nextTick(() => {
        if (!compareChart) {
          initCompareChart()
        }
        updateCompareChart()
      })
    }
  } catch (error) {
    // 用户取消或其他错误
    if (error !== 'cancel') {
      console.error('Add compare dataset failed:', error)
      ElMessage.error('添加数据集失败: ' + error.message)
    }
  }
}

/**
 * 移除对比数据集
 */
function removeCompareDataset(index) {
  compareDatasets.value.splice(index, 1)
  updateCompareChart()
  ElMessage.success('数据集已移除')
}

/**
 * 获取差异样式类
 */
function getDifferenceClass(difference) {
  if (difference > 0) return 'difference-positive'
  if (difference < 0) return 'difference-negative'
  return 'difference-zero'
}

// ==================== 导出功能 ====================

/**
 * 导出历史数据
 */
function exportHistoryData() {
  if (tableData.value.length === 0) {
    ElMessage.warning('没有数据可导出')
    return
  }
  
  // 生成CSV内容
  const csvContent = [
    '时间,设备,数值,单位',
    ...tableData.value.map(d => `${d.timestamp},${d.device},${d.value.toFixed(3)},${d.unit}`)
  ].join('\n')
  
  // 创建下载链接
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', `history_data_${Date.now()}.csv`)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  
  ElMessage.success('数据已导出')
}

// ==================== 窗口大小变化处理 ====================

/**
 * 处理窗口大小变化
 */
function handleResize() {
  chart?.resize()
  compareChart?.resize()
  overlayChart?.resize()
}

// ==================== 监听器 ====================

// 监听图表类型变化
watch(chartType, () => {
  updateChart()
})

// 监听标签页切换
watch(activeTab, (newTab) => {
  nextTick(() => {
    if (newTab === 'query' && !chart) {
      initChart()
    } else if (newTab === 'compare' && !compareChart && compareDatasets.value.length > 0) {
      initCompareChart()
    } else if (newTab === 'overlay' && !overlayChart && compareDatasets.value.length > 0) {
      initOverlayChart()
    }
  })
})

// 监听叠加显示模式变化
watch(overlayDisplay, () => {
  updateOverlayChart()
})

// ==================== 生命周期 ====================

// 组件挂载时初始化
onMounted(() => {
  // 等待DOM渲染完成后初始化图表
  nextTick(() => {
    initChart()
    window.addEventListener('resize', handleResize)
  })

  // 加载实验列表
  experimentStore.fetchExperiments()
  
  // 自动加载初始数据（可选）
  // handleQuery({ devices: ['电机'], experiment_ids: [], data_types: ['field'] })
})

// 组件卸载时清理资源
onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  compareChart?.dispose()
  overlayChart?.dispose()
})
</script>

<style scoped>
.analysis-history-page {
  padding: var(--spacing-6);
  min-height: calc(100vh - 60px);
  background-color: var(--color-bg-secondary);
}

/* ==================== 页面头部 ==================== */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-6);
  padding: var(--spacing-5) var(--spacing-6);
  background: linear-gradient(135deg, var(--color-secondary-500) 0%, var(--color-secondary-600) 100%);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  position: relative;
  overflow: hidden;
}

.page-header::before {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 200px;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1));
  pointer-events: none;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
  position: relative;
  z-index: 1;
}

.header-icon {
  font-size: 40px;
  color: var(--color-text-inverse);
  padding: var(--spacing-3);
  background-color: rgba(255, 255, 255, 0.15);
  border-radius: var(--radius-lg);
  backdrop-filter: blur(10px);
}

.header-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.page-title {
  margin: 0;
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-inverse);
  letter-spacing: var(--letter-spacing-wide);
}

.page-subtitle {
  margin: 0;
  font-size: var(--font-size-sm);
  color: rgba(255, 255, 255, 0.85);
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  position: relative;
  z-index: 1;
}

/* ==================== 标签页 ==================== */
.main-tabs {
  background-color: var(--color-surface-primary);
  border-radius: var(--radius-lg);
  padding: var(--spacing-4);
  box-shadow: var(--shadow-card);
  border: 1px solid var(--color-border-primary);
}

:deep(.el-tabs__header) {
  margin-bottom: var(--spacing-5);
}

:deep(.el-tabs__nav-wrap::after) {
  height: 1px;
  background-color: var(--color-border-primary);
}

:deep(.el-tabs__item) {
  font-weight: var(--font-weight-medium);
  font-size: var(--font-size-base);
  padding: 0 var(--spacing-5);
  height: 42px;
  line-height: 42px;
  color: var(--color-text-secondary);
  transition: var(--transition-all);
}

:deep(.el-tabs__item:hover) {
  color: var(--color-primary-500);
}

:deep(.el-tabs__item.is-active) {
  color: var(--color-primary-500);
  font-weight: var(--font-weight-semibold);
}

:deep(.el-tabs__active-bar) {
  height: 3px;
  border-radius: var(--radius-full);
  background: linear-gradient(90deg, var(--color-primary-500), var(--color-secondary-500));
}

/* ==================== 内容区域 ==================== */
.content-row {
  margin-top: var(--spacing-4);
}

/* ==================== 数据列表卡片 ==================== */
.data-list-card {
  background-color: var(--color-surface-primary);
  border-color: var(--color-border-primary);
  border-radius: var(--radius-lg);
  height: 100%;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-card);
  transition: var(--transition-all);
}

.data-list-card:hover {
  box-shadow: var(--shadow-lg);
  border-color: var(--color-primary-200);
}

.data-list-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: var(--spacing-4);
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
}

.card-header .el-icon {
  color: var(--color-primary-500);
  font-size: var(--font-size-lg);
}

.card-header .el-tag {
  margin-left: auto;
  font-size: var(--font-size-xs);
}

/* ==================== 数据项 ==================== */
.data-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: var(--spacing-3);
  cursor: pointer;
  transition: var(--transition-fast);
  border-radius: var(--radius-md);
  border-left: 3px solid transparent;
  margin-bottom: var(--spacing-1);
}

.data-item:hover {
  background-color: var(--color-interactive-hover);
  border-left-color: var(--color-primary-500);
  transform: translateX(4px);
}

.empty-list {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 400px;
  gap: var(--spacing-3);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  border: 2px dashed var(--color-border-primary);
}

.empty-list .empty-icon {
  font-size: 64px;
  color: var(--color-neutral-400);
  opacity: 0.5;
}

.empty-list p {
  margin: 0;
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
}

.empty-list .empty-hint {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  padding: var(--spacing-2) var(--spacing-4);
  background-color: var(--color-bg-tertiary);
  border-radius: var(--radius-md);
}

.item-main {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
  flex: 1;
  min-width: 0;
}

.item-time {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  font-family: var(--font-family-mono);
  font-weight: var(--font-weight-medium);
}

.item-device {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
}

.item-device::before {
  content: '';
  width: 4px;
  height: 4px;
  background-color: var(--color-primary-400);
  border-radius: var(--radius-full);
}

.item-value {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-1);
}

.value-number {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary-600);
  font-family: var(--font-family-mono);
}

.value-unit {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-weight: var(--font-weight-medium);
}

.mono {
  font-family: var(--font-family-mono);
  color: var(--color-primary-600);
  font-weight: var(--font-weight-semibold);
}

/* ==================== 分页 ==================== */
.pagination-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: var(--spacing-4);
  padding-top: var(--spacing-4);
  border-top: 1px solid var(--color-border-primary);
  background-color: var(--color-bg-secondary);
  margin: var(--spacing-4) calc(-1 * var(--spacing-4)) calc(-1 * var(--spacing-4));
  padding: var(--spacing-4);
  border-radius: 0 0 var(--radius-md) var(--radius-md);
}

:deep(.el-pagination) {
  display: flex;
  gap: var(--spacing-2);
}

:deep(.el-pagination .el-pagination__total),
:deep(.el-pagination .el-pagination__sizes) {
  font-weight: var(--font-weight-medium);
}

/* ==================== 图表卡片 ==================== */
.chart-card {
  background-color: var(--color-surface-primary);
  border-color: var(--color-border-primary);
  border-radius: var(--radius-lg);
  margin-bottom: var(--spacing-4);
  box-shadow: var(--shadow-card);
  transition: var(--transition-all);
  overflow: hidden;
}

.chart-card:hover {
  box-shadow: var(--shadow-lg);
  border-color: var(--color-primary-200);
}

.chart-container {
  height: 480px;
  width: 100%;
  border-radius: var(--radius-md);
  background-color: var(--color-bg-primary);
  position: relative;
}

.chart-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, 
    var(--color-secondary-500), 
    var(--color-primary-500),
    var(--color-secondary-500)
  );
  border-radius: var(--radius-md) var(--radius-md) 0 0;
}

.chart-loading,
.chart-empty {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 480px;
  gap: var(--spacing-4);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  border: 2px dashed var(--color-border-primary);
}

.loading-icon {
  font-size: 48px;
  color: var(--color-primary-500);
  animation: spin 1s linear infinite;
}

.empty-icon {
  font-size: 48px;
  color: var(--color-neutral-400);
  opacity: 0.5;
}

.chart-loading p,
.chart-empty p {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin: 0;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.chart-actions {
  margin-left: auto;
  display: flex;
  gap: var(--spacing-2);
}

/* ==================== 统计卡片 ==================== */
.stats-card {
  background-color: var(--color-surface-primary);
  border-color: var(--color-border-primary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  transition: var(--transition-all);
}

.stats-card:hover {
  box-shadow: var(--shadow-lg);
}

.stat-item {
  text-align: center;
  padding: var(--spacing-5);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  transition: var(--transition-all);
  border: 1px solid transparent;
}

.stat-item:hover {
  background-color: var(--color-interactive-hover);
  border-color: var(--color-primary-200);
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.stat-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  margin-bottom: var(--spacing-2);
  font-weight: var(--font-weight-medium);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-value {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary-600);
  font-family: var(--font-family-mono);
}

/* ==================== 对比卡片 ==================== */
.compare-card,
.overlay-card {
  background-color: var(--color-surface-primary);
  border-color: var(--color-border-primary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
}

.compare-datasets {
  margin-bottom: var(--spacing-6);
}

.dataset-card {
  padding: var(--spacing-4);
  border-radius: var(--radius-md);
  border: 2px solid;
  transition: all var(--transition-fast);
  position: relative;
  overflow: hidden;
}

.dataset-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 100%;
}

.dataset-color-0 {
  border-color: var(--color-data-blue);
  background-color: rgba(49, 130, 206, 0.05);
}

.dataset-color-0::before {
  background-color: var(--color-data-blue);
}

.dataset-color-1 {
  border-color: var(--color-data-green);
  background-color: rgba(16, 185, 129, 0.05);
}

.dataset-color-1::before {
  background-color: var(--color-data-green);
}

.dataset-color-2 {
  border-color: var(--color-data-yellow);
  background-color: rgba(245, 158, 11, 0.05);
}

.dataset-color-2::before {
  background-color: var(--color-data-yellow);
}

.dataset-color-3 {
  border-color: var(--color-data-red);
  background-color: rgba(239, 68, 68, 0.05);
}

.dataset-color-3::before {
  background-color: var(--color-data-red);
}

.dataset-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.dataset-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-3);
}

.dataset-name {
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
}

.dataset-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.info-item {
  display: flex;
  justify-content: space-between;
  font-size: var(--font-size-sm);
}

.info-label {
  color: var(--color-text-tertiary);
}

.info-value {
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
  font-family: var(--font-family-mono);
}

.compare-chart,
.overlay-chart {
  height: 520px;
  width: 100%;
  margin-top: var(--spacing-4);
  border-radius: var(--radius-md);
  background-color: var(--color-bg-primary);
  position: relative;
}

.compare-chart::before,
.overlay-chart::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, 
    var(--color-data-blue), 
    var(--color-data-green),
    var(--color-data-yellow),
    var(--color-data-red)
  );
  border-radius: var(--radius-md) var(--radius-md) 0 0;
}

/* ==================== 差异分析 ==================== */
.difference-analysis {
  margin-top: var(--spacing-6);
  padding-top: var(--spacing-6);
  border-top: 1px solid var(--color-border-primary);
}

.analysis-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-4);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.analysis-header .el-icon {
  color: var(--color-primary-500);
  font-size: var(--font-size-xl);
}

.difference-positive {
  color: var(--color-success);
  font-weight: var(--font-weight-semibold);
  font-family: var(--font-family-mono);
}

.difference-negative {
  color: var(--color-error);
  font-weight: var(--font-weight-semibold);
  font-family: var(--font-family-mono);
}

.difference-zero {
  color: var(--color-text-tertiary);
  font-family: var(--font-family-mono);
}

/* ==================== 叠加配置 ==================== */
.overlay-config {
  padding: var(--spacing-4);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-4);
  border: 1px solid var(--color-border-primary);
}

/* ==================== Element Plus 样式覆盖 ==================== */
:deep(.el-card) {
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  background-color: var(--color-surface-primary);
  transition: var(--transition-all);
}

:deep(.el-card:hover) {
  box-shadow: var(--shadow-lg);
}

:deep(.el-card__header) {
  background-color: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border-primary);
  padding: var(--spacing-4) var(--spacing-5);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

:deep(.el-card__body) {
  padding: var(--spacing-5);
}

:deep(.el-table) {
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--color-border-primary);
}

:deep(.el-table th) {
  background-color: var(--color-bg-secondary);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-sm);
}

:deep(.el-table td) {
  transition: var(--transition-fast);
}

:deep(.el-table__row:hover td) {
  background-color: var(--color-interactive-hover);
}

/* ==================== 响应式优化 ==================== */
@media (max-width: 768px) {
  .analysis-history-page {
    padding: var(--spacing-4);
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-4);
    padding: var(--spacing-4);
  }

  .header-left {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-icon {
    font-size: 32px;
  }

  .page-title {
    font-size: var(--font-size-xl);
  }

  .header-right {
    width: 100%;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: var(--spacing-2);
  }

  .chart-container,
  .compare-chart,
  .overlay-chart {
    height: 320px;
  }

  .chart-loading,
  .chart-empty {
    height: 320px;
  }

  .stat-item {
    padding: var(--spacing-3);
  }

  .stat-value {
    font-size: var(--font-size-lg);
  }

  .value-number {
    font-size: var(--font-size-lg);
  }

  .data-item {
    padding: var(--spacing-2);
  }
}

@media (min-width: 1920px) {
  .analysis-history-page {
    padding: var(--spacing-8);
  }

  .chart-container {
    height: 540px;
  }

  .chart-loading,
  .chart-empty {
    height: 540px;
  }

  .compare-chart,
  .overlay-chart {
    height: 620px;
  }

  .page-title {
    font-size: var(--font-size-3xl);
  }

  .header-icon {
    font-size: 48px;
  }

  .stat-value {
    font-size: var(--font-size-3xl);
  }
}

/* ==================== 打印样式 ==================== */
@media print {
  .page-header {
    background: var(--color-secondary-600);
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }

  .header-right {
    display: none;
  }

  .chart-container::before,
  .compare-chart::before,
  .overlay-chart::before {
    display: none;
  }
}
</style>
