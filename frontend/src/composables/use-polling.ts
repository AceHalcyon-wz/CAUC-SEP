/**
 * @file use-polling.ts
 * @path src/composables/use-polling.ts
 * @description 轮询管理组合式函数
 * @author Agent
 * @date 2026-03-25
 */

import { ref, onUnmounted } from 'vue'

/**
 * 轮询管理选项
 */
export interface UsePollingOptions {
  /** 轮询间隔（毫秒） */
  interval: number
  /** 是否立即执行 */
  immediate?: boolean
  /** 是否在页面不可见时暂停 */
  pauseOnHidden?: boolean
}

/**
 * 轮询管理返回值
 */
export interface UsePollingReturn {
  /** 是否正在轮询 */
  isPolling: ReturnType<typeof ref<boolean>>
  /** 开始轮询 */
  start: () => void
  /** 停止轮询 */
  stop: () => void
  /** 切换轮询状态 */
  toggle: () => void
}

/**
 * 轮询管理组合式函数
 * 
 * @param callback - 轮询回调函数
 * @param options - 配置选项
 * @returns 轮询管理方法
 * 
 * @example
 * ```typescript
 * const { isPolling, start, stop } = usePolling(
 *   async () => {
 *     const status = await fetchDeviceStatus();
 *     console.log(status);
 *   },
 *   { interval: 1000, immediate: true }
 * );
 * ```
 */
export function usePolling(
  callback: () => Promise<void> | void,
  options: UsePollingOptions
): UsePollingReturn {
  const {
    interval,
    immediate = false,
    pauseOnHidden = true,
  } = options

  const isPolling = ref(false)
  let timer: ReturnType<typeof setInterval> | null = null

  function start(): void {
    if (isPolling.value) return

    isPolling.value = true

    if (immediate) {
      callback()
    }

    timer = setInterval(() => {
      if (pauseOnHidden && document.hidden) {
        return
      }
      callback()
    }, interval)
  }

  function stop(): void {
    if (!isPolling.value) return

    isPolling.value = false

    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  function toggle(): void {
    if (isPolling.value) {
      stop()
    } else {
      start()
    }
  }

  onUnmounted(() => {
    stop()
  })

  return {
    isPolling,
    start,
    stop,
    toggle,
  }
}

export default usePolling
