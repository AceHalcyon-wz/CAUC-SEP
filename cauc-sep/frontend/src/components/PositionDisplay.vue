<template>
  <el-card class="position-display">
    <template #header>
      <div class="card-header">
        <div class="header-title">
          <el-icon><Location /></el-icon>
          <span>实时位置</span>
        </div>
        <div
          v-if="motorStore.wsConnected"
          class="live-indicator"
        >
          <span class="pulse-dot" />
          <span class="live-text">实时</span>
        </div>
      </div>
    </template>

    <div class="display-content">
      <!-- 主要位置显示 -->
      <div class="main-position">
        <div class="position-value-wrapper">
          <transition
            name="number-update"
            mode="out-in"
          >
            <div 
              :key="positionMmDisplay" 
              class="position-value"
              :class="{ 'value-updated': isValueUpdating }"
            >
              {{ positionMmDisplay }}
            </div>
          </transition>
        </div>
        <div class="position-unit">
          mm
        </div>
      </div>

      <!-- 位置进度条 -->
      <div class="position-progress">
        <div class="progress-bar">
          <div 
            class="progress-fill"
            :style="{ width: positionProgress + '%' }"
            :class="{ 'progress-animated': motorStore.status === 'busy' }"
          />
        </div>
        <div class="progress-labels">
          <span class="progress-min">{{ formatPosition(motorStore.minPosition) }}</span>
          <span class="progress-max">{{ formatPosition(motorStore.maxPosition) }}</span>
        </div>
      </div>

      <!-- 详细信息 -->
      <el-divider />
      
      <div class="detail-grid">
        <div class="detail-item">
          <span class="label">
            <el-icon><Coin /></el-icon>
            步数
          </span>
          <span class="value mono">{{ formatNumber(motorStore.positionSteps) }} steps</span>
        </div>
        
        <div class="detail-item">
          <span class="label">
            <el-icon><CircleCheck /></el-icon>
            状态
          </span>
          <el-tag
            :type="statusType"
            size="small"
            class="status-tag"
          >
            {{ statusText }}
          </el-tag>
        </div>
        
        <div class="detail-item">
          <span class="label">
            <el-icon><Warning /></el-icon>
            限位
          </span>
          <el-tag
            :type="motorStore.limitStatusType"
            size="small"
            class="status-tag"
          >
            {{ motorStore.limitStatus }}
          </el-tag>
        </div>
        
        <div class="detail-item">
          <span class="label">
            <el-icon><Connection /></el-icon>
            连接
          </span>
          <el-tag
            :type="motorStore.wsConnected ? 'success' : 'info'"
            size="small"
            class="status-tag"
          >
            {{ motorStore.wsConnected ? '在线' : '离线' }}
          </el-tag>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
/**
 * @file PositionDisplay.vue
 * @path src/components/
 * @description 实时位置显示组件，支持数值动画和主题切换
 * @author Agent
 * @date 2024-03-07
 */

import { computed, ref, watch } from 'vue'
import { useMotorStore } from '../stores/motor'

const motorStore = useMotorStore()

/** 数值更新动画状态 */
const isValueUpdating = ref(false)

/** 上一次的位置值 */
let lastPosition = null

/**
 * 位置显示（保留3位小数）
 */
const positionMmDisplay = computed(() => {
  return motorStore.positionMm.toFixed(3)
})

/**
 * 位置进度百分比
 */
const positionProgress = computed(() => {
  const min = motorStore.minPosition || 0
  const max = motorStore.maxPosition || 100
  const current = motorStore.positionMm
  
  if (max === min) return 50
  return Math.min(100, Math.max(0, ((current - min) / (max - min)) * 100))
})

/**
 * 状态文本映射
 */
const statusText = computed(() => {
  const statusMap = {
    'disconnected': '未连接',
    'connecting': '连接中',
    'ready': '就绪',
    'busy': '运动中',
    'error': '错误',
    'emergency_stop': '急停'
  }
  return statusMap[motorStore.status] || motorStore.status
})

/**
 * 状态类型映射
 */
const statusType = computed(() => {
  const typeMap = {
    'disconnected': 'info',
    'connecting': 'warning',
    'ready': 'success',
    'busy': 'primary',
    'error': 'danger',
    'emergency_stop': 'danger'
  }
  return typeMap[motorStore.status] || 'info'
})

/**
 * 格式化位置数值
 * 
 * @param {number} value - 位置值
 * @returns {string} 格式化后的字符串
 */
function formatPosition(value) {
  if (value === null || value === undefined) return '-'
  return value.toFixed(2) + ' mm'
}

/**
 * 格式化数字（添加千位分隔符）
 * 
 * @param {number} value - 数值
 * @returns {string} 格式化后的字符串
 */
function formatNumber(value) {
  if (value === null || value === undefined) return '0'
  return value.toLocaleString()
}

/**
 * 监听位置变化，触发更新动画
 */
watch(() => motorStore.positionMm, (newVal, oldVal) => {
  if (newVal !== oldVal && oldVal !== undefined) {
    isValueUpdating.value = true
    setTimeout(() => {
      isValueUpdating.value = false
    }, 300)
  }
  lastPosition = newVal
})
</script>

<style scoped>
.position-display {
  margin-bottom: var(--spacing-5);
  background-color: var(--color-surface-primary);
  border-color: var(--color-border-primary);
  border-radius: var(--radius-lg);
  transition: var(--transition-all);
}

.position-display:hover {
  box-shadow: var(--shadow-lg);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.header-title .el-icon {
  color: var(--color-primary-500);
}

/* 实时指示器 */
.live-indicator {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  padding: var(--spacing-1) var(--spacing-2);
  background-color: var(--color-success-light);
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  color: var(--color-success);
}

.pulse-dot {
  width: 6px;
  height: 6px;
  background-color: var(--color-success);
  border-radius: var(--radius-full);
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(1.2);
  }
}

.live-text {
  font-weight: var(--font-weight-medium);
}

.display-content {
  padding: var(--spacing-5) 0;
}

/* 主要位置显示 */
.main-position {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: var(--spacing-3);
  margin-bottom: var(--spacing-5);
}

.position-value-wrapper {
  position: relative;
  overflow: hidden;
}

.position-value {
  font-family: var(--font-family-mono);
  font-size: 56px;
  font-weight: var(--font-weight-bold);
  color: var(--color-primary-500);
  letter-spacing: 0.02em;
  line-height: 1;
  text-shadow: 0 2px 8px rgba(44, 82, 130, 0.15);
  transition: var(--transition-transform);
}

.position-value.value-updated {
  animation: valueFlash 0.3s ease-out;
}

@keyframes valueFlash {
  0% {
    transform: scale(1.05);
    color: var(--color-accent-500);
  }
  100% {
    transform: scale(1);
    color: var(--color-primary-500);
  }
}

.position-unit {
  font-size: var(--font-size-2xl);
  color: var(--color-text-tertiary);
  font-weight: var(--font-weight-medium);
}

/* 位置进度条 */
.position-progress {
  margin-bottom: var(--spacing-4);
  padding: 0 var(--spacing-4);
}

.progress-bar {
  height: 8px;
  background-color: var(--color-bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
  position: relative;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary-500), var(--color-accent-500));
  border-radius: var(--radius-full);
  transition: width var(--transition-base);
  position: relative;
}

.progress-fill.progress-animated {
  animation: progressPulse 1.5s ease-in-out infinite;
}

@keyframes progressPulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

.progress-fill::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.3),
    transparent
  );
  animation: shimmer 2s infinite;
}

@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

.progress-labels {
  display: flex;
  justify-content: space-between;
  margin-top: var(--spacing-1);
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-family: var(--font-family-mono);
}

/* 详细信息网格 */
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-4);
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-2) var(--spacing-3);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  transition: var(--transition-fast);
}

.detail-item:hover {
  background-color: var(--color-interactive-hover);
}

.label {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
}

.label .el-icon {
  font-size: var(--font-size-base);
  color: var(--color-text-tertiary);
}

.value {
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
}

.value.mono {
  font-family: var(--font-family-mono);
  letter-spacing: 0.02em;
}

.status-tag {
  font-weight: var(--font-weight-medium);
}

/* 数值更新动画 */
.number-update-enter-active,
.number-update-leave-active {
  transition: all var(--transition-fast);
}

.number-update-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.number-update-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

/* 响应式优化 */
@media (max-width: 768px) {
  .position-value {
    font-size: 42px;
  }
  
  .position-unit {
    font-size: var(--font-size-xl);
  }
  
  .detail-grid {
    grid-template-columns: 1fr;
    gap: var(--spacing-3);
  }
  
  .detail-item {
    padding: var(--spacing-2);
  }
}
</style>
