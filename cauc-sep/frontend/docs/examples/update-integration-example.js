/**
 * @file update-integration-example.js
 * @path docs/examples/
 * @description 自动更新系统集成示例
 * @author Agent
 * @date 2026-03-07
 */

import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useUpdateStore, UPDATE_STATUS } from '@/stores/update';

/**
 * 自动更新组合式函数
 *
 * @param {Object} options - 配置选项
 * @param {boolean} [options.autoCheck=true] - 是否自动检查
 * @param {number} [options.checkInterval=3600000] - 检查间隔（毫秒）
 * @param {string} [options.channel='stable'] - 更新通道
 * @returns {Object} 更新相关状态和方法
 */
export function useAutoUpdate(options = {}) {
  const {
    autoCheck = true,
    checkInterval: _checkInterval = 3600000,
    channel = 'stable'
  } = options;

  const updateStore = useUpdateStore();

  const visible = ref(false);
  const notification = ref(null);

  const hasUpdate = computed(() => updateStore.hasUpdate);
  const isUpdating = computed(() => updateStore.isUpdating);
  const status = computed(() => updateStore.status);
  const progress = computed(() => updateStore.downloadProgress);
  const updateInfo = computed(() => updateStore.updateInfo);
  const currentVersion = computed(() => updateStore.currentVersion);

  async function checkUpdate() {
    await updateStore.checkUpdate();
    if (updateStore.hasUpdate) {
      visible.value = true;
    }
  }

  async function applyUpdate() {
    await updateStore.applyUpdate();
  }

  function showNotification() {
    visible.value = true;
  }

  function hideNotification() {
    visible.value = false;
  }

  function setChannel(newChannel) {
    updateStore.setChannel(newChannel);
  }

  function setAutoCheck(enabled) {
    updateStore.setAutoCheckEnabled(enabled);
  }

  onMounted(() => {
    updateStore.setChannel(channel);
    if (autoCheck) {
      updateStore.setAutoCheckEnabled(true);
      updateStore.startAutoCheck();
    }
  });

  onUnmounted(() => {
    updateStore.stopAutoCheck();
  });

  return {
    visible,
    hasUpdate,
    isUpdating,
    status,
    progress,
    updateInfo,
    currentVersion,
    notification,
    checkUpdate,
    applyUpdate,
    showNotification,
    hideNotification,
    setChannel,
    setAutoCheck,
    UPDATE_STATUS
  };
}

/**
 * 更新通知服务
 */
export class UpdateNotificationService {
  constructor() {
    this.permission = Notification.permission;
  }

  async requestPermission() {
    if (this.permission === 'default') {
      this.permission = await Notification.requestPermission();
    }
    return this.permission === 'granted';
  }

  async showUpdateAvailable(updateInfo) {
    if (await this.requestPermission()) {
      const notification = new Notification('发现新版本', {
        body: `版本 ${updateInfo.latest_version} 已发布\n${updateInfo.release_notes}`,
        icon: '/logo.png',
        tag: 'update-available',
        requireInteraction: true
      });

      notification.onclick = () => {
        window.focus();
        notification.close();
      };
    }
  }

  async showUpdateComplete() {
    if (await this.requestPermission()) {
      new Notification('更新完成', {
        body: '更新已成功安装，请重启应用',
        icon: '/logo.png',
        tag: 'update-complete'
      });
    }
  }

  playSound() {
    const audio = new Audio('/sounds/notification.mp3');
    audio.volume = 0.5;
    audio.play().catch(err => {
      console.warn('[UpdateNotification] Failed to play sound:', err);
    });
  }
}

export const UPDATE_CONFIG = {
  CHANNELS: {
    STABLE: 'stable',
    BETA: 'beta',
    DEV: 'dev'
  },
  CHECK_INTERVALS: {
    HOURLY: 3600000,
    DAILY: 86400000,
    WEEKLY: 604800000
  },
  PRIORITIES: {
    LOW: 'low',
    MEDIUM: 'medium',
    HIGH: 'high',
    CRITICAL: 'critical'
  },
  STATUS: UPDATE_STATUS
};

export function getUpdateConfig() {
  return {
    autoCheck: localStorage.getItem('update_autoCheck') !== 'false',
    checkInterval: parseInt(localStorage.getItem('update_checkInterval')) || 3600000,
    channel: localStorage.getItem('update_channel') || 'stable',
    backgroundDownload: localStorage.getItem('update_backgroundDownload') !== 'false'
  };
}

export function saveUpdateConfig(config) {
  if (config.autoCheck !== undefined) {
    localStorage.setItem('update_autoCheck', String(config.autoCheck));
  }
  if (config.checkInterval !== undefined) {
    localStorage.setItem('update_checkInterval', String(config.checkInterval));
  }
  if (config.channel !== undefined) {
    localStorage.setItem('update_channel', config.channel);
  }
  if (config.backgroundDownload !== undefined) {
    localStorage.setItem('update_backgroundDownload', String(config.backgroundDownload));
  }
}
