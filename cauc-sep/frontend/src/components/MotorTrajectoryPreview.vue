<template>
  <el-card class="trajectory-preview-card">
    <template #header>
      <div class="card-header">
        <div class="header-left">
          <el-icon class="header-icon"><TrendCharts /></el-icon>
          <span class="header-title">轨迹预览</span>
        </div>
        <div class="header-actions">
          <el-button
            type="primary"
            size="small"
            :icon="VideoPlay"
            :disabled="!canPreview"
            @click="startPreview"
          >
            预览动画
          </el-button>
          <el-button
            size="small"
            :icon="RefreshRight"
            @click="resetPreview"
          >
            重置
          </el-button>
        </div>
      </div>
    </template>

    <div class="trajectory-content">
      <!-- 轨迹画布 -->
      <div class="trajectory-canvas-wrapper">
        <canvas
          ref="canvasRef"
          class="trajectory-canvas"
          :width="canvasWidth"
          :height="canvasHeight"
        ></canvas>
      </div>

      <!-- 运动参数显示 -->
      <div class="motion-params">
        <div class="param-item">
          <div class="param-label">
            <el-icon><Location /></el-icon>
            <span>当前位置</span>
          </div>
          <div class="param-value">
            <span class="value">{{ motorStore.positionMm.toFixed(3) }}</span>
            <span class="unit">mm</span>
          </div>
        </div>

        <div class="param-item">
          <div class="param-label">
            <el-icon><Aim /></el-icon>
            <span>目标位置</span>
          </div>
          <div class="param-value">
            <span class="value">{{ targetPosition.toFixed(3) }}</span>
            <span class="unit">mm</span>
          </div>
        </div>

        <div class="param-item">
          <div class="param-label">
            <el-icon><Odometer /></el-icon>
            <span>运动速度</span>
          </div>
          <div class="param-value">
            <span class="value">{{ velocity.toFixed(1) }}</span>
            <span class="unit">mm/s</span>
          </div>
        </div>

        <div class="param-item">
          <div class="param-label">
            <el-icon><Timer /></el-icon>
            <span>预计时间</span>
          </div>
          <div class="param-value">
            <span class="value">{{ estimatedTime.toFixed(2) }}</span>
            <span class="unit">s</span>
          </div>
        </div>

        <div class="param-item">
          <div class="param-label">
            <el-icon><DataLine /></el-icon>
            <span>运动距离</span>
          </div>
          <div class="param-value">
            <span class="value">{{ Math.abs(distance).toFixed(3) }}</span>
            <span class="unit">mm</span>
          </div>
        </div>
      </div>

      <!-- 限位警告 -->
      <transition name="slide-fade">
        <el-alert
          v-if="limitWarning"
          :title="limitWarning.message"
          :type="limitWarning.type"
          :closable="false"
          show-icon
          class="limit-warning"
        />
      </transition>
    </div>
  </el-card>
</template>

<script setup>
/**
 * @file MotorTrajectoryPreview.vue
 * @path src/components/
 * @description 电机运动轨迹预览组件，显示当前位置、目标位置、运动轨迹和参数
 * @author Agent
 * @date 2024-03-07
 */

import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useMotorStore } from '../stores/motor'
import {
  TrendCharts,
  VideoPlay,
  RefreshRight,
  Location,
  Aim,
  Odometer,
  Timer,
  DataLine
} from '@element-plus/icons-vue'

const motorStore = useMotorStore()

// ============ Props ============

const props = defineProps({
  /** 目标位置 */
  targetPosition: {
    type: Number,
    default: 0
  },
  /** 运动速度 */
  velocity: {
    type: Number,
    default: 10
  }
})

// ============ 响应式状态 ============

/** Canvas引用 */
const canvasRef = ref(null)

/** Canvas宽度 */
const canvasWidth = ref(600)

/** Canvas高度 */
const canvasHeight = ref(200)

/** 动画帧ID */
let animationFrameId = null

/** 预览动画状态 */
const previewState = ref({
  isPlaying: false,
  progress: 0,
  startTime: 0
})

// ============ 计算属性 ============

/** 运动距离 */
const distance = computed(() => {
  return props.targetPosition - motorStore.positionMm
})

/** 预计时间 */
const estimatedTime = computed(() => {
  if (props.velocity === 0) return 0
  return Math.abs(distance.value) / props.velocity
})

/** 是否可以预览 */
const canPreview = computed(() => {
  return motorStore.canControl && props.velocity > 0 && distance.value !== 0
})

/** 限位警告 */
const limitWarning = computed(() => {
  const posLimit = motorStore.limits.positive_mm
  const negLimit = motorStore.limits.negative_mm
  const target = props.targetPosition
  const current = motorStore.positionMm

  // 超出限位
  if (target > posLimit || target < negLimit) {
    return {
      type: 'error',
      message: `目标位置超出限位范围！限位: ${negLimit}mm ~ ${posLimit}mm`
    }
  }

  // 接近限位（距离限位5mm以内）
  const warningThreshold = 5
  if (Math.abs(target - posLimit) < warningThreshold || Math.abs(target - negLimit) < warningThreshold) {
    return {
      type: 'warning',
      message: '目标位置接近限位边界，请注意安全'
    }
  }

  // 运动过程中会经过限位区域
  const minPos = Math.min(current, target)
  const maxPos = Math.max(current, target)
  if (minPos <= negLimit + warningThreshold || maxPos >= posLimit - warningThreshold) {
    return {
      type: 'warning',
      message: '运动轨迹将经过限位边界区域'
    }
  }

  return null
})

// ============ 方法 ============

/**
 * 绘制轨迹
 */
function drawTrajectory() {
  const canvas = canvasRef.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  const width = canvas.width
  const height = canvas.height

  // 清空画布
  ctx.clearRect(0, 0, width, height)

  // 绘制背景
  ctx.fillStyle = '#f8f9fa'
  ctx.fillRect(0, 0, width, height)

  // 计算缩放比例
  const posLimit = motorStore.limits.positive_mm
  const negLimit = motorStore.limits.negative_mm
  const totalRange = posLimit - negLimit
  const padding = 40
  const drawWidth = width - padding * 2
  const scale = drawWidth / totalRange

  // 绘制限位区域
  const warningZone = 5 * scale
  ctx.fillStyle = 'rgba(239, 68, 68, 0.1)'
  ctx.fillRect(padding, 0, warningZone, height)
  ctx.fillRect(width - padding - warningZone, 0, warningZone, height)

  // 绘制限位线
  ctx.strokeStyle = '#ef4444'
  ctx.lineWidth = 2
  ctx.setLineDash([5, 5])
  
  // 正向限位线
  const posX = padding + (posLimit - negLimit) * scale
  ctx.beginPath()
  ctx.moveTo(posX, 0)
  ctx.lineTo(posX, height)
  ctx.stroke()

  // 负向限位线
  const negX = padding
  ctx.beginPath()
  ctx.moveTo(negX, 0)
  ctx.lineTo(negX, height)
  ctx.stroke()

  ctx.setLineDash([])

  // 绘制零点线
  const zeroX = padding + (0 - negLimit) * scale
  ctx.strokeStyle = '#94a3b8'
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.moveTo(zeroX, 0)
  ctx.lineTo(zeroX, height)
  ctx.stroke()

  // 绘制当前位置
  const currentX = padding + (motorStore.positionMm - negLimit) * scale
  ctx.fillStyle = '#3b82f6'
  ctx.beginPath()
  ctx.arc(currentX, height / 2, 8, 0, Math.PI * 2)
  ctx.fill()

  // 当前位置标签
  ctx.fillStyle = '#1e40af'
  ctx.font = 'bold 12px sans-serif'
  ctx.textAlign = 'center'
  ctx.fillText('当前', currentX, height / 2 - 20)
  ctx.font = '11px sans-serif'
  ctx.fillText(`${motorStore.positionMm.toFixed(2)}mm`, currentX, height / 2 + 25)

  // 绘制目标位置
  const targetX = padding + (props.targetPosition - negLimit) * scale
  ctx.fillStyle = '#10b981'
  ctx.beginPath()
  ctx.arc(targetX, height / 2, 8, 0, Math.PI * 2)
  ctx.fill()

  // 目标位置标签
  ctx.fillStyle = '#047857'
  ctx.font = 'bold 12px sans-serif'
  ctx.textAlign = 'center'
  ctx.fillText('目标', targetX, height / 2 - 20)
  ctx.font = '11px sans-serif'
  ctx.fillText(`${props.targetPosition.toFixed(2)}mm`, targetX, height / 2 + 25)

  // 绘制轨迹线
  ctx.strokeStyle = '#6366f1'
  ctx.lineWidth = 2
  ctx.setLineDash([8, 4])
  ctx.beginPath()
  ctx.moveTo(currentX, height / 2)
  ctx.lineTo(targetX, height / 2)
  ctx.stroke()
  ctx.setLineDash([])

  // 绘制运动方向箭头
  const arrowX = (currentX + targetX) / 2
  const direction = props.targetPosition > motorStore.positionMm ? 1 : -1
  
  ctx.fillStyle = '#6366f1'
  ctx.beginPath()
  ctx.moveTo(arrowX + direction * 10, height / 2)
  ctx.lineTo(arrowX - direction * 5, height / 2 - 6)
  ctx.lineTo(arrowX - direction * 5, height / 2 + 6)
  ctx.closePath()
  ctx.fill()

  // 绘制预览动画位置
  if (previewState.value.isPlaying) {
    const progress = previewState.value.progress
    const previewX = currentX + (targetX - currentX) * progress
    
    ctx.fillStyle = '#f59e0b'
    ctx.beginPath()
    ctx.arc(previewX, height / 2, 6, 0, Math.PI * 2)
    ctx.fill()
    
    // 动画位置光晕
    ctx.strokeStyle = 'rgba(245, 158, 11, 0.3)'
    ctx.lineWidth = 3
    ctx.beginPath()
    ctx.arc(previewX, height / 2, 12, 0, Math.PI * 2)
    ctx.stroke()
  }

  // 绘制刻度
  ctx.fillStyle = '#64748b'
  ctx.font = '10px sans-serif'
  ctx.textAlign = 'center'
  
  const tickCount = 10
  for (let i = 0; i <= tickCount; i++) {
    const tickX = padding + (drawWidth / tickCount) * i
    const tickValue = negLimit + (totalRange / tickCount) * i
    
    ctx.beginPath()
    ctx.moveTo(tickX, height - 10)
    ctx.lineTo(tickX, height - 5)
    ctx.stroke()
    
    if (i % 2 === 0) {
      ctx.fillText(tickValue.toFixed(0), tickX, height - 15)
    }
  }
}

/**
 * 开始预览动画
 */
function startPreview() {
  if (!canPreview.value) return

  previewState.value.isPlaying = true
  previewState.value.progress = 0
  previewState.value.startTime = Date.now()

  animatePreview()
}

/**
 * 预览动画循环
 */
function animatePreview() {
  if (!previewState.value.isPlaying) return

  const elapsed = (Date.now() - previewState.value.startTime) / 1000
  const duration = estimatedTime.value * 0.5 // 动画速度为实际速度的2倍

  previewState.value.progress = Math.min(elapsed / duration, 1)

  drawTrajectory()

  if (previewState.value.progress < 1) {
    animationFrameId = requestAnimationFrame(animatePreview)
  } else {
    previewState.value.isPlaying = false
  }
}

/**
 * 重置预览
 */
function resetPreview() {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
    animationFrameId = null
  }

  previewState.value.isPlaying = false
  previewState.value.progress = 0
  drawTrajectory()
}

// ============ 生命周期 ============

onMounted(() => {
  drawTrajectory()
})

onUnmounted(() => {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
  }
})

// 监听位置和速度变化，重新绘制轨迹
watch([() => props.targetPosition, () => props.velocity, () => motorStore.positionMm], () => {
  if (!previewState.value.isPlaying) {
    drawTrajectory()
  }
})
</script>

<style scoped>
.trajectory-preview-card {
  margin-bottom: var(--spacing-6);
  border: 1px solid var(--color-border-primary);
  transition: var(--transition-all);
}

.trajectory-preview-card:hover {
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

.header-actions {
  display: flex;
  gap: var(--spacing-2);
}

.trajectory-content {
  padding: var(--spacing-2) 0;
}

.trajectory-canvas-wrapper {
  margin-bottom: var(--spacing-4);
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--color-border-primary);
}

.trajectory-canvas {
  display: block;
  width: 100%;
  height: auto;
}

.motion-params {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--spacing-3);
  margin-bottom: var(--spacing-4);
}

.param-item {
  display: flex;
  flex-direction: column;
  padding: var(--spacing-3);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
  transition: var(--transition-all);
}

.param-item:hover {
  border-color: var(--color-primary-300);
  box-shadow: var(--shadow-sm);
}

.param-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-2);
}

.param-label .el-icon {
  font-size: var(--font-size-base);
}

.param-value {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-1);
}

.param-value .value {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
}

.param-value .unit {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.limit-warning {
  border-radius: var(--radius-md);
}

/* 响应式优化 */
@media (max-width: 768px) {
  .motion-params {
    grid-template-columns: 1fr;
  }

  .header-actions {
    flex-direction: column;
    width: 100%;
  }

  .header-actions .el-button {
    width: 100%;
  }
}
</style>
