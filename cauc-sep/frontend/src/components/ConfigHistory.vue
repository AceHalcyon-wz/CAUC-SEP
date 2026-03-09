/**
 * @file ConfigHistory.vue
 * @path src/components/
 * @description 配置历史记录组件，提供变更历史查看、对比和回滚功能
 * @author Frontend Engineer Agent
 * @date 2026-03-07
 * @dependencies vue, element-plus, @element-plus/icons-vue, stores/settings
 */

<template>
  <div class="config-history">
    <!-- 历史记录头部 -->
    <div class="history-header">
      <div class="header-left">
        <h3 class="history-title">
          <el-icon><Clock /></el-icon>
          变更历史
        </h3>
        <el-tag v-if="settingsStore.hasHistory" type="info" effect="plain">
          共 {{ settingsStore.configHistory.length }} 条记录
        </el-tag>
      </div>
      <div class="header-right">
        <el-button
          text
          @click="handleClearHistory"
          :disabled="!settingsStore.hasHistory"
        >
          <el-icon><Delete /></el-icon>
          清除历史
        </el-button>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-select
        v-model="filterCategory"
        placeholder="筛选分类"
        clearable
        class="filter-select"
      >
        <el-option
          v-for="category in settingsStore.configCategories"
          :key="category.id"
          :label="category.name"
          :value="category.id"
        />
      </el-select>

      <el-date-picker
        v-model="filterDateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        class="filter-date"
        @change="handleDateFilter"
      />

      <el-input
        v-model="filterKeyword"
        placeholder="搜索配置项..."
        clearable
        class="filter-input"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </div>

    <!-- 历史记录列表 -->
    <div class="history-list" v-loading="settingsStore.loading">
      <template v-if="filteredHistory.length > 0">
        <div
          v-for="record in filteredHistory"
          :key="record.id"
          class="history-item"
          :class="{ 'is-selected': selectedRecord?.id === record.id }"
          @click="handleSelectRecord(record)"
        >
          <div class="item-header">
            <div class="item-info">
              <el-tag
                :type="getCategoryTagType(record.category)"
                size="small"
                effect="plain"
              >
                {{ getCategoryName(record.category) }}
              </el-tag>
              <span class="item-key">{{ getConfigLabel(record.key) }}</span>
            </div>
            <div class="item-time">
              {{ formatTimestamp(record.timestamp) }}
            </div>
          </div>

          <div class="item-changes">
            <div class="change-item">
              <span class="change-label">旧值:</span>
              <code class="change-value old">{{ formatValue(record.oldValue) }}</code>
            </div>
            <el-icon class="change-arrow"><Right /></el-icon>
            <div class="change-item">
              <span class="change-label">新值:</span>
              <code class="change-value new">{{ formatValue(record.newValue) }}</code>
            </div>
          </div>

          <div class="item-actions">
            <el-button
              text
              size="small"
              @click.stop="handleRollback(record)"
            >
              <el-icon><RefreshLeft /></el-icon>
              回滚
            </el-button>
            <el-button
              text
              size="small"
              @click.stop="handleCompare(record)"
            >
              <el-icon><Switch /></el-icon>
              对比
            </el-button>
          </div>
        </div>
      </template>

      <!-- 空状态 -->
      <el-empty
        v-else
        description="暂无变更历史记录"
        :image-size="120"
      >
        <template #image>
          <el-icon class="empty-icon"><DocumentRemove /></el-icon>
        </template>
      </el-empty>
    </div>

    <!-- 变更详情对话框 -->
    <el-dialog
      v-model="showDetailDialog"
      title="变更详情"
      width="600px"
      class="detail-dialog"
    >
      <div v-if="selectedRecord" class="detail-content">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="变更时间">
            {{ formatTimestamp(selectedRecord.timestamp, true) }}
          </el-descriptions-item>
          <el-descriptions-item label="配置分类">
            {{ getCategoryName(selectedRecord.category) }}
          </el-descriptions-item>
          <el-descriptions-item label="配置项">
            {{ getConfigLabel(selectedRecord.key) }}
          </el-descriptions-item>
          <el-descriptions-item label="变更前">
            <code class="detail-code">{{ formatValue(selectedRecord.oldValue) }}</code>
          </el-descriptions-item>
          <el-descriptions-item label="变更后">
            <code class="detail-code">{{ formatValue(selectedRecord.newValue) }}</code>
          </el-descriptions-item>
        </el-descriptions>

        <div class="detail-diff">
          <h4>变更对比</h4>
          <div class="diff-viewer">
            <div class="diff-line old">
              <span class="diff-prefix">-</span>
              <span>{{ formatValue(selectedRecord.oldValue) }}</span>
            </div>
            <div class="diff-line new">
              <span class="diff-prefix">+</span>
              <span>{{ formatValue(selectedRecord.newValue) }}</span>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="showDetailDialog = false">关闭</el-button>
        <el-button
          type="primary"
          @click="handleRollback(selectedRecord)"
          :disabled="!selectedRecord"
        >
          <el-icon><RefreshLeft /></el-icon>
          回滚到此版本
        </el-button>
      </template>
    </el-dialog>

    <!-- 配置对比对话框 -->
    <el-dialog
      v-model="showCompareDialog"
      title="配置对比"
      width="800px"
      class="compare-dialog"
    >
      <div v-if="compareData" class="compare-content">
        <div class="compare-header">
          <div class="compare-side">
            <h4>当前配置</h4>
          </div>
          <div class="compare-side">
            <h4>历史版本</h4>
            <span class="compare-time">{{ formatTimestamp(compareData.timestamp) }}</span>
          </div>
        </div>

        <div class="compare-body">
          <div class="compare-side">
            <div class="compare-item">
              <span class="compare-label">{{ getConfigLabel(compareData.key) }}:</span>
              <code class="compare-value">{{ formatValue(compareData.newValue) }}</code>
            </div>
          </div>
          <div class="compare-side">
            <div class="compare-item">
              <span class="compare-label">{{ getConfigLabel(compareData.key) }}:</span>
              <code class="compare-value">{{ formatValue(compareData.oldValue) }}</code>
            </div>
          </div>
        </div>

        <div class="compare-diff">
          <el-alert
            title="差异说明"
            type="info"
            :closable="false"
          >
            配置项 "{{ getConfigLabel(compareData.key) }}" 从
            <code>{{ formatValue(compareData.oldValue) }}</code>
            变更为
            <code>{{ formatValue(compareData.newValue) }}</code>
          </el-alert>
        </div>
      </div>

      <template #footer>
        <el-button @click="showCompareDialog = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * @file ConfigHistory.vue
 * @path src/components/
 * @description 配置历史记录组件，提供变更历史查看、对比和回滚功能
 * @author Frontend Engineer Agent
 * @date 2026-03-07
 */

import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Clock,
  Delete,
  Search,
  Right,
  RefreshLeft,
  Switch,
  DocumentRemove
} from '@element-plus/icons-vue'
import { useSettingsStore } from '@/stores/settings'

// ==================== Store ====================

const settingsStore = useSettingsStore()

// ==================== 响应式状态 ====================

/** 筛选条件 */
const filterCategory = ref(null)
const filterDateRange = ref(null)
const filterKeyword = ref('')

/** 选中的记录 */
const selectedRecord = ref(null)

/** 对话框显示状态 */
const showDetailDialog = ref(false)
const showCompareDialog = ref(false)

/** 对比数据 */
const compareData = ref(null)

// ==================== 配置标签映射 ====================

/**
 * 配置项标签映射
 */
const configLabels = {
  // 通用配置
  systemName: '系统名称',
  language: '系统语言',
  theme: '界面主题',
  samplingRate: '采样频率',
  refreshInterval: '数据刷新间隔',
  logLevel: '日志级别',

  // 设备配置
  defaultDevice: '默认设备',
  connectionTimeout: '连接超时',
  retryAttempts: '重试次数',
  autoReconnect: '自动重连',
  heartbeatInterval: '设备心跳',

  // 网络配置
  apiBaseUrl: 'API地址',
  websocketUrl: 'WebSocket地址',
  requestTimeout: '请求超时',
  maxConnections: '最大连接数',

  // 安全配置
  enableSafetyMonitor: '安全监控',
  temperatureLimit: '温度上限',
  currentLimit: '电流上限',
  voltageLimit: '电压上限',
  enableEmergencyStop: '紧急停止',
  autoShutdown: '自动关机',

  // 数据管理
  autoSave: '自动保存',
  autoSaveInterval: '保存间隔',
  dataRetentionDays: '数据保留',
  backupPath: '备份路径',
  compressionFormat: '压缩格式',
  maxStorageSize: '最大存储空间'
}

// ==================== 计算属性 ====================

/**
 * 过滤后的历史记录
 */
const filteredHistory = computed(() => {
  let history = [...settingsStore.configHistory]

  // 按分类筛选
  if (filterCategory.value) {
    history = history.filter(h => h.category === filterCategory.value)
  }

  // 按日期范围筛选
  if (filterDateRange.value && filterDateRange.value.length === 2) {
    const [start, end] = filterDateRange.value
    const startTime = new Date(start).getTime()
    const endTime = new Date(end).getTime() + 24 * 60 * 60 * 1000 // 包含结束日期

    history = history.filter(h => {
      const recordTime = new Date(h.timestamp).getTime()
      return recordTime >= startTime && recordTime < endTime
    })
  }

  // 按关键词筛选
  if (filterKeyword.value) {
    const keyword = filterKeyword.value.toLowerCase()
    history = history.filter(h => {
      const label = configLabels[h.key] || h.key
      return label.toLowerCase().includes(keyword) ||
             String(h.oldValue).toLowerCase().includes(keyword) ||
             String(h.newValue).toLowerCase().includes(keyword)
    })
  }

  return history
})

// ==================== 方法 ====================

/**
 * 获取配置标签
 * 
 * @param {string} key - 配置键
 * @returns {string} 配置标签
 */
function getConfigLabel(key) {
  return configLabels[key] || key
}

/**
 * 获取分类名称
 * 
 * @param {string} categoryId - 分类ID
 * @returns {string} 分类名称
 */
function getCategoryName(categoryId) {
  const category = settingsStore.configCategories.find(c => c.id === categoryId)
  return category?.name || categoryId
}

/**
 * 获取分类标签类型
 * 
 * @param {string} categoryId - 分类ID
 * @returns {string} 标签类型
 */
function getCategoryTagType(categoryId) {
  const types = {
    general: '',
    device: 'success',
    network: 'info',
    security: 'warning',
    data: ''
  }
  return types[categoryId] || ''
}

/**
 * 格式化时间戳
 * 
 * @param {string} timestamp - 时间戳
 * @param {boolean} full - 是否显示完整时间
 * @returns {string} 格式化后的时间
 */
function formatTimestamp(timestamp, full = false) {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date

  // 如果是今天，显示相对时间
  if (diff < 24 * 60 * 60 * 1000 && date.getDate() === now.getDate()) {
    const hours = Math.floor(diff / (60 * 60 * 1000))
    const minutes = Math.floor(diff / (60 * 1000))

    if (hours > 0) {
      return `${hours}小时前`
    } else if (minutes > 0) {
      return `${minutes}分钟前`
    } else {
      return '刚刚'
    }
  }

  // 否则显示日期时间
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')

  if (full) {
    const second = String(date.getSeconds()).padStart(2, '0')
    return `${year}-${month}-${day} ${hour}:${minute}:${second}`
  }

  return `${month}-${day} ${hour}:${minute}`
}

/**
 * 格式化值
 * 
 * @param {any} value - 值
 * @returns {string} 格式化后的值
 */
function formatValue(value) {
  if (value === null || value === undefined) {
    return 'null'
  }
  if (typeof value === 'boolean') {
    return value ? 'true' : 'false'
  }
  if (typeof value === 'object') {
    return JSON.stringify(value)
  }
  return String(value)
}

/**
 * 选择记录
 * 
 * @param {Object} record - 历史记录
 */
function handleSelectRecord(record) {
  selectedRecord.value = record
  showDetailDialog.value = true
}

/**
 * 回滚到历史版本
 * 
 * @param {Object} record - 历史记录
 */
async function handleRollback(record) {
  if (!record) return

  try {
    await ElMessageBox.confirm(
      `确定要回滚配置项 "${getConfigLabel(record.key)}" 到历史版本吗？`,
      '确认回滚',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const success = settingsStore.rollbackToHistory(record.id)
    
    if (success) {
      ElMessage.success('配置已回滚')
      showDetailDialog.value = false
    } else {
      ElMessage.error('回滚失败')
    }
  } catch (error) {
    // 用户取消操作
  }
}

/**
 * 对比配置
 * 
 * @param {Object} record - 历史记录
 */
function handleCompare(record) {
  compareData.value = record
  showCompareDialog.value = true
}

/**
 * 处理日期筛选
 */
function handleDateFilter() {
  // 日期筛选逻辑已在 computed 中实现
}

/**
 * 清除历史记录
 */
async function handleClearHistory() {
  try {
    await ElMessageBox.confirm(
      '确定要清除所有历史记录吗？此操作不可撤销。',
      '确认清除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    settingsStore.clearHistory({ keepRecent: 0 })
    ElMessage.success('历史记录已清除')
  } catch (error) {
    // 用户取消操作
  }
}
</script>

<style scoped>
.config-history {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 400px;
  max-height: 600px;
  background-color: var(--color-surface-primary);
}

/* 历史记录头部 */
.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-4);
  border-bottom: 1px solid var(--color-border-primary);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.history-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

/* 筛选栏 */
.filter-bar {
  display: flex;
  gap: var(--spacing-3);
  padding: var(--spacing-4);
  background-color: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border-primary);
}

.filter-select {
  width: 150px;
}

.filter-date {
  width: 260px;
}

.filter-input {
  flex: 1;
  max-width: 300px;
}

/* 历史记录列表 */
.history-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-4);
  min-height: 300px;
}

.history-item {
  padding: var(--spacing-4);
  margin-bottom: var(--spacing-3);
  background-color: var(--color-surface-primary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: var(--transition-all);
}

.history-item:hover {
  border-color: var(--color-primary-300);
  box-shadow: var(--shadow-sm);
}

.history-item.is-selected {
  border-color: var(--color-primary-500);
  background-color: var(--color-primary-50);
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-3);
}

.item-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.item-key {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.item-time {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.item-changes {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-3);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
}

.change-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.change-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.change-value {
  padding: var(--spacing-1) var(--spacing-2);
  background-color: var(--color-surface-primary);
  border-radius: var(--radius-sm);
  font-family: monospace;
  font-size: var(--font-size-sm);
}

.change-value.old {
  color: var(--color-error);
  text-decoration: line-through;
}

.change-value.new {
  color: var(--color-success);
}

.change-arrow {
  color: var(--color-text-secondary);
}

.item-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-2);
  margin-top: var(--spacing-3);
  padding-top: var(--spacing-3);
  border-top: 1px solid var(--color-border-primary);
}

/* 空状态 */
.empty-icon {
  font-size: 80px;
  color: var(--color-text-placeholder);
}

/* 详情对话框 */
.detail-content {
  padding: var(--spacing-4) 0;
}

.detail-code {
  padding: var(--spacing-1) var(--spacing-2);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
  font-family: monospace;
}

.detail-diff {
  margin-top: var(--spacing-6);
}

.detail-diff h4 {
  margin: 0 0 var(--spacing-3) 0;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.diff-viewer {
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.diff-line {
  padding: var(--spacing-2) var(--spacing-3);
  font-family: monospace;
  font-size: var(--font-size-sm);
}

.diff-line.old {
  background-color: rgba(239, 68, 68, 0.1);
  color: var(--color-error);
}

.diff-line.new {
  background-color: rgba(34, 197, 94, 0.1);
  color: var(--color-success);
}

.diff-prefix {
  display: inline-block;
  width: 20px;
  font-weight: var(--font-weight-bold);
}

/* 对比对话框 */
.compare-content {
  padding: var(--spacing-4) 0;
}

.compare-header {
  display: flex;
  gap: var(--spacing-4);
  margin-bottom: var(--spacing-4);
}

.compare-side {
  flex: 1;
}

.compare-side h4 {
  margin: 0 0 var(--spacing-2) 0;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.compare-time {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.compare-body {
  display: flex;
  gap: var(--spacing-4);
  margin-bottom: var(--spacing-4);
}

.compare-item {
  padding: var(--spacing-3);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
}

.compare-label {
  display: block;
  margin-bottom: var(--spacing-2);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.compare-value {
  padding: var(--spacing-2);
  background-color: var(--color-surface-primary);
  border-radius: var(--radius-sm);
  font-family: monospace;
}

.compare-diff {
  margin-top: var(--spacing-4);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .filter-bar {
    flex-wrap: wrap;
  }

  .filter-select,
  .filter-date,
  .filter-input {
    width: 100%;
    max-width: none;
  }

  .item-changes {
    flex-direction: column;
    align-items: flex-start;
  }

  .change-arrow {
    transform: rotate(90deg);
  }

  .compare-header,
  .compare-body {
    flex-direction: column;
  }
}
</style>
