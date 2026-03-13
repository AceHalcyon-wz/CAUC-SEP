<template>
  <el-card class="history-panel-card">
    <template #header>
      <div class="card-header">
        <div class="header-left">
          <el-icon class="header-icon">
            <Clock />
          </el-icon>
          <span class="header-title">运动历史</span>
          <el-tag
            type="info"
            size="small"
          >
            {{ motorStore.movementHistory.length }} 条记录
          </el-tag>
        </div>
        <div class="header-actions">
          <el-button
            type="primary"
            size="small"
            :icon="Download"
            :disabled="motorStore.movementHistory.length === 0"
            @click="exportHistory"
          >
            导出
          </el-button>
          <el-popconfirm
            title="确定要清空所有历史记录吗？"
            confirm-button-text="确定"
            cancel-button-text="取消"
            @confirm="clearHistory"
          >
            <template #reference>
              <el-button
                type="danger"
                size="small"
                :icon="Delete"
                :disabled="motorStore.movementHistory.length === 0"
              >
                清空
              </el-button>
            </template>
          </el-popconfirm>
        </div>
      </div>
    </template>

    <div class="history-content">
      <!-- 历史记录列表 -->
      <div
        v-if="motorStore.movementHistory.length > 0"
        class="history-list"
      >
        <el-scrollbar max-height="400px">
          <div
            v-for="record in motorStore.movementHistory"
            :key="record.id"
            class="history-item"
            :class="{ 'history-error': !record.success }"
          >
            <div class="history-header">
              <div class="history-type">
                <el-tag
                  :type="getTypeTagType(record.type)"
                  size="small"
                  effect="plain"
                >
                  {{ getTypeLabel(record.type) }}
                </el-tag>
                <el-tag
                  v-if="!record.success"
                  type="danger"
                  size="small"
                  effect="plain"
                >
                  失败
                </el-tag>
              </div>
              <div class="history-time">
                {{ formatTime(record.timestamp) }}
              </div>
            </div>

            <div class="history-details">
              <div class="detail-row">
                <span class="detail-label">
                  <el-icon><Location /></el-icon>
                  起始位置:
                </span>
                <span class="detail-value">{{ record.startPosition.toFixed(3) }} mm</span>
              </div>

              <div
                v-if="record.targetPosition !== undefined"
                class="detail-row"
              >
                <span class="detail-label">
                  <el-icon><Aim /></el-icon>
                  目标位置:
                </span>
                <span class="detail-value">{{ record.targetPosition.toFixed(3) }} mm</span>
              </div>

              <div
                v-if="record.velocity"
                class="detail-row"
              >
                <span class="detail-label">
                  <el-icon><Odometer /></el-icon>
                  运动速度:
                </span>
                <span class="detail-value">{{ record.velocity.toFixed(1) }} mm/s</span>
              </div>

              <div
                v-if="!record.success && record.errorMessage"
                class="detail-row error-message"
              >
                <span class="detail-label">
                  <el-icon><Warning /></el-icon>
                  错误信息:
                </span>
                <span class="detail-value">{{ record.errorMessage }}</span>
              </div>
            </div>

            <div class="history-actions">
              <el-button
                v-if="record.targetPosition !== undefined && record.success"
                type="primary"
                size="small"
                text
                :disabled="!motorStore.canControl"
                @click="replayMovement(record)"
              >
                <el-icon><VideoPlay /></el-icon>
                重放
              </el-button>
            </div>
          </div>
        </el-scrollbar>
      </div>

      <!-- 空状态 -->
      <el-empty
        v-else
        description="暂无运动历史记录"
        :image-size="120"
        class="empty-state"
      />
    </div>

    <!-- 导出对话框 -->
    <el-dialog
      v-model="exportDialogVisible"
      title="导出历史记录"
      width="600px"
    >
      <div class="export-content">
        <el-input
          v-model="exportData"
          type="textarea"
          :rows="15"
          readonly
        />
      </div>
      <template #footer>
        <el-button @click="exportDialogVisible = false">
          关闭
        </el-button>
        <el-button
          type="primary"
          @click="copyToClipboard"
        >
          复制到剪贴板
        </el-button>
        <el-button
          type="success"
          @click="downloadAsFile"
        >
          下载文件
        </el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
/**
 * @file MotorHistoryPanel.vue
 * @path src/components/
 * @description 电机运动历史记录面板，显示所有运动操作历史并支持回放和导出
 * @author Agent
 * @date 2024-03-07
 */

import { ref } from 'vue'
import { useMotorStore } from '@/stores/motor'
import { ElMessage } from 'element-plus'
import {
  Clock,
  Download,
  Delete,
  VideoPlay,
  Location,
  Aim,
  Odometer,
  Warning
} from '@element-plus/icons-vue'

const motorStore = useMotorStore()

// ============ 响应式状态 ============

/** 导出对话框显示状态 */
const exportDialogVisible = ref(false)

/** 导出数据 */
const exportData = ref('')

// ============ 方法 ============

/**
 * 获取运动类型标签
 * 
 * @param {string} type - 运动类型
 * @returns {string} 类型标签
 */
function getTypeLabel(type) {
  const labels = {
    absolute: '绝对定位',
    jog: 'JOG运动',
    home: '回零',
    emergency: '急停',
    unknown: '未知'
  }
  return labels[type] || type
}

/**
 * 获取运动类型标签样式
 * 
 * @param {string} type - 运动类型
 * @returns {string} 标签类型
 */
function getTypeTagType(type) {
  const types = {
    absolute: 'primary',
    jog: 'warning',
    home: 'success',
    emergency: 'danger',
    unknown: 'info'
  }
  return types[type] || 'info'
}

/**
 * 格式化时间
 * 
 * @param {string} timestamp - ISO时间戳
 * @returns {string} 格式化后的时间
 */
function formatTime(timestamp) {
  const date = new Date(timestamp)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

/**
 * 重放运动
 * 
 * @param {Object} record - 历史记录
 */
async function replayMovement(record) {
  if (!motorStore.canControl) {
    ElMessage.warning('电机未就绪，无法重放')
    return
  }

  if (record.targetPosition === undefined) {
    ElMessage.warning('该记录无法重放')
    return
  }

  const success = await motorStore.moveAbsolute(
    record.targetPosition,
    record.velocity || 10
  )

  if (success) {
    ElMessage.success('重放指令已发送')
  }
}

/**
 * 导出历史记录
 */
function exportHistory() {
  exportData.value = motorStore.exportMovementHistory()
  exportDialogVisible.value = true
}

/**
 * 复制到剪贴板
 */
async function copyToClipboard() {
  try {
    await navigator.clipboard.writeText(exportData.value)
    ElMessage.success('已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

/**
 * 下载为文件
 */
function downloadAsFile() {
  const blob = new Blob([exportData.value], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `motor_history_${new Date().toISOString().slice(0, 10)}.json`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  ElMessage.success('文件下载成功')
}

/**
 * 清空历史记录
 */
function clearHistory() {
  motorStore.clearMovementHistory()
  ElMessage.success('历史记录已清空')
}
</script>

<style scoped>
.history-panel-card {
  margin-bottom: var(--spacing-6);
  border: 1px solid var(--color-border-primary);
  transition: var(--transition-all);
}

.history-panel-card:hover {
  box-shadow: var(--shadow-md);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.header-icon {
  font-size: var(--font-size-lg);
  color: var(--color-primary-500);
}

.header-title {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.header-actions {
  display: flex;
  gap: var(--spacing-2);
}

.history-content {
  padding: var(--spacing-2) 0;
}

.history-list {
  border-radius: var(--radius-md);
}

.history-item {
  padding: var(--spacing-3);
  margin-bottom: var(--spacing-2);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
  transition: var(--transition-all);
}

.history-item:hover {
  border-color: var(--color-primary-300);
  box-shadow: var(--shadow-sm);
}

.history-item.history-error {
  border-color: var(--color-error-300);
  background-color: var(--color-error-light);
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-2);
}

.history-type {
  display: flex;
  gap: var(--spacing-2);
}

.history-time {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.history-details {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
  margin-bottom: var(--spacing-2);
}

.detail-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: var(--font-size-sm);
}

.detail-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  color: var(--color-text-secondary);
  min-width: 100px;
}

.detail-label .el-icon {
  font-size: var(--font-size-sm);
}

.detail-value {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
}

.error-message .detail-value {
  color: var(--color-error-500);
}

.history-actions {
  display: flex;
  justify-content: flex-end;
}

.empty-state {
  padding: var(--spacing-8) 0;
}

.export-content {
  padding: var(--spacing-2) 0;
}

/* 响应式优化 */
@media (max-width: 768px) {
  .header-left {
    flex-wrap: wrap;
  }

  .header-actions {
    flex-direction: column;
    width: 100%;
  }

  .header-actions .el-button {
    width: 100%;
  }

  .history-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-2);
  }

  .detail-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .detail-label {
    min-width: auto;
  }
}
</style>
