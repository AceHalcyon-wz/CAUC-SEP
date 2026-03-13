/**
 * @file useUserPreferences.js
 * @path src/composables/
 * @description 用户偏好设置组合式函数，支持主题切换、布局调整、字体设置、配置导入导出
 * @author Agent
 * @date 2024-03-07
 * @dependencies vue
 */

import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'

/**
 * 主题类型枚举
 */
export const THEME_TYPES = {
  LIGHT: 'light',
  DARK: 'dark',
  SYSTEM: 'system'
}

/**
 * 布局模式枚举
 */
export const LAYOUT_MODES = {
  DEFAULT: 'default',
  COMPACT: 'compact',
  WIDE: 'wide',
  CUSTOM: 'custom'
}

/**
 * 字体大小枚举
 */
export const FONT_SIZES = {
  SMALL: 'small',
  MEDIUM: 'medium',
  LARGE: 'large',
  EXTRA_LARGE: 'extra-large'
}

/**
 * 默认偏好配置
 */
const DEFAULT_PREFERENCES = {
  // 主题设置
  theme: {
    type: THEME_TYPES.SYSTEM,
    primaryColor: '#1890ff',
    successColor: '#52c41a',
    warningColor: '#faad14',
    errorColor: '#f5222d',
    borderRadius: 6
  },

  // 布局设置
  layout: {
    mode: LAYOUT_MODES.DEFAULT,
    sidebarWidth: 240,
    sidebarCollapsed: false,
    showStatusBar: true,
    showBreadcrumb: true,
    contentPadding: 24,
    headerHeight: 56
  },

  // 字体设置
  font: {
    size: FONT_SIZES.MEDIUM,
    family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial',
    lineHeight: 1.6,
    codeFont: '"Fira Code", "Consolas", monospace'
  },

  // 动画设置
  animation: {
    enabled: true,
    duration: 300,
    easing: 'ease-in-out'
  },

  // 数据显示设置
  dataDisplay: {
    refreshInterval: 1000,
    decimalPlaces: 2,
    dateFormat: 'YYYY-MM-DD HH:mm:ss',
    numberFormat: 'standard', // standard, scientific, engineering
    showUnits: true
  },

  // 通知设置
  notification: {
    enabled: true,
    position: 'top-right',
    duration: 4500,
    sound: true,
    desktop: false
  },

  // 快捷键设置
  shortcuts: {
    enabled: true,
    showHints: true
  },

  // 实验设置
  experiment: {
    autoSave: true,
    autoSaveInterval: 60000,
    maxDataPoints: 10000,
    showRealtimeData: true
  },

  // 高级设置
  advanced: {
    debugMode: false,
    performanceMode: false,
    language: 'zh-CN',
    timezone: 'Asia/Shanghai'
  }
}

/**
 * 字体大小映射
 */
const FONT_SIZE_MAP = {
  [FONT_SIZES.SMALL]: 12,
  [FONT_SIZES.MEDIUM]: 14,
  [FONT_SIZES.LARGE]: 16,
  [FONT_SIZES.EXTRA_LARGE]: 18
}

/**
 * 用户偏好设置组合式函数
 *
 * @param {Object} options - 配置选项
 * @param {string} [options.storageKey='user_preferences'] - 本地存储键名
 * @param {boolean} [options.autoSave=true] - 是否自动保存
 * @param {Object} [options.defaultPreferences={}] - 默认偏好覆盖
 * @returns {Object} 用户偏好状态与操作方法
 *
 * @example
 * ```javascript
 * const { preferences, setTheme, updateLayout, exportConfig, importConfig } = useUserPreferences()
 *
 * // 切换主题
 * setTheme(THEME_TYPES.DARK)
 *
 * // 更新布局
 * updateLayout({ sidebarWidth: 280 })
 *
 * // 设置字体大小
 * setFontSize(FONT_SIZES.LARGE)
 *
 * // 导出配置
 * const config = exportConfig()
 *
 * // 导入配置
 * importConfig(config)
 * ```
 */
export function useUserPreferences(options = {}) {
  const {
    storageKey = 'user_preferences',
    autoSave = true,
    defaultPreferences = {}
  } = options

  // === 响应式状态 ===
  /** 用户偏好配置 */
  const preferences = reactive({
    ...DEFAULT_PREFERENCES,
    ...defaultPreferences
  })

  /** 是否已初始化 */
  const isInitialized = ref(false)

  /** 当前实际主题（解析system后的值） */
  const actualTheme = ref(THEME_TYPES.LIGHT)

  /** 系统主题偏好 */
  const systemTheme = ref(THEME_TYPES.LIGHT)

  /** 是否正在加载 */
  const isLoading = ref(false)

  /** 最后保存时间 */
  const lastSavedAt = ref(null)

  /** 配置变更历史 */
  const changeHistory = ref([])

  /** 是否有未保存的更改 */
  const hasUnsavedChanges = ref(false)

  // === 计算属性 ===
  /** 是否为暗色主题 */
  const isDarkTheme = computed(() => {
    return actualTheme.value === THEME_TYPES.DARK
  })

  /** 当前字体大小（像素值） */
  const currentFontSize = computed(() => {
    return FONT_SIZE_MAP[preferences.font.size] || 14
  })

  /** 主题CSS变量 */
  const themeVariables = computed(() => {
    const isDark = isDarkTheme.value
    return {
      '--primary-color': preferences.theme.primaryColor,
      '--success-color': preferences.theme.successColor,
      '--warning-color': preferences.theme.warningColor,
      '--error-color': preferences.theme.errorColor,
      '--border-radius': `${preferences.theme.borderRadius}px`,
      '--sidebar-width': `${preferences.layout.sidebarWidth}px`,
      '--header-height': `${preferences.layout.headerHeight}px`,
      '--content-padding': `${preferences.layout.contentPadding}px`,
      '--font-size-base': `${currentFontSize.value}px`,
      '--font-family': preferences.font.family,
      '--line-height': preferences.font.lineHeight,
      '--code-font-family': preferences.font.codeFont,
      '--animation-duration': `${preferences.animation.duration}ms`,
      '--animation-easing': preferences.animation.easing,
      // 主题相关变量
      '--bg-color': isDark ? '#141414' : '#ffffff',
      '--bg-secondary': isDark ? '#1f1f1f' : '#f5f5f5',
      '--text-color': isDark ? '#ffffffd9' : '#000000d9',
      '--text-secondary': isDark ? '#ffffff73' : '#00000073',
      '--border-color': isDark ? '#434343' : '#d9d9d9',
      '--shadow-color': isDark ? 'rgba(0, 0, 0, 0.45)' : 'rgba(0, 0, 0, 0.08)'
    }
  })

  /**
   * 检测系统主题
   *
   * @internal
   */
  function detectSystemTheme() {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      systemTheme.value = THEME_TYPES.DARK
    } else {
      systemTheme.value = THEME_TYPES.LIGHT
    }
  }

  /**
   * 更新实际主题
   *
   * @internal
   */
  function updateActualTheme() {
    if (preferences.theme.type === THEME_TYPES.SYSTEM) {
      actualTheme.value = systemTheme.value
    } else {
      actualTheme.value = preferences.theme.type
    }

    // 更新HTML类名
    document.documentElement.classList.remove('light', 'dark')
    document.documentElement.classList.add(actualTheme.value)
  }

  /**
   * 应用CSS变量
   *
   * @internal
   */
  function applyCSSVariables() {
    const root = document.documentElement
    Object.entries(themeVariables.value).forEach(([key, value]) => {
      root.style.setProperty(key, value)
    })
  }

  /**
   * 设置主题
   *
   * @param {string} themeType - 主题类型
   *
   * @example
   * ```javascript
   * setTheme(THEME_TYPES.DARK)
   * setTheme(THEME_TYPES.SYSTEM)
   * ```
   */
  function setTheme(themeType) {
    if (!Object.values(THEME_TYPES).includes(themeType)) {
      console.warn(`[UserPreferences] 无效的主题类型: ${themeType}`)
      return
    }

    const oldValue = preferences.theme.type
    preferences.theme.type = themeType
    updateActualTheme()

    recordChange('theme.type', oldValue, themeType)
    hasUnsavedChanges.value = true

    if (autoSave) {
      saveToStorage()
    }
  }

  /**
   * 切换主题（亮色/暗色）
   */
  function toggleTheme() {
    const newTheme = actualTheme.value === THEME_TYPES.DARK
      ? THEME_TYPES.LIGHT
      : THEME_TYPES.DARK
    setTheme(newTheme)
  }

  /**
   * 设置主题色
   *
   * @param {string} color - 主题色（十六进制）
   */
  function setPrimaryColor(color) {
    const oldValue = preferences.theme.primaryColor
    preferences.theme.primaryColor = color
    applyCSSVariables()

    recordChange('theme.primaryColor', oldValue, color)
    hasUnsavedChanges.value = true

    if (autoSave) {
      saveToStorage()
    }
  }

  /**
   * 更新布局设置
   *
   * @param {Object} layoutConfig - 布局配置
   *
   * @example
   * ```javascript
   * updateLayout({
   *   sidebarWidth: 280,
   *   sidebarCollapsed: false,
   *   showStatusBar: true
   * })
   * ```
   */
  function updateLayout(layoutConfig) {
    const oldValues = { ...preferences.layout }
    Object.assign(preferences.layout, layoutConfig)
    applyCSSVariables()

    recordChange('layout', oldValues, { ...preferences.layout })
    hasUnsavedChanges.value = true

    if (autoSave) {
      saveToStorage()
    }
  }

  /**
   * 切换侧边栏折叠状态
   */
  function toggleSidebar() {
    updateLayout({ sidebarCollapsed: !preferences.layout.sidebarCollapsed })
  }

  /**
   * 设置字体大小
   *
   * @param {string} fontSize - 字体大小
   */
  function setFontSize(fontSize) {
    if (!Object.values(FONT_SIZES).includes(fontSize)) {
      console.warn(`[UserPreferences] 无效的字体大小: ${fontSize}`)
      return
    }

    const oldValue = preferences.font.size
    preferences.font.size = fontSize
    applyCSSVariables()

    recordChange('font.size', oldValue, fontSize)
    hasUnsavedChanges.value = true

    if (autoSave) {
      saveToStorage()
    }
  }

  /**
   * 增大字体
   */
  function increaseFontSize() {
    const sizes = Object.values(FONT_SIZES)
    const currentIndex = sizes.indexOf(preferences.font.size)
    if (currentIndex < sizes.length - 1) {
      setFontSize(sizes[currentIndex + 1])
    }
  }

  /**
   * 减小字体
   */
  function decreaseFontSize() {
    const sizes = Object.values(FONT_SIZES)
    const currentIndex = sizes.indexOf(preferences.font.size)
    if (currentIndex > 0) {
      setFontSize(sizes[currentIndex - 1])
    }
  }

  /**
   * 更新数据显示设置
   *
   * @param {Object} displayConfig - 显示配置
   */
  function updateDataDisplay(displayConfig) {
    const oldValues = { ...preferences.dataDisplay }
    Object.assign(preferences.dataDisplay, displayConfig)

    recordChange('dataDisplay', oldValues, { ...preferences.dataDisplay })
    hasUnsavedChanges.value = true

    if (autoSave) {
      saveToStorage()
    }
  }

  /**
   * 更新通知设置
   *
   * @param {Object} notificationConfig - 通知配置
   */
  function updateNotification(notificationConfig) {
    const oldValues = { ...preferences.notification }
    Object.assign(preferences.notification, notificationConfig)

    recordChange('notification', oldValues, { ...preferences.notification })
    hasUnsavedChanges.value = true

    if (autoSave) {
      saveToStorage()
    }
  }

  /**
   * 更新实验设置
   *
   * @param {Object} experimentConfig - 实验配置
   */
  function updateExperiment(experimentConfig) {
    const oldValues = { ...preferences.experiment }
    Object.assign(preferences.experiment, experimentConfig)

    recordChange('experiment', oldValues, { ...preferences.experiment })
    hasUnsavedChanges.value = true

    if (autoSave) {
      saveToStorage()
    }
  }

  /**
   * 更新高级设置
   *
   * @param {Object} advancedConfig - 高级配置
   */
  function updateAdvanced(advancedConfig) {
    const oldValues = { ...preferences.advanced }
    Object.assign(preferences.advanced, advancedConfig)

    recordChange('advanced', oldValues, { ...preferences.advanced })
    hasUnsavedChanges.value = true

    if (autoSave) {
      saveToStorage()
    }
  }

  /**
   * 更新动画设置
   *
   * @param {Object} animationConfig - 动画配置
   */
  function updateAnimation(animationConfig) {
    const oldValues = { ...preferences.animation }
    Object.assign(preferences.animation, animationConfig)
    applyCSSVariables()

    recordChange('animation', oldValues, { ...preferences.animation })
    hasUnsavedChanges.value = true

    if (autoSave) {
      saveToStorage()
    }
  }

  /**
   * 启用/禁用动画
   *
   * @param {boolean} enabled - 是否启用
   */
  function setAnimationEnabled(enabled) {
    updateAnimation({ enabled })
  }

  /**
   * 批量更新偏好设置
   *
   * @param {Object} newPreferences - 新的偏好设置
   */
  function updatePreferences(newPreferences) {
    const oldPreferences = JSON.parse(JSON.stringify(preferences))

    // 深度合并
    Object.keys(newPreferences).forEach(key => {
      if (typeof newPreferences[key] === 'object' && newPreferences[key] !== null) {
        preferences[key] = {
          ...preferences[key],
          ...newPreferences[key]
        }
      } else {
        preferences[key] = newPreferences[key]
      }
    })

    updateActualTheme()
    applyCSSVariables()

    recordChange('preferences', oldPreferences, JSON.parse(JSON.stringify(preferences)))
    hasUnsavedChanges.value = true

    if (autoSave) {
      saveToStorage()
    }
  }

  /**
   * 记录配置变更
   *
   * @param {string} key - 配置键
   * @param {*} oldValue - 旧值
   * @param {*} newValue - 新值
   * @internal
   */
  function recordChange(key, oldValue, newValue) {
    changeHistory.value.push({
      key,
      oldValue,
      newValue,
      timestamp: Date.now()
    })

    // 限制历史记录数量
    if (changeHistory.value.length > 100) {
      changeHistory.value = changeHistory.value.slice(-50)
    }
  }

  /**
   * 导出配置
   *
   * @param {Object} options - 导出选项
   * @param {boolean} [options.includeHistory=false] - 是否包含变更历史
   * @returns {string} JSON配置字符串
   */
  function exportConfig(options = {}) {
    const { includeHistory = false } = options

    const exportData = {
      version: '1.0',
      exportedAt: new Date().toISOString(),
      preferences: JSON.parse(JSON.stringify(preferences))
    }

    if (includeHistory) {
      exportData.changeHistory = [...changeHistory.value]
    }

    return JSON.stringify(exportData, null, 2)
  }

  /**
   * 导入配置
   *
   * @param {string} jsonString - JSON配置字符串
   * @param {boolean} [merge=true] - 是否合并现有配置
   * @returns {boolean} 是否导入成功
   */
  function importConfig(jsonString, merge = true) {
    try {
      const imported = JSON.parse(jsonString)

      if (!imported.preferences) {
        throw new Error('无效的配置格式')
      }

      if (merge) {
        updatePreferences(imported.preferences)
      } else {
        // 完全替换
        Object.keys(preferences).forEach(key => delete preferences[key])
        Object.assign(preferences, DEFAULT_PREFERENCES, imported.preferences)
        updateActualTheme()
        applyCSSVariables()
      }

      if (imported.changeHistory) {
        changeHistory.value = imported.changeHistory
      }

      hasUnsavedChanges.value = true

      if (autoSave) {
        saveToStorage()
      }

      return true
    } catch (error) {
      console.error('[UserPreferences] 导入配置失败:', error)
      return false
    }
  }

  /**
   * 保存到本地存储
   */
  function saveToStorage() {
    try {
      const data = {
        preferences: JSON.parse(JSON.stringify(preferences)),
        savedAt: Date.now()
      }
      localStorage.setItem(storageKey, JSON.stringify(data))
      lastSavedAt.value = Date.now()
      hasUnsavedChanges.value = false
    } catch (error) {
      console.error('[UserPreferences] 保存失败:', error)
    }
  }

  /**
   * 从本地存储加载
   *
   * @returns {boolean} 是否加载成功
   */
  function loadFromStorage() {
    isLoading.value = true

    try {
      const data = localStorage.getItem(storageKey)
      if (data) {
        const parsed = JSON.parse(data)

        // 深度合并保存的偏好
        Object.keys(parsed.preferences).forEach(key => {
          if (typeof parsed.preferences[key] === 'object' && parsed.preferences[key] !== null) {
            preferences[key] = {
              ...preferences[key],
              ...parsed.preferences[key]
            }
          } else {
            preferences[key] = parsed.preferences[key]
          }
        })

        return true
      }
    } catch (error) {
      console.error('[UserPreferences] 加载失败:', error)
    } finally {
      isLoading.value = false
    }

    return false
  }

  /**
   * 重置为默认配置
   *
   * @param {string} [category] - 要重置的类别，不传则重置全部
   */
  function resetToDefault(category) {
    if (category) {
      if (DEFAULT_PREFERENCES[category]) {
        const oldValue = JSON.parse(JSON.stringify(preferences[category]))
        preferences[category] = JSON.parse(JSON.stringify(DEFAULT_PREFERENCES[category]))

        recordChange(category, oldValue, preferences[category])
      }
    } else {
      const oldPreferences = JSON.parse(JSON.stringify(preferences))

      Object.keys(preferences).forEach(key => delete preferences[key])
      Object.assign(preferences, DEFAULT_PREFERENCES, defaultPreferences)

      recordChange('preferences', oldPreferences, JSON.parse(JSON.stringify(preferences)))
    }

    updateActualTheme()
    applyCSSVariables()
    hasUnsavedChanges.value = true

    if (autoSave) {
      saveToStorage()
    }
  }

  /**
   * 获取偏好设置值
   *
   * @param {string} path - 配置路径（如 'theme.type'）
   * @param {*} defaultValue - 默认值
   * @returns {*} 配置值
   */
  function getPreference(path, defaultValue = undefined) {
    const keys = path.split('.')
    let value = preferences

    for (const key of keys) {
      if (value && typeof value === 'object' && key in value) {
        value = value[key]
      } else {
        return defaultValue
      }
    }

    return value
  }

  /**
   * 设置偏好设置值
   *
   * @param {string} path - 配置路径（如 'theme.type'）
   * @param {*} value - 配置值
   */
  function setPreference(path, value) {
    const keys = path.split('.')
    const lastKey = keys.pop()
    let target = preferences

    for (const key of keys) {
      if (!(key in target)) {
        target[key] = {}
      }
      target = target[key]
    }

    const oldValue = target[lastKey]
    target[lastKey] = value

    recordChange(path, oldValue, value)
    hasUnsavedChanges.value = true

    // 应用特定配置
    if (path.startsWith('theme.')) {
      updateActualTheme()
    }
    applyCSSVariables()

    if (autoSave) {
      saveToStorage()
    }
  }

  // === 系统主题变化监听 ===
  let mediaQuery = null

  /**
   * 初始化
   */
  function init() {
    if (isInitialized.value) return

    // 检测系统主题
    detectSystemTheme()

    // 监听系统主题变化
    if (window.matchMedia) {
      mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      mediaQuery.addEventListener('change', (e) => {
        systemTheme.value = e.matches ? THEME_TYPES.DARK : THEME_TYPES.LIGHT
        updateActualTheme()
      })
    }

    // 加载保存的配置
    loadFromStorage()

    // 应用主题和CSS变量
    updateActualTheme()
    applyCSSVariables()

    isInitialized.value = true
  }

  // === 生命周期 ===
  onMounted(() => {
    init()
  })

  onUnmounted(() => {
    if (mediaQuery) {
      mediaQuery.removeEventListener('change', detectSystemTheme)
    }
  })

  // 监听偏好变化，自动应用
  watch(
    () => preferences.theme.type,
    () => {
      updateActualTheme()
    }
  )

  watch(
    themeVariables,
    () => {
      applyCSSVariables()
    },
    { deep: true }
  )

  return {
    // 状态
    preferences,
    isInitialized,
    actualTheme,
    systemTheme,
    isLoading,
    lastSavedAt,
    changeHistory,
    hasUnsavedChanges,

    // 计算属性
    isDarkTheme,
    currentFontSize,
    themeVariables,

    // 主题方法
    setTheme,
    toggleTheme,
    setPrimaryColor,

    // 布局方法
    updateLayout,
    toggleSidebar,

    // 字体方法
    setFontSize,
    increaseFontSize,
    decreaseFontSize,

    // 其他设置方法
    updateDataDisplay,
    updateNotification,
    updateExperiment,
    updateAdvanced,
    updateAnimation,
    setAnimationEnabled,

    // 通用方法
    updatePreferences,
    getPreference,
    setPreference,
    exportConfig,
    importConfig,
    saveToStorage,
    loadFromStorage,
    resetToDefault,
    init
  }
}

/**
 * 默认偏好配置（导出供外部使用）
 */
export { DEFAULT_PREFERENCES }
