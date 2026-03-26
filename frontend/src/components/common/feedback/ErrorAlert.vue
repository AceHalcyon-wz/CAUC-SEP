<script setup lang="ts">
/**
 * @file ErrorAlert.vue
 * @path src/components/common/feedback/ErrorAlert.vue
 * @description 错误提示组件
 * @author Agent
 * @date 2026-03-25
 */

import { computed } from 'vue'

type ErrorType = 'error' | 'warning' | 'info' | 'success'

interface Props {
  type?: ErrorType
  title?: string
  message: string
  showIcon?: boolean
  closable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  type: 'error',
  title: '',
  showIcon: true,
  closable: false,
})

const emit = defineEmits<{
  (e: 'close'): void
}>()

const alertClass = computed(() => ['error-alert', `error-alert--${props.type}`])

const iconMap: Record<ErrorType, string> = {
  error: '❌',
  warning: '⚠️',
  info: 'ℹ️',
  success: '✅',
}
</script>

<template>
  <div :class="alertClass">
    <span v-if="showIcon" class="alert-icon">{{ iconMap[type] }}</span>
    <div class="alert-content">
      <h4 v-if="title" class="alert-title">{{ title }}</h4>
      <p class="alert-message">{{ message }}</p>
      <slot />
    </div>
    <button v-if="closable" class="alert-close" @click="emit('close')">×</button>
  </div>
</template>

<style scoped lang="scss">
.error-alert {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  border-radius: 8px;
  font-size: 14px;

  &--error {
    background-color: rgba(245, 108, 108, 0.1);
    border: 1px solid rgba(245, 108, 108, 0.3);
    color: #f56c6c;
  }

  &--warning {
    background-color: rgba(230, 162, 60, 0.1);
    border: 1px solid rgba(230, 162, 60, 0.3);
    color: #e6a23c;
  }

  &--info {
    background-color: rgba(144, 147, 153, 0.1);
    border: 1px solid rgba(144, 147, 153, 0.3);
    color: #909399;
  }

  &--success {
    background-color: rgba(103, 194, 58, 0.1);
    border: 1px solid rgba(103, 194, 58, 0.3);
    color: #67c23a;
  }

  .alert-icon {
    font-size: 18px;
    flex-shrink: 0;
  }

  .alert-content {
    flex: 1;

    .alert-title {
      font-size: 16px;
      font-weight: 600;
      margin: 0 0 4px;
    }

    .alert-message {
      margin: 0;
      line-height: 1.5;
    }
  }

  .alert-close {
    background: none;
    border: none;
    font-size: 20px;
    cursor: pointer;
    opacity: 0.6;
    transition: opacity 0.2s;
    padding: 0;
    line-height: 1;

    &:hover {
      opacity: 1;
    }
  }
}
</style>
