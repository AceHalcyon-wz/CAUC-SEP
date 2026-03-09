<template>
  <div class="pr-path-editor">
    <el-row :gutter="24">
      <!-- 左侧：路径点列表 -->
      <el-col :xs="24" :lg="8">
        <el-card class="path-list-card">
          <template #header>
            <div class="card-header">
              <div class="header-title">
                <el-icon class="header-icon"><List /></el-icon>
                <span>路径点列表</span>
              </div>
              <el-button 
                type="primary" 
                :icon="Plus"
                @click="addPathPoint"
                size="small"
              >
                添加点
              </el-button>
            </div>
          </template>

          <div class="path-list">
            <draggable
              v-model="pathPoints"
              item-key="id"
              handle=".drag-handle"
              animation="200"
              @change="onPathPointsChange"
            >
              <template #item="{ element, index }">
                <div 
                  class="path-point-item"
                  :class="{ 
                    'active': selectedPointIndex === index,
                    'dragging': draggingIndex === index 
                  }"
                  @click="selectPoint(index)"
                >
                  <el-icon class="drag-handle"><Rank /></el-icon>
                  <div class="point-info">
                    <div class="point-header">
                      <span class="point-number">点 {{ index + 1 }}</span>
                      <el-tag 
                        :type="element.mode === 0 ? 'primary' : 'success'" 
                        size="small"
                      >
                        {{ element.mode === 0 ? '绝对' : '增量' }}
                      </el-tag>
                    </div>
                    <div class="point-details">
                      <span>位置: {{ element.position_mm.toFixed(2) }} mm</span>
                      <span>速度: {{ element.velocity_mm_s.toFixed(1) }} mm/s</span>
                    </div>
                  </div>
                  <el-button
                    type="danger"
                    :icon="Delete"
                    circle
                    size="small"
                    @click.stop="deletePathPoint(index)"
                  />
                </div>
              </template>
            </draggable>
          </div>

          <el-divider />

          <div class="path-summary">
            <div class="summary-item">
              <span class="label">总点数:</span>
              <span class="value">{{ pathPoints.length }}</span>
            </div>
            <div class="summary-item">
              <span class="label">总距离:</span>
              <span class="value">{{ totalDistance.toFixed(2) }} mm</span>
            </div>
            <div class="summary-item">
              <span class="label">预估时间:</span>
              <span class="value">{{ estimatedTime.toFixed(2) }} s</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 中间：可视化预览 -->
      <el-col :xs="24" :lg="10">
        <el-card class="preview-card">
          <template #header>
            <div class="card-header">
              <div class="header-title">
                <el-icon class="header-icon"><TrendCharts /></el-icon>
                <span>路径可视化</span>
              </div>
              <div class="preview-controls">
                <el-button 
                  type="primary" 
                  :icon="VideoPlay"
                  :disabled="pathPoints.length === 0"
                  @click="startPreview"
                  size="small"
                >
                  预览
                </el-button>
                <el-button 
                  :icon="RefreshRight"
                  @click="resetPreview"
                  size="small"
                >
                  重置
                </el-button>
              </div>
            </div>
          </template>

          <div class="chart-container">
            <v-chart 
              ref="chartRef"
              :option="chartOption"
              :autoresize="true"
              class="path-chart"
              @click="handleChartClick"
            />
          </div>

          <div class="preview-status" v-if="isPreviewing">
            <el-progress 
              :percentage="previewProgress" 
              :format="formatProgress"
              :stroke-width="8"
            />
            <div class="preview-info">
              <span>当前位置: {{ previewCurrentPosition.toFixed(2) }} mm</span>
              <span>进度: {{ previewProgress.toFixed(1) }}%</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：参数编辑面板 -->
      <el-col :xs="24" :lg="6">
        <el-card class="editor-card">
          <template #header>
            <div class="card-header">
              <div class="header-title">
                <el-icon class="header-icon"><Edit /></el-icon>
                <span>参数编辑</span>
              </div>
            </div>
          </template>

          <div v-if="selectedPointIndex !== null" class="editor-form">
            <el-form 
              :model="selectedPoint"
              label-width="100px"
              label-position="top"
            >
              <el-form-item label="运行模式">
                <el-radio-group v-model="selectedPoint.mode">
                  <el-radio :label="0">绝对位置</el-radio>
                  <el-radio :label="1">增量位置</el-radio>
                </el-radio-group>
              </el-form-item>

              <el-form-item label="目标位置 (mm)">
                <el-slider
                  v-model="selectedPoint.position_mm"
                  :min="-50"
                  :max="50"
                  :step="0.1"
                  show-input
                  :show-input-controls="false"
                />
              </el-form-item>

              <el-form-item label="速度 (mm/s)">
                <el-slider
                  v-model="selectedPoint.velocity_mm_s"
                  :min="0.1"
                  :max="50"
                  :step="0.1"
                  show-input
                  :show-input-controls="false"
                />
              </el-form-item>

              <el-form-item label="加速时间 (ms)">
                <el-slider
                  v-model="selectedPoint.accel_time"
                  :min="1"
                  :max="10000"
                  :step="10"
                  show-input
                  :show-input-controls="false"
                />
              </el-form-item>

              <el-form-item label="减速时间 (ms)">
                <el-slider
                  v-model="selectedPoint.decel_time"
                  :min="1"
                  :max="10000"
                  :step="10"
                  show-input
                  :show-input-controls="false"
                />
              </el-form-item>

              <el-form-item label="停留时间 (ms)">
                <el-slider
                  v-model="selectedPoint.dwell_time"
                  :min="0"
                  :max="60000"
                  :step="100"
                  show-input
                  :show-input-controls="false"
                />
              </el-form-item>

              <el-form-item label="特殊参数">
                <el-input-number 
                  v-model="selectedPoint.special_param"
                  :min="0"
                  :max="65535"
                  :step="1"
                  style="width: 100%"
                />
              </el-form-item>
            </el-form>

            <el-divider />

            <div class="point-actions">
              <el-button 
                type="success" 
                :icon="Check"
                @click="applyChanges"
                style="width: 100%"
              >
                应用更改
              </el-button>
            </div>
          </div>

          <el-empty 
            v-else 
            description="请选择一个路径点进行编辑"
            :image-size="120"
          />
        </el-card>
      </el-col>
    </el-row>

    <!-- 底部：冲突检测和模拟运行 -->
    <el-row :gutter="24" class="bottom-section">
      <el-col :xs="24" :lg="12">
        <el-card class="conflict-card">
          <template #header>
            <div class="card-header">
              <div class="header-title">
                <el-icon class="header-icon"><Warning /></el-icon>
                <span>路径冲突检测</span>
              </div>
              <el-button 
                type="primary" 
                :icon="Search"
                @click="detectConflicts"
                size="small"
              >
                检测冲突
              </el-button>
            </div>
          </template>

          <div class="conflict-results">
            <el-alert
              v-if="conflicts.length === 0"
              title="未检测到路径冲突"
              type="success"
              :closable="false"
              show-icon
            />
            <div v-else class="conflict-list">
              <el-alert
                v-for="(conflict, index) in conflicts"
                :key="index"
                :title="conflict.message"
                :type="conflict.severity"
                :closable="false"
                show-icon
                class="conflict-item"
              >
                <template #default>
                  <div class="conflict-detail">
                    <span>点 {{ conflict.pointA }} ↔ 点 {{ conflict.pointB }}</span>
                    <span>距离: {{ conflict.distance.toFixed(2) }} mm</span>
                  </div>
                </template>
              </el-alert>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="12">
        <el-card class="simulation-card">
          <template #header>
            <div class="card-header">
              <div class="header-title">
                <el-icon class="header-icon"><Timer /></el-icon>
                <span>模拟运行</span>
              </div>
              <el-button 
                type="primary" 
                :icon="VideoPlay"
                :disabled="pathPoints.length === 0"
                @click="startSimulation"
                size="small"
              >
                开始模拟
              </el-button>
            </div>
          </template>

          <div class="simulation-info">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="总路径长度">
                {{ totalDistance.toFixed(2) }} mm
              </el-descriptions-item>
              <el-descriptions-item label="预估总时间">
                {{ estimatedTime.toFixed(2) }} s
              </el-descriptions-item>
              <el-descriptions-item label="平均速度">
                {{ averageVelocity.toFixed(2) }} mm/s
              </el-descriptions-item>
              <el-descriptions-item label="最大速度">
                {{ maxVelocity.toFixed(2) }} mm/s
              </el-descriptions-item>
              <el-descriptions-item label="路径点数">
                {{ pathPoints.length }}
              </el-descriptions-item>
              <el-descriptions-item label="总停留时间">
                {{ totalDwellTime.toFixed(2) }} s
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
/**
 * @file PRPathEditor.vue
 * @path src/components/
 * @description PR路径可视化编辑器组件，支持路径点的可视化编辑、拖拽调整、预览和模拟运行
 * @author Agent
 * @date 2024-03-07
 */

import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  List, Plus, Delete, TrendCharts, VideoPlay, RefreshRight, 
  Edit, Check, Rank, Warning, Search, Timer
} from '@element-plus/icons-vue'
import draggable from 'vuedraggable'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, ScatterChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  DataZoomComponent
} from 'echarts/components'

// 注册ECharts组件
use([
  CanvasRenderer,
  LineChart,
  ScatterChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  DataZoomComponent
])

// ==================== Props & Emits ====================

const props = defineProps({
  initialPathPoints: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits<{
  (e: 'update:pathPoints', points: PathPoint[]): void
  (e: 'save', points: PathPoint[]): void
}>()

// ==================== 类型定义 ====================

interface PathPoint {
  id: number
  mode: number
  position_mm: number
  velocity_mm_s: number
  accel_time: number
  decel_time: number
  dwell_time: number
  special_param: number
}

interface Conflict {
  pointA: number
  pointB: number
  distance: number
  message: string
  severity: 'warning' | 'error'
}

// ==================== 响应式状态 ====================

const pathPoints = ref<PathPoint[]>([])
const selectedPointIndex = ref<number | null>(null)
const draggingIndex = ref<number | null>(null)
const conflicts = ref<Conflict[]>([])
const isPreviewing = ref(false)
const previewProgress = ref(0)
const previewCurrentPosition = ref(0)
const chartRef = ref(null)

// ==================== 计算属性 ====================

const selectedPoint = computed(() => {
  if (selectedPointIndex.value === null) return null
  return pathPoints.value[selectedPointIndex.value]
})

const totalDistance = computed(() => {
  if (pathPoints.value.length === 0) return 0
  
  let distance = 0
  let currentPos = 0
  
  pathPoints.value.forEach(point => {
    if (point.mode === 0) {
      distance += Math.abs(point.position_mm - currentPos)
      currentPos = point.position_mm
    } else {
      distance += Math.abs(point.position_mm)
      currentPos += point.position_mm
    }
  })
  
  return distance
})

const estimatedTime = computed(() => {
  if (pathPoints.value.length === 0) return 0
  
  let time = 0
  
  pathPoints.value.forEach(point => {
    const distance = point.mode === 0 ? point.position_mm : point.position_mm
    const moveTime = Math.abs(distance) / point.velocity_mm_s
    const accelTime = point.accel_time / 1000
    const decelTime = point.decel_time / 1000
    const dwellTime = point.dwell_time / 1000
    
    time += moveTime + accelTime + decelTime + dwellTime
  })
  
  return time
})

const averageVelocity = computed(() => {
  if (pathPoints.value.length === 0) return 0
  const sum = pathPoints.value.reduce((acc, p) => acc + p.velocity_mm_s, 0)
  return sum / pathPoints.value.length
})

const maxVelocity = computed(() => {
  if (pathPoints.value.length === 0) return 0
  return Math.max(...pathPoints.value.map(p => p.velocity_mm_s))
})

const totalDwellTime = computed(() => {
  return pathPoints.value.reduce((acc, p) => acc + p.dwell_time / 1000, 0)
})

const chartOption = computed(() => {
  const positions: number[] = []
  const times: number[] = []
  let currentPos = 0
  let currentTime = 0
  
  pathPoints.value.forEach((point, index) => {
    if (point.mode === 0) {
      currentPos = point.position_mm
    } else {
      currentPos += point.position_mm
    }
    
    positions.push(currentPos)
    times.push(currentTime)
    
    const moveTime = Math.abs(point.position_mm) / point.velocity_mm_s
    currentTime += moveTime + point.accel_time / 1000 + point.decel_time / 1000 + point.dwell_time / 1000
  })

  return {
    title: {
      text: '位置-时间曲线',
      left: 'center',
      textStyle: {
        fontSize: 14,
        fontWeight: 'normal'
      }
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const point = pathPoints.value[params[0].dataIndex]
        return `
          <div style="padding: 8px;">
            <div><strong>点 ${params[0].dataIndex + 1}</strong></div>
            <div>位置: ${params[0].value.toFixed(2)} mm</div>
            <div>时间: ${params[1].value.toFixed(2)} s</div>
            <div>速度: ${point.velocity_mm_s.toFixed(1)} mm/s</div>
          </div>
        `
      }
    },
    grid: {
      left: '10%',
      right: '10%',
      bottom: '15%',
      top: '15%'
    },
    xAxis: {
      type: 'value',
      name: '时间 (s)',
      nameLocation: 'middle',
      nameGap: 30,
      min: 0
    },
    yAxis: {
      type: 'value',
      name: '位置 (mm)',
      nameLocation: 'middle',
      nameGap: 40,
      min: -60,
      max: 60
    },
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: 0,
        filterMode: 'none'
      },
      {
        type: 'slider',
        xAxisIndex: 0,
        filterMode: 'none'
      }
    ],
    series: [
      {
        name: '位置',
        type: 'line',
        data: times.map((t, i) => [t, positions[i]]),
        smooth: true,
        symbol: 'circle',
        symbolSize: 10,
        lineStyle: {
          width: 3,
          color: '#409EFF'
        },
        itemStyle: {
          color: '#409EFF',
          borderWidth: 2,
          borderColor: '#fff'
        },
        emphasis: {
          itemStyle: {
            color: '#67C23A',
            borderColor: '#fff',
            borderWidth: 3,
            shadowBlur: 10,
            shadowColor: 'rgba(103, 194, 58, 0.5)'
          }
        }
      },
      {
        name: '路径点',
        type: 'scatter',
        data: times.map((t, i) => [t, positions[i]]),
        symbol: 'circle',
        symbolSize: 15,
        itemStyle: {
          color: '#67C23A',
          borderWidth: 2,
          borderColor: '#fff'
        }
      }
    ]
  }
})

// ==================== 方法 ====================

/**
 * 添加路径点
 */
function addPathPoint() {
  const newPoint: PathPoint = {
    id: Date.now(),
    mode: 0,
    position_mm: 0,
    velocity_mm_s: 10,
    accel_time: 100,
    decel_time: 100,
    dwell_time: 0,
    special_param: 0
  }
  
  pathPoints.value.push(newPoint)
  selectedPointIndex.value = pathPoints.value.length - 1
  emit('update:pathPoints', pathPoints.value)
  ElMessage.success('已添加新路径点')
}

/**
 * 删除路径点
 * 
 * @param {number} index - 路径点索引
 */
async function deletePathPoint(index: number) {
  try {
    await ElMessageBox.confirm(
      `确定要删除路径点 ${index + 1} 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    pathPoints.value.splice(index, 1)
    
    if (selectedPointIndex.value === index) {
      selectedPointIndex.value = null
    } else if (selectedPointIndex.value !== null && selectedPointIndex.value > index) {
      selectedPointIndex.value--
    }
    
    emit('update:pathPoints', pathPoints.value)
    ElMessage.success('路径点已删除')
  } catch {
    // 用户取消
  }
}

/**
 * 选择路径点
 * 
 * @param {number} index - 路径点索引
 */
function selectPoint(index: number) {
  selectedPointIndex.value = index
}

/**
 * 路径点顺序变化处理
 */
function onPathPointsChange() {
  emit('update:pathPoints', pathPoints.value)
  ElMessage.success('路径点顺序已更新')
}

/**
 * 应用参数更改
 */
function applyChanges() {
  if (selectedPointIndex.value === null) return
  
  emit('update:pathPoints', pathPoints.value)
  ElMessage.success('参数已更新')
}

/**
 * 开始预览动画
 */
function startPreview() {
  if (pathPoints.value.length === 0) return
  
  isPreviewing.value = true
  previewProgress.value = 0
  previewCurrentPosition.value = 0
  
  const totalSteps = 100
  const stepDuration = (estimatedTime.value * 1000) / totalSteps
  let currentStep = 0
  
  const interval = setInterval(() => {
    currentStep++
    previewProgress.value = (currentStep / totalSteps) * 100
    
    // 计算当前位置
    const progress = currentStep / totalSteps
    const pointIndex = Math.floor(progress * pathPoints.value.length)
    if (pointIndex < pathPoints.value.length) {
      const point = pathPoints.value[pointIndex]
      previewCurrentPosition.value = point.position_mm
    }
    
    if (currentStep >= totalSteps) {
      clearInterval(interval)
      isPreviewing.value = false
      ElMessage.success('预览完成')
    }
  }, stepDuration)
}

/**
 * 重置预览
 */
function resetPreview() {
  isPreviewing.value = false
  previewProgress.value = 0
  previewCurrentPosition.value = 0
}

/**
 * 格式化进度显示
 * 
 * @param {number} percentage - 百分比
 * @returns {string} 格式化后的字符串
 */
function formatProgress(percentage: number): string {
  return `${percentage.toFixed(1)}%`
}

/**
 * 处理图表点击
 * 
 * @param {Object} params - 点击参数
 */
function handleChartClick(params: any) {
  if (params.componentType === 'series') {
    selectedPointIndex.value = params.dataIndex
  }
}

/**
 * 检测路径冲突
 */
function detectConflicts() {
  conflicts.value = []
  
  for (let i = 0; i < pathPoints.value.length - 1; i++) {
    for (let j = i + 1; j < pathPoints.value.length; j++) {
      const pointA = pathPoints.value[i]
      const pointB = pathPoints.value[j]
      
      // 计算实际位置
      let posA = 0
      let posB = 0
      
      for (let k = 0; k <= i; k++) {
        if (pathPoints.value[k].mode === 0) {
          posA = pathPoints.value[k].position_mm
        } else {
          posA += pathPoints.value[k].position_mm
        }
      }
      
      for (let k = 0; k <= j; k++) {
        if (pathPoints.value[k].mode === 0) {
          posB = pathPoints.value[k].position_mm
        } else {
          posB += pathPoints.value[k].position_mm
        }
      }
      
      const distance = Math.abs(posA - posB)
      
      // 检测冲突
      if (distance < 1) {
        conflicts.value.push({
          pointA: i + 1,
          pointB: j + 1,
          distance,
          message: `点 ${i + 1} 和点 ${j + 1} 位置过于接近`,
          severity: 'error'
        })
      } else if (distance < 5) {
        conflicts.value.push({
          pointA: i + 1,
          pointB: j + 1,
          distance,
          message: `点 ${i + 1} 和点 ${j + 1} 位置较近`,
          severity: 'warning'
        })
      }
    }
  }
  
  if (conflicts.value.length === 0) {
    ElMessage.success('未检测到路径冲突')
  } else {
    ElMessage.warning(`检测到 ${conflicts.value.length} 个潜在冲突`)
  }
}

/**
 * 开始模拟运行
 */
function startSimulation() {
  ElMessage.info('模拟运行功能开发中...')
}

// ==================== 监听器 ====================

watch(() => props.initialPathPoints, (newPoints) => {
  if (newPoints && newPoints.length > 0) {
    pathPoints.value = JSON.parse(JSON.stringify(newPoints))
  }
}, { immediate: true, deep: true })

// ==================== 生命周期 ====================

onMounted(() => {
  if (props.initialPathPoints && props.initialPathPoints.length > 0) {
    pathPoints.value = JSON.parse(JSON.stringify(props.initialPathPoints))
  }
})
</script>

<style scoped lang="scss">
.pr-path-editor {
  width: 100%;
}

/* 卡片通用样式 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.header-icon {
  font-size: var(--font-size-lg);
  color: var(--color-primary-500);
}

/* 路径列表卡片 */
.path-list-card {
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  height: 100%;
}

.path-list {
  max-height: 400px;
  overflow-y: auto;
  padding: var(--spacing-2);
}

.path-point-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-3);
  margin-bottom: var(--spacing-2);
  background: var(--color-bg-secondary);
  border: 2px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: var(--transition-all);
  
  &:hover {
    background: var(--color-interactive-hover);
    border-color: var(--color-primary-400);
    transform: translateX(4px);
  }
  
  &.active {
    background: var(--color-primary-50);
    border-color: var(--color-primary-500);
    box-shadow: 0 2px 8px rgba(64, 158, 255, 0.2);
  }
  
  &.dragging {
    opacity: 0.5;
    transform: scale(0.95);
  }
}

.drag-handle {
  cursor: move;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-lg);
  
  &:hover {
    color: var(--color-primary-500);
  }
}

.point-info {
  flex: 1;
}

.point-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-1);
}

.point-number {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.point-details {
  display: flex;
  gap: var(--spacing-3);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.path-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-3);
  padding: var(--spacing-3);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
}

.summary-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-1);
  
  .label {
    font-size: var(--font-size-xs);
    color: var(--color-text-tertiary);
  }
  
  .value {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--color-primary-600);
    font-family: var(--font-family-mono);
  }
}

/* 预览卡片 */
.preview-card {
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  height: 100%;
}

.preview-controls {
  display: flex;
  gap: var(--spacing-2);
}

.chart-container {
  width: 100%;
  height: 400px;
  padding: var(--spacing-2);
}

.path-chart {
  width: 100%;
  height: 100%;
}

.preview-status {
  padding: var(--spacing-4);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  margin-top: var(--spacing-3);
}

.preview-info {
  display: flex;
  justify-content: space-between;
  margin-top: var(--spacing-2);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

/* 编辑卡片 */
.editor-card {
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  height: 100%;
}

.editor-form {
  padding: var(--spacing-2);
}

.point-actions {
  margin-top: var(--spacing-4);
}

/* 底部区域 */
.bottom-section {
  margin-top: var(--spacing-6);
}

.conflict-card,
.simulation-card {
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
}

.conflict-results {
  min-height: 150px;
}

.conflict-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.conflict-item {
  border-radius: var(--radius-md);
}

.conflict-detail {
  display: flex;
  justify-content: space-between;
  margin-top: var(--spacing-1);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.simulation-info {
  padding: var(--spacing-2);
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .path-summary {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .path-list {
    max-height: 300px;
  }
  
  .chart-container {
    height: 300px;
  }
  
  .path-summary {
    grid-template-columns: 1fr;
  }
  
  .point-details {
    flex-direction: column;
    gap: var(--spacing-1);
  }
}
</style>
