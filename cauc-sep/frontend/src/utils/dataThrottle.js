/**
 * @file dataThrottle.js
 * @path src/utils/
 * @description 数据节流和批量更新工具，优化高频数据推送性能
 * @author Agent
 * @date 2024-03-08
 */

/**
 * 节流器类
 * 
 * @description 限制数据更新频率，支持多种节流策略
 */
export class DataThrottler {
  /**
   * 创建节流器实例
   * 
   * @param {Object} options - 配置选项
   * @param {number} [options.interval=100] - 节流间隔（毫秒）
   * @param {string} [options.mode='throttle'] - 节流模式（throttle/debounce）
   * @param {boolean} [options.leading=true] - 是否在开始时立即执行
   * @param {boolean} [options.trailing=true] - 是否在结束时执行最后一次
   * @param {number} [options.maxBatchSize=100] - 最大批量大小
   */
  constructor(options = {}) {
    this.options = {
      interval: 100,
      mode: 'throttle',
      leading: true,
      trailing: true,
      maxBatchSize: 100,
      ...options
    }

    this.timer = null
    this.lastExecTime = 0
    this.pendingData = []
    this.isProcessing = false
    this.callback = null
  }

  /**
   * 设置回调函数
   * 
   * @param {Function} callback - 数据处理回调
   */
  setCallback(callback) {
    this.callback = callback
  }

  /**
   * 添加数据到队列
   * 
   * @param {any} data - 数据项
   */
  push(data) {
    this.pendingData.push({
      data,
      timestamp: Date.now()
    })

    // 限制队列大小
    if (this.pendingData.length > this.options.maxBatchSize) {
      this.pendingData = this.pendingData.slice(-this.options.maxBatchSize)
    }

    this._scheduleProcess()
  }

  /**
   * 批量添加数据
   * 
   * @param {Array} dataArray - 数据数组
   */
  pushBatch(dataArray) {
    const timestamp = Date.now()
    dataArray.forEach(data => {
      this.pendingData.push({ data, timestamp })
    })

    // 限制队列大小
    if (this.pendingData.length > this.options.maxBatchSize) {
      this.pendingData = this.pendingData.slice(-this.options.maxBatchSize)
    }

    this._scheduleProcess()
  }

  /**
   * 安排数据处理
   * 
   * @internal 内部方法
   */
  _scheduleProcess() {
    const now = Date.now()
    const timeSinceLastExec = now - this.lastExecTime

    if (this.options.mode === 'throttle') {
      // 节流模式：固定间隔执行
      if (timeSinceLastExec >= this.options.interval) {
        this._process()
      } else if (!this.timer) {
        this.timer = setTimeout(() => {
          this._process()
          this.timer = null
        }, this.options.interval - timeSinceLastExec)
      }
    } else {
      // 防抖模式：延迟执行
      if (this.timer) {
        clearTimeout(this.timer)
      }
      this.timer = setTimeout(() => {
        this._process()
        this.timer = null
      }, this.options.interval)
    }
  }

  /**
   * 处理队列中的数据
   * 
   * @internal 内部方法
   */
  _process() {
    if (this.isProcessing || this.pendingData.length === 0) {
      return
    }

    this.isProcessing = true
    this.lastExecTime = Date.now()

    // 取出待处理数据
    const batch = this.pendingData.splice(0, this.pendingData.length)

    // 执行回调
    if (this.callback) {
      try {
        this.callback(batch.map(item => item.data), batch)
      } catch (error) {
        console.error('[DataThrottler] Callback error:', error)
      }
    }

    this.isProcessing = false
  }

  /**
   * 立即处理所有待处理数据
   */
  flush() {
    if (this.timer) {
      clearTimeout(this.timer)
      this.timer = null
    }
    this._process()
  }

  /**
   * 清空队列
   */
  clear() {
    if (this.timer) {
      clearTimeout(this.timer)
      this.timer = null
    }
    this.pendingData = []
  }

  /**
   * 获取队列长度
   * 
   * @returns {number} 队列长度
   */
  get queueLength() {
    return this.pendingData.length
  }

  /**
   * 销毁节流器
   */
  destroy() {
    this.clear()
    this.callback = null
  }
}

/**
 * 批量更新器类
 * 
 * @description 合并多次更新，减少渲染次数
 */
export class BatchUpdater {
  /**
   * 创建批量更新器实例
   * 
   * @param {Object} options - 配置选项
   * @param {number} [options.batchInterval=50] - 批量更新间隔（毫秒）
   * @param {number} [options.maxBatchSize=50] - 最大批量大小
   * @param {Function} [options.onBatchUpdate] - 批量更新回调
   */
  constructor(options = {}) {
    this.options = {
      batchInterval: 50,
      maxBatchSize: 50,
      onBatchUpdate: null,
      ...options
    }

    this.pendingUpdates = new Map()
    this.timer = null
    this.isScheduled = false
  }

  /**
   * 添加更新
   * 
   * @param {string} key - 更新键
   * @param {any} value - 更新值
   * @param {Object} [meta] - 元数据
   */
  update(key, value, meta = {}) {
    this.pendingUpdates.set(key, {
      value,
      timestamp: Date.now(),
      ...meta
    })

    this._scheduleBatch()
  }

  /**
   * 批量添加更新
   * 
   * @param {Object} updates - 更新对象
   */
  updateBatch(updates) {
    const timestamp = Date.now()
    Object.entries(updates).forEach(([key, value]) => {
      this.pendingUpdates.set(key, {
        value,
        timestamp
      })
    })

    this._scheduleBatch()
  }

  /**
   * 安排批量更新
   * 
   * @internal 内部方法
   */
  _scheduleBatch() {
    if (this.isScheduled) {
      return
    }

    // 如果达到最大批量大小，立即执行
    if (this.pendingUpdates.size >= this.options.maxBatchSize) {
      this._executeBatch()
      return
    }

    this.isScheduled = true
    this.timer = setTimeout(() => {
      this._executeBatch()
      this.timer = null
      this.isScheduled = false
    }, this.options.batchInterval)
  }

  /**
   * 执行批量更新
   * 
   * @internal 内部方法
   */
  _executeBatch() {
    if (this.pendingUpdates.size === 0) {
      return
    }

    // 取出所有待更新项
    const updates = new Map(this.pendingUpdates)
    this.pendingUpdates.clear()

    // 执行回调
    if (this.options.onBatchUpdate) {
      try {
        this.options.onBatchUpdate(updates)
      } catch (error) {
        console.error('[BatchUpdater] Batch update error:', error)
      }
    }
  }

  /**
   * 立即执行所有待更新项
   */
  flush() {
    if (this.timer) {
      clearTimeout(this.timer)
      this.timer = null
      this.isScheduled = false
    }
    this._executeBatch()
  }

  /**
   * 清空待更新项
   */
  clear() {
    if (this.timer) {
      clearTimeout(this.timer)
      this.timer = null
      this.isScheduled = false
    }
    this.pendingUpdates.clear()
  }

  /**
   * 获取待更新项数量
   * 
   * @returns {number} 待更新项数量
   */
  get pendingCount() {
    return this.pendingUpdates.size
  }

  /**
   * 销毁批量更新器
   */
  destroy() {
    this.clear()
    this.options.onBatchUpdate = null
  }
}

/**
 * 数据聚合器类
 * 
 * @description 聚合高频数据，减少数据量
 */
export class DataAggregator {
  /**
   * 创建数据聚合器实例
   * 
   * @param {Object} options - 配置选项
   * @param {number} [options.windowSize=1000] - 聚合窗口大小（毫秒）
   * @param {string} [options.strategy='average'] - 聚合策略（average/sum/max/min/last）
   * @param {Function} [options.onAggregate] - 聚合回调
   */
  constructor(options = {}) {
    this.options = {
      windowSize: 1000,
      strategy: 'average',
      onAggregate: null,
      ...options
    }

    this.windows = new Map()
    this.timer = null
  }

  /**
   * 添加数据点
   * 
   * @param {string} key - 数据键
   * @param {number} value - 数据值
   */
  add(key, value) {
    if (!this.windows.has(key)) {
      this.windows.set(key, {
        values: [],
        startTime: Date.now()
      })
    }

    const window = this.windows.get(key)
    window.values.push({
      value,
      timestamp: Date.now()
    })

    // 检查窗口是否已满
    const elapsed = Date.now() - window.startTime
    if (elapsed >= this.options.windowSize) {
      this._aggregateWindow(key)
    }

    this._startTimer()
  }

  /**
   * 启动定时器
   * 
   * @internal 内部方法
   */
  _startTimer() {
    if (this.timer) return

    this.timer = setInterval(() => {
      this._aggregateAll()
    }, this.options.windowSize)
  }

  /**
   * 聚合指定窗口
   * 
   * @param {string} key - 数据键
   * @internal 内部方法
   */
  _aggregateWindow(key) {
    const window = this.windows.get(key)
    if (!window || window.values.length === 0) {
      return
    }

    const aggregated = this._aggregateValues(window.values)
    const result = {
      key,
      value: aggregated,
      count: window.values.length,
      startTime: window.startTime,
      endTime: Date.now()
    }

    // 执行回调
    if (this.options.onAggregate) {
      try {
        this.options.onAggregate(result)
      } catch (error) {
        console.error('[DataAggregator] Aggregate callback error:', error)
      }
    }

    // 重置窗口
    window.values = []
    window.startTime = Date.now()
  }

  /**
   * 聚合所有窗口
   * 
   * @internal 内部方法
   */
  _aggregateAll() {
    this.windows.forEach((_, key) => {
      this._aggregateWindow(key)
    })
  }

  /**
   * 聚合值
   * 
   * @param {Array} values - 值数组
   * @returns {number} 聚合结果
   * @internal 内部方法
   */
  _aggregateValues(values) {
    const nums = values.map(v => v.value)

    switch (this.options.strategy) {
      case 'average':
        return nums.reduce((a, b) => a + b, 0) / nums.length

      case 'sum':
        return nums.reduce((a, b) => a + b, 0)

      case 'max':
        return Math.max(...nums)

      case 'min':
        return Math.min(...nums)

      case 'last':
        return nums[nums.length - 1]

      default:
        return nums.reduce((a, b) => a + b, 0) / nums.length
    }
  }

  /**
   * 立即聚合所有窗口
   */
  flush() {
    this._aggregateAll()
  }

  /**
   * 清空所有窗口
   */
  clear() {
    if (this.timer) {
      clearInterval(this.timer)
      this.timer = null
    }
    this.windows.clear()
  }

  /**
   * 销毁聚合器
   */
  destroy() {
    this.clear()
    this.options.onAggregate = null
  }
}

/**
 * 创建数据节流器
 * 
 * @param {Object} options - 配置选项
 * @returns {DataThrottler} 节流器实例
 */
export function createThrottler(options = {}) {
  return new DataThrottler(options)
}

/**
 * 创建批量更新器
 * 
 * @param {Object} options - 配置选项
 * @returns {BatchUpdater} 批量更新器实例
 */
export function createBatchUpdater(options = {}) {
  return new BatchUpdater(options)
}

/**
 * 创建数据聚合器
 * 
 * @param {Object} options - 配置选项
 * @returns {DataAggregator} 数据聚合器实例
 */
export function createAggregator(options = {}) {
  return new DataAggregator(options)
}

/**
 * 数据流处理器
 * 
 * @description 组合节流、批量更新和聚合功能
 */
export class DataStreamProcessor {
  /**
   * 创建数据流处理器实例
   * 
   * @param {Object} options - 配置选项
   */
  constructor(options = {}) {
    this.options = {
      throttleInterval: 100,
      batchInterval: 50,
      maxBatchSize: 50,
      aggregateWindow: 1000,
      aggregateStrategy: 'average',
      enableAggregation: true,
      ...options
    }

    // 创建节流器
    this.throttler = new DataThrottler({
      interval: this.options.throttleInterval,
      mode: 'throttle'
    })

    // 创建批量更新器
    this.batchUpdater = new BatchUpdater({
      batchInterval: this.options.batchInterval,
      maxBatchSize: this.options.maxBatchSize
    })

    // 创建聚合器（可选）
    if (this.options.enableAggregation) {
      this.aggregator = new DataAggregator({
        windowSize: this.options.aggregateWindow,
        strategy: this.options.aggregateStrategy
      })
    } else {
      this.aggregator = null
    }

    this._setupPipeline()
  }

  /**
   * 设置数据处理管道
   * 
   * @internal 内部方法
   */
  _setupPipeline() {
    // 节流器 -> 批量更新器
    this.throttler.setCallback((data) => {
      data.forEach(item => {
        if (typeof item === 'object' && item.key) {
          this.batchUpdater.update(item.key, item.value)
        }
      })
    })

    // 批量更新器 -> 聚合器（可选）
    if (this.aggregator) {
      this.batchUpdater.options.onBatchUpdate = (updates) => {
        updates.forEach((data, key) => {
          if (typeof data.value === 'number') {
            this.aggregator.add(key, data.value)
          }
        })
      }
    }
  }

  /**
   * 处理数据
   * 
   * @param {any} data - 数据
   */
  process(data) {
    this.throttler.push(data)
  }

  /**
   * 设置最终输出回调
   * 
   * @param {Function} callback - 回调函数
   */
  setOutputCallback(callback) {
    if (this.aggregator) {
      this.aggregator.options.onAggregate = callback
    } else {
      this.batchUpdater.options.onBatchUpdate = callback
    }
  }

  /**
   * 立即处理所有待处理数据
   */
  flush() {
    this.throttler.flush()
    this.batchUpdater.flush()
    if (this.aggregator) {
      this.aggregator.flush()
    }
  }

  /**
   * 清空所有队列
   */
  clear() {
    this.throttler.clear()
    this.batchUpdater.clear()
    if (this.aggregator) {
      this.aggregator.clear()
    }
  }

  /**
   * 销毁处理器
   */
  destroy() {
    this.throttler.destroy()
    this.batchUpdater.destroy()
    if (this.aggregator) {
      this.aggregator.destroy()
    }
  }
}

/**
 * 创建数据流处理器
 * 
 * @param {Object} options - 配置选项
 * @returns {DataStreamProcessor} 数据流处理器实例
 */
export function createStreamProcessor(options = {}) {
  return new DataStreamProcessor(options)
}

export default {
  DataThrottler,
  BatchUpdater,
  DataAggregator,
  DataStreamProcessor,
  createThrottler,
  createBatchUpdater,
  createAggregator,
  createStreamProcessor
}
