<template>
  <div class="audit-log-stats">
    <!-- 统计概览卡片 -->
    <el-row
      :gutter="24"
      class="overview-cards"
    >
      <el-col
        :xs="12"
        :sm="6"
        :md="4"
      >
        <div class="stat-card total">
          <div class="stat-icon">
            <el-icon><Document /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">
              {{ formatNumber(statistics.total_logs) }}
            </div>
            <div class="stat-label">
              总记录数
            </div>
          </div>
        </div>
      </el-col>

      <el-col
        :xs="12"
        :sm="6"
        :md="4"
      >
        <div class="stat-card today">
          <div class="stat-icon">
            <el-icon><Clock /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">
              {{ formatNumber(statistics.today_logs) }}
            </div>
            <div class="stat-label">
              今日记录
            </div>
          </div>
        </div>
      </el-col>

      <el-col
        :xs="12"
        :sm="6"
        :md="4"
      >
        <div class="stat-card success">
          <div class="stat-icon">
            <el-icon><CircleCheck /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">
              {{ formatNumber(getSuccessCount()) }}
            </div>
            <div class="stat-label">
              成功请求
            </div>
          </div>
        </div>
      </el-col>

      <el-col
        :xs="12"
        :sm="6"
        :md="4"
      >
        <div class="stat-card error">
          <div class="stat-icon">
            <el-icon><CircleClose /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">
              {{ formatNumber(getErrorCount()) }}
            </div>
            <div class="stat-label">
              错误请求
            </div>
          </div>
        </div>
      </el-col>

      <el-col
        :xs="12"
        :sm="6"
        :md="4"
      >
        <div class="stat-card rate">
          <div class="stat-icon">
            <el-icon><TrendCharts /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">
              {{ getSuccessRate() }}%
            </div>
            <div class="stat-label">
              成功率
            </div>
          </div>
        </div>
      </el-col>

      <el-col
        :xs="12"
        :sm="6"
        :md="4"
      >
        <div class="stat-card avg-time">
          <div class="stat-icon">
            <el-icon><Timer /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">
              {{ getAvgDuration() }}ms
            </div>
            <div class="stat-label">
              平均耗时
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row
      :gutter="24"
      class="charts-row"
    >
      <!-- 操作类型分布 -->
      <el-col
        :xs="24"
        :lg="12"
      >
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">操作类型分布</span>
              <el-radio-group
                v-model="chartType.operation"
                size="small"
              >
                <el-radio-button label="pie">
                  饼图
                </el-radio-button>
                <el-radio-button label="bar">
                  柱状图
                </el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div
            ref="operationChartRef"
            class="chart-container"
          />
        </el-card>
      </el-col>

      <!-- 分类统计 -->
      <el-col
        :xs="24"
        :lg="12"
      >
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">操作分类统计</span>
              <el-radio-group
                v-model="chartType.category"
                size="small"
              >
                <el-radio-button label="pie">
                  饼图
                </el-radio-button>
                <el-radio-button label="bar">
                  柱状图
                </el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div
            ref="categoryChartRef"
            class="chart-container"
          />
        </el-card>
      </el-col>

      <!-- 时间分布趋势 -->
      <el-col
        :xs="24"
        :lg="12"
      >
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">时间分布趋势</span>
              <el-radio-group
                v-model="chartType.time"
                size="small"
                @change="handleTimeChartChange"
              >
                <el-radio-button label="hour">
                  按小时
                </el-radio-button>
                <el-radio-button label="day">
                  按天
                </el-radio-button>
                <el-radio-button label="week">
                  按周
                </el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div
            ref="timeChartRef"
            class="chart-container"
          />
        </el-card>
      </el-col>

      <!-- 用户活动统计 -->
      <el-col
        :xs="24"
        :lg="12"
      >
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">用户活动统计 TOP 10</span>
              <el-button
                size="small"
                @click="handleExportUserStats"
              >
                <el-icon><Download /></el-icon>
                导出
              </el-button>
            </div>
          </template>
          <div
            ref="userChartRef"
            class="chart-container"
          />
        </el-card>
      </el-col>

      <!-- 设备使用统计 -->
      <el-col
        :xs="24"
        :lg="12"
      >
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">设备使用统计</span>
            </div>
          </template>
          <div
            ref="deviceChartRef"
            class="chart-container"
          />
        </el-card>
      </el-col>

      <!-- 响应状态分布 -->
      <el-col
        :xs="24"
        :lg="12"
      >
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">响应状态分布</span>
            </div>
          </template>
          <div
            ref="statusChartRef"
            class="chart-container"
          />
        </el-card>
      </el-col>
    </el-row>

    <!-- 报表生成 -->
    <el-card class="report-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">报表生成</span>
        </div>
      </template>
      
      <el-form
        :model="reportForm"
        label-width="100px"
        class="report-form"
      >
        <el-row :gutter="24">
          <el-col
            :xs="24"
            :sm="12"
            :md="8"
          >
            <el-form-item label="报表类型">
              <el-select
                v-model="reportForm.report_type"
                class="form-select"
              >
                <el-option
                  label="汇总报表"
                  value="summary"
                />
                <el-option
                  label="详细报表"
                  value="detail"
                />
                <el-option
                  label="趋势分析"
                  value="trend"
                />
                <el-option
                  label="用户活动"
                  value="user_activity"
                />
                <el-option
                  label="设备使用"
                  value="device_usage"
                />
              </el-select>
            </el-form-item>
          </el-col>

          <el-col
            :xs="24"
            :sm="12"
            :md="8"
          >
            <el-form-item label="时间范围">
              <el-date-picker
                v-model="reportForm.timeRange"
                type="datetimerange"
                range-separator="至"
                start-placeholder="开始时间"
                end-placeholder="结束时间"
                format="YYYY-MM-DD HH:mm:ss"
                value-format="YYYY-MM-DDTHH:mm:ss"
                class="form-date-picker"
              />
            </el-form-item>
          </el-col>

          <el-col
            :xs="24"
            :sm="12"
            :md="8"
          >
            <el-form-item label="输出格式">
              <el-select
                v-model="reportForm.format"
                class="form-select"
              >
                <el-option
                  label="PDF"
                  value="pdf"
                />
                <el-option
                  label="Excel"
                  value="excel"
                />
                <el-option
                  label="Word"
                  value="word"
                />
              </el-select>
            </el-form-item>
          </el-col>

          <el-col
            :xs="24"
            :sm="24"
            :md="24"
          >
            <el-form-item label="包含内容">
              <el-checkbox-group v-model="reportForm.includes">
                <el-checkbox label="overview">
                  统计概览
                </el-checkbox>
                <el-checkbox label="operation">
                  操作类型分析
                </el-checkbox>
                <el-checkbox label="category">
                  分类统计
                </el-checkbox>
                <el-checkbox label="user">
                  用户活动
                </el-checkbox>
                <el-checkbox label="device">
                  设备使用
                </el-checkbox>
                <el-checkbox label="trend">
                  趋势分析
                </el-checkbox>
              </el-checkbox-group>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item>
          <el-button
            type="primary"
            :loading="generating"
            @click="handleGenerateReport"
          >
            <el-icon><Document /></el-icon>
            生成报表
          </el-button>
          <el-button @click="handlePreviewReport">
            <el-icon><View /></el-icon>
            预览
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 报表预览对话框 -->
    <el-dialog
      v-model="previewVisible"
      title="报表预览"
      width="80%"
      top="5vh"
      class="preview-dialog"
      destroy-on-close
    >
      <div
        class="preview-content"
        v-html="previewContent"
      />
      <template #footer>
        <el-button @click="previewVisible = false">
          关闭
        </el-button>
        <el-button
          type="primary"
          @click="handleDownloadReport"
        >
          <el-icon><Download /></el-icon>
          下载
        </el-button>
        <el-button
          type="success"
          @click="handlePrintReport"
        >
          <el-icon><Printer /></el-icon>
          打印
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * @file AuditLogStats.vue
 * @path src/components/
 * @description 审计日志统计和报表组件，提供操作类型统计、用户活动统计、时间分布分析等功能
 * @author Frontend Engineer Agent
 * @date 2026-03-07
 * @dependencies vue, element-plus, echarts, stores/audit
 */

import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { useAuditStore } from '../stores/audit'

// ==================== Store 实例 ====================

const auditStore = useAuditStore()

// ==================== 图表引用 ====================

const operationChartRef = ref(null)
const categoryChartRef = ref(null)
const timeChartRef = ref(null)
const userChartRef = ref(null)
const deviceChartRef = ref(null)
const statusChartRef = ref(null)

/** 图表实例 */
let operationChart = null
let categoryChart = null
let timeChart = null
let userChart = null
let deviceChart = null
let statusChart = null

// ==================== 本地状态 ====================

/** 图表类型选择 */
const chartType = reactive({
  operation: 'pie',
  category: 'pie',
  time: 'hour'
})

/** 报表表单 */
const reportForm = reactive({
  report_type: 'summary',
  timeRange: null,
  format: 'pdf',
  includes: ['overview', 'operation', 'category', 'user', 'device', 'trend']
})

/** 生成报表状态 */
const generating = ref(false)

/** 预览对话框 */
const previewVisible = ref(false)
const previewContent = ref('')

// ==================== 计算属性 ====================

/** 统计数据 */
const statistics = computed(() => auditStore.statistics)

// ==================== 统计计算方法 ====================

/**
 * 格式化数字
 * 
 * @param {number} num - 数字
 * @returns {string} 格式化后的字符串
 */
function formatNumber(num) {
  if (!num || num === 0) return '0'
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + 'w'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  return num.toString()
}

/**
 * 获取成功请求数量
 * 
 * @returns {number} 成功请求数量
 */
function getSuccessCount() {
  const stats = statistics.value.operation_type_stats || {}
  let count = 0
  Object.keys(stats).forEach(key => {
    if (key.startsWith('2')) {
      count += stats[key] || 0
    }
  })
  return count
}

/**
 * 获取错误请求数量
 * 
 * @returns {number} 错误请求数量
 */
function getErrorCount() {
  const stats = statistics.value.operation_type_stats || {}
  let count = 0
  Object.keys(stats).forEach(key => {
    if (key.startsWith('4') || key.startsWith('5')) {
      count += stats[key] || 0
    }
  })
  return count
}

/**
 * 获取成功率
 * 
 * @returns {string} 成功率百分比
 */
function getSuccessRate() {
  const total = statistics.value.total_logs
  if (!total || total === 0) return '0.0'
  const success = getSuccessCount()
  return ((success / total) * 100).toFixed(1)
}

/**
 * 获取平均耗时
 * 
 * @returns {number} 平均耗时(ms)
 */
function getAvgDuration() {
  // 从统计数据中获取平均耗时，如果没有则返回0
  return statistics.value.avg_duration || 0
}

// ==================== 图表初始化 ====================

/**
 * 初始化所有图表
 */
function initCharts() {
  nextTick(() => {
    initOperationChart()
    initCategoryChart()
    initTimeChart()
    initUserChart()
    initDeviceChart()
    initStatusChart()
  })
}

/**
 * 初始化操作类型图表
 */
function initOperationChart() {
  if (!operationChartRef.value) return
  
  if (operationChart) {
    operationChart.dispose()
  }
  
  operationChart = echarts.init(operationChartRef.value)
  updateOperationChart()
}

/**
 * 更新操作类型图表
 */
function updateOperationChart() {
  if (!operationChart) return
  
  const data = statistics.value.operation_type_stats || {}
  const chartData = Object.entries(data).map(([name, value]) => ({
    name: getOperationName(name),
    value
  }))
  
  const option = chartType.operation === 'pie' ? getPieOption(chartData) : getBarOption(chartData)
  operationChart.setOption(option)
}

/**
 * 初始化分类图表
 */
function initCategoryChart() {
  if (!categoryChartRef.value) return
  
  if (categoryChart) {
    categoryChart.dispose()
  }
  
  categoryChart = echarts.init(categoryChartRef.value)
  updateCategoryChart()
}

/**
 * 更新分类图表
 */
function updateCategoryChart() {
  if (!categoryChart) return
  
  const data = statistics.value.category_stats || {}
  const chartData = Object.entries(data).map(([name, value]) => ({
    name: getCategoryName(name),
    value
  }))
  
  const option = chartType.category === 'pie' ? getPieOption(chartData) : getBarOption(chartData)
  categoryChart.setOption(option)
}

/**
 * 初始化时间分布图表
 */
function initTimeChart() {
  if (!timeChartRef.value) return
  
  if (timeChart) {
    timeChart.dispose()
  }
  
  timeChart = echarts.init(timeChartRef.value)
  updateTimeChart()
}

/**
 * 更新时间分布图表
 */
async function updateTimeChart() {
  if (!timeChart) return
  
  // 根据选择的时间类型获取数据
  const groupBy = chartType.time
  const data = statistics.value.daily_trend || []
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: data.map(item => item.time)
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        name: '请求数',
        type: 'line',
        smooth: true,
        areaStyle: {
          opacity: 0.3
        },
        data: data.map(item => item.count)
      }
    ]
  }
  
  timeChart.setOption(option)
}

/**
 * 初始化用户活动图表
 */
function initUserChart() {
  if (!userChartRef.value) return
  
  if (userChart) {
    userChart.dispose()
  }
  
  userChart = echarts.init(userChartRef.value)
  updateUserChart()
}

/**
 * 更新用户活动图表
 */
function updateUserChart() {
  if (!userChart) return
  
  const data = statistics.value.user_stats || {}
  const sortedData = Object.entries(data)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([name, value]) => ({
      name: getUserName(name),
      value
    }))
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'value'
    },
    yAxis: {
      type: 'category',
      data: sortedData.map(item => item.name).reverse()
    },
    series: [
      {
        name: '操作次数',
        type: 'bar',
        data: sortedData.map(item => item.value).reverse(),
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#83bff6' },
            { offset: 0.5, color: '#188df0' },
            { offset: 1, color: '#188df0' }
          ])
        }
      }
    ]
  }
  
  userChart.setOption(option)
}

/**
 * 初始化设备使用图表
 */
function initDeviceChart() {
  if (!deviceChartRef.value) return
  
  if (deviceChart) {
    deviceChart.dispose()
  }
  
  deviceChart = echarts.init(deviceChartRef.value)
  updateDeviceChart()
}

/**
 * 更新设备使用图表
 */
function updateDeviceChart() {
  if (!deviceChart) return
  
  const data = statistics.value.device_stats || {}
  const chartData = Object.entries(data).map(([name, value]) => ({
    name: getDeviceName(name),
    value
  }))
  
  const option = getPieOption(chartData)
  deviceChart.setOption(option)
}

/**
 * 初始化响应状态图表
 */
function initStatusChart() {
  if (!statusChartRef.value) return
  
  if (statusChart) {
    statusChart.dispose()
  }
  
  statusChart = echarts.init(statusChartRef.value)
  updateStatusChart()
}

/**
 * 更新响应状态图表
 */
function updateStatusChart() {
  if (!statusChart) return
  
  const data = statistics.value.operation_type_stats || {}
  const chartData = Object.entries(data).map(([code, count]) => ({
    name: getStatusName(code),
    value: count
  }))
  
  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left'
    },
    series: [
      {
        name: '响应状态',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          formatter: '{b}: {c}'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 16,
            fontWeight: 'bold'
          }
        },
        data: chartData
      }
    ]
  }
  
  statusChart.setOption(option)
}

// ==================== 图表配置 ====================

/**
 * 获取饼图配置
 * 
 * @param {Array} data - 图表数据
 * @returns {Object} ECharts配置对象
 */
function getPieOption(data) {
  return {
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left',
      top: 'middle'
    },
    series: [
      {
        name: '统计',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          formatter: '{b}: {c}'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 16,
            fontWeight: 'bold'
          }
        },
        data: data
      }
    ]
  }
}

/**
 * 获取柱状图配置
 * 
 * @param {Array} data - 图表数据
 * @returns {Object} ECharts配置对象
 */
function getBarOption(data) {
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: data.map(item => item.name),
      axisLabel: {
        interval: 0,
        rotate: 30
      }
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        name: '数量',
        type: 'bar',
        data: data.map(item => item.value),
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#83bff6' },
            { offset: 0.5, color: '#188df0' },
            { offset: 1, color: '#188df0' }
          ])
        }
      }
    ]
  }
}

// ==================== 事件处理 ====================

/**
 * 时间图表类型变更
 */
function handleTimeChartChange() {
  updateTimeChart()
}

/**
 * 导出用户统计
 */
function handleExportUserStats() {
  const data = statistics.value.user_stats || {}
  const csvContent = '用户ID,操作次数\n' + 
    Object.entries(data).map(([id, count]) => `${id},${count}`).join('\n')
  
  downloadFile(csvContent, 'user_stats.csv', 'text/csv')
}

/**
 * 生成报表
 */
async function handleGenerateReport() {
  generating.value = true
  
  try {
    const params = {
      report_type: reportForm.report_type,
      format: reportForm.format,
      includes: reportForm.includes
    }
    
    if (reportForm.timeRange && reportForm.timeRange.length === 2) {
      params.start_time = reportForm.timeRange[0]
      params.end_time = reportForm.timeRange[1]
    }
    
    const result = await auditStore.generateReport(params)
    
    if (result) {
      downloadFile(result, `audit_report_${Date.now()}.${reportForm.format}`, getMimeType(reportForm.format))
      ElMessage.success('报表生成成功')
    }
  } catch (error) {
    console.error('Failed to generate report:', error)
    ElMessage.error('报表生成失败')
  } finally {
    generating.value = false
  }
}

/**
 * 预览报表
 */
async function handlePreviewReport() {
  // 生成HTML预览内容
  previewContent.value = generatePreviewHTML()
  previewVisible.value = true
}

/**
 * 生成预览HTML
 * 
 * @returns {string} HTML内容
 */
function generatePreviewHTML() {
  return `
    <div style="padding: 20px; font-family: Arial, sans-serif;">
      <h1 style="text-align: center; color: #333;">审计日志统计报表</h1>
      <p style="text-align: center; color: #666;">生成时间: ${new Date().toLocaleString('zh-CN')}</p>
      
      <h2 style="margin-top: 30px; color: #409EFF;">统计概览</h2>
      <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
        <tr style="background-color: #f5f7fa;">
          <th style="padding: 12px; border: 1px solid #ddd; text-align: left;">指标</th>
          <th style="padding: 12px; border: 1px solid #ddd; text-align: right;">数值</th>
        </tr>
        <tr>
          <td style="padding: 12px; border: 1px solid #ddd;">总记录数</td>
          <td style="padding: 12px; border: 1px solid #ddd; text-align: right;">${statistics.value.total_logs}</td>
        </tr>
        <tr>
          <td style="padding: 12px; border: 1px solid #ddd;">今日记录</td>
          <td style="padding: 12px; border: 1px solid #ddd; text-align: right;">${statistics.value.today_logs}</td>
        </tr>
        <tr>
          <td style="padding: 12px; border: 1px solid #ddd;">成功请求</td>
          <td style="padding: 12px; border: 1px solid #ddd; text-align: right;">${getSuccessCount()}</td>
        </tr>
        <tr>
          <td style="padding: 12px; border: 1px solid #ddd;">错误请求</td>
          <td style="padding: 12px; border: 1px solid #ddd; text-align: right;">${getErrorCount()}</td>
        </tr>
        <tr>
          <td style="padding: 12px; border: 1px solid #ddd;">成功率</td>
          <td style="padding: 12px; border: 1px solid #ddd; text-align: right;">${getSuccessRate()}%</td>
        </tr>
      </table>
      
      <h2 style="margin-top: 30px; color: #409EFF;">操作类型分布</h2>
      <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
        <tr style="background-color: #f5f7fa;">
          <th style="padding: 12px; border: 1px solid #ddd; text-align: left;">操作类型</th>
          <th style="padding: 12px; border: 1px solid #ddd; text-align: right;">次数</th>
        </tr>
        ${Object.entries(statistics.value.operation_type_stats || {}).map(([type, count]) => `
          <tr>
            <td style="padding: 12px; border: 1px solid #ddd;">${getOperationName(type)}</td>
            <td style="padding: 12px; border: 1px solid #ddd; text-align: right;">${count}</td>
          </tr>
        `).join('')}
      </table>
    </div>
  `
}

/**
 * 下载报表
 */
function handleDownloadReport() {
  handleGenerateReport()
}

/**
 * 打印报表
 */
function handlePrintReport() {
  const printWindow = window.open('', '_blank')
  printWindow.document.write(`
    <html>
      <head>
        <title>审计日志统计报表</title>
        <style>
          body { font-family: Arial, sans-serif; padding: 20px; }
          h1 { text-align: center; color: #333; }
          h2 { margin-top: 30px; color: #409EFF; }
          table { width: 100%; border-collapse: collapse; margin-top: 15px; }
          th, td { padding: 12px; border: 1px solid #ddd; }
          th { background-color: #f5f7fa; text-align: left; }
        </style>
      </head>
      <body>
        ${previewContent.value}
      </body>
    </html>
  `)
  printWindow.document.close()
  printWindow.print()
}

// ==================== 辅助方法 ====================

/**
 * 获取操作名称
 * 
 * @param {string} type - 操作类型
 * @returns {string} 操作名称
 */
function getOperationName(type) {
  const op = auditStore.operationTypes.find(o => o.type === type)
  return op?.description || type
}

/**
 * 获取分类名称
 * 
 * @param {string} category - 分类代码
 * @returns {string} 分类名称
 */
function getCategoryName(category) {
  const cat = auditStore.categories.find(c => c.code === category)
  return cat?.name || category
}

/**
 * 获取用户名称
 * 
 * @param {string} userId - 用户ID
 * @returns {string} 用户名称
 */
function getUserName(userId) {
  const user = auditStore.userList.find(u => u.id === userId)
  return user?.name || userId
}

/**
 * 获取设备名称
 * 
 * @param {string} deviceId - 设备ID
 * @returns {string} 设备名称
 */
function getDeviceName(deviceId) {
  const device = auditStore.deviceList.find(d => d.id === deviceId)
  return device?.name || deviceId
}

/**
 * 获取状态名称
 * 
 * @param {string} code - 状态码
 * @returns {string} 状态名称
 */
function getStatusName(code) {
  const statusNames = {
    '2xx': '成功 (2xx)',
    '3xx': '重定向 (3xx)',
    '4xx': '客户端错误 (4xx)',
    '5xx': '服务器错误 (5xx)'
  }
  return statusNames[code] || code
}

/**
 * 获取MIME类型
 * 
 * @param {string} format - 文件格式
 * @returns {string} MIME类型
 */
function getMimeType(format) {
  const mimeTypes = {
    pdf: 'application/pdf',
    excel: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    word: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    csv: 'text/csv'
  }
  return mimeTypes[format] || 'application/octet-stream'
}

/**
 * 下载文件
 * 
 * @param {Blob|string} content - 文件内容
 * @param {string} filename - 文件名
 * @param {string} mimeType - MIME类型
 */
function downloadFile(content, filename, mimeType) {
  const blob = content instanceof Blob ? content : new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * 调整图表大小
 */
function resizeCharts() {
  operationChart?.resize()
  categoryChart?.resize()
  timeChart?.resize()
  userChart?.resize()
  deviceChart?.resize()
  statusChart?.resize()
}

// ==================== 监听器 ====================

watch(() => chartType.operation, () => {
  updateOperationChart()
})

watch(() => chartType.category, () => {
  updateCategoryChart()
})

watch(() => statistics.value, () => {
  updateOperationChart()
  updateCategoryChart()
  updateTimeChart()
  updateUserChart()
  updateDeviceChart()
  updateStatusChart()
}, { deep: true })

// ==================== 生命周期 ====================

onMounted(() => {
  initCharts()
  window.addEventListener('resize', resizeCharts)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeCharts)
  operationChart?.dispose()
  categoryChart?.dispose()
  timeChart?.dispose()
  userChart?.dispose()
  deviceChart?.dispose()
  statusChart?.dispose()
})
</script>

<style scoped>
.audit-log-stats {
  padding: var(--spacing-4);
}

.overview-cards {
  margin-bottom: var(--spacing-4);
}

.stat-card {
  display: flex;
  align-items: center;
  padding: var(--spacing-4);
  background-color: var(--color-surface-primary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  transition: var(--transition-all);
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.stat-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  margin-right: var(--spacing-3);
  font-size: 24px;
}

.stat-card.total .stat-icon {
  background-color: var(--color-primary-100);
  color: var(--color-primary-500);
}

.stat-card.today .stat-icon {
  background-color: var(--color-info-100);
  color: var(--color-info-500);
}

.stat-card.success .stat-icon {
  background-color: var(--color-success-100);
  color: var(--color-success);
}

.stat-card.error .stat-icon {
  background-color: var(--color-error-100);
  color: var(--color-error);
}

.stat-card.rate .stat-icon {
  background-color: var(--color-warning-100);
  color: var(--color-warning);
}

.stat-card.avg-time .stat-icon {
  background-color: var(--color-purple-100);
  color: var(--color-purple-500);
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  font-family: var(--font-family-mono);
}

.stat-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-top: var(--spacing-1);
}

.charts-row {
  margin-bottom: var(--spacing-4);
}

.chart-card {
  margin-bottom: var(--spacing-4);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.chart-container {
  width: 100%;
  height: 300px;
}

.report-card {
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
}

.report-form {
  margin-bottom: 0;
}

.form-select,
.form-date-picker {
  width: 100%;
}

.preview-dialog {
  border-radius: var(--radius-lg);
}

.preview-content {
  max-height: 70vh;
  overflow-y: auto;
  padding: var(--spacing-4);
  background-color: var(--color-surface-primary);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .audit-log-stats {
    padding: var(--spacing-2);
  }

  .stat-card {
    padding: var(--spacing-3);
  }

  .stat-icon {
    width: 40px;
    height: 40px;
    font-size: 20px;
  }

  .stat-value {
    font-size: var(--font-size-xl);
  }

  .chart-container {
    height: 250px;
  }
}
</style>
