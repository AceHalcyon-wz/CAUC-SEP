/**
 * @file useOperationHistory.js
 * @path src/composables/
 * @description 操作历史管理组合式函数，支持操作记录、搜索、重做、清理等功能
 * @author Agent
 * @date 2024-03-07
 * @dependencies vue
 */

import { ref, reactive, computed } from 'vue'

/**
 * 操作类型枚举
 */
export const OPERATION_TYPES = {
  CREATE: 'create',
  UPDATE: 'update',
  DELETE: 'delete',
  MOVE: 'move',
  CONFIG: 'config',
  CONNECT: 'connect',
  DISCONNECT: 'disconnect',
  START: 'start',
  STOP: 'stop',
  PAUSE: 'pause',
  RESUME: 'resume',
  IMPORT: 'import',
  EXPORT: 'export',
  CUSTOM: 'custom'
}

/**
 * 操作状态枚举
 */
export const OPERATION_STATUS = {
  PENDING: 'pending',
  SUCCESS: 'success',
  FAILED: 'failed',
  UNDONE: 'undone',
  REDONE: 'redone'
}

/**
 * 默认配置
 */
const DEFAULT_CONFIG = {
  maxHistorySize: 100,
  enableAutoSave: true,
  autoSaveInterval: 60000,
  storageKey: 'operation_history',
  excludeTypes: [],
  enableSearch: true
}

/**
 * 操作历史管理组合式函数
 *
 * @param {Object} options - 配置选项
 * @param {number} [options.maxHistorySize=100] - 最大历史记录数量
 * @param {boolean} [options.enableAutoSave=true] - 是否自动保存到本地存储
 * @param {number} [options.autoSaveInterval=60000] - 自动保存间隔（毫秒）
 * @param {string} [options.storageKey='operation_history'] - 本地存储键名
 * @param {Array} [options.excludeTypes=[]] - 排除的操作类型
 * @param {boolean} [options.enableSearch=true] - 是否启用搜索功能
 * @returns {Object} 操作历史状态与操作方法
 *
 * @example
 * ```javascript
 * const { record, undo, redo, search, clear } = useOperationHistory({
 *   maxHistorySize: 200,
 *   enableAutoSave: true
 * })
 *
 * // 记录操作
 * record({
 *   type: OPERATION_TYPES.UPDATE,
 *   category: 'motor',
 *   description: '更新电机位置',
 *   before: { position: 0 },
 *   after: { position: 100 },
 *   action: () => motorStore.setPosition(100),
 *   rollback: () => motorStore.setPosition(0)
 * })
 *
 * // 撤销操作
 * undo()
 *
 * // 重做操作
 * redo()
 *
 * // 搜索历史
 * const results = search({ keyword: '电机', type: OPERATION_TYPES.UPDATE })
 * ```
 */
export function useOperationHistory(options = {}) {
  const config = { ...DEFAULT_CONFIG, ...options }

  // === 响应式状态 ===
  /** 操作历史记录 */
  const history = ref([])
  /** 当前操作索引（用于撤销/重做） */
  const currentIndex = ref(-1)
  /** 搜索关键词 */
  const searchKeyword = ref('')
  /** 搜索过滤器 */
  const searchFilters = reactive({
    type: null,
    category: null,
    status: null,
    startDate: null,
    endDate: null
  })
  /** 搜索结果 */
  const searchResults = ref([])
  /** 是否正在执行撤销/重做 */
  const isExecuting = ref(false)
  /** 最后执行的操作 */
  const lastExecuted = ref(null)
  /** 统计信息 */
  const statistics = reactive({
    totalOperations: 0,
    undoCount: 0,
    redoCount: 0,
    failedCount: 0,
    byType: {},
    byCategory: {}
  })

  // === 内部变量 ===
  let autoSaveTimer = null
  let operationIdCounter = 0

  // === 计算属性 ===
  /** 是否可以撤销 */
  const canUndo = computed(() => {
    return currentIndex.value >= 0 && !isExecuting.value
  })

  /** 是否可以重做 */
  const canRedo = computed(() => {
    return currentIndex.value < history.value.length - 1 && !isExecuting.value
  })

  /** 当前操作 */
  const currentOperation = computed(() => {
    if (currentIndex.value >= 0 && currentIndex.value < history.value.length) {
      return history.value[currentIndex.value]
    }
    return null
  })

  /** 历史记录数量 */
  const historyCount = computed(() => history.value.length)

  /** 按类别分组的操作 */
  const groupedByCategory = computed(() => {
    const groups = {}
    history.value.forEach(op => {
      if (!groups[op.category]) {
        groups[op.category] = []
      }
      groups[op.category].push(op)
    })
    return groups
  })

  /** 按类型分组的操作 */
  const groupedByType = computed(() => {
    const groups = {}
    history.value.forEach(op => {
      if (!groups[op.type]) {
        groups[op.type] = []
      }
      groups[op.type].push(op)
    })
    return groups
  })

  /**
   * 生成唯一操作ID
   *
   * @returns {string} 操作ID
   * @internal
   */
  function generateOperationId() {
    return `op_${Date.now()}_${++operationIdCounter}`
  }

  /**
   * 更新统计信息
   *
   * @internal
   */
  function updateStatistics() {
    statistics.totalOperations = history.value.length
    statistics.byType = {}
    statistics.byCategory = {}

    history.value.forEach(op => {
      // 按类型统计
      if (!statistics.byType[op.type]) {
        statistics.byType[op.type] = 0
      }
      statistics.byType[op.type]++

      // 按类别统计
      if (!statistics.byCategory[op.category]) {
        statistics.byCategory[op.category] = 0
      }
      statistics.byCategory[op.category]++

      // 失败统计
      if (op.status === OPERATION_STATUS.FAILED) {
        statistics.failedCount++
      }
    })
  }

  /**
   * 记录操作
   *
   * @param {Object} operation - 操作对象
   * @param {string} operation.type - 操作类型
   * @param {string} operation.category - 操作类别
   * @param {string} operation.description - 操作描述
   * @param {*} operation.before - 操作前状态
   * @param {*} operation.after - 操作后状态
   * @param {Function} [operation.action] - 执行函数
   * @param {Function} [operation.rollback] - 回滚函数
   * @param {Object} [operation.metadata={}] - 额外元数据
   * @returns {string} 操作ID
   *
   * @example
   * ```javascript
   * const opId = record({
   *   type: OPERATION_TYPES.UPDATE,
   *   category: 'motor',
   *   description: '设置电机位置为100',
   *   before: { position: 0 },
   *   after: { position: 100 },
   *   action: async () => {
   *     await motorStore.setPosition(100)
   *   },
   *   rollback: async () => {
   *     await motorStore.setPosition(0)
   *   },
   *   metadata: {
   *     deviceId: 'motor-1',
   *     user: 'admin'
   *   }
   * })
   * ```
   */
  function record(operation) {
    // 检查是否排除该类型
    if (config.excludeTypes.includes(operation.type)) {
      return null
    }

    const operationRecord = {
      id: generateOperationId(),
      type: operation.type,
      category: operation.category,
      description: operation.description,
      before: operation.before ? JSON.parse(JSON.stringify(operation.before)) : null,
      after: operation.after ? JSON.parse(JSON.stringify(operation.after)) : null,
      action: operation.action,
      rollback: operation.rollback,
      metadata: operation.metadata || {},
      status: OPERATION_STATUS.PENDING,
      timestamp: Date.now(),
      undoneAt: null,
      redoneAt: null
    }

    // 如果当前不在历史末尾，删除当前位置之后的所有记录
    if (currentIndex.value < history.value.length - 1) {
      history.value = history.value.slice(0, currentIndex.value + 1)
    }

    // 添加新记录
    history.value.push(operationRecord)
    currentIndex.value = history.value.length - 1

    // 检查最大历史记录限制
    if (history.value.length > config.maxHistorySize) {
      const removeCount = history.value.length - config.maxHistorySize
      history.value = history.value.slice(removeCount)
      currentIndex.value = Math.max(0, currentIndex.value - removeCount)
    }

    // 更新统计
    updateStatistics()

    // 自动保存
    if (config.enableAutoSave) {
      scheduleAutoSave()
    }

    return operationRecord.id
  }

  /**
   * 撤销操作
   *
   * @param {number} [steps=1] - 撤销步数
   * @returns {Promise<Object|null>} 被撤销的操作
   *
   * @example
   * ```javascript
   * // 撤销最后一步操作
   * const undoneOp = await undo()
   *
   * // 撤销最近3步操作
   * await undo(3)
   * ```
   */
  async function undo(steps = 1) {
    if (!canUndo.value || isExecuting.value) {
      return null
    }

    isExecuting.value = true
    let lastUndone = null

    try {
      for (let i = 0; i < steps && currentIndex.value >= 0; i++) {
        const operation = history.value[currentIndex.value]

        // 执行回滚
        if (operation.rollback) {
          await operation.rollback()
        }

        // 更新状态
        operation.status = OPERATION_STATUS.UNDONE
        operation.undoneAt = Date.now()

        lastUndone = operation
        currentIndex.value--
        statistics.undoCount++
      }

      lastExecuted.value = {
        type: 'undo',
        operation: lastUndone,
        timestamp: Date.now()
      }

      updateStatistics()
      return lastUndone
    } catch (error) {
      console.error('[OperationHistory] 撤销失败:', error)
      if (lastUndone) {
        lastUndone.status = OPERATION_STATUS.FAILED
      }
      throw error
    } finally {
      isExecuting.value = false
      if (config.enableAutoSave) {
        scheduleAutoSave()
      }
    }
  }

  /**
   * 重做操作
   *
   * @param {number} [steps=1] - 重做步数
   * @returns {Promise<Object|null>} 被重做的操作
   *
   * @example
   * ```javascript
   * // 重做最后一步撤销的操作
   * const redoneOp = await redo()
   *
   * // 重做最近3步撤销的操作
   * await redo(3)
   * ```
   */
  async function redo(steps = 1) {
    if (!canRedo.value || isExecuting.value) {
      return null
    }

    isExecuting.value = true
    let lastRedone = null

    try {
      for (let i = 0; i < steps && currentIndex.value < history.value.length - 1; i++) {
        currentIndex.value++
        const operation = history.value[currentIndex.value]

        // 执行操作
        if (operation.action) {
          await operation.action()
        }

        // 更新状态
        operation.status = OPERATION_STATUS.REDONE
        operation.redoneAt = Date.now()

        lastRedone = operation
        statistics.redoCount++
      }

      lastExecuted.value = {
        type: 'redo',
        operation: lastRedone,
        timestamp: Date.now()
      }

      updateStatistics()
      return lastRedone
    } catch (error) {
      console.error('[OperationHistory] 重做失败:', error)
      if (lastRedone) {
        lastRedone.status = OPERATION_STATUS.FAILED
      }
      throw error
    } finally {
      isExecuting.value = false
      if (config.enableAutoSave) {
        scheduleAutoSave()
      }
    }
  }

  /**
   * 搜索历史记录
   *
   * @param {Object} criteria - 搜索条件
   * @param {string} [criteria.keyword] - 关键词
   * @param {string} [criteria.type] - 操作类型
   * @param {string} [criteria.category] - 操作类别
   * @param {string} [criteria.status] - 操作状态
   * @param {number} [criteria.startDate] - 开始时间戳
   * @param {number} [criteria.endDate] - 结束时间戳
   * @param {number} [criteria.limit] - 结果数量限制
   * @returns {Array} 搜索结果
   *
   * @example
   * ```javascript
   * // 搜索包含"电机"的操作
   * const results = search({ keyword: '电机' })
   *
   * // 搜索特定类型和类别的操作
   * const results = search({
   *   type: OPERATION_TYPES.UPDATE,
   *   category: 'motor',
   *   startDate: Date.now() - 86400000 // 最近24小时
   * })
   * ```
   */
  function search(criteria = {}) {
    const {
      keyword = searchKeyword.value,
      type = searchFilters.type,
      category = searchFilters.category,
      status = searchFilters.status,
      startDate = searchFilters.startDate,
      endDate = searchFilters.endDate,
      limit
    } = criteria

    let results = [...history.value]

    // 关键词过滤
    if (keyword) {
      const lowerKeyword = keyword.toLowerCase()
      results = results.filter(op =>
        op.description.toLowerCase().includes(lowerKeyword) ||
        op.category.toLowerCase().includes(lowerKeyword) ||
        (op.metadata && JSON.stringify(op.metadata).toLowerCase().includes(lowerKeyword))
      )
    }

    // 类型过滤
    if (type) {
      results = results.filter(op => op.type === type)
    }

    // 类别过滤
    if (category) {
      results = results.filter(op => op.category === category)
    }

    // 状态过滤
    if (status) {
      results = results.filter(op => op.status === status)
    }

    // 时间范围过滤
    if (startDate) {
      results = results.filter(op => op.timestamp >= startDate)
    }
    if (endDate) {
      results = results.filter(op => op.timestamp <= endDate)
    }

    // 按时间倒序排列
    results.sort((a, b) => b.timestamp - a.timestamp)

    // 限制结果数量
    if (limit && limit > 0) {
      results = results.slice(0, limit)
    }

    searchResults.value = results
    return results
  }

  /**
   * 获取指定ID的操作
   *
   * @param {string} operationId - 操作ID
   * @returns {Object|null} 操作对象
   */
  function getOperation(operationId) {
    return history.value.find(op => op.id === operationId) || null
  }

  /**
   * 获取指定时间范围的操作
   *
   * @param {number} startDate - 开始时间戳
   * @param {number} endDate - 结束时间戳
   * @returns {Array} 操作列表
   */
  function getOperationsByTimeRange(startDate, endDate) {
    return history.value.filter(op =>
      op.timestamp >= startDate && op.timestamp <= endDate
    )
  }

  /**
   * 清除历史记录
   *
   * @param {Object} options - 清除选项
   * @param {boolean} [options.clearAll=false] - 清除所有记录
   * @param {number} [options.beforeTime] - 清除指定时间之前的记录
   * @param {string} [options.category] - 清除指定类别的记录
   * @param {string} [options.type] - 清除指定类型的记录
   * @param {boolean} [options.keepUndoable=true] - 是否保留可撤销的记录
   *
   * @example
   * ```javascript
   * // 清除所有历史
   * clear({ clearAll: true })
   *
   * // 清除7天前的记录
   * clear({ beforeTime: Date.now() - 7 * 86400000 })
   *
   * // 清除motor类别的记录
   * clear({ category: 'motor' })
   * ```
   */
  function clear(options = {}) {
    const {
      clearAll = false,
      beforeTime,
      category,
      type,
      keepUndoable = true
    } = options

    if (clearAll) {
      history.value = []
      currentIndex.value = -1
    } else {
      let filtered = history.value

      // 时间过滤
      if (beforeTime) {
        filtered = filtered.filter(op => op.timestamp >= beforeTime)
      }

      // 类别过滤
      if (category) {
        filtered = filtered.filter(op => op.category !== category)
      }

      // 类型过滤
      if (type) {
        filtered = filtered.filter(op => op.type !== type)
      }

      // 保留可撤销的记录
      if (keepUndoable && currentIndex.value >= 0) {
        const undoableOps = history.value.slice(0, currentIndex.value + 1)
        history.value = history.value.filter(op =>
          filtered.includes(op) || undoableOps.includes(op)
        )
        filtered = [...undoableOps, ...filtered.filter(op => !undoableOps.includes(op))]
      } else {
        history.value = filtered
      }

      // 调整当前索引
      if (currentIndex.value >= history.value.length) {
        currentIndex.value = history.value.length - 1
      }
    }

    updateStatistics()

    if (config.enableAutoSave) {
      scheduleAutoSave()
    }
  }

  /**
   * 导出历史记录
   *
   * @param {Object} options - 导出选项
   * @param {string} [options.format='json'] - 导出格式 ('json' | 'csv')
   * @param {boolean} [options.includeActions=false] - 是否包含执行函数
   * @returns {string} 导出的数据
   */
  function exportHistory(options = {}) {
    const { format = 'json', includeActions = false } = options

    const exportData = history.value.map(op => {
      const record = {
        id: op.id,
        type: op.type,
        category: op.category,
        description: op.description,
        before: op.before,
        after: op.after,
        status: op.status,
        timestamp: op.timestamp,
        metadata: op.metadata
      }

      if (includeActions) {
        record.hasAction = !!op.action
        record.hasRollback = !!op.rollback
      }

      return record
    })

    if (format === 'csv') {
      const headers = ['ID', '类型', '类别', '描述', '状态', '时间', '元数据']
      const rows = exportData.map(op => [
        op.id,
        op.type,
        op.category,
        `"${op.description.replace(/"/g, '""')}"`,
        op.status,
        new Date(op.timestamp).toISOString(),
        `"${JSON.stringify(op.metadata).replace(/"/g, '""')}"`
      ])
      return [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
    }

    return JSON.stringify(exportData, null, 2)
  }

  /**
   * 导入历史记录
   *
   * @param {string} data - 导入的数据
   * @param {string} [format='json'] - 数据格式
   * @param {boolean} [merge=true] - 是否合并现有记录
   * @returns {number} 导入的记录数量
   */
  function importHistory(data, format = 'json', merge = true) {
    try {
      let imported = []

      if (format === 'json') {
        imported = JSON.parse(data)
      } else if (format === 'csv') {
        const lines = data.split('\n')
        for (let i = 1; i < lines.length; i++) {
          const values = lines[i].split(',')
          imported.push({
            id: values[0],
            type: values[1],
            category: values[2],
            description: values[3].replace(/^"|"$/g, '').replace(/""/g, '"'),
            status: values[4],
            timestamp: new Date(values[5]).getTime(),
            metadata: JSON.parse(values[6].replace(/^"|"$/g, '').replace(/""/g, '"'))
          })
        }
      }

      if (!merge) {
        history.value = []
        currentIndex.value = -1
      }

      imported.forEach(op => {
        // 不包含执行函数的导入
        op.action = null
        op.rollback = null
        history.value.push(op)
      })

      // 按时间排序
      history.value.sort((a, b) => a.timestamp - b.timestamp)
      currentIndex.value = history.value.length - 1

      // 检查最大限制
      if (history.value.length > config.maxHistorySize) {
        const removeCount = history.value.length - config.maxHistorySize
        history.value = history.value.slice(removeCount)
        currentIndex.value = history.value.length - 1
      }

      updateStatistics()

      if (config.enableAutoSave) {
        scheduleAutoSave()
      }

      return imported.length
    } catch (error) {
      console.error('[OperationHistory] 导入失败:', error)
      return 0
    }
  }

  /**
   * 安排自动保存
   *
   * @internal
   */
  function scheduleAutoSave() {
    if (autoSaveTimer) {
      clearTimeout(autoSaveTimer)
    }
    autoSaveTimer = setTimeout(() => {
      saveToStorage()
    }, 1000) // 防抖1秒
  }

  /**
   * 保存到本地存储
   *
   * @internal
   */
  function saveToStorage() {
    try {
      const data = {
        history: history.value.map(op => ({
          ...op,
          action: null, // 不保存函数
          rollback: null
        })),
        currentIndex: currentIndex.value,
        savedAt: Date.now()
      }
      localStorage.setItem(config.storageKey, JSON.stringify(data))
    } catch (error) {
      console.error('[OperationHistory] 保存失败:', error)
    }
  }

  /**
   * 从本地存储加载
   *
   * @returns {boolean} 是否加载成功
   */
  function loadFromStorage() {
    try {
      const data = localStorage.getItem(config.storageKey)
      if (data) {
        const parsed = JSON.parse(data)
        history.value = parsed.history || []
        currentIndex.value = parsed.currentIndex ?? -1
        updateStatistics()
        return true
      }
    } catch (error) {
      console.error('[OperationHistory] 加载失败:', error)
    }
    return false
  }

  /**
   * 重置历史记录
   */
  function reset() {
    history.value = []
    currentIndex.value = -1
    searchKeyword.value = ''
    searchResults.value = []
    lastExecuted.value = null
    statistics.totalOperations = 0
    statistics.undoCount = 0
    statistics.redoCount = 0
    statistics.failedCount = 0
    statistics.byType = {}
    statistics.byCategory = {}

    if (config.enableAutoSave) {
      localStorage.removeItem(config.storageKey)
    }
  }

  // 初始化时加载历史记录
  if (config.enableAutoSave) {
    loadFromStorage()
  }

  return {
    // 状态
    history,
    currentIndex,
    searchKeyword,
    searchFilters,
    searchResults,
    isExecuting,
    lastExecuted,
    statistics,

    // 计算属性
    canUndo,
    canRedo,
    currentOperation,
    historyCount,
    groupedByCategory,
    groupedByType,

    // 方法
    record,
    undo,
    redo,
    search,
    getOperation,
    getOperationsByTimeRange,
    clear,
    exportHistory,
    importHistory,
    loadFromStorage,
    saveToStorage,
    reset
  }
}
