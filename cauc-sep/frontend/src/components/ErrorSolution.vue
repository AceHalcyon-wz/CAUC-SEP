<template>
  <div class="error-solution">
    <!-- 解决方案标题 -->
    <div class="solution-header">
      <div class="solution-title-row">
        <el-icon class="solution-icon" :style="{ color: severityColor }">
          <component :is="solutionIcon" />
        </el-icon>
        <div class="solution-title-content">
          <h3 class="solution-title">{{ solution?.title || '解决方案' }}</h3>
          <p class="solution-description">{{ solution?.description }}</p>
        </div>
      </div>

      <!-- 严重程度和类型标签 -->
      <div class="solution-tags">
        <el-tag
          v-if="solution?.type"
          :type="severityTagType"
          effect="dark"
          size="small"
        >
          {{ typeLabel }}
        </el-tag>
        <el-tag
          :type="severityTagType"
          effect="plain"
          size="small"
        >
          {{ severityLabel }}
        </el-tag>
      </div>
    </div>

    <!-- 解决方案搜索 -->
    <div v-if="solution?.solutions?.length > 3" class="solution-search">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索解决步骤..."
        clearable
        size="small"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </div>

    <!-- 解决步骤 -->
    <div v-if="filteredSteps.length" class="solution-steps">
      <div class="steps-header">
        <h4 class="steps-title">
          <el-icon><List /></el-icon>
          <span>解决步骤</span>
        </h4>
        <div class="steps-progress">
          <span class="progress-text">{{ completedSteps }} / {{ filteredSteps.length }}</span>
          <el-progress
            :percentage="progressPercentage"
            :stroke-width="6"
            :show-text="false"
            :color="severityColor"
          />
        </div>
      </div>

      <el-timeline>
        <el-timeline-item
          v-for="step in filteredSteps"
          :key="step.step"
          :timestamp="`步骤 ${step.step}`"
          placement="top"
          :color="getStepColor(step.step)"
          :class="{ 'step-completed': isStepCompleted(step.step) }"
        >
          <div class="step-card" @click="toggleStepCompletion(step.step)">
            <div class="step-header">
              <el-checkbox
                :model-value="isStepCompleted(step.step)"
                @click.stop
                @change="toggleStepCompletion(step.step)"
              />
              <el-icon class="step-icon"><component :is="step.icon" /></el-icon>
              <span class="step-action">{{ step.action }}</span>
              <el-tag
                v-if="isStepCompleted(step.step)"
                type="success"
                size="small"
                effect="plain"
              >
                已完成
              </el-tag>
            </div>
            <p class="step-description">{{ step.description }}</p>
          </div>
        </el-timeline-item>
      </el-timeline>
    </div>

    <!-- 无搜索结果 -->
    <el-empty
      v-else-if="solution?.solutions?.length && searchKeyword"
      description="未找到匹配的解决步骤"
      :image-size="80"
    />

    <!-- 自动操作按钮 -->
    <div v-if="solution?.autoActions?.length" class="auto-actions">
      <h4 class="actions-title">
        <el-icon><MagicStick /></el-icon>
        <span>快捷操作</span>
      </h4>

      <div class="action-buttons">
        <el-button
          v-for="action in solution.autoActions"
          :key="action.action"
          :type="getActionType(action.action)"
          :icon="getActionIcon(action.action)"
          @click="handleAutoAction(action.action)"
        >
          {{ action.label }}
        </el-button>
      </div>
    </div>

    <!-- 相关文档 -->
    <div v-if="solution?.relatedDocs?.length" class="related-docs">
      <h4 class="docs-title">
        <el-icon><Document /></el-icon>
        <span>相关文档</span>
      </h4>

      <div class="docs-list">
        <a
          v-for="doc in solution.relatedDocs"
          :key="doc.url"
          :href="doc.url"
          class="doc-link"
          target="_blank"
        >
          <el-icon><Link /></el-icon>
          <span>{{ doc.title }}</span>
          <el-icon class="external-icon"><TopRight /></el-icon>
        </a>
      </div>
    </div>

    <!-- 匹配信息 -->
    <div v-if="solution?.matchedPattern" class="match-info">
      <el-icon><InfoFilled /></el-icon>
      <span>匹配规则: {{ solution.matchedPattern }}</span>
    </div>
  </div>
</template>

<script setup>
/**
 * @file ErrorSolution.vue
 * @path src/components/
 * @description 错误解决方案显示组件，提供步骤指引、快捷操作和相关文档链接
 *              支持解决方案搜索、步骤进度追踪和完成状态管理
 * @author Agent
 * @date 2024-03-07
 */

import { computed, ref, watch } from 'vue'
import {
  List,
  MagicStick,
  Document,
  Link,
  TopRight,
  InfoFilled,
  Refresh,
  Connection,
  Monitor,
  Setting,
  Warning,
  Search,
  CircleCheck
} from '@element-plus/icons-vue'
import {
  getErrorIcon,
  getSeverityColor,
  getErrorTypeLabel,
  ERROR_SEVERITY
} from '../composables/useErrorHandler'

/**
 * Props定义
 */
const props = defineProps({
  /**
   * 解决方案对象
   */
  solution: {
    type: Object,
    default: null
  }
})

/**
 * Emits定义
 */
const emit = defineEmits({
  /**
   * 自动操作事件
   * @param {string} action - 操作类型
   */
  'auto-action': (action) => typeof action === 'string',
  /**
   * 步骤完成状态变更事件
   * @param {Object} data - 包含step和completed的对象
   */
  'step-toggle': (data) => typeof data === 'object'
})

/**
 * 搜索关键词
 */
const searchKeyword = ref('')

/**
 * 已完成的步骤
 */
const completedStepsSet = ref(new Set())

/**
 * 解决方案图标
 */
const solutionIcon = computed(() => {
  if (!props.solution?.type) return Warning
  const iconName = getErrorIcon(props.solution.type)
  // 图标名称映射
  const iconMap = {
    Connection,
    Lock: Warning,
    Warning,
    Monitor,
    Time: Warning,
    Document
  }
  return iconMap[iconName] || Warning
})

/**
 * 严重程度颜色
 */
const severityColor = computed(() => {
  return getSeverityColor(props.solution?.severity || ERROR_SEVERITY.MEDIUM)
})

/**
 * 严重程度标签类型
 */
const severityTagType = computed(() => {
  const typeMap = {
    [ERROR_SEVERITY.LOW]: 'success',
    [ERROR_SEVERITY.MEDIUM]: 'warning',
    [ERROR_SEVERITY.HIGH]: 'danger',
    [ERROR_SEVERITY.CRITICAL]: 'danger'
  }
  return typeMap[props.solution?.severity] || 'warning'
})

/**
 * 严重程度标签文本
 */
const severityLabel = computed(() => {
  const labelMap = {
    [ERROR_SEVERITY.LOW]: '低',
    [ERROR_SEVERITY.MEDIUM]: '中',
    [ERROR_SEVERITY.HIGH]: '高',
    [ERROR_SEVERITY.CRITICAL]: '严重'
  }
  return labelMap[props.solution?.severity] || '中'
})

/**
 * 错误类型标签
 */
const typeLabel = computed(() => {
  return getErrorTypeLabel(props.solution?.type)
})

/**
 * 过滤后的解决步骤
 */
const filteredSteps = computed(() => {
  if (!props.solution?.solutions) return []
  if (!searchKeyword.value) return props.solution.solutions
  
  const keyword = searchKeyword.value.toLowerCase()
  return props.solution.solutions.filter(step => 
    step.action.toLowerCase().includes(keyword) ||
    step.description.toLowerCase().includes(keyword)
  )
})

/**
 * 已完成的步骤数量
 */
const completedSteps = computed(() => {
  return completedStepsSet.value.size
})

/**
 * 进度百分比
 */
const progressPercentage = computed(() => {
  if (filteredSteps.value.length === 0) return 0
  return Math.round((completedSteps.value / filteredSteps.value.length) * 100)
})

/**
 * 检查步骤是否已完成
 *
 * @param {number} step - 步骤编号
 * @returns {boolean} 是否已完成
 */
function isStepCompleted(step) {
  return completedStepsSet.value.has(step)
}

/**
 * 切换步骤完成状态
 *
 * @param {number} step - 步骤编号
 */
function toggleStepCompletion(step) {
  if (completedStepsSet.value.has(step)) {
    completedStepsSet.value.delete(step)
  } else {
    completedStepsSet.value.add(step)
  }
  // 触发事件
  emit('step-toggle', {
    step,
    completed: completedStepsSet.value.has(step),
    completedSteps: Array.from(completedStepsSet.value)
  })
}

/**
 * 获取步骤颜色
 *
 * @param {number} step - 步骤编号
 * @returns {string} 颜色值
 */
function getStepColor(step) {
  if (isStepCompleted(step)) {
    return 'var(--color-success)'
  }
  return severityColor.value
}

/**
 * 获取操作按钮类型
 *
 * @param {string} action - 操作类型
 * @returns {string} 按钮类型
 */
function getActionType(action) {
  const typeMap = {
    retry: 'primary',
    reconnect: 'primary',
    refresh: 'primary',
    relogin: 'warning',
    resetForm: 'info',
    scanDevices: 'primary',
    checkServer: 'info',
    checkStatus: 'info',
    testConnection: 'primary',
    exportReport: 'success'
  }
  return typeMap[action] || 'default'
}

/**
 * 获取操作按钮图标
 *
 * @param {string} action - 操作类型
 * @returns {Object} 图标组件
 */
function getActionIcon(action) {
  const iconMap = {
    retry: Refresh,
    reconnect: Connection,
    refresh: Refresh,
    relogin: Warning,
    resetForm: Refresh,
    scanDevices: Monitor,
    checkServer: Monitor,
    checkStatus: Monitor,
    testConnection: Connection,
    exportReport: Document
  }
  return iconMap[action] || Setting
}

/**
 * 处理自动操作
 *
 * @param {string} action - 操作类型
 */
function handleAutoAction(action) {
  emit('auto-action', action)
}

/**
 * 监听解决方案变化，重置完成状态
 */
watch(() => props.solution, () => {
  completedStepsSet.value.clear()
  searchKeyword.value = ''
}, { immediate: true })
</script>

<style scoped>
.error-solution {
  padding: var(--spacing-4);
  background-color: var(--color-surface-primary);
  border-radius: var(--radius-lg);
}

/* 解决方案标题 */
.solution-header {
  margin-bottom: var(--spacing-6);
}

.solution-title-row {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-3);
  margin-bottom: var(--spacing-3);
}

.solution-icon {
  font-size: var(--font-size-2xl);
  flex-shrink: 0;
  margin-top: 2px;
}

.solution-title-content {
  flex: 1;
}

.solution-title {
  margin: 0 0 var(--spacing-2) 0;
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.solution-description {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: var(--line-height-relaxed);
}

.solution-tags {
  display: flex;
  gap: var(--spacing-2);
  margin-top: var(--spacing-3);
}

/* 解决方案搜索 */
.solution-search {
  margin-bottom: var(--spacing-4);
}

/* 解决步骤 */
.solution-steps {
  margin-bottom: var(--spacing-6);
}

.steps-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-4);
}

.steps-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  margin: 0;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.steps-progress {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  min-width: 150px;
}

.progress-text {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.step-card {
  padding: var(--spacing-3);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
  transition: var(--transition-all);
  cursor: pointer;
}

.step-card:hover {
  background-color: var(--color-interactive-hover);
  border-color: var(--color-border-focus);
}

.step-completed .step-card {
  background-color: rgba(56, 161, 105, 0.05);
  border-color: var(--color-success);
}

.step-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-2);
}

.step-icon {
  font-size: var(--font-size-lg);
  color: var(--color-primary-500);
}

.step-action {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  flex: 1;
}

.step-description {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: var(--line-height-relaxed);
  padding-left: 28px;
}

/* 自动操作按钮 */
.auto-actions {
  margin-bottom: var(--spacing-6);
}

.actions-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  margin: 0 0 var(--spacing-3) 0;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.action-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-2);
}

/* 相关文档 */
.related-docs {
  margin-bottom: var(--spacing-4);
}

.docs-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  margin: 0 0 var(--spacing-3) 0;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.docs-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.doc-link {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-3);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  color: var(--color-primary-500);
  text-decoration: none;
  font-size: var(--font-size-sm);
  transition: var(--transition-all);
}

.doc-link:hover {
  background-color: var(--color-interactive-hover);
  color: var(--color-primary-600);
}

.external-icon {
  margin-left: auto;
  font-size: var(--font-size-xs);
  opacity: 0.6;
}

/* 匹配信息 */
.match-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-3);
  background-color: var(--color-bg-tertiary);
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

/* Element Plus 时间线样式覆盖 */
:deep(.el-timeline-item__timestamp) {
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
}

:deep(.el-timeline-item__tail) {
  border-left-color: var(--color-border-primary);
}

:deep(.el-timeline-item__node) {
  background-color: var(--color-primary-500);
}
</style>
