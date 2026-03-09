<template>
  <div class="ws-status-indicator">
    <!-- 状态徽章 -->
    <el-tooltip
      v-if="showTooltip"
      :content="statusTooltip"
      placement="top"
    >
      <div
        class="status-badge"
        :class="statusClass"
        @click="handleClick"
      >
        <el-icon
          :class="{ 'is-spinning': isSpinning }"
          class="status-icon"
        >
          <component :is="statusIcon" />
        </el-icon>
        
        <span v-if="showText" class="status-text">
          {{ statusText }}
        </span>
        
        <span v-if="showReconnectProgress" class="reconnect-progress">
          ({{ reconnectProgressText }})
        </span>
        
        <el-progress
          v-if="showQuality && wsConnected"
          :percentage="connectionQuality"
          :color="qualityColor"
          :stroke-width="3"
          :show-text="false"
          class="quality-bar"
        />
      </div>
    </el-tooltip>

    <!-- 无提示的状态徽章 -->
    <div
      v-else
      class="status-badge"
      :class="statusClass"
      @click="handleClick"
    >
      <el-icon
        :class="{ 'is-spinning': isSpinning }"
        class="status-icon"
      >
        <component :is="statusIcon" />
      </el-icon>
      
      <span v-if="showText" class="status-text">
        {{ statusText }}
      </span>
      
      <span v-if="showReconnectProgress" class="reconnect-progress">
        ({{ reconnectProgressText }})
      </span>
      
      <el-progress
        v-if="showQuality && wsConnected"
        :percentage="connectionQuality"
        :color="qualityColor"
        :stroke-width="3"
        :show-text="false"
        class="quality-bar"
      />
    </div>

    <!-- 详细信息弹窗 -->
    <el-popover
      v-if="showDetails"
      placement="bottom"
      :width="400"
      trigger="click"
      v-model:visible="detailsVisible"
    >
      <template #reference>
        <el-button
          :icon="InfoFilled"
          circle
          size="small"
          class="details-btn"
        />
      </template>

      <div class="status-details">
        <h4 class="details-title">连接详情</h4>
        
        <!-- 连接状态 -->
        <div class="detail-section">
          <div class="detail-row">
            <span class="detail-label">连接状态</span>
            <el-tag :type="statusTagType" size="small">
              {{ connectionState }}
            </el-tag>
          </div>
          
          <div class="detail-row">
            <span class="detail-label">协议类型</span>
            <el-tag type="info" size="small">
              {{ currentProtocol }}
            </el-tag>
          </div>
          
          <div class="detail-row">
            <span class="detail-label">连接质量</span>
            <div class="quality-indicator">
              <el-progress
                :percentage="connectionQuality"
                :color="qualityColor"
                :stroke-width="6"
              />
              <span class="quality-text">{{ connectionQuality }}分</span>
            </div>
          </div>
        </div>

        <!-- 性能指标 -->
        <div class="detail-section">
          <h5 class="section-title">性能指标</h5>
          
          <div class="detail-row">
            <span class="detail-label">消息频率</span>
            <span class="detail-value">{{ pushFrequency }} msg/s</span>
          </div>
          
          <div class="detail-row">
            <span class="detail-label">数据延迟</span>
            <span class="detail-value" :class="{ 'is-warning': dataLatency > 500 }">
              {{ dataLatency }}ms
            </span>
          </div>
          
          <div class="detail-row">
            <span class="detail-label">消息队列</span>
            <span class="detail-value">{{ queueLength }} 条</span>
          </div>
        </div>

        <!-- 重连信息 -->
        <div v-if="reconnectAttempts > 0" class="detail-section">
          <h5 class="section-title">重连信息</h5>
          
          <div class="detail-row">
            <span class="detail-label">重连次数</span>
            <span class="detail-value">
              {{ reconnectAttempts }} / {{ maxReconnectAttempts }}
            </span>
          </div>
          
          <div class="detail-row">
            <span class="detail-label">重连策略</span>
            <span class="detail-value">{{ reconnectStrategyText }}</span>
          </div>
        </div>

        <!-- 错误信息 -->
        <div v-if="lastError" class="detail-section error-section">
          <h5 class="section-title">最近错误</h5>
          
          <div class="error-message">
            <el-icon class="error-icon"><WarningFilled /></el-icon>
            <span>{{ lastError.userMessage }}</span>
          </div>
          
          <div v-if="lastError.suggestion" class="error-suggestion">
            <el-icon><InfoFilled /></el-icon>
            <span>{{ lastError.suggestion }}</span>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="detail-actions">
          <el-button
            v-if="!wsConnected"
            type="primary"
            size="small"
            :loading="isConnecting"
            @click="handleReconnect"
          >
            {{ isConnecting ? '连接中...' : '重新连接' }}
          </el-button>
          
          <el-button
            v-else
            type="danger"
            size="small"
            @click="handleDisconnect"
          >
            断开连接
          </el-button>
          
          <el-button
            size="small"
            @click="handleRefreshStats"
          >
            刷新状态
          </el-button>
        </div>
      </div>
    </el-popover>
  </div>
</template>

<script setup>
/**
 * @file WebSocketStatusIndicator.vue
 * @path src/components/
 * @description WebSocket连接状态可视化指示器组件，提供实时连接状态展示、性能监控和错误提示
 * @author Agent
 * @date 2026-03-08
 * @dependencies vue, element-plus
 */

import { ref, computed, watch } from 'vue'
import {
  Connection,
  WarningFilled,
  CircleCheckFilled,
  Loading,
  InfoFilled
} from '@element-plus/icons-vue'

/**
 * 组件属性
 */
const props = defineProps({
  /** 连接状态 */
  connectionState: {
    type: String,
    default: 'disconnected'
  },
  /** 是否已连接 */
  wsConnected: {
    type: Boolean,
    default: false
  },
  /** 是否正在连接 */
  wsConnecting: {
    type: Boolean,
    default: false
  },
  /** 连接质量评分（0-100） */
  connectionQuality: {
    type: Number,
    default: 0
  },
  /** 当前协议类型 */
  currentProtocol: {
    type: String,
    default: 'json'
  },
  /** 重连次数 */
  reconnectAttempts: {
    type: Number,
    default: 0
  },
  /** 最大重连次数 */
  maxReconnectAttempts: {
    type: Number,
    default: 5
  },
  /** 重连策略 */
  reconnectStrategy: {
    type: String,
    default: 'exponential'
  },
  /** 消息频率 */
  pushFrequency: {
    type: Number,
    default: 0
  },
  /** 数据延迟 */
  dataLatency: {
    type: Number,
    default: 0
  },
  /** 消息队列长度 */
  queueLength: {
    type: Number,
    default: 0
  },
  /** 最后错误信息 */
  lastError: {
    type: Object,
    default: null
  },
  /** 是否显示文本 */
  showText: {
    type: Boolean,
    default: true
  },
  /** 是否显示提示 */
  showTooltip: {
    type: Boolean,
    default: true
  },
  /** 是否显示详情弹窗 */
  showDetails: {
    type: Boolean,
    default: true
  },
  /** 是否显示连接质量 */
  showQuality: {
    type: Boolean,
    default: false
  }
})

/**
 * 组件事件
 */
const emit = defineEmits([
  'reconnect',
  'disconnect',
  'refresh',
  'click'
])

// === 内部状态 ===
const detailsVisible = ref(false)

// === 计算属性 ===

/**
 * 状态样式类
 */
const statusClass = computed(() => {
  const classes = []
  
  if (props.wsConnected) {
    classes.push('status-badge--connected')
  } else if (props.wsConnecting) {
    classes.push('status-badge--connecting')
  } else if (props.connectionState === 'reconnect_failed') {
    classes.push('status-badge--failed')
  } else {
    classes.push('status-badge--disconnected')
  }
  
  // 低质量警告
  if (props.wsConnected && props.connectionQuality < 60) {
    classes.push('status-badge--warning')
  }
  
  return classes
})

/**
 * 状态图标
 */
const statusIcon = computed(() => {
  if (props.wsConnected) {
    return CircleCheckFilled
  } else if (props.wsConnecting) {
    return Loading
  } else if (props.connectionState === 'reconnect_failed') {
    return WarningFilled
  }
  return Connection
})

/**
 * 状态文本
 */
const statusText = computed(() => {
  if (props.wsConnected) {
    return '已连接'
  } else if (props.wsConnecting) {
    return '连接中...'
  } else if (props.connectionState === 'reconnecting') {
    return '重连中...'
  } else if (props.connectionState === 'reconnect_failed') {
    return '连接失败'
  }
  return '未连接'
})

/**
 * 状态提示文本
 */
const statusTooltip = computed(() => {
  if (props.wsConnected) {
    let tooltip = `WebSocket已连接 (${props.currentProtocol})`
    if (props.connectionQuality < 60) {
      tooltip += ' - 连接质量较差'
    }
    return tooltip
  } else if (props.wsConnecting) {
    return '正在建立WebSocket连接...'
  } else if (props.connectionState === 'reconnecting') {
    return `正在重连 (${props.reconnectAttempts}/${props.maxReconnectAttempts})`
  } else if (props.connectionState === 'reconnect_failed') {
    return '连接失败，请检查网络后手动重连'
  }
  return 'WebSocket未连接'
})

/**
 * 状态标签类型
 */
const statusTagType = computed(() => {
  if (props.wsConnected) {
    return props.connectionQuality < 60 ? 'warning' : 'success'
  } else if (props.wsConnecting) {
    return 'info'
  } else if (props.connectionState === 'reconnect_failed') {
    return 'danger'
  }
  return 'info'
})

/**
 * 是否显示旋转动画
 */
const isSpinning = computed(() => {
  return props.wsConnecting || props.connectionState === 'reconnecting'
})

/**
 * 是否显示重连进度
 */
const showReconnectProgress = computed(() => {
  return props.connectionState === 'reconnecting' && props.reconnectAttempts > 0
})

/**
 * 重连进度文本
 */
const reconnectProgressText = computed(() => {
  return `${props.reconnectAttempts}/${props.maxReconnectAttempts}`
})

/**
 * 重连策略文本
 */
const reconnectStrategyText = computed(() => {
  const strategyMap = {
    'fixed': '固定间隔',
    'linear': '线性递增',
    'exponential': '指数退避',
    'fibonacci': '斐波那契'
  }
  return strategyMap[props.reconnectStrategy] || props.reconnectStrategy
})

/**
 * 连接质量颜色
 */
const qualityColor = computed(() => {
  if (props.connectionQuality >= 80) {
    return '#67C23A'
  } else if (props.connectionQuality >= 60) {
    return '#E6A23C'
  } else if (props.connectionQuality >= 40) {
    return '#F56C6C'
  }
  return '#909399'
})

// === 方法 ===

/**
 * 处理点击事件
 */
function handleClick() {
  emit('click')
}

/**
 * 处理重连
 */
function handleReconnect() {
  emit('reconnect')
}

/**
 * 处理断开连接
 */
function handleDisconnect() {
  emit('disconnect')
}

/**
 * 刷新状态
 */
function handleRefreshStats() {
  emit('refresh')
}
</script>

<style scoped>
.ws-status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  user-select: none;
}

.status-badge:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.status-badge--connected {
  background-color: #f0f9ff;
  color: #059669;
  border: 1px solid #10b981;
}

.status-badge--connecting {
  background-color: #eff6ff;
  color: #2563eb;
  border: 1px solid #3b82f6;
}

.status-badge--disconnected {
  background-color: #f9fafb;
  color: #6b7280;
  border: 1px solid #d1d5db;
}

.status-badge--failed {
  background-color: #fef2f2;
  color: #dc2626;
  border: 1px solid #ef4444;
}

.status-badge--warning {
  animation: pulse-warning 2s ease-in-out infinite;
}

@keyframes pulse-warning {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

.status-icon {
  font-size: 16px;
}

.status-icon.is-spinning {
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

.status-text {
  line-height: 1;
}

.reconnect-progress {
  font-size: 12px;
  opacity: 0.8;
  margin-left: 4px;
}

.quality-bar {
  width: 40px;
  margin-left: 8px;
}

.details-btn {
  margin-left: 4px;
}

.status-details {
  padding: 8px;
}

.details-title {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 8px;
}

.detail-section {
  margin-bottom: 16px;
}

.detail-section:last-child {
  margin-bottom: 0;
}

.section-title {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 500;
  color: #6b7280;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
}

.detail-label {
  color: #6b7280;
  font-size: 14px;
}

.detail-value {
  color: #1f2937;
  font-size: 14px;
  font-weight: 500;
}

.detail-value.is-warning {
  color: #f59e0b;
}

.quality-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 120px;
}

.quality-text {
  font-size: 12px;
  color: #6b7280;
  white-space: nowrap;
}

.error-section {
  background-color: #fef2f2;
  padding: 8px;
  border-radius: 4px;
  margin-top: 12px;
}

.error-message {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  color: #dc2626;
  font-size: 14px;
  margin-bottom: 8px;
}

.error-icon {
  flex-shrink: 0;
  margin-top: 2px;
}

.error-suggestion {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  color: #6b7280;
  font-size: 13px;
}

.detail-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
}
</style>
