<!--
  @file OperationFeedback.vue
  @path src/components/
  @description 操作反馈组件，包含成功提示、错误详情、撤销功能等
  @author Agent
  @date 2024-03-07
-->

<script setup>
/**
 * 操作反馈组件
 * 
 * 提供操作成功确认提示、失败详细提示、撤销操作等功能
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useOperationStore, ERROR_TYPE, OPERATION_TYPE_TEXT } from '@/stores/operation'

// ==================== Props & Emits ====================

const props = defineProps({
  /** 成功提示显示时长（毫秒） */
  successDuration: {
    type: Number,
    default: 5000
  },
  /** 错误提示是否自动关闭 */
  autoCloseError: {
    type: Boolean,
    default: false
  },
  /** 错误提示自动关闭延迟（毫秒） */
  errorAutoCloseDelay: {
    type: Number,
    default: 10000
  },
  /** 最大显示通知数量 */
  maxVisibleNotifications: {
    type: Number,
    default: 3
  },
  /** 显示位置 */
  position: {
    type: String,
    default: 'top-right',
    validator: (value) => ['top-right', 'top-left', 'bottom-right', 'bottom-left'].includes(value)
  }
})

const emit = defineEmits([
  'success-dismiss',
  'error-dismiss',
  'undo',
  'retry'
])

// ==================== 组合式函数调用 ====================

const operationStore = useOperationStore()

// ==================== 响应式状态 ====================

/** 自动关闭定时器映射 */
const autoCloseTimers = new Map()

// ==================== 计算属性 ====================

/**
 * 可见的通知列表（限制数量）
 */
const visibleSuccessNotifications = computed(() => {
  return operationStore.successNotifications
    .slice(0, props.maxVisibleNotifications)
})

/**
 * 可见的错误通知列表（限制数量）
 */
const visibleErrorNotifications = computed(() => {
  return operationStore.errorNotifications
    .slice(0, props.maxVisibleNotifications)
})

/**
 * 可撤销的操作列表
 */
const undoableOperations = computed(() => {
  return operationStore.undoQueue.filter(item => item.canUndo && !item.undone)
})

/**
 * 位置样式类
 */
const positionClass = computed(() => {
  return `feedback-${props.position}`
})

// ==================== 方法 ====================

/**
 * 关闭成功提示
 *
 * @param {string} notificationId - 通知ID
 */
function dismissSuccess(notificationId) {
  operationStore.removeSuccessNotification(notificationId)
  emit('success-dismiss', notificationId)
}

/**
 * 关闭错误提示
 *
 * @param {string} notificationId - 通知ID
 */
function dismissError(notificationId) {
  clearAutoCloseTimer(notificationId)
  operationStore.removeErrorNotification(notificationId)
  emit('error-dismiss', notificationId)
}

/**
 * 切换错误详情展开
 *
 * @param {string} notificationId - 通知ID
 */
function toggleErrorDetails(notificationId) {
  operationStore.toggleErrorExpanded(notificationId)
}

/**
 * 执行撤销
 *
 * @param {string} undoId - 撤销项ID
 */
async function handleUndo(undoId) {
  const result = await operationStore.executeUndo(undoId)
  emit('undo', { undoId, result })
}

/**
 * 重试操作
 *
 * @param {string} notificationId - 通知ID
 */
async function handleRetry(notificationId) {
  const notification = operationStore.errorNotifications.find(n => n.id === notificationId)
  if (notification?.operationId) {
    const result = await operationStore.retryOperation(notification.operationId)
    emit('retry', { notificationId, result })
    
    // 关闭错误提示
    dismissError(notificationId)
  }
}

/**
 * 获取错误类型文本
 *
 * @param {string} errorType - 错误类型
 * @returns {string} 错误类型文本
 */
function getErrorTypeText(errorType) {
  return ERROR_TYPE[errorType] ? 
    (operationStore.ERROR_TYPE_TEXT[errorType] || errorType) : 
    '未知错误'
}

/**
 * 获取帮助链接
 *
 * @param {string} errorType - 错误类型
 * @returns {Object} 帮助链接信息
 */
function getHelpLink(errorType) {
  return operationStore.getErrorHelpLink(errorType)
}

/**
 * 获取操作类型文本
 *
 * @param {string} type - 操作类型
 * @returns {string} 操作类型文本
 */
function getOperationTypeText(type) {
  return OPERATION_TYPE_TEXT[type] || type
}

/**
 * 格式化时间
 *
 * @param {number} timestamp - 时间戳
 * @returns {string} 格式化后的时间
 */
function formatTime(timestamp) {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

/**
 * 设置自动关闭定时器
 *
 * @param {string} notificationId - 通知ID
 */
function setAutoCloseTimer(notificationId) {
  if (props.autoCloseError) {
    const timer = setTimeout(() => {
      dismissError(notificationId)
    }, props.errorAutoCloseDelay)
    autoCloseTimers.set(notificationId, timer)
  }
}

/**
 * 清除自动关闭定时器
 *
 * @param {string} notificationId - 通知ID
 */
function clearAutoCloseTimer(notificationId) {
  const timer = autoCloseTimers.get(notificationId)
  if (timer) {
    clearTimeout(timer)
    autoCloseTimers.delete(notificationId)
  }
}

/**
 * 计算撤销剩余时间
 *
 * @param {Object} undoItem - 撤销项
 * @returns {number} 剩余秒数
 */
function getUndoRemainingTime(undoItem) {
  const remaining = undoItem.expiresAt - Date.now()
  return Math.max(0, Math.ceil(remaining / 1000))
}

// ==================== 生命周期 ====================

onMounted(() => {
  // 为现有错误通知设置自动关闭
  visibleErrorNotifications.value.forEach(notification => {
    setAutoCloseTimer(notification.id)
  })
})

onUnmounted(() => {
  // 清除所有定时器
  autoCloseTimers.forEach(timer => clearTimeout(timer))
  autoCloseTimers.clear()
})
</script>

<template>
  <div
    class="operation-feedback"
    :class="positionClass"
  >
    <!-- 成功提示列表 -->
    <TransitionGroup
      name="notification"
      tag="div"
      class="success-list"
    >
      <div
        v-for="notification in visibleSuccessNotifications"
        :key="notification.id"
        class="notification success-notification"
      >
        <!-- 成功图标 -->
        <div class="notification-icon success-icon">
          <svg
            viewBox="0 0 24 24"
            width="24"
            height="24"
          >
            <path
              fill="currentColor"
              d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"
            />
          </svg>
        </div>

        <!-- 内容 -->
        <div class="notification-content">
          <div class="notification-title">
            {{ notification.title }}
          </div>
          <div
            v-if="notification.message"
            class="notification-message"
          >
            {{ notification.message }}
          </div>
          
          <!-- 操作结果摘要 -->
          <div
            v-if="notification.result"
            class="notification-result"
          >
            <template v-if="notification.result.deviceId">
              设备ID: {{ notification.result.deviceId }}
            </template>
            <template v-else-if="notification.result.total">
              处理: {{ notification.result.succeeded }}/{{ notification.result.total }}
            </template>
          </div>

          <!-- 操作历史链接 -->
          <router-link
            v-if="notification.showHistoryLink && notification.operationId"
            :to="`/history/${notification.operationId}`"
            class="notification-link"
          >
            查看详情
          </router-link>
        </div>

        <!-- 关闭按钮 -->
        <button
          class="notification-close"
          title="关闭"
          @click="dismissSuccess(notification.id)"
        >
          <svg
            viewBox="0 0 24 24"
            width="18"
            height="18"
          >
            <path
              fill="currentColor"
              d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"
            />
          </svg>
        </button>

        <!-- 自动消失进度条 -->
        <div class="notification-progress">
          <div
            class="notification-progress-bar"
            :style="{ animationDuration: `${notification.duration}ms` }"
          />
        </div>
      </div>
    </TransitionGroup>

    <!-- 错误提示列表 -->
    <TransitionGroup
      name="notification"
      tag="div"
      class="error-list"
    >
      <div
        v-for="notification in visibleErrorNotifications"
        :key="notification.id"
        class="notification error-notification"
        :class="{ 'error-expanded': notification.expanded }"
      >
        <!-- 错误图标 -->
        <div class="notification-icon error-icon">
          <svg
            viewBox="0 0 24 24"
            width="24"
            height="24"
          >
            <path
              fill="currentColor"
              d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"
            />
          </svg>
        </div>

        <!-- 内容 -->
        <div class="notification-content">
          <div class="notification-title">
            <span>{{ notification.title }}</span>
            <span class="error-type-badge">{{ getErrorTypeText(notification.error?.type) }}</span>
          </div>
          <div class="notification-message">
            {{ notification.error?.message }}
          </div>

          <!-- 错误详情（可展开） -->
          <div
            v-if="notification.expanded && notification.error?.details"
            class="error-details"
          >
            <div class="error-details-title">
              详细信息：
            </div>
            <pre class="error-details-content">{{ JSON.stringify(notification.error.details, null, 2) }}</pre>
          </div>

          <!-- 操作按钮 -->
          <div class="notification-actions">
            <button
              v-if="notification.retryable"
              class="action-btn retry-btn"
              @click="handleRetry(notification.id)"
            >
              <svg
                viewBox="0 0 24 24"
                width="16"
                height="16"
              >
                <path
                  fill="currentColor"
                  d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"
                />
              </svg>
              重试
            </button>

            <button
              class="action-btn details-btn"
              @click="toggleErrorDetails(notification.id)"
            >
              {{ notification.expanded ? '收起' : '详情' }}
            </button>

            <a
              :href="getHelpLink(notification.error?.type).url"
              class="action-btn help-btn"
              target="_blank"
            >
              <svg
                viewBox="0 0 24 24"
                width="16"
                height="16"
              >
                <path
                  fill="currentColor"
                  d="M11 18h2v-2h-2v2zm1-16C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm0-14c-2.21 0-4 1.79-4 4h2c0-1.1.9-2 2-2s2 .9 2 2c0 2-3 1.75-3 5h2c0-2.25 3-2.5 3-5 0-2.21-1.79-4-4-4z"
                />
              </svg>
              帮助
            </a>
          </div>
        </div>

        <!-- 关闭按钮 -->
        <button
          class="notification-close"
          title="关闭"
          @click="dismissError(notification.id)"
        >
          <svg
            viewBox="0 0 24 24"
            width="18"
            height="18"
          >
            <path
              fill="currentColor"
              d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"
            />
          </svg>
        </button>
      </div>
    </TransitionGroup>

    <!-- 撤销操作提示 -->
    <TransitionGroup
      name="notification"
      tag="div"
      class="undo-list"
    >
      <div
        v-for="undoItem in undoableOperations"
        :key="undoItem.id"
        class="notification undo-notification"
      >
        <div class="undo-content">
          <span class="undo-title">{{ undoItem.title }}</span>
          <span class="undo-hint">已撤销</span>
        </div>
        
        <button
          class="undo-btn"
          @click="handleUndo(undoItem.id)"
        >
          撤销
        </button>

        <span class="undo-countdown">{{ getUndoRemainingTime(undoItem) }}s</span>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.operation-feedback {
  position: fixed;
  z-index: var(--z-index-popover);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
  max-width: 400px;
  pointer-events: none;
}

.feedback-top-right {
  top: var(--spacing-4);
  right: var(--spacing-4);
}

.feedback-top-left {
  top: var(--spacing-4);
  left: var(--spacing-4);
}

.feedback-bottom-right {
  bottom: var(--spacing-4);
  right: var(--spacing-4);
}

.feedback-bottom-left {
  bottom: var(--spacing-4);
  left: var(--spacing-4);
}

.success-list,
.error-list,
.undo-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.notification {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-3);
  padding: var(--spacing-3) var(--spacing-4);
  background: var(--color-surface-elevated);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  pointer-events: auto;
  overflow: hidden;
}

.success-notification {
  border-left: 4px solid var(--color-success);
}

.error-notification {
  border-left: 4px solid var(--color-error);
}

.undo-notification {
  border-left: 4px solid var(--color-primary-500);
  align-items: center;
}

.notification-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.success-icon {
  color: var(--color-success);
}

.error-icon {
  color: var(--color-error);
}

.notification-content {
  flex: 1;
  min-width: 0;
}

.notification-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-1);
}

.notification-message {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  word-break: break-word;
}

.notification-result {
  margin-top: var(--spacing-2);
  padding: var(--spacing-2);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.notification-link {
  display: inline-block;
  margin-top: var(--spacing-2);
  font-size: var(--font-size-xs);
  color: var(--color-primary-500);
  text-decoration: none;
  transition: color var(--transition-fast);
}

.notification-link:hover {
  color: var(--color-primary-600);
  text-decoration: underline;
}

.error-type-badge {
  padding: 2px 8px;
  background: var(--color-error-light);
  color: var(--color-error);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-normal);
  border-radius: var(--radius-sm);
}

.error-details {
  margin-top: var(--spacing-2);
  padding: var(--spacing-2);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
}

.error-details-title {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-1);
}

.error-details-content {
  margin: 0;
  padding: var(--spacing-2);
  background: var(--color-bg-primary);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-family: var(--font-family-mono);
  color: var(--color-text-primary);
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.notification-actions {
  display: flex;
  gap: var(--spacing-2);
  margin-top: var(--spacing-2);
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-1);
  padding: var(--spacing-1) var(--spacing-2);
  border: 1px solid var(--color-border-primary);
  background: var(--color-bg-primary);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
  text-decoration: none;
}

.action-btn:hover {
  background: var(--color-interactive-hover);
  color: var(--color-text-primary);
  border-color: var(--color-border-focus);
}

.retry-btn:hover {
  color: var(--color-primary-500);
  border-color: var(--color-primary-500);
}

.notification-close {
  position: absolute;
  top: var(--spacing-2);
  right: var(--spacing-2);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: var(--color-text-tertiary);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

.notification-close:hover {
  background: var(--color-interactive-hover);
  color: var(--color-text-primary);
}

.notification-progress {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--color-neutral-200);
}

.notification-progress-bar {
  height: 100%;
  background: var(--color-success);
  animation: progress-shrink linear forwards;
}

@keyframes progress-shrink {
  from {
    width: 100%;
  }
  to {
    width: 0%;
  }
}

.undo-content {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.undo-title {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.undo-hint {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.undo-btn {
  padding: var(--spacing-1) var(--spacing-3);
  border: 1px solid var(--color-primary-500);
  background: transparent;
  color: var(--color-primary-500);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.undo-btn:hover {
  background: var(--color-primary-500);
  color: var(--color-text-inverse);
}

.undo-countdown {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  min-width: 24px;
  text-align: right;
}

/* 通知动画 */
.notification-enter-active {
  animation: slideIn 0.3s ease;
}

.notification-leave-active {
  animation: slideOut 0.3s ease;
}

.notification-move {
  transition: transform 0.3s ease;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

@keyframes slideOut {
  from {
    transform: translateX(0);
    opacity: 1;
  }
  to {
    transform: translateX(100%);
    opacity: 0;
  }
}

/* 响应式 */
@media (max-width: 768px) {
  .operation-feedback {
    left: var(--spacing-2);
    right: var(--spacing-2);
    max-width: none;
  }

  .feedback-top-left,
  .feedback-top-right {
    left: var(--spacing-2);
    right: var(--spacing-2);
  }

  .feedback-bottom-left,
  .feedback-bottom-right {
    left: var(--spacing-2);
    right: var(--spacing-2);
  }
}
</style>
