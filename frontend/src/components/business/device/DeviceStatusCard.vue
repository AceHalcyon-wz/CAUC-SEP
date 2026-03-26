<script setup lang="ts">
/**
 * @file DeviceStatusCard.vue
 * @path src/components/business/device/DeviceStatusCard.vue
 * @description 设备状态卡片业务组件
 * @author Agent
 * @date 2026-03-25
 */

import { computed } from 'vue'
import { GlassCard } from '@/components/common/cards'
import { StatusIndicator, StatusTag } from '@/components/common/status'
import type { DeviceInfo, DeviceStatus, DeviceConnectionStatus } from '@/types/device'

interface Props {
  device: DeviceInfo
  status: DeviceStatus
  connectionStatus: DeviceConnectionStatus
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'click'): void
  (e: 'refresh'): void
}>()

const statusItems = computed(() => [
  { label: '设备ID', value: props.device.id },
  { label: '设备类型', value: props.device.type },
  { label: '连接状态', value: getConnectionLabel(props.connectionStatus) },
])

const alarmCount = computed(() => {
  return props.status.alarms?.length || 0
})

const hasAlarm = computed(() => alarmCount.value > 0)

function getConnectionLabel(status: DeviceConnectionStatus): string {
  const labels: Record<DeviceConnectionStatus, string> = {
    connected: '已连接',
    connecting: '连接中',
    disconnected: '未连接',
    error: '错误',
  }
  return labels[status]
}

function getStatusType(status: DeviceConnectionStatus): 'success' | 'warning' | 'danger' | 'info' {
  const map: Record<DeviceConnectionStatus, 'success' | 'warning' | 'danger' | 'info'> = {
    connected: 'success',
    connecting: 'warning',
    disconnected: 'info',
    error: 'danger',
  }
  return map[status]
}
</script>

<template>
  <GlassCard class="device-status-card" @click="emit('click')">
    <template #header>
      <div class="card-header">
        <div class="header-left">
          <span class="device-icon">{{ device.icon || '🔌' }}</span>
          <h4 class="device-name">{{ device.name }}</h4>
        </div>
        <div class="header-right">
          <StatusIndicator
            :status="getStatusType(connectionStatus)"
            :pulse="connectionStatus === 'connecting'"
          />
          <StatusTag v-if="hasAlarm" type="danger" :label="`${alarmCount} 报警`" round />
        </div>
      </div>
    </template>

    <div class="card-body">
      <div v-for="item in statusItems" :key="item.label" class="status-row">
        <span class="status-label">{{ item.label }}</span>
        <span class="status-value">{{ item.value }}</span>
      </div>

      <slot />
    </div>

    <template v-if="$slots.footer" #footer>
      <slot name="footer" />
    </template>
  </GlassCard>
</template>

<style scoped lang="scss">
.device-status-card {
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;

    .header-left {
      display: flex;
      align-items: center;
      gap: 8px;

      .device-icon {
        font-size: 20px;
      }

      .device-name {
        font-size: 14px;
        font-weight: 600;
        color: var(--color-text-primary);
        margin: 0;
      }
    }

    .header-right {
      display: flex;
      align-items: center;
      gap: 8px;
    }
  }

  .card-body {
    .status-row {
      display: flex;
      justify-content: space-between;
      padding: 8px 0;
      border-bottom: 1px solid var(--color-border-light);

      &:last-child {
        border-bottom: none;
      }

      .status-label {
        font-size: 12px;
        color: var(--color-text-secondary);
      }

      .status-value {
        font-size: 12px;
        font-weight: 500;
        color: var(--color-text-primary);
      }
    }
  }
}
</style>
