<template>
  <div class="device-status-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-main">
        <div class="header-left">
          <el-icon class="header-icon">
            <DataBoard />
          </el-icon>
          <div class="header-content">
            <h1 class="page-title">
              设备状态监控
            </h1>
            <p class="page-subtitle">
              实时监控设备运行状态、健康度和告警信息
            </p>
          </div>
        </div>
        <div class="header-right">
          <div
            class="status-indicator"
            :class="`status-indicator--${devicesStore.systemStatusType}`"
          >
            <span class="status-dot" />
            <span class="status-text">{{ devicesStore.systemStatusText }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 快速操作区域 -->
    <div class="content-wrapper">
      <el-row
        :gutter="16"
        class="quick-actions-row"
      >
        <el-col
          :xs="12"
          :sm="6"
        >
          <div
            class="quick-action-card"
            @click="refreshAllStatus"
          >
            <div class="action-icon action-icon--primary">
              <el-icon><Refresh /></el-icon>
            </div>
            <div class="action-content">
              <div class="action-title">
                刷新状态
              </div>
              <div class="action-desc">
                更新所有设备状态
              </div>
            </div>
          </div>
        </el-col>
        <el-col
          :xs="12"
          :sm="6"
        >
          <div
            class="quick-action-card"
            @click="viewAlarms"
          >
            <div
              class="action-icon"
              :class="unacknowledgedAlarmsCount > 0 ? 'action-icon--danger' : 'action-icon--success'"
            >
              <el-icon><Bell /></el-icon>
            </div>
            <div class="action-content">
              <div class="action-title">
                告警管理
              </div>
              <div class="action-desc">
                {{ unacknowledgedAlarmsCount > 0 ? `${unacknowledgedAlarmsCount} 条未确认` : '无告警' }}
              </div>
            </div>
          </div>
        </el-col>
        <el-col
          :xs="12"
          :sm="6"
        >
          <div
            class="quick-action-card"
            @click="exportStatus"
          >
            <div class="action-icon action-icon--info">
              <el-icon><Download /></el-icon>
            </div>
            <div class="action-content">
              <div class="action-title">
                导出报告
              </div>
              <div class="action-desc">
                生成状态报告
              </div>
            </div>
          </div>
        </el-col>
        <el-col
          :xs="12"
          :sm="6"
        >
          <div
            class="quick-action-card"
            @click="viewHistory"
          >
            <div class="action-icon action-icon--warning">
              <el-icon><Clock /></el-icon>
            </div>
            <div class="action-content">
              <div class="action-title">
                历史记录
              </div>
              <div class="action-desc">
                查看历史状态
              </div>
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- 设备状态仪表板 -->
      <div class="dashboard-section">
        <DeviceStatusDashboard />
      </div>

      <!-- 详细状态监控（可折叠） -->
      <div class="detailed-monitor-section">
        <div
          class="section-header"
          @click="toggleDetailedMonitor"
        >
          <div class="section-title">
            <el-icon><Monitor /></el-icon>
            <span>详细状态监控</span>
            <el-tag
              size="small"
              type="info"
              effect="plain"
              class="collapse-hint"
            >
              {{ showDetailedMonitor ? '点击收起' : '点击展开' }}
            </el-tag>
          </div>
          <el-icon
            class="toggle-icon"
            :class="{ 'toggle-icon--expanded': showDetailedMonitor }"
          >
            <ArrowDown />
          </el-icon>
        </div>
        
        <Transition name="expand">
          <div
            v-show="showDetailedMonitor"
            class="section-content"
          >
            <DeviceStatusMonitor ref="statusMonitorRef" />
          </div>
        </Transition>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * @file Status.vue
 * @path src/views/device/
 * @description 设备状态监控页面，集成仪表板视图和详细监控组件
 * @author Agent
 * @date 2024-03-07
 */

import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useDevicesStore } from '@/stores/devices'
import { ElMessage } from 'element-plus'
import { DataBoard, Monitor, ArrowDown, Refresh, Bell, Download, Clock } from '@element-plus/icons-vue'
import DeviceStatusDashboard from '@/components/DeviceStatusDashboard.vue'
import DeviceStatusMonitor from '@/components/DeviceStatusMonitor.vue'

const devicesStore = useDevicesStore()
const statusMonitorRef = ref(null)
const showDetailedMonitor = ref(false)

/** 未确认告警数量 */
const unacknowledgedAlarmsCount = computed(() => devicesStore.unacknowledgedAlarmsCount)

/**
 * 切换详细监控显示
 */
function toggleDetailedMonitor() {
  showDetailedMonitor.value = !showDetailedMonitor.value
}

/**
 * 刷新所有设备状态
 */
function refreshAllStatus() {
  devicesStore.refreshAllDevices()
  ElMessage.success('设备状态已刷新')
}

/**
 * 查看告警
 */
function viewAlarms() {
  ElMessage.info('打开告警管理面板')
}

/**
 * 导出状态报告
 */
function exportStatus() {
  ElMessage.success('状态报告已生成')
}

/**
 * 查看历史记录
 */
function viewHistory() {
  ElMessage.info('打开历史记录面板')
}

// ==================== 生命周期 ====================

onMounted(() => {
  // 初始化设备状态store
  devicesStore.init()
})

onBeforeUnmount(() => {
  // 清理资源
  devicesStore.cleanup()
})
</script>

<style scoped lang="scss">
/**
 * 设备状态监控页面样式
 * 遵循 CAUC-SEP 设计系统规范
 */

.device-status-page {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  background-color: var(--color-bg-secondary);
}

/* ==================== 页面头部 ==================== */

.page-header {
  background: linear-gradient(135deg, var(--color-secondary-500) 0%, var(--color-secondary-600) 100%);
  padding: var(--spacing-6);
  box-shadow: var(--shadow-lg);
}

.header-main {
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
  font-size: 48px;
  color: var(--color-text-inverse);
  opacity: 0.95;
  padding: var(--spacing-3);
  background: rgba(255, 255, 255, 0.15);
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
}

.page-subtitle {
  margin: 0;
  font-size: var(--font-size-sm);
  color: rgba(255, 255, 255, 0.85);
}

.header-right {
  display: flex;
  gap: var(--spacing-3);
}

/* 状态指示器 */
.status-indicator {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-3) var(--spacing-4);
  background: rgba(255, 255, 255, 0.15);
  border-radius: var(--radius-lg);
  backdrop-filter: blur(10px);
  transition: var(--transition-all);

  .status-dot {
    width: 10px;
    height: 10px;
    border-radius: var(--radius-full);
    animation: pulse 2s ease-in-out infinite;
  }

  .status-text {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-inverse);
  }

  &--success .status-dot {
    background-color: var(--color-success);
    box-shadow: 0 0 8px var(--color-success);
  }

  &--warning .status-dot {
    background-color: var(--color-warning);
    box-shadow: 0 0 8px var(--color-warning);
  }

  &--danger .status-dot {
    background-color: var(--color-error);
    box-shadow: 0 0 8px var(--color-error);
    animation: pulse 1s ease-in-out infinite;
  }

  &--info .status-dot {
    background-color: var(--color-neutral-400);
  }
}

/* ==================== 内容区域 ==================== */

.content-wrapper {
  flex: 1;
  max-width: var(--content-max-width);
  margin: 0 auto;
  width: 100%;
  padding: var(--spacing-6);
}

/* ==================== 快速操作区域 ==================== */

.quick-actions-row {
  margin-bottom: var(--spacing-6);
}

.quick-action-card {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
  padding: var(--spacing-5);
  background: var(--color-surface-primary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: var(--transition-all);
  box-shadow: var(--shadow-sm);

  &:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-md);
    border-color: var(--color-primary-400);

    .action-icon {
      transform: scale(1.1);
    }
  }

  &:active {
    transform: translateY(-2px);
  }
}

.action-icon {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-lg);
  font-size: var(--font-size-2xl);
  flex-shrink: 0;
  transition: var(--transition-all);

  &--primary {
    background: var(--color-primary-50);
    color: var(--color-primary-500);
  }

  &--success {
    background: var(--color-success-light);
    color: var(--color-success);
  }

  &--warning {
    background: var(--color-warning-light);
    color: var(--color-warning);
  }

  &--danger {
    background: var(--color-error-light);
    color: var(--color-error);
  }

  &--info {
    background: linear-gradient(135deg, var(--color-secondary-50) 0%, var(--color-secondary-100) 100%);
    color: var(--color-secondary-600);
  }
}

.action-content {
  flex: 1;
  min-width: 0;
}

.action-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-1);
}

.action-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: var(--line-height-relaxed);
}

/* ==================== 仪表板区域 ==================== */

.dashboard-section {
  margin-bottom: var(--spacing-6);
}

/* ==================== 详细监控区域 ==================== */

.detailed-monitor-section {
  background: var(--color-surface-primary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  overflow: hidden;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-4) var(--spacing-6);
  background: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border-primary);
  cursor: pointer;
  transition: var(--transition-all);
  user-select: none;

  &:hover {
    background: var(--color-interactive-hover);
  }
}

.section-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.collapse-hint {
  margin-left: var(--spacing-2);
}

.toggle-icon {
  font-size: var(--font-size-lg);
  color: var(--color-text-secondary);
  transition: var(--transition-all);

  &--expanded {
    transform: rotate(180deg);
  }
}

.section-content {
  padding: var(--spacing-6);
}

/* ==================== 动画 ==================== */

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(1.15);
  }
}

/* 展开动画 */
.expand-enter-active,
.expand-leave-active {
  transition: all 0.3s ease;
  max-height: 2000px;
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  max-height: 0;
  opacity: 0;
}

/* ==================== 响应式设计 ==================== */

@media (max-width: 768px) {
  .page-header {
    padding: var(--spacing-4);
  }

  .header-main {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-4);
  }

  .header-icon {
    font-size: 36px;
    padding: var(--spacing-2);
  }

  .page-title {
    font-size: var(--font-size-xl);
  }

  .header-right {
    width: 100%;
  }

  .status-indicator {
    width: 100%;
    justify-content: center;
  }

  .content-wrapper {
    padding: var(--spacing-4);
  }

  .quick-action-card {
    padding: var(--spacing-4);
  }

  .action-icon {
    width: 48px;
    height: 48px;
    font-size: var(--font-size-xl);
  }

  .action-title {
    font-size: var(--font-size-base);
  }

  .section-header {
    padding: var(--spacing-3) var(--spacing-4);
  }

  .section-content {
    padding: var(--spacing-4);
  }
}

@media (max-width: 480px) {
  .quick-action-card {
    flex-direction: column;
    text-align: center;
    gap: var(--spacing-3);
  }

  .action-content {
    display: flex;
    flex-direction: column;
    align-items: center;
  }
}
</style>
