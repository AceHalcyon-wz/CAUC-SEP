<template>
  <el-dialog
    v-model="visible"
    :title="dialogTitle"
    width="800px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    class="error-display-dialog"
    @close="handleClose"
  >
    <div class="error-display">
      <!-- 错误概览 -->
      <div
        class="error-overview"
        :class="`severity-${errorInfo?.severity || 'medium'}`"
      >
        <div
          class="error-icon-wrapper"
          :style="{ backgroundColor: severityBgColor }"
        >
          <el-icon
            class="error-icon"
            :style="{ color: severityColor }"
          >
            <component :is="errorIcon" />
          </el-icon>
        </div>

        <div class="error-info">
          <div class="error-header-row">
            <h3 class="error-title">
              {{ displayTitle }}
            </h3>
            <div class="error-actions">
              <el-tooltip
                content="复制错误信息"
                placement="top"
              >
                <el-button
                  circle
                  size="small"
                  @click="copyToClipboard('detail')"
                >
                  <el-icon><CopyDocument /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip
                content="复制堆栈信息"
                placement="top"
              >
                <el-button
                  circle
                  size="small"
                  @click="copyToClipboard('stack')"
                >
                  <el-icon><Document /></el-icon>
                </el-button>
              </el-tooltip>
            </div>
          </div>
          <p class="error-message">
            {{ displayMessage }}
          </p>

          <div class="error-meta">
            <el-tag
              :type="severityTagType"
              effect="dark"
              size="small"
            >
              <el-icon class="tag-icon">
                <component :is="severityIcon" />
              </el-icon>
              {{ severityLabel }}
            </el-tag>
            <el-tag
              type="info"
              effect="plain"
              size="small"
            >
              <el-icon class="tag-icon">
                <component :is="typeIconComponent" />
              </el-icon>
              {{ typeLabel }}
            </el-tag>
            <span class="error-time">
              <el-icon><Clock /></el-icon>
              {{ formattedTime }}
            </span>
            <span
              v-if="errorInfo?.id"
              class="error-id"
            >
              <el-icon><Key /></el-icon>
              {{ errorInfo.id.slice(-8) }}
            </span>
          </div>
        </div>
      </div>

      <!-- 标签页切换 -->
      <el-tabs
        v-model="activeTab"
        class="error-tabs"
      >
        <!-- 解决方案标签页 -->
        <el-tab-pane
          label="解决方案"
          name="solution"
        >
          <ErrorSolution
            v-if="errorInfo?.solution"
            :solution="errorInfo.solution"
            @auto-action="handleAutoAction"
          />
          <el-empty
            v-else
            description="暂无解决方案"
          />
        </el-tab-pane>

        <!-- 错误详情标签页 -->
        <el-tab-pane
          label="错误详情"
          name="detail"
        >
          <div class="error-detail">
            <!-- 错误消息 -->
            <div class="detail-section">
              <div
                class="section-header"
                @click="toggleSection('message')"
              >
                <div class="section-title">
                  <el-icon><Message /></el-icon>
                  <h4>错误消息</h4>
                </div>
                <div class="section-actions">
                  <el-button
                    text
                    size="small"
                    @click.stop="copyToClipboard('detail')"
                  >
                    <el-icon><CopyDocument /></el-icon>
                    <span>复制</span>
                  </el-button>
                  <el-icon
                    class="collapse-icon"
                    :class="{ expanded: expandedSections.message }"
                  >
                    <ArrowDown />
                  </el-icon>
                </div>
              </div>
              <el-collapse-transition>
                <div
                  v-show="expandedSections.message"
                  class="detail-content"
                >
                  <pre class="error-text">{{ errorInfo?.message }}</pre>
                </div>
              </el-collapse-transition>
            </div>

            <!-- 错误上下文 -->
            <div
              v-if="errorInfo?.context"
              class="detail-section"
            >
              <div
                class="section-header"
                @click="toggleSection('context')"
              >
                <div class="section-title">
                  <el-icon><InfoFilled /></el-icon>
                  <h4>错误上下文</h4>
                </div>
                <el-icon
                  class="collapse-icon"
                  :class="{ expanded: expandedSections.context }"
                >
                  <ArrowDown />
                </el-icon>
              </div>
              <el-collapse-transition>
                <div
                  v-show="expandedSections.context"
                  class="detail-content"
                >
                  <div class="context-item">
                    <span class="context-label">组件:</span>
                    <span class="context-value">{{ errorInfo.context.component }}</span>
                  </div>
                  <div class="context-item">
                    <span class="context-label">操作:</span>
                    <span class="context-value">{{ errorInfo.context.action }}</span>
                  </div>
                  <div class="context-item">
                    <span class="context-label">路由:</span>
                    <span class="context-value">{{ errorInfo.context.route }}</span>
                  </div>
                  <div
                    v-if="errorInfo.context.userMessage"
                    class="context-item"
                  >
                    <span class="context-label">提示:</span>
                    <span class="context-value highlight">{{ errorInfo.context.userMessage }}</span>
                  </div>
                </div>
              </el-collapse-transition>
            </div>

            <!-- 错误堆栈（可折叠） -->
            <div
              v-if="errorInfo?.stack?.length"
              class="detail-section"
            >
              <div
                class="section-header"
                @click="toggleSection('stack')"
              >
                <div class="section-title">
                  <el-icon><Document /></el-icon>
                  <h4>错误堆栈</h4>
                  <el-tag
                    size="small"
                    type="info"
                  >
                    {{ errorInfo.stack.length }} 行
                  </el-tag>
                </div>
                <div class="section-actions">
                  <el-button
                    text
                    size="small"
                    @click.stop="copyToClipboard('stack')"
                  >
                    <el-icon><CopyDocument /></el-icon>
                    <span>复制</span>
                  </el-button>
                  <el-icon
                    class="collapse-icon"
                    :class="{ expanded: expandedSections.stack }"
                  >
                    <ArrowDown />
                  </el-icon>
                </div>
              </div>
              <el-collapse-transition>
                <div
                  v-show="expandedSections.stack"
                  class="detail-content"
                >
                  <pre class="stack-trace">{{ errorInfo.fullStack }}</pre>
                </div>
              </el-collapse-transition>
            </div>
          </div>
        </el-tab-pane>

        <!-- 系统信息标签页 -->
        <el-tab-pane
          label="系统信息"
          name="system"
        >
          <div
            v-if="errorInfo?.system"
            class="system-info"
          >
            <!-- 基础信息 -->
            <div class="info-section">
              <h4 class="info-title">
                基础信息
              </h4>
              <div class="info-grid">
                <div class="info-item">
                  <span class="info-label">平台:</span>
                  <span class="info-value">{{ errorInfo.system.platform }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">语言:</span>
                  <span class="info-value">{{ errorInfo.system.language }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">在线状态:</span>
                  <el-tag
                    :type="errorInfo.system.online ? 'success' : 'danger'"
                    size="small"
                  >
                    {{ errorInfo.system.online ? '在线' : '离线' }}
                  </el-tag>
                </div>
                <div class="info-item">
                  <span class="info-label">连接类型:</span>
                  <span class="info-value">{{ errorInfo.system.connection?.effectiveType || '未知' }}</span>
                </div>
              </div>
            </div>

            <!-- 视口信息 -->
            <div class="info-section">
              <h4 class="info-title">
                视口信息
              </h4>
              <div class="info-grid">
                <div class="info-item">
                  <span class="info-label">视口尺寸:</span>
                  <span class="info-value">{{ errorInfo.system.viewport.width }} × {{ errorInfo.system.viewport.height }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">屏幕尺寸:</span>
                  <span class="info-value">{{ errorInfo.system.screen.width }} × {{ errorInfo.system.screen.height }}</span>
                </div>
              </div>
            </div>

            <!-- 内存信息 -->
            <div
              v-if="errorInfo.system.memory"
              class="info-section"
            >
              <h4 class="info-title">
                内存使用
              </h4>
              <div class="info-grid">
                <div class="info-item">
                  <span class="info-label">已用堆:</span>
                  <span class="info-value">{{ errorInfo.system.memory.usedJSHeapSize }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">总堆:</span>
                  <span class="info-value">{{ errorInfo.system.memory.totalJSHeapSize }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">堆限制:</span>
                  <span class="info-value">{{ errorInfo.system.memory.jsHeapSizeLimit }}</span>
                </div>
              </div>
            </div>

            <!-- 用户代理 -->
            <div class="info-section">
              <h4 class="info-title">
                用户代理
              </h4>
              <div class="user-agent">
                <pre>{{ errorInfo.system.userAgent }}</pre>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- 操作历史标签页 -->
        <el-tab-pane
          label="操作历史"
          name="history"
        >
          <div
            v-if="errorInfo?.userActions?.length"
            class="action-history"
          >
            <el-timeline>
              <el-timeline-item
                v-for="(action, index) in errorInfo.userActions"
                :key="index"
                :timestamp="formatTimestamp(action.timestamp)"
                placement="top"
                :type="getActionType(index)"
              >
                <div class="action-card">
                  <div class="action-name">
                    {{ action.action }}
                  </div>
                  <div
                    v-if="action.route"
                    class="action-route"
                  >
                    <el-icon><Location /></el-icon>
                    <span>{{ action.route }}</span>
                  </div>
                  <div
                    v-if="action.data"
                    class="action-data"
                  >
                    <pre>{{ JSON.stringify(action.data, null, 2) }}</pre>
                  </div>
                </div>
              </el-timeline-item>
            </el-timeline>
          </div>
          <el-empty
            v-else
            description="暂无操作历史"
          />
        </el-tab-pane>
      </el-tabs>

      <!-- 错误报告 -->
      <div class="error-report">
        <el-button
          type="primary"
          :loading="isGeneratingReport"
          @click="exportReport"
        >
          <el-icon><Download /></el-icon>
          <span>导出错误报告</span>
        </el-button>
      </div>
    </div>

    <!-- 复制成功提示 -->
    <el-dialog
      v-model="copySuccessVisible"
      title="复制成功"
      width="300px"
      append-to-body
      center
      class="copy-success-dialog"
    >
      <div class="copy-success-content">
        <el-icon class="success-icon">
          <CircleCheck />
        </el-icon>
        <p>错误信息已复制到剪贴板</p>
      </div>
    </el-dialog>
  </el-dialog>
</template>

<script setup>
/**
 * @file ErrorDisplay.vue
 * @path src/components/
 * @description 错误显示组件，提供错误详情展示、解决方案指引、系统信息记录和一键复制功能
 *              支持错误分类图标、详情展开/折叠、错误复制等增强功能
 * @author Agent
 * @date 2024-03-07
 */

import { ref, computed, watch, reactive } from 'vue'
import {
  CopyDocument,
  Document,
  Download,
  CircleCheck,
  Location,
  Warning,
  Connection,
  Lock,
  Monitor,
  Timer,
  Clock,
  Key,
  ArrowDown,
  Message,
  InfoFilled,
  SuccessFilled,
  CircleCloseFilled,
  WarningFilled
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import ErrorSolution from './ErrorSolution.vue'
import {
  getErrorIcon,
  getSeverityColor,
  getErrorTypeLabel,
  ERROR_SEVERITY,
  ERROR_TYPES
} from '@/composables/useErrorHandler'

/**
 * Props定义
 */
const props = defineProps({
  /**
   * 对话框可见性
   */
  modelValue: {
    type: Boolean,
    default: false
  },

  /**
   * 错误信息对象
   */
  errorInfo: {
    type: Object,
    default: null
  },

  /**
   * 是否正在生成报告
   */
  isGeneratingReport: {
    type: Boolean,
    default: false
  }
})

/**
 * Emits定义
 */
const emit = defineEmits({
  'update:modelValue': (value) => typeof value === 'boolean',
  'auto-action': (action) => typeof action === 'string',
  'export-report': (report) => typeof report === 'object',
  'copy': (type) => typeof type === 'string',
  'close': () => true
})

/**
 * 当前激活的标签页
 */
const activeTab = ref('solution')

/**
 * 展开的详情区域
 */
const expandedSections = reactive({
  message: true,
  context: true,
  stack: false
})

/**
 * 复制成功提示可见性
 */
const copySuccessVisible = ref(false)

/**
 * 对话框可见性（双向绑定）
 */
const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

/**
 * 对话框标题
 */
const dialogTitle = computed(() => {
  return props.errorInfo?.context?.userMessage || '错误详情'
})

/**
 * 显示标题
 */
const displayTitle = computed(() => {
  return props.errorInfo?.solution?.title || '发生错误'
})

/**
 * 显示消息
 */
const displayMessage = computed(() => {
  return props.errorInfo?.message || '未知错误'
})

/**
 * 错误图标
 */
const errorIcon = computed(() => {
  if (!props.errorInfo?.type) return Warning
  const iconName = getErrorIcon(props.errorInfo.type)
  const iconMap = {
    Connection,
    Lock,
    Warning,
    Monitor,
    Timer,
    Document
  }
  return iconMap[iconName] || Warning
})

/**
 * 严重程度图标
 */
const severityIcon = computed(() => {
  const iconMap = {
    [ERROR_SEVERITY.LOW]: SuccessFilled,
    [ERROR_SEVERITY.MEDIUM]: WarningFilled,
    [ERROR_SEVERITY.HIGH]: CircleCloseFilled,
    [ERROR_SEVERITY.CRITICAL]: CircleCloseFilled
  }
  return iconMap[props.errorInfo?.severity] || WarningFilled
})

/**
 * 错误类型图标组件
 */
const typeIconComponent = computed(() => {
  return errorIcon.value
})

/**
 * 严重程度颜色
 */
const severityColor = computed(() => {
  return getSeverityColor(props.errorInfo?.severity || ERROR_SEVERITY.MEDIUM)
})

/**
 * 严重程度背景色
 */
const severityBgColor = computed(() => {
  const color = severityColor.value
  // 转换为rgba格式，添加透明度
  return color.replace(')', ', 0.1)').replace('rgb', 'rgba')
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
  return typeMap[props.errorInfo?.severity] || 'warning'
})

/**
 * 严重程度标签
 */
const severityLabel = computed(() => {
  const labelMap = {
    [ERROR_SEVERITY.LOW]: '低',
    [ERROR_SEVERITY.MEDIUM]: '中',
    [ERROR_SEVERITY.HIGH]: '高',
    [ERROR_SEVERITY.CRITICAL]: '严重'
  }
  return labelMap[props.errorInfo?.severity] || '中'
})

/**
 * 错误类型标签
 */
const typeLabel = computed(() => {
  return getErrorTypeLabel(props.errorInfo?.type)
})

/**
 * 格式化时间
 */
const formattedTime = computed(() => {
  if (!props.errorInfo?.timestamp) return ''
  return formatTimestamp(props.errorInfo.timestamp)
})

/**
 * 格式化时间戳
 *
 * @param {string} timestamp - ISO时间戳
 * @returns {string} 格式化后的时间字符串
 */
function formatTimestamp(timestamp) {
  if (!timestamp) return ''
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

/**
 * 获取操作类型（用于时间线颜色）
 *
 * @param {number} index - 操作索引
 * @returns {string} 类型
 */
function getActionType(index) {
  const types = ['primary', 'success', 'warning', 'danger', 'info']
  return types[index % types.length]
}

/**
 * 切换详情区域展开/折叠
 *
 * @param {string} section - 区域名称
 */
function toggleSection(section) {
  expandedSections[section] = !expandedSections[section]
}

/**
 * 复制到剪贴板
 *
 * @param {string} type - 复制类型
 */
async function copyToClipboard(type) {
  emit('copy', type)
  // 显示复制成功提示
  copySuccessVisible.value = true
  setTimeout(() => {
    copySuccessVisible.value = false
  }, 1500)
}

/**
 * 导出错误报告
 */
function exportReport() {
  emit('export-report', props.errorInfo)
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
 * 关闭对话框
 */
function handleClose() {
  emit('close')
  // 重置状态
  activeTab.value = 'solution'
  expandedSections.message = true
  expandedSections.context = true
  expandedSections.stack = false
}

/**
 * 监听错误信息变化，重置标签页
 */
watch(() => props.errorInfo, () => {
  activeTab.value = 'solution'
  expandedSections.message = true
  expandedSections.context = true
  expandedSections.stack = false
})
</script>

<style scoped>
.error-display-dialog {
  z-index: var(--z-index-modal);
}

.error-display {
  max-height: 70vh;
  overflow-y: auto;
}

/* 错误概览 */
.error-overview {
  display: flex;
  gap: var(--spacing-4);
  padding: var(--spacing-4);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  margin-bottom: var(--spacing-4);
  border-left: 4px solid transparent;
  transition: var(--transition-all);
}

.error-overview.severity-low {
  border-left-color: var(--color-success);
}

.error-overview.severity-medium {
  border-left-color: var(--color-warning);
}

.error-overview.severity-high {
  border-left-color: var(--color-error);
}

.error-overview.severity-critical {
  border-left-color: var(--color-error-dark);
  background-color: rgba(229, 62, 62, 0.05);
}

.error-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: var(--radius-lg);
  flex-shrink: 0;
}

.error-icon {
  font-size: 32px;
}

.error-info {
  flex: 1;
  min-width: 0;
}

.error-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--spacing-3);
  margin-bottom: var(--spacing-2);
}

.error-title {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.error-actions {
  display: flex;
  gap: var(--spacing-1);
  flex-shrink: 0;
}

.error-message {
  margin: 0 0 var(--spacing-3) 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: var(--line-height-relaxed);
  word-break: break-word;
}

.error-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  flex-wrap: wrap;
}

.tag-icon {
  margin-right: 4px;
  font-size: 12px;
}

.error-time,
.error-id {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

/* 标签页 */
.error-tabs {
  margin-bottom: var(--spacing-4);
}

:deep(.el-tabs__header) {
  margin-bottom: var(--spacing-4);
}

:deep(.el-tabs__item) {
  font-weight: var(--font-weight-medium);
}

/* 错误详情 */
.error-detail {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
}

.detail-section {
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-2) var(--spacing-3);
  background-color: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border-primary);
  cursor: pointer;
  user-select: none;
  transition: var(--transition-all);
}

.section-header:hover {
  background-color: var(--color-interactive-hover);
}

.section-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.section-title h4 {
  margin: 0;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.section-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.collapse-icon {
  transition: transform 0.3s ease;
  color: var(--color-text-tertiary);
}

.collapse-icon.expanded {
  transform: rotate(180deg);
}

.detail-content {
  padding: var(--spacing-3);
}

.error-text {
  margin: 0;
  padding: var(--spacing-3);
  background-color: var(--color-bg-tertiary);
  border-radius: var(--radius-sm);
  font-family: var(--font-family-mono);
  font-size: var(--font-size-sm);
  color: var(--color-error);
  line-height: var(--line-height-normal);
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.context-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) 0;
  border-bottom: 1px solid var(--color-border-secondary);
}

.context-item:last-child {
  border-bottom: none;
}

.context-label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  min-width: 60px;
}

.context-value {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.context-value.highlight {
  color: var(--color-error);
  font-weight: var(--font-weight-medium);
}

.stack-trace {
  margin: 0;
  padding: var(--spacing-3);
  background-color: var(--color-bg-tertiary);
  border-radius: var(--radius-sm);
  font-family: var(--font-family-mono);
  font-size: var(--font-size-xs);
  color: var(--color-text-primary);
  line-height: var(--line-height-normal);
  overflow-x: auto;
  max-height: 300px;
  overflow-y: auto;
}

/* 系统信息 */
.system-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.info-section {
  padding: var(--spacing-3);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
}

.info-title {
  margin: 0 0 var(--spacing-3) 0;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-2);
}

.info-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.info-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.info-value {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  font-family: var(--font-family-mono);
}

.user-agent {
  padding: var(--spacing-2);
  background-color: var(--color-bg-tertiary);
  border-radius: var(--radius-sm);
}

.user-agent pre {
  margin: 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  white-space: pre-wrap;
  word-break: break-all;
}

/* 操作历史 */
.action-history {
  padding: var(--spacing-2);
}

.action-card {
  padding: var(--spacing-3);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
}

.action-name {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-2);
}

.action-route {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-2);
}

.action-data {
  padding: var(--spacing-2);
  background-color: var(--color-bg-tertiary);
  border-radius: var(--radius-sm);
}

.action-data pre {
  margin: 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-primary);
  font-family: var(--font-family-mono);
}

/* 错误报告 */
.error-report {
  display: flex;
  justify-content: center;
  padding-top: var(--spacing-4);
  border-top: 1px solid var(--color-border-primary);
}

/* 复制成功对话框 */
.copy-success-dialog :deep(.el-dialog__body) {
  padding: var(--spacing-4);
}

.copy-success-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-2);
}

.success-icon {
  font-size: 48px;
  color: var(--color-success);
}

.copy-success-content p {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

/* Element Plus 样式覆盖 */
:deep(.el-collapse-item__header) {
  background-color: var(--color-bg-secondary);
  border-bottom: none;
  font-size: var(--font-size-sm);
}

:deep(.el-collapse-item__wrap) {
  border-bottom: none;
}

:deep(.el-collapse-item__content) {
  padding: 0;
}

/* 响应式优化 */
@media (max-width: 768px) {
  .error-overview {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }

  .error-meta {
    justify-content: center;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }
}
</style>
