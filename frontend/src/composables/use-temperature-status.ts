/**
 * @file use-temperature-status.ts
 * @path src/composables/use-temperature-status.ts
 * @description 温度控制器状态管理组合式函数
 * @author Agent
 * @date 2026-03-26
 * @dependencies @/api/services, @/types/device
 */

import { ref, computed, onMounted, onUnmounted, type Ref, type ComputedRef } from 'vue'
import { TemperatureApiService } from '@/api/services'
import type { TemperatureControllerStatus } from '@/types/device'

/**
 * 温度控制器状态管理选项
 */
export interface UseTemperatureStatusOptions {
  /** 传感器ID */
  sensorId?: string
  /** 是否自动刷新状态 */
  autoRefresh?: boolean
  /** 刷新间隔（毫秒) */
  refreshInterval?: number
  /** 是否在组件挂载时立即获取状态 */
  immediate?: boolean
}

/**
 * 温度控制器状态管理返回值
 */
export interface UseTemperatureStatusReturn {
  /** 温度控制器状态 */
  temperatureStatus: Ref<TemperatureControllerStatus | null>
  /** 是否正在加载 */
  isLoading: Ref<boolean>
  /** 是否已连接 */
  isConnected: ComputedRef<boolean>
  /** 是否正在加热 */
  isHeating: ComputedRef<boolean>
  /** 是否正在冷却 */
  isCooling: ComputedRef<boolean>
  /** 当前温度 */
  realTimeTemperature: ComputedRef<number>
  /** 目标温度 */
  targetTemperature: ComputedRef<number>
  /** 错误信息 */
  error: Ref<Error | null>
  /** 刷新温度控制器状态 */
  refreshTemperatureStatus: () => Promise<void>
  /** 获取温度控制器配置 */
  fetchTemperatureConfig: () => Promise<void>
  /** 开始轮询 */
  startPolling: () => void
  /** 停止轮询 */
  stopPolling: () => void
}

/**
 * 温度控制器状态管理组合式函数
 * 
 * @param options - 配置选项
 * @returns 温度控制器状态管理方法和状态
 * 
 * @example
 * ```typescript
 * const {
 *   temperatureStatus,
 *   isConnected,
 *   isHeating,
 *   isCooling,
 *   realTimeTemperature,
 *   refreshTemperatureStatus
 * } = useTemperatureStatus({ sensorId: 'default', autoRefresh: true });
 * ```
 */
export function useTemperatureStatus(options: UseTemperatureStatusOptions = {}): UseTemperatureStatusReturn {
  const {
    sensorId = 'default',
    autoRefresh = true,
    refreshInterval = 100,
    immediate = true,
  } = options

  const temperatureApi = new TemperatureApiService(sensorId)

  const temperatureStatus = ref<TemperatureControllerStatus | null>(null)
  const isLoading = ref(false)
  const error = ref<Error | null>(null)

  let pollingTimer: ReturnType<typeof setInterval> | null = null)
  const isConnected = computed(() => {
    return temperatureStatus.value?.connected ?? false
  })

  const isHeating = computed(() => {
    return temperatureStatus.value?.isHeating ?? false
  })

  const isCooling = computed(() => {
    return temperatureStatus.value?.isCooling ?? false
  })

  const realTimeTemperature = computed(() => {
    return temperatureStatus.value?.temperature ?? 0
  })

  const targetTemperature = computed(() => {
    return temperatureStatus.value?.targetTemperature ?? 0
  })

  async function refreshTemperatureStatus(): Promise<void> {
    try {
      const result = await temperatureApi.getStatus()
      temperatureStatus.value = result
      error.value = null
    } catch (e) {
      error.value = e as Error
      console.error('[useTemperatureStatus] 获取温度控制器状态失败:', e)
    }
  }

  async function fetchTemperatureConfig(): Promise<void> {
    isLoading.value = true

    try {
      const result = await temperatureApi.getConfig()
      console.log('Temperature config:', result)
      error.value = null
    } catch (e) {
      error.value = e as Error
      console.error('[useTemperatureStatus] 获取温度控制器配置失败:', e)
    } finally {
      isLoading.value = false
    }
  }

  function startPolling(): void {
    if (pollingTimer) return

    pollingTimer = setInterval(() => {
      refreshTemperatureStatus()
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
      refreshTemperatureStatus()
      fetchTemperatureConfig()
    }
    if (autoRefresh) {
      startPolling()
    }
  })

  onUnmounted(() => {
    stopPolling()
  })

  return {
    temperatureStatus,
    isLoading,
    isConnected,
    isHeating,
    isCooling,
    realTimeTemperature,
    targetTemperature,
    error,
    refreshTemperatureStatus,
    fetchTemperatureConfig,
    startPolling,
    stopPolling,
  }
}
