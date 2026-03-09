<template>
  <div class="analysis-realtime-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <el-icon class="header-icon"><TrendCharts /></el-icon>
        <div class="header-content">
          <h1 class="page-title">实时数据分析</h1>
          <p class="page-subtitle">实时监控设备数据变化，支持多通道同步显示</p>
        </div>
      </div>
      <div class="header-right">
        <div class="refresh-status">
          <div class="status-indicator" :class="{ 'is-active': autoRefresh }">
            <span class="status-dot"></span>
            <span class="status-text">{{ autoRefresh ? '自动刷新中' : '手动模式' }}</span>
          </div>
          <div class="refresh-info" v-if="autoRefresh">
            <span class="interval-text">间隔: {{ refreshInterval }}ms</span>
          </div>
        </div>
        <el-switch
          v-model="autoRefresh"
          active-text="自动"
          inactive-text="手动"
          @change="handleAutoRefreshChange"
        />
        <el-button type="primary" :icon="Refresh" @click="refreshData">
          刷新数据
        </el-button>
      </div>
    </div>

    <!-- 数据统计概览 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="stat-icon stat-icon--primary">
            <el-icon><DataLine /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">数据点数</div>
            <div class="stat-value mono">{{ dataStats.pointCount }}</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="stat-icon stat-icon--success">
            <el-icon><Top /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">最大值</div>
            <div class="stat-value mono">{{ dataStats.maxValue.toFixed(3) }}</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="stat-icon stat-icon--warning">
            <el-icon><Bottom /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">最小值</div>
            <div class="stat-value mono">{{ dataStats.minValue.toFixed(3) }}</div>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="stat-icon stat-icon--info">
            <el-icon><TrendCharts /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-label">平均值</div>
            <div class="stat-value mono">{{ dataStats.avgValue.toFixed(3) }}</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 实时分析组件 -->
    <RealtimeAnalysis />

    <!-- 快捷操作面板 -->
    <el-card class="quick-actions-card">
      <template #header>
        <div class="card-header">
          <el-icon><Operation /></el-icon>
          <span>快捷操作</span>
        </div>
      </template>
      <el-row :gutter="16">
        <el-col :xs="24" :sm="12" :md="6">
          <el-button 
            type="primary" 
            :icon="Download" 
            class="action-btn"
            @click="exportRealtimeData"
          >
            导出实时数据
          </el-button>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <el-button 
            type="success" 
            :icon="VideoPause" 
            class="action-btn"
            :disabled="!autoRefresh"
            @click="pauseRefresh"
          >
            暂停刷新
          </el-button>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <el-button 
            type="warning" 
            :icon="Delete" 
            class="action-btn"
            @click="clearRealtimeData"
          >
            清除数据
          </el-button>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <el-button 
            type="info" 
            :icon="Setting" 
            class="action-btn"
            @click="showSettingsDialog = true"
          >
            显示设置
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 显示设置对话框 -->
    <el-dialog
      v-model="showSettingsDialog"
      title="显示设置"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form label-width="120px">
        <el-form-item label="刷新间隔">
          <el-input-number 
            v-model="refreshInterval" 
            :min="100" 
            :max="5000" 
            :step="100"
            style="width: 100%"
          />
          <span class="form-hint">单位：毫秒</span>
        </el-form-item>
        <el-form-item label="最大数据点">
          <el-input-number 
            v-model="maxDataPoints" 
            :min="50" 
            :max="500" 
            :step="10"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="显示网格">
          <el-switch v-model="showGrid" />
        </el-form-item>
        <el-form-item label="平滑曲线">
          <el-switch v-model="smoothLine" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSettingsDialog = false">取消</el-button>
        <el-button type="primary" @click="applySettings">应用设置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * @file Realtime.vue
 * @path src/views/analysis/
 * @description 实时数据分析页面，集成实时分析组件提供多设备数据同步、通道过滤、统计计算和导出功能
 * @author Agent
 * @date 2024-03-07
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useMotorStore } from '@/stores/motor'
import { useAnalysisStore } from '@/stores/analysis'
import RealtimeAnalysis from '@/components/RealtimeAnalysis.vue'
import { ElMessage } from 'element-plus'
import {
  TrendCharts,
  Refresh,
  Download,
  VideoPause,
  Delete,
  Setting,
  Operation,
  DataLine,
  Top,
  Bottom
} from '@element-plus/icons-vue'

const motorStore = useMotorStore()
const analysisStore = useAnalysisStore()

/** 自动刷新开关 */
const autoRefresh = ref(true)

/** 显示设置对话框 */
const showSettingsDialog = ref(false)

/** 刷新间隔（毫秒） */
const refreshInterval = ref(500)

/** 最大数据点数 */
const maxDataPoints = ref(100)

/** 显示网格 */
const showGrid = ref(true)

/** 平滑曲线 */
const smoothLine = ref(true)

/** 数据统计 */
const dataStats = computed(() => {
  const positions = motorStore.positionHistory || []
  if (positions.length === 0) {
    return {
      pointCount: 0,
      maxValue: 0,
      minValue: 0,
      avgValue: 0
    }
  }
  
  const values = positions.map(p => p.value)
  return {
    pointCount: values.length,
    maxValue: Math.max(...values),
    minValue: Math.min(...values),
    avgValue: values.reduce((a, b) => a + b, 0) / values.length
  }
})

/** 定时刷新器 */
let refreshTimer = null

/**
 * 刷新数据
 */
function refreshData() {
  motorStore.fetchCurrentPosition()
  ElMessage.success('数据已刷新')
}

/**
 * 处理自动刷新状态变化
 * 
 * @param {boolean} enabled - 是否启用自动刷新
 */
function handleAutoRefreshChange(enabled) {
  if (enabled) {
    startAutoRefresh()
    ElMessage.success('已启用自动刷新')
  } else {
    stopAutoRefresh()
    ElMessage.info('已暂停自动刷新')
  }
}

/**
 * 启动自动刷新
 */
function startAutoRefresh() {
  stopAutoRefresh()
  refreshTimer = setInterval(() => {
    motorStore.fetchCurrentPosition()
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
 * 暂停刷新
 */
function pauseRefresh() {
  autoRefresh.value = false
  stopAutoRefresh()
  ElMessage.info('已暂停刷新')
}

/**
 * 导出实时数据
 */
function exportRealtimeData() {
  const positions = motorStore.positionHistory || []
  if (positions.length === 0) {
    ElMessage.warning('没有数据可导出')
    return
  }
  
  // 生成CSV内容
  const csvContent = [
    '时间,位置(mm)',
    ...positions.map(p => `${p.timestamp},${p.value.toFixed(3)}`)
  ].join('\n')
  
  // 创建下载链接
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', `realtime_data_${Date.now()}.csv`)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  
  ElMessage.success('数据已导出')
}

/**
 * 清除实时数据
 */
function clearRealtimeData() {
  motorStore.clearPositionHistory()
  analysisStore.clearData()
  ElMessage.success('数据已清除')
}

/**
 * 应用设置
 */
function applySettings() {
  showSettingsDialog.value = false
  
  // 如果自动刷新已启用，重启定时器
  if (autoRefresh.value) {
    startAutoRefresh()
  }
  
  ElMessage.success('设置已应用')
}

// 组件挂载时启动自动刷新
onMounted(() => {
  if (autoRefresh.value) {
    startAutoRefresh()
  }
})

// 组件卸载时停止自动刷新
onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<style scoped>
.analysis-realtime-page {
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
  gap: var(--spacing-4);
  position: relative;
  z-index: 1;
}

/* ==================== 刷新状态指示器 ==================== */
.refresh-status {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--spacing-1);
  padding: var(--spacing-3);
  background-color: rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-md);
  backdrop-filter: blur(10px);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-3);
  background: rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-md);
  transition: var(--transition-all);
}

.status-indicator.is-active {
  background: rgba(103, 194, 58, 0.25);
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: var(--radius-full);
  background: rgba(255, 255, 255, 0.5);
  transition: var(--transition-all);
  position: relative;
}

.status-indicator.is-active .status-dot {
  background: #67c23a;
  box-shadow: 0 0 0 3px rgba(103, 194, 58, 0.3);
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 0 3px rgba(103, 194, 58, 0.3);
  }
  50% {
    transform: scale(1.1);
    box-shadow: 0 0 0 6px rgba(103, 194, 58, 0.15);
  }
}

.status-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-inverse);
  font-weight: var(--font-weight-medium);
}

.refresh-info {
  font-size: var(--font-size-xs);
  color: rgba(255, 255, 255, 0.7);
}

.interval-text {
  font-family: var(--font-family-mono);
  font-weight: var(--font-weight-medium);
}

/* ==================== 统计卡片行 ==================== */
.stats-row {
  margin-bottom: var(--spacing-6);
}

.stat-card {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
  padding: var(--spacing-5);
  background-color: var(--color-surface-primary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  box-shadow: var(--shadow-card);
  transition: var(--transition-all);
  position: relative;
  overflow: hidden;
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 100%;
  transition: var(--transition-all);
}

.stat-card:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-3px);
}

.stat-card:hover::before {
  width: 6px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-lg);
  font-size: var(--font-size-2xl);
  flex-shrink: 0;
  transition: var(--transition-all);
}

.stat-card:hover .stat-icon {
  transform: scale(1.05);
}

.stat-icon--primary {
  background: linear-gradient(135deg, var(--color-primary-50), var(--color-primary-100));
  color: var(--color-primary-600);
}

.stat-card:has(.stat-icon--primary)::before {
  background: linear-gradient(180deg, var(--color-primary-400), var(--color-primary-500));
}

.stat-icon--success {
  background: linear-gradient(135deg, var(--color-success-light), #d9f7be);
  color: var(--color-success-dark);
}

.stat-card:has(.stat-icon--success)::before {
  background: linear-gradient(180deg, var(--color-success), var(--color-success-dark));
}

.stat-icon--warning {
  background: linear-gradient(135deg, var(--color-warning-light), #fff1b8);
  color: var(--color-warning-dark);
}

.stat-card:has(.stat-icon--warning)::before {
  background: linear-gradient(180deg, var(--color-warning), var(--color-warning-dark));
}

.stat-icon--info {
  background: linear-gradient(135deg, var(--color-secondary-50), var(--color-secondary-100));
  color: var(--color-secondary-600);
}

.stat-card:has(.stat-icon--info)::before {
  background: linear-gradient(180deg, var(--color-secondary-400), var(--color-secondary-500));
}

.stat-content {
  flex: 1;
  min-width: 0;
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
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: var(--font-family-mono);
}

.mono {
  font-family: var(--font-family-mono);
}

/* ==================== 快捷操作卡片 ==================== */
.quick-actions-card {
  margin-top: var(--spacing-6);
  background-color: var(--color-surface-primary);
  border-color: var(--color-border-primary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  transition: var(--transition-all);
}

.quick-actions-card:hover {
  box-shadow: var(--shadow-lg);
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

.action-btn {
  width: 100%;
  margin-bottom: var(--spacing-3);
  height: 44px;
  font-weight: var(--font-weight-medium);
  transition: var(--transition-all);
  border-radius: var(--radius-md);
}

.action-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.action-btn:active:not(:disabled) {
  transform: translateY(0);
}

/* ==================== 表单提示 ==================== */
.form-hint {
  display: block;
  margin-top: var(--spacing-1);
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
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

:deep(.el-switch) {
  --el-switch-on-color: var(--color-primary-500);
}

:deep(.el-input-number) {
  width: 100%;
}

/* ==================== 响应式优化 ==================== */
@media (max-width: 768px) {
  .analysis-realtime-page {
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
    justify-content: space-between;
    gap: var(--spacing-3);
  }

  .refresh-status {
    width: 100%;
    align-items: flex-start;
  }

  .stat-card {
    padding: var(--spacing-4);
  }

  .stat-icon {
    width: 44px;
    height: 44px;
    font-size: var(--font-size-xl);
  }

  .stat-value {
    font-size: var(--font-size-lg);
  }

  .action-btn {
    margin-bottom: var(--spacing-2);
    height: 40px;
  }
}

@media (min-width: 1920px) {
  .analysis-realtime-page {
    padding: var(--spacing-8);
  }

  .stat-card {
    padding: var(--spacing-6);
  }

  .stat-icon {
    width: 64px;
    height: 64px;
    font-size: var(--font-size-3xl);
  }

  .stat-value {
    font-size: var(--font-size-3xl);
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
    background: var(--color-primary-600);
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }

  .header-right {
    display: none;
  }

  .quick-actions-card {
    display: none;
  }
}
</style>
