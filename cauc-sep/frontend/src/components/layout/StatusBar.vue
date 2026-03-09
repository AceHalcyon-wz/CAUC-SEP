<template>
  <footer class="status-bar">
    <!-- 左侧：连接状态区域 -->
    <div class="status-bar__left">
      <!-- 连接状态卡片 -->
      <div 
        class="status-bar__connection"
        :class="`status-bar__connection--${connectionStatus}`"
      >
        <div class="status-bar__connection-content">
          <div class="status-bar__indicator-wrapper">
            <span class="status-bar__indicator"></span>
            <span class="status-bar__indicator-ring"></span>
          </div>
          <div class="status-bar__connection-info">
            <span class="status-bar__text">
              {{ connectionStatusText[connectionStatus] }}
            </span>
            <span v-if="connectionStatus === 'connected'" class="status-bar__connection-detail">
              WebSocket 已连接
            </span>
          </div>
        </div>
        
        <!-- WebSocket重连进度 -->
        <transition name="fade">
          <div 
            v-if="wsReconnectProgress.isReconnecting"
            class="status-bar__reconnect-badge"
          >
            <el-icon class="status-bar__reconnect-icon">
              <Loading />
            </el-icon>
            <span>{{ wsReconnectProgress.attempt }}/{{ wsReconnectProgress.maxAttempts }}</span>
          </div>
        </transition>
      </div>
    </div>

    <!-- 中间：告警和提示信息 -->
    <div class="status-bar__center">
      <!-- 数据告警区域（优先显示） -->
      <transition-group 
        v-if="hasVisibleAlerts"
        name="slide" 
        tag="div" 
        class="status-bar__alerts"
      >
        <div
          v-for="alert in visibleAlerts"
          :key="alert.id"
          class="status-bar__alert"
          :class="`status-bar__alert--${alert.level}`"
          @click="handleAlertClick(alert)"
        >
          <div class="status-bar__alert-icon-wrapper">
            <el-icon class="status-bar__alert-icon">
              <component :is="getAlertIcon(alert.level)" />
            </el-icon>
          </div>
          <div class="status-bar__alert-content">
            <span class="status-bar__alert-text">{{ alert.message }}</span>
            <span class="status-bar__alert-time">{{ formatAlertTime(alert.timestamp) }}</span>
          </div>
          <el-button
            class="status-bar__alert-close"
            :icon="Close"
            circle
            size="small"
            @click.stop="handleAlertDismiss(alert.id)"
          />
        </div>
      </transition-group>

      <!-- 告警计数器 -->
      <transition name="fade">
        <div 
          v-if="hasVisibleAlerts && dataAlerts.length > 3"
          class="status-bar__alert-counter"
        >
          <el-icon><Bell /></el-icon>
          <span>+{{ dataAlerts.length - 3 }}</span>
        </div>
      </transition>

      <!-- 操作提示（无告警时显示） -->
      <div v-if="!hasVisibleAlerts && !hasWarnings" class="status-bar__tip">
        <el-icon class="status-bar__tip-icon">
          <InfoFilled />
        </el-icon>
        <span class="status-bar__tip-text">{{ operationTip }}</span>
      </div>

      <!-- 警告信息 -->
      <transition-group 
        v-if="hasWarnings"
        name="slide" 
        tag="div" 
        class="status-bar__warnings"
      >
        <div
          v-for="warning in warnings"
          :key="warning.id"
          class="status-bar__warning"
          :class="`status-bar__warning--${warning.type}`"
        >
          <el-icon class="status-bar__warning-icon">
            <component :is="warning.type === 'error' ? 'CircleClose' : 'Warning'" />
          </el-icon>
          <span class="status-bar__warning-text">{{ warning.message }}</span>
          <el-button
            class="status-bar__warning-close"
            :icon="Close"
            circle
            size="small"
            @click="handleRemoveWarning(warning.id)"
          />
        </div>
      </transition-group>
    </div>

    <!-- 右侧：统计信息和时间戳 -->
    <div class="status-bar__right">
      <!-- 性能指标组 -->
      <div class="status-bar__metrics">
        <!-- 推送频率 -->
        <div v-if="wsPushFrequency > 0" class="status-bar__metric">
          <div class="status-bar__metric-icon-wrapper">
            <el-icon class="status-bar__metric-icon">
              <TrendCharts />
            </el-icon>
          </div>
          <div class="status-bar__metric-content">
            <span class="status-bar__metric-value">{{ wsPushFrequency }}</span>
            <span class="status-bar__metric-unit">条/秒</span>
          </div>
        </div>
        
        <!-- 数据延迟 -->
        <div v-if="wsDataLatency > 0" class="status-bar__metric">
          <div class="status-bar__metric-icon-wrapper">
            <el-icon class="status-bar__metric-icon">
              <Timer />
            </el-icon>
          </div>
          <div class="status-bar__metric-content">
            <span class="status-bar__metric-value">{{ wsDataLatency }}</span>
            <span class="status-bar__metric-unit">ms</span>
          </div>
        </div>
      </div>
      
      <!-- 分隔线 -->
      <div class="status-bar__divider"></div>
      
      <!-- 时间戳 -->
      <div class="status-bar__time">
        <div class="status-bar__time-icon-wrapper">
          <el-icon class="status-bar__time-icon">
            <Clock />
          </el-icon>
        </div>
        <div class="status-bar__time-content">
          <span class="status-bar__time-relative">{{ relativeTime }}</span>
          <span class="status-bar__time-absolute">{{ currentTimestamp }}</span>
        </div>
      </div>
    </div>
  </footer>
</template>

<script setup>
/**
 * @file StatusBar.vue
 * @path src/components/layout/
 * @description 底部状态栏组件，显示连接状态、操作提示、警告信息、数据告警和时间戳
 * @author Agent
 * @date 2024-03-07
 */

import { computed } from 'vue'
import { useLayoutStore } from '@/stores/layout'
import {
  InfoFilled,
  Clock,
  Warning,
  CircleClose,
  Close,
  Loading,
  TrendCharts,
  Timer,
  Bell,
  WarningFilled,
  CircleCheckFilled
} from '@element-plus/icons-vue'
import { ANOMALY_LEVEL } from '@/composables/useDataAnomaly'

// ==================== 组合式函数 ====================

const layoutStore = useLayoutStore()

// ==================== 响应式状态 ====================

/** 连接状态 */
const connectionStatus = computed(() => layoutStore.connectionStatus)

/** 连接状态文本 */
const connectionStatusText = computed(() => layoutStore.connectionStatusText)

/** 操作提示 */
const operationTip = computed(() => layoutStore.operationTip)

/** 警告信息列表 */
const warnings = computed(() => layoutStore.warnings)

/** 当前时间戳 */
const currentTimestamp = computed(() => layoutStore.currentTimestamp)

/** WebSocket重连进度 */
const wsReconnectProgress = computed(() => layoutStore.wsReconnectProgress)

/** WebSocket推送频率 */
const wsPushFrequency = computed(() => layoutStore.wsPushFrequency)

/** WebSocket数据延迟 */
const wsDataLatency = computed(() => layoutStore.wsDataLatency)

/** 数据告警列表 */
const dataAlerts = computed(() => layoutStore.dataAlerts)

/** 可见的数据告警（未确认的优先） */
const visibleAlerts = computed(() => {
  // 优先显示未确认的告警，最多显示3条
  const unacknowledged = dataAlerts.value.filter(a => !a.acknowledged)
  if (unacknowledged.length > 0) {
    return unacknowledged.slice(0, 3)
  }
  // 如果没有未确认的，显示最近的告警
  return dataAlerts.value.slice(-3)
})

/** 是否有可见告警 */
const hasVisibleAlerts = computed(() => visibleAlerts.value.length > 0)

/** 是否有警告信息 */
const hasWarnings = computed(() => warnings.value.length > 0)

/** 相对时间显示 */
const relativeTime = computed(() => {
  const now = Date.now()
  const diff = now - layoutStore.lastUpdateTime
  
  if (diff < 60000) {
    return '刚刚更新'
  } else if (diff < 3600000) {
    return `${Math.floor(diff / 60000)}分钟前`
  } else if (diff < 86400000) {
    return `${Math.floor(diff / 3600000)}小时前`
  } else {
    return `${Math.floor(diff / 86400000)}天前`
  }
})

// ==================== 方法 ====================

/**
 * 移除警告信息
 * 
 * @param {number} id - 警告ID
 */
function handleRemoveWarning(id) {
  layoutStore.removeWarning(id)
}

/**
 * 处理告警点击
 * 
 * @param {Object} alert - 告警对象
 */
function handleAlertClick(alert) {
  // 点击告警时确认
  layoutStore.acknowledgeDataAlert(alert.id)
}

/**
 * 处理告警关闭
 * 
 * @param {number} alertId - 告警ID
 */
function handleAlertDismiss(alertId) {
  layoutStore.clearDataAlert(alertId)
}

/**
 * 获取告警图标
 * 
 * @param {string} level - 告警级别
 * @returns {Object} 图标组件
 */
function getAlertIcon(level) {
  switch (level) {
    case ANOMALY_LEVEL.CRITICAL:
    case ANOMALY_LEVEL.ERROR:
      return CircleClose
    case ANOMALY_LEVEL.WARNING:
      return WarningFilled
    default:
      return Bell
  }
}

/**
 * 格式化告警时间
 * 
 * @param {number} timestamp - 时间戳
 * @returns {string} 格式化后的时间字符串
 */
function formatAlertTime(timestamp) {
  const now = Date.now()
  const diff = now - timestamp
  
  if (diff < 60000) {
    return '刚刚'
  } else if (diff < 3600000) {
    return `${Math.floor(diff / 60000)}分钟前`
  } else if (diff < 86400000) {
    return `${Math.floor(diff / 3600000)}小时前`
  } else {
    const date = new Date(timestamp)
    return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`
  }
}
</script>

<style scoped lang="scss">
.status-bar {
  position: fixed;
  bottom: 0;
  left: var(--sidebar-width, 0);
  right: 0;
  height: 40px;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.98) 0%,
    rgba(248, 250, 252, 0.96) 50%,
    rgba(255, 255, 255, 0.98) 100%
  );
  border-top: 1px solid var(--color-border-primary);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--spacing-4);
  z-index: var(--z-index-sticky);
  font-size: var(--font-size-xs);
  transition: left var(--transition-base) linear;
  box-shadow: 
    0 -2px 12px rgba(0, 0, 0, 0.04),
    0 -1px 6px rgba(0, 0, 0, 0.02),
    inset 0 1px 0 rgba(255, 255, 255, 0.5);
  backdrop-filter: blur(24px);
  
  // 顶部渐变光效
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(
      90deg,
      transparent 0%,
      rgba(20, 184, 166, 0.25) 20%,
      rgba(24, 144, 255, 0.3) 50%,
      rgba(20, 184, 166, 0.25) 80%,
      transparent 100%
    );
    animation: statusbar-glow 5s ease-in-out infinite;
  }
}

@keyframes statusbar-glow {
  0%, 100% {
    opacity: 0.4;
    transform: scaleX(0.95);
  }
  50% {
    opacity: 0.8;
    transform: scaleX(1);
  }
}

// ==================== 左侧：连接状态区域 ====================
.status-bar__left {
  display: flex;
  align-items: center;
  min-width: 180px;
}

.status-bar__connection {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-1) var(--spacing-3);
  border-radius: var(--radius-lg);
  background: var(--color-surface-elevated);
  border: 1px solid var(--color-border-secondary);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  flex-shrink: 0; // 优化：防止被压缩
  min-width: 160px; // 优化：保证最小宽度
  
  &--disconnected {
    border-color: var(--color-border-tertiary);
    
    .status-bar__indicator {
      background: var(--color-status-offline);
    }
    .status-bar__text {
      color: var(--color-text-tertiary);
    }
  }
  
  &--connecting {
    border-color: var(--color-warning-light);
    background: linear-gradient(
      135deg,
      var(--color-warning-lighter) 0%,
      rgba(251, 191, 36, 0.08) 100%
    );
    
    .status-bar__indicator {
      background: var(--color-status-warning);
      animation: blink 1.5s ease-in-out infinite;
    }
    .status-bar__indicator-ring {
      animation: ring-pulse 1.5s ease-in-out infinite;
    }
    .status-bar__text {
      color: var(--color-warning-dark);
    }
  }
  
  &--connected {
    border-color: var(--color-success-light);
    background: linear-gradient(
      135deg,
      var(--color-success-lighter) 0%,
      rgba(16, 185, 129, 0.08) 100%
    );
    
    .status-bar__indicator {
      background: var(--color-status-online);
      box-shadow: 0 0 12px var(--color-status-online);
    }
    .status-bar__indicator-ring {
      opacity: 1;
      animation: ring-pulse 2s ease-in-out infinite;
    }
    .status-bar__text {
      color: var(--color-success-dark);
      font-weight: var(--font-weight-semibold);
    }
  }
}

.status-bar__connection-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.status-bar__indicator-wrapper {
  position: relative;
  width: 12px;
  height: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-bar__indicator {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  transition: all var(--transition-base) var(--ease-in-out);
  flex-shrink: 0;
  position: relative;
  z-index: 2;
}

.status-bar__indicator-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 12px;
  height: 12px;
  transform: translate(-50%, -50%);
  border-radius: var(--radius-full);
  border: 1.5px solid currentColor;
  opacity: 0;
  transition: opacity var(--transition-base) var(--ease-in-out);
}

@keyframes ring-pulse {
  0%, 100% {
    opacity: 0.2;
    transform: translate(-50%, -50%) scale(1);
  }
  50% {
    opacity: 0.7;
    transform: translate(-50%, -50%) scale(1.4);
  }
}

@keyframes blink {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.3;
    transform: scale(0.9);
  }
}

.status-bar__connection-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
  line-height: 1.2;
}

.status-bar__text {
  font-weight: var(--font-weight-medium);
  white-space: nowrap;
  font-size: 12px;
}

.status-bar__connection-detail {
  font-size: 10px;
  color: var(--color-text-tertiary);
  white-space: nowrap;
}

.status-bar__reconnect-badge {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  padding: 3px var(--spacing-2);
  background: linear-gradient(
    135deg,
    var(--color-warning) 0%,
    #f59e0b 100%
  );
  color: white;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: var(--font-weight-semibold);
  animation: pulse 2s ease-in-out infinite;
  box-shadow: 0 2px 8px rgba(251, 191, 36, 0.3);
}

.status-bar__reconnect-icon {
  font-size: 12px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.85;
    transform: scale(0.98);
  }
}

// ==================== 中间：告警和提示信息 ====================
.status-bar__center {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-3);
  overflow: hidden;
  padding: 0 var(--spacing-4);
}

.status-bar__alerts {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  flex-wrap: wrap; // 优化：支持换行
  max-width: 100%;
  min-width: 0; // 优化：允许缩小
}

.status-bar__alert {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-1) var(--spacing-3);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--transition-base) var(--ease-in-out);
  border: 1px solid transparent;
  backdrop-filter: blur(12px);
  position: relative;
  overflow: hidden;
  
  &--critical,
  &--error {
    background: linear-gradient(
      135deg,
      rgba(239, 68, 68, 0.15) 0%,
      rgba(239, 68, 68, 0.08) 50%,
      rgba(239, 68, 68, 0.05) 100%
    );
    color: var(--color-error-dark);
    border-color: rgba(239, 68, 68, 0.35);
    animation: alert-flash 2s ease-in-out infinite;
    
    .status-bar__alert-icon-wrapper {
      background: linear-gradient(
        135deg,
        rgba(239, 68, 68, 0.25) 0%,
        rgba(239, 68, 68, 0.12) 100%
      );
      box-shadow: 0 2px 8px rgba(239, 68, 68, 0.3);
    }
    
    .status-bar__alert-icon {
      color: var(--color-error);
      animation: icon-pulse 1.5s ease-in-out infinite;
    }
  }
  
  &--warning {
    background: linear-gradient(
      135deg,
      rgba(251, 191, 36, 0.15) 0%,
      rgba(251, 191, 36, 0.08) 50%,
      rgba(251, 191, 36, 0.05) 100%
    );
    color: var(--color-warning-dark);
    border-color: rgba(251, 191, 36, 0.35);
    
    .status-bar__alert-icon-wrapper {
      background: linear-gradient(
        135deg,
        rgba(251, 191, 36, 0.25) 0%,
        rgba(251, 191, 36, 0.12) 100%
      );
      box-shadow: 0 2px 8px rgba(251, 191, 36, 0.3);
    }
    
    .status-bar__alert-icon {
      color: var(--color-warning);
    }
  }
  
  &--info {
    background: linear-gradient(
      135deg,
      rgba(59, 130, 246, 0.15) 0%,
      rgba(59, 130, 246, 0.08) 50%,
      rgba(59, 130, 246, 0.05) 100%
    );
    color: var(--color-primary-700);
    border-color: rgba(59, 130, 246, 0.35);
    
    .status-bar__alert-icon-wrapper {
      background: linear-gradient(
        135deg,
        rgba(59, 130, 246, 0.25) 0%,
        rgba(59, 130, 246, 0.12) 100%
      );
      box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
    }
    
    .status-bar__alert-icon {
      color: var(--color-primary-500);
    }
  }
  
  &:hover {
    transform: translateY(-3px) scale(1.02);
    box-shadow: 
      0 6px 16px rgba(0, 0, 0, 0.12),
      0 3px 8px rgba(0, 0, 0, 0.08);
  }
}

@keyframes alert-flash {
  0%, 100% {
    opacity: 1;
    box-shadow: 
      0 0 0 0 rgba(239, 68, 68, 0.4),
      0 2px 8px rgba(239, 68, 68, 0.2);
  }
  50% {
    opacity: 0.92;
    box-shadow: 
      0 0 16px 4px rgba(239, 68, 68, 0.3),
      0 4px 12px rgba(239, 68, 68, 0.15);
  }
}

@keyframes icon-pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
}

.status-bar__alert-icon-wrapper {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  flex-shrink: 0;
}

.status-bar__alert-icon {
  font-size: 14px;
  flex-shrink: 0;
}

.status-bar__alert-content {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.status-bar__alert-text {
  white-space: nowrap;
  max-width: 180px; // 优化：缩小最大宽度避免溢出
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: var(--font-weight-medium);
  font-size: 12px;
  line-height: 1.3;
}

.status-bar__alert-time {
  font-size: 10px;
  color: var(--color-text-tertiary);
  white-space: nowrap;
  opacity: 0.8;
}

.status-bar__alert-close {
  padding: 2px;
  width: 18px;
  height: 18px;
  min-height: 18px;
  background: transparent;
  border: none;
  opacity: 0.5;
  margin-left: var(--spacing-1);
  transition: all 0.2s ease;
  
  &:hover {
    opacity: 1;
    background: rgba(0, 0, 0, 0.05);
    transform: scale(1.1);
  }
}

.status-bar__alert-counter {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  padding: var(--spacing-1) var(--spacing-2);
  background: linear-gradient(
    135deg,
    var(--color-primary-100) 0%,
    rgba(24, 144, 255, 0.08) 100%
  );
  color: var(--color-primary-700);
  border-radius: var(--radius-lg);
  font-size: 11px;
  font-weight: var(--font-weight-semibold);
  border: 1px solid var(--color-primary-200);
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.15);
  
  .el-icon {
    font-size: 12px;
  }
}

.status-bar__tip {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  color: var(--color-text-secondary);
  padding: var(--spacing-1) var(--spacing-3);
  border-radius: var(--radius-lg);
  background: var(--color-surface-elevated);
  border: 1px solid var(--color-border-secondary);
}

.status-bar__tip-icon {
  font-size: 14px;
  color: var(--color-primary-500);
}

.status-bar__tip-text {
  white-space: nowrap;
  font-size: 12px;
}

.status-bar__warnings {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.status-bar__warning {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-1) var(--spacing-3);
  border-radius: var(--radius-lg);
  border: 1px solid transparent;
  transition: all 0.2s ease;
  
  &--warning {
    background: var(--color-warning-lighter);
    color: var(--color-warning-dark);
    border-color: var(--color-warning-light);
  }
  
  &--error {
    background: var(--color-error-lighter);
    color: var(--color-error-dark);
    border-color: var(--color-error-light);
  }
}

.status-bar__warning-icon {
  font-size: 14px;
}

.status-bar__warning-text {
  white-space: nowrap;
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 12px;
}

.status-bar__warning-close {
  padding: 2px;
  width: 18px;
  height: 18px;
  min-height: 18px;
  background: transparent;
  border: none;
  opacity: 0.5;
  transition: all 0.2s ease;
  
  &:hover {
    opacity: 1;
    transform: scale(1.1);
  }
}

// ==================== 右侧：统计信息和时间戳 ====================
.status-bar__right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--spacing-3);
  min-width: 260px;
}

.status-bar__metrics {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  flex-shrink: 0; // 优化：防止被压缩
}

.status-bar__metric {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: 3px var(--spacing-3);
  background: linear-gradient(
    135deg,
    var(--color-surface-elevated) 0%,
    rgba(255, 255, 255, 0.95) 100%
  );
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-secondary);
  transition: all var(--transition-base) var(--ease-in-out);
  flex-shrink: 0;
  position: relative;
  overflow: hidden;
  
  // 背景光效
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(
      135deg,
      transparent 0%,
      rgba(24, 144, 255, 0.08) 50%,
      transparent 100%
    );
    opacity: 0;
    transition: opacity var(--transition-base) var(--ease-in-out);
  }
  
  &:hover {
    border-color: var(--color-primary-300);
    background: linear-gradient(
      135deg,
      var(--color-surface-elevated) 0%,
      rgba(24, 144, 255, 0.08) 100%
    );
    box-shadow: 
      0 4px 12px rgba(24, 144, 255, 0.15),
      0 2px 6px rgba(0, 0, 0, 0.05);
    transform: translateY(-2px);
    
    &::before {
      opacity: 1;
    }
    
    .status-bar__metric-icon-wrapper {
      transform: scale(1.1) rotate(-5deg);
      box-shadow: 0 2px 8px rgba(24, 144, 255, 0.3);
    }
    
    .status-bar__metric-value {
      color: var(--color-primary-700);
    }
  }
}

.status-bar__metric-icon-wrapper {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(
    135deg,
    rgba(24, 144, 255, 0.18) 0%,
    rgba(24, 144, 255, 0.1) 100%
  );
  border-radius: var(--radius-sm);
  flex-shrink: 0;
  transition: all var(--transition-base) var(--ease-in-out);
  position: relative;
  z-index: 1;
}

.status-bar__metric-icon {
  font-size: 12px;
  color: var(--color-primary-600);
  position: relative;
  z-index: 1;
}

.status-bar__metric-content {
  display: flex;
  align-items: baseline;
  gap: 3px;
}

.status-bar__metric-value {
  font-weight: var(--font-weight-bold);
  font-family: var(--font-family-mono);
  color: var(--color-text-primary);
  font-size: 13px;
  line-height: 1;
}

.status-bar__metric-unit {
  font-size: 10px;
  color: var(--color-text-tertiary);
  white-space: nowrap;
  font-weight: var(--font-weight-medium);
}

.status-bar__divider {
  width: 1px;
  height: 24px;
  background: linear-gradient(
    to bottom,
    transparent 0%,
    var(--color-border-secondary) 20%,
    var(--color-border-secondary) 80%,
    transparent 100%
  );
  margin: 0 var(--spacing-1);
}

.status-bar__time {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: 3px var(--spacing-3);
  background: linear-gradient(
    135deg,
    var(--color-surface-elevated) 0%,
    rgba(255, 255, 255, 0.95) 100%
  );
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-secondary);
  transition: all var(--transition-base) var(--ease-in-out);
  flex-shrink: 0;
  position: relative;
  overflow: hidden;
  
  // 背景光效
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(
      135deg,
      transparent 0%,
      rgba(59, 130, 246, 0.08) 50%,
      transparent 100%
    );
    opacity: 0;
    transition: opacity var(--transition-base) var(--ease-in-out);
  }
  
  &:hover {
    border-color: var(--color-primary-300);
    background: linear-gradient(
      135deg,
      var(--color-surface-elevated) 0%,
      rgba(59, 130, 246, 0.08) 100%
    );
    box-shadow: 
      0 4px 12px rgba(59, 130, 246, 0.15),
      0 2px 6px rgba(0, 0, 0, 0.05);
    transform: translateY(-2px);
    
    &::before {
      opacity: 1;
    }
    
    .status-bar__time-icon-wrapper {
      transform: scale(1.1) rotate(-5deg);
      box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
    }
  }
}

.status-bar__time-icon-wrapper {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(
    135deg,
    rgba(59, 130, 246, 0.15) 0%,
    rgba(59, 130, 246, 0.08) 100%
  );
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}

.status-bar__time-icon {
  font-size: 12px;
  color: var(--color-primary-600);
}

.status-bar__time-content {
  display: flex;
  flex-direction: column;
  gap: 1px;
  line-height: 1.2;
}

.status-bar__time-relative {
  font-size: 10px;
  color: var(--color-text-tertiary);
  white-space: nowrap;
  font-weight: var(--font-weight-medium);
}

.status-bar__time-absolute {
  font-family: var(--font-family-mono);
  font-size: 11px;
  color: var(--color-text-primary);
  white-space: nowrap;
  font-weight: var(--font-weight-semibold);
}

// ==================== 过渡动画 ====================
.slide-enter-active,
.slide-leave-active {
  transition: all 0.3s ease;
}

.slide-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.slide-leave-to {
  opacity: 0;
  transform: translateX(10px);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
