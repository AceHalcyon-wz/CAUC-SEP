/**
 * @file data-diff.ts
 * @path frontend/src/utils/data-diff.ts
 * @description 实时数据diff和局部更新工具，避免全量DOM更新
 * @author Agent
 * @date 2026-03-25
 */

/**
 * 变更类型枚举
 */
export enum ChangeType {
  ADD = 'add',
  UPDATE = 'update',
  DELETE = 'delete'
}

/**
 * 数据变更接口
 */
export interface IDataChange {
  type: ChangeType
  path: string
  oldValue?: unknown
  newValue?: unknown
  key?: string
}

/**
 * Diff选项接口
 */
export interface IDiffOptions {
  /** 是否深度比较 */
  deep?: boolean
  /** 是否比较数组顺序 */
  arrayOrder?: boolean
  /** 忽略的键列表 */
  ignoreKeys?: string[]
  /** 自定义比较函数 */
  comparator?: (oldValue: unknown, newValue: unknown, key: string) => boolean
}

/**
 * 深度比较两个对象，返回差异
 * 
 * @param oldObj - 旧对象
 * @param newObj - 新对象
 * @param path - 当前路径
 * @param options - 选项
 * @returns 差异数组
 */
export function deepDiff(
  oldObj: Record<string, unknown>,
  newObj: Record<string, unknown>,
  path = '',
  options: IDiffOptions = {}
): { changes: IDataChange[] } {
  const { deep = true, ignoreKeys = [], comparator } = options
  const changes: IDataChange[] = []

  // 获取所有键
  const allKeys = new Set([
    ...Object.keys(oldObj),
    ...Object.keys(newObj)
  ])

  for (const key of allKeys) {
    // 跳过忽略的键
    if (ignoreKeys?.includes(key)) continue

    const currentPath = path ? `${path}.${key}` : key
    const oldValue = oldObj[key]
    const newValue = newObj[key]

    // 使用自定义比较函数
    if (comparator && comparator(oldValue, newValue, key)) continue

    // 判断类型
    if (oldValue === undefined) {
      // 新增
      changes.push({
        type: ChangeType.ADD,
        path: currentPath,
        newValue
      })
    } else if (newValue === undefined) {
      // 删除
      changes.push({
        type: ChangeType.DELETE,
        path: currentPath,
        oldValue
      })
    } else if (typeof oldValue === 'object' && typeof newValue === 'object' && oldValue !== null && newValue !== null) {
      // 递归比较对象
      if (deep) {
        const subResult = deepDiff(
          oldValue as Record<string, unknown>,
          newValue as Record<string, unknown>,
          currentPath,
          options
        )
        changes.push(...subResult.changes)
      } else if (oldValue !== newValue) {
        changes.push({
          type: ChangeType.UPDATE,
          path: currentPath,
          oldValue,
          newValue
        })
      }
    } else if (Array.isArray(oldValue) && Array.isArray(newValue)) {
      // 比较数组
      const arrayChanges = diffArray(oldValue, newValue, currentPath, options)
      changes.push(...arrayChanges)
    } else if (oldValue !== newValue) {
      // 更新
      changes.push({
        type: ChangeType.UPDATE,
        path: currentPath,
        oldValue,
        newValue
      })
    }
  }

  return { changes }
}

/**
 * 比较两个数组
 */
function diffArray(
  oldArr: unknown[],
  newArr: unknown[],
  path: string,
  options: IDiffOptions
): IDataChange[] {
  const changes: IDataChange[] = []
  const maxLength = Math.max(oldArr.length, newArr.length)

  for (let i = 0; i < maxLength; i++) {
    const currentPath = `${path}[${i}]`
    const oldValue = oldArr[i]
    const newValue = newArr[i]

    if (oldValue === undefined) {
      changes.push({
        type: ChangeType.ADD,
        path: currentPath,
        newValue,
        key: String(i)
      })
    } else if (newValue === undefined) {
      changes.push({
        type: ChangeType.DELETE,
        path: currentPath,
        oldValue,
        key: String(i)
      })
    } else if (typeof oldValue === 'object' && typeof newValue === 'object' && oldValue !== null && newValue !== null) {
      // 递归比较
      const subResult = deepDiff(
        oldValue as Record<string, unknown>,
        newValue as Record<string, unknown>,
        currentPath,
        options
      )
      changes.push(...subResult.changes)
    } else if (oldValue !== newValue) {
      changes.push({
        type: ChangeType.UPDATE,
        path: currentPath,
        oldValue,
        newValue,
        key: String(i)
      })
    }
  }

  return changes
}

/**
 * 应用差异到对象
 * 
 * @param obj - 目标对象
 * @param changes - 变更列表
 * @returns 更新后的对象
 */
export function applyChanges<T extends Record<string, unknown>>(
  obj: T,
  changes: IDataChange[]
): T {
  const result = { ...obj }

  changes.forEach(change => {
    const paths = change.path.split('.')
    let current: Record<string, unknown> = result

    // 导航到目标路径
    for (let i = 0; i < paths.length - 1; i++) {
      const key = paths[i]
      if (!(key in current)) {
        current[key] = {}
      }
      current = current[key] as Record<string, unknown>
    }

    // 应用变更
    const lastKey = paths[paths.length - 1]
    switch (change.type) {
      case ChangeType.ADD:
      case ChangeType.UPDATE:
        current[lastKey] = change.newValue
        break
      case ChangeType.DELETE:
        delete current[lastKey]
        break
    }
  })

  return result
}
/**
 * 浅比较两个对象
* 
 * @param obj1 - 对象1
 * @param obj2 - 对象2
 * @returns 是否相等
 */
export function shallowEqual(obj1: unknown, obj2: unknown): boolean {
  if (obj1 === obj2) return true
  if (typeof obj1 !== 'object' || obj1 === null || typeof obj2 !== 'object' || obj2 === null) {
    return false
  }
  const keys1 = Object.keys(obj1 as Record<string, unknown>)
  const keys2 = Object.keys(obj2 as Record<string, unknown>)
  if (keys1.length !== keys2.length) return false
  for (const key of keys1) {
    if ((obj1 as Record<string, unknown>)[key] !== (obj2 as Record<string, unknown>)[key]) {
      return false
    }
  }
  return true
}
/**
 * 比较两个数组是否相等（浅比较）
 * 
 * @param arr1 - 数组1
 * @param arr2 - 数组2
 * @returns 是否相等
 */
export function arrayEqual(arr1: unknown[], arr2: unknown[]): boolean {
  if (arr1 === arr2) return true
  if (arr1.length !== arr2.length) return false
  for (let i = 0; i < arr1.length; i++) {
    if (arr1[i] !== arr2[i]) return false
  }
  return true
}
/**
 * 数据更新器类
 * 
 * @description 管理数据更新，支持批量更新、防抖、节流
 */
export class DataUpdater {
  private updateQueue: Map<string, { value: unknown; timestamp: number }> = new Map()
  private timer: number | null = null
  private updateCallback: ((updates: Map<string, unknown>) => void) | null = null
  private batchInterval: number
  private maxBatchSize: number

  constructor(options: { batchInterval?: number; maxBatchSize?: number } = {}) {
    this.batchInterval = options.batchInterval || 50
    this.maxBatchSize = options.maxBatchSize || 50
  }

  /**
   * 设置更新回调
   */
  setUpdateCallback(callback: (updates: Map<string, unknown>) => void): void {
    this.updateCallback = callback
  }

  /**
   * 添加更新
   */
  update(key: string, value: unknown): void {
    this.updateQueue.set(key, {
      value,
      timestamp: Date.now()
    })
    this.scheduleBatch()
  }

  /**
   * 批量添加更新
   */
  updateBatch(updates: Record<string, unknown>): void {
    const timestamp = Date.now()
    Object.entries(updates).forEach(([key, value]) => {
      this.updateQueue.set(key, { value, timestamp })
    })
    this.scheduleBatch()
  }

  /**
   * 安排批量更新
   */
  private scheduleBatch(): void {
    // 如果达到最大批量大小，立即执行
    if (this.updateQueue.size >= this.maxBatchSize) {
      this.executeBatch()
      return
    }

    // 否则延迟执行
    if (this.timer) return
    this.timer = window.setTimeout(() => {
      this.executeBatch()
      this.timer = null
    }, this.batchInterval)
  }

  /**
   * 执行批量更新
   */
  private executeBatch(): void {
    if (this.updateQueue.size === 0) return
    const updates = new Map<string, unknown>()
    this.updateQueue.forEach((data, key) => {
      updates.set(key, data.value)
    })
    this.updateQueue.clear()
    if (this.updateCallback) {
      this.updateCallback(updates)
    }
  }

  /**
   * 刷新队列
   */
  flush(): void {
    if (this.timer) {
      clearTimeout(this.timer)
      this.timer = null
    }
    this.executeBatch()
  }

  /**
   * 清空队列
   */
  clear(): void {
    if (this.timer) {
      clearTimeout(this.timer)
      this.timer = null
    }
    this.updateQueue.clear()
  }

  /**
   * 销毁
   */
  destroy(): void {
    this.clear()
    this.updateCallback = null
  }
}
/**
 * 创建数据更新器
 */
export function createDataUpdater(options?: { batchInterval?: number; maxBatchSize?: number }): DataUpdater {
  return new DataUpdater(options)
}
export default {
  deepDiff,
  applyChanges,
  shallowEqual,
  arrayEqual,
  DataUpdater,
  createDataUpdater,
  ChangeType
}
