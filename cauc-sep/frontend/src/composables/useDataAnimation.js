/**
 * @file useDataAnimation.js
 * @path src/composables/
 * @description 数据更新动画组合式函数，提供数据更新时的视觉反馈动画效果
 * @author Agent
 * @date 2024-03-07
 * @dependencies vue
 */

import { ref, computed, onUnmounted } from 'vue'

/**
 * 动画类型枚举
 */
export const ANIMATION_TYPE = {
  FLASH: 'flash',           // 闪烁
  HIGHLIGHT: 'highlight',   // 高亮
  PULSE: 'pulse',           // 脉冲
  BOUNCE: 'bounce',         // 弹跳
  FADE: 'fade',             // 淡入淡出
  SLIDE: 'slide'            // 滑动
}

/**
 * 动画强度枚举
 */
export const ANIMATION_INTENSITY = {
  SUBTLE: 'subtle',    // 微弱
  NORMAL: 'normal',    // 正常
  STRONG: 'strong'     // 强烈
}

/**
 * 默认动画配置
 */
const DEFAULT_CONFIG = {
  duration: 500,           // 动画持续时间（毫秒）
  type: ANIMATION_TYPE.FLASH,
  intensity: ANIMATION_INTENSITY.NORMAL,
  color: 'var(--color-accent-500)',  // 动画颜色
  autoReset: true,         // 动画结束后自动重置
  debounceTime: 100        // 防抖时间（毫秒）
}

/**
 * 数据更新动画组合式函数
 * 
 * @param {Object} options - 配置选项
 * @param {number} [options.duration=500] - 动画持续时间（毫秒）
 * @param {string} [options.type='flash'] - 动画类型
 * @param {string} [options.intensity='normal'] - 动画强度
 * @param {string} [options.color] - 动画颜色
 * @param {boolean} [options.autoReset=true] - 动画结束后自动重置
 * @param {number} [options.debounceTime=100] - 防抖时间
 * @returns {Object} 动画控制对象
 * 
 * @example
 * ```javascript
 * const animation = useDataAnimation({
 *   type: 'flash',
 *   intensity: 'normal'
 * })
 * 
 * // 触发动画
 * animation.trigger()
 * 
 * // 在模板中使用
 * <div :class="animation.animationClass.value">
 *   {{ data }}
 * </div>
 * ```
 */
export function useDataAnimation(options = {}) {
  const config = { ...DEFAULT_CONFIG, ...options }

  // ==================== 响应式状态 ====================

  /** 是否正在播放动画 */
  const isAnimating = ref(false)

  /** 当前动画类型 */
  const currentType = ref(config.type)

  /** 当前动画强度 */
  const currentIntensity = ref(config.intensity)

  /** 动画触发时间戳 */
  const animationTimestamp = ref(null)

  /** 动画定时器 */
  let animationTimer = null

  /** 防抖定时器 */
  let debounceTimer = null

  /** 上次触发时间 */
  let lastTriggerTime = 0

  // ==================== 计算属性 ====================

  /**
   * 动画CSS类名
   */
  const animationClass = computed(() => {
    if (!isAnimating.value) return ''
    
    const typeClass = `data-animation--${currentType.value}`
    const intensityClass = `data-animation--${currentIntensity.value}`
    
    return `data-animation ${typeClass} ${intensityClass}`
  })

  /**
   * 动画样式
   */
  const animationStyle = computed(() => {
    if (!isAnimating.value) return {}
    
    return {
      '--animation-duration': `${config.duration}ms`,
      '--animation-color': config.color
    }
  })

  /**
   * 动画是否激活
   */
  const isActive = computed(() => isAnimating.value)

  // ==================== 方法 ====================

  /**
   * 触发动画
   * 
   * @param {Object} [overrideOptions] - 可选的覆盖配置
   * @param {string} [overrideOptions.type] - 动画类型
   * @param {string} [overrideOptions.intensity] - 动画强度
   */
  function trigger(overrideOptions = {}) {
    const now = Date.now()
    
    // 防抖处理
    if (now - lastTriggerTime < config.debounceTime) {
      return
    }
    lastTriggerTime = now

    // 清除之前的动画
    clearAnimation()

    // 应用覆盖配置
    if (overrideOptions.type) {
      currentType.value = overrideOptions.type
    }
    if (overrideOptions.intensity) {
      currentIntensity.value = overrideOptions.intensity
    }

    // 启动动画
    isAnimating.value = true
    animationTimestamp.value = now

    // 设置动画结束定时器
    if (config.autoReset) {
      animationTimer = setTimeout(() => {
        reset()
      }, config.duration)
    }
  }

  /**
   * 重置动画状态
   */
  function reset() {
    clearAnimation()
    isAnimating.value = false
    animationTimestamp.value = null
    currentType.value = config.type
    currentIntensity.value = config.intensity
  }

  /**
   * 清除动画定时器
   * 
   * @internal 内部方法
   */
  function clearAnimation() {
    if (animationTimer) {
      clearTimeout(animationTimer)
      animationTimer = null
    }
    if (debounceTimer) {
      clearTimeout(debounceTimer)
      debounceTimer = null
    }
  }

  /**
   * 设置动画类型
   * 
   * @param {string} type - 动画类型
   */
  function setAnimationType(type) {
    if (Object.values(ANIMATION_TYPE).includes(type)) {
      currentType.value = type
    }
  }

  /**
   * 设置动画强度
   * 
   * @param {string} intensity - 动画强度
   */
  function setAnimationIntensity(intensity) {
    if (Object.values(ANIMATION_INTENSITY).includes(intensity)) {
      currentIntensity.value = intensity
    }
  }

  /**
   * 更新动画配置
   * 
   * @param {Object} newConfig - 新配置
   */
  function updateConfig(newConfig) {
    Object.assign(config, newConfig)
    if (newConfig.type) {
      currentType.value = newConfig.type
    }
    if (newConfig.intensity) {
      currentIntensity.value = newConfig.intensity
    }
  }

  // ==================== 生命周期 ====================

  onUnmounted(() => {
    clearAnimation()
  })

  // ==================== 返回值 ====================

  return {
    // 状态
    isAnimating,
    currentType,
    currentIntensity,
    animationTimestamp,
    
    // 计算属性
    animationClass,
    animationStyle,
    isActive,
    
    // 方法
    trigger,
    reset,
    setAnimationType,
    setAnimationIntensity,
    updateConfig
  }
}

/**
 * 创建多字段动画管理器
 * 
 * @param {Array<string>} fieldKeys - 字段键名数组
 * @param {Object} defaultConfig - 默认动画配置
 * @returns {Object} 多字段动画管理对象
 * 
 * @example
 * ```javascript
 * const animator = createFieldAnimator(['position', 'velocity', 'temperature'])
 * 
 * // 触发单个字段动画
 * animator.triggerField('position', { type: 'flash' })
 * 
 * // 批量触发动画
 * animator.triggerAll({ type: 'pulse' })
 * ```
 */
export function createFieldAnimator(fieldKeys, defaultConfig = {}) {
  const animations = {}
  const animatingFields = ref(new Set())

  // 为每个字段创建动画控制器
  fieldKeys.forEach(key => {
    animations[key] = useDataAnimation(defaultConfig)
  })

  /**
   * 触发指定字段的动画
   * 
   * @param {string} key - 字段键名
   * @param {Object} [options] - 动画选项
   */
  function triggerField(key, options = {}) {
    if (animations[key]) {
      animations[key].trigger(options)
      animatingFields.value.add(key)
      
      // 动画结束后移除
      setTimeout(() => {
        animatingFields.value.delete(key)
      }, defaultConfig.duration || 500)
    }
  }

  /**
   * 触发所有字段的动画
   * 
   * @param {Object} [options] - 动画选项
   */
  function triggerAll(options = {}) {
    fieldKeys.forEach(key => {
      triggerField(key, options)
    })
  }

  /**
   * 重置指定字段的动画
   * 
   * @param {string} key - 字段键名
   */
  function resetField(key) {
    if (animations[key]) {
      animations[key].reset()
      animatingFields.value.delete(key)
    }
  }

  /**
   * 重置所有字段的动画
   */
  function resetAll() {
    fieldKeys.forEach(key => {
      resetField(key)
    })
  }

  /**
   * 获取字段的动画类名
   * 
   * @param {string} key - 字段键名
   * @returns {string} 动画类名
   */
  function getFieldClass(key) {
    return animations[key]?.animationClass.value || ''
  }

  /**
   * 获取字段的动画样式
   * 
   * @param {string} key - 字段键名
   * @returns {Object} 动画样式对象
   */
  function getFieldStyle(key) {
    return animations[key]?.animationStyle.value || {}
  }

  /**
   * 字段是否正在动画
   * 
   * @param {string} key - 字段键名
   * @returns {boolean} 是否正在动画
   */
  function isFieldAnimating(key) {
    return animations[key]?.isAnimating.value || false
  }

  /**
   * 是否有任何字段正在动画
   */
  const hasAnyAnimation = computed(() => {
    return animatingFields.value.size > 0
  })

  return {
    // 状态
    animatingFields,
    hasAnyAnimation,
    
    // 方法
    triggerField,
    triggerAll,
    resetField,
    resetAll,
    getFieldClass,
    getFieldStyle,
    isFieldAnimating,
    
    // 单个动画控制器访问
    animations
  }
}

/**
 * 数据变化动画组合式函数
 * 根据数据变化方向自动选择动画效果
 * 
 * @param {Object} options - 配置选项
 * @returns {Object} 数据变化动画控制对象
 * 
 * @example
 * ```javascript
 * const changeAnimation = useDataChangeAnimation()
 * 
 * // 监听数据变化
 * watch(() => props.value, (newVal, oldVal) => {
 *   changeAnimation.handleValueChange(newVal, oldVal)
 * })
 * ```
 */
export function useDataChangeAnimation(options = {}) {
  const {
    increaseColor = 'var(--color-success)',
    decreaseColor = 'var(--color-error)',
    neutralColor = 'var(--color-accent-500)',
    threshold = 0.001  // 变化阈值
  } = options

  const animation = useDataAnimation(options)
  const changeDirection = ref('neutral')  // 'increase' | 'decrease' | 'neutral'
  const previousValue = ref(null)

  /**
   * 处理值变化
   * 
   * @param {number} newValue - 新值
   * @param {number} oldValue - 旧值
   */
  function handleValueChange(newValue, oldValue) {
    // 保存旧值
    previousValue.value = oldValue

    // 计算变化方向
    const diff = newValue - oldValue
    
    if (Math.abs(diff) < threshold) {
      changeDirection.value = 'neutral'
      return
    }

    // 设置变化方向和颜色
    if (diff > 0) {
      changeDirection.value = 'increase'
      animation.updateConfig({ color: increaseColor })
    } else {
      changeDirection.value = 'decrease'
      animation.updateConfig({ color: decreaseColor })
    }

    // 触发动画
    animation.trigger()
  }

  /**
   * 获取变化指示器类名
   */
  const changeIndicatorClass = computed(() => {
    return `data-change--${changeDirection.value}`
  })

  /**
   * 获取变化指示器颜色
   */
  const changeIndicatorColor = computed(() => {
    switch (changeDirection.value) {
      case 'increase':
        return increaseColor
      case 'decrease':
        return decreaseColor
      default:
        return neutralColor
    }
  })

  return {
    // 继承基础动画
    ...animation,
    
    // 额外状态
    changeDirection,
    previousValue,
    changeIndicatorClass,
    changeIndicatorColor,
    
    // 额外方法
    handleValueChange
  }
}
