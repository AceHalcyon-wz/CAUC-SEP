/**
 * @file update.js
 * @path src/stores/
 * @description 自动更新状态管理Store
 * @author Agent
 * @date 2026-03-07
 * @dependencies pinia, @/api/update
 */

import { defineStore } from 'pinia';
import {
  getCurrentVersion,
  checkForUpdate,
  getUpdateProgress,
  applyUpdate,
  getBackupList,
  createManualBackup,
  deleteBackup,
  getUpdateHistory,
  cleanupOldBackups
} from '../api/update';

/**
 * 更新状态枚举
 */
export const UPDATE_STATUS = {
  IDLE: 'idle',
  CHECKING: 'checking',
  AVAILABLE: 'available',
  DOWNLOADING: 'downloading',
  VERIFYING: 'verifying',
  INSTALLING: 'installing',
  COMPLETED: 'completed',
  FAILED: 'failed',
  ROLLING_BACK: 'rolling_back'
};

/**
 * 更新优先级枚举
 */
export const UPDATE_PRIORITY = {
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
  CRITICAL: 'critical'
};

/**
 * 自动更新Store
 */
export const useUpdateStore = defineStore('update', {
  state: () => ({
    // ==================== 版本信息 ====================

    /** 当前版本信息 */
    currentVersion: null,

    /** 更新信息 */
    updateInfo: null,

    /** 更新状态 */
    status: UPDATE_STATUS.IDLE,

    // ==================== 进度信息 ====================

    /** 下载进度 */
    downloadProgress: {
      percent: 0,
      downloadedBytes: 0,
      totalBytes: 0,
      speed: 0,
      estimatedTime: 0
    },

    /** 安装进度 */
    installProgress: {
      percent: 0,
      currentStep: '',
      startedAt: null
    },

    // ==================== 备份管理 ====================

    /** 备份列表 */
    backups: [],

    /** 更新历史 */
    updateHistory: [],

    // ==================== 配置 ====================

    /** 更新通道 */
    channel: 'stable',

    /** 自动检查间隔（毫秒） */
    autoCheckInterval: 3600000, // 1小时

    /** 是否启用自动检查 */
    autoCheckEnabled: true,

    /** 是否启用后台下载 */
    backgroundDownloadEnabled: true,

    // ==================== 内部状态 ====================

    /** 错误信息 */
    error: null,

    /** 是否正在处理 */
    processing: false,

    /** 进度轮询定时器 */
    _progressTimer: null,

    /** 自动检查定时器 */
    _checkTimer: null,

    /** 上次检查时间 */
    lastCheckTime: null
  }),

  getters: {
    /**
     * 是否有可用更新
     */
    hasUpdate: (state) => {
      return state.status === UPDATE_STATUS.AVAILABLE ||
             state.status === UPDATE_STATUS.READY ||
             state.status === UPDATE_STATUS.DOWNLOADING;
    },

    /**
     * 是否正在更新
     */
    isUpdating: (state) => {
      return [
        UPDATE_STATUS.CHECKING,
        UPDATE_STATUS.DOWNLOADING,
        UPDATE_STATUS.VERIFYING,
        UPDATE_STATUS.INSTALLING,
        UPDATE_STATUS.ROLLING_BACK
      ].includes(state.status);
    },

    /**
     * 更新优先级文本
     */
    priorityText: (state) => {
      const priority = state.updateInfo?.priority;
      const map = {
        [UPDATE_PRIORITY.LOW]: '可选更新',
        [UPDATE_PRIORITY.MEDIUM]: '建议更新',
        [UPDATE_PRIORITY.HIGH]: '重要更新',
        [UPDATE_PRIORITY.CRITICAL]: '关键更新'
      };
      return map[priority] || '更新';
    },

    /**
     * 更新类型文本
     */
    updateTypeText: (state) => {
      const type = state.updateInfo?.update_type;
      const map = {
        full: '全量更新',
        incremental: '增量更新',
        hotfix: '热修复'
      };
      return map[type] || '更新';
    },

    /**
     * 格式化的下载进度
     */
    formattedDownloadProgress: (state) => {
      const { downloadedBytes, totalBytes, speed } = state.downloadProgress;
      return {
        downloaded: formatBytes(downloadedBytes),
        total: formatBytes(totalBytes),
        speed: speed > 0 ? `${formatBytes(speed)}/s` : '--',
        percent: state.downloadProgress.percent.toFixed(1)
      };
    },

    /**
     * 备份数量
     */
    backupCount: (state) => state.backups.length,

    /**
     * 是否可回滚
     */
    canRollback: (state) => state.backups.length > 0
  },

  actions: {
    /**
     * 初始化Store
     */
    async init() {
      // 获取当前版本
      await this.fetchCurrentVersion();

      // 获取备份列表
      await this.fetchBackups();

      // 获取更新历史
      await this.fetchUpdateHistory();

      // 启动自动检查
      if (this.autoCheckEnabled) {
        this.startAutoCheck();
      }
    },

    /**
     * 获取当前版本信息
     */
    async fetchCurrentVersion() {
      try {
        const version = await getCurrentVersion();
        if (version) {
          this.currentVersion = version;
        }
      } catch (error) {
        console.error('[UpdateStore] Fetch version failed:', error);
      }
    },

    /**
     * 检查更新
     */
    async checkUpdate() {
      if (this.processing || this.status === UPDATE_STATUS.CHECKING) {
        return;
      }

      this.status = UPDATE_STATUS.CHECKING;
      this.processing = true;
      this.error = null;

      try {
        const result = await checkForUpdate({
          current_version: this.currentVersion?.version || '0.0.0',
          current_build: this.currentVersion?.build_number || 0,
          channel: this.channel
        });

        this.lastCheckTime = new Date().toISOString();

        if (result && result.has_update) {
          this.updateInfo = result.update_info;
          this.status = UPDATE_STATUS.AVAILABLE;

          // 如果启用后台下载，自动开始下载
          if (this.backgroundDownloadEnabled) {
            this.startBackgroundDownload();
          }
        } else {
          this.status = UPDATE_STATUS.IDLE;
          this.updateInfo = null;
        }
      } catch (error) {
        console.error('[UpdateStore] Check update failed:', error);
        this.error = error.message || '检查更新失败';
        this.status = UPDATE_STATUS.FAILED;
      } finally {
        this.processing = false;
      }
    },

    /**
     * 开始后台下载
     */
    startBackgroundDownload() {
      if (!this.updateInfo?.download_url) {
        return;
      }

      this.status = UPDATE_STATUS.DOWNLOADING;
      this.downloadProgress = {
        percent: 0,
        downloadedBytes: 0,
        totalBytes: (this.updateInfo.package_size_mb || 0) * 1024 * 1024,
        speed: 0,
        estimatedTime: 0
      };

      // 启动进度轮询
      this.startProgressPolling();
    },

    /**
     * 启动进度轮询
     */
    startProgressPolling() {
      this.stopProgressPolling();

      this._progressTimer = setInterval(async () => {
        try {
          const progress = await getUpdateProgress();
          if (progress) {
            this.updateProgress(progress);
          }
        } catch (error) {
          console.error('[UpdateStore] Poll progress failed:', error);
        }
      }, 1000);
    },

    /**
     * 停止进度轮询
     */
    stopProgressPolling() {
      if (this._progressTimer) {
        clearInterval(this._progressTimer);
        this._progressTimer = null;
      }
    },

    /**
     * 更新进度数据
     *
     * @param {Object} progress - 进度数据
     */
    updateProgress(progress) {
      if (progress.status === 'downloading') {
        this.downloadProgress = {
          percent: progress.progress_percent || 0,
          downloadedBytes: progress.downloaded_bytes || 0,
          totalBytes: progress.total_bytes || 0,
          speed: this.calculateSpeed(progress.downloaded_bytes),
          estimatedTime: progress.estimated_remaining_seconds || 0
        };

      } else if (progress.status === 'verifying') {
        this.status = UPDATE_STATUS.VERIFYING;
        this.downloadProgress.percent = 95;

      } else if (progress.status === 'installing') {
        this.status = UPDATE_STATUS.INSTALLING;
        this.installProgress = {
          percent: progress.progress_percent || 0,
          currentStep: progress.current_step || '',
          startedAt: progress.started_at
        };

      } else if (progress.status === 'completed') {
        this.stopProgressPolling();
        this.status = UPDATE_STATUS.COMPLETED;
        this.downloadProgress.percent = 100;

      } else if (progress.status === 'failed') {
        this.stopProgressPolling();
        this.status = UPDATE_STATUS.FAILED;
        this.error = progress.current_step || '更新失败';
      }
    },

    /**
     * 计算下载速度
     *
     * @param {number} downloaded - 已下载字节数
     * @returns {number} 速度（字节/秒）
     */
    calculateSpeed(downloaded) {
      // 简化实现，实际应记录时间差
      return downloaded / 10; // 假设10秒
    },

    /**
     * 应用更新
     */
    async applyUpdate() {
      if (this.processing || !this.updateInfo) {
        return;
      }

      this.processing = true;
      this.status = UPDATE_STATUS.INSTALLING;
      this.error = null;

      try {
        const result = await applyUpdate({
          package_path: this.updateInfo.download_url,
          checksum_sha256: this.updateInfo.checksum_sha256,
          create_backup: true,
          auto_rollback: true
        });

        if (result && result.success) {
          this.status = UPDATE_STATUS.COMPLETED;

          // 刷新版本信息
          await this.fetchCurrentVersion();

          // 刷新备份列表
          await this.fetchBackups();

          // 刷新更新历史
          await this.fetchUpdateHistory();
        } else {
          throw new Error(result?.message || '应用更新失败');
        }
      } catch (error) {
        console.error('[UpdateStore] Apply update failed:', error);
        this.error = error.message || '应用更新失败';
        this.status = UPDATE_STATUS.FAILED;
      } finally {
        this.processing = false;
      }
    },

    /**
     * 获取备份列表
     */
    async fetchBackups() {
      try {
        const result = await getBackupList();
        if (result) {
          this.backups = result.backups || [];
        }
      } catch (error) {
        console.error('[UpdateStore] Fetch backups failed:', error);
      }
    },

    /**
     * 创建手动备份
     *
     * @param {string} [description=''] - 备份描述
     */
    async createBackup(description = '') {
      this.processing = true;
      this.error = null;

      try {
        const result = await createManualBackup(description);
        if (result) {
          await this.fetchBackups();
          return result;
        }
      } catch (error) {
        console.error('[UpdateStore] Create backup failed:', error);
        this.error = error.message || '创建备份失败';
      } finally {
        this.processing = false;
      }

      return null;
    },

    /**
     * 删除备份
     *
     * @param {string} backupId - 备份ID
     */
    async removeBackup(backupId) {
      this.processing = true;
      this.error = null;

      try {
        const success = await deleteBackup(backupId);
        if (success) {
          await this.fetchBackups();
          return true;
        }
      } catch (error) {
        console.error('[UpdateStore] Delete backup failed:', error);
        this.error = error.message || '删除备份失败';
      } finally {
        this.processing = false;
      }

      return false;
    },

    /**
     * 获取更新历史
     */
    async fetchUpdateHistory() {
      try {
        const result = await getUpdateHistory();
        if (result) {
          this.updateHistory = result.records || [];
        }
      } catch (error) {
        console.error('[UpdateStore] Fetch history failed:', error);
      }
    },

    /**
     * 清理旧备份
     *
     * @param {number} [maxCount=5] - 最大保留数量
     */
    async cleanupBackups(maxCount = 5) {
      this.processing = true;
      this.error = null;

      try {
        const result = await cleanupOldBackups(maxCount);
        if (result) {
          await this.fetchBackups();
          return result.deleted_count || 0;
        }
      } catch (error) {
        console.error('[UpdateStore] Cleanup backups failed:', error);
        this.error = error.message || '清理备份失败';
      } finally {
        this.processing = false;
      }

      return 0;
    },

    /**
     * 启动自动检查
     */
    startAutoCheck() {
      this.stopAutoCheck();

      // 立即检查一次
      this.checkUpdate();

      // 设置定时检查
      this._checkTimer = setInterval(() => {
        if (this.status === UPDATE_STATUS.IDLE) {
          this.checkUpdate();
        }
      }, this.autoCheckInterval);
    },

    /**
     * 停止自动检查
     */
    stopAutoCheck() {
      if (this._checkTimer) {
        clearInterval(this._checkTimer);
        this._checkTimer = null;
      }
    },

    /**
     * 设置更新通道
     *
     * @param {string} channel - 更新通道
     */
    setChannel(channel) {
      if (['stable', 'beta', 'dev'].includes(channel)) {
        this.channel = channel;
      }
    },

    /**
     * 设置自动检查
     *
     * @param {boolean} enabled - 是否启用
     */
    setAutoCheckEnabled(enabled) {
      this.autoCheckEnabled = enabled;

      if (enabled) {
        this.startAutoCheck();
      } else {
        this.stopAutoCheck();
      }
    },

    /**
     * 设置后台下载
     *
     * @param {boolean} enabled - 是否启用
     */
    setBackgroundDownloadEnabled(enabled) {
      this.backgroundDownloadEnabled = enabled;
    },

    /**
     * 重置状态
     */
    reset() {
      this.status = UPDATE_STATUS.IDLE;
      this.error = null;
      this.updateInfo = null;
      this.downloadProgress = {
        percent: 0,
        downloadedBytes: 0,
        totalBytes: 0,
        speed: 0,
        estimatedTime: 0
      };
      this.installProgress = {
        percent: 0,
        currentStep: '',
        startedAt: null
      };
    },

    /**
     * 清理资源
     */
    cleanup() {
      this.stopProgressPolling();
      this.stopAutoCheck();
    }
  }
});

/**
 * 格式化字节数
 *
 * @param {number} bytes - 字节数
 * @returns {string} 格式化后的字符串
 */
function formatBytes(bytes) {
  if (bytes === 0) return '0 B';

  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
}
