/**
 * @file index.ts
 * @path frontend/src/types/index.ts
 * @description 类型定义统一导出入口，提供完整的TypeScript类型支持
 * @author Agent
 * @date 2026-03-25
 * @dependencies ./api, ./device, ./experiment, ./forms, ./events, ./chart, ./websocket, ./generated
 */

// ==================== API通用类型 ====================
export * from './api'

// ==================== 设备相关类型 ====================
export * from './device'

// ==================== 实验相关类型 ====================
export * from './experiment'

// ==================== 表单参数类型 ====================
export * from './forms'

// ==================== 事件参数类型 ====================
export * from './events'

// ==================== 图表相关类型 ====================
export * from './chart'

// ==================== WebSocket消息类型 ====================
export * from './websocket'

// ==================== 自动生成类型 ====================
export type {
  components,
  ApiSuccessResponse,
  ApiErrorResponse,
} from './generated'

// ==================== Vue组件类型 ====================
export type { DefineComponent } from 'vue'

// ==================== 通用工具类型 ====================

/** 通用键值对 */
export type KeyValueMap<K extends string | number | symbol = string, V = unknown> = Record<K, V>

/** 通用数字字典 */
export type NumberMap = Record<string, number>

/** 通用字符串字典 */
export type StringMap = Record<string, string>

/** 通用布尔字典 */
export type BooleanMap = Record<string, boolean>

/** 可空类型 */
export type Nullable<T> = T | null

/** 可选类型 */
export type Optional<T> = T | undefined

/** 可空可选类型 */
export type Maybe<T> = T | null | undefined

/** 非空类型断言 */
export type NonNullable<T> = T extends null | undefined ? never : T

/** 只读类型 */
export type Readonly<T> = {
  readonly [P in keyof T]: T[P]
}

/** 深度只读类型 */
export type DeepReadonly<T> = {
  readonly [P in keyof T]: T[P] extends object ? DeepReadonly<T[P]> : T[P]
}

/** 部分可选类型 */
export type PartialBy<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>

/** 部分必选类型 */
export type RequiredBy<T, K extends keyof T> = Omit<T, K> & Required<Pick<T, K>>

/** 提取函数参数类型 */
export type ArgumentTypes<T> = T extends (...args: infer A) => unknown ? A : never

/** 提取函数返回类型 */
export type ReturnType<T> = T extends (...args: unknown[]) => infer R ? R : never

/** 提取Promise返回类型 */
export type PromiseType<T> = T extends Promise<infer U> ? U : T

/** 提取数组元素类型 */
export type ArrayElement<T> = T extends readonly (infer E)[] ? E : never

/** 提取对象值类型 */
export type ValueOf<T> = T[keyof T]

/** 提取对象键类型 */
export type KeyOf<T> = keyof T

/** 将对象键转换为联合类型 */
export type ObjectKeys<T> = T extends object ? keyof T : never

/** 将对象值转换为联合类型 */
export type ObjectValues<T> = T extends object ? T[keyof T] : never

/** 事件处理器类型 */
export type EventHandler<T = unknown> = (event: T) => void

/** 异步事件处理器类型 */
export type AsyncEventHandler<T = unknown> = (event: T) => Promise<void>

/** 回调函数类型 */
export type Callback<T = void, R = void> = (arg: T) => R

/** 异步回调函数类型 */
export type AsyncCallback<T = void, R = void> = (arg: T) => Promise<R>

/** 比较函数类型 */
export type CompareFunction<T> = (a: T, b: T) => number

/** 过滤函数类型 */
export type FilterFunction<T> = (value: T, index: number, array: T[]) => boolean

/** 映射函数类型 */
export type MapFunction<T, R> = (value: T, index: number, array: T[]) => R

/** 归约函数类型 */
export type ReduceFunction<T, R> = (accumulator: R, currentValue: T, index: number, array: T[]) => R

/** 断言函数类型 */
export type PredicateFunction<T = unknown> = (value: T) => boolean

/** 类型守卫函数 */
export type TypeGuardFunction<T, U extends T> = (value: T) => value is U

// ==================== 类型守卫工具函数 ====================

/** 排除null和undefined的类型守卫 */
export function isDefined<T>(value: T | null | undefined): value is T {
  return value !== null && value !== undefined
}

/** 排除null的类型守卫 */
export function isNotNull<T>(value: T | null): value is T {
  return value !== null
}

/** 排除undefined的类型守卫 */
export function isNotUndefined<T>(value: T | undefined): value is T {
  return value !== undefined
}

/** 类型断言辅助函数 */
export function assertDefined<T>(value: T | null | undefined, message?: string): asserts value is T {
  if (value === null || value === undefined) {
    throw new Error(message ?? 'Value is null or undefined')
  }
}

/** 类型断言辅助函数（不抛出异常） */
export function assertType<T>(value: unknown, condition: boolean): value is T {
  return condition
}

/** 判断是否为字符串 */
export function isString(value: unknown): value is string {
  return typeof value === 'string'
}

/** 判断是否为数字 */
export function isNumber(value: unknown): value is number {
  return typeof value === 'number' && !isNaN(value)
}

/** 判断是否为布尔值 */
export function isBoolean(value: unknown): value is boolean {
  return typeof value === 'boolean'
}

/** 判断是否为对象 */
export function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/** 判断是否为数组 */
export function isArray<T = unknown>(value: unknown): value is T[] {
  return Array.isArray(value)
}

/** 判断是否为函数 */
export function isFunction(value: unknown): value is (...args: unknown[]) => unknown {
  return typeof value === 'function'
}

/** 判断是否为Promise */
export function isPromise<T = unknown>(value: unknown): value is Promise<T> {
  return value instanceof Promise || (isObject(value) && isFunction((value as Record<string, unknown>).then))
}

/** 判断是否为Date */
export function isDate(value: unknown): value is Date {
  return value instanceof Date
}

/** 判断是否为Error */
export function isError(value: unknown): value is Error {
  return value instanceof Error
}

// ==================== 类型转换工具函数 ====================

/** 安全获取对象属性值 */
export function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] | undefined {
  return obj?.[key]
}

/** 安全设置对象属性值 */
export function setProperty<T, K extends keyof T>(obj: T, key: K, value: T[K]): void {
  if (obj) {
    obj[key] = value
  }
}

/** 深度克隆对象 */
export function deepClone<T>(obj: T): T {
  if (obj === null || typeof obj !== 'object') {
    return obj
  }

  if (Array.isArray(obj)) {
    return obj.map((item) => deepClone(item)) as T
  }

  if (obj instanceof Date) {
    return new Date(obj.getTime()) as T
  }

  if (obj instanceof Map) {
    const clonedMap = new Map()
    obj.forEach((value, key) => {
      clonedMap.set(key, deepClone(value))
    })
    return clonedMap as T
  }

  if (obj instanceof Set) {
    const clonedSet = new Set()
    obj.forEach((value) => {
      clonedSet.add(deepClone(value))
    })
    return clonedSet as T
  }

  const cloned = {} as T
  for (const key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      cloned[key] = deepClone(obj[key])
    }
  }
  return cloned
}

/** 深度合并对象 */
export function deepMerge<T extends Record<string, unknown>>(target: T, ...sources: Partial<T>[]): T {
  if (!sources.length) return target

  const source = sources.shift()

  if (isObject(target) && isObject(source)) {
    for (const key in source) {
      if (isObject(source[key])) {
        if (!target[key]) {
          Object.assign(target, { [key]: {} })
        }
        deepMerge(target[key] as Record<string, unknown>, source[key] as Record<string, unknown>)
      } else {
        Object.assign(target, { [key]: source[key] })
      }
    }
  }

  return deepMerge(target, ...sources)
}

/** 对象键名转换 */
export function mapKeys<T extends Record<string, unknown>>(
  obj: T,
  mapper: (key: string) => string
): Record<string, unknown> {
  const result: Record<string, unknown> = {}
  for (const key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      result[mapper(key)] = obj[key]
    }
  }
  return result
}

/** 对象值转换 */
export function mapValues<T extends Record<string, unknown>, R>(
  obj: T,
  mapper: (value: T[keyof T], key: string) => R
): Record<string, R> {
  const result: Record<string, R> = {}
  for (const key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      result[key] = mapper(obj[key] as T[keyof T], key)
    }
  }
  return result
}

/** 挑选对象属性 */
export function pick<T extends object, K extends keyof T>(obj: T, keys: K[]): Pick<T, K> {
  const result = {} as Pick<T, K>
  keys.forEach((key) => {
    if (key in obj) {
      result[key] = obj[key]
    }
  })
  return result
}

/** 排除对象属性 */
export function omit<T extends object, K extends keyof T>(obj: T, keys: K[]): Omit<T, K> {
  const result = { ...obj }
  keys.forEach((key) => {
    delete result[key]
  })
  return result
}
