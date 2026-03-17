/**
 * @file index.js
 * @path frontend/tests/e2e/helpers/
 * @description E2E测试辅助函数统一导出
 * 
 * 提供所有测试辅助函数的统一导出入口，包括：
 * - Electron应用测试辅助
 * - 认证测试辅助
 * - 设备测试辅助
 * - 测试配置
 * 
 * @author Agent
 * @date 2024-03-16
 */

// Electron测试辅助
export {
  ElectronAppHelper,
  createElectronApp,
  quickLaunchElectron,
} from './electron.helper.js';

// 认证测试辅助
export {
  AuthHelper,
  createAuthHelper,
  quickLogin,
} from './auth.helper.js';

// 设备测试辅助
export {
  DeviceHelper,
  DeviceType,
  DeviceStatus,
  createDeviceHelper,
  quickConnectDevice,
} from './device.helper.js';

// 测试配置
export {
  testConfig,
  getApiUrl,
  getWebSocketUrl,
  getTestUser,
  getDeviceConfig,
  getTimeout,
  isCI,
  isElectronTestEnabled,
  getReportPath,
  overrideConfig,
} from './test.config.js';
