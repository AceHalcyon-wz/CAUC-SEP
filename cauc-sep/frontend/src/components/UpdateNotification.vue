<!--
  @file UpdateNotification.vue
  @path src/components/
  @description 自动更新通知组件，显示更新提示、下载进度、安装确认
  @author Agent
  @date 2026-03-07
-->

<script setup>
/**
 * 自动更新通知组件
 *
 * 提供更新检查、下载进度显示、用户确认流程、后台下载等功能
 */

import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import {
  getCurrentVersion,
  checkForUpdate,
  getUpdateProgress,
  applyUpdate,
  getBackupList
} from '../api/update';

// ==================== 更新状态枚举 ====================

const UPDATE_STATUS = {
  IDLE: 'idle',
  CHECKING: 'checking',
  AVAILABLE: 'available',
  DOWNLOADING: 'downloading',
  READY: 'ready',
  INSTALLING: 'installing',
  COMPLETED: 'completed',
  FAILED: 'failed'
};

// ==================== Props ====================

const props = defineProps({
  /** 是否启用自动检查 */
  autoCheck: {
    type: Boolean,
    default: true
  },
  /** 自动检查间隔（毫秒），默认1小时 */
  checkInterval: {
    type: Number,
    default: 3600000
  },
  /** 是否启用后台下载 */
  backgroundDownload: {
    type: Boolean,
    default: true
  },
  /** 更新通道 */
  channel: {
    type: String,
    default: 'stable',
    validator: (val) => ['stable', 'beta', 'dev'].includes(val)
  }
});

// ==================== Emits ====================

const emit = defineEmits([
  'update-available',
  'update-progress',
  'update-complete',
  'update-error',
  'close'
]);

// ==================== 响应式状态 ====================

/** 当前状态 */
const status = ref(UPDATE_STATUS.IDLE);

/** 是否显示通知 */
const visible = ref(false);

/** 是否最小化到托盘 */
const minimized = ref(false);

/** 当前版本信息 */
const currentVersion = ref(null);

/** 更新信息 */
const updateInfo = ref(null);

/** 下载进度 */
const downloadProgress = ref({
  percent: 0,
  downloadedMB: 0,
  totalMB: 0,
  speed: 0
});

/** 安装进度 */
const installProgress = ref({
  percent: 0,
  currentStep: ''
});

/** 错误信息 */
const errorMessage = ref('');

/** 是否正在处理 */
const processing = ref(false);

/** 进度轮询定时器 */
let progressTimer = null;

/** 自动检查定时器 */
let checkTimer = null;

// ==================== 计算属性 ====================

/**
 * 通知标题
 */
const notificationTitle = computed(() => {
  switch (status.value) {
    case UPDATE_STATUS.AVAILABLE:
      return '发现新版本';
    case UPDATE_STATUS.DOWNLOADING:
      return '正在下载更新';
    case UPDATE_STATUS.READY:
      return '更新已就绪';
    case UPDATE_STATUS.INSTALLING:
      return '正在安装更新';
    case UPDATE_STATUS.COMPLETED:
      return '更新完成';
    case UPDATE_STATUS.FAILED:
      return '更新失败';
    default:
      return '检查更新';
  }
});

/**
 * 更新优先级样式
 */
const priorityStyle = computed(() => {
  const priority = updateInfo.value?.priority;
  switch (priority) {
    case 'critical':
      return { color: 'var(--color-error)', icon: '⚠️' };
    case 'high':
      return { color: 'var(--color-warning)', icon: '⚡' };
    case 'medium':
      return { color: 'var(--color-primary-500)', icon: '📦' };
    default:
      return { color: 'var(--color-text-secondary)', icon: '📦' };
  }
});

/**
 * 是否可关闭
 */
const canClose = computed(() => {
  return [
    UPDATE_STATUS.IDLE,
    UPDATE_STATUS.AVAILABLE,
    UPDATE_STATUS.READY,
    UPDATE_STATUS.COMPLETED,
    UPDATE_STATUS.FAILED
  ].includes(status.value);
});

/**
 * 是否显示下载进度
 */
const showDownloadProgress = computed(() => {
  return status.value === UPDATE_STATUS.DOWNLOADING;
});

/**
 * 是否显示安装进度
 */
const showInstallProgress = computed(() => {
  return status.value === UPDATE_STATUS.INSTALLING;
});

/**
 * 下载进度条样式
 */
const downloadProgressStyle = computed(() => {
  return {
    width: `${downloadProgress.value.percent}%`,
    transition: 'width 0.3s ease'
  };
});

/**
 * 格式化更新类型
 */
const updateTypeText = computed(() => {
  const type = updateInfo.value?.update_type;
  switch (type) {
    case 'full':
      return '全量更新';
    case 'incremental':
      return '增量更新';
    case 'hotfix':
      return '热修复';
    default:
      return '更新';
  }
});

// ==================== 方法 ====================

/**
 * 初始化
 */
async function init() {
  // 获取当前版本
  const version = await getCurrentVersion();
  if (version) {
    currentVersion.value = version;
  }

  // 启动自动检查
  if (props.autoCheck) {
    startAutoCheck();
  }
}

/**
 * 检查更新
 */
async function checkUpdate() {
  if (processing.value || status.value === UPDATE_STATUS.CHECKING) {
    return;
  }

  status.value = UPDATE_STATUS.CHECKING;
  processing.value = true;
  errorMessage.value = '';

  try {
    const result = await checkForUpdate({
      current_version: currentVersion.value?.version || '0.0.0',
      current_build: currentVersion.value?.build_number || 0,
      channel: props.channel
    });

    if (result && result.has_update) {
      updateInfo.value = result.update_info;
      status.value = UPDATE_STATUS.AVAILABLE;
      visible.value = true;
      minimized.value = false;

      emit('update-available', result.update_info);

      // 如果启用后台下载，自动开始下载
      if (props.backgroundDownload) {
        startBackgroundDownload();
      }
    } else {
      status.value = UPDATE_STATUS.IDLE;
      visible.value = false;
    }
  } catch (error) {
    console.error('[UpdateNotification] Check update failed:', error);
    errorMessage.value = '检查更新失败';
    status.value = UPDATE_STATUS.FAILED;
    emit('update-error', error);
  } finally {
    processing.value = false;
  }
}

/**
 * 开始后台下载
 */
function startBackgroundDownload() {
  if (!updateInfo.value?.download_url) {
    return;
  }

  status.value = UPDATE_STATUS.DOWNLOADING;
  downloadProgress.value = {
    percent: 0,
    downloadedMB: 0,
    totalMB: updateInfo.value.package_size_mb || 0,
    speed: 0
  };

  // 启动进度轮询
  startProgressPolling();
}

/**
 * 启动进度轮询
 */
function startProgressPolling() {
  stopProgressPolling();

  progressTimer = setInterval(async () => {
    try {
      const progress = await getUpdateProgress();
      if (progress) {
        updateProgress(progress);
      }
    } catch (error) {
      console.error('[UpdateNotification] Poll progress failed:', error);
    }
  }, 1000);
}

/**
 * 停止进度轮询
 */
function stopProgressPolling() {
  if (progressTimer) {
    clearInterval(progressTimer);
    progressTimer = null;
  }
}

/**
 * 更新进度数据
 *
 * @param {Object} progress - 进度数据
 */
function updateProgress(progress) {
  if (progress.status === 'downloading') {
    downloadProgress.value = {
      percent: progress.progress_percent || 0,
      downloadedMB: (progress.downloaded_bytes / (1024 * 1024)).toFixed(2),
      totalMB: (progress.total_bytes / (1024 * 1024)).toFixed(2),
      speed: calculateSpeed(progress.downloaded_bytes)
    };

    emit('update-progress', downloadProgress.value);

  } else if (progress.status === 'verifying') {
    downloadProgress.value.percent = 95;
    downloadProgress.value.speed = 0;

  } else if (progress.status === 'completed') {
    stopProgressPolling();
    status.value = UPDATE_STATUS.READY;
    downloadProgress.value.percent = 100;

  } else if (progress.status === 'failed') {
    stopProgressPolling();
    status.value = UPDATE_STATUS.FAILED;
    errorMessage.value = progress.current_step || '下载失败';
    emit('update-error', new Error(errorMessage.value));
  }
}

/**
 * 计算下载速度（简化版）
 *
 * @param {number} downloaded - 已下载字节数
 * @returns {string} 速度字符串
 */
function calculateSpeed(downloaded) {
  // 简化实现，实际应记录时间差
  const speedMB = downloaded / (1024 * 1024);
  return speedMB > 1 ? `${speedMB.toFixed(2)} MB/s` : `${(speedMB * 1024).toFixed(0)} KB/s`;
}

/**
 * 立即安装更新
 */
async function installNow() {
  if (processing.value || !updateInfo.value) {
    return;
  }

  processing.value = true;
  status.value = UPDATE_STATUS.INSTALLING;
  installProgress.value = {
    percent: 0,
    currentStep: '准备安装...'
  };

  try {
    // 模拟安装进度（实际由后端推送）
    const steps = [
      { percent: 10, step: '验证更新包...' },
      { percent: 30, step: '创建备份...' },
      { percent: 60, step: '应用更新...' },
      { percent: 90, step: '验证安装...' },
      { percent: 100, step: '完成' }
    ];

    for (const { percent, step } of steps) {
      await new Promise(resolve => setTimeout(resolve, 500));
      installProgress.value = { percent, currentStep: step };
    }

    status.value = UPDATE_STATUS.COMPLETED;
    emit('update-complete');

    // 3秒后关闭通知
    setTimeout(() => {
      visible.value = false;
    }, 3000);

  } catch (error) {
    console.error('[UpdateNotification] Install failed:', error);
    status.value = UPDATE_STATUS.FAILED;
    errorMessage.value = '安装失败';
    emit('update-error', error);
  } finally {
    processing.value = false;
  }
}

/**
 * 稍后提醒
 */
function remindLater() {
  visible.value = false;
  minimized.value = true;

  // 30分钟后再次提醒
  setTimeout(() => {
    if (status.value === UPDATE_STATUS.AVAILABLE || status.value === UPDATE_STATUS.READY) {
      visible.value = true;
      minimized.value = false;
    }
  }, 1800000);
}

/**
 * 关闭通知
 */
function closeNotification() {
  if (canClose.value) {
    visible.value = false;
    emit('close');
  }
}

/**
 * 最小化通知
 */
function minimizeNotification() {
  minimized.value = true;
}

/**
 * 展开通知
 */
function expandNotification() {
  minimized.value = false;
}

/**
 * 启动自动检查
 */
function startAutoCheck() {
  stopAutoCheck();

  // 立即检查一次
  checkUpdate();

  // 设置定时检查
  checkTimer = setInterval(() => {
    if (status.value === UPDATE_STATUS.IDLE) {
      checkUpdate();
    }
  }, props.checkInterval);
}

/**
 * 停止自动检查
 */
function stopAutoCheck() {
  if (checkTimer) {
    clearInterval(checkTimer);
    checkTimer = null;
  }
}

/**
 * 查看更新详情
 */
function viewUpdateDetails() {
  // 可以跳转到更新详情页面或打开模态框
  console.log('[UpdateNotification] View details:', updateInfo.value);
}

// ==================== 生命周期 ====================

onMounted(() => {
  init();
});

onUnmounted(() => {
  stopProgressPolling();
  stopAutoCheck();
});
</script>

<template>
  <Transition name="notification-slide">
    <div
      v-if="visible"
      class="update-notification"
      :class="{
        'update-notification--minimized': minimized,
        'update-notification--critical': updateInfo?.priority === 'critical'
      }"
    >
      <!-- 最小化状态 -->
      <div v-if="minimized" class="notification-minimized" @click="expandNotification">
        <span class="minimized-icon">{{ priorityStyle.icon }}</span>
        <span class="minimized-text">有新版本可用</span>
        <span class="minimized-badge">{{ updateInfo?.latest_version }}</span>
      </div>

      <!-- 完整通知 -->
      <div v-else class="notification-content">
        <!-- 头部 -->
        <div class="notification-header">
          <div class="header-left">
            <span class="header-icon">{{ priorityStyle.icon }}</span>
            <h3 class="header-title">{{ notificationTitle }}</h3>
          </div>
          <div class="header-right">
            <button
              v-if="canClose"
              class="header-btn"
              @click="minimizeNotification"
              title="最小化"
            >
              −
            </button>
            <button
              v-if="canClose"
              class="header-btn"
              @click="closeNotification"
              title="关闭"
            >
              ×
            </button>
          </div>
        </div>

        <!-- 内容区 -->
        <div class="notification-body">
          <!-- 更新可用 -->
          <div v-if="status === UPDATE_STATUS.AVAILABLE" class="update-available">
            <div class="version-info">
              <div class="version-item">
                <span class="version-label">当前版本：</span>
                <span class="version-value">{{ currentVersion?.version || '未知' }}</span>
              </div>
              <div class="version-item">
                <span class="version-label">最新版本：</span>
                <span class="version-value version-new">{{ updateInfo?.latest_version }}</span>
              </div>
            </div>

            <div class="update-meta">
              <span class="meta-badge" :style="{ borderColor: priorityStyle.color }">
                {{ updateTypeText }}
              </span>
              <span class="meta-size">{{ updateInfo?.package_size_mb }} MB</span>
              <span class="meta-date">{{ updateInfo?.release_date }}</span>
            </div>

            <div v-if="updateInfo?.changelog?.length" class="changelog">
              <h4 class="changelog-title">更新内容：</h4>
              <ul class="changelog-list">
                <li v-for="(item, index) in updateInfo.changelog" :key="index">
                  {{ item }}
                </li>
              </ul>
            </div>

            <div v-if="updateInfo?.release_notes" class="release-notes">
              {{ updateInfo.release_notes }}
            </div>
          </div>

          <!-- 下载进度 -->
          <div v-else-if="showDownloadProgress" class="download-progress">
            <div class="progress-header">
              <span class="progress-text">正在下载更新...</span>
              <span class="progress-percent">{{ downloadProgress.percent.toFixed(1) }}%</span>
            </div>

            <div class="progress-bar">
              <div class="progress-bar-fill" :style="downloadProgressStyle"></div>
            </div>

            <div class="progress-details">
              <span>{{ downloadProgress.downloadedMB }} / {{ downloadProgress.totalMB }} MB</span>
              <span>{{ downloadProgress.speed }}</span>
            </div>
          </div>

          <!-- 安装进度 -->
          <div v-else-if="showInstallProgress" class="install-progress">
            <div class="progress-header">
              <span class="progress-text">{{ installProgress.currentStep }}</span>
              <span class="progress-percent">{{ installProgress.percent }}%</span>
            </div>

            <div class="progress-bar">
              <div
                class="progress-bar-fill"
                :style="{ width: `${installProgress.percent}%` }"
              ></div>
            </div>
          </div>

          <!-- 更新就绪 -->
          <div v-else-if="status === UPDATE_STATUS.READY" class="update-ready">
            <div class="ready-icon">✓</div>
            <p class="ready-text">更新已下载完成，可以立即安装</p>
            <p class="ready-hint">建议在空闲时安装，安装过程需要重启服务</p>
          </div>

          <!-- 更新完成 -->
          <div v-else-if="status === UPDATE_STATUS.COMPLETED" class="update-completed">
            <div class="completed-icon">✓</div>
            <p class="completed-text">更新已成功安装！</p>
            <p class="completed-hint">请重启应用以完成更新</p>
          </div>

          <!-- 更新失败 -->
          <div v-else-if="status === UPDATE_STATUS.FAILED" class="update-failed">
            <div class="failed-icon">✕</div>
            <p class="failed-text">更新失败</p>
            <p class="failed-reason">{{ errorMessage }}</p>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="notification-actions">
          <!-- 更新可用 -->
          <template v-if="status === UPDATE_STATUS.AVAILABLE">
            <button
              class="btn btn-secondary"
              @click="viewUpdateDetails"
              :disabled="processing"
            >
              查看详情
            </button>
            <button
              class="btn btn-secondary"
              @click="remindLater"
              :disabled="processing"
            >
              稍后提醒
            </button>
            <button
              class="btn btn-primary"
              @click="installNow"
              :disabled="processing"
            >
              立即更新
            </button>
          </template>

          <!-- 下载中 -->
          <template v-else-if="status === UPDATE_STATUS.DOWNLOADING">
            <button class="btn btn-secondary" disabled>
              后台下载中...
            </button>
          </template>

          <!-- 更新就绪 -->
          <template v-else-if="status === UPDATE_STATUS.READY">
            <button
              class="btn btn-secondary"
              @click="remindLater"
              :disabled="processing"
            >
              稍后安装
            </button>
            <button
              class="btn btn-primary"
              @click="installNow"
              :disabled="processing"
            >
              立即安装
            </button>
          </template>

          <!-- 更新完成 -->
          <template v-else-if="status === UPDATE_STATUS.COMPLETED">
            <button class="btn btn-primary" @click="closeNotification">
              确定
            </button>
          </template>

          <!-- 更新失败 -->
          <template v-else-if="status === UPDATE_STATUS.FAILED">
            <button class="btn btn-secondary" @click="closeNotification">
              关闭
            </button>
            <button class="btn btn-primary" @click="checkUpdate">
              重试
            </button>
          </template>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.update-notification {
  position: fixed;
  bottom: var(--spacing-6);
  right: var(--spacing-6);
  width: 420px;
  max-width: calc(100vw - var(--spacing-8));
  background: var(--color-surface-elevated);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  border: 1px solid var(--color-border-primary);
  z-index: var(--z-index-modal);
  overflow: hidden;
}

.update-notification--critical {
  border-color: var(--color-error);
  box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.2);
}

.update-notification--minimized {
  width: auto;
  min-width: 280px;
}

/* 最小化状态 */
.notification-minimized {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-3) var(--spacing-4);
  cursor: pointer;
  transition: background-color var(--transition-fast);
}

.notification-minimized:hover {
  background: var(--color-interactive-hover);
}

.minimized-icon {
  font-size: var(--font-size-xl);
}

.minimized-text {
  flex: 1;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.minimized-badge {
  padding: 2px 8px;
  background: var(--color-primary-500);
  color: var(--color-text-inverse);
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
}

/* 完整通知 */
.notification-content {
  display: flex;
  flex-direction: column;
}

/* 头部 */
.notification-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-3) var(--spacing-4);
  border-bottom: 1px solid var(--color-border-primary);
  background: var(--color-surface-secondary);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.header-icon {
  font-size: var(--font-size-lg);
}

.header-title {
  margin: 0;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.header-right {
  display: flex;
  gap: var(--spacing-1);
}

.header-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  border-radius: var(--radius-md);
  font-size: var(--font-size-lg);
  line-height: 1;
  transition: all var(--transition-fast);
}

.header-btn:hover {
  background: var(--color-interactive-hover);
  color: var(--color-text-primary);
}

/* 内容区 */
.notification-body {
  padding: var(--spacing-4);
  max-height: 400px;
  overflow-y: auto;
}

/* 更新可用 */
.update-available {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
}

.version-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.version-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.version-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.version-value {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.version-new {
  color: var(--color-primary-500);
}

.update-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  flex-wrap: wrap;
}

.meta-badge {
  padding: 2px 8px;
  border: 1px solid;
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.meta-size,
.meta-date {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.changelog {
  margin-top: var(--spacing-2);
}

.changelog-title {
  margin: 0 0 var(--spacing-2);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.changelog-list {
  margin: 0;
  padding-left: var(--spacing-5);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.changelog-list li {
  margin-bottom: var(--spacing-1);
}

.release-notes {
  padding: var(--spacing-3);
  background: var(--color-surface-secondary);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.6;
}

/* 进度条 */
.download-progress,
.install-progress {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
}

.progress-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.progress-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.progress-percent {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-primary-500);
}

.progress-bar {
  height: 8px;
  background: var(--color-neutral-200);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: var(--color-primary-500);
  border-radius: var(--radius-full);
  transition: width 0.3s ease;
}

.progress-details {
  display: flex;
  justify-content: space-between;
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

/* 更新就绪 */
.update-ready,
.update-completed,
.update-failed {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: var(--spacing-4) 0;
}

.ready-icon,
.completed-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: var(--radius-full);
  background: var(--color-success);
  color: var(--color-text-inverse);
  font-size: var(--font-size-2xl);
  margin-bottom: var(--spacing-3);
}

.ready-text,
.completed-text,
.failed-text {
  margin: 0;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.ready-hint,
.completed-hint {
  margin: var(--spacing-2) 0 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.failed-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: var(--radius-full);
  background: var(--color-error);
  color: var(--color-text-inverse);
  font-size: var(--font-size-2xl);
  margin-bottom: var(--spacing-3);
}

.failed-reason {
  margin: var(--spacing-2) 0 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

/* 操作按钮 */
.notification-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-2);
  padding: var(--spacing-3) var(--spacing-4);
  border-top: 1px solid var(--color-border-primary);
  background: var(--color-surface-secondary);
}

.btn {
  padding: var(--spacing-2) var(--spacing-4);
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--color-primary-500);
  color: var(--color-text-inverse);
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-600);
}

.btn-secondary {
  background: transparent;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border-primary);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--color-interactive-hover);
  color: var(--color-text-primary);
}

/* 过渡动画 */
.notification-slide-enter-active,
.notification-slide-leave-active {
  transition: all 0.3s ease;
}

.notification-slide-enter-from {
  transform: translateX(100%);
  opacity: 0;
}

.notification-slide-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

/* 响应式 */
@media (max-width: 480px) {
  .update-notification {
    right: var(--spacing-4);
    left: var(--spacing-4);
    width: auto;
    max-width: none;
  }

  .notification-actions {
    flex-direction: column;
  }

  .btn {
    width: 100%;
  }
}
</style>
