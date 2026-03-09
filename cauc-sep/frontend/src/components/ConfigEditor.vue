/**
 * @file ConfigEditor.vue
 * @path src/components/
 * @description 配置编辑器组件，提供分类配置的编辑、验证和搜索功能
 * @author Frontend Engineer Agent
 * @date 2026-03-07
 * @dependencies vue, element-plus, @element-plus/icons-vue, stores/settings
 */

<template>
  <div class="config-editor">
    <!-- 加载状态 -->
    <div v-if="settingsStore.loading" class="loading-state">
      <el-icon class="loading-icon"><Loading /></el-icon>
      <p>正在加载配置...</p>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="settingsStore.errorMessage && !settingsStore.currentConfig" class="error-state">
      <el-icon class="error-icon"><WarningFilled /></el-icon>
      <p>{{ settingsStore.errorMessage }}</p>
      <el-button type="primary" @click="handleRetry">重试</el-button>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!settingsStore.configCategories || settingsStore.configCategories.length === 0" class="empty-state">
      <el-icon class="empty-icon"><Tools /></el-icon>
      <p>暂无配置项</p>
    </div>

    <!-- 正常内容 -->
    <template v-else>
      <!-- 搜索栏 -->
      <div class="search-bar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索配置项..."
          clearable
          class="search-input"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>

      <!-- 配置分类标签页 -->
      <el-tabs v-model="activeCategory" class="config-tabs" @tab-change="handleCategoryChange">
        <el-tab-pane
          v-for="category in filteredCategories"
          :key="category.id"
          :label="category.name"
          :name="category.id"
        >
          <template #label>
            <div class="tab-label">
              <el-icon class="tab-icon">
                <component :is="category.icon" />
              </el-icon>
              <span>{{ category.name }}</span>
              <el-badge
                v-if="getCategoryErrorCount(category.id) > 0"
                :value="getCategoryErrorCount(category.id)"
                type="danger"
                class="error-badge"
              />
            </div>
          </template>

          <!-- 分类描述 -->
          <div class="category-description">
            <el-icon><InfoFilled /></el-icon>
            <span>{{ category.description }}</span>
          </div>

          <!-- 配置表单 -->
          <el-form
            :model="categoryConfig"
            label-width="140px"
            class="config-form"
            :class="{ 'has-errors': hasCategoryErrors(category.id) }"
          >
            <el-form-item
              v-for="(configItem, key) in categoryConfig"
              :key="key"
              :label="getConfigLabel(key)"
              :error="getFieldError(category.id, key)"
              :class="{ 'is-modified': isFieldModified(category.id, key) }"
            >
              <!-- 布尔类型：开关 -->
              <el-switch
                v-if="typeof configItem === 'boolean'"
                v-model="categoryConfig[key]"
                active-text="启用"
                inactive-text="禁用"
                @change="handleConfigChange(category.id, key, $event)"
              />

              <!-- 数字类型：数字输入框 -->
              <div v-else-if="typeof configItem === 'number'" class="number-input-wrapper">
                <el-input-number
                  v-model="categoryConfig[key]"
                  :min="getNumberConfig(key, 'min')"
                  :max="getNumberConfig(key, 'max')"
                  :step="getNumberConfig(key, 'step', 1)"
                  :precision="getNumberConfig(key, 'precision')"
                  class="number-input"
                  @change="handleConfigChange(category.id, key, $event)"
                />
                <span v-if="getConfigUnit(key)" class="unit">{{ getConfigUnit(key) }}</span>
              </div>

              <!-- 枚举类型：下拉选择 -->
              <el-select
                v-else-if="getSelectOptions(key)"
                v-model="categoryConfig[key]"
                placeholder="请选择"
                class="form-select"
                @change="handleConfigChange(category.id, key, $event)"
              >
                <el-option
                  v-for="option in getSelectOptions(key)"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>

              <!-- 字符串类型：输入框 -->
              <el-input
                v-else
                v-model="categoryConfig[key]"
                :placeholder="getPlaceholder(key)"
                class="form-input"
                @change="handleConfigChange(category.id, key, $event)"
              >
                <template v-if="key.includes('Url') || key.includes('Path')" #prepend>
                  <el-icon><Link /></el-icon>
                </template>
              </el-input>

              <!-- 配置状态指示器 -->
              <div class="config-status">
                <el-tooltip
                  v-if="isFieldModified(category.id, key)"
                  content="已修改"
                  placement="top"
                >
                  <el-icon class="status-icon modified"><Edit /></el-icon>
                </el-tooltip>
                <el-tooltip
                  v-if="getFieldError(category.id, key)"
                  :content="getFieldError(category.id, key)"
                  placement="top"
                >
                  <el-icon class="status-icon error"><WarningFilled /></el-icon>
                </el-tooltip>
              </div>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <!-- 配置状态栏 -->
      <div class="config-status-bar">
        <div class="status-left">
          <el-tag v-if="settingsStore.hasChanges" type="warning" effect="plain">
            <el-icon><Edit /></el-icon>
            有未保存的更改
          </el-tag>
          <el-tag v-if="settingsStore.hasValidationErrors" type="danger" effect="plain">
            <el-icon><WarningFilled /></el-icon>
            存在验证错误
          </el-tag>
        </div>
        <div class="status-right">
          <el-button
            text
            @click="handleResetCategory"
            :disabled="!settingsStore.hasChanges"
          >
            <el-icon><RefreshLeft /></el-icon>
            重置当前分类
          </el-button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
/**
 * @file ConfigEditor.vue
 * @path src/components/
 * @description 配置编辑器组件，提供分类配置的编辑、验证和搜索功能
 * @author Frontend Engineer Agent
 * @date 2026-03-07
 */

import { ref, computed, watch, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Search,
  InfoFilled,
  Edit,
  WarningFilled,
  RefreshLeft,
  Link,
  Tools,
  Monitor,
  Warning,
  Coin,
  Loading
} from '@element-plus/icons-vue'
import { useSettingsStore } from '@/stores/settings'

// ==================== Store ====================

const settingsStore = useSettingsStore()

// ==================== 响应式状态 ====================

/** 搜索关键词 */
const searchKeyword = ref('')

/** 当前激活的分类 */
const activeCategory = ref('general')

/** 当前分类的配置（响应式副本） */
const categoryConfig = reactive({})

// ==================== 配置标签映射 ====================

/**
 * 配置项标签映射
 */
const configLabels = {
  // 通用配置
  systemName: '系统名称',
  language: '系统语言',
  theme: '界面主题',
  samplingRate: '采样频率',
  refreshInterval: '数据刷新间隔',
  logLevel: '日志级别',

  // 设备配置
  defaultDevice: '默认设备',
  connectionTimeout: '连接超时',
  retryAttempts: '重试次数',
  autoReconnect: '自动重连',
  heartbeatInterval: '设备心跳',

  // 网络配置
  apiBaseUrl: 'API地址',
  websocketUrl: 'WebSocket地址',
  requestTimeout: '请求超时',
  maxConnections: '最大连接数',

  // 安全配置
  enableSafetyMonitor: '安全监控',
  temperatureLimit: '温度上限',
  currentLimit: '电流上限',
  voltageLimit: '电压上限',
  enableEmergencyStop: '紧急停止',
  autoShutdown: '自动关机',

  // 数据管理
  autoSave: '自动保存',
  autoSaveInterval: '保存间隔',
  dataRetentionDays: '数据保留',
  backupPath: '备份路径',
  compressionFormat: '压缩格式',
  maxStorageSize: '最大存储空间'
}

/**
 * 配置单位映射
 */
const configUnits = {
  samplingRate: 'Hz',
  refreshInterval: '毫秒',
  connectionTimeout: '毫秒',
  heartbeatInterval: '毫秒',
  requestTimeout: '毫秒',
  temperatureLimit: '°C',
  currentLimit: 'μA',
  voltageLimit: 'V',
  autoSaveInterval: '毫秒',
  dataRetentionDays: '天',
  maxStorageSize: 'MB'
}

/**
 * 数字配置参数映射
 */
const numberConfigs = {
  samplingRate: { min: 10, max: 1000, step: 10 },
  refreshInterval: { min: 100, max: 10000, step: 100 },
  connectionTimeout: { min: 1000, max: 60000, step: 1000 },
  retryAttempts: { min: 0, max: 10, step: 1 },
  heartbeatInterval: { min: 1000, max: 60000, step: 1000 },
  requestTimeout: { min: 1000, max: 120000, step: 1000 },
  maxConnections: { min: 1, max: 50, step: 1 },
  temperatureLimit: { min: 0, max: 200, step: 1 },
  currentLimit: { min: 0, max: 100, step: 0.1, precision: 2 },
  voltageLimit: { min: 0, max: 1000, step: 1 },
  autoSaveInterval: { min: 10000, max: 600000, step: 10000 },
  dataRetentionDays: { min: 1, max: 365, step: 1 },
  maxStorageSize: { min: 100, max: 102400, step: 100 }
}

/**
 * 下拉选项映射
 */
const selectOptions = {
  language: [
    { label: '简体中文', value: 'zh-CN' },
    { label: 'English', value: 'en-US' }
  ],
  theme: [
    { label: '浅色主题', value: 'light' },
    { label: '深色主题', value: 'dark' },
    { label: '跟随系统', value: 'auto' }
  ],
  logLevel: [
    { label: '调试 (DEBUG)', value: 'debug' },
    { label: '信息 (INFO)', value: 'info' },
    { label: '警告 (WARNING)', value: 'warning' },
    { label: '错误 (ERROR)', value: 'error' }
  ],
  defaultDevice: [
    { label: '步进电机', value: 'stepper_01' },
    { label: '压电陶瓷', value: 'piezo_01' },
    { label: '电磁铁', value: 'electromagnet_01' },
    { label: '温控系统', value: 'temp_controller_01' },
    { label: '微电流计', value: 'picoammeter_01' }
  ],
  compressionFormat: [
    { label: 'ZIP', value: 'zip' },
    { label: 'GZIP', value: 'gzip' },
    { label: 'TAR.GZ', value: 'tar.gz' }
  ]
}

// ==================== 计算属性 ====================

/**
 * 过滤后的配置分类
 */
const filteredCategories = computed(() => {
  if (!searchKeyword.value) {
    return settingsStore.configCategories
  }

  const keyword = searchKeyword.value.toLowerCase()
  return settingsStore.configCategories.filter(category => {
    // 匹配分类名称
    if (category.name.toLowerCase().includes(keyword)) {
      return true
    }

    // 匹配配置项
    const config = settingsStore.getCategoryConfig(category.id)
    return Object.keys(config).some(key => {
      const label = configLabels[key] || key
      return label.toLowerCase().includes(keyword)
    })
  })
})

// ==================== 方法 ====================

/**
 * 获取配置项标签
 * 
 * @param {string} key - 配置键
 * @returns {string} 配置标签
 */
function getConfigLabel(key) {
  return configLabels[key] || key
}

/**
 * 获取配置单位
 * 
 * @param {string} key - 配置键
 * @returns {string} 单位
 */
function getConfigUnit(key) {
  return configUnits[key] || ''
}

/**
 * 获取数字配置参数
 * 
 * @param {string} key - 配置键
 * @param {string} param - 参数名
 * @param {any} defaultValue - 默认值
 * @returns {any} 参数值
 */
function getNumberConfig(key, param, defaultValue) {
  const config = numberConfigs[key]
  return config?.[param] ?? defaultValue
}

/**
 * 获取下拉选项
 * 
 * @param {string} key - 配置键
 * @returns {Array|null} 选项列表
 */
function getSelectOptions(key) {
  return selectOptions[key] || null
}

/**
 * 获取占位符
 * 
 * @param {string} key - 配置键
 * @returns {string} 占位符
 */
function getPlaceholder(key) {
  if (key.includes('Url')) {
    return '例如: http://localhost:8000'
  }
  if (key.includes('Path')) {
    return '例如: /data/experiments'
  }
  return '请输入'
}

/**
 * 获取字段错误信息
 * 
 * @param {string} categoryId - 分类ID
 * @param {string} key - 配置键
 * @returns {string} 错误信息
 */
function getFieldError(categoryId, key) {
  const path = `${categoryId}.${key}`
  return settingsStore.validationErrors[path] || ''
}

/**
 * 获取分类错误数量
 * 
 * @param {string} categoryId - 分类ID
 * @returns {number} 错误数量
 */
function getCategoryErrorCount(categoryId) {
  return Object.keys(settingsStore.validationErrors).filter(path => 
    path.startsWith(categoryId)
  ).length
}

/**
 * 检查分类是否有错误
 * 
 * @param {string} categoryId - 分类ID
 * @returns {boolean} 是否有错误
 */
function hasCategoryErrors(categoryId) {
  return getCategoryErrorCount(categoryId) > 0
}

/**
 * 检查字段是否已修改
 * 
 * @param {string} categoryId - 分类ID
 * @param {string} key - 配置键
 * @returns {boolean} 是否已修改
 */
function isFieldModified(categoryId, key) {
  const currentValue = settingsStore.currentConfig[categoryId]?.[key]
  const defaultValue = settingsStore.defaultConfig[categoryId]?.[key]
  return JSON.stringify(currentValue) !== JSON.stringify(defaultValue)
}

/**
 * 处理配置变更
 * 
 * @param {string} categoryId - 分类ID
 * @param {string} key - 配置键
 * @param {any} value - 新值
 */
function handleConfigChange(categoryId, key, value) {
  const success = settingsStore.updateConfig(categoryId, key, value)
  
  if (!success) {
    ElMessage.error('配置更新失败，请检查输入值')
  }
}

/**
 * 处理分类切换
 * 
 * @param {string} categoryId - 分类ID
 */
function handleCategoryChange(categoryId) {
  // 加载当前分类的配置
  loadCategoryConfig(categoryId)
}

/**
 * 加载分类配置
 * 
 * @param {string} categoryId - 分类ID
 */
function loadCategoryConfig(categoryId) {
  const config = settingsStore.getCategoryConfig(categoryId)
  
  // 清空当前配置
  Object.keys(categoryConfig).forEach(key => {
    delete categoryConfig[key]
  })
  
  // 加载新配置
  Object.keys(config).forEach(key => {
    categoryConfig[key] = config[key]
  })
}

/**
 * 重置当前分类配置
 */
function handleResetCategory() {
  settingsStore.resetConfig(activeCategory.value)
  loadCategoryConfig(activeCategory.value)
  ElMessage.success('已重置当前分类配置')
}

/**
 * 重试加载配置
 */
async function handleRetry() {
  try {
    await settingsStore.init()
    ElMessage.success('配置加载成功')
  } catch (error) {
    ElMessage.error('配置加载失败: ' + error.message)
  }
}

// ==================== 生命周期 ====================

onMounted(async () => {
  try {
    // 确保 store 已初始化
    if (!settingsStore.currentConfig || Object.keys(settingsStore.currentConfig).length === 0) {
      await settingsStore.init()
    }
    
    // 等待下一个 tick 确保响应式数据已更新
    await new Promise(resolve => setTimeout(resolve, 0))
    
    // 加载默认分类配置
    loadCategoryConfig(activeCategory.value)
  } catch (error) {
    console.error('[ConfigEditor] Failed to initialize:', error)
    ElMessage.error('配置加载失败：' + error.message)
  }
})

// ==================== 监听器 ====================

// 监听分类切换，确保 store 已初始化后再加载配置
watch(
  activeCategory,
  async (newCategory) => {
    // 等待 store 初始化完成
    if (settingsStore.loading) {
      await new Promise(resolve => setTimeout(resolve, 100))
    }
    loadCategoryConfig(newCategory)
  },
  { immediate: true }
)

// 监听搜索关键词变化
watch(searchKeyword, (keyword) => {
  if (keyword && filteredCategories.value.length > 0) {
    // 如果搜索结果只有一个分类，自动切换
    if (filteredCategories.value.length === 1) {
      activeCategory.value = filteredCategories.value[0].id
    }
  }
})
</script>

<style scoped>
.config-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: var(--color-surface-primary);
}

/* 加载状态 */
.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 400px;
  gap: var(--spacing-4);
}

.loading-icon {
  font-size: 48px;
  color: var(--color-primary-500);
  animation: spin 1s linear infinite;
}

.error-icon {
  font-size: 48px;
  color: var(--color-error);
}

.empty-icon {
  font-size: 48px;
  color: var(--color-text-placeholder);
}

.loading-state p,
.error-state p,
.empty-state p {
  font-size: var(--font-size-lg);
  color: var(--color-text-secondary);
  margin: 0;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* 搜索栏 */
.search-bar {
  padding: var(--spacing-4);
  border-bottom: 1px solid var(--color-border-primary);
}

.search-input {
  max-width: 400px;
}

/* 配置标签页 */
.config-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.config-tabs :deep(.el-tabs__header) {
  margin: 0;
  background-color: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border-primary);
  padding: 0;
}

.config-tabs :deep(.el-tabs__nav-wrap) {
  padding: 0 var(--spacing-4);
  overflow-x: auto;
  overflow-y: hidden;
}

.config-tabs :deep(.el-tabs__nav-wrap::before) {
  display: none;
}

.config-tabs :deep(.el-tabs__nav-scroll) {
  overflow-x: auto;
}

.config-tabs :deep(.el-tabs__item) {
  height: 50px;
  line-height: 50px;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  padding: 0 var(--spacing-6);
  white-space: nowrap;
}

.config-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-6);
  background-color: var(--color-surface-primary);
}

.tab-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.tab-icon {
  font-size: 16px;
}

.error-badge {
  margin-left: var(--spacing-2);
}

/* 分类描述 */
.category-description {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-3) var(--spacing-4);
  margin-bottom: var(--spacing-6);
  background-color: var(--color-primary-50);
  border-radius: var(--radius-md);
  color: var(--color-primary-600);
  font-size: var(--font-size-sm);
}

/* 配置表单 */
.config-form {
  max-width: 900px;
}

.config-form.has-errors :deep(.el-form-item) {
  margin-bottom: var(--spacing-6);
}

.config-form :deep(.el-form-item__label) {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
}

.config-form :deep(.el-form-item) {
  margin-bottom: var(--spacing-6);
  padding-bottom: var(--spacing-4);
  border-bottom: 1px solid var(--color-border-light);
}

.config-form :deep(.el-form-item:last-child) {
  border-bottom: none;
}

.config-form :deep(.el-form-item.is-modified .el-form-item__label::after) {
  content: ' *';
  color: var(--color-accent-500);
}

/* 数字输入框 */
.number-input-wrapper {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.number-input {
  flex: 1;
}

.unit {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  white-space: nowrap;
}

/* 表单控件 */
.form-input,
.form-select {
  width: 100%;
}

/* 配置状态指示器 */
.config-status {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  margin-left: var(--spacing-2);
}

.status-icon {
  font-size: 16px;
}

.status-icon.modified {
  color: var(--color-accent-500);
}

.status-icon.error {
  color: var(--color-error);
}

/* 配置状态栏 */
.config-status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-4);
  background-color: var(--color-bg-secondary);
  border-top: 1px solid var(--color-border-primary);
}

.status-left {
  display: flex;
  gap: var(--spacing-3);
}

.status-left :deep(.el-tag) {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .config-tabs :deep(.el-tabs__content) {
    padding: var(--spacing-4);
  }

  .config-form :deep(.el-form-item__label) {
    text-align: left;
    width: 100% !important;
  }

  .number-input-wrapper {
    flex-direction: column;
    align-items: flex-start;
  }

  .config-status-bar {
    flex-direction: column;
    gap: var(--spacing-3);
  }
}
</style>
