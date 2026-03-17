/**
 * @file playwright.config.js
 * @path frontend/tests/e2e/
 * @description Playwright E2E测试配置文件
 * 
 * 本配置文件定义了端到端测试的运行环境和参数，包括：
 * - 测试目录和文件匹配规则
 * - 浏览器项目配置（Chromium、Firefox、WebKit、移动端）
 * - 测试超时和重试策略
 * - 测试报告生成配置
 * - 开发服务器启动配置
 * - 截图、视频录制等调试功能
 * 
 * @author Agent
 * @date 2024-03-07
 * @dependencies @playwright/test
 */

import { defineConfig } from '@playwright/test';

/**
 * Playwright测试配置
 * 
 * @type {import('@playwright/test').PlaywrightTestConfig}
 */
export default defineConfig({
  /**
   * 测试目录路径
   * 相对于项目根目录的测试文件存放位置
   */
  testDir: './tests/e2e',
  
  /**
   * 测试文件匹配模式
   * 匹配所有.spec.js和.spec.ts文件
   */
  testMatch: '**/*.spec.{js,ts}',
  
  /**
   * 忽略的测试目录
   * 排除node_modules和fixtures目录
   */
  testIgnore: ['**/node_modules/**', 'tests/e2e/fixtures/**'],
  
  /**
   * 完全并行模式
   * 启用后所有测试文件将并行执行
   */
  fullyParallel: true,
  
  /**
   * 禁止.only修饰符
   * 在CI环境中禁止使用.only，防止意外跳过其他测试
   */
  forbidOnly: !!process.env.CI,
  
  /**
   * 失败重试次数
   * CI环境重试2次，本地开发不重试
   */
  retries: process.env.CI ? 2 : 0,
  
  /**
   * 并行工作进程数
   * CI环境使用单进程，本地使用默认值（CPU核心数）
   */
  workers: process.env.CI ? 1 : undefined,
  
  /**
   * 测试报告配置
   * - html: 生成HTML报告，不自动打开
   * - list: 控制台列表输出
   */
  reporter: [
    ['html', { open: 'never' }],
    ['list'],
  ],
  
  /**
   * 全局测试配置
   * 应用于所有测试的默认选项
   */
  use: {
    /** 基础URL，用于page.goto('/')等相对路径 */
    baseURL: 'http://localhost:5173',
    /** 追踪模式：仅在重试时记录 */
    trace: 'on-first-retry',
    /** 截图模式：仅在失败时截图 */
    screenshot: 'only-on-failure',
    /** 视频模式：仅在失败时保留 */
    video: 'retain-on-failure',
    /** 单个操作超时时间（毫秒） */
    actionTimeout: 10000,
    /** 页面导航超时时间（毫秒） */
    navigationTimeout: 30000,
  },
  
  /**
   * 浏览器项目配置
   * 定义不同浏览器和设备的测试环境
   */
  projects: [
    {
      /** Chromium浏览器测试 */
      name: 'chromium',
      use: {
        browserName: 'chromium',
        viewport: { width: 1920, height: 1080 },
      },
    },
    {
      /** Firefox浏览器测试 */
      name: 'firefox',
      use: {
        browserName: 'firefox',
        viewport: { width: 1920, height: 1080 },
      },
    },
    {
      /** WebKit浏览器测试（Safari内核） */
      name: 'webkit',
      use: {
        browserName: 'webkit',
        viewport: { width: 1920, height: 1080 },
      },
    },
    {
      /** 移动端Chrome测试（iPhone 8尺寸） */
      name: 'mobile-chrome',
      use: {
        browserName: 'chromium',
        viewport: { width: 375, height: 667 },
        isMobile: true,
      },
    },
    {
      /** Electron应用测试（仅在启用时运行） */
      name: 'electron',
      testMatch: '**/*.electron.spec.{js,ts}',
      use: {
        // Electron测试不使用浏览器配置
      },
    },
  ],
  
  /**
   * 开发服务器配置
   * 测试启动前自动运行开发服务器
   */
  webServer: {
    /** 启动开发服务器的命令 */
    command: 'npm run dev',
    /** 服务器就绪检测URL */
    url: 'http://localhost:5173',
    /** 是否复用已存在的服务器（本地开发时复用） */
    reuseExistingServer: !process.env.CI,
    /** 服务器启动超时时间（毫秒） */
    timeout: 120000,
  },
  
  /**
   * 断言超时配置
   * expect断言的默认超时时间
   */
  expect: {
    timeout: 10000,
  },
  
  /**
   * 全局超时时间
   * 单个测试文件的最大执行时间（毫秒）
   */
  timeout: 60000,
});
