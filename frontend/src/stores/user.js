/**
 * @file user.js
 * @path src/stores/
 * @description 用户状态管理Store，处理用户认证、个人信息、偏好设置、操作历史等功能
 * @author Frontend Engineer Agent
 * @date 2026-03-07
 * @dependencies pinia, vue, utils
 */

import { defineStore } from 'pinia'
import { ref, computed, reactive } from 'vue'
import { get, post, put, del } from '../utils/apiRequest'

/**
 * 用户角色枚举
 */
export const USER_ROLES = {
  ADMIN: 'admin',
  OPERATOR: 'operator',
  VIEWER: 'viewer'
}

/**
 * 用户状态枚举
 */
export const USER_STATUS = {
  ACTIVE: 'active',
  INACTIVE: 'inactive',
  LOCKED: 'locked'
}

/**
 * 操作类型枚举
 */
export const OPERATION_TYPES = {
  LOGIN: 'login',
  LOGOUT: 'logout',
  UPDATE_PROFILE: 'update_profile',
  CHANGE_PASSWORD: 'change_password',
  UPDATE_PREFERENCES: 'update_preferences',
  DEVICE_OPERATION: 'device_operation',
  DATA_EXPORT: 'data_export',
  CONFIG_CHANGE: 'config_change'
}

/**
 * 默认用户偏好设置
 */
const DEFAULT_PREFERENCES = {
  notification: {
    enabled: true,
    sound: true,
    email: false,
    desktop: false
  },
  display: {
    refreshInterval: 1000,
    chartDefaultType: 'line',
    chartAnimation: true,
    decimalPlaces: 2
  },
  language: 'zh-CN',
  theme: 'light'
}

/**
 * 用户状态管理Store
 */
export const useUserStore = defineStore('user', () => {
  // ==================== 用户状态 ====================

  /** 当前用户信息 */
  const currentUser = ref(null)

  /** 是否已认证 */
  const isAuthenticated = computed(() => !!currentUser.value && !!token.value)

  /** 认证令牌 */
  const token = ref(localStorage.getItem('auth_token') || null)

  /** 用户偏好设置 */
  const preferences = reactive({ ...DEFAULT_PREFERENCES })

  /** 操作历史记录 */
  const operationHistory = ref([])

  /** 加载状态 */
  const loading = ref(false)

  /** 错误消息 */
  const errorMessage = ref('')

  /** 操作历史分页 */
  const historyPagination = ref({
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0
  })

  // ==================== 计算属性 ====================

  /**
   * 用户角色标签
   */
  const roleLabel = computed(() => {
    const roleMap = {
      [USER_ROLES.ADMIN]: '管理员',
      [USER_ROLES.OPERATOR]: '操作员',
      [USER_ROLES.VIEWER]: '观察者'
    }
    return roleMap[currentUser.value?.role] || '未知'
  })

  /**
   * 是否为管理员
   */
  const isAdmin = computed(() => currentUser.value?.role === USER_ROLES.ADMIN)

  /**
   * 用户首字母头像
   */
  const avatarText = computed(() => {
    if (!currentUser.value?.username) return '?'
    return currentUser.value.username.charAt(0).toUpperCase()
  })

  // ==================== 认证方法 ====================

  /**
   * 用户登录
   *
   * @param {Object} credentials - 登录凭据
   * @param {string} credentials.username - 用户名
   * @param {string} credentials.password - 密码
   * @returns {Promise<Object>} 登录结果
   */
  async function login(credentials) {
    loading.value = true
    errorMessage.value = ''

    const { username, password } = credentials

    try {
      const result = await post('/api/v1/user/login', {
        username,
        password
      }, {
        onError: (msg) => {
          errorMessage.value = msg
        }
      })

      if (result.success && result.data) {
        // 保存令牌 (API返回access_token)
        const accessToken = result.data.access_token || result.data.token
        token.value = accessToken
        localStorage.setItem('auth_token', accessToken)

        // 设置用户信息
        currentUser.value = result.data.user || {
          id: result.data.user_id,
          username: username,
          role: result.data.role || 'user'
        }

        // 记录登录操作
        recordOperation({
          type: OPERATION_TYPES.LOGIN,
          description: '用户登录',
          metadata: {
            loginTime: new Date().toISOString(),
            ip: result.data.ip || 'unknown'
          }
        })

        // 加载用户偏好设置
        await fetchPreferences()

        return {
          success: true,
          user: currentUser.value
        }
      }

      return {
        success: false,
        message: errorMessage.value || '登录失败'
      }
    } catch (error) {
      errorMessage.value = error.message || '登录请求失败'
      return {
        success: false,
        message: errorMessage.value
      }
    } finally {
      loading.value = false
    }
  }

  /**
   * 用户登出
   *
   * @returns {Promise<boolean>} 是否登出成功
   */
  async function logout() {
    loading.value = true

    try {
      // 记录登出操作
      recordOperation({
        type: OPERATION_TYPES.LOGOUT,
        description: '用户登出',
        metadata: {
          logoutTime: new Date().toISOString()
        }
      })

      // 调用后端登出接口
      await post('/api/v1/user/logout', null, {
        onError: (msg) => {
          console.warn('[User] Logout API error:', msg)
        }
      })

      return true
    } catch (error) {
      console.error('[User] Logout error:', error)
      return false
    } finally {
      // 清除本地状态
      clearUserData()
      loading.value = false
    }
  }

  /**
   * 获取当前用户信息
   *
   * @returns {Promise<Object|null>} 用户信息
   */
  async function fetchCurrentUser() {
    if (!token.value) {
      return null
    }

    loading.value = true
    errorMessage.value = ''

    try {
      const result = await get('/api/v1/user/me', null, {
        onError: (msg) => {
          errorMessage.value = msg
          // 令牌无效时清除用户数据
          if (msg.includes('token') || msg.includes('认证')) {
            clearUserData()
          }
        }
      })

      if (result.success && result.data) {
        currentUser.value = result.data
        return result.data
      }

      return null
    } catch (error) {
      console.error('[User] Fetch current user error:', error)
      return null
    } finally {
      loading.value = false
    }
  }

  // ==================== 用户信息管理 ====================

  /**
   * 更新用户信息
   *
   * @param {Object} data - 更新数据
   * @param {string} [data.username] - 用户名
   * @param {string} [data.email] - 邮箱
   * @param {string} [data.avatar] - 头像URL
   * @returns {Promise<Object>} 更新结果
   */
  async function updateProfile(data) {
    loading.value = true
    errorMessage.value = ''

    try {
      const result = await put('/api/v1/user/profile', data, {
        onError: (msg) => {
          errorMessage.value = msg
        }
      })

      if (result.success && result.data) {
        // 更新本地用户信息
        currentUser.value = {
          ...currentUser.value,
          ...result.data
        }

        // 记录操作
        recordOperation({
          type: OPERATION_TYPES.UPDATE_PROFILE,
          description: '更新个人信息',
          metadata: {
            updatedFields: Object.keys(data)
          }
        })

        return {
          success: true,
          user: currentUser.value
        }
      }

      return {
        success: false,
        message: errorMessage.value
      }
    } catch (error) {
      errorMessage.value = error.message || '更新失败'
      return {
        success: false,
        message: errorMessage.value
      }
    } finally {
      loading.value = false
    }
  }

  /**
   * 修改密码
   *
   * @param {string} oldPassword - 旧密码
   * @param {string} newPassword - 新密码
   * @returns {Promise<Object>} 修改结果
   */
  async function changePassword(oldPassword, newPassword) {
    loading.value = true
    errorMessage.value = ''

    try {
      const result = await post('/api/v1/user/password', {
        old_password: oldPassword,
        new_password: newPassword
      }, {
        onError: (msg) => {
          errorMessage.value = msg
        }
      })

      if (result.success) {
        // 记录操作
        recordOperation({
          type: OPERATION_TYPES.CHANGE_PASSWORD,
          description: '修改密码',
          metadata: {
            changedAt: new Date().toISOString()
          }
        })

        return {
          success: true,
          message: result.message || '密码修改成功'
        }
      }

      return {
        success: false,
        message: errorMessage.value || '密码修改失败'
      }
    } catch (error) {
      errorMessage.value = error.message || '密码修改请求失败'
      return {
        success: false,
        message: errorMessage.value
      }
    } finally {
      loading.value = false
    }
  }

  /**
   * 上传头像
   *
   * @param {FormData} formData - 包含头像文件的FormData对象
   * @returns {Promise<Object>} 上传结果
   */
  async function uploadAvatar(formData) {
    loading.value = true
    errorMessage.value = ''

    try {
      const response = await fetch('/api/v1/user/avatar', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token.value}`
        },
        body: formData
      })

      const result = await response.json()

      if (response.ok && result.success) {
        if (currentUser.value) {
          currentUser.value = {
            ...currentUser.value,
            avatar: result.data?.url || result.data?.avatar
          }
        }

        recordOperation({
          type: OPERATION_TYPES.UPDATE_PROFILE,
          description: '上传头像',
          metadata: {
            uploadedAt: new Date().toISOString()
          }
        })

        return {
          success: true,
          avatar: result.data?.url || result.data?.avatar
        }
      }

      errorMessage.value = result.message || '头像上传失败'
      return {
        success: false,
        message: errorMessage.value
      }
    } catch (error) {
      errorMessage.value = error.message || '头像上传请求失败'
      return {
        success: false,
        message: errorMessage.value
      }
    } finally {
      loading.value = false
    }
  }

  // ==================== 偏好设置管理 ====================

  /**
   * 获取偏好设置
   *
   * @returns {Promise<Object|null>} 偏好设置
   */
  async function fetchPreferences() {
    if (!token.value) {
      return null
    }

    loading.value = true

    try {
      const result = await get('/api/v1/user/preferences', null, {
        onError: (msg) => {
          console.warn('[User] Fetch preferences error:', msg)
        }
      })

      if (result.success && result.data) {
        // 合并偏好设置
        Object.keys(result.data).forEach(key => {
          if (preferences[key] !== undefined) {
            preferences[key] = result.data[key]
          }
        })
        return preferences
      }

      return null
    } catch (error) {
      console.error('[User] Fetch preferences error:', error)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * 更新偏好设置
   *
   * @param {Object} newPreferences - 新的偏好设置
   * @returns {Promise<Object>} 更新结果
   */
  async function updatePreferences(newPreferences) {
    loading.value = true
    errorMessage.value = ''

    try {
      const result = await put('/api/v1/user/preferences', newPreferences, {
        onError: (msg) => {
          errorMessage.value = msg
        }
      })

      if (result.success) {
        // 更新本地偏好设置
        Object.keys(newPreferences).forEach(key => {
          if (preferences[key] !== undefined) {
            preferences[key] = newPreferences[key]
          }
        })

        // 记录操作
        recordOperation({
          type: OPERATION_TYPES.UPDATE_PREFERENCES,
          description: '更新偏好设置',
          metadata: {
            updatedFields: Object.keys(newPreferences)
          }
        })

        return {
          success: true,
          preferences
        }
      }

      return {
        success: false,
        message: errorMessage.value
      }
    } catch (error) {
      errorMessage.value = error.message || '更新偏好设置失败'
      return {
        success: false,
        message: errorMessage.value
      }
    } finally {
      loading.value = false
    }
  }

  // ==================== 操作历史管理 ====================

  /**
   * 记录操作
   *
   * @param {Object} operation - 操作对象
   * @param {string} operation.type - 操作类型
   * @param {string} operation.description - 操作描述
   * @param {Object} [operation.metadata] - 操作元数据
   * @internal
   */
  function recordOperation(operation) {
    const record = {
      id: `op_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      type: operation.type,
      description: operation.description,
      metadata: operation.metadata || {},
      timestamp: new Date().toISOString(),
      userId: currentUser.value?.id
    }

    operationHistory.value.unshift(record)

    // 限制历史记录数量
    if (operationHistory.value.length > 100) {
      operationHistory.value = operationHistory.value.slice(0, 100)
    }
  }

  /**
   * 获取操作历史
   *
   * @param {Object} params - 查询参数
   * @param {number} [params.page=1] - 页码
   * @param {number} [params.pageSize=20] - 每页数量
   * @param {string} [params.type] - 操作类型过滤
   * @param {string} [params.startDate] - 开始日期
   * @param {string} [params.endDate] - 结束日期
   * @returns {Promise<Object|null>} 操作历史数据
   */
  async function fetchOperationHistory(params = {}) {
    if (!token.value) {
      return null
    }

    loading.value = true

    const queryParams = {
      page: params.page || historyPagination.value.page,
      page_size: params.pageSize || historyPagination.value.pageSize,
      type: params.type,
      start_date: params.startDate,
      end_date: params.endDate
    }

    try {
      const result = await get('/api/v1/user/history', queryParams, {
        onError: (msg) => {
          console.warn('[User] Fetch operation history error:', msg)
        }
      })

      if (result.success && result.data) {
        operationHistory.value = result.data.items || []
        historyPagination.value = {
          page: result.data.page || 1,
          pageSize: result.data.page_size || 20,
          total: result.data.total || 0,
          totalPages: result.data.total_pages || 0
        }
        return result.data
      }

      return null
    } catch (error) {
      console.error('[User] Fetch operation history error:', error)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * 清除操作历史
   *
   * @returns {Promise<boolean>} 是否清除成功
   */
  async function clearOperationHistory() {
    loading.value = true

    try {
      const result = await del('/user/history', {
        onError: (msg) => {
          console.warn('[User] Clear operation history error:', msg)
        }
      })

      if (result.success) {
        operationHistory.value = []
        historyPagination.value = {
          page: 1,
          pageSize: 20,
          total: 0,
          totalPages: 0
        }
        return true
      }

      return false
    } catch (error) {
      console.error('[User] Clear operation history error:', error)
      return false
    } finally {
      loading.value = false
    }
  }

  // ==================== 工具方法 ====================

  /**
   * 清除用户数据
   *
   * @internal
   */
  function clearUserData() {
    currentUser.value = null
    token.value = null
    localStorage.removeItem('auth_token')
    operationHistory.value = []
    Object.assign(preferences, DEFAULT_PREFERENCES)
    errorMessage.value = ''
  }

  /**
   * 清除错误消息
   */
  function clearError() {
    errorMessage.value = ''
  }

  /**
   * 重置Store状态
   */
  function resetState() {
    clearUserData()
    loading.value = false
  }

  /**
   * 检查令牌有效性
   *
   * @returns {Promise<boolean>} 令牌是否有效
   */
  async function checkAuth() {
    if (!token.value) {
      return false
    }

    const user = await fetchCurrentUser()
    return !!user
  }

  // ==================== 导出 ====================

  return {
    // 状态
    currentUser,
    isAuthenticated,
    token,
    preferences,
    operationHistory,
    loading,
    errorMessage,
    historyPagination,

    // 计算属性
    roleLabel,
    isAdmin,
    avatarText,

    // 认证方法
    login,
    logout,
    fetchCurrentUser,
    checkAuth,

    // 用户信息管理
    updateProfile,
    changePassword,
    uploadAvatar,

    // 偏好设置管理
    fetchPreferences,
    updatePreferences,

    // 操作历史管理
    fetchOperationHistory,
    clearOperationHistory,

    // 工具方法
    clearError,
    resetState
  }
})
