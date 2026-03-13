<template>
  <el-card class="scan-config-card">
    <template #header>
      <div class="card-header">
        <div class="header-title">
          <el-icon class="header-icon">
            <Setting />
          </el-icon>
          <span>扫描模式配置</span>
        </div>
        <div class="header-actions">
          <el-button
            type="primary"
            size="small"
            :icon="Plus"
            @click="showPresetDialog = true"
          >
            保存预设
          </el-button>
          <el-button
            type="info"
            size="small"
            :icon="Folder"
            @click="showPresetList = true"
          >
            预设列表
          </el-button>
        </div>
      </div>
    </template>

    <div class="scan-config-content">
      <!-- 扫描模式选择 -->
      <div class="mode-selector">
        <div class="mode-label">
          扫描模式
        </div>
        <el-radio-group
          v-model="scanConfig.mode"
          class="mode-group"
        >
          <el-radio-button label="linear">
            <el-icon><TrendCharts /></el-icon>
            <span>线性扫描</span>
          </el-radio-button>
          <el-radio-button label="step">
            <el-icon><Grid /></el-icon>
            <span>步进扫描</span>
          </el-radio-button>
          <el-radio-button label="custom">
            <el-icon><Edit /></el-icon>
            <span>自定义</span>
          </el-radio-button>
        </el-radio-group>
      </div>

      <!-- 参数配置面板 -->
      <el-form
        :model="scanConfig"
        label-width="120px"
        class="config-form"
      >
        <!-- 基本参数 -->
        <el-divider class="form-divider">
          基本参数
        </el-divider>

        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item
              label="起始电流"
              :error="errors.startCurrent"
            >
              <el-input-number
                v-model="scanConfig.startCurrent"
                :min="currentLimits.min"
                :max="currentLimits.max"
                :precision="3"
                :step="0.1"
                class="form-input"
                @change="handleConfigChange"
              />
              <span class="unit-label">A</span>
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item
              label="终止电流"
              :error="errors.endCurrent"
            >
              <el-input-number
                v-model="scanConfig.endCurrent"
                :min="currentLimits.min"
                :max="currentLimits.max"
                :precision="3"
                :step="0.1"
                class="form-input"
                @change="handleConfigChange"
              />
              <span class="unit-label">A</span>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 线性扫描参数 -->
        <template v-if="scanConfig.mode === 'linear'">
          <el-divider class="form-divider">
            线性扫描参数
          </el-divider>

          <el-form-item
            label="扫描速率"
            :error="errors.scanRate"
          >
            <el-input-number
              v-model="scanConfig.scanRate"
              :min="0.01"
              :max="1"
              :precision="3"
              :step="0.01"
              class="form-input"
              @change="handleConfigChange"
            />
            <span class="unit-label">A/s</span>
          </el-form-item>
        </template>

        <!-- 步进扫描参数 -->
        <template v-if="scanConfig.mode === 'step'">
          <el-divider class="form-divider">
            步进扫描参数
          </el-divider>

          <el-row :gutter="24">
            <el-col :span="12">
              <el-form-item
                label="步进大小"
                :error="errors.stepSize"
              >
                <el-input-number
                  v-model="scanConfig.stepSize"
                  :min="0.001"
                  :max="5"
                  :precision="3"
                  :step="0.01"
                  class="form-input"
                  @change="handleStepSizeChange"
                />
                <span class="unit-label">A</span>
              </el-form-item>
            </el-col>

            <el-col :span="12">
              <el-form-item
                label="步数"
                :error="errors.stepCount"
              >
                <el-input-number
                  v-model="scanConfig.stepCount"
                  :min="2"
                  :max="1000"
                  :step="1"
                  class="form-input"
                  @change="handleConfigChange"
                />
              </el-form-item>
            </el-col>
          </el-row>

          <el-form-item
            label="步间延时"
            :error="errors.stepDelay"
          >
            <el-input-number
              v-model="scanConfig.stepDelay"
              :min="0.1"
              :max="60"
              :precision="1"
              :step="0.1"
              class="form-input"
              @change="handleConfigChange"
            />
            <span class="unit-label">s</span>
          </el-form-item>
        </template>

        <!-- 自定义扫描参数 -->
        <template v-if="scanConfig.mode === 'custom'">
          <el-divider class="form-divider">
            自定义扫描参数
          </el-divider>

          <el-row :gutter="24">
            <el-col :span="12">
              <el-form-item
                label="扫描速率"
                :error="errors.scanRate"
              >
                <el-input-number
                  v-model="scanConfig.scanRate"
                  :min="0.01"
                  :max="1"
                  :precision="3"
                  :step="0.01"
                  class="form-input"
                  @change="handleConfigChange"
                />
                <span class="unit-label">A/s</span>
              </el-form-item>
            </el-col>

            <el-col :span="12">
              <el-form-item
                label="循环次数"
                :error="errors.cycles"
              >
                <el-input-number
                  v-model="scanConfig.cycles"
                  :min="1"
                  :max="10"
                  :step="1"
                  class="form-input"
                  @change="handleConfigChange"
                />
              </el-form-item>
            </el-col>
          </el-row>

          <el-form-item label="扫描类型">
            <el-select
              v-model="scanConfig.customType"
              class="form-input"
              @change="handleConfigChange"
            >
              <el-option
                label="磁滞回线"
                value="hysteresis"
              />
              <el-option
                label="三角波"
                value="triangle"
              />
              <el-option
                label="正弦波"
                value="sine"
              />
            </el-select>
          </el-form-item>
        </template>
      </el-form>

      <!-- 扫描路径可视化 -->
      <div class="scan-path-section">
        <div class="section-header">
          <span class="section-title">扫描路径预览</span>
          <el-button
            type="primary"
            size="small"
            text
            :icon="Refresh"
            @click="updateScanPath"
          >
            刷新路径
          </el-button>
        </div>
        <div
          ref="pathChartRef"
          class="path-chart"
        />
      </div>

      <!-- 扫描参数预览 -->
      <div
        v-if="scanPreview.isValid"
        class="scan-preview"
      >
        <div class="preview-header">
          扫描参数预览
        </div>
        <el-row :gutter="16">
          <el-col :span="6">
            <div class="preview-item">
              <div class="preview-label">
                总步数
              </div>
              <div class="preview-value mono">
                {{ scanPreview.totalSteps }}
              </div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="preview-item">
              <div class="preview-label">
                预计时长
              </div>
              <div class="preview-value">
                {{ scanPreview.estimatedTime }}
              </div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="preview-item">
              <div class="preview-label">
                电流范围
              </div>
              <div class="preview-value mono">
                {{ scanPreview.currentRange }}
              </div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="preview-item">
              <div class="preview-label">
                扫描方向
              </div>
              <div class="preview-value">
                {{ scanPreview.direction }}
              </div>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- 操作按钮 -->
      <div class="action-buttons">
        <el-button
          type="primary"
          :disabled="!isConfigValid"
          :loading="loading.configScan"
          class="action-btn"
          @click="handleApplyConfig"
        >
          应用配置
        </el-button>
        <el-button
          type="info"
          :disabled="!isConfigValid"
          :loading="loading.validateScanConfig"
          class="action-btn"
          @click="handleValidateConfig"
        >
          验证参数
        </el-button>
        <el-button
          type="warning"
          class="action-btn"
          @click="handleResetConfig"
        >
          重置
        </el-button>
      </div>
    </div>

    <!-- 预设保存对话框 -->
    <el-dialog
      v-model="showPresetDialog"
      title="保存扫描预设"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form
        :model="presetForm"
        label-width="100px"
      >
        <el-form-item
          label="预设名称"
          required
        >
          <el-input
            v-model="presetForm.name"
            placeholder="请输入预设名称"
            maxlength="50"
          />
        </el-form-item>
        <el-form-item label="预设描述">
          <el-input
            v-model="presetForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入预设描述（可选）"
            maxlength="200"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPresetDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="handleSavePreset"
        >
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 预设列表对话框 -->
    <el-dialog
      v-model="showPresetList"
      title="扫描预设列表"
      width="700px"
    >
      <el-table
        :data="allPresets"
        style="width: 100%"
      >
        <el-table-column
          prop="name"
          label="预设名称"
          width="150"
        />
        <el-table-column
          prop="description"
          label="描述"
        />
        <el-table-column
          prop="config.mode"
          label="模式"
          width="100"
        >
          <template #default="{ row }">
            <el-tag size="small">
              {{ getModeLabel(row.config.mode) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          label="操作"
          width="180"
        >
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              link
              @click="handleLoadPreset(row)"
            >
              加载
            </el-button>
            <el-button
              v-if="row.id.startsWith('custom_')"
              type="danger"
              size="small"
              link
              @click="handleDeletePreset(row.id)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </el-card>
</template>

<script setup>
/**
 * @file ElectromagnetScanConfig.vue
 * @path src/components/
 * @description 扫描模式可视化配置组件，提供扫描参数配置、路径预览、预设管理等功能
 * @author Agent
 * @date 2024-03-06
 */

import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useElectromagnetStore } from '@/stores/electromagnet'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Setting,
  Plus,
  Folder,
  TrendCharts,
  Grid,
  Edit,
  Refresh
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'

const electromagnetStore = useElectromagnetStore()

// ============ 响应式状态 ============

/** 扫描配置 */
const scanConfig = reactive({
  mode: 'linear',
  startCurrent: 0,
  endCurrent: 5,
  stepSize: 0.1,
  stepCount: 10,
  stepDelay: 0.5,
  scanRate: 0.1,
  cycles: 1,
  customType: 'hysteresis'
})

/** 错误信息 */
const errors = reactive({
  startCurrent: '',
  endCurrent: '',
  scanRate: '',
  stepSize: '',
  stepCount: '',
  stepDelay: '',
  cycles: ''
})

/** 扫描预览 */
const scanPreview = reactive({
  isValid: false,
  totalSteps: 0,
  estimatedTime: '',
  currentRange: '',
  direction: ''
})

/** 预设表单 */
const presetForm = reactive({
  name: '',
  description: ''
})

/** 对话框显示状态 */
const showPresetDialog = ref(false)
const showPresetList = ref(false)

/** 图表引用 */
const pathChartRef = ref(null)
let pathChart = null

// ============ 计算属性 ============

/** 电流限制 */
const currentLimits = computed(() => electromagnetStore.currentLimits)

/** 加载状态 */
const loading = computed(() => electromagnetStore.loading)

/** 所有预设 */
const allPresets = computed(() => electromagnetStore.allPresets)

/** 配置是否有效 */
const isConfigValid = computed(() => {
  const validation = electromagnetStore.validateScanParameters(scanConfig)
  return validation.valid
})

// ============ 方法 ============

/**
 * 处理配置变化
 */
function handleConfigChange() {
  validateConfig()
  updateScanPreview()
  updateScanPath()
}

/**
 * 处理步进大小变化
 */
function handleStepSizeChange() {
  // 根据步进大小自动计算步数
  if (scanConfig.stepSize > 0) {
    const currentRange = Math.abs(scanConfig.endCurrent - scanConfig.startCurrent)
    scanConfig.stepCount = Math.ceil(currentRange / scanConfig.stepSize) + 1

    // 限制最大步数
    if (scanConfig.stepCount > 1000) {
      scanConfig.stepCount = 1000
    }
  }

  handleConfigChange()
}

/**
 * 验证配置
 */
function validateConfig() {
  // 重置错误
  Object.keys(errors).forEach(key => {
    errors[key] = ''
  })

  const validation = electromagnetStore.validateScanParameters(scanConfig)

  if (!validation.valid) {
    validation.errors.forEach(error => {
      if (error.includes('起始电流')) {
        errors.startCurrent = error
      } else if (error.includes('终止电流')) {
        errors.endCurrent = error
      } else if (error.includes('扫描速率')) {
        errors.scanRate = error
      } else if (error.includes('步数')) {
        errors.stepCount = error
      } else if (error.includes('步间延时')) {
        errors.stepDelay = error
      } else if (error.includes('循环次数')) {
        errors.cycles = error
      }
    })
  }
}

/**
 * 更新扫描预览
 */
function updateScanPreview() {
  const validation = electromagnetStore.validateScanParameters(scanConfig)
  if (!validation.valid) {
    scanPreview.isValid = false
    return
  }

  const currentRange = Math.abs(scanConfig.endCurrent - scanConfig.startCurrent)

  // 计算总步数
  if (scanConfig.mode === 'linear') {
    scanPreview.totalSteps = Math.ceil(currentRange / scanConfig.scanRate)
  } else if (scanConfig.mode === 'step') {
    scanPreview.totalSteps = scanConfig.stepCount
  } else if (scanConfig.mode === 'custom') {
    scanPreview.totalSteps = currentRange / scanConfig.scanRate * scanConfig.cycles * 2
  }

  // 计算预计时长
  if (scanConfig.mode === 'linear') {
    const timeSeconds = currentRange / scanConfig.scanRate
    scanPreview.estimatedTime = formatDuration(timeSeconds)
  } else if (scanConfig.mode === 'step') {
    const timeSeconds = (scanConfig.stepCount - 1) * scanConfig.stepDelay
    scanPreview.estimatedTime = formatDuration(timeSeconds)
  } else if (scanConfig.mode === 'custom') {
    const timeSeconds = currentRange / scanConfig.scanRate * scanConfig.cycles * 2
    scanPreview.estimatedTime = formatDuration(timeSeconds)
  }

  // 电流范围
  const minCurrent = Math.min(scanConfig.startCurrent, scanConfig.endCurrent)
  const maxCurrent = Math.max(scanConfig.startCurrent, scanConfig.endCurrent)
  scanPreview.currentRange = `${minCurrent.toFixed(3)} ~ ${maxCurrent.toFixed(3)} A`

  // 扫描方向
  scanPreview.direction = scanConfig.endCurrent > scanConfig.startCurrent ? '正向扫描' : '反向扫描'

  scanPreview.isValid = true
}

/**
 * 格式化时长
 */
function formatDuration(seconds) {
  if (seconds < 60) {
    return `${seconds.toFixed(1)}秒`
  } else if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60)
    const secs = (seconds % 60).toFixed(0)
    return `${minutes}分${secs}秒`
  } else {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours}小时${minutes}分`
  }
}

/**
 * 初始化路径图表
 */
function initPathChart() {
  if (!pathChartRef.value) return

  pathChart = echarts.init(pathChartRef.value)

  const option = {
    grid: {
      left: '10%',
      right: '5%',
      top: '10%',
      bottom: '15%'
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'var(--color-surface-elevated)',
      borderColor: 'var(--color-border-primary)',
      textStyle: {
        color: 'var(--color-text-primary)'
      },
      formatter: (params) => {
        if (params.length === 0) return ''
        const point = params[0]
        return `步数: ${point.value[0]}<br/>电流: ${point.value[1].toFixed(3)} A<br/>磁场: ${point.value[2].toFixed(2)} mT`
      }
    },
    xAxis: {
      type: 'value',
      name: '步数',
      nameLocation: 'middle',
      nameGap: 30,
      nameTextStyle: {
        color: 'var(--color-text-secondary)'
      },
      axisLine: {
        lineStyle: {
          color: 'var(--color-border-primary)'
        }
      },
      splitLine: {
        show: true,
        lineStyle: {
          color: 'var(--color-border-secondary)',
          type: 'dashed'
        }
      }
    },
    yAxis: [
      {
        type: 'value',
        name: '电流 (A)',
        nameLocation: 'middle',
        nameGap: 40,
        nameTextStyle: {
          color: 'var(--color-text-secondary)'
        },
        axisLine: {
          lineStyle: {
            color: 'var(--color-data-blue)'
          }
        },
        splitLine: {
          show: false
        }
      },
      {
        type: 'value',
        name: '磁场 (mT)',
        nameLocation: 'middle',
        nameGap: 40,
        nameTextStyle: {
          color: 'var(--color-text-secondary)'
        },
        axisLine: {
          lineStyle: {
            color: 'var(--color-data-green)'
          }
        },
        splitLine: {
          show: false
        }
      }
    ],
    series: [
      {
        name: '电流',
        type: 'line',
        yAxisIndex: 0,
        data: [],
        smooth: true,
        lineStyle: {
          color: 'var(--color-data-blue)',
          width: 2
        },
        symbol: 'none'
      },
      {
        name: '磁场',
        type: 'line',
        yAxisIndex: 1,
        data: [],
        smooth: true,
        lineStyle: {
          color: 'var(--color-data-green)',
          width: 2
        },
        symbol: 'none'
      }
    ]
  }

  pathChart.setOption(option)
}

/**
 * 更新扫描路径
 */
function updateScanPath() {
  if (!pathChart) return

  const path = electromagnetStore.calculateScanPath(scanConfig)

  const currentData = path.map(p => [p.step, p.current])
  const fieldData = path.map(p => [p.step, p.field])

  pathChart.setOption({
    series: [
      { data: currentData },
      { data: fieldData }
    ]
  })
}

/**
 * 应用配置
 */
async function handleApplyConfig() {
  const success = await electromagnetStore.configureScan(scanConfig)
  if (success) {
    ElMessage.success('扫描配置已应用')
  }
}

/**
 * 验证配置
 */
async function handleValidateConfig() {
  const result = await electromagnetStore.validateScanConfig(scanConfig)
  if (result) {
    if (result.valid) {
      ElMessage.success('扫描参数验证通过')
    } else {
      ElMessage.warning(`参数验证失败: ${result.message || '未知错误'}`)
    }
  }
}

/**
 * 重置配置
 */
function handleResetConfig() {
  scanConfig.mode = 'linear'
  scanConfig.startCurrent = 0
  scanConfig.endCurrent = 5
  scanConfig.stepSize = 0.1
  scanConfig.stepCount = 10
  scanConfig.stepDelay = 0.5
  scanConfig.scanRate = 0.1
  scanConfig.cycles = 1
  scanConfig.customType = 'hysteresis'

  handleConfigChange()
  ElMessage.info('配置已重置')
}

/**
 * 保存预设
 */
function handleSavePreset() {
  if (!presetForm.name.trim()) {
    ElMessage.warning('请输入预设名称')
    return
  }

  const success = electromagnetStore.savePreset({
    name: presetForm.name.trim(),
    description: presetForm.description.trim(),
    config: { ...scanConfig }
  })

  if (success) {
    ElMessage.success('预设已保存')
    showPresetDialog.value = false
    presetForm.name = ''
    presetForm.description = ''
  }
}

/**
 * 加载预设
 */
function handleLoadPreset(preset) {
  Object.assign(scanConfig, preset.config)
  handleConfigChange()
  showPresetList.value = false
  ElMessage.success(`已加载预设: ${preset.name}`)
}

/**
 * 删除预设
 */
async function handleDeletePreset(presetId) {
  try {
    await ElMessageBox.confirm('确定要删除此预设吗？', '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })

    const success = electromagnetStore.deletePreset(presetId)
    if (success) {
      ElMessage.success('预设已删除')
    }
  } catch {
    // 用户取消
  }
}

/**
 * 获取模式标签
 */
function getModeLabel(mode) {
  const labels = {
    linear: '线性',
    step: '步进',
    custom: '自定义'
  }
  return labels[mode] || mode
}

/**
 * 窗口大小变化处理
 */
function handleResize() {
  pathChart?.resize()
}

// ============ 监听器 ============

// 监听扫描模式变化
watch(() => scanConfig.mode, () => {
  handleConfigChange()
})

// ============ 生命周期 ============

onMounted(() => {
  initPathChart()
  updateScanPreview()
  updateScanPath()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  pathChart?.dispose()
})
</script>

<style scoped>
.scan-config-card {
  margin-bottom: var(--spacing-4);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  transition: var(--transition-all);
}

.scan-config-card:hover {
  box-shadow: var(--shadow-lg);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-2);
}

.header-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
}

.header-icon {
  font-size: var(--font-size-xl);
  color: var(--color-primary-500);
}

.header-actions {
  display: flex;
  gap: var(--spacing-2);
}

.scan-config-content {
  padding: var(--spacing-3) 0;
}

/* 模式选择器 */
.mode-selector {
  margin-bottom: var(--spacing-4);
  padding: var(--spacing-3);
  background-color: var(--color-surface-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
}

.mode-label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-2);
}

.mode-group {
  width: 100%;
}

.mode-group :deep(.el-radio-button__inner) {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-3) var(--spacing-4);
}

/* 表单样式 */
.config-form {
  margin-bottom: var(--spacing-4);
}

.form-divider {
  margin: var(--spacing-4) 0;
}

.form-input {
  width: 200px;
}

.unit-label {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  margin-left: var(--spacing-2);
}

/* 扫描路径区域 */
.scan-path-section {
  margin-bottom: var(--spacing-4);
  padding: var(--spacing-3);
  background-color: var(--color-surface-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-3);
}

.section-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.path-chart {
  width: 100%;
  height: 300px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
}

/* 扫描预览 */
.scan-preview {
  padding: var(--spacing-3);
  background-color: var(--color-surface-secondary);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-4);
  border: 1px solid var(--color-border-primary);
}

.preview-header {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-3);
}

.preview-item {
  text-align: center;
  padding: var(--spacing-2);
}

.preview-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-bottom: var(--spacing-1);
}

.preview-value {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: var(--spacing-3);
  justify-content: center;
}

.action-btn {
  min-width: 120px;
  transition: var(--transition-all);
}

.action-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

/* 工具类 */
.mono {
  font-family: var(--font-family-mono);
}

/* Element Plus 样式覆盖 */
:deep(.el-card__header) {
  background-color: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border-primary);
}

:deep(.el-divider__text) {
  background-color: var(--color-surface-primary);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-semibold);
}

:deep(.el-form-item__label) {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
}

:deep(.el-input-number) {
  font-family: var(--font-family-mono);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .mode-group :deep(.el-radio-button__inner) {
    padding: var(--spacing-2);
    font-size: var(--font-size-sm);
  }

  .form-input {
    width: 100%;
  }

  .action-buttons {
    flex-direction: column;
  }

  .action-btn {
    width: 100%;
  }

  .path-chart {
    height: 250px;
  }
}
</style>
