<template>
  <el-card class="safety-panel">
    <template #header>
      <div class="card-header">
        <el-icon class="header-icon">
          <Warning />
        </el-icon>
        <span class="header-title">安全控制</span>
      </div>
    </template>

    <div class="safety-content">
      <!-- 急停按钮 -->
      <div class="emergency-section">
        <button
          class="emergency-btn"
          :class="{ 'emergency-btn--active': motorStore.isEmergencyStopped }"
          :disabled="!motorStore.isConnected"
          @click="handleEmergencyStop"
        >
          <div class="btn-glow" />
          <div class="btn-content">
            <el-icon class="btn-icon">
              <CircleClose />
            </el-icon>
            <span class="btn-text">急 停</span>
          </div>
        </button>

        <transition name="reset-fade">
          <button
            v-if="motorStore.isEmergencyStopped"
            class="reset-btn"
            @click="handleReset"
          >
            <el-icon class="reset-icon">
              <RefreshRight />
            </el-icon>
            <span>复位急停</span>
          </button>
        </transition>
      </div>

      <!-- 状态显示 -->
      <div class="status-section">
        <div class="status-item">
          <span class="status-label">电机状态</span>
          <div class="status-indicator">
            <span
              class="indicator-dot"
              :class="`indicator-dot--${motorStatusType}`"
            />
            <span class="indicator-text">{{ motorStatusText }}</span>
          </div>
        </div>

        <div class="status-item">
          <span class="status-label">限位状态</span>
          <div class="status-indicator">
            <span
              class="indicator-dot"
              :class="`indicator-dot--${motorStore.limitStatusType}`"
            />
            <span class="indicator-text">{{ motorStore.limitStatus }}</span>
          </div>
        </div>

        <div class="status-item">
          <span class="status-label">控制权限</span>
          <div class="status-indicator">
            <span 
              class="indicator-dot" 
              :class="motorStore.canControl ? 'indicator-dot--success' : 'indicator-dot--info'"
            />
            <span class="indicator-text">{{ motorStore.canControl ? '可用' : '禁用' }}</span>
          </div>
        </div>
      </div>

      <!-- 安全提示 -->
      <div class="safety-alert">
        <div class="alert-header">
          <el-icon class="alert-icon">
            <InfoFilled />
          </el-icon>
          <span class="alert-title">安全提示</span>
        </div>
        <ul class="safety-list">
          <li class="safety-item">
            <span class="item-bullet">•</span>
            <span>实验时必须有人值守</span>
          </li>
          <li class="safety-item">
            <span class="item-bullet">•</span>
            <span>首次使用前验证限位参数</span>
          </li>
          <li class="safety-item">
            <span class="item-bullet">•</span>
            <span>急停后需人工确认才能复位</span>
          </li>
          <li class="safety-item">
            <span class="item-bullet">•</span>
            <span>定期检查机械连接</span>
          </li>
        </ul>
      </div>
    </div>
  </el-card>
</template>

<script setup>
/**
 * @file SafetyPanel.vue
 * @path src/components/
 * @description 安全控制面板组件，提供急停功能和设备状态监控
 * @author Agent
 * @date 2024-03-07
 * @dependencies vue, element-plus, pinia
 */

import { computed } from 'vue'
import { useMotorStore } from '@/stores/motor'
import { ElMessageBox, ElMessage } from 'element-plus'

const motorStore = useMotorStore()

/**
 * 电机状态文本映射
 */
const motorStatusText = computed(() => {
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
 * 电机状态类型映射
 */
const motorStatusType = computed(() => {
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
 * 处理急停操作
 */
async function handleEmergencyStop() {
  try {
    await ElMessageBox.confirm(
      '确定要触发急停吗？电机将立即停止运动。',
      '急停确认',
      {
        confirmButtonText: '确认急停',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )
    
    const success = await motorStore.emergencyStop()
    if (success) {
      ElMessage.warning('急停已触发')
    }
  } catch {
    // 用户取消操作
  }
}

/**
 * 处理复位操作
 */
async function handleReset() {
  try {
    await ElMessageBox.confirm(
      '确认已排除故障，准备复位急停？',
      '复位确认',
      {
        confirmButtonText: '确认复位',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const success = await motorStore.resetEmergency()
    if (success) {
      ElMessage.success('急停已复位')
    }
  } catch {
    // 用户取消操作
  }
}
</script>

<style scoped>
.safety-panel {
  margin-bottom: var(--spacing-5);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  transition: var(--transition-all);
}

.safety-panel:hover {
  box-shadow: var(--shadow-lg);
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.header-icon {
  font-size: var(--font-size-lg);
  color: var(--color-warning);
}

.header-title {
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
}

.safety-content {
  padding: var(--spacing-2) 0;
}

/* 急停按钮区域 */
.emergency-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
  margin-bottom: var(--spacing-6);
}

/* 急停按钮样式 */
.emergency-btn {
  position: relative;
  width: 100%;
  height: 72px;
  border: none;
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, #dc2626, #b91c1c);
  color: white;
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  cursor: pointer;
  overflow: hidden;
  transition: var(--transition-all);
  box-shadow: var(--shadow-md), 0 4px 12px rgba(220, 38, 38, 0.3);
}

.emergency-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg), 0 8px 20px rgba(220, 38, 38, 0.4);
}

.emergency-btn:active:not(:disabled) {
  transform: translateY(0);
}

.emergency-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: var(--shadow-sm);
}

/* 急停按钮激活状态 */
.emergency-btn--active {
  animation: emergency-pulse 2s ease-in-out infinite;
}

@keyframes emergency-pulse {
  0%, 100% {
    box-shadow: var(--shadow-md), 0 0 0 0 rgba(220, 38, 38, 0.7);
  }
  50% {
    box-shadow: var(--shadow-lg), 0 0 0 12px rgba(220, 38, 38, 0);
  }
}

/* 按钮发光效果 */
.btn-glow {
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.3) 0%, transparent 70%);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.emergency-btn:hover:not(:disabled) .btn-glow {
  opacity: 1;
  animation: glow-rotate 3s linear infinite;
}

@keyframes glow-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.btn-content {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-3);
  z-index: 1;
}

.btn-icon {
  font-size: 28px;
}

.btn-text {
  letter-spacing: 4px;
}

/* 复位按钮 */
.reset-btn {
  width: 100%;
  height: 52px;
  border: 2px solid var(--color-warning);
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--color-warning-light), rgba(237, 137, 54, 0.1));
  color: var(--color-warning-dark);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-2);
  transition: var(--transition-all);
}

.reset-btn:hover {
  background: linear-gradient(135deg, var(--color-warning), var(--color-warning-dark));
  color: white;
  border-color: var(--color-warning-dark);
  transform: translateY(-2px);
  box-shadow: var(--shadow-glow-warning);
}

.reset-icon {
  font-size: var(--font-size-lg);
  transition: var(--transition-transform);
}

.reset-btn:hover .reset-icon {
  transform: rotate(180deg);
}

/* 状态显示区域 */
.status-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
  margin-bottom: var(--spacing-6);
  padding: var(--spacing-4);
  background: var(--color-surface-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-3) 0;
  border-bottom: 1px solid var(--color-border-secondary);
}

.status-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.status-item:first-child {
  padding-top: 0;
}

.status-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.indicator-dot {
  width: 10px;
  height: 10px;
  border-radius: var(--radius-full);
  position: relative;
}

.indicator-dot::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
  height: 100%;
  border-radius: var(--radius-full);
  animation: dot-pulse 2s ease-in-out infinite;
}

/* 状态指示器颜色 */
.indicator-dot--success {
  background: var(--color-status-online);
}

.indicator-dot--success::after {
  background: var(--color-status-online);
}

.indicator-dot--danger {
  background: var(--color-status-error);
}

.indicator-dot--danger::after {
  background: var(--color-status-error);
}

.indicator-dot--warning {
  background: var(--color-status-warning);
}

.indicator-dot--warning::after {
  background: var(--color-status-warning);
}

.indicator-dot--primary {
  background: var(--color-status-measuring);
}

.indicator-dot--primary::after {
  background: var(--color-status-measuring);
}

.indicator-dot--info {
  background: var(--color-status-offline);
}

.indicator-dot--info::after {
  background: var(--color-status-offline);
}

@keyframes dot-pulse {
  0%, 100% {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
  50% {
    opacity: 0;
    transform: translate(-50%, -50%) scale(2);
  }
}

.indicator-text {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

/* 安全提示区域 */
.safety-alert {
  padding: var(--spacing-4);
  background: linear-gradient(135deg, var(--color-warning-light), rgba(237, 137, 54, 0.05));
  border: 1px solid rgba(237, 137, 54, 0.3);
  border-radius: var(--radius-md);
  border-left: 4px solid var(--color-warning);
}

.alert-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-3);
}

.alert-icon {
  font-size: var(--font-size-lg);
  color: var(--color-warning);
}

.alert-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-warning-dark);
}

.safety-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.safety-item {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-2);
  padding: var(--spacing-2) 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: var(--line-height-normal);
  transition: var(--transition-colors);
}

.safety-item:hover {
  color: var(--color-text-primary);
}

.item-bullet {
  color: var(--color-warning);
  font-weight: var(--font-weight-bold);
}

/* 过渡动画 */
.reset-fade-enter-active,
.reset-fade-leave-active {
  transition: all 0.3s ease;
}

.reset-fade-enter-from,
.reset-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .emergency-btn {
    height: 64px;
    font-size: var(--font-size-lg);
  }
  
  .btn-icon {
    font-size: 24px;
  }
  
  .btn-text {
    letter-spacing: 2px;
  }
}
</style>
