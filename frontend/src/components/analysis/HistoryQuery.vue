<script setup lang="ts">
/**
 * @file HistoryQuery.vue
 * @path src/components/
 * @description 多维度历史数据查询组件，支持时间、设备、实验等多条件筛选
 * @author Agent
 * @date 2024-03-07
 */

import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Clock,
  Search,
  Refresh,
  DocumentCopy,
  Delete,
  Timer,
  Calendar,
  Cpu,
  DataAnalysis,
  ArrowDown,
  ArrowUp,
  Star,
  StarFilled,
  MoreFilled
} from '@element-plus/icons-vue'
import { useHistoryQuery } from '@/composables/useHistoryQuery'

/**
 * Props定义
 */
const props = defineProps({
  /** 是否显示高级选项 */
  showAdvanced: {
    type: Boolean,
    default: false
  },
  /** 可选设备列表 */
  deviceOptions: {
    type: Array,
    default: () => [
      { label: '电机', value: 'motor' },
      { label: '压电陶瓷', value: 'piezo' },
      { label: '电磁铁', value: 'electromagnet' },
      { label: '温度控制器', value: 'temperature' },
      { label: '微电流计', value: 'ammeter' }
    ]
  },
  /** 可选实验列表 */
  experimentOptions: {
    type: Array,
    default: () => []
  },
  /** 可选数据类型列表 */
  dataTypeOptions: {
    type: Array,
    default: () => [
      { label: '位置数据', value: 'position' },
      { label: '温度数据', value: 'temperature' },
      { label: '电流数据', value: 'current' },
      { label: '磁场数据', value: 'magnetic' },
      { label: '电压数据', value: 'voltage' }
    ]
  }
})

/**
 * Emits定义
 */
const emit = defineEmits<{
  (e: 'query', conditions: any): void
  (e: 'reset'): void
  (e: 'template-saved', template: any): void
  (e: 'template-applied', template: any): void
}>()

// ==================== 组合式函数调用 ====================

const {
  queryConditions,
  isQuerying,
  templates,
  history,
  saveTemplate,
  deleteTemplate,
  applyTemplate,
  applyHistory,
  clearHistory,
  deleteHistory,
  resetConditions,
  validateConditions
} = useHistoryQuery({ autoSave: true })

// ==================== 响应式状态 ====================

/** 是否展开高级选项 */
const isAdvancedExpanded = ref(props.showAdvanced)

/** 是否显示模板对话框 */
const showTemplateDialog = ref(false)

/** 是否显示历史对话框 */
const showHistoryDialog = ref(false)

/** 新模板名称 */
const newTemplateName = ref('')

/** 新模板描述 */
const newTemplateDescription = ref('')

/** 当前选中的历史记录 */
const selectedHistoryId = ref('')

/** 快捷时间选项 */
const quickTimeOptions = [
  { label: '最近1小时', value: { value: 1, unit: 'hour' } },
  { label: '最近6小时', value: { value: 6, unit: 'hour' } },
  { label: '最近12小时', value: { value: 12, unit: 'hour' } },
  { label: '最近24小时', value: { value: 24, unit: 'hour' } },
  { label: '最近3天', value: { value: 3, unit: 'day' } },
  { label: '最近7天', value: { value: 7, unit: 'day' } },
  { label: '最近30天', value: { value: 30, unit: 'day' } }
]

/** 时间单位选项 */
const timeUnitOptions = [
  { label: '分钟', value: 'minute' },
  { label: '小时', value: 'hour' },
  { label: '天', value: 'day' },
  { label: '周', value: 'week' },
  { label: '月', value: 'month' }
]

/** 数据质量选项 */
const qualityOptions = [
  { label: '全部', value: '' },
  { label: '优质', value: 'good' },
  { label: '一般', value: 'normal' },
  { label: '较差', value: 'poor' }
]

/** 聚合方式选项 */
const aggregationOptions = [
  { label: '无聚合', value: 'none' },
  { label: '平均值', value: 'avg' },
  { label: '最大值', value: 'max' },
  { label: '最小值', value: 'min' },
  { label: '求和', value: 'sum' }
]

/** 是否可以查询 */
const canQuery = computed(() => {
  return !isQuerying.value
})

// ==================== 方法 ====================

/**
 * 处理查询
 */
function handleQuery() {
  const validation = validateConditions()
  if (!validation.valid) {
    ElMessage.warning(validation.message)
    return
  }

  emit('query', queryConditions)
}

/**
 * 处理重置
 */
function handleReset() {
  resetConditions()
  emit('reset')
  ElMessage.success('查询条件已重置')
}

/**
 * 应用快捷时间
 */
function applyQuickTime(option) {
  queryConditions.timeRange.type = 'relative'
  queryConditions.relativeTime = { ...option.value }
}

/**
 * 打开保存模板对话框
 */
function openSaveTemplateDialog() {
  newTemplateName.value = ''
  newTemplateDescription.value = ''
  showTemplateDialog.value = true
}

/**
 * 确认保存模板
 */
function confirmSaveTemplate() {
  if (!newTemplateName.value.trim()) {
    ElMessage.warning('请输入模板名称')
    return
  }

  const template = saveTemplate(newTemplateName.value, newTemplateDescription.value)
  if (template) {
    showTemplateDialog.value = false
    emit('template-saved', template)
  }
}

/**
 * 处理应用模板
 */
function handleApplyTemplate(templateId) {
  if (applyTemplate(templateId)) {
    const template = templates.value.find(t => t.id === templateId)
    emit('template-applied', template)
  }
}

/**
 * 处理删除模板
 */
async function handleDeleteTemplate(templateId) {
  try {
    await ElMessageBox.confirm('确定要删除此模板吗？', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    deleteTemplate(templateId)
  } catch {
    // 用户取消
  }
}

/**
 * 处理应用历史记录
 */
function handleApplyHistory(historyId) {
  if (applyHistory(historyId)) {
    showHistoryDialog.value = false
  }
}

/**
 * 处理删除历史记录
 */
function handleDeleteHistory(historyId) {
  deleteHistory(historyId)
}

/**
 * 处理清空历史记录
 */
async function handleClearHistory() {
  try {
    await ElMessageBox.confirm('确定要清空所有历史记录吗？', '确认清空', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    clearHistory()
    showHistoryDialog.value = false
  } catch {
    // 用户取消
  }
}

/**
 * 格式化时间戳
 */
function formatTimestamp(timestamp) {
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
 * 格式化相对时间
 */
function formatRelativeTime(value, unit) {
  const unitMap = {
    minute: '分钟',
    hour: '小时',
    day: '天',
    week: '周',
    month: '月'
  }
  return `${value} ${unitMap[unit] || unit}`
}

// ==================== 监听器 ====================

// 监听时间类型变化
watch(() => queryConditions.timeRange.type, (newType) => {
  if (newType === 'relative') {
    // 切换到相对时间时，清空绝对时间
    queryConditions.timeRange.start = null
    queryConditions.timeRange.end = null
  } else {
    // 切换到绝对时间时，设置默认值
    if (!queryConditions.timeRange.start || !queryConditions.timeRange.end) {
      const now = new Date()
      const start = new Date(now.getTime() - 24 * 60 * 60 * 1000)
      queryConditions.timeRange.start = start.toISOString()
      queryConditions.timeRange.end = now.toISOString()
    }
  }
})
</script>

<template>
  <div class="history-query">
    <!-- 查询条件表单 -->
    <el-form
      :model="queryConditions"
      label-width="100px"
      class="query-form"
    >
      <!-- 时间范围选择 -->
      <el-card
        class="query-section"
        shadow="never"
      >
        <template #header>
          <div class="section-header">
            <el-icon><Timer /></el-icon>
            <span>时间范围</span>
          </div>
        </template>

        <!-- 时间类型选择 -->
        <el-form-item label="时间类型">
          <el-radio-group v-model="queryConditions.timeRange.type">
            <el-radio-button label="absolute">
              绝对时间
            </el-radio-button>
            <el-radio-button label="relative">
              相对时间
            </el-radio-button>
          </el-radio-group>
        </el-form-item>

        <!-- 绝对时间选择 -->
        <el-form-item
          v-if="queryConditions.timeRange.type === 'absolute'"
          label="时间范围"
        >
          <el-date-picker
            v-model="queryConditions.timeRange.start"
            type="datetime"
            placeholder="开始时间"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 200px"
          />
          <span class="range-separator">至</span>
          <el-date-picker
            v-model="queryConditions.timeRange.end"
            type="datetime"
            placeholder="结束时间"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 200px"
          />
        </el-form-item>

        <!-- 相对时间选择 -->
        <el-form-item
          v-else
          label="时间范围"
        >
          <div class="relative-time-picker">
            <span>最近</span>
            <el-input-number
              v-model="queryConditions.relativeTime.value"
              :min="1"
              :max="999"
              style="width: 120px; margin: 0 var(--spacing-2)"
            />
            <el-select
              v-model="queryConditions.relativeTime.unit"
              style="width: 100px"
            >
              <el-option
                v-for="opt in timeUnitOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
          </div>
        </el-form-item>

        <!-- 快捷时间选择 -->
        <el-form-item label="快捷选择">
          <el-button-group>
            <el-button
              v-for="opt in quickTimeOptions"
              :key="opt.label"
              size="small"
              @click="applyQuickTime(opt)"
            >
              {{ opt.label }}
            </el-button>
          </el-button-group>
        </el-form-item>
      </el-card>

      <!-- 设备和实验选择 -->
      <el-card
        class="query-section"
        shadow="never"
      >
        <template #header>
          <div class="section-header">
            <el-icon><Cpu /></el-icon>
            <span>设备与实验</span>
          </div>
        </template>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="设备选择">
              <el-select
                v-model="queryConditions.devices"
                multiple
                collapse-tags
                collapse-tags-tooltip
                placeholder="请选择设备"
                style="width: 100%"
              >
                <el-option
                  v-for="opt in deviceOptions"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item label="实验选择">
              <el-select
                v-model="queryConditions.experiments"
                multiple
                collapse-tags
                collapse-tags-tooltip
                placeholder="请选择实验"
                style="width: 100%"
              >
                <el-option
                  v-for="opt in experimentOptions"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </el-card>

      <!-- 数据类型选择 -->
      <el-card
        class="query-section"
        shadow="never"
      >
        <template #header>
          <div class="section-header">
            <el-icon><DataAnalysis /></el-icon>
            <span>数据类型</span>
          </div>
        </template>

        <el-form-item label="数据类型">
          <el-checkbox-group v-model="queryConditions.dataTypes">
            <el-checkbox
              v-for="opt in dataTypeOptions"
              :key="opt.value"
              :label="opt.value"
            >
              {{ opt.label }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-card>

      <!-- 高级选项 -->
      <el-collapse-transition>
        <el-card
          v-show="isAdvancedExpanded"
          class="query-section advanced-section"
          shadow="never"
        >
          <template #header>
            <div class="section-header">
              <el-icon><MoreFilled /></el-icon>
              <span>高级选项</span>
            </div>
          </template>

          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="采样间隔">
                <el-input-number
                  v-model="queryConditions.advanced.sampleInterval"
                  :min="1"
                  :max="3600"
                  style="width: 100%"
                />
                <span class="form-hint">单位：秒</span>
              </el-form-item>
            </el-col>

            <el-col :span="8">
              <el-form-item label="数据质量">
                <el-select
                  v-model="queryConditions.advanced.dataQuality"
                  placeholder="请选择"
                  style="width: 100%"
                >
                  <el-option
                    v-for="opt in qualityOptions"
                    :key="opt.value"
                    :label="opt.label"
                    :value="opt.value"
                  />
                </el-select>
              </el-form-item>
            </el-col>

            <el-col :span="8">
              <el-form-item label="聚合方式">
                <el-select
                  v-model="queryConditions.advanced.aggregation"
                  placeholder="请选择"
                  style="width: 100%"
                >
                  <el-option
                    v-for="opt in aggregationOptions"
                    :key="opt.value"
                    :label="opt.label"
                    :value="opt.value"
                  />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="数值范围">
                <el-row :gutter="10">
                  <el-col :span="11">
                    <el-input-number
                      v-model="queryConditions.advanced.valueRange[0]"
                      placeholder="最小值"
                      style="width: 100%"
                    />
                  </el-col>
                  <el-col
                    :span="2"
                    style="text-align: center"
                  >
                    -
                  </el-col>
                  <el-col :span="11">
                    <el-input-number
                      v-model="queryConditions.advanced.valueRange[1]"
                      placeholder="最大值"
                      style="width: 100%"
                    />
                  </el-col>
                </el-row>
              </el-form-item>
            </el-col>

            <el-col :span="12">
              <el-form-item label="聚合间隔">
                <el-input-number
                  v-model="queryConditions.advanced.aggregationInterval"
                  :min="1"
                  :max="3600"
                  style="width: 100%"
                />
                <span class="form-hint">单位：秒</span>
              </el-form-item>
            </el-col>
          </el-row>
        </el-card>
      </el-collapse-transition>

      <!-- 操作按钮 -->
      <div class="query-actions">
        <div class="left-actions">
          <el-button
            :icon="isAdvancedExpanded ? ArrowUp : ArrowDown"
            @click="isAdvancedExpanded = !isAdvancedExpanded"
          >
            {{ isAdvancedExpanded ? '收起' : '展开' }}高级选项
          </el-button>
          <el-button
            :icon="Star"
            @click="openSaveTemplateDialog"
          >
            保存为模板
          </el-button>
          <el-button
            :icon="Clock"
            @click="showHistoryDialog = true"
          >
            查询历史
          </el-button>
        </div>

        <div class="right-actions">
          <el-button
            :icon="Refresh"
            @click="handleReset"
          >
            重置
          </el-button>
          <el-button
            id="history-query-btn"
            type="primary"
            :icon="Search"
            :loading="isQuerying"
            :disabled="!canQuery"
            @click="handleQuery"
          >
            查询
          </el-button>
        </div>
      </div>

      <!-- 已保存的模板 -->
      <div
        v-if="templates.length > 0"
        class="saved-templates"
      >
        <div class="templates-header">
          <el-icon><StarFilled /></el-icon>
          <span>已保存的模板</span>
        </div>
        <div class="templates-list">
          <el-tag
            v-for="template in templates.slice(0, 5)"
            :key="template.id"
            class="template-tag"
            closable
            @click="handleApplyTemplate(template.id)"
            @close="handleDeleteTemplate(template.id)"
          >
            <el-icon><DocumentCopy /></el-icon>
            {{ template.name }}
          </el-tag>
        </div>
      </div>
    </el-form>

    <!-- 保存模板对话框 -->
    <el-dialog
      v-model="showTemplateDialog"
      title="保存查询模板"
      width="500px"
    >
      <el-form label-width="80px">
        <el-form-item
          label="模板名称"
          required
        >
          <el-input
            v-model="newTemplateName"
            placeholder="请输入模板名称"
            maxlength="50"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="模板描述">
          <el-input
            v-model="newTemplateDescription"
            type="textarea"
            :rows="3"
            placeholder="请输入模板描述（可选）"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showTemplateDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="confirmSaveTemplate"
        >
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 查询历史对话框 -->
    <el-dialog
      v-model="showHistoryDialog"
      title="查询历史"
      width="700px"
    >
      <div class="history-header">
        <span class="history-count">共 {{ history.length }} 条历史记录</span>
        <el-button
          v-if="history.length > 0"
          type="danger"
          size="small"
          :icon="Delete"
          @click="handleClearHistory"
        >
          清空历史
        </el-button>
      </div>

      <el-table
        :data="history"
        max-height="400"
        style="width: 100%"
      >
        <el-table-column
          label="查询时间"
          width="180"
        >
          <template #default="{ row }">
            {{ formatTimestamp(row.timestamp) }}
          </template>
        </el-table-column>

        <el-table-column
          label="查询条件"
          min-width="300"
        >
          <template #default="{ row }">
            <div class="history-conditions">
              <el-tag
                v-if="row.conditions.timeRange.type === 'relative'"
                size="small"
              >
                最近 {{ formatRelativeTime(row.conditions.relativeTime.value, row.conditions.relativeTime.unit) }}
              </el-tag>
              <el-tag
                v-else
                size="small"
              >
                {{ row.conditions.timeRange.start }} ~ {{ row.conditions.timeRange.end }}
              </el-tag>
              <el-tag
                v-if="row.conditions.devices.length > 0"
                size="small"
                type="info"
              >
                {{ row.conditions.devices.length }} 个设备
              </el-tag>
              <el-tag
                v-if="row.conditions.experiments.length > 0"
                size="small"
                type="success"
              >
                {{ row.conditions.experiments.length }} 个实验
              </el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column
          label="结果数"
          width="100"
          align="center"
        >
          <template #default="{ row }">
            {{ row.resultCount }}
          </template>
        </el-table-column>

        <el-table-column
          label="操作"
          width="150"
          align="center"
        >
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              link
              @click="handleApplyHistory(row.id)"
            >
              应用
            </el-button>
            <el-button
              type="danger"
              size="small"
              link
              @click="handleDeleteHistory(row.id)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty
        v-if="history.length === 0"
        description="暂无查询历史"
      />
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.history-query {
  background-color: var(--color-surface-primary);
  border-radius: var(--radius-lg);
}

.query-form {
  padding: var(--spacing-4);
}

.query-section {
  margin-bottom: var(--spacing-4);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);

  :deep(.el-card__header) {
    padding: var(--spacing-3) var(--spacing-4);
    background-color: var(--color-bg-secondary);
    border-bottom: 1px solid var(--color-border-primary);
  }

  :deep(.el-card__body) {
    padding: var(--spacing-4);
  }
}

.section-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);

  .el-icon {
    color: var(--color-primary-500);
    font-size: var(--font-size-lg);
  }
}

.advanced-section {
  border-color: var(--color-primary-200);
  background-color: var(--color-primary-50);
}

.range-separator {
  margin: 0 var(--spacing-3);
  color: var(--color-text-tertiary);
}

.relative-time-picker {
  display: flex;
  align-items: center;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.form-hint {
  display: block;
  margin-top: var(--spacing-1);
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.query-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-4);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  margin-top: var(--spacing-4);
}

.left-actions,
.right-actions {
  display: flex;
  gap: var(--spacing-2);
}

.saved-templates {
  margin-top: var(--spacing-4);
  padding: var(--spacing-3);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
}

.templates-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-3);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);

  .el-icon {
    color: var(--color-warning-500);
  }
}

.templates-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-2);
}

.template-tag {
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-sm);
  }

  .el-icon {
    margin-right: var(--spacing-1);
  }
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-3);
}

.history-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.history-conditions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-1);
}

/* 响应式优化 */
@media (max-width: 768px) {
  .query-actions {
    flex-direction: column;
    gap: var(--spacing-3);
  }

  .left-actions,
  .right-actions {
    width: 100%;
    justify-content: center;
  }
}
</style>
