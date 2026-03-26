<script setup lang="ts">
/**
 * @file StatusIndicator.vue
 * @path src/components/common/status/StatusIndicator.vue
 * @description 状态指示器组件，用于显示设备/连接状态
 * @author Agent
 * @date 2026-03-25
 */

import { computed } from 'vue'

type StatusType = 'success' | 'warning' | 'danger' | 'info' | 'default'
type StatusSize = 'small' | 'default' | 'large'

interface Props {
  status?: StatusType
  size?: StatusSize
  pulse?: boolean
  label?: string
  showDot?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  status: 'default',
  size: 'default',
  pulse: false,
  label: '',
  showDot: true,
})

const statusColors: Record<StatusType, string> = {
  success: '#67c23a',
  warning: '#e6a23c',
  danger: '#f56c6c',
  info: '#909399',
  default: '#c0c4cc',
}

const dotSize = computed(() => {
  const sizeMap = {
    small: '8px',
    default: '12px',
    large: '16px',
  }
  return sizeMap[props.size]
})

const fontSize = computed(() => {
  const sizeMap = {
    small: '12px',
    default: '14px',
    large: '16px',
  }
  return sizeMap[props.size]
})
</script>

<template>
  <span class="status-indicator" :class="[`status-indicator--${status}`, { 'is-pulse': pulse }]">
    <span
      v-if="showDot"
      class="status-dot"
      :style="{
        width: dotSize,
        height: dotSize,
        backgroundColor: statusColors[status],
      }"
    />
    <span v-if="label" class="status-label" :style="{ fontSize }">
      {{ label }}
    </span>
    <slot />
  </span>
</template>

<style scoped lang="scss">
.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 8px;

  .status-dot {
    border-radius: 50%;
    flex-shrink: 0;
  }

  &.is-pulse .status-dot {
    animation: pulse 2s infinite;
  }

  .status-label {
    color: var(--color-text-primary);
    font-weight: 500;
  }
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 currentColor;
    opacity: 1;
  }
  70% {
    box-shadow: 0 0 0 10px transparent;
    opacity: 0.7;
  }
  100% {
    box-shadow: 0 0 0 0 transparent;
    opacity: 1;
  }
}
</style>
