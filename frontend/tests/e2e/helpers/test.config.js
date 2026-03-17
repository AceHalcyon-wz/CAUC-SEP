/**
 * @file test.config.js
 * @path frontend/tests/e2e/helpers/
 * @description E2E测试环境配置
 * 
 * 提供测试环境的统一配置管理，包括：
 * - 测试环境变量
 * - API端点配置
 * - 测试数据配置
 * - 超时和重试配置
 * 
 * @author Agent
 * @date 2024-03-16
 * @dependencies @playwright/test
 */

/**
 * 测试环境配置
 */
export const testConfig = {
  /**
   * 应用配置
   */
  app: {
    /** 前端基础URL */
    frontendUrl: process.env.FRONTEND_URL || 'http://localhost:5173',
    /** 后端API基础URL */
    apiBaseUrl: process.env.API_BASE_URL || 'http://localhost:8000',
    /** API版本 */
    apiVersion: process.env.API_VERSION || 'v1',
    /** Electron应用路径 */
    electronPath: process.env.ELECTRON_PATH || '../electron',
  },

  /**
   * 测试用户配置
   */
  users: {
    /** 管理员账户 */
    admin: {
      username: process.env.TEST_ADMIN_USERNAME || 'admin',
      password: process.env.TEST_ADMIN_PASSWORD || 'admin123',
      role: 'admin',
      permissions: ['read', 'write', 'delete', 'admin'],
    },
    /** 普通用户账户 */
    user: {
      username: process.env.TEST_USER_USERNAME || 'testuser',
      password: process.env.TEST_USER_PASSWORD || 'test123',
      role: 'user',
      permissions: ['read', 'write'],
    },
    /** 只读用户账户 */
    readonly: {
      username: process.env.TEST_READONLY_USERNAME || 'readonly',
      password: process.env.TEST_READONLY_PASSWORD || 'readonly123',
      role: 'readonly',
      permissions: ['read'],
    },
  },

  /**
   * 设备配置
   */
  devices: {
    /** 步进电机配置 */
    motor: {
      type: 'motor',
      port: process.env.TEST_MOTOR_PORT || 'COM3',
      baudRate: 9600,
      timeout: 30000,
    },
    /** 温度控制器配置 */
    temperature: {
      type: 'temperature',
      port: process.env.TEST_TEMP_PORT || 'COM4',
      baudRate: 9600,
      timeout: 30000,
    },
    /** 压电控制器配置 */
    piezo: {
      type: 'piezo',
      port: process.env.TEST_PIEZO_PORT || 'COM5',
      baudRate: 9600,
      timeout: 30000,
    },
    /** 电磁铁配置 */
    electromagnet: {
      type: 'electromagnet',
      port: process.env.TEST_EM_PORT || 'COM6',
      baudRate: 9600,
      timeout: 30000,
    },
    /** 皮安表配置 */
    ammeter: {
      type: 'ammeter',
      port: process.env.TEST_AMMETER_PORT || 'COM7',
      baudRate: 9600,
      timeout: 30000,
    },
  },

  /**
   * 超时配置（毫秒）
   */
  timeouts: {
    /** 默认操作超时 */
    default: 10000,
    /** 导航超时 */
    navigation: 30000,
    /** API请求超时 */
    api: 15000,
    /** 设备连接超时 */
    deviceConnection: 30000,
    /** 设备操作超时 */
    deviceOperation: 60000,
    /** WebSocket连接超时 */
    websocket: 10000,
  },

  /**
   * 重试配置
   */
  retries: {
    /** 失败重试次数 */
    maxRetries: process.env.CI ? 2 : 0,
    /** 重试延迟（毫秒） */
    retryDelay: 1000,
    /** API请求重试次数 */
    apiRetries: 3,
  },

  /**
   * 测试数据配置
   */
  testData: {
    /** 是否使用模拟数据 */
    useMockData: process.env.USE_MOCK_DATA !== 'false',
    /** 模拟数据路径 */
    mockDataPath: './tests/e2e/fixtures/mock-data',
    /** 测试报告输出路径 */
    reportPath: './test-results',
    /** 截图保存路径 */
    screenshotPath: './test-results/screenshots',
    /** 视频保存路径 */
    videoPath: './test-results/videos',
  },

  /**
   * 浏览器配置
   */
  browser: {
    /** 默认浏览器 */
    defaultBrowser: 'chromium',
    /** 视口大小 */
    viewport: { width: 1920, height: 1080 },
    /** 是否无头模式 */
    headless: process.env.CI ? true : false,
    /** 是否启用追踪 */
    trace: 'on-first-retry',
    /** 是否启用截图 */
    screenshot: 'only-on-failure',
    /** 是否启用视频录制 */
    video: 'retain-on-failure',
  },

  /**
   * Electron配置
   */
  electron: {
    /** 是否启用Electron测试 */
    enabled: process.env.ELECTRON_TEST === 'true',
    /** Electron可执行文件路径 */
    executablePath: null, // 自动检测
    /** 是否启用开发者工具 */
    devTools: false,
    /** 启动参数 */
    args: ['--enable-logging'],
  },

  /**
   * API端点配置
   */
  api: {
    /** 认证端点 */
    auth: {
      login: '/api/v1/auth/login',
      logout: '/api/v1/auth/logout',
      refresh: '/api/v1/auth/refresh',
      me: '/api/v1/auth/me',
    },
    /** 设备端点 */
    devices: {
      list: '/api/v1/devices',
      connect: '/api/v1/devices/:type/connect',
      disconnect: '/api/v1/devices/:type/disconnect',
      status: '/api/v1/devices/:type/status',
      config: '/api/v1/devices/:type/config',
    },
    /** 实验端点 */
    experiments: {
      list: '/api/v1/experiments',
      create: '/api/v1/experiments',
      update: '/api/v1/experiments/:id',
      delete: '/api/v1/experiments/:id',
      start: '/api/v1/experiments/:id/start',
      stop: '/api/v1/experiments/:id/stop',
    },
    /** 分析端点 */
    analysis: {
      realtime: '/api/v1/analysis/realtime',
      history: '/api/v1/analysis/history',
      export: '/api/v1/analysis/export',
    },
  },

  /**
   * WebSocket配置
   */
  websocket: {
    /** WebSocket基础URL */
    baseUrl: process.env.WS_BASE_URL || 'ws://localhost:8000',
    /** 连接超时 */
    connectionTimeout: 10000,
    /** 重连延迟 */
    reconnectDelay: 3000,
    /** 最大重连次数 */
    maxReconnectAttempts: 5,
  },

  /**
   * 日志配置
   */
  logging: {
    /** 日志级别 */
    level: process.env.LOG_LEVEL || 'info',
    /** 是否输出到控制台 */
    console: true,
    /** 是否输出到文件 */
    file: process.env.CI ? true : false,
    /** 日志文件路径 */
    filePath: './test-results/test.log',
  },
};

/**
 * 获取API完整URL
 * 
 * @param {string} endpoint - API端点
 * @returns {string} 完整URL
 */
export function getApiUrl(endpoint) {
  const baseUrl = testConfig.app.apiBaseUrl;
  const version = testConfig.app.apiVersion;
  return `${baseUrl}/api/${version}${endpoint}`;
}

/**
 * 获取WebSocket完整URL
 * 
 * @param {string} path - WebSocket路径
 * @returns {string} 完整URL
 */
export function getWebSocketUrl(path) {
  const baseUrl = testConfig.websocket.baseUrl;
  return `${baseUrl}${path}`;
}

/**
 * 获取测试用户
 * 
 * @param {string} role - 用户角色
 * @returns {Object} 用户信息
 */
export function getTestUser(role = 'admin') {
  return testConfig.users[role] || testConfig.users.admin;
}

/**
 * 获取设备配置
 * 
 * @param {string} deviceType - 设备类型
 * @returns {Object} 设备配置
 */
export function getDeviceConfig(deviceType) {
  return testConfig.devices[deviceType] || null;
}

/**
 * 获取超时配置
 * 
 * @param {string} type - 超时类型
 * @returns {number} 超时时间（毫秒）
 */
export function getTimeout(type = 'default') {
  return testConfig.timeouts[type] || testConfig.timeouts.default;
}

/**
 * 检查是否为CI环境
 * 
 * @returns {boolean} 是否为CI环境
 */
export function isCI() {
  return process.env.CI === 'true';
}

/**
 * 检查是否启用Electron测试
 * 
 * @returns {boolean} 是否启用Electron测试
 */
export function isElectronTestEnabled() {
  return testConfig.electron.enabled;
}

/**
 * 获取测试报告路径
 * 
 * @param {string} type - 报告类型
 * @returns {string} 报告路径
 */
export function getReportPath(type = 'report') {
  const paths = {
    report: testConfig.testData.reportPath,
    screenshot: testConfig.testData.screenshotPath,
    video: testConfig.testData.videoPath,
  };

  return paths[type] || paths.report;
}

/**
 * 环境变量覆盖配置
 * 
 * @param {Object} overrides - 覆盖的配置
 * @returns {Object} 合并后的配置
 */
export function overrideConfig(overrides = {}) {
  return {
    ...testConfig,
    ...overrides,
    app: { ...testConfig.app, ...overrides.app },
    users: { ...testConfig.users, ...overrides.users },
    devices: { ...testConfig.devices, ...overrides.devices },
    timeouts: { ...testConfig.timeouts, ...overrides.timeouts },
    browser: { ...testConfig.browser, ...overrides.browser },
  };
}

export default testConfig;
