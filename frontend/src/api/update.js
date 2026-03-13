/**
 * @file update.js
 * @path src/api/
 * @description 自动更新系统API接口封装
 * @author Agent
 * @date 2026-03-07
 * @dependencies utils/apiRequest
 */

import { get, post, del } from '../utils/apiRequest';

/**
 * 获取当前版本信息
 *
 * @returns {Promise<Object|null>} 版本信息对象
 */
export async function getCurrentVersion() {
  const result = await get('/api/update/version', null, {
    onError: (msg) => console.error('[UpdateAPI] Get version error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 检查更新
 *
 * @param {Object} params - 检查参数
 * @param {string} params.current_version - 当前版本号
 * @param {number} params.current_build - 当前构建号
 * @param {string} [params.channel='stable'] - 更新通道
 * @returns {Promise<Object|null>} 更新检查结果
 */
export async function checkForUpdate(params) {
  const result = await post('/api/update/check', params, {
    onError: (msg) => console.error('[UpdateAPI] Check update error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取更新进度
 *
 * @returns {Promise<Object|null>} 更新进度对象
 */
export async function getUpdateProgress() {
  const result = await get('/api/update/progress', null, {
    onError: (msg) => console.error('[UpdateAPI] Get progress error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 应用更新
 *
 * @param {Object} params - 应用参数
 * @param {string} params.package_path - 更新包路径
 * @param {string} params.checksum_sha256 - SHA256校验和
 * @param {boolean} [params.create_backup=true] - 是否创建备份
 * @param {boolean} [params.auto_rollback=true] - 失败时是否自动回滚
 * @returns {Promise<Object|null>} 应用结果
 */
export async function applyUpdate(params) {
  const result = await post('/api/update/apply', params, {
    onError: (msg) => console.error('[UpdateAPI] Apply update error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 上传更新包
 *
 * @param {File} file - 更新包文件
 * @param {Function} [onProgress] - 上传进度回调
 * @returns {Promise<Object|null>} 上传结果
 */
export async function uploadUpdatePackage(file, onProgress) {
  try {
    const formData = new FormData();
    formData.append('file', file);

    const xhr = new XMLHttpRequest();

    return new Promise((resolve, reject) => {
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable && onProgress) {
          const percent = Math.round((e.loaded / e.total) * 100);
          onProgress(percent);
        }
      });

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const response = JSON.parse(xhr.responseText);
            resolve(response);
          } catch (e) {
            reject(new Error('Invalid response format'));
          }
        } else {
          reject(new Error(`Upload failed: ${xhr.status}`));
        }
      });

      xhr.addEventListener('error', () => {
        reject(new Error('Network error'));
      });

      xhr.open('POST', '/api/update/upload');
      xhr.send(formData);
    });
  } catch (error) {
    console.error('[UpdateAPI] Upload error:', error);
    return null;
  }
}

/**
 * 验证更新包
 *
 * @param {string} packagePath - 更新包路径
 * @param {string} checksum - SHA256校验和
 * @returns {Promise<Object|null>} 验证结果
 */
export async function verifyUpdatePackage(packagePath, checksum) {
  const result = await post('/api/update/verify', {
    package_path: packagePath,
    checksum
  }, {
    onError: (msg) => console.error('[UpdateAPI] Verify package error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 执行回滚
 *
 * @param {Object} params - 回滚参数
 * @param {string} params.backup_id - 备份ID
 * @param {boolean} [params.verify_integrity=true] - 是否验证完整性
 * @returns {Promise<Object|null>} 回滚结果
 */
export async function performRollback(params) {
  const result = await post('/api/update/rollback', params, {
    onError: (msg) => console.error('[UpdateAPI] Rollback error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取备份列表
 *
 * @returns {Promise<Object|null>} 备份列表
 */
export async function getBackupList() {
  const result = await get('/api/update/backups', null, {
    onError: (msg) => console.error('[UpdateAPI] Get backups error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 创建手动备份
 *
 * @param {string} [description=''] - 备份描述
 * @returns {Promise<Object|null>} 备份信息
 */
export async function createManualBackup(description = '') {
  const result = await post('/api/update/backups', { description }, {
    onError: (msg) => console.error('[UpdateAPI] Create backup error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 删除备份
 *
 * @param {string} backupId - 备份ID
 * @returns {Promise<boolean>} 是否删除成功
 */
export async function deleteBackup(backupId) {
  const result = await del(`/api/update/backups/${backupId}`, {
    onError: (msg) => console.error('[UpdateAPI] Delete backup error:', msg)
  });

  return result.success;
}

/**
 * 获取更新历史
 *
 * @returns {Promise<Object|null>} 更新历史
 */
export async function getUpdateHistory() {
  const result = await get('/api/update/history', null, {
    onError: (msg) => console.error('[UpdateAPI] Get history error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 清理旧备份
 *
 * @param {number} [maxCount=5] - 最大保留数量
 * @returns {Promise<Object|null>} 清理结果
 */
export async function cleanupOldBackups(maxCount = 5) {
  const result = await post('/api/update/cleanup', { max_count: maxCount }, {
    onError: (msg) => console.error('[UpdateAPI] Cleanup error:', msg)
  });

  return result.success ? result.data : null;
}
