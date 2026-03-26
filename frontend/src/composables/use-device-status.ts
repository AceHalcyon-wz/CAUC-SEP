/**
 * @file use-device-status.ts
 * @path src/composables/use-device-status.ts
 * @description 设备状态管理组合式函数
 * @author Agent
 * @date 2026-03-25
 * @dependencies @/api/services, @/types/device
 */

import { ref, computed, onMounted, onUnmounted, type Ref, type ComputedRef } from 'vue'
import { DeviceApiService } from '@/api/services'
import type { DeviceInfo, DeviceStatus, DeviceConnectionStatus } from '@/types/device'

/**
 * 设备状态管理选项
 */
export interface UseDeviceStatusOptions {
  /** 是否自动刷新状态 */
  autoRefresh?: boolean
  /** 刷新间隔（毫秒） */
  refreshInterval?: number
  /** 是否在组件挂载时立即获取状态 */
  immediate?: boolean
}

/**
 * 设备状态管理返回值
 */
export interface UseDeviceStatusReturn {
  /** 设备列表 */
  devices: Ref<DeviceInfo[]>
  /** 连接状态映射 */
  connectionStatus: Ref<Record<string, DeviceConnectionStatus>>
  /** 设备状态映射 */
  deviceStatus: Ref<Record<string, DeviceStatus>>
  /** 是否正在加载 */
  isLoading: Ref<boolean>
  /** 错误信息 */
  error: Ref<Error | null>
  /** 已连接设备数量 */
  connectedCount: ComputedRef<number>
  /** 是否全部已连接 */
  allConnected: ComputedRef<boolean>
  /** 刷新设备状态 */
  refreshStatus: () => Promise<void>
  /** 连接设备 */
  connectDevice: (deviceId: string) => Promise<boolean>
  /** 断开设备 */
  disconnectDevice: (deviceId: string) => Promise<boolean>
  /** 连接所有设备 */
  connectAllDevices: () => Promise<boolean>
  /** 断开所有设备 */
  disconnectAllDevices: () => Promise<boolean>
  /** 开始轮询 */
  startPolling: () => void
  /** 停止轮询 */
  stopPolling: () => void
}

/**
 * 设备状态管理组合式函数
 * 
 * @param options - 配置选项
 * @returns 设备状态管理方法和状态
 * 
 * @example
 * ```typescript
 * const {
 *   devices,
 *   connectionStatus,
 *   isLoading,
 *   refreshStatus,
 *   connectDevice
 * } = useDeviceStatus({ autoRefresh: true, refreshInterval: 5000 });
 * ```
 */
export function useDeviceStatus(options: UseDeviceStatusOptions = {}): UseDeviceStatusReturn {
  const {
    autoRefresh = true,
    refreshInterval = 5000,
    immediate = true,
  } = options

  const deviceApi = new DeviceApiService()

  const devices = ref<DeviceInfo[]>([])
  const connectionStatus = ref<Record<string, DeviceConnectionStatus>>({})
  const deviceStatus = ref<Record<string, DeviceStatus>>({})
  const isLoading = ref(false)
  const error = ref<Error | null>(null)

  let pollingTimer: ReturnType<typeof setInterval> | null = null

  const connectedCount = computed(() => {
    return Object.values(connectionStatus.value).filter((s) => s === 'connected').length
  })

  const allConnected = computed(() => {
    return devices.value.length > 0 && connectedCount.value === devices.value.length
  })

  async function fetchDevices(): Promise<void> {
    isLoading.value = true
    error.value = null

    try {
      const result = await deviceApi.getDevices()
      devices.value = result

      const statusMap: Record<string, DeviceConnectionStatus> = {}
      for (const device of result) {
        statusMap[device.id] = connectionStatus.value[device.id] || 'disconnected'
      }
      connectionStatus.value = statusMap
    } catch (e) {
      error.value = e as Error
      console.error('[useDeviceStatus] 获取设备列表失败:', e)
    } finally {
      isLoading.value = false
    }
  }

  async function refreshStatus(): Promise<void> {
    isLoading.value = true
    error.value = null

    try {
      await deviceApi.refreshStatus()

      for (const device of devices.value) {
        const statusResult = await deviceApi.getDeviceStatus(device.id)
        if (statusResult) {
          connectionStatus.value[device.id] = statusResult.connectionStatus
          deviceStatus.value[device.id] = statusResult.status
        }
      }
    } catch (e) {
      error.value = e as Error
      console.error('[useDeviceStatus] 刷新状态失败:', e)
    } finally {
      isLoading.value = false
    }
  }

  async function connectDevice(deviceId: string): Promise<boolean> {
    connectionStatus.value[deviceId] = 'connecting'

    try {
      const result = await deviceApi.connectDevice(deviceId)
      connectionStatus.value[deviceId] = result ? 'connected' : 'error'
      return result
    } catch (e) {
      connectionStatus.value[deviceId] = 'error'
      error.value = e as Error
      console.error(`[useDeviceStatus] 连接设备 ${deviceId} 失败:`, e)
      return false
    }
  }

  async function disconnectDevice(deviceId: string): Promise<boolean> {
    try {
      const result = await deviceApi.disconnectDevice(deviceId)
      if (result) {
        connectionStatus.value[deviceId] = 'disconnected'
      }
      return result
    } catch (e) {
      error.value = e as Error
      console.error(`[useDeviceStatus] 断开设备 ${deviceId} 失败:`, e)
      return false
    }
  }

  async function connectAllDevices(): Promise<boolean> {
    isLoading.value = true

    try {
      const result = await deviceApi.connectAllDevices()
      if (result) {
        for (const device of devices.value) {
          connectionStatus.value[device.id] = 'connected'
        }
      }
      return result
    } catch (e) {
      error.value = e as Error
      console.error('[useDeviceStatus] 批量连接设备失败:', e)
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function disconnectAllDevices(): Promise<boolean> {
    try {
      const result = await deviceApi.disconnectAllDevices()
      if (result) {
        for (const device of devices.value) {
          connectionStatus.value[device.id] = 'disconnected'
        }
      }
      return result
    } catch (e) {
      error.value = e as Error
      console.error('[useDeviceStatus] 批量断开设备失败:', e)
      return false
    }
  }

  function startPolling(): void {
    if (pollingTimer) return

    pollingTimer = setInterval(() => {
      refreshStatus()
    }, refreshInterval)
  }

  function stopPolling(): void {
    if (pollingTimer) {
      clearInterval(pollingTimer)
      pollingTimer = null
    }
  }

  onMounted(() => {
    if (immediate) {
      fetchDevices()
    }
    if (autoRefresh) {
      startPolling()
    }
  })

  onUnmounted(() => {
    stopPolling()
  })

  return {
    devices,
    connectionStatus,
    deviceStatus,
    isLoading,
    error,
    connectedCount,
    allConnected,
    refreshStatus,
    connectDevice,
    disconnectDevice,
    connectAllDevices,
    disconnectAllDevices,
    startPolling,
    stopPolling,
  }
}

export default useDeviceStatus
