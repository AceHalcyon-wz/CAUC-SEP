/**
 * @file index.js
 * @path src/composables/
 * @description 组合式函数统一导出文件
 * @author Agent
 * @date 2024-03-07
 */

// 错误处理相关
export { useErrorHandler, setupGlobalErrorHandler } from './useErrorHandler'
export {
  ERROR_TYPES,
  ERROR_SEVERITY,
  getErrorIcon,
  getSeverityColor,
  getErrorTypeLabel
} from '../utils/errorSolutions'

// 进度管理
export { useProgress, createProgressTracker, OPERATION_STATUS } from './useProgress'

// 在线状态检测
export {
  useOnlineStatus,
  getNetworkConnectionInfo,
  isNetworkInformationSupported,
  CONNECTION_TYPES
} from './useOnlineStatus'

// WebSocket相关
export { useWebSocket, ProtocolType, ConnectionState } from './useWebSocket'
export {
  useWebSocketReconnect,
  createWebSocketManager,
  RECONNECT_STRATEGY,
  CONNECTION_STATUS
} from './useWebSocketReconnect'

// 数据相关
export { useDataAnimation } from './useDataAnimation'
export { useDataAnomaly } from './useDataAnomaly'
export { useDataFreshness } from './useDataFreshness'

// 设备相关
export { useDeviceBase } from './useDeviceBase'

// 历史记录相关
export { useHistoryQuery } from './useHistoryQuery'
export { useOperationHistory } from './useOperationHistory'

// 用户交互相关
export { useKeyboardShortcuts } from './useKeyboardShortcuts'
export { useOperationFeedback } from './useOperationFeedback'
export { useUserPreferences } from './useUserPreferences'

// 推送频率控制
export { usePushFrequency, PUSH_MODE, FREQUENCY_PRESETS } from './usePushFrequency'

// WebSocket集成
export { useWebSocketIntegration } from './useWebSocketIntegration'

// 离线功能
export {
  useOffline,
  OperationPriority,
  OperationStatus,
  SyncStatus,
  SyncStrategy
} from './useOffline'
