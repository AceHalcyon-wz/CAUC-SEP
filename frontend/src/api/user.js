/**
 * @file user.js
 * @path src/api/
 * @description 用户管理API接口封装
 * @author Agent
 * @date 2024-03-15
 * @dependencies utils/apiRequest
 */

import { get, post, put, del } from '../utils/apiRequest';

/**
 * 用户登录
 *
 * @param {Object} params - 登录参数
 * @param {string} params.username - 用户名
 * @param {string} params.password - 密码
 * @returns {Promise<Object|null>} 登录结果
 */
export async function login(params) {
  const result = await post('/api/v1/user/login', params, {
    onError: (msg) => console.error('[UserAPI] Login error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 用户登出
 *
 * @returns {Promise<boolean>} 是否登出成功
 */
export async function logout() {
  const result = await post('/api/v1/user/logout', null, {
    onError: (msg) => console.error('[UserAPI] Logout error:', msg)
  });

  return result.success;
}

/**
 * 获取当前用户信息
 *
 * @returns {Promise<Object|null>} 用户信息
 */
export async function getCurrentUser() {
  const result = await get('/api/v1/user/me', null, {
    onError: (msg) => console.error('[UserAPI] Get current user error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 更新用户资料
 *
 * @param {Object} profile - 用户资料
 * @returns {Promise<Object|null>} 更新后的资料
 */
export async function updateProfile(profile) {
  const result = await put('/api/v1/user/profile', profile, {
    onError: (msg) => console.error('[UserAPI] Update profile error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 修改密码
 *
 * @param {Object} params - 密码参数
 * @param {string} params.old_password - 旧密码
 * @param {string} params.new_password - 新密码
 * @returns {Promise<boolean>} 是否修改成功
 */
export async function changePassword(params) {
  const result = await put('/api/v1/user/password', params, {
    onError: (msg) => console.error('[UserAPI] Change password error:', msg)
  });

  return result.success;
}

/**
 * 获取用户偏好设置
 *
 * @returns {Promise<Object|null>} 用户偏好设置
 */
export async function getUserPreferences() {
  const result = await get('/api/v1/user/preferences', null, {
    onError: (msg) => console.error('[UserAPI] Get preferences error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 更新用户偏好设置
 *
 * @param {Object} preferences - 偏好设置
 * @returns {Promise<Object|null>} 更新后的偏好设置
 */
export async function updateUserPreferences(preferences) {
  const result = await put('/api/v1/user/preferences', preferences, {
    onError: (msg) => console.error('[UserAPI] Update preferences error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 上传头像
 *
 * @param {FormData} formData - 包含头像文件的FormData
 * @returns {Promise<Object|null>} 上传结果
 */
export async function uploadAvatar(formData) {
  const result = await post('/api/v1/user/avatar', formData, {
    onError: (msg) => console.error('[UserAPI] Upload avatar error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 记录操作历史
 *
 * @param {Object} params - 操作记录
 * @returns {Promise<boolean>} 是否记录成功
 */
export async function recordOperation(params) {
  const result = await post('/api/v1/user/history', params, {
    onError: (msg) => console.error('[UserAPI] Record operation error:', msg)
  });

  return result.success;
}

/**
 * 获取操作历史
 *
 * @param {Object} params - 查询参数
 * @returns {Promise<Array|null>} 操作历史列表
 */
export async function getOperationHistory(params = {}) {
  const result = await get('/api/v1/user/history', params, {
    onError: (msg) => console.error('[UserAPI] Get operation history error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 清除操作历史
 *
 * @returns {Promise<boolean>} 是否清除成功
 */
export async function clearOperationHistory() {
  const result = await del('/api/v1/user/history', null, {
    onError: (msg) => console.error('[UserAPI] Clear operation history error:', msg)
  });

  return result.success;
}
