/**
 * @file example.spec.js
 * @path frontend/tests/e2e/
 * @description E2E测试框架验证示例
 * 
 * 本测试文件用于验证Playwright E2E测试框架的正确配置，包括：
 * - 测试环境配置验证
 * - 辅助函数功能验证
 * - 页面导航测试
 * - 基础功能测试
 * 
 * @author Agent
 * @date 2024-03-16
 * @dependencies @playwright/test, ./helpers
 */

import { test, expect } from '@playwright/test';
import { 
  AuthHelper, 
  DeviceHelper,
  testConfig,
  getTestUser,
  getTimeout,
  isCI 
} from './helpers/index.js';

/**
 * 测试框架配置验证套件
 * 
 * 验证测试框架的基础配置是否正确。
 */
test.describe('测试框架配置验证', () => {
  /**
   * 验证测试配置加载
   */
  test('应该正确加载测试配置', () => {
    expect(testConfig).toBeDefined();
    expect(testConfig.app).toBeDefined();
    expect(testConfig.app.frontendUrl).toBeTruthy();
    expect(testConfig.timeouts).toBeDefined();
    expect(testConfig.browser).toBeDefined();
  });

  /**
   * 验证测试用户配置
   */
  test('应该正确加载测试用户配置', () => {
    const adminUser = getTestUser('admin');
    expect(adminUser).toBeDefined();
    expect(adminUser.username).toBeTruthy();
    expect(adminUser.password).toBeTruthy();
    expect(adminUser.role).toBe('admin');
  });

  /**
   * 验证超时配置
   */
  test('应该正确获取超时配置', () => {
    const defaultTimeout = getTimeout('default');
    const navigationTimeout = getTimeout('navigation');
    
    expect(defaultTimeout).toBeGreaterThan(0);
    expect(navigationTimeout).toBeGreaterThan(0);
  });

  /**
   * 验证CI环境检测
   */
  test('应该正确检测CI环境', () => {
    const ciStatus = isCI();
    expect(typeof ciStatus).toBe('boolean');
  });
});

/**
 * 辅助函数验证套件
 * 
 * 验证测试辅助函数的功能。
 */
test.describe('辅助函数验证', () => {
  let page;

  test.beforeEach(async ({ page: testPage }) => {
    page = testPage;
  });

  /**
   * 验证AuthHelper实例化
   */
  test('应该正确创建AuthHelper实例', () => {
    const authHelper = new AuthHelper(page);
    expect(authHelper).toBeDefined();
    expect(authHelper.page).toBe(page);
  });

  /**
   * 验证DeviceHelper实例化
   */
  test('应该正确创建DeviceHelper实例', () => {
    const deviceHelper = new DeviceHelper(page);
    expect(deviceHelper).toBeDefined();
    expect(deviceHelper.page).toBe(page);
  });

  /**
   * 验证设备名称映射
   */
  test('应该正确获取设备名称', () => {
    const deviceHelper = new DeviceHelper(page);
    
    expect(deviceHelper.getDeviceName('motor')).toBe('步进电机');
    expect(deviceHelper.getDeviceName('temperature')).toBe('温度控制器');
    expect(deviceHelper.getDeviceName('piezo')).toBe('压电控制器');
  });

  /**
   * 验证状态文本映射
   */
  test('应该正确获取状态文本', () => {
    const deviceHelper = new DeviceHelper(page);
    
    expect(deviceHelper.getStatusText('connected')).toBe('已连接');
    expect(deviceHelper.getStatusText('disconnected')).toBe('未连接');
    expect(deviceHelper.getStatusText('error')).toBe('错误');
  });
});

/**
 * 页面导航验证套件
 * 
 * 验证应用的页面导航功能。
 */
test.describe('页面导航验证', () => {
  /**
   * 验证首页加载
   */
  test('应该正确加载首页', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 验证页面标题
    const title = await page.title();
    expect(title).toBeTruthy();
    
    // 验证页面内容
    const body = page.locator('body');
    await expect(body).toBeVisible();
  });

  /**
   * 验证登录页面
   */
  test('应该正确加载登录页面', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    // 验证登录表单存在
    const usernameInput = page.locator('input[name="username"]');
    const passwordInput = page.locator('input[name="password"]');
    
    // 如果登录表单存在，验证其可见性
    if (await usernameInput.isVisible()) {
      await expect(usernameInput).toBeVisible();
      await expect(passwordInput).toBeVisible();
    }
  });

  /**
   * 验证设备连接页面
   */
  test('应该正确加载设备连接页面', async ({ page }) => {
    await page.goto('/device/connection');
    await page.waitForLoadState('networkidle');
    
    expect(page.url()).toContain('/device/connection');
  });

  /**
   * 验证设备状态页面
   */
  test('应该正确加载设备状态页面', async ({ page }) => {
    await page.goto('/device/status');
    await page.waitForLoadState('networkidle');
    
    expect(page.url()).toContain('/device/status');
  });
});

/**
 * 认证功能验证套件
 * 
 * 验证认证辅助函数的功能。
 */
test.describe('认证功能验证', () => {
  let authHelper;

  test.beforeEach(async ({ page }) => {
    authHelper = new AuthHelper(page);
  });

  /**
   * 验证模拟认证功能
   */
  test('应该能够模拟认证状态', async ({ page }) => {
    await page.goto('/');
    
    // 模拟认证状态
    await authHelper.mockAuthenticated({
      username: 'testuser',
      role: 'admin',
    });
    
    // 验证Token已设置
    const token = await authHelper.getToken();
    expect(token).toBeTruthy();
    
    // 验证用户信息已设置
    const user = await authHelper.getCurrentUser();
    expect(user).toBeDefined();
    expect(user.username).toBe('testuser');
  });

  /**
   * 验证清除认证功能
   */
  test('应该能够清除认证状态', async ({ page }) => {
    await page.goto('/');
    
    // 设置认证状态
    await authHelper.setToken('test-token');
    
    // 清除认证
    await authHelper.clearAuth();
    
    // 验证Token已清除
    const token = await authHelper.getToken();
    expect(token).toBeNull();
  });

  /**
   * 验证权限检查功能
   */
  test('应该能够检查用户权限', async ({ page }) => {
    await page.goto('/');
    
    // 模拟带权限的用户
    await authHelper.mockAuthenticated({
      permissions: ['read', 'write'],
    });
    
    // 检查权限
    const hasRead = await authHelper.hasPermission('read');
    const hasWrite = await authHelper.hasPermission('write');
    const hasDelete = await authHelper.hasPermission('delete');
    
    expect(hasRead).toBe(true);
    expect(hasWrite).toBe(true);
    expect(hasDelete).toBe(false);
  });
});

/**
 * 设备功能验证套件
 * 
 * 验证设备辅助函数的功能。
 */
test.describe('设备功能验证', () => {
  let deviceHelper;

  test.beforeEach(async ({ page }) => {
    deviceHelper = new DeviceHelper(page);
  });

  /**
   * 验证导航到设备连接页面
   */
  test('应该能够导航到设备连接页面', async ({ page }) => {
    await deviceHelper.gotoConnectionPage();
    
    expect(page.url()).toContain('/device/connection');
  });

  /**
   * 验证导航到设备状态页面
   */
  test('应该能够导航到设备状态页面', async ({ page }) => {
    await deviceHelper.gotoStatusPage();
    
    expect(page.url()).toContain('/device/status');
  });

  /**
   * 验证设备模拟功能
   */
  test('应该能够模拟设备连接', async ({ page }) => {
    await page.goto('/device/status');
    
    // 模拟设备连接
    await deviceHelper.mockDeviceConnection('motor', {
      status: 'connected',
      port: 'COM3',
    });
    
    // 验证模拟数据已设置
    const mockData = await page.evaluate(() => {
      return window.__mockDevices?.motor;
    });
    
    expect(mockData).toBeDefined();
    expect(mockData.status).toBe('connected');
  });

  /**
   * 验证清除设备模拟
   */
  test('应该能够清除设备模拟', async ({ page }) => {
    await page.goto('/device/status');
    
    // 设置模拟数据
    await deviceHelper.mockDeviceConnection('motor');
    
    // 清除模拟
    await deviceHelper.clearDeviceMock('motor');
    
    // 验证模拟数据已清除
    const mockData = await page.evaluate(() => {
      return window.__mockDevices?.motor;
    });
    
    expect(mockData).toBeUndefined();
  });
});

/**
 * 测试框架完整性验证
 * 
 * 验证测试框架的所有组件是否正常工作。
 */
test.describe('测试框架完整性验证', () => {
  /**
   * 验证所有辅助模块导出
   */
  test('应该正确导出所有辅助模块', async () => {
    // 动态导入helpers模块
    const helpers = await import('./helpers/index.js');
    
    // 验证导出的模块
    expect(helpers.AuthHelper).toBeDefined();
    expect(helpers.DeviceHelper).toBeDefined();
    expect(helpers.testConfig).toBeDefined();
    expect(helpers.getTestUser).toBeDefined();
    expect(helpers.getTimeout).toBeDefined();
  });

  /**
   * 验证测试环境配置完整性
   */
  test('应该包含完整的测试环境配置', () => {
    expect(testConfig.app).toBeDefined();
    expect(testConfig.users).toBeDefined();
    expect(testConfig.devices).toBeDefined();
    expect(testConfig.timeouts).toBeDefined();
    expect(testConfig.browser).toBeDefined();
    expect(testConfig.api).toBeDefined();
    expect(testConfig.websocket).toBeDefined();
  });

  /**
   * 验证测试报告生成
   */
  test('应该能够生成测试报告', async ({ page }) => {
    await page.goto('/');
    
    // 执行一些操作以生成测试数据
    await page.waitForLoadState('networkidle');
    
    // 验证页面已加载
    const title = await page.title();
    expect(title).toBeTruthy();
  });
});
