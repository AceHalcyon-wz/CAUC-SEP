<template>
  <div class="ammeter-control-page">
    <!-- 页面标题 - 状态指示器位于顶部 -->
    <div class="page-header">
      <div class="header-left">
        <el-icon class="header-icon">
          <Aim />
        </el-icon>
        <div class="header-text">
          <h1 class="page-title">
            微电流测量
          </h1>
          <p class="page-description">
            高精度多通道电流采集与分析
          </p>
        </div>
      </div>
      <div class="header-right">
        <!-- 采集控制按钮组 -->
        <el-button-group class="control-btn-group">
          <el-button
            type="primary"
            :disabled="!canStartCollection"
            :loading="store.loading?.startCollection"
            @click="handleStartCollection"
          >
            <el-icon><VideoPlay /></el-icon>
            开始采集
          </el-button>
          <el-button
            type="danger"
            :disabled="!canStopCollection"
            :loading="store.loading?.stopCollection"
            @click="handleStopCollection"
          >
            <el-icon><VideoPause /></el-icon>
            停止采集
          </el-button>
          <el-button
            type="warning"
            :disabled="!canClearBuffer"
            :loading="store.loading?.clearBuffer"
            @click="handleClearBuffer"
          >
            <el-icon><Delete /></el-icon>
            清空缓冲区
          </el-button>
        </el-button-group>
        <el-tag
          :type="collectionStatusType"
          effect="dark"
          size="large"
          class="status-indicator"
        >
          <el-icon><Aim /></el-icon>
          {{ collectionStatusText }}
        </el-tag>
      </div>
    </div>

    <!-- 主内容区域 - 左右分栏布局 -->
    <el-row
      :gutter="24"
      class="content-row"
    >
      <!-- 左侧：控制面板 -->
      <el-col
        :xs="24"
        :lg="12"
        class="control-col"
      >
        <AmmeterControl class="control-card" />
      </el-col>

      <!-- 右侧：实时数据展示区域（支持折叠） -->
      <el-col
        :xs="24"
        :lg="12"
        class="info-col"
      >
        <!-- 实时状态卡片 - 可折叠 -->
        <el-card class="status-card">
          <template #header>
            <div
              class="card-header"
              @click="toggleStatusPanel"
            >
              <div class="header-left-section">
                <el-icon class="header-icon">
                  <Aim />
                </el-icon>
                <span class="header-title">实时状态</span>
              </div>
              <el-icon
                class="collapse-icon"
                :class="{ 'is-collapsed': statusCollapsed }"
              >
                <ArrowDown />
              </el-icon>
            </div>
          </template>
          <el-collapse-transition>
            <div
              v-show="!statusCollapsed"
              class="status-grid"
            >
              <div class="status-item">
                <div class="status-label">
                  当前电流
                </div>
                <div class="status-value mono highlight">
                  {{ currentCurrent.toFixed(6) }} A
                </div>
              </div>
              <div class="status-item">
                <div class="status-label">
                  采样率
                </div>
                <div class="status-value mono">
                  {{ store.sampleRate }} S/s
                </div>
              </div>
              <div class="status-item">
                <div class="status-label">
                  采集状态
                </div>
                <el-tag
                  :type="collectionStatusType"
                  size="small"
                >
                  {{ collectionStatusText }}
                </el-tag>
              </div>
              <div class="status-item">
                <div class="status-label">
                  通道数
                </div>
                <div class="status-value mono">
                  {{ store.channelCount }}
                </div>
              </div>
            </div>
          </el-collapse-transition>
        </el-card>

        <!-- 缓冲区状态卡片 - 可折叠 -->
        <el-card class="buffer-card">
          <template #header>
            <div
              class="card-header"
              @click="toggleBufferPanel"
            >
              <div class="header-left-section">
                <el-icon class="header-icon">
                  <DataLine />
                </el-icon>
                <span class="header-title">缓冲区状态</span>
              </div>
              <el-icon
                class="collapse-icon"
                :class="{ 'is-collapsed': bufferCollapsed }"
              >
                <ArrowDown />
              </el-icon>
            </div>
          </template>
          <el-collapse-transition>
            <div v-show="!bufferCollapsed">
              <div class="buffer-status-section">
                <div class="buffer-progress">
                  <div class="buffer-progress-header">
                    <span class="buffer-label">缓冲区使用率</span>
                    <span class="buffer-value">{{ store.bufferUsagePercent }}%</span>
                  </div>
                  <el-progress
                    :percentage="store.bufferUsagePercent"
                    :status="store.bufferStatusType"
                    :stroke-width="12"
                    :show-text="false"
                  />
                  <div class="buffer-detail">
                    <span class="mono">{{ store.bufferStatus?.size || 0 }} / {{ store.bufferStatus?.max_size || 10000 }}</span>
                    <el-tag
                      :type="store.bufferStatusType"
                      size="small"
                    >
                      {{ store.bufferStatusText }}
                    </el-tag>
                  </div>
                </div>
                <div class="buffer-stats">
                  <div class="stat-item">
                    <span class="stat-label">采集时长</span>
                    <span class="stat-value mono">{{ formatDuration(store.collectionStats?.duration || 0) }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">样本数</span>
                    <span class="stat-value mono">{{ store.collectionStats?.samples_collected || 0 }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">数据速率</span>
                    <span class="stat-value mono">{{ (store.collectionStats?.data_rate || 0).toFixed(1) }} S/s</span>
                  </div>
                </div>
              </div>
            </div>
          </el-collapse-transition>
        </el-card>

        <!-- SNR数据卡片 - 可折叠 -->
        <el-card class="snr-card">
          <template #header>
            <div
              class="card-header"
              @click="toggleSnrPanel"
            >
              <div class="header-left-section">
                <el-icon class="header-icon">
                  <TrendCharts />
                </el-icon>
                <span class="header-title">信噪比数据</span>
                <el-tag
                  v-if="store.hasSNRAlarm"
                  type="danger"
                  size="small"
                  effect="dark"
                  class="snr-alarm-badge"
                >
                  告警
                </el-tag>
              </div>
              <el-icon
                class="collapse-icon"
                :class="{ 'is-collapsed': snrCollapsed }"
              >
                <ArrowDown />
              </el-icon>
            </div>
          </template>
          <el-collapse-transition>
            <div v-show="!snrCollapsed">
              <el-descriptions
                :column="1"
                border
                size="small"
              >
                <el-descriptions-item
                  v-for="channel in store.channelCount"
                  :key="channel"
                  :label="`通道 ${channel}`"
                >
                  <div class="snr-channel-item">
                    <span class="mono snr-value">
                      {{ getSNRValue(channel) }}
                    </span>
                    <el-tag
                      :type="getSNRType(channel)"
                      size="small"
                    >
                      {{ getSNRStatus(channel) }}
                    </el-tag>
                  </div>
                </el-descriptions-item>
              </el-descriptions>
              <div class="snr-threshold-info">
                <el-alert
                  title="SNR阈值"
                  type="info"
                  :description="`警告阈值: ${store.snrThresholds?.warning || 20} dB, 临界阈值: ${store.snrThresholds?.critical || 10} dB`"
                  :closable="false"
                  show-icon
                />
              </div>
            </div>
          </el-collapse-transition>
        </el-card>

        <!-- 测量精度卡片 - 可折叠 -->
        <el-card class="precision-card">
          <template #header>
            <div
              class="card-header"
              @click="togglePrecisionPanel"
            >
              <div class="header-left-section">
                <el-icon class="header-icon">
                  <SetUp />
                </el-icon>
                <span class="header-title">测量精度</span>
              </div>
              <el-icon
                class="collapse-icon"
                :class="{ 'is-collapsed': precisionCollapsed }"
              >
                <ArrowDown />
              </el-icon>
            </div>
          </template>
          <el-collapse-transition>
            <div v-show="!precisionCollapsed">
              <el-descriptions
                :column="1"
                border
                size="small"
              >
                <el-descriptions-item label="分辨率">
                  <span class="mono">{{ resolution }} pA</span>
                </el-descriptions-item>
                <el-descriptions-item label="准确度">
                  <el-tag
                    :type="accuracyType"
                    size="small"
                  >
                    {{ accuracy }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="量程">
                  {{ measurementRange }}
                </el-descriptions-item>
                <el-descriptions-item label="噪声抑制">
                  <el-tag
                    type="success"
                    size="small"
                  >
                    {{ noiseRejection }}
                  </el-tag>
                </el-descriptions-item>
              </el-descriptions>
            </div>
          </el-collapse-transition>
        </el-card>

        <!-- 操作提示卡片 - 可折叠 -->
        <el-card class="tips-card">
          <template #header>
            <div
              class="card-header"
              @click="toggleTipsPanel"
            >
              <div class="header-left-section">
                <el-icon class="header-icon">
                  <InfoFilled />
                </el-icon>
                <span class="header-title">操作提示</span>
              </div>
              <el-icon
                class="collapse-icon"
                :class="{ 'is-collapsed': tipsCollapsed }"
              >
                <ArrowDown />
              </el-icon>
            </div>
          </template>
          <el-collapse-transition>
            <div v-show="!tipsCollapsed">
              <el-alert
                v-for="(tip, index) in operationTips"
                :key="index"
                :title="tip.title"
                :type="tip.type"
                :description="tip.description"
                :closable="false"
                show-icon
                class="tip-alert"
              />
            </div>
          </el-collapse-transition>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
/**
 * @file AmmeterControl.vue
 * @path src/views/experiment/
 * @description 微电流测量页面，提供采集控制、通道配置和数据可视化功能
 * @author Agent
 * @date 2024-03-07
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  Aim,
  SetUp,
  InfoFilled,
  ArrowDown,
  VideoPlay,
  VideoPause,
  Delete,
  DataLine,
  TrendCharts
} from '@element-plus/icons-vue'
import { AmmeterControl } from '@/components/experiment/ammeter'
import { useAmmeterStore } from '@/stores/ammeter'

/** Ammeter Store实例 */
const store = useAmmeterStore()

/** 当前电流（从store的channelData计算） */
const currentCurrent = computed(() => {
  // 获取通道1的数据作为当前电流显示，如果没有数据则返回0
  const channel1Data = store.channelData?.[1]
  if (channel1Data !== undefined && channel1Data !== null) {
    return parseFloat(channel1Data) || 0
  }
  return 0
})

/** 分辨率 */
const resolution = ref(10)

/** 准确度 */
const accuracy = ref('0.1%')

/** 量程 */
const measurementRange = ref('100pA - 10mA')

/** 噪声抑制 */
const noiseRejection = ref('> 80dB')

/** 状态面板折叠状态 */
const statusCollapsed = ref(false)

/** 缓冲区面板折叠状态 */
const bufferCollapsed = ref(false)

/** SNR面板折叠状态 */
const snrCollapsed = ref(false)

/** 精度面板折叠状态 */
const precisionCollapsed = ref(false)

/** 提示面板折叠状态 */
const tipsCollapsed = ref(false)

/** 采集状态文本 */
const collectionStatusText = computed(() => {
  if (!store.isConnected) {
    return '未连接'
  }
  if (store.isCollecting) {
    return '采集中'
  }
  return '就绪'
})

/** 采集状态标签类型 */
const collectionStatusType = computed(() => {
  if (!store.isConnected) {
    return 'info'
  }
  if (store.isCollecting) {
    return 'success'
  }
  return 'primary'
})

/** 是否可以开始采集 */
const canStartCollection = computed(() => {
  return store.canControl && !store.isCollecting
})

/** 是否可以停止采集 */
const canStopCollection = computed(() => {
  return store.isCollecting
})

/** 是否可以清空缓冲区 */
const canClearBuffer = computed(() => {
  return store.isConnected && (store.bufferStatus?.size || 0) > 0
})

/** 准确度标签类型 */
const accuracyType = computed(() => {
  return 'success'
})

/** 操作提示 */
const operationTips = [
  {
    title: '量程选择',
    type: 'info',
    description: '请根据预期电流大小选择合适的量程'
  },
  {
    title: '屏蔽保护',
    type: 'warning',
    description: '微电流测量时请使用屏蔽线缆避免干扰'
  },
  {
    title: '预热时间',
    type: 'success',
    description: '设备预热30分钟后可达到最佳精度'
  }
]

/**
 * 处理开始采集
 */
async function handleStartCollection() {
  await store.startCollection()
}

/**
 * 处理停止采集
 */
async function handleStopCollection() {
  await store.stopCollection()
}

/**
 * 处理清空缓冲区
 */
async function handleClearBuffer() {
  await store.clearBuffer()
}

/**
 * 切换状态面板折叠状态
 */
function toggleStatusPanel() {
  statusCollapsed.value = !statusCollapsed.value
}

/**
 * 切换缓冲区面板折叠状态
 */
function toggleBufferPanel() {
  bufferCollapsed.value = !bufferCollapsed.value
}

/**
 * 切换SNR面板折叠状态
 */
function toggleSnrPanel() {
  snrCollapsed.value = !snrCollapsed.value
}

/**
 * 切换精度面板折叠状态
 */
function togglePrecisionPanel() {
  precisionCollapsed.value = !precisionCollapsed.value
}

/**
 * 切换提示面板折叠状态
 */
function toggleTipsPanel() {
  tipsCollapsed.value = !tipsCollapsed.value
}

/**
 * 获取通道SNR值
 *
 * @param {number} channel - 通道编号
 * @returns {string} SNR值字符串
 */
function getSNRValue(channel) {
  const snrInfo = store.snrData?.[channel]
  if (snrInfo && snrInfo.snr !== undefined) {
    return `${snrInfo.snr.toFixed(1)} dB`
  }
  return '--'
}

/**
 * 获取通道SNR状态类型
 *
 * @param {number} channel - 通道编号
 * @returns {string} 标签类型
 */
function getSNRType(channel) {
  const snrInfo = store.snrData?.[channel]
  if (!snrInfo || snrInfo.snr === undefined) {
    return 'info'
  }
  const snr = snrInfo.snr
  const thresholds = store.snrThresholds || { warning: 20, critical: 10 }
  if (snr < thresholds.critical) {
    return 'danger'
  }
  if (snr < thresholds.warning) {
    return 'warning'
  }
  return 'success'
}

/**
 * 获取通道SNR状态文本
 *
 * @param {number} channel - 通道编号
 * @returns {string} 状态文本
 */
function getSNRStatus(channel) {
  const snrInfo = store.snrData?.[channel]
  if (!snrInfo || snrInfo.snr === undefined) {
    return '无数据'
  }
  const snr = snrInfo.snr
  const thresholds = store.snrThresholds || { warning: 20, critical: 10 }
  if (snr < thresholds.critical) {
    return '临界'
  }
  if (snr < thresholds.warning) {
    return '警告'
  }
  return '正常'
}

/**
 * 格式化时长
 *
 * @param {number} ms - 毫秒数
 * @returns {string} 格式化后的时长字符串
 */
function formatDuration(ms) {
  if (!ms || ms <= 0) {
    return '00:00:00'
  }
  const seconds = Math.floor(ms / 1000)
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

/**
 * 页面挂载时初始化store
 */
onMounted(() => {
  store.init()
})

/**
 * 页面卸载时清理store资源
 */
onUnmounted(() => {
  store.cleanup()
})
</script>

<style scoped lang="scss">
.ammeter-control-page {
  max-width: 1600px;
  margin: 0 auto;
  padding: var(--spacing-6);
  min-height: 100%;
  background-color: var(--color-bg-secondary);
}

/* ==================== 页面头部 ==================== */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--spacing-6);
  padding: var(--spacing-6);
  padding-bottom: var(--spacing-4);
  background-color: var(--color-surface-primary);
  border-radius: var(--radius-lg);
  border-bottom: 2px solid var(--color-border-primary);
  box-shadow: var(--shadow-sm);
}

.header-left {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
}

.header-icon {
  font-size: 32px;
  color: var(--color-info);
  padding: var(--spacing-3);
  background-color: var(--color-info-light);
  border-radius: var(--radius-lg);
  transition: var(--transition-all);
}

.header-icon:hover {
  background-color: var(--color-primary-100);
  transform: scale(1.05);
}

.header-text {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  margin: 0;
  letter-spacing: -0.02em;
}

.page-description {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

/* 状态指示器 */
.status-indicator {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-4);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  border-radius: var(--radius-full);
  transition: var(--transition-all);
}

.status-indicator:hover {
  transform: scale(1.05);
  box-shadow: var(--shadow-md);
}

/* ==================== 内容区域 ==================== */
.content-row {
  margin: 0;
}

.control-col,
.info-col {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-5);
}

/* ==================== 卡片样式 ==================== */
.control-card,
.status-card,
.buffer-card,
.snr-card,
.precision-card,
.tips-card {
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  transition: var(--transition-all);
  background: var(--color-surface-primary);
  border: none;
}

.control-card:hover,
.status-card:hover,
.buffer-card:hover,
.snr-card:hover,
.precision-card:hover,
.tips-card:hover {
  box-shadow: var(--shadow-lg);
}

/* 控制按钮组 */
.control-btn-group {
  margin-right: var(--spacing-4);
}

/* ==================== 缓冲区状态 ==================== */
.buffer-status-section {
  padding: var(--spacing-4);
}

.buffer-progress {
  margin-bottom: var(--spacing-5);
}

.buffer-progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-2);
}

.buffer-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.buffer-value {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  font-family: var(--font-family-mono);
}

.buffer-detail {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: var(--spacing-2);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.buffer-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-3);
  padding-top: var(--spacing-4);
  border-top: 1px solid var(--color-border-primary);
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
  text-align: center;
}

.stat-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.stat-value {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

/* ==================== SNR状态 ==================== */
.snr-alarm-badge {
  margin-left: var(--spacing-2);
}

.snr-channel-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.snr-value {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.snr-threshold-info {
  margin-top: var(--spacing-4);
}

/* 卡片头部 */
:deep(.el-card__header) {
  background-color: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border-primary);
  padding: var(--spacing-4) var(--spacing-6);
  cursor: pointer;
  user-select: none;
  transition: var(--transition-all);
}

:deep(.el-card__header:hover) {
  background-color: var(--color-bg-tertiary);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-2);
}

.header-left-section {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.header-icon {
  font-size: var(--font-size-lg);
  color: var(--color-primary-500);
}

.header-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

/* 折叠图标 */
.collapse-icon {
  font-size: var(--font-size-lg);
  color: var(--color-text-tertiary);
  transition: var(--transition-transform);
}

.collapse-icon.is-collapsed {
  transform: rotate(-90deg);
}

/* ==================== 状态网格 ==================== */
.status-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-4);
}

.status-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
  padding: var(--spacing-4);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  border-left: 4px solid var(--color-primary-500);
  transition: var(--transition-all);
}

.status-item:hover {
  background-color: var(--color-bg-tertiary);
  transform: translateX(4px);
}

.status-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: var(--font-weight-medium);
}

.status-value {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
}

.status-value.highlight {
  color: var(--color-primary-500);
}

.mono {
  font-family: var(--font-family-mono);
}

/* ==================== 提示 ==================== */
.tip-alert {
  margin-bottom: var(--spacing-3);
  border-radius: var(--radius-md);
  transition: var(--transition-all);
}

.tip-alert:hover {
  transform: translateX(4px);
}

.tip-alert:last-child {
  margin-bottom: 0;
}

/* ==================== 响应式设计 ==================== */
@media (max-width: 1024px) {
  .ammeter-control-page {
    padding: var(--spacing-4);
  }

  .page-header {
    flex-direction: column;
    gap: var(--spacing-3);
    padding: var(--spacing-5);
  }

  .header-right {
    width: 100%;
    justify-content: flex-start;
  }

  .control-col,
  .info-col {
    margin-bottom: var(--spacing-5);
  }
}

@media (max-width: 768px) {
  .ammeter-control-page {
    padding: var(--spacing-3);
  }

  .page-header {
    padding: var(--spacing-4);
  }

  .page-title {
    font-size: var(--font-size-xl);
  }

  .control-col,
  .info-col {
    gap: var(--spacing-4);
  }

  .status-grid {
    grid-template-columns: 1fr;
  }
  
  .status-value {
    font-size: var(--font-size-lg);
  }
  
  .status-indicator {
    padding: var(--spacing-1) var(--spacing-3);
    font-size: var(--font-size-xs);
  }
}
</style>
