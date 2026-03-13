<template>
  <div class="app">
    <router-view v-slot="{ Component }">
      <transition
        name="fade"
        mode="out-in"
      >
        <component :is="Component" />
      </transition>
    </router-view>
  </div>
</template>

<script setup>
/**
 * @file App.vue
 * @path src/
 * @description 自旋电子实验平台主应用组件，负责全局初始化、错误处理和WebSocket连接管理
 * @author Agent
 * @date 2024-03-07
 */

import { onMounted, onUnmounted, onErrorCaptured } from 'vue'
import { useLayoutStore } from '@/stores/layout'
import { useWebSocketIntegration } from '@/composables/useWebSocketIntegration'

// ==================== Store初始化 ====================

const layoutStore = useLayoutStore()

// ==================== WebSocket集成 ====================

/**
 * WebSocket配置
 * 实际使用时应该从环境变量或配置文件读取
 */
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'

/**
 * 初始化WebSocket连接
 */
const {
  wsConnected: _wsConnected,
  pushFrequency: _pushFrequency,
  dataLatency: _dataLatency,
  connect,
  disconnect,
  send: _send
} = useWebSocketIntegration({
  url: WS_URL
})

// ==================== 全局错误处理 ====================

onErrorCaptured((error, instance, info) => {
  console.error('[App] Global error captured:', error)
  console.error('[App] Error info:', info)
  
  // 添加警告到布局Store
  layoutStore.addWarning(`应用错误: ${error.message}`, 'error')
  
  // 阻止错误继续传播
  return false
})

// ==================== 生命周期 ====================

onMounted(() => {
  console.log('[App] Application mounted')
  
  // 初始化布局Store（加载本地存储的偏好）
  layoutStore.loadLayoutPreference()
  
  // 建立WebSocket连接
  connect()
})

onUnmounted(() => {
  console.log('[App] Application unmounted')
  
  // 断开WebSocket连接
  disconnect()
})
</script>

<style scoped>
.app {
  min-height: 100vh;
  background-color: var(--color-bg-secondary);
}

/* 页面切换动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.fade-enter-from {
  opacity: 0;
  transform: translateX(10px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}
</style>
