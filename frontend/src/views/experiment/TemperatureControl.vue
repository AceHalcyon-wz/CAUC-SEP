<template>
  <div class="temperature-control-page">
    <!-- 页面标题 - 状态指示器位于顶部 -->
    <div class="page-header">
      <div class="header-left">
        <el-icon class="header-icon">
          <Thermometer />
        </el-icon>
        <div class="header-text">
          <h1 class="page-title">
            温度控制
          </h1>
          <p class="page-description">
            精密恒温控制与程序升温
          </p>
        </div>
      </div>
      <div class="header-right">
        <!-- 连接状态 -->
        <div
          class="connection-badge"
          :class="connectionBadgeClass"
        >
          <span class="badge-dot" />
          {{ connectionStatus.text }}
        </div>
        <!-- 温度状态 -->
        <el-tag
          :type="tempStore.tempStatusType"
          effect="dark"
          size="large"
          class="status-indicator"
        >
          <el-icon><Thermometer /></el-icon>
          {{ tempStore.tempStatusText }}
        </el-tag>
      </div>
    </div>

    <!-- 快速状态栏 -->
    <div class="quick-status-bar">
      <div class="status-item">
        <span class="status-label">当前温度</span>
        <span class="status-value mono">{{ formatTemp(tempStore.currentTemp) }}</span>
      </div>
      <div class="status-item">
        <span class="status-label">目标温度</span>
        <span class="status-value mono">{{ formatTemp(tempStore.targetTemp) }}</span>
      </div>
      <div class="status-item">
        <span class="status-label">输出功率</span>
        <span class="status-value mono">{{ tempStore.outputPower.toFixed(1) }}%</span>
      </div>
      <div class="status-item">
        <span class="status-label">升温速率</span>
        <span class="status-value mono">{{ tempStore.heatingRate.toFixed(2) }} K/s</span>
      </div>
      <div class="status-item">
        <span class="status-label">PID参数</span>
        <span class="status-value mono">Kp={{ tempStore.pidParams.kp }} Ki={{ tempStore.pidParams.ki }} Kd={{ tempStore.pidParams.kd }}</span>
      </div>
      <div
        v-if="tempStore.isProgramRunning"
        class="status-item"
      >
        <span class="status-label">程序进度</span>
        <span class="status-value mono">{{ tempStore.programProgress }}%</span>
      </div>
    </div>

    <!-- 程序控制按钮栏 -->
    <div
      v-if="tempStore.isProgramRunning || tempStore.programStatus === 'paused'"
      class="program-control-bar"
    >
      <el-progress
        :percentage="tempStore.programProgress"
        :status="tempStore.programStatus === 'paused' ? 'warning' : ''"
        class="program-progress"
      />
      <div class="program-buttons">
        <el-button
          v-if="tempStore.programStatus === 'running'"
          type="warning"
          size="small"
          :loading="tempStore.loading.pauseProgram"
          @click="handlePauseProgram"
        >
          <el-icon><VideoPause /></el-icon>
          暂停程序
        </el-button>
        <el-button
          v-if="tempStore.programStatus === 'paused'"
          type="success"
          size="small"
          :loading="tempStore.loading.resumeProgram"
          @click="handleResumeProgram"
        >
          <el-icon><VideoPlay /></el-icon>
          恢复程序
        </el-button>
        <el-button
          type="danger"
          size="small"
          :loading="tempStore.loading.stopProgram"
          @click="handleStopProgram"
        >
          <el-icon><Close /></el-icon>
          停止程序
        </el-button>
      </div>
    </div>

    <!-- 主内容区域 - 标签页布局 -->
    <div class="content-wrapper">
      <el-tabs
        v-model="activeTab"
        type="border-card"
        class="main-tabs"
      >
        <!-- 温度控制面板 -->
        <el-tab-pane
          label="温度控制"
          name="control"
        >
          <TemperatureControlPanel class="main-card" />
        </el-tab-pane>

        <!-- 温度曲线监控 -->
        <el-tab-pane
          label="实时曲线"
          name="curve"
        >
          <TemperatureCurve class="main-card" />
        </el-tab-pane>

        <!-- 程序升温配置 -->
        <el-tab-pane
          label="程序升温"
          name="program"
        >
          <TemperatureProgram class="main-card" />
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 历史数据导出浮动按钮 -->
    <div class="export-actions">
      <el-dropdown trigger="click">
        <el-button
          type="primary"
          :disabled="tempStore.tempHistory.length === 0"
          class="export-btn"
        >
          <el-icon><Download /></el-icon>
          导出历史数据
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="handleExportHistory('csv')">
              <el-icon><Document /></el-icon>
              导出为 CSV
            </el-dropdown-item>
            <el-dropdown-item @click="handleExportHistory('json')">
              <el-icon><DocumentChecked /></el-icon>
              导出为 JSON
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <el-button
        v-if="!tempStore.isConnected"
        type="success"
        :loading="tempStore.isConnecting"
        class="connect-btn"
        @click="handleConnect"
      >
        <el-icon><Link /></el-icon>
        连接温控器
      </el-button>
      <el-button
        v-else
        type="danger"
        class="disconnect-btn"
        @click="handleDisconnect"
      >
        <el-icon><Disconnect /></el-icon>
        断开连接
      </el-button>
    </div>
  </div>
</template>

<script setup>
/**
 * @file TemperatureControl.vue
 * @path src/views/experiment/
 * @description 温度控制页面，提供目标温度设置、PID参数配置、程序控温和实时曲线监控功能
 * @author Agent
 * @date 2024-03-07
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useTemperatureStore } from '@/stores/temperature'
import {
  TemperatureControl as TemperatureControlPanel,
  TemperatureCurve,
  TemperatureProgram
} from '@/components/experiment/temperature'

// ============ Store ============
const tempStore = useTemperatureStore()

// ============ 响应式状态 ============
/** 当前激活的标签页 */
const activeTab = ref('control')

// ============ 计算属性 ============

/** 连接状态 */
const connectionStatus = computed(() => {
  if (tempStore.isConnected) {
    return { type: 'success', text: '已连接' }
  } else if (tempStore.isConnecting) {
    return { type: 'warning', text: '连接中...' }
  } else {
    return { type: 'danger', text: '未连接' }
  }
})

/** 连接状态徽章样式 */
const connectionBadgeClass = computed(() => {
  if (tempStore.isConnected) return 'connection-badge--connected'
  if (tempStore.isConnecting) return 'connection-badge--connecting'
  return 'connection-badge--disconnected'
})

// ============ 方法 ============

/**
 * 格式化温度显示
 * @param {number} temp - 温度值
 * @returns {string} 格式化后的温度值
 */
function formatTemp(temp) {
  return `${temp.toFixed(2)}K (${tempStore.kelvinToCelsius(temp).toFixed(1)}°C)`
}

/**
 * 连接温控器
 */
async function handleConnect() {
  const success = await tempStore.connect()
  if (success) {
    ElMessage.success('温控器连接成功')
  }
}

/**
 * 断开温控器
 */
async function handleDisconnect() {
  try {
    await ElMessageBox.confirm('确定要断开温控器连接吗？', '确认', {
      type: 'warning'
    })
    await tempStore.disconnect()
    ElMessage.success('温控器已断开')
  } catch {
    // 用户取消
  }
}

/**
 * 暂停程序
 */
async function handlePauseProgram() {
  const success = await tempStore.pauseProgram()
  if (success) {
    ElMessage.success('程序已暂停')
  }
}

/**
 * 恢复程序
 */
async function handleResumeProgram() {
  const success = await tempStore.resumeProgram()
  if (success) {
    ElMessage.success('程序已恢复')
  }
}

/**
 * 停止程序
 */
async function handleStopProgram() {
  try {
    await ElMessageBox.confirm('确定要停止当前运行的程序吗？', '确认', {
      type: 'warning'
    })
    const success = await tempStore.stopProgram()
    if (success) {
      ElMessage.success('程序已停止')
    }
  } catch {
    // 用户取消
  }
}

/**
 * 导出温度历史记录
 * @param {string} format - 导出格式 ('csv' 或 'json')
 */
async function handleExportHistory(format) {
  try {
    const blob = await tempStore.exportTemperatureHistory(format)
    if (blob) {
      // 创建下载链接
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `temperature_history_${Date.now()}.${format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      ElMessage.success(`历史记录已导出为 ${format.toUpperCase()} 格式`)
    }
  } catch (error) {
    ElMessage.error('导出失败: ' + error.message)
  }
}

// ============ 生命周期 ============

onMounted(() => {
  // 初始化store
  tempStore.init()
})

onUnmounted(() => {
  // 清理store资源
  tempStore.cleanup()
})
</script>

<style scoped lang="scss">
.temperature-control-page {
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
  margin-bottom: var(--spacing-4);
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
  color: var(--color-success);
  padding: var(--spacing-3);
  background-color: var(--color-success-light);
  border-radius: var(--radius-lg);
  transition: var(--transition-all);
}

.header-icon:hover {
  background-color: var(--color-success-lighter);
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

/* 连接状态徽章 */
.connection-badge {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-1) var(--spacing-3);
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  transition: var(--transition-all);
}

.badge-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  animation: pulse 2s ease-in-out infinite;
}

.connection-badge--connected {
  background: var(--color-success-light);
  color: var(--color-success-dark);
}

.connection-badge--connected .badge-dot {
  background: var(--color-status-online);
  box-shadow: 0 0 8px var(--color-status-online);
}

.connection-badge--connecting {
  background: var(--color-warning-light);
  color: var(--color-warning-dark);
}

.connection-badge--connecting .badge-dot {
  background: var(--color-status-warning);
  box-shadow: 0 0 8px var(--color-status-warning);
  animation: pulse-fast 1s ease-in-out infinite;
}

.connection-badge--disconnected {
  background: var(--color-error-light);
  color: var(--color-error-dark);
}

.connection-badge--disconnected .badge-dot {
  background: var(--color-status-error);
  animation: none;
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

/* ==================== 快速状态栏 ==================== */
.quick-status-bar {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--spacing-4);
  margin-bottom: var(--spacing-4);
  padding: var(--spacing-4);
  background-color: var(--color-surface-primary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.status-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
  padding: var(--spacing-3);
  background: var(--color-surface-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
}

.status-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-weight: var(--font-weight-medium);
}

.status-value {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
}

/* ==================== 程序控制栏 ==================== */
.program-control-bar {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
  margin-bottom: var(--spacing-4);
  padding: var(--spacing-4);
  background: linear-gradient(135deg, var(--color-primary-50), var(--color-surface-primary));
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-primary-200);
  box-shadow: var(--shadow-sm);
}

.program-progress {
  flex: 1;
}

.program-buttons {
  display: flex;
  gap: var(--spacing-2);
  flex-shrink: 0;
}

/* ==================== 内容区域 ==================== */
.content-wrapper {
  width: 100%;
}

.main-tabs {
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  overflow: hidden;
  border: none;
}

.main-tabs :deep(.el-tabs__header) {
  background: var(--color-surface-secondary);
  border-bottom: 2px solid var(--color-border-primary);
}

.main-tabs :deep(.el-tabs__item) {
  font-weight: var(--font-weight-medium);
  font-size: var(--font-size-base);
  padding: 0 var(--spacing-6);
  height: 48px;
  line-height: 48px;
  color: var(--color-text-secondary);
  transition: var(--transition-all);
}

.main-tabs :deep(.el-tabs__item:hover) {
  color: var(--color-primary-500);
  background-color: var(--color-bg-tertiary);
}

.main-tabs :deep(.el-tabs__item.is-active) {
  color: var(--color-primary-500);
  font-weight: var(--font-weight-semibold);
  background: var(--color-surface-primary);
  border-bottom: 2px solid var(--color-primary-500);
}

.main-tabs :deep(.el-tabs__content) {
  padding: 0;
}

.main-card {
  border-radius: 0;
  box-shadow: none;
  border: none;
  background: var(--color-surface-primary);
}

/* ==================== 导出操作栏 ==================== */
.export-actions {
  position: fixed;
  bottom: var(--spacing-6);
  right: var(--spacing-6);
  display: flex;
  gap: var(--spacing-3);
  z-index: 100;
}

.export-btn,
.connect-btn,
.disconnect-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-3) var(--spacing-5);
  border-radius: var(--radius-md);
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-base);
  box-shadow: var(--shadow-lg);
  transition: var(--transition-all);
}

.export-btn:hover,
.connect-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-glow-primary);
}

.disconnect-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-glow-error);
}

/* ==================== 动画 ==================== */
@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(1.2);
  }
}

@keyframes pulse-fast {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

/* ==================== 响应式设计 ==================== */
@media (max-width: 1024px) {
  .temperature-control-page {
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

  .quick-status-bar {
    grid-template-columns: repeat(3, 1fr);
  }

  .program-control-bar {
    flex-direction: column;
    gap: var(--spacing-3);
  }

  .program-buttons {
    width: 100%;
    justify-content: center;
  }
}

@media (max-width: 768px) {
  .temperature-control-page {
    padding: var(--spacing-3);
  }

  .page-header {
    padding: var(--spacing-4);
  }

  .page-title {
    font-size: var(--font-size-xl);
  }

  .main-tabs :deep(.el-tabs__item) {
    padding: 0 var(--spacing-4);
    font-size: var(--font-size-sm);
  }

  .status-indicator {
    padding: var(--spacing-1) var(--spacing-3);
    font-size: var(--font-size-xs);
  }

  .quick-status-bar {
    grid-template-columns: repeat(2, 1fr);
  }

  .export-actions {
    position: relative;
    bottom: auto;
    right: auto;
    margin-top: var(--spacing-4);
    justify-content: center;
  }
}
</style>
