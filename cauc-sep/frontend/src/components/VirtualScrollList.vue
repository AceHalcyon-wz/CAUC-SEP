<script setup>
/**
 * @file VirtualScrollList.vue
 * @path src/components/
 * @description 高性能虚拟滚动列表组件，支持动态item大小、滚动位置记忆和性能优化
 * @author Agent
 * @date 2024-03-08
 */

import { ref, computed, onMounted, onUnmounted, watch, nextTick, provide } from 'vue'
import { Loading, ArrowUp } from '@element-plus/icons-vue'

/**
 * Props定义
 */
const props = defineProps({
  /** 数据列表 */
  items: {
    type: Array,
    required: true,
    default: () => []
  },
  /** 每项预估高度（像素），用于初始估算 */
  itemHeight: {
    type: Number,
    default: 50
  },
  /** 缓冲区大小（可见区域外额外渲染的项数） */
  bufferSize: {
    type: Number,
    default: 5
  },
  /** 容器高度（像素） */
  height: {
    type: Number,
    default: 600
  },
  /** 是否启用懒加载 */
  enableLazyLoad: {
    type: Boolean,
    default: true
  },
  /** 懒加载触发阈值（距离底部的像素） */
  lazyLoadThreshold: {
    type: Number,
    default: 200
  },
  /** 是否启用动态高度 */
  dynamicHeight: {
    type: Boolean,
    default: false
  },
  /** 是否启用滚动位置记忆 */
  rememberPosition: {
    type: Boolean,
    default: true
  },
  /** 滚动位置记忆的key（用于区分不同列表） */
  positionKey: {
    type: String,
    default: 'virtual-scroll-list'
  },
  /** 是否启用滚动优化（减少重排） */
  enableScrollOptimization: {
    type: Boolean,
    default: true
  },
  /** 滚动优化阈值（毫秒） */
  scrollThrottle: {
    type: Number,
    default: 16 // 约60fps
  }
})

/**
 * Emits定义
 */
const emit = defineEmits(['scroll', 'lazy-load', 'item-click', 'position-restored'])

/** 容器引用 */
const containerRef = ref(null)

/** 当前滚动位置 */
const scrollTop = ref(0)

/** 是否正在加载 */
const isLoading = ref(false)

/** item高度缓存（动态高度模式） */
const itemHeightCache = ref(new Map())

/** item位置缓存（动态高度模式） */
const itemPositionCache = ref(new Map())

/** 是否正在滚动 */
const isScrolling = ref(false)

/** 滚动定时器ID */
let scrollTimer = null

/** 上次滚动时间 */
let lastScrollTime = 0

/** 上次滚动位置 */
let lastScrollTop = 0

/** ResizeObserver实例 */
let resizeObserver = null

/**
 * 计算总高度
 */
const totalHeight = computed(() => {
  if (!props.dynamicHeight) {
    return props.items.length * props.itemHeight
  }
  
  // 动态高度模式：累加所有item高度
  let height = 0
  for (let i = 0; i < props.items.length; i++) {
    height += getItemHeight(i)
  }
  return height
})

/**
 * 可见项数量
 */
const visibleCount = computed(() => {
  const avgHeight = props.dynamicHeight 
    ? (totalHeight.value / props.items.length || props.itemHeight)
    : props.itemHeight
  return Math.ceil(props.height / avgHeight)
})

/**
 * 计算起始索引（支持动态高度）
 */
const startIndex = computed(() => {
  if (!props.dynamicHeight) {
    const index = Math.floor(scrollTop.value / props.itemHeight) - props.bufferSize
    return Math.max(0, index)
  }
  
  // 动态高度模式：二分查找
  return findStartIndex(scrollTop.value)
})

/**
 * 计算结束索引（支持动态高度）
 */
const endIndex = computed(() => {
  if (!props.dynamicHeight) {
    const index = startIndex.value + visibleCount.value + props.bufferSize * 2
    return Math.min(props.items.length, index)
  }
  
  // 动态高度模式：从起始位置累加高度
  let height = 0
  let index = startIndex.value
  
  while (index < props.items.length && height < props.height + props.bufferSize * props.itemHeight * 2) {
    height += getItemHeight(index)
    index++
  }
  
  return Math.min(props.items.length, index)
})

/**
 * 可见项
 */
const visibleItems = computed(() => {
  return props.items.slice(startIndex.value, endIndex.value).map((item, i) => ({
    item,
    index: startIndex.value + i
  }))
})

/**
 * 计算偏移量（支持动态高度）
 */
const offsetY = computed(() => {
  if (!props.dynamicHeight) {
    return startIndex.value * props.itemHeight
  }
  
  // 动态高度模式：累加前面所有item的高度
  return getItemOffset(startIndex.value)
})

/**
 * 获取item高度
 * 
 * @param {number} index - item索引
 * @returns {number} item高度
 */
function getItemHeight(index) {
  if (!props.dynamicHeight) {
    return props.itemHeight
  }
  
  // 优先从缓存获取
  if (itemHeightCache.value.has(index)) {
    return itemHeightCache.value.get(index)
  }
  
  // 返回预估高度
  return props.itemHeight
}

/**
 * 获取item偏移量
 * 
 * @param {number} index - item索引
 * @returns {number} item偏移量
 */
function getItemOffset(index) {
  if (!props.dynamicHeight) {
    return index * props.itemHeight
  }
  
  // 从缓存获取
  if (itemPositionCache.value.has(index)) {
    return itemPositionCache.value.get(index)
  }
  
  // 计算并缓存
  let offset = 0
  for (let i = 0; i < index; i++) {
    offset += getItemHeight(i)
  }
  
  itemPositionCache.value.set(index, offset)
  return offset
}

/**
 * 二分查找起始索引
 * 
 * @param {number} scrollOffset - 滚动偏移量
 * @returns {number} 起始索引
 */
function findStartIndex(scrollOffset) {
  if (scrollOffset <= 0) return 0
  
  let low = 0
  let high = props.items.length - 1
  
  while (low < high) {
    const mid = Math.floor((low + high) / 2)
    const offset = getItemOffset(mid)
    
    if (offset < scrollOffset) {
      low = mid + 1
    } else {
      high = mid
    }
  }
  
  return Math.max(0, low - props.bufferSize)
}

/**
 * 更新item高度缓存
 * 
 * @param {number} index - item索引
 * @param {number} height - 实际高度
 */
function updateItemHeight(index, height) {
  if (!props.dynamicHeight) return
  
  const oldHeight = itemHeightCache.value.get(index)
  
  if (oldHeight !== height) {
    itemHeightCache.value.set(index, height)
    
    // 清除位置缓存（从当前索引开始）
    for (let i = index; i < props.items.length; i++) {
      itemPositionCache.value.delete(i)
    }
  }
}

/**
 * 处理滚动事件
 */
function handleScroll(event) {
  const target = event.target
  const currentScrollTop = target.scrollTop
  
  // 滚动优化：节流处理
  if (props.enableScrollOptimization) {
    const now = Date.now()
    const timeSinceLastScroll = now - lastScrollTime
    
    if (timeSinceLastScroll < props.scrollThrottle) {
      // 使用requestAnimationFrame优化
      if (!scrollTimer) {
        scrollTimer = requestAnimationFrame(() => {
          processScroll(currentScrollTop)
          scrollTimer = null
        })
      }
      return
    }
    
    lastScrollTime = now
  }
  
  processScroll(currentScrollTop)
}

/**
 * 处理滚动逻辑
 * 
 * @param {number} currentScrollTop - 当前滚动位置
 */
function processScroll(currentScrollTop) {
  scrollTop.value = currentScrollTop
  isScrolling.value = true
  emit('scroll', currentScrollTop)
  
  // 清除滚动状态定时器
  if (scrollTimer) {
    clearTimeout(scrollTimer)
  }
  
  // 延迟清除滚动状态
  scrollTimer = setTimeout(() => {
    isScrolling.value = false
  }, 150)
  
  // 懒加载检测
  if (props.enableLazyLoad && !isLoading.value) {
    const scrollBottom = containerRef.value.scrollHeight - currentScrollTop - containerRef.value.clientHeight
    if (scrollBottom < props.lazyLoadThreshold) {
      isLoading.value = true
      emit('lazy-load')
      
      // 重置加载状态（延迟500ms，防止频繁触发）
      setTimeout(() => {
        isLoading.value = false
      }, 500)
    }
  }
  
  // 保存滚动位置
  if (props.rememberPosition) {
    saveScrollPosition(currentScrollTop)
  }
}

/**
 * 保存滚动位置
 * 
 * @param {number} position - 滚动位置
 */
function saveScrollPosition(position) {
  try {
    sessionStorage.setItem(`scroll-position-${props.positionKey}`, position.toString())
  } catch (error) {
    console.warn('[VirtualScrollList] Failed to save scroll position:', error)
  }
}

/**
 * 恢复滚动位置
 */
function restoreScrollPosition() {
  if (!props.rememberPosition || !containerRef.value) return
  
  try {
    const savedPosition = sessionStorage.getItem(`scroll-position-${props.positionKey}`)
    if (savedPosition) {
      const position = parseInt(savedPosition, 10)
      nextTick(() => {
        containerRef.value.scrollTop = position
        scrollTop.value = position
        emit('position-restored', position)
        console.log(`[VirtualScrollList] Restored scroll position: ${position}`)
      })
    }
  } catch (error) {
    console.warn('[VirtualScrollList] Failed to restore scroll position:', error)
  }
}

/**
 * 清除滚动位置
 */
function clearScrollPosition() {
  try {
    sessionStorage.removeItem(`scroll-position-${props.positionKey}`)
  } catch (error) {
    console.warn('[VirtualScrollList] Failed to clear scroll position:', error)
  }
}

/**
 * 滚动到指定索引
 * 
 * @param {number} index - 目标索引
 */
function scrollToIndex(index) {
  if (!containerRef.value) return
  
  if (!props.dynamicHeight) {
    containerRef.value.scrollTop = index * props.itemHeight
  } else {
    // 动态高度模式：计算偏移量
    const offset = getItemOffset(index)
    containerRef.value.scrollTop = offset
  }
}

/**
 * 滚动到顶部
 */
function scrollToTop() {
  if (containerRef.value) {
    containerRef.value.scrollTop = 0
  }
}

/**
 * 滚动到底部
 */
function scrollToBottom() {
  if (containerRef.value) {
    containerRef.value.scrollTop = totalHeight.value
  }
}

/**
 * 处理项点击
 */
function handleItemClick(item, index) {
  emit('item-click', item, index)
}

/**
 * 重置加载状态
 */
function resetLoading() {
  isLoading.value = false
}

/**
 * 刷新高度缓存
 */
function refreshHeightCache() {
  itemHeightCache.value.clear()
  itemPositionCache.value.clear()
}

/**
 * 处理item resize
 * 
 * @param {number} index - item索引
 * @param {ResizeObserverEntry} entry - resize entry
 */
function handleItemResize(index, entry) {
  if (!entry || !entry.contentRect) return
  
  const height = entry.contentRect.height
  updateItemHeight(index, height)
}

/**
 * 设置item元素引用
 * 
 * @param {number} index - item索引
 * @param {HTMLElement} el - DOM元素
 */
function setItemRef(index, el) {
  if (!el || !props.dynamicHeight) return
  
  // 使用ResizeObserver监听高度变化
  if (!resizeObserver) {
    resizeObserver = new ResizeObserver((entries) => {
      entries.forEach(entry => {
        const idx = parseInt(entry.target.dataset.index, 10)
        if (!isNaN(idx)) {
          handleItemResize(idx, entry)
        }
      })
    })
  }
  
  // 设置data-index属性
  el.dataset.index = index.toString()
  
  // 开始观察
  resizeObserver.observe(el)
}

// 监听items变化
watch(() => props.items.length, (newLength, oldLength) => {
  // 数据减少时，滚动到顶部
  if (newLength < oldLength) {
    scrollToTop()
  }
  
  // 清除高度缓存
  if (props.dynamicHeight) {
    refreshHeightCache()
  }
})

// 监听动态高度模式变化
watch(() => props.dynamicHeight, (isDynamic) => {
  if (isDynamic) {
    refreshHeightCache()
  }
})

// 组件挂载
onMounted(() => {
  // 恢复滚动位置
  if (props.rememberPosition) {
    restoreScrollPosition()
  }
})

// 组件卸载
onUnmounted(() => {
  // 清理定时器
  if (scrollTimer) {
    clearTimeout(scrollTimer)
    cancelAnimationFrame(scrollTimer)
  }
  
  // 清理ResizeObserver
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
})

// 暴露方法给父组件
defineExpose({
  scrollToIndex,
  scrollToTop,
  scrollToBottom,
  resetLoading,
  refreshHeightCache,
  clearScrollPosition,
  getItemHeight,
  getItemOffset
})

// 提供方法给子组件
provide('virtualScrollList', {
  updateItemHeight,
  getItemHeight
})
</script>

<template>
  <div
    ref="containerRef"
    class="virtual-scroll-list"
    :class="{ 'is-scrolling': isScrolling }"
    :style="{ height: `${height}px` }"
    @scroll="handleScroll"
  >
    <!-- 总高度占位容器 -->
    <div class="scroll-content" :style="{ height: `${totalHeight}px` }">
      <!-- 可见项容器 -->
      <div
        class="visible-items"
        :style="{ transform: `translateY(${offsetY}px)` }"
      >
        <div
          v-for="{ item, index } in visibleItems"
          :key="index"
          :ref="el => setItemRef(index, el)"
          class="scroll-item"
          :style="dynamicHeight ? {} : { height: `${itemHeight}px` }"
          @click="handleItemClick(item, index)"
        >
          <slot :item="item" :index="index">
            <!-- 默认插槽内容 -->
            <div class="default-item">
              <span class="item-index">{{ index + 1 }}</span>
              <span class="item-content">{{ item }}</span>
            </div>
          </slot>
        </div>
      </div>
    </div>

    <!-- 加载指示器 -->
    <div v-if="isLoading" class="loading-indicator">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载中...</span>
    </div>
    
    <!-- 滚动到顶部按钮 -->
    <Transition name="fade">
      <button
        v-if="scrollTop > height"
        class="scroll-to-top"
        @click="scrollToTop"
        title="回到顶部"
      >
        <el-icon><ArrowUp /></el-icon>
      </button>
    </Transition>
  </div>
</template>

<style scoped lang="scss">
.virtual-scroll-list {
  position: relative;
  overflow-y: auto;
  overflow-x: hidden;
  background-color: var(--color-surface-primary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
  
  /* 自定义滚动条 */
  &::-webkit-scrollbar {
    width: 8px;
  }

  &::-webkit-scrollbar-track {
    background-color: var(--color-bg-secondary);
    border-radius: var(--radius-sm);
  }

  &::-webkit-scrollbar-thumb {
    background-color: var(--color-border-secondary);
    border-radius: var(--radius-sm);
    transition: background-color var(--transition-fast);

    &:hover {
      background-color: var(--color-primary-400);
    }
  }
  
  /* 滚动时隐藏滚动条（优化体验） */
  &.is-scrolling {
    &::-webkit-scrollbar-thumb {
      background-color: var(--color-primary-500);
    }
  }
}

.scroll-content {
  position: relative;
  width: 100%;
}

.visible-items {
  position: absolute;
  width: 100%;
  will-change: transform;
}

.scroll-item {
  display: flex;
  align-items: center;
  padding: 0 var(--spacing-4);
  border-bottom: 1px solid var(--color-border-primary);
  transition: background-color var(--transition-fast);
  cursor: pointer;

  &:hover {
    background-color: var(--color-interactive-hover);
  }

  &:last-child {
    border-bottom: none;
  }
}

.default-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  width: 100%;
  font-size: var(--font-size-sm);
}

.item-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 40px;
  height: 24px;
  padding: 0 var(--spacing-2);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
  font-family: var(--font-family-mono);
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.item-content {
  flex: 1;
  color: var(--color-text-primary);
}

.loading-indicator {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-2);
  padding: var(--spacing-3);
  background: linear-gradient(to top, var(--color-surface-primary), transparent);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  animation: fadeIn 0.3s ease-in;
}

.scroll-to-top {
  position: absolute;
  right: var(--spacing-4);
  bottom: var(--spacing-4);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 50%;
  background-color: var(--color-primary-500);
  color: white;
  cursor: pointer;
  box-shadow: var(--shadow-lg);
  transition: all var(--transition-fast);
  z-index: 10;
  
  &:hover {
    background-color: var(--color-primary-600);
    transform: translateY(-2px);
    box-shadow: var(--shadow-xl);
  }
  
  &:active {
    transform: translateY(0);
  }
  
  .el-icon {
    font-size: 20px;
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
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
</style>
