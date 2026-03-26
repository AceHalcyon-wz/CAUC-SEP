/**
 * @file element-plus-import.ts
 * @path frontend/src/plugins/element-plus-import.ts
 * @description Element Plus按需引入配置，支持自动导入组件和样式
 * @author Agent
 * @date 2026-03-25
 * @dependencies element-plus, unplugin-vue-components, unplugin-auto-import
 */

import type { Plugin } from 'vue'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'

/**
 * Element Plus需要全局注册的组件
 * 这些组件通过编程式调用，无法自动导入
 */
const globalComponents = {
  ElMessage,
  ElMessageBox,
  ElNotification
}

/**
 * 安装Element Plus全局组件
 * 
 * @param app - Vue应用实例
 */
export function setupElementPlus(app: import('vue').App): void {
  // 注册全局组件
  Object.entries(globalComponents).forEach(([name, component]) => {
    app.config.globalProperties[`$${name}`] = component
  })

  // 配置全局默认值
  ElMessage.defaults = {
    duration: 3000,
    grouping: true,
    offset: 20
  }

  ElMessageBox.defaults = {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    closeOnClickModal: false,
    closeOnPressEscape: false
  }
}

/**
 * Element Plus插件
 */
export const ElementPlusPlugin: Plugin = {
  install(app) {
    setupElementPlus(app)
  }
}

export default ElementPlusPlugin
