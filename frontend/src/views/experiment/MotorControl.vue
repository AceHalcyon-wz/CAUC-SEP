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
                    <div class="status-item">
                      <span class="status-label">运行状态</span>
                      <el-tag
                        :type="motorStatusType"
                        size="large"
                        effect="plain"
                      >
                        {{ motorStore.status || '未知' }}
                      </el-tag>
                    </div>
                    <div class="status-item">
                      <span class="status-label">限位状态</span>
                      <el-tag
                        :type="motorStore.limitStatusType"
                        size="large"
                        effect="plain"
                      >
                        {{ motorStore.limitStatus }}
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
                      <span class="status-value highlight">{{ motorStore.positionSteps || '--' }}</span>
                    </div>
                    <div class="status-item">
                      <span class="status-label">实际位置</span>
                      <span class="status-value highlight">{{ formatPosition(motorStore.positionMm) }} mm</span>
                    </div>
                    <div class="status-item">
                      <span class="status-label">正向限位</span>
                      <span class="status-value">{{ motorStore.limits.positive_mm }} mm</span>
                    </div>
                    <div class="status-item">
                      <span class="status-label">负向限位</span>
                      <span class="status-value">{{ motorStore.limits.negative_mm }} mm</span>
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
                        当前速度
                        <el-tooltip
                          content="单位：mm/s"
                          placement="top"
                        >
                          <el-icon class="tooltip-icon"><QuestionFilled /></el-icon>
                        </el-tooltip>
                      </span>
                      <span class="status-value highlight">{{ motorStore.velocity || 0 }} mm/s</span>
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
 * @date 2024-03-15
 * @version 3.5.1
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

/**
 * 电机状态类型
 */
const motorStatusType = computed(() => {
  const statusMap = {
    'ready': 'success',
    'running': 'primary',
    'error': 'danger',
    'emergency_stop': 'danger',
    'disconnected': 'info'
  }
  return statusMap[motorStore.status] || 'info'
})

// ==================== 方法 ====================

/**
 * 格式化位置显示
 */
function formatPosition(value) {
  if (value === undefined || value === null) return '--'
  return Number(value).toFixed(3)
}

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
    await motorStore.fetchStatus()
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
async function handleExport() {
  try {
    // 准备导出数据
    const exportData = {
      timestamp: new Date().toISOString(),
      device: 'motor',
      status: {
        connected: motorStore.isConnected,
        status: motorStore.status,
        position_steps: motorStore.positionSteps,
        position_mm: motorStore.positionMm,
        velocity: motorStore.velocity,
        limits: motorStore.limits,
        limit_status: motorStore.limitStatus
      },
      position_history: motorStore.positionHistory.slice(-100),
      movement_history: motorStore.movementHistory.slice(-50)
    }

    // 转换为JSON字符串
    const jsonStr = JSON.stringify(exportData, null, 2)
    
    // 创建下载链接
    const blob = new Blob([jsonStr], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `motor-data-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)

    ElMessage.success('数据导出成功')
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error(`导出失败：${error.message}`)
  }
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

.action-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

/* ==================== 主内容区域 ==================== */
.main-content {
  flex: 1;
  padding: var(--spacing-6);
  max-width: var(--content-max-width);
  margin: 0 auto;
  width: 100%;
}

/* 控制卡片通用样式 */
.control-card,
.monitor-card {
  margin-bottom: var(--spacing-4);
}

/* ==================== 状态卡片 ==================== */
.status-card {
  margin-bottom: var(--spacing-4);
  
  :deep(.el-card__header) {
    padding: 0;
    border-bottom: none;
  }
  
  :deep(.el-card__body) {
    padding: var(--spacing-4);
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-4) var(--spacing-5);
  background-color: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border-primary);
  cursor: pointer;
  transition: var(--transition-all);
  
  &:hover {
    background-color: var(--color-interactive-hover);
  }
}

.header-left-section {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.collapse-icon {
  transition: transform 0.3s ease;
  
  &.is-collapsed {
    transform: rotate(-90deg);
  }
}

/* 状态网格 */
.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--spacing-6);
}

.status-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
}

.status-group-title {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-secondary);
  padding-bottom: var(--spacing-2);
  border-bottom: 1px solid var(--color-border-primary);
}

.status-items {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-2) 0;
}

.status-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
}

.tooltip-icon {
  font-size: 14px;
  color: var(--color-text-tertiary);
  cursor: help;
}

.status-value {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
  
  &.highlight {
    color: var(--color-primary-500);
    font-weight: var(--font-weight-semibold);
  }
}

/* ==================== 图表卡片 ==================== */
.chart-card {
  :deep(.el-card__header) {
    padding: 0;
    border-bottom: none;
  }
  
  :deep(.el-card__body) {
    padding: var(--spacing-4);
  }
}

.chart-container {
  height: 320px;
}

/* ==================== 响应式设计 ==================== */
@media (max-width: 768px) {
  .page-header {
    padding: var(--spacing-4);
  }
  
  .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-4);
  }
  
  .header-right {
    width: 100%;
    flex-wrap: wrap;
  }
  
  .main-content {
    padding: var(--spacing-4);
  }
  
  .status-grid {
    grid-template-columns: 1fr;
  }
}
</style>
