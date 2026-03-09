<template>
  <div 
    class="layout"
    :style="{ '--sidebar-width': `${currentSidebarWidth}px` }"
  >
    <!-- 左侧导航栏 -->
    <Sidebar />

    <!-- 顶部工具栏 -->
    <Topbar />

    <!-- 主内容区域 -->
    <main 
      class="layout__main"
      :style="{ 
        marginLeft: `${currentSidebarWidth}px`,
        paddingTop: '56px',
        paddingBottom: '40px'
      }"
    >
      <div class="layout__content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <keep-alive :include="cachedViews">
              <component :is="Component" />
            </keep-alive>
          </transition>
        </router-view>
      </div>
    </main>

    <!-- 底部状态栏 -->
    <StatusBar />

    <!-- 操作进度指示器 -->
    <OperationProgress />

    <!-- 操作反馈通知 -->
    <OperationFeedback />
  </div>
</template>

<script setup>
/**
 * @file Layout.vue
 * @path src/views/
 * @description 主布局容器组件，整合三栏式布局系统
 * @author Agent
 * @date 2024-03-07
 */

import { computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useLayoutStore } from '@/stores/layout'
import Sidebar from '@/components/layout/Sidebar.vue'
import Topbar from '@/components/layout/Topbar.vue'
import StatusBar from '@/components/layout/StatusBar.vue'
import OperationProgress from '@/components/OperationProgress.vue'
import OperationFeedback from '@/components/OperationFeedback.vue'

// ==================== 组合式函数 ====================

const route = useRoute()
const layoutStore = useLayoutStore()

// ==================== 响应式状态 ====================

/** 当前侧边栏宽度 */
const currentSidebarWidth = computed(() => layoutStore.currentSidebarWidth)

/** 缓存的视图组件 */
const cachedViews = computed(() => {
  // 可以根据需要配置需要缓存的页面
  return []
})

// ==================== 监听路由变化 ====================

watch(
  () => route.path,
  (newPath) => {
    // 根据路由路径更新激活状态
    layoutStore.setActiveByPath(newPath)
  },
  { immediate: true }
)

// ==================== 生命周期 ====================

onMounted(() => {
  // 初始化连接状态（模拟）
  setTimeout(() => {
    layoutStore.setConnectionStatus('connecting')
    setTimeout(() => {
      layoutStore.setConnectionStatus('connected')
      layoutStore.setOperationTip('系统已就绪，所有设备连接正常')
    }, 1500)
  }, 500)
})
</script>

<style scoped lang="scss">
.layout {
  min-height: 100vh;
  background-color: var(--color-bg-secondary);
  overflow: hidden;
}

// 主内容区域
.layout__main {
  min-height: 100vh;
  transition: margin-left var(--transition-slow);
  overflow: hidden;
}

.layout__content {
  padding: var(--spacing-6);
  min-height: calc(100vh - 56px - 40px);
  overflow-y: auto;
  overflow-x: hidden;
  
  &::-webkit-scrollbar {
    width: 8px;
  }
  
  &::-webkit-scrollbar-track {
    background: var(--color-bg-secondary);
  }
  
  &::-webkit-scrollbar-thumb {
    background: var(--color-neutral-300);
    border-radius: var(--radius-full);
    
    &:hover {
      background: var(--color-neutral-400);
    }
  }
}

// 页面切换动画
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
