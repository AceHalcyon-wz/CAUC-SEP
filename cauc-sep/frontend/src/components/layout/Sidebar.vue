<template>
  <aside 
    class="sidebar"
    :class="{ 
      'sidebar--collapsed': isCollapsed,
      'sidebar--hover': isHovering && isCollapsed
    }"
    :style="{ 
      width: `${currentWidth}px`,
      '--sidebar-width': `${currentWidth}px`
    }"
    @mouseenter="handleMouseEnter"
    @mouseleave="handleMouseLeave"
  >
    <!-- Logo区域 -->
    <div class="sidebar__header">
      <div class="sidebar__logo-wrapper">
        <el-icon class="sidebar__logo">
          <Cpu />
        </el-icon>
        <!-- Logo脉冲光晕 -->
        <div class="sidebar__logo-glow" />
      </div>
      <transition name="slide-fade">
        <div
          v-show="!isCollapsed || isHovering"
          class="sidebar__title-wrapper"
        >
          <span class="sidebar__title">自旋电子</span>
          <span class="sidebar__subtitle">实验平台</span>
        </div>
      </transition>
    </div>

    <!-- 主导航图标 -->
    <nav class="sidebar__nav">
      <div
        v-for="(module, index) in modules"
        :key="module.id"
        class="sidebar__item"
        :class="{ 
          'sidebar__item--active': activeModuleId === module.id,
          'sidebar__item--first': index === 0
        }"
        @click="handleModuleClick(module)"
      >
        <el-tooltip
          :content="module.name"
          placement="right"
          :disabled="!isCollapsed || isHovering"
          :show-after="300"
        >
          <div class="sidebar__icon-wrapper">
            <el-icon class="sidebar__icon">
              <component :is="module.icon" />
            </el-icon>
            <!-- 激活状态光晕效果 -->
            <div
              v-if="activeModuleId === module.id"
              class="sidebar__icon-glow"
            />
            <!-- 悬停光晕 -->
            <div class="sidebar__icon-hover-glow" />
          </div>
        </el-tooltip>
        
        <transition name="slide-fade">
          <span
            v-show="!isCollapsed || isHovering"
            class="sidebar__label"
          >
            {{ module.name }}
          </span>
        </transition>

        <!-- 激活状态指示器 -->
        <transition name="indicator-fade">
          <div
            v-if="activeModuleId === module.id"
            class="sidebar__active-indicator"
          >
            <div class="sidebar__active-indicator-bar" />
          </div>
        </transition>

        <!-- 涟漪效果容器 -->
        <div class="sidebar__ripple-container" />
      </div>
    </nav>

    <!-- 底部折叠按钮 -->
    <div class="sidebar__footer">
      <el-button
        class="sidebar__toggle"
        :icon="isCollapsed ? 'Expand' : 'Fold'"
        circle
        size="small"
        @click="toggleSidebar"
      />
      <transition name="slide-fade">
        <span
          v-show="!isCollapsed"
          class="sidebar__toggle-label"
        >
          {{ isCollapsed ? '展开' : '收起' }}
        </span>
      </transition>
    </div>
  </aside>
</template>

<script setup>
/**
 * @file Sidebar.vue
 * @path src/components/layout/
 * @description 左侧导航栏组件，支持折叠/展开状态、悬停展开
 * @author Agent
 * @date 2024-03-07
 */

import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useLayoutStore } from '@/stores/layout'
import {
  Setting,
  Monitor,
  DataAnalysis,
  Tools,
  Cpu,
  Expand,
  Fold
} from '@element-plus/icons-vue'

// ==================== 组合式函数 ====================

const router = useRouter()
const layoutStore = useLayoutStore()

// ==================== 响应式状态 ====================

/** 侧边栏是否折叠 */
const isCollapsed = computed(() => layoutStore.isSidebarCollapsed)

/** 悬停状态（用于折叠时的悬停展开） */
const isHovering = ref(false)

/** 悬停展开延迟定时器 */
let hoverTimer = null

/** 当前宽度（用于模板绑定） */
const currentWidth = computed(() => {
  // 悬停展开状态
  if (isHovering.value && isCollapsed.value) return 240
  
  // 桌面端：根据折叠状态
  return isCollapsed.value ? 64 : 240
})

/** 模块列表 */
const modules = computed(() => layoutStore.modules)

/** 当前激活的模块ID */
const activeModuleId = computed(() => layoutStore.activeModuleId)

// ==================== 方法 ====================

/**
 * 处理模块点击
 * 
 * @param {Object} module - 模块配置对象
 */
function handleModuleClick(module) {
  // 添加涟漪效果
  addRippleEffect(event)
  
  // 设置激活模块
  layoutStore.setActiveModule(module.id)
  
  // 导航到该模块的第一个子功能
  if (module.children && module.children.length > 0) {
    router.push(module.children[0].path)
  }
}

/**
 * 切换侧边栏折叠状态
 */
function toggleSidebar() {
  layoutStore.toggleSidebar()
}

/**
 * 鼠标进入事件处理
 * 折叠状态下悬停展开侧边栏
 */
function handleMouseEnter() {
  if (isCollapsed.value) {
    // 延迟 150ms 展开，避免误触
    hoverTimer = setTimeout(() => {
      isHovering.value = true
    }, 150)
  }
}

/**
 * 鼠标离开事件处理
 * 折叠状态下悬停收起侧边栏
 */
function handleMouseLeave() {
  // 清除定时器
  if (hoverTimer) {
    clearTimeout(hoverTimer)
    hoverTimer = null
  }
  
  // 重置悬停状态
  isHovering.value = false
}

/**
 * 添加涟漪效果
 * 
 * @param {Event} event - 点击事件
 */
function addRippleEffect(event) {
  const item = event.currentTarget
  const rippleContainer = item.querySelector('.sidebar__ripple-container')
  
  if (!rippleContainer) return
  
  const rect = item.getBoundingClientRect()
  const size = Math.max(rect.width, rect.height)
  const x = event.clientX - rect.left - size / 2
  const y = event.clientY - rect.top - size / 2
  
  const ripple = document.createElement('div')
  ripple.className = 'sidebar__ripple'
  ripple.style.width = ripple.style.height = `${size}px`
  ripple.style.left = `${x}px`
  ripple.style.top = `${y}px`
  
  rippleContainer.appendChild(ripple)
  
  // 动画结束后移除元素
  ripple.addEventListener('animationend', () => {
    ripple.remove()
  })
}
</script>

<style scoped lang="scss">
// ==================== 侧边栏主容器 ====================
.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  height: 100vh;
  background: linear-gradient(
    180deg,
    var(--color-primary-700) 0%,
    var(--color-primary-800) 50%,
    var(--color-primary-900) 100%
  );
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  flex-direction: column;
  transition: 
    width var(--transition-slow) var(--ease-in-out), 
    transform var(--transition-slow) var(--ease-in-out),
    box-shadow var(--transition-slow) var(--ease-in-out);
  z-index: var(--z-index-fixed);
  box-shadow: 
    2px 0 8px rgba(0, 0, 0, 0.1),
    4px 0 16px rgba(0, 0, 0, 0.05),
    inset -1px 0 0 rgba(255, 255, 255, 0.05);
  overflow: hidden;
  
  // 背景动态纹理
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: 
      radial-gradient(circle at 20% 30%, rgba(20, 184, 166, 0.08) 0%, transparent 50%),
      radial-gradient(circle at 80% 70%, rgba(59, 130, 246, 0.06) 0%, transparent 50%);
    pointer-events: none;
    animation: sidebar-shimmer 15s ease-in-out infinite;
  }
  
  // 折叠状态
  &--collapsed {
    --sidebar-width: 64px;
    
    .sidebar__header {
      justify-content: center;
      padding: 0;
    }
    
    .sidebar__nav {
      align-items: center;
    }
    
    .sidebar__item {
      justify-content: center;
      padding: 0;
    }
    
    .sidebar__footer {
      justify-content: center;
    }
  }
  
  // 悬停展开状态
  &--hover {
    --sidebar-width: 240px;
    
    box-shadow: 
      4px 0 16px rgba(0, 0, 0, 0.15),
      8px 0 32px rgba(0, 0, 0, 0.1),
      inset -1px 0 0 rgba(255, 255, 255, 0.1);
    
    .sidebar__header {
      justify-content: flex-start;
      padding: 0 var(--spacing-4);
    }
    
    .sidebar__nav {
      align-items: stretch;
    }
    
    .sidebar__item {
      justify-content: flex-start;
      padding: 0 var(--spacing-4);
    }
  }
}

@keyframes sidebar-shimmer {
  0%, 100% {
    opacity: 0.5;
    transform: scale(1);
  }
  50% {
    opacity: 0.8;
    transform: scale(1.05);
  }
}

// ==================== Logo区域 ====================
.sidebar__header {
  height: 72px;
  display: flex;
  align-items: center;
  padding: 0 var(--spacing-4);
  gap: var(--spacing-3);
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
  background: linear-gradient(
    135deg,
    var(--color-accent-600) 0%,
    var(--color-accent-700) 50%,
    var(--color-accent-800) 100%
  );
  flex-shrink: 0;
  transition: all var(--transition-slow) var(--ease-in-out);
  position: relative;
  overflow: hidden;
  box-shadow: 
    0 2px 8px rgba(0, 0, 0, 0.15),
    inset 0 -1px 0 rgba(255, 255, 255, 0.1);
  
  // 背景动态光效
  &::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(
      circle,
      rgba(255, 255, 255, 0.15) 0%,
      transparent 70%
    );
    animation: header-shine 10s ease-in-out infinite;
    pointer-events: none;
  }
  
  // 底部光晕
  &::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(
      90deg,
      transparent 0%,
      rgba(20, 184, 166, 0.6) 50%,
      transparent 100%
    );
    animation: header-glow 3s ease-in-out infinite;
  }
}

@keyframes header-shine {
  0%, 100% {
    transform: translate(0, 0) rotate(0deg);
    opacity: 0.4;
  }
  50% {
    transform: translate(30%, 30%) rotate(180deg);
    opacity: 0.7;
  }
}

@keyframes header-glow {
  0%, 100% {
    opacity: 0.3;
    transform: scaleX(0.8);
  }
  50% {
    opacity: 0.8;
    transform: scaleX(1);
  }
}

.sidebar__logo-wrapper {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.2) 0%,
    rgba(255, 255, 255, 0.1) 100%
  );
  border-radius: var(--radius-lg);
  flex-shrink: 0;
  transition: all var(--transition-slow) var(--ease-in-out);
  position: relative;
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.25);
  box-shadow: 
    0 4px 12px rgba(0, 0, 0, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
  
  &:hover {
    transform: scale(1.1) rotate(8deg);
    background: linear-gradient(
      135deg,
      rgba(255, 255, 255, 0.25) 0%,
      rgba(255, 255, 255, 0.15) 100%
    );
    box-shadow: 
      0 8px 24px rgba(0, 0, 0, 0.25),
      0 0 20px rgba(20, 184, 166, 0.3),
      inset 0 1px 0 rgba(255, 255, 255, 0.3);
  }
}

.sidebar__logo {
  font-size: 24px;
  color: var(--color-text-inverse);
  position: relative;
  z-index: 1;
  animation: logo-float 4s ease-in-out infinite;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
}

@keyframes logo-float {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
  }
  25% {
    transform: translateY(-3px) rotate(-2deg);
  }
  50% {
    transform: translateY(-1px) rotate(0deg);
  }
  75% {
    transform: translateY(-3px) rotate(2deg);
  }
}

.sidebar__logo-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 120%;
  height: 120%;
  transform: translate(-50%, -50%);
  background: radial-gradient(
    circle,
    rgba(20, 184, 166, 0.5) 0%,
    rgba(20, 184, 166, 0.2) 40%,
    transparent 70%
  );
  border-radius: var(--radius-lg);
  animation: logo-glow-pulse 3s ease-in-out infinite;
  pointer-events: none;
}

@keyframes logo-glow-pulse {
  0%, 100% {
    opacity: 0.5;
    transform: translate(-50%, -50%) scale(1);
  }
  50% {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1.3);
  }
}

.sidebar__title-wrapper {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  overflow: hidden;
}

.sidebar__title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-inverse);
  white-space: nowrap;
  letter-spacing: 0.08em;
  line-height: 1.2;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.sidebar__subtitle {
  font-size: 11px;
  font-weight: var(--font-weight-medium);
  color: rgba(255, 255, 255, 0.7);
  white-space: nowrap;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.sidebar__close {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
  color: var(--color-text-inverse);
  flex-shrink: 0;
  
  &:hover {
    background: rgba(255, 255, 255, 0.2);
    border-color: rgba(255, 255, 255, 0.3);
    transform: rotate(90deg);
    transition: transform 0.3s ease;
  }
}

// ==================== 导航区域 ====================
.sidebar__nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: var(--spacing-3) 0;
  overflow-y: auto;
  overflow-x: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  
  // 自定义滚动条
  &::-webkit-scrollbar {
    width: 4px;
  }
  
  &::-webkit-scrollbar-track {
    background: transparent;
  }
  
  &::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.2);
    border-radius: var(--radius-full);
    
    &:hover {
      background: rgba(255, 255, 255, 0.3);
    }
  }
}

// ==================== 导航项 ====================
.sidebar__item {
  display: flex;
  align-items: center;
  padding: 0 var(--spacing-4);
  height: 64px;
  gap: var(--spacing-3);
  cursor: pointer;
  transition: all var(--transition-base) var(--ease-in-out);
  position: relative;
  color: rgba(255, 255, 255, 0.85);
  overflow: hidden;
  border-radius: var(--radius-lg);
  margin: 0 var(--spacing-2);
  
  // 第一个导航项增加上边距
  &--first {
    margin-top: var(--spacing-3);
  }
  
  // 悬停效果
  &:hover {
    background: linear-gradient(
      90deg,
      rgba(255, 255, 255, 0.15) 0%,
      rgba(255, 255, 255, 0.08) 50%,
      rgba(255, 255, 255, 0.03) 100%
    );
    color: var(--color-text-inverse);
    transform: translateX(6px);
    box-shadow: 
      0 4px 16px rgba(0, 0, 0, 0.2),
      0 2px 8px rgba(0, 0, 0, 0.1),
      inset 0 1px 0 rgba(255, 255, 255, 0.15),
      inset -1px 0 0 rgba(255, 255, 255, 0.1);
    
    .sidebar__icon-wrapper {
      background: linear-gradient(
        135deg,
        rgba(255, 255, 255, 0.2) 0%,
        rgba(255, 255, 255, 0.1) 100%
      );
      transform: scale(1.1) rotate(-3deg);
      box-shadow: 
        0 6px 20px rgba(0, 0, 0, 0.2),
        inset 0 1px 0 rgba(255, 255, 255, 0.2);
    }
    
    .sidebar__icon-hover-glow {
      opacity: 1;
      transform: translate(-50%, -50%) scale(1.4);
    }
    
    .sidebar__label {
      font-weight: var(--font-weight-semibold);
      letter-spacing: 0.01em;
    }
  }
  
  // 激活状态
  &--active {
    background: linear-gradient(
      90deg,
      rgba(24, 144, 255, 0.25) 0%,
      rgba(24, 144, 255, 0.12) 50%,
      rgba(24, 144, 255, 0.05) 100%
    );
    color: var(--color-primary-200);
    box-shadow: 
      inset 4px 0 0 var(--color-primary-500),
      0 2px 8px rgba(24, 144, 255, 0.15);
    
    .sidebar__icon-wrapper {
      background: linear-gradient(
        135deg,
        rgba(24, 144, 255, 0.35) 0%,
        rgba(24, 144, 255, 0.2) 100%
      );
      box-shadow: 
        0 0 24px rgba(24, 144, 255, 0.6),
        0 0 12px rgba(24, 144, 255, 0.4),
        inset 0 1px 0 rgba(255, 255, 255, 0.25);
      border: 1px solid rgba(24, 144, 255, 0.5);
    }
    
    .sidebar__icon {
      animation: icon-bounce 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55);
      color: var(--color-primary-200);
    }
    
    .sidebar__label {
      font-weight: var(--font-weight-bold);
      letter-spacing: 0.02em;
    }
  }
}

// 图标容器
.sidebar__icon-wrapper {
  width: 46px;
  height: 46px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-lg);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  flex-shrink: 0;
  position: relative;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
}

.sidebar__icon {
  font-size: 20px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  z-index: 2;
}

// 激活状态光晕
.sidebar__icon-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 100%;
  height: 100%;
  transform: translate(-50%, -50%);
  background: radial-gradient(
    circle,
    rgba(24, 144, 255, 0.4) 0%,
    transparent 70%
  );
  border-radius: var(--radius-lg);
  animation: glow-pulse 2s ease-in-out infinite;
  pointer-events: none;
  z-index: 1;
}

// 悬停光晕
.sidebar__icon-hover-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 100%;
  height: 100%;
  transform: translate(-50%, -50%) scale(1);
  background: radial-gradient(
    circle,
    rgba(255, 255, 255, 0.3) 0%,
    transparent 70%
  );
  border-radius: var(--radius-lg);
  opacity: 0;
  transition: all 0.3s ease;
  pointer-events: none;
  z-index: 0;
}

@keyframes glow-pulse {
  0%, 100% {
    opacity: 0.5;
    transform: translate(-50%, -50%) scale(1);
  }
  50% {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1.15);
  }
}

@keyframes icon-bounce {
  0% {
    transform: scale(1);
  }
  30% {
    transform: scale(1.2);
  }
  50% {
    transform: scale(0.95);
  }
  70% {
    transform: scale(1.1);
  }
  100% {
    transform: scale(1);
  }
}

// 导航标签
.sidebar__label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  transition: all 0.2s ease;
}

// 激活状态指示器
.sidebar__active-indicator {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
}

.sidebar__active-indicator-bar {
  width: 100%;
  height: 100%;
  background: linear-gradient(
    180deg,
    var(--color-primary-300) 0%,
    var(--color-primary-400) 30%,
    var(--color-primary-300) 50%,
    var(--color-primary-400) 70%,
    var(--color-primary-300) 100%
  );
  border-radius: 0 var(--radius-full) var(--radius-full) 0;
  box-shadow: 
    0 0 20px rgba(24, 144, 255, 0.8),
    0 0 40px rgba(24, 144, 255, 0.6),
    0 0 60px rgba(24, 144, 255, 0.4),
    inset 0 0 10px rgba(255, 255, 255, 0.4);
  animation: indicator-slide-in 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
  position: relative;
  
  // 动态光效
  &::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(
      180deg,
      transparent 0%,
      rgba(255, 255, 255, 0.6) 50%,
      transparent 100%
    );
    border-radius: inherit;
    animation: indicator-shine 2.5s ease-in-out infinite;
  }
}

@keyframes indicator-slide-in {
  0% {
    height: 0;
    opacity: 0;
    transform: scaleX(0);
  }
  60% {
    height: 44px;
    opacity: 1;
    transform: scaleX(1.1);
  }
  100% {
    height: 40px;
    opacity: 1;
    transform: scaleX(1);
  }
}

@keyframes indicator-shine {
  0%, 100% {
    opacity: 0.4;
    transform: translateY(-100%);
  }
  50% {
    opacity: 1;
    transform: translateY(100%);
  }
}

// 涟漪效果容器
.sidebar__ripple-container {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  overflow: hidden;
  pointer-events: none;
  border-radius: inherit;
}

.sidebar__ripple {
  position: absolute;
  border-radius: 50%;
  background: radial-gradient(
    circle,
    rgba(24, 144, 255, 0.3) 0%,
    rgba(24, 144, 255, 0.15) 50%,
    transparent 100%
  );
  transform: scale(0);
  animation: ripple-animation var(--transition-slow) var(--ease-in-out);
  pointer-events: none;
}

@keyframes ripple-animation {
  to {
    transform: scale(4);
    opacity: 0;
  }
}

// ==================== 底部折叠按钮 ====================
.sidebar__footer {
  padding: var(--spacing-4);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  flex-shrink: 0;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  background: rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
}

.sidebar__toggle {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.2);
  color: var(--color-text-inverse);
  flex-shrink: 0;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid rgba(255, 255, 255, 0.15);
  
  &:hover {
    background: rgba(255, 255, 255, 0.2);
    border-color: rgba(255, 255, 255, 0.3);
    transform: rotate(180deg) scale(1.1);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  }
  
  &:active {
    transform: rotate(180deg) scale(0.95);
  }
}

.sidebar__toggle-label {
  font-size: var(--font-size-xs);
  color: rgba(255, 255, 255, 0.7);
  white-space: nowrap;
  overflow: hidden;
  font-weight: var(--font-weight-medium);
  letter-spacing: 0.02em;
}

// ==================== 过渡动画 ====================

// 淡入淡出
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

// 滑动淡入淡出
.slide-fade-enter-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-fade-leave-active {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-fade-enter-from {
  opacity: 0;
  transform: translateX(-10px);
}

.slide-fade-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}

// 指示器淡入淡出
.indicator-fade-enter-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.indicator-fade-leave-active {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.indicator-fade-enter-from,
.indicator-fade-leave-to {
  opacity: 0;
  transform: translateY(-50%) scaleY(0);
}
</style>
