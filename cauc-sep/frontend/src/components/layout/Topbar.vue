<template>
  <header class="topbar">
    <!-- 左侧：当前模块标题 -->
    <div class="topbar__left">
      <div class="topbar__title-group">
        <h1 class="topbar__title">
          {{ activeModule?.name || '实验平台' }}
        </h1>
        <transition name="subtitle-fade">
          <span v-if="activeChild" class="topbar__subtitle">
            <span class="topbar__subtitle-divider"></span>
            {{ activeChild.name }}
          </span>
        </transition>
      </div>
    </div>

    <!-- 中间：子功能标签页 -->
    <nav v-if="activeModule?.children?.length" class="topbar__tabs">
      <div class="topbar__tabs-wrapper">
        <div
          v-for="child in activeModule.children"
          :key="child.id"
          class="topbar__tab"
          :class="{ 'topbar__tab--active': activeChildId === child.id }"
          @click="handleTabClick(child)"
          role="tab"
          :aria-selected="activeChildId === child.id"
        >
          <div class="topbar__tab-icon-wrapper">
            <el-icon class="topbar__tab-icon">
              <component :is="child.icon" />
            </el-icon>
          </div>
          <span class="topbar__tab-label">{{ child.name }}</span>
          <div class="topbar__tab-indicator"></div>
        </div>
      </div>
    </nav>

    <!-- 右侧：操作按钮区域 -->
    <div class="topbar__right">
      <!-- 快速操作 -->
      <div class="topbar__actions">
        <el-tooltip content="刷新数据" placement="bottom" :show-after="500">
          <button class="topbar__action-btn" @click="handleRefresh">
            <el-icon><Refresh /></el-icon>
          </button>
        </el-tooltip>
        
        <el-tooltip content="导出数据" placement="bottom" :show-after="500">
          <button class="topbar__action-btn" @click="handleExport">
            <el-icon><Download /></el-icon>
          </button>
        </el-tooltip>
        
        <el-tooltip content="全屏显示" placement="bottom" :show-after="500">
          <button class="topbar__action-btn" @click="handleFullscreen">
            <el-icon><FullScreen /></el-icon>
          </button>
        </el-tooltip>
      </div>

      <!-- 用户信息 -->
      <el-dropdown trigger="click" @command="handleUserCommand" class="topbar__user-dropdown">
        <div class="topbar__user">
          <div class="topbar__avatar-wrapper">
            <el-avatar :size="32" class="topbar__avatar">
              {{ userStore.avatarText }}
            </el-avatar>
            <div class="topbar__avatar-ring"></div>
          </div>
          <div class="topbar__user-info">
            <span class="topbar__username">{{ userStore.currentUser?.username || '实验员' }}</span>
            <span v-if="userStore.currentUser?.role" class="topbar__role-badge">
              {{ userStore.roleLabel }}
            </span>
          </div>
          <el-icon class="topbar__dropdown-icon">
            <ArrowDown />
          </el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">
              <el-icon><User /></el-icon>
              <span>个人中心</span>
            </el-dropdown-item>
            <el-dropdown-item command="settings">
              <el-icon><Setting /></el-icon>
              <span>系统设置</span>
            </el-dropdown-item>
            <el-dropdown-item divided command="logout">
              <el-icon><SwitchButton /></el-icon>
              <span>退出登录</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<script setup>
/**
 * @file Topbar.vue
 * @path src/components/layout/
 * @description 顶部工具栏组件，显示模块标题、子功能标签页和操作按钮
 * @author Agent
 * @date 2024-03-07
 */

import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useLayoutStore } from '@/stores/layout'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import {
  Refresh,
  Download,
  FullScreen,
  User,
  Setting,
  SwitchButton,
  ArrowDown
} from '@element-plus/icons-vue'

// ==================== 组合式函数 ====================

const router = useRouter()
const layoutStore = useLayoutStore()
const userStore = useUserStore()

// ==================== 响应式状态 ====================

/** 当前激活的模块 */
const activeModule = computed(() => layoutStore.activeModule)

/** 当前激活的子功能 */
const activeChild = computed(() => layoutStore.activeChild)

/** 当前激活的子功能ID */
const activeChildId = computed(() => layoutStore.activeChildId)

// ==================== 方法 ====================

/**
 * 处理标签页点击
 * 
 * @param {Object} child - 子功能配置对象
 */
function handleTabClick(child) {
  layoutStore.setActiveChild(child.id)
  router.push(child.path)
}

/**
 * 处理刷新操作
 */
function handleRefresh() {
  ElMessage.success('数据已刷新')
  // 触发页面刷新事件
  window.dispatchEvent(new CustomEvent('layout-refresh'))
}

/**
 * 处理导出操作
 */
function handleExport() {
  ElMessage.info('导出功能开发中...')
}

/**
 * 处理全屏操作
 */
function handleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
  } else {
    document.exitFullscreen()
  }
}

/**
 * 处理用户菜单命令
 * 
 * @param {string} command - 命令标识
 */
function handleUserCommand(command) {
  switch (command) {
    case 'profile':
      router.push('/settings/profile')
      break
    case 'settings':
      router.push('/settings/config')
      break
    case 'logout':
      handleLogout()
      break
  }
}

/**
 * 处理登出
 */
async function handleLogout() {
  try {
    await userStore.logout()
    ElMessage.success('已退出登录')
    router.push('/')
  } catch (error) {
    console.error('[Topbar] Logout error:', error)
    ElMessage.error('退出登录失败')
  }
}
</script>

<style scoped lang="scss">
.topbar {
  position: fixed;
  top: 0;
  left: var(--sidebar-width, 0);
  right: 0;
  height: 56px;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.98) 0%,
    rgba(248, 250, 252, 0.96) 50%,
    rgba(255, 255, 255, 0.98) 100%
  );
  border-bottom: 1px solid var(--color-border-primary);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--spacing-5);
  z-index: var(--z-index-sticky);
  box-shadow: 
    0 1px 4px rgba(0, 0, 0, 0.04),
    0 2px 8px rgba(0, 0, 0, 0.02),
    inset 0 -1px 0 rgba(0, 0, 0, 0.03);
  transition: left var(--transition-base) linear;
  backdrop-filter: blur(24px);
  
  // 底部渐变光效
  &::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(
      90deg,
      transparent 0%,
      rgba(24, 144, 255, 0.2) 20%,
      rgba(20, 184, 166, 0.3) 50%,
      rgba(24, 144, 255, 0.2) 80%,
      transparent 100%
    );
    animation: topbar-glow 4s ease-in-out infinite;
  }
}

@keyframes topbar-glow {
  0%, 100% {
    opacity: 0.3;
    transform: scaleX(0.9);
  }
  50% {
    opacity: 0.7;
    transform: scaleX(1);
  }
}

// 左侧标题区域
.topbar__left {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  min-width: 220px;
}

.topbar__title-group {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.topbar__title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  margin: 0;
  letter-spacing: 0.02em;
  line-height: 1.2;
  background: linear-gradient(
    135deg,
    var(--color-primary-700) 0%,
    var(--color-primary-600) 40%,
    var(--color-accent-600) 100%
  );
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  position: relative;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.1));
}

.topbar__subtitle {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
  white-space: nowrap;
}

.topbar__subtitle-divider {
  width: 2px;
  height: 16px;
  background: linear-gradient(
    180deg,
    var(--color-primary-400) 0%,
    var(--color-primary-500) 100%
  );
  border-radius: var(--radius-full);
}

// 子标题过渡动画
.subtitle-fade-enter-active,
.subtitle-fade-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.subtitle-fade-enter-from {
  opacity: 0;
  transform: translateX(-10px);
}

.subtitle-fade-leave-to {
  opacity: 0;
  transform: translateX(10px);
}

// 中间标签页区域
.topbar__tabs {
  flex: 1;
  display: flex;
  align-items: center;
  padding: 0 var(--spacing-4);
}

.topbar__tabs-wrapper {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  padding: var(--spacing-1);
  background: linear-gradient(
    135deg,
    var(--color-surface-secondary) 0%,
    rgba(248, 250, 252, 0.8) 100%
  );
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  backdrop-filter: blur(10px);
  overflow-x: auto;
  scrollbar-width: none;
  
  &::-webkit-scrollbar {
    display: none;
  }
}

.topbar__tab {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-4);
  border-radius: var(--radius-base);
  cursor: pointer;
  transition: all var(--transition-base) var(--ease-in-out);
  color: var(--color-text-secondary);
  white-space: nowrap;
  background: transparent;
  border: none;
  flex-shrink: 0;
  
  &:hover {
    color: var(--color-text-primary);
    background: linear-gradient(
      135deg,
      var(--color-surface-primary) 0%,
      rgba(255, 255, 255, 0.95) 100%
    );
    transform: translateY(-2px);
    box-shadow: 
      0 4px 12px rgba(0, 0, 0, 0.08),
      0 2px 6px rgba(0, 0, 0, 0.04);
    
    .topbar__tab-icon-wrapper {
      background: linear-gradient(
        135deg,
        rgba(59, 130, 246, 0.15) 0%,
        rgba(59, 130, 246, 0.08) 100%
      );
      transform: scale(1.08) rotate(-3deg);
    }
  }
  
  &--active {
    background: linear-gradient(
      135deg,
      var(--color-surface-primary) 0%,
      rgba(255, 255, 255, 1) 100%
    );
    color: var(--color-primary-600);
    font-weight: var(--font-weight-semibold);
    box-shadow: 
      0 4px 16px rgba(0, 0, 0, 0.08),
      0 2px 8px rgba(0, 0, 0, 0.04),
      inset 0 1px 0 rgba(255, 255, 255, 0.9);
    transform: translateY(-1px);
    
    .topbar__tab-icon-wrapper {
      background: linear-gradient(
        135deg,
        rgba(24, 144, 255, 0.2) 0%,
        rgba(24, 144, 255, 0.1) 100%
      );
      box-shadow: 0 2px 8px rgba(24, 144, 255, 0.2);
    }
    
    .topbar__tab-icon {
      color: var(--color-primary-600);
      transform: scale(1.15);
    }
    
    .topbar__tab-indicator {
      opacity: 1;
      transform: translateX(-50%) scaleX(1);
    }
  }
}

.topbar__tab-icon-wrapper {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  background: rgba(0, 0, 0, 0.04);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.topbar__tab-icon {
  font-size: 14px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.topbar__tab-label {
  font-size: var(--font-size-sm);
  letter-spacing: 0.01em;
  font-weight: var(--font-weight-medium);
}

.topbar__tab-indicator {
  position: absolute;
  bottom: -1px;
  left: 50%;
  transform: translateX(-50%) scaleX(0);
  width: 60%;
  height: 2px;
  background: linear-gradient(
    90deg,
    var(--color-primary-400) 0%,
    var(--color-primary-500) 100%
  );
  border-radius: var(--radius-full);
  opacity: 0;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 0 8px rgba(24, 144, 255, 0.4);
}

// 右侧操作区域
.topbar__right {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  min-width: 220px;
  justify-content: flex-end;
}

.topbar__actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2);
  background: linear-gradient(
    135deg,
    var(--color-surface-secondary) 0%,
    rgba(248, 250, 252, 0.8) 100%
  );
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  backdrop-filter: blur(10px);
}

.topbar__action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-base);
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-base) var(--ease-in-out);
  position: relative;
  overflow: hidden;
  
  // 涟漪效果
  &::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 0;
    height: 0;
    border-radius: 50%;
    background: radial-gradient(
      circle,
      rgba(59, 130, 246, 0.25) 0%,
      rgba(59, 130, 246, 0.1) 50%,
      transparent 100%
    );
    transform: translate(-50%, -50%);
    transition: width 0.4s ease, height 0.4s ease;
  }
  
  &:hover {
    background: linear-gradient(
      135deg,
      var(--color-surface-primary) 0%,
      rgba(255, 255, 255, 0.95) 100%
    );
    color: var(--color-primary-600);
    transform: translateY(-3px) scale(1.05);
    box-shadow: 
      0 6px 16px rgba(0, 0, 0, 0.1),
      0 3px 8px rgba(0, 0, 0, 0.06);
    
    &::after {
      width: 150%;
      height: 150%;
    }
  }
  
  &:active {
    transform: translateY(-1px) scale(1);
    box-shadow: 
      0 2px 8px rgba(0, 0, 0, 0.08),
      0 1px 4px rgba(0, 0, 0, 0.04);
  }
  
  .el-icon {
    font-size: 16px;
    position: relative;
    z-index: 1;
    transition: transform var(--transition-base) var(--ease-in-out);
  }
  
  &:hover .el-icon {
    transform: rotate(15deg);
  }
}

// 用户信息
.topbar__user-dropdown {
  cursor: pointer;
}

.topbar__user {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-2) var(--spacing-3);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--transition-base) var(--ease-in-out);
  background: linear-gradient(
    135deg,
    var(--color-surface-secondary) 0%,
    rgba(248, 250, 252, 0.85) 100%
  );
  border: 1px solid var(--color-border-primary);
  backdrop-filter: blur(12px);
  min-height: 40px;
  position: relative;
  overflow: hidden;
  
  // 背景光效
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(
      135deg,
      transparent 0%,
      rgba(255, 255, 255, 0.3) 50%,
      transparent 100%
    );
    opacity: 0;
    transition: opacity var(--transition-base) var(--ease-in-out);
  }
  
  &:hover {
    background: linear-gradient(
      135deg,
      var(--color-surface-primary) 0%,
      rgba(255, 255, 255, 0.95) 100%
    );
    border-color: var(--color-primary-300);
    box-shadow: 
      0 6px 16px rgba(0, 0, 0, 0.1),
      0 3px 8px rgba(0, 0, 0, 0.06);
    transform: translateY(-2px);
    
    &::before {
      opacity: 1;
    }
    
    .topbar__dropdown-icon {
      transform: rotate(180deg);
    }
    
    .topbar__avatar-ring {
      opacity: 1;
      transform: scale(1.15);
    }
  }
}

.topbar__avatar-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.topbar__avatar {
  background: linear-gradient(
    135deg,
    var(--color-primary-500) 0%,
    var(--color-accent-500) 100%
  );
  color: var(--color-text-inverse);
  font-weight: var(--font-weight-semibold);
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  position: relative;
  z-index: 1;
  border-radius: var(--radius-full);
}

.topbar__avatar-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 100%;
  height: 100%;
  transform: translate(-50%, -50%) scale(1);
  border-radius: var(--radius-full);
  border: 2px solid var(--color-primary-400);
  opacity: 0;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  pointer-events: none;
}

.topbar__user-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.topbar__username {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
}

.topbar__role-badge {
  display: inline-flex;
  align-items: center;
  padding: 1px var(--spacing-2);
  font-size: 10px;
  font-weight: var(--font-weight-semibold);
  color: var(--color-primary-700);
  background: linear-gradient(
    135deg,
    var(--color-primary-50) 0%,
    rgba(59, 130, 246, 0.08) 100%
  );
  border-radius: var(--radius-full);
  white-space: nowrap;
  letter-spacing: 0.02em;
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.topbar__dropdown-icon {
  font-size: 12px;
  color: var(--color-text-secondary);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  margin-left: auto;
}
</style>
