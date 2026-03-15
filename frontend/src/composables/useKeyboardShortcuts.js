/**
 * @file useKeyboardShortcuts.js
 * @path src/composables/
 * @description 键盘快捷键管理组合式函数，支持全局快捷键注册、冲突检测、自定义配置
 * @author Agent
 * @date 2024-03-07
 * @dependencies vue
 */

import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'

/**
 * 默认快捷键配置
 */
const DEFAULT_SHORTCUTS = {
  // 全局操作
  'global.search': { key: 'f', ctrl: true, description: '全局搜索' },
  'global.help': { key: '?', shift: true, description: '显示帮助' },
  'global.escape': { key: 'Escape', description: '关闭弹窗/取消操作' },
  
  // 设备控制
  'device.connect': { key: 'c', ctrl: true, shift: true, description: '连接所有设备' },
  'device.disconnect': { key: 'd', ctrl: true, shift: true, description: '断开所有设备' },
  'device.refresh': { key: 'r', ctrl: true, description: '刷新设备状态' },
  
  // 实验操作
  'experiment.start': { key: 's', ctrl: true, description: '开始实验' },
  'experiment.stop': { key: 's', ctrl: true, shift: true, description: '停止实验' },
  'experiment.pause': { key: 'p', ctrl: true, description: '暂停/恢复实验' },
  'experiment.save': { key: 's', ctrl: true, alt: true, description: '保存实验数据' },
  
  // 数据操作
  'data.export': { key: 'e', ctrl: true, description: '导出数据' },
  'data.import': { key: 'i', ctrl: true, description: '导入数据' },
  'data.clear': { key: 'Delete', ctrl: true, shift: true, description: '清除数据' },
  
  // 视图切换
  'view.dashboard': { key: '1', ctrl: true, description: '切换到仪表盘' },
  'view.experiment': { key: '2', ctrl: true, description: '切换到实验控制' },
  'view.analysis': { key: '3', ctrl: true, description: '切换到数据分析' },
  'view.settings': { key: ',', ctrl: true, description: '打开设置' },
  
  // 历史操作
  'history.undo': { key: 'z', ctrl: true, description: '撤销' },
  'history.redo': { key: 'z', ctrl: true, shift: true, description: '重做' },
  'history.search': { key: 'h', ctrl: true, description: '搜索历史' },
  
  // 界面操作
  'ui.theme': { key: 't', ctrl: true, alt: true, description: '切换主题' },
  'ui.fullscreen': { key: 'F11', description: '全屏切换' },
  'ui.zoomIn': { key: '=', ctrl: true, description: '放大' },
  'ui.zoomOut': { key: '-', ctrl: true, description: '缩小' },
  'ui.zoomReset': { key: '0', ctrl: true, description: '重置缩放' },

  // 个人中心操作
  'profile.open': { key: 'p', ctrl: true, shift: true, description: '打开个人中心' },
  'profile.settings': { key: ',', ctrl: true, description: '打开偏好设置' },
  'profile.history': { key: 'h', ctrl: true, shift: true, description: '查看操作历史' }
}

/**
 * 修饰键状态追踪
 */
const modifierState = reactive({
  ctrl: false,
  alt: false,
  shift: false,
  meta: false
})

/**
 * 键盘快捷键管理组合式函数
 *
 * @param {Object} options - 配置选项
 * @param {boolean} [options.enabled=true] - 是否启用快捷键
 * @param {boolean} [options.preventDefault=true] - 是否阻止默认行为
 * @param {Object} [options.customShortcuts={}] - 自定义快捷键配置
 * @returns {Object} 快捷键状态与操作方法
 *
 * @example
 * ```javascript
 * const { register, unregister, trigger, getShortcuts } = useKeyboardShortcuts({
 *   enabled: true,
 *   customShortcuts: {
 *     'custom.action': { key: 'x', ctrl: true, description: '自定义操作' }
 *   }
 * })
 *
 * // 注册快捷键回调
 * register('experiment.start', () => {
 *   console.log('开始实验')
 * })
 *
 * // 手动触发快捷键
 * trigger('experiment.start')
 * ```
 */
export function useKeyboardShortcuts(options = {}) {
  const {
    enabled = true,
    preventDefault = true,
    customShortcuts = {}
  } = options

  // === 响应式状态 ===
  /** 快捷键是否启用 */
  const isEnabled = ref(enabled)
  /** 当前注册的快捷键配置 */
  const shortcuts = reactive({ ...DEFAULT_SHORTCUTS, ...customShortcuts })
  /** 快捷键回调映射 */
  const callbacks = reactive(new Map())
  /** 冲突检测结果 */
  const conflicts = ref([])
  /** 最后触发的快捷键 */
  const lastTriggered = ref(null)
  /** 按键历史（用于序列快捷键） */
  const keyHistory = ref([])
  /** 是否正在录制快捷键 */
  const isRecording = ref(false)
  /** 录制的快捷键序列 */
  const recordedSequence = ref([])

  // === 计算属性 ===
  /** 所有已注册的快捷键列表 */
  const registeredShortcuts = computed(() => {
    return Object.entries(shortcuts).map(([id, config]) => ({
      id,
      ...config,
      hasCallback: callbacks.has(id)
    }))
  })

  /** 按类别分组的快捷键 */
  const groupedShortcuts = computed(() => {
    const groups = {}
    registeredShortcuts.value.forEach(shortcut => {
      const category = shortcut.id.split('.')[0]
      if (!groups[category]) {
        groups[category] = []
      }
      groups[category].push(shortcut)
    })
    return groups
  })

  /**
   * 生成快捷键唯一标识符
   *
   * @param {Object} config - 快捷键配置
   * @returns {string} 快捷键标识符
   * @internal
   */
  function generateShortcutId(config) {
    const parts = []
    if (config.ctrl) parts.push('Ctrl')
    if (config.alt) parts.push('Alt')
    if (config.shift) parts.push('Shift')
    if (config.meta) parts.push('Meta')
    parts.push(config.key.toUpperCase())
    return parts.join('+')
  }

  /**
   * 检测快捷键冲突
   *
   * @returns {Array} 冲突列表
   * @internal
   */
  function detectConflicts() {
    const idMap = new Map()
    const conflictList = []

    Object.entries(shortcuts).forEach(([shortcutId, config]) => {
      const identifier = generateShortcutId(config)
      if (idMap.has(identifier)) {
        conflictList.push({
          identifier,
          shortcuts: [idMap.get(identifier), shortcutId]
        })
      } else {
        idMap.set(identifier, shortcutId)
      }
    })

    conflicts.value = conflictList
    return conflictList
  }

  /**
   * 匹配键盘事件与快捷键配置
   *
   * @param {KeyboardEvent} event - 键盘事件
   * @param {Object} config - 快捷键配置
   * @returns {boolean} 是否匹配
   * @internal
   */
  function matchShortcut(event, config) {
    const key = config.key.toLowerCase()
    const eventKey = event.key.toLowerCase()

    // 特殊键处理
    if (key === 'escape' && eventKey === 'escape') return true
    if (key === 'f11' && eventKey === 'f11') return true

    // 检查修饰键状态
    const ctrlMatch = config.ctrl ? (event.ctrlKey || event.metaKey) : !(event.ctrlKey || event.metaKey)
    const altMatch = config.alt ? event.altKey : !event.altKey
    const shiftMatch = config.shift ? event.shiftKey : !event.shiftKey

    // 检查主键
    const keyMatch = eventKey === key || event.code.toLowerCase() === `key${key}`

    return ctrlMatch && altMatch && shiftMatch && keyMatch
  }

  /**
   * 查找匹配的快捷键
   *
   * @param {KeyboardEvent} event - 键盘事件
   * @returns {string|null} 快捷键ID
   * @internal
   */
  function findMatchingShortcut(event) {
    for (const [id, config] of Object.entries(shortcuts)) {
      if (matchShortcut(event, config)) {
        return id
      }
    }
    return null
  }

  /**
   * 键盘按下事件处理
   *
   * @param {KeyboardEvent} event - 键盘事件
   * @internal
   */
  function handleKeyDown(event) {
    if (!isEnabled.value) return

    // 更新修饰键状态
    modifierState.ctrl = event.ctrlKey || event.metaKey
    modifierState.alt = event.altKey
    modifierState.shift = event.shiftKey
    modifierState.meta = event.metaKey

    // 录制模式
    if (isRecording.value) {
      recordedSequence.value.push({
        key: event.key,
        ctrl: event.ctrlKey,
        alt: event.altKey,
        shift: event.shiftKey,
        meta: event.metaKey
      })
      return
    }

    // 查找匹配的快捷键
    const shortcutId = findMatchingShortcut(event)

    if (shortcutId && callbacks.has(shortcutId)) {
      if (preventDefault) {
        event.preventDefault()
        event.stopPropagation()
      }

      lastTriggered.value = {
        id: shortcutId,
        timestamp: Date.now(),
        config: shortcuts[shortcutId]
      }

      // 执行回调
      const callback = callbacks.get(shortcutId)
      callback(event)
    }
  }

  /**
   * 键盘释放事件处理
   *
   * @param {KeyboardEvent} event - 键盘事件
   * @internal
   */
  function handleKeyUp(event) {
    // 更新修饰键状态
    modifierState.ctrl = event.ctrlKey || event.metaKey
    modifierState.alt = event.altKey
    modifierState.shift = event.shiftKey
    modifierState.meta = event.metaKey
  }

  /**
   * 注册快捷键回调
   *
   * @param {string} shortcutId - 快捷键ID
   * @param {Function} callback - 回调函数
   * @returns {Function} 取消注册函数
   *
   * @example
   * ```javascript
   * const unregister = register('experiment.start', () => {
   *   startExperiment()
   * })
   *
   * // 取消注册
   * unregister()
   * ```
   */
  function register(shortcutId, callback) {
    if (!shortcuts[shortcutId]) {
      console.warn(`[KeyboardShortcuts] 未知的快捷键ID: ${shortcutId}`)
      return () => {}
    }

    callbacks.set(shortcutId, callback)

    // 返回取消注册函数
    return () => unregister(shortcutId)
  }

  /**
   * 取消注册快捷键回调
   *
   * @param {string} shortcutId - 快捷键ID
   */
  function unregister(shortcutId) {
    callbacks.delete(shortcutId)
  }

  /**
   * 手动触发快捷键
   *
   * @param {string} shortcutId - 快捷键ID
   * @param {Object} [payload={}] - 传递给回调的数据
   * @returns {boolean} 是否成功触发
   */
  function trigger(shortcutId, payload = {}) {
    if (!isEnabled.value) return false

    if (callbacks.has(shortcutId)) {
      const callback = callbacks.get(shortcutId)
      callback({ type: 'manual', payload })
      lastTriggered.value = {
        id: shortcutId,
        timestamp: Date.now(),
        config: shortcuts[shortcutId]
      }
      return true
    }
    return false
  }

  /**
   * 添加自定义快捷键
   *
   * @param {string} shortcutId - 快捷键ID
   * @param {Object} config - 快捷键配置
   * @param {string} config.key - 主键
   * @param {boolean} [config.ctrl=false] - 是否需要Ctrl
   * @param {boolean} [config.alt=false] - 是否需要Alt
   * @param {boolean} [config.shift=false] - 是否需要Shift
   * @param {string} config.description - 快捷键描述
   */
  function addShortcut(shortcutId, config) {
    shortcuts[shortcutId] = config
    detectConflicts()
  }

  /**
   * 移除快捷键
   *
   * @param {string} shortcutId - 快捷键ID
   */
  function removeShortcut(shortcutId) {
    delete shortcuts[shortcutId]
    callbacks.delete(shortcutId)
    detectConflicts()
  }

  /**
   * 更新快捷键配置
   *
   * @param {string} shortcutId - 快捷键ID
   * @param {Object} newConfig - 新配置
   */
  function updateShortcut(shortcutId, newConfig) {
    if (shortcuts[shortcutId]) {
      shortcuts[shortcutId] = { ...shortcuts[shortcutId], ...newConfig }
      detectConflicts()
    }
  }

  /**
   * 获取快捷键配置
   *
   * @param {string} shortcutId - 快捷键ID
   * @returns {Object|null} 快捷键配置
   */
  function getShortcut(shortcutId) {
    return shortcuts[shortcutId] || null
  }

  /**
   * 获取所有快捷键
   *
   * @returns {Object} 快捷键配置映射
   */
  function getShortcuts() {
    return { ...shortcuts }
  }

  /**
   * 启用快捷键
   */
  function enable() {
    isEnabled.value = true
  }

  /**
   * 禁用快捷键
   */
  function disable() {
    isEnabled.value = false
  }

  /**
   * 开始录制快捷键
   *
   * @returns {Function} 停止录制并获取结果的函数
   */
  function startRecording() {
    isRecording.value = true
    recordedSequence.value = []

    return () => {
      isRecording.value = false
      const result = [...recordedSequence.value]
      recordedSequence.value = []
      return result
    }
  }

  /**
   * 导出快捷键配置
   *
   * @returns {string} JSON字符串
   */
  function exportConfig() {
    return JSON.stringify(shortcuts, null, 2)
  }

  /**
   * 导入快捷键配置
   *
   * @param {string} jsonString - JSON配置字符串
   * @param {boolean} [merge=true] - 是否合并现有配置
   */
  function importConfig(jsonString, merge = true) {
    try {
      const imported = JSON.parse(jsonString)
      if (merge) {
        Object.assign(shortcuts, imported)
      } else {
        Object.keys(shortcuts).forEach(key => delete shortcuts[key])
        Object.assign(shortcuts, imported)
      }
      detectConflicts()
    } catch (error) {
      console.error('[KeyboardShortcuts] 导入配置失败:', error)
    }
  }

  /**
   * 重置为默认快捷键
   */
  function resetToDefault() {
    Object.keys(shortcuts).forEach(key => delete shortcuts[key])
    Object.assign(shortcuts, DEFAULT_SHORTCUTS)
    callbacks.clear()
    detectConflicts()
  }

  // === 生命周期 ===
  onMounted(() => {
    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('keyup', handleKeyUp)
    detectConflicts()
  })

  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeyDown)
    window.removeEventListener('keyup', handleKeyUp)
  })

  return {
    // 状态
    isEnabled,
    shortcuts,
    conflicts,
    lastTriggered,
    modifierState,
    isRecording,
    recordedSequence,

    // 计算属性
    registeredShortcuts,
    groupedShortcuts,

    // 方法
    register,
    unregister,
    trigger,
    addShortcut,
    removeShortcut,
    updateShortcut,
    getShortcut,
    getShortcuts,
    enable,
    disable,
    startRecording,
    exportConfig,
    importConfig,
    resetToDefault,
    detectConflicts
  }
}

/**
 * 默认快捷键配置（导出供外部使用）
 */
export { DEFAULT_SHORTCUTS }
