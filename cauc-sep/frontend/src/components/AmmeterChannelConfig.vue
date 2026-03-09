<template>
  <div class="ammeter-channel-config">
    <!-- 批量操作工具栏 -->
    <div class="batch-toolbar">
      <div class="toolbar-left">
        <el-checkbox
          v-model="selectAll"
          :indeterminate="isIndeterminate"
          @change="handleSelectAll"
        >
          全选
        </el-checkbox>
        
        <div class="selected-count" v-if="selectedChannels.length > 0">
          已选择 {{ selectedChannels.length }} 个通道
        </div>
      </div>

      <div class="toolbar-right">
        <el-button
          size="small"
          :disabled="selectedChannels.length === 0 || !canControl || isCollecting"
          @click="showBatchConfigDialog = true"
        >
          <el-icon><Setting /></el-icon>
          批量配置
        </el-button>

        <el-button
          size="small"
          :disabled="selectedChannels.length === 0 || !canControl || isCollecting"
          @click="handleBatchEnable(true)"
        >
          <el-icon><Check /></el-icon>
          批量启用
        </el-button>

        <el-button
          size="small"
          :disabled="selectedChannels.length === 0 || !canControl || isCollecting"
          @click="handleBatchEnable(false)"
        >
          <el-icon><Close /></el-icon>
          批量禁用
        </el-button>
      </div>
    </div>

    <!-- 通道分组管理 -->
    <div class="channel-groups">
      <div class="groups-header">
        <h3 class="groups-title">通道分组</h3>
        <el-button
          size="small"
          @click="showGroupDialog = true"
          :disabled="!canControl || isCollecting"
        >
          <el-icon><Plus /></el-icon>
          新建分组
        </el-button>
      </div>

      <div class="groups-list">
        <div
          v-for="group in channelGroups"
          :key="group.id"
          class="group-item"
          :class="{ 'group-active': activeGroup === group.id }"
          @click="selectGroup(group.id)"
        >
          <div class="group-info">
            <span class="group-name">{{ group.name }}</span>
            <span class="group-count">{{ group.channels.length }} 个通道</span>
          </div>
          <div class="group-actions">
            <el-button
              text
              size="small"
              @click.stop="editGroup(group)"
            >
              <el-icon><Edit /></el-icon>
            </el-button>
            <el-button
              text
              size="small"
              @click.stop="deleteGroup(group.id)"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </div>

        <div
          class="group-item group-all"
          :class="{ 'group-active': activeGroup === null }"
          @click="selectGroup(null)"
        >
          <div class="group-info">
            <span class="group-name">所有通道</span>
            <span class="group-count">{{ channelCount }} 个通道</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 通道列表 -->
    <div class="channel-list">
      <div class="list-header">
        <span class="col col-select">选择</span>
        <span class="col col-channel">通道</span>
        <span class="col col-status">状态</span>
        <span class="col col-range">量程</span>
        <span class="col col-filter">滤波</span>
        <span class="col col-actions">操作</span>
      </div>

      <div class="list-body">
        <div
          v-for="channel in filteredChannels"
          :key="channel.id"
          class="channel-row"
          :class="{ 'channel-disabled': !channel.enabled }"
        >
          <div class="col col-select">
            <el-checkbox
              v-model="selectedChannels"
              :label="channel.id"
            />
          </div>

          <div class="col col-channel">
            <div class="channel-info">
              <span class="channel-dot" :style="{ background: channel.color }"></span>
              <span class="channel-name">通道 {{ channel.id }}</span>
            </div>
          </div>

          <div class="col col-status">
            <el-switch
              v-model="channel.enabled"
              :disabled="!canControl || isCollecting"
              @change="handleChannelEnable(channel.id, $event)"
            />
          </div>

          <div class="col col-range">
            <el-select
              v-model="channel.range"
              size="small"
              :disabled="!channel.enabled || !canControl || isCollecting"
              @change="handleChannelConfig(channel.id, 'range', $event)"
            >
              <el-option label="自动" value="auto" />
              <el-option label="低量程" value="low" />
              <el-option label="中量程" value="medium" />
              <el-option label="高量程" value="high" />
            </el-select>
          </div>

          <div class="col col-filter">
            <el-select
              v-model="channel.filter"
              size="small"
              :disabled="!channel.enabled || !canControl || isCollecting"
              @change="handleChannelConfig(channel.id, 'filter', $event)"
            >
              <el-option label="低通滤波" value="low" />
              <el-option label="中通滤波" value="medium" />
              <el-option label="高通滤波" value="high" />
            </el-select>
          </div>

          <div class="col col-actions">
            <el-button
              text
              size="small"
              :disabled="!canControl || isCollecting"
              @click="handleChannelEnable(channel.id, !channel.enabled)"
            >
              {{ channel.enabled ? '禁用' : '启用' }}
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 批量配置对话框 -->
    <el-dialog
      v-model="showBatchConfigDialog"
      title="批量配置通道"
      width="500px"
    >
      <el-form :model="batchConfig" label-width="100px">
        <el-form-item label="配置项">
          <el-checkbox-group v-model="batchConfigItems">
            <el-checkbox label="range">量程</el-checkbox>
            <el-checkbox label="filter">滤波</el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item v-if="batchConfigItems.includes('range')" label="量程">
          <el-select v-model="batchConfig.range" placeholder="选择量程">
            <el-option label="自动" value="auto" />
            <el-option label="低量程" value="low" />
            <el-option label="中量程" value="medium" />
            <el-option label="高量程" value="high" />
          </el-select>
        </el-form-item>

        <el-form-item v-if="batchConfigItems.includes('filter')" label="滤波">
          <el-select v-model="batchConfig.filter" placeholder="选择滤波">
            <el-option label="低通滤波" value="low" />
            <el-option label="中通滤波" value="medium" />
            <el-option label="高通滤波" value="high" />
          </el-select>
        </el-form-item>

        <el-form-item label="应用范围">
          <div class="selected-channels-preview">
            <el-tag
              v-for="ch in selectedChannels"
              :key="ch"
              size="small"
              style="margin: 2px;"
            >
              通道 {{ ch }}
            </el-tag>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showBatchConfigDialog = false">取消</el-button>
        <el-button
          type="primary"
          @click="handleBatchConfig"
          :disabled="batchConfigItems.length === 0"
        >
          应用配置
        </el-button>
      </template>
    </el-dialog>

    <!-- 分组管理对话框 -->
    <el-dialog
      v-model="showGroupDialog"
      :title="editingGroup ? '编辑分组' : '新建分组'"
      width="500px"
    >
      <el-form :model="groupForm" label-width="100px">
        <el-form-item label="分组名称">
          <el-input
            v-model="groupForm.name"
            placeholder="请输入分组名称"
          />
        </el-form-item>

        <el-form-item label="选择通道">
          <el-checkbox-group v-model="groupForm.channels">
            <el-checkbox
              v-for="ch in channelList"
              :key="ch.id"
              :label="ch.id"
            >
              通道 {{ ch.id }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="cancelGroupEdit">取消</el-button>
        <el-button
          type="primary"
          @click="saveGroup"
          :disabled="!groupForm.name || groupForm.channels.length === 0"
        >
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * @file AmmeterChannelConfig.vue
 * @path src/components/
 * @description 微电流通道配置组件，支持批量操作和分组管理
 * @author Agent
 * @date 2024-03-07
 * @dependencies vue, element-plus
 */

import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// ============ Props 定义 ============

const props = defineProps({
  /** 通道配置 */
  channelConfig: {
    type: Object,
    default: () => ({})
  },
  /** 通道数量 */
  channelCount: {
    type: Number,
    default: 4
  },
  /** 是否允许控制 */
  canControl: {
    type: Boolean,
    default: false
  },
  /** 是否正在采集 */
  isCollecting: {
    type: Boolean,
    default: false
  }
})

// ============ Emits 定义 ============

const emit = defineEmits([
  'channel-enable',
  'channel-config',
  'batch-enable',
  'batch-config'
])

// ============ 常量定义 ============

/** 通道颜色配置 */
const CHANNEL_COLORS = [
  '#3B82F6', // 蓝色
  '#10B981', // 绿色
  '#F59E0B', // 黄色
  '#EF4444'  // 红色
]

// ============ 响应式状态 ============

/** 选中的通道 */
const selectedChannels = ref([])

/** 全选状态 */
const selectAll = ref(false)

/** 活动分组 */
const activeGroup = ref(null)

/** 通道分组 */
const channelGroups = ref([])

/** 批量配置对话框 */
const showBatchConfigDialog = ref(false)
const batchConfigItems = ref(['range', 'filter'])
const batchConfig = ref({
  range: 'auto',
  filter: 'low'
})

/** 分组管理对话框 */
const showGroupDialog = ref(false)
const editingGroup = ref(null)
const groupForm = ref({
  name: '',
  channels: []
})

// ============ 计算属性 ============

/**
 * 通道列表（包含颜色和配置）
 */
const channelList = computed(() => {
  return Array.from({ length: props.channelCount }, (_, i) => {
    const id = i + 1
    const config = props.channelConfig[id] || {}
    return {
      id,
      color: CHANNEL_COLORS[i % CHANNEL_COLORS.length],
      enabled: config.enabled ?? true,
      range: config.range || 'auto',
      filter: config.filter || 'low'
    }
  })
})

/**
 * 过滤后的通道列表（根据活动分组）
 */
const filteredChannels = computed(() => {
  if (activeGroup.value === null) {
    return channelList.value
  }

  const group = channelGroups.value.find(g => g.id === activeGroup.value)
  if (!group) {
    return channelList.value
  }

  return channelList.value.filter(ch => group.channels.includes(ch.id))
})

/**
 * 是否半选状态
 */
const isIndeterminate = computed(() => {
  const count = selectedChannels.value.length
  return count > 0 && count < filteredChannels.value.length
})

// ============ 监听器 ============

// 监听全选状态
watch(selectAll, (val) => {
  if (val) {
    selectedChannels.value = filteredChannels.value.map(ch => ch.id)
  } else if (!isIndeterminate.value) {
    selectedChannels.value = []
  }
})

// 监听选中通道，更新全选状态
watch(selectedChannels, (val) => {
  if (val.length === filteredChannels.value.length) {
    selectAll.value = true
  } else if (val.length === 0) {
    selectAll.value = false
  }
})

// ============ 方法 ============

/**
 * 处理全选
 * 
 * @param {boolean} val - 是否全选
 */
function handleSelectAll(val) {
  selectedChannels.value = val ? filteredChannels.value.map(ch => ch.id) : []
}

/**
 * 选择分组
 * 
 * @param {string|null} groupId - 分组ID
 */
function selectGroup(groupId) {
  activeGroup.value = groupId
  selectedChannels.value = []
}

/**
 * 处理通道启用/禁用
 * 
 * @param {number} channelId - 通道ID
 * @param {boolean} enabled - 是否启用
 */
function handleChannelEnable(channelId, enabled) {
  emit('channel-enable', channelId, enabled)
}

/**
 * 处理通道配置变化
 * 
 * @param {number} channelId - 通道ID
 * @param {string} key - 配置键
 * @param {any} value - 配置值
 */
function handleChannelConfig(channelId, key, value) {
  emit('channel-config', channelId, { [key]: value })
}

/**
 * 批量启用/禁用通道
 * 
 * @param {boolean} enabled - 是否启用
 */
async function handleBatchEnable(enabled) {
  if (selectedChannels.value.length === 0) {
    ElMessage.warning('请先选择通道')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要${enabled ? '启用' : '禁用'}选中的 ${selectedChannels.value.length} 个通道吗？`,
      '确认操作',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    emit('batch-enable', selectedChannels.value, enabled)
    ElMessage.success(`已${enabled ? '启用' : '禁用'} ${selectedChannels.value.length} 个通道`)
  } catch {
    // 用户取消操作
  }
}

/**
 * 批量配置通道
 */
async function handleBatchConfig() {
  if (selectedChannels.value.length === 0) {
    ElMessage.warning('请先选择通道')
    return
  }

  if (batchConfigItems.value.length === 0) {
    ElMessage.warning('请至少选择一个配置项')
    return
  }

  const config = {}
  if (batchConfigItems.value.includes('range')) {
    config.range = batchConfig.value.range
  }
  if (batchConfigItems.value.includes('filter')) {
    config.filter = batchConfig.value.filter
  }

  emit('batch-config', selectedChannels.value, config)
  
  showBatchConfigDialog.value = false
  ElMessage.success(`已配置 ${selectedChannels.value.length} 个通道`)
}

/**
 * 编辑分组
 * 
 * @param {Object} group - 分组对象
 */
function editGroup(group) {
  editingGroup.value = group.id
  groupForm.value = {
    name: group.name,
    channels: [...group.channels]
  }
  showGroupDialog.value = true
}

/**
 * 删除分组
 * 
 * @param {string} groupId - 分组ID
 */
async function deleteGroup(groupId) {
  try {
    await ElMessageBox.confirm(
      '确定要删除此分组吗？',
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const index = channelGroups.value.findIndex(g => g.id === groupId)
    if (index !== -1) {
      channelGroups.value.splice(index, 1)
      
      if (activeGroup.value === groupId) {
        activeGroup.value = null
      }
      
      ElMessage.success('分组已删除')
    }
  } catch {
    // 用户取消操作
  }
}

/**
 * 保存分组
 */
function saveGroup() {
  if (!groupForm.value.name) {
    ElMessage.warning('请输入分组名称')
    return
  }

  if (groupForm.value.channels.length === 0) {
    ElMessage.warning('请至少选择一个通道')
    return
  }

  if (editingGroup.value) {
    // 编辑现有分组
    const group = channelGroups.value.find(g => g.id === editingGroup.value)
    if (group) {
      group.name = groupForm.value.name
      group.channels = [...groupForm.value.channels]
    }
    ElMessage.success('分组已更新')
  } else {
    // 创建新分组
    const newGroup = {
      id: `group_${Date.now()}`,
      name: groupForm.value.name,
      channels: [...groupForm.value.channels]
    }
    channelGroups.value.push(newGroup)
    ElMessage.success('分组已创建')
  }

  cancelGroupEdit()
}

/**
 * 取消分组编辑
 */
function cancelGroupEdit() {
  showGroupDialog.value = false
  editingGroup.value = null
  groupForm.value = {
    name: '',
    channels: []
  }
}

// ============ 暴露方法 ============

defineExpose({
  getSelectedChannels: () => selectedChannels.value,
  clearSelection: () => {
    selectedChannels.value = []
  }
})
</script>

<style scoped>
.ammeter-channel-config {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

/* 批量操作工具栏 */
.batch-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-3) var(--spacing-4);
  background: var(--color-surface-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.selected-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  padding-left: var(--spacing-3);
  border-left: 1px solid var(--color-border-primary);
}

/* 通道分组管理 */
.channel-groups {
  background: var(--color-surface-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
  overflow: hidden;
}

.groups-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-3) var(--spacing-4);
  border-bottom: 1px solid var(--color-border-primary);
}

.groups-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.groups-list {
  max-height: 200px;
  overflow-y: auto;
}

.group-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-3) var(--spacing-4);
  cursor: pointer;
  transition: var(--transition-all);
  border-bottom: 1px solid var(--color-border-primary);
}

.group-item:last-child {
  border-bottom: none;
}

.group-item:hover {
  background: var(--color-interactive-hover);
}

.group-item.group-active {
  background: var(--color-primary-50);
  border-left: 3px solid var(--color-primary-500);
}

.group-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.group-name {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.group-count {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.group-actions {
  display: flex;
  gap: var(--spacing-1);
  opacity: 0;
  transition: var(--transition-opacity);
}

.group-item:hover .group-actions {
  opacity: 1;
}

/* 通道列表 */
.channel-list {
  flex: 1;
  background: var(--color-surface-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
  overflow: hidden;
}

.list-header {
  display: flex;
  align-items: center;
  padding: var(--spacing-3) var(--spacing-4);
  background: var(--color-surface-tertiary);
  border-bottom: 1px solid var(--color-border-primary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-secondary);
}

.list-body {
  max-height: 400px;
  overflow-y: auto;
}

.channel-row {
  display: flex;
  align-items: center;
  padding: var(--spacing-3) var(--spacing-4);
  border-bottom: 1px solid var(--color-border-primary);
  transition: var(--transition-all);
}

.channel-row:last-child {
  border-bottom: none;
}

.channel-row:hover {
  background: var(--color-interactive-hover);
}

.channel-row.channel-disabled {
  opacity: 0.5;
}

/* 列宽定义 */
.col {
  flex-shrink: 0;
}

.col-select {
  width: 60px;
}

.col-channel {
  width: 150px;
}

.col-status {
  width: 80px;
}

.col-range {
  width: 140px;
}

.col-filter {
  width: 140px;
}

.col-actions {
  flex: 1;
  text-align: right;
}

.channel-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.channel-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
}

.channel-name {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

/* 对话框样式 */
.selected-channels-preview {
  max-height: 150px;
  overflow-y: auto;
  padding: var(--spacing-2);
  background: var(--color-surface-secondary);
  border-radius: var(--radius-sm);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .batch-toolbar {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-2);
  }
  
  .toolbar-left,
  .toolbar-right {
    justify-content: space-between;
  }
  
  .list-header {
    font-size: var(--font-size-xs);
  }
  
  .col-channel {
    width: 120px;
  }
  
  .col-range,
  .col-filter {
    width: 120px;
  }
}
</style>
