/**
 * @file main.js
 * @path src/
 * @description 应用入口文件，初始化Vue应用、Pinia状态管理、路由、懒加载指令和全局配置
 * @author Agent
 * @date 2024-03-08
 */

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

import App from './App.vue'
import router, { initRoutePreload } from './router'
import { useLayoutStore } from './stores/layout'
import { installLazyLoad } from './directives/lazyload'
import './styles/global.css'

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

// 安装懒加载指令
installLazyLoad(app, {
  rootMargin: '100px',
  threshold: 0.1,
  retryCount: 3
})

/**
 * 应用挂载后的初始化
 */
app.mount('#app')

/**
 * 初始化布局Store
 * 确保在应用挂载后初始化，避免SSR问题
 */
const layoutStore = useLayoutStore()

/**
 * 初始化路由预加载
 * 在应用空闲时预加载常用路由
 */
if (typeof window !== 'undefined') {
  // 使用requestIdleCallback在浏览器空闲时预加载
  if ('requestIdleCallback' in window) {
    window.requestIdleCallback(() => {
      initRoutePreload()
    }, { timeout: 5000 })
  } else {
    // 降级处理：延迟3秒后预加载
    setTimeout(() => {
      initRoutePreload()
    }, 3000)
  }
}

console.log('[Main] Application initialized successfully')
