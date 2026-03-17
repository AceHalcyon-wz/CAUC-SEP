/**
 * @file global.d.ts
 * @path src/types/
 * @description 全局类型定义
 */

export {}

declare global {
  interface Window {
    __APP_VERSION__?: string
    __APP_ENV__?: string
  }
}
