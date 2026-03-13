/**
 * @file layout.js
 * @path src/stores/
 * @description 布局状态管理，控制侧边栏、顶部栏、状态栏等UI状态，并与路由系统协调
 * @author Agent
 * @date 2024-03-07
 * @dependencies pinia, vue
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ANOMALY_LEVEL, ANOMALY_TYPE } from '../composables/useDataAnomaly'

/**
 * 布局状态Store
 * 
 * 管理全局布局状态，包括：
 * - 侧边栏折叠状态
 * - 当前激活模块
 * - 状态栏信息
 * - 数据告警管理
 * - 与路由系统的协调
 */
export const useLayoutStore = defineStore('layout', () => {
  // ==================== 侧边栏状态 ====================
  
  /** 侧边栏是否折叠 */
  const isSidebarCollapsed = ref(false)
  
  /** 侧边栏宽度配置 */
  const sidebarWidth = {
    collapsed: 64,
    expanded: 240
  }
  
  /**
   * 当前侧边栏宽度
   */
  const currentSidebarWidth = computed(() => {
    return isSidebarCollapsed.value ? sidebarWidth.collapsed : sidebarWidth.expanded
  })
  
  /**
   * 切换侧边栏折叠状态
   */
  function toggleSidebar() {
    isSidebarCollapsed.value = !isSidebarCollapsed.value
    saveLayoutPreference()
  }
  
  /**
   * 设置侧边栏折叠状态
   * @param {boolean} collapsed - 是否折叠
   */
  function setSidebarCollapsed(collapsed) {
    isSidebarCollapsed.value = collapsed
    saveLayoutPreference()
  }
  
  // ==================== 模块导航状态 ====================
  
  /**
   * 模块配置
   * 定义四个主要功能模块及其子功能
   */
  const modules = ref([
    {
      id: 'experiment',
      name: '实验控制',
      icon: 'Setting',
      path: '/experiment',
      children: [
        { id: 'motor', name: '电机控制', icon: 'Connection', path: '/experiment/motor' },
        { id: 'piezo', name: '压电陶瓷', icon: 'Grid', path: '/experiment/piezo' },
        { id: 'electromagnet', name: '电磁铁', icon: 'Cpu', path: '/experiment/electromagnet' },
        { id: 'safety', name: '安全面板', icon: 'Warning', path: '/experiment/safety' },
        { id: 'temperature', name: '温度控制', icon: 'Sunny', path: '/experiment/temperature' },
        { id: 'ammeter', name: '微电流', icon: 'Aim', path: '/experiment/ammeter' }
      ]
    },
    {
      id: 'device',
      name: '设备管理',
      icon: 'Monitor',
      path: '/device',
      children: [
        { id: 'status', name: '设备状态', icon: 'DataBoard', path: '/device/status' },
        { id: 'connection', name: '连接配置', icon: 'Link', path: '/device/connection' },
        { id: 'pr-path', name: 'PR路径配置', icon: 'Route', path: '/device/pr-path' }
      ]
    },
    {
      id: 'analysis',
      name: '数据分析',
      icon: 'DataAnalysis',
      path: '/analysis',
      children: [
        { id: 'realtime', name: '实时数据', icon: 'TrendCharts', path: '/analysis/realtime' },
        { id: 'history', name: '历史数据', icon: 'Clock', path: '/analysis/history' },
        { id: 'charts', name: '图表分析', icon: 'PieChart', path: '/analysis/charts' }
      ]
    },
    {
      id: 'settings',
      name: '系统设置',
      icon: 'Tools',
      path: '/settings',
      children: [
        { id: 'audit', name: '审计日志', icon: 'Document', path: '/settings/audit' },
        { id: 'config', name: '系统配置', icon: 'Setting', path: '/settings/config' },
        { id: 'about', name: '关于', icon: 'InfoFilled', path: '/settings/about' }
      ]
    }
  ])
  
  /** 当前激活的模块ID */
  const activeModuleId = ref('experiment')
  
  /** 当前激活的子功能ID */
  const activeChildId = ref('motor')
  
  /**
   * 获取当前激活的模块
   */
  const activeModule = computed(() => {
    return modules.value.find(m => m.id === activeModuleId.value) || modules.value[0]
  })
  
  /**
   * 获取当前激活的子功能
   */
  const activeChild = computed(() => {
    return activeModule.value?.children.find(c => c.id === activeChildId.value) || activeModule.value?.children[0]
  })
  
  /**
   * 设置激活模块
   * @param {string} moduleId - 模块ID
   */
  function setActiveModule(moduleId) {
    activeModuleId.value = moduleId
    // 默认激活第一个子功能
    const module = modules.value.find(m => m.id === moduleId)
    if (module && module.children.length > 0) {
      activeChildId.value = module.children[0].id
    }
  }
  
  /**
   * 设置激活子功能
   * @param {string} childId - 子功能ID
   */
  function setActiveChild(childId) {
    activeChildId.value = childId
  }
  
  /**
   * 根据路由路径设置激活状态
   * @param {string} path - 当前路由路径
   */
  function setActiveByPath(path) {
    for (const module of modules.value) {
      for (const child of module.children) {
        if (path.startsWith(child.path) || path === child.path) {
          activeModuleId.value = module.id
          activeChildId.value = child.id
          return
        }
      }
    }
  }
  
  // ==================== 状态栏信息 ====================
  
  /** 连接状态 */
  const connectionStatus = ref('disconnected') // disconnected | connecting | connected
  
  /** 连接状态文本映射 */
  const connectionStatusText = {
    disconnected: '未连接',
    connecting: '连接中...',
    connected: '已连接'
  }
  
  /** 当前操作提示 */
  const operationTip = ref('系统就绪')
  
  /** 警告信息列表 */
  const warnings = ref([])
  
  /** 当前时间戳 */
  const currentTimestamp = ref(new Date().toLocaleString('zh-CN'))
  
  /** 最后更新时间戳 */
  const lastUpdateTime = ref(Date.now())
  
  /** WebSocket重连进度 */
  const wsReconnectProgress = ref({
    attempt: 0,
    maxAttempts: 3,
    delay: 0,
    isReconnecting: false
  })
  
  /** WebSocket推送频率（条/秒） */
  const wsPushFrequency = ref(0)
  
  /** WebSocket数据延迟（毫秒） */
  const wsDataLatency = ref(0)
  
  /** WebSocket是否达到最大重连次数 */
  const wsMaxReconnectReached = ref(false)
  
  /** 路由加载状态 */
  const routeLoading = ref(false)
  
  /** 路由加载进度 */
  const routeLoadingProgress = ref(0)
  
  /**
   * 设置路由加载状态
   * @param {boolean} loading - 是否正在加载
   */
  function setRouteLoading(loading) {
    routeLoading.value = loading
    if (!loading) {
      routeLoadingProgress.value = 0
    }
  }
  
  /**
   * 设置路由加载进度
   * @param {number} progress - 加载进度（0-100）
   */
  function setRouteLoadingProgress(progress) {
    routeLoadingProgress.value = Math.min(100, Math.max(0, progress))
  }
  
  /**
   * 更新连接状态
   * @param {string} status - 连接状态
   */
  function setConnectionStatus(status) {
    connectionStatus.value = status
  }
  
  /**
   * 设置操作提示
   * @param {string} tip - 提示文本
   */
  function setOperationTip(tip) {
    operationTip.value = tip
  }
  
  /**
   * 添加警告信息
   * @param {string} message - 警告消息
   * @param {string} type - 警告类型 (warning | error)
   */
  function addWarning(message, type = 'warning') {
    const id = Date.now()
    warnings.value.push({ id, message, type, timestamp: new Date() })
    // 最多保留5条警告
    if (warnings.value.length > 5) {
      warnings.value.shift()
    }
  }
  
  /**
   * 移除警告信息
   * @param {number} id - 警告ID
   */
  function removeWarning(id) {
    const index = warnings.value.findIndex(w => w.id === id)
    if (index !== -1) {
      warnings.value.splice(index, 1)
    }
  }
  
  /**
   * 清空所有警告
   */
  function clearWarnings() {
    warnings.value = []
  }
  
  /**
   * 更新时间戳
   */
  function updateTimestamp() {
    currentTimestamp.value = new Date().toLocaleString('zh-CN')
    lastUpdateTime.value = Date.now()
  }
  
  /**
   * 更新WebSocket重连进度
   * @param {Object} progress - 重连进度信息
   * @param {number} progress.attempt - 当前尝试次数
   * @param {number} progress.maxAttempts - 最大尝试次数
   * @param {number} progress.delay - 重连延迟（毫秒）
   */
  function updateWsReconnectProgress(progress) {
    wsReconnectProgress.value = {
      ...wsReconnectProgress.value,
      ...progress,
      isReconnecting: true
    }
  }
  
  /**
   * 重置WebSocket重连进度
   */
  function resetWsReconnectProgress() {
    wsReconnectProgress.value = {
      attempt: 0,
      maxAttempts: 3,
      delay: 0,
      isReconnecting: false
    }
  }
  
  /**
   * 更新WebSocket推送频率
   * @param {number} frequency - 推送频率（条/秒）
   */
  function updateWsPushFrequency(frequency) {
    wsPushFrequency.value = frequency
  }
  
  /**
   * 更新WebSocket数据延迟
   * @param {number} latency - 数据延迟（毫秒）
   */
  function updateWsDataLatency(latency) {
    wsDataLatency.value = latency
  }
  
  /**
   * 设置WebSocket最大重连状态
   * @param {boolean} reached - 是否已达到最大重连次数
   */
  function setWsMaxReconnectReached(reached) {
    wsMaxReconnectReached.value = reached
  }

  // ==================== 数据告警管理 ====================

  /** 数据告警列表 */
  const dataAlerts = ref([])

  /** 告警计数器 */
  let alertIdCounter = 0

  /**
   * 添加数据告警
   * 
   * @param {Object} alert - 告警信息
   * @param {string} alert.source - 数据源（如 'motor', 'temperature'）
   * @param {string} alert.type - 告警类型
   * @param {string} alert.level - 告警级别
   * @param {string} alert.message - 告警消息
   * @param {Object} [alert.details] - 详细信息
   * @returns {number} 告警ID
   */
  function addDataAlert(alert) {
    const id = ++alertIdCounter
    const newAlert = {
      id,
      source: alert.source || 'unknown',
      type: alert.type || ANOMALY_TYPE.OUT_OF_RANGE,
      level: alert.level || ANOMALY_LEVEL.WARNING,
      message: alert.message,
      details: alert.details || {},
      timestamp: Date.now(),
      acknowledged: false
    }
    
    dataAlerts.value.push(newAlert)
    
    // 限制告警数量
    if (dataAlerts.value.length > 20) {
      dataAlerts.value = dataAlerts.value.slice(-20)
    }
    
    // 同时添加到警告列表
    const warningType = alert.level === ANOMALY_LEVEL.ERROR || alert.level === ANOMALY_LEVEL.CRITICAL 
      ? 'error' 
      : 'warning'
    addWarning(`[${alert.source}] ${alert.message}`, warningType)
    
    return id
  }

  /**
   * 确认数据告警
   * 
   * @param {number} alertId - 告警ID
   */
  function acknowledgeDataAlert(alertId) {
    const alert = dataAlerts.value.find(a => a.id === alertId)
    if (alert) {
      alert.acknowledged = true
    }
  }

  /**
   * 清除数据告警
   * 
   * @param {number} [alertId] - 可选的告警ID，不提供则清除所有
   */
  function clearDataAlert(alertId) {
    if (alertId !== undefined) {
      const index = dataAlerts.value.findIndex(a => a.id === alertId)
      if (index !== -1) {
        dataAlerts.value.splice(index, 1)
      }
    } else {
      dataAlerts.value = []
    }
  }

  /**
   * 清除已确认的告警
   */
  function clearAcknowledgedAlerts() {
    dataAlerts.value = dataAlerts.value.filter(a => !a.acknowledged)
  }

  /**
   * 清除指定数据源的告警
   * 
   * @param {string} source - 数据源名称
   */
  function clearSourceAlerts(source) {
    dataAlerts.value = dataAlerts.value.filter(a => a.source !== source)
  }

  /**
   * 获取未确认的告警数量
   */
  const unacknowledgedAlertCount = computed(() => {
    return dataAlerts.value.filter(a => !a.acknowledged).length
  })

  /**
   * 获取严重告警数量
   */
  const criticalAlertCount = computed(() => {
    return dataAlerts.value.filter(a => 
      a.level === ANOMALY_LEVEL.CRITICAL || a.level === ANOMALY_LEVEL.ERROR
    ).length
  })

  /**
   * 是否有未确认的告警
   */
  const hasUnacknowledgedAlerts = computed(() => {
    return unacknowledgedAlertCount.value > 0
  })

  /**
   * 是否有严重告警
   */
  const hasCriticalAlerts = computed(() => {
    return criticalAlertCount.value > 0
  })

  // ==================== 本地存储 ====================
  
  /**
   * 保存布局偏好到本地存储
   */
  function saveLayoutPreference() {
    try {
      const preference = {
        isSidebarCollapsed: isSidebarCollapsed.value,
        activeModuleId: activeModuleId.value,
        activeChildId: activeChildId.value
      }
      localStorage.setItem('layout-preference', JSON.stringify(preference))
    } catch (error) {
      console.warn('[LayoutStore] Failed to save layout preference:', error)
    }
  }
  
  /**
   * 从本地存储加载布局偏好
   */
  function loadLayoutPreference() {
    try {
      const saved = localStorage.getItem('layout-preference')
      if (saved) {
        const preference = JSON.parse(saved)
        if (preference.isSidebarCollapsed !== undefined) {
          isSidebarCollapsed.value = preference.isSidebarCollapsed
        }
        if (preference.activeModuleId) {
          activeModuleId.value = preference.activeModuleId
        }
        if (preference.activeChildId) {
          activeChildId.value = preference.activeChildId
        }
      }
    } catch (error) {
      console.warn('[LayoutStore] Failed to load layout preference:', error)
    }
  }
  
  // ==================== 初始化 ====================
  
  // 加载保存的布局偏好
  loadLayoutPreference()
  
  // 定时更新时间戳
  if (typeof window !== 'undefined') {
    setInterval(updateTimestamp, 1000)
  }
  
  // ==================== 导出 ====================
  
  return {
    // 侧边栏状态
    isSidebarCollapsed,
    sidebarWidth,
    currentSidebarWidth,
    toggleSidebar,
    setSidebarCollapsed,
    
    // 模块导航
    modules,
    activeModuleId,
    activeChildId,
    activeModule,
    activeChild,
    setActiveModule,
    setActiveChild,
    setActiveByPath,
    
    // 状态栏
    connectionStatus,
    connectionStatusText,
    operationTip,
    warnings,
    currentTimestamp,
    lastUpdateTime,
    wsReconnectProgress,
    wsPushFrequency,
    wsDataLatency,
    wsMaxReconnectReached,
    routeLoading,
    routeLoadingProgress,
    setConnectionStatus,
    setOperationTip,
    addWarning,
    removeWarning,
    clearWarnings,
    updateTimestamp,
    updateWsReconnectProgress,
    resetWsReconnectProgress,
    updateWsPushFrequency,
    updateWsDataLatency,
    setWsMaxReconnectReached,
    setRouteLoading,
    setRouteLoadingProgress,
    
    // 数据告警
    dataAlerts,
    addDataAlert,
    acknowledgeDataAlert,
    clearDataAlert,
    clearAcknowledgedAlerts,
    clearSourceAlerts,
    unacknowledgedAlertCount,
    criticalAlertCount,
    hasUnacknowledgedAlerts,
    hasCriticalAlerts,
    
    // 本地存储
    saveLayoutPreference,
    loadLayoutPreference
  }
})
