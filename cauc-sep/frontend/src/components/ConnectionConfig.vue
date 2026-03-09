<template>
  <div class="connection-config">
    <!-- 串口扫描区域 -->
    <el-card class="scan-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <el-icon class="header-icon"><Search /></el-icon>
          <span class="header-title">串口扫描</span>
        </div>
      </template>

      <div class="scan-content">
        <el-button
          type="primary"
          :loading="scanning"
          :disabled="scanning"
          class="scan-btn"
          @click="scanPorts"
        >
          <el-icon><Search /></el-icon>
          <span>{{ scanning ? '扫描中...' : '扫描串口' }}</span>
        </el-button>

        <div v-if="availablePorts.length > 0" class="ports-list">
          <div class="list-header">
            <span class="header-text">发现 {{ availablePorts.length }} 个串口</span>
            <el-button
              text
              type="primary"
              size="small"
              @click="clearPorts"
            >
              清空列表
            </el-button>
          </div>

          <el-table
            :data="availablePorts"
            highlight-current-row
            @current-change="handlePortSelect"
            class="ports-table"
          >
            <el-table-column prop="port" label="串口号" width="100" />
            <el-table-column prop="description" label="设备描述" min-width="150" />
            <el-table-column prop="hwid" label="硬件ID" min-width="180">
              <template #default="{ row }">
                <span class="hwid-text">{{ row.hwid || '未知' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" align="center">
              <template #default="{ row }">
                <el-button
                  type="primary"
                  size="small"
                  text
                  @click.stop="selectPort(row)"
                >
                  选择
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <el-empty
          v-else-if="!scanning"
          description="暂无可用串口，请点击扫描按钮"
          :image-size="80"
        />
      </div>
    </el-card>

    <!-- 连接配置区域 -->
    <el-card class="config-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-icon class="header-icon"><Setting /></el-icon>
            <span class="header-title">连接参数</span>
          </div>
          <div class="header-right">
            <el-dropdown @command="handleTemplateCommand" trigger="click">
              <el-button type="primary" text>
                <el-icon><Document /></el-icon>
                <span>加载模板</span>
                <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item
                    v-for="template in filteredTemplates"
                    :key="template.id"
                    :command="template.id"
                  >
                    <div class="template-item">
                      <span class="template-name">{{ template.name }}</span>
                      <el-tag v-if="template.isDefault" size="small" type="info">默认</el-tag>
                    </div>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </template>

      <el-form
        ref="configFormRef"
        :model="localConfig"
        :rules="configRules"
        label-width="100px"
        class="config-form"
      >
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="串口号" prop="port">
              <el-select
                v-model="localConfig.port"
                placeholder="请选择串口"
                filterable
                allow-create
                class="form-select"
              >
                <el-option
                  v-for="port in portOptions"
                  :key="port.value"
                  :label="port.label"
                  :value="port.value"
                />
              </el-select>
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item label="波特率" prop="baudrate">
              <el-select v-model="localConfig.baudrate" class="form-select">
                <el-option
                  v-for="opt in BAUDRATE_OPTIONS"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="数据位" prop="databits">
              <el-select v-model="localConfig.databits" class="form-select">
                <el-option
                  v-for="opt in DATABITS_OPTIONS"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
            </el-form-item>
          </el-col>

          <el-col :span="8">
            <el-form-item label="停止位" prop="stopbits">
              <el-select v-model="localConfig.stopbits" class="form-select">
                <el-option
                  v-for="opt in STOPBITS_OPTIONS"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
            </el-form-item>
          </el-col>

          <el-col :span="8">
            <el-form-item label="校验位" prop="parity">
              <el-select v-model="localConfig.parity" class="form-select">
                <el-option
                  v-for="opt in PARITY_OPTIONS"
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
            <el-form-item label="流控制" prop="flowcontrol">
              <el-select v-model="localConfig.flowcontrol" class="form-select">
                <el-option
                  v-for="opt in FLOWCONTROL_OPTIONS"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item label="从站地址" prop="slaveId">
              <el-input-number
                v-model="localConfig.slaveId"
                :min="1"
                :max="247"
                class="form-input-number"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="超时时间" prop="timeout">
              <el-input-number
                v-model="localConfig.timeout"
                :min="100"
                :max="10000"
                :step="100"
                class="form-input-number"
              />
              <span class="unit-text">ms</span>
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item label="配置名称" prop="name">
              <el-input
                v-model="localConfig.name"
                placeholder="为配置命名（可选）"
                class="form-input"
              />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <!-- 操作按钮 -->
      <div class="action-buttons">
        <el-button
          type="primary"
          :loading="testing"
          :disabled="testing"
          @click="testConnection"
        >
          <el-icon><Connection /></el-icon>
          <span>测试连接</span>
        </el-button>

        <el-button @click="resetConfig">
          <el-icon><RefreshRight /></el-icon>
          <span>重置</span>
        </el-button>

        <el-button type="success" @click="saveAsTemplate">
          <el-icon><DocumentAdd /></el-icon>
          <span>保存为模板</span>
        </el-button>

        <el-dropdown @command="handleExportCommand" trigger="click">
          <el-button>
            <el-icon><Download /></el-icon>
            <span>导出配置</span>
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="json">导出为 JSON</el-dropdown-item>
              <el-dropdown-item command="clipboard">复制到剪贴板</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <el-button @click="importConfig">
          <el-icon><Upload /></el-icon>
          <span>导入配置</span>
        </el-button>
      </div>
    </el-card>

    <!-- 连接测试结果 -->
    <el-card v-if="testResult" class="result-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <el-icon class="header-icon"><DataAnalysis /></el-icon>
          <span class="header-title">测试结果</span>
        </div>
      </template>

      <div class="test-result" :class="`test-result--${testResult.success ? 'success' : 'error'}`">
        <div class="result-header">
          <el-icon class="result-icon" :class="testResult.success ? 'success-icon' : 'error-icon'">
            <component :is="testResult.success ? 'CircleCheck' : 'CircleClose'" />
          </el-icon>
          <span class="result-title">{{ testResult.success ? '连接成功' : '连接失败' }}</span>
        </div>

        <div v-if="testResult.diagnostics" class="diagnostics">
          <div class="diagnostic-item" v-for="(item, index) in testResult.diagnostics" :key="index">
            <div class="diagnostic-header">
              <el-tag :type="item.level" size="small">{{ item.title }}</el-tag>
            </div>
            <div class="diagnostic-desc">{{ item.description }}</div>
            <ul v-if="item.suggestions && item.suggestions.length > 0" class="suggestions-list">
              <li v-for="(suggestion, sIndex) in item.suggestions" :key="sIndex">
                {{ suggestion }}
              </li>
            </ul>
          </div>
        </div>

        <div v-if="testResult.details" class="result-details">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item
              v-for="(value, key) in testResult.details"
              :key="key"
              :label="key"
            >
              {{ value }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </div>
    </el-card>

    <!-- 保存模板对话框 -->
    <el-dialog
      v-model="saveTemplateDialogVisible"
      title="保存为模板"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form :model="templateForm" label-width="80px">
        <el-form-item label="模板名称" required>
          <el-input v-model="templateForm.name" placeholder="请输入模板名称" />
        </el-form-item>
        <el-form-item label="模板描述">
          <el-input
            v-model="templateForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入模板描述（可选）"
          />
        </el-form-item>
        <el-form-item label="设为默认">
          <el-switch v-model="templateForm.isDefault" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="saveTemplateDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmSaveTemplate">保存</el-button>
      </template>
    </el-dialog>

    <!-- 导入配置对话框 -->
    <el-dialog
      v-model="importDialogVisible"
      title="导入配置"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-input
        v-model="importJsonString"
        type="textarea"
        :rows="10"
        placeholder="请粘贴配置JSON字符串"
      />

      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmImport">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * @file ConnectionConfig.vue
 * @path src/components/
 * @description 连接配置组件，提供串口扫描、参数配置、模板管理等功能
 * @author Agent
 * @date 2024-03-07
 */

import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Setting, Document, ArrowDown, Connection, RefreshRight,
  DocumentAdd, Download, Upload, DataAnalysis, CircleCheck, CircleClose
} from '@element-plus/icons-vue'
import { get, post } from '@/utils/apiRequest'
import {
  BAUDRATE_OPTIONS,
  DATABITS_OPTIONS,
  STOPBITS_OPTIONS,
  PARITY_OPTIONS,
  FLOWCONTROL_OPTIONS,
  CONNECTION_TEMPLATES,
  DEVICE_TYPE_CONFIGS,
  validateConnectionConfig,
  exportConfigToJSON,
  importConfigFromJSON
} from '@/config/connectionTemplates'

/**
 * @typedef {Object} Props
 * @property {string} deviceType - 设备类型
 * @property {Object} modelValue - 配置对象 (v-model)
 */
const props = defineProps({
  deviceType: {
    type: String,
    required: true,
    validator: (value) => Object.keys(DEVICE_TYPE_CONFIGS).includes(value)
  },
  modelValue: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['update:modelValue', 'test-success', 'test-failed'])

// ==================== 响应式状态 ====================

/** 扫描状态 */
const scanning = ref(false)

/** 测试状态 */
const testing = ref(false)

/** 可用串口列表 */
const availablePorts = ref([])

/** 本地配置 */
const localConfig = ref({
  port: '',
  baudrate: 115200,
  databits: 8,
  stopbits: 1,
  parity: 'N',
  flowcontrol: 'none',
  slaveId: 1,
  timeout: 1000,
  name: ''
})

/** 配置表单引用 */
const configFormRef = ref(null)

/** 测试结果 */
const testResult = ref(null)

/** 保存模板对话框 */
const saveTemplateDialogVisible = ref(false)

/** 模板表单 */
const templateForm = ref({
  name: '',
  description: '',
  isDefault: false
})

/** 导入对话框 */
const importDialogVisible = ref(false)

/** 导入JSON字符串 */
const importJsonString = ref('')

/** 自定义模板列表 */
const customTemplates = ref([])

// ==================== 计算属性 ====================

/**
 * 串口选项列表
 */
const portOptions = computed(() => {
  const ports = availablePorts.value.map(p => ({
    label: `${p.port} - ${p.description || '未知设备'}`,
    value: p.port
  }))

  // 添加常用串口选项
  const commonPorts = ['COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8']
  commonPorts.forEach(port => {
    if (!ports.find(p => p.value === port)) {
      ports.push({ label: port, value: port })
    }
  })

  return ports
})

/**
 * 过滤后的模板列表（根据设备类型）
 */
const filteredTemplates = computed(() => {
  return [...CONNECTION_TEMPLATES, ...customTemplates.value].filter(
    t => t.deviceType === props.deviceType
  )
})

/**
 * 配置验证规则
 */
const configRules = {
  port: [{ required: true, message: '请选择串口', trigger: 'change' }],
  baudrate: [{ required: true, message: '请选择波特率', trigger: 'change' }],
  slaveId: [
    { required: true, message: '请输入从站地址', trigger: 'blur' },
    { type: 'number', min: 1, max: 247, message: '从站地址必须在1-247之间', trigger: 'blur' }
  ],
  timeout: [
    { required: true, message: '请输入超时时间', trigger: 'blur' },
    { type: 'number', min: 100, max: 10000, message: '超时时间必须在100-10000ms之间', trigger: 'blur' }
  ]
}

// ==================== 监听器 ====================

/**
 * 监听本地配置变化，同步到父组件
 */
watch(localConfig, (newConfig) => {
  emit('update:modelValue', { ...newConfig })
}, { deep: true })

/**
 * 监听父组件传入的配置
 */
watch(() => props.modelValue, (newConfig) => {
  if (newConfig && Object.keys(newConfig).length > 0) {
    localConfig.value = { ...localConfig.value, ...newConfig }
  }
}, { immediate: true, deep: true })

// ==================== 方法 ====================

/**
 * 扫描可用串口
 */
async function scanPorts() {
  scanning.value = true
  availablePorts.value = []

  try {
    const result = await get('/api/v1/device/ports/scan', null, {
      onError: (msg) => {
        ElMessage.error('扫描串口失败: ' + msg)
      }
    })

    if (result.success && result.data) {
      availablePorts.value = result.data.ports || []
      ElMessage.success(`扫描完成，发现 ${availablePorts.value.length} 个串口`)
    }
  } catch (error) {
    console.error('Scan ports error:', error)
    ElMessage.error('扫描串口时发生错误')
  } finally {
    scanning.value = false
  }
}

/**
 * 清空串口列表
 */
function clearPorts() {
  availablePorts.value = []
}

/**
 * 处理串口选择
 *
 * @param {Object} row - 选中的行数据
 */
function handlePortSelect(row) {
  if (row) {
    localConfig.value.port = row.port
  }
}

/**
 * 选择串口
 *
 * @param {Object} port - 端口信息
 */
function selectPort(port) {
  localConfig.value.port = port.port
  ElMessage.success(`已选择串口 ${port.port}`)
}

/**
 * 加载模板
 *
 * @param {string} templateId - 模板ID
 */
function handleTemplateCommand(templateId) {
  const template = filteredTemplates.value.find(t => t.id === templateId)
  if (template) {
    localConfig.value = {
      ...localConfig.value,
      ...template.config,
      name: template.name
    }
    ElMessage.success(`已加载模板: ${template.name}`)
  }
}

/**
 * 测试连接
 */
async function testConnection() {
  // 验证配置
  const validation = validateConnectionConfig(localConfig.value)
  if (!validation.valid) {
    ElMessage.error('配置验证失败: ' + validation.errors.join(', '))
    return
  }

  testing.value = true
  testResult.value = null

  try {
    const result = await post('/api/v1/device/test_connection', {
      device_type: props.deviceType,
      config: localConfig.value
    }, {
      onError: (msg) => {
        testResult.value = {
          success: false,
          diagnostics: [{
            level: 'error',
            title: '连接测试失败',
            description: msg,
            suggestions: ['检查配置参数是否正确', '确认设备已正确连接']
          }]
        }
        emit('test-failed', testResult.value)
      }
    })

    if (result.success && result.data) {
      testResult.value = {
        success: result.data.success,
        diagnostics: result.data.diagnostics || [],
        details: result.data.details || null
      }

      if (result.data.success) {
        ElMessage.success('连接测试成功')
        emit('test-success', testResult.value)
      } else {
        ElMessage.warning('连接测试失败，请查看诊断信息')
        emit('test-failed', testResult.value)
      }
    }
  } catch (error) {
    console.error('Test connection error:', error)
    testResult.value = {
      success: false,
      diagnostics: [{
        level: 'error',
        title: '测试异常',
        description: error.message || '未知错误',
        suggestions: ['检查网络连接', '确认后端服务正常运行']
      }]
    }
    emit('test-failed', testResult.value)
  } finally {
    testing.value = false
  }
}

/**
 * 重置配置
 */
function resetConfig() {
  const deviceConfig = DEVICE_TYPE_CONFIGS[props.deviceType]
  if (deviceConfig) {
    localConfig.value = {
      port: '',
      ...deviceConfig.defaultConfig,
      name: ''
    }
    testResult.value = null
    ElMessage.info('配置已重置')
  }
}

/**
 * 保存为模板
 */
function saveAsTemplate() {
  templateForm.value = {
    name: localConfig.value.name || `${DEVICE_TYPE_CONFIGS[props.deviceType].name}配置`,
    description: '',
    isDefault: false
  }
  saveTemplateDialogVisible.value = true
}

/**
 * 确认保存模板
 */
function confirmSaveTemplate() {
  if (!templateForm.value.name) {
    ElMessage.warning('请输入模板名称')
    return
  }

  const newTemplate = {
    id: `custom_${Date.now()}`,
    name: templateForm.value.name,
    deviceType: props.deviceType,
    description: templateForm.value.description,
    config: { ...localConfig.value },
    isDefault: templateForm.value.isDefault
  }

  customTemplates.value.push(newTemplate)
  saveTemplatesToStorage()

  saveTemplateDialogVisible.value = false
  ElMessage.success('模板保存成功')
}

/**
 * 导出配置
 *
 * @param {string} command - 导出命令
 */
async function handleExportCommand(command) {
  const configData = {
    deviceType: props.deviceType,
    ...localConfig.value,
    exportedAt: new Date().toISOString()
  }

  if (command === 'json') {
    const jsonStr = exportConfigToJSON(configData)
    const blob = new Blob([jsonStr], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `connection_config_${props.deviceType}_${Date.now()}.json`
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success('配置已导出为JSON文件')
  } else if (command === 'clipboard') {
    const jsonStr = exportConfigToJSON(configData)
    await navigator.clipboard.writeText(jsonStr)
    ElMessage.success('配置已复制到剪贴板')
  }
}

/**
 * 导入配置
 */
function importConfig() {
  importJsonString.value = ''
  importDialogVisible.value = true
}

/**
 * 确认导入配置
 */
function confirmImport() {
  try {
    const config = importConfigFromJSON(importJsonString.value)
    localConfig.value = {
      ...localConfig.value,
      ...config
    }
    importDialogVisible.value = false
    ElMessage.success('配置导入成功')
  } catch (error) {
    ElMessage.error('配置导入失败: ' + error.message)
  }
}

/**
 * 从localStorage加载自定义模板
 */
function loadTemplatesFromStorage() {
  try {
    const stored = localStorage.getItem(`connection_templates_${props.deviceType}`)
    if (stored) {
      customTemplates.value = JSON.parse(stored)
    }
  } catch (error) {
    console.error('Load templates error:', error)
  }
}

/**
 * 保存自定义模板到localStorage
 */
function saveTemplatesToStorage() {
  try {
    localStorage.setItem(
      `connection_templates_${props.deviceType}`,
      JSON.stringify(customTemplates.value)
    )
  } catch (error) {
    console.error('Save templates error:', error)
  }
}

// ==================== 生命周期 ====================

onMounted(() => {
  loadTemplatesFromStorage()
})
</script>

<style scoped>
.connection-config {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

/* 卡片通用样式 */
.scan-card,
.config-card,
.result-card {
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  transition: var(--transition-all);
}

.scan-card:hover,
.config-card:hover,
.result-card:hover {
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

/* 扫描区域样式 */
.scan-content {
  padding: var(--spacing-2) 0;
}

.scan-btn {
  width: 100%;
  height: 44px;
  font-weight: var(--font-weight-medium);
}

.ports-list {
  margin-top: var(--spacing-4);
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-3);
}

.header-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

.ports-table {
  border-radius: var(--radius-md);
  overflow: hidden;
}

.hwid-text {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

/* 配置表单样式 */
.config-form {
  margin-top: var(--spacing-2);
}

.form-select,
.form-input-number,
.form-input {
  width: 100%;
}

.unit-text {
  margin-left: var(--spacing-2);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

/* 操作按钮样式 */
.action-buttons {
  display: flex;
  gap: var(--spacing-3);
  margin-top: var(--spacing-4);
  padding-top: var(--spacing-4);
  border-top: 1px solid var(--color-border-primary);
  flex-wrap: wrap;
}

.action-buttons .el-button {
  flex: 1;
  min-width: 120px;
}

/* 测试结果样式 */
.test-result {
  padding: var(--spacing-4);
  border-radius: var(--radius-md);
  background: var(--color-bg-secondary);
}

.test-result--success {
  border-left: 4px solid var(--color-success);
}

.test-result--error {
  border-left: 4px solid var(--color-error);
}

.result-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  margin-bottom: var(--spacing-4);
}

.result-icon {
  font-size: 32px;
}

.success-icon {
  color: var(--color-success);
}

.error-icon {
  color: var(--color-error);
}

.result-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.diagnostics {
  margin-bottom: var(--spacing-4);
}

.diagnostic-item {
  padding: var(--spacing-3);
  margin-bottom: var(--spacing-3);
  background: var(--color-surface-primary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
}

.diagnostic-header {
  margin-bottom: var(--spacing-2);
}

.diagnostic-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-2);
}

.suggestions-list {
  margin: 0;
  padding-left: var(--spacing-5);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.suggestions-list li {
  margin-bottom: var(--spacing-1);
}

.result-details {
  margin-top: var(--spacing-3);
}

/* 模板项样式 */
.template-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.template-name {
  font-weight: var(--font-weight-medium);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .action-buttons {
    flex-direction: column;
  }

  .action-buttons .el-button {
    width: 100%;
    min-width: auto;
  }
}
</style>
