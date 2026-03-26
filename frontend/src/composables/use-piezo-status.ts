/**
 * @file use-piezo-status.ts
 * @path src/composables/use-piezo-status.ts
 * @description 压电控制器状态管理组合式函数
 * @author Agent
 * @date 2026-03-26
 * @dependencies @/api/services, @/types/device
 */

import { ref, computed, onMounted, onUnmounted, type Ref, type ComputedRef } from 'vue'
import { PiezoApiService } from '@/api/services'
import type { PiezoControllerStatus } from '@/types/device'

/**
 * 压电控制器状态管理选项
 */
export interface UsePiezoStatusOptions {
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
 * 压电控制器状态管理返回值
 */
export interface UsePiezoStatusReturn {
  /** 压电控制器状态 */
  piezoStatus: Ref<PiezoControllerStatus | null>
  /** 是否正在加载 */
  isLoading: Ref<boolean>
  /** 是否已连接 */
  isConnected: ComputedRef<boolean>
  /** 各通道电压 */
  voltages: ComputedRef<number[]>
  /** 各通道位移 */
  displacements: ComputedRef<number[]>
  /** 最大电压 */
  maxVoltage: ComputedRef<number>
  /** 最大位移 */
  maxDisplacement: ComputedRef<number>
  /** 错误信息 */
  error: Ref<Error | null>
  /** 刷新压电控制器状态 */
  refreshPiezoStatus: () => Promise<void>
  /** 获取压电控制器配置 */
  fetchPiezoConfig: () => Promise<void>
  /** 开始轮询 */
  startPolling: () => void
  /** 停止轮询 */
  stopPolling: () => void
}

/**
 * 压电控制器状态管理组合式函数
 * 
 * @param options - 配置选项
 * @returns 压电控制器状态管理方法和状态
 * 
 * @example
 * ```typescript
 * const {
 *   piezoStatus,
 *   isConnected,
 *   voltages,
 *   displacements,
 *   refreshPiezoStatus
 * } = usePiezoStatus({ deviceId: 'default', autoRefresh: true });
 * ```
 */
export function usePiezoStatus(options: UsePiezoStatusOptions = {}): UsePiezoStatusReturn {
  const {
    deviceId = 'default',
    autoRefresh = true,
    refreshInterval = 100,
    immediate = true,
  } = options

  const piezoApi = new PiezoApiService(deviceId)

  const piezoStatus = ref<PiezoControllerStatus | null>(null)
  const isLoading = ref(false)
  const error = ref<Error | null>(null)
  let pollingTimer: ReturnType<typeof setInterval> | null = null)
  const isConnected = computed(() => {
    return piezoStatus.value?.connected ?? false
  })

  const voltages = computed(() => {
    return piezoStatus.value?.voltages ?? []
  })

  const displacements = computed(() => {
    return piezoStatus.value?.displacements ?? []
  })

  const maxVoltage = computed(() => {
    return piezoStatus.value?.maxVoltage ?? 0
  })

  const maxDisplacement = computed(() => {
    return piezoStatus.value?.maxDisplacement ?? 0
  })

  async function refreshPiezoStatus(): Promise<void> {
    try {
      const result = await piezoApi.getStatus()
      piezoStatus.value = result
      error.value = null
    } catch (e) {
      error.value = e as Error
      console.error('[usePiezoStatus] 获取压电控制器状态失败:', e)
    }
  }

  async function fetchPiezoConfig(): Promise<void> {
    isLoading.value = true

    try {
      const result = await piezoApi.getConfig()
      console.log('Piezo config:', result)
      error.value = null
    } catch (e) {
      error.value = e as Error
      console.error('[usePiezoStatus] 获取压电控制器配置失败:', e)
    } finally {
      isLoading.value = false
    }
  }

  function startPolling(): void {
    if (pollingTimer) return

    pollingTimer = setInterval(() => {
      refreshPiezoStatus()
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
      refreshPiezoStatus()
      fetchPiezoConfig()
    }
    if (autoRefresh) {
      startPolling()
    }
  })

  onUnmounted(() => {
    stopPolling()
  })

  return {
    piezoStatus,
    isLoading,
    isConnected,
    voltages,
    displacements,
    maxVoltage,
    maxDisplacement,
    error,
    refreshPiezoStatus,
    fetchPiezoConfig,
    startPolling,
    stopPolling,
  }
}
