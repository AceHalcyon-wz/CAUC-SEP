/**
 * @file loginConfig.js
 * @path src/config/
 * @description 登录配置 - 管理预设账号和登录模式
 * @author Agent
 * @date 2026-03-15
 * @version 1.0.0
 */

/**
 * 登录模式枚举
 */
export const LoginMode = {
  /** 快速登录模式 - 使用预设令牌 */
  QUICK: 'quick',
  /** 账号密码登录 - 传统方式 */
  PASSWORD: 'password',
  /** 访客模式 - 只读权限 */
  GUEST: 'guest'
}

/**
 * 预设账号配置
 * 
 * 说明：
 * - 生产环境应从环境变量或配置文件加载
 * - 开发环境可使用默认配置
 * - 密码字段仅用于传统登录模式
 */
export const PRESET_ACCOUNTS = [
  {
    id: 'admin',
    username: 'admin',
    displayName: '管理员',
    role: 'admin',
    description: '系统管理员，拥有所有权限',
    icon: 'SafetyOutlined',
    color: '#1890ff',
    bgColor: 'rgba(24, 144, 255, 0.1)',
    /** 快速登录令牌（生产环境应从服务器动态获取） */
    quickToken: 'quick_admin_token_2026',
    /** 传统密码（仅用于兼容模式） */
    password: import.meta.env.VITE_ADMIN_PASSWORD || 'admin123',
    /** 权限范围 */
    permissions: ['all']
  },
  {
    id: 'user',
    username: '123456',
    displayName: '实验员',
    role: 'user',
    description: '实验操作员，可进行实验操作',
    icon: 'TeamOutlined',
    color: '#52c41a',
    bgColor: 'rgba(82, 196, 26, 0.1)',
    quickToken: 'quick_user_token_2026',
    password: import.meta.env.VITE_USER_PASSWORD || '123456',
    permissions: ['experiment.read', 'experiment.write', 'device.operate']
  },
  {
    id: 'guest',
    username: 'guest',
    displayName: '访客',
    role: 'guest',
    description: '访客模式，仅查看权限',
    icon: 'EyeOutlined',
    color: '#faad14',
    bgColor: 'rgba(250, 173, 20, 0.1)',
    quickToken: 'quick_guest_token_2026',
    password: 'guest',
    permissions: ['experiment.read']
  }
]

/**
 * 登录配置
 */
export const LOGIN_CONFIG = {
  /** 默认登录模式 */
  defaultMode: LoginMode.QUICK,
  /** 是否启用快速登录 */
  enableQuickLogin: true,
  /** 是否记住登录状态 */
  enableRemember: true,
  /** 令牌有效期（小时） */
  tokenExpiresIn: 24,
  /** 自动登录超时时间（毫秒） */
  autoLoginTimeout: 5000,
  /** 最大重试次数 */
  maxRetries: 3,
  /** 是否启用访客模式 */
  enableGuestMode: true
}

/**
 * 获取账号配置
 * 
 * @param {string} accountId - 账号 ID
 * @returns {Object|undefined} 账号配置
 */
export function getAccountConfig(accountId) {
  return PRESET_ACCOUNTS.find(acc => acc.id === accountId)
}

/**
 * 获取所有可用账号
 * 
 * @param {string} [mode] - 登录模式过滤
 * @returns {Array} 账号列表
 */
export function getAvailableAccounts(mode) {
  if (!mode) {
    return PRESET_ACCOUNTS
  }
  
  if (mode === LoginMode.GUEST) {
    return PRESET_ACCOUNTS.filter(acc => acc.id === 'guest')
  }
  
  return PRESET_ACCOUNTS.filter(acc => acc.id !== 'guest')
}

/**
 * 生成临时令牌
 * 
 * @param {Object} account - 账号信息
 * @returns {string} 临时令牌
 */
export function generateTempToken(account) {
  const timestamp = Date.now()
  const payload = {
    sub: account.id,
    username: account.username,
    role: account.role,
    iat: timestamp,
    exp: timestamp + (LOGIN_CONFIG.tokenExpiresIn * 3600 * 1000)
  }
  
  const base64Payload = btoa(JSON.stringify(payload))
  const signature = btoa(`temp_${account.id}_${timestamp}`)
  
  return `temp_token.${base64Payload}.${signature}`
}

/**
 * 验证临时令牌
 * 
 * @param {string} token - 令牌
 * @returns {Object|null} 解析结果
 */
export function verifyTempToken(token) {
  try {
    if (!token || !token.startsWith('temp_token.')) {
      return null
    }
    
    const parts = token.split('.')
    if (parts.length !== 3) {
      return null
    }
    
    const payload = JSON.parse(atob(parts[1]))
    const now = Date.now()
    
    if (payload.exp && now > payload.exp) {
      return null
    }
    
    return payload
  } catch (error) {
    console.error('[LoginConfig] Token verification failed:', error)
    return null
  }
}

/**
 * 检查账号是否可用
 * 
 * @param {Object} account - 账号配置
 * @returns {boolean} 是否可用
 */
export function isAccountAvailable(account) {
  if (!account) {
    return false
  }
  
  const accountKey = `account_${account.id}_disabled`
  const isDisabled = localStorage.getItem(accountKey) === 'true'
  
  return !isDisabled
}

/**
 * 设置账号可用状态
 * 
 * @param {string} accountId - 账号 ID
 * @param {boolean} available - 是否可用
 */
export function setAccountAvailability(accountId, available) {
  const accountKey = `account_${accountId}_disabled`
  if (available) {
    localStorage.removeItem(accountKey)
  } else {
    localStorage.setItem(accountKey, 'true')
  }
}

/**
 * 获取登录模式配置
 * 
 * @param {string} mode - 登录模式
 * @returns {Object} 模式配置
 */
export function getModeConfig(mode) {
  const modeConfigs = {
    [LoginMode.QUICK]: {
      title: '快速登录',
      subtitle: '点击账号即可登录，无需输入密码',
      icon: 'ThunderboltOutlined',
      description: '适用于开发测试环境'
    },
    [LoginMode.PASSWORD]: {
      title: '账号密码登录',
      subtitle: '请输入账号和密码',
      icon: 'KeyOutlined',
      description: '传统登录方式'
    },
    [LoginMode.GUEST]: {
      title: '访客模式',
      subtitle: '仅查看权限，无需登录',
      icon: 'EyeOutlined',
      description: '适合临时访问'
    }
  }
  
  return modeConfigs[mode] || modeConfigs[LoginMode.QUICK]
}
