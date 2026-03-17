/**
 * @file Config.vue
 * @path src/views/settings/
 * @description 系统配置页面，提供配置编辑、导入导出、历史记录等完整功能
 * @author Frontend Engineer Agent
 * @date 2026-03-07
 * @dependencies vue, element-plus, @element-plus/icons-vue, stores/settings, components
 */

<template>
  <div class="settings-config-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <el-icon class="header-icon">
            <Setting />
          </el-icon>
          <div class="header-text">
            <h1 class="page-title">
              系统配置
            </h1>
            <p class="page-subtitle">
              配置系统参数、设备连接与安全策略
            </p>
          </div>
        </div>
        <div class="header-actions">
          <el-button @click="showImportDialog = true">
            <el-icon><Upload /></el-icon>
            导入配置
          </el-button>
          <el-button @click="handleExport">
            <el-icon><Download /></el-icon>
            导出配置
          </el-button>
          <el-button @click="handleReset">
            <el-icon><RefreshLeft /></el-icon>
            重置
          </el-button>
          <el-button
            type="primary"
            :disabled="!settingsStore.hasChanges || settingsStore.hasValidationErrors"
            @click="handleSave"
          >
            <el-icon><Check /></el-icon>
            保存配置
          </el-button>
        </div>
      </div>
    </div>

    <!-- 配置状态指示器 -->
    <div class="status-bar">
      <div class="status-left">
        <el-tag
          v-if="settingsStore.hasChanges"
          type="warning"
          effect="plain"
          size="small"
        >
          <el-icon><Edit /></el-icon>
          有未保存的更改
        </el-tag>
        <el-tag
          v-if="settingsStore.hasValidationErrors"
          type="danger"
          effect="plain"
          size="small"
        >
          <el-icon><WarningFilled /></el-icon>
          存在验证错误
        </el-tag>
        <el-tag
          v-if="!settingsStore.hasChanges && !settingsStore.hasValidationErrors"
          type="success"
          effect="plain"
          size="small"
        >
          <el-icon><CircleCheck /></el-icon>
          配置正常
        </el-tag>
      </div>
      <div class="status-right">
        <span class="version-info">版本：{{ settingsStore.currentVersion }}</span>
        <span
          v-if="lastSavedTime"
          class="last-saved"
        >
          上次保存：{{ formatLastSaved(lastSavedTime) }}
        </span>
      </div>
    </div>

    <!-- 主内容区域 - 扁平化布局 -->
    <div class="config-main">
      <!-- 配置验证错误面板 -->
      <el-card
        v-if="settingsStore.hasValidationErrors"
        class="error-panel"
        shadow="hover"
      >
        <template #header>
          <div class="error-header">
            <div class="error-title">
              <el-icon class="error-icon">
                <WarningFilled />
              </el-icon>
              <span>验证错误</span>
            </div>
            <el-button
              text
              size="small"
              @click="handleClearErrors"
            >
              清除错误
            </el-button>
          </div>
        </template>

        <div class="error-list">
          <div
            v-for="(message, path) in settingsStore.validationErrors"
            :key="path"
            class="error-item"
          >
            <el-icon class="error-icon">
              <CircleClose />
            </el-icon>
            <span class="error-path">{{ path }}</span>
            <span class="error-message">{{ message }}</span>
          </div>
        </div>
      </el-card>

      <!-- 配置编辑器 -->
      <el-card
        class="editor-card"
        shadow="never"
      >
        <ConfigEditor />
      </el-card>

      <!-- 配置历史记录 -->
      <el-card
        class="history-card"
        shadow="never"
      >
        <template #header>
          <div class="card-header">
            <el-icon><Clock /></el-icon>
            <span>配置历史</span>
          </div>
        </template>
        <ConfigHistory />
      </el-card>
    </div>

    <!-- 导入配置对话框 -->
    <el-dialog
      v-model="showImportDialog"
      title="导入配置"
      width="600px"
      class="import-dialog"
    >
      <div class="import-content">
        <el-alert
          title="导入说明"
          type="info"
          :closable="false"
          class="import-alert"
        >
          <p>支持导入 JSON 格式的配置文件。导入前请确保配置文件格式正确。</p>
          <p>导入模式：</p>
          <ul>
            <li><strong>合并模式</strong>：只更新配置文件中提供的配置项，其他配置保持不变</li>
            <li><strong>替换模式</strong>：完全替换当前配置（谨慎使用）</li>
          </ul>
        </el-alert>

        <el-form
          :model="importForm"
          label-width="100px"
          class="import-form"
        >
          <el-form-item label="导入模式">
            <el-radio-group v-model="importForm.mode">
              <el-radio value="merge">
                合并模式
              </el-radio>
              <el-radio value="replace">
                替换模式
              </el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="配置文件">
            <el-upload
              ref="uploadRef"
              :auto-upload="false"
              :limit="1"
              accept=".json"
              :on-change="handleFileChange"
              :on-remove="handleFileRemove"
              drag
              class="upload-area"
            >
              <el-icon class="upload-icon">
                <UploadFilled />
              </el-icon>
              <div class="upload-text">
                将配置文件拖到此处，或<em>点击上传</em>
              </div>
              <template #tip>
                <div class="upload-tip">
                  只能上传 JSON 格式的配置文件
                </div>
              </template>
            </el-upload>
          </el-form-item>

          <el-form-item label="验证配置">
            <el-switch
              v-model="importForm.validate"
              active-text="启用"
              inactive-text="禁用"
            />
          </el-form-item>
        </el-form>

        <!-- 导入预览 -->
        <div
          v-if="importPreview"
          class="import-preview"
        >
          <h4>配置预览</h4>
          <el-descriptions
            :column="1"
            border
            size="small"
          >
            <el-descriptions-item label="版本">
              {{ importPreview.version || '未知' }}
            </el-descriptions-item>
            <el-descriptions-item label="导出时间">
              {{ importPreview.exportTime || '未知' }}
            </el-descriptions-item>
            <el-descriptions-item label="配置分类">
              {{ Object.keys(importPreview.config || {}).join(', ') }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </div>

      <template #footer>
        <el-button @click="showImportDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :disabled="!importFile"
          @click="handleImport"
        >
          确定导入
        </el-button>
      </template>
    </el-dialog>

    <!-- 导出配置对话框 -->
    <el-dialog
      v-model="showExportDialog"
      title="导出配置"
      width="600px"
      class="export-dialog"
    >
      <div class="export-content">
        <el-form
          :model="exportForm"
          label-width="120px"
          class="export-form"
        >
          <el-form-item label="导出分类">
            <el-checkbox-group v-model="exportForm.categories">
              <el-checkbox
                v-for="category in settingsStore.configCategories"
                :key="category.id"
                :value="category.id"
              >
                {{ category.name }}
              </el-checkbox>
            </el-checkbox-group>
          </el-form-item>

          <el-form-item label="包含历史记录">
            <el-switch
              v-model="exportForm.includeHistory"
              active-text="是"
              inactive-text="否"
            />
          </el-form-item>

          <el-form-item label="文件格式">
            <el-radio-group v-model="exportForm.format">
              <el-radio value="json">
                JSON
              </el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>

        <el-alert
          title="导出说明"
          type="info"
          :closable="false"
        >
          导出的配置文件可用于备份或迁移到其他系统。
        </el-alert>
      </div>

      <template #footer>
        <el-button @click="showExportDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="handleConfirmExport"
        >
          确定导出
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * @file Config.vue
 * @path src/views/settings/
 * @description 系统配置页面，提供配置编辑、导入导出、历史记录等完整功能
 * @author Frontend Engineer Agent
 * @date 2026-03-07
 */

import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Setting,
  Check,
  RefreshLeft,
  Upload,
  Download,
  Edit,
  WarningFilled,
  CircleCheck,
  Clock,
  UploadFilled
} from '@element-plus/icons-vue'
import { useSettingsStore } from '@/stores/settings'
import { ConfigEditor, ConfigHistory } from '@/components/settings'

// ==================== Store ====================

const settingsStore = useSettingsStore()

// ==================== 响应式状态 ====================

/** 显示导入对话框 */
const showImportDialog = ref(false)

/** 显示导出对话框 */
const showExportDialog = ref(false)

/** 上传组件引用 */
const uploadRef = ref(null)

/** 导入文件 */
const importFile = ref(null)

/** 导入预览 */
const importPreview = ref(null)

/** 上次保存时间 */
const lastSavedTime = ref(null)

/** 导入表单 */
const importForm = reactive({
  mode: 'merge',
  validate: true
})

/** 导出表单 */
const exportForm = reactive({
  categories: [],
  includeHistory: false,
  format: 'json'
})

// ==================== 生命周期 ====================

onMounted(async () => {
  // 初始化 Store
  await settingsStore.init()

  // 设置默认导出分类
  exportForm.categories = settingsStore.configCategories.map(c => c.id)
})

// ==================== 方法 ====================

/**
 * 保存配置
 */
async function handleSave() {
  // 验证所有配置
  if (!settingsStore.validateAllConfig()) {
    ElMessage.error('配置验证失败，请检查错误项')
    return
  }

  try {
    const success = await settingsStore.saveConfigToServer()

    if (success) {
      ElMessage.success('配置保存成功')
      lastSavedTime.value = new Date()
    } else {
      ElMessage.error('配置保存失败：' + (settingsStore.errorMessage || '未知错误'))
    }
  } catch (error) {
    console.error('[Config] Save error:', error)
    ElMessage.error('配置保存失败：' + (error.message || '未知错误'))
  }
}

/**
 * 重置配置
 */
async function handleReset() {
  try {
    await ElMessageBox.confirm(
      '确定要重置所有配置项为默认值吗？此操作不可撤销。',
      '确认重置',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    settingsStore.resetConfig()
    ElMessage.success('配置已重置')
  } catch {
    // 用户取消操作
  }
}

/**
 * 导出配置
 */
function handleExport() {
  showExportDialog.value = true
}

/**
 * 确认导出
 */
function handleConfirmExport() {
  const options = {
    categories: exportForm.categories.length > 0 ? exportForm.categories : undefined,
    includeHistory: exportForm.includeHistory
  }

  settingsStore.exportConfigToFile(options)
  showExportDialog.value = false
  ElMessage.success('配置导出成功')
}

/**
 * 处理文件选择
 * 
 * @param {Object} file - 文件对象
 */
function handleFileChange(file) {
  importFile.value = file.raw

  // 预览配置
  const reader = new FileReader()
  reader.onload = (event) => {
    try {
      const data = JSON.parse(event.target.result)
      importPreview.value = data
    } catch {
      ElMessage.error('配置文件格式错误')
      importPreview.value = null
    }
  }
  reader.readAsText(file.raw)
}

/**
 * 处理文件移除
 */
function handleFileRemove() {
  importFile.value = null
  importPreview.value = null
}

/**
 * 导入配置
 */
async function handleImport() {
  if (!importFile.value) {
    ElMessage.warning('请选择配置文件')
    return
  }

  try {
    const result = await settingsStore.importConfigFromFile(importFile.value, {
      validate: importForm.validate,
      merge: importForm.mode === 'merge'
    })

    if (result.success) {
      ElMessage.success('配置导入成功')
      showImportDialog.value = false

      // 清理
      importFile.value = null
      importPreview.value = null
      if (uploadRef.value) {
        uploadRef.value.clearFiles()
      }
    } else {
      ElMessage.error(result.message)
      if (result.errors && result.errors.length > 0) {
        console.error('Import errors:', result.errors)
      }
    }
  } catch (error) {
    ElMessage.error('配置导入失败：' + error.message)
  }
}

/**
 * 清除验证错误
 */
function handleClearErrors() {
  settingsStore.clearValidationErrors()
}

/**
 * 格式化上次保存时间
 * 
 * @param {Date} time - 时间对象
 * @returns {string} 格式化后的时间
 */
function formatLastSaved(time) {
  const date = new Date(time)
  const now = new Date()
  const diff = now - date

  // 如果是今天
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

  // 否则显示日期
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')

  return `${month}-${day} ${hour}:${minute}`
}
</script>

<style scoped>
.settings-config-page {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  background-color: var(--color-bg-secondary);
}

/* 页面头部 */
.page-header {
  background-color: var(--color-surface-primary);
  border-bottom: 1px solid var(--color-border-primary);
  padding: var(--spacing-6);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: var(--content-max-width);
  margin: 0 auto;
  width: 100%;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
}

.header-icon {
  font-size: 32px;
  color: var(--color-primary-500);
  padding: var(--spacing-3);
  background-color: var(--color-primary-50);
  border-radius: var(--radius-lg);
  transition: var(--transition-all);
}

.header-icon:hover {
  background-color: var(--color-primary-100);
  transform: scale(1.05);
}

.header-text {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.page-title {
  margin: 0;
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  line-height: var(--line-height-tight);
}

.page-subtitle {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.header-actions {
  display: flex;
  gap: var(--spacing-3);
}

.header-actions .el-button {
  transition: var(--transition-all);
}

.header-actions .el-button:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.header-actions .el-button--primary {
  box-shadow: var(--shadow-glow-primary);
}

/* 状态栏 */
.status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-3) var(--spacing-6);
  background-color: var(--color-surface-primary);
  border-bottom: 1px solid var(--color-border-primary);
}

.status-left {
  display: flex;
  gap: var(--spacing-3);
}

.status-left :deep(.el-tag) {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  transition: var(--transition-all);
}

.status-left :deep(.el-tag:hover) {
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.status-right {
  display: flex;
  gap: var(--spacing-4);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

/* 主内容区域 */
.config-main {
  flex: 1;
  max-width: var(--content-max-width);
  margin: 0 auto;
  width: 100%;
  padding: var(--spacing-6);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-6);
}

/* 错误面板 */
.error-panel {
  border-color: var(--color-error-light);
  border-width: 2px;
  animation: shake 0.3s ease-in-out;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-5px); }
  75% { transform: translateX(5px); }
}

.error-panel :deep(.el-card__header) {
  background-color: rgba(239, 68, 68, 0.05);
  border-bottom-color: var(--color-error-light);
}

.error-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.error-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.error-icon {
  color: var(--color-error);
  font-size: 20px;
  animation: pulse 1s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.error-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.error-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-3);
  background-color: rgba(239, 68, 68, 0.05);
  border-radius: var(--radius-sm);
  border-left: 3px solid var(--color-error);
  transition: var(--transition-all);
}

.error-item:hover {
  background-color: rgba(239, 68, 68, 0.1);
  transform: translateX(4px);
}

.error-item .error-icon {
  color: var(--color-error);
  font-size: 16px;
}

.error-path {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  font-family: var(--font-family-mono);
  font-size: var(--font-size-sm);
}

.error-message {
  color: var(--color-error);
  font-size: var(--font-size-sm);
}

/* 编辑器卡片 */
.editor-card {
  border-radius: var(--radius-lg);
  min-height: 600px;
  border: 1px solid var(--color-border-primary);
  transition: var(--transition-all);
}

.editor-card:hover {
  box-shadow: var(--shadow-md);
  border-color: var(--color-primary-200);
}

.editor-card :deep(.el-card__body) {
  padding: 0;
  height: 100%;
}

/* 历史卡片 */
.history-card {
  border-radius: var(--radius-lg);
  min-height: 400px;
  border: 1px solid var(--color-border-primary);
  transition: var(--transition-all);
}

.history-card:hover {
  box-shadow: var(--shadow-md);
  border-color: var(--color-primary-200);
}

.history-card :deep(.el-card__body) {
  padding: 0;
  height: 100%;
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

/* 导入对话框 */
.import-content {
  padding: var(--spacing-4) 0;
}

.import-alert {
  margin-bottom: var(--spacing-4);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-info-light);
}

.import-alert ul {
  margin: var(--spacing-2) 0 0 var(--spacing-4);
  padding: 0;
}

.import-alert li {
  margin: var(--spacing-1) 0;
}

.import-form {
  margin-top: var(--spacing-4);
}

.import-form :deep(.el-form-item__label) {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
}

.upload-area {
  width: 100%;
}

.upload-area :deep(.el-upload-dragger) {
  width: 100%;
  height: 150px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  border: 2px dashed var(--color-border-primary);
  border-radius: var(--radius-md);
  transition: var(--transition-all);
}

.upload-area :deep(.el-upload-dragger:hover) {
  border-color: var(--color-primary-400);
  background-color: var(--color-primary-50);
}

.upload-icon {
  font-size: 48px;
  color: var(--color-text-placeholder);
  margin-bottom: var(--spacing-2);
  transition: var(--transition-all);
}

.upload-area :deep(.el-upload-dragger:hover) .upload-icon {
  color: var(--color-primary-500);
  transform: scale(1.1);
}

.upload-text {
  color: var(--color-text-secondary);
}

.upload-text em {
  color: var(--color-primary-500);
  font-style: normal;
}

.upload-tip {
  margin-top: var(--spacing-2);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.import-preview {
  margin-top: var(--spacing-4);
  padding: var(--spacing-4);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-secondary);
}

.import-preview h4 {
  margin: 0 0 var(--spacing-3) 0;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

/* 导出对话框 */
.export-content {
  padding: var(--spacing-4) 0;
}

.export-form {
  margin-bottom: var(--spacing-4);
}

.export-form :deep(.el-form-item__label) {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
}

/* Element Plus 样式覆盖 */
:deep(.el-card__header) {
  background-color: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border-primary);
  padding: var(--spacing-4) var(--spacing-6);
}

:deep(.el-card__body) {
  padding: var(--spacing-6);
}

:deep(.el-dialog) {
  border-radius: var(--radius-lg);
}

:deep(.el-dialog__header) {
  border-bottom: 1px solid var(--color-border-secondary);
  padding: var(--spacing-4) var(--spacing-6);
}

:deep(.el-dialog__body) {
  padding: var(--spacing-6);
}

:deep(.el-dialog__footer) {
  border-top: 1px solid var(--color-border-secondary);
  padding: var(--spacing-4) var(--spacing-6);
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-3);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .page-header {
    padding: var(--spacing-4);
  }

  .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-4);
  }

  .header-actions {
    width: 100%;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .header-actions .el-button {
    flex: 1;
    min-width: 100px;
  }

  .page-title {
    font-size: var(--font-size-xl);
  }

  .status-bar {
    flex-direction: column;
    gap: var(--spacing-2);
    align-items: flex-start;
  }

  .config-main {
    padding: var(--spacing-4);
  }

  :deep(.el-card__body) {
    padding: var(--spacing-4);
  }

  .error-item {
    flex-wrap: wrap;
  }

  .error-path {
    word-break: break-all;
  }
}
</style>
