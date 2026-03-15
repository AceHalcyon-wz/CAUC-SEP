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

    <GlobalLoading
      :show-progress="true"
      :show-message="true"
      spinner-type="circle"
    />
  </div>
</template>

<script setup>
/**
 * @file App.vue
 * @path src/
 * @description 自旋电子实验平台主应用组件
 * @author Agent
 * @date 2024-03-07
 * @version 3.5.1
 */

import { onMounted, onUnmounted } from 'vue'
import { useLayoutStore } from '@/stores/layout'
import { useDevicesStore } from '@/stores/devices'
import { GlobalLoading } from '@/components/common'
import { cancelPendingRequests, clearCache } from '@/utils/apiRequest'

const layoutStore = useLayoutStore()
const devicesStore = useDevicesStore()

onMounted(() => {
  console.log('[App] Application mounted')
  
  layoutStore.loadLayoutPreference()
  
  devicesStore.init()
  
  document.addEventListener('visibilitychange', handleVisibilityChange)
  
  window.addEventListener('beforeunload', handleBeforeUnload)
})

onUnmounted(() => {
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  window.removeEventListener('beforeunload', handleBeforeUnload)
  
  devicesStore.cleanup()
})

/**
 * 处理页面可见性变化
 * 当页面重新变为可见时，刷新设备状态
 */
function handleVisibilityChange() {
  if (document.visibilityState === 'visible') {
    console.log('[App] Page visible, refreshing device status')
    devicesStore.refreshAll()
  } else {
    console.log('[App] Page hidden')
  }
}

/**
 * 处理页面卸载前事件
 * 清理资源并取消待处理请求
 */
function handleBeforeUnload() {
  cancelPendingRequests()
  clearCache()
  devicesStore.cleanup()
}
</script>

<style scoped>
.app {
  min-height: 100vh;
  background-color: var(--color-bg-secondary);
}

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
