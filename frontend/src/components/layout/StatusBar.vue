/**
 * @file StatusBar.vue
 * @path src/components/layout/
 * @description 状态栏组件 - 显示系统状态和快捷信息
 * @author Agent
 * @date 2024-03-15
 * @version 3.5.1
 */

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  WifiOutlined,
  ClockCircleOutlined,
  DatabaseOutlined,
  SafetyOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons-vue';
import { useDevicesStore } from '../../stores/devices';

const { t } = useI18n();
const devicesStore = useDevicesStore();

/**
 * 当前时间
 */
const currentTime = computed(() => {
  return new Date().toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
});

/**
 * 系统状态
 */
const systemStatus = computed(() => {
  const connectedCount = devicesStore.connectedDevices?.length || 0;
  const totalCount = devicesStore.devices?.length || 0;
  
  if (connectedCount === totalCount && totalCount > 0) {
    return { type: 'success', text: t('status.normal'), icon: CheckCircleOutlined };
  } else if (connectedCount > 0) {
    return { type: 'warning', text: t('status.warning'), icon: ExclamationCircleOutlined };
  }
  return { type: 'error', text: t('status.error'), icon: ExclamationCircleOutlined };
});

/**
 * 连接设备数量
 */
const deviceCount = computed(() => {
  return `${devicesStore.connectedDevices?.length || 0}/${devicesStore.devices?.length || 0}`;
});
</script>

<template>
  <div class="status-bar">
    <div class="status-bar__left">
      <!-- 系统状态 -->
      <div
        class="status-bar__item"
        :class="`status-bar__item--${systemStatus.type}`"
      >
        <component :is="systemStatus.icon" />
        <span>{{ systemStatus.text }}</span>
      </div>
      
      <!-- 设备连接数 -->
      <div class="status-bar__item">
        <DatabaseOutlined />
        <span>{{ t('device.status') }}: {{ deviceCount }}</span>
      </div>
    </div>
    
    <div class="status-bar__right">
      <!-- 安全状态 -->
      <div class="status-bar__item status-bar__item--success">
        <SafetyOutlined />
        <span>安全</span>
      </div>
      
      <!-- 当前时间 -->
      <div class="status-bar__item">
        <ClockCircleOutlined />
        <span>{{ currentTime }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-2) var(--spacing-4);
  background: var(--color-bg-secondary);
  border-top: 1px solid var(--color-border-primary);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.status-bar__left,
.status-bar__right {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
}

.status-bar__item {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
}

.status-bar__item--success {
  color: var(--color-success);
}

.status-bar__item--warning {
  color: var(--color-warning);
}

.status-bar__item--error {
  color: var(--color-error);
}

@media (max-width: 768px) {
  .status-bar {
    padding: var(--spacing-2);
    font-size: var(--font-size-xs);
  }
  
  .status-bar__left,
  .status-bar__right {
    gap: var(--spacing-2);
  }
}
</style>
