<script setup lang="ts">
/**
 * @file StatusCard.vue
 * @path src/components/common/cards/StatusCard.vue
 * @description 状态卡片组件，用于显示设备状态摘要
 * @author Agent
 * @date 2026-03-25
 */

import { computed } from 'vue'
import GlassCard from './GlassCard.vue'
import StatusIndicator from '../status/StatusIndicator.vue'

type StatusType = 'success' | 'warning' | 'danger' | 'info' | 'default'

interface StatusItem {
  label: string
  value: string | number
  unit?: string
  status?: StatusType
}

interface Props {
  title: string
  status: StatusType
  statusLabel?: string
  items: StatusItem[]
  icon?: string
}

const props = defineProps<Props>()
</script>

<template>
  <GlassCard class="status-card">
    <template #header>
      <div class="status-card__header">
        <div class="header-left">
          <span v-if="icon" class="header-icon" v-html="icon" />
          <h3 class="header-title">{{ title }}</h3>
        </div>
        <StatusIndicator :status="status" :label="statusLabel" pulse />
      </div>
    </template>

    <div class="status-card__content">
      <div v-for="item in items" :key="item.label" class="status-item">
        <span class="status-item__label">{{ item.label }}</span>
        <span class="status-item__value">
          {{ item.value }}
          <span v-if="item.unit" class="status-item__unit">{{ item.unit }}</span>
        </span>
        <StatusIndicator v-if="item.status" :status="item.status" :show-dot="true" />
      </div>
    </div>

    <template v-if="$slots.footer" #footer>
      <slot name="footer" />
    </template>
  </GlassCard>
</template>

<style scoped lang="scss">
.status-card {
  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;

    .header-left {
      display: flex;
      align-items: center;
      gap: 8px;

      .header-icon {
        font-size: 20px;
      }

      .header-title {
        font-size: 16px;
        font-weight: 600;
        color: var(--color-text-primary);
        margin: 0;
      }
    }
  }

  &__content {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 16px;

    .status-item {
      display: flex;
      flex-direction: column;
      gap: 4px;

      &__label {
        font-size: 12px;
        color: var(--color-text-secondary);
      }

      &__value {
        font-size: 20px;
        font-weight: 600;
        color: var(--color-text-primary);

        .status-item__unit {
          font-size: 14px;
          font-weight: 400;
          color: var(--color-text-secondary);
          margin-left: 4px;
        }
      }
    }
  }
}
</style>
