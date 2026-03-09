<template>
  <el-card class="ammeter-control">
    <template #header>
      <div class="card-header">
        <el-icon class="header-icon">
          <Aim />
        </el-icon>
        <span class="header-title">微电流采集控制</span>
      </div>
    </template>

    <div class="control-content">
      <!-- 连接状态 -->
      <div
        class="connection-status"
        :class="isConnected ? 'connected' : 'disconnected'"
      >
        <span class="status-dot" />
        <span class="status-text">{{ connectionStatus }}</span>
      </div>

      <!-- 主要控制区域 -->
      <el-tabs
        v-model="activeTab"
        class="control-tabs"
      >
        <!-- 采集控制面板 -->
        <el-tab-pane
          label="采集控制"
          name="collection"
        >
          <div class="collection-control">
            <!-- 采样率设置 -->
            <div class="sample-rate-section">
              <div class="section-label">
                采样率设置
              </div>
              <div class="rate-control">
                <div class="rate-display">
                  <span
                    class="rate-value"
                    :class="{ 'rate-changing': isRateChanging }"
                  >
                    {{ sampleRate }}
                  </span>
                  <span class="rate-unit">Hz</span>
                </div>
                <el-slider
                  v-model="sampleRateValue"
                  :min="1"
                  :max="10000"
                  :step="1"
                  :disabled="!canControl || isCollecting"
                  show-input
                  class="rate-slider"
                  @change="handleSampleRateChange"
                  @input="onRateInput"
                />
                <div class="rate-marks">
                  <span class="mark">1 Hz</span>
                  <span class="mark">2500 Hz</span>
                  <span class="mark">5000 Hz</span>
                  <span class="mark">7500 Hz</span>
                  <span class="mark">10000 Hz</span>
                </div>
              </div>
            </div>

            <!-- 快捷采样率按钮 -->
            <div class="quick-rate-section">
              <div class="section-label">
                快捷设置
              </div>
              <div class="quick-rate-buttons">
                <button
                  v-for="rate in quickSampleRates"
                  :key="rate"
                  class="quick-btn"
                  :class="{ 'quick-btn--active': sampleRate === rate }"
                  :disabled="!canControl || isCollecting"
                  @click="setQuickSampleRate(rate)"
                >
                  {{ formatRate(rate) }}
                </button>
              </div>
            </div>

            <!-- 采集控制按钮 -->
            <div class="collection-actions">
              <button
                class="action-btn"
                :class="isCollecting ? 'action-btn--danger' : 'action-btn--primary'"
                :disabled="!canControl"
                @click="toggleCollection"
              >
                <el-icon v-if="!isCollecting">
                  <VideoPlay />
                </el-icon>
                <el-icon v-else>
                  <VideoPause />
                </el-icon>
                <span>{{ isCollecting ? '停止采集' : '开始采集' }}</span>
              </button>

              <button
                class="action-btn"
                :disabled="!isConnected"
                @click="handleClearBuffer"
              >
                <el-icon><Delete /></el-icon>
                <span>清空缓冲区</span>
              </button>

              <button
                class="action-btn"
                :disabled="!isConnected"
                @click="refreshStatus"
              >
                <el-icon><Refresh /></el-icon>
                <span>刷新状态</span>
              </button>
            </div>

            <!-- 采集统计信息 -->
            <div class="stats-section">
              <div class="section-label">
                采集统计
              </div>
              <div class="stats-grid">
                <div class="stat-card">
                  <div class="stat-label">
                    采集状态
                  </div>
                  <div class="stat-value">
                    <span
                      class="status-badge"
                      :class="`status-badge--${collectingStatusType}`"
                    >
                      {{ collectingStatusText }}
                    </span>
                  </div>
                </div>
                <div class="stat-card">
                  <div class="stat-label">
                    采样率
                  </div>
                  <div class="stat-value">
                    <span class="mono">{{ sampleRate }}</span>
                    <span class="unit">Hz</span>
                  </div>
                </div>
                <div class="stat-card">
                  <div class="stat-label">
                    已采集样本
                  </div>
                  <div class="stat-value">
                    <span class="mono">{{ collectionStats.samples_collected }}</span>
                    <span class="unit">个</span>
                  </div>
                </div>
                <div class="stat-card">
                  <div class="stat-label">
                    数据速率
                  </div>
                  <div class="stat-value">
                    <span class="mono">{{ collectionStats.data_rate.toFixed(1) }}</span>
                    <span class="unit">样本/秒</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- 通道配置面板 -->
        <el-tab-pane
          label="通道配置"
          name="channels"
        >
          <div class="channel-config-panel">
            <div class="section-label">
              通道参数配置
            </div>
            
            <el-row :gutter="16">
              <el-col
                v-for="channelNum in channelCount"
                :key="channelNum"
                :span="12"
                class="channel-col"
              >
                <el-card
                  shadow="hover"
                  class="channel-config-card"
                >
                  <div class="channel-header">
                    <div class="channel-title">
                      <el-switch
                        v-model="channelConfigs[channelNum].enabled"
                        :disabled="!canControl || isCollecting"
                        @change="handleChannelEnable(channelNum, $event)"
                      />
                      <span class="channel-name">通道 {{ channelNum }}</span>
                    </div>
                    <el-tag
                      :type="channelConfigs[channelNum].enabled ? 'success' : 'info'"
                      size="small"
                    >
                      {{ channelConfigs[channelNum].enabled ? '启用' : '禁用' }}
                    </el-tag>
                  </div>

                  <el-form
                    v-if="channelConfigs[channelNum].enabled"
                    label-width="80px"
                    size="small"
                    class="channel-form"
                  >
                    <el-form-item label="量程">
                      <el-select
                        v-model="channelConfigs[channelNum].range"
                        :disabled="!canControl || isCollecting"
                        placeholder="选择量程"
                        @change="handleChannelConfig(channelNum, 'range', $event)"
                      >
                        <el-option
                          label="自动"
                          value="auto"
                        />
                        <el-option
                          label="低量程"
                          value="low"
                        />
                        <el-option
                          label="中量程"
                          value="medium"
                        />
                        <el-option
                          label="高量程"
                          value="high"
                        />
                      </el-select>
                    </el-form-item>

                    <el-form-item label="滤波">
                      <el-select
                        v-model="channelConfigs[channelNum].filter"
                        :disabled="!canControl || isCollecting"
                        placeholder="选择滤波"
                        @change="handleChannelConfig(channelNum, 'filter', $event)"
                      >
                        <el-option
                          label="低通滤波"
                          value="low"
                        />
                        <el-option
                          label="中通滤波"
                          value="medium"
                        />
                        <el-option
                          label="高通滤波"
                          value="high"
                        />
                      </el-select>
                    </el-form-item>
                  </el-form>
                </el-card>
              </el-col>
            </el-row>
          </div>
        </el-tab-pane>

        <!-- 实时数据面板 -->
        <el-tab-pane
          label="实时数据"
          name="realtime"
        >
          <div class="realtime-panel">
            <!-- 缓冲区状态 -->
            <div class="buffer-status-section">
              <div class="section-label">
                缓冲区状态
              </div>
              <div class="buffer-status-display">
                <div class="buffer-info">
                  <div class="buffer-header">
                    <span class="buffer-label">缓冲区使用率</span>
                    <span
                      class="buffer-percent"
                      :class="`buffer-percent--${bufferStatusType}`"
                    >
                      {{ bufferUsagePercent }}%
                    </span>
                  </div>
                  <div class="buffer-bar">
                    <div
                      class="buffer-fill"
                      :class="`buffer-fill--${bufferStatusType}`"
                      :style="{ width: `${bufferUsagePercent}%` }"
                    />
                  </div>
                  <div class="buffer-details">
                    <span>已用: {{ bufferStatus.size }} / {{ bufferStatus.max_size }}</span>
                    <span>{{ bufferStatusText }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 通道数据显示 -->
            <div class="channel-data-section">
              <div class="section-label">
                通道实时数据
              </div>
              <el-row :gutter="16">
                <el-col
                  v-for="channelNum in channelCount"
                  :key="channelNum"
                  :span="6"
                  class="data-channel-col"
                >
                  <div
                    class="data-channel-card"
                    :class="{
                      'data-channel-active': isCollecting && channelConfigs[channelNum]?.enabled,
                      'data-channel-disabled': !channelConfigs[channelNum]?.enabled
                    }"
                  >
                    <div class="data-channel-header">
                      <span class="data-channel-name">通道 {{ channelNum }}</span>
                      <el-tag
                        :type="channelConfigs[channelNum]?.enabled ? 'success' : 'info'"
                        size="small"
                      >
                        {{ channelConfigs[channelNum]?.enabled ? '启用' : '禁用' }}
                      </el-tag>
                    </div>
                    <div class="data-channel-value">
                      <span
                        class="data-value"
                        :class="{ 'data-value-changing': isCollecting }"
                      >
                        {{ formatCurrent(channelData[channelNum] || 0) }}
                      </span>
                    </div>
                    <div
                      v-if="snrData[channelNum]"
                      class="data-channel-snr"
                    >
                      <span class="snr-label">SNR:</span>
                      <span class="snr-value">{{ snrData[channelNum].snr?.toFixed(2) || 'N/A' }} dB</span>
                    </div>
                  </div>
                </el-col>
              </el-row>
            </div>

            <!-- 信噪比监控 -->
            <div class="snr-section">
              <div class="section-label">
                信噪比监控
              </div>
              <div class="snr-actions">
                <button
                  class="snr-btn"
                  :disabled="!isConnected"
                  @click="refreshAllSNR"
                >
                  <el-icon><Refresh /></el-icon>
                  <span>刷新SNR</span>
                </button>
              </div>
              <el-row :gutter="16">
                <el-col
                  v-for="channelNum in channelCount"
                  :key="channelNum"
                  :span="6"
                >
                  <div class="snr-card">
                    <div class="snr-header">
                      通道 {{ channelNum }}
                    </div>
                    <div class="snr-content">
                      <div class="snr-item">
                        <span class="snr-item-label">SNR</span>
                        <span class="snr-item-value">
                          {{ snrData[channelNum]?.snr?.toFixed(2) || 'N/A' }} dB
                        </span>
                      </div>
                      <div class="snr-item">
                        <span class="snr-item-label">信号</span>
                        <span class="snr-item-value">
                          {{ formatCurrent(snrData[channelNum]?.signal || 0) }}
                        </span>
                      </div>
                      <div class="snr-item">
                        <span class="snr-item-label">噪声</span>
                        <span class="snr-item-value">
                          {{ formatCurrent(snrData[channelNum]?.noise || 0) }}
                        </span>
                      </div>
                    </div>
                  </div>
                </el-col>
              </el-row>
            </div>
          </div>
        </el-tab-pane>

        <!-- 数据可视化面板 -->
        <el-tab-pane
          label="数据图表"
          name="chart"
        >
          <div class="chart-panel">
            <AmmeterWaveform
              :data="realtimeData"
              :channel-config="channelConfigs"
              :channel-count="channelCount"
              :auto-update="autoUpdate"
              :update-interval="200"
              @zoom-change="handleZoomChange"
              @channel-toggle="handleChannelToggle"
              @display-mode-change="handleDisplayModeChange"
            />
          </div>
        </el-tab-pane>

        <!-- 高级通道配置面板 -->
        <el-tab-pane
          label="高级配置"
          name="advanced"
        >
          <div class="advanced-panel">
            <AmmeterChannelConfig
              :channel-config="channelConfigs"
              :channel-count="channelCount"
              :can-control="canControl"
              :is-collecting="isCollecting"
              @channel-enable="handleChannelEnable"
              @channel-config="handleChannelConfig"
              @batch-enable="handleBatchEnable"
              @batch-config="handleBatchConfig"
            />
          </div>
        </el-tab-pane>

        <!-- 采集模板管理面板 -->
        <el-tab-pane
          label="模板管理"
          name="templates"
        >
          <div class="templates-panel">
            <!-- 模板列表 -->
            <div class="templates-section">
              <div class="section-header">
                <h3 class="section-title">
                  采集参数模板
                </h3>
                <el-button
                  size="small"
                  type="primary"
                  :disabled="!canControl || isCollecting"
                  @click="showSaveTemplateDialog = true"
                >
                  <el-icon><Plus /></el-icon>
                  保存当前配置为模板
                </el-button>
              </div>

              <div
                v-if="collectionTemplates.length > 0"
                class="templates-list"
              >
                <div
                  v-for="template in collectionTemplates"
                  :key="template.id"
                  class="template-item"
                  :class="{ 'template-active': activeTemplateId === template.id }"
                >
                  <div class="template-info">
                    <div class="template-name">
                      {{ template.name }}
                    </div>
                    <div class="template-meta">
                      <span>采样率: {{ template.config.sampleRate }} Hz</span>
                      <span>创建时间: {{ formatDate(template.createdAt) }}</span>
                    </div>
                  </div>
                  <div class="template-actions">
                    <el-button
                      size="small"
                      :disabled="!canControl || isCollecting"
                      @click="applyTemplate(template.id)"
                    >
                      应用
                    </el-button>
                    <el-button
                      size="small"
                      @click="editTemplate(template)"
                    >
                      编辑
                    </el-button>
                    <el-button
                      size="small"
                      type="danger"
                      @click="deleteTemplate(template.id)"
                    >
                      删除
                    </el-button>
                  </div>
                </div>
              </div>

              <div
                v-else
                class="empty-state"
              >
                <el-icon class="empty-icon">
                  <Document />
                </el-icon>
                <p>暂无模板，请保存当前配置为模板</p>
              </div>
            </div>

            <!-- SNR阈值配置 -->
            <div class="snr-config-section">
              <div class="section-header">
                <h3 class="section-title">
                  SNR阈值配置
                </h3>
              </div>

              <div class="snr-thresholds">
                <div class="threshold-item">
                  <label>警告阈值 (dB)</label>
                  <el-input-number
                    v-model="snrThresholds.warning"
                    :min="0"
                    :max="100"
                    :step="1"
                    :disabled="!canControl || isCollecting"
                  />
                </div>
                <div class="threshold-item">
                  <label>临界阈值 (dB)</label>
                  <el-input-number
                    v-model="snrThresholds.critical"
                    :min="0"
                    :max="100"
                    :step="1"
                    :disabled="!canControl || isCollecting"
                  />
                </div>
              </div>

              <!-- SNR告警显示 -->
              <div
                v-if="hasSNRAlarm"
                class="snr-alarms"
              >
                <div class="alarms-header">
                  <el-icon class="alarm-icon">
                    <Warning />
                  </el-icon>
                  <span>SNR告警</span>
                </div>
                <div class="alarms-list">
                  <div
                    v-for="(alarm, channel) in snrAlarms"
                    v-if="alarm.active"
                    :key="channel"
                    class="alarm-item"
                    :class="`alarm-${alarm.level}`"
                  >
                    <span class="alarm-channel">通道 {{ channel }}</span>
                    <span class="alarm-message">{{ alarm.message }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 缓冲区配置 -->
            <div class="buffer-config-section">
              <div class="section-header">
                <h3 class="section-title">
                  缓冲区配置
                </h3>
              </div>

              <div class="buffer-settings">
                <div class="buffer-setting">
                  <label>最大缓冲区大小</label>
                  <el-input-number
                    v-model="bufferConfig.maxSize"
                    :min="100"
                    :max="100000"
                    :step="1000"
                    :disabled="!canControl || isCollecting"
                  />
                </div>
                <div class="buffer-setting">
                  <label>警告阈值 (%)</label>
                  <el-slider
                    v-model="bufferConfig.warningThreshold"
                    :min="0"
                    :max="1"
                    :step="0.05"
                    :format-tooltip="(val) => (val * 100).toFixed(0) + '%'"
                    :disabled="!canControl || isCollecting"
                  />
                </div>
                <div class="buffer-setting">
                  <label>临界阈值 (%)</label>
                  <el-slider
                    v-model="bufferConfig.criticalThreshold"
                    :min="0"
                    :max="1"
                    :step="0.05"
                    :format-tooltip="(val) => (val * 100).toFixed(0) + '%'"
                    :disabled="!canControl || isCollecting"
                  />
                </div>
                <div class="buffer-setting">
                  <el-checkbox
                    v-model="bufferConfig.autoClear"
                    :disabled="!canControl || isCollecting"
                  >
                    自动清理缓冲区
                  </el-checkbox>
                </div>
              </div>

              <!-- 缓冲区优化建议 -->
              <div class="buffer-optimization">
                <el-button
                  size="small"
                  :disabled="realtimeData.length === 0"
                  @click="showBufferOptimization"
                >
                  分析缓冲区使用情况
                </el-button>
              </div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 保存模板对话框 -->
    <el-dialog
      v-model="showSaveTemplateDialog"
      title="保存采集参数模板"
      width="500px"
    >
      <el-form
        :model="templateForm"
        label-width="100px"
      >
        <el-form-item label="模板名称">
          <el-input
            v-model="templateForm.name"
            placeholder="请输入模板名称"
          />
        </el-form-item>

        <el-form-item label="配置预览">
          <div class="config-preview">
            <div class="preview-item">
              <span class="preview-label">采样率:</span>
              <span class="preview-value">{{ sampleRate }} Hz</span>
            </div>
            <div class="preview-item">
              <span class="preview-label">启用通道:</span>
              <span class="preview-value">{{ enabledChannelsCount }} 个</span>
            </div>
            <div class="preview-item">
              <span class="preview-label">缓冲区大小:</span>
              <span class="preview-value">{{ bufferConfig.maxSize }}</span>
            </div>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showSaveTemplateDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :disabled="!templateForm.name"
          @click="handleSaveTemplate"
        >
          保存
        </el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
/**
 * @file AmmeterControl.vue
 * @path src/components/
 * @description 微电流采集控制组件，提供采集控制、通道配置、实时数据显示和数据可视化功能
 * @author Agent
 * @date 2024-03-07
 * @dependencies vue, element-plus, echarts, pinia
 */

import { ref, reactive, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAmmeterStore } from '../stores/ammeter'
import { AMMETER } from '../config/constants'
import AmmeterWaveform from './AmmeterWaveform.vue'
import AmmeterChannelConfig from './AmmeterChannelConfig.vue'

// ============ Store 使用 ============

const ammeterStore = useAmmeterStore()

// ============ 类型定义 ============

/**
 * @typedef {Object} ChannelConfig
 * @property {boolean} enabled - 是否启用
 * @property {string} range - 量程 ('auto' | 'low' | 'medium' | 'high')
 * @property {string} filter - 滤波设置 ('low' | 'medium' | 'high')
 */

/**
 * @typedef {Object} SNRData
 * @property {number} snr - 信噪比 (dB)
 * @property {number} signal - 信号值
 * @property {number} noise - 噪声值
 */

// ============ 常量定义 ============

const quickSampleRates = [1, 10, 100, 1000, 5000, 10000]

// ============ 响应式状态 ============

// Tab 控制
const activeTab = ref('collection')

// 采样率控制
const sampleRateValue = ref(1000)
const isRateChanging = ref(false)

// 通道配置本地状态
const channelConfigs = reactive({
  1: { enabled: true, range: 'auto', filter: 'low' },
  2: { enabled: true, range: 'auto', filter: 'low' },
  3: { enabled: true, range: 'auto', filter: 'low' },
  4: { enabled: true, range: 'auto', filter: 'low' }
})

// 图表相关
const chartContainer = ref(null)
const chartInstance = null
const visibleChannels = ref([1, 2, 3, 4])
const autoUpdate = ref(false)
const chartUpdateTimer = null

// 模板管理相关
const showSaveTemplateDialog = ref(false)
const templateForm = ref({
  name: ''
})

// 从 Store 获取新增的状态
const collectionTemplates = computed(() => ammeterStore.collectionTemplates)
const activeTemplateId = computed(() => ammeterStore.activeTemplateId)
const snrThresholds = computed(() => ammeterStore.snrThresholds)
const snrAlarms = computed(() => ammeterStore.snrAlarms)
const hasSNRAlarm = computed(() => ammeterStore.hasSNRAlarm)
const bufferConfig = computed(() => ammeterStore.bufferConfig)

// ============ 计算属性 ============

// 从 Store 获取状态
const isConnected = computed(() => ammeterStore.isConnected)
const status = computed(() => ammeterStore.status)
const isCollecting = computed(() => ammeterStore.isCollecting)
const sampleRate = computed(() => ammeterStore.sampleRate)
const channelCount = computed(() => ammeterStore.channelCount)
const channelData = computed(() => ammeterStore.channelData)
const bufferStatus = computed(() => ammeterStore.bufferStatus)
const bufferUsagePercent = computed(() => ammeterStore.bufferUsagePercent)
const bufferStatusType = computed(() => ammeterStore.bufferStatusType)
const bufferStatusText = computed(() => ammeterStore.bufferStatusText)
const snrData = computed(() => ammeterStore.snrData)
const realtimeData = computed(() => ammeterStore.realtimeData)
const collectionStats = computed(() => ammeterStore.collectionStats)
const canControl = computed(() => ammeterStore.canControl)

// 连接状态文本
const connectionStatus = computed(() => {
  if (isConnected.value) {
    return status.value === 'ready' ? '设备已就绪' : '设备已连接'
  }
  return '设备未连接'
})

// 采集状态类型
const collectingStatusType = computed(() => {
  return isCollecting.value ? 'primary' : 'success'
})

// 采集状态文本
const collectingStatusText = computed(() => {
  return isCollecting.value ? '采集中' : '空闲'
})

// 启用通道数量
const enabledChannelsCount = computed(() => {
  return Object.values(channelConfigs).filter(c => c.enabled).length
})

// ============ 方法 ============

/**
 * 格式化采样率显示
 * 
 * @param {number} rate - 采样率 (Hz)
 * @returns {string} 格式化后的字符串
 */
function formatRate(rate) {
  if (rate >= 1000) {
    return `${(rate / 1000).toFixed(1)} kHz`
  }
  return `${rate} Hz`
}

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
 * 切换采集状态
 */
async function toggleCollection() {
  if (isCollecting.value) {
    const success = await ammeterStore.stopCollection()
    if (success) {
      ElMessage.success('停止采集')
    }
  } else {
    const success = await ammeterStore.startCollection()
    if (success) {
      ElMessage.success('开始采集')
    }
  }
}

/**
 * 清空缓冲区
 */
async function handleClearBuffer() {
  const success = await ammeterStore.clearBuffer()
  if (success) {
    ElMessage.success('缓冲区已清空')
  }
}

/**
 * 刷新状态
 */
async function refreshStatus() {
  await ammeterStore.fetchStatus()
  ElMessage.success('状态已刷新')
}

/**
 * 采样率滑块输入处理
 * 
 * @param {number} value - 新采样率值
 */
function onRateInput(value) {
  isRateChanging.value = true
  
  setTimeout(() => {
    isRateChanging.value = false
  }, 300)
}

/**
 * 采样率变化处理
 * 
 * @param {number} value - 新采样率值
 */
async function handleSampleRateChange(value) {
  const success = await ammeterStore.setSampleRate(value)
  if (success) {
    ElMessage.success(`采样率已设置为 ${value} Hz`)
  } else {
    // 恢复原值
    sampleRateValue.value = sampleRate.value
  }
}

/**
 * 设置快捷采样率
 * 
 * @param {number} rate - 目标采样率
 */
async function setQuickSampleRate(rate) {
  sampleRateValue.value = rate
  await handleSampleRateChange(rate)
}

/**
 * 通道启用/禁用处理
 * 
 * @param {number} channel - 通道编号
 * @param {boolean} enabled - 是否启用
 */
async function handleChannelEnable(channel, enabled) {
  await ammeterStore.configureChannel(channel, { enabled })
}

/**
 * 通道配置变化处理
 * 
 * @param {number} channel - 通道编号
 * @param {string} key - 配置键
 * @param {any} value - 配置值
 */
async function handleChannelConfig(channel, key, value) {
  await ammeterStore.configureChannel(channel, { [key]: value })
}

/**
 * 刷新所有通道SNR
 */
async function refreshAllSNR() {
  await ammeterStore.fetchAllSNR()
  ElMessage.success('SNR数据已刷新')
}

/**
 * 清空图表数据
 */
function clearChartData() {
  ammeterStore.clearRealtimeData()
  if (chartInstance) {
    chartInstance.clear()
  }
  ElMessage.info('数据已清空')
}

/**
 * 处理波形缩放变化
 * 
 * @param {number} level - 缩放级别
 */
function handleZoomChange(level) {
  console.log('Zoom level changed:', level)
}

/**
 * 处理通道切换
 * 
 * @param {Array} channels - 可见通道列表
 */
function handleChannelToggle(channels) {
  visibleChannels.value = channels
}

/**
 * 处理显示模式变化
 * 
 * @param {string} mode - 显示模式
 */
function handleDisplayModeChange(mode) {
  console.log('Display mode changed:', mode)
}

/**
 * 处理批量启用通道
 * 
 * @param {Array} channels - 通道列表
 * @param {boolean} enabled - 是否启用
 */
async function handleBatchEnable(channels, enabled) {
  for (const channel of channels) {
    await ammeterStore.configureChannel(channel, { enabled })
  }
  ElMessage.success(`已${enabled ? '启用' : '禁用'} ${channels.length} 个通道`)
}

/**
 * 处理批量配置通道
 * 
 * @param {Array} channels - 通道列表
 * @param {Object} config - 配置对象
 */
async function handleBatchConfig(channels, config) {
  for (const channel of channels) {
    await ammeterStore.configureChannel(channel, config)
  }
  ElMessage.success(`已配置 ${channels.length} 个通道`)
}

/**
 * 保存模板
 */
function handleSaveTemplate() {
  if (!templateForm.value.name) {
    ElMessage.warning('请输入模板名称')
    return
  }

  const templateId = ammeterStore.saveTemplate(templateForm.value.name, {
    sampleRate: sampleRate.value,
    channelConfig: { ...channelConfigs },
    bufferConfig: { ...bufferConfig.value },
    snrThresholds: { ...snrThresholds.value }
  })

  showSaveTemplateDialog.value = false
  templateForm.value.name = ''
  ElMessage.success('模板保存成功')
}

/**
 * 应用模板
 * 
 * @param {string} templateId - 模板ID
 */
async function applyTemplate(templateId) {
  try {
    await ElMessageBox.confirm(
      '应用模板将覆盖当前配置，确定继续吗？',
      '确认应用',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const success = ammeterStore.loadTemplate(templateId)
    if (success) {
      ElMessage.success('模板应用成功')
      
      // 同步本地状态
      Object.keys(channelConfigs).forEach(channel => {
        const config = ammeterStore.channelConfig[channel]
        if (config) {
          channelConfigs[channel] = { ...config }
        }
      })
      
      sampleRateValue.value = sampleRate.value
    }
  } catch {
    // 用户取消
  }
}

/**
 * 编辑模板
 * 
 * @param {Object} template - 模板对象
 */
function editTemplate(template) {
  ElMessage.info('模板编辑功能开发中')
}

/**
 * 删除模板
 * 
 * @param {string} templateId - 模板ID
 */
async function deleteTemplate(templateId) {
  try {
    await ElMessageBox.confirm(
      '确定要删除此模板吗？',
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const success = ammeterStore.deleteTemplate(templateId)
    if (success) {
      ElMessage.success('模板已删除')
    }
  } catch {
    // 用户取消
  }
}

/**
 * 格式化日期
 * 
 * @param {number} timestamp - 时间戳
 * @returns {string} 格式化后的日期字符串
 */
function formatDate(timestamp) {
  const date = new Date(timestamp)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

/**
 * 显示缓冲区优化建议
 */
function showBufferOptimization() {
  const stats = ammeterStore.optimizeBufferSize()
  
  let message = `当前缓冲区大小: ${stats.currentSize}\n`
  message += `平均使用率: ${stats.averageUsage.toFixed(1)}%\n`
  message += `峰值使用率: ${stats.peakUsage.toFixed(1)}%\n\n`
  message += `建议: ${stats.recommendation.reason}`
  
  if (stats.recommendation.action !== 'maintain') {
    message += `\n建议大小: ${stats.recommendation.suggestedSize}`
  }
  
  ElMessageBox.alert(message, '缓冲区使用分析', {
    confirmButtonText: '确定',
    type: 'info'
  })
}

// ============ 生命周期钩子 ============

onMounted(() => {
  // 初始化 Store
  ammeterStore.init()

  // 同步通道配置
  Object.keys(channelConfigs).forEach(channel => {
    const config = ammeterStore.channelConfig[channel]
    if (config) {
      channelConfigs[channel] = { ...config }
    }
  })

  // 同步采样率
  sampleRateValue.value = sampleRate.value
})

onBeforeUnmount(() => {
  // 清理 Store
  ammeterStore.cleanup()
})

// ============ 监听器 ============

// 监听 Store 中的采样率变化
watch(sampleRate, (newRate) => {
  sampleRateValue.value = newRate
})

// 监听 Store 中的通道配置变化
watch(() => ammeterStore.channelConfig, (newConfig) => {
  Object.keys(newConfig).forEach(channel => {
    channelConfigs[channel] = { ...newConfig[channel] }
  })
}, { deep: true })

// ============ 监听器 ============

// 监听 Store 中的采样率变化
watch(sampleRate, (newRate) => {
  sampleRateValue.value = newRate
})

// 监听 Store 中的通道配置变化
watch(() => ammeterStore.channelConfig, (newConfig) => {
  Object.keys(newConfig).forEach(channel => {
    channelConfigs[channel] = { ...newConfig[channel] }
  })
}, { deep: true })

</script>

<style scoped>
.ammeter-control {
  margin-bottom: var(--spacing-5);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  transition: var(--transition-all);
}

.ammeter-control:hover {
  box-shadow: var(--shadow-lg);
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.header-icon {
  font-size: var(--font-size-lg);
  color: var(--color-accent-500);
}

.header-title {
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
}

.control-content {
  padding: var(--spacing-2) 0;
}

/* 连接状态 */
.connection-status {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-3) var(--spacing-4);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-4);
  transition: var(--transition-all);
}

.connection-status.connected {
  background: linear-gradient(135deg, var(--color-success-light), rgba(56, 161, 105, 0.1));
  border: 1px solid rgba(56, 161, 105, 0.3);
}

.connection-status.disconnected {
  background: var(--color-surface-secondary);
  border: 1px solid var(--color-border-primary);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  position: relative;
}

.connected .status-dot {
  background: var(--color-status-online);
}

.connected .status-dot::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
  height: 100%;
  border-radius: var(--radius-full);
  background: var(--color-status-online);
  animation: dot-pulse 2s ease-in-out infinite;
}

.disconnected .status-dot {
  background: var(--color-status-offline);
}

@keyframes dot-pulse {
  0%, 100% {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
  50% {
    opacity: 0;
    transform: translate(-50%, -50%) scale(2);
  }
}

.status-text {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.control-tabs {
  margin-top: var(--spacing-2);
}

/* 通用标签样式 */
.section-label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-3);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* 采样率控制样式 */
.sample-rate-section {
  margin-bottom: var(--spacing-6);
}

.rate-control {
  padding: 0 var(--spacing-2);
}

.rate-display {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-4);
}

.rate-value {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary-500);
  font-family: var(--font-family-mono);
  letter-spacing: 1px;
  transition: var(--transition-colors);
}

.rate-value.rate-changing {
  color: var(--color-accent-500);
  animation: value-flash 0.3s ease;
}

@keyframes value-flash {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.rate-unit {
  font-size: var(--font-size-lg);
  color: var(--color-text-tertiary);
  font-weight: var(--font-weight-medium);
}

/* 采样率滑块样式 - el-slider 组件上直接添加 class */
.rate-slider.el-slider {
  --el-slider-main-bg-color: var(--color-primary-500);
  --el-slider-runway-bg-color: var(--color-neutral-200);
}

/* 滑块轨道样式 */
.rate-slider.el-slider :deep(.el-slider__runway) {
  background-color: var(--color-neutral-200);
  border-radius: var(--radius-full);
}

/* 滑块进度条样式 */
.rate-slider.el-slider :deep(.el-slider__bar) {
  background: linear-gradient(90deg, var(--color-primary-400), var(--color-primary-500));
  border-radius: var(--radius-full);
}

/* 滑块按钮样式 */
.rate-slider.el-slider :deep(.el-slider__button-wrapper) {
  transition: var(--transition-all);
}

.rate-slider.el-slider :deep(.el-slider__button) {
  border: 3px solid var(--color-primary-500);
  background: var(--color-surface-primary);
  box-shadow: var(--shadow-md);
  transition: var(--transition-all);
}

.rate-slider.el-slider :deep(.el-slider__button:hover) {
  transform: scale(1.2);
  box-shadow: var(--shadow-glow-primary);
}

/* 滑块输入框样式 */
.rate-slider.el-slider :deep(.el-input-number) {
  width: 100px;
}

.rate-slider.el-slider :deep(.el-input-number .el-input__wrapper) {
  background-color: var(--color-surface-secondary);
  border-radius: var(--radius-sm);
}

.rate-marks {
  display: flex;
  justify-content: space-between;
  margin-top: var(--spacing-2);
  padding: 0 var(--spacing-1);
}

.mark {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-family: var(--font-family-mono);
}

/* 快捷采样率按钮 */
.quick-rate-section {
  margin-bottom: var(--spacing-6);
}

.quick-rate-buttons {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: var(--spacing-2);
}

.quick-btn {
  padding: var(--spacing-3) var(--spacing-2);
  border: 2px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  font-family: var(--font-family-mono);
  cursor: pointer;
  transition: var(--transition-all);
}

.quick-btn:hover:not(:disabled) {
  border-color: var(--color-primary-400);
  background: var(--color-interactive-hover);
  transform: translateY(-2px);
}

.quick-btn--active {
  border-color: var(--color-primary-500);
  background: var(--color-primary-500);
  color: white;
  box-shadow: var(--shadow-glow-primary);
}

.quick-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 采集控制按钮 */
.collection-actions {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-3);
  margin-bottom: var(--spacing-6);
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-2);
  padding: var(--spacing-3) var(--spacing-4);
  border: 2px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: var(--transition-all);
}

.action-btn:hover:not(:disabled) {
  border-color: var(--color-primary-400);
  background: var(--color-interactive-hover);
  transform: translateY(-2px);
}

.action-btn--primary {
  border-color: var(--color-primary-500);
  background: var(--color-primary-500);
  color: white;
}

.action-btn--primary:hover:not(:disabled) {
  background: var(--color-primary-600);
  border-color: var(--color-primary-600);
  box-shadow: var(--shadow-glow-primary);
}

.action-btn--danger {
  border-color: var(--color-error-500);
  background: var(--color-error-500);
  color: white;
}

.action-btn--danger:hover:not(:disabled) {
  background: var(--color-error-600);
  border-color: var(--color-error-600);
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 统计信息 */
.stats-section {
  margin-bottom: var(--spacing-4);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-3);
}

.stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-3);
  background: var(--color-surface-secondary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
}

.stat-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-1);
}

.stat-value .mono {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  font-family: var(--font-family-mono);
}

.stat-value .unit {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.status-badge {
  padding: var(--spacing-1) var(--spacing-2);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
}

.status-badge--success {
  background: var(--color-success-light);
  color: var(--color-success-dark);
}

.status-badge--primary {
  background: rgba(49, 130, 206, 0.1);
  color: var(--color-data-blue);
}

.status-badge--warning {
  background: var(--color-warning-light);
  color: var(--color-warning-dark);
}

.status-badge--danger {
  background: var(--color-error-light);
  color: var(--color-error-dark);
}

/* 通道配置面板 */
.channel-config-panel {
  padding: var(--spacing-2) 0;
}

.channel-col {
  margin-bottom: var(--spacing-4);
}

.channel-config-card {
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
  transition: var(--transition-all);
}

.channel-config-card:hover {
  box-shadow: var(--shadow-md);
}

.channel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-3);
}

.channel-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.channel-name {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
}

.channel-form {
  margin-top: var(--spacing-3);
}

/* 实时数据面板 */
.realtime-panel {
  padding: var(--spacing-2) 0;
}

/* 缓冲区状态 */
.buffer-status-section {
  margin-bottom: var(--spacing-6);
}

.buffer-status-display {
  background: var(--color-surface-secondary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  padding: var(--spacing-4);
}

.buffer-info {
  width: 100%;
}

.buffer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-3);
}

.buffer-label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
}

.buffer-percent {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  font-family: var(--font-family-mono);
}

.buffer-percent--success {
  color: var(--color-success-dark);
}

.buffer-percent--warning {
  color: var(--color-warning-dark);
}

.buffer-percent--danger {
  color: var(--color-error-dark);
}

.buffer-bar {
  height: 12px;
  background: var(--color-neutral-200);
  border-radius: var(--radius-full);
  overflow: hidden;
  margin-bottom: var(--spacing-2);
}

.buffer-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width 0.3s ease;
}

.buffer-fill--success {
  background: linear-gradient(90deg, var(--color-success-light), var(--color-success-dark));
}

.buffer-fill--warning {
  background: linear-gradient(90deg, var(--color-warning-light), var(--color-warning-dark));
}

.buffer-fill--danger {
  background: linear-gradient(90deg, var(--color-error-light), var(--color-error-dark));
}

.buffer-details {
  display: flex;
  justify-content: space-between;
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

/* 通道数据显示 */
.channel-data-section {
  margin-bottom: var(--spacing-6);
}

.data-channel-col {
  margin-bottom: var(--spacing-3);
}

.data-channel-card {
  padding: var(--spacing-4);
  background: var(--color-surface-secondary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  transition: var(--transition-all);
}

.data-channel-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.data-channel-active {
  border-color: var(--color-accent-500);
  box-shadow: var(--shadow-glow-accent);
}

.data-channel-disabled {
  opacity: 0.5;
}

.data-channel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-3);
}

.data-channel-name {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

.data-channel-value {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-3);
  background: var(--color-surface-primary);
  border-radius: var(--radius-sm);
  margin-bottom: var(--spacing-2);
}

.data-value {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary-500);
  font-family: var(--font-family-mono);
  letter-spacing: 0.05em;
}

.data-value-changing {
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

.data-channel-snr {
  display: flex;
  justify-content: space-between;
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  padding-top: var(--spacing-2);
  border-top: 1px solid var(--color-border-primary);
}

.snr-label {
  font-weight: var(--font-weight-medium);
}

.snr-value {
  font-family: var(--font-family-mono);
  color: var(--color-text-secondary);
}

/* 信噪比监控 */
.snr-section {
  margin-bottom: var(--spacing-4);
}

.snr-actions {
  margin-bottom: var(--spacing-3);
}

.snr-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  padding: var(--spacing-2) var(--spacing-3);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-sm);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: var(--transition-all);
}

.snr-btn:hover:not(:disabled) {
  border-color: var(--color-primary-400);
  color: var(--color-text-primary);
}

.snr-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.snr-card {
  padding: var(--spacing-3);
  background: var(--color-surface-secondary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
}

.snr-header {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  margin-bottom: var(--spacing-2);
  padding-bottom: var(--spacing-2);
  border-bottom: 1px solid var(--color-border-primary);
}

.snr-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.snr-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.snr-item-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.snr-item-value {
  font-size: var(--font-size-sm);
  font-family: var(--font-family-mono);
  color: var(--color-text-primary);
}

/* 高级配置面板 */
.advanced-panel {
  padding: var(--spacing-2) 0;
}

/* 模板管理面板 */
.templates-panel {
  padding: var(--spacing-2) 0;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-6);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-3);
}

.section-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.templates-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
}

.template-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-4);
  background: var(--color-surface-secondary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  transition: var(--transition-all);
}

.template-item:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.template-item.template-active {
  border-color: var(--color-primary-500);
  background: var(--color-primary-50);
}

.template-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.template-name {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.template-meta {
  display: flex;
  gap: var(--spacing-3);
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.template-actions {
  display: flex;
  gap: var(--spacing-2);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-8);
  color: var(--color-text-tertiary);
}

.empty-icon {
  font-size: 48px;
  margin-bottom: var(--spacing-3);
  opacity: 0.3;
}

/* SNR配置 */
.snr-config-section {
  background: var(--color-surface-secondary);
  border-radius: var(--radius-md);
  padding: var(--spacing-4);
  border: 1px solid var(--color-border-primary);
}

.snr-thresholds {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-4);
  margin-bottom: var(--spacing-4);
}

.threshold-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.threshold-item label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

.snr-alarms {
  margin-top: var(--spacing-4);
  padding: var(--spacing-3);
  background: var(--color-error-light);
  border: 1px solid var(--color-error-500);
  border-radius: var(--radius-md);
}

.alarms-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-error-dark);
  margin-bottom: var(--spacing-2);
}

.alarm-icon {
  font-size: 16px;
}

.alarms-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.alarm-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2);
  background: rgba(255, 255, 255, 0.5);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
}

.alarm-item.alarm-critical {
  border-left: 3px solid var(--color-error-500);
}

.alarm-item.alarm-warning {
  border-left: 3px solid var(--color-warning-500);
}

.alarm-channel {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.alarm-message {
  color: var(--color-text-secondary);
}

/* 缓冲区配置 */
.buffer-config-section {
  background: var(--color-surface-secondary);
  border-radius: var(--radius-md);
  padding: var(--spacing-4);
  border: 1px solid var(--color-border-primary);
}

.buffer-settings {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.buffer-setting {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.buffer-setting label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

.buffer-optimization {
  margin-top: var(--spacing-3);
  padding-top: var(--spacing-3);
  border-top: 1px solid var(--color-border-primary);
}

/* 模板保存对话框 */
.config-preview {
  background: var(--color-surface-secondary);
  border-radius: var(--radius-md);
  padding: var(--spacing-3);
}

.preview-item {
  display: flex;
  justify-content: space-between;
  padding: var(--spacing-2) 0;
  border-bottom: 1px solid var(--color-border-primary);
}

.preview-item:last-child {
  border-bottom: none;
}

.preview-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.preview-value {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  font-family: var(--font-family-mono);
}
</style>
