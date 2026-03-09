<template>
  <div class="error-handler-example">
    <el-card class="demo-card">
      <template #header>
        <div class="card-header">
          <el-icon><Warning /></el-icon>
          <span>错误处理系统示例</span>
        </div>
      </template>

      <div class="demo-content">
        <p class="demo-description">
          本示例展示如何使用错误处理系统，包括错误捕获、解决方案匹配、详情记录和一键复制功能。
        </p>

        <!-- 错误触发按钮 -->
        <div class="error-triggers">
          <h4>触发不同类型的错误</h4>
          <div class="trigger-buttons">
            <el-button
              type="primary"
              @click="triggerNetworkError"
            >
              网络错误
            </el-button>
            <el-button
              type="warning"
              @click="triggerDeviceError"
            >
              设备错误
            </el-button>
            <el-button
              type="danger"
              @click="triggerValidationError"
            >
              验证错误
            </el-button>
            <el-button
              type="info"
              @click="triggerTimeoutError"
            >
              超时错误
            </el-button>
            <el-button @click="triggerUnknownError">
              未知错误
            </el-button>
          </div>
        </div>

        <!-- 错误统计 -->
        <div
          v-if="errorStats.total > 0"
          class="error-stats"
        >
          <h4>错误统计</h4>
          <div class="stats-grid">
            <div class="stat-item">
              <span class="stat-label">总错误数:</span>
              <span class="stat-value">{{ errorStats.total }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">错误类型:</span>
              <div class="stat-tags">
                <el-tag
                  v-for="(count, type) in errorStats.byType"
                  :key="type"
                  size="small"
                  class="stat-tag"
                >
                  {{ getErrorTypeLabel(type) }}: {{ count }}
                </el-tag>
              </div>
            </div>
          </div>
        </div>

        <!-- 操作历史 -->
        <div class="action-recorder">
          <h4>操作记录</h4>
          <div class="action-buttons">
            <el-button
              size="small"
              @click="recordDemoAction('点击按钮')"
            >
              记录操作
            </el-button>
            <el-button
              size="small"
              @click="recordDemoAction('提交表单', { form: 'user-data' })"
            >
              记录带数据操作
            </el-button>
          </div>
        </div>

        <!-- 清理按钮 -->
        <div class="cleanup-actions">
          <el-button
            type="danger"
            plain
            @click="handleClearHistory"
          >
            清空错误历史
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 错误显示对话框 -->
    <ErrorDisplay
      v-model="errorVisible"
      :error-info="currentError"
      :is-generating-report="isGeneratingReport"
      @auto-action="handleAutoAction"
      @export-report="handleExportReport"
      @copy="handleCopy"
      @close="handleErrorClose"
    />
  </div>
</template>

<script setup>
/**
 * @file ErrorHandlerExample.vue
 * @path src/components/
 * @description 错误处理系统使用示例，展示如何集成和使用错误处理功能
 * @author Agent
 * @date 2024-03-07
 */

import { ref } from 'vue'
import { Warning } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ErrorDisplay from './ErrorDisplay.vue'
import { useErrorHandler } from '../composables/useErrorHandler'

/**
 * 使用错误处理组合式函数
 */
const {
  currentError,
  errorVisible,
  errorStats,
  handleError,
  clearError,
  clearHistory,
  recordAction,
  generateReport,
  copyErrorInfo,
  getErrorTypeLabel
} = useErrorHandler({
  enableHistory: true,
  enableAutoReport: false
})

/**
 * 是否正在生成报告
 */
const isGeneratingReport = ref(false)

/**
 * 触发网络错误
 */
function triggerNetworkError() {
  // 记录操作
  recordAction('触发网络错误测试')

  // 模拟网络错误
  const error = new Error('Failed to fetch: network error')
  error.name = 'NetworkError'

  // 处理错误
  handleError(error, {
    component: 'ErrorHandlerExample',
    action: '触发网络错误',
    userMessage: '网络连接失败，请检查网络设置'
  })
}

/**
 * 触发设备错误
 */
function triggerDeviceError() {
  recordAction('触发设备错误测试')

  const error = new Error('Serial port COM3: device not found')
  error.name = 'DeviceError'

  handleError(error, {
    component: 'ErrorHandlerExample',
    action: '触发设备错误',
    userMessage: '设备连接失败，请检查设备是否正确连接'
  })
}

/**
 * 触发验证错误
 */
function triggerValidationError() {
  recordAction('触发验证错误测试')

  const error = new Error('Validation error: parameter out of range')
  error.name = 'ValidationError'

  handleError(error, {
    component: 'ErrorHandlerExample',
    action: '触发验证错误',
    userMessage: '参数验证失败，请检查输入值',
    data: { field: 'temperature', value: 999, range: [0, 100] }
  })
}

/**
 * 触发超时错误
 */
function triggerTimeoutError() {
  recordAction('触发超时错误测试')

  const error = new Error('Request timeout after 30000ms')
  error.name = 'TimeoutError'

  handleError(error, {
    component: 'ErrorHandlerExample',
    action: '触发超时错误',
    userMessage: '操作超时，请稍后重试'
  })
}

/**
 * 触发未知错误
 */
function triggerUnknownError() {
  recordAction('触发未知错误测试')

  const error = new Error('Something went wrong unexpectedly')
  error.name = 'UnknownError'

  handleError(error, {
    component: 'ErrorHandlerExample',
    action: '触发未知错误',
    userMessage: '发生未知错误'
  })
}

/**
 * 记录演示操作
 *
 * @param {string} action - 操作名称
 * @param {Object} [data] - 操作数据
 */
function recordDemoAction(action, data = null) {
  recordAction(action, data)
  ElMessage.success(`已记录操作: ${action}`)
}

/**
 * 处理自动操作
 *
 * @param {string} action - 操作类型
 */
function handleAutoAction(action) {
  switch (action) {
    case 'retry':
      ElMessage.info('正在重试...')
      setTimeout(() => {
        ElMessage.success('重试成功')
        clearError()
      }, 1000)
      break

    case 'reconnect':
      ElMessage.info('正在重新连接...')
      setTimeout(() => {
        ElMessage.success('重新连接成功')
        clearError()
      }, 1500)
      break

    case 'refresh':
      ElMessage.info('正在刷新页面...')
      setTimeout(() => {
        window.location.reload()
      }, 500)
      break

    case 'relogin':
      ElMessage.warning('即将跳转到登录页面')
      setTimeout(() => {
        clearError()
      }, 1500)
      break

    case 'resetForm':
      ElMessage.success('表单已重置')
      clearError()
      break

    case 'scanDevices':
      ElMessage.info('正在扫描设备...')
      setTimeout(() => {
        ElMessage.success('扫描完成，发现 3 个设备')
      }, 2000)
      break

    default:
      ElMessage.info(`执行操作: ${action}`)
  }
}

/**
 * 处理导出报告
 *
 * @param {Object} errorInfo - 错误信息
 */
async function handleExportReport(errorInfo) {
  isGeneratingReport.value = true

  try {
    const report = generateReport(errorInfo)

    // 创建下载文件
    const blob = new Blob([JSON.stringify(report, null, 2)], {
      type: 'application/json'
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `error-report-${Date.now()}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)

    ElMessage.success('错误报告已导出')
  } catch (error) {
    ElMessage.error('导出失败: ' + error.message)
  } finally {
    isGeneratingReport.value = false
  }
}

/**
 * 处理复制操作
 *
 * @param {string} type - 复制类型
 */
async function handleCopy(type) {
  const success = await copyErrorInfo(type)
  if (success) {
    ElMessage.success('已复制到剪贴板')
  } else {
    ElMessage.error('复制失败')
  }
}

/**
 * 处理错误对话框关闭
 */
function handleErrorClose() {
  clearError()
}

/**
 * 清空错误历史
 */
async function handleClearHistory() {
  try {
    await ElMessageBox.confirm(
      '确定要清空所有错误历史记录吗？',
      '确认操作',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    clearHistory()
    ElMessage.success('错误历史已清空')
  } catch {
    // 用户取消
  }
}
</script>

<style scoped>
.error-handler-example {
  padding: var(--spacing-4);
}

.demo-card {
  border: 1px solid var(--color-border-primary);
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.demo-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-6);
}

.demo-description {
  margin: 0;
  padding: var(--spacing-3);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: var(--line-height-relaxed);
}

.error-triggers h4,
.error-stats h4,
.action-recorder h4 {
  margin: 0 0 var(--spacing-3) 0;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.trigger-buttons,
.action-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-2);
}

.error-stats {
  padding: var(--spacing-4);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
}

.stats-grid {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
}

.stat-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.stat-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.stat-value {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary-500);
}

.stat-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-2);
}

.stat-tag {
  font-size: var(--font-size-xs);
}

.action-recorder {
  padding: var(--spacing-4);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
}

.cleanup-actions {
  display: flex;
  justify-content: center;
  padding-top: var(--spacing-4);
  border-top: 1px solid var(--color-border-primary);
}

/* 响应式优化 */
@media (max-width: 768px) {
  .trigger-buttons,
  .action-buttons {
    flex-direction: column;
  }

  .trigger-buttons .el-button,
  .action-buttons .el-button {
    width: 100%;
  }
}
</style>
