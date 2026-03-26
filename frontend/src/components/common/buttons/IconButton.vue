<script setup lang="ts">
/**
 * @file IconButton.vue
 * @path src/components/common/buttons/IconButton.vue
 * @description 通用图标按钮组件
 * @author Agent
 * @date 2026-03-25
 */

import { computed } from 'vue'

interface Props {
  icon?: string
  iconClass?: string
  type?: 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'default'
  size?: 'small' | 'default' | 'large'
  disabled?: boolean
  loading?: boolean
  tooltip?: string
}

const props = withDefaults(defineProps<Props>(), {
  icon: '',
  iconClass: '',
  type: 'default',
  size: 'default',
  disabled: false,
  loading: false,
  tooltip: '',
})

const emit = defineEmits<{
  (e: 'click', event: MouseEvent): void
}>()

const buttonClass = computed(() => [
  'icon-button',
  `icon-button--${props.type}`,
  `icon-button--${props.size}`,
  {
    'is-disabled': props.disabled,
    'is-loading': props.loading,
  },
])

function handleClick(event: MouseEvent): void {
  if (!props.disabled && !props.loading) {
    emit('click', event)
  }
}
</script>

<template>
  <el-tooltip v-if="tooltip" :content="tooltip" placement="top">
    <button
      :class="buttonClass"
      :disabled="disabled || loading"
      @click="handleClick"
    >
      <i v-if="loading" class="el-icon-loading" />
      <i v-else-if="icon" :class="['icon', iconClass]" v-html="icon" />
      <slot />
    </button>
  </el-tooltip>
  <button
    v-else
    :class="buttonClass"
    :disabled="disabled || loading"
    @click="handleClick"
  >
    <i v-if="loading" class="el-icon-loading" />
    <i v-else-if="icon" :class="['icon', iconClass]" v-html="icon" />
    <slot />
  </button>
</template>

<style scoped lang="scss">
.icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;

  &--small {
    width: 28px;
    height: 28px;
    font-size: 14px;
  }

  &--default {
    width: 36px;
    height: 36px;
    font-size: 16px;
  }

  &--large {
    width: 44px;
    height: 44px;
    font-size: 18px;
  }

  &--default {
    background: var(--color-bg-secondary);
    color: var(--color-text-primary);

    &:hover:not(.is-disabled) {
      background: var(--color-bg-tertiary);
    }
  }

  &--primary {
    background: var(--color-primary);
    color: #fff;

    &:hover:not(.is-disabled) {
      background: var(--color-primary-light);
    }
  }

  &--success {
    background: var(--color-success);
    color: #fff;

    &:hover:not(.is-disabled) {
      background: var(--color-success-light);
    }
  }

  &--warning {
    background: var(--color-warning);
    color: #fff;

    &:hover:not(.is-disabled) {
      background: var(--color-warning-light);
    }
  }

  &--danger {
    background: var(--color-danger);
    color: #fff;

    &:hover:not(.is-disabled) {
      background: var(--color-danger-light);
    }
  }

  &--info {
    background: var(--color-info);
    color: #fff;

    &:hover:not(.is-disabled) {
      background: var(--color-info-light);
    }
  }

  &.is-disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &.is-loading {
    cursor: wait;
  }
}
</style>
