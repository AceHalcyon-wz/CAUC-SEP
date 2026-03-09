/**
 * @file lazyload.js
 * @path src/directives/
 * @description 图片和组件懒加载指令，支持IntersectionObserver API和占位符
 * @author Agent
 * @date 2024-03-08
 */

import { createApp, h, defineComponent, ref, onMounted, onUnmounted } from 'vue'

/**
 * IntersectionObserver实例（全局共享）
 */
let observer = null

/**
 * 观察队列
 */
const observerQueue = new Map()

/**
 * 默认配置
 */
const defaultConfig = {
  /** 根元素（用于计算可见性） */
  root: null,
  /** 根元素边距 */
  rootMargin: '50px',
  /** 可见比例阈值 */
  threshold: 0.1,
  /** 是否立即加载（禁用懒加载） */
  immediate: false,
  /** 占位符背景色 */
  placeholderBg: 'var(--color-bg-secondary)',
  /** 加载失败占位符 */
  errorPlaceholder: null,
  /** 重试次数 */
  retryCount: 3,
  /** 重试延迟（毫秒） */
  retryDelay: 1000
}

/**
 * 初始化IntersectionObserver
 *
 * @param {Object} config - 配置选项
 */
function initObserver(config) {
  if (observer) return

  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        const { target, isIntersecting } = entry
        
        if (isIntersecting) {
          const callback = observerQueue.get(target)
          if (callback) {
            callback()
            observerQueue.delete(target)
            observer.unobserve(target)
          }
        }
      })
    },
    {
      root: config.root,
      rootMargin: config.rootMargin,
      threshold: config.threshold
    }
  )
}

/**
 * 添加到观察队列
 *
 * @param {HTMLElement} el - DOM元素
 * @param {Function} callback - 进入可见区域时的回调
 */
function addToObserver(el, callback) {
  if (!observer) {
    initObserver(defaultConfig)
  }

  observerQueue.set(el, callback)
  observer.observe(el)
}

/**
 * 从观察队列移除
 *
 * @param {HTMLElement} el - DOM元素
 */
function removeFromObserver(el) {
  if (observer && observerQueue.has(el)) {
    observerQueue.delete(el)
    observer.unobserve(el)
  }
}

/**
 * 图片懒加载指令
 *
 * @description 支持图片懒加载、加载状态、错误处理和重试机制
 *
 * @example
 * ```vue
 * <template>
 *   <!-- 基础用法 -->
 *   <img v-lazy="imageUrl" />
 *
 *   <!-- 带占位符 -->
 *   <img v-lazy="{ src: imageUrl, placeholder: 'placeholder.jpg' }" />
 *
 *   <!-- 自定义配置 -->
 *   <img v-lazy="{
 *     src: imageUrl,
 *     placeholder: 'placeholder.jpg',
 *     error: 'error.jpg',
 *     retryCount: 3
 *   }" />
 * </template>
 * ```
 */
export const lazyDirective = {
  /**
   * 指令挂载
   */
  mounted(el, binding) {
    const config = parseBinding(binding)
    
    // 如果立即加载，直接设置src
    if (config.immediate) {
      loadImage(el, config)
      return
    }

    // 设置占位符
    if (config.placeholder) {
      el.src = config.placeholder
    } else {
      // 设置默认占位符样式
      el.style.backgroundColor = config.placeholderBg
      el.dataset.loaded = 'false'
    }

    // 添加到观察队列
    addToObserver(el, () => {
      loadImage(el, config)
    })
  },

  /**
   * 指令更新
   */
  updated(el, binding) {
    const config = parseBinding(binding)
    
    // 如果src变化，重新加载
    if (el.dataset.src !== config.src) {
      el.dataset.src = config.src
      
      if (config.immediate) {
        loadImage(el, config)
      } else {
        // 重置状态
        el.dataset.loaded = 'false'
        if (config.placeholder) {
          el.src = config.placeholder
        }
        
        // 重新添加到观察队列
        removeFromObserver(el)
        addToObserver(el, () => {
          loadImage(el, config)
        })
      }
    }
  },

  /**
   * 指令卸载
   */
  unmounted(el) {
    removeFromObserver(el)
  }
}

/**
 * 解析指令绑定值
 *
 * @param {Object} binding - Vue指令绑定对象
 * @returns {Object} 配置对象
 */
function parseBinding(binding) {
  const value = binding.value
  
  if (typeof value === 'string') {
    return {
      ...defaultConfig,
      src: value
    }
  }
  
  return {
    ...defaultConfig,
    ...value
  }
}

/**
 * 加载图片
 *
 * @param {HTMLImageElement} el - 图片元素
 * @param {Object} config - 配置对象
 * @param {number} [attempt=1] - 当前尝试次数
 */
function loadImage(el, config, attempt = 1) {
  const img = new Image()
  
  img.onload = () => {
    el.src = config.src
    el.dataset.loaded = 'true'
    el.style.backgroundColor = ''
    el.classList.remove('lazy-loading', 'lazy-error')
    el.classList.add('lazy-loaded')
    
    // 触发自定义事件
    el.dispatchEvent(new CustomEvent('lazy-loaded', {
      detail: { src: config.src }
    }))
  }
  
  img.onerror = () => {
    // 重试逻辑
    if (attempt < config.retryCount) {
      console.log(`[LazyLoad] Retry loading image (${attempt}/${config.retryCount}): ${config.src}`)
      setTimeout(() => {
        loadImage(el, config, attempt + 1)
      }, config.retryDelay)
      return
    }
    
    // 加载失败
    console.error(`[LazyLoad] Failed to load image: ${config.src}`)
    el.dataset.loaded = 'error'
    el.classList.remove('lazy-loading', 'lazy-loaded')
    el.classList.add('lazy-error')
    
    // 设置错误占位符
    if (config.error) {
      el.src = config.error
    } else if (config.errorPlaceholder) {
      el.src = config.errorPlaceholder
    }
    
    // 触发自定义事件
    el.dispatchEvent(new CustomEvent('lazy-error', {
      detail: { src: config.src, attempt }
    }))
  }
  
  // 添加加载中状态
  el.classList.remove('lazy-loaded', 'lazy-error')
  el.classList.add('lazy-loading')
  
  // 开始加载
  img.src = config.src
  el.dataset.src = config.src
}

/**
 * 组件懒加载指令
 *
 * @description 支持组件懒加载，当组件进入可见区域时才渲染
 *
 * @example
 * ```vue
 * <template>
 *   <!-- 基础用法 -->
 *   <div v-lazy-component>
 *     <HeavyComponent />
 *   </div>
 *
 *   <!-- 带最小高度 -->
 *   <div v-lazy-component="{ minHeight: 200 }">
 *     <HeavyComponent />
 *   </div>
 *
 *   <!-- 带占位符 -->
 *   <div v-lazy-component="{ placeholder: 'Loading...' }">
 *     <HeavyComponent />
 *   </div>
 * </template>
 * ```
 */
export const lazyComponentDirective = {
  /**
   * 指令挂载
   */
  mounted(el, binding) {
    const config = {
      ...defaultConfig,
      ...binding.value
    }

    // 如果立即加载，直接显示
    if (config.immediate) {
      el.dataset.loaded = 'true'
      return
    }

    // 设置最小高度
    if (config.minHeight) {
      el.style.minHeight = `${config.minHeight}px`
    }

    // 设置占位符
    if (config.placeholder) {
      el.innerHTML = config.placeholder
    }

    // 标记为未加载
    el.dataset.loaded = 'false'
    el.classList.add('lazy-component')

    // 添加到观察队列
    addToObserver(el, () => {
      el.dataset.loaded = 'true'
      el.classList.remove('lazy-component')
      el.classList.add('lazy-component-loaded')
      
      // 触发自定义事件
      el.dispatchEvent(new CustomEvent('lazy-component-loaded'))
    })
  },

  /**
   * 指令卸载
   */
  unmounted(el) {
    removeFromObserver(el)
  }
}

/**
 * 背景图片懒加载指令
 *
 * @description 支持背景图片懒加载
 *
 * @example
 * ```vue
 * <template>
 *   <div v-lazy-bg="backgroundImageUrl"></div>
 *   <div v-lazy-bg="{ src: imageUrl, placeholder: 'placeholder.jpg' }"></div>
 * </template>
 * ```
 */
export const lazyBgDirective = {
  /**
   * 指令挂载
   */
  mounted(el, binding) {
    const config = parseBinding(binding)
    
    if (config.immediate) {
      loadBackgroundImage(el, config)
      return
    }

    // 设置占位符
    if (config.placeholder) {
      el.style.backgroundImage = `url(${config.placeholder})`
    } else {
      el.style.backgroundColor = config.placeholderBg
    }

    el.dataset.loaded = 'false'

    // 添加到观察队列
    addToObserver(el, () => {
      loadBackgroundImage(el, config)
    })
  },

  /**
   * 指令更新
   */
  updated(el, binding) {
    const config = parseBinding(binding)
    
    if (el.dataset.src !== config.src) {
      el.dataset.src = config.src
      
      if (config.immediate) {
        loadBackgroundImage(el, config)
      } else {
        removeFromObserver(el)
        addToObserver(el, () => {
          loadBackgroundImage(el, config)
        })
      }
    }
  },

  /**
   * 指令卸载
   */
  unmounted(el) {
    removeFromObserver(el)
  }
}

/**
 * 加载背景图片
 *
 * @param {HTMLElement} el - DOM元素
 * @param {Object} config - 配置对象
 */
function loadBackgroundImage(el, config) {
  const img = new Image()
  
  img.onload = () => {
    el.style.backgroundImage = `url(${config.src})`
    el.style.backgroundColor = ''
    el.dataset.loaded = 'true'
    el.classList.add('lazy-bg-loaded')
    
    el.dispatchEvent(new CustomEvent('lazy-bg-loaded', {
      detail: { src: config.src }
    }))
  }
  
  img.onerror = () => {
    console.error(`[LazyLoad] Failed to load background image: ${config.src}`)
    el.dataset.loaded = 'error'
    el.classList.add('lazy-bg-error')
    
    if (config.error) {
      el.style.backgroundImage = `url(${config.error})`
    }
    
    el.dispatchEvent(new CustomEvent('lazy-bg-error', {
      detail: { src: config.src }
    }))
  }
  
  img.src = config.src
  el.dataset.src = config.src
}

/**
 * 安装懒加载指令
 *
 * @param {Object} app - Vue应用实例
 * @param {Object} options - 配置选项
 */
export function installLazyLoad(app, options = {}) {
  // 合并配置
  Object.assign(defaultConfig, options)
  
  // 初始化Observer
  initObserver(defaultConfig)
  
  // 注册指令
  app.directive('lazy', lazyDirective)
  app.directive('lazy-component', lazyComponentDirective)
  app.directive('lazy-bg', lazyBgDirective)
  
  console.log('[LazyLoad] Directives installed')
}

/**
 * 懒加载组件包装器
 *
 * @description 用于包装需要懒加载的组件
 *
 * @param {Object} component - 组件定义
 * @param {Object} options - 配置选项
 * @returns {Object} 懒加载组件
 *
 * @example
 * ```javascript
 * const LazyHeavyComponent = createLazyComponent(
 *   () => import('./HeavyComponent.vue'),
 *   { minHeight: 200 }
 * )
 * ```
 */
export function createLazyComponent(component, options = {}) {
  return defineComponent({
    name: 'LazyComponentWrapper',
    props: {
      /** 是否立即加载 */
      immediate: {
        type: Boolean,
        default: false
      },
      /** 最小高度 */
      minHeight: {
        type: Number,
        default: options.minHeight || 100
      },
      /** 占位符内容 */
      placeholder: {
        type: String,
        default: options.placeholder || ''
      }
    },
    setup(props, { slots }) {
      const isLoaded = ref(false)
      const isError = ref(false)
      const containerRef = ref(null)
      let observerInstance = null

      const loadComponent = async () => {
        try {
          if (typeof component === 'function') {
            await component()
          }
          isLoaded.value = true
        } catch (error) {
          console.error('[LazyComponent] Failed to load component:', error)
          isError.value = true
        }
      }

      onMounted(() => {
        if (props.immediate) {
          loadComponent()
          return
        }

        observerInstance = new IntersectionObserver(
          (entries) => {
            entries.forEach(entry => {
              if (entry.isIntersecting) {
                loadComponent()
                observerInstance.disconnect()
              }
            })
          },
          {
            rootMargin: defaultConfig.rootMargin,
            threshold: defaultConfig.threshold
          }
        )

        if (containerRef.value) {
          observerInstance.observe(containerRef.value)
        }
      })

      onUnmounted(() => {
        if (observerInstance) {
          observerInstance.disconnect()
        }
      })

      return () => {
        if (isLoaded.value) {
          return h('div', { class: 'lazy-component-loaded' }, slots.default?.())
        }

        if (isError.value) {
          return h('div', { class: 'lazy-component-error' }, [
            slots.error?.() || h('div', '加载失败')
          ])
        }

        return h('div', {
          ref: containerRef,
          class: 'lazy-component-loading',
          style: { minHeight: `${props.minHeight}px` }
        }, [
          slots.placeholder?.() || props.placeholder
        ])
      }
    }
  })
}

/**
 * 清理Observer
 */
export function cleanupLazyLoad() {
  if (observer) {
    observer.disconnect()
    observer = null
  }
  observerQueue.clear()
}

// 默认导出
export default {
  install: installLazyLoad,
  lazyDirective,
  lazyComponentDirective,
  lazyBgDirective,
  createLazyComponent,
  cleanupLazyLoad
}
