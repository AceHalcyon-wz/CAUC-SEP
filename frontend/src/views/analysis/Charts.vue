<template>
  <div class="analysis-charts-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <el-icon class="header-icon">
          <PieChart />
        </el-icon>
        <div class="header-content">
          <h1 class="page-title">
            图表分析
          </h1>
          <p class="page-subtitle">
            多维度数据可视化分析，支持自定义图表配置
          </p>
        </div>
      </div>
      <div class="header-right">
        <el-button-group>
          <el-button 
            :type="viewMode === 'analysis' ? 'primary' : 'default'"
            @click="viewMode = 'analysis'"
          >
            数据分析
          </el-button>
          <el-button 
            :type="viewMode === 'comparison' ? 'primary' : 'default'"
            @click="viewMode = 'comparison'"
          >
            数据对比
          </el-button>
          <el-button 
            :type="viewMode === 'advanced' ? 'primary' : 'default'"
            @click="viewMode = 'advanced'"
          >
            高级图表
          </el-button>
        </el-button-group>
        <el-button
          type="primary"
          :icon="Plus"
          @click="createNewChart"
        >
          新建图表
        </el-button>
      </div>
    </div>

    <!-- 数据分析视图 -->
    <transition
      name="fade"
      mode="out-in"
    >
      <div
        v-if="viewMode === 'analysis'"
        key="analysis"
      >
        <DataAnalysis />
      </div>

      <!-- 高级图表视图 -->
      <div
        v-else-if="viewMode === 'advanced'"
        key="advanced"
        class="advanced-view"
      >
        <el-row :gutter="24">
          <!-- 左侧：数据源配置 -->
          <el-col
            :xs="24"
            :sm="24"
            :md="8"
            :lg="6"
          >
            <el-card class="data-source-card">
              <template #header>
                <div class="card-header">
                  <el-icon><Coin /></el-icon>
                  <span>数据源配置</span>
                </div>
              </template>
              
              <el-form
                label-width="80px"
                size="small"
              >
                <el-form-item label="数据来源">
                  <el-select
                    v-model="dataSource"
                    style="width: 100%"
                  >
                    <el-option
                      label="生成示例数据"
                      value="demo"
                    />
                    <el-option
                      label="导入CSV文件"
                      value="import"
                    />
                    <el-option
                      label="实时数据"
                      value="realtime"
                    />
                  </el-select>
                </el-form-item>
                
                <el-form-item
                  v-if="dataSource === 'demo'"
                  label="数据点数"
                >
                  <el-input-number 
                    v-model="dataPointCount" 
                    :min="100" 
                    :max="100000" 
                    :step="100"
                    style="width: 100%" 
                  />
                </el-form-item>
                
                <el-form-item
                  v-if="dataSource === 'demo'"
                  label="噪声强度"
                >
                  <el-slider
                    v-model="noiseLevel"
                    :min="0"
                    :max="100"
                  />
                </el-form-item>
                
                <el-form-item
                  v-if="dataSource === 'demo'"
                  label="数据系列"
                >
                  <el-input-number 
                    v-model="seriesCount" 
                    :min="1" 
                    :max="6" 
                    style="width: 100%" 
                  />
                </el-form-item>
                
                <el-form-item v-if="dataSource === 'import'">
                  <el-upload
                    :auto-upload="false"
                    :show-file-list="false"
                    accept=".csv"
                    :on-change="handleFileUpload"
                  >
                    <el-button
                      type="primary"
                      style="width: 100%"
                    >
                      <el-icon><Upload /></el-icon>
                      选择CSV文件
                    </el-button>
                  </el-upload>
                </el-form-item>
                
                <el-form-item>
                  <el-button 
                    type="success" 
                    style="width: 100%"
                    :loading="isGenerating"
                    @click="generateData"
                  >
                    生成数据
                  </el-button>
                </el-form-item>
              </el-form>
            </el-card>

            <!-- 配置模板 -->
            <el-card class="template-card">
              <template #header>
                <div class="card-header">
                  <el-icon><Document /></el-icon>
                  <span>配置模板</span>
                </div>
              </template>
              
              <div class="template-list">
                <div
                  v-for="template in configTemplates"
                  :key="template.id"
                  class="template-item"
                  @click="applyTemplate(template)"
                >
                  <div class="template-info">
                    <el-icon><Files /></el-icon>
                    <div class="template-details">
                      <div class="template-name">
                        {{ template.name }}
                      </div>
                      <div class="template-meta">
                        <span>{{ template.chartType }}</span>
                      </div>
                    </div>
                  </div>
                  <el-button
                    type="danger"
                    size="small"
                    text
                    @click.stop="deleteTemplate(template.id)"
                  >
                    删除
                  </el-button>
                </div>
                
                <el-empty 
                  v-if="configTemplates.length === 0" 
                  description="暂无模板"
                  :image-size="60"
                />
              </div>
            </el-card>
          </el-col>

          <!-- 右侧：高级图表 -->
          <el-col
            :xs="24"
            :sm="24"
            :md="16"
            :lg="18"
          >
            <ChartAnalysis
              ref="chartAnalysisRef"
              :data="chartData"
              :initial-chart-type="chartType"
              :show-toolbar="true"
              :enable-annotation="true"
              height="600px"
              @chart-click="handleChartClick"
              @annotation-add="handleAnnotationAdd"
              @config-change="handleConfigChange"
            />
          </el-col>
        </el-row>
      </div>

      <!-- 数据对比视图 -->
      <div
        v-else
        key="comparison"
        class="comparison-view"
      >
        <el-row :gutter="24">
          <!-- 左侧：图表选择 -->
          <el-col
            :xs="24"
            :sm="24"
            :md="8"
            :lg="6"
          >
            <el-card class="chart-selector-card">
              <template #header>
                <div class="card-header">
                  <el-icon><List /></el-icon>
                  <span>图表列表</span>
                </div>
              </template>
              
              <div class="chart-list">
                <div
                  v-for="chart in chartList"
                  :key="chart.id"
                  class="chart-item"
                  :class="{ active: selectedCharts.includes(chart.id) }"
                  @click="toggleChartSelection(chart.id)"
                >
                  <div class="chart-info">
                    <el-icon><TrendCharts /></el-icon>
                    <div class="chart-details">
                      <div class="chart-name">
                        {{ chart.name }}
                      </div>
                      <div class="chart-meta">
                        <span>{{ chart.type }}</span>
                        <span>{{ chart.dataPoints }} 点</span>
                      </div>
                    </div>
                  </div>
                  <el-checkbox 
                    :model-value="selectedCharts.includes(chart.id)"
                    @click.stop
                    @change="toggleChartSelection(chart.id)"
                  />
                </div>
              </div>

              <el-divider />

              <el-button 
                type="primary" 
                :icon="Plus" 
                style="width: 100%"
                @click="createNewChart"
              >
                添加新图表
              </el-button>
            </el-card>

            <!-- 对比设置 -->
            <el-card class="comparison-settings-card">
              <template #header>
                <div class="card-header">
                  <el-icon><Setting /></el-icon>
                  <span>对比设置</span>
                </div>
              </template>
              
              <el-form
                label-width="80px"
                size="small"
              >
                <el-form-item label="对比方式">
                  <el-select
                    v-model="comparisonMode"
                    style="width: 100%"
                  >
                    <el-option
                      label="叠加显示"
                      value="overlay"
                    />
                    <el-option
                      label="并列显示"
                      value="sideBySide"
                    />
                    <el-option
                      label="差值显示"
                      value="difference"
                    />
                  </el-select>
                </el-form-item>
                <el-form-item label="归一化">
                  <el-switch v-model="normalize" />
                </el-form-item>
                <el-form-item label="显示网格">
                  <el-switch v-model="showGrid" />
                </el-form-item>
                <el-form-item label="同步缩放">
                  <el-switch v-model="syncZoom" />
                </el-form-item>
              </el-form>
            </el-card>
          </el-col>

          <!-- 右侧：对比图表 -->
          <el-col
            :xs="24"
            :sm="24"
            :md="16"
            :lg="18"
          >
            <el-card class="comparison-chart-card">
              <template #header>
                <div class="card-header">
                  <el-icon><DataAnalysis /></el-icon>
                  <span>数据对比</span>
                  <div class="chart-actions">
                    <el-button 
                      type="primary" 
                      size="small" 
                      :icon="Download"
                      :disabled="selectedCharts.length === 0"
                      @click="exportComparison"
                    >
                      导出对比图
                    </el-button>
                    <el-button 
                      type="warning" 
                      size="small" 
                      :icon="Delete"
                      :disabled="selectedCharts.length === 0"
                      @click="clearSelection"
                    >
                      清除选择
                    </el-button>
                  </div>
                </div>
              </template>
              
              <div
                v-if="selectedCharts.length === 0"
                class="empty-state"
              >
                <el-icon :size="64">
                  <PieChart />
                </el-icon>
                <p>请从左侧选择要对比的图表</p>
                <p class="hint">
                  支持多选，最多可同时对比 4 个图表
                </p>
              </div>
              
              <div
                v-else
                ref="comparisonChartRef"
                class="chart-container"
              />
            </el-card>

            <!-- 对比统计 -->
            <el-card
              v-if="selectedCharts.length > 0"
              class="comparison-stats-card"
            >
              <template #header>
                <div class="card-header">
                  <el-icon><DataLine /></el-icon>
                  <span>对比统计</span>
                </div>
              </template>
              
              <el-table
                :data="comparisonStats"
                border
                style="width: 100%"
              >
                <el-table-column
                  prop="name"
                  label="图表名称"
                  width="150"
                />
                <el-table-column
                  prop="max"
                  label="最大值"
                  width="120"
                >
                  <template #default="{ row }">
                    <span class="mono">{{ row.max.toFixed(3) }}</span>
                  </template>
                </el-table-column>
                <el-table-column
                  prop="min"
                  label="最小值"
                  width="120"
                >
                  <template #default="{ row }">
                    <span class="mono">{{ row.min.toFixed(3) }}</span>
                  </template>
                </el-table-column>
                <el-table-column
                  prop="avg"
                  label="平均值"
                  width="120"
                >
                  <template #default="{ row }">
                    <span class="mono">{{ row.avg.toFixed(3) }}</span>
                  </template>
                </el-table-column>
                <el-table-column
                  prop="std"
                  label="标准差"
                  width="120"
                >
                  <template #default="{ row }">
                    <span class="mono">{{ row.std.toFixed(3) }}</span>
                  </template>
                </el-table-column>
                <el-table-column
                  prop="range"
                  label="极差"
                  width="120"
                >
                  <template #default="{ row }">
                    <span class="mono">{{ row.range.toFixed(3) }}</span>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </transition>

    <!-- 新建图表对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      title="新建图表"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form
        :model="newChartForm"
        label-width="100px"
      >
        <el-form-item
          label="图表名称"
          required
        >
          <el-input
            v-model="newChartForm.name"
            placeholder="请输入图表名称"
          />
        </el-form-item>
        <el-form-item
          label="图表类型"
          required
        >
          <el-select
            v-model="newChartForm.type"
            style="width: 100%"
          >
            <el-option
              label="折线图"
              value="line"
            />
            <el-option
              label="柱状图"
              value="bar"
            />
            <el-option
              label="散点图"
              value="scatter"
            />
            <el-option
              label="面积图"
              value="area"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="数据来源">
          <el-select
            v-model="newChartForm.dataSource"
            style="width: 100%"
          >
            <el-option
              label="实时数据"
              value="realtime"
            />
            <el-option
              label="历史数据"
              value="history"
            />
            <el-option
              label="导入文件"
              value="import"
            />
          </el-select>
        </el-form-item>
        <el-form-item
          v-if="newChartForm.dataSource === 'history'"
          label="时间范围"
        >
          <el-date-picker
            v-model="newChartForm.timeRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input 
            v-model="newChartForm.description" 
            type="textarea" 
            :rows="3"
            placeholder="请输入图表备注信息"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="handleCreateChart"
        >
          创建图表
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * @file Charts.vue
 * @path src/views/analysis/
 * @description 图表分析页面，集成DataAnalysis组件、高级图表分析和数据对比功能
 * @author Agent
 * @date 2024-03-07
 */

import { ref, reactive, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { DataAnalysis, ChartAnalysis } from '@/components/analysis'
import {
  PieChart,
  Plus,
  Download,
  Delete,
  List,
  TrendCharts,
  Setting,
  DataAnalysis as DataAnalysisIcon,
  DataLine,
  Coin,
  Upload,
  Document,
  Files
} from '@element-plus/icons-vue'

/** 视图模式 */
const viewMode = ref('analysis')

/** 图表分析组件引用 */
const chartAnalysisRef = ref(null)

/** 数据源类型 */
const dataSource = ref('demo')

/** 数据点数量 */
const dataPointCount = ref(1000)

/** 噪声强度 */
const noiseLevel = ref(20)

/** 数据系列数量 */
const seriesCount = ref(2)

/** 是否正在生成数据 */
const isGenerating = ref(false)

/** 图表数据 */
const chartData = ref([])

/** 图表类型 */
const chartType = ref('line')

/** 配置模板列表 */
const configTemplates = ref([])

/** 图表列表 */
const chartList = ref([
  { id: 1, name: '电机位置曲线', type: '折线图', dataPoints: 120 },
  { id: 2, name: '温度变化趋势', type: '折线图', dataPoints: 85 },
  { id: 3, name: '电流数据分布', type: '柱状图', dataPoints: 60 },
  { id: 4, name: '磁场强度测量', type: '散点图', dataPoints: 95 }
])

/** 选中的图表 */
const selectedCharts = ref([])

/** 对比模式 */
const comparisonMode = ref('overlay')

/** 归一化 */
const normalize = ref(false)

/** 显示网格 */
const showGrid = ref(true)

/** 同步缩放 */
const syncZoom = ref(true)

/** 显示创建对话框 */
const showCreateDialog = ref(false)

/** 对比图表容器引用 */
const comparisonChartRef = ref(null)

/** 对比图表实例 */
let comparisonChart = null

/** 新建图表表单 */
const newChartForm = reactive({
  name: '',
  type: 'line',
  dataSource: 'realtime',
  timeRange: [],
  description: ''
})

/** 图表颜色 */
const chartColors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c']

/** 对比统计数据 */
const comparisonStats = computed(() => {
  return selectedCharts.value.map((chartId, index) => {
    const chart = chartList.value.find(c => c.id === chartId)
    if (!chart) return null
    
    // 模拟统计数据
    const baseValue = 10 + index * 5
    return {
      name: chart.name,
      max: baseValue + Math.random() * 5,
      min: baseValue - Math.random() * 5,
      avg: baseValue + Math.random() * 2 - 1,
      std: Math.random() * 2,
      range: Math.random() * 8
    }
  }).filter(Boolean)
})

/**
 * 切换图表选择
 * 
 * @param {number} chartId - 图表ID
 */
function toggleChartSelection(chartId) {
  const index = selectedCharts.value.indexOf(chartId)
  if (index > -1) {
    selectedCharts.value.splice(index, 1)
  } else {
    if (selectedCharts.value.length >= 4) {
      ElMessage.warning('最多只能选择 4 个图表进行对比')
      return
    }
    selectedCharts.value.push(chartId)
  }
  
  if (selectedCharts.value.length > 0) {
    nextTick(() => {
      updateComparisonChart()
    })
  }
}

/**
 * 生成示例数据
 */
function generateData() {
  isGenerating.value = true
  
  setTimeout(() => {
    const data = []
    const colors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#9c27b0', '#00bcd4']
    
    for (let s = 0; s < seriesCount.value; s++) {
      const xData = []
      const yData = []
      const baseValue = 10 + s * 10
      const noise = noiseLevel.value / 100
      
      for (let i = 0; i < dataPointCount.value; i++) {
        xData.push(i)
        const signal = Math.sin(i * 0.02 + s) * 5 + baseValue
        const noiseValue = (Math.random() - 0.5) * 10 * noise
        yData.push(signal + noiseValue)
      }
      
      data.push({
        xData,
        yData,
        name: `数据系列 ${s + 1}`,
        color: colors[s % colors.length]
      })
    }
    
    chartData.value = data
    isGenerating.value = false
    ElMessage.success(`已生成 ${seriesCount.value} 个系列，共 ${dataPointCount.value} 个数据点`)
  }, 300)
}

/**
 * 处理文件上传
 * 
 * @param {File} file - 上传的文件
 */
function handleFileUpload(file) {
  const reader = new FileReader()
  
  reader.onload = (e) => {
    try {
      const text = e.target.result
      const lines = text.split('\n').filter(line => line.trim())
      
      // 解析CSV数据
      const headers = lines[0].split(',').map(h => h.trim())
      const data = []
      
      for (let i = 1; i < headers.length; i++) {
        const xData = []
        const yData = []
        
        for (let j = 1; j < lines.length; j++) {
          const values = lines[j].split(',')
          if (values.length >= i + 1) {
            xData.push(j - 1)
            yData.push(parseFloat(values[i]) || 0)
          }
        }
        
        data.push({
          xData,
          yData,
          name: headers[i] || `系列 ${i}`
        })
      }
      
      chartData.value = data
      ElMessage.success(`已导入 ${data.length} 个数据系列`)
    } catch (error) {
      console.error('解析CSV失败:', error)
      ElMessage.error('CSV文件格式错误')
    }
  }
  
  reader.readAsText(file.raw)
}

/**
 * 应用配置模板
 * 
 * @param {Object} template - 配置模板
 */
function applyTemplate(template) {
  chartType.value = template.chartType
  
  // 如果模板包含数据，应用数据
  if (template.series && template.series.length > 0) {
    chartData.value = template.series
  }
  
  ElMessage.success(`已应用模板: ${template.name}`)
}

/**
 * 删除配置模板
 * 
 * @param {string} templateId - 模板ID
 */
function deleteTemplate(templateId) {
  configTemplates.value = configTemplates.value.filter(t => t.id !== templateId)
  
  // 更新本地存储
  localStorage.setItem('chartTemplates', JSON.stringify(configTemplates.value))
  
  ElMessage.success('模板已删除')
}

/**
 * 处理图表点击事件
 * 
 * @param {Object} params - 点击参数
 */
function handleChartClick(params) {
  console.log('图表点击:', params)
}

/**
 * 处理标注添加事件
 * 
 * @param {Object} annotation - 标注对象
 */
function handleAnnotationAdd(annotation) {
  console.log('添加标注:', annotation)
}

/**
 * 处理配置变更事件
 * 
 * @param {Object} config - 配置对象
 */
function handleConfigChange(config) {
  console.log('配置变更:', config)
}

/**
 * 初始化对比图表
 */
function initComparisonChart() {
  if (!comparisonChartRef.value) return
  
  comparisonChart = echarts.init(comparisonChartRef.value)
}

/**
 * 更新对比图表
 */
function updateComparisonChart() {
  if (!comparisonChart || selectedCharts.value.length === 0) return
  
  const series = selectedCharts.value.map((chartId, index) => {
    const chart = chartList.value.find(c => c.id === chartId)
    if (!chart) return null
    
    // 生成模拟数据
    const data = Array.from({ length: 50 }, (_, i) => {
      const baseValue = 10 + index * 5
      return baseValue + Math.sin(i * 0.2) * 3 + Math.random() * 2
    })
    
    return {
      name: chart.name,
      type: 'line',
      data: data,
      smooth: true,
      symbol: 'circle',
      symbolSize: 4,
      lineStyle: {
        color: chartColors[index],
        width: 2
      },
      itemStyle: {
        color: chartColors[index]
      }
    }
  }).filter(Boolean)
  
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
      top: 10,
      textStyle: { color: '#4a5568' }
    },
    xAxis: {
      type: 'category',
      data: Array.from({ length: 50 }, (_, i) => i + 1),
      name: '采样点',
      nameTextStyle: { color: '#4a5568' },
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { color: '#4a5568' },
      splitLine: { 
        show: showGrid.value,
        lineStyle: { color: '#edf2f7' } 
      }
    },
    yAxis: {
      type: 'value',
      name: '数值',
      nameTextStyle: { color: '#4a5568' },
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { color: '#4a5568' },
      splitLine: { 
        show: showGrid.value,
        lineStyle: { color: '#edf2f7' } 
      }
    },
    series
  }
  
  comparisonChart.setOption(option, true)
}

/**
 * 创建新图表
 */
function createNewChart() {
  showCreateDialog.value = true
}

/**
 * 处理创建图表
 */
function handleCreateChart() {
  if (!newChartForm.name) {
    ElMessage.warning('请输入图表名称')
    return
  }
  
  const newChart = {
    id: Date.now(),
    name: newChartForm.name,
    type: newChartForm.type === 'line' ? '折线图' : 
          newChartForm.type === 'bar' ? '柱状图' : 
          newChartForm.type === 'scatter' ? '散点图' : '面积图',
    dataPoints: Math.floor(Math.random() * 100) + 50
  }
  
  chartList.value.push(newChart)
  showCreateDialog.value = false
  
  // 重置表单
  newChartForm.name = ''
  newChartForm.type = 'line'
  newChartForm.dataSource = 'realtime'
  newChartForm.timeRange = []
  newChartForm.description = ''
  
  ElMessage.success('图表创建成功')
}

/**
 * 导出对比图
 */
function exportComparison() {
  if (!comparisonChart) {
    ElMessage.warning('没有图表可导出')
    return
  }
  
  const url = comparisonChart.getDataURL({
    type: 'png',
    pixelRatio: 2,
    backgroundColor: '#fff'
  })
  
  const link = document.createElement('a')
  link.download = `comparison_${Date.now()}.png`
  link.href = url
  link.click()
  
  ElMessage.success('对比图已导出')
}

/**
 * 清除选择
 */
function clearSelection() {
  selectedCharts.value = []
  ElMessage.info('已清除选择')
}

/**
 * 处理窗口大小变化
 */
function handleResize() {
  comparisonChart?.resize()
}

// 监听设置变化
watch([normalize, showGrid], () => {
  if (selectedCharts.value.length > 0) {
    updateComparisonChart()
  }
})

// 组件挂载时初始化图表
onMounted(() => {
  nextTick(() => {
    initComparisonChart()
    window.addEventListener('resize', handleResize)
    
    // 加载配置模板
    const savedTemplates = localStorage.getItem('chartTemplates')
    if (savedTemplates) {
      try {
        configTemplates.value = JSON.parse(savedTemplates)
      } catch (error) {
        console.error('加载模板失败:', error)
      }
    }
    
    // 生成初始数据
    generateData()
  })
})

// 组件卸载时清理资源
onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  comparisonChart?.dispose()
})
</script>

<style scoped lang="scss">
.analysis-charts-page {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  background-color: var(--color-bg-secondary);
  padding: var(--spacing-6);
}

/* ==================== 页面头部 ==================== */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-6);
  padding: var(--spacing-5) var(--spacing-6);
  background: linear-gradient(135deg, var(--color-primary-500) 0%, var(--color-primary-600) 100%);
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
  line-height: var(--line-height-tight);
  letter-spacing: var(--letter-spacing-wide);
}

.page-subtitle {
  margin: 0;
  font-size: var(--font-size-sm);
  color: rgba(255, 255, 255, 0.85);
}

.header-right {
  display: flex;
  gap: var(--spacing-3);
  position: relative;
  z-index: 1;
}

.header-right :deep(.el-button-group) {
  background-color: rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-md);
  padding: 2px;
}

.header-right :deep(.el-button-group .el-button) {
  background-color: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.9);
  font-weight: var(--font-weight-medium);
  transition: var(--transition-all);
}

.header-right :deep(.el-button-group .el-button:hover) {
  background-color: rgba(255, 255, 255, 0.15);
  color: var(--color-text-inverse);
}

.header-right :deep(.el-button-group .el-button--primary) {
  background-color: rgba(255, 255, 255, 0.25);
  color: var(--color-text-inverse);
  box-shadow: var(--shadow-sm);
}

/* ==================== 主内容区域 ==================== */
.main-content {
  flex: 1;
  max-width: var(--content-max-width);
  margin: 0 auto;
  width: 100%;
}

/* ==================== 视图切换过渡 ==================== */
.comparison-view,
.advanced-view {
  animation: fadeIn var(--transition-base);
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ==================== 卡片通用样式 ==================== */
:deep(.el-card) {
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  background-color: var(--color-surface-primary);
  box-shadow: var(--shadow-card);
  transition: var(--transition-all);
  overflow: hidden;
}

:deep(.el-card:hover) {
  box-shadow: var(--shadow-lg);
  border-color: var(--color-primary-200);
}

:deep(.el-card__header) {
  background-color: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border-primary);
  padding: var(--spacing-4) var(--spacing-5);
}

:deep(.el-card__body) {
  padding: var(--spacing-5);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-3);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.card-header .el-icon {
  color: var(--color-primary-500);
  font-size: var(--font-size-lg);
}

/* ==================== 数据源配置卡片 ==================== */
.data-source-card,
.template-card {
  background-color: var(--color-surface-primary);
  border-color: var(--color-border-primary);
  border-radius: var(--radius-lg);
  margin-bottom: var(--spacing-4);
}

.template-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
  max-height: 280px;
  overflow-y: auto;
  padding-right: var(--spacing-2);
}

.template-list::-webkit-scrollbar {
  width: 6px;
}

.template-list::-webkit-scrollbar-track {
  background: var(--color-bg-secondary);
  border-radius: var(--radius-full);
}

.template-list::-webkit-scrollbar-thumb {
  background: var(--color-neutral-400);
  border-radius: var(--radius-full);
}

.template-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-3);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: var(--transition-fast);
  border: 1px solid transparent;
}

.template-item:hover {
  background-color: var(--color-interactive-hover);
  border-color: var(--color-primary-300);
  transform: translateX(4px);
}

.template-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.template-info .el-icon {
  font-size: var(--font-size-xl);
  color: var(--color-primary-500);
}

.template-details {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.template-name {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

.template-meta {
  display: flex;
  gap: var(--spacing-2);
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

/* ==================== 图表选择器 ==================== */
.chart-selector-card,
.comparison-settings-card {
  background-color: var(--color-surface-primary);
  border-color: var(--color-border-primary);
  border-radius: var(--radius-lg);
  margin-bottom: var(--spacing-4);
}

.chart-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
  max-height: 320px;
  overflow-y: auto;
  padding-right: var(--spacing-2);
}

.chart-list::-webkit-scrollbar {
  width: 6px;
}

.chart-list::-webkit-scrollbar-track {
  background: var(--color-bg-secondary);
  border-radius: var(--radius-full);
}

.chart-list::-webkit-scrollbar-thumb {
  background: var(--color-neutral-400);
  border-radius: var(--radius-full);
}

.chart-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-3);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: var(--transition-fast);
  border: 2px solid transparent;
  position: relative;
}

.chart-item:hover {
  background-color: var(--color-interactive-hover);
  transform: translateX(4px);
}

.chart-item.active {
  background-color: var(--color-interactive-selected);
  border-color: var(--color-primary-500);
  box-shadow: 0 0 0 3px rgba(24, 144, 255, 0.1);
}

.chart-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 60%;
  background-color: var(--color-primary-500);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

.chart-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.chart-info .el-icon {
  font-size: var(--font-size-xl);
  color: var(--color-primary-500);
}

.chart-details {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.chart-name {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

.chart-meta {
  display: flex;
  gap: var(--spacing-2);
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

/* ==================== 对比图表区域 ==================== */
.comparison-chart-card,
.comparison-stats-card {
  background-color: var(--color-surface-primary);
  border-color: var(--color-border-primary);
  border-radius: var(--radius-lg);
  margin-bottom: var(--spacing-4);
}

.chart-actions {
  margin-left: auto;
  display: flex;
  gap: var(--spacing-2);
}

.chart-container {
  height: 520px;
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
    var(--color-primary-500), 
    var(--color-secondary-500),
    var(--color-primary-500)
  );
  border-radius: var(--radius-md) var(--radius-md) 0 0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 520px;
  color: var(--color-text-tertiary);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  border: 2px dashed var(--color-border-primary);
}

.empty-state .el-icon {
  color: var(--color-neutral-400);
  margin-bottom: var(--spacing-4);
  opacity: 0.5;
}

.empty-state p {
  margin: var(--spacing-1) 0;
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
}

.empty-state .hint {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  margin-top: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-4);
  background-color: var(--color-bg-tertiary);
  border-radius: var(--radius-md);
}

/* ==================== 统计表格 ==================== */
.mono {
  font-family: var(--font-family-mono);
  color: var(--color-primary-600);
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-sm);
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
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

:deep(.el-table td) {
  transition: var(--transition-fast);
}

:deep(.el-table__row:hover td) {
  background-color: var(--color-interactive-hover);
}

/* ==================== 过渡动画 ==================== */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-base), transform var(--transition-base);
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* ==================== 对话框样式 ==================== */
:deep(.el-dialog) {
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-modal);
}

:deep(.el-dialog__header) {
  border-bottom: 1px solid var(--color-border-primary);
  padding: var(--spacing-5) var(--spacing-6);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}

:deep(.el-dialog__title) {
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
}

:deep(.el-dialog__body) {
  padding: var(--spacing-6);
}

:deep(.el-dialog__footer) {
  border-top: 1px solid var(--color-border-primary);
  padding: var(--spacing-4) var(--spacing-6);
  background-color: var(--color-bg-secondary);
}

/* ==================== 响应式设计 ==================== */
@media (max-width: 768px) {
  .analysis-charts-page {
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
    flex-wrap: wrap;
    gap: var(--spacing-2);
  }

  .header-right :deep(.el-button-group) {
    width: 100%;
    order: 1;
  }

  .header-right :deep(.el-button-group .el-button) {
    flex: 1;
  }

  .chart-container {
    height: 350px;
  }

  .empty-state {
    height: 350px;
  }

  .chart-list {
    max-height: 250px;
  }

  .template-list {
    max-height: 200px;
  }
}

@media (min-width: 1920px) {
  .analysis-charts-page {
    padding: var(--spacing-8);
  }

  .chart-container {
    height: 620px;
  }

  .empty-state {
    height: 620px;
  }

  .page-title {
    font-size: var(--font-size-3xl);
  }

  .header-icon {
    font-size: 48px;
  }
}

/* ==================== 打印样式 ==================== */
@media print {
  .page-header {
    background: var(--color-text-primary);
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }

  .header-right {
    display: none;
  }
}
</style>
