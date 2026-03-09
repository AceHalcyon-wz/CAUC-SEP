<template>
  <div class="audit-log-filter">
    <!-- 快捷时间选择 -->
    <div class="quick-time-selector">
      <el-radio-group v-model="quickTimeRange" size="small" @change="handleQuickTimeChange">
        <el-radio-button label="today">今天</el-radio-button>
        <el-radio-button label="yesterday">昨天</el-radio-button>
        <el-radio-button label="week">本周</el-radio-button>
        <el-radio-button label="month">本月</el-radio-button>
        <el-radio-button label="custom">自定义</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 筛选表单 -->
    <el-form :model="filterForm" label-width="100px" class="filter-form">
      <el-row :gutter="24">
        <!-- 时间范围 -->
        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <el-form-item label="时间范围" class="form-item">
            <el-date-picker
              v-model="filterForm.timeRange"
              type="datetimerange"
              range-separator="至"
              start-placeholder="开始时间"
              end-placeholder="结束时间"
              format="YYYY-MM-DD HH:mm:ss"
              value-format="YYYY-MM-DDTHH:mm:ss"
              :disabled="quickTimeRange !== 'custom'"
              class="form-date-picker"
              @change="handleTimeRangeChange"
            />
          </el-form-item>
        </el-col>

        <!-- 用户筛选 -->
        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <el-form-item label="用户" class="form-item">
            <el-select
              v-model="filterForm.user_id"
              placeholder="全部用户"
              clearable
              filterable
              class="form-select"
              @change="handleFilterChange"
            >
              <el-option
                v-for="user in auditStore.userList"
                :key="user.id"
                :label="user.name || user.id"
                :value="user.id"
              />
            </el-select>
          </el-form-item>
        </el-col>

        <!-- 设备筛选 -->
        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <el-form-item label="设备" class="form-item">
            <el-select
              v-model="filterForm.device_id"
              placeholder="全部设备"
              clearable
              class="form-select"
              @change="handleFilterChange"
            >
              <el-option
                v-for="device in auditStore.deviceList"
                :key="device.id"
                :label="device.name || device.id"
                :value="device.id"
              />
            </el-select>
          </el-form-item>
        </el-col>

        <!-- 操作分类 -->
        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <el-form-item label="操作分类" class="form-item">
            <el-select
              v-model="filterForm.category"
              placeholder="全部分类"
              clearable
              class="form-select"
              @change="handleFilterChange"
            >
              <el-option
                v-for="cat in auditStore.categories"
                :key="cat.code"
                :label="cat.name"
                :value="cat.code"
              />
            </el-select>
          </el-form-item>
        </el-col>

        <!-- 操作类型 -->
        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <el-form-item label="操作类型" class="form-item">
            <el-select
              v-model="filterForm.operation_type"
              placeholder="全部类型"
              clearable
              filterable
              class="form-select"
              @change="handleFilterChange"
            >
              <el-option
                v-for="op in auditStore.operationTypes"
                :key="op.type"
                :label="op.description"
                :value="op.type"
              />
            </el-select>
          </el-form-item>
        </el-col>

        <!-- 响应状态 -->
        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <el-form-item label="响应状态" class="form-item">
            <el-select
              v-model="filterForm.status"
              placeholder="全部状态"
              clearable
              class="form-select"
              @change="handleFilterChange"
            >
              <el-option label="成功 (2xx)" :value="200" />
              <el-option label="重定向 (3xx)" :value="300" />
              <el-option label="客户端错误 (4xx)" :value="400" />
              <el-option label="服务器错误 (5xx)" :value="500" />
            </el-select>
          </el-form-item>
        </el-col>

        <!-- 状态码范围 -->
        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <el-form-item label="状态码范围" class="form-item">
            <div class="range-input-group">
              <el-input-number
                v-model="filterForm.response_status_min"
                :min="100"
                :max="599"
                placeholder="最小"
                controls-position="right"
                class="range-input"
                @change="handleFilterChange"
              />
              <span class="range-separator">-</span>
              <el-input-number
                v-model="filterForm.response_status_max"
                :min="100"
                :max="599"
                placeholder="最大"
                controls-position="right"
                class="range-input"
                @change="handleFilterChange"
              />
            </div>
          </el-form-item>
        </el-col>

        <!-- 耗时范围 -->
        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <el-form-item label="耗时范围(ms)" class="form-item">
            <div class="range-input-group">
              <el-input-number
                v-model="filterForm.duration_min"
                :min="0"
                placeholder="最小"
                controls-position="right"
                class="range-input"
                @change="handleFilterChange"
              />
              <span class="range-separator">-</span>
              <el-input-number
                v-model="filterForm.duration_max"
                :min="0"
                placeholder="最大"
                controls-position="right"
                class="range-input"
                @change="handleFilterChange"
              />
            </div>
          </el-form-item>
        </el-col>

        <!-- 关键词搜索 -->
        <el-col :xs="24" :sm="24" :md="16" :lg="12">
          <el-form-item label="关键词搜索" class="form-item">
            <el-input
              v-model="filterForm.keyword"
              placeholder="搜索路径、参数、消息等..."
              clearable
              class="keyword-input"
              @keyup.enter="handleSearch"
              @clear="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
              <template #append>
                <el-button @click="handleSearch">
                  搜索
                </el-button>
              </template>
            </el-input>
          </el-form-item>
        </el-col>
      </el-row>

      <!-- 操作按钮 -->
      <el-row :gutter="24" class="action-row">
        <el-col :span="24">
          <div class="action-buttons">
            <el-button type="primary" @click="handleApplyFilter">
              <el-icon><Search /></el-icon>
              应用筛选
            </el-button>
            <el-button @click="handleResetFilter">
              <el-icon><RefreshLeft /></el-icon>
              重置
            </el-button>
            <el-button @click="handleSaveFilter" :disabled="!hasActiveFilters">
              <el-icon><CollectionTag /></el-icon>
              保存条件
            </el-button>
            <el-dropdown @command="handleLoadSavedFilter" v-if="savedFilters.length > 0">
              <el-button>
                <el-icon><FolderOpened /></el-icon>
                加载条件
                <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item
                    v-for="(filter, index) in savedFilters"
                    :key="index"
                    :command="index"
                  >
                    {{ filter.name }}
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-col>
      </el-row>
    </el-form>

    <!-- 活动筛选标签 -->
    <div class="active-filters" v-if="hasActiveFilters">
      <span class="filter-label">当前筛选：</span>
      <el-tag
        v-if="filterForm.timeRange && filterForm.timeRange.length === 2"
        closable
        @close="removeFilter('timeRange')"
        class="filter-tag"
      >
        时间: {{ formatTimeRange(filterForm.timeRange) }}
      </el-tag>
      <el-tag
        v-if="filterForm.user_id"
        closable
        @close="removeFilter('user_id')"
        class="filter-tag"
      >
        用户: {{ getUserName(filterForm.user_id) }}
      </el-tag>
      <el-tag
        v-if="filterForm.device_id"
        closable
        @close="removeFilter('device_id')"
        class="filter-tag"
      >
        设备: {{ getDeviceName(filterForm.device_id) }}
      </el-tag>
      <el-tag
        v-if="filterForm.category"
        closable
        @close="removeFilter('category')"
        class="filter-tag"
      >
        分类: {{ getCategoryName(filterForm.category) }}
      </el-tag>
      <el-tag
        v-if="filterForm.operation_type"
        closable
        @close="removeFilter('operation_type')"
        class="filter-tag"
      >
        类型: {{ getOperationName(filterForm.operation_type) }}
      </el-tag>
      <el-tag
        v-if="filterForm.status"
        closable
        @close="removeFilter('status')"
        class="filter-tag"
      >
        状态: {{ getStatusName(filterForm.status) }}
      </el-tag>
      <el-tag
        v-if="filterForm.keyword"
        closable
        @close="removeFilter('keyword')"
        class="filter-tag"
      >
        关键词: {{ filterForm.keyword }}
      </el-tag>
      <el-tag
        v-if="filterForm.response_status_min || filterForm.response_status_max"
        closable
        @close="removeFilter('statusRange')"
        class="filter-tag"
      >
        状态码: {{ filterForm.response_status_min || '100' }} - {{ filterForm.response_status_max || '599' }}
      </el-tag>
      <el-tag
        v-if="filterForm.duration_min || filterForm.duration_max"
        closable
        @close="removeFilter('durationRange')"
        class="filter-tag"
      >
        耗时: {{ filterForm.duration_min || '0' }}ms - {{ filterForm.duration_max || '∞' }}ms
      </el-tag>
    </div>

    <!-- 保存筛选对话框 -->
    <el-dialog
      v-model="saveFilterDialogVisible"
      title="保存筛选条件"
      width="400px"
      class="save-filter-dialog"
    >
      <el-form :model="saveFilterForm" label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="saveFilterForm.name" placeholder="请输入筛选条件名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="saveFilterForm.description"
            type="textarea"
            :rows="3"
            placeholder="可选：添加描述信息"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="saveFilterDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmSaveFilter">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
/**
 * @file AuditLogFilter.vue
 * @path src/components/
 * @description 审计日志多条件筛选组件，支持时间、用户、设备、操作类型等多种筛选条件
 * @author Frontend Engineer Agent
 * @date 2026-03-07
 * @dependencies vue, element-plus, stores/audit
 */

import { ref, reactive, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuditStore } from '../stores/audit'

// ==================== Props & Emits ====================

const emit = defineEmits<{
  (e: 'filter', filters: any): void
  (e: 'reset'): void
}>()

// ==================== Store 实例 ====================

const auditStore = useAuditStore()

// ==================== 本地状态 ====================

/** 快捷时间选择 */
const quickTimeRange = ref('today')

/** 筛选表单 */
const filterForm = reactive({
  timeRange: null,
  user_id: null,
  device_id: null,
  category: null,
  operation_type: null,
  status: null,
  keyword: '',
  response_status_min: null,
  response_status_max: null,
  duration_min: null,
  duration_max: null
})

/** 保存的筛选条件 */
const savedFilters = ref([])

/** 保存筛选对话框 */
const saveFilterDialogVisible = ref(false)

/** 保存筛选表单 */
const saveFilterForm = reactive({
  name: '',
  description: ''
})

// ==================== 计算属性 ====================

/** 是否有活动的筛选条件 */
const hasActiveFilters = computed(() => {
  return !!(
    filterForm.timeRange ||
    filterForm.user_id ||
    filterForm.device_id ||
    filterForm.category ||
    filterForm.operation_type ||
    filterForm.status ||
    filterForm.keyword ||
    filterForm.response_status_min ||
    filterForm.response_status_max ||
    filterForm.duration_min ||
    filterForm.duration_max
  )
})

// ==================== 时间处理方法 ====================

/**
 * 获取时间范围
 * 
 * @param {string} type - 时间类型
 * @returns {Array<string>} 时间范围数组
 */
function getTimeRange(type) {
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  
  switch (type) {
    case 'today':
      return [
        today.toISOString().slice(0, 19).replace('T', ' '),
        now.toISOString().slice(0, 19).replace('T', ' ')
      ]
    case 'yesterday': {
      const yesterday = new Date(today)
      yesterday.setDate(yesterday.getDate() - 1)
      return [
        yesterday.toISOString().slice(0, 19).replace('T', ' '),
        today.toISOString().slice(0, 19).replace('T', ' ')
      ]
    }
    case 'week': {
      const weekStart = new Date(today)
      weekStart.setDate(weekStart.getDate() - weekStart.getDay())
      return [
        weekStart.toISOString().slice(0, 19).replace('T', ' '),
        now.toISOString().slice(0, 19).replace('T', ' ')
      ]
    }
    case 'month': {
      const monthStart = new Date(now.getFullYear(), now.getMonth(), 1)
      return [
        monthStart.toISOString().slice(0, 19).replace('T', ' '),
        now.toISOString().slice(0, 19).replace('T', ' ')
      ]
    }
    default:
      return null
  }
}

/**
 * 快捷时间选择变更处理
 * 
 * @param {string} type - 时间类型
 */
function handleQuickTimeChange(type) {
  if (type !== 'custom') {
    filterForm.timeRange = getTimeRange(type)
    handleFilterChange()
  }
}

/**
 * 时间范围变更处理
 */
function handleTimeRangeChange() {
  handleFilterChange()
}

// ==================== 筛选处理方法 ====================

/**
 * 筛选条件变更处理
 */
function handleFilterChange() {
  // 延迟处理，避免频繁触发
  if (filterChangeTimer) {
    clearTimeout(filterChangeTimer)
  }
  filterChangeTimer = setTimeout(() => {
    emit('filter', getFilterParams())
  }, 300)
}

let filterChangeTimer = null

/**
 * 关键词搜索处理
 */
function handleSearch() {
  emit('filter', getFilterParams())
}

/**
 * 应用筛选
 */
function handleApplyFilter() {
  emit('filter', getFilterParams())
}

/**
 * 重置筛选
 */
function handleResetFilter() {
  // 重置表单
  filterForm.timeRange = null
  filterForm.user_id = null
  filterForm.device_id = null
  filterForm.category = null
  filterForm.operation_type = null
  filterForm.status = null
  filterForm.keyword = ''
  filterForm.response_status_min = null
  filterForm.response_status_max = null
  filterForm.duration_min = null
  filterForm.duration_max = null
  quickTimeRange.value = 'today'
  
  // 重置Store筛选条件
  auditStore.clearFilters()
  
  emit('reset')
  
  ElMessage.success('筛选条件已重置')
}

/**
 * 移除单个筛选条件
 * 
 * @param {string} field - 字段名
 */
function removeFilter(field) {
  switch (field) {
    case 'timeRange':
      filterForm.timeRange = null
      quickTimeRange.value = 'custom'
      break
    case 'user_id':
      filterForm.user_id = null
      break
    case 'device_id':
      filterForm.device_id = null
      break
    case 'category':
      filterForm.category = null
      break
    case 'operation_type':
      filterForm.operation_type = null
      break
    case 'status':
      filterForm.status = null
      break
    case 'keyword':
      filterForm.keyword = ''
      break
    case 'statusRange':
      filterForm.response_status_min = null
      filterForm.response_status_max = null
      break
    case 'durationRange':
      filterForm.duration_min = null
      filterForm.duration_max = null
      break
  }
  
  handleFilterChange()
}

/**
 * 获取筛选参数
 * 
 * @returns {Object} 筛选参数对象
 */
function getFilterParams() {
  const params = {}
  
  if (filterForm.timeRange && filterForm.timeRange.length === 2) {
    params.start_time = filterForm.timeRange[0]
    params.end_time = filterForm.timeRange[1]
  }
  
  if (filterForm.user_id) params.user_id = filterForm.user_id
  if (filterForm.device_id) params.device_id = filterForm.device_id
  if (filterForm.category) params.category = filterForm.category
  if (filterForm.operation_type) params.operation_type = filterForm.operation_type
  if (filterForm.status) params.status = filterForm.status
  if (filterForm.keyword) params.keyword = filterForm.keyword
  if (filterForm.response_status_min) params.response_status_min = filterForm.response_status_min
  if (filterForm.response_status_max) params.response_status_max = filterForm.response_status_max
  if (filterForm.duration_min) params.duration_min = filterForm.duration_min
  if (filterForm.duration_max) params.duration_max = filterForm.duration_max
  
  return params
}

// ==================== 保存/加载筛选条件 ====================

/**
 * 保存筛选条件
 */
function handleSaveFilter() {
  saveFilterForm.name = ''
  saveFilterForm.description = ''
  saveFilterDialogVisible.value = true
}

/**
 * 确认保存筛选条件
 */
function confirmSaveFilter() {
  if (!saveFilterForm.name) {
    ElMessage.warning('请输入筛选条件名称')
    return
  }
  
  const filterData = {
    name: saveFilterForm.name,
    description: saveFilterForm.description,
    filters: { ...filterForm },
    quickTimeRange: quickTimeRange.value,
    createdAt: new Date().toISOString()
  }
  
  savedFilters.value.push(filterData)
  
  // 保存到本地存储
  localStorage.setItem('auditLogFilters', JSON.stringify(savedFilters.value))
  
  saveFilterDialogVisible.value = false
  ElMessage.success('筛选条件已保存')
}

/**
 * 加载保存的筛选条件
 * 
 * @param {number} index - 筛选条件索引
 */
function handleLoadSavedFilter(index) {
  const filterData = savedFilters.value[index]
  if (!filterData) return
  
  // 恢复筛选条件
  Object.assign(filterForm, filterData.filters)
  quickTimeRange.value = filterData.quickTimeRange || 'custom'
  
  handleApplyFilter()
  ElMessage.success(`已加载筛选条件: ${filterData.name}`)
}

// ==================== 格式化方法 ====================

/**
 * 格式化时间范围显示
 * 
 * @param {Array<string>} range - 时间范围
 * @returns {string} 格式化后的时间范围字符串
 */
function formatTimeRange(range) {
  if (!range || range.length !== 2) return ''
  const start = new Date(range[0]).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
  const end = new Date(range[1]).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
  return `${start} ~ ${end}`
}

/**
 * 获取用户名称
 * 
 * @param {string} userId - 用户ID
 * @returns {string} 用户名称
 */
function getUserName(userId) {
  const user = auditStore.userList.find(u => u.id === userId)
  return user?.name || userId
}

/**
 * 获取设备名称
 * 
 * @param {string} deviceId - 设备ID
 * @returns {string} 设备名称
 */
function getDeviceName(deviceId) {
  const device = auditStore.deviceList.find(d => d.id === deviceId)
  return device?.name || deviceId
}

/**
 * 获取分类名称
 * 
 * @param {string} category - 分类代码
 * @returns {string} 分类名称
 */
function getCategoryName(category) {
  const cat = auditStore.categories.find(c => c.code === category)
  return cat?.name || category
}

/**
 * 获取操作名称
 * 
 * @param {string} type - 操作类型
 * @returns {string} 操作描述
 */
function getOperationName(type) {
  const op = auditStore.operationTypes.find(o => o.type === type)
  return op?.description || type
}

/**
 * 获取状态名称
 * 
 * @param {number} status - 状态码
 * @returns {string} 状态名称
 */
function getStatusName(status) {
  const statusNames = {
    200: '成功 (2xx)',
    300: '重定向 (3xx)',
    400: '客户端错误 (4xx)',
    500: '服务器错误 (5xx)'
  }
  return statusNames[status] || `${status}`
}

// ==================== 生命周期 ====================

onMounted(() => {
  // 加载保存的筛选条件
  const saved = localStorage.getItem('auditLogFilters')
  if (saved) {
    try {
      savedFilters.value = JSON.parse(saved)
    } catch (e) {
      console.error('Failed to load saved filters:', e)
    }
  }
  
  // 初始化时间范围
  handleQuickTimeChange('today')
})
</script>

<style scoped>
.audit-log-filter {
  padding: var(--spacing-4);
  background-color: var(--color-surface-primary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
}

.quick-time-selector {
  margin-bottom: var(--spacing-4);
  padding-bottom: var(--spacing-4);
  border-bottom: 1px solid var(--color-border-secondary);
}

.filter-form {
  margin-bottom: 0;
}

.form-item {
  margin-bottom: var(--spacing-3);
}

.form-select,
.form-date-picker {
  width: 100%;
}

.range-input-group {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.range-input {
  flex: 1;
}

.range-separator {
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

.keyword-input {
  width: 100%;
}

.action-row {
  margin-top: var(--spacing-4);
  padding-top: var(--spacing-4);
  border-top: 1px solid var(--color-border-secondary);
}

.action-buttons {
  display: flex;
  gap: var(--spacing-2);
  flex-wrap: wrap;
}

.active-filters {
  margin-top: var(--spacing-4);
  padding-top: var(--spacing-4);
  border-top: 1px solid var(--color-border-secondary);
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-2);
  align-items: center;
}

.filter-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

.filter-tag {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: scale(0.9);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.save-filter-dialog {
  border-radius: var(--radius-lg);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .audit-log-filter {
    padding: var(--spacing-3);
  }

  .quick-time-selector {
    overflow-x: auto;
    white-space: nowrap;
  }

  .action-buttons {
    width: 100%;
  }

  .action-buttons .el-button {
    flex: 1;
    min-width: 0;
  }
}
</style>
