/**
 * @file use-ammeter-status.ts
 * @path src/composables/use-ammeter-status.ts
 * @description 皮安表状态管理组合式函数
 * @author Agent
 * @date 2026-03-26
 * @dependencies @/api/services, @/types/device
 */

import { ref, computed, onMounted, onUnmounted, type Ref, type ComputedRef } from 'vue'
import { AmmeterApiService } from '@/api/services'
import type { PicoammeterStatus } from '@/types/device'

/**
 * 皮安表状态管理选项
 */
export interface UseAmmeterStatusOptions {
  /** 设备ID */
  deviceId?: string
  /** 是否自动刷新状态 */
  autoRefresh?: boolean
  /** 刷新间隔（毫秒) */
  refreshInterval?: number
  /** 是否在组件挂载时立即获取状态 */
  immediate?: boolean
}

/**
 * 皮安表状态管理返回值
 */
export interface UseAmmeterStatusReturn {
  /** 皮安表状态 */
  ammeterStatus: Ref<PicoammeterStatus | null>
  /** 是否正在加载 */
  isLoading: Ref<boolean>
  /** 是否已连接 */
  isConnected: ComputedRef<boolean>
  /** 当前电流 */
  realTimeCurrent: ComputedRef<number>
  /** 电流范围 */
  range: ComputedRef<string>
  /** 采样率 */
  sampleRate: ComputedRef<number>
  /** 是否正在采集 */
  isSampling: ComputedRef<boolean>
  /** 错误信息 */
  error: Ref<Error | null>
  /** 刷新皮安表状态 */
  refreshAmmeterStatus: () => Promise<void>
  /** 获取皮安表配置 */
  fetchAmmeterConfig: () => Promise<void>
  /** 开始轮询 */
  startPolling: () => void
  /** 停止轮询 */
  stopPolling: () => void
}

/**
 * 皮安表状态管理组合式函数
 * 
 * @param options - 配置选项
 * @returns 皮安表状态管理方法和状态
 * 
 * @example
 * ```typescript
 * const {
 *   ammeterStatus,
 *   isConnected,
 *   realTimeCurrent,
 *   refreshAmmeterStatus
 * } = useAmmeterStatus({ deviceId: 'default', autoRefresh: true });
 * ```
 */
export function useAmmeterStatus(options: UseAmmeterStatusOptions = {}): UseAmmeterStatusReturn {
  const {
    deviceId = 'default',
    autoRefresh = true,
    refreshInterval = 100,
    immediate = true,
  } = options

  const ammeterApi = new AmmeterApiService(deviceId)

  const ammeterStatus = ref<PicoammeterStatus | null>(null)
  const isLoading = ref(false)
  const error = ref<Error | null>(null)
  let pollingTimer: ReturnType<typeof setInterval> | null = null)
  const isConnected = computed(() => {
    return ammeterStatus.value?.connected ?? false
  })

  const realTimeCurrent = computed(() => {
    return ammeterStatus.value?.current ?? 0
  })

  const range = computed(() => {
    return ammeterStatus.value?.range ?? 'auto'
  })

  const sampleRate = computed(() => {
    return ammeterStatus.value?.sampleRate ?? 0
  })

  const isSampling = computed(() => {
    return ammeterStatus.value?.isSampling ?? false
  })

  async function refreshAmmeterStatus(): Promise<void> {
    try {
      const result = await ammeterApi.getStatus()
      ammeterStatus.value = result
      error.value = null
    } catch (e) {
      error.value = e as Error
      console.error('[useAmmeterStatus] 获取皮安表状态失败:', e)
    }
  }

  async function fetchAmmeterConfig(): Promise<void> {
    isLoading.value = true

    try {
      const result = await ammeterApi.getConfig()
      console.log('Ammeter config:', result)
      error.value = null
    } catch (e) {
      error.value = e as Error
      console.error('[useAmmeterStatus] 获取皮安表配置失败:', e)
    } finally {
      isLoading.value = false
    }
  }

  function startPolling(): void {
    if (pollingTimer) return

    pollingTimer = setInterval(() => {
      refreshAmmeterStatus()
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
      refreshAmmeterStatus()
      fetchAmmeterConfig()
    }
    if (autoRefresh) {
      startPolling()
    }
  })

  onUnmounted(() => {
    stopPolling()
  })

  return {
    ammeterStatus,
    isLoading,
    isConnected,
    realTimeCurrent,
    range,
    sampleRate,
    isSampling,
    error,
    refreshAmmeterStatus,
    fetchAmmeterConfig,
    startPolling,
    stopPolling,
  }
}
