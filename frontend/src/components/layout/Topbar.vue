/**
 * @file Topbar.vue
 * @path src/components/layout/
 * @description 顶部导航栏组件 - 优化版
 * @author Agent
 * @date 2024-03-15
 * @version 3.5.1
 */

<script setup>
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  MenuOutlined,
  BellOutlined,
  UserOutlined,
  SettingOutlined,
  LogoutOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined
} from '@ant-design/icons-vue';
import { wsClient } from '../../api/websocket';

const props = defineProps({
  title: {
    type: String,
    default: 'CAUC-SEP'
  },
  sidebarCollapsed: {
    type: Boolean,
    default: false
  },
  connectionStatus: {
    type: String,
    default: 'connected'
  }
});

const emit = defineEmits(['toggleSidebar', 'toggleMobileMenu']);

const router = useRouter();
const { t } = useI18n();

const isFullscreen = ref(false);
const notificationCount = ref(0);

/**
 * 连接状态显示配置
 */
const connectionStatusConfig = computed(() => {
  const configs = {
    connected: { 
      text: t('status.connected'), 
      type: 'success', 
      icon: CheckCircleOutlined,
      class: 'topbar__status--success'
    },
    disconnected: { 
      text: t('status.disconnected'), 
      type: 'error', 
      icon: CloseCircleOutlined,
      class: 'topbar__status--error'
    },
    reconnecting: { 
      text: t('status.reconnecting'), 
      type: 'warning', 
      icon: LoadingOutlined,
      class: 'topbar__status--warning'
    },
    connecting: { 
      text: t('status.connecting'), 
      type: 'default', 
      icon: LoadingOutlined,
      class: 'topbar__status--default'
    }
  };
  return configs[props.connectionStatus] || configs.connecting;
});

/**
 * 切换全屏
 */
const toggleFullscreen = () => {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(() => {});
    isFullscreen.value = true;
  } else {
    document.exitFullscreen().catch(() => {});
    isFullscreen.value = false;
  }
};

/**
 * 跳转到设置页面
 */
const goToSettings = () => {
  router.push('/settings/profile');
};

/**
 * 跳转到个人资料
 */
const goToProfile = () => {
  router.push('/settings/profile');
};

/**
 * 处理登出
 */
const handleLogout = () => {
  wsClient.disconnect();
  localStorage.removeItem('token');
  router.push('/login');
};

/**
 * 用户菜单项
 */
const userMenuItems = [
  {
    key: 'profile',
    icon: UserOutlined,
    label: t('user.profile'),
    onClick: goToProfile
  },
  {
    key: 'settings',
    icon: SettingOutlined,
    label: t('user.settings'),
    onClick: goToSettings
  },
  { type: 'divider' },
  {
    key: 'logout',
    icon: LogoutOutlined,
    label: t('user.logout'),
    danger: true,
    onClick: handleLogout
  }
];
</script>

<template>
  <header class="topbar">
    <div class="topbar__left">
      <!-- 页面标题 - 移至左侧 -->
      <h1 class="topbar__title">
        {{ title }}
      </h1>
    </div>

    <div class="topbar__center">
      <!-- 桌面端侧边栏切换按钮 - 移至中间 -->
      <button
        class="topbar__toggle-btn"
        :class="{ 'is-collapsed': sidebarCollapsed }"
        :title="sidebarCollapsed ? t('action.expandSidebar') : t('action.collapseSidebar')"
        @click="$emit('toggleSidebar')"
      >
        <MenuFoldOutlined v-if="!sidebarCollapsed" />
        <MenuUnfoldOutlined v-else />
      </button>

      <!-- 移动端菜单按钮 -->
      <button
        class="topbar__toggle-btn hide-desktop"
        :title="t('action.openMenu')"
        @click="$emit('toggleMobileMenu')"
      >
        <MenuOutlined />
      </button>
    </div>

    <div class="topbar__right">
      <!-- 连接状态指示器 - 汉字在左，符号在右 -->
      <div
        class="topbar__status"
        :class="connectionStatusConfig.class"
      >
        <span class="topbar__status-text">{{ connectionStatusConfig.text }}</span>
        <component
          :is="connectionStatusConfig.icon"
          class="topbar__status-icon"
        />
      </div>

      <!-- 全屏切换 -->
      <button
        class="topbar__action-btn"
        :title="isFullscreen ? t('action.exitFullscreen') : t('action.fullscreen')"
        @click="toggleFullscreen"
      >
        <FullscreenExitOutlined v-if="isFullscreen" />
        <FullscreenOutlined v-else />
      </button>

      <!-- 通知 -->
      <a-dropdown :trigger="['click']">
        <button class="topbar__action-btn topbar__action-btn--badge">
          <BellOutlined />
          <span
            v-if="notificationCount > 0"
            class="topbar__badge"
          >
            {{ notificationCount > 99 ? '99+' : notificationCount }}
          </span>
        </button>
        <template #overlay>
          <a-menu class="topbar__notification-menu">
            <a-menu-item disabled>
              <span class="topbar__notification-empty">{{ t('notification.empty') }}</span>
            </a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>

      <!-- 用户菜单 -->
      <a-dropdown :trigger="['click']">
        <button class="topbar__user-btn">
          <a-avatar
            :size="32"
            class="topbar__avatar"
          >
            <template #icon>
              <UserOutlined />
            </template>
          </a-avatar>
          <span class="topbar__username hide-mobile">{{ t('user.admin') }}</span>
        </button>
        <template #overlay>
          <a-menu>
            <template
              v-for="item in userMenuItems"
              :key="item.key"
            >
              <a-menu-divider v-if="item.type === 'divider'" />
              <a-menu-item
                v-else
                :danger="item.danger"
                @click="item.onClick"
              >
                <template #icon>
                  <component :is="item.icon" />
                </template>
                {{ item.label }}
              </a-menu-item>
            </template>
          </a-menu>
        </template>
      </a-dropdown>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
  padding: 0 var(--spacing-5);
  background: var(--color-surface-primary);
  border-bottom: 1px solid var(--color-border-primary);
  box-shadow: var(--shadow-sm);
  position: sticky;
  top: 0;
  z-index: var(--z-index-sticky);
}

.topbar__left {
  display: flex;
  align-items: center;
  flex: 1;
}

.topbar__center {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-2);
}

.topbar__right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--spacing-2);
  flex: 1;
}

.topbar__toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  font-size: 18px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.topbar__toggle-btn:hover {
  background: var(--color-interactive-hover);
  color: var(--color-primary-500);
  border-color: var(--color-primary-300);
}

.topbar__toggle-btn.is-collapsed {
  background: var(--color-primary-50);
  border-color: var(--color-primary-200);
  color: var(--color-primary-600);
}

.topbar__title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  margin: 0;
  background: linear-gradient(135deg, var(--color-primary-600) 0%, var(--color-primary-500) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.topbar__status {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-1) var(--spacing-3);
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  transition: all var(--transition-fast);
  cursor: default;
}

.topbar__status--success {
  background: var(--color-success-light);
  color: var(--color-success-dark);
}

.topbar__status--error {
  background: var(--color-error-light);
  color: var(--color-error-dark);
}

.topbar__status--warning {
  background: var(--color-warning-light);
  color: var(--color-warning-dark);
}

.topbar__status--default {
  background: var(--color-neutral-100);
  color: var(--color-neutral-500);
}

.topbar__status-icon {
  font-size: 14px;
}

.topbar__status-icon:global(.anticon-loading) {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.topbar__action-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-1);
  width: 40px;
  height: 40px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  font-size: 18px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.topbar__action-btn:hover {
  background: var(--color-interactive-hover);
  color: var(--color-primary-500);
  border-color: var(--color-border-primary);
}

.topbar__action-btn--badge {
  position: relative;
}

.topbar__badge {
  position: absolute;
  top: 4px;
  right: 4px;
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

.topbar__user-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-1) var(--spacing-2) var(--spacing-1) var(--spacing-1);
  background: transparent;
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.topbar__user-btn:hover {
  border-color: var(--color-primary-300);
  background: var(--color-interactive-hover);
}

.topbar__avatar {
  background: linear-gradient(135deg, var(--color-primary-500) 0%, var(--color-primary-600) 100%);
}

.topbar__username {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  padding-right: var(--spacing-2);
}

.topbar__notification-menu {
  min-width: 280px;
}

.topbar__notification-empty {
  color: var(--color-text-tertiary);
  text-align: center;
  display: block;
  padding: var(--spacing-4);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .topbar {
    padding: 0 var(--spacing-3);
  }

  .topbar__title {
    font-size: var(--font-size-lg);
  }

  .topbar__status {
    padding: var(--spacing-1);
  }

  .topbar__status-text {
    display: none;
  }

  .topbar__action-btn {
    width: 36px;
    height: 36px;
    font-size: 16px;
  }

  .topbar__user-btn {
    padding: var(--spacing-1);
  }
}

@media (max-width: 480px) {
  .topbar__right {
    gap: var(--spacing-1);
  }

  .topbar__action-btn {
    width: 32px;
    height: 32px;
    font-size: 14px;
  }

  .topbar__toggle-btn {
    width: 36px;
    height: 36px;
    font-size: 16px;
  }
}

/* 隐藏类 */
.hide-mobile {
  display: inline;
}

.hide-desktop {
  display: none;
}

@media (max-width: 768px) {
  .hide-mobile {
    display: none;
  }

  .hide-desktop {
    display: flex;
  }
}
</style>
