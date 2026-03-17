<template>
  <div class="safety-panel-page">
    <!-- 页面标题 - 状态指示器位于顶部 -->
    <div class="page-header">
      <div class="header-left">
        <el-icon class="header-icon warning-icon">
          <Warning />
        </el-icon>
        <div class="header-text">
          <h1 class="page-title">
            安全面板
          </h1>
          <p class="page-description">
            设备安全监控与紧急控制
          </p>
        </div>
      </div>
      <div class="header-right">
        <el-tag
          type="danger"
          effect="dark"
          size="large"
          class="status-indicator danger"
        >
          <el-icon><Warning /></el-icon>
          安全第一
        </el-tag>
      </div>
    </div>

    <!-- 主内容区域 - 左右分栏布局 -->
    <el-row
      :gutter="24"
      class="content-row"
    >
      <!-- 左侧：安全控制面板 -->
      <el-col
        :xs="24"
        :lg="16"
        class="control-col"
      >
        <SafetyPanel class="control-card" />
      </el-col>

      <!-- 右侧：实时数据展示区域（支持折叠） -->
      <el-col
        :xs="24"
        :lg="8"
        class="info-col"
      >
        <!-- 安全状态卡片 - 可折叠 -->
        <el-card class="status-card">
          <template #header>
            <div
              class="card-header"
              @click="toggleStatusPanel"
            >
              <div class="header-left-section">
                <el-icon class="header-icon safety-icon">
                  <CircleCheck />
                </el-icon>
                <span class="header-title">安全状态</span>
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
                  系统状态
                </div>
                <el-tag
                  :type="systemStatusType"
                  size="small"
                >
                  {{ systemStatusText }}
                </el-tag>
              </div>
              <div class="status-item">
                <div class="status-label">
                  急停状态
                </div>
                <el-tag
                  :type="emergencyStopType"
                  size="small"
                >
                  {{ emergencyStopText }}
                </el-tag>
              </div>
              <div class="status-item">
                <div class="status-label">
                  门锁状态
                </div>
                <el-tag
                  :type="doorLockType"
                  size="small"
                >
                  {{ doorLockText }}
                </el-tag>
              </div>
              <div class="status-item">
                <div class="status-label">
                  报警数量
                </div>
                <div
                  class="status-value mono"
                  :class="{ 'warning': alarmCount > 0 }"
                >
                  {{ alarmCount }}
                </div>
              </div>
            </div>
          </el-collapse-transition>
        </el-card>

        <!-- 报警历史卡片 - 可折叠 -->
        <el-card class="alarm-card">
          <template #header>
            <div
              class="card-header"
              @click="toggleAlarmPanel"
            >
              <div class="header-left-section">
                <el-icon class="header-icon alarm-icon">
                  <Bell />
                </el-icon>
                <span class="header-title">报警历史</span>
                <el-badge
                  v-if="alarmCount > 0"
                  :value="alarmCount"
                  type="danger"
                  class="alarm-badge"
                />
              </div>
              <div class="header-actions">
                <el-button
                  type="primary"
                  size="small"
                  link
                  :loading="isLoading"
                  @click.stop="refreshAlarms"
                >
                  <el-icon><Refresh /></el-icon>
                </el-button>
                <el-icon
                  class="collapse-icon"
                  :class="{ 'is-collapsed': alarmCollapsed }"
                >
                  <ArrowDown />
                </el-icon>
              </div>
            </div>
          </template>
          <el-collapse-transition>
            <div v-show="!alarmCollapsed">
              <div
                v-if="alarmHistory.length === 0"
                class="empty-alarms"
              >
                <el-empty
                  description="暂无告警记录"
                  :image-size="80"
                />
              </div>
              <el-timeline v-else>
                <el-timeline-item
                  v-for="alarm in alarmHistory"
                  :key="alarm.id"
                  :type="alarm.type"
                  :timestamp="alarm.time"
                  placement="top"
                >
                  <div class="alarm-item">
                    <div class="alarm-header">
                      <div class="alarm-title">
                        {{ alarm.title }}
                      </div>
                      <el-button
                        v-if="!alarm.acknowledged"
                        type="primary"
                        size="small"
                        link
                        @click="acknowledgeAlarm(alarm.id)"
                      >
                        确认
                      </el-button>
                    </div>
                    <div class="alarm-desc">
                      {{ alarm.description }}
                    </div>
                    <el-tag
                      v-if="alarm.acknowledged"
                      type="success"
                      size="small"
                    >
                      已确认
                    </el-tag>
                  </div>
                </el-timeline-item>
              </el-timeline>
            </div>
          </el-collapse-transition>
        </el-card>

        <!-- 安全操作指南卡片 - 可折叠 -->
        <el-card class="guide-card">
          <template #header>
            <div
              class="card-header"
              @click="toggleGuidePanel"
            >
              <div class="header-left-section">
                <el-icon class="header-icon">
                  <InfoFilled />
                </el-icon>
                <span class="header-title">安全操作指南</span>
              </div>
              <el-icon
                class="collapse-icon"
                :class="{ 'is-collapsed': guideCollapsed }"
              >
                <ArrowDown />
              </el-icon>
            </div>
          </template>
          <el-collapse-transition>
            <div v-show="!guideCollapsed">
              <el-alert
                v-for="(guide, index) in safetyGuides"
                :key="index"
                :title="guide.title"
                :type="guide.type"
                :description="guide.description"
                :closable="false"
                show-icon
                class="guide-alert"
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
 * @file SafetyPanel.vue
 * @path src/views/experiment/
 * @description 安全面板页面，提供急停功能和设备状态监控
 * @author Agent
 * @date 2024-03-07
 */

import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { Warning, CircleCheck, Bell, InfoFilled, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { SafetyPanel } from '@/components/experiment'
import { useDevicesStore } from '@/stores/devices'

const devicesStore = useDevicesStore()

/** 系统状态 */
const systemStatus = ref('normal')

/** 急停状态 */
const emergencyStop = ref('released')

/** 门锁状态 */
const doorLock = ref('locked')

/** 状态面板折叠状态 */
const statusCollapsed = ref(false)

/** 报警面板折叠状态 */
const alarmCollapsed = ref(false)

/** 指南面板折叠状态 */
const guideCollapsed = ref(false)

/** 加载状态 */
const isLoading = ref(false)

/** 自动刷新定时器 */
let refreshTimer = null

/** 系统状态文本 */
const systemStatusText = computed(() => {
  const statusMap = {
    normal: '正常',
    warning: '警告',
    error: '故障',
    emergency: '紧急'
  }
  return statusMap[systemStatus.value] || '未知'
})

/** 系统状态标签类型 */
const systemStatusType = computed(() => {
  const typeMap = {
    normal: 'success',
    warning: 'warning',
    error: 'danger',
    emergency: 'danger'
  }
  return typeMap[systemStatus.value] || 'info'
})

/** 急停状态文本 */
const emergencyStopText = computed(() => {
  const statusMap = {
    released: '已释放',
    pressed: '已按下'
  }
  return statusMap[emergencyStop.value] || '未知'
})

/** 急停状态标签类型 */
const emergencyStopType = computed(() => {
  return emergencyStop.value === 'released' ? 'success' : 'danger'
})

/** 门锁状态文本 */
const doorLockText = computed(() => {
  const statusMap = {
    locked: '已锁定',
    unlocked: '已解锁'
  }
  return statusMap[doorLock.value] || '未知'
})

/** 门锁状态标签类型 */
const doorLockType = computed(() => {
  return doorLock.value === 'locked' ? 'success' : 'warning'
})

/** 报警数量 - 从store获取 */
const alarmCount = computed(() => {
  return devicesStore.alarms.filter(a => !a.acknowledged).length
})

/** 报警历史 - 从store获取并格式化 */
const alarmHistory = computed(() => {
  const alarms = devicesStore.alarms || []
  return alarms.slice(0, 10).map(alarm => ({
    id: alarm.id,
    time: formatTimestamp(alarm.timestamp),
    title: alarm.message || alarm.title || '未知告警',
    description: alarm.description || getDeviceName(alarm.deviceId),
    type: getAlarmType(alarm.severity),
    acknowledged: alarm.acknowledged,
    deviceId: alarm.deviceId
  }))
})

/**
 * 格式化时间戳
 * @param {number|string} timestamp - 时间戳
 * @returns {string} 格式化后的时间字符串
 */
function formatTimestamp(timestamp) {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

/**
 * 获取设备名称
 * @param {string} deviceId - 设备ID
 * @returns {string} 设备名称
 */
function getDeviceName(deviceId) {
  if (!deviceId) return '系统'
  const device = devicesStore.devices[deviceId]
  return device ? device.name : deviceId
}

/**
 * 获取告警类型
 * @param {string} severity - 告警严重程度
 * @returns {string} Element Plus类型
 */
function getAlarmType(severity) {
  const typeMap = {
    critical: 'danger',
    error: 'danger',
    warning: 'warning',
    info: 'primary'
  }
  return typeMap[severity] || 'warning'
}

/** 安全操作指南 */
const safetyGuides = [
  {
    title: '急停按钮',
    type: 'error',
    description: '紧急情况下立即按下急停按钮'
  },
  {
    title: '设备检查',
    type: 'warning',
    description: '实验前请检查所有安全装置是否正常'
  },
  {
    title: '人员培训',
    type: 'info',
    description: '操作人员必须经过安全培训后方可操作设备'
  }
]

/**
 * 切换状态面板折叠状态
 */
function toggleStatusPanel() {
  statusCollapsed.value = !statusCollapsed.value
}

/**
 * 切换报警面板折叠状态
 */
function toggleAlarmPanel() {
  alarmCollapsed.value = !alarmCollapsed.value
}

/**
 * 切换指南面板折叠状态
 */
function toggleGuidePanel() {
  guideCollapsed.value = !guideCollapsed.value
}

/**
 * 刷新告警数据
 */
async function refreshAlarms() {
  isLoading.value = true
  try {
    await devicesStore.fetchAlarms()
    ElMessage.success('告警数据已刷新')
  } catch (error) {
    ElMessage.error('刷新失败: ' + (error.message || '未知错误'))
  } finally {
    isLoading.value = false
  }
}

/**
 * 确认告警
 * @param {string} alarmId - 告警ID
 */
async function acknowledgeAlarm(alarmId) {
  const success = devicesStore.acknowledgeAlarm(alarmId, 'user')
  if (success) {
    ElMessage.success('告警已确认')
  }
}

/**
 * 初始化数据
 */
async function initData() {
  isLoading.value = true
  try {
    await devicesStore.init()
    updateSystemStatus()
  } catch (error) {
    console.error('初始化失败:', error)
  } finally {
    isLoading.value = false
  }
}

/**
 * 更新系统状态
 */
function updateSystemStatus() {
  const health = devicesStore.systemHealth
  const statusMap = {
    healthy: 'normal',
    degraded: 'warning',
    critical: 'error',
    emergency: 'emergency'
  }
  systemStatus.value = statusMap[health] || 'normal'
  
  const hasEmergency = devicesStore.alarms.some(a => a.severity === 'critical' && !a.acknowledged)
  if (hasEmergency) {
    systemStatus.value = 'emergency'
  }
}

/**
 * 开始自动刷新
 */
function startAutoRefresh() {
  refreshTimer = setInterval(() => {
    devicesStore.fetchAlarms()
    updateSystemStatus()
  }, 30000)
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

// ==================== 生命周期 ====================

onMounted(() => {
  initData()
  startAutoRefresh()
})

onBeforeUnmount(() => {
  stopAutoRefresh()
  devicesStore.cleanup()
})
</script>

<style scoped lang="scss">
.safety-panel-page {
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
  color: var(--color-error);
  padding: var(--spacing-3);
  background-color: var(--color-error-light);
  border-radius: var(--radius-lg);
  transition: var(--transition-all);
}

.header-icon:hover {
  background-color: var(--color-error-lighter);
  transform: scale(1.05);
}

.header-icon.warning-icon {
  color: var(--color-error);
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

.status-indicator.danger {
  background-color: var(--color-error);
  border-color: var(--color-error);
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
.alarm-card,
.guide-card {
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  transition: var(--transition-all);
  background: var(--color-surface-primary);
  border: none;
}

.control-card:hover,
.status-card:hover,
.alarm-card:hover,
.guide-card:hover {
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

.header-icon.safety-icon {
  color: var(--color-success);
}

.header-icon.alarm-icon {
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

.status-value.warning {
  color: var(--color-warning);
}

.mono {
  font-family: var(--font-family-mono);
}

/* ==================== 报警项 ==================== */
.alarm-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.alarm-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.alarm-title {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.alarm-desc {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.alarm-badge {
  margin-left: var(--spacing-2);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.empty-alarms {
  padding: var(--spacing-4) 0;
}

/* ==================== 指南 ==================== */
.guide-alert {
  margin-bottom: var(--spacing-3);
  border-radius: var(--radius-md);
  transition: var(--transition-all);
}

.guide-alert:hover {
  transform: translateX(4px);
}

.guide-alert:last-child {
  margin-bottom: 0;
}

/* ==================== 响应式设计 ==================== */
@media (max-width: 1024px) {
  .safety-panel-page {
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
  .safety-panel-page {
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
