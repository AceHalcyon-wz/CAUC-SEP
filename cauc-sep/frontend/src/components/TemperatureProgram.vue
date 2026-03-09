<template>
  <div class="temperature-program">
    <!-- 程序编辑器头部 -->
    <div class="program-header">
      <div class="header-left">
        <h3 class="program-title">程序升温配置</h3>
        <el-tag v-if="isEditing" type="warning" size="small">编辑中</el-tag>
      </div>
      <div class="header-right">
        <el-button size="small" @click="handleLoadProgram">
          <el-icon><FolderOpened /></el-icon>
          加载程序
        </el-button>
        <el-button size="small" type="primary" @click="handleSaveProgram" :disabled="!canSave">
          <el-icon><DocumentChecked /></el-icon>
          保存程序
        </el-button>
      </div>
    </div>

    <!-- 程序编辑区域 -->
    <div class="program-editor">
      <!-- 左侧：程序步骤列表 -->
      <div class="steps-panel">
        <div class="panel-header">
          <h4 class="panel-title">升温步骤</h4>
          <el-button size="small" type="primary" @click="handleAddStep">
            <el-icon><Plus /></el-icon>
            添加步骤
          </el-button>
        </div>

        <div class="steps-list">
          <draggable
            v-model="programSteps"
            item-key="id"
            handle=".step-handle"
            animation="200"
            class="draggable-list"
            @end="handleStepReorder"
          >
            <template #item="{ element, index }">
              <div
                class="step-item"
                :class="{ 'step-item--active': selectedStepIndex === index }"
                @click="handleSelectStep(index)"
              >
                <div class="step-handle">
                  <el-icon><Rank /></el-icon>
                </div>
                <div class="step-content">
                  <div class="step-header">
                    <span class="step-number">步骤 {{ index + 1 }}</span>
                    <el-tag :type="getStepTypeTag(element.type)" size="small">
                      {{ getStepTypeName(element.type) }}
                    </el-tag>
                  </div>
                  <div class="step-info">
                    <span class="info-item">
                      <el-icon><Aim /></el-icon>
                      {{ element.targetTemp }}K
                    </span>
                    <span v-if="element.type === 'hold'" class="info-item">
                      <el-icon><Timer /></el-icon>
                      {{ element.duration }}min
                    </span>
                    <span v-else class="info-item">
                      <el-icon><TrendCharts /></el-icon>
                      {{ element.rate }}K/min
                    </span>
                  </div>
                </div>
                <div class="step-actions">
                  <el-button
                    text
                    size="small"
                    @click.stop="handleDuplicateStep(index)"
                  >
                    <el-icon><CopyDocument /></el-icon>
                  </el-button>
                  <el-button
                    text
                    size="small"
                    type="danger"
                    @click.stop="handleDeleteStep(index)"
                    :disabled="programSteps.length <= 1"
                  >
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
              </div>
            </template>
          </draggable>
        </div>

        <!-- 程序统计信息 -->
        <div class="program-stats">
          <div class="stat-row">
            <span class="stat-label">总步骤:</span>
            <span class="stat-value">{{ programSteps.length }}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">总时长:</span>
            <span class="stat-value">{{ totalDuration.toFixed(1) }} min</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">最高温度:</span>
            <span class="stat-value">{{ maxTempInProgram }}K</span>
          </div>
        </div>
      </div>

      <!-- 右侧：步骤配置面板 -->
      <div class="config-panel">
        <div v-if="selectedStepIndex >= 0 && programSteps[selectedStepIndex]" class="step-config">
          <div class="config-header">
            <h4 class="config-title">步骤 {{ selectedStepIndex + 1 }} 配置</h4>
          </div>

          <el-form :model="selectedStep" label-width="100px" class="config-form">
            <el-form-item label="步骤类型">
              <el-radio-group v-model="selectedStep.type" @change="handleStepTypeChange">
                <el-radio-button value="heat">
                  <el-icon><Top /></el-icon>
                  升温
                </el-radio-button>
                <el-radio-button value="hold">
                  <el-icon><Minus /></el-icon>
                  恒温
                </el-radio-button>
                <el-radio-button value="cool">
                  <el-icon><Bottom /></el-icon>
                  降温
                </el-radio-button>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="目标温度">
              <div class="temp-input-group">
                <el-input-number
                  v-model="selectedStep.targetTemp"
                  :min="tempStore.tempLimits.min"
                  :max="tempStore.tempLimits.max"
                  :precision="1"
                  :step="10"
                  class="temp-input"
                />
                <span class="temp-unit">K</span>
                <span class="temp-celsius">({{ tempStore.kelvinToCelsius(selectedStep.targetTemp).toFixed(1) }}°C)</span>
              </div>
            </el-form-item>

            <el-form-item v-if="selectedStep.type === 'hold'" label="持续时间">
              <div class="duration-input-group">
                <el-input-number
                  v-model="selectedStep.duration"
                  :min="0"
                  :max="1000"
                  :precision="1"
                  :step="5"
                  class="duration-input"
                />
                <span class="duration-unit">min</span>
              </div>
            </el-form-item>

            <el-form-item v-else label="升温/降温速率">
              <div class="rate-input-group">
                <el-slider
                  v-model="selectedStep.rate"
                  :min="0.1"
                  :max="20"
                  :step="0.1"
                  :marks="rateMarks"
                  show-input
                  class="rate-slider"
                />
                <span class="rate-unit">K/min</span>
              </div>
            </el-form-item>

            <el-form-item label="预计时长">
              <el-input
                :value="calculateStepDuration(selectedStep)"
                disabled
                class="duration-display"
              >
                <template #append>min</template>
              </el-input>
            </el-form-item>
          </el-form>
        </div>

        <!-- 程序预览图表 -->
        <div class="preview-section">
          <div class="preview-header">
            <h4 class="preview-title">程序预览</h4>
            <el-button-group size="small">
              <el-button
                :type="previewMode === 'chart' ? 'primary' : ''"
                @click="previewMode = 'chart'"
              >
                图表
              </el-button>
              <el-button
                :type="previewMode === 'table' ? 'primary' : ''"
                @click="previewMode = 'table'"
              >
                表格
              </el-button>
            </el-button-group>
          </div>

          <div v-if="previewMode === 'chart'" class="preview-chart-container">
            <v-chart
              :option="previewChartOption"
              :autoresize="true"
              class="preview-chart"
            />
          </div>

          <div v-else class="preview-table-container">
            <el-table :data="programSteps" border stripe>
              <el-table-column type="index" label="序号" width="60" />
              <el-table-column label="类型" width="80">
                <template #default="{ row }">
                  <el-tag :type="getStepTypeTag(row.type)" size="small">
                    {{ getStepTypeName(row.type) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="目标温度 (K)" width="120">
                <template #default="{ row }">
                  {{ row.targetTemp.toFixed(1) }}
                </template>
              </el-table-column>
              <el-table-column label="参数">
                <template #default="{ row }">
                  <span v-if="row.type === 'hold'">{{ row.duration }} min</span>
                  <span v-else>{{ row.rate }} K/min</span>
                </template>
              </el-table-column>
              <el-table-column label="预计时长 (min)">
                <template #default="{ row }">
                  {{ calculateStepDuration(row) }}
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </div>
    </div>

    <!-- 程序保存对话框 -->
    <el-dialog
      v-model="showSaveDialog"
      title="保存程序"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form :model="programInfo" label-width="100px">
        <el-form-item label="程序名称" required>
          <el-input v-model="programInfo.name" placeholder="请输入程序名称" />
        </el-form-item>
        <el-form-item label="程序描述">
          <el-input
            v-model="programInfo.description"
            type="textarea"
            :rows="3"
            placeholder="请输入程序描述（可选）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSaveDialog = false">取消</el-button>
        <el-button type="primary" @click="handleConfirmSave" :loading="saving">
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 程序加载对话框 -->
    <el-dialog
      v-model="showLoadDialog"
      title="加载程序"
      width="800px"
    >
      <el-table
        :data="savedPrograms"
        highlight-current-row
        @current-change="handleProgramSelect"
        style="width: 100%"
      >
        <el-table-column prop="name" label="程序名称" width="200" />
        <el-table-column prop="description" label="描述" />
        <el-table-column label="步骤数" width="100">
          <template #default="{ row }">
            {{ row.segments ? row.segments.length : 0 }}
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            {{ new Date(row.created_at).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button
              type="danger"
              size="small"
              @click.stop="handleDeleteSavedProgram(row.id)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="showLoadDialog = false">取消</el-button>
        <el-button
          type="primary"
          @click="handleConfirmLoad"
          :disabled="!selectedProgramToLoad"
        >
          加载
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * @file TemperatureProgram.vue
 * @path src/components/
 * @description 程序升温可视化配置组件，提供升温程序编辑、预览、保存和加载功能
 * @author Agent
 * @date 2024-03-07
 */

import { ref, reactive, computed, watch } from 'vue'
import { useTemperatureStore } from '../stores/temperature'
import { ElMessage, ElMessageBox } from 'element-plus'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  MarkPointComponent
} from 'echarts/components'
import VChart from 'vue-echarts'
import draggable from 'vuedraggable'

// 注册 ECharts 组件
use([
  CanvasRenderer,
  LineChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
  MarkPointComponent
])

// ============ Store ============
const tempStore = useTemperatureStore()

// ============ Refs ============
const selectedStepIndex = ref(0)
const previewMode = ref('chart')
const showSaveDialog = ref(false)
const showLoadDialog = ref(false)
const saving = ref(false)
const selectedProgramToLoad = ref(null)
const isEditing = ref(false)

// ============ 响应式状态 ============

/** 程序步骤列表 */
const programSteps = ref([
  {
    id: Date.now(),
    type: 'heat',
    targetTemp: 300,
    duration: 0,
    rate: 5
  },
  {
    id: Date.now() + 1,
    type: 'hold',
    targetTemp: 300,
    duration: 30,
    rate: 0
  },
  {
    id: Date.now() + 2,
    type: 'cool',
    targetTemp: 100,
    duration: 0,
    rate: 3
  }
])

/** 程序信息 */
const programInfo = reactive({
  name: '',
  description: ''
})

/** 已保存的程序列表 */
const savedPrograms = ref([])

/** 升温速率标记 */
const rateMarks = {
  1: '慢速',
  5: '中速',
  10: '快速',
  15: '极速'
}

// ============ 计算属性 ============

/** 当前选中的步骤 */
const selectedStep = computed({
  get: () => programSteps.value[selectedStepIndex.value],
  set: (value) => {
    programSteps.value[selectedStepIndex.value] = value
  }
})

/** 是否可以保存 */
const canSave = computed(() => {
  return programSteps.value.length > 0 && programSteps.value.every(step => {
    if (step.type === 'hold') {
      return step.targetTemp > 0 && step.duration > 0
    } else {
      return step.targetTemp > 0 && step.rate > 0
    }
  })
})

/** 程序总时长 */
const totalDuration = computed(() => {
  let total = 0
  let currentTemp = programSteps.value[0]?.targetTemp || 0

  programSteps.value.forEach(step => {
    if (step.type === 'hold') {
      total += step.duration
    } else {
      const tempDiff = Math.abs(step.targetTemp - currentTemp)
      if (step.rate > 0) {
        total += tempDiff / step.rate
      }
    }
    currentTemp = step.targetTemp
  })

  return total
})

/** 程序中最高温度 */
const maxTempInProgram = computed(() => {
  if (programSteps.value.length === 0) return 0
  return Math.max(...programSteps.value.map(s => s.targetTemp))
})

/** 预览图表配置 */
const previewChartOption = computed(() => {
  const data = []
  let currentTime = 0
  let currentTemp = programSteps.value[0]?.targetTemp || tempStore.currentTemp

  programSteps.value.forEach((step, index) => {
    // 添加起始点
    data.push({
      value: [currentTime, currentTemp],
      stepIndex: index
    })

    if (step.type === 'heat' || step.type === 'cool') {
      if (step.rate > 0 && step.targetTemp !== currentTemp) {
        const tempDiff = step.targetTemp - currentTemp
        const timeNeeded = Math.abs(tempDiff) / step.rate
        currentTime += timeNeeded
        data.push({
          value: [currentTime, step.targetTemp],
          stepIndex: index
        })
        currentTemp = step.targetTemp
      }
    } else if (step.type === 'hold') {
      if (step.duration > 0) {
        currentTime += step.duration
        data.push({
          value: [currentTime, currentTemp],
          stepIndex: index
        })
      }
    }
  })

  return {
    title: {
      show: false
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'var(--color-surface-elevated)',
      borderColor: 'var(--color-border-primary)',
      borderWidth: 1,
      textStyle: {
        color: 'var(--color-text-primary)',
        fontFamily: 'var(--font-family-mono)'
      },
      formatter: (params) => {
        const point = params[0]
        return `
          <div style="font-weight: 600; margin-bottom: 4px;">时间: ${point.value[0].toFixed(1)} min</div>
          <div>温度: <span style="font-weight: 600;">${point.value[1].toFixed(1)}K</span></div>
          <div style="color: var(--color-text-tertiary);">(${tempStore.kelvinToCelsius(point.value[1]).toFixed(1)}°C)</div>
        `
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      name: '时间 (min)',
      nameTextStyle: {
        color: 'var(--color-text-secondary)'
      },
      splitLine: {
        show: false
      },
      axisLine: {
        lineStyle: {
          color: 'var(--color-border-primary)'
        }
      },
      axisLabel: {
        color: 'var(--color-text-secondary)',
        fontFamily: 'var(--font-family-mono)'
      }
    },
    yAxis: {
      type: 'value',
      name: '温度 (K)',
      nameTextStyle: {
        color: 'var(--color-text-secondary)'
      },
      min: tempStore.tempLimits.min,
      max: tempStore.tempLimits.max,
      splitLine: {
        lineStyle: {
          color: 'var(--color-border-secondary)',
          type: 'dashed'
        }
      },
      axisLine: {
        show: false
      },
      axisLabel: {
        color: 'var(--color-text-secondary)',
        fontFamily: 'var(--font-family-mono)'
      }
    },
    series: [
      {
        name: '温度曲线',
        type: 'line',
        step: 'middle',
        lineStyle: {
          width: 2,
          color: 'var(--color-data-green)'
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(16, 185, 129, 0.25)' },
              { offset: 1, color: 'rgba(16, 185, 129, 0.02)' }
            ]
          }
        },
        data: data,
        markPoint: {
          symbol: 'circle',
          symbolSize: 8,
          itemStyle: {
            color: 'var(--color-primary-500)'
          },
          data: data.map((item, index) => ({
            coord: item.value,
            value: `步骤${index + 1}`
          })),
          label: {
            show: false
          }
        }
      }
    ]
  }
})

// ============ 方法 ============

/**
 * 获取步骤类型名称
 * @param {string} type - 步骤类型
 * @returns {string} 类型名称
 */
function getStepTypeName(type) {
  const names = {
    heat: '升温',
    hold: '恒温',
    cool: '降温'
  }
  return names[type] || type
}

/**
 * 获取步骤类型标签样式
 * @param {string} type - 步骤类型
 * @returns {string} 标签类型
 */
function getStepTypeTag(type) {
  const tags = {
    heat: 'danger',
    hold: 'success',
    cool: 'primary'
  }
  return tags[type] || ''
}

/**
 * 计算步骤时长
 * @param {Object} step - 步骤对象
 * @returns {string} 时长字符串
 */
function calculateStepDuration(step) {
  if (step.type === 'hold') {
    return step.duration.toFixed(1)
  }

  // 计算升温/降温时长
  const prevStep = programSteps.value[selectedStepIndex.value - 1]
  const startTemp = prevStep ? prevStep.targetTemp : tempStore.currentTemp
  const tempDiff = Math.abs(step.targetTemp - startTemp)
  const duration = step.rate > 0 ? tempDiff / step.rate : 0

  return duration.toFixed(1)
}

/**
 * 选择步骤
 * @param {number} index - 步骤索引
 */
function handleSelectStep(index) {
  selectedStepIndex.value = index
  isEditing.value = true
}

/**
 * 添加步骤
 */
function handleAddStep() {
  const lastStep = programSteps.value[programSteps.value.length - 1]
  const newStep = {
    id: Date.now(),
    type: 'hold',
    targetTemp: lastStep.targetTemp,
    duration: 10,
    rate: 0
  }

  programSteps.value.push(newStep)
  selectedStepIndex.value = programSteps.value.length - 1
  isEditing.value = true
  ElMessage.success('已添加新步骤')
}

/**
 * 删除步骤
 * @param {number} index - 步骤索引
 */
function handleDeleteStep(index) {
  if (programSteps.value.length <= 1) {
    ElMessage.warning('至少需要保留一个步骤')
    return
  }

  programSteps.value.splice(index, 1)

  // 调整选中索引
  if (selectedStepIndex.value >= programSteps.value.length) {
    selectedStepIndex.value = programSteps.value.length - 1
  }

  isEditing.value = true
  ElMessage.success('已删除步骤')
}

/**
 * 复制步骤
 * @param {number} index - 步骤索引
 */
function handleDuplicateStep(index) {
  const step = programSteps.value[index]
  const newStep = {
    ...step,
    id: Date.now()
  }

  programSteps.value.splice(index + 1, 0, newStep)
  selectedStepIndex.value = index + 1
  isEditing.value = true
  ElMessage.success('已复制步骤')
}

/**
 * 步骤类型变化处理
 */
function handleStepTypeChange() {
  isEditing.value = true
}

/**
 * 步骤重新排序
 */
function handleStepReorder() {
  isEditing.value = true
}

/**
 * 保存程序
 */
function handleSaveProgram() {
  programInfo.name = ''
  programInfo.description = ''
  showSaveDialog.value = true
}

/**
 * 确认保存程序
 */
async function handleConfirmSave() {
  if (!programInfo.name.trim()) {
    ElMessage.warning('请输入程序名称')
    return
  }

  saving.value = true

  try {
    const success = await tempStore.createProgram({
      name: programInfo.name,
      description: programInfo.description,
      segments: programSteps.value.map(step => ({
        type: step.type,
        targetTemp: step.targetTemp,
        duration: step.duration,
        rate: step.rate
      }))
    })

    if (success) {
      ElMessage.success('程序保存成功')
      showSaveDialog.value = false
      isEditing.value = false
      await loadSavedPrograms()
    }
  } catch (error) {
    ElMessage.error('保存失败: ' + error.message)
  } finally {
    saving.value = false
  }
}

/**
 * 加载程序
 */
async function handleLoadProgram() {
  await loadSavedPrograms()
  showLoadDialog.value = true
}

/**
 * 加载已保存的程序列表
 */
async function loadSavedPrograms() {
  try {
    const programs = await tempStore.fetchPrograms()
    savedPrograms.value = programs || []
  } catch (error) {
    console.error('Failed to load programs:', error)
    ElMessage.error('加载程序列表失败')
  }
}

/**
 * 选择要加载的程序
 * @param {Object} program - 程序对象
 */
function handleProgramSelect(program) {
  selectedProgramToLoad.value = program
}

/**
 * 确认加载程序
 */
function handleConfirmLoad() {
  if (!selectedProgramToLoad.value) {
    ElMessage.warning('请选择要加载的程序')
    return
  }

  const program = selectedProgramToLoad.value

  // 加载程序步骤
  if (program.segments && program.segments.length > 0) {
    programSteps.value = program.segments.map((seg, index) => ({
      id: Date.now() + index,
      type: seg.type,
      targetTemp: seg.targetTemp,
      duration: seg.duration || 0,
      rate: seg.rate || 0
    }))

    selectedStepIndex.value = 0
    isEditing.value = false
    ElMessage.success(`已加载程序: ${program.name}`)
    showLoadDialog.value = false
  }
}

/**
 * 删除已保存的程序
 * @param {string} programId - 程序ID
 */
async function handleDeleteSavedProgram(programId) {
  try {
    await ElMessageBox.confirm('确定要删除该程序吗？', '确认删除', {
      type: 'warning'
    })

    const success = await tempStore.deleteProgram(programId)
    if (success) {
      ElMessage.success('程序已删除')
      await loadSavedPrograms()
    }
  } catch {
    // 用户取消
  }
}

// ============ 监听器 ============

watch(selectedStep, (newVal) => {
  if (newVal) {
    isEditing.value = true
  }
}, { deep: true })
</script>

<style scoped>
.temperature-program {
  width: 100%;
  background: var(--color-surface-primary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  overflow: hidden;
}

/* 头部 */
.program-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-4);
  border-bottom: 1px solid var(--color-border-primary);
  background: var(--color-surface-secondary);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.program-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.header-right {
  display: flex;
  gap: var(--spacing-2);
}

/* 编辑器主体 */
.program-editor {
  display: grid;
  grid-template-columns: 320px 1fr;
  min-height: 600px;
}

/* 左侧步骤面板 */
.steps-panel {
  border-right: 1px solid var(--color-border-primary);
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-3) var(--spacing-4);
  border-bottom: 1px solid var(--color-border-secondary);
}

.panel-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.steps-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-2);
}

.draggable-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.step-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-3);
  background: var(--color-surface-primary);
  border: 2px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: var(--transition-all);
}

.step-item:hover {
  border-color: var(--color-primary-300);
  background: var(--color-surface-secondary);
}

.step-item--active {
  border-color: var(--color-primary-500);
  background: var(--color-primary-50);
  box-shadow: var(--shadow-md);
}

.step-handle {
  cursor: move;
  color: var(--color-text-tertiary);
  padding: var(--spacing-1);
}

.step-handle:hover {
  color: var(--color-text-secondary);
}

.step-content {
  flex: 1;
  min-width: 0;
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-1);
}

.step-number {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.step-info {
  display: flex;
  gap: var(--spacing-3);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.info-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
}

.step-actions {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

/* 程序统计信息 */
.program-stats {
  padding: var(--spacing-3) var(--spacing-4);
  border-top: 1px solid var(--color-border-secondary);
  background: var(--color-surface-secondary);
}

.stat-row {
  display: flex;
  justify-content: space-between;
  padding: var(--spacing-1) 0;
  font-size: var(--font-size-sm);
}

.stat-label {
  color: var(--color-text-secondary);
}

.stat-value {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  font-family: var(--font-family-mono);
}

/* 右侧配置面板 */
.config-panel {
  display: flex;
  flex-direction: column;
  padding: var(--spacing-4);
  gap: var(--spacing-4);
}

.step-config {
  background: var(--color-surface-secondary);
  border-radius: var(--radius-md);
  padding: var(--spacing-4);
  border: 1px solid var(--color-border-primary);
}

.config-header {
  margin-bottom: var(--spacing-4);
}

.config-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.config-form {
  max-width: 600px;
}

.temp-input-group,
.duration-input-group,
.rate-input-group {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.temp-input,
.duration-input {
  width: 150px;
}

.temp-unit,
.duration-unit,
.rate-unit {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.temp-celsius {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.rate-slider {
  flex: 1;
  margin-right: var(--spacing-2);
}

.duration-display {
  width: 200px;
}

/* 预览区域 */
.preview-section {
  flex: 1;
  background: var(--color-surface-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-3) var(--spacing-4);
  border-bottom: 1px solid var(--color-border-secondary);
}

.preview-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.preview-chart-container,
.preview-table-container {
  flex: 1;
  padding: var(--spacing-4);
  overflow: auto;
}

.preview-chart {
  width: 100%;
  height: 300px;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .program-editor {
    grid-template-columns: 280px 1fr;
  }
}

@media (max-width: 768px) {
  .program-editor {
    grid-template-columns: 1fr;
  }

  .steps-panel {
    border-right: none;
    border-bottom: 1px solid var(--color-border-primary);
    max-height: 300px;
  }

  .program-header {
    flex-direction: column;
    gap: var(--spacing-2);
    align-items: flex-start;
  }

  .header-right {
    width: 100%;
  }
}
</style>
