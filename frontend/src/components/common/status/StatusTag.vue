<script setup lang="ts">
/**
 * @file StatusTag.vue
 * @path src/components/common/status/StatusTag.vue
 * @description 状态标签组件
 * @author Agent
 * @date 2026-03-25
 */

import { computed } from 'vue'

type TagType = 'success' | 'warning' | 'danger' | 'info' | 'default'
type TagSize = 'small' | 'default' | 'large'

interface Props {
  type?: TagType
  size?: TagSize
  label: string
  icon?: string
  round?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  type: 'default',
  size: 'default',
  icon: '',
  round: false,
})

const tagClass = computed(() => [
  'status-tag',
  `status-tag--${props.type}`,
  `status-tag--${props.size}`,
  {
    'is-round': props.round,
  },
])
</script>

<template>
  <span :class="tagClass">
    <i v-if="icon" class="tag-icon" v-html="icon" />
    <span class="tag-label">{{ label }}</span>
  </span>
</template>

<style scoped lang="scss">
.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  border-radius: 4px;
  font-weight: 500;

  &--small {
    font-size: 12px;
    padding: 2px 8px;
  }

  &--default {
    font-size: 14px;
  }

  &--large {
    font-size: 16px;
    padding: 6px 16px;
  }

  &--success {
    background-color: rgba(103, 194, 58, 0.1);
    color: #67c23a;
    border: 1px solid rgba(103, 194, 58, 0.2);
  }

  &--warning {
    background-color: rgba(230, 162, 60, 0.1);
    color: #e6a23c;
    border: 1px solid rgba(230, 162, 60, 0.2);
  }

  &--danger {
    background-color: rgba(245, 108, 108, 0.1);
    color: #f56c6c;
    border: 1px solid rgba(245, 108, 108, 0.2);
  }

  &--info {
    background-color: rgba(144, 147, 153, 0.1);
    color: #909399;
    border: 1px solid rgba(144, 147, 153, 0.2);
  }

  &--default {
    background-color: rgba(192, 196, 204, 0.1);
    color: #c0c4cc;
    border: 1px solid rgba(192, 196, 204, 0.2);
  }

  &.is-round {
    border-radius: 20px;
  }

  .tag-icon {
    font-size: 1em;
  }
}
</style>
