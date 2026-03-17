<template>
  <el-dialog
    v-model="visible"
    title="历史记录"
    width="900px"
    :close-on-click-modal="false"
    class="history-dialog"
    @close="handleClose"
  >
    <div class="history-content">
      <div class="history-toolbar">
        <div class="toolbar-left">
          <el-select
            v-model="filterDevice"
            placeholder="选择设备"
            clearable
            size="small"
            style="width: 140px"
          >
            <el-option
              label="全部设备"
              value=""
            />
            <el-option
              v-for="device in deviceList"
              :key="device.id"
              :label="device.name"
              :value="device.id"
            />
          </el-select>
          <el-date-picker
            v-model="timeRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            size="small"
            style="width: 340px"
            :shortcuts="timeShortcuts"
          />
        </div>
        <div class="toolbar-right">
          <el-button
            type="primary"
            size="small"
            @click="handleRefresh"
          >
            刷新
          </el-button>
          <el-button
            size="small"
            @click="handleExport"
          >
            导出
          </el-button>
        </div>
      </div>

      <el-table
        :data="filteredHistory"
        style="width: 100%"
        max-height="400"
      >
        <el-table-column
          prop="timestamp"
          label="时间"
          width="160"
        >
          <template #default="{ row }">
            {{ formatTimestamp(row.timestamp) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="deviceName"
          label="设备"
          width="100"
        />
        <el-table-column
          prop="previousStatus"
          label="原状态"
          width="100"
        >
          <template #default="{ row }">
            <el-tag
              :type="getStatusType(row.previousStatus)"
              size="small"
            >
              {{ getStatusText(row.previousStatus) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="currentStatus"
          label="新状态"
          width="100"
        >
          <template #default="{ row }">
            <el-tag
              :type="getStatusType(row.currentStatus)"
              size="small"
            >
              {{ getStatusText(row.currentStatus) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="previousConnected"
          label="连接状态变更"
          width="120"
        >
          <template #default="{ row }">
            <span v-if="row.previousConnected !== row.currentConnected">
              <el-tag
                v-if="row.currentConnected"
                type="success"
                size="small"
              >
                已连接
              </el-tag>
              <el-tag
                v-else
                type="info"
                size="small"
              >
                已断开
              </el-tag>
            </span>
            <span
              v-else
              class="text-muted"
            >-</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="details"
          label="详情"
          min-width="150"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            {{ getDetailsText(row) }}
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100]"
          :total="totalRecords"
          layout="total, sizes, prev, pager, next"
          small
        />
      </div>

      <div
        v-if="filteredHistory.length === 0"
        class="empty-state"
      >
        <el-empty description="暂无历史记录" />
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">
          关闭
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
/**
 * @file StatusHistoryDialog.vue
 * @path src/components/device/
 * @description 设备状态历史记录对话框组件，提供历史记录查看和导出功能
 * @author Agent
 * @date 2024-03-15
 * @dependencies vue, element-plus, pinia
 */

import { ref, computed, watch } from 'vue'
import { useDevicesStore } from '@/stores/devices'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const devicesStore = useDevicesStore()

const filterDevice = ref('')
const timeRange = ref([])
const currentPage = ref(1)
const pageSize = ref(20)

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const deviceList = computed(() => {
  const devices = devicesStore.devices
  return Object.values(devices).map(d => ({
    id: d.id,
    name: d.name
  }))
})

const statusHistory = computed(() => devicesStore.statusHistory)

const filteredHistory = computed(() => {
  let result = [...statusHistory.value]
  
  if (filterDevice.value) {
    result = result.filter(h => h.deviceId === filterDevice.value)
  }
  
  if (timeRange.value && timeRange.value.length === 2) {
    const [start, end] = timeRange.value
    result = result.filter(h => {
      const ts = h.timestamp
      return ts >= start.getTime() && ts <= end.getTime()
    })
  }
  
  const start = (currentPage.value - 1) * pageSize.value
  return result.slice(start, start + pageSize.value)
})

const totalRecords = computed(() => {
  let count = statusHistory.value.length
  
  if (filterDevice.value) {
    count = statusHistory.value.filter(h => h.deviceId === filterDevice.value).length
  }
  
  if (timeRange.value && timeRange.value.length === 2) {
    const [start, end] = timeRange.value
    count = statusHistory.value.filter(h => {
      const ts = h.timestamp
      return ts >= start.getTime() && ts <= end.getTime()
    }).length
  }
  
  return count
})

const timeShortcuts = [
  {
    text: '最近1小时',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000)
      return [start, end]
    }
  },
  {
    text: '最近24小时',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24)
      return [start, end]
    }
  },
  {
    text: '最近7天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 7)
      return [start, end]
    }
  }
]

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

function getStatusType(status) {
  const typeMap = {
    ready: 'success',
    busy: 'primary',
    moving: 'primary',
    running: 'primary',
    error: 'danger',
    disconnected: 'info',
    connecting: 'warning',
    emergency_stop: 'danger'
  }
  return typeMap[status] || 'info'
}

function getStatusText(status) {
  const textMap = {
    ready: '就绪',
    busy: '忙碌',
    moving: '运动中',
    running: '运行中',
    error: '错误',
    disconnected: '断开',
    connecting: '连接中',
    emergency_stop: '急停'
  }
  return textMap[status] || status
}

function getDetailsText(row) {
  const parts = []
  if (row.previousStatus !== row.currentStatus) {
    parts.push(`状态: ${getStatusText(row.previousStatus)} → ${getStatusText(row.currentStatus)}`)
  }
  if (row.previousConnected !== row.currentConnected) {
    parts.push(`连接: ${row.previousConnected ? '已连接' : '已断开'} → ${row.currentConnected ? '已连接' : '已断开'}`)
  }
  return parts.join('; ') || '-'
}

function handleRefresh() {
  devicesStore.fetchAllDeviceStatus()
  ElMessage.success('历史记录已刷新')
}

function handleExport() {
  const data = filteredHistory.value.map(h => ({
    时间: formatTimestamp(h.timestamp),
    设备: h.deviceName,
    原状态: getStatusText(h.previousStatus),
    新状态: getStatusText(h.currentStatus),
    连接状态: h.currentConnected ? '已连接' : '已断开'
  }))
  
  const headers = Object.keys(data[0] || {})
  const csvContent = [
    headers.join(','),
    ...data.map(row => headers.map(h => row[h]).join(','))
  ].join('\n')
  
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `status_history_${new Date().toISOString().slice(0, 10)}.csv`
  link.click()
  URL.revokeObjectURL(url)
  
  ElMessage.success('历史记录已导出')
}

function handleClose() {
  visible.value = false
  filterDevice.value = ''
  timeRange.value = []
  currentPage.value = 1
}

watch(visible, (val) => {
  if (val) {
    filterDevice.value = ''
    timeRange.value = []
    currentPage.value = 1
  }
})
</script>

<style scoped lang="scss">
.history-dialog {
  :deep(.el-dialog__body) {
    padding: 0;
  }
}

.history-content {
  padding: var(--spacing-4);
}

.history-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-4);
  flex-wrap: wrap;
  gap: var(--spacing-3);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.toolbar-right {
  display: flex;
  gap: var(--spacing-2);
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--spacing-4);
}

.empty-state {
  padding: var(--spacing-8) 0;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
}

.text-muted {
  color: var(--color-text-tertiary);
}

@media (max-width: 768px) {
  .history-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .toolbar-left {
    flex-wrap: wrap;
  }
  
  .toolbar-right {
    justify-content: flex-end;
  }
}
</style>
