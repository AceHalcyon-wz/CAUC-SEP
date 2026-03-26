/**
 * @file index.ts
 * @path src/components/common/
 * @description 通用组件统一导出
 * @author Agent
 * @date 2026-03-26
 * @version 3.5.2
 */

// ==================== 反馈组件 ====================
export { default as ErrorDisplay } from './ErrorDisplay.vue'
export { default as ErrorSolution } from './ErrorSolution.vue'
export { default as GlobalLoading } from './GlobalLoading.vue'
export { default as OperationFeedback } from './OperationFeedback.vue'
export { default as OperationProgress } from './OperationProgress.vue'

// ==================== 鸭架组件 ====================
export { default as PageSkeleton } from './PageSkeleton.vue'
export { default as RouteLoading } from './RouteLoading.vue'

// ==================== 用户引导组件 ====================
export { default as ShortcutHelp } from './ShortcutHelp.vue'
export { default as UserGuide } from './UserGuide.vue'

// ==================== 虚拟列表组件 ====================
export { default as VirtualList } from './VirtualList.vue'
export { default as VirtualScrollList } from './VirtualScrollList.vue'

// ==================== 状态指示组件 ====================
export { default as WebSocketStatusIndicator } from './WebSocketStatusIndicator.vue'

// ==================== 更新通知组件 ====================
export { default as UpdateNotification } from './UpdateNotification.vue'

// ==================== 子目录组件 ====================
export * from './buttons'
export * from './cards'
export * from './charts'
export * from './feedback'
export * from './forms'
export * from './status'
