<!--
  @file GlobalLoading.vue
  @path src/components/common/
  @description 全局加载指示器组件，显示加载状态和进度
  @author Agent
  @date 2024-03-15
  @version 3.5.1
-->

<script setup>
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import { useLoading } from '@/composables/useLoading'

const props = defineProps({
  /** 是否显示进度条 */
  showProgress: {
    type: Boolean,
    default: true
  },
  /** 是否显示加载消息 */
  showMessage: {
    type: Boolean,
    default: true
  },
  /** 最小显示时间（毫秒），防止闪烁 */
  minDisplayTime: {
    type: Number,
    default: 300
  },
  /** 延迟显示时间（毫秒），快速操作不显示 */
  delayShow: {
    type: Number,
    default: 200
  },
  /** 加载器类型 */
  spinnerType: {
    type: String,
    default: 'circle',
    validator: (value) => ['circle', 'dots', 'bar', 'pulse'].includes(value)
  }
})

const {
  isLoading,
  currentLoadingMessage,
  loadingProgress,
  showGlobalOverlay,
  loadingTaskCount
} = useLoading()

const visible = ref(false)
const delayedShow = ref(false)
const showStartTime = ref(0)
let delayTimer = null
let minDisplayTimer = null

watch(isLoading, (loading) => {
  if (loading) {
    if (delayTimer) {
      clearTimeout(delayTimer)
    }
    
    delayTimer = setTimeout(() => {
      delayedShow.value = true
      visible.value = true
      showStartTime.value = Date.now()
    }, props.delayShow)
  } else {
    if (delayTimer) {
      clearTimeout(delayTimer)
      delayTimer = null
    }
    
    if (visible.value) {
      const elapsed = Date.now() - showStartTime.value
      const remaining = Math.max(0, props.minDisplayTime - elapsed)
      
      if (minDisplayTimer) {
        clearTimeout(minDisplayTimer)
      }
      
      minDisplayTimer = setTimeout(() => {
        visible.value = false
        delayedShow.value = false
      }, remaining)
    } else {
      delayedShow.value = false
    }
  }
})

const progressStyle = computed(() => ({
  width: `${loadingProgress.value}%`,
  transition: loadingProgress.value < 100 ? 'width 0.3s ease' : 'width 0.1s ease'
}))

const overlayStyle = computed(() => ({
  backgroundColor: 'rgba(255, 255, 255, 0.85)',
  backdropFilter: 'blur(4px)'
}))

const spinnerClass = computed(() => `spinner-${props.spinnerType}`)

onUnmounted(() => {
  if (delayTimer) {
    clearTimeout(delayTimer)
  }
  if (minDisplayTimer) {
    clearTimeout(minDisplayTimer)
  }
})
</script>

<template>
  <Transition name="fade">
    <div
      v-if="visible && showGlobalOverlay"
      class="global-loading-overlay"
      :style="overlayStyle"
    >
      <div class="loading-container">
        <div
          class="loading-spinner"
          :class="spinnerClass"
        >
          <div
            v-if="spinnerType === 'circle'"
            class="spinner-circle"
          />
          <div
            v-else-if="spinnerType === 'dots'"
            class="spinner-dots"
          >
            <span class="dot" />
            <span class="dot" />
            <span class="dot" />
          </div>
          <div
            v-else-if="spinnerType === 'bar'"
            class="spinner-bar"
          >
            <div class="bar" />
            <div class="bar" />
            <div class="bar" />
            <div class="bar" />
          </div>
          <div
            v-else-if="spinnerType === 'pulse'"
            class="spinner-pulse"
          />
        </div>

        <div
          v-if="showMessage && currentLoadingMessage"
          class="loading-message"
        >
          {{ currentLoadingMessage }}
        </div>

        <div
          v-if="showProgress && loadingProgress > 0"
          class="loading-progress"
        >
          <div class="progress-bar">
            <div
              class="progress-fill"
              :style="progressStyle"
            />
          </div>
          <div class="progress-text">
            {{ Math.round(loadingProgress) }}%
          </div>
        </div>

        <div
          v-if="loadingTaskCount > 1"
          class="loading-tasks"
        >
          {{ loadingTaskCount }} 个任务进行中
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.global-loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-4);
  padding: var(--spacing-6) var(--spacing-8);
  background: var(--color-surface-primary);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  min-width: 200px;
  max-width: 320px;
}

.loading-spinner {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
}

.spinner-circle {
  width: 40px;
  height: 40px;
  border: 3px solid var(--color-neutral-200);
  border-top-color: var(--color-primary-500);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.spinner-dots {
  display: flex;
  gap: 6px;
}

.spinner-dots .dot {
  width: 10px;
  height: 10px;
  background: var(--color-primary-500);
  border-radius: 50%;
  animation: bounce 1.4s ease-in-out infinite both;
}

.spinner-dots .dot:nth-child(1) {
  animation-delay: -0.32s;
}

.spinner-dots .dot:nth-child(2) {
  animation-delay: -0.16s;
}

.spinner-bar {
  display: flex;
  gap: 4px;
  align-items: flex-end;
  height: 32px;
}

.spinner-bar .bar {
  width: 6px;
  height: 100%;
  background: var(--color-primary-500);
  border-radius: 3px;
  animation: bar-stretch 1s ease-in-out infinite;
}

.spinner-bar .bar:nth-child(1) {
  animation-delay: -0.4s;
}

.spinner-bar .bar:nth-child(2) {
  animation-delay: -0.3s;
}

.spinner-bar .bar:nth-child(3) {
  animation-delay: -0.2s;
}

.spinner-bar .bar:nth-child(4) {
  animation-delay: -0.1s;
}

.spinner-pulse {
  width: 40px;
  height: 40px;
  background: var(--color-primary-500);
  border-radius: 50%;
  animation: pulse 1.2s ease-in-out infinite;
}

.loading-message {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  text-align: center;
  line-height: var(--line-height-normal);
}

.loading-progress {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
  align-items: center;
}

.progress-bar {
  width: 100%;
  height: 4px;
  background: var(--color-neutral-200);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary-500), var(--color-primary-400));
  border-radius: var(--radius-full);
}

.progress-text {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

.loading-tasks {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes bounce {
  0%,
  80%,
  100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

@keyframes bar-stretch {
  0%,
  40%,
  100% {
    transform: scaleY(0.4);
  }
  20% {
    transform: scaleY(1);
  }
}

@keyframes pulse {
  0%,
  100% {
    transform: scale(0.5);
    opacity: 0.5;
  }
  50% {
    transform: scale(1);
    opacity: 1;
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
