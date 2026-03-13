/**
 * @file useDataFreshness.js
 * @path src/composables/
 * @description 数据新鲜度管理组合式函数，跟踪数据更新时间、计算新鲜度、管理过期状态
 * @author Agent
 * @date 2024-03-07
 * @dependencies vue
 */

import { ref, computed, onUnmounted } from 'vue'

/**
 * 数据新鲜度级别枚举
 */
export const FRESHNESS_LEVEL = {
  FRESH: 'fresh',       // 新鲜（0-5秒）
  NORMAL: 'normal',     // 正常（5-30秒）
  STALE: 'stale',       // 陈旧（30-60秒）
  EXPIRED: 'expired'    // 过期（>60秒）
}

/**
 * 数据新鲜度管理组合式函数
 * 
 * @param {Object} options - 配置选项
 * @param {number} [options.freshThreshold=5000] - 新鲜阈值（毫秒）
 * @param {number} [options.normalThreshold=30000] - 正常阈值（毫秒）
 * @param {number} [options.staleThreshold=60000] - 陈旧阈值（毫秒）
 * @param {number} [options.updateInterval=1000] - 新鲜度更新间隔（毫秒）
 * @returns {Object} 数据新鲜度管理对象
 * 
 * @example
 * ```javascript
 * const freshness = useDataFreshness({
 *   freshThreshold: 5000,
 *   normalThreshold: 30000,
 *   staleThreshold: 60000
 * })
 * 
 * // 更新数据时间戳
 * freshness.updateTimestamp()
 * 
 * // 获取新鲜度信息
 * console.log(freshness.freshnessLevel.value) // 'fresh'
 * console.log(freshness.freshnessText.value)  // '3秒前'
 * ```
 */
export function useDataFreshness(options = {}) {
  const {
    freshThreshold = 5000,
    normalThreshold = 30000,
    staleThreshold = 60000,
    updateInterval = 1000
  } = options

  // ==================== 响应式状态 ====================

  /** 数据最后更新时间戳 */
  const lastUpdateTime = ref(null)

  /** 当前时间戳（定时更新） */
  const currentTime = ref(Date.now())

  /** 新鲜度更新定时器 */
  let freshnessTimer = null

  // ==================== 计算属性 ====================

  /**
   * 距离上次更新的时间差（毫秒）
   */
  const timeSinceUpdate = computed(() => {
    if (!lastUpdateTime.value) return Infinity
    return currentTime.value - lastUpdateTime.value
  })

  /**
   * 数据新鲜度级别
   */
  const freshnessLevel = computed(() => {
    if (!lastUpdateTime.value) return FRESHNESS_LEVEL.EXPIRED
    
    const elapsed = timeSinceUpdate.value
    
    if (elapsed <= freshThreshold) {
      return FRESHNESS_LEVEL.FRESH
    } else if (elapsed <= normalThreshold) {
      return FRESHNESS_LEVEL.NORMAL
    } else if (elapsed <= staleThreshold) {
      return FRESHNESS_LEVEL.STALE
    } else {
      return FRESHNESS_LEVEL.EXPIRED
    }
  })

  /**
   * 新鲜度状态类型（用于UI样式）
   */
  const freshnessStatusType = computed(() => {
    switch (freshnessLevel.value) {
      case FRESHNESS_LEVEL.FRESH:
        return 'success'
      case FRESHNESS_LEVEL.NORMAL:
        return 'info'
      case FRESHNESS_LEVEL.STALE:
        return 'warning'
      case FRESHNESS_LEVEL.EXPIRED:
        return 'danger'
      default:
        return 'info'
    }
  })

  /**
   * 新鲜度文本描述
   */
  const freshnessText = computed(() => {
    if (!lastUpdateTime.value) return '无数据'
    
    const elapsed = timeSinceUpdate.value
    
    // 小于1秒
    if (elapsed < 1000) {
      return '刚刚'
    }
    
    // 小于1分钟
    if (elapsed < 60000) {
      const seconds = Math.floor(elapsed / 1000)
      return `${seconds}秒前`
    }
    
    // 小于1小时
    if (elapsed < 3600000) {
      const minutes = Math.floor(elapsed / 60000)
      return `${minutes}分钟前`
    }
    
    // 小于24小时
    if (elapsed < 86400000) {
      const hours = Math.floor(elapsed / 3600000)
      return `${hours}小时前`
    }
    
    // 大于24小时
    const days = Math.floor(elapsed / 86400000)
    return `${days}天前`
  })

  /**
   * 格式化的最后更新时间
   */
  const formattedLastUpdate = computed(() => {
    if (!lastUpdateTime.value) return '--'
    
    const date = new Date(lastUpdateTime.value)
    const hours = date.getHours().toString().padStart(2, '0')
    const minutes = date.getMinutes().toString().padStart(2, '0')
    const seconds = date.getSeconds().toString().padStart(2, '0')
    
    return `${hours}:${minutes}:${seconds}`
  })

  /**
   * 数据是否过期
   */
  const isExpired = computed(() => {
    return freshnessLevel.value === FRESHNESS_LEVEL.EXPIRED
  })

  /**
   * 数据是否需要警告
   */
  const needsWarning = computed(() => {
    return freshnessLevel.value === FRESHNESS_LEVEL.STALE || 
           freshnessLevel.value === FRESHNESS_LEVEL.EXPIRED
  })

  // ==================== 方法 ====================

  /**
   * 更新数据时间戳
   * 
   * @param {number} [timestamp] - 可选的时间戳，默认使用当前时间
   */
  function updateTimestamp(timestamp) {
    lastUpdateTime.value = timestamp || Date.now()
  }

  /**
   * 重置新鲜度状态
   */
  function reset() {
    lastUpdateTime.value = null
  }

  /**
   * 启动新鲜度定时更新
   * 
   * @internal 内部方法
   */
  function startFreshnessTimer() {
    stopFreshnessTimer()
    
    freshnessTimer = setInterval(() => {
      currentTime.value = Date.now()
    }, updateInterval)
  }

  /**
   * 停止新鲜度定时更新
   * 
   * @internal 内部方法
   */
  function stopFreshnessTimer() {
    if (freshnessTimer) {
      clearInterval(freshnessTimer)
      freshnessTimer = null
    }
  }

  /**
   * 获取新鲜度详细信息
   * 
   * @returns {Object} 新鲜度详细信息对象
   */
  function getFreshnessInfo() {
    return {
      lastUpdateTime: lastUpdateTime.value,
      timeSinceUpdate: timeSinceUpdate.value,
      level: freshnessLevel.value,
      statusType: freshnessStatusType.value,
      text: freshnessText.value,
      isExpired: isExpired.value,
      needsWarning: needsWarning.value
    }
  }

  // ==================== 生命周期 ====================

  // 启动定时器
  startFreshnessTimer()

  // 组件卸载时清理
  onUnmounted(() => {
    stopFreshnessTimer()
  })

  // ==================== 返回值 ====================

  return {
    // 状态
    lastUpdateTime,
    currentTime,
    timeSinceUpdate,
    
    // 计算属性
    freshnessLevel,
    freshnessStatusType,
    freshnessText,
    formattedLastUpdate,
    isExpired,
    needsWarning,
    
    // 方法
    updateTimestamp,
    reset,
    getFreshnessInfo
  }
}

/**
 * 创建多数据源新鲜度管理器
 * 
 * @param {Array<string>} dataKeys - 数据源键名数组
 * @param {Object} options - 配置选项
 * @returns {Object} 多数据源新鲜度管理对象
 * 
 * @example
 * ```javascript
 * const manager = createFreshnessManager(['motor', 'temperature', 'piezo'])
 * 
 * // 更新单个数据源
 * manager.updateDataTimestamp('motor')
 * 
 * // 获取所有数据源的新鲜度状态
 * console.log(manager.allFreshnessStatus.value)
 * ```
 */
export function createFreshnessManager(dataKeys, options = {}) {
  const freshnessMap = ref({})
  const managers = {}

  // 为每个数据源创建新鲜度管理器
  dataKeys.forEach(key => {
    managers[key] = useDataFreshness(options)
    freshnessMap.value[key] = managers[key].getFreshnessInfo()
  })

  /**
   * 更新指定数据源的时间戳
   * 
   * @param {string} key - 数据源键名
   * @param {number} [timestamp] - 可选的时间戳
   */
  function updateDataTimestamp(key, timestamp) {
    if (managers[key]) {
      managers[key].updateTimestamp(timestamp)
      freshnessMap.value[key] = managers[key].getFreshnessInfo()
    }
  }

  /**
   * 重置指定数据源的新鲜度
   * 
   * @param {string} key - 数据源键名
   */
  function resetDataFreshness(key) {
    if (managers[key]) {
      managers[key].reset()
      freshnessMap.value[key] = managers[key].getFreshnessInfo()
    }
  }

  /**
   * 重置所有数据源的新鲜度
   */
  function resetAll() {
    dataKeys.forEach(key => {
      resetDataFreshness(key)
    })
  }

  /**
   * 获取所有数据源的新鲜度状态
   */
  const allFreshnessStatus = computed(() => {
    const status = {}
    dataKeys.forEach(key => {
      if (managers[key]) {
        status[key] = managers[key].getFreshnessInfo()
      }
    })
    return status
  })

  /**
   * 是否有任何数据源过期
   */
  const hasExpiredData = computed(() => {
    return dataKeys.some(key => {
      return managers[key]?.isExpired.value
    })
  })

  /**
   * 是否有任何数据源需要警告
   */
  const hasWarningData = computed(() => {
    return dataKeys.some(key => {
      return managers[key]?.needsWarning.value
    })
  })

  /**
   * 获取需要警告的数据源列表
   */
  const warningDataKeys = computed(() => {
    return dataKeys.filter(key => {
      return managers[key]?.needsWarning.value
    })
  })

  return {
    // 状态
    freshnessMap,
    allFreshnessStatus,
    hasExpiredData,
    hasWarningData,
    warningDataKeys,
    
    // 方法
    updateDataTimestamp,
    resetDataFreshness,
    resetAll,
    
    // 单个管理器访问
    managers
  }
}
