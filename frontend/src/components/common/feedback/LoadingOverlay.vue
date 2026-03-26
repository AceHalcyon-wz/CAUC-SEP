<script setup lang="ts">
/**
 * @file LoadingOverlay.vue
 * @path src/components/common/feedback/LoadingOverlay.vue
 * @description 加载遮罩组件
 * @author Agent
 * @date 2026-03-25
 */

import { computed } from 'vue'

interface Props {
  visible: boolean
  text?: string
  background?: string
  spinner?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  visible: false,
  text: '加载中...',
  background: 'rgba(255, 255, 255, 0.9)',
  spinner: true,
})

const overlayStyle = computed(() => ({
  background: props.background,
}))
</script>

<template>
  <Transition name="fade">
    <div v-if="visible" class="loading-overlay" :style="overlayStyle">
      <div class="loading-content">
        <div v-if="spinner" class="loading-spinner">
          <div class="spinner-ring" />
          <div class="spinner-ring" />
          <div class="spinner-ring" />
        </div>
        <p v-if="text" class="loading-text">{{ text }}</p>
        <slot />
      </div>
    </div>
  </Transition>
</template>

<style scoped lang="scss">
.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  border-radius: inherit;

  .loading-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;

    .loading-spinner {
      position: relative;
      width: 48px;
      height: 48px;

      .spinner-ring {
        position: absolute;
        width: 100%;
        height: 100%;
        border-radius: 50%;
        border: 3px solid transparent;
        border-top-color: var(--color-primary);
        animation: spin 1.2s cubic-bezier(0.5, 0, 0.5, 1) infinite;

        &:nth-child(1) {
          animation-delay: -0.3s;
        }

        &:nth-child(2) {
          animation-delay: -0.15s;
          width: 80%;
          height: 80%;
          top: 10%;
          left: 10%;
        }

        &:nth-child(3) {
          width: 60%;
          height: 60%;
          top: 20%;
          left: 20%;
        }
      }
    }

    .loading-text {
      font-size: 14px;
      color: var(--color-text-secondary);
      margin: 0;
    }
  }
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
