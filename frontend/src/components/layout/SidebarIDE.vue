/**
 * @file SidebarIDE.vue
 * @path src/components/layout/
 * @description IDE风格侧边栏组件 - 参考VS Code/PyCharm/Cursor的Activity Bar + Side Panel设计
 * @author Agent
 * @date 2024-03-15
 * @version 3.6.0
 */

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  DashboardOutlined,
  SettingOutlined,
  ExperimentOutlined,
  LineChartOutlined,
  ControlOutlined,
  ThunderboltOutlined,
  AimOutlined,
  FireOutlined,
  CompressOutlined,
  CloseOutlined,
  HomeOutlined,
  SafetyOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  AppstoreOutlined,
  DatabaseOutlined,
  HistoryOutlined,
  UserOutlined,
  TeamOutlined,
  InfoCircleOutlined,
  FileTextOutlined,
  SearchOutlined,
  FolderOutlined,
  BugOutlined,
  ApiOutlined,
  CodeOutlined
} from '@ant-design/icons-vue'
import { useDevicesStore } from '../../stores/devices'

const props = defineProps({
  collapsed: {
    type: Boolean,
    default: false
  },
  mobileOpen: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:mobileOpen', 'toggle', 'viewChange'])

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const devicesStore = useDevicesStore()

const searchQuery = ref('')
const searchInputRef = ref(null)
const hoveredItem = ref(null)

/**
 * Activity Bar 项目配置
 */
const activityItems = [
  {
    key: 'device',
    icon: DatabaseOutlined,
    title: '设备管理',
    badge: computed(() => devicesStore.disconnectedDevices.length)
  },
  {
    key: 'experiment',
    icon: ExperimentOutlined,
    title: '实验控制'
  },
  {
    key: 'analysis',
    icon: LineChartOutlined,
    title: '数据分析'
  },
  {
    key: 'settings',
    icon: SettingOutlined,
    title: '系统设置',
    badge: computed(() => devicesStore.unacknowledgedAlarmsCount)
  }
]

/**
 * 侧边面板视图配置
 */
const viewConfigs = {
  device: {
    title: '设备管理',
    icon: DatabaseOutlined,
    items: [
      {
        key: 'device-status',
        label: '设备状态',
        icon: DashboardOutlined,
        path: '/device/status'
      },
      {
        key: 'device-connection',
        label: '设备连接',
        icon: ApiOutlined,
        path: '/device/connection'
      },
      {
        key: 'device-prpath',
        label: 'PR路径',
        icon: CodeOutlined,
        path: '/device/prpath'
      }
    ]
  },
  experiment: {
    title: '实验控制',
    icon: ExperimentOutlined,
    items: [
      {
        key: 'motor',
        label: '电机控制',
        icon: ThunderboltOutlined,
        path: '/experiment/motor'
      },
      {
        key: 'electromagnet',
        label: '电磁铁控制',
        icon: AimOutlined,
        path: '/experiment/electromagnet'
      },
      {
        key: 'temperature',
        label: '温度控制',
        icon: FireOutlined,
        path: '/experiment/temperature'
      },
      {
        key: 'piezo',
        label: '压电陶瓷',
        icon: CompressOutlined,
        path: '/experiment/piezo'
      },
      {
        key: 'ammeter',
        label: '微电流计',
        icon: LineChartOutlined,
        path: '/experiment/ammeter'
      },
      {
        key: 'safety',
        label: '安全面板',
        icon: SafetyOutlined,
        path: '/experiment/safety'
      }
    ]
  },
  analysis: {
    title: '数据分析',
    icon: LineChartOutlined,
    items: [
      {
        key: 'realtime',
        label: '实时分析',
        icon: LineChartOutlined,
        path: '/analysis/realtime'
      },
      {
        key: 'history',
        label: '历史查询',
        icon: HistoryOutlined,
        path: '/analysis/history'
      },
      {
        key: 'charts',
        label: '图表分析',
        icon: LineChartOutlined,
        path: '/analysis/charts'
      }
    ]
  },
  settings: {
    title: '系统设置',
    icon: SettingOutlined,
    items: [
      {
        key: 'audit',
        label: '审计日志',
        icon: FileTextOutlined,
        path: '/settings/audit'
      },
      {
        key: 'config',
        label: '系统配置',
        icon: SettingOutlined,
        path: '/settings/config'
      },
      {
        key: 'profile',
        label: '个人资料',
        icon: UserOutlined,
        path: '/settings/profile'
      },
      {
        key: 'user-management',
        label: '用户管理',
        icon: TeamOutlined,
        path: '/settings/user-management'
      },
      {
        key: 'performance',
        label: '性能监控',
        icon: DashboardOutlined,
        path: '/settings/performance'
      },
      {
        key: 'about',
        label: '关于系统',
        icon: InfoCircleOutlined,
        path: '/settings/about'
      }
    ]
  }
}

/**
 * 当前激活的Activity
 */
const activeActivity = ref('device')

/**
 * 当前选中的菜单项
 */
const selectedKey = computed(() => {
  const path = route.path
  
  for (const [activityKey, config] of Object.entries(viewConfigs)) {
    for (const item of config.items) {
      if (item.path === path) {
        return item.key
      }
    }
  }
  
  return 'device-status'
})

/**
 * 当前视图配置
 */
const currentView = computed(() => viewConfigs[activeActivity.value])

/**
 * 过滤后的菜单项
 */
const filteredItems = computed(() => {
  if (!searchQuery.value.trim()) {
    return currentView.value.items
  }
  const query = searchQuery.value.toLowerCase()
  return currentView.value.items.filter(item => 
    item.label.toLowerCase().includes(query) ||
    item.key.toLowerCase().includes(query)
  )
})

/**
 * 根据路由自动设置激活的Activity
 */
watch(() => route.path, (path) => {
  for (const [activityKey, config] of Object.entries(viewConfigs)) {
    for (const item of config.items) {
      if (item.path === path) {
        activeActivity.value = activityKey
        return
      }
    }
  }
}, { immediate: true })

/**
 * 处理Activity点击
 */
function handleActivityClick(key) {
  if (activeActivity.value === key && !props.collapsed) {
    emit('toggle')
  } else {
    activeActivity.value = key
    if (props.collapsed) {
      emit('toggle')
    }
  }
}

/**
 * 处理菜单项点击
 */
function handleMenuClick(item) {
  router.push(item.path)
  emit('update:mobileOpen', false)
}

/**
 * 关闭移动端菜单
 */
function closeMobileMenu() {
  emit('update:mobileOpen', false)
}

/**
 * 切换侧边栏折叠状态
 */
function toggleSidebar() {
  emit('toggle')
}

/**
 * 处理搜索
 */
function handleSearch(event) {
  if (event.key === 'Escape') {
    searchQuery.value = ''
  }
}

/**
 * 快捷键处理
 */
function handleKeyboardShortcuts(event) {
  if ((event.ctrlKey || event.metaKey) && event.key === '/') {
    event.preventDefault()
    nextTick(() => {
      searchInputRef.value?.focus()
    })
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeyboardShortcuts)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyboardShortcuts)
})
</script>

<template>
  <aside
    class="ide-sidebar"
    :class="{
      'ide-sidebar--collapsed': collapsed && !mobileOpen,
      'ide-sidebar--mobile-open': mobileOpen
    }"
  >
    <!-- Activity Bar（最左侧图标栏） -->
    <div class="ide-sidebar__activity-bar">
      <!-- Logo -->
      <div
        class="activity-logo"
        @click="router.push('/')"
      >
        <ExperimentOutlined />
      </div>

      <!-- Activity Items -->
      <div class="activity-items">
        <button
          v-for="item in activityItems"
          :key="item.key"
          class="activity-item"
          :class="{ 'is-active': activeActivity === item.key }"
          :title="item.title"
          @click="handleActivityClick(item.key)"
        >
          <component :is="item.icon" />
          <span
            v-if="item.badge?.value > 0"
            class="activity-badge"
          >
            {{ item.badge.value > 99 ? '99+' : item.badge.value }}
          </span>
        </button>
      </div>

      <!-- 底部操作 -->
      <div class="activity-footer">
        <button
          class="activity-item"
          title="切换侧边栏"
          @click="toggleSidebar"
        >
          <MenuFoldOutlined v-if="!collapsed" />
          <MenuUnfoldOutlined v-else />
        </button>
      </div>
    </div>

    <!-- Side Panel（侧边面板） -->
    <div
      v-if="!collapsed || mobileOpen"
      class="ide-sidebar__panel"
    >
      <!-- 面板头部 -->
      <div class="panel-header">
        <h3 class="panel-title">
          {{ currentView.title }}
        </h3>
        <button
          v-if="mobileOpen"
          class="panel-close"
          @click="closeMobileMenu"
        >
          <CloseOutlined />
        </button>
      </div>

      <!-- 搜索框 -->
      <div class="panel-search">
        <SearchOutlined class="search-icon" />
        <input
          ref="searchInputRef"
          v-model="searchQuery"
          type="text"
          placeholder="搜索菜单... (Ctrl+/)"
          class="search-input"
          @keydown="handleSearch"
        >
      </div>

      <!-- 菜单列表 -->
      <nav class="panel-nav">
        <button
          v-for="item in filteredItems"
          :key="item.key"
          class="nav-item"
          :class="{ 'is-active': selectedKey === item.key }"
          @click="handleMenuClick(item)"
          @mouseenter="hoveredItem = item.key"
          @mouseleave="hoveredItem = null"
        >
          <component
            :is="item.icon"
            class="nav-icon"
          />
          <span class="nav-label">{{ item.label }}</span>
          <span class="nav-shortcut">
            <kbd>{{ item.key.charAt(0).toUpperCase() }}</kbd>
          </span>
        </button>
        <div
          v-if="filteredItems.length === 0"
          class="nav-empty"
        >
          未找到匹配的菜单
        </div>
      </nav>

      <!-- 面板底部 -->
      <div class="panel-footer">
        <div class="footer-info">
          <span class="version">v3.6.0</span>
          <span
            class="status-dot"
            :class="{ 'is-connected': devicesStore.wsConnected }"
          />
        </div>
      </div>
    </div>

    <!-- 移动端遮罩 -->
    <transition name="fade">
      <div
        v-if="mobileOpen"
        class="ide-sidebar__overlay"
        @click="closeMobileMenu"
      />
    </transition>
  </aside>
</template>

<style scoped>
.ide-sidebar {
  display: flex;
  height: 100vh;
  position: fixed;
  top: 0;
  left: 0;
  z-index: var(--z-index-fixed);
  background: var(--color-surface-primary);
}

/* Activity Bar */
.ide-sidebar__activity-bar {
  display: flex;
  flex-direction: column;
  width: 48px;
  background: var(--color-neutral-900);
  border-right: 1px solid var(--color-border-primary);
}

.activity-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 48px;
  font-size: 22px;
  color: var(--color-primary-400);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.activity-logo:hover {
  color: var(--color-primary-300);
  background: rgba(255, 255, 255, 0.05);
}

.activity-items {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
  padding: var(--spacing-2);
}

.activity-item {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  margin: 0 auto;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  color: var(--color-neutral-400);
  font-size: 20px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.activity-item:hover {
  color: white;
  background: rgba(255, 255, 255, 0.1);
}

.activity-item.is-active {
  color: white;
  background: rgba(255, 255, 255, 0.15);
}

.activity-item.is-active::before {
  content: '';
  position: absolute;
  left: -8px;
  top: 50%;
  transform: translateY(-50%);
  width: 2px;
  height: 24px;
  background: var(--color-primary-500);
  border-radius: 0 2px 2px 0;
}

.activity-badge {
  position: absolute;
  top: 2px;
  right: 2px;
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

.activity-footer {
  padding: var(--spacing-2);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

/* Side Panel */
.ide-sidebar__panel {
  display: flex;
  flex-direction: column;
  width: 220px;
  background: var(--color-surface-primary);
  border-right: 1px solid var(--color-border-primary);
  transition: width var(--transition-normal);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-3) var(--spacing-4);
  border-bottom: 1px solid var(--color-border-primary);
  height: 48px;
}

.panel-title {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0;
}

.panel-close {
  display: none;
  width: 28px;
  height: 28px;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
}

.panel-search {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-3);
  margin: var(--spacing-2);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
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

/* 导航菜单 */
.panel-nav {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-2);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  width: 100%;
  padding: var(--spacing-2) var(--spacing-3);
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  text-align: left;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.nav-item:hover {
  background: var(--color-interactive-hover);
  color: var(--color-text-primary);
}

.nav-item.is-active {
  background: var(--color-primary-50);
  color: var(--color-primary-600);
}

.nav-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.nav-label {
  flex: 1;
  font-weight: var(--font-weight-medium);
}

.nav-shortcut {
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.nav-item:hover .nav-shortcut {
  opacity: 1;
}

.nav-shortcut kbd {
  padding: 2px 6px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-family: inherit;
  color: var(--color-text-tertiary);
}

.nav-empty {
  padding: var(--spacing-6);
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

/* 面板底部 */
.panel-footer {
  padding: var(--spacing-3) var(--spacing-4);
  border-top: 1px solid var(--color-border-primary);
}

.footer-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.version {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.status-dot {
  width: 8px;
  height: 8px;
  background: var(--color-error);
  border-radius: 50%;
  transition: background var(--transition-fast);
}

.status-dot.is-connected {
  background: var(--color-success);
}

/* 遮罩 */
.ide-sidebar__overlay {
  display: none;
}

/* 折叠状态 */
.ide-sidebar--collapsed .ide-sidebar__panel {
  display: none;
}

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 响应式 */
@media (max-width: 768px) {
  .ide-sidebar {
    transform: translateX(-100%);
  }

  .ide-sidebar--mobile-open {
    transform: translateX(0);
  }

  .ide-sidebar__panel {
    width: 280px;
  }

  .panel-close {
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .ide-sidebar__overlay {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: -1;
  }
}
</style>
