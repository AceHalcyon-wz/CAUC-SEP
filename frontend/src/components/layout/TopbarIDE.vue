/**
 * @file TopbarIDE.vue
 * @path src/components/layout/
 * @description IDE风格顶部导航栏组件 - 参考VS Code/PyCharm/Cursor设计
 * @author Agent
 * @date 2024-03-15
 * @version 3.6.0
 */

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { message, Modal } from 'ant-design-vue'
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  SearchOutlined,
  BellOutlined,
  UserOutlined,
  SettingOutlined,
  LogoutOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  QuestionCircleOutlined,
  GithubOutlined,
  ThunderboltOutlined,
  BookOutlined,
  ReloadOutlined,
  SyncOutlined
} from '@ant-design/icons-vue'
import { wsClient } from '../../api/websocket'
import { useDevicesStore } from '../../stores/devices'
import { useUserStore } from '../../stores/user'

const props = defineProps({
  sidebarCollapsed: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['toggleSidebar', 'toggleMobileMenu', 'openCommandPalette'])

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const devicesStore = useDevicesStore()
const userStore = useUserStore()

const isFullscreen = ref(false)
const searchQuery = ref('')
const searchFocused = ref(false)
const showSearch = ref(false)
const showNotifications = ref(false)
const autoRefresh = ref(false)
const notifications = ref([
  { id: 1, title: '系统更新', content: '新版本 v3.6.0 已发布', time: '10分钟前', read: false },
  { id: 2, title: '设备告警', content: '温度传感器超出阈值', time: '30分钟前', read: false },
  { id: 3, title: '实验完成', content: '电机控制实验已完成', time: '1小时前', read: true }
])

/**
 * 连接状态配置
 */
const connectionStatus = computed(() => {
  if (devicesStore.wsConnected) {
    return { 
      text: '已连接', 
      type: 'success', 
      icon: CheckCircleOutlined,
      color: '#10b981'
    }
  }
  return { 
    text: '未连接', 
    type: 'error', 
    icon: CloseCircleOutlined,
    color: '#ef4444'
  }
})

/**
 * 面包屑导航
 */
const breadcrumbs = computed(() => {
  const path = route.path
  const parts = path.split('/').filter(Boolean)
  const crumbs = [{ label: '首页', path: '/device/status' }]
  
  const routeMap = {
    'device': '设备管理',
    'experiment': '实验控制',
    'analysis': '数据分析',
    'settings': '系统设置',
    'status': '设备状态',
    'connection': '设备连接',
    'prpath': 'PR路径',
    'motor': '电机控制',
    'electromagnet': '电磁铁控制',
    'temperature': '温度控制',
    'piezo': '压电陶瓷',
    'ammeter': '微电流计',
    'safety': '安全面板',
    'realtime': '实时分析',
    'history': '历史查询',
    'charts': '图表分析',
    'audit': '审计日志',
    'config': '系统配置',
    'profile': '个人资料',
    'about': '关于系统',
    'performance': '性能监控',
    'user-management': '用户管理'
  }
  
  parts.forEach((part, index) => {
    const label = routeMap[part] || part
    const pathTo = '/' + parts.slice(0, index + 1).join('/')
    crumbs.push({ label, path: pathTo })
  })
  
  return crumbs
})

/**
 * 当前页面标题
 */
const pageTitle = computed(() => {
  return route.meta?.title || 'CAUC-SEP'
})

/**
 * 未读通知数量
 */
const unreadCount = computed(() => {
  return notifications.value.filter(n => !n.read).length
})

/**
 * 当前用户信息
 */
const currentUser = computed(() => {
  return userStore.currentUser || { username: 'Guest', role: '访客' }
})

/**
 * 切换全屏
 */
function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(() => {})
    isFullscreen.value = true
  } else {
    document.exitFullscreen().catch(() => {})
    isFullscreen.value = false
  }
}

/**
 * 处理搜索
 */
function handleSearch(event) {
  if (event.key === 'Enter' && searchQuery.value.trim()) {
    message.info(`搜索: ${searchQuery.value}`)
    searchQuery.value = ''
  }
  if (event.key === 'Escape') {
    searchQuery.value = ''
    searchFocused.value = false
  }
}

/**
 * 打开命令面板
 */
function openCommandPalette() {
  emit('openCommandPalette')
}

/**
 * 快捷键处理
 */
function handleKeyboardShortcuts(event) {
  if ((event.ctrlKey || event.metaKey) && event.key === 'p') {
    event.preventDefault()
    openCommandPalette()
  }
  if ((event.ctrlKey || event.metaKey) && event.key === 'f') {
    event.preventDefault()
    showSearch.value = true
    searchFocused.value = true
  }
}

/**
 * 打开帮助文档
 */
function openHelp() {
  router.push('/settings/help-docs')
}

/**
 * 打开GitHub
 */
function openGitHub() {
  window.open('https://github.com', '_blank')
}

/**
 * 刷新当前页面
 */
function refreshPage() {
  router.go(0)
}

/**
 * 切换自动刷新
 */
function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) {
    message.success('已开启页面自动刷新')
  } else {
    message.info('已关闭页面自动刷新')
  }
}

/**
 * 标记通知已读
 */
function markAsRead(id) {
  const notification = notifications.value.find(n => n.id === id)
  if (notification) {
    notification.read = true
  }
}

/**
 * 全部标记已读
 */
function markAllAsRead() {
  notifications.value.forEach(n => n.read = true)
  message.success('已全部标记为已读')
}

/**
 * 处理登出
 */
async function handleLogout() {
  Modal.confirm({
    title: '确认退出',
    content: '确定要退出登录吗？',
    okText: '确定',
    cancelText: '取消',
    async onOk() {
      try {
        wsClient.disconnect()
        await userStore.logout()
        localStorage.removeItem('auth_token')
        localStorage.removeItem('token')
        message.success('已成功退出登录')
        router.push('/login')
      } catch (error) {
        console.error('[TopbarIDE] 登出错误:', error)
        localStorage.removeItem('auth_token')
        localStorage.removeItem('token')
        router.push('/login')
      }
    }
  })
}

/**
 * 跳转到个人资料
 */
function goToProfile() {
  router.push('/settings/profile')
}

/**
 * 跳转到设置
 */
function goToSettings() {
  router.push('/settings/config')
}

onMounted(() => {
  document.addEventListener('keydown', handleKeyboardShortcuts)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyboardShortcuts)
})

watch(() => route.path, () => {
  if (autoRefresh.value) {
    router.go(0)
  }
})
</script>

<template>
  <header class="ide-topbar">
    <!-- 左侧区域：菜单按钮 + 面包屑 -->
    <div class="ide-topbar__left">
      <!-- 侧边栏切换按钮 -->
      <button
        class="ide-topbar__menu-btn"
        :class="{ 'is-collapsed': sidebarCollapsed }"
        :title="sidebarCollapsed ? '展开侧边栏 (Ctrl+B)' : '收起侧边栏 (Ctrl+B)'"
        @click="$emit('toggleSidebar')"
      >
        <MenuFoldOutlined v-if="!sidebarCollapsed" />
        <MenuUnfoldOutlined v-else />
      </button>

      <!-- 面包屑导航 -->
      <nav class="ide-topbar__breadcrumbs">
        <template
          v-for="(crumb, index) in breadcrumbs"
          :key="crumb.path"
        >
          <span
            v-if="index > 0"
            class="breadcrumb-separator"
          >/</span>
          <router-link
            :to="crumb.path"
            class="breadcrumb-item"
            :class="{ 'is-current': index === breadcrumbs.length - 1 }"
          >
            {{ crumb.label }}
          </router-link>
        </template>
      </nav>
    </div>

    <!-- 中间区域：页面标题 -->
    <div class="ide-topbar__center">
      <h1 class="ide-topbar__title">
        {{ pageTitle }}
      </h1>
    </div>

    <!-- 右侧区域：工具栏 -->
    <div class="ide-topbar__right">
      <!-- 搜索框 -->
      <div
        class="ide-topbar__search"
        :class="{ 'is-focused': searchFocused, 'is-visible': showSearch }"
      >
        <SearchOutlined class="search-icon" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索... (Ctrl+F)"
          class="search-input"
          @focus="searchFocused = true"
          @blur="searchFocused = false"
          @keydown="handleSearch"
        >
        <kbd
          v-if="!searchFocused"
          class="search-shortcut"
        >
          Ctrl+F
        </kbd>
      </div>

      <!-- 命令面板按钮 -->
      <button
        class="ide-topbar__tool-btn"
        title="命令面板 (Ctrl+P)"
        @click="openCommandPalette"
      >
        <ThunderboltOutlined />
      </button>

      <!-- 刷新按钮 -->
      <button
        class="ide-topbar__tool-btn"
        title="刷新页面"
        @click="refreshPage"
      >
        <ReloadOutlined />
      </button>

      <!-- 自动刷新开关 -->
      <button
        class="ide-topbar__tool-btn"
        :class="{ 'is-active': autoRefresh }"
        :title="autoRefresh ? '关闭自动刷新' : '开启自动刷新'"
        @click="toggleAutoRefresh"
      >
        <SyncOutlined :spin="autoRefresh" />
      </button>

      <!-- 连接状态 -->
      <div
        class="ide-topbar__status"
        :style="{ color: connectionStatus.color }"
        :title="`WebSocket: ${connectionStatus.text}`"
      >
        <component :is="connectionStatus.icon" />
        <span class="status-text">{{ connectionStatus.text }}</span>
      </div>

      <!-- 分隔线 -->
      <div class="ide-topbar__divider" />

      <!-- 全屏 -->
      <button
        class="ide-topbar__tool-btn"
        :title="isFullscreen ? '退出全屏' : '全屏'"
        @click="toggleFullscreen"
      >
        <FullscreenExitOutlined v-if="isFullscreen" />
        <FullscreenOutlined v-else />
      </button>

      <!-- 通知 -->
      <a-dropdown
        :trigger="['click']"
        placement="bottomRight"
      >
        <button class="ide-topbar__tool-btn ide-topbar__tool-btn--badge">
          <BellOutlined />
          <span
            v-if="unreadCount > 0"
            class="ide-topbar__badge"
          >
            {{ unreadCount > 99 ? '99+' : unreadCount }}
          </span>
        </button>
        <template #overlay>
          <div class="notification-dropdown">
            <div class="notification-header">
              <span class="notification-title">通知</span>
              <a
                v-if="unreadCount > 0"
                class="notification-mark-all"
                @click="markAllAsRead"
              >
                全部已读
              </a>
            </div>
            <div class="notification-list">
              <div
                v-for="notification in notifications"
                :key="notification.id"
                class="notification-item"
                :class="{ 'is-unread': !notification.read }"
                @click="markAsRead(notification.id)"
              >
                <div class="notification-item__title">
                  {{ notification.title }}
                </div>
                <div class="notification-item__content">
                  {{ notification.content }}
                </div>
                <div class="notification-item__time">
                  {{ notification.time }}
                </div>
              </div>
            </div>
            <div class="notification-footer">
              <a @click="message.info('查看全部通知功能即将上线')">
                查看全部
              </a>
            </div>
          </div>
        </template>
      </a-dropdown>

      <!-- 帮助 -->
      <a-dropdown :trigger="['click']">
        <button
          class="ide-topbar__tool-btn"
          title="帮助"
        >
          <QuestionCircleOutlined />
        </button>
        <template #overlay>
          <a-menu>
            <a-menu-item @click="openHelp">
              <template #icon>
                <BookOutlined />
              </template>
              帮助文档
            </a-menu-item>
            <a-menu-item @click="openGitHub">
              <template #icon>
                <GithubOutlined />
              </template>
              GitHub
            </a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>

      <!-- 用户菜单 -->
      <a-dropdown :trigger="['click']">
        <button class="ide-topbar__user-btn">
          <a-avatar
            :size="28"
            class="user-avatar"
          >
            <template #icon>
              <UserOutlined />
            </template>
          </a-avatar>
          <span class="user-name">{{ currentUser.username }}</span>
        </button>
        <template #overlay>
          <a-menu class="user-menu">
            <a-menu-item
              key="profile"
              @click="goToProfile"
            >
              <template #icon>
                <UserOutlined />
              </template>
              个人资料
            </a-menu-item>
            <a-menu-item
              key="settings"
              @click="goToSettings"
            >
              <template #icon>
                <SettingOutlined />
              </template>
              设置
            </a-menu-item>
            <a-menu-divider />
            <a-menu-item
              key="logout"
              danger
              @click="handleLogout"
            >
              <template #icon>
                <LogoutOutlined />
              </template>
              退出登录
            </a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
    </div>
  </header>
</template>

<style scoped>
.ide-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 var(--spacing-4);
  background: var(--color-surface-primary);
  border-bottom: 1px solid var(--color-border-primary);
  position: sticky;
  top: 0;
  z-index: var(--z-index-sticky);
  gap: var(--spacing-4);
}

/* 左侧区域 */
.ide-topbar__left {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  flex: 1;
  min-width: 0;
}

.ide-topbar__menu-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  font-size: 18px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.ide-topbar__menu-btn:hover {
  background: var(--color-interactive-hover);
  color: var(--color-primary-500);
}

.ide-topbar__menu-btn.is-collapsed {
  color: var(--color-primary-500);
}

/* 面包屑 */
.ide-topbar__breadcrumbs {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  font-size: var(--font-size-sm);
  overflow: hidden;
}

.breadcrumb-item {
  color: var(--color-text-secondary);
  text-decoration: none;
  padding: var(--spacing-1) var(--spacing-2);
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.breadcrumb-item:hover {
  color: var(--color-primary-500);
  background: var(--color-interactive-hover);
}

.breadcrumb-item.is-current {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
}

.breadcrumb-separator {
  color: var(--color-text-tertiary);
  user-select: none;
}

/* 中间区域 */
.ide-topbar__center {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.ide-topbar__title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
  white-space: nowrap;
}

/* 右侧区域 */
.ide-topbar__right {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  flex: 1;
  justify-content: flex-end;
}

/* 搜索框 */
.ide-topbar__search {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-1) var(--spacing-3);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
  width: 200px;
}

.ide-topbar__search.is-focused {
  border-color: var(--color-primary-400);
  box-shadow: 0 0 0 2px rgba(0, 119, 255, 0.1);
}

.search-icon {
  color: var(--color-text-tertiary);
  font-size: 14px;
}

.search-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  outline: none;
}

.search-input::placeholder {
  color: var(--color-text-tertiary);
}

.search-shortcut {
  padding: 2px 6px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-sm);
  font-size: 11px;
  color: var(--color-text-tertiary);
  font-family: inherit;
}

/* 工具按钮 */
.ide-topbar__tool-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  font-size: 16px;
  cursor: pointer;
  transition: all var(--transition-fast);
  text-decoration: none;
}

.ide-topbar__tool-btn:hover {
  background: var(--color-interactive-hover);
  color: var(--color-primary-500);
}

.ide-topbar__tool-btn.is-active {
  background: var(--color-primary-50);
  color: var(--color-primary-500);
}

.ide-topbar__tool-btn--badge {
  position: relative;
}

.ide-topbar__badge {
  position: absolute;
  top: 4px;
  right: 4px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  background: var(--color-error);
  color: white;
  font-size: 10px;
  font-weight: var(--font-weight-semibold);
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 状态指示器 */
.ide-topbar__status {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  padding: var(--spacing-1) var(--spacing-2);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
}

.status-text {
  display: none;
}

@media (min-width: 1024px) {
  .status-text {
    display: inline;
  }
}

/* 分隔线 */
.ide-topbar__divider {
  width: 1px;
  height: 24px;
  background: var(--color-border-primary);
  margin: 0 var(--spacing-1);
}

/* 用户按钮 */
.ide-topbar__user-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-1);
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.ide-topbar__user-btn:hover {
  background: var(--color-interactive-hover);
}

.user-avatar {
  background: linear-gradient(135deg, var(--color-primary-500), var(--color-primary-600));
}

.user-name {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  display: none;
}

@media (min-width: 768px) {
  .user-name {
    display: inline;
  }
}

/* 响应式 */
@media (max-width: 768px) {
  .ide-topbar {
    padding: 0 var(--spacing-3);
  }

  .ide-topbar__search {
    display: none;
  }

  .ide-topbar__breadcrumbs {
    display: none;
  }

  .ide-topbar__divider {
    display: none;
  }
}

/* 通知下拉菜单 */
.notification-dropdown {
  width: 320px;
  background: var(--color-surface-primary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
}

.notification-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-3) var(--spacing-4);
  border-bottom: 1px solid var(--color-border-primary);
}

.notification-title {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.notification-mark-all {
  font-size: var(--font-size-sm);
  color: var(--color-primary-500);
  cursor: pointer;
}

.notification-mark-all:hover {
  color: var(--color-primary-600);
}

.notification-list {
  max-height: 300px;
  overflow-y: auto;
}

.notification-item {
  padding: var(--spacing-3) var(--spacing-4);
  border-bottom: 1px solid var(--color-border-primary);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.notification-item:hover {
  background: var(--color-interactive-hover);
}

.notification-item.is-unread {
  background: rgba(0, 119, 255, 0.05);
}

.notification-item__title {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-1);
}

.notification-item__content {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-1);
}

.notification-item__time {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.notification-footer {
  padding: var(--spacing-3) var(--spacing-4);
  text-align: center;
  border-top: 1px solid var(--color-border-primary);
}

.notification-footer a {
  font-size: var(--font-size-sm);
  color: var(--color-primary-500);
  cursor: pointer;
}

.notification-footer a:hover {
  color: var(--color-primary-600);
}
</style>
