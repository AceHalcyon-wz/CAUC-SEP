/**
 * @file usePushFrequency.js
 * @path src/composables/
 * @description 推送频率控制组合式函数，管理数据推送频率、模式切换、用户偏好设置
 * @author Agent
 * @date 2024-03-07
 * @dependencies vue
 */

import { ref, computed, watch, onUnmounted } from 'vue'

/**
 * 推送频率模式枚举
 */
export const PUSH_MODE = {
  LOW: 'low',         // 低频模式（2秒）
  NORMAL: 'normal',   // 正常模式（1秒）
  HIGH: 'high',       // 高频模式（0.5秒）
  REALTIME: 'realtime', // 实时模式（0.1秒）
  CUSTOM: 'custom'    // 自定义模式
}

/**
 * 预设频率配置（毫秒）
 */
export const FREQUENCY_PRESETS = {
  [PUSH_MODE.LOW]: 2000,
  [PUSH_MODE.NORMAL]: 1000,
  [PUSH_MODE.HIGH]: 500,
  [PUSH_MODE.REALTIME]: 100,
  [PUSH_MODE.CUSTOM]: 1000  // 默认自定义频率
}

/**
 * 频率范围限制
 */
export const FREQUENCY_LIMITS = {
  min: 50,    // 最小50ms（最高20Hz）
  max: 5000,  // 最大5000ms（最低0.2Hz）
  step: 50    // 步进值
}

/**
 * 本地存储键名
 */
const STORAGE_KEY = 'push-frequency-preference'

/**
 * 推送频率控制组合式函数
 * 
 * @param {Object} options - 配置选项
 * @param {string} [options.defaultMode='normal'] - 默认模式
 * @param {number} [options.defaultCustomFrequency=1000] - 默认自定义频率
 * @param {boolean} [options.persistPreference=true] - 是否持久化用户偏好
 * @returns {Object} 推送频率控制对象
 * 
 * @example
 * ```javascript
 * const frequency = usePushFrequency({
 *   defaultMode: 'normal',
 *   persistPreference: true
 * })
 * 
 * // 切换模式
 * frequency.setMode('high')
 * 
 * // 设置自定义频率
 * frequency.setCustomFrequency(800)
 * 
 * // 获取当前频率
 * console.log(frequency.currentFrequency.value) // 500
 * ```
 */
export function usePushFrequency(options = {}) {
  const {
    defaultMode = PUSH_MODE.NORMAL,
    defaultCustomFrequency = 1000,
    persistPreference = true
  } = options

  // ==================== 响应式状态 ====================

  /** 当前推送模式 */
  const currentMode = ref(defaultMode)

  /** 自定义频率值（毫秒） */
  const customFrequency = ref(defaultCustomFrequency)

  /** 频率变更回调列表 */
  const frequencyCallbacks = new Set()

  /** 频率变更定时器 */
  const frequencyTimer = null

  // ==================== 计算属性 ====================

  /**
   * 当前频率值（毫秒）
   */
  const currentFrequency = computed(() => {
    if (currentMode.value === PUSH_MODE.CUSTOM) {
      return Math.max(
        FREQUENCY_LIMITS.min,
        Math.min(FREQUENCY_LIMITS.max, customFrequency.value)
      )
    }
    return FREQUENCY_PRESETS[currentMode.value] || FREQUENCY_PRESETS[PUSH_MODE.NORMAL]
  })

  /**
   * 当前频率值（秒）
   */
  const currentFrequencySeconds = computed(() => {
    return currentFrequency.value / 1000
  })

  /**
   * 当前频率值（Hz）
   */
  const currentFrequencyHz = computed(() => {
    return 1000 / currentFrequency.value
  })

  /**
   * 频率模式描述
   */
  const modeDescription = computed(() => {
    const descriptions = {
      [PUSH_MODE.LOW]: '低频模式 - 适合稳定状态监控',
      [PUSH_MODE.NORMAL]: '正常模式 - 平衡性能与实时性',
      [PUSH_MODE.HIGH]: '高频模式 - 快速响应变化',
      [PUSH_MODE.REALTIME]: '实时模式 - 最高频率更新',
      [PUSH_MODE.CUSTOM]: `自定义模式 - ${currentFrequency.value}ms`
    }
    return descriptions[currentMode.value] || '未知模式'
  })

  /**
   * 频率滑块值（用于UI滑块）
   */
  const sliderValue = computed({
    get: () => customFrequency.value,
    set: (val) => {
      customFrequency.value = Math.round(val / FREQUENCY_LIMITS.step) * FREQUENCY_LIMITS.step
    }
  })

  /**
   * 频率滑块百分比
   */
  const sliderPercentage = computed(() => {
    const range = FREQUENCY_LIMITS.max - FREQUENCY_LIMITS.min
    return ((customFrequency.value - FREQUENCY_LIMITS.min) / range) * 100
  })

  /**
   * 是否为高频模式
   */
  const isHighFrequency = computed(() => {
    return currentFrequency.value <= 500
  })

  /**
   * 是否为低频模式
   */
  const isLowFrequency = computed(() => {
    return currentFrequency.value >= 2000
  })

  // ==================== 方法 ====================

  /**
   * 设置推送模式
   * 
   * @param {string} mode - 推送模式
   */
  function setMode(mode) {
    if (Object.values(PUSH_MODE).includes(mode)) {
      currentMode.value = mode
      notifyFrequencyChange()
      savePreference()
    }
  }

  /**
   * 设置自定义频率
   * 
   * @param {number} frequency - 频率值（毫秒）
   */
  function setCustomFrequency(frequency) {
    const clampedFrequency = Math.max(
      FREQUENCY_LIMITS.min,
      Math.min(FREQUENCY_LIMITS.max, frequency)
    )
    customFrequency.value = Math.round(clampedFrequency / FREQUENCY_LIMITS.step) * FREQUENCY_LIMITS.step
    
    if (currentMode.value !== PUSH_MODE.CUSTOM) {
      currentMode.value = PUSH_MODE.CUSTOM
    }
    
    notifyFrequencyChange()
    savePreference()
  }

  /**
   * 切换到下一个模式
   */
  function cycleMode() {
    const modes = [PUSH_MODE.LOW, PUSH_MODE.NORMAL, PUSH_MODE.HIGH, PUSH_MODE.REALTIME]
    const currentIndex = modes.indexOf(currentMode.value)
    const nextIndex = (currentIndex + 1) % modes.length
    setMode(modes[nextIndex])
  }

  /**
   * 注册频率变更回调
   * 
   * @param {Function} callback - 回调函数
   * @returns {Function} 取消注册函数
   */
  function onFrequencyChange(callback) {
    frequencyCallbacks.add(callback)
    return () => {
      frequencyCallbacks.delete(callback)
    }
  }

  /**
   * 通知频率变更
   * 
   * @internal 内部方法
   */
  function notifyFrequencyChange() {
    const info = {
      mode: currentMode.value,
      frequency: currentFrequency.value,
      frequencySeconds: currentFrequencySeconds.value,
      frequencyHz: currentFrequencyHz.value
    }
    
    frequencyCallbacks.forEach(callback => {
      try {
        callback(info)
      } catch (error) {
        console.error('[usePushFrequency] Callback error:', error)
      }
    })
  }

  /**
   * 保存用户偏好到本地存储
   * 
   * @internal 内部方法
   */
  function savePreference() {
    if (!persistPreference) return
    
    try {
      const preference = {
        mode: currentMode.value,
        customFrequency: customFrequency.value
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(preference))
    } catch (error) {
      console.warn('[usePushFrequency] Failed to save preference:', error)
    }
  }

  /**
   * 从本地存储加载用户偏好
   * 
   * @internal 内部方法
   */
  function loadPreference() {
    if (!persistPreference) return
    
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        const preference = JSON.parse(saved)
        if (preference.mode && Object.values(PUSH_MODE).includes(preference.mode)) {
          currentMode.value = preference.mode
        }
        if (typeof preference.customFrequency === 'number') {
          customFrequency.value = preference.customFrequency
        }
      }
    } catch (error) {
      console.warn('[usePushFrequency] Failed to load preference:', error)
    }
  }

  /**
   * 重置为默认设置
   */
  function reset() {
    currentMode.value = defaultMode
    customFrequency.value = defaultCustomFrequency
    notifyFrequencyChange()
    savePreference()
  }

  /**
   * 获取频率信息
   * 
   * @returns {Object} 频率信息对象
   */
  function getFrequencyInfo() {
    return {
      mode: currentMode.value,
      frequency: currentFrequency.value,
      frequencySeconds: currentFrequencySeconds.value,
      frequencyHz: currentFrequencyHz.value,
      modeDescription: modeDescription.value,
      isHighFrequency: isHighFrequency.value,
      isLowFrequency: isLowFrequency.value
    }
  }

  // ==================== 监听器 ====================

  // 监听模式变化
  watch(currentMode, () => {
    notifyFrequencyChange()
  })

  // ==================== 生命周期 ====================

  // 加载保存的偏好
  loadPreference()

  // 组件卸载时清理
  onUnmounted(() => {
    frequencyCallbacks.clear()
    if (frequencyTimer) {
      clearTimeout(frequencyTimer)
    }
  })

  // ==================== 返回值 ====================

  return {
    // 状态
    currentMode,
    customFrequency,
    
    // 计算属性
    currentFrequency,
    currentFrequencySeconds,
    currentFrequencyHz,
    modeDescription,
    sliderValue,
    sliderPercentage,
    isHighFrequency,
    isLowFrequency,
    
    // 方法
    setMode,
    setCustomFrequency,
    cycleMode,
    onFrequencyChange,
    reset,
    getFrequencyInfo
  }
}

/**
 * 创建全局推送频率管理器
 * 
 * @param {Object} options - 配置选项
 * @returns {Object} 全局推送频率管理器
 * 
 * @example
 * ```javascript
 * const globalFrequency = createGlobalFrequencyManager()
 * 
 * // 在组件中使用
 * const frequency = usePushFrequency()
 * frequency.setMode('high')
 * ```
 */
export function createGlobalFrequencyManager(options = {}) {
  const frequencyControl = usePushFrequency(options)
  
  /** 订阅者列表 */
  const subscribers = new Map()
  
  /** 推送定时器 */
  let pushTimer = null
  
  /** 是否正在推送 */
  let isPushing = false

  /**
   * 订阅推送
   * 
   * @param {string} id - 订阅者ID
   * @param {Function} callback - 推送回调
   * @returns {Function} 取消订阅函数
   */
  function subscribe(id, callback) {
    subscribers.set(id, callback)
    
    // 如果是第一个订阅者，启动推送
    if (subscribers.size === 1) {
      startPushing()
    }
    
    return () => {
      subscribers.delete(id)
      
      // 如果没有订阅者，停止推送
      if (subscribers.size === 0) {
        stopPushing()
      }
    }
  }

  /**
   * 启动推送
   * 
   * @internal 内部方法
   */
  function startPushing() {
    if (isPushing) return
    isPushing = true
    
    const push = () => {
      subscribers.forEach((callback, id) => {
        try {
          callback()
        } catch (error) {
          console.error(`[GlobalFrequency] Subscriber ${id} error:`, error)
        }
      })
      
      // 安排下一次推送
      pushTimer = setTimeout(push, frequencyControl.currentFrequency.value)
    }
    
    push()
  }

  /**
   * 停止推送
   * 
   * @internal 内部方法
   */
  function stopPushing() {
    isPushing = false
    if (pushTimer) {
      clearTimeout(pushTimer)
      pushTimer = null
    }
  }

  /**
   * 更新推送频率
   * 
   * @param {string} mode - 推送模式
   */
  function updatePushFrequency(mode) {
    frequencyControl.setMode(mode)
    
    // 如果正在推送，重启以应用新频率
    if (isPushing) {
      stopPushing()
      startPushing()
    }
  }

  // 监听频率变化
  frequencyControl.onFrequencyChange(() => {
    if (isPushing) {
      stopPushing()
      startPushing()
    }
  })

  return {
    // 继承频率控制
    ...frequencyControl,
    
    // 额外方法
    subscribe,
    updatePushFrequency,
    
    // 状态
    isPushing: () => isPushing,
    subscriberCount: () => subscribers.size
  }
}

/**
 * 频率调节滑块配置
 */
export const FREQUENCY_SLIDER_CONFIG = {
  min: FREQUENCY_LIMITS.min,
  max: FREQUENCY_LIMITS.max,
  step: FREQUENCY_LIMITS.step,
  marks: {
    [FREQUENCY_LIMITS.min]: '实时',
    [FREQUENCY_PRESETS[PUSH_MODE.HIGH]]: '高频',
    [FREQUENCY_PRESETS[PUSH_MODE.NORMAL]]: '正常',
    [FREQUENCY_PRESETS[PUSH_MODE.LOW]]: '低频',
    [FREQUENCY_LIMITS.max]: '省电'
  }
}
