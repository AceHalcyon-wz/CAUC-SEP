/**
 * @file Sidebar.vue
 * @path src/components/layout/
 * @description 侧边栏导航组件 - 优化版
 * @author Agent
 * @date 2024-03-15
 * @version 3.5.1
 */

<script setup>
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
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
  MenuUnfoldOutlined
} from '@ant-design/icons-vue';
import { useDevicesStore } from '../../stores/devices';

const props = defineProps({
  collapsed: {
    type: Boolean,
    default: false
  },
  mobileOpen: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['update:mobileOpen', 'toggle']);

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const devicesStore = useDevicesStore();

/**
 * 导航菜单项配置
 */
const menuItems = [
  {
    key: 'device',
    icon: DashboardOutlined,
    label: t('nav.device'),
    path: '/device/status',
    badge: computed(() => devicesStore.disconnectedDevices.length)
  },
  {
    key: 'experiment',
    icon: ControlOutlined,
    label: t('nav.experiment'),
    children: [
      {
        key: 'motor',
        icon: ThunderboltOutlined,
        label: t('nav.motor'),
        path: '/experiment/motor'
      },
      {
        key: 'electromagnet',
        icon: AimOutlined,
        label: t('nav.electromagnet'),
        path: '/experiment/electromagnet'
      },
      {
        key: 'temperature',
        icon: FireOutlined,
        label: t('nav.temperature'),
        path: '/experiment/temperature'
      },
      {
        key: 'piezo',
        icon: CompressOutlined,
        label: t('nav.piezo'),
        path: '/experiment/piezo'
      },
      {
        key: 'ammeter',
        icon: LineChartOutlined,
        label: t('nav.ammeter'),
        path: '/experiment/ammeter'
      }
    ]
  },
  {
    key: 'analysis',
    icon: LineChartOutlined,
    label: t('nav.analysis'),
    path: '/analysis/realtime'
  },
  {
    key: 'settings',
    icon: SettingOutlined,
    label: t('nav.settings'),
    path: '/settings/audit',
    badge: computed(() => devicesStore.unacknowledgedAlarmsCount)
  }
];

/**
 * 展开的子菜单
 */
const openKeys = ref([]);

/**
 * 当前选中的菜单项
 */
const selectedKeys = computed(() => {
  const path = route.path;
  const keys = [];

  menuItems.forEach(item => {
    if (item.path === path) {
      keys.push(item.key);
    }
    if (item.children) {
      item.children.forEach(child => {
        if (child.path === path) {
          keys.push(child.key);
          if (!openKeys.value.includes(item.key)) {
            openKeys.value.push(item.key);
          }
        }
      });
    }
  });

  return keys;
});

/**
 * 处理菜单点击
 */
const handleMenuClick = ({ key }) => {
  const findPath = (items) => {
    for (const item of items) {
      if (item.key === key && item.path) {
        return item.path;
      }
      if (item.children) {
        const path = findPath(item.children);
        if (path) return path;
      }
    }
    return null;
  };

  const path = findPath(menuItems);
  if (path) {
    router.push(path);
    emit('update:mobileOpen', false);
  }
};

/**
 * 处理子菜单展开/收起
 */
const handleOpenChange = (keys) => {
  openKeys.value = keys;
};

/**
 * 关闭移动端菜单
 */
const closeMobileMenu = () => {
  emit('update:mobileOpen', false);
};

/**
 * 切换侧边栏折叠状态
 */
const toggleSidebar = () => {
  emit('toggle');
};
</script>

<template>
  <aside
    class="sidebar"
    :class="{
      'sidebar--collapsed': collapsed && !mobileOpen,
      'sidebar--mobile-open': mobileOpen
    }"
  >
    <!-- Logo区域 -->
    <div class="sidebar__header">
      <div
        class="sidebar__logo"
        @click="router.push('/')"
      >
        <div class="sidebar__logo-icon">
          <ExperimentOutlined />
        </div>
        <transition name="fade">
          <span
            v-if="!collapsed || mobileOpen"
            class="sidebar__logo-text"
          >
            CAUC-SEP
          </span>
        </transition>
      </div>
      
      <!-- 移动端关闭按钮 -->
      <button
        v-if="mobileOpen"
        class="sidebar__close-btn"
        @click="closeMobileMenu"
      >
        <CloseOutlined />
      </button>
    </div>

    <!-- 导航菜单 -->
    <nav class="sidebar__nav">
      <a-menu
        :selected-keys="selectedKeys"
        :open-keys="openKeys"
        :inline-collapsed="collapsed && !mobileOpen"
        mode="inline"
        theme="dark"
        class="sidebar__menu"
        @click="handleMenuClick"
        @open-change="handleOpenChange"
      >
        <template
          v-for="item in menuItems"
          :key="item.key"
        >
          <!-- 有子菜单的项 -->
          <a-sub-menu
            v-if="item.children"
            :key="item.key"
          >
            <template #icon>
              <component :is="item.icon" />
              <span
                v-if="item.badge?.value > 0"
                class="menu-badge"
              >
                {{ item.badge.value > 99 ? '99+' : item.badge.value }}
              </span>
            </template>
            <template #title>
              <span class="menu-title">{{ item.label }}</span>
            </template>
            <a-menu-item
              v-for="child in item.children"
              :key="child.key"
            >
              <template #icon>
                <component :is="child.icon" />
              </template>
              <span class="menu-title">{{ child.label }}</span>
            </a-menu-item>
          </a-sub-menu>

          <!-- 无子菜单的项 -->
          <a-menu-item
            v-else
            :key="item.key"
          >
            <template #icon>
              <component :is="item.icon" />
              <span
                v-if="item.badge?.value > 0"
                class="menu-badge"
              >
                {{ item.badge.value > 99 ? '99+' : item.badge.value }}
              </span>
            </template>
            <span class="menu-title">{{ item.label }}</span>
          </a-menu-item>
        </template>
      </a-menu>
    </nav>

    <!-- 底部信息 -->
    <div class="sidebar__footer">
      <transition name="fade">
        <div
          v-if="!collapsed || mobileOpen"
          class="sidebar__footer-content"
        >
          <div class="sidebar__version">
            <span class="version-label">v3.5.1</span>
            <span class="version-badge">PRO</span>
          </div>
          <div class="sidebar__copyright">
            CAUC-SEP 实验平台
          </div>
        </div>
      </transition>
      
      <!-- 折叠状态下的简化footer -->
      <div
        v-if="collapsed && !mobileOpen"
        class="sidebar__footer-collapsed"
      >
        <span class="version-dot" />
      </div>
      
      <!-- 悬浮折叠按钮 - 位于footer区域 -->
      <div
        v-if="!mobileOpen"
        class="sidebar__collapse-wrapper"
      >
        <button
          class="sidebar__collapse-btn"
          :class="{ 'is-collapsed': collapsed }"
          :title="collapsed ? '展开' : '收起'"
          @click="toggleSidebar"
        >
          <MenuFoldOutlined v-if="!collapsed" />
          <MenuUnfoldOutlined v-else />
        </button>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  width: 260px;
  height: 100vh;
  background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
  display: flex;
  flex-direction: column;
  z-index: 1000;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.2);
}

.sidebar--collapsed {
  width: 80px;
}

.sidebar__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-4) var(--spacing-4);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  height: 72px;
}

.sidebar__logo {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  overflow: hidden;
  cursor: pointer;
  transition: opacity var(--transition-fast);
}

.sidebar__logo:hover {
  opacity: 0.8;
}

.sidebar__logo-icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-primary-500) 0%, var(--color-primary-600) 100%);
  border-radius: var(--radius-xl);
  color: white;
  font-size: 22px;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(0, 119, 255, 0.3);
}

.sidebar__logo-text {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: white;
  white-space: nowrap;
  letter-spacing: 0.5px;
  background: linear-gradient(135deg, #ffffff 0%, #e2e8f0 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.sidebar__close-btn {
  display: none;
  width: 36px;
  height: 36px;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  border-radius: var(--radius-md);
  color: white;
  font-size: 18px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.sidebar__close-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.sidebar__nav {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: var(--spacing-3) 0;
}

.sidebar__nav::-webkit-scrollbar {
  width: 4px;
}

.sidebar__nav::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar__nav::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.15);
  border-radius: var(--radius-full);
}

.sidebar__menu {
  background: transparent !important;
  border-right: none !important;
}

.sidebar__menu :deep(.ant-menu-item),
.sidebar__menu :deep(.ant-menu-submenu-title) {
  color: rgba(255, 255, 255, 0.75);
  margin: var(--spacing-1) var(--spacing-3);
  border-radius: var(--radius-lg);
  transition: all var(--transition-fast);
  height: 44px;
  line-height: 44px;
}

.sidebar__menu :deep(.ant-menu-item:hover),
.sidebar__menu :deep(.ant-menu-submenu-title:hover) {
  color: white;
  background: rgba(255, 255, 255, 0.1);
}

.sidebar__menu :deep(.ant-menu-item-selected) {
  color: white !important;
  background: linear-gradient(135deg, var(--color-primary-500) 0%, var(--color-primary-600) 100%) !important;
  box-shadow: 0 4px 12px rgba(0, 119, 255, 0.35);
}

.sidebar__menu :deep(.ant-menu-submenu-arrow) {
  color: rgba(255, 255, 255, 0.4);
}

.sidebar__menu :deep(.ant-menu-submenu-open) .ant-menu-submenu-arrow {
  color: white;
}

.sidebar__menu :deep(.ant-menu-sub) {
  background: rgba(0, 0, 0, 0.25) !important;
  border-radius: var(--radius-lg);
  margin: 0 var(--spacing-3);
}

.sidebar__menu :deep(.ant-menu-sub .ant-menu-item) {
  margin: var(--spacing-1) 0;
  height: 40px;
  line-height: 40px;
}

.menu-badge {
  position: absolute;
  top: 50%;
  right: 8px;
  transform: translateY(-50%);
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  background: var(--color-error);
  color: white;
  font-size: 11px;
  font-weight: var(--font-weight-semibold);
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
}

.menu-title {
  font-weight: var(--font-weight-medium);
}

.sidebar__footer {
  padding: var(--spacing-4);
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  position: relative;
}

.sidebar__footer-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-2);
}

.sidebar__version {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.version-label {
  font-size: var(--font-size-sm);
  color: rgba(255, 255, 255, 0.5);
  font-weight: var(--font-weight-medium);
}

.version-badge {
  font-size: 10px;
  padding: 2px 6px;
  background: linear-gradient(135deg, var(--color-primary-500) 0%, var(--color-primary-600) 100%);
  color: white;
  border-radius: var(--radius-sm);
  font-weight: var(--font-weight-semibold);
}

.sidebar__copyright {
  font-size: var(--font-size-xs);
  color: rgba(255, 255, 255, 0.35);
  text-align: center;
}

.sidebar__footer-collapsed {
  display: flex;
  justify-content: center;
  align-items: center;
}

.version-dot {
  width: 8px;
  height: 8px;
  background: var(--color-primary-500);
  border-radius: 50%;
  box-shadow: 0 0 8px var(--color-primary-500);
}

/* 悬浮折叠按钮容器 */
.sidebar__collapse-wrapper {
  position: absolute;
  top: 50%;
  right: -16px;
  transform: translateY(-50%);
  opacity: 0;
  transition: opacity 0.2s ease;
  z-index: 1001;
}

/* 鼠标悬停sidebar时显示折叠按钮 */
.sidebar:hover .sidebar__collapse-wrapper {
  opacity: 1;
}

.sidebar__collapse-btn {
  width: 32px;
  height: 32px;
  background: var(--color-primary-500);
  border: 2px solid white;
  border-radius: 50%;
  color: white;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  transition: all var(--transition-fast);
}

.sidebar__collapse-btn:hover {
  background: var(--color-primary-600);
  transform: scale(1.1);
  box-shadow: 0 4px 12px rgba(0, 119, 255, 0.4);
}

.sidebar__collapse-btn.is-collapsed {
  background: var(--color-neutral-600);
}

.sidebar__collapse-btn.is-collapsed:hover {
  background: var(--color-neutral-500);
}

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .sidebar {
    transform: translateX(-100%);
    width: 280px;
  }

  .sidebar--mobile-open {
    transform: translateX(0);
  }

  .sidebar__close-btn {
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .sidebar__collapse-wrapper {
    display: none;
  }

  .sidebar__header {
    padding: var(--spacing-4);
  }
}

@media (max-width: 480px) {
  .sidebar {
    width: 100%;
  }
}
</style>
