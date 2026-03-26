<script setup lang="ts">
/**
 * @file ConnectionBadge.vue
 * @path src/components/common/status/ConnectionBadge.vue
 * @description 连接状态徽章组件
 * @author Agent
 * @date 2026-03-25
 */

import { computed } from 'vue'
import StatusIndicator from './StatusIndicator.vue'

type ConnectionStatus = 'connected' | 'disconnected' | 'connecting' | 'error'

interface Props {
  status: ConnectionStatus
  showLabel?: boolean
  size?: 'small' | 'default' | 'large'
}

const props = withDefaults(defineProps<Props>(), {
  showLabel: true,
  size: 'default',
})

const statusConfig = computed(() => {
  const config: Record<ConnectionStatus, { type: 'success' | 'warning' | 'danger' | 'info'; label: string; pulse: boolean }> = {
    connected: { type: 'success', label: '已连接', pulse: false },
    disconnected: { type: 'default', label: '未连接', pulse: false },
    connecting: { type: 'warning', label: '连接中', pulse: true },
    error: { type: 'danger', label: '连接错误', pulse: false },
  }
  return config[props.status]
})
</script>

<template>
  <div class="connection-badge">
    <StatusIndicator
      :status="statusConfig.type"
      :size="size"
      :pulse="statusConfig.pulse"
      :label="showLabel ? statusConfig.label : ''"
    />
    <slot />
  </div>
</template>

<style scoped lang="scss">
.connection-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
</style>
