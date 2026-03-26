/**
 * @file use-motor-status.ts
 * @path src/composables/use-motor-status.ts
 * @description 电机状态管理组合式函数
 * @author Agent
 * @date 2026-03-25
 * @dependencies @/api/services, @/types/device
 */

import { ref, computed, onMounted, onUnmounted, type Ref, type ComputedRef } from 'vue'
import { MotorApiService } from '@/api/services'
import type { MotorStatus, MotorConfig } from '@/types/device'

/**
 * 电机状态管理选项
 */
export interface UseMotorStatusOptions {
  /** 电机ID */
  motorId?: string
  /** 是否自动刷新状态 */
  autoRefresh?: boolean
  /** 刷新间隔（毫秒） */
  refreshInterval?: number
  /** 是否在组件挂载时立即获取状态 */
  immediate?: boolean
}

/**
 * 电机状态管理返回值
 */
export interface UseMotorStatusReturn {
  /** 电机状态 */
  motorStatus: Ref<MotorStatus | null>
  /** 电机配置 */
  motorConfig: Ref<MotorConfig | null>
  /** 是否正在加载 */
  isLoading: Ref<boolean>
  /** 是否已连接 */
  isConnected: ComputedRef<boolean>
  /** 是否处于报警状态 */
  isAlarm: ComputedRef<boolean>
  /** 实时位置 */
  realTimePosition: ComputedRef<number>
  /** 实时速度 */
  realTimeSpeed: ComputedRef<number>
  /** 错误信息 */
  error: Ref<Error | null>
  /** 刷新电机状态 */
  refreshMotorStatus: () => Promise<void>
  /** 获取电机配置 */
  fetchMotorConfig: () => Promise<void>
  /** 开始轮询 */
  startPolling: () => void
  /** 停止轮询 */
  stopPolling: () => void
}

/**
 * 电机状态管理组合式函数
 * 
 * @param options - 配置选项
 * @returns 电机状态管理方法和状态
 * 
 * @example
 * ```typescript
 * const {
 *   motorStatus,
 *   isConnected,
 *   isAlarm,
 *   realTimePosition,
 *   refreshMotorStatus
 * } = useMotorStatus({ motorId: 'default', autoRefresh: true });
 * ```
 */
export function useMotorStatus(options: UseMotorStatusOptions = {}): UseMotorStatusReturn {
  const {
    motorId = 'default',
    autoRefresh = true,
    refreshInterval = 100,
    immediate = true,
  } = options

  const motorApi = new MotorApiService(motorId)

  const motorStatus = ref<MotorStatus | null>(null)
  const motorConfig = ref<MotorConfig | null>(null)
  const isLoading = ref(false)
  const error = ref<Error | null>(null)

  let pollingTimer: ReturnType<typeof setInterval> | null = null

  const isConnected = computed(() => {
    return motorStatus.value?.connected ?? false
  })

  const isAlarm = computed(() => {
    return (motorStatus.value?.alarmCode ?? 0) !== 0
  })

  const realTimePosition = computed(() => {
    return motorStatus.value?.positionMm ?? 0
  })

  const realTimeSpeed = computed(() => {
    return motorStatus.value?.velocityMmS ?? 0
  })

  async function refreshMotorStatus(): Promise<void> {
    try {
      const result = await motorApi.getStatus()
      motorStatus.value = result
      error.value = null
    } catch (e) {
      error.value = e as Error
      console.error('[useMotorStatus] 获取电机状态失败:', e)
    }
  }

  async function fetchMotorConfig(): Promise<void> {
    isLoading.value = true

    try {
      const result = await motorApi.getConfig()
      motorConfig.value = result
      error.value = null
    } catch (e) {
      error.value = e as Error
      console.error('[useMotorStatus] 获取电机配置失败:', e)
    } finally {
      isLoading.value = false
    }
  }

  function startPolling(): void {
    if (pollingTimer) return

    pollingTimer = setInterval(() => {
      refreshMotorStatus()
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
      refreshMotorStatus()
      fetchMotorConfig()
    }
    if (autoRefresh) {
      startPolling()
    }
  })

  onUnmounted(() => {
    stopPolling()
  })

  return {
    motorStatus,
    motorConfig,
    isLoading,
    isConnected,
    isAlarm,
    realTimePosition,
    realTimeSpeed,
    error,
    refreshMotorStatus,
    fetchMotorConfig,
    startPolling,
    stopPolling,
  }
}

export default useMotorStatus
