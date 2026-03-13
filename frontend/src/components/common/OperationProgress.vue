<!--
  @file OperationProgress.vue
  @path src/components/
  @description 全局操作进度指示器组件，显示操作进度、步骤、支持取消操作
  @author Agent
  @date 2024-03-07
-->

<script setup>
/**
 * 操作进度指示器组件
 * 
 * 提供全局进度条、步骤进度显示、进度百分比、取消操作等功能
 */

import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useOperationStore, OPERATION_STATUS } from '@/stores/operation'

// ==================== Props & Emits ====================

const props = defineProps({
  /** 是否显示全局进度条 */
  showGlobal: {
    type: Boolean,
    default: true
  },
  /** 是否显示步骤详情 */
  showSteps: {
    type: Boolean,
    default: true
  },
  /** 是否显示百分比 */
  showPercentage: {
    type: Boolean,
    default: true
  },
  /** 是否显示取消按钮 */
  showCancel: {
    type: Boolean,
    default: true
  },
  /** 最小显示时间（毫秒） */
  minDisplayTime: {
    type: Number,
    default: 300
  },
  /** 自定义操作ID（用于局部进度显示） */
  operationId: {
    type: String,
    default: null
  }
})

const emit = defineEmits([
  'cancel',
  'complete',
  'error'
])

// ==================== 组合式函数调用 ====================

const operationStore = useOperationStore()

// ==================== 响应式状态 ====================

/** 是否可见 */
const visible = ref(false)
/** 动画状态 */
const animating = ref(false)
/** 显示计时器 */
let displayTimer = null

// ==================== 计算属性 ====================

/**
 * 当前进度数据
 */
const progressData = computed(() => {
  if (props.operationId) {
    // 局部操作
    const operation = operationStore.activeOperations.find(
      op => op.id === props.operationId
    )
    if (operation) {
      return {
        percentage: operation.progress,
        status: operation.status,
        message: operation.steps[operation.currentStep]?.message || operation.title,
        cancellable: operation.cancellable,
        operation
      }
    }
  }
  // 全局进度
  return operationStore.globalProgress
})

/**
 * 当前操作对象
 */
const currentOperation = computed(() => {
  if (props.operationId) {
    return operationStore.activeOperations.find(op => op.id === props.operationId)
  }
  return operationStore.activeOperations.find(
    op => op.status === OPERATION_STATUS.RUNNING
  )
})

/**
 * 进度条颜色
 */
const progressColor = computed(() => {
  const status = progressData.value.status
  switch (status) {
    case OPERATION_STATUS.SUCCESS:
      return 'var(--color-success)'
    case OPERATION_STATUS.FAILED:
      return 'var(--color-error)'
    case OPERATION_STATUS.CANCELLED:
      return 'var(--color-warning)'
    default:
      return 'var(--color-primary-500)'
  }
})

/**
 * 进度条样式
 */
const progressStyle = computed(() => {
  return {
    width: `${progressData.value.percentage}%`,
    backgroundColor: progressColor.value,
    transition: 'width 0.3s ease'
  }
})

/**
 * 是否可取消
 */
const canCancel = computed(() => {
  return props.showCancel && progressData.value.cancellable
})

/**
 * 步骤列表
 */
const steps = computed(() => {
  return currentOperation.value?.steps || []
})

/**
 * 当前步骤索引
 */
const currentStepIndex = computed(() => {
  return currentOperation.value?.currentStep || 0
})

/**
 * 状态图标
 */
const statusIcon = computed(() => {
  const status = progressData.value.status
  switch (status) {
    case OPERATION_STATUS.SUCCESS:
      return '✓'
    case OPERATION_STATUS.FAILED:
      return '✕'
    case OPERATION_STATUS.CANCELLED:
      return '⊘'
    default:
      return ''
  }
})

// ==================== 方法 ====================

/**
 * 显示进度条
 */
function show() {
  if (displayTimer) {
    clearTimeout(displayTimer)
  }
  animating.value = true
  visible.value = true
}

/**
 * 隐藏进度条
 */
function hide() {
  animating.value = false
  displayTimer = setTimeout(() => {
    visible.value = false
  }, props.minDisplayTime)
}

/**
 * 取消操作
 */
function handleCancel() {
  if (canCancel.value) {
    const operationId = currentOperation.value?.id
    if (operationId) {
      operationStore.cancelOperation(operationId)
      emit('cancel', operationId)
    }
  }
}

/**
 * 获取步骤状态类名
 *
 * @param {number} index - 步骤索引
 * @returns {string} 类名
 */
function getStepStatusClass(index) {
  if (index < currentStepIndex.value) {
    return 'completed'
  } else if (index === currentStepIndex.value) {
    const status = steps.value[index]?.status
    return status === OPERATION_STATUS.RUNNING ? 'running' : 'pending'
  }
  return 'pending'
}

/**
 * 获取步骤图标
 *
 * @param {number} index - 步骤索引
 * @returns {string} 图标
 */
function getStepIcon(index) {
  const status = getStepStatusClass(index)
  switch (status) {
    case 'completed':
      return '✓'
    case 'running':
      return '●'
    default:
      return String(index + 1)
  }
}

// ==================== 监听器 ====================

// 监听进度数据变化
watch(
  () => progressData.value.visible,
  (newVal) => {
    if (newVal) {
      show()
    } else {
      hide()
    }
  },
  { immediate: true }
)

// 监听操作状态变化
watch(
  () => progressData.value.status,
  (newStatus) => {
    if (newStatus === OPERATION_STATUS.SUCCESS) {
      emit('complete', currentOperation.value)
    } else if (newStatus === OPERATION_STATUS.FAILED) {
      emit('error', currentOperation.value?.error)
    }
  }
)

// ==================== 生命周期 ====================

onMounted(() => {
  if (progressData.value.visible) {
    show()
  }
})

onUnmounted(() => {
  if (displayTimer) {
    clearTimeout(displayTimer)
  }
})
</script>

<template>
  <Transition name="progress-fade">
    <div
      v-if="visible && showGlobal"
      class="operation-progress"
      :class="{ 'operation-progress--animating': animating }"
    >
      <!-- 进度条容器 -->
      <div class="progress-container">
        <!-- 进度信息 -->
        <div class="progress-info">
          <span class="progress-message">{{ progressData.message }}</span>
          <span
            v-if="showPercentage"
            class="progress-percentage"
          >
            {{ progressData.percentage }}%
          </span>
        </div>

        <!-- 进度条 -->
        <div class="progress-bar-wrapper">
          <div class="progress-bar">
            <div
              class="progress-bar-fill"
              :style="progressStyle"
            >
              <div
                v-if="progressData.status === OPERATION_STATUS.RUNNING"
                class="progress-bar-indeterminate"
              />
            </div>
          </div>

          <!-- 状态图标 -->
          <div
            v-if="statusIcon && progressData.status !== OPERATION_STATUS.RUNNING"
            class="progress-status-icon"
            :style="{ color: progressColor }"
          >
            {{ statusIcon }}
          </div>
        </div>

        <!-- 取消按钮 -->
        <button
          v-if="canCancel"
          class="progress-cancel-btn"
          title="取消操作"
          @click="handleCancel"
        >
          <span class="cancel-icon">✕</span>
        </button>
      </div>

      <!-- 步骤详情 -->
      <div
        v-if="showSteps && steps.length > 0"
        class="progress-steps"
      >
        <div
          v-for="(step, index) in steps"
          :key="index"
          class="progress-step"
          :class="getStepStatusClass(index)"
        >
          <div class="step-indicator">
            <span class="step-icon">{{ getStepIcon(index) }}</span>
          </div>
          <div class="step-content">
            <span class="step-name">{{ step.name }}</span>
            <span
              v-if="step.message && index === currentStepIndex"
              class="step-message"
            >
              {{ step.message }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.operation-progress {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: var(--z-index-fixed);
  background: var(--color-surface-elevated);
  border-bottom: 1px solid var(--color-border-primary);
  box-shadow: var(--shadow-md);
  transition: transform 0.3s ease, opacity 0.3s ease;
}

.operation-progress--animating {
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    transform: translateY(-100%);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.progress-container {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-3) var(--spacing-4);
}

.progress-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  min-width: 0;
  flex: 1;
}

.progress-message {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.progress-percentage {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-primary-500);
  white-space: nowrap;
}

.progress-bar-wrapper {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  flex: 2;
  min-width: 200px;
}

.progress-bar {
  flex: 1;
  height: 6px;
  background: var(--color-neutral-200);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  border-radius: var(--radius-full);
  position: relative;
  transition: width 0.3s ease;
}

.progress-bar-indeterminate {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.4),
    transparent
  );
  animation: indeterminate 1.5s infinite;
}

@keyframes indeterminate {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

.progress-status-icon {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  min-width: 24px;
  text-align: center;
}

.progress-cancel-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
}

.progress-cancel-btn:hover {
  background: var(--color-interactive-hover);
  color: var(--color-error);
}

.cancel-icon {
  font-size: var(--font-size-base);
  line-height: 1;
}

.progress-steps {
  display: flex;
  gap: var(--spacing-2);
  padding: 0 var(--spacing-4) var(--spacing-3);
  overflow-x: auto;
}

.progress-step {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-2);
  min-width: 120px;
  padding: var(--spacing-2);
  border-radius: var(--radius-md);
  transition: background-color var(--transition-fast);
}

.progress-step.running {
  background: var(--color-primary-50);
}

.step-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  flex-shrink: 0;
}

.progress-step.pending .step-indicator {
  background: var(--color-neutral-200);
  color: var(--color-text-tertiary);
}

.progress-step.running .step-indicator {
  background: var(--color-primary-500);
  color: var(--color-text-inverse);
  animation: pulse 2s infinite;
}

.progress-step.completed .step-indicator {
  background: var(--color-success);
  color: var(--color-text-inverse);
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(44, 82, 130, 0.4);
  }
  50% {
    box-shadow: 0 0 0 4px rgba(44, 82, 130, 0);
  }
}

.step-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.step-name {
  font-size: var(--font-size-xs);
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.step-message {
  font-size: 10px;
  color: var(--color-text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 过渡动画 */
.progress-fade-enter-active,
.progress-fade-leave-active {
  transition: all 0.3s ease;
}

.progress-fade-enter-from,
.progress-fade-leave-to {
  transform: translateY(-100%);
  opacity: 0;
}

/* 响应式 */
@media (max-width: 768px) {
  .progress-steps {
    display: none;
  }

  .progress-bar-wrapper {
    min-width: 150px;
  }
}
</style>
