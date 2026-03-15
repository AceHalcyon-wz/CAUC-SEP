/**
 * @file PageSkeleton.vue
 * @path src/components/common/
 * @description 页面骨架屏组件 - 提升页面加载感知速度
 * @author Agent
 * @date 2024-03-15
 * @version 3.5.2
 */

<script setup>
import { computed } from 'vue'

const props = defineProps({
  type: {
    type: String,
    default: 'default',
    validator: (value) => ['default', 'control', 'analysis', 'settings', 'list'].includes(value)
  },
  loading: {
    type: Boolean,
    default: true
  }
})

/**
 * 骨架屏配置
 */
const skeletonConfig = computed(() => {
  const configs = {
    default: {
      header: true,
      cards: 3,
      rows: 2,
      chart: false
    },
    control: {
      header: true,
      cards: 2,
      rows: 4,
      chart: true
    },
    analysis: {
      header: true,
      cards: 1,
      rows: 0,
      chart: true
    },
    settings: {
      header: true,
      cards: 1,
      rows: 6,
      chart: false
    },
    list: {
      header: true,
      cards: 0,
      rows: 8,
      chart: false
    }
  }
  return configs[props.type] || configs.default
})
</script>

<template>
  <div
    v-if="loading"
    class="page-skeleton"
  >
    <!-- 页面头部骨架 -->
    <div
      v-if="skeletonConfig.header"
      class="skeleton-header"
    >
      <div class="skeleton-title" />
      <div class="skeleton-subtitle" />
    </div>

    <!-- 卡片骨架 -->
    <div
      v-if="skeletonConfig.cards > 0"
      class="skeleton-cards"
    >
      <div
        v-for="i in skeletonConfig.cards"
        :key="i"
        class="skeleton-card"
      >
        <div class="skeleton-card-header" />
        <div class="skeleton-card-content">
          <div
            v-for="j in skeletonConfig.rows"
            :key="j"
            class="skeleton-row"
            :style="{ width: `${80 - j * 10}%` }"
          />
        </div>
      </div>
    </div>

    <!-- 图表骨架 -->
    <div
      v-if="skeletonConfig.chart"
      class="skeleton-chart"
    >
      <div class="skeleton-chart-header" />
      <div class="skeleton-chart-content">
        <div class="skeleton-chart-area" />
      </div>
    </div>

    <!-- 列表骨架 -->
    <div
      v-if="skeletonConfig.rows > 4"
      class="skeleton-list"
    >
      <div
        v-for="i in skeletonConfig.rows"
        :key="i"
        class="skeleton-list-item"
      >
        <div class="skeleton-avatar" />
        <div class="skeleton-content">
          <div
            class="skeleton-row"
            style="width: 60%"
          />
          <div
            class="skeleton-row"
            style="width: 40%"
          />
        </div>
      </div>
    </div>
  </div>

  <!-- 实际内容 -->
  <slot v-else />
</template>

<style scoped>
.page-skeleton {
  padding: var(--spacing-4);
  animation: skeleton-pulse 1.5s ease-in-out infinite;
}

@keyframes skeleton-pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

.skeleton-header {
  margin-bottom: var(--spacing-6);
}

.skeleton-title {
  width: 200px;
  height: 28px;
  background: var(--color-neutral-200);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-2);
}

.skeleton-subtitle {
  width: 300px;
  height: 16px;
  background: var(--color-neutral-200);
  border-radius: var(--radius-sm);
}

.skeleton-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--spacing-4);
  margin-bottom: var(--spacing-4);
}

.skeleton-card {
  background: var(--color-surface-primary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-lg);
  padding: var(--spacing-4);
}

.skeleton-card-header {
  width: 120px;
  height: 20px;
  background: var(--color-neutral-200);
  border-radius: var(--radius-sm);
  margin-bottom: var(--spacing-4);
}

.skeleton-card-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.skeleton-row {
  height: 14px;
  background: var(--color-neutral-200);
  border-radius: var(--radius-sm);
}

.skeleton-chart {
  background: var(--color-surface-primary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-lg);
  padding: var(--spacing-4);
}

.skeleton-chart-header {
  width: 150px;
  height: 20px;
  background: var(--color-neutral-200);
  border-radius: var(--radius-sm);
  margin-bottom: var(--spacing-4);
}

.skeleton-chart-content {
  height: 300px;
}

.skeleton-chart-area {
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, var(--color-neutral-100) 0%, var(--color-neutral-200) 50%, var(--color-neutral-100) 100%);
  border-radius: var(--radius-md);
  animation: skeleton-shimmer 2s infinite;
}

@keyframes skeleton-shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
}

.skeleton-list-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-3);
  background: var(--color-surface-primary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
}

.skeleton-avatar {
  width: 40px;
  height: 40px;
  background: var(--color-neutral-200);
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

.skeleton-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}
</style>
