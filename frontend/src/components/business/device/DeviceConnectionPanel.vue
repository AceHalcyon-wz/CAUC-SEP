<script setup lang="ts">
/**
 * @file DeviceConnectionPanel.vue
 * @path src/components/business/device/DeviceConnectionPanel.vue
 * @description 设备连接管理面板业务组件
 * @author Agent
 * @date 2026-03-25
 * @safety: 设备连接操作需包含异常处理，连接失败时需显示明确错误信息
 */

import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { GlassCard } from '@/components/common/cards'
import { ConnectionBadge, StatusIndicator } from '@/components/common/status'
import { LoadingOverlay } from '@/components/common/feedback'
import { useDeviceStore } from '@/stores/device'
import type { DeviceInfo, DeviceConnectionStatus } from '@/types/device'

interface Props {
  autoRefresh?: boolean
  refreshInterval?: number
}

const props = withDefaults(defineProps<Props>(), {
  autoRefresh: true,
  refreshInterval: 5000,
})

const emit = defineEmits<{
  (e: 'connect', deviceId: string): void
  (e: 'disconnect', deviceId: string): void
  (e: 'connect-all'): void
  (e: 'disconnect-all'): void
  (e: 'error', error: Error): void
}>()

const deviceStore = useDeviceStore()

const isLoading = ref(false)
const connectingDevices = ref<Set<string>>(new Set())

const devices = computed<DeviceInfo[]>(() => deviceStore.devices)
const connectionStatus = computed<Record<string, DeviceConnectionStatus>>(
  () => deviceStore.connectionStatus
)

const connectedCount = computed(
  () => Object.values(connectionStatus.value).filter((s) => s === 'connected').length
)

const allConnected = computed(
  () => devices.value.length > 0 && connectedCount.value === devices.value.length
)

const anyConnecting = computed(
  () => Object.values(connectionStatus.value).some((s) => s === 'connecting')
)

async function handleConnect(deviceId: string): Promise<void> {
  if (connectingDevices.value.has(deviceId)) return

  connectingDevices.value.add(deviceId)
  try {
    await deviceStore.connectDevice(deviceId)
    ElMessage.success(`设备 ${deviceId} 连接成功`)
    emit('connect', deviceId)
  } catch (error) {
    const errorMessage = (error as Error).message || '未知错误'
    ElMessage.error(`设备 ${deviceId} 连接失败: ${errorMessage}`)
    emit('error', error as Error)
  } finally {
    connectingDevices.value.delete(deviceId)
  }
}

async function handleDisconnect(deviceId: string): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定要断开设备 ${deviceId} 的连接吗？`, '断开确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })

    await deviceStore.disconnectDevice(deviceId)
    ElMessage.success(`设备 ${deviceId} 已断开`)
    emit('disconnect', deviceId)
  } catch (error) {
    if ((error as string) !== 'cancel') {
      ElMessage.error(`断开设备失败: ${(error as Error).message || '未知错误'}`)
      emit('error', error as Error)
    }
  }
}

async function handleConnectAll(): Promise<void> {
  const disconnectedDevices = devices.value.filter(
    (d) => connectionStatus.value[d.id] !== 'connected'
  )

  if (disconnectedDevices.length === 0) {
    ElMessage.info('所有设备已连接')
    return
  }

  isLoading.value = true
  try {
    await deviceStore.connectAllDevices()
    ElMessage.success('所有设备连接成功')
    emit('connect-all')
  } catch (error) {
    ElMessage.error(`批量连接失败: ${(error as Error).message || '未知错误'}`)
    emit('error', error as Error)
  } finally {
    isLoading.value = false
  }
}

async function handleDisconnectAll(): Promise<void> {
  try {
    await ElMessageBox.confirm('确定要断开所有设备连接吗？', '断开确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })

    await deviceStore.disconnectAllDevices()
    ElMessage.success('所有设备已断开')
    emit('disconnect-all')
  } catch (error) {
    if ((error as string) !== 'cancel') {
      ElMessage.error(`批量断开失败: ${(error as Error).message || '未知错误'}`)
      emit('error', error as Error)
    }
  }
}

function getStatusType(status: DeviceConnectionStatus): 'success' | 'warning' | 'danger' | 'info' {
  const statusMap: Record<DeviceConnectionStatus, 'success' | 'warning' | 'danger' | 'info'> = {
    connected: 'success',
    connecting: 'warning',
    disconnected: 'info',
    error: 'danger',
  }
  return statusMap[status]
}

function getStatusLabel(status: DeviceConnectionStatus): string {
  const labelMap: Record<DeviceConnectionStatus, string> = {
    connected: '已连接',
    connecting: '连接中',
    disconnected: '未连接',
    error: '连接错误',
  }
  return labelMap[status]
}

let refreshTimer: ReturnType<typeof setInterval> | null = null

function startAutoRefresh(): void {
  if (props.autoRefresh && !refreshTimer) {
    refreshTimer = setInterval(() => {
      deviceStore.refreshDeviceStatus()
    }, props.refreshInterval)
  }
}

function stopAutoRefresh(): void {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

onMounted(() => {
  deviceStore.fetchDevices()
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
})

watch(
  () => props.autoRefresh,
  (newVal) => {
    if (newVal) {
      startAutoRefresh()
    } else {
      stopAutoRefresh()
    }
  }
)
</script>

<template>
  <GlassCard class="device-connection-panel" title="设备连接管理">
    <template #header>
      <div class="panel-header">
        <div class="header-left">
          <h3 class="header-title">设备连接管理</h3>
          <StatusIndicator
            v-if="allConnected"
            status="success"
            label="全部已连接"
            size="small"
          />
          <StatusIndicator
            v-else-if="connectedCount > 0"
            status="warning"
            :label="`${connectedCount}/${devices.length} 已连接`"
            size="small"
          />
          <StatusIndicator v-else status="default" label="未连接" size="small" />
        </div>
        <div class="header-actions">
          <el-button
            type="primary"
            size="small"
            :loading="isLoading || anyConnecting"
            :disabled="allConnected"
            @click="handleConnectAll"
          >
            全部连接
          </el-button>
          <el-button
            type="danger"
            size="small"
            plain
            :disabled="connectedCount === 0"
            @click="handleDisconnectAll"
          >
            全部断开
          </el-button>
        </div>
      </div>
    </template>

    <div class="device-list">
      <div v-for="device in devices" :key="device.id" class="device-item">
        <div class="device-info">
          <span class="device-name">{{ device.name }}</span>
          <span class="device-type">{{ device.type }}</span>
        </div>

        <div class="device-status">
          <ConnectionBadge
            :status="connectionStatus[device.id] || 'disconnected'"
            size="small"
          />
        </div>

        <div class="device-actions">
          <el-button
            v-if="connectionStatus[device.id] !== 'connected'"
            type="primary"
            size="small"
            :loading="connectingDevices.has(device.id)"
            :disabled="connectionStatus[device.id] === 'connecting'"
            @click="handleConnect(device.id)"
          >
            连接
          </el-button>
          <el-button
            v-else
            type="danger"
            size="small"
            plain
            @click="handleDisconnect(device.id)"
          >
            断开
          </el-button>
        </div>
      </div>

      <div v-if="devices.length === 0" class="empty-state">
        <span class="empty-icon">📭</span>
        <p class="empty-text">暂无设备</p>
      </div>
    </div>

    <LoadingOverlay :visible="isLoading" text="正在连接设备..." />
  </GlassCard>
</template>

<style scoped lang="scss">
.device-connection-panel {
  position: relative;

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;

    .header-left {
      display: flex;
      align-items: center;
      gap: 12px;

      .header-title {
        font-size: 16px;
        font-weight: 600;
        color: var(--color-text-primary);
        margin: 0;
      }
    }

    .header-actions {
      display: flex;
      gap: 8px;
    }
  }

  .device-list {
    display: flex;
    flex-direction: column;
    gap: 12px;

    .device-item {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 12px 16px;
      background: var(--color-bg-secondary);
      border-radius: 8px;
      transition: all 0.2s ease;

      &:hover {
        background: var(--color-bg-tertiary);
      }

      .device-info {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 4px;

        .device-name {
          font-weight: 500;
          color: var(--color-text-primary);
        }

        .device-type {
          font-size: 12px;
          color: var(--color-text-secondary);
        }
      }

      .device-status {
        flex-shrink: 0;
      }

      .device-actions {
        flex-shrink: 0;
      }
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 40px 0;
      color: var(--color-text-secondary);

      .empty-icon {
        font-size: 48px;
        margin-bottom: 12px;
      }

      .empty-text {
        font-size: 14px;
        margin: 0;
      }
    }
  }
}
</style>
