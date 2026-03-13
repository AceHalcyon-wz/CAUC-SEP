/**
 * @file user.js
 * @path src/api/
 * @description 用户管理相关API接口封装
 * @author Agent
 * @date 2024-03-14
 * @dependencies utils/apiRequest
 */

import { get, post, put, del } from '../utils/apiRequest';

/**
 * 用户登录
 *
 * @param {Object} credentials - 登录凭证
 * @param {string} credentials.username - 用户名
 * @param {string} credentials.password - 密码
 * @returns {Promise<Object|null>} 登录结果，包含token和用户信息
 */
export async function login(credentials) {
  const result = await post('/api/v1/auth/login', credentials, {
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
  const result = await post('/api/v1/auth/logout', null, {
    onError: (msg) => console.error('[UserAPI] Logout error:', msg)
  });

  return result.success;
}

/**
 * 刷新Token
 *
 * @returns {Promise<Object|null>} 新的token信息
 */
export async function refreshToken() {
  const result = await post('/api/v1/auth/refresh', null, {
    onError: (msg) => console.error('[UserAPI] Refresh token error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 获取当前用户信息
 *
 * @returns {Promise<Object|null>} 当前用户信息
 */
export async function getCurrentUser() {
  const result = await get('/api/v1/user/me', null, {
    onError: (msg) => console.error('[UserAPI] Get current user error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 更新当前用户信息
 *
 * @param {Object} userData - 用户数据
 * @returns {Promise<Object|null>} 更新后的用户信息
 */
export async function updateCurrentUser(userData) {
  const result = await put('/api/v1/user/me', userData, {
    onError: (msg) => console.error('[UserAPI] Update current user error:', msg)
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
  const result = await post('/api/v1/user/me/password', params, {
    onError: (msg) => console.error('[UserAPI] Change password error:', msg)
  });

  return result.success;
}

/**
 * 获取用户列表
 *
 * @param {Object} params - 查询参数
 * @param {number} [params.page=1] - 页码
 * @param {number} [params.size=10] - 每页数量
 * @param {string} [params.keyword] - 搜索关键词
 * @returns {Promise<Object|null>} 用户列表
 */
export async function getUserList(params = {}) {
  const result = await get('/api/v1/user/list', params, {
    onError: (msg) => console.error('[UserAPI] Get user list error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 创建用户
 *
 * @param {Object} userData - 用户数据
 * @param {string} userData.username - 用户名
 * @param {string} userData.password - 密码
 * @param {string} userData.email - 邮箱
 * @param {string} [userData.role='user'] - 角色
 * @returns {Promise<Object|null>} 创建的用户信息
 */
export async function createUser(userData) {
  const result = await post('/api/v1/user', userData, {
    onError: (msg) => console.error('[UserAPI] Create user error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 更新用户信息
 *
 * @param {string} userId - 用户ID
 * @param {Object} userData - 用户数据
 * @returns {Promise<Object|null>} 更新后的用户信息
 */
export async function updateUser(userId, userData) {
  const result = await put(`/api/v1/user/${userId}`, userData, {
    onError: (msg) => console.error('[UserAPI] Update user error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 删除用户
 *
 * @param {string} userId - 用户ID
 * @returns {Promise<boolean>} 是否删除成功
 */
export async function deleteUser(userId) {
  const result = await del(`/api/v1/user/${userId}`, {
    onError: (msg) => console.error('[UserAPI] Delete user error:', msg)
  });

  return result.success;
}

/**
 * 获取用户权限列表
 *
 * @param {string} userId - 用户ID
 * @returns {Promise<Object|null>} 权限列表
 */
export async function getUserPermissions(userId) {
  const result = await get(`/api/v1/user/${userId}/permissions`, null, {
    onError: (msg) => console.error('[UserAPI] Get permissions error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 更新用户权限
 *
 * @param {string} userId - 用户ID
 * @param {Object} permissions - 权限配置
 * @returns {Promise<boolean>} 是否更新成功
 */
export async function updateUserPermissions(userId, permissions) {
  const result = await put(`/api/v1/user/${userId}/permissions`, permissions, {
    onError: (msg) => console.error('[UserAPI] Update permissions error:', msg)
  });

  return result.success;
}

/**
 * 获取角色列表
 *
 * @returns {Promise<Object|null>} 角色列表
 */
export async function getRoleList() {
  const result = await get('/api/v1/role/list', null, {
    onError: (msg) => console.error('[UserAPI] Get role list error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 重置用户密码
 *
 * @param {string} userId - 用户ID
 * @returns {Promise<Object|null>} 重置结果（包含临时密码）
 */
export async function resetUserPassword(userId) {
  const result = await post(`/api/v1/user/${userId}/reset-password`, null, {
    onError: (msg) => console.error('[UserAPI] Reset password error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 启用/禁用用户
 *
 * @param {string} userId - 用户ID
 * @param {boolean} enabled - 是否启用
 * @returns {Promise<boolean>} 是否操作成功
 */
export async function toggleUserStatus(userId, enabled) {
  const result = await put(`/api/v1/user/${userId}/status`, { enabled }, {
    onError: (msg) => console.error('[UserAPI] Toggle user status error:', msg)
  });

  return result.success;
}
