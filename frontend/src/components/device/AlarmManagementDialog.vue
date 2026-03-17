<template>
  <el-dialog
    v-model="visible"
    title="告警管理"
    width="800px"
    :close-on-click-modal="false"
    class="alarm-dialog"
    @close="handleClose"
  >
    <div class="alarm-content">
      <div class="alarm-toolbar">
        <div class="toolbar-left">
          <el-radio-group
            v-model="filterType"
            size="small"
          >
            <el-radio-button label="all">
              全部 ({{ alarms.length }})
            </el-radio-button>
            <el-radio-button label="unacknowledged">
              未确认 ({{ unacknowledgedCount }})
            </el-radio-button>
            <el-radio-button label="critical">
              严重 ({{ criticalCount }})
            </el-radio-button>
          </el-radio-group>
        </div>
        <div class="toolbar-right">
          <el-button
            type="primary"
            size="small"
            :disabled="selectedAlarms.length === 0"
            @click="handleAcknowledgeSelected"
          >
            确认选中 ({{ selectedAlarms.length }})
          </el-button>
          <el-button
            type="success"
            size="small"
            :disabled="unacknowledgedCount === 0"
            @click="handleAcknowledgeAll"
          >
            确认全部
          </el-button>
          <el-button
            type="danger"
            size="small"
            :disabled="selectedAlarms.length === 0"
            @click="handleClearSelected"
          >
            清除选中
          </el-button>
        </div>
      </div>

      <el-table
        ref="tableRef"
        :data="filteredAlarms"
        style="width: 100%"
        max-height="400"
        @selection-change="handleSelectionChange"
      >
        <el-table-column
          type="selection"
          width="50"
        />
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
          prop="severity"
          label="级别"
          width="80"
        >
          <template #default="{ row }">
            <el-tag
              :type="getSeverityType(row.severity)"
              size="small"
              effect="dark"
            >
              {{ getSeverityText(row.severity) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="message"
          label="告警信息"
          min-width="200"
          show-overflow-tooltip
        />
        <el-table-column
          prop="acknowledged"
          label="状态"
          width="80"
        >
          <template #default="{ row }">
            <el-tag
              v-if="row.acknowledged"
              type="success"
              size="small"
            >
              已确认
            </el-tag>
            <el-tag
              v-else
              type="warning"
              size="small"
            >
              待确认
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          label="操作"
          width="120"
          fixed="right"
        >
          <template #default="{ row }">
            <el-button
              v-if="!row.acknowledged"
              type="primary"
              size="small"
              link
              @click="handleAcknowledge(row)"
            >
              确认
            </el-button>
            <el-button
              v-if="!row.cleared"
              type="danger"
              size="small"
              link
              @click="handleClear(row)"
            >
              清除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div
        v-if="filteredAlarms.length === 0"
        class="empty-state"
      >
        <el-empty description="暂无告警记录" />
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
 * @file AlarmManagementDialog.vue
 * @path src/components/device/
 * @description 告警管理对话框组件，提供告警查看、确认和清除功能
 * @author Agent
 * @date 2024-03-15
 * @dependencies vue, element-plus, pinia
 */

import { ref, computed, watch } from 'vue'
import { useDevicesStore } from '@/stores/devices'
import { ElMessage, ElMessageBox } from 'element-plus'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const devicesStore = useDevicesStore()
const tableRef = ref(null)
const filterType = ref('all')
const selectedAlarms = ref([])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const alarms = computed(() => devicesStore.alarms)

const unacknowledgedCount = computed(() => 
  alarms.value.filter(a => !a.acknowledged).length
)

const criticalCount = computed(() => 
  alarms.value.filter(a => a.severity === 'critical' || a.severity === 'error').length
)

const filteredAlarms = computed(() => {
  switch (filterType.value) {
    case 'unacknowledged':
      return alarms.value.filter(a => !a.acknowledged)
    case 'critical':
      return alarms.value.filter(a => a.severity === 'critical' || a.severity === 'error')
    default:
      return alarms.value
  }
})

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

function getSeverityType(severity) {
  const typeMap = {
    critical: 'danger',
    error: 'danger',
    warning: 'warning',
    info: 'info'
  }
  return typeMap[severity] || 'info'
}

function getSeverityText(severity) {
  const textMap = {
    critical: '严重',
    error: '错误',
    warning: '警告',
    info: '信息'
  }
  return textMap[severity] || severity
}

function handleSelectionChange(selection) {
  selectedAlarms.value = selection
}

async function handleAcknowledge(alarm) {
  const success = devicesStore.acknowledgeAlarm(alarm.id, 'user')
  if (success) {
    ElMessage.success('告警已确认')
  }
}

async function handleAcknowledgeSelected() {
  if (selectedAlarms.value.length === 0) return
  
  try {
    await ElMessageBox.confirm(
      `确定要确认选中的 ${selectedAlarms.value.length} 条告警吗？`,
      '批量确认',
      { type: 'warning' }
    )
    
    const ids = selectedAlarms.value.map(a => a.id)
    const count = devicesStore.acknowledgeAlarms(ids, 'user')
    ElMessage.success(`已确认 ${count} 条告警`)
    selectedAlarms.value = []
  } catch {
    // 用户取消
  }
}

async function handleAcknowledgeAll() {
  const unacknowledged = alarms.value.filter(a => !a.acknowledged)
  if (unacknowledged.length === 0) return
  
  try {
    await ElMessageBox.confirm(
      `确定要确认全部 ${unacknowledged.length} 条未确认告警吗？`,
      '确认全部',
      { type: 'warning' }
    )
    
    const ids = unacknowledged.map(a => a.id)
    const count = devicesStore.acknowledgeAlarms(ids, 'user')
    ElMessage.success(`已确认 ${count} 条告警`)
  } catch {
    // 用户取消
  }
}

async function handleClear(alarm) {
  try {
    await ElMessageBox.confirm(
      '确定要清除这条告警吗？',
      '清除告警',
      { type: 'warning' }
    )
    
    const success = devicesStore.clearAlarm(alarm.id)
    if (success) {
      ElMessage.success('告警已清除')
    }
  } catch {
    // 用户取消
  }
}

async function handleClearSelected() {
  if (selectedAlarms.value.length === 0) return
  
  try {
    await ElMessageBox.confirm(
      `确定要清除选中的 ${selectedAlarms.value.length} 条告警吗？`,
      '批量清除',
      { type: 'warning' }
    )
    
    let count = 0
    for (const alarm of selectedAlarms.value) {
      if (devicesStore.clearAlarm(alarm.id)) {
        count++
      }
    }
    ElMessage.success(`已清除 ${count} 条告警`)
    selectedAlarms.value = []
  } catch {
    // 用户取消
  }
}

function handleClose() {
  visible.value = false
  selectedAlarms.value = []
  filterType.value = 'all'
}

watch(visible, (val) => {
  if (val) {
    selectedAlarms.value = []
    filterType.value = 'all'
  }
})
</script>

<style scoped lang="scss">
.alarm-dialog {
  :deep(.el-dialog__body) {
    padding: 0;
  }
}

.alarm-content {
  padding: var(--spacing-4);
}

.alarm-toolbar {
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
}

.toolbar-right {
  display: flex;
  gap: var(--spacing-2);
}

.empty-state {
  padding: var(--spacing-8) 0;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .alarm-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .toolbar-right {
    justify-content: flex-end;
  }
}
</style>
