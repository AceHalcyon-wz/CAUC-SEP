<script setup lang="ts">
/**
 * @file GlassCard.vue
 * @path src/components/common/cards/GlassCard.vue
 * @description 玻璃态卡片组件
 * @author Agent
 * @date 2026-03-25
 */

import { computed } from 'vue'

interface Props {
  title?: string
  subtitle?: string
  padding?: string
  shadow?: 'always' | 'hover' | 'never'
  glass?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  title: '',
  subtitle: '',
  padding: '20px',
  shadow: 'hover',
  glass: true,
})

const cardClass = computed(() => [
  'glass-card',
  `glass-card--shadow-${props.shadow}`,
  {
    'glass-card--glass': props.glass,
  },
])

const cardStyle = computed(() => ({
  padding: props.padding,
}))
</script>

<template>
  <div :class="cardClass" :style="cardStyle">
    <div v-if="title || $slots.header" class="glass-card__header">
      <slot name="header">
        <div class="header-content">
          <h3 class="header-title">{{ title }}</h3>
          <p v-if="subtitle" class="header-subtitle">{{ subtitle }}</p>
        </div>
      </slot>
    </div>
    <div class="glass-card__body">
      <slot />
    </div>
    <div v-if="$slots.footer" class="glass-card__footer">
      <slot name="footer" />
    </div>
  </div>
</template>

<style scoped lang="scss">
.glass-card {
  border-radius: 16px;
  background: var(--color-bg-card, rgba(255, 255, 255, 0.8));
  border: 1px solid var(--color-border-light, rgba(255, 255, 255, 0.2));
  transition: all 0.3s ease;

  &--glass {
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
  }

  &--shadow-always {
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  }

  &--shadow-hover {
    &:hover {
      box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
      transform: translateY(-2px);
    }
  }

  &--shadow-never {
    box-shadow: none;
  }

  &__header {
    padding-bottom: 16px;
    border-bottom: 1px solid var(--color-border-light, rgba(0, 0, 0, 0.05));
    margin-bottom: 16px;

    .header-content {
      .header-title {
        font-size: 18px;
        font-weight: 600;
        color: var(--color-text-primary);
        margin: 0;
      }

      .header-subtitle {
        font-size: 14px;
        color: var(--color-text-secondary);
        margin: 4px 0 0;
      }
    }
  }

  &__body {
    flex: 1;
  }

  &__footer {
    padding-top: 16px;
    border-top: 1px solid var(--color-border-light, rgba(0, 0, 0, 0.05));
    margin-top: 16px;
  }
}
</style>
