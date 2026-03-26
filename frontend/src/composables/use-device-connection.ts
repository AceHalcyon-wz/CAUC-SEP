/**
 * @file use-device-connection.ts
 * @path src/composables/use-device-connection.ts
 * @description 设备连接管理组合式函数
 * @author Agent
 * @date 2026-03-25
 */

import { ref, computed, onMounted, onUnmounted, type Ref, type ComputedRef } from 'vue'
import { DeviceApiService } from '@/api/services'
import type { DeviceConnectionStatus } from '@/types/device'

/**
 * 设备连接管理选项
 */
export interface UseDeviceConnectionOptions {
  /** 设备ID */
  deviceId: string
  /** 是否自动重连 */
  autoReconnect?: boolean
  /** 重连间隔（毫秒） */
  reconnectInterval?: number
  /** 最大重连次数 */
  maxReconnectAttempts?: number
}

/**
 * 设备连接管理返回值
 */
export interface UseDeviceConnectionReturn {
  /** 连接状态 */
  status: Ref<DeviceConnectionStatus>
  /** 是否已连接 */
  isConnected: ComputedRef<boolean>
  /** 是否正在连接 */
  isConnecting: ComputedRef<boolean>
  /** 是否连接错误 */
  hasError: ComputedRef<boolean>
  /** 重连次数 */
  reconnectAttempts: Ref<number>
  /** 错误信息 */
  error: Ref<string | null>
  /** 连接设备 */
  connect: () => Promise<boolean>
  /** 断开连接 */
  disconnect: () => Promise<boolean>
  /** 重置连接 */
  reconnect: () => Promise<boolean>
}

/**
 * 设备连接管理组合式函数
 * 
 * @param options - 配置选项
 * @returns 设备连接管理方法和状态
 */
export function useDeviceConnection(options: UseDeviceConnectionOptions): UseDeviceConnectionReturn {
  const {
    deviceId,
    autoReconnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
  } = options

  const deviceApi = new DeviceApiService()

  const status = ref<DeviceConnectionStatus>('disconnected')
  const reconnectAttempts = ref(0)
  const error = ref<string | null>(null)

  let reconnectTimer: ReturnType<typeof setInterval> | null = null

  const isConnected = computed(() => status.value === 'connected')
  const isConnecting = computed(() => status.value === 'connecting')
  const hasError = computed(() => status.value === 'error')

  async function connect(): Promise<boolean> {
    status.value = 'connecting'
    error.value = null

    try {
      const result = await deviceApi.connectDevice(deviceId)
      if (result) {
        status.value = 'connected'
        reconnectAttempts.value = 0
        return true
      } else {
        status.value = 'error'
        error.value = '连接失败'
        return false
      }
    } catch (e) {
      status.value = 'error'
      error.value = (e as Error).message
      console.error(`[useDeviceConnection] 连接设备 ${deviceId} 失败:`, e)
      return false
    }
  }

  async function disconnect(): Promise<boolean> {
    stopReconnectTimer()

    try {
      const result = await deviceApi.disconnectDevice(deviceId)
      if (result) {
        status.value = 'disconnected'
        error.value = null
      }
      return result
    } catch (e) {
      error.value = (e as Error).message
      console.error(`[useDeviceConnection] 断开设备 ${deviceId} 失败:`, e)
      return false
    }
  }

  async function reconnect(): Promise<boolean> {
    await disconnect()
    return connect()
  }

  function startReconnectTimer(): void {
    if (!autoReconnect || reconnectTimer) return

    reconnectTimer = setInterval(() => {
      if (reconnectAttempts.value < maxReconnectAttempts) {
        reconnectAttempts.value++
        console.log(`[useDeviceConnection] 尝试重连 (${reconnectAttempts.value}/${maxReconnectAttempts})`)
        connect()
      } else {
        stopReconnectTimer()
        error.value = `重连失败，已达到最大重连次数 ${maxReconnectAttempts}`
      }
    }, reconnectInterval)
  }

  function stopReconnectTimer(): void {
    if (reconnectTimer) {
      clearInterval(reconnectTimer)
      reconnectTimer = null
    }
  }

  onMounted(() => {
    if (autoReconnect && hasError.value) {
      startReconnectTimer()
    }
  })

  onUnmounted(() => {
    stopReconnectTimer()
  })

  return {
    status,
    isConnected,
    isConnecting,
    hasError,
    reconnectAttempts,
    error,
    connect,
    disconnect,
    reconnect,
  }
}

export default useDeviceConnection
