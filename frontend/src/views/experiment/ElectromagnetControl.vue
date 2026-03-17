<template>
  <div class="electromagnet-control-page">
    <!-- 页面标题 - 状态指示器位于顶部 -->
    <div class="page-header">
      <div class="header-left">
        <el-icon class="header-icon">
          <Opportunity />
        </el-icon>
        <div class="header-text">
          <h1 class="page-title">
            电磁铁控制
          </h1>
          <p class="page-description">
            磁场强度控制与扫描测量
          </p>
        </div>
      </div>
      <div class="header-right">
        <el-tag
          :type="isConnected ? 'success' : 'danger'"
          effect="dark"
          size="large"
          class="status-indicator"
        >
          <el-icon><Opportunity /></el-icon>
          {{ isConnected ? '已连接' : '未连接' }}
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
        <ElectromagnetControlPanel class="control-card" />
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
                <div class="status-value mono">
                  {{ formattedCurrent }}
                </div>
              </div>
              <div class="status-item">
                <div class="status-label">
                  磁场强度
                </div>
                <div class="status-value mono highlight">
                  {{ formattedField }}
                </div>
              </div>
              <div class="status-item">
                <div class="status-label">
                  工作模式
                </div>
                <el-tag
                  :type="workModeType"
                  size="small"
                >
                  {{ workModeText }}
                </el-tag>
              </div>
              <div class="status-item">
                <div class="status-label">
                  设备状态
                </div>
                <el-tag
                  :type="deviceStatusType"
                  size="small"
                >
                  {{ deviceStatusText }}
                </el-tag>
              </div>
            </div>
          </el-collapse-transition>
        </el-card>

        <!-- 扫描控制卡片 - 可折叠 -->
        <el-card class="scan-card">
          <template #header>
            <div
              class="card-header"
              @click="toggleScanPanel"
            >
              <div class="header-left-section">
                <el-icon class="header-icon">
                  <DataLine />
                </el-icon>
                <span class="header-title">扫描控制</span>
              </div>
              <el-icon
                class="collapse-icon"
                :class="{ 'is-collapsed': scanCollapsed }"
              >
                <ArrowDown />
              </el-icon>
            </div>
          </template>
          <el-collapse-transition>
            <div v-show="!scanCollapsed">
              <!-- 扫描进度 -->
              <div
                v-if="isScanning"
                class="scan-progress-section"
              >
                <div class="scan-progress-header">
                  <span class="scan-status-text">{{ scanStatusText }}</span>
                  <span class="scan-progress-text">{{ scanProgressPercent }}%</span>
                </div>
                <el-progress
                  :percentage="scanStatus.progress"
                  :status="scanProgressStatus"
                  :stroke-width="12"
                  class="scan-progress-bar"
                />
                <div class="scan-info-row">
                  <span>当前步: {{ scanStatus.currentStep }} / {{ scanStatus.totalSteps }}</span>
                  <span v-if="estimatedRemainingTime > 0">
                    剩余时间: {{ formatRemainingTime(estimatedRemainingTime) }}
                  </span>
                </div>
              </div>

              <!-- 扫描控制按钮 -->
              <div class="scan-controls">
                <el-button
                  type="primary"
                  :disabled="!canControl || isScanning"
                  :loading="loading.startScan"
                  @click="handleStartScan"
                >
                  <el-icon><VideoPlay /></el-icon>
                  开始扫描
                </el-button>
                <el-button
                  type="danger"
                  :disabled="!isScanning"
                  :loading="loading.stopScan"
                  @click="handleStopScan"
                >
                  <el-icon><VideoPause /></el-icon>
                  停止扫描
                </el-button>
                <el-button
                  v-if="isScanning && !isPaused"
                  type="warning"
                  @click="handlePauseScan"
                >
                  <el-icon><VideoPause /></el-icon>
                  暂停
                </el-button>
                <el-button
                  v-if="isScanning && isPaused"
                  type="success"
                  @click="handleResumeScan"
                >
                  <el-icon><CaretRight /></el-icon>
                  恢复
                </el-button>
              </div>

              <!-- 数据导出按钮 -->
              <div class="export-section">
                <el-button
                  type="info"
                  :disabled="scanData.current.length === 0"
                  @click="handleExportData"
                >
                  <el-icon><Download /></el-icon>
                  导出扫描数据 (CSV)
                </el-button>
                <el-button
                  type="default"
                  :disabled="scanData.current.length === 0"
                  @click="handleClearData"
                >
                  <el-icon><Delete /></el-icon>
                  清除数据
                </el-button>
              </div>

              <!-- 数据点统计 -->
              <div
                v-if="scanData.current.length > 0"
                class="data-stats"
              >
                <el-descriptions
                  :column="3"
                  size="small"
                  border
                >
                  <el-descriptions-item label="数据点数">
                    {{ scanData.current.length }}
                  </el-descriptions-item>
                  <el-descriptions-item label="电流范围">
                    {{ scanDataCurrentRange }}
                  </el-descriptions-item>
                  <el-descriptions-item label="磁场范围">
                    {{ scanDataFieldRange }}
                  </el-descriptions-item>
                </el-descriptions>
              </div>
            </div>
          </el-collapse-transition>
        </el-card>

        <!-- 安全警告卡片 - 可折叠 -->
        <el-card class="warning-card">
          <template #header>
            <div
              class="card-header"
              @click="toggleWarningPanel"
            >
              <div class="header-left-section">
                <el-icon class="header-icon warning-icon">
                  <Warning />
                </el-icon>
                <span class="header-title">安全警告</span>
              </div>
              <el-icon
                class="collapse-icon"
                :class="{ 'is-collapsed': warningCollapsed }"
              >
                <ArrowDown />
              </el-icon>
            </div>
          </template>
          <el-collapse-transition>
            <div v-show="!warningCollapsed">
              <el-alert
                v-for="(warning, index) in safetyWarnings"
                :key="index"
                :title="warning.title"
                :type="warning.type"
                :description="warning.description"
                :closable="false"
                show-icon
                class="warning-alert"
              />
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
 * @file ElectromagnetControl.vue
 * @path src/views/experiment/
 * @description 电磁铁控制页面，提供电流设置、扫描模式和校准功能
 * @author Agent
 * @date 2024-03-07
 * @dependencies stores/electromagnet, vue
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  Opportunity,
  Aim,
  Warning,
  InfoFilled,
  DataLine,
  VideoPlay,
  VideoPause,
  CaretRight,
  Download,
  Delete,
  ArrowDown
} from '@element-plus/icons-vue'
import { ElectromagnetControl as ElectromagnetControlPanel } from '@/components/experiment/electromagnet'
import { useElectromagnetStore } from '@/stores/electromagnet'
import { ElMessage } from 'element-plus'

// ============ Store 实例化 ============

const store = useElectromagnetStore()

// ============ 从 Store 解构状态 ============

const {
  isConnected,
  canControl,
  status,
  loading,
  scanStatus,
  scanData,
  isScanning,
  isPaused,
  estimatedRemainingTime,
  scanProgressPercent,
  formattedCurrent,
  formattedField
} = store

// ============ 本地 UI 状态 ============

/** 状态面板折叠状态 */
const statusCollapsed = ref(false)

/** 扫描面板折叠状态 */
const scanCollapsed = ref(false)

/** 警告面板折叠状态 */
const warningCollapsed = ref(false)

/** 提示面板折叠状态 */
const tipsCollapsed = ref(false)

// ============ 计算属性 ============

/** 工作模式文本 */
const workModeText = computed(() => {
  const modeMap = {
    manual: '手动控制',
    scan: '扫描模式',
    program: '程序控制'
  }
  if (isScanning.value) return '扫描模式'
  return '手动控制'
})

/** 工作模式标签类型 */
const workModeType = computed(() => {
  if (isScanning.value) return 'success'
  return 'primary'
})

/** 设备状态文本 */
const deviceStatusText = computed(() => {
  const statusMap = {
    ready: '就绪',
    running: '运行中',
    scanning: '扫描中',
    paused: '已暂停',
    error: '错误',
    disconnected: '未连接',
    emergency_stop: '急停',
    overcurrent: '过流保护'
  }
  return statusMap[status] || status
})

/** 设备状态标签类型 */
const deviceStatusType = computed(() => {
  const typeMap = {
    ready: 'success',
    running: 'primary',
    scanning: 'warning',
    paused: 'info',
    error: 'danger',
    disconnected: 'info',
    emergency_stop: 'danger',
    overcurrent: 'danger'
  }
  return typeMap[status] || 'info'
})

/** 扫描状态文本 */
const scanStatusText = computed(() => {
  if (isPaused.value) return '扫描已暂停'
  if (isScanning.value) return '扫描进行中'
  return '扫描未开始'
})

/** 扫描进度条状态 */
const scanProgressStatus = computed(() => {
  if (isPaused.value) return ''
  if (scanStatus.value.progress >= 100) return 'success'
  return ''
})

/** 扫描数据电流范围 */
const scanDataCurrentRange = computed(() => {
  if (scanData.value.current.length === 0) return '-'
  const min = Math.min(...scanData.value.current)
  const max = Math.max(...scanData.value.current)
  return `${min.toFixed(2)} ~ ${max.toFixed(2)} A`
})

/** 扫描数据磁场范围 */
const scanDataFieldRange = computed(() => {
  if (scanData.value.field.length === 0) return '-'
  const min = Math.min(...scanData.value.field)
  const max = Math.max(...scanData.value.field)
  return `${min.toFixed(2)} ~ ${max.toFixed(2)} mT`
})

/** 安全警告 */
const safetyWarnings = [
  {
    title: '高功率设备',
    type: 'error',
    description: '电磁铁为大功率设备，请注意散热'
  },
  {
    title: '磁场安全',
    type: 'warning',
    description: '强磁场可能影响心脏起搏器等医疗设备'
  }
]

/** 操作提示 */
const operationTips = [
  {
    title: '电流范围',
    type: 'info',
    description: `工作电流范围: ${store.currentLimits.min}A ~ ${store.currentLimits.max}A，请勿超出范围`
  },
  {
    title: '扫描模式',
    type: 'success',
    description: '扫描模式下请确保样品已正确放置'
  },
  {
    title: '数据导出',
    type: 'info',
    description: '扫描完成后可导出CSV格式数据用于后续分析'
  }
]

// ============ 方法 ============

/**
 * 切换状态面板折叠状态
 */
function toggleStatusPanel() {
  statusCollapsed.value = !statusCollapsed.value
}

/**
 * 切换扫描面板折叠状态
 */
function toggleScanPanel() {
  scanCollapsed.value = !scanCollapsed.value
}

/**
 * 切换警告面板折叠状态
 */
function toggleWarningPanel() {
  warningCollapsed.value = !warningCollapsed.value
}

/**
 * 切换提示面板折叠状态
 */
function toggleTipsPanel() {
  tipsCollapsed.value = !tipsCollapsed.value
}

/**
 * 格式化剩余时间
 * @param {number} seconds - 秒数
 * @returns {string} 格式化后的时间字符串
 */
function formatRemainingTime(seconds) {
  if (seconds < 60) {
    return `${Math.ceil(seconds)}秒`
  }
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = Math.ceil(seconds % 60)
  return `${minutes}分${remainingSeconds}秒`
}

/**
 * 开始扫描
 */
async function handleStartScan() {
  const success = await store.startScan()
  if (success) {
    ElMessage.success('扫描已开始')
  }
}

/**
 * 停止扫描
 */
async function handleStopScan() {
  const success = await store.stopScan()
  if (success) {
    ElMessage.success('扫描已停止')
  }
}

/**
 * 暂停扫描
 */
async function handlePauseScan() {
  const success = await store.pauseScan()
  if (success) {
    ElMessage.info('扫描已暂停')
  }
}

/**
 * 恢复扫描
 */
async function handleResumeScan() {
  const success = await store.resumeScan()
  if (success) {
    ElMessage.success('扫描已恢复')
  }
}

/**
 * 导出扫描数据
 */
function handleExportData() {
  const csvContent = store.exportScanData()
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
  link.href = URL.createObjectURL(blob)
  link.download = `electromagnet_scan_${timestamp}.csv`
  link.click()
  URL.revokeObjectURL(link.href)
  ElMessage.success('数据导出成功')
}

/**
 * 清除扫描数据
 */
function handleClearData() {
  store.clearScanData()
  ElMessage.success('扫描数据已清除')
}

// ============ 生命周期 ============

onMounted(() => {
  store.init()
})

onUnmounted(() => {
  store.cleanup()
})
</script>

<style scoped lang="scss">
.electromagnet-control-page {
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
  color: var(--color-warning);
  padding: var(--spacing-3);
  background-color: var(--color-warning-light);
  border-radius: var(--radius-lg);
  transition: var(--transition-all);
}

.header-icon:hover {
  background-color: var(--color-warning-lighter);
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
.scan-card,
.warning-card,
.tips-card {
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  transition: var(--transition-all);
  background: var(--color-surface-primary);
  border: none;
}

.control-card:hover,
.status-card:hover,
.scan-card:hover,
.warning-card:hover,
.tips-card:hover {
  box-shadow: var(--shadow-lg);
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

.header-icon.warning-icon {
  color: var(--color-warning);
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

.status-value.warning {
  color: var(--color-warning);
}

.mono {
  font-family: var(--font-family-mono);
}

/* ==================== 扫描控制卡片 ==================== */
.scan-progress-section {
  margin-bottom: var(--spacing-4);
  padding: var(--spacing-4);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
}

.scan-progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-2);
}

.scan-status-text {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.scan-progress-text {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary-500);
}

.scan-progress-bar {
  margin-bottom: var(--spacing-2);
}

.scan-info-row {
  display: flex;
  justify-content: space-between;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.scan-controls {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-4);
}

.export-section {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-3);
  padding-top: var(--spacing-3);
  border-top: 1px solid var(--color-border);
}

.data-stats {
  margin-top: var(--spacing-3);
}

/* ==================== 警告和提示 ==================== */
.warning-alert,
.tip-alert {
  margin-bottom: var(--spacing-3);
  border-radius: var(--radius-md);
  transition: var(--transition-all);
}

.warning-alert:hover,
.tip-alert:hover {
  transform: translateX(4px);
}

.warning-alert:last-child,
.tip-alert:last-child {
  margin-bottom: 0;
}

/* ==================== 响应式设计 ==================== */
@media (max-width: 1024px) {
  .electromagnet-control-page {
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
  .electromagnet-control-page {
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
