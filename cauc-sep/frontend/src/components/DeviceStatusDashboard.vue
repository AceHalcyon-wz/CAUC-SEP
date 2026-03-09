<template>
  <div class="device-status-dashboard">
    <!-- 系统概览卡片 -->
    <el-row :gutter="16" class="overview-row">
      <el-col :xs="24" :sm="12" :md="6">
        <div class="overview-card" :class="`overview-card--${devicesStore.systemStatusType}`">
          <div class="overview-icon">
            <el-icon><Monitor /></el-icon>
          </div>
          <div class="overview-content">
            <div class="overview-label">系统状态</div>
            <div class="overview-value">{{ devicesStore.systemStatusText }}</div>
          </div>
        </div>
      </el-col>
      
      <el-col :xs="24" :sm="12" :md="6">
        <div class="overview-card" :class="`overview-card--${devicesStore.systemHealthType}`">
          <div class="overview-icon">
            <el-icon><Cpu /></el-icon>
          </div>
          <div class="overview-content">
            <div class="overview-label">系统健康度</div>
            <div class="overview-value">{{ devicesStore.systemHealthText }}</div>
          </div>
        </div>
      </el-col>
      
      <el-col :xs="24" :sm="12" :md="6">
        <div class="overview-card overview-card--primary">
          <div class="overview-icon">
            <el-icon><Connection /></el-icon>
          </div>
          <div class="overview-content">
            <div class="overview-label">设备连接</div>
            <div class="overview-value">
              <span class="value-highlight">{{ devicesStore.connectedCount }}</span>
              <span class="value-total">/ {{ devicesStore.totalDevicesCount }}</span>
            </div>
          </div>
        </div>
      </el-col>
      
      <el-col :xs="24" :sm="12" :md="6">
        <div class="overview-card" :class="devicesStore.unacknowledgedAlarmsCount > 0 ? 'overview-card--danger' : 'overview-card--success'">
          <div class="overview-icon">
            <el-icon><Bell /></el-icon>
          </div>
          <div class="overview-content">
            <div class="overview-label">活跃告警</div>
            <div class="overview-value">
              <span class="value-highlight">{{ devicesStore.unacknowledgedAlarmsCount }}</span>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 操作栏 -->
    <div class="action-bar">
      <div class="action-left">
        <el-button
          type="primary"
          :icon="Link"
          :loading="batchConnecting"
          :disabled="devicesStore.allConnected || devicesStore.batchOperation.inProgress"
          @click="handleConnectAll"
        >
          全部连接
        </el-button>
        
        <el-button
          type="danger"
          :icon="SwitchButton"
          :loading="batchDisconnecting"
          :disabled="devicesStore.connectedCount === 0 || devicesStore.batchOperation.inProgress"
          @click="handleDisconnectAll"
        >
          全部断开
        </el-button>
        
        <el-button
          :icon="Refresh"
          :loading="refreshing"
          @click="handleRefresh"
        >
          刷新状态
        </el-button>
      </div>
      
      <div class="action-right">
        <el-button
          :icon="View"
          @click="showHistoryDialog = true"
        >
          状态历史
        </el-button>
        
        <el-button
          :icon="Bell"
          @click="showAlarmDialog = true"
        >
          告警管理
          <el-badge
            v-if="devicesStore.unacknowledgedAlarmsCount > 0"
            :value="devicesStore.unacknowledgedAlarmsCount"
            class="alarm-badge"
          />
        </el-button>
      </div>
    </div>

    <!-- 批量操作进度条 -->
    <Transition name="slide-down">
      <div v-if="devicesStore.batchOperation.inProgress" class="batch-progress">
        <div class="progress-header">
          <span class="progress-title">
            {{ devicesStore.batchOperation.type === 'connect' ? '批量连接中...' : '批量断开中...' }}
          </span>
          <span class="progress-count">
            {{ devicesStore.batchOperation.completed }} / {{ devicesStore.batchOperation.total }}
          </span>
        </div>
        <el-progress
          :percentage="batchProgress"
          :status="batchProgressStatus"
          :stroke-width="8"
        />
        <div class="progress-stats">
          <span class="stat-item stat-success">
            <el-icon><SuccessFilled /></el-icon>
            成功: {{ devicesStore.batchOperation.succeeded }}
          </span>
          <span class="stat-item stat-failed">
            <el-icon><CircleCloseFilled /></el-icon>
            失败: {{ devicesStore.batchOperation.failed }}
          </span>
        </div>
      </div>
    </Transition>

    <!-- 设备状态卡片网格 -->
    <div class="devices-grid">
      <div
        v-for="device in deviceList"
        :key="device.id"
        class="device-card"
        :class="getDeviceCardClass(device)"
        @click="handleDeviceClick(device)"
      >
        <!-- 设备头部 -->
        <div class="device-header">
          <div class="device-info">
            <div class="device-icon" :class="`device-icon--${device.isConnected ? 'connected' : 'disconnected'}`">
              <el-icon><component :is="getDeviceIcon(device.id)" /></el-icon>
            </div>
            <div class="device-name">{{ device.name }}</div>
          </div>
          <div class="device-status">
            <el-tag :type="getStatusTagType(device)" size="small">
              {{ getStatusText(device) }}
            </el-tag>
          </div>
        </div>

        <!-- 设备健康度 -->
        <div class="device-health">
          <div class="health-header">
            <span class="health-label">健康度</span>
            <span class="health-score" :class="`health-score--${devicesStore.HEALTH_STATUS_TYPE[device.health]}`">
              {{ device.healthScore }}%
            </span>
          </div>
          <el-progress
            :percentage="device.healthScore"
            :color="getHealthColor(device.healthScore)"
            :show-text="false"
            :stroke-width="6"
          />
          <div class="health-status">
            <el-tag
              :type="devicesStore.HEALTH_STATUS_TYPE[device.health]"
              size="small"
              effect="plain"
            >
              {{ devicesStore.HEALTH_STATUS_TEXT[device.health] }}
            </el-tag>
          </div>
        </div>

        <!-- 设备指标 -->
        <div class="device-metrics">
          <div class="metric-item">
            <el-icon><Timer /></el-icon>
            <span class="metric-label">运行时间</span>
            <span class="metric-value">{{ formatUptime(device.metrics.uptime) }}</span>
          </div>
          <div class="metric-item">
            <el-icon><Warning /></el-icon>
            <span class="metric-label">错误次数</span>
            <span class="metric-value" :class="{ 'metric-value--warning': device.metrics.errorCount > 0 }">
              {{ device.metrics.errorCount }}
            </span>
          </div>
        </div>

        <!-- 最后更新时间 -->
        <div class="device-footer">
          <el-icon><Clock /></el-icon>
          <span>{{ formatLastUpdate(device.lastUpdate) }}</span>
        </div>

        <!-- 告警指示器 -->
        <div v-if="device.alarms && device.alarms.length > 0" class="alarm-indicator">
          <el-badge :value="device.alarms.length" type="danger">
            <el-icon><Bell /></el-icon>
          </el-badge>
        </div>
      </div>
    </div>

    <!-- 告警管理对话框 -->
    <el-dialog
      v-model="showAlarmDialog"
      title="告警管理"
      width="70%"
      :close-on-click-modal="false"
    >
      <div class="alarm-dialog-content">
        <div class="alarm-toolbar">
          <el-button
            type="primary"
            :disabled="selectedAlarms.length === 0"
            @click="handleAcknowledgeSelected"
          >
            确认选中 ({{ selectedAlarms.length }})
          </el-button>
          <el-button
            type="danger"
            :disabled="devicesStore.alarms.length === 0"
            @click="handleClearAllAlarms"
          >
            清除所有已确认
          </el-button>
        </div>

        <el-table
          :data="devicesStore.alarms"
          style="width: 100%"
          max-height="400"
          @selection-change="handleAlarmSelectionChange"
        >
          <el-table-column type="selection" width="55" />
          <el-table-column prop="deviceName" label="设备" width="120" />
          <el-table-column prop="code" label="代码" width="80" />
          <el-table-column prop="message" label="告警信息" min-width="200" />
          <el-table-column prop="severity" label="级别" width="100">
            <template #default="{ row }">
              <el-tag :type="getSeverityType(row.severity)" size="small">
                {{ getSeverityText(row.severity) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="timestamp" label="时间" width="180">
            <template #default="{ row }">
              {{ formatTimestamp(row.timestamp) }}
            </template>
          </el-table-column>
          <el-table-column prop="acknowledged" label="状态" width="100">
            <template #default="{ row }">
              <el-tag v-if="row.cleared" type="info" size="small">已清除</el-tag>
              <el-tag v-else-if="row.acknowledged" type="success" size="small">已确认</el-tag>
              <el-tag v-else type="warning" size="small">未确认</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="!row.acknowledged"
                type="primary"
                size="small"
                text
                @click="handleAcknowledgeAlarm(row.id)"
              >
                确认
              </el-button>
              <el-button
                v-if="row.acknowledged && !row.cleared"
                type="danger"
                size="small"
                text
                @click="handleClearAlarm(row.id)"
              >
                清除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>

    <!-- 状态历史对话框 -->
    <el-dialog
      v-model="showHistoryDialog"
      title="状态变更历史"
      width="70%"
      :close-on-click-modal="false"
    >
      <div class="history-dialog-content">
        <div class="history-toolbar">
          <el-select
            v-model="historyFilter.deviceId"
            placeholder="选择设备"
            clearable
            style="width: 150px"
          >
            <el-option
              v-for="device in deviceList"
              :key="device.id"
              :label="device.name"
              :value="device.id"
            />
          </el-select>
          
          <el-date-picker
            v-model="historyFilter.timeRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            value-format="timestamp"
          />
          
          <el-button type="primary" @click="handleQueryHistory">
            查询
          </el-button>
          
          <el-button @click="handleClearHistoryFilter">
            重置
          </el-button>
        </div>

        <div class="history-timeline">
          <el-timeline>
            <el-timeline-item
              v-for="record in filteredHistory"
              :key="record.id"
              :timestamp="formatTimestamp(record.timestamp)"
              placement="top"
              :type="getHistoryType(record)"
            >
              <div class="history-card">
                <div class="history-header">
                  <span class="history-device">{{ record.deviceName }}</span>
                  <el-tag size="small" :type="record.currentConnected ? 'success' : 'danger'">
                    {{ record.currentConnected ? '已连接' : '已断开' }}
                  </el-tag>
                </div>
                <div class="history-content">
                  <div class="history-change">
                    <span class="change-label">状态变更:</span>
                    <span class="change-value">{{ record.previousStatus }}</span>
                    <el-icon class="change-arrow"><Right /></el-icon>
                    <span class="change-value">{{ record.currentStatus }}</span>
                  </div>
                </div>
              </div>
            </el-timeline-item>
          </el-timeline>
          
          <el-empty v-if="filteredHistory.length === 0" description="暂无历史记录" />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * @file DeviceStatusDashboard.vue
 * @path src/components/
 * @description 设备状态概览仪表板组件，提供设备状态总览、批量操作、告警管理和历史查询功能
 * @author Agent
 * @date 2024-03-07
 */

import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useDevicesStore } from '@/stores/devices'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Monitor, Cpu, Connection, Bell, Link, SwitchButton, Refresh, View,
  Timer, Warning, Clock, Right, SuccessFilled, CircleCloseFilled
} from '@element-plus/icons-vue'

const router = useRouter()
const devicesStore = useDevicesStore()

// ==================== 响应式状态 ====================

const refreshing = ref(false)
const batchConnecting = ref(false)
const batchDisconnecting = ref(false)
const showAlarmDialog = ref(false)
const showHistoryDialog = ref(false)
const selectedAlarms = ref([])
const historyFilter = ref({
  deviceId: null,
  timeRange: null
})

// ==================== 计算属性 ====================

/**
 * 设备列表
 */
const deviceList = computed(() => {
  return Object.values(devicesStore.devices)
})

/**
 * 批量操作进度百分比
 */
const batchProgress = computed(() => {
  if (devicesStore.batchOperation.total === 0) return 0
  return Math.round((devicesStore.batchOperation.completed / devicesStore.batchOperation.total) * 100)
})

/**
 * 批量操作进度状态
 */
const batchProgressStatus = computed(() => {
  if (devicesStore.batchOperation.inProgress) return null
  if (devicesStore.batchOperation.failed > 0) return 'exception'
  return 'success'
})

/**
 * 过滤后的历史记录
 */
const filteredHistory = computed(() => {
  const options = {}
  
  if (historyFilter.value.deviceId) {
    options.deviceId = historyFilter.value.deviceId
  }
  
  if (historyFilter.value.timeRange && historyFilter.value.timeRange.length === 2) {
    options.startTime = historyFilter.value.timeRange[0]
    options.endTime = historyFilter.value.timeRange[1]
  }
  
  options.limit = 100
  
  return devicesStore.queryStatusHistory(options)
})

// ==================== 方法 ====================

/**
 * 获取设备图标
 */
function getDeviceIcon(deviceId) {
  const iconMap = {
    motor: 'Cpu',
    electromagnet: 'Connection',
    temperature: 'Monitor',
    piezo: 'View',
    ammeter: 'Monitor'
  }
  return iconMap[deviceId] || 'Monitor'
}

/**
 * 获取设备卡片样式类
 */
function getDeviceCardClass(device) {
  return {
    'device-card--connected': device.isConnected,
    'device-card--disconnected': !device.isConnected,
    'device-card--error': device.status === 'error',
    'device-card--warning': device.health === 'warning' || device.health === 'critical'
  }
}

/**
 * 获取状态标签类型
 */
function getStatusTagType(device) {
  if (!device.isConnected) return 'info'
  if (device.status === 'error') return 'danger'
  if (device.status === 'busy' || device.status === 'moving') return 'warning'
  return 'success'
}

/**
 * 获取状态文本
 */
function getStatusText(device) {
  const statusMap = {
    'disconnected': '未连接',
    'ready': '就绪',
    'busy': '忙碌',
    'moving': '运动中',
    'error': '错误',
    'running': '运行中'
  }
  return statusMap[device.status] || device.status
}

/**
 * 获取健康度颜色
 */
function getHealthColor(score) {
  if (score >= 90) return '#67C23A'
  if (score >= 70) return '#95D475'
  if (score >= 50) return '#E6A23C'
  return '#F56C6C'
}

/**
 * 格式化运行时间
 */
function formatUptime(seconds) {
  if (!seconds || seconds === 0) return '0分钟'
  
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  
  if (hours > 0) {
    return `${hours}小时${minutes}分钟`
  }
  return `${minutes}分钟`
}

/**
 * 格式化最后更新时间
 */
function formatLastUpdate(timestamp) {
  if (!timestamp) return '未更新'
  
  const now = Date.now()
  const diff = now - timestamp
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  
  const date = new Date(timestamp)
  return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`
}

/**
 * 格式化时间戳
 */
function formatTimestamp(timestamp) {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`
}

/**
 * 获取告警严重程度类型
 */
function getSeverityType(severity) {
  const typeMap = {
    'info': 'info',
    'warning': 'warning',
    'error': 'danger',
    'critical': 'danger'
  }
  return typeMap[severity] || 'info'
}

/**
 * 获取告警严重程度文本
 */
function getSeverityText(severity) {
  const textMap = {
    'info': '信息',
    'warning': '警告',
    'error': '错误',
    'critical': '严重'
  }
  return textMap[severity] || severity
}

/**
 * 获取历史记录类型
 */
function getHistoryType(record) {
  if (!record.currentConnected) return 'danger'
  if (record.currentStatus === 'error') return 'warning'
  return 'success'
}

/**
 * 处理设备卡片点击
 */
function handleDeviceClick(device) {
  // 根据设备类型跳转到对应的控制页面
  const routeMap = {
    motor: '/experiment/motor',
    electromagnet: '/experiment/electromagnet',
    temperature: '/experiment/temperature',
    piezo: '/experiment/piezo',
    ammeter: '/experiment/ammeter'
  }
  
  const route = routeMap[device.id]
  if (route) {
    router.push(route)
  }
}

/**
 * 刷新所有设备状态
 */
async function handleRefresh() {
  refreshing.value = true
  try {
    await devicesStore.refreshAll()
    ElMessage.success('设备状态已刷新')
  } catch (error) {
    ElMessage.error('刷新失败: ' + error.message)
  } finally {
    refreshing.value = false
  }
}

/**
 * 批量连接所有设备
 */
async function handleConnectAll() {
  try {
    await ElMessageBox.confirm(
      '确定要连接所有未连接的设备吗？',
      '批量连接确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    batchConnecting.value = true
    const result = await devicesStore.connectAllDevices()
    
    if (result.success) {
      ElMessage.success(`成功连接 ${result.succeeded} 个设备`)
    } else {
      ElMessage.warning({
        message: `连接完成：成功 ${result.succeeded} 个，失败 ${result.failed} 个`,
        duration: 5000
      })
      
      // 显示错误详情
      if (result.errors.length > 0) {
        console.error('[DeviceDashboard] Connection errors:', result.errors)
      }
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('批量连接失败: ' + error.message)
    }
  } finally {
    batchConnecting.value = false
    devicesStore.resetBatchOperation()
  }
}

/**
 * 批量断开所有设备
 */
async function handleDisconnectAll() {
  try {
    await ElMessageBox.confirm(
      '确定要断开所有已连接的设备吗？',
      '批量断开确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    batchDisconnecting.value = true
    const result = await devicesStore.disconnectAllDevices()
    
    if (result.success) {
      ElMessage.success(`成功断开 ${result.succeeded} 个设备`)
    } else {
      ElMessage.warning({
        message: `断开完成：成功 ${result.succeeded} 个，失败 ${result.failed} 个`,
        duration: 5000
      })
      
      if (result.errors.length > 0) {
        console.error('[DeviceDashboard] Disconnection errors:', result.errors)
      }
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('批量断开失败: ' + error.message)
    }
  } finally {
    batchDisconnecting.value = false
    devicesStore.resetBatchOperation()
  }
}

/**
 * 处理告警选择变化
 */
function handleAlarmSelectionChange(selection) {
  selectedAlarms.value = selection.map(item => item.id)
}

/**
 * 确认选中的告警
 */
function handleAcknowledgeSelected() {
  if (selectedAlarms.value.length === 0) {
    ElMessage.warning('请先选择要确认的告警')
    return
  }
  
  const count = devicesStore.acknowledgeAlarms(selectedAlarms.value)
  ElMessage.success(`已确认 ${count} 个告警`)
  selectedAlarms.value = []
}

/**
 * 确认单个告警
 */
function handleAcknowledgeAlarm(alarmId) {
  if (devicesStore.acknowledgeAlarm(alarmId)) {
    ElMessage.success('告警已确认')
  }
}

/**
 * 清除单个告警
 */
function handleClearAlarm(alarmId) {
  if (devicesStore.clearAlarm(alarmId)) {
    ElMessage.success('告警已清除')
  }
}

/**
 * 清除所有已确认的告警
 */
async function handleClearAllAlarms() {
  try {
    await ElMessageBox.confirm(
      '确定要清除所有已确认的告警吗？',
      '清除告警确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const count = devicesStore.clearAcknowledgedAlarms()
    ElMessage.success(`已清除 ${count} 个告警`)
  } catch (error) {
    // 用户取消
  }
}

/**
 * 查询历史记录
 */
function handleQueryHistory() {
  // 查询逻辑已在计算属性中实现
  ElMessage.success('历史记录已更新')
}

/**
 * 重置历史查询过滤
 */
function handleClearHistoryFilter() {
  historyFilter.value = {
    deviceId: null,
    timeRange: null
  }
}

// ==================== 生命周期 ====================

onMounted(() => {
  // 初始化设备状态
  devicesStore.init()
})
</script>

<style scoped>
.device-status-dashboard {
  width: 100%;
}

/* 系统概览卡片 */
.overview-row {
  margin-bottom: var(--spacing-6);
}

.overview-card {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
  padding: var(--spacing-5);
  background: var(--color-surface-primary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  transition: var(--transition-all);
  margin-bottom: var(--spacing-3);
}

.overview-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.overview-card--success {
  border-left: 4px solid var(--color-success);
}

.overview-card--warning {
  border-left: 4px solid var(--color-warning);
}

.overview-card--danger {
  border-left: 4px solid var(--color-error);
}

.overview-card--info {
  border-left: 4px solid var(--color-info);
}

.overview-card--primary {
  border-left: 4px solid var(--color-primary-500);
}

.overview-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  font-size: 24px;
  color: var(--color-primary-500);
}

.overview-card--success .overview-icon {
  color: var(--color-success);
}

.overview-card--warning .overview-icon {
  color: var(--color-warning);
}

.overview-card--danger .overview-icon {
  color: var(--color-error);
}

.overview-content {
  flex: 1;
}

.overview-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-1);
}

.overview-value {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
}

.value-highlight {
  color: var(--color-primary-500);
}

.value-total {
  font-size: var(--font-size-base);
  color: var(--color-text-tertiary);
  margin-left: var(--spacing-1);
}

/* 操作栏 */
.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-6);
  padding: var(--spacing-4);
  background: var(--color-surface-primary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
}

.action-left,
.action-right {
  display: flex;
  gap: var(--spacing-3);
}

.alarm-badge {
  margin-left: var(--spacing-2);
}

/* 批量操作进度条 */
.batch-progress {
  padding: var(--spacing-4);
  margin-bottom: var(--spacing-6);
  background: var(--color-surface-primary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-primary-300);
  box-shadow: var(--shadow-md);
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-3);
}

.progress-title {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.progress-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.progress-stats {
  display: flex;
  gap: var(--spacing-6);
  margin-top: var(--spacing-3);
}

.stat-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  font-size: var(--font-size-sm);
}

.stat-success {
  color: var(--color-success);
}

.stat-failed {
  color: var(--color-error);
}

/* 设备卡片网格 */
.devices-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--spacing-4);
}

.device-card {
  position: relative;
  padding: var(--spacing-5);
  background: var(--color-surface-primary);
  border-radius: var(--radius-lg);
  border: 2px solid var(--color-border-primary);
  transition: var(--transition-all);
  cursor: pointer;
  overflow: hidden;
}

.device-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.device-card--connected {
  border-color: var(--color-success);
}

.device-card--disconnected {
  border-color: var(--color-neutral-400);
  opacity: 0.8;
}

.device-card--error {
  border-color: var(--color-error);
  background: linear-gradient(135deg, rgba(229, 62, 62, 0.05) 0%, var(--color-surface-primary) 100%);
}

.device-card--warning {
  border-color: var(--color-warning);
  background: linear-gradient(135deg, rgba(230, 162, 60, 0.05) 0%, var(--color-surface-primary) 100%);
}

/* 设备头部 */
.device-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-4);
}

.device-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.device-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  font-size: 20px;
  transition: var(--transition-all);
}

.device-icon--connected {
  background: var(--color-success-light);
  color: var(--color-success);
}

.device-icon--disconnected {
  background: var(--color-neutral-200);
  color: var(--color-neutral-500);
}

.device-name {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

/* 设备健康度 */
.device-health {
  margin-bottom: var(--spacing-4);
  padding: var(--spacing-3);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
}

.health-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-2);
}

.health-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.health-score {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
}

.health-score--success {
  color: var(--color-success);
}

.health-score--warning {
  color: var(--color-warning);
}

.health-score--danger {
  color: var(--color-error);
}

.health-status {
  margin-top: var(--spacing-2);
  text-align: center;
}

/* 设备指标 */
.device-metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-3);
  margin-bottom: var(--spacing-4);
}

.metric-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: var(--font-size-sm);
}

.metric-item .el-icon {
  color: var(--color-text-tertiary);
}

.metric-label {
  color: var(--color-text-secondary);
}

.metric-value {
  margin-left: auto;
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.metric-value--warning {
  color: var(--color-error);
}

/* 设备底部 */
.device-footer {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding-top: var(--spacing-3);
  border-top: 1px solid var(--color-border-secondary);
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

/* 告警指示器 */
.alarm-indicator {
  position: absolute;
  top: var(--spacing-3);
  right: var(--spacing-3);
}

/* 对话框内容 */
.alarm-dialog-content,
.history-dialog-content {
  min-height: 400px;
}

.alarm-toolbar,
.history-toolbar {
  display: flex;
  gap: var(--spacing-3);
  margin-bottom: var(--spacing-4);
  padding: var(--spacing-3);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
}

/* 历史时间线 */
.history-timeline {
  max-height: 500px;
  overflow-y: auto;
  padding: var(--spacing-4);
}

.history-card {
  padding: var(--spacing-3);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-2);
}

.history-device {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.history-content {
  font-size: var(--font-size-sm);
}

.history-change {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.change-label {
  color: var(--color-text-secondary);
}

.change-value {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.change-arrow {
  color: var(--color-text-tertiary);
}

/* 过渡动画 */
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all var(--transition-base);
}

.slide-down-enter-from,
.slide-down-leave-to {
  transform: translateY(-20px);
  opacity: 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .action-bar {
    flex-direction: column;
    gap: var(--spacing-3);
  }
  
  .action-left,
  .action-right {
    width: 100%;
    justify-content: center;
  }
  
  .devices-grid {
    grid-template-columns: 1fr;
  }
  
  .alarm-toolbar,
  .history-toolbar {
    flex-wrap: wrap;
  }
}
</style>
