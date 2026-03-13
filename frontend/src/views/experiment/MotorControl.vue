<template>
  <div class="motor-control-page">
    <!-- 页面头部 - 状态指示器位于顶部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <el-icon class="header-icon">
            <Connection />
          </el-icon>
          <div class="header-text">
            <h1 class="page-title">
              电机控制
            </h1>
            <p class="page-subtitle">
              精密电机运动控制系统
            </p>
          </div>
        </div>
        <div class="header-right">
          <!-- 状态指示器位于顶部 -->
          <el-tag 
            v-if="motorStore.isConnected" 
            type="success" 
            effect="dark"
            size="large"
            class="status-indicator"
          >
            <el-icon><CircleCheck /></el-icon>
            在线
          </el-tag>
          <el-tag 
            v-else 
            type="danger" 
            effect="dark"
            size="large"
            class="status-indicator"
          >
            <el-icon><CircleClose /></el-icon>
            离线
          </el-tag>
          <el-button
            class="action-btn"
            :loading="refreshing"
            @click="handleRefresh"
          >
            <el-icon><Refresh /></el-icon>
            刷新数据
          </el-button>
          <el-button
            class="action-btn"
            @click="handleExport"
          >
            <el-icon><Download /></el-icon>
            导出数据
          </el-button>
        </div>
      </div>
    </div>

    <!-- 主内容区域 - 左右分栏布局 -->
    <div class="main-content">
      <el-row :gutter="24">
        <!-- 左侧：控制区域（操作流程从上到下） -->
        <el-col
          :xs="24"
          :sm="24"
          :lg="8"
        >
          <!-- 连接面板 - 首要操作 -->
          <ConnectionPanel class="control-card" />
          
          <!-- 电机控制 - 核心控制 -->
          <MotorControl class="control-card" />
          
          <!-- 位置显示 - 辅助显示 -->
          <PositionDisplay class="monitor-card" />
          
          <!-- IO端口配置 -->
          <IOConfig class="control-card" />
          
          <!-- 实验记录 - 记录管理 -->
          <ExperimentPanel class="monitor-card" />
        </el-col>

        <!-- 右侧：实时数据展示区域（支持折叠） -->
        <el-col
          :xs="24"
          :sm="24"
          :lg="16"
        >
          <!-- 设备状态卡片 - 可折叠 -->
          <el-card
            class="status-card"
            shadow="hover"
          >
            <template #header>
              <div
                class="card-header"
                @click="toggleStatusPanel"
              >
                <div class="header-left-section">
                  <el-icon><Monitor /></el-icon>
                  <span>设备状态</span>
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
                <!-- 运行状态组 -->
                <div class="status-group">
                  <div class="status-group-title">
                    运行状态
                  </div>
                  <div class="status-items">
                    <div class="status-item">
                      <span class="status-label">连接状态</span>
                      <el-tag
                        :type="connectionStatus.type"
                        size="large"
                        effect="plain"
                      >
                        {{ connectionStatus.text }}
                      </el-tag>
                    </div>
                  </div>
                </div>

                <!-- 位置信息组 -->
                <div class="status-group">
                  <div class="status-group-title">
                    位置信息
                  </div>
                  <div class="status-items">
                    <div class="status-item">
                      <span class="status-label">
                        目标位置
                        <el-tooltip
                          content="单位：脉冲数"
                          placement="top"
                        >
                          <el-icon class="tooltip-icon"><QuestionFilled /></el-icon>
                        </el-tooltip>
                      </span>
                      <span class="status-value highlight">--</span>
                    </div>
                    <div class="status-item">
                      <span class="status-label">实际位置</span>
                      <span class="status-value">--</span>
                    </div>
                  </div>
                </div>

                <!-- 速度信息组 -->
                <div class="status-group">
                  <div class="status-group-title">
                    速度信息
                  </div>
                  <div class="status-items">
                    <div class="status-item">
                      <span class="status-label">
                        目标速度
                        <el-tooltip
                          content="单位：RPM"
                          placement="top"
                        >
                          <el-icon class="tooltip-icon"><QuestionFilled /></el-icon>
                        </el-tooltip>
                      </span>
                      <span class="status-value highlight">--</span>
                    </div>
                    <div class="status-item">
                      <span class="status-label">实际速度</span>
                      <span class="status-value">--</span>
                    </div>
                  </div>
                </div>
              </div>
            </el-collapse-transition>
          </el-card>

          <!-- 实时曲线卡片 - 可折叠 -->
          <el-card
            class="chart-card"
            shadow="hover"
          >
            <template #header>
              <div
                class="card-header"
                @click="toggleChartPanel"
              >
                <div class="header-left-section">
                  <el-icon><TrendCharts /></el-icon>
                  <span>实时曲线</span>
                </div>
                <el-icon
                  class="collapse-icon"
                  :class="{ 'is-collapsed': chartCollapsed }"
                >
                  <ArrowDown />
                </el-icon>
              </div>
            </template>

            <el-collapse-transition>
              <div
                v-show="!chartCollapsed"
                class="chart-container"
              >
                <PositionChart
                  ref="chartRef"
                  height="300px"
                />
              </div>
            </el-collapse-transition>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
/**
 * @file MotorControl.vue
 * @path src/views/experiment/
 * @description 电机控制页面，集成连接控制、运动控制、位置监测和实验记录功能
 * @author Agent
 * @date 2024-03-07
 */

import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useMotorStore } from '@/stores/motor'
import { ConnectionPanel, PositionDisplay, PositionChart, IOConfig } from '@/components/device'
import { MotorControl } from '@/components/experiment/motor'
import { ExperimentPanel } from '@/components/experiment'

const motorStore = useMotorStore()

// ==================== 响应式状态 ====================

/** 刷新状态 */
const refreshing = ref(false)

/** 状态面板折叠状态 */
const statusCollapsed = ref(false)

/** 图表面板折叠状态 */
const chartCollapsed = ref(false)

// ==================== 计算属性 ====================

/**
 * 连接状态计算属性
 */
const connectionStatus = computed(() => {
  if (motorStore.isConnected) {
    return { type: 'success', text: '已连接' }
  } else if (motorStore.isConnecting) {
    return { type: 'warning', text: '连接中...' }
  } else {
    return { type: 'danger', text: '未连接' }
  }
})

// ==================== 方法 ====================

/**
 * 切换状态面板折叠状态
 */
function toggleStatusPanel() {
  statusCollapsed.value = !statusCollapsed.value
}

/**
 * 切换图表面板折叠状态
 */
function toggleChartPanel() {
  chartCollapsed.value = !chartCollapsed.value
}

/**
 * 刷新数据
 */
async function handleRefresh() {
  refreshing.value = true
  try {
    // TODO: 调用后端 API 刷新数据
    await motorStore.refreshStatus()
    ElMessage.success('数据已刷新')
  } catch (error) {
    ElMessage.error(`刷新失败：${error.message}`)
  } finally {
    refreshing.value = false
  }
}

/**
 * 导出数据
 */
function handleExport() {
  // TODO: 实现导出功能
  ElMessage.info('导出功能开发中')
}
</script>

<style scoped lang="scss">
.motor-control-page {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  background-color: var(--color-bg-secondary);
}

/* ==================== 页面头部 ==================== */
.page-header {
  background-color: var(--color-surface-primary);
  border-bottom: 1px solid var(--color-border-primary);
  padding: var(--spacing-6);
  box-shadow: var(--shadow-sm);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: var(--content-max-width);
  margin: 0 auto;
  width: 100%;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
}

.header-icon {
  font-size: 32px;
  color: var(--color-primary-500);
  padding: var(--spacing-3);
  background-color: var(--color-primary-50);
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
  margin: 0;
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  line-height: var(--line-height-tight);
}

.page-subtitle {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
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

/* 操作按钮 */
.action-btn {
  transition: var(--transition-all);
  font-weight: var(--font-weight-medium);
}

.action-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.action-btn:active:not(:disabled) {
  transform: translateY(0);
}

/* ==================== 主内容区域 ==================== */
.main-content {
  flex: 1;
  max-width: var(--content-max-width);
  margin: 0 auto;
  width: 100%;
  padding: var(--spacing-6);
}

/* ==================== 卡片通用样式 ==================== */
:deep(.el-card) {
  border-radius: var(--radius-lg);
  border: none;
  margin-bottom: var(--spacing-5);
  transition: var(--transition-all);
}

:deep(.el-card:hover) {
  box-shadow: var(--shadow-lg);
}

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
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.header-left-section {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
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

/* ==================== 控制卡片 ==================== */
.control-card,
.monitor-card {
  :deep(.el-card__body) {
    padding: var(--spacing-6);
  }
}

/* ==================== 状态卡片 ==================== */
.status-card {
  :deep(.el-card__body) {
    padding: var(--spacing-6);
  }
}

.status-grid {
  display: grid;
  gap: var(--spacing-6);
}

.status-group {
  padding: var(--spacing-5);
  background-color: var(--color-bg-tertiary);
  border-radius: var(--radius-md);
  border-left: 4px solid var(--color-primary-500);
  transition: var(--transition-all);
}

.status-group:hover {
  background-color: var(--color-bg-quaternary);
  transform: translateX(4px);
}

.status-group-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-3);
  padding-bottom: var(--spacing-2);
  border-bottom: 2px solid var(--color-primary-500);
}

.status-items {
  display: grid;
  gap: var(--spacing-3);
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-2) 0;
  border-bottom: 1px solid var(--color-border-secondary);
}

.status-item:last-child {
  border-bottom: none;
}

.status-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
}

.tooltip-icon {
  color: var(--color-text-tertiary);
  cursor: help;
  transition: var(--transition-colors);
}

.tooltip-icon:hover {
  color: var(--color-primary-500);
}

.status-value {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  font-family: var(--font-family-mono);
  
  &.highlight {
    color: var(--color-primary-500);
    font-weight: var(--font-weight-bold);
    font-size: var(--font-size-lg);
  }
  
  &.warning {
    color: var(--color-warning);
  }
}

/* ==================== 图表卡片 ==================== */
.chart-card {
  :deep(.el-card__body) {
    padding: var(--spacing-4);
  }
}

.chart-container {
  height: 300px;
  width: 100%;
  border-radius: var(--radius-md);
  overflow: hidden;
}

/* ==================== 参数表单 ==================== */
.params-form {
  padding: var(--spacing-2);
}

.form-unit {
  margin-left: var(--spacing-2);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

/* ==================== 控制按钮 ==================== */
.control-buttons {
  display: grid;
  gap: var(--spacing-3);
}

.control-btn {
  width: 100%;
  height: 48px;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  transition: var(--transition-all);
  
  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
  }
  
  &:active:not(:disabled) {
    transform: translateY(0);
  }
}

/* ==================== 点动控制 ==================== */
.jog-controls {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.jog-direction {
  display: flex;
  justify-content: center;
}

.jog-btn {
  width: 100%;
  height: 48px;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  transition: var(--transition-all);
}

.jog-btn:hover:not(:disabled) {
  transform: scale(1.02);
}

.jog-form {
  padding: var(--spacing-2);
}

/* ==================== 限位状态 ==================== */
.limit-status {
  display: grid;
  gap: var(--spacing-3);
}

.limit-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-2);
  background-color: var(--color-bg-tertiary);
  border-radius: var(--radius-sm);
  transition: var(--transition-all);
}

.limit-item:hover {
  background-color: var(--color-bg-quaternary);
}

.limit-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

/* ==================== 响应式设计 ==================== */
@media (max-width: 1024px) {
  .page-header {
    padding: var(--spacing-5);
  }

  .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-4);
  }

  .header-right {
    width: 100%;
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .main-content {
    padding: var(--spacing-5);
  }
}

@media (max-width: 768px) {
  .page-header {
    padding: var(--spacing-4);
  }

  .page-title {
    font-size: var(--font-size-xl);
  }

  .main-content {
    padding: var(--spacing-4);
  }
  
  .status-grid {
    grid-template-columns: 1fr;
    gap: var(--spacing-4);
  }
  
  .control-buttons {
    grid-template-columns: 1fr;
  }
  
  .status-group {
    padding: var(--spacing-4);
  }
  
  .header-right {
    gap: var(--spacing-2);
  }
  
  .status-indicator {
    padding: var(--spacing-1) var(--spacing-3);
    font-size: var(--font-size-xs);
  }
}
</style>
