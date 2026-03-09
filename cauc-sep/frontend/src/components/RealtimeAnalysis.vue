<template>
  <div class="realtime-analysis">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-button-group>
          <el-button 
            :type="autoRefresh ? 'primary' : 'default'" 
            :icon="autoRefresh ? VideoPause : VideoPlay"
            @click="toggleAutoRefresh"
          >
            {{ autoRefresh ? '暂停' : '开始' }}
          </el-button>
          <el-button 
            :icon="Refresh" 
            :loading="isRefreshing"
            @click="refreshData"
          >
            刷新
          </el-button>
        </el-button-group>

        <el-divider direction="vertical" />

        <el-button-group>
          <el-button 
            :type="showDeviceSelector ? 'primary' : 'default'"
            :icon="Monitor"
            @click="showDeviceSelector = !showDeviceSelector"
          >
            设备选择
          </el-button>
          <el-button 
            :type="showFilterPanel ? 'primary' : 'default'"
            :icon="Filter"
            @click="showFilterPanel = !showFilterPanel"
          >
            数据过滤
          </el-button>
          <el-button 
            :type="showStatisticsPanel ? 'primary' : 'default'"
            :icon="DataAnalysis"
            @click="showStatisticsPanel = !showStatisticsPanel"
          >
            统计指标
          </el-button>
        </el-button-group>
      </div>

      <div class="toolbar-right">
        <el-dropdown @command="handleExportCommand">
          <el-button
            type="success"
            :icon="Download"
          >
            导出数据 <el-icon class="el-icon--right">
              <ArrowDown />
            </el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="csv">
                导出为 CSV
              </el-dropdown-item>
              <el-dropdown-item command="json">
                导出为 JSON
              </el-dropdown-item>
              <el-dropdown-item
                divided
                command="screenshot"
              >
                截图保存
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <el-button 
          :icon="Setting" 
          @click="showSettingsDialog = true"
        >
          设置
        </el-button>
      </div>
    </div>

    <!-- 设备选择器面板 -->
    <el-collapse-transition>
      <div
        v-show="showDeviceSelector"
        class="device-selector-panel"
      >
        <el-card shadow="hover">
          <template #header>
            <div class="panel-header">
              <span><el-icon><Monitor /></el-icon> 多设备数据选择器</span>
              <div class="panel-actions">
                <el-button
                  size="small"
                  @click="selectAllDevices"
                >
                  全选
                </el-button>
                <el-button
                  size="small"
                  @click="deselectAllDevices"
                >
                  清空
                </el-button>
              </div>
            </div>
          </template>

          <el-row :gutter="16">
            <el-col 
              v-for="device in analysisStore.availableDevices" 
              :key="device.id"
              :xs="24"
              :sm="12"
              :md="8"
              :lg="6"
            >
              <el-card 
                shadow="hover" 
                class="device-card"
                :class="{ 'selected': isSelectedDevice(device.id) }"
                @click="toggleDevice(device.id)"
              >
                <div class="device-header">
                  <el-checkbox 
                    :model-value="isSelectedDevice(device.id)"
                    @click.stop
                    @change="toggleDevice(device.id)"
                  />
                  <span class="device-name">{{ device.name }}</span>
                  <el-tag 
                    v-if="getDeviceDataCount(device.id) > 0" 
                    size="small" 
                    type="success"
                  >
                    {{ getDeviceDataCount(device.id) }} 点
                  </el-tag>
                </div>

                <div
                  v-if="isSelectedDevice(device.id)"
                  class="channel-list"
                >
                  <el-checkbox-group 
                    v-model="selectedChannels[device.id]"
                    @change="handleChannelChange(device.id)"
                  >
                    <div 
                      v-for="channel in device.channels" 
                      :key="channel.id"
                      class="channel-item"
                    >
                      <el-checkbox :label="channel.id">
                        <span class="channel-info">
                          <span 
                            class="channel-color" 
                            :style="{ backgroundColor: channel.color }"
                          />
                          {{ channel.name }} ({{ channel.unit }})
                        </span>
                      </el-checkbox>
                    </div>
                  </el-checkbox-group>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <div class="selection-summary">
            <el-tag>已选择 {{ analysisStore.selectedDeviceCount }} 个设备</el-tag>
            <el-tag type="success">
              {{ analysisStore.selectedChannelCount }} 个通道
            </el-tag>
          </div>
        </el-card>
      </div>
    </el-collapse-transition>

    <!-- 数据过滤面板 -->
    <el-collapse-transition>
      <div
        v-show="showFilterPanel"
        class="filter-panel"
      >
        <el-card shadow="hover">
          <template #header>
            <div class="panel-header">
              <span><el-icon><Filter /></el-icon> 数据过滤条件</span>
              <el-button
                size="small"
                @click="resetFilters"
              >
                重置
              </el-button>
            </div>
          </template>

          <el-form label-width="100px">
            <el-row :gutter="20">
              <el-col
                :xs="24"
                :sm="12"
                :md="8"
              >
                <el-form-item label="时间范围">
                  <el-date-picker
                    v-model="timeRangeValue"
                    type="datetimerange"
                    range-separator="至"
                    start-placeholder="开始时间"
                    end-placeholder="结束时间"
                    value-format="x"
                    style="width: 100%"
                    @change="handleTimeRangeChange"
                  />
                </el-form-item>
              </el-col>

              <el-col
                :xs="24"
                :sm="12"
                :md="8"
              >
                <el-form-item label="数值范围">
                  <el-slider
                    v-model="valueRangeValue"
                    range
                    :min="-100"
                    :max="100"
                    @change="handleValueRangeChange"
                  />
                </el-form-item>
              </el-col>

              <el-col
                :xs="24"
                :sm="12"
                :md="8"
              >
                <el-form-item label="采样间隔">
                  <el-input-number
                    v-model="samplingInterval"
                    :min="10"
                    :max="10000"
                    :step="10"
                    style="width: 100%"
                  />
                  <span class="form-hint">毫秒</span>
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="20">
              <el-col
                :xs="24"
                :sm="12"
              >
                <el-form-item label="数据平滑">
                  <el-switch 
                    v-model="enableSmoothing"
                    @change="handleSmoothingChange"
                  />
                  <el-input-number
                    v-if="enableSmoothing"
                    v-model="smoothingWindow"
                    :min="3"
                    :max="21"
                    :step="2"
                    style="margin-left: 16px"
                  />
                  <span
                    v-if="enableSmoothing"
                    class="form-hint"
                  >窗口大小</span>
                </el-form-item>
              </el-col>

              <el-col
                :xs="24"
                :sm="12"
              >
                <el-form-item label="实时预览">
                  <el-switch v-model="realtimePreview" />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </el-card>
      </div>
    </el-collapse-transition>

    <!-- 统计指标面板 -->
    <el-collapse-transition>
      <div
        v-show="showStatisticsPanel"
        class="statistics-panel"
      >
        <el-card shadow="hover">
          <template #header>
            <div class="panel-header">
              <span><el-icon><DataAnalysis /></el-icon> 实时统计指标</span>
              <el-tag :type="autoRefresh ? 'success' : 'info'">
                {{ autoRefresh ? '实时更新中' : '已暂停' }}
              </el-tag>
            </div>
          </template>

          <div
            v-if="!analysisStore.hasData"
            class="empty-state"
          >
            <el-empty description="暂无数据，请选择设备并开始采集" />
          </div>

          <div
            v-else
            class="statistics-grid"
          >
            <div 
              v-for="(deviceStats, deviceId) in analysisStore.statistics" 
              :key="deviceId"
              class="device-statistics"
            >
              <h4 class="device-title">
                {{ analysisStore.DEVICE_NAMES[deviceId] || deviceId }}
              </h4>

              <el-row :gutter="12">
                <el-col 
                  v-for="(stats, channelId) in deviceStats" 
                  :key="channelId"
                  :xs="24"
                  :sm="12"
                  :md="8"
                >
                  <el-card
                    shadow="hover"
                    class="stat-card"
                  >
                    <div class="stat-header">
                      <span class="stat-channel">
                        {{ getChannelName(deviceId, channelId) }}
                      </span>
                      <el-tag 
                        :type="getTrendType(stats.trend?.direction)"
                        size="small"
                      >
                        {{ getTrendText(stats.trend?.direction) }}
                      </el-tag>
                    </div>

                    <el-descriptions
                      :column="2"
                      border
                      size="small"
                    >
                      <el-descriptions-item label="数据点">
                        <span class="mono">{{ stats.count }}</span>
                      </el-descriptions-item>
                      <el-descriptions-item label="均值">
                        <span class="mono">{{ stats.mean?.toFixed(3) }}</span>
                      </el-descriptions-item>
                      <el-descriptions-item label="标准差">
                        <span class="mono">{{ stats.std?.toFixed(3) }}</span>
                      </el-descriptions-item>
                      <el-descriptions-item label="范围">
                        <span class="mono">{{ stats.range?.toFixed(3) }}</span>
                      </el-descriptions-item>
                      <el-descriptions-item label="最小值">
                        <span class="mono">{{ stats.min?.toFixed(3) }}</span>
                      </el-descriptions-item>
                      <el-descriptions-item label="最大值">
                        <span class="mono">{{ stats.max?.toFixed(3) }}</span>
                      </el-descriptions-item>
                      <el-descriptions-item label="中位数">
                        <span class="mono">{{ stats.median?.toFixed(3) }}</span>
                      </el-descriptions-item>
                      <el-descriptions-item label="变化率">
                        <span 
                          class="mono" 
                          :class="stats.changeRate >= 0 ? 'text-success' : 'text-danger'"
                        >
                          {{ stats.changeRate?.toFixed(2) }}%
                        </span>
                      </el-descriptions-item>
                    </el-descriptions>
                  </el-card>
                </el-col>
              </el-row>
            </div>
          </div>
        </el-card>
      </div>
    </el-collapse-transition>

    <!-- 主内容区域 -->
    <div class="main-content">
      <el-row :gutter="24">
        <!-- 左侧：同步时间轴 -->
        <el-col
          :xs="24"
          :lg="8"
        >
          <el-card
            shadow="hover"
            class="timeline-card"
          >
            <template #header>
              <div class="card-header">
                <span><el-icon><Clock /></el-icon> 同步时间轴</span>
                <el-switch 
                  v-model="timeAxisConfig.syncEnabled"
                  active-text="同步"
                  inactive-text="独立"
                />
              </div>
            </template>

            <div class="time-range-display">
              <div class="time-item">
                <span class="label">开始时间:</span>
                <span class="value">{{ formatTime(analysisStore.dataTimeRange.start) }}</span>
              </div>
              <div class="time-item">
                <span class="label">结束时间:</span>
                <span class="value">{{ formatTime(analysisStore.dataTimeRange.end) }}</span>
              </div>
              <div class="time-item">
                <span class="label">持续时间:</span>
                <span class="value">{{ formatDuration(analysisStore.dataTimeRange.duration) }}</span>
              </div>
            </div>

            <el-divider />

            <div class="timeline-controls">
              <el-form
                label-width="80px"
                size="small"
              >
                <el-form-item label="显示网格">
                  <el-switch v-model="timeAxisConfig.showGrid" />
                </el-form-item>
                <el-form-item label="网格间隔">
                  <el-input-number
                    v-model="timeAxisConfig.gridInterval"
                    :min="1000"
                    :max="60000"
                    :step="1000"
                    style="width: 100%"
                  />
                </el-form-item>
                <el-form-item label="自动滚动">
                  <el-switch v-model="timeAxisConfig.autoScroll" />
                </el-form-item>
              </el-form>
            </div>
          </el-card>

          <!-- 对比视图配置 -->
          <el-card
            shadow="hover"
            class="comparison-card"
          >
            <template #header>
              <div class="card-header">
                <span><el-icon><Grid /></el-icon> 对比视图</span>
              </div>
            </template>

            <el-form
              label-width="80px"
              size="small"
            >
              <el-form-item label="布局方式">
                <el-radio-group v-model="comparisonConfig.layout">
                  <el-radio-button label="horizontal">
                    水平
                  </el-radio-button>
                  <el-radio-button label="vertical">
                    垂直
                  </el-radio-button>
                  <el-radio-button label="grid">
                    网格
                  </el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="归一化">
                <el-switch v-model="comparisonConfig.normalizeData" />
              </el-form-item>
              <el-form-item label="显示差异">
                <el-switch v-model="comparisonConfig.showDifference" />
              </el-form-item>
              <el-form-item label="叠加模式">
                <el-switch v-model="comparisonConfig.overlayMode" />
              </el-form-item>
            </el-form>
          </el-card>
        </el-col>

        <!-- 右侧：数据图表 -->
        <el-col
          :xs="24"
          :lg="16"
        >
          <el-card
            ref="chartCardRef"
            shadow="hover"
            class="chart-card"
          >
            <template #header>
              <div class="card-header">
                <span><el-icon><TrendCharts /></el-icon> 实时数据图表</span>
                <div class="chart-actions">
                  <el-button-group size="small">
                    <el-button 
                      :icon="ZoomIn"
                      @click="zoomIn"
                    />
                    <el-button 
                      :icon="ZoomOut"
                      @click="zoomOut"
                    />
                    <el-button 
                      :icon="RefreshRight"
                      @click="resetZoom"
                    />
                  </el-button-group>
                </div>
              </div>
            </template>

            <div
              v-if="!analysisStore.hasData"
              class="empty-chart"
            >
              <el-empty description="暂无数据，请选择设备并开始采集">
                <el-button
                  type="primary"
                  @click="showDeviceSelector = true"
                >
                  选择设备
                </el-button>
              </el-empty>
            </div>

            <div
              v-else
              ref="chartRef"
              class="chart-container"
            />
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 设置对话框 -->
    <el-dialog
      v-model="showSettingsDialog"
      title="导出设置"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form label-width="120px">
        <el-divider content-position="left">
          导出格式
        </el-divider>

        <el-form-item label="默认格式">
          <el-radio-group v-model="exportConfig.format">
            <el-radio label="csv">
              CSV
            </el-radio>
            <el-radio label="json">
              JSON
            </el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="包含时间戳">
          <el-switch v-model="exportConfig.includeTimestamp" />
        </el-form-item>

        <el-form-item label="包含统计信息">
          <el-switch v-model="exportConfig.includeStatistics" />
        </el-form-item>

        <el-divider content-position="left">
          格式化选项
        </el-divider>

        <el-form-item label="日期格式">
          <el-input v-model="exportConfig.dateFormat" />
        </el-form-item>

        <el-form-item label="小数位数">
          <el-input-number 
            v-model="exportConfig.decimalPlaces"
            :min="0"
            :max="10"
          />
        </el-form-item>

        <el-form-item label="分隔符">
          <el-input
            v-model="exportConfig.separator"
            style="width: 100px"
          />
        </el-form-item>

        <el-divider content-position="left">
          截图选项
        </el-divider>

        <el-form-item label="背景颜色">
          <el-color-picker v-model="screenshotBackgroundColor" />
        </el-form-item>

        <el-form-item label="像素比例">
          <el-input-number 
            v-model="screenshotPixelRatio"
            :min="1"
            :max="4"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showSettingsDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="applyExportSettings"
        >
          应用
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * @file RealtimeAnalysis.vue
 * @path src/components/
 * @description 实时数据分析组件，提供多设备数据同步、通道过滤、统计计算和导出功能
 * @author Agent
 * @date 2024-03-07
 */

import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useAnalysisStore } from '@/stores/analysis'
import { useDevicesStore } from '@/stores/devices'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import {
  Monitor,
  Filter,
  DataAnalysis,
  Download,
  Setting,
  Refresh,
  VideoPlay,
  VideoPause,
  Clock,
  Grid,
  TrendCharts,
  ZoomIn,
  ZoomOut,
  RefreshRight,
  ArrowDown
} from '@element-plus/icons-vue'

const analysisStore = useAnalysisStore()
const devicesStore = useDevicesStore()

// ==================== 响应式状态 ====================

/** 自动刷新开关 */
const autoRefresh = ref(true)

/** 刷新状态 */
const isRefreshing = ref(false)

/** 显示设备选择器 */
const showDeviceSelector = ref(false)

/** 显示过滤面板 */
const showFilterPanel = ref(false)

/** 显示统计面板 */
const showStatisticsPanel = ref(true)

/** 显示设置对话框 */
const showSettingsDialog = ref(false)

/** 图表容器引用 */
const chartRef = ref(null)

/** 图表卡片引用 */
const chartCardRef = ref(null)

/** 图表实例 */
let chartInstance = null

/** 刷新定时器 */
let refreshTimer = null

/** 刷新间隔 */
const refreshInterval = ref(1000)

/** 数据缓冲区配置 */
const bufferConfig = ref({
  maxSize: 10000, // 每个通道最大缓冲数据点数
  flushInterval: 5000, // 缓冲区刷新间隔（毫秒）
  enableAnimation: true, // 是否启用动画
  animationDuration: 300, // 动画持续时间（毫秒）
  throttleInterval: 100, // 数据更新节流间隔（毫秒）
  batchSize: 100, // 批量处理大小
  enableCompression: true, // 是否启用数据压缩
})

/** 数据缓冲区 */
const dataBuffer = ref({})

/** 缓冲区刷新定时器 */
let bufferFlushTimer = null

/** 数据更新节流定时器 */
let dataUpdateThrottleTimer = null

/** 待处理数据队列 */
const pendingDataQueue = ref([])

/** 动画帧率监控 */
const animationFPS = ref(60)

/** 是否正在播放动画 */
const isAnimating = ref(false)

/** 性能监控指标 */
const performanceMetrics = ref({
  dataReceiveRate: 0, // 数据接收速率（点/秒）
  renderTime: 0, // 渲染耗时
  bufferSize: 0, // 当前缓冲区大小
  droppedPoints: 0, // 丢弃的数据点数
  lastUpdateTime: 0, // 上次更新时间
  averageFPS: 60, // 平均帧率
})

/** WebSocket连接状态 */
const wsConnectionState = ref({
  connected: false,
  reconnectAttempts: 0,
  lastHeartbeat: 0,
  latency: 0,
})

/** 数据压缩配置 */
const compressionConfig = {
  enabled: true,
  algorithm: 'delta', // delta: 增量压缩, threshold: 阈值压缩
  threshold: 0.01, // 变化阈值
}

/** 选中的通道（本地状态） */
const selectedChannels = ref({})

/** 时间范围值 */
const timeRangeValue = ref(null)

/** 数值范围值 */
const valueRangeValue = ref([-100, 100])

/** 采样间隔 */
const samplingInterval = ref(100)

/** 启用平滑 */
const enableSmoothing = ref(false)

/** 平滑窗口 */
const smoothingWindow = ref(5)

/** 实时预览 */
const realtimePreview = ref(true)

/** 时间轴配置 */
const timeAxisConfig = ref({
  syncEnabled: true,
  showGrid: true,
  gridInterval: 5000,
  autoScroll: true
})

/** 对比视图配置 */
const comparisonConfig = ref({
  layout: 'horizontal',
  normalizeData: false,
  showDifference: false,
  overlayMode: false
})

/** 导出配置 */
const exportConfig = ref({
  format: 'csv',
  includeTimestamp: true,
  includeStatistics: true,
  dateFormat: 'YYYY-MM-DD HH:mm:ss',
  decimalPlaces: 4,
  separator: ','
})

/** 截图背景颜色 */
const screenshotBackgroundColor = ref('#ffffff')

/** 截图像素比例 */
const screenshotPixelRatio = ref(2)

/** 缩放级别 */
const zoomLevel = ref(100)

// ==================== 计算属性 ====================

/** 是否选中设备 */
const isSelectedDevice = computed(() => {
  return (deviceId) => analysisStore.selectedDevices.includes(deviceId)
})

// ==================== 方法 ====================

/**
 * 切换自动刷新
 */
function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value
  
  if (autoRefresh.value) {
    startAutoRefresh()
    ElMessage.success('已开始自动刷新')
  } else {
    stopAutoRefresh()
    ElMessage.info('已暂停自动刷新')
  }
}

/**
 * 开始自动刷新
 */
function startAutoRefresh() {
  stopAutoRefresh()
  
  refreshTimer = setInterval(() => {
    refreshData()
  }, refreshInterval.value)
}

/**
 * 停止自动刷新
 */
function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

/**
 * 刷新数据
 */
async function refreshData() {
  if (isRefreshing.value) return
  
  isRefreshing.value = true
  
  try {
    // 模拟数据更新（实际应从设备获取）
    generateMockData()
    
    // 更新缓冲区
    updateDataBuffer()
    
    // 更新图表（带动画）
    await updateChartWithAnimation()
  } catch (error) {
    console.error('[RealtimeAnalysis] Refresh failed:', error)
    ElMessage.error('数据刷新失败')
  } finally {
    isRefreshing.value = false
  }
}

/**
 * 更新数据缓冲区
 * 支持批量处理和数据压缩
 */
function updateDataBuffer() {
  const timestamp = Date.now()
  const config = bufferConfig.value
  
  analysisStore.selectedDevices.forEach(deviceId => {
    const channels = analysisStore.selectedChannels[deviceId] || []
    
    channels.forEach(channelId => {
      const baseValue = Math.random() * 50 + 25
      const noise = (Math.random() - 0.5) * 10
      
      // 初始化缓冲区
      if (!dataBuffer.value[deviceId]) {
        dataBuffer.value[deviceId] = {}
      }
      if (!dataBuffer.value[deviceId][channelId]) {
        dataBuffer.value[deviceId][channelId] = []
      }
      
      const buffer = dataBuffer.value[deviceId][channelId]
      
      // 数据压缩：只添加变化超过阈值的数据点
      if (config.enableCompression && buffer.length > 0) {
        const lastValue = buffer[buffer.length - 1].value
        const change = Math.abs(baseValue + noise - lastValue)
        
        if (change < compressionConfig.threshold) {
          // 数据变化太小，跳过
          performanceMetrics.value.droppedPoints++
          return
        }
      }
      
      // 添加新数据点
      buffer.push({
        timestamp,
        value: baseValue + noise
      })
      
      // 限制缓冲区大小（使用循环缓冲区优化）
      if (buffer.length > config.maxSize) {
        // 移除最旧的10%数据，避免频繁操作
        const removeCount = Math.floor(config.maxSize * 0.1)
        buffer.splice(0, removeCount)
      }
    })
  })
  
  // 更新性能指标
  performanceMetrics.value.bufferSize = getTotalBufferSize()
  performanceMetrics.value.lastUpdateTime = timestamp
}

/**
 * 批量更新数据缓冲区
 * 
 * @param {Array} dataPoints - 数据点数组
 */
function batchUpdateDataBuffer(dataPoints) {
  const config = bufferConfig.value
  
  dataPoints.forEach(point => {
    const { deviceId, channelId, timestamp, value } = point
    
    // 初始化缓冲区
    if (!dataBuffer.value[deviceId]) {
      dataBuffer.value[deviceId] = {}
    }
    if (!dataBuffer.value[deviceId][channelId]) {
      dataBuffer.value[deviceId][channelId] = []
    }
    
    const buffer = dataBuffer.value[deviceId][channelId]
    buffer.push({ timestamp, value })
    
    // 限制缓冲区大小
    if (buffer.length > config.maxSize) {
      buffer.shift()
    }
  })
}

/**
 * 获取总缓冲区大小
 * 
 * @returns {number} 总数据点数
 */
function getTotalBufferSize() {
  let total = 0
  Object.values(dataBuffer.value).forEach(deviceBuffer => {
    Object.values(deviceBuffer).forEach(channelBuffer => {
      total += channelBuffer.length
    })
  })
  return total
}

/**
 * 清空数据缓冲区
 */
function clearDataBuffer() {
  dataBuffer.value = {}
  pendingDataQueue.value = []
  performanceMetrics.value.bufferSize = 0
  performanceMetrics.value.droppedPoints = 0
}

/**
 * 更新图表（带平滑动画）
 * 使用 requestAnimationFrame 和节流优化
 */
async function updateChartWithAnimation() {
  if (!chartInstance) {
    updateChart()
    return
  }
  
  const config = bufferConfig.value
  
  // 节流控制
  const now = Date.now()
  const timeSinceLastUpdate = now - performanceMetrics.value.lastUpdateTime
  
  if (timeSinceLastUpdate < config.throttleInterval) {
    // 延迟更新
    if (!dataUpdateThrottleTimer) {
      dataUpdateThrottleTimer = setTimeout(() => {
        dataUpdateThrottleTimer = null
        performChartUpdate()
      }, config.throttleInterval - timeSinceLastUpdate)
    }
    return
  }
  
  // 立即更新
  await performChartUpdate()
}

/**
 * 执行图表更新
 */
async function performChartUpdate() {
  const startTime = performance.now()
  
  if (!bufferConfig.value.enableAnimation) {
    updateChart()
    return
  }
  
  isAnimating.value = true
  
  // 使用 requestAnimationFrame 实现平滑动画
  await new Promise(resolve => {
    requestAnimationFrame(() => {
      updateChart()
      
      // 动画完成后重置状态
      setTimeout(() => {
        isAnimating.value = false
        
        // 更新性能指标
        const endTime = performance.now()
        performanceMetrics.value.renderTime = endTime - startTime
        
        resolve()
      }, bufferConfig.value.animationDuration)
    })
  })
}

/**
 * 平滑动画过渡
 * 
 * @param {Array} oldData - 旧数据
 * @param {Array} newData - 新数据
 * @param {number} duration - 动画时长
 * @returns {Promise<void>}
 */
async function smoothTransition(oldData, newData, duration = 300) {
  if (!chartInstance) return
  
  const startTime = Date.now()
  const steps = 10 // 动画步数
  const stepDuration = duration / steps
  
  for (let i = 1; i <= steps; i++) {
    const progress = i / steps
    const eased = easeOutCubic(progress)
    
    // 插值计算中间数据
    const interpolatedData = interpolateData(oldData, newData, eased)
    
    // 更新图表
    updateChartWithData(interpolatedData)
    
    await new Promise(resolve => setTimeout(resolve, stepDuration))
  }
}

/**
 * 数据插值
 * 
 * @param {Array} data1 - 数据1
 * @param {Array} data2 - 数据2
 * @param {number} t - 插值因子 (0-1)
 * @returns {Array} 插值后的数据
 */
function interpolateData(data1, data2, t) {
  if (!data1 || !data2) return data2 || data1
  
  const maxLength = Math.max(data1.length, data2.length)
  const result = []
  
  for (let i = 0; i < maxLength; i++) {
    const v1 = data1[i] || data1[data1.length - 1] || 0
    const v2 = data2[i] || data2[data2.length - 1] || 0
    
    result.push(v1 + (v2 - v1) * t)
  }
  
  return result
}

/**
 * 缓动函数（三次方缓出）
 * 
 * @param {number} t - 进度 (0-1)
 * @returns {number} 缓动后的值
 */
function easeOutCubic(t) {
  return 1 - Math.pow(1 - t, 3)
}

/**
 * 使用指定数据更新图表
 * 
 * @param {Object} data - 图表数据
 */
function updateChartWithData(data) {
  if (!chartInstance) return
  
  // 实现数据更新逻辑
  const option = chartInstance.getOption()
  // ... 更新option
  chartInstance.setOption(option)
}

/**
 * 停止缓冲区刷新定时器
 */
function stopBufferFlushTimer() {
  if (bufferFlushTimer) {
    clearInterval(bufferFlushTimer)
    bufferFlushTimer = null
  }
}

/**
 * 定期刷新缓冲区到图表
 */
function startBufferFlushTimer() {
  stopBufferFlushTimer()
  
  bufferFlushTimer = setInterval(() => {
    if (autoRefresh.value) {
      updateChartWithAnimation()
    }
  }, bufferConfig.value.flushInterval)
}



/**
 * 生成模拟数据
 */
function generateMockData() {
  const timestamp = Date.now()
  
  analysisStore.selectedDevices.forEach(deviceId => {
    const channels = analysisStore.selectedChannels[deviceId] || []
    
    channels.forEach(channelId => {
      const baseValue = Math.random() * 50 + 25
      const noise = (Math.random() - 0.5) * 10
      
      analysisStore.addDataPoint(deviceId, channelId, {
        timestamp,
        value: baseValue + noise
      })
    })
  })
}

/**
 * 切换设备选择
 *
 * @param {string} deviceId - 设备ID
 */
function toggleDevice(deviceId) {
  analysisStore.toggleDevice(deviceId)
  
  // 同步本地通道选择状态
  if (analysisStore.selectedDevices.includes(deviceId)) {
    selectedChannels.value[deviceId] = analysisStore.selectedChannels[deviceId] || []
  } else {
    delete selectedChannels.value[deviceId]
  }
}

/**
 * 选择所有设备
 */
function selectAllDevices() {
  analysisStore.selectAll()
  
  // 同步本地通道选择状态
  analysisStore.availableDevices.forEach(device => {
    selectedChannels.value[device.id] = analysisStore.selectedChannels[device.id] || []
  })
}

/**
 * 取消选择所有设备
 */
function deselectAllDevices() {
  analysisStore.deselectAll()
  selectedChannels.value = {}
}

/**
 * 处理通道变更
 *
 * @param {string} deviceId - 设备ID
 */
function handleChannelChange(deviceId) {
  const channels = selectedChannels.value[deviceId] || []
  
  channels.forEach(channelId => {
    if (!analysisStore.selectedChannels[deviceId]?.includes(channelId)) {
      analysisStore.selectChannel(deviceId, channelId)
    }
  })
  
  // 移除未选中的通道
  const currentChannels = analysisStore.selectedChannels[deviceId] || []
  currentChannels.forEach(channelId => {
    if (!channels.includes(channelId)) {
      analysisStore.deselectChannel(deviceId, channelId)
    }
  })
}

/**
 * 处理时间范围变更
 */
function handleTimeRangeChange(value) {
  if (value && value.length === 2) {
    analysisStore.setTimeRangeFilter(value[0], value[1])
  } else {
    analysisStore.setTimeRangeFilter(null, null)
  }
}

/**
 * 处理数值范围变更
 */
function handleValueRangeChange(value) {
  analysisStore.setValueRangeFilter(value[0], value[1])
}

/**
 * 处理平滑变更
 */
function handleSmoothingChange(enabled) {
  analysisStore.setSmoothing(enabled, smoothingWindow.value)
}

/**
 * 重置过滤条件
 */
function resetFilters() {
  timeRangeValue.value = null
  valueRangeValue.value = [-100, 100]
  samplingInterval.value = 100
  enableSmoothing.value = false
  smoothingWindow.value = 5
  
  analysisStore.resetFilters()
  ElMessage.success('过滤条件已重置')
}

/**
 * 获取设备数据点数量
 *
 * @param {string} deviceId - 设备ID
 * @returns {number} 数据点数量
 */
function getDeviceDataCount(deviceId) {
  const deviceData = analysisStore.dataBuffer[deviceId]
  if (!deviceData) return 0
  
  return Object.values(deviceData).reduce((sum, channelData) => {
    return sum + (channelData?.length || 0)
  }, 0)
}

/**
 * 获取通道名称
 *
 * @param {string} deviceId - 设备ID
 * @param {string} channelId - 通道ID
 * @returns {string} 通道名称
 */
function getChannelName(deviceId, channelId) {
  const channel = analysisStore.getChannelConfig(deviceId, channelId)
  return channel ? `${channel.name} (${channel.unit})` : channelId
}

/**
 * 获取趋势类型
 *
 * @param {string} direction - 趋势方向
 * @returns {string} 类型
 */
function getTrendType(direction) {
  switch (direction) {
    case 'increasing':
      return 'success'
    case 'decreasing':
      return 'danger'
    default:
      return 'info'
  }
}

/**
 * 获取趋势文本
 *
 * @param {string} direction - 趋势方向
 * @returns {string} 文本
 */
function getTrendText(direction) {
  switch (direction) {
    case 'increasing':
      return '上升'
    case 'decreasing':
      return '下降'
    default:
      return '稳定'
  }
}

/**
 * 格式化时间
 *
 * @param {number} timestamp - 时间戳
 * @returns {string} 格式化后的时间
 */
function formatTime(timestamp) {
  if (!timestamp) return '--'
  return analysisStore.formatTimestamp(timestamp, 'HH:mm:ss')
}

/**
 * 格式化持续时间
 *
 * @param {number} duration - 持续时间（毫秒）
 * @returns {string} 格式化后的持续时间
 */
function formatDuration(duration) {
  if (!duration) return '--'
  
  const seconds = Math.floor(duration / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  
  if (hours > 0) {
    return `${hours}时${minutes % 60}分${seconds % 60}秒`
  } else if (minutes > 0) {
    return `${minutes}分${seconds % 60}秒`
  } else {
    return `${seconds}秒`
  }
}

  /**
   * 更新图表
   * 优化数据处理和渲染性能
   */
  function updateChart() {
    if (!chartInstance) return
    
    const series = []
    const legendData = []
    
    // 构建图表数据（使用缓冲区数据）
    Object.entries(analysisStore.filteredData).forEach(([deviceId, deviceData]) => {
      Object.entries(deviceData).forEach(([channelId, channelData]) => {
        const channel = analysisStore.getChannelConfig(deviceId, channelId)
        const deviceName = analysisStore.DEVICE_NAMES[deviceId]
        const seriesName = `${deviceName}-${channel?.name || channelId}`
        
        legendData.push(seriesName)
        
        // 使用缓冲区中的数据
        const bufferedData = dataBuffer.value[deviceId]?.[channelId] || channelData
        
        series.push({
          name: seriesName,
          type: 'line',
          data: bufferedData.map(d => [d.timestamp, d.value]),
          symbol: 'none',
          lineStyle: {
            width: 2,
            color: channel?.color || '#409eff'
          },
          // 性能优化配置
          animation: false,
          sampling: 'lttb',
          large: bufferedData.length > 5000,
          progressive: 1000,
          progressiveThreshold: 5000,
        })
      })
    })
    
    // 更新图表配置
    chartInstance.setOption({
    legend: {
      data: legendData,
      top: 10,
      textStyle: {
        color: '#606266'
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '10%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'time',
      name: '时间',
      nameLocation: 'middle',
      nameGap: 30,
      nameTextStyle: {
        color: '#909399'
      },
      axisLine: {
        lineStyle: {
          color: '#E4E7ED'
        }
      },
      axisLabel: {
        color: '#606266',
        formatter: (value) => {
          return formatTime(value)
        }
      },
      splitLine: {
        show: timeAxisConfig.value.showGrid,
        lineStyle: {
          color: '#E4E7ED'
        }
      }
    },
    yAxis: {
      type: 'value',
      name: '数值',
      nameLocation: 'middle',
      nameGap: 40,
      nameTextStyle: {
        color: '#909399'
      },
      axisLine: {
        lineStyle: {
          color: '#E4E7ED'
        }
      },
      axisLabel: {
        color: '#606266'
      },
      splitLine: {
        lineStyle: {
          color: '#E4E7ED'
        }
      }
    },
    dataZoom: [
      {
        type: 'inside',
        start: 100 - zoomLevel.value,
        end: 100
      },
      {
        type: 'slider',
        start: 100 - zoomLevel.value,
        end: 100,
        height: 20,
        bottom: 10
      }
    ],
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      formatter: (params) => {
        if (!params || params.length === 0) return ''
        
        const time = formatTime(params[0].data[0])
        let html = `<div style="font-weight: bold; margin-bottom: 8px;">${time}</div>`
        
        params.forEach(param => {
          html += `
            <div style="display: flex; justify-content: space-between; align-items: center; margin: 4px 0;">
              <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: ${param.color}; margin-right: 8px;"></span>
              <span style="flex: 1;">${param.seriesName}</span>
              <span style="font-weight: bold; margin-left: 16px;">${param.data[1].toFixed(3)}</span>
            </div>
          `
        })
        
        return html
      }
    },
    series
  }, true)
}

/**
 * 放大
 */
function zoomIn() {
  zoomLevel.value = Math.min(100, zoomLevel.value + 10)
  updateChart()
}

/**
 * 缩小
 */
function zoomOut() {
  zoomLevel.value = Math.max(10, zoomLevel.value - 10)
  updateChart()
}

/**
 * 重置缩放
 */
function resetZoom() {
  zoomLevel.value = 100
  updateChart()
}

/**
 * 处理导出命令
 *
 * @param {string} command - 导出命令
 */
async function handleExportCommand(command) {
  try {
    switch (command) {
      case 'csv':
        analysisStore.downloadExport('csv')
        ElMessage.success('CSV 导出成功')
        break
      
      case 'json':
        analysisStore.downloadExport('json')
        ElMessage.success('JSON 导出成功')
        break
      
      case 'screenshot':
        if (chartCardRef.value?.$el) {
          await analysisStore.exportChartScreenshot(chartCardRef.value.$el, {
            backgroundColor: screenshotBackgroundColor.value,
            pixelRatio: screenshotPixelRatio.value
          })
          ElMessage.success('截图保存成功')
        } else {
          ElMessage.warning('无法获取图表元素')
        }
        break
    }
  } catch (error) {
    console.error('[RealtimeAnalysis] Export failed:', error)
    ElMessage.error('导出失败: ' + error.message)
  }
}

/**
 * 应用导出设置
 */
function applyExportSettings() {
  analysisStore.exportConfig = { ...exportConfig.value }
  showSettingsDialog.value = false
  ElMessage.success('设置已应用')
}

/**
 * 处理窗口大小变化
 */
function handleResize() {
  if (chartInstance) {
    chartInstance.resize()
  }
}

// ==================== 生命周期 ====================

onMounted(() => {
  // 初始化 store
  analysisStore.init()
  
  // 初始化图表
  nextTick(() => {
    if (chartRef.value) {
      chartInstance = echarts.init(chartRef.value)
      updateChart()
    }
  })
  
  // 开始自动刷新
  if (autoRefresh.value) {
    startAutoRefresh()
  }
  
  // 监听窗口大小变化
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  // 停止自动刷新
  stopAutoRefresh()
  
  // 清理图表
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  
  // 清理 store
  analysisStore.cleanup()
  
  // 移除事件监听
  window.removeEventListener('resize', handleResize)
})

// 监听过滤条件变化
watch([samplingInterval, enableSmoothing, smoothingWindow], () => {
  analysisStore.setSamplingInterval(samplingInterval.value)
  analysisStore.setSmoothing(enableSmoothing.value, smoothingWindow.value)
  
  if (realtimePreview.value) {
    updateChart()
  }
})

// 监听数据变化
watch(() => analysisStore.filteredData, () => {
  if (realtimePreview.value) {
    updateChart()
  }
}, { deep: true })
</script>

<style scoped>
.realtime-analysis {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
  height: 100%;
}

/* 工具栏 */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-4);
  background-color: var(--color-surface-primary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

/* 面板通用样式 */
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-4);
}

.panel-header span {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.panel-actions {
  display: flex;
  gap: var(--spacing-2);
}

/* 设备选择器面板 */
.device-selector-panel {
  margin-bottom: var(--spacing-4);
}

.device-card {
  cursor: pointer;
  transition: all var(--transition-base);
  border: 2px solid transparent;
}

.device-card:hover {
  box-shadow: var(--shadow-md);
}

.device-card.selected {
  border-color: var(--color-primary-500);
  background-color: var(--color-primary-50);
}

.device-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  margin-bottom: var(--spacing-3);
}

.device-name {
  flex: 1;
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.channel-list {
  margin-top: var(--spacing-3);
  padding-top: var(--spacing-3);
  border-top: 1px solid var(--color-border-primary);
}

.channel-item {
  margin-bottom: var(--spacing-2);
}

.channel-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.channel-color {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: var(--radius-sm);
}

.selection-summary {
  display: flex;
  gap: var(--spacing-2);
  margin-top: var(--spacing-4);
  padding-top: var(--spacing-4);
  border-top: 1px solid var(--color-border-primary);
}

/* 过滤面板 */
.filter-panel {
  margin-bottom: var(--spacing-4);
}

.form-hint {
  display: block;
  margin-top: var(--spacing-1);
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

/* 统计面板 */
.statistics-panel {
  margin-bottom: var(--spacing-4);
}

.empty-state {
  padding: var(--spacing-8);
}

.statistics-grid {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.device-statistics {
  padding: var(--spacing-4);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
}

.device-title {
  margin: 0 0 var(--spacing-3) 0;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-primary-500);
}

.stat-card {
  margin-bottom: var(--spacing-3);
}

.stat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-3);
}

.stat-channel {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.mono {
  font-family: var(--font-family-mono);
  color: var(--color-primary-500);
  font-weight: var(--font-weight-medium);
}

.text-success {
  color: var(--color-success-500);
}

.text-danger {
  color: var(--color-danger-500);
}

/* 主内容区域 */
.main-content {
  flex: 1;
  min-height: 0;
}

.timeline-card,
.comparison-card {
  margin-bottom: var(--spacing-4);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-4);
}

.card-header span {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.time-range-display {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.time-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-2);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
}

.time-item .label {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.time-item .value {
  font-family: var(--font-family-mono);
  color: var(--color-primary-500);
  font-weight: var(--font-weight-medium);
}

/* 图表卡片 */
.chart-card {
  height: 100%;
  min-height: 400px;
}

.empty-chart {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 400px;
}

.chart-container {
  width: 100%;
  height: 400px;
}

.chart-actions {
  display: flex;
  gap: var(--spacing-2);
}

/* Element Plus 样式覆盖 */
:deep(.el-card) {
  background-color: var(--color-surface-primary);
  border-color: var(--color-border-primary);
  border-radius: var(--radius-lg);
  transition: var(--transition-all);
}

:deep(.el-card:hover) {
  box-shadow: var(--shadow-md);
}

:deep(.el-card__header) {
  padding: var(--spacing-4) var(--spacing-5);
  border-bottom: 1px solid var(--color-border-primary);
  background-color: var(--color-bg-secondary);
}

:deep(.el-card__body) {
  padding: var(--spacing-5);
}

:deep(.el-divider) {
  border-color: var(--color-border-primary);
}

:deep(.el-descriptions) {
  border-radius: var(--radius-md);
  overflow: hidden;
}

:deep(.el-descriptions__label) {
  background-color: var(--color-bg-secondary);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

:deep(.el-descriptions__content) {
  font-family: var(--font-family-mono);
  color: var(--color-text-primary);
}

:deep(.el-dialog) {
  border-radius: var(--radius-lg);
}

:deep(.el-dialog__header) {
  border-bottom: 1px solid var(--color-border-primary);
  padding: var(--spacing-4) var(--spacing-5);
}

:deep(.el-dialog__body) {
  padding: var(--spacing-5);
}

/* 响应式优化 */
@media (max-width: 768px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-3);
  }
  
  .toolbar-left,
  .toolbar-right {
    justify-content: center;
  }
  
  .chart-container {
    height: 300px;
  }
}
</style>
