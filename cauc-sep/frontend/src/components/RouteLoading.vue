<script setup>
/**
 * @file RouteLoading.vue
 * @path src/components/
 * @description 路由加载状态组件，显示加载进度和动画
 * @author Agent
 * @date 2024-03-08
 */

import { ref, onMounted, onUnmounted } from 'vue'
import { useLoadingStore } from '@/stores/layout'

/**
 * Props定义
 */
const props = defineProps({
  /** 是否显示进度条 */
  showProgress: {
    type: Boolean,
    default: true
  },
  /** 是否显示加载文字 */
  showText: {
    type: Boolean,
    default: true
  },
  /** 加载文字 */
  loadingText: {
    type: String,
    default: '加载中...'
  },
  /** 最小显示时间（毫秒） */
  minDisplayTime: {
    type: Number,
    default: 300
  }
})

/** 加载进度 */
const progress = ref(0)

/** 是否正在加载 */
const isLoading = ref(false)

/** 加载开始时间 */
let loadingStartTime = 0

/** 进度动画定时器 */
let progressTimer = null

/** 加载Store */
const loadingStore = useLoadingStore()

/**
 * 开始加载动画
 */
function startLoading() {
  isLoading.value = true
  loadingStartTime = Date.now()
  progress.value = 0

  // 模拟进度增长
  progressTimer = setInterval(() => {
    if (progress.value < 90) {
      // 前90%快速增长
      progress.value += Math.random() * 15
    } else if (progress.value < 95) {
      // 90-95%慢速增长
      progress.value += Math.random() * 3
    }
    // 95%以上停止，等待实际加载完成
  }, 100)
}

/**
 * 完成加载动画
 */
function finishLoading() {
  // 确保最小显示时间
  const elapsed = Date.now() - loadingStartTime
  const remainingTime = Math.max(0, props.minDisplayTime - elapsed)

  setTimeout(() => {
    // 进度完成
    progress.value = 100

    // 清除定时器
    if (progressTimer) {
      clearInterval(progressTimer)
      progressTimer = null
    }

    // 延迟隐藏，让用户看到完成状态
    setTimeout(() => {
      isLoading.value = false
      progress.value = 0
    }, 200)
  }, remainingTime)
}

/**
 * 监听路由加载状态
 */
onMounted(() => {
  // 监听加载Store
  loadingStore.$subscribe((mutation, state) => {
    if (state.routeLoading && !isLoading.value) {
      startLoading()
    } else if (!state.routeLoading && isLoading.value) {
      finishLoading()
    }
  })

  // 如果已经在加载中，立即开始
  if (loadingStore.routeLoading) {
    startLoading()
  }
})

/**
 * 清理资源
 */
onUnmounted(() => {
  if (progressTimer) {
    clearInterval(progressTimer)
    progressTimer = null
  }
})

// 暴露方法
defineExpose({
  startLoading,
  finishLoading
})
</script>

<template>
  <Transition name="fade">
    <div
      v-if="isLoading"
      class="route-loading"
    >
      <!-- 顶部进度条 -->
      <div
        v-if="showProgress"
        class="progress-bar"
      >
        <div
          class="progress-fill"
          :style="{ width: `${progress}%` }"
        />
      </div>

      <!-- 中央加载动画 -->
      <div class="loading-content">
        <div class="loading-spinner">
          <svg
            viewBox="0 0 50 50"
            class="circular"
          >
            <circle
              cx="25"
              cy="25"
              r="20"
              fill="none"
              class="path"
            />
          </svg>
        </div>
        <p
          v-if="showText"
          class="loading-text"
        >
          {{ loadingText }}
        </p>
      </div>
    </div>
  </Transition>
</template>

<style scoped lang="scss">
.route-loading {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(4px);
}

.progress-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background-color: var(--color-bg-secondary);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(
    90deg,
    var(--color-primary-500),
    var(--color-primary-400)
  );
  transition: width 0.3s ease-out;
  box-shadow: 0 0 10px var(--color-primary-500);
}

.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-4);
}

.loading-spinner {
  width: 50px;
  height: 50px;
}

.circular {
  animation: rotate 2s linear infinite;
}

.path {
  stroke: var(--color-primary-500);
  stroke-width: 3;
  stroke-linecap: round;
  animation: dash 1.5s ease-in-out infinite;
}

.loading-text {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  animation: pulse 1.5s ease-in-out infinite;
}

/* 动画 */
@keyframes rotate {
  100% {
    transform: rotate(360deg);
  }
}

@keyframes dash {
  0% {
    stroke-dasharray: 1, 150;
    stroke-dashoffset: 0;
  }
  50% {
    stroke-dasharray: 90, 150;
    stroke-dashoffset: -35;
  }
  100% {
    stroke-dasharray: 90, 150;
    stroke-dashoffset: -124;
  }
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
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

/* 暗色主题适配 */
@media (prefers-color-scheme: dark) {
  .route-loading {
    background-color: rgba(30, 30, 30, 0.9);
  }
}
</style>
