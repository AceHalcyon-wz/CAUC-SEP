/**
 * @file Layout.vue
 * @path src/views/
 * @description 主布局组件 - 包含侧边栏和主内容区（优化版）
 * @author Agent
 * @date 2024-03-15
 * @version 3.5.1
 */

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, defineAsyncComponent } from 'vue';
import { useRoute } from 'vue-router';
import { wsClient } from '../api/websocket';
import { useDevicesStore } from '../stores/devices';

// 异步加载布局组件，减少初始加载时间
const Sidebar = defineAsyncComponent(() => import('../components/layout/Sidebar.vue'));
const Topbar = defineAsyncComponent(() => import('../components/layout/Topbar.vue'));

const route = useRoute();
const devicesStore = useDevicesStore();

const sidebarCollapsed = ref(false);
const isMobile = ref(false);
const mobileMenuOpen = ref(false);
const connectionStatus = ref('connecting');
const isPageLoading = ref(false);

/**
 * 当前页面标题
 */
const pageTitle = computed(() => route.meta?.title || 'CAUC-SEP');

/**
 * 切换侧边栏折叠状态
 */
const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value;
  // 保存用户偏好到localStorage
  localStorage.setItem('sidebar_collapsed', sidebarCollapsed.value);
};

/**
 * 切换移动端菜单
 */
const toggleMobileMenu = () => {
  mobileMenuOpen.value = !mobileMenuOpen.value;
};

/**
 * 检查是否为移动设备
 */
const checkMobile = () => {
  const wasMobile = isMobile.value;
  isMobile.value = window.innerWidth < 768;
  
  if (!isMobile.value) {
    mobileMenuOpen.value = false;
  }
  
  // 如果从桌面切换到移动端，自动折叠侧边栏
  if (!wasMobile && isMobile.value) {
    sidebarCollapsed.value = false;
  }
};

/**
 * 处理WebSocket连接状态变化
 */
const handleConnectionChange = (status) => {
  connectionStatus.value = status;
};

/**
 * 从localStorage恢复侧边栏状态
 */
const restoreSidebarState = () => {
  const saved = localStorage.getItem('sidebar_collapsed');
  if (saved !== null) {
    sidebarCollapsed.value = saved === 'true';
  }
};

// 监听路由变化，移动端自动关闭菜单，显示加载状态
watch(() => route.path, () => {
  if (isMobile.value) {
    mobileMenuOpen.value = false;
  }
  // 显示页面加载指示器
  isPageLoading.value = true;
  // 使用requestAnimationFrame确保在下一帧隐藏加载指示器
  requestAnimationFrame(() => {
    setTimeout(() => {
      isPageLoading.value = false;
    }, 50);
  });
});

// 生命周期钩子
onMounted(() => {
  checkMobile();
  restoreSidebarState();
  window.addEventListener('resize', checkMobile);

  // 初始化WebSocket连接
  wsClient.connect().catch(() => {
    connectionStatus.value = 'disconnected';
  });

  // 监听连接状态
  wsClient.on('connected', () => handleConnectionChange('connected'));
  wsClient.on('disconnected', () => handleConnectionChange('disconnected'));
  wsClient.on('reconnecting', () => handleConnectionChange('reconnecting'));

  // 初始化设备Store
  devicesStore.init();
});

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile);
  wsClient.disconnect();
  devicesStore.cleanup();
});
</script>

<template>
  <div class="layout">
    <!-- 移动端遮罩 -->
    <transition name="fade">
      <div
        v-if="mobileMenuOpen"
        class="layout__overlay"
        @click="mobileMenuOpen = false"
      />
    </transition>

    <!-- 侧边栏 -->
    <Sidebar
      :collapsed="sidebarCollapsed"
      :mobile-open="mobileMenuOpen"
      @update:mobile-open="mobileMenuOpen = $event"
      @toggle="toggleSidebar"
    />

    <!-- 主内容区 -->
    <div
      class="layout__main"
      :class="{
        'layout__main--collapsed': sidebarCollapsed && !isMobile,
        'layout__main--mobile-open': mobileMenuOpen
      }"
    >
      <!-- 顶部栏 -->
      <Topbar
        :title="pageTitle"
        :sidebar-collapsed="sidebarCollapsed"
        :connection-status="connectionStatus"
        @toggle-sidebar="toggleSidebar"
        @toggle-mobile-menu="toggleMobileMenu"
      />

      <!-- 页面内容 -->
      <main class="layout__content">
        <!-- 页面加载指示器 -->
        <div
          v-if="isPageLoading"
          class="page-loading"
        >
          <a-spin
            size="large"
            tip="加载中..."
          />
        </div>
        
        <router-view v-slot="{ Component }">
          <transition
            name="page"
            mode="out-in"
          >
            <keep-alive :include="['DeviceStatus', 'MotorControl', 'RealtimeAnalysis']">
              <component :is="Component" />
            </keep-alive>
          </transition>
        </router-view>
      </main>

      <!-- 页脚 -->
      <footer class="layout__footer">
        <div class="layout__footer-content">
          <div class="footer__left">
            <span class="layout__footer-text">
              CAUC-SEP 科学实验平台
            </span>
            <span class="version-tag">v3.5.1</span>
          </div>
          <div class="footer__right">
            <span class="layout__footer-text">
              中国民航大学 理学院 材料物理
            </span>
          </div>
        </div>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  min-height: 100vh;
  background: var(--color-bg-secondary);
}

.layout__overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.6);
  z-index: var(--z-index-modal-backdrop);
  backdrop-filter: blur(4px);
}

.layout__main {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-left: 260px;
  transition: margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  min-height: 100vh;
  background: var(--color-bg-secondary);
}

.layout__main--collapsed {
  margin-left: 80px;
}

.layout__content {
  flex: 1;
  padding: var(--spacing-6);
  overflow-x: hidden;
  min-height: calc(100vh - 64px - 56px);
  position: relative;
}

.page-loading {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.8);
  z-index: 100;
  backdrop-filter: blur(2px);
}

.layout__footer {
  padding: var(--spacing-4) var(--spacing-6);
  background: var(--color-bg-primary);
  border-top: 1px solid var(--color-border-primary);
}

.layout__footer-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: var(--content-max-width);
  margin: 0 auto;
}

.footer__left,
.footer__right {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.layout__footer-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.version-tag {
  font-size: var(--font-size-xs);
  padding: 2px 8px;
  background: var(--color-primary-50);
  color: var(--color-primary-600);
  border-radius: var(--radius-sm);
  font-weight: var(--font-weight-medium);
}

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 页面切换动画 - 优化为更快的过渡 */
.page-enter-active,
.page-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateX(10px);
}

.page-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .layout__main {
    margin-left: 0;
  }

  .layout__main--collapsed {
    margin-left: 0;
  }

  .layout__content {
    padding: var(--spacing-4);
  }

  .layout__footer-content {
    flex-direction: column;
    gap: var(--spacing-2);
    text-align: center;
  }

  .footer__left,
  .footer__right {
    flex-direction: column;
    gap: var(--spacing-1);
  }
}

@media (max-width: 480px) {
  .layout__content {
    padding: var(--spacing-3);
  }

  .layout__footer {
    padding: var(--spacing-3);
  }
}
</style>
