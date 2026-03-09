/**
 * @file lazy.js
 * @path src/router/
 * @description 路由懒加载工具函数，支持预加载、加载状态管理和错误处理
 * @author Agent
 * @date 2024-03-08
 */

import { defineAsyncComponent, h } from 'vue'
import { ElLoading } from 'element-plus'

/**
 * 已加载的组件缓存
 * @type {Map<string, Component>}
 */
const componentCache = new Map()

/**
 * 正在加载的组件
 * @type {Map<string, Promise>}
 */
const loadingComponents = new Map()

/**
 * 预加载队列
 * @type {Array<{path: string, loader: Function}>}
 */
const preloadQueue = []

/**
 * 是否正在处理预加载队列
 */
let isProcessingPreload = false

/**
 * 创建带加载状态的异步组件
 *
 * @param {string} name - 组件名称（用于缓存和调试）
 * @param {Function} loader - 组件加载函数
 * @param {Object} options - 配置选项
 * @param {number} [options.delay=200] - 显示加载状态的延迟时间（毫秒）
 * @param {number} [options.timeout=30000] - 加载超时时间（毫秒）
 * @param {Component} [options.loadingComponent] - 自定义加载组件
 * @param {Component} [options.errorComponent] - 自定义错误组件
 * @param {Function} [options.onError] - 错误回调
 * @returns {Component} 异步组件
 */
export function createLazyComponent(name, loader, options = {}) {
  const {
    delay = 200,
    timeout = 30000,
    loadingComponent = null,
    errorComponent = null,
    onError = null
  } = options

  // 检查缓存
  if (componentCache.has(name)) {
    return componentCache.get(name)
  }

  // 创建异步组件
  const asyncComponent = defineAsyncComponent({
    loader: async () => {
      // 检查是否正在加载
      if (loadingComponents.has(name)) {
        return loadingComponents.get(name)
      }

      // 开始加载
      const loadPromise = loader()
      loadingComponents.set(name, loadPromise)

      try {
        const component = await loadPromise
        componentCache.set(name, component)
        loadingComponents.delete(name)
        return component
      } catch (error) {
        loadingComponents.delete(name)
        console.error(`[Router] Failed to load component "${name}":`, error)
        onError?.(error)
        throw error
      }
    },
    loadingComponent,
    errorComponent,
    delay,
    timeout
  })

  return asyncComponent
}

/**
 * 预加载路由组件
 *
 * @param {string} name - 组件名称
 * @param {Function} loader - 组件加载函数
 * @param {Object} options - 配置选项
 * @param {number} [options.priority=0] - 优先级（数值越大越优先）
 * @param {number} [options.delay=1000] - 延迟加载时间（毫秒）
 * @returns {Promise<void>}
 */
export function preloadRoute(name, loader, options = {}) {
  const {
    priority = 0,
    delay = 1000
  } = options

  // 如果已缓存，直接返回
  if (componentCache.has(name)) {
    return Promise.resolve()
  }

  // 添加到预加载队列
  preloadQueue.push({
    name,
    loader,
    priority,
    delay
  })

  // 按优先级排序
  preloadQueue.sort((a, b) => b.priority - a.priority)

  // 处理队列
  processPreloadQueue()
}

/**
 * 处理预加载队列
 */
async function processPreloadQueue() {
  if (isProcessingPreload || preloadQueue.length === 0) {
    return
  }

  isProcessingPreload = true

  while (preloadQueue.length > 0) {
    const item = preloadQueue.shift()

    // 延迟加载
    if (item.delay > 0) {
      await new Promise(resolve => setTimeout(resolve, item.delay))
    }

    // 检查是否已缓存
    if (componentCache.has(item.name)) {
      continue
    }

    // 加载组件
    try {
      const component = await item.loader()
      componentCache.set(item.name, component)
      console.log(`[Router] Preloaded component: ${item.name}`)
    } catch (error) {
      console.warn(`[Router] Failed to preload component "${item.name}":`, error)
    }
  }

  isProcessingPreload = false
}

/**
 * 批量预加载路由组件
 *
 * @param {Array<{name: string, loader: Function, options?: Object}>} routes - 路由配置数组
 */
export function preloadRoutes(routes) {
  routes.forEach(({ name, loader, options = {} }) => {
    preloadRoute(name, loader, options)
  })
}

/**
 * 清除组件缓存
 *
 * @param {string} [name] - 组件名称，不传则清除所有缓存
 */
export function clearComponentCache(name) {
  if (name) {
    componentCache.delete(name)
  } else {
    componentCache.clear()
  }
}

/**
 * 获取缓存状态
 *
 * @returns {Object} 缓存状态信息
 */
export function getCacheStatus() {
  return {
    cachedComponents: Array.from(componentCache.keys()),
    loadingComponents: Array.from(loadingComponents.keys()),
    preloadQueueLength: preloadQueue.length
  }
}

/**
 * 创建路由懒加载函数（带预加载支持）
 *
 * @param {Function} loader - 动态导入函数
 * @param {Object} options - 配置选项
 * @returns {Function} 路由组件加载函数
 */
export function lazyRoute(loader, options = {}) {
  const {
    preload = false,
    preloadDelay = 2000,
    ...lazyOptions
  } = options

  let component = null
  let loaderPromise = null

  const loadComponent = async () => {
    if (component) {
      return component
    }

    if (loaderPromise) {
      return loaderPromise
    }

    loaderPromise = loader().then(module => {
      component = module.default
      return component
    }).finally(() => {
      loaderPromise = null
    })

    return loaderPromise
  }

  // 创建懒加载组件
  const lazyComponent = createLazyComponent(
    loader.toString(),
    loadComponent,
    lazyOptions
  )

  // 如果需要预加载，延迟执行
  if (preload) {
    setTimeout(() => {
      loadComponent().catch(err => {
        console.warn('[Router] Preload failed:', err)
      })
    }, preloadDelay)
  }

  return lazyComponent
}

/**
 * 路由预加载策略
 */
export const PreloadStrategy = {
  /** 预加载所有路由 */
  ALL: 'all',
  /** 预加载相邻路由 */
  ADJACENT: 'adjacent',
  /** 预加载常用路由 */
  COMMON: 'common',
  /** 不预加载 */
  NONE: 'none'
}

/**
 * 根据策略预加载路由
 *
 * @param {string} strategy - 预加载策略
 * @param {Object} context - 上下文信息
 * @param {Array} context.routes - 路由配置
 * @param {string} context.currentPath - 当前路径
 */
export function preloadByStrategy(strategy, context = {}) {
  const { routes = [], currentPath = '' } = context

  switch (strategy) {
    case PreloadStrategy.ALL:
      // 预加载所有路由
      routes.forEach(route => {
        if (route.component) {
          preloadRoute(route.name || route.path, route.component, { delay: 500 })
        }
      })
      break

    case PreloadStrategy.ADJACENT:
      // 预加载相邻路由
      const currentIndex = routes.findIndex(r => r.path === currentPath)
      if (currentIndex > 0) {
        const prevRoute = routes[currentIndex - 1]
        if (prevRoute?.component) {
          preloadRoute(prevRoute.name || prevRoute.path, prevRoute.component, { priority: 1 })
        }
      }
      if (currentIndex < routes.length - 1) {
        const nextRoute = routes[currentIndex + 1]
        if (nextRoute?.component) {
          preloadRoute(nextRoute.name || nextRoute.path, nextRoute.component, { priority: 2 })
        }
      }
      break

    case PreloadStrategy.COMMON:
      // 预加载常用路由（根据业务需求配置）
      const commonRoutes = ['ExperimentMotor', 'DeviceStatus', 'AnalysisRealtime']
      routes.forEach(route => {
        if (commonRoutes.includes(route.name) && route.component) {
          preloadRoute(route.name, route.component, { priority: 3, delay: 1000 })
        }
      })
      break

    case PreloadStrategy.NONE:
    default:
      // 不预加载
      break
  }
}

export default {
  createLazyComponent,
  preloadRoute,
  preloadRoutes,
  clearComponentCache,
  getCacheStatus,
  lazyRoute,
  PreloadStrategy,
  preloadByStrategy
}
