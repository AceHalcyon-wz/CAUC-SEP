<template>
  <el-card class="ammeter-display">
    <template #header>
      <div class="card-header">
        <div class="header-title">
          <el-icon class="header-icon">
            <Aim />
          </el-icon>
          <span>微电流采集显示</span>
        </div>
        <el-tag
          :type="connectionStatus"
          size="small"
          class="status-tag"
        >
          {{ connectionText }}
        </el-tag>
      </div>
    </template>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      :closable="true"
      class="error-alert"
      @close="clearError()"
    />

    <el-tabs
      v-model="activeTab"
      type="border-card"
      class="data-tabs"
    >
      <!-- 多通道电流显示 -->
      <el-tab-pane
        label="实时数据"
        name="realtime"
      >
        <el-row :gutter="24">
          <!-- 通道配置 -->
          <el-col :span="6">
            <el-card
              shadow="hover"
              class="config-card"
            >
              <template #header>
                <div class="config-header">
                  <el-icon><Setting /></el-icon>
                  <span>采集配置</span>
                </div>
              </template>
              <el-form
                label-width="80px"
                size="small"
                class="config-form"
              >
                <el-form-item
                  label="采样率"
                  class="form-item"
                >
                  <el-select
                    v-model="config.sampleRate"
                    placeholder="选择采样率"
                    class="form-select"
                  >
                    <el-option
                      label="10 Hz"
                      :value="10"
                    />
                    <el-option
                      label="100 Hz"
                      :value="100"
                    />
                    <el-option
                      label="1 kHz"
                      :value="1000"
                    />
                    <el-option
                      label="10 kHz"
                      :value="10000"
                    />
                  </el-select>
                </el-form-item>
                <el-form-item
                  label="通道数"
                  class="form-item"
                >
                  <el-input-number
                    v-model="config.channelCount"
                    :min="1"
                    :max="8"
                    style="width: 100%"
                  />
                </el-form-item>
                <el-form-item
                  label="量程"
                  class="form-item"
                >
                  <el-select
                    v-model="config.range"
                    placeholder="选择量程"
                    class="form-select"
                  >
                    <el-option
                      label="±10 nA"
                      value="10nA"
                    />
                    <el-option
                      label="±100 nA"
                      value="100nA"
                    />
                    <el-option
                      label="±1 μA"
                      value="1uA"
                    />
                    <el-option
                      label="±10 μA"
                      value="10uA"
                    />
                  </el-select>
                </el-form-item>
                <el-form-item
                  label="滤波"
                  class="form-item"
                >
                  <el-switch v-model="config.filterEnabled" />
                </el-form-item>
                <el-form-item class="action-item">
                  <el-button
                    type="primary"
                    :loading="isCollecting"
                    class="collect-btn"
                    @click="toggleCollection"
                  >
                    <el-icon v-if="!isCollecting">
                      <VideoPlay />
                    </el-icon>
                    <el-icon v-else>
                      <VideoPause />
                    </el-icon>
                    {{ isCollecting ? '停止采集' : '开始采集' }}
                  </el-button>
                </el-form-item>
              </el-form>
            </el-card>
          </el-col>

          <!-- 通道数据显示 -->
          <el-col :span="18">
            <el-row :gutter="16">
              <el-col
                v-for="channel in displayChannels"
                :key="channel.id"
                :span="12"
                class="channel-col"
              >
                <el-card
                  shadow="hover"
                  class="channel-card"
                  :class="{ 'channel-active': isCollecting }"
                >
                  <div class="channel-header">
                    <span class="channel-name">{{ channel.name }}</span>
                    <el-tag
                      :type="channel.status === 'normal' ? 'success' : 'warning'"
                      size="small"
                      class="channel-status"
                    >
                      {{ channel.status === 'normal' ? '正常' : '异常' }}
                    </el-tag>
                  </div>
                  <div class="channel-value">
                    <span
                      class="value"
                      :class="{ 'value-changing': isCollecting }"
                    >{{ formatCurrent(channel.current) }}</span>
                    <span class="unit">{{ channel.unit }}</span>
                  </div>
                  <div class="channel-stats">
                    <div class="stat-item">
                      <span class="label">最大值:</span>
                      <span class="value mono">{{ formatCurrent(channel.max) }}</span>
                    </div>
                    <div class="stat-item">
                      <span class="label">最小值:</span>
                      <span class="value mono">{{ formatCurrent(channel.min) }}</span>
                    </div>
                    <div class="stat-item">
                      <span class="label">平均值:</span>
                      <span class="value mono">{{ formatCurrent(channel.avg) }}</span>
                    </div>
                  </div>
                </el-card>
              </el-col>
            </el-row>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- 实时波形显示 -->
      <el-tab-pane
        label="波形显示"
        name="waveform"
      >
        <el-row :gutter="24">
          <!-- 波形控制 -->
          <el-col :span="4">
            <el-card
              shadow="hover"
              class="control-card"
            >
              <template #header>
                <div class="control-header">
                  <el-icon><DataLine /></el-icon>
                  <span>波形控制</span>
                </div>
              </template>
              <el-form
                label-width="70px"
                size="small"
                class="control-form"
              >
                <el-form-item
                  label="时间窗"
                  class="form-item"
                >
                  <el-select
                    v-model="waveformConfig.timeWindow"
                    placeholder="选择时间窗"
                    class="form-select"
                  >
                    <el-option
                      label="1秒"
                      :value="1"
                    />
                    <el-option
                      label="5秒"
                      :value="5"
                    />
                    <el-option
                      label="10秒"
                      :value="10"
                    />
                    <el-option
                      label="30秒"
                      :value="30"
                    />
                    <el-option
                      label="60秒"
                      :value="60"
                    />
                  </el-select>
                </el-form-item>
                <el-form-item
                  label="显示通道"
                  class="form-item"
                >
                  <el-checkbox-group
                    v-model="waveformConfig.visibleChannels"
                    class="channel-checkbox-group"
                  >
                    <el-checkbox
                      v-for="ch in displayChannels"
                      :key="ch.id"
                      :label="ch.id"
                      class="channel-checkbox"
                    >
                      {{ ch.name }}
                    </el-checkbox>
                  </el-checkbox-group>
                </el-form-item>
                <el-form-item
                  label="Y轴缩放"
                  class="form-item"
                >
                  <el-radio-group
                    v-model="waveformConfig.yAxisMode"
                    class="radio-group"
                  >
                    <el-radio label="auto">
                      自动
                    </el-radio>
                    <el-radio label="fixed">
                      固定
                    </el-radio>
                  </el-radio-group>
                </el-form-item>
                <el-form-item
                  v-if="waveformConfig.yAxisMode === 'fixed'"
                  label="Y轴范围"
                  class="form-item"
                >
                  <div class="y-axis-range">
                    <el-input-number
                      v-model="waveformConfig.yMin"
                      placeholder="最小值"
                      size="small"
                    />
                    <el-input-number
                      v-model="waveformConfig.yMax"
                      placeholder="最大值"
                      size="small"
                    />
                  </div>
                </el-form-item>
                <el-form-item class="action-item">
                  <el-button
                    type="primary"
                    :disabled="!isCollecting"
                    class="clear-btn"
                    @click="clearWaveform"
                  >
                    <el-icon><Delete /></el-icon>
                    清除波形
                  </el-button>
                </el-form-item>
              </el-form>
            </el-card>
          </el-col>

          <!-- 波形图表 -->
          <el-col :span="20">
            <el-card
              shadow="hover"
              class="chart-card"
            >
              <div
                ref="waveformChartRef"
                class="waveform-chart"
              />
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- 数据导出 -->
      <el-tab-pane
        label="数据导出"
        name="export"
      >
        <el-row :gutter="24">
          <!-- 导出配置 -->
          <el-col :span="6">
            <el-card
              shadow="hover"
              class="export-config-card"
            >
              <template #header>
                <div class="export-header">
                  <el-icon><Download /></el-icon>
                  <span>导出配置</span>
                </div>
              </template>
              <el-form
                label-width="80px"
                size="small"
                class="export-form"
              >
                <el-form-item
                  label="导出格式"
                  class="form-item"
                >
                  <el-select
                    v-model="exportConfig.format"
                    placeholder="选择格式"
                    class="form-select"
                  >
                    <el-option
                      label="CSV"
                      value="csv"
                    />
                    <el-option
                      label="JSON"
                      value="json"
                    />
                    <el-option
                      label="Excel"
                      value="xlsx"
                    />
                  </el-select>
                </el-form-item>
                <el-form-item
                  label="时间范围"
                  class="form-item"
                >
                  <el-date-picker
                    v-model="exportConfig.timeRange"
                    type="datetimerange"
                    range-separator="至"
                    start-placeholder="开始时间"
                    end-placeholder="结束时间"
                    style="width: 100%"
                  />
                </el-form-item>
                <el-form-item
                  label="导出通道"
                  class="form-item"
                >
                  <el-checkbox-group
                    v-model="exportConfig.channels"
                    class="channel-checkbox-group"
                  >
                    <el-checkbox
                      v-for="ch in displayChannels"
                      :key="ch.id"
                      :label="ch.id"
                      class="channel-checkbox"
                    >
                      {{ ch.name }}
                    </el-checkbox>
                  </el-checkbox-group>
                </el-form-item>
                <el-form-item
                  label="包含统计"
                  class="form-item"
                >
                  <el-switch v-model="exportConfig.includeStats" />
                </el-form-item>
                <el-form-item class="action-item">
                  <el-button
                    type="primary"
                    :loading="isExporting"
                    :disabled="!hasDataToExport"
                    class="export-btn"
                    @click="exportData"
                  >
                    <el-icon><Download /></el-icon>
                    导出数据
                  </el-button>
                </el-form-item>
              </el-form>
            </el-card>
          </el-col>

          <!-- 数据预览 -->
          <el-col :span="18">
            <el-card
              shadow="hover"
              class="preview-card"
            >
              <template #header>
                <div class="preview-header">
                  <div class="header-title">
                    <el-icon><Document /></el-icon>
                    <span>数据预览</span>
                  </div>
                  <el-tag
                    size="small"
                    class="record-count"
                  >
                    {{ dataPreview.length }} 条记录
                  </el-tag>
                </div>
              </template>
              <el-table
                :data="dataPreview"
                border
                class="preview-table"
                max-height="500"
              >
                <el-table-column
                  prop="timestamp"
                  label="时间戳"
                  width="180"
                >
                  <template #default="{ row }">
                    <span class="mono">{{ row.timestamp }}</span>
                  </template>
                </el-table-column>
                <el-table-column
                  v-for="ch in displayChannels"
                  :key="ch.id"
                  :prop="`channel_${ch.id}`"
                  :label="ch.name"
                  width="120"
                >
                  <template #default="scope">
                    <span class="mono">{{ formatCurrent(scope.row[`channel_${ch.id}`]) }}</span>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>
    </el-tabs>
  </el-card>
</template>

<script setup lang="ts">
/**
 * @file AmmeterDisplay.vue
 * @path src/components/
 * @description 微电流采集显示组件，支持多通道实时采集、波形显示和数据导出
 * @author Agent
 * @date 2024-03-07
 */

import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import axios from 'axios'

// ============ 类型定义 ============

/**
 * 通道数据接口
 */
interface ChannelData {
  id: number
  name: string
  current: number
  unit: string
  status: 'normal' | 'warning'
  max: number
  min: number
  avg: number
  history: number[]
}

/**
 * 采集配置接口
 */
interface CollectionConfig {
  sampleRate: number
  channelCount: number
  range: string
  filterEnabled: boolean
}

/**
 * 波形配置接口
 */
interface WaveformConfig {
  timeWindow: number
  visibleChannels: number[]
  yAxisMode: 'auto' | 'fixed'
  yMin: number
  yMax: number
}

/**
 * 导出配置接口
 */
interface ExportConfig {
  format: 'csv' | 'json' | 'xlsx'
  timeRange: [Date, Date] | null
  channels: number[]
  includeStats: boolean
}

/**
 * 数据记录接口
 */
interface DataRecord {
  timestamp: string
  [key: string]: number | string
}

// ============ 常量定义 ============

import { API_BASE_URL, WS_BASE_URL } from '@/config/api'
import { AMMETER, GENERAL } from '@/config/constants'

const AMMETER_API_BASE = `${API_BASE_URL}/api/ammeter`
const MAX_HISTORY_POINTS = GENERAL.MAX_HISTORY_POINTS
const PREVIEW_LIMIT = 100

// ============ 响应式状态 ============

const activeTab = ref<string>('realtime')
const isCollecting = ref<boolean>(false)
const isExporting = ref<boolean>(false)
const errorMessage = ref<string>('')
const waveformChartRef = ref<HTMLElement | null>(null)

let waveformChart: echarts.ECharts | null = null
let collectionTimer: ReturnType<typeof setInterval> | null = null
let ws: WebSocket | null = null

// 采集配置
const config = ref<CollectionConfig>({
  sampleRate: 100,
  channelCount: 4,
  range: '1uA',
  filterEnabled: true
})

// 波形配置
const waveformConfig = ref<WaveformConfig>({
  timeWindow: 10,
  visibleChannels: [1, 2, 3, 4],
  yAxisMode: 'auto',
  yMin: -1,
  yMax: 1
})

// 导出配置
const exportConfig = ref<ExportConfig>({
  format: 'csv',
  timeRange: null,
  channels: [1, 2, 3, 4],
  includeStats: true
})

// 通道数据
const channels = ref<ChannelData[]>([
  { id: 1, name: '通道 1', current: 0, unit: 'μA', status: 'normal', max: 0, min: 0, avg: 0, history: [] },
  { id: 2, name: '通道 2', current: 0, unit: 'μA', status: 'normal', max: 0, min: 0, avg: 0, history: [] },
  { id: 3, name: '通道 3', current: 0, unit: 'μA', status: 'normal', max: 0, min: 0, avg: 0, history: [] },
  { id: 4, name: '通道 4', current: 0, unit: 'μA', status: 'normal', max: 0, min: 0, avg: 0, history: [] }
])

// 数据缓冲区
const dataBuffer = ref<DataRecord[]>([])
const timestamps = ref<string[]>([])

// ============ 计算属性 ============

/**
 * 显示的通道列表（根据配置的通道数）
 */
const displayChannels = computed(() => {
  return channels.value.slice(0, config.value.channelCount)
})

/**
 * 连接状态类型
 */
const connectionStatus = computed(() => {
  return isCollecting.value ? 'success' : 'info'
})

/**
 * 连接状态文本
 */
const connectionText = computed(() => {
  return isCollecting.value ? '采集中' : '未采集'
})

/**
 * 是否有数据可导出
 */
const hasDataToExport = computed(() => {
  return dataBuffer.value.length > 0
})

/**
 * 数据预览（最近100条）
 */
const dataPreview = computed(() => {
  return dataBuffer.value.slice(-PREVIEW_LIMIT)
})

// ============ 方法 ============

/**
 * 格式化电流值显示
 * 
 * @param value - 电流值（单位：μA）
 * @returns 格式化后的字符串
 */
function formatCurrent(value: number): string {
  if (Math.abs(value) < 0.001) {
    return (value * 1000).toFixed(3) + ' nA'
  } else if (Math.abs(value) < 1) {
    return value.toFixed(4) + ' μA'
  } else {
    return value.toFixed(3) + ' μA'
  }
}

/**
 * 清除错误信息
 */
function clearError(): void {
  errorMessage.value = ''
}

/**
 * 显示错误信息
 * 
 * @param message - 错误消息
 */
function showError(message: string): void {
  errorMessage.value = message
  ElMessage.error(message)
}

/**
 * 切换采集状态
 */
async function toggleCollection(): Promise<void> {
  if (isCollecting.value) {
    await stopCollection()
  } else {
    await startCollection()
  }
}

/**
 * 开始采集
 */
async function startCollection(): Promise<void> {
  try {
    // 调用后端 API 开始采集
    const response = await axios.post(`${AMMETER_API_BASE}/start`, {
      sample_rate: config.value.sampleRate,
      channel_count: config.value.channelCount,
      range: config.value.range,
      filter_enabled: config.value.filterEnabled
    })

    if (response.data.success) {
      isCollecting.value = true
      ElMessage.success('开始采集')
      
      // 连接 WebSocket 接收实时数据
      connectWebSocket()
      
      // 启动定时器更新波形
      startWaveformUpdate()
    } else {
      showError('启动采集失败: ' + response.data.message)
    }
  } catch (error: any) {
    showError('启动采集错误: ' + (error.response?.data?.detail || error.message))
  }
}

/**
 * 停止采集
 */
async function stopCollection(): Promise<void> {
  try {
    const response = await axios.post(`${AMMETER_API_BASE}/stop`)
    
    if (response.data.success) {
      isCollecting.value = false
      ElMessage.success('停止采集')
      
      // 断开 WebSocket
      disconnectWebSocket()
      
      // 停止定时器
      stopWaveformUpdate()
    } else {
      showError('停止采集失败: ' + response.data.message)
    }
  } catch (error: any) {
    showError('停止采集错误: ' + (error.response?.data?.detail || error.message))
  }
}

/**
 * 连接 WebSocket
 */
function connectWebSocket(): void {
  disconnectWebSocket()
  
  try {
    ws = new WebSocket(`${WS_BASE_URL}/ws/ammeter`)
    
    ws.onopen = () => {
      console.log('[AmmeterDisplay] WebSocket connected')
    }
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleRealtimeData(data)
      } catch (e) {
        console.error('[AmmeterDisplay] Failed to parse WebSocket message:', e)
      }
    }
    
    ws.onclose = () => {
      console.log('[AmmeterDisplay] WebSocket disconnected')
    }
    
    ws.onerror = (error) => {
      console.error('[AmmeterDisplay] WebSocket error:', error)
    }
  } catch (error) {
    console.error('[AmmeterDisplay] Failed to create WebSocket:', error)
  }
}

/**
 * 断开 WebSocket
 */
function disconnectWebSocket(): void {
  if (ws) {
    ws.close()
    ws = null
  }
}

/**
 * 处理实时数据
 * 
 * @param data - 实时数据对象
 */
function handleRealtimeData(data: any): void {
  if (!data.channels) return
  
  const timestamp = new Date().toISOString()
  const record: DataRecord = { timestamp }
  
  // 更新各通道数据
  data.channels.forEach((chData: any, index: number) => {
    const channel = channels.value[index]
    if (!channel) return
    
    const currentValue = chData.current
    
    // 更新当前值
    channel.current = currentValue
    
    // 更新统计值
    if (channel.history.length === 0) {
      channel.max = currentValue
      channel.min = currentValue
      channel.avg = currentValue
    } else {
      channel.max = Math.max(channel.max, currentValue)
      channel.min = Math.min(channel.min, currentValue)
      channel.avg = channel.history.reduce((a, b) => a + b, currentValue) / (channel.history.length + 1)
    }
    
    // 更新历史数据
    channel.history.push(currentValue)
    if (channel.history.length > MAX_HISTORY_POINTS) {
      channel.history.shift()
    }
    
    // 添加到记录
    record[`channel_${channel.id}`] = currentValue
  })
  
  // 添加时间戳
  timestamps.value.push(timestamp)
  if (timestamps.value.length > MAX_HISTORY_POINTS) {
    timestamps.value.shift()
  }
  
  // 添加到数据缓冲区
  dataBuffer.value.push(record)
}

/**
 * 启动波形更新定时器
 */
function startWaveformUpdate(): void {
  stopWaveformUpdate()
  
  collectionTimer = setInterval(() => {
    updateWaveformChart()
  }, 100) // 10 Hz 更新率
}

/**
 * 停止波形更新定时器
 */
function stopWaveformUpdate(): void {
  if (collectionTimer) {
    clearInterval(collectionTimer)
    collectionTimer = null
  }
}

/**
 * 更新波形图表
 */
function updateWaveformChart(): void {
  if (!waveformChart || !isCollecting.value) return
  
  const series: any[] = []
  const colors = [
    'var(--color-data-blue)',
    'var(--color-data-green)',
    'var(--color-data-yellow)',
    'var(--color-data-red)',
    'var(--color-neutral-500)',
    'var(--color-data-cyan)',
    'var(--color-data-purple)',
    'var(--color-data-pink)'
  ]
  
  displayChannels.value.forEach((channel, index) => {
    if (!waveformConfig.value.visibleChannels.includes(channel.id)) return
    
    series.push({
      name: channel.name,
      type: 'line',
      data: channel.history,
      symbol: 'none',
      lineStyle: { width: 2, color: colors[index % colors.length] },
      smooth: config.value.filterEnabled
    })
  })
  
  const yAxisConfig: any = {
    type: 'value',
    name: '电流 (μA)',
    nameTextStyle: {
      color: 'var(--color-text-secondary)'
    },
    axisLine: {
      lineStyle: {
        color: 'var(--color-border-primary)'
      }
    },
    splitLine: {
      lineStyle: {
        color: 'var(--color-border-secondary)'
      }
    }
  }
  
  if (waveformConfig.value.yAxisMode === 'fixed') {
    yAxisConfig.min = waveformConfig.value.yMin
    yAxisConfig.max = waveformConfig.value.yMax
  }
  
  waveformChart.setOption({
    title: { 
      text: '实时电流波形',
      textStyle: {
        color: 'var(--color-text-primary)',
        fontSize: 16,
        fontWeight: 'var(--font-weight-semibold)'
      }
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'var(--color-surface-elevated)',
      borderColor: 'var(--color-border-primary)',
      textStyle: {
        color: 'var(--color-text-primary)'
      },
      formatter: (params: any) => {
        let result = `时间: ${params[0].dataIndex}<br/>`
        params.forEach((item: any) => {
          result += `${item.marker}${item.seriesName}: ${formatCurrent(item.value)}<br/>`
        })
        return result
      }
    },
    legend: {
      data: displayChannels.value
        .filter(ch => waveformConfig.value.visibleChannels.includes(ch.id))
        .map(ch => ch.name),
      top: 30,
      textStyle: {
        color: 'var(--color-text-secondary)'
      }
    },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: Array.from({ length: MAX_HISTORY_POINTS }, (_, i) => i),
      name: '采样点',
      nameTextStyle: {
        color: 'var(--color-text-secondary)'
      },
      axisLine: {
        lineStyle: {
          color: 'var(--color-border-primary)'
        }
      },
      splitLine: {
        lineStyle: {
          color: 'var(--color-border-secondary)'
        }
      }
    },
    yAxis: yAxisConfig,
    series
  })
}

/**
 * 清除波形数据
 */
function clearWaveform(): void {
  channels.value.forEach(channel => {
    channel.history = []
    channel.max = 0
    channel.min = 0
    channel.avg = 0
  })
  timestamps.value = []
  
  if (waveformChart) {
    waveformChart.clear()
    updateWaveformChart()
  }
  
  ElMessage.success('波形已清除')
}

/**
 * 导出数据
 */
async function exportData(): Promise<void> {
  if (!hasDataToExport.value) {
    ElMessage.warning('没有数据可导出')
    return
  }
  
  isExporting.value = true
  
  try {
    const response = await axios.post(`${AMMETER_API_BASE}/export`, {
      format: exportConfig.value.format,
      time_range: exportConfig.value.timeRange,
      channels: exportConfig.value.channels,
      include_stats: exportConfig.value.includeStats,
      data: dataBuffer.value
    }, {
      responseType: 'blob'
    })
    
    // 创建下载链接
    const blob = new Blob([response.data])
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    
    // 设置文件名
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
    const extension = exportConfig.value.format === 'xlsx' ? 'xlsx' : exportConfig.value.format
    link.download = `ammeter_data_${timestamp}.${extension}`
    
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('数据导出成功')
  } catch (error: any) {
    showError('数据导出错误: ' + (error.response?.data?.detail || error.message))
  } finally {
    isExporting.value = false
  }
}

/**
 * 初始化波形图表
 */
function initWaveformChart(): void {
  if (!waveformChartRef.value) return
  
  waveformChart = echarts.init(waveformChartRef.value)
  updateWaveformChart()
}

/**
 * 处理窗口大小变化
 */
function handleResize(): void {
  if (waveformChart) {
    waveformChart.resize()
  }
}

// ============ 生命周期 ============

onMounted(() => {
  nextTick(() => {
    initWaveformChart()
    window.addEventListener('resize', handleResize)
  })
})

onUnmounted(() => {
  stopWaveformUpdate()
  disconnectWebSocket()
  
  if (waveformChart) {
    waveformChart.dispose()
    waveformChart = null
  }
  
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.ammeter-display {
  width: 100%;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  transition: var(--transition-all);
}

.ammeter-display:hover {
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

.status-tag {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-xs);
}

.error-alert {
  margin-bottom: var(--spacing-4);
  border-radius: var(--radius-md);
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.data-tabs {
  border-radius: var(--radius-md);
}

/* 配置卡片样式 */
.config-card,
.control-card,
.export-config-card {
  height: 100%;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
  transition: var(--transition-all);
}

.config-card:hover,
.control-card:hover,
.export-config-card:hover {
  box-shadow: var(--shadow-md);
}

.config-header,
.control-header,
.export-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.config-form,
.control-form,
.export-form {
  margin-bottom: 0;
}

.form-item {
  margin-bottom: var(--spacing-3);
  transition: var(--transition-all);
}

.form-item:hover {
  background-color: var(--color-interactive-hover);
  border-radius: var(--radius-sm);
}

.form-select {
  width: 100%;
}

.action-item {
  margin-top: var(--spacing-4);
}

.collect-btn,
.clear-btn,
.export-btn {
  width: 100%;
  transition: var(--transition-all);
}

.collect-btn:hover,
.clear-btn:hover,
.export-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

/* 通道卡片样式 */
.channel-col {
  margin-bottom: var(--spacing-4);
}

.channel-card {
  padding: var(--spacing-3);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
  transition: var(--transition-all);
  background: linear-gradient(135deg, var(--color-surface-primary) 0%, var(--color-surface-secondary) 100%);
}

.channel-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.channel-active {
  border-color: var(--color-accent-500);
  box-shadow: var(--shadow-glow-accent);
}

.channel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-3);
}

.channel-name {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
}

.channel-status {
  font-size: var(--font-size-xs);
}

.channel-value {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: var(--spacing-2);
  margin: var(--spacing-4) 0;
  padding: var(--spacing-3);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
}

.channel-value .value {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary-500);
  font-family: var(--font-family-mono);
  letter-spacing: 0.05em;
  transition: var(--transition-all);
}

.channel-value .value-changing {
  animation: pulse 1s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

.channel-value .unit {
  font-size: var(--font-size-base);
  color: var(--color-text-tertiary);
  font-family: var(--font-family-mono);
}

.channel-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-2);
  padding-top: var(--spacing-3);
  border-top: 1px solid var(--color-border-primary);
}

.channel-stats .stat-item {
  text-align: center;
}

.channel-stats .label {
  display: block;
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-bottom: var(--spacing-1);
}

.channel-stats .value {
  display: block;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  font-family: var(--font-family-mono);
}

/* 波形图表样式 */
.chart-card {
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
}

.waveform-chart {
  height: 500px;
  width: 100%;
}

.y-axis-range {
  display: flex;
  gap: var(--spacing-2);
}

.y-axis-range .el-input-number {
  flex: 1;
}

.channel-checkbox-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.channel-checkbox {
  margin: 0;
}

.radio-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

/* 数据预览样式 */
.preview-card {
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.record-count {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-xs);
}

.preview-table {
  font-size: var(--font-size-sm);
}

.mono {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-xs);
}

/* Element Plus 样式覆盖 */
:deep(.el-card__header) {
  background-color: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border-primary);
}

:deep(.el-tabs__header) {
  margin-bottom: var(--spacing-4);
}

:deep(.el-tabs__item) {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  transition: var(--transition-all);
}

:deep(.el-tabs__item.is-active) {
  color: var(--color-primary-500);
  font-weight: var(--font-weight-semibold);
}

:deep(.el-tabs__item:hover) {
  color: var(--color-primary-500);
}

:deep(.el-table) {
  background-color: var(--color-surface-primary);
}

:deep(.el-table th.el-table__cell) {
  background-color: var(--color-bg-secondary);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .channel-value .value {
    font-size: var(--font-size-2xl);
  }
  
  .channel-stats {
    grid-template-columns: 1fr;
    gap: var(--spacing-1);
  }
  
  .waveform-chart {
    height: 300px;
  }
}
</style>
