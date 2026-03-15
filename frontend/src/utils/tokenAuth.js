/**
 * @file tokenAuth.js
 * @path src/utils/
 * @description 令牌认证工具 - 提供临时令牌生成、验证和管理
 * @author Agent
 * @date 2026-03-15
 * @version 1.0.0
 */

import { LOGIN_CONFIG } from '../config/loginConfig'

/**
 * 令牌存储键
 */
const TOKEN_STORAGE_KEY = 'auth_token'
const TOKEN_TYPE_KEY = 'token_type'
const TOKEN_EXPIRY_KEY = 'token_expiry'

/**
 * 令牌类型
 */
export const TokenType = {
  /** JWT 令牌（后端签发） */
  JWT: 'jwt',
  /** 临时令牌（前端生成） */
  TEMP: 'temp',
  /** 访客令牌 */
  GUEST: 'guest'
}

/**
 * 生成访客令牌
 * 
 * @returns {string} 访客令牌
 */
export function generateGuestToken() {
  const timestamp = Date.now()
  const payload = {
    sub: 'guest',
    username: 'guest',
    role: 'guest',
    permissions: ['read'],
    iat: timestamp,
    exp: timestamp + (2 * 3600 * 1000) // 访客令牌 2 小时有效
  }
  
  const base64Payload = btoa(JSON.stringify(payload))
  const signature = btoa(`guest_token_${timestamp}`)
  
  return `guest_token.${base64Payload}.${signature}`
}

/**
 * 保存令牌到本地存储
 * 
 * @param {string} token - 令牌
 * @param {string} type - 令牌类型
 * @param {number} expiresIn - 有效期（毫秒）
 */
export function saveToken(token, type = TokenType.TEMP, expiresIn) {
  try {
    localStorage.setItem(TOKEN_STORAGE_KEY, token)
    localStorage.setItem(TOKEN_TYPE_KEY, type)
    
    if (expiresIn) {
      const expiry = Date.now() + expiresIn
      localStorage.setItem(TOKEN_EXPIRY_KEY, expiry.toString())
    }
    
    console.log('[TokenAuth] Token saved:', { type, expiresIn })
  } catch (error) {
    console.error('[TokenAuth] Failed to save token:', error)
  }
}

/**
 * 从本地存储获取令牌
 * 
 * @returns {{token: string|null, type: string|null, isExpired: boolean}}
 */
export function getToken() {
  const token = localStorage.getItem(TOKEN_STORAGE_KEY)
  const type = localStorage.getItem(TOKEN_TYPE_KEY)
  const expiryStr = localStorage.getItem(TOKEN_EXPIRY_KEY)
  
  if (!token || !type) {
    return { token: null, type: null, isExpired: false }
  }
  
  let isExpired = false
  if (expiryStr) {
    const expiry = parseInt(expiryStr, 10)
    isExpired = Date.now() > expiry
  }
  
  return { token, type, isExpired }
}

/**
 * 清除本地令牌
 */
export function clearToken() {
  localStorage.removeItem(TOKEN_STORAGE_KEY)
  localStorage.removeItem(TOKEN_TYPE_KEY)
  localStorage.removeItem(TOKEN_EXPIRY_KEY)
  console.log('[TokenAuth] Token cleared')
}

/**
 * 验证令牌是否有效
 * 
 * @param {string} token - 令牌
 * @returns {boolean} 是否有效
 */
export function validateToken(token) {
  if (!token) {
    return false
  }
  
  const { isExpired } = getToken()
  if (isExpired) {
    clearToken()
    return false
  }
  
  try {
    if (token.startsWith('temp_token.')) {
      const parts = token.split('.')
      if (parts.length !== 3) {
        return false
      }
      
      const payload = JSON.parse(atob(parts[1]))
      return payload.exp && Date.now() <= payload.exp
    }
    
    if (token.startsWith('guest_token.')) {
      const parts = token.split('.')
      if (parts.length !== 3) {
        return false
      }
      
      const payload = JSON.parse(atob(parts[1]))
      return payload.role === 'guest' && payload.exp && Date.now() <= payload.exp
    }
    
    return true
  } catch (error) {
    console.error('[TokenAuth] Token validation failed:', error)
    return false
  }
}

/**
 * 解析令牌信息
 * 
 * @param {string} token - 令牌
 * @returns {Object|null} 令牌信息
 */
export function decodeToken(token) {
  try {
    if (!token) {
      return null
    }
    
    if (token.startsWith('temp_token.') || token.startsWith('guest_token.')) {
      const parts = token.split('.')
      if (parts.length !== 3) {
        return null
      }
      
      return JSON.parse(atob(parts[1]))
    }
    
    return null
  } catch (error) {
    console.error('[TokenAuth] Failed to decode token:', error)
    return null
  }
}

/**
 * 获取当前用户信息
 * 
 * @returns {Object|null} 用户信息
 */
export function getCurrentUser() {
  const { token } = getToken()
  if (!token) {
    return null
  }
  
  const decoded = decodeToken(token)
  if (!decoded) {
    return null
  }
  
  return {
    id: decoded.sub,
    username: decoded.username,
    role: decoded.role,
    permissions: decoded.permissions || []
  }
}

/**
 * 检查是否已登录
 * 
 * @returns {boolean} 是否已登录
 */
export function isLoggedIn() {
  const { token, isExpired } = getToken()
  return !!token && !isExpired
}

/**
 * 检查是否为访客模式
 * 
 * @returns {boolean} 是否为访客
 */
export function isGuest() {
  const user = getCurrentUser()
  return user?.role === 'guest'
}

/**
 * 自动登录（尝试使用保存的令牌）
 * 
 * @returns {Promise<{success: boolean, user?: Object, message?: string}>}
 */
export async function autoLogin() {
  const { token, type, isExpired } = getToken()
  
  if (!token || isExpired) {
    clearToken()
    return {
      success: false,
      message: '无有效令牌'
    }
  }
  
  const user = getCurrentUser()
  if (!user) {
    return {
      success: false,
      message: '令牌解析失败'
    }
  }
  
  return {
    success: true,
    user,
    message: '自动登录成功'
  }
}

/**
 * 快速登录（生成临时令牌）
 * 
 * @param {Object} account - 账号信息
 * @returns {{success: boolean, token: string, user: Object}}
 */
export function quickLogin(account) {
  try {
    const token = `temp_token.${btoa(JSON.stringify({
      sub: account.id,
      username: account.username,
      role: account.role,
      permissions: account.permissions || [],
      iat: Date.now(),
      exp: Date.now() + (LOGIN_CONFIG.tokenExpiresIn * 3600 * 1000)
    }))}.${btoa(`temp_${account.id}_${Date.now()}`)}`
    
    saveToken(token, TokenType.TEMP, LOGIN_CONFIG.tokenExpiresIn * 3600 * 1000)
    
    return {
      success: true,
      token,
      user: {
        id: account.id,
        username: account.username,
        role: account.role,
        permissions: account.permissions || []
      }
    }
  } catch (error) {
    console.error('[TokenAuth] Quick login failed:', error)
    return {
      success: false,
      message: error.message || '快速登录失败'
    }
  }
}

/**
 * 访客登录
 * 
 * @returns {{success: boolean, token: string, user: Object}}
 */
export function guestLogin() {
  const token = generateGuestToken()
  saveToken(token, TokenType.GUEST, 2 * 3600 * 1000)
  
  return {
    success: true,
    token,
    user: {
      id: 'guest',
      username: 'guest',
      role: 'guest',
      permissions: ['read']
    }
  }
}

/**
 * 令牌刷新（续期）
 * 
 * @param {string} [newToken] - 新令牌（可选）
 * @returns {boolean} 是否成功
 */
export function refreshToken(newToken) {
  if (newToken) {
    const { type } = getToken()
    saveToken(newToken, type || TokenType.TEMP, LOGIN_CONFIG.tokenExpiresIn * 3600 * 1000)
    return true
  }
  
  const { token, type } = getToken()
  if (!token) {
    return false
  }
  
  const decoded = decodeToken(token)
  if (!decoded) {
    return false
  }
  
  if (token.startsWith('temp_token.')) {
    decoded.exp = Date.now() + (LOGIN_CONFIG.tokenExpiresIn * 3600 * 1000)
    const newTempToken = `temp_token.${btoa(JSON.stringify(decoded))}.${btoa(`temp_${decoded.sub}_${Date.now()}`)}`
    saveToken(newTempToken, type || TokenType.TEMP, LOGIN_CONFIG.tokenExpiresIn * 3600 * 1000)
    return true
  }
  
  return false
}
