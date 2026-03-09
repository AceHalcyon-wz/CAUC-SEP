/**
 * @file audit.js
 * @path src/stores/
 * @description 审计日志状态管理Store，处理日志查询、统计、导出、清理策略等功能
 * @author Agent
 * @date 2024-03-07
 * @dependencies pinia, vue, utils
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { get, post, del } from '../utils/apiRequest'

export const useAuditStore = defineStore('audit', () => {
  // ==================== 日志列表状态 ====================

  /** 日志列表数据 */
  const logList = ref([])

  /** 分页信息 */
  const pagination = ref({
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0
  })

  /** 加载状态 */
  const loading = ref(false)

  /** 错误消息 */
  const errorMessage = ref('')

  // ==================== 统计数据 ====================

  /** 统计信息 */
  const statistics = ref({
    total_logs: 0,
    today_logs: 0,
    operation_type_stats: {},
    category_stats: {},
    user_stats: {},
    time_distribution: [],
    device_stats: {},
    hourly_distribution: [],
    daily_trend: []
  })

  // ==================== 筛选条件 ====================

  /** 当前筛选条件 */
  const filters = ref({
    operation_type: null,
    category: null,
    user_id: null,
    device_id: null,
    start_time: null,
    end_time: null,
    keyword: null,
    status: null,
    response_status_min: null,
    response_status_max: null,
    duration_min: null,
    duration_max: null
  })

  // ==================== 操作类型与分类 ====================

  /** 操作类型列表 */
  const operationTypes = ref([])

  /** 操作分类列表 */
  const categories = ref([])

  /** 用户列表（用于筛选） */
  const userList = ref([])

  /** 设备列表（用于筛选） */
  const deviceList = ref([])

  // ==================== 日志详情 ====================

  /** 当前查看的日志详情 */
  const currentLogDetail = ref(null)

  // ==================== 清理策略配置 ====================

  /** 清理策略配置 */
  const cleanupConfig = ref({
    enabled: false,
    retention_days: 90,
    cleanup_interval: 'weekly',
    last_cleanup_time: null,
    auto_cleanup: true,
    keep_important: true
  })

  /** 导出配置 */
  const exportConfig = ref({
    format: 'csv',
    include_details: true,
    include_params: false,
    date_format: 'YYYY-MM-DD HH:mm:ss',
    timezone: 'local'
  })

  // ==================== 计算属性 ====================

  /**
   * 是否有筛选条件
   */
  const hasFilters = computed(() => {
    return !!(
      filters.value.operation_type ||
      filters.value.category ||
      filters.value.user_id ||
      filters.value.device_id ||
      filters.value.start_time ||
      filters.value.end_time ||
      filters.value.keyword ||
      filters.value.status ||
      filters.value.response_status_min ||
      filters.value.response_status_max ||
      filters.value.duration_min ||
      filters.value.duration_max
    )
  })

  /**
   * 是否有日志数据
   */
  const hasLogs = computed(() => {
    return logList.value.length > 0
  })

  // ==================== API 操作方法 ====================

  /**
   * 查询审计日志
   * 
   * @param {Object} params - 查询参数
   * @param {number} [params.page=1] - 页码
   * @param {number} [params.page_size=20] - 每页数量
   * @param {string} [params.operation_type] - 操作类型
   * @param {string} [params.category] - 操作分类
   * @param {string} [params.user_id] - 用户ID
   * @param {string} [params.device_id] - 设备ID
   * @param {string} [params.start_time] - 开始时间
   * @param {string} [params.end_time] - 结束时间
   * @param {string} [params.keyword] - 关键词
   * @param {string} [params.status] - 状态
   * @param {number} [params.response_status_min] - 最小响应状态码
   * @param {number} [params.response_status_max] - 最大响应状态码
   * @param {number} [params.duration_min] - 最小耗时(ms)
   * @param {number} [params.duration_max] - 最大耗时(ms)
   * @returns {Promise<Object|null>} 查询结果
   */
  async function fetchLogs(params = {}) {
    loading.value = true
    errorMessage.value = ''

    // 合并默认分页参数
    const queryParams = {
      page: params.page || pagination.value.page,
      page_size: params.page_size || pagination.value.pageSize,
      ...filters.value,
      ...params
    }

    // 移除空值参数
    Object.keys(queryParams).forEach(key => {
      if (queryParams[key] === null || queryParams[key] === undefined || queryParams[key] === '') {
        delete queryParams[key]
      }
    })

    const result = await get('/logs/query', queryParams, {
      onError: (msg) => {
        errorMessage.value = msg
        console.error('Failed to fetch logs:', msg)
      }
    })

    loading.value = false

    if (result.success && result.data) {
      logList.value = result.data.items || []
      pagination.value = {
        page: result.data.page || 1,
        pageSize: result.data.page_size || 20,
        total: result.data.total || 0,
        totalPages: result.data.total_pages || 0
      }
      return result.data
    }

    return null
  }

  /**
   * 获取统计信息
   * 
   * @param {Object} params - 查询参数
   * @param {string} [params.start_time] - 开始时间
   * @param {string} [params.end_time] - 结束时间
   * @param {string} [params.group_by] - 分组方式 ('hour' | 'day' | 'week' | 'month')
   * @returns {Promise<Object|null>} 统计数据
   */
  async function fetchStatistics(params = {}) {
    const result = await get('/logs/statistics', params, {
      onError: (msg) => {
        console.error('Failed to fetch statistics:', msg)
      }
    })

    if (result.success && result.data) {
      statistics.value = {
        total_logs: result.data.total_logs || 0,
        today_logs: result.data.today_logs || 0,
        operation_type_stats: result.data.operation_type_stats || {},
        category_stats: result.data.category_stats || {},
        user_stats: result.data.user_stats || {},
        time_distribution: result.data.time_distribution || [],
        device_stats: result.data.device_stats || {},
        hourly_distribution: result.data.hourly_distribution || [],
        daily_trend: result.data.daily_trend || []
      }
      return result.data
    }

    return null
  }

  /**
   * 获取用户列表（用于筛选）
   * 
   * @param {Object} params - 查询参数
   * @returns {Promise<Array>} 用户列表
   */
  async function fetchUserList(params = {}) {
    const result = await get('/logs/users', params, {
      onError: (msg) => {
        console.error('Failed to fetch user list:', msg)
      }
    })

    if (result.success && result.data) {
      userList.value = result.data.users || result.data || []
      return userList.value
    }

    return []
  }

  /**
   * 获取设备列表（用于筛选）
   * 
   * @param {Object} params - 查询参数
   * @returns {Promise<Array>} 设备列表
   */
  async function fetchDeviceList(params = {}) {
    const result = await get('/logs/devices', params, {
      onError: (msg) => {
        console.error('Failed to fetch device list:', msg)
      }
    })

    if (result.success && result.data) {
      deviceList.value = result.data.devices || result.data || []
      return deviceList.value
    }

    return []
  }

  /**
   * 获取操作类型列表
   * 
   * @returns {Promise<Array>} 操作类型列表
   */
  async function fetchOperationTypes() {
    const result = await get('/logs/operation-types', null, {
      onError: (msg) => {
        console.error('Failed to fetch operation types:', msg)
      }
    })

    if (result.success && result.data) {
      operationTypes.value = result.data.types || result.data || []
      return operationTypes.value
    }

    return []
  }

  /**
   * 获取操作分类列表
   * 
   * @returns {Promise<Array>} 操作分类列表
   */
  async function fetchCategories() {
    const result = await get('/logs/categories', null, {
      onError: (msg) => {
        console.error('Failed to fetch categories:', msg)
      }
    })

    if (result.success && result.data) {
      categories.value = result.data.categories || result.data || []
      return categories.value
    }

    return []
  }

  /**
   * 获取日志详情
   * 
   * @param {string} logId - 日志ID
   * @returns {Promise<Object|null>} 日志详情
   */
  async function fetchLogDetail(logId) {
    if (!logId) {
      errorMessage.value = '日志ID不能为空'
      return null
    }

    loading.value = true
    errorMessage.value = ''

    const result = await get(`/logs/${logId}`, null, {
      onError: (msg) => {
        errorMessage.value = msg
        console.error('Failed to fetch log detail:', msg)
      }
    })

    loading.value = false

    if (result.success && result.data) {
      currentLogDetail.value = result.data
      return result.data
    }

    return null
  }

  /**
   * 删除单条日志
   * 
   * @param {string} logId - 日志ID
   * @returns {Promise<boolean>} 删除是否成功
   */
  async function deleteLog(logId) {
    if (!logId) {
      errorMessage.value = '日志ID不能为空'
      return false
    }

    loading.value = true
    errorMessage.value = ''

    const result = await del(`/logs/${logId}`, {
      onError: (msg) => {
        errorMessage.value = msg
        console.error('Failed to delete log:', msg)
      }
    })

    loading.value = false

    if (result.success) {
      // 从列表中移除已删除的日志
      const index = logList.value.findIndex(log => log.id === logId)
      if (index !== -1) {
        logList.value.splice(index, 1)
        pagination.value.total = Math.max(0, pagination.value.total - 1)
      }
      return true
    }

    return false
  }

  /**
   * 批量删除日志
   * 
   * @param {Array<string>} logIds - 日志ID数组
   * @returns {Promise<Object|null>} 删除结果
   */
  async function bulkDeleteLogs(logIds) {
    if (!logIds || logIds.length === 0) {
      errorMessage.value = '请选择要删除的日志'
      return null
    }

    loading.value = true
    errorMessage.value = ''

    const result = await post('/logs/bulk/delete', {
      log_ids: logIds
    }, {
      onError: (msg) => {
        errorMessage.value = msg
        console.error('Failed to bulk delete logs:', msg)
      }
    })

    loading.value = false

    if (result.success) {
      // 刷新日志列表
      await fetchLogs()
      return result.data
    }

    return null
  }

  /**
   * 导出日志
   * 
   * @param {Object} params - 导出参数
   * @param {string} [params.format='csv'] - 导出格式 ('csv' | 'excel' | 'json' | 'pdf')
   * @param {Array<string>} [params.log_ids] - 指定导出的日志ID列表
   * @param {Object} [params.filters] - 筛选条件
   * @param {boolean} [params.include_details] - 是否包含详情
   * @param {boolean} [params.include_params] - 是否包含请求参数
   * @returns {Promise<Blob|null>} 文件Blob对象
   */
  async function exportLogs(params = {}) {
    const exportParams = {
      format: params.format || exportConfig.value.format,
      include_details: params.include_details ?? exportConfig.value.include_details,
      include_params: params.include_params ?? exportConfig.value.include_params,
      date_format: params.date_format || exportConfig.value.date_format,
      timezone: params.timezone || exportConfig.value.timezone,
      ...params
    }

    // 如果有筛选条件，添加到导出参数
    if (hasFilters.value && !params.log_ids) {
      exportParams.filters = { ...filters.value }
    }

    loading.value = true
    errorMessage.value = ''

    const result = await post('/logs/export', exportParams, {
      onError: (msg) => {
        errorMessage.value = msg
        console.error('Failed to export logs:', msg)
      }
    })

    loading.value = false

    if (result.success && result.data) {
      return result.data
    }

    return null
  }

  /**
   * 导出为Excel格式
   * 
   * @param {Object} params - 导出参数
   * @returns {Promise<Blob|null>} Excel文件Blob
   */
  async function exportToExcel(params = {}) {
    return exportLogs({ ...params, format: 'excel' })
  }

  /**
   * 导出为PDF格式
   * 
   * @param {Object} params - 导出参数
   * @returns {Promise<Blob|null>} PDF文件Blob
   */
  async function exportToPDF(params = {}) {
    return exportLogs({ ...params, format: 'pdf' })
  }

  /**
   * 导出为CSV格式
   * 
   * @param {Object} params - 导出参数
   * @returns {Promise<Blob|null>} CSV文件Blob
   */
  async function exportToCSV(params = {}) {
    return exportLogs({ ...params, format: 'csv' })
  }

  /**
   * 生成报表
   * 
   * @param {Object} params - 报表参数
   * @param {string} [params.report_type='summary'] - 报表类型 ('summary' | 'detail' | 'trend')
   * @param {string} [params.start_time] - 开始时间
   * @param {string} [params.end_time] - 结束时间
   * @param {string} [params.format='pdf'] - 输出格式
   * @returns {Promise<Blob|null>} 报表文件Blob
   */
  async function generateReport(params = {}) {
    loading.value = true
    errorMessage.value = ''

    const result = await post('/logs/report', {
      report_type: params.report_type || 'summary',
      start_time: params.start_time || filters.value.start_time,
      end_time: params.end_time || filters.value.end_time,
      format: params.format || 'pdf',
      ...params
    }, {
      onError: (msg) => {
        errorMessage.value = msg
        console.error('Failed to generate report:', msg)
      }
    })

    loading.value = false

    if (result.success && result.data) {
      return result.data
    }

    return null
  }

  // ==================== 清理策略管理 ====================

  /**
   * 获取清理策略配置
   * 
   * @returns {Promise<Object|null>} 清理策略配置
   */
  async function fetchCleanupConfig() {
    const result = await get('/logs/cleanup/config', null, {
      onError: (msg) => {
        console.error('Failed to fetch cleanup config:', msg)
      }
    })

    if (result.success && result.data) {
      cleanupConfig.value = {
        ...cleanupConfig.value,
        ...result.data
      }
      return cleanupConfig.value
    }

    return null
  }

  /**
   * 更新清理策略配置
   * 
   * @param {Object} config - 新的清理策略配置
   * @returns {Promise<boolean>} 更新是否成功
   */
  async function updateCleanupConfig(config) {
    loading.value = true
    errorMessage.value = ''

    const result = await post('/logs/cleanup/config', config, {
      onError: (msg) => {
        errorMessage.value = msg
        console.error('Failed to update cleanup config:', msg)
      }
    })

    loading.value = false

    if (result.success) {
      cleanupConfig.value = {
        ...cleanupConfig.value,
        ...config
      }
      return true
    }

    return false
  }

  /**
   * 执行手动清理
   * 
   * @param {Object} params - 清理参数
   * @param {number} [params.older_than_days] - 清理多少天前的日志
   * @param {boolean} [params.keep_important] - 是否保留重要日志
   * @returns {Promise<Object|null>} 清理结果
   */
  async function executeCleanup(params = {}) {
    loading.value = true
    errorMessage.value = ''

    const result = await post('/logs/cleanup/execute', {
      older_than_days: params.older_than_days || cleanupConfig.value.retention_days,
      keep_important: params.keep_important ?? cleanupConfig.value.keep_important,
      ...params
    }, {
      onError: (msg) => {
        errorMessage.value = msg
        console.error('Failed to execute cleanup:', msg)
      }
    })

    loading.value = false

    if (result.success) {
      // 刷新统计信息
      await fetchStatistics()
      return result.data
    }

    return null
  }

  /**
   * 获取清理预览
   * 
   * @param {Object} params - 预览参数
   * @returns {Promise<Object|null>} 预览结果
   */
  async function getCleanupPreview(params = {}) {
    const result = await post('/logs/cleanup/preview', {
      older_than_days: params.older_than_days || cleanupConfig.value.retention_days,
      keep_important: params.keep_important ?? cleanupConfig.value.keep_important,
      ...params
    }, {
      onError: (msg) => {
        console.error('Failed to get cleanup preview:', msg)
      }
    })

    if (result.success && result.data) {
      return result.data
    }

    return null
  }

  // ==================== 筛选条件管理 ====================

  /**
   * 设置筛选条件
   * 
   * @param {Object} newFilters - 新的筛选条件
   */
  function setFilters(newFilters) {
    filters.value = {
      ...filters.value,
      ...newFilters
    }
  }

  /**
   * 清除所有筛选条件
   */
  function clearFilters() {
    filters.value = {
      operation_type: null,
      category: null,
      user_id: null,
      device_id: null,
      start_time: null,
      end_time: null,
      keyword: null,
      status: null,
      response_status_min: null,
      response_status_max: null,
      duration_min: null,
      duration_max: null
    }
  }

  /**
   * 重置筛选条件并刷新
   */
  async function resetFilters() {
    clearFilters()
    pagination.value.page = 1
    await fetchLogs()
  }

  // ==================== 分页管理 ====================

  /**
   * 跳转到指定页
   * 
   * @param {number} page - 页码
   */
  async function goToPage(page) {
    if (page < 1 || page > pagination.value.totalPages) {
      return
    }
    pagination.value.page = page
    await fetchLogs({ page })
  }

  /**
   * 设置每页数量
   * 
   * @param {number} pageSize - 每页数量
   */
  async function setPageSize(pageSize) {
    pagination.value.pageSize = pageSize
    pagination.value.page = 1
    await fetchLogs({ page: 1, page_size: pageSize })
  }

  // ==================== 工具方法 ====================

  /**
   * 清除错误消息
   */
  function clearError() {
    errorMessage.value = ''
  }

  /**
   * 清除日志详情
   */
  function clearLogDetail() {
    currentLogDetail.value = null
  }

  /**
   * 重置Store状态
   */
  function resetState() {
    logList.value = []
    pagination.value = {
      page: 1,
      pageSize: 20,
      total: 0,
      totalPages: 0
    }
    statistics.value = {
      total_logs: 0,
      today_logs: 0,
      operation_type_stats: {},
      category_stats: {},
      user_stats: {},
      time_distribution: [],
      device_stats: {},
      hourly_distribution: [],
      daily_trend: []
    }
    clearFilters()
    currentLogDetail.value = null
    errorMessage.value = ''
    loading.value = false
  }

  // ==================== 生命周期方法 ====================

  /**
   * 初始化Store
   */
  async function init() {
    await Promise.all([
      fetchOperationTypes(),
      fetchCategories(),
      fetchUserList(),
      fetchDeviceList(),
      fetchStatistics(),
      fetchCleanupConfig()
    ])
    await fetchLogs()
  }

  /**
   * 清理资源
   */
  function cleanup() {
    resetState()
  }

  // ==================== 导出 ====================

  return {
    // 日志列表状态
    logList,
    pagination,
    loading,
    errorMessage,

    // 统计数据
    statistics,

    // 筛选条件
    filters,

    // 操作类型与分类
    operationTypes,
    categories,
    userList,
    deviceList,

    // 日志详情
    currentLogDetail,

    // 清理策略配置
    cleanupConfig,
    exportConfig,

    // 计算属性
    hasFilters,
    hasLogs,

    // API操作方法
    fetchLogs,
    fetchStatistics,
    fetchOperationTypes,
    fetchCategories,
    fetchUserList,
    fetchDeviceList,
    fetchLogDetail,
    deleteLog,
    bulkDeleteLogs,
    exportLogs,
    exportToExcel,
    exportToPDF,
    exportToCSV,
    generateReport,

    // 清理策略管理
    fetchCleanupConfig,
    updateCleanupConfig,
    executeCleanup,
    getCleanupPreview,

    // 筛选条件管理
    setFilters,
    clearFilters,
    resetFilters,

    // 分页管理
    goToPage,
    setPageSize,

    // 工具方法
    clearError,
    clearLogDetail,
    resetState,

    // 生命周期
    init,
    cleanup
  }
})
