<template>
  <div class="device-connection-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-main">
        <div class="header-left">
          <el-icon class="header-icon">
            <Link />
          </el-icon>
          <div class="header-content">
            <h1 class="page-title">
              设备连接配置
            </h1>
            <p class="page-subtitle">
              管理设备串口连接、配置模板和实时数据通信
            </p>
          </div>
        </div>
        <div class="header-right">
          <div class="status-indicators">
            <div
              class="status-indicator"
              :class="`status-indicator--${devicesStore.systemStatusType}`"
            >
              <span class="status-dot" />
              <span class="status-text">{{ devicesStore.systemStatusText }}</span>
            </div>
            <div class="connection-counter">
              <span class="counter-label">已连接</span>
              <span class="counter-value">{{ connectedCount }}/{{ totalDevicesCount }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 主内容区域 -->
    <div class="content-wrapper">
      <el-row
        :gutter="24"
        class="content-row"
      >
        <el-col
          :xs="24"
          :lg="16"
        >
          <!-- 设备连接配置标签页 -->
          <el-card class="config-card">
            <el-tabs
              v-model="activeTab"
              class="config-tabs"
            >
              <!-- 单设备配置 -->
              <el-tab-pane
                label="设备配置"
                name="single"
              >
                <div class="tab-content">
                  <!-- 设备选择器卡片 -->
                  <div class="device-selector-card">
                    <div class="selector-header">
                      <h3 class="selector-title">
                        <el-icon><Monitor /></el-icon>
                        选择设备
                      </h3>
                    </div>
                    <div class="selector-body">
                      <el-select 
                        v-model="selectedDevice" 
                        placeholder="请选择要配置的设备" 
                        class="device-select"
                        size="large"
                      >
                        <el-option
                          v-for="device in deviceOptions"
                          :key="device.value"
                          :label="device.label"
                          :value="device.value"
                        >
                          <div class="device-option">
                            <span class="device-name">{{ device.label }}</span>
                            <el-tag 
                              :type="device.connected ? 'success' : 'info'" 
                              size="small"
                              effect="plain"
                            >
                              {{ device.connected ? '已连接' : '未连接' }}
                            </el-tag>
                          </div>
                        </el-option>
                      </el-select>
                    </div>
                  </div>

                  <!-- 配置表单区域 -->
                  <div
                    v-if="selectedDevice"
                    class="config-form-section"
                  >
                    <ConnectionConfig
                      v-model="currentConfig"
                      :device-type="selectedDevice"
                      @test-success="handleTestSuccess"
                      @test-failed="handleTestFailed"
                    />
                  </div>

                  <el-empty
                    v-else
                    description="请先选择要配置的设备"
                    :image-size="120"
                  />
                </div>
              </el-tab-pane>

              <!-- 多设备管理 -->
              <el-tab-pane
                label="多设备管理"
                name="multi"
              >
                <div class="tab-content">
                  <!-- 快速操作工具栏 -->
                  <div class="quick-actions-toolbar">
                    <div class="toolbar-left">
                      <el-button
                        type="primary"
                        @click="connectSelectedDevices"
                      >
                        <el-icon><Connection /></el-icon>
                        连接选中设备
                      </el-button>
                      <el-button
                        type="danger"
                        @click="disconnectSelectedDevices"
                      >
                        <el-icon><CircleClose /></el-icon>
                        断开选中设备
                      </el-button>
                    </div>
                    <div class="toolbar-right">
                      <el-button @click="selectAllDevices">
                        <el-icon><Check /></el-icon>
                        全选
                      </el-button>
                      <el-button @click="clearDeviceSelection">
                        <el-icon><Close /></el-icon>
                        清空选择
                      </el-button>
                    </div>
                  </div>

                  <!-- 设备列表表格 -->
                  <el-table
                    ref="deviceTableRef"
                    :data="deviceList"
                    class="device-table"
                    stripe
                    @selection-change="handleSelectionChange"
                  >
                    <el-table-column
                      type="selection"
                      width="55"
                      align="center"
                    />
                    <el-table-column
                      prop="name"
                      label="设备名称"
                      min-width="140"
                    >
                      <template #default="{ row }">
                        <div class="device-name-cell">
                          <span class="device-name-text">{{ row.name }}</span>
                        </div>
                      </template>
                    </el-table-column>
                    <el-table-column
                      label="连接状态"
                      width="120"
                      align="center"
                    >
                      <template #default="{ row }">
                        <div
                          class="status-badge"
                          :class="row.isConnected ? 'status-badge--success' : 'status-badge--default'"
                        >
                          <span class="badge-dot" />
                          <span>{{ row.isConnected ? '已连接' : '未连接' }}</span>
                        </div>
                      </template>
                    </el-table-column>
                    <el-table-column
                      label="健康状态"
                      width="120"
                      align="center"
                    >
                      <template #default="{ row }">
                        <el-tag
                          :type="getHealthType(row.health)"
                          size="small"
                          effect="plain"
                        >
                          {{ getHealthText(row.health) }}
                        </el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column
                      label="配置信息"
                      min-width="220"
                    >
                      <template #default="{ row }">
                        <div
                          v-if="row.config"
                          class="config-tags"
                        >
                          <el-tag
                            size="small"
                            type="info"
                            effect="plain"
                          >
                            {{ row.config.port }}
                          </el-tag>
                          <el-tag
                            size="small"
                            type="info"
                            effect="plain"
                          >
                            {{ row.config.baudrate }}
                          </el-tag>
                          <el-tag
                            size="small"
                            type="info"
                            effect="plain"
                          >
                            ID: {{ row.config.slaveId }}
                          </el-tag>
                        </div>
                        <span
                          v-else
                          class="no-config-text"
                        >未配置</span>
                      </template>
                    </el-table-column>
                    <el-table-column
                      label="操作"
                      width="200"
                      fixed="right"
                      align="center"
                    >
                      <template #default="{ row }">
                        <el-button-group class="action-buttons">
                          <el-button
                            type="primary"
                            size="small"
                            text
                            @click="editDeviceConfig(row)"
                          >
                            配置
                          </el-button>
                          <el-button
                            type="success"
                            size="small"
                            text
                            :disabled="row.isConnected"
                            @click="connectDevice(row.id)"
                          >
                            连接
                          </el-button>
                          <el-button
                            type="danger"
                            size="small"
                            text
                            :disabled="!row.isConnected"
                            @click="disconnectDevice(row.id)"
                          >
                            断开
                          </el-button>
                        </el-button-group>
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </el-tab-pane>

              <!-- 配置模板管理 -->
              <el-tab-pane
                label="配置模板"
                name="templates"
              >
                <div class="tab-content">
                  <!-- 模板操作工具栏 -->
                  <div class="template-toolbar">
                    <div class="toolbar-left">
                      <el-button
                        type="primary"
                        @click="createNewTemplate"
                      >
                        <el-icon><Plus /></el-icon>
                        新建模板
                      </el-button>
                    </div>
                    <div class="toolbar-right">
                      <el-button @click="importTemplates">
                        <el-icon><Upload /></el-icon>
                        导入
                      </el-button>
                      <el-button @click="exportTemplates">
                        <el-icon><Download /></el-icon>
                        导出
                      </el-button>
                    </div>
                  </div>

                  <!-- 模板列表表格 -->
                  <el-table
                    :data="allTemplates"
                    class="template-table"
                    stripe
                  >
                    <el-table-column
                      prop="name"
                      label="模板名称"
                      min-width="180"
                    >
                      <template #default="{ row }">
                        <div class="template-name-cell">
                          <span class="template-name">{{ row.name }}</span>
                          <el-tag
                            v-if="row.isDefault"
                            type="success"
                            size="small"
                            effect="plain"
                          >
                            默认
                          </el-tag>
                        </div>
                      </template>
                    </el-table-column>
                    <el-table-column
                      prop="deviceType"
                      label="设备类型"
                      width="140"
                    >
                      <template #default="{ row }">
                        <el-tag
                          size="small"
                          effect="plain"
                        >
                          {{ getDeviceTypeName(row.deviceType) }}
                        </el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column
                      prop="description"
                      label="描述"
                      min-width="200"
                      show-overflow-tooltip
                    />
                    <el-table-column
                      label="配置预览"
                      width="180"
                    >
                      <template #default="{ row }">
                        <div class="config-preview">
                          <span class="preview-item">{{ row.config.port }}</span>
                          <span class="preview-item">{{ row.config.baudrate }}</span>
                        </div>
                      </template>
                    </el-table-column>
                    <el-table-column
                      label="操作"
                      width="180"
                      fixed="right"
                      align="center"
                    >
                      <template #default="{ row }">
                        <el-button-group class="action-buttons">
                          <el-button
                            type="primary"
                            size="small"
                            text
                            @click="applyTemplate(row)"
                          >
                            应用
                          </el-button>
                          <el-button
                            type="primary"
                            size="small"
                            text
                            @click="editTemplate(row)"
                          >
                            编辑
                          </el-button>
                          <el-button
                            type="danger"
                            size="small"
                            text
                            @click="deleteTemplate(row)"
                          >
                            删除
                          </el-button>
                        </el-button-group>
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </el-tab-pane>
            </el-tabs>
          </el-card>
        </el-col>
        
        <!-- 右侧状态面板 -->
        <el-col
          :xs="24"
          :lg="8"
        >
          <!-- 系统状态卡片 -->
          <el-card class="status-overview-card">
            <template #header>
              <div class="card-header">
                <el-icon class="header-icon">
                  <DataLine />
                </el-icon>
                <span class="header-title">系统状态</span>
              </div>
            </template>

            <div class="status-grid">
              <div class="status-item">
                <div class="status-icon-wrapper status-icon--primary">
                  <el-icon><Connection /></el-icon>
                </div>
                <div class="status-info">
                  <div class="status-label">
                    已连接设备
                  </div>
                  <div class="status-value">
                    {{ connectedCount }} / {{ totalDevicesCount }}
                  </div>
                </div>
              </div>

              <div class="status-item">
                <div
                  class="status-icon-wrapper"
                  :class="`status-icon--${devicesStore.systemHealthType}`"
                >
                  <el-icon><Monitor /></el-icon>
                </div>
                <div class="status-info">
                  <div class="status-label">
                    系统健康度
                  </div>
                  <div class="status-value">
                    {{ devicesStore.systemHealthText }}
                  </div>
                </div>
              </div>

              <div class="status-item">
                <div
                  class="status-icon-wrapper"
                  :class="unacknowledgedAlarmsCount > 0 ? 'status-icon--danger' : 'status-icon--success'"
                >
                  <el-icon><Bell /></el-icon>
                </div>
                <div class="status-info">
                  <div class="status-label">
                    未确认告警
                  </div>
                  <div class="status-value">
                    {{ unacknowledgedAlarmsCount }}
                  </div>
                </div>
              </div>

              <div class="status-item">
                <div class="status-icon-wrapper status-icon--primary">
                  <el-icon><Timer /></el-icon>
                </div>
                <div class="status-info">
                  <div class="status-label">
                    连接时长
                  </div>
                  <div class="status-value mono">
                    {{ connectionDuration }}
                  </div>
                </div>
              </div>
            </div>
          </el-card>

          <!-- 连接指南卡片 -->
          <el-card class="guide-card">
            <template #header>
              <div class="card-header">
                <el-icon class="header-icon">
                  <Document />
                </el-icon>
                <span class="header-title">连接指南</span>
              </div>
            </template>
            
            <el-timeline class="guide-timeline">
              <el-timeline-item
                v-for="(step, index) in connectionSteps"
                :key="index"
                :icon="step.icon"
                :type="step.type"
                :size="step.size"
              >
                <div class="timeline-content">
                  <div class="step-title">
                    {{ step.title }}
                  </div>
                  <div class="step-desc">
                    {{ step.description }}
                  </div>
                </div>
              </el-timeline-item>
            </el-timeline>
          </el-card>

          <!-- 连接提示卡片 -->
          <el-card class="tips-card">
            <template #header>
              <div class="card-header">
                <el-icon class="header-icon">
                  <InfoFilled />
                </el-icon>
                <span class="header-title">连接提示</span>
              </div>
            </template>
            
            <div class="tips-list">
              <el-alert
                v-for="(tip, index) in connectionTips"
                :key="index"
                :title="tip.title"
                :type="tip.type"
                :description="tip.description"
                :closable="false"
                show-icon
                class="tip-alert"
              />
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 设备配置对话框 -->
    <el-dialog
      v-model="deviceConfigDialogVisible"
      :title="`配置 ${currentDeviceName}`"
      width="700px"
      :close-on-click-modal="false"
    >
      <ConnectionConfig
        v-if="deviceConfigDialogVisible"
        v-model="tempConfig"
        :device-type="currentDeviceId"
        @test-success="handleTestSuccess"
        @test-failed="handleTestFailed"
      />

      <template #footer>
        <el-button @click="deviceConfigDialogVisible = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="saveDeviceConfig"
        >
          保存配置
        </el-button>
      </template>
    </el-dialog>

    <!-- 模板编辑对话框 -->
    <el-dialog
      v-model="templateDialogVisible"
      :title="templateForm.id ? '编辑模板' : '新建模板'"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form
        :model="templateForm"
        label-width="100px"
      >
        <el-form-item
          label="模板名称"
          required
        >
          <el-input
            v-model="templateForm.name"
            placeholder="请输入模板名称"
          />
        </el-form-item>
        <el-form-item
          label="设备类型"
          required
        >
          <el-select
            v-model="templateForm.deviceType"
            placeholder="请选择设备类型"
          >
            <el-option
              v-for="device in deviceOptions"
              :key="device.value"
              :label="device.label"
              :value="device.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="templateForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入模板描述"
          />
        </el-form-item>
        <el-form-item label="设为默认">
          <el-switch v-model="templateForm.isDefault" />
        </el-form-item>
      </el-form>

      <el-divider>连接参数</el-divider>

      <el-form
        :model="templateForm.config"
        label-width="100px"
      >
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="串口号">
              <el-input
                v-model="templateForm.config.port"
                placeholder="如: COM3"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="波特率">
              <el-select v-model="templateForm.config.baudrate">
                <el-option
                  label="9600"
                  :value="9600"
                />
                <el-option
                  label="19200"
                  :value="19200"
                />
                <el-option
                  label="38400"
                  :value="38400"
                />
                <el-option
                  label="57600"
                  :value="57600"
                />
                <el-option
                  label="115200"
                  :value="115200"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="从站地址">
              <el-input-number
                v-model="templateForm.config.slaveId"
                :min="1"
                :max="247"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="超时时间">
              <el-input-number
                v-model="templateForm.config.timeout"
                :min="100"
                :max="10000"
                :step="100"
              />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <el-button @click="templateDialogVisible = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="saveTemplate"
        >
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * @file Connection.vue
 * @path src/views/device/
 * @description 设备连接配置页面，提供设备连接管理、配置模板和多设备管理功能
 * @author Agent
 * @date 2024-03-07
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Link, Connection, Document, InfoFilled, DataLine, Timer,
  Check, Close, CircleClose, Plus, Upload, Download, Monitor, Bell
} from '@element-plus/icons-vue'
import { useDevicesStore } from '@/stores/devices'
import { useMotorStore } from '@/stores/motor'
import { CONNECTION_TEMPLATES, DEVICE_TYPE_CONFIGS } from '@/config/connectionTemplates'
import { ConnectionConfig } from '@/components/device'

const devicesStore = useDevicesStore()
const motorStore = useMotorStore()

// ==================== 响应式状态 ====================

/** 当前激活的标签页 */
const activeTab = ref('single')

/** 选中的设备 */
const selectedDevice = ref('motor')

/** 当前配置 */
const currentConfig = ref({})

/** 选中的设备列表 */
const selectedDevices = ref([])

/** 设备表格引用 */
const deviceTableRef = ref(null)

/** 设备配置对话框 */
const deviceConfigDialogVisible = ref(false)
const currentDeviceId = ref('')
const currentDeviceName = ref('')
const tempConfig = ref({})

/** 模板对话框 */
const templateDialogVisible = ref(false)
const templateForm = ref({
  id: '',
  name: '',
  deviceType: '',
  description: '',
  isDefault: false,
  config: {
    port: '',
    baudrate: 115200,
    databits: 8,
    stopbits: 1,
    parity: 'N',
    flowcontrol: 'none',
    slaveId: 1,
    timeout: 1000
  }
})

/** 连接时长计时器 */
const connectionTimer = ref(null)
const connectionSeconds = ref(0)

// ==================== 计算属性 ====================

/** 设备选项列表 */
const deviceOptions = computed(() => {
  return Object.entries(devicesStore.DEVICE_NAMES).map(([id, name]) => ({
    value: id,
    label: name,
    connected: devicesStore.devices[id]?.isConnected || false
  }))
})

/** 设备列表 */
const deviceList = computed(() => {
  return Object.entries(devicesStore.devices).map(([id, device]) => ({
    id,
    name: device.name,
    isConnected: device.isConnected,
    health: device.health,
    config: devicesStore.connectionConfigs[id] || null
  }))
})

/** 所有模板（包括预定义和自定义） */
const allTemplates = computed(() => {
  return [...CONNECTION_TEMPLATES, ...devicesStore.configTemplates]
})

/** 已连接设备数量 */
const connectedCount = computed(() => devicesStore.connectedCount)

/** 总设备数量 */
const totalDevicesCount = computed(() => devicesStore.totalDevicesCount)

/** 未确认告警数量 */
const unacknowledgedAlarmsCount = computed(() => devicesStore.unacknowledgedAlarmsCount)

/** 连接时长 */
const connectionDuration = computed(() => {
  const hours = Math.floor(connectionSeconds.value / 3600)
  const minutes = Math.floor((connectionSeconds.value % 3600) / 60)
  const seconds = connectionSeconds.value % 60
  
  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
  }
  return `${minutes}:${String(seconds).padStart(2, '0')}`
})

/** 连接步骤指南 */
const connectionSteps = [
  {
    icon: Check,
    type: 'primary',
    size: 'large',
    title: '选择设备',
    description: '从设备列表中选择要配置的设备'
  },
  {
    icon: Check,
    type: 'primary',
    size: 'large',
    title: '扫描串口',
    description: '点击扫描按钮查找可用串口'
  },
  {
    icon: Check,
    type: 'primary',
    size: 'large',
    title: '配置参数',
    description: '设置波特率、从站地址等连接参数'
  },
  {
    icon: Check,
    type: 'primary',
    size: 'large',
    title: '测试连接',
    description: '测试配置是否正确，确保设备可以正常连接'
  },
  {
    icon: Check,
    type: 'success',
    size: 'large',
    title: '保存配置',
    description: '保存配置以便下次使用，或保存为模板'
  }
]

/** 连接提示信息 */
const connectionTips = [
  {
    title: '串口选择',
    type: 'info',
    description: '请确保设备已正确连接到计算机，并在设备管理器中确认串口号'
  },
  {
    title: '波特率匹配',
    type: 'warning',
    description: '波特率必须与设备配置一致，否则会导致通信失败'
  },
  {
    title: '配置保存',
    type: 'success',
    description: '配置会自动保存到本地，下次打开时会自动加载'
  }
]

// ==================== 方法 ====================

/**
 * 获取健康状态类型
 */
function getHealthType(health) {
  const typeMap = {
    excellent: 'success',
    good: 'success',
    warning: 'warning',
    critical: 'danger',
    unknown: 'info'
  }
  return typeMap[health] || 'info'
}

/**
 * 获取健康状态文本
 */
function getHealthText(health) {
  const textMap = {
    excellent: '优秀',
    good: '良好',
    warning: '警告',
    critical: '严重',
    unknown: '未知'
  }
  return textMap[health] || '未知'
}

/**
 * 获取设备类型名称
 */
function getDeviceTypeName(deviceType) {
  return DEVICE_TYPE_CONFIGS[deviceType]?.name || deviceType
}

/**
 * 处理测试成功
 */
function handleTestSuccess(_result) {
  ElMessage.success('连接测试成功')
}

function handleTestFailed(_result) {
  ElMessage.error('连接测试失败，请查看诊断信息')
}

/**
 * 处理设备选择变化
 */
function handleSelectionChange(selection) {
  selectedDevices.value = selection
}

/**
 * 全选设备
 */
function selectAllDevices() {
  deviceTableRef.value?.toggleAllSelection()
}

/**
 * 清空设备选择
 */
function clearDeviceSelection() {
  deviceTableRef.value?.clearSelection()
}

/**
 * 编辑设备配置
 */
function editDeviceConfig(device) {
  currentDeviceId.value = device.id
  currentDeviceName.value = device.name
  tempConfig.value = device.config || {}
  deviceConfigDialogVisible.value = true
}

/**
 * 保存设备配置
 */
function saveDeviceConfig() {
  const success = devicesStore.saveConnectionConfig(currentDeviceId.value, tempConfig.value)
  if (success) {
    ElMessage.success('配置保存成功')
    deviceConfigDialogVisible.value = false
  } else {
    ElMessage.error('配置保存失败')
  }
}

/**
 * 连接设备
 */
async function connectDevice(deviceId) {
  const config = devicesStore.loadConnectionConfig(deviceId)
  if (!config || !config.port) {
    ElMessage.warning('请先配置设备连接参数')
    return
  }

  try {
    if (deviceId === 'motor') {
      await motorStore.connectMotor()
    }
    // 其他设备的连接逻辑...
    ElMessage.success('设备连接成功')
  } catch (error) {
    ElMessage.error('设备连接失败: ' + error.message)
  }
}

/**
 * 断开设备
 */
async function disconnectDevice(deviceId) {
  try {
    if (deviceId === 'motor') {
      await motorStore.disconnectMotor()
    }
    // 其他设备的断开逻辑...
    ElMessage.success('设备已断开')
  } catch (error) {
    ElMessage.error('断开设备失败: ' + error.message)
  }
}

/**
 * 连接选中设备
 */
async function connectSelectedDevices() {
  if (selectedDevices.value.length === 0) {
    ElMessage.warning('请先选择要连接的设备')
    return
  }

  const result = await devicesStore.connectAllDevices()
  if (result.success) {
    ElMessage.success(`成功连接 ${result.succeeded} 个设备`)
  } else {
    ElMessage.warning(`连接完成：成功 ${result.succeeded} 个，失败 ${result.failed} 个`)
  }
}

/**
 * 断开选中设备
 */
async function disconnectSelectedDevices() {
  if (selectedDevices.value.length === 0) {
    ElMessage.warning('请先选择要断开的设备')
    return
  }

  const result = await devicesStore.disconnectAllDevices()
  if (result.success) {
    ElMessage.success(`成功断开 ${result.succeeded} 个设备`)
  } else {
    ElMessage.warning(`断开完成：成功 ${result.succeeded} 个，失败 ${result.failed} 个`)
  }
}

/**
 * 创建新模板
 */
function createNewTemplate() {
  templateForm.value = {
    id: '',
    name: '',
    deviceType: 'motor',
    description: '',
    isDefault: false,
    config: {
      port: '',
      baudrate: 115200,
      databits: 8,
      stopbits: 1,
      parity: 'N',
      flowcontrol: 'none',
      slaveId: 1,
      timeout: 1000
    }
  }
  templateDialogVisible.value = true
}

/**
 * 编辑模板
 */
function editTemplate(template) {
  templateForm.value = { ...template }
  templateDialogVisible.value = true
}

/**
 * 保存模板
 */
function saveTemplate() {
  if (!templateForm.value.name) {
    ElMessage.warning('请输入模板名称')
    return
  }

  const success = devicesStore.saveConfigTemplate(templateForm.value)
  if (success) {
    ElMessage.success('模板保存成功')
    templateDialogVisible.value = false
  } else {
    ElMessage.error('模板保存失败')
  }
}

/**
 * 删除模板
 */
async function deleteTemplate(template) {
  try {
    await ElMessageBox.confirm(`确定要删除模板"${template.name}"吗？`, '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    const success = devicesStore.deleteConfigTemplate(template.id)
    if (success) {
      ElMessage.success('模板已删除')
    } else {
      ElMessage.error('删除模板失败')
    }
  } catch {
    // 用户取消
  }
}

/**
 * 应用模板
 */
async function applyTemplate(template) {
  try {
    const { value: deviceId } = await ElMessageBox.prompt('请选择要应用模板的设备', '应用模板', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputType: 'select',
      inputOptions: deviceOptions.value.reduce((acc, opt) => {
        acc[opt.value] = opt.label
        return acc
      }, {})
    })

    if (deviceId) {
      const success = devicesStore.applyTemplateToDevice(deviceId, template.id)
      if (success) {
        ElMessage.success('模板应用成功')
      } else {
        ElMessage.error('模板应用失败')
      }
    }
  } catch {
    // 用户取消
  }
}

/**
 * 导入模板
 */
function importTemplates() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.json'
  input.onchange = async (e) => {
    const file = e.target.files[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = (event) => {
        const result = devicesStore.importConfigs(event.target.result)
        if (result.errors.length === 0) {
          ElMessage.success(`导入成功：${result.configsImported} 个配置，${result.templatesImported} 个模板`)
        } else {
          ElMessage.warning(`导入完成，但有 ${result.errors.length} 个错误`)
        }
      }
      reader.readAsText(file)
    }
  }
  input.click()
}

/**
 * 导出模板
 */
function exportTemplates() {
  const jsonStr = devicesStore.exportAllConfigs()
  const blob = new Blob([jsonStr], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `device_configs_${Date.now()}.json`
  link.click()
  URL.revokeObjectURL(url)
  ElMessage.success('配置已导出')
}

/**
 * 启动连接时长计时器
 */
function startConnectionTimer() {
  if (connectionTimer.value) {
    clearInterval(connectionTimer.value)
  }
  connectionSeconds.value = 0
  connectionTimer.value = setInterval(() => {
    if (connectedCount.value > 0) {
      connectionSeconds.value++
    }
  }, 1000)
}

/**
 * 停止连接时长计时器
 */
function stopConnectionTimer() {
  if (connectionTimer.value) {
    clearInterval(connectionTimer.value)
    connectionTimer.value = null
  }
}

// ==================== 生命周期 ====================

onMounted(() => {
  startConnectionTimer()
  // 加载当前设备的配置
  if (selectedDevice.value) {
    currentConfig.value = devicesStore.loadConnectionConfig(selectedDevice.value) || {}
  }
})

onUnmounted(() => {
  stopConnectionTimer()
})
</script>

<style scoped lang="scss">
/**
 * 设备连接配置页面样式
 * 遵循 CAUC-SEP 设计系统规范
 */

.device-connection-page {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  background-color: var(--color-bg-secondary);
}

/* ==================== 页面头部 ==================== */

.page-header {
  background: linear-gradient(135deg, var(--color-primary-500) 0%, var(--color-primary-600) 100%);
  padding: var(--spacing-6);
  box-shadow: var(--shadow-lg);
}

.header-main {
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
  font-size: 48px;
  color: var(--color-text-inverse);
  opacity: 0.95;
  padding: var(--spacing-3);
  background: rgba(255, 255, 255, 0.15);
  border-radius: var(--radius-lg);
  backdrop-filter: blur(10px);
}

.header-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-inverse);
  margin: 0;
  line-height: var(--line-height-tight);
}

.page-subtitle {
  font-size: var(--font-size-sm);
  color: rgba(255, 255, 255, 0.85);
  margin: 0;
}

.header-right {
  display: flex;
  gap: var(--spacing-4);
}

/* 状态指示器 */
.status-indicators {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-3) var(--spacing-4);
  background: rgba(255, 255, 255, 0.15);
  border-radius: var(--radius-lg);
  backdrop-filter: blur(10px);
  transition: var(--transition-all);

  .status-dot {
    width: 10px;
    height: 10px;
    border-radius: var(--radius-full);
    animation: pulse 2s ease-in-out infinite;
  }

  .status-text {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-inverse);
  }

  &--success .status-dot {
    background-color: var(--color-success);
    box-shadow: 0 0 8px var(--color-success);
  }

  &--warning .status-dot {
    background-color: var(--color-warning);
    box-shadow: 0 0 8px var(--color-warning);
  }

  &--danger .status-dot {
    background-color: var(--color-error);
    box-shadow: 0 0 8px var(--color-error);
    animation: pulse 1s ease-in-out infinite;
  }

  &--info .status-dot {
    background-color: var(--color-neutral-400);
  }
}

.connection-counter {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--spacing-2) var(--spacing-4);
  background: rgba(255, 255, 255, 0.15);
  border-radius: var(--radius-lg);
  backdrop-filter: blur(10px);

  .counter-label {
    font-size: var(--font-size-xs);
    color: rgba(255, 255, 255, 0.8);
  }

  .counter-value {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-bold);
    color: var(--color-text-inverse);
    font-family: var(--font-family-mono);
  }
}

/* ==================== 内容区域 ==================== */

.content-wrapper {
  flex: 1;
  max-width: var(--content-max-width);
  margin: 0 auto;
  width: 100%;
  padding: var(--spacing-6);
}

.content-row {
  margin-bottom: var(--spacing-6);
}

/* ==================== 配置卡片 ==================== */

.config-card {
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  box-shadow: var(--shadow-md);
  min-height: 600px;
  transition: var(--transition-all);

  &:hover {
    box-shadow: var(--shadow-lg);
  }
}

.config-tabs {
  height: 100%;
}

.tab-content {
  padding: var(--spacing-4);
}

/* 设备选择器卡片 */
.device-selector-card {
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  padding: var(--spacing-4);
  margin-bottom: var(--spacing-6);
  border: 1px solid var(--color-border-primary);
}

.selector-header {
  margin-bottom: var(--spacing-3);
}

.selector-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.selector-body {
  display: flex;
  align-items: center;
}

.device-select {
  width: 100%;
  max-width: 400px;
}

.device-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.device-name {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.config-form-section {
  animation: slide-up 0.3s ease-out;
}

/* ==================== 工具栏样式 ==================== */

.quick-actions-toolbar,
.template-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--spacing-3);
  padding: var(--spacing-4);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  margin-bottom: var(--spacing-4);
  border: 1px solid var(--color-border-primary);
}

.toolbar-left,
.toolbar-right {
  display: flex;
  gap: var(--spacing-2);
}

/* ==================== 表格样式 ==================== */

.device-table,
.template-table {
  border-radius: var(--radius-lg);
  overflow: hidden;

  :deep(.el-table__header-wrapper) {
    th {
      background-color: var(--color-bg-secondary);
      color: var(--color-text-primary);
      font-weight: var(--font-weight-semibold);
    }
  }

  :deep(.el-table__body-wrapper) {
    tr:hover > td {
      background-color: var(--color-interactive-hover);
    }
  }
}

.device-name-cell {
  display: flex;
  align-items: center;
}

.device-name-text {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

/* 状态徽章 */
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-1) var(--spacing-3);
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  transition: var(--transition-all);

  .badge-dot {
    width: 6px;
    height: 6px;
    border-radius: var(--radius-full);
  }

  &--success {
    background-color: var(--color-success-light);
    color: var(--color-success-dark);

    .badge-dot {
      background-color: var(--color-success);
      box-shadow: 0 0 6px var(--color-success);
    }
  }

  &--default {
    background-color: var(--color-neutral-100);
    color: var(--color-text-secondary);

    .badge-dot {
      background-color: var(--color-neutral-400);
    }
  }
}

.config-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-2);
}

.no-config-text {
  color: var(--color-text-tertiary);
  font-style: italic;
  font-size: var(--font-size-sm);
}

.action-buttons {
  display: flex;
  gap: var(--spacing-1);
}

/* 模板名称单元格 */
.template-name-cell {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.template-name {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.config-preview {
  display: flex;
  gap: var(--spacing-2);
  font-family: var(--font-family-mono);
  font-size: var(--font-size-sm);
}

.preview-item {
  padding: var(--spacing-1) var(--spacing-2);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
}

/* ==================== 状态卡片 ==================== */

.status-overview-card {
  margin-bottom: var(--spacing-6);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  box-shadow: var(--shadow-md);
  transition: var(--transition-all);

  &:hover {
    box-shadow: var(--shadow-lg);
  }
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.header-icon {
  font-size: var(--font-size-lg);
  color: var(--color-primary-500);
}

.header-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-4);
}

.status-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-4);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  transition: var(--transition-all);

  &:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
  }
}

.status-icon-wrapper {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-lg);
  font-size: var(--font-size-xl);
  flex-shrink: 0;
}

.status-icon--primary {
  background: var(--color-primary-50);
  color: var(--color-primary-500);
}

.status-icon--success {
  background: var(--color-success-light);
  color: var(--color-success);
}

.status-icon--warning {
  background: var(--color-warning-light);
  color: var(--color-warning);
}

.status-icon--danger {
  background: var(--color-error-light);
  color: var(--color-error);
}

.status-info {
  flex: 1;
  min-width: 0;
}

.status-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-1);
}

.status-value {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  font-family: var(--font-family-mono);
}

/* ==================== 指南卡片 ==================== */

.guide-card {
  margin-bottom: var(--spacing-6);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  box-shadow: var(--shadow-md);
}

.guide-timeline {
  padding: var(--spacing-2);
}

.timeline-content {
  padding-left: var(--spacing-2);
}

.step-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-1);
}

.step-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: var(--line-height-relaxed);
}

/* ==================== 提示卡片 ==================== */

.tips-card {
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  box-shadow: var(--shadow-md);
}

.tips-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
}

.tip-alert {
  border-radius: var(--radius-md);
  transition: var(--transition-all);

  &:hover {
    transform: translateX(4px);
  }
}

.mono {
  font-family: var(--font-family-mono);
}

/* ==================== 动画 ==================== */

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(1.15);
  }
}

@keyframes slide-up {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ==================== 响应式设计 ==================== */

@media (max-width: 1200px) {
  .status-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .page-header {
    padding: var(--spacing-4);
  }

  .header-main {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-4);
  }

  .header-icon {
    font-size: 36px;
    padding: var(--spacing-2);
  }

  .page-title {
    font-size: var(--font-size-xl);
  }

  .header-right {
    width: 100%;
  }

  .status-indicators {
    width: 100%;
    justify-content: space-between;
  }

  .content-wrapper {
    padding: var(--spacing-4);
  }

  .quick-actions-toolbar,
  .template-toolbar {
    flex-direction: column;
    align-items: stretch;

    .toolbar-left,
    .toolbar-right {
      justify-content: space-between;
    }
  }

  .device-select {
    max-width: 100%;
  }

  .status-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .status-indicators {
    flex-direction: column;
    align-items: stretch;
  }

  .status-indicator,
  .connection-counter {
    justify-content: center;
  }
}
</style>
