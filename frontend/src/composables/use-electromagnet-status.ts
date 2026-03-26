/**
 * @file use-electromagnet-status.ts
 * @path src/composables/use-electromagnet-status.ts
 * @description 电磁铁状态管理组合式函数
 * @author Agent
 * @date 2026-03-26
 * @dependencies @/api/services, @/types/device
 */

import { ref, computed, onMounted, onUnmounted, type Ref, type ComputedRef } from 'vue'
import { ElectromagnetApiService } from '@/api/services'
import type { ElectromagnetStatus } from '@/types/device'

/**
 * 电磁铁状态管理选项
 */
export interface UseElectromagnetStatusOptions {
  /** 设备ID */
  deviceId?: string
  /** 是否自动刷新状态 */
  autoRefresh?: boolean
  /** 刷新间隔（毫秒） */
  refreshInterval?: number
  /** 是否在组件挂载时立即获取状态 */
  immediate?: boolean
}

/**
 * 电磁铁状态管理返回值
 */
export interface UseElectromagnetStatusReturn {
  /** 电磁铁状态 */
  electromagnetStatus: Ref<ElectromagnetStatus | null>
  /** 是否正在加载 */
  isLoading: Ref<boolean>
  /** 是否已连接 */
  isConnected: ComputedRef<boolean>
  /** 是否处于报警状态 */
  isAlarm: ComputedRef<boolean>
  /** 当前电流 */
  realTimeCurrent: ComputedRef<number>
  /** 目标电流 */
  targetCurrent: ComputedRef<number>
  /** 最大电流 */
  maxCurrent: ComputedRef<number>
  /** 输出使能状态 */
  outputEnabled: ComputedRef<boolean>
  /** 错误信息 */
  error: Ref<Error | null>
  /** 刷新电磁铁状态 */
  refreshElectromagnetStatus: () => Promise<void>
  /** 获取电磁铁配置 */
  fetchElectromagnetConfig: () => Promise<void>
  /** 开始轮询 */
  startPolling: () => void
  /** 停止轮询 */
  stopPolling: () => void
}

/**
 * 电磁铁状态管理组合式函数
 * 
 * @param options - 配置选项
 * @returns 电磁铁状态管理方法和状态
 * 
 * @example
 * ```typescript
 * const {
 *   electromagnetStatus,
 *   isConnected,
 *   isAlarm,
 *   realTimeCurrent,
 *   refreshElectromagnetStatus
 * } = useElectromagnetStatus({ deviceId: 'default', autoRefresh: true });
 * ```
 */
export function useElectromagnetStatus(options: UseElectromagnetStatusOptions = {}): UseElectromagnetStatusReturn {
  const {
    deviceId = 'default',
    autoRefresh = true,
    refreshInterval = 100,
    immediate = true,
  } = options

  const electromagnetApi = new ElectromagnetApiService(deviceId)

  const electromagnetStatus = ref<ElectromagnetStatus | null>(null)
  const isLoading = ref(false)
  const error = ref<Error | null>(null)

  let pollingTimer: ReturnType<typeof setInterval> | null = null

  const isConnected = computed(() => {
    return electromagnetStatus.value?.connected ?? false
  })

  const isAlarm = computed(() => {
    return (electromagnetStatus.value?.alarmCode ?? 0) !== 0
  })

  const realTimeCurrent = computed(() => {
    return electromagnetStatus.value?.current ?? 0
  })

  const targetCurrent = computed(() => {
    return electromagnetStatus.value?.targetCurrent ?? 0
  })

  const maxCurrent = computed(() => {
    return electromagnetStatus.value?.maxCurrent ?? 0
  })

  const outputEnabled = computed(() => {
    return electromagnetStatus.value?.outputEnabled ?? false
  })

  async function refreshElectromagnetStatus(): Promise<void> {
    try {
      const result = await electromagnetApi.getStatus()
      electromagnetStatus.value = result
      error.value = null
    } catch (e) {
      error.value = e as Error
      console.error('[useElectromagnetStatus] 获取电磁铁状态失败:', e)
    }
  }

  async function fetchElectromagnetConfig(): Promise<void> {
    isLoading.value = true

    try {
      const result = await electromagnetApi.getConfig()
      console.log('Electromagnet config:', result)
      error.value = null
    } catch (e) {
      error.value = e as Error
      console.error('[useElectromagnetStatus] 获取电磁铁配置失败:', e)
    } finally {
      isLoading.value = false
    }
  }

  function startPolling(): void {
    if (pollingTimer) return

    pollingTimer = setInterval(() => {
      refreshElectromagnetStatus()
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
      refreshElectromagnetStatus()
      fetchElectromagnetConfig()
    }
    if (autoRefresh) {
      startPolling()
    }
  })

  onUnmounted(() => {
    stopPolling()
  })

  return {
    electromagnetStatus,
    isLoading,
    isConnected,
    isAlarm,
    realTimeCurrent,
    targetCurrent,
    maxCurrent,
    outputEnabled,
    error,
    refreshElectromagnetStatus,
    fetchElectromagnetConfig,
    startPolling,
    stopPolling,
  }
}

