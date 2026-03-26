<script setup lang="ts">
/**
 * @file VirtualList.vue
 * @path src/components/
 * @description 虚拟滚动列表组件，用于大数据量列表的高效渲染
 * @author Agent
 * @date 2024-03-07
 */

import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';

/**
 * Props定义
 */
interface Props {
  /** 数据列表 */
  items: Array<Record<string, unknown>>;
  /** 每项高度（像素） */
  itemHeight: number;
  /** 可见项数量 */
  visibleCount: number;
  /** 缓冲区大小（可见区域外额外渲染的项数） */
  bufferSize?: number;
  /** 容器高度（像素），优先使用visibleCount */
  height?: number;
  /** 是否启用懒加载 */
  enableLazyLoad?: boolean;
  /** 懒加载触发阈值（距离底部的像素） */
  lazyLoadThreshold?: number;
  /** 是否显示滚动条 */
  showScrollbar?: boolean;
  /** 自定义键字段 */
  keyField?: string;
}

const props = withDefaults(defineProps<Props>(), {
  items: () => [],
  itemHeight: 40,
  visibleCount: 20,
  bufferSize: 5,
  height: 0,
  enableLazyLoad: false,
  lazyLoadThreshold: 200,
  showScrollbar: true,
  keyField: 'id',
});

/**
 * Emits定义
 */
const emit = defineEmits<{
  (e: 'scroll', scrollTop: number): void;
  (e: 'lazy-load'): void;
  (e: 'item-click', item: Record<string, unknown>, index: number): void;
  (e: 'visible-change', startIndex: number, endIndex: number): void;
}>();

/** 容器引用 */
const containerRef = ref<HTMLElement | null>(null);

/** 当前滚动位置 */
const scrollTop = ref(0);

/** 是否正在加载 */
const isLoading = ref(false);

/** 容器实际高度 */
const containerHeight = computed(() => {
  return props.height > 0 ? props.height : props.visibleCount * props.itemHeight;
});

/** 总高度 */
const totalHeight = computed(() => props.items.length * props.itemHeight);

/** 实际可见项数量 */
const actualVisibleCount = computed(() => {
  return Math.ceil(containerHeight.value / props.itemHeight);
});

/** 起始索引 */
const startIndex = computed(() => {
  const index = Math.floor(scrollTop.value / props.itemHeight) - props.bufferSize;
  return Math.max(0, index);
});

/** 结束索引 */
const endIndex = computed(() => {
  const index = startIndex.value + actualVisibleCount.value + props.bufferSize * 2;
  return Math.min(props.items.length, index);
});

/** 可见项 */
const visibleItems = computed(() => {
  return props.items.slice(startIndex.value, endIndex.value).map((item, i) => ({
    item,
    index: startIndex.value + i,
    key: item[props.keyField] || startIndex.value + i,
  }));
});

/** 偏移量 */
const offsetY = computed(() => startIndex.value * props.itemHeight);

/** 上一次可见范围（用于触发visible-change事件） */
let lastVisibleRange = { start: -1, end: -1 };

/**
 * 处理滚动事件
 */
function handleScroll(event: Event): void {
  const target = event.target as HTMLElement;
  scrollTop.value = target.scrollTop;
  emit('scroll', scrollTop.value);

  // 检测可见范围变化
  if (startIndex.value !== lastVisibleRange.start || endIndex.value !== lastVisibleRange.end) {
    lastVisibleRange = { start: startIndex.value, end: endIndex.value };
    emit('visible-change', startIndex.value, endIndex.value);
  }

  // 懒加载检测
  if (props.enableLazyLoad && !isLoading.value) {
    const scrollBottom = target.scrollHeight - target.scrollTop - target.clientHeight;
    if (scrollBottom < props.lazyLoadThreshold) {
      isLoading.value = true;
      emit('lazy-load');
      
      // 重置加载状态（延迟500ms，防止频繁触发）
      setTimeout(() => {
        isLoading.value = false;
      }, 500);
    }
  }
}

/**
 * 滚动到指定索引
 */
function scrollToIndex(index: number): void {
  if (containerRef.value) {
    const targetTop = Math.max(0, Math.min(index * props.itemHeight, totalHeight.value - containerHeight.value));
    containerRef.value.scrollTop = targetTop;
  }
}

/**
 * 滚动到顶部
 */
function scrollToTop(): void {
  if (containerRef.value) {
    containerRef.value.scrollTop = 0;
  }
}

/**
 * 滚动到底部
 */
function scrollToBottom(): void {
  if (containerRef.value) {
    containerRef.value.scrollTop = totalHeight.value;
  }
}

/**
 * 滚动到指定项
 */
function scrollToItem(predicate: (item: Record<string, unknown>) => boolean): boolean {
  const index = props.items.findIndex(predicate);
  if (index >= 0) {
    scrollToIndex(index);
    return true;
  }
  return false;
}

/**
 * 处理项点击
 */
function handleItemClick(item: Record<string, unknown>, index: number): void {
  emit('item-click', item, index);
}

/**
 * 重置加载状态
 */
function resetLoading(): void {
  isLoading.value = false;
}

/**
 * 获取当前可见项信息
 */
function getVisibleInfo(): { startIndex: number; endIndex: number; visibleCount: number } {
  return {
    startIndex: startIndex.value,
    endIndex: endIndex.value,
    visibleCount: endIndex.value - startIndex.value,
  };
}

/**
 * 刷新列表（重新计算滚动位置）
 */
async function refresh(): Promise<void> {
  await nextTick();
  if (containerRef.value) {
    const currentScrollTop = containerRef.value.scrollTop;
    containerRef.value.scrollTop = currentScrollTop;
  }
}

// 监听items变化，重置滚动位置
watch(() => props.items.length, (newLength, oldLength) => {
  if (newLength < oldLength) {
    scrollToTop();
  }
});

// 组件挂载时初始化
onMounted(() => {
  lastVisibleRange = { start: startIndex.value, end: endIndex.value };
});

// 组件卸载时清理
onUnmounted(() => {
  lastVisibleRange = { start: -1, end: -1 };
});

// 暴露方法给父组件
defineExpose({
  scrollToIndex,
  scrollToTop,
  scrollToBottom,
  scrollToItem,
  resetLoading,
  getVisibleInfo,
  refresh,
});
</script>

<template>
  <div
    ref="containerRef"
    class="virtual-list"
    :class="{ 'virtual-list--no-scrollbar': !showScrollbar }"
    :style="{ height: `${containerHeight}px` }"
    @scroll="handleScroll"
  >
    <!-- 总高度占位容器 -->
    <div
      class="virtual-list__content"
      :style="{ height: `${totalHeight}px` }"
    >
      <!-- 可见项容器 -->
      <div
        class="virtual-list__visible"
        :style="{ transform: `translateY(${offsetY}px)` }"
      >
        <div
          v-for="{ item, index, key } in visibleItems"
          :key="key"
          class="virtual-list__item"
          :style="{ height: `${itemHeight}px` }"
          @click="handleItemClick(item, index)"
        >
          <slot
            :item="item"
            :index="index"
          >
            <!-- 默认插槽内容 -->
            <div class="virtual-list__item-default">
              <span class="virtual-list__item-index">{{ index + 1 }}</span>
              <span class="virtual-list__item-content">{{ item }}</span>
            </div>
          </slot>
        </div>
      </div>
    </div>

    <!-- 加载指示器 -->
    <div
      v-if="isLoading"
      class="virtual-list__loading"
    >
      <el-icon class="is-loading">
        <Loading />
      </el-icon>
      <span>加载中...</span>
    </div>

    <!-- 空状态 -->
    <div
      v-if="items.length === 0"
      class="virtual-list__empty"
    >
      <slot name="empty">
        <el-empty description="暂无数据" />
      </slot>
    </div>
  </div>
</template>

<style scoped lang="scss">
.virtual-list {
  position: relative;
  overflow-y: auto;
  overflow-x: hidden;
  background-color: var(--color-surface-primary, #fff);
  border-radius: var(--radius-md, 8px);
  border: 1px solid var(--color-border-primary, #e4e7ed);
  
  /* 自定义滚动条 */
  &::-webkit-scrollbar {
    width: 8px;
  }

  &::-webkit-scrollbar-track {
    background-color: var(--color-bg-secondary, #f5f7fa);
    border-radius: var(--radius-sm, 4px);
  }

  &::-webkit-scrollbar-thumb {
    background-color: var(--color-border-secondary, #c0c4cc);
    border-radius: var(--radius-sm, 4px);
    transition: background-color 0.3s;

    &:hover {
      background-color: var(--color-primary-400, #409eff);
    }
  }

  /* 隐藏滚动条 */
  &--no-scrollbar {
    &::-webkit-scrollbar {
      display: none;
    }
  }

  &__content {
    position: relative;
    width: 100%;
  }

  &__visible {
    position: absolute;
    width: 100%;
    will-change: transform;
  }

  &__item {
    display: flex;
    align-items: center;
    padding: 0 var(--spacing-4, 16px);
    border-bottom: 1px solid var(--color-border-primary, #e4e7ed);
    transition: background-color 0.2s;
    cursor: pointer;
    box-sizing: border-box;

    &:hover {
      background-color: var(--color-interactive-hover, #f5f7fa);
    }

    &:last-child {
      border-bottom: none;
    }
  }

  &__item-default {
    display: flex;
    align-items: center;
    gap: var(--spacing-3, 12px);
    width: 100%;
    font-size: var(--font-size-sm, 14px);
  }

  &__item-index {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 40px;
    height: 24px;
    padding: 0 var(--spacing-2, 8px);
    background-color: var(--color-bg-secondary, #f5f7fa);
    border-radius: var(--radius-sm, 4px);
    font-family: var(--font-family-mono, 'Courier New', monospace);
    font-size: var(--font-size-xs, 12px);
    color: var(--color-text-tertiary, #909399);
  }

  &__item-content {
    flex: 1;
    color: var(--color-text-primary, #303133);
  }

  &__loading {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--spacing-2, 8px);
    padding: var(--spacing-3, 12px);
    background: linear-gradient(to top, var(--color-surface-primary, #fff), transparent);
    color: var(--color-text-secondary, #606266);
    font-size: var(--font-size-sm, 14px);
    animation: fadeIn 0.3s ease-in;
  }

  &__empty {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
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
</style>
