/**
 * @file LayoutIDE.vue
 * @path src/views/
 * @description IDE风格主布局组件 - 参考VS Code/PyCharm/Cursor布局设计
 * @author Agent
 * @date 2024-03-15
 * @version 3.6.0
 */

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, defineAsyncComponent, provide, shallowRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { wsClient } from '../api/websocket'
import { useDevicesStore } from '../stores/devices'
import { useLoading } from '../composables/useLoading'

const SidebarIDE = defineAsyncComponent(() => import('../components/layout/SidebarIDE.vue'))
const TopbarIDE = defineAsyncComponent(() => import('../components/layout/TopbarIDE.vue'))
const StatusBarIDE = defineAsyncComponent(() => import('../components/layout/StatusBarIDE.vue'))
const GlobalLoading = defineAsyncComponent(() => import('../components/common/GlobalLoading.vue'))
const PageSkeleton = defineAsyncComponent(() => import('../components/common/PageSkeleton.vue'))

const route = useRoute()
const router = useRouter()
const devicesStore = useDevicesStore()
const { startLoading, stopLoading, showGlobalOverlay } = useLoading()

const sidebarCollapsed = ref(false)
const isMobile = ref(false)
const mobileMenuOpen = ref(false)
const showCommandPalette = ref(false)
const commandQuery = ref('')
const commandInputRef = ref(null)
const isPageLoading = ref(false)
const pageLoadingKey = ref(0)

provide('layoutContext', {
  sidebarCollapsed,
  isMobile,
  toggleSidebar: () => { sidebarCollapsed.value = !sidebarCollapsed.value }
})

/**
 * 命令列表
 */
const commands = [
  { key: 'navigate', label: '快速导航', icon: '🧭', shortcut: 'Ctrl+P', action: () => {} },
  { key: 'search', label: '全局搜索', icon: '🔍', shortcut: 'Ctrl+F', action: () => {} },
  { key: 'settings', label: '系统设置', icon: '⚙️', shortcut: 'Ctrl+,', action: () => router.push('/settings/config') },
  { key: 'device-status', label: '设备状态', icon: '📊', action: () => router.push('/device/status') },
  { key: 'motor', label: '电机控制', icon: '⚡', action: () => router.push('/experiment/motor') },
  { key: 'realtime', label: '实时分析', icon: '📈', action: () => router.push('/analysis/realtime') },
  { key: 'help', label: '帮助文档', icon: '❓', action: () => message.info('帮助文档即将上线') }
]

/**
 * 过滤后的命令
 */
const filteredCommands = computed(() => {
  if (!commandQuery.value) return commands
  const query = commandQuery.value.toLowerCase()
  return commands.filter(cmd => 
    cmd.label.toLowerCase().includes(query) || 
    cmd.key.toLowerCase().includes(query)
  )
})

/**
 * 当前页面标题
 */
const pageTitle = computed(() => route.meta?.title || 'CAUC-SEP')

/**
 * 页面类型（用于骨架屏）
 */
const pageType = computed(() => {
  const path = route.path
  if (path.includes('/experiment/')) return 'control'
  if (path.includes('/analysis/')) return 'analysis'
  if (path.includes('/settings/')) return 'settings'
  if (path.includes('/device/')) return 'default'
  return 'default'
})

/**
 * 切换侧边栏
 */
function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
  localStorage.setItem('sidebar_collapsed', sidebarCollapsed.value)
}

/**
 * 切换移动端菜单
 */
function toggleMobileMenu() {
  mobileMenuOpen.value = !mobileMenuOpen.value
}

/**
 * 打开命令面板
 */
function openCommandPalette() {
  showCommandPalette.value = true
  setTimeout(() => {
    commandInputRef.value?.focus()
  }, 100)
}

/**
 * 执行命令
 */
function executeCommand(cmd) {
  showCommandPalette.value = false
  commandQuery.value = ''
  if (cmd.action) {
    cmd.action()
  }
}

/**
 * 检查移动设备
 */
function checkMobile() {
  isMobile.value = window.innerWidth < 768
  if (!isMobile.value) {
    mobileMenuOpen.value = false
  }
}

/**
 * 恢复侧边栏状态
 */
function restoreSidebarState() {
  const saved = localStorage.getItem('sidebar_collapsed')
  if (saved !== null) {
    sidebarCollapsed.value = saved === 'true'
  }
}

/**
 * 处理键盘快捷键
 */
function handleKeyboardShortcuts(event) {
  if ((event.ctrlKey || event.metaKey) && event.key === 'b') {
    event.preventDefault()
    toggleSidebar()
  }
  if ((event.ctrlKey || event.metaKey) && event.key === 'p') {
    event.preventDefault()
    openCommandPalette()
  }
  if (event.key === 'Escape') {
    showCommandPalette.value = false
    mobileMenuOpen.value = false
    commandQuery.value = ''
  }
}

watch(() => route.path, (newPath) => {
  if (isMobile.value) {
    mobileMenuOpen.value = false
  }
}, { immediate: true })

onMounted(() => {
  checkMobile()
  restoreSidebarState()
  window.addEventListener('resize', checkMobile)
  document.addEventListener('keydown', handleKeyboardShortcuts)

  startLoading('app-init', { message: '正在初始化...', showOverlay: true })
  
  const wsConnectTimeout = setTimeout(() => {
    stopLoading('app-init', false)
    console.warn('[LayoutIDE] WebSocket连接超时，已跳过')
  }, 5000)
  
  wsClient.connect()
    .then(() => {
      clearTimeout(wsConnectTimeout)
      stopLoading('app-init', true)
    })
    .catch((error) => {
      clearTimeout(wsConnectTimeout)
      stopLoading('app-init', false)
      console.warn('[LayoutIDE] WebSocket连接失败，应用仍可正常使用:', error)
    })

  devicesStore.init()
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
  document.removeEventListener('keydown', handleKeyboardShortcuts)
  wsClient.disconnect()
  devicesStore.cleanup()
})
</script>

<template>
  <div class="ide-layout">
    <!-- IDE风格侧边栏 -->
    <SidebarIDE
      :collapsed="sidebarCollapsed"
      :mobile-open="mobileMenuOpen"
      @update:mobile-open="mobileMenuOpen = $event"
      @toggle="toggleSidebar"
    />

    <!-- 主内容区域 -->
    <div
      class="ide-layout__main"
      :class="{
        'ide-layout__main--collapsed': sidebarCollapsed && !isMobile
      }"
    >
      <!-- IDE风格顶部栏 -->
      <TopbarIDE
        :sidebar-collapsed="sidebarCollapsed"
        @toggle-sidebar="toggleSidebar"
        @toggle-mobile-menu="toggleMobileMenu"
        @open-command-palette="openCommandPalette"
      />

      <!-- 页面内容区域 -->
      <main class="ide-layout__content">
        <!-- 骨架屏加载状态 -->
        <transition
          name="skeleton-fade"
          mode="out-in"
        >
          <PageSkeleton
            v-if="isPageLoading"
            :key="pageLoadingKey"
            :type="pageType"
          />
          <!-- 路由视图 -->
          <router-view
            v-else
            v-slot="{ Component }"
          >
            <transition
              name="page-slide"
              mode="out-in"
              @before-enter="isPageLoading = true"
              @after-enter="isPageLoading = false"
            >
              <keep-alive :include="['DeviceStatus', 'MotorControl', 'RealtimeAnalysis', 'ElectromagnetControl', 'TemperatureControl']">
                <component
                  :is="Component"
                  :key="route.path"
                />
              </keep-alive>
            </transition>
          </router-view>
        </transition>
      </main>

      <!-- IDE风格底部状态栏 - 固定在主界面上层 -->
      <StatusBarIDE />
    </div>

    <!-- 全局加载指示器 -->
    <GlobalLoading
      :show-progress="true"
      :show-message="true"
      spinner-type="circle"
    />

    <!-- 命令面板 -->
    <Teleport to="body">
      <transition name="modal">
        <div
          v-if="showCommandPalette"
          class="command-palette-overlay"
          @click="showCommandPalette = false"
        >
          <div
            class="command-palette"
            @click.stop
          >
            <div class="command-palette__header">
              <span class="command-palette__title">命令面板</span>
              <kbd>ESC</kbd>
            </div>
            <div class="command-palette__search">
              <input
                ref="commandInputRef"
                v-model="commandQuery"
                type="text"
                placeholder="输入命令或搜索..."
                @keydown.enter="filteredCommands[0] && executeCommand(filteredCommands[0])"
                @keydown.escape="showCommandPalette = false"
              >
            </div>
            <div class="command-palette__list">
              <div
                v-for="cmd in filteredCommands"
                :key="cmd.key"
                class="command-palette__item"
                @click="executeCommand(cmd)"
              >
                <span class="command-palette__item-icon">{{ cmd.icon }}</span>
                <span class="command-palette__item-text">{{ cmd.label }}</span>
                <kbd v-if="cmd.shortcut">{{ cmd.shortcut }}</kbd>
              </div>
              <div
                v-if="filteredCommands.length === 0"
                class="command-palette__empty"
              >
                未找到匹配的命令
              </div>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<style scoped>
.ide-layout {
  display: flex;
  min-height: 100vh;
  background: var(--color-bg-secondary);
}

.ide-layout__main {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-left: 268px;
  transition: margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  min-height: 100vh;
  position: relative;
}

.ide-layout__main--collapsed {
  margin-left: 48px;
}

.ide-layout__content {
  flex: 1;
  padding: var(--spacing-4);
  overflow-x: hidden;
  overflow-y: auto;
  position: relative;
  background: var(--color-bg-secondary);
  padding-bottom: 40px;
}

/* 过渡动画 */
.page-slide-enter-active,
.page-slide-leave-active {
  transition: all 0.15s ease;
}

.page-slide-enter-from {
  opacity: 0;
  transform: translateX(10px);
}

.page-slide-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}

/* 骨架屏过渡动画 */
.skeleton-fade-enter-active,
.skeleton-fade-leave-active {
  transition: opacity 0.2s ease;
}

.skeleton-fade-enter-from,
.skeleton-fade-leave-to {
  opacity: 0;
}

/* 命令面板 */
.command-palette-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 15vh;
  z-index: var(--z-index-modal);
}

.command-palette {
  width: 100%;
  max-width: 560px;
  background: var(--color-surface-primary);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-2xl);
  overflow: hidden;
}

.command-palette__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-3) var(--spacing-4);
  border-bottom: 1px solid var(--color-border-primary);
}

.command-palette__title {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-secondary);
}

.command-palette__header kbd {
  padding: 2px 6px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-sm);
  font-size: 11px;
  color: var(--color-text-tertiary);
}

.command-palette__search {
  padding: var(--spacing-3) var(--spacing-4);
}

.command-palette__search input {
  width: 100%;
  padding: var(--spacing-3);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  outline: none;
}

.command-palette__search input:focus {
  border-color: var(--color-primary-400);
  box-shadow: 0 0 0 2px rgba(0, 119, 255, 0.1);
}

.command-palette__list {
  max-height: 300px;
  overflow-y: auto;
}

.command-palette__item {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-3) var(--spacing-4);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.command-palette__item:hover {
  background: var(--color-interactive-hover);
}

.command-palette__item-icon {
  font-size: 16px;
}

.command-palette__item-text {
  flex: 1;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.command-palette__item kbd {
  padding: 2px 6px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-sm);
  font-size: 11px;
  color: var(--color-text-tertiary);
}

.command-palette__empty {
  padding: var(--spacing-6);
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

/* 模态框动画 */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-active .command-palette,
.modal-leave-active .command-palette {
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .command-palette,
.modal-leave-to .command-palette {
  transform: translateY(-20px);
  opacity: 0;
}

/* 响应式 */
@media (max-width: 768px) {
  .ide-layout__main {
    margin-left: 0;
  }

  .ide-layout__main--collapsed {
    margin-left: 0;
  }

  .ide-layout__content {
    padding: var(--spacing-3);
  }

  .command-palette {
    margin: 0 var(--spacing-4);
    max-width: calc(100% - var(--spacing-8));
  }
}
</style>
