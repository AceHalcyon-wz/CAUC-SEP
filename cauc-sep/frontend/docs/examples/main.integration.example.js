/**
 * @file main.integration.example.js
 * @path src/
 * @description 错误处理系统集成示例 - 展示如何在main.js中初始化和使用错误处理系统
 * @author Agent
 * @date 2024-03-07
 *
 * 使用说明：
 * 1. 将此文件中的代码复制到 main.js 中
 * 2. 根据项目需求调整配置选项
 * 3. 在需要错误处理的组件中使用 useErrorHandler 或全局错误处理器
 */

// ==================== 在 main.js 中添加以下导入 ====================
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

import App from './App.vue'
import router from './router'
import { useLayoutStore } from './stores/layout'
import './styles/global.css'

// ==================== 新增：导入错误处理系统 ====================
import {
  initializeErrorHandler,
  vueErrorHandler
} from './utils/errorHandlerIntegration'

/**
 * 创建Vue应用实例
 */
const app = createApp(App)

/**
 * 创建Pinia实例
 */
const pinia = createPinia()

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 安装插件
app.use(pinia)
app.use(router)
app.use(ElementPlus, { locale: zhCn })

// ==================== 新增：初始化全局错误处理器 ====================
/**
 * 初始化错误处理系统
 *
 * 配置选项：
 * - enableHistory: 启用错误历史记录（默认true）
 * - enableAutoReport: 启用自动错误上报（默认false）
 * - onReport: 错误上报回调函数
 * - onError: 错误处理回调函数
 */
const errorHandler = initializeErrorHandler({
  // 启用错误历史记录
  enableHistory: true,

  // 是否自动上报错误到服务器
  enableAutoReport: false,

  /**
   * 错误上报回调
   * 当发生错误时，可以自动将错误报告发送到服务器
   *
   * @param {Object} report - 错误报告对象
   */
  onReport: async (report) => {
    try {
      // 示例：发送错误报告到服务器
      // await fetch('/api/errors/report', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(report)
      // })
      console.log('[ErrorHandler] 错误报告:', report)
    } catch (error) {
      console.error('[ErrorHandler] 上报失败:', error)
    }
  },

  /**
   * 错误处理回调
   * 可以在这里添加自定义错误处理逻辑
   *
   * @param {Object} errorInfo - 错误信息对象
   */
  onError: (errorInfo) => {
    // 示例：在开发环境打印详细错误信息
    if (import.meta.env.DEV) {
      console.group('🚨 错误详情')
      console.log('错误ID:', errorInfo.id)
      console.log('错误类型:', errorInfo.type)
      console.log('错误消息:', errorInfo.message)
      console.log('解决方案:', errorInfo.solution?.title)
      console.groupEnd()
    }

    // 示例：根据错误类型执行特定操作
    if (errorInfo.type === 'permission') {
      // 权限错误，跳转到登录页
      // router.push('/login')
    }
  }
})

// ==================== 新增：设置Vue错误处理器 ====================
/**
 * Vue应用错误处理器
 * 捕获组件渲染和生命周期钩子中的错误
 */
app.config.errorHandler = vueErrorHandler

/**
 * Vue应用警告处理器（仅开发环境）
 */
if (import.meta.env.DEV) {
  app.config.warnHandler = (msg, instance, trace) => {
    console.warn('[Vue警告]', msg)
    console.warn('组件:', instance?.$options?.name || 'Unknown')
    console.warn('追踪:', trace)
  }
}

/**
 * 应用挂载后的初始化
 */
app.mount('#app')

/**
 * 初始化布局Store
 * 确保在应用挂载后初始化，避免SSR问题
 */
const layoutStore = useLayoutStore()

// ==================== 新增：将错误处理器挂载到全局 ====================
/**
 * 将错误处理器挂载到全局，方便在控制台调试
 * 仅在开发环境启用
 */
if (import.meta.env.DEV) {
  window.__ERROR_HANDLER__ = errorHandler
  console.log('[Main] 错误处理系统已初始化')
  console.log('[Main] 可通过 window.__ERROR_HANDLER__ 访问错误处理器')
}

console.log('[Main] Application initialized successfully')

// ==================== 在组件中使用错误处理器的示例 ====================
/**
 * 示例1：在组件中使用 useErrorHandler
 *
 * ```vue
 * <script setup>
 * import { useErrorHandler } from '@/composables/useErrorHandler'
 * import ErrorDisplay from '@/components/ErrorDisplay.vue'
 *
 * const {
 *   currentError,
 *   errorVisible,
 *   handleError,
 *   clearError,
 *   copyErrorInfo
 * } = useErrorHandler()
 *
 * async function fetchData() {
 *   try {
 *     const response = await fetch('/api/data')
 *     return await response.json()
 *   } catch (error) {
 *     handleError(error, {
 *       component: 'MyComponent',
 *       action: 'fetchData',
 *       userMessage: '数据加载失败'
 *     })
 *   }
 * }
 * </script>
 *
 * <template>
 *   <ErrorDisplay
 *     v-model="errorVisible"
 *     :error-info="currentError"
 *     @copy="handleCopy"
 *   />
 * </template>
 * ```
 */

/**
 * 示例2：使用全局错误处理器
 *
 * ```javascript
 * import { getGlobalErrorHandler } from '@/utils/errorHandlerIntegration'
 *
 * const errorHandler = getGlobalErrorHandler()
 *
 * // 处理错误
 * errorHandler.handleError(error, {
 *   component: 'MyComponent',
 *   action: 'someAction'
 * })
 *
 * // 访问错误历史
 * console.log(errorHandler.errorHistory.value)
 *
 * // 复制错误信息
 * await errorHandler.copyErrorInfo('detail')
 * ```
 */

/**
 * 示例3：使用专用错误处理器
 *
 * ```javascript
 * import {
 *   handleApiError,
 *   handleDeviceError,
 *   handleWebSocketError
 * } from '@/utils/errorHandlerIntegration'
 *
 * // API错误
 * try {
 *   await api.getData()
 * } catch (error) {
 *   handleApiError(error, { url: '/api/data', method: 'GET' })
 * }
 *
 * // 设备错误
 * try {
 *   await device.connect()
 * } catch (error) {
 *   handleDeviceError(error, { name: 'Motor', port: 'COM3' })
 * }
 *
 * // WebSocket错误
 * ws.onerror = (error) => {
 *   handleWebSocketError(error, { url: wsUrl })
 * }
 * ```
 */

/**
 * 示例4：在Store中使用错误处理器
 *
 * ```javascript
 * import { defineStore } from 'pinia'
 * import { handleDeviceError } from '@/utils/errorHandlerIntegration'
 *
 * export const useMotorStore = defineStore('motor', {
 *   actions: {
 *     async connectMotor(config) {
 *       try {
 *         const response = await fetch('/api/motor/connect', {
 *           method: 'POST',
 *           body: JSON.stringify(config)
 *         })
 *         return await response.json()
 *       } catch (error) {
 *         handleDeviceError(error, {
 *           name: 'Motor',
 *           port: config.port,
 *           action: 'connect'
 *         })
 *         throw error
 *       }
 *     }
 *   }
 * })
 * ```
 */

/**
 * 示例5：在API请求工具中使用错误处理器
 *
 * ```javascript
 * // src/utils/apiRequest.js
 * import { handleApiError } from './errorHandlerIntegration'
 *
 * export async function apiRequest(url, options = {}) {
 *   try {
 *     const response = await fetch(url, {
 *       headers: { 'Content-Type': 'application/json' },
 *       ...options
 *     })
 *
 *     if (!response.ok) {
 *       throw new Error(`HTTP ${response.status}: ${response.statusText}`)
 *     }
 *
 *     return await response.json()
 *   } catch (error) {
 *     handleApiError(error, { url, method: options.method || 'GET' })
 *     throw error
 *   }
 * }
 * ```
 */
