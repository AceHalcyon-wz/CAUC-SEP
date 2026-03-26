<script setup lang="ts">
/**
 * @file AlarmBanner.vue
 * @path src/components/common/status/AlarmBanner.vue
 * @description 报警横幅组件，用于显示设备报警信息
 * @author Agent
 * @date 2026-03-25
 * @safety: 报警信息必须实时显示，支持一键清除报警
 */

import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'

type AlarmLevel = 'info' | 'warning' | 'danger' | 'critical'

interface AlarmInfo {
  id: string
  code: number
  message: string
  level: AlarmLevel
  timestamp: Date
  deviceName?: string
}

interface Props {
  alarms: AlarmInfo[]
  showDismiss?: boolean
  autoHide?: boolean
  autoHideDelay?: number
}

const props = withDefaults(defineProps<Props>(), {
  showDismiss: true,
  autoHide: false,
  autoHideDelay: 5000,
})

const emit = defineEmits<{
  (e: 'dismiss', alarmId: string): void
  (e: 'dismiss-all'): void
  (e: 'click', alarm: AlarmInfo): void
}>()

const visibleAlarms = ref<AlarmInfo[]>([...props.alarms])

watch(
  () => props.alarms,
  (newAlarms) => {
    visibleAlarms.value = [...newAlarms]
  },
  { deep: true }
)

const hasAlarms = computed(() => visibleAlarms.value.length > 0)

const highestLevel = computed((): AlarmLevel => {
  const levelPriority: Record<AlarmLevel, number> = {
    info: 0,
    warning: 1,
    danger: 2,
    critical: 3,
  }
  if (visibleAlarms.value.length === 0) return 'info'
  return visibleAlarms.value.reduce((highest, alarm) => {
    return levelPriority[alarm.level] > levelPriority[highest] ? alarm.level : highest
  }, 'info' as AlarmLevel)
})

const bannerClass = computed(() => [
  'alarm-banner',
  `alarm-banner--${highestLevel.value}`,
])

const levelColors: Record<AlarmLevel, string> = {
  info: '#909399',
  warning: '#e6a23c',
  danger: '#f56c6c',
  critical: '#ff0000',
}

function handleDismiss(alarmId: string): void {
  visibleAlarms.value = visibleAlarms.value.filter((a) => a.id !== alarmId)
  emit('dismiss', alarmId)
}

function handleDismissAll(): void {
  visibleAlarms.value = []
  emit('dismiss-all')
}

function handleClick(alarm: AlarmInfo): void {
  emit('click', alarm)
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
</script>

<template>
  <Transition name="slide-down">
    <div v-if="hasAlarms" :class="bannerClass">
      <div class="alarm-banner__content">
        <div class="alarm-icon">
          <span v-if="highestLevel === 'critical'">🚨</span>
          <span v-else-if="highestLevel === 'danger'">⚠️</span>
          <span v-else-if="highestLevel === 'warning'">⚡</span>
          <span v-else>ℹ️</span>
        </div>

        <div class="alarm-list">
          <div
            v-for="alarm in visibleAlarms"
            :key="alarm.id"
            class="alarm-item"
            @click="handleClick(alarm)"
          >
            <span class="alarm-code">[{{ alarm.code }}]</span>
            <span class="alarm-message">{{ alarm.message }}</span>
            <span v-if="alarm.deviceName" class="alarm-device">({{ alarm.deviceName }})</span>
            <span class="alarm-time">{{ formatTime(alarm.timestamp) }}</span>
          </div>
        </div>

        <div v-if="showDismiss" class="alarm-actions">
          <el-button
            v-if="visibleAlarms.length > 1"
            size="small"
            type="text"
            @click="handleDismissAll"
          >
            清除全部
          </el-button>
          <el-button
            v-else
            size="small"
            type="text"
            @click="handleDismiss(visibleAlarms[0].id)"
          >
            清除
          </el-button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped lang="scss">
.alarm-banner {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 2000;
  padding: 12px 24px;
  color: #fff;
  font-weight: 500;

  &--info {
    background: linear-gradient(90deg, #909399, #a6a9ad);
  }

  &--warning {
    background: linear-gradient(90deg, #e6a23c, #f0c78a);
  }

  &--danger {
    background: linear-gradient(90deg, #f56c6c, #fab6b6);
  }

  &--critical {
    background: linear-gradient(90deg, #ff0000, #ff6666);
    animation: critical-pulse 1s infinite;
  }

  &__content {
    display: flex;
    align-items: center;
    gap: 16px;
    max-width: 1400px;
    margin: 0 auto;
  }

  .alarm-icon {
    font-size: 24px;
    flex-shrink: 0;
  }

  .alarm-list {
    flex: 1;
    overflow: hidden;

    .alarm-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 4px 0;
      cursor: pointer;

      &:hover {
        opacity: 0.9;
      }

      .alarm-code {
        font-weight: bold;
        opacity: 0.9;
      }

      .alarm-message {
        flex: 1;
      }

      .alarm-device {
        opacity: 0.8;
        font-size: 12px;
      }

      .alarm-time {
        opacity: 0.7;
        font-size: 12px;
      }
    }
  }

  .alarm-actions {
    flex-shrink: 0;

    .el-button {
      color: #fff;
    }
  }
}

@keyframes critical-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.8;
  }
}

.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.3s ease;
}

.slide-down-enter-from,
.slide-down-leave-to {
  transform: translateY(-100%);
  opacity: 0;
}
</style>
