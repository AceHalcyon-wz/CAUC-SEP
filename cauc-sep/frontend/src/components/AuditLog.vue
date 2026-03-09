<template>
  <div class="audit-log-enhanced">
    <!-- 标签页切换 -->
    <el-tabs v-model="activeTab" class="main-tabs" @tab-change="handleTabChange">
      <!-- 日志查询标签页 -->
      <el-tab-pane label="日志查询" name="query">
        <!-- 筛选组件 -->
        <AuditLogFilter
          @filter="handleFilter"
          @reset="handleFilterReset"
        />

        <!-- 操作工具栏 -->
        <div class="toolbar">
          <div class="toolbar-left">
            <el-checkbox v-model="selectAll" @change="handleSelectAll">
              全选
            </el-checkbox>
            <el-button
              v-if="selectedLogs.length > 0"
              type="danger"
              size="small"
              @click="handleBulkDelete"
            >
              批量删除 ({{ selectedLogs.length }})
            </el-button>
          </div>
          <div class="toolbar-right">
            <el-button @click="handleRefresh" size="small">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button @click="showCleanupDialog = true" size="small">
              <el-icon><Delete /></el-icon>
              清理策略
            </el-button>
            <el-dropdown @command="handleExportCommand">
              <el-button type="primary" size="small">
                <el-icon><Download /></el-icon>
                导出
                <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="csv">导出为 CSV</el-dropdown-item>
                  <el-dropdown-item command="excel">导出为 Excel</el-dropdown-item>
                  <el-dropdown-item command="pdf">导出为 PDF</el-dropdown-item>
                  <el-dropdown-item command="json">导出为 JSON</el-dropdown-item>
                  <el-dropdown-item divided command="config">导出配置</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button @click="handlePrint" size="small">
              <el-icon><Printer /></el-icon>
              打印
            </el-button>
          </div>
        </div>

        <!-- 日志列表 -->
        <el-card class="log-list-card">
          <!-- 错误提示 -->
          <el-alert
            v-if="auditStore.errorMessage"
            :title="auditStore.errorMessage"
            type="error"
            :closable="true"
            @close="auditStore.clearError"
            class="error-alert"
          />

          <!-- 空数据状态提示 -->
          <el-empty
            v-if="!auditStore.loading && auditStore.logList.length === 0 && !auditStore.errorMessage"
            :image-size="200"
            description="暂无审计日志数据"
          >
            <template #description>
              <div class="empty-description">
                <p class="empty-title">暂无审计日志数据</p>
                <p class="empty-hint">可能的原因：</p>
                <ul class="empty-reasons">
                  <li>系统尚未记录任何操作日志</li>
                  <li>当前筛选条件过滤掉了所有日志</li>
                  <li>日志已被清理策略自动清理</li>
                </ul>
                <el-button type="primary" @click="handleFilterReset" class="empty-action">
                  重置筛选条件
                </el-button>
              </div>
            </template>
          </el-empty>

          <!-- 日志表格 -->
          <el-table
            v-else
            ref="logTableRef"
            :data="auditStore.logList"
            v-loading="auditStore.loading"
            stripe
            class="log-table"
            @selection-change="handleSelectionChange"
            @row-click="handleRowClick"
          >
            <el-table-column type="selection" width="55" />

            <el-table-column prop="timestamp" label="时间" width="180">
              <template #default="{ row }">
                <div class="timestamp-cell">
                  <el-icon class="time-icon"><Clock /></el-icon>
                  <span>{{ formatTime(row.timestamp) }}</span>
                </div>
              </template>
            </el-table-column>

            <el-table-column prop="user_id" label="用户" width="120">
              <template #default="{ row }">
                <el-tag size="small" v-if="row.user_id" class="user-tag">
                  {{ getUserName(row.user_id) }}
                </el-tag>
                <span v-else class="empty-cell">-</span>
              </template>
            </el-table-column>

            <el-table-column prop="device_id" label="设备" width="120">
              <template #default="{ row }">
                <el-tag size="small" v-if="row.device_id" class="device-tag">
                  {{ getDeviceName(row.device_id) }}
                </el-tag>
                <span v-else class="empty-cell">-</span>
              </template>
            </el-table-column>

            <el-table-column prop="operation_category" label="分类" width="100">
              <template #default="{ row }">
                <el-tag :type="getCategoryType(row.operation_category)" size="small" class="category-tag">
                  {{ getCategoryName(row.operation_category) }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column prop="operation_type" label="操作类型" width="150">
              <template #default="{ row }">
                <span class="operation-text">{{ getOperationName(row.operation_type) }}</span>
              </template>
            </el-table-column>

            <el-table-column prop="request_method" label="方法" width="80">
              <template #default="{ row }">
                <el-tag :type="getMethodType(row.request_method)" size="small" class="method-tag">
                  {{ row.request_method }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column prop="request_path" label="路径" min-width="200" show-overflow-tooltip>
              <template #default="{ row }">
                <span class="path-text">{{ row.request_path }}</span>
              </template>
            </el-table-column>

            <el-table-column prop="response_status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.response_status)" size="small" class="status-tag">
                  {{ row.response_status || '-' }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column prop="duration_ms" label="耗时" width="100">
              <template #default="{ row }">
                <span class="duration-text">{{ row.duration_ms ? `${row.duration_ms}ms` : '-' }}</span>
              </template>
            </el-table-column>

            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click.stop="handleViewDetail(row)" class="detail-btn">
                  详情
                </el-button>
                <el-button type="danger" link size="small" @click.stop="handleDeleteLog(row)" class="delete-btn">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- 分页 -->
          <div class="pagination-container">
            <el-pagination
              v-model:current-page="currentPage"
              v-model:page-size="currentPageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="auditStore.pagination.total"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handlePageSizeChange"
              @current-change="handlePageChange"
            />
          </div>
        </el-card>
      </el-tab-pane>

      <!-- 统计分析标签页 -->
      <el-tab-pane label="统计分析" name="stats">
        <AuditLogStats />
      </el-tab-pane>
    </el-tabs>

    <!-- 详情对话框 -->
    <el-dialog
      v-model="detailVisible"
      title="日志详情"
      width="700px"
      destroy-on-close
      class="detail-dialog"
    >
      <el-descriptions :column="2" border v-if="currentLog" class="detail-descriptions">
        <el-descriptions-item label="日志ID">
          <span class="mono-text">{{ currentLog.id }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="时间">{{ formatTime(currentLog.timestamp) }}</el-descriptions-item>
        <el-descriptions-item label="用户ID">{{ currentLog.user_id || '-' }}</el-descriptions-item>
        <el-descriptions-item label="设备ID">{{ currentLog.device_id || '-' }}</el-descriptions-item>
        <el-descriptions-item label="操作分类">{{ getCategoryName(currentLog.operation_category) }}</el-descriptions-item>
        <el-descriptions-item label="操作类型">{{ getOperationName(currentLog.operation_type) }}</el-descriptions-item>
        <el-descriptions-item label="请求方法">{{ currentLog.request_method }}</el-descriptions-item>
        <el-descriptions-item label="响应状态">{{ currentLog.response_status || '-' }}</el-descriptions-item>
        <el-descriptions-item label="请求路径" :span="2">
          <span class="mono-text">{{ currentLog.request_path }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="IP地址">{{ currentLog.ip_address || '-' }}</el-descriptions-item>
        <el-descriptions-item label="处理耗时">{{ currentLog.duration_ms ? `${currentLog.duration_ms}ms` : '-' }}</el-descriptions-item>
        <el-descriptions-item label="用户代理" :span="2">{{ currentLog.user_agent || '-' }}</el-descriptions-item>
        <el-descriptions-item label="响应消息" :span="2">{{ currentLog.response_message || '-' }}</el-descriptions-item>
      </el-descriptions>

      <div class="params-section" v-if="currentLog?.request_params">
        <h4>请求参数</h4>
        <pre class="params-content">{{ JSON.stringify(currentLog.request_params, null, 2) }}</pre>
      </div>

      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button type="primary" @click="handleExportDetail">
          <el-icon><Download /></el-icon>
          导出
        </el-button>
      </template>
    </el-dialog>

    <!-- 清理策略配置对话框 -->
    <el-dialog
      v-model="showCleanupDialog"
      title="日志清理策略配置"
      width="600px"
      class="cleanup-dialog"
      destroy-on-close
    >
      <el-form :model="cleanupForm" label-width="120px" class="cleanup-form">
        <el-form-item label="启用自动清理">
          <el-switch v-model="cleanupForm.enabled" />
        </el-form-item>

        <el-form-item label="保留时间" v-if="cleanupForm.enabled">
          <el-input-number
            v-model="cleanupForm.retention_days"
            :min="7"
            :max="365"
            :step="1"
          />
          <span class="form-hint">天（超过此时间的日志将被清理）</span>
        </el-form-item>

        <el-form-item label="清理周期" v-if="cleanupForm.enabled">
          <el-select v-model="cleanupForm.cleanup_interval" class="form-select">
            <el-option label="每天" value="daily" />
            <el-option label="每周" value="weekly" />
            <el-option label="每月" value="monthly" />
          </el-select>
        </el-form-item>

        <el-form-item label="保留重要日志" v-if="cleanupForm.enabled">
          <el-switch v-model="cleanupForm.keep_important" />
          <span class="form-hint">保留标记为重要的日志</span>
        </el-form-item>

        <el-divider />

        <el-form-item label="手动清理">
          <div class="manual-cleanup">
            <el-input-number
              v-model="manualCleanupDays"
              :min="1"
              :max="365"
              placeholder="天数"
            />
            <span class="form-hint">天前的日志</span>
            <el-button type="danger" @click="handleManualCleanup" :loading="cleanupLoading">
              立即清理
            </el-button>
          </div>
        </el-form-item>

        <el-form-item label="清理预览">
          <el-button @click="handlePreviewCleanup" :loading="previewLoading">
            查看预览
          </el-button>
          <div v-if="cleanupPreview" class="preview-result">
            <p>将清理 <strong>{{ cleanupPreview.count }}</strong> 条日志</p>
            <p>释放空间约 <strong>{{ formatBytes(cleanupPreview.size) }}</strong></p>
            <p>最早日志时间: {{ formatTime(cleanupPreview.earliest) }}</p>
          </div>
        </el-form-item>

        <el-form-item label="上次清理时间" v-if="auditStore.cleanupConfig.last_cleanup_time">
          <span>{{ formatTime(auditStore.cleanupConfig.last_cleanup_time) }}</span>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCleanupDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSaveCleanupConfig" :loading="savingConfig">
          保存配置
        </el-button>
      </template>
    </el-dialog>

    <!-- 导出配置对话框 -->
    <el-dialog
      v-model="showExportDialog"
      title="导出配置"
      width="500px"
      class="export-dialog"
      destroy-on-close
    >
      <el-form :model="exportForm" label-width="100px" class="export-form">
        <el-form-item label="导出格式">
          <el-radio-group v-model="exportForm.format">
            <el-radio label="csv">CSV</el-radio>
            <el-radio label="excel">Excel</el-radio>
            <el-radio label="pdf">PDF</el-radio>
            <el-radio label="json">JSON</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="包含详情">
          <el-switch v-model="exportForm.include_details" />
        </el-form-item>

        <el-form-item label="包含参数">
          <el-switch v-model="exportForm.include_params" />
        </el-form-item>

        <el-form-item label="日期格式">
          <el-select v-model="exportForm.date_format" class="form-select">
            <el-option label="YYYY-MM-DD HH:mm:ss" value="YYYY-MM-DD HH:mm:ss" />
            <el-option label="YYYY/MM/DD HH:mm:ss" value="YYYY/MM/DD HH:mm:ss" />
            <el-option label="MM/DD/YYYY HH:mm:ss" value="MM/DD/YYYY HH:mm:ss" />
          </el-select>
        </el-form-item>

        <el-form-item label="时区">
          <el-select v-model="exportForm.timezone" class="form-select">
            <el-option label="本地时间" value="local" />
            <el-option label="UTC" value="utc" />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showExportDialog = false">取消</el-button>
        <el-button type="primary" @click="handleConfirmExport" :loading="exporting">
          确认导出
        </el-button>
      </template>
    </el-dialog>

    <!-- 打印预览 -->
    <div v-if="printMode" class="print-container">
      <div class="print-header">
        <h1>审计日志报告</h1>
        <p>生成时间: {{ new Date().toLocaleString('zh-CN') }}</p>
      </div>
      <el-table :data="printData" border style="width: 100%">
        <el-table-column prop="timestamp" label="时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.timestamp) }}
          </template>
        </el-table-column>
        <el-table-column prop="user_id" label="用户" width="100" />
        <el-table-column prop="device_id" label="设备" width="100" />
        <el-table-column prop="operation_type" label="操作类型" width="150" />
        <el-table-column prop="request_path" label="路径" />
        <el-table-column prop="response_status" label="状态" width="80" />
        <el-table-column prop="duration_ms" label="耗时(ms)" width="100" />
      </el-table>
    </div>
  </div>
</template>

<script setup>
/**
 * @file AuditLog.vue (Enhanced)
 * @path src/components/
 * @description 增强版审计日志管理组件，集成筛选、统计、导出、打印、清理策略等功能
 * @author Frontend Engineer Agent
 * @date 2026-03-07
 * @dependencies vue, element-plus, stores/audit, components/AuditLogFilter, components/AuditLogStats
 */

import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuditStore } from '../stores/audit'
import AuditLogFilter from './AuditLogFilter.vue'
import AuditLogStats from './AuditLogStats.vue'

// ==================== Store 实例 ====================

const auditStore = useAuditStore()

// ==================== 本地状态 ====================

/** 当前标签页 */
const activeTab = ref('query')

/** 详情对话框可见性 */
const detailVisible = ref(false)

/** 当前查看的日志详情 */
const currentLog = ref(null)

/** 选中的日志列表 */
const selectedLogs = ref([])

/** 全选状态 */
const selectAll = ref(false)

/** 表格引用 */
const logTableRef = ref(null)

/** 清理策略对话框 */
const showCleanupDialog = ref(false)
const cleanupForm = reactive({
  enabled: false,
  retention_days: 90,
  cleanup_interval: 'weekly',
  keep_important: true
})
const manualCleanupDays = ref(90)
const cleanupPreview = ref(null)
const cleanupLoading = ref(false)
const previewLoading = ref(false)
const savingConfig = ref(false)

/** 导出配置对话框 */
const showExportDialog = ref(false)
const exportForm = reactive({
  format: 'csv',
  include_details: true,
  include_params: false,
  date_format: 'YYYY-MM-DD HH:mm:ss',
  timezone: 'local'
})
const exporting = ref(false)

/** 打印模式 */
const printMode = ref(false)
const printData = ref([])

// ==================== 计算属性 ====================

/** 当前页码（双向绑定） */
const currentPage = computed({
  get: () => auditStore.pagination.page,
  set: (val) => { auditStore.pagination.page = val }
})

/** 每页数量（双向绑定） */
const currentPageSize = computed({
  get: () => auditStore.pagination.pageSize,
  set: (val) => { auditStore.pagination.pageSize = val }
})

// ==================== 格式化与辅助方法 ====================

/**
 * 格式化时间
 * 
 * @param {string} timestamp - 时间戳
 * @returns {string} 格式化后的时间字符串
 */
function formatTime(timestamp) {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

/**
 * 格式化字节数
 * 
 * @param {number} bytes - 字节数
 * @returns {string} 格式化后的字符串
 */
function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
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
 * @param {string} category - 分类标识
 * @returns {string} 分类名称
 */
function getCategoryName(category) {
  const cat = auditStore.categories.find(c => c.code === category)
  return cat?.name || category
}

/**
 * 获取分类标签类型
 * 
 * @param {string} category - 分类标识
 * @returns {string} Element Plus Tag类型
 */
function getCategoryType(category) {
  const categoryTypes = {
    device: 'primary',
    motion_control: 'success',
    safety: 'danger',
    parameter: 'warning',
    calibration: 'info',
    experiment: '',
    query: '',
    motor: 'success',
    analysis: 'info',
    general: '',
  }
  return categoryTypes[category] || ''
}

/**
 * 获取操作名称
 * 
 * @param {string} type - 操作类型
 * @returns {string} 操作描述名称
 */
function getOperationName(type) {
  const op = auditStore.operationTypes.find(o => o.type === type)
  return op ? op.description : type
}

/**
 * 获取请求方法标签类型
 * 
 * @param {string} method - HTTP方法
 * @returns {string} Element Plus Tag类型
 */
function getMethodType(method) {
  const methodTypes = {
    GET: 'success',
    POST: 'primary',
    PUT: 'warning',
    DELETE: 'danger',
    EVENT: 'info',
  }
  return methodTypes[method] || ''
}

/**
 * 获取状态标签类型
 * 
 * @param {number} status - HTTP状态码
 * @returns {string} Element Plus Tag类型
 */
function getStatusType(status) {
  if (!status) return 'info'
  if (status >= 200 && status < 300) return 'success'
  if (status >= 400 && status < 500) return 'warning'
  if (status >= 500) return 'danger'
  return 'info'
}

// ==================== 事件处理方法 ====================

/**
 * 标签页切换处理
 * 
 * @param {string} tab - 标签页名称
 */
function handleTabChange(tab) {
  if (tab === 'stats') {
    // 切换到统计页面时刷新统计数据
    auditStore.fetchStatistics()
  }
}

/**
 * 筛选处理
 * 
 * @param {Object} filters - 筛选条件
 */
async function handleFilter(filters) {
  auditStore.setFilters(filters)
  await auditStore.fetchLogs()
  
  if (auditStore.errorMessage) {
    ElMessage.error(auditStore.errorMessage)
  }
}

/**
 * 筛选重置处理
 */
async function handleFilterReset() {
  await auditStore.resetFilters()
}

/**
 * 刷新日志列表
 */
function handleRefresh() {
  auditStore.fetchLogs()
  auditStore.fetchStatistics()
}

/**
 * 页码变更处理
 * 
 * @param {number} page - 新页码
 */
async function handlePageChange(page) {
  await auditStore.goToPage(page)
}

/**
 * 每页数量变更处理
 * 
 * @param {number} pageSize - 新的每页数量
 */
async function handlePageSizeChange(pageSize) {
  await auditStore.setPageSize(pageSize)
}

/**
 * 表格选择变更处理
 * 
 * @param {Array} selection - 选中的行数据
 */
function handleSelectionChange(selection) {
  selectedLogs.value = selection
  selectAll.value = selection.length === auditStore.logList.length
}

/**
 * 全选处理
 * 
 * @param {boolean} val - 全选状态
 */
function handleSelectAll(val) {
  if (val) {
    logTableRef.value?.toggleAllSelection()
  } else {
    logTableRef.value?.clearSelection()
  }
}

/**
 * 表格行点击处理
 * 
 * @param {Object} row - 日志行数据
 */
function handleRowClick(row) {
  handleViewDetail(row)
}

/**
 * 查看日志详情
 * 
 * @param {Object} row - 日志行数据
 */
function handleViewDetail(row) {
  currentLog.value = row
  detailVisible.value = true
}

/**
 * 删除单条日志
 * 
 * @param {Object} row - 日志行数据
 */
async function handleDeleteLog(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除此日志记录吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const result = await auditStore.deleteLog(row.id)
    if (result) {
      ElMessage.success('日志删除成功')
    } else if (auditStore.errorMessage) {
      ElMessage.error(auditStore.errorMessage)
    }
  } catch (error) {
    // 用户取消操作
  }
}

/**
 * 批量删除日志
 */
async function handleBulkDelete() {
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedLogs.value.length} 条日志记录吗？`,
      '确认批量删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const logIds = selectedLogs.value.map(log => log.id)
    const result = await auditStore.bulkDeleteLogs(logIds)
    
    if (result) {
      ElMessage.success(`成功删除 ${result.deleted_count || selectedLogs.value.length} 条日志`)
      selectedLogs.value = []
      selectAll.value = false
    } else if (auditStore.errorMessage) {
      ElMessage.error(auditStore.errorMessage)
    }
  } catch (error) {
    // 用户取消操作
  }
}

// ==================== 导出功能 ====================

/**
 * 导出命令处理
 * 
 * @param {string} command - 导出命令
 */
function handleExportCommand(command) {
  if (command === 'config') {
    showExportDialog.value = true
  } else {
    exportForm.format = command
    handleExport()
  }
}

/**
 * 导出日志
 */
async function handleExport() {
  exporting.value = true
  
  try {
    const params = {
      format: exportForm.format,
      include_details: exportForm.include_details,
      include_params: exportForm.include_params,
      date_format: exportForm.date_format,
      timezone: exportForm.timezone
    }

    // 如果有选中的日志，只导出选中的
    if (selectedLogs.value.length > 0) {
      params.log_ids = selectedLogs.value.map(log => log.id)
    }

    const result = await auditStore.exportLogs(params)
    
    if (result) {
      downloadFile(result, `audit_logs_${Date.now()}.${exportForm.format}`, getMimeType(exportForm.format))
      ElMessage.success('日志导出成功')
    } else if (auditStore.errorMessage) {
      ElMessage.error(auditStore.errorMessage)
    }
  } catch (error) {
    console.error('Export failed:', error)
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

/**
 * 确认导出
 */
async function handleConfirmExport() {
  await handleExport()
  showExportDialog.value = false
}

/**
 * 导出详情
 */
async function handleExportDetail() {
  if (!currentLog.value) return
  
  const result = await auditStore.exportLogs({
    format: 'json',
    log_ids: [currentLog.value.id],
    include_details: true,
    include_params: true
  })
  
  if (result) {
    downloadFile(result, `log_detail_${currentLog.value.id}.json`, 'application/json')
    ElMessage.success('详情导出成功')
  }
}

/**
 * 获取MIME类型
 * 
 * @param {string} format - 文件格式
 * @returns {string} MIME类型
 */
function getMimeType(format) {
  const mimeTypes = {
    csv: 'text/csv',
    excel: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    pdf: 'application/pdf',
    json: 'application/json'
  }
  return mimeTypes[format] || 'application/octet-stream'
}

/**
 * 下载文件
 * 
 * @param {Blob|string} content - 文件内容
 * @param {string} filename - 文件名
 * @param {string} mimeType - MIME类型
 */
function downloadFile(content, filename, mimeType) {
  const blob = content instanceof Blob ? content : new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

// ==================== 打印功能 ====================

/**
 * 打印处理
 */
function handlePrint() {
  printData.value = [...auditStore.logList]
  
  // 使用打印预览
  const printWindow = window.open('', '_blank')
  printWindow.document.write(`
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="UTF-8">
        <title>审计日志报告</title>
        <style>
          body {
            font-family: Arial, sans-serif;
            padding: 20px;
          }
          .header {
            text-align: center;
            margin-bottom: 30px;
          }
          .header h1 {
            margin: 0;
            color: #333;
          }
          .header p {
            color: #666;
            margin-top: 10px;
          }
          table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
          }
          th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
          }
          th {
            background-color: #f5f7fa;
            font-weight: bold;
          }
          tr:nth-child(even) {
            background-color: #f9f9f9;
          }
          .footer {
            margin-top: 30px;
            text-align: center;
            color: #999;
            font-size: 12px;
          }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>审计日志报告</h1>
          <p>生成时间: ${new Date().toLocaleString('zh-CN')}</p>
        </div>
        <table>
          <thead>
            <tr>
              <th>时间</th>
              <th>用户</th>
              <th>设备</th>
              <th>操作类型</th>
              <th>路径</th>
              <th>状态</th>
              <th>耗时</th>
            </tr>
          </thead>
          <tbody>
            ${printData.value.map(log => `
              <tr>
                <td>${formatTime(log.timestamp)}</td>
                <td>${log.user_id || '-'}</td>
                <td>${log.device_id || '-'}</td>
                <td>${getOperationName(log.operation_type)}</td>
                <td>${log.request_path}</td>
                <td>${log.response_status || '-'}</td>
                <td>${log.duration_ms ? log.duration_ms + 'ms' : '-'}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
        <div class="footer">
          <p>共 ${printData.value.length} 条记录</p>
        </div>
      </body>
    </html>
  `)
  printWindow.document.close()
  printWindow.print()
}

// ==================== 清理策略功能 ====================

/**
 * 手动清理
 */
async function handleManualCleanup() {
  try {
    await ElMessageBox.confirm(
      `确定要清理 ${manualCleanupDays.value} 天前的日志吗？此操作不可恢复。`,
      '确认清理',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    cleanupLoading.value = true
    
    const result = await auditStore.executeCleanup({
      older_than_days: manualCleanupDays.value,
      keep_important: cleanupForm.keep_important
    })

    if (result) {
      ElMessage.success(`成功清理 ${result.deleted_count || 0} 条日志`)
      cleanupPreview.value = null
      await auditStore.fetchLogs()
    } else if (auditStore.errorMessage) {
      ElMessage.error(auditStore.errorMessage)
    }
  } catch (error) {
    // 用户取消操作
  } finally {
    cleanupLoading.value = false
  }
}

/**
 * 清理预览
 */
async function handlePreviewCleanup() {
  previewLoading.value = true
  
  try {
    const result = await auditStore.getCleanupPreview({
      older_than_days: manualCleanupDays.value,
      keep_important: cleanupForm.keep_important
    })

    if (result) {
      cleanupPreview.value = result
    } else {
      ElMessage.warning('无法获取清理预览')
    }
  } catch (error) {
    console.error('Failed to get cleanup preview:', error)
    ElMessage.error('获取清理预览失败')
  } finally {
    previewLoading.value = false
  }
}

/**
 * 保存清理配置
 */
async function handleSaveCleanupConfig() {
  savingConfig.value = true
  
  try {
    const result = await auditStore.updateCleanupConfig(cleanupForm)
    
    if (result) {
      ElMessage.success('清理策略配置已保存')
      showCleanupDialog.value = false
    } else if (auditStore.errorMessage) {
      ElMessage.error(auditStore.errorMessage)
    }
  } catch (error) {
    console.error('Failed to save cleanup config:', error)
    ElMessage.error('保存配置失败')
  } finally {
    savingConfig.value = false
  }
}

// ==================== 生命周期 ====================

onMounted(async () => {
  try {
    // 初始化Store
    await auditStore.init()
    
    // 同步清理配置
    Object.assign(cleanupForm, auditStore.cleanupConfig)
  } catch (error) {
    console.error('[AuditLog] Initialization failed:', error)
    ElMessage.error('审计日志组件初始化失败，请刷新页面重试')
  }
})

onUnmounted(() => {
  // 清理Store资源
  auditStore.cleanup()
})
</script>

<style scoped>
.audit-log-enhanced {
  padding: var(--spacing-4);
  background-color: var(--color-bg-primary);
  min-height: 100vh;
}

.main-tabs {
  background-color: var(--color-surface-primary);
  border-radius: var(--radius-lg);
  padding: var(--spacing-4);
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: var(--spacing-4) 0;
  padding: var(--spacing-3);
  background-color: var(--color-surface-secondary);
  border-radius: var(--radius-md);
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.log-list-card {
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
}

.error-alert {
  margin-bottom: var(--spacing-4);
}

.empty-description {
  text-align: center;
  padding: var(--spacing-4);
}

.empty-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-3);
}

.empty-hint {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-2);
}

.empty-reasons {
  text-align: left;
  display: inline-block;
  margin: 0 auto var(--spacing-4);
  padding-left: var(--spacing-6);
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-relaxed);
}

.empty-reasons li {
  margin-bottom: var(--spacing-1);
}

.empty-action {
  margin-top: var(--spacing-3);
}

.log-table {
  font-size: var(--font-size-sm);
}

.timestamp-cell {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-family: var(--font-family-mono);
  font-size: var(--font-size-xs);
}

.time-icon {
  color: var(--color-text-tertiary);
}

.user-tag,
.device-tag,
.category-tag,
.method-tag,
.status-tag {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-xs);
  border-radius: var(--radius-sm);
}

.operation-text,
.path-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.path-text {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-xs);
}

.duration-text {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.empty-cell {
  color: var(--color-text-disabled);
}

.detail-btn,
.delete-btn {
  transition: var(--transition-all);
}

.detail-btn:hover {
  transform: translateX(4px);
}

.pagination-container {
  margin-top: var(--spacing-4);
  display: flex;
  justify-content: flex-end;
}

.detail-dialog {
  border-radius: var(--radius-lg);
}

.detail-descriptions {
  margin-bottom: var(--spacing-4);
}

.mono-text {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-sm);
}

.params-section {
  margin-top: var(--spacing-4);
}

.params-section h4 {
  margin-bottom: var(--spacing-3);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
}

.params-content {
  background-color: var(--color-surface-secondary);
  padding: var(--spacing-4);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-family: var(--font-family-mono);
  max-height: 300px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  border: 1px solid var(--color-border-primary);
}

.cleanup-dialog,
.export-dialog {
  border-radius: var(--radius-lg);
}

.cleanup-form,
.export-form {
  margin-bottom: 0;
}

.form-select {
  width: 100%;
}

.form-hint {
  margin-left: var(--spacing-2);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.manual-cleanup {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.preview-result {
  margin-top: var(--spacing-3);
  padding: var(--spacing-3);
  background-color: var(--color-surface-secondary);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
}

.preview-result p {
  margin: var(--spacing-1) 0;
}

.print-container {
  display: none;
}

@media print {
  .print-container {
    display: block;
  }
}

/* Element Plus 样式覆盖 */
:deep(.el-tabs__header) {
  margin-bottom: var(--spacing-4);
}

:deep(.el-tabs__item) {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
}

:deep(.el-tabs__item.is-active) {
  font-weight: var(--font-weight-semibold);
}

:deep(.el-card__header) {
  background-color: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border-primary);
  font-weight: var(--font-weight-semibold);
}

:deep(.el-table) {
  font-size: var(--font-size-sm);
  background-color: var(--color-surface-primary);
}

:deep(.el-table th.el-table__cell) {
  background-color: var(--color-bg-secondary);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
}

:deep(.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell) {
  background-color: var(--color-bg-secondary);
}

:deep(.el-table__row) {
  cursor: pointer;
  transition: var(--transition-all);
}

:deep(.el-table__row:hover) {
  background-color: var(--color-interactive-hover) !important;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .audit-log-enhanced {
    padding: var(--spacing-2);
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-2);
  }

  .page-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .toolbar {
    flex-direction: column;
    gap: var(--spacing-2);
  }

  .toolbar-left,
  .toolbar-right {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
