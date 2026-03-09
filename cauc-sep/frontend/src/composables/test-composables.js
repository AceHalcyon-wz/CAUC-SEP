/**
 * @file test-composables.js
 * @path src/composables/
 * @description 组合式函数导入测试
 */

// 测试导入所有组合式函数
import {
  useErrorHandler,
  useProgress,
  useOnlineStatus,
  useWebSocketReconnect,
  OPERATION_STATUS,
  RECONNECT_STRATEGY,
  CONNECTION_STATUS
} from './index.js'

console.log('✓ 所有组合式函数导入成功')

// 测试导出的常量
console.log('OPERATION_STATUS:', OPERATION_STATUS)
console.log('RECONNECT_STRATEGY:', RECONNECT_STRATEGY)
console.log('CONNECTION_STATUS:', CONNECTION_STATUS)

console.log('✓ 所有测试通过')
