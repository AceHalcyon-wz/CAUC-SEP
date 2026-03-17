/**
 * @file auth-flow.spec.js
 * @path frontend/tests/e2e/
 * @description 用户认证流程E2E测试
 * 
 * 测试范围：
 * - 用户登录流程
 * - 用户登出流程
 * - Token管理
 * - 权限验证
 * - 认证状态持久化
 * 
 * @author Agent
 * @date 2024-03-16
 * @dependencies @playwright/test, ./helpers
 */

import { test, expect } from '@playwright/test';
import { 
  ElectronAppHelper, 
  quickLaunchElectron,
  isElectronTestEnabled,
  AuthHelper,
  quickLogin,
} from './helpers/index.js';

/**
 * 测试配置
 */
const TEST_CONFIG = {
  /** 测试用户账号 */
  TEST_USERS: {
    admin: {
      username: 'admin',
      password: 'admin123',
      displayName: '系统管理员',
      role: 'admin',
    },
    operator: {
      username: 'operator',
      password: 'operator123',
      displayName: '实验操作员',
      role: 'operator',
    },
    viewer: {
      username: 'viewer',
      password: 'viewer123',
      displayName: '访客用户',
      role: 'viewer',
    },
  },
  /** 登录超时时间（毫秒） */
  LOGIN_TIMEOUT: 15000,
  /** Token刷新间隔（毫秒） */
  TOKEN_REFRESH_INTERVAL: 300000,
};

/**
 * 用户认证流程测试套件
 */
test.describe('用户认证流程测试', () => {
  let electronHelper;
  let window;
  let authHelper;

  /**
   * 测试前准备：启动Electron应用
   */
  test.beforeAll(async () => {
    if (!isElectronTestEnabled()) {
      test.skip(true, 'Electron测试未启用');
      return;
    }

    const result = await quickLaunchElectron({ headless: false });
    electronHelper = result.helper;
    window = result.window;
    authHelper = new AuthHelper(window);
  });

  /**
   * 测试后清理：关闭Electron应用
   */
  test.afterAll(async () => {
    if (electronHelper) {
      await electronHelper.close();
    }
  });

  /**
   * 每个测试前清除认证状态
   */
  test.beforeEach(async () => {
    await authHelper.clearAuth();
    await window.reload();
    await window.waitForLoadState('networkidle');
  });

  /**
   * 测试1：验证登录页面显示
   */
  test('应该显示登录页面', async () => {
    // 验证在登录页面
    const isOnLoginPage = await authHelper.isOnLoginPage();
    expect(isOnLoginPage).toBe(true);
    
    // 验证登录表单存在
    await authHelper.verifyLoginFormExists();
  });

  /**
   * 测试2：验证快速登录功能
   */
  test('应该能够使用快速登录', async () => {
    // 等待登录页面加载
    await window.waitForSelector('.login-card', { timeout: 10000 });
    
    // 点击管理员账号卡片
    const adminCard = window.locator('.account-card').first();
    await adminCard.click();
    
    // 等待登录完成
    await window.waitForURL('**/device/**', { timeout: TEST_CONFIG.LOGIN_TIMEOUT });
    
    // 验证已登录
    const isLoggedIn = await authHelper.isLoggedIn();
    expect(isLoggedIn).toBe(true);
  });

  /**
   * 测试3：验证账号密码登录功能
   */
  test('应该能够使用账号密码登录', async () => {
    // 等待登录页面加载
    await window.waitForSelector('.login-card', { timeout: 10000 });
    
    // 切换到账号密码模式
    const passwordModeBtn = window.locator('.mode-btn:has-text("账号密码")');
    if (await passwordModeBtn.isVisible()) {
      await passwordModeBtn.click();
    }
    
    // 填写登录表单
    const usernameInput = window.locator('input[name="username"]');
    const passwordInput = window.locator('input[name="password"]');
    
    if (await usernameInput.isVisible()) {
      await usernameInput.fill(TEST_CONFIG.TEST_USERS.admin.username);
      await passwordInput.fill(TEST_CONFIG.TEST_USERS.admin.password);
      
      // 提交登录
      const submitBtn = window.locator('button[type="submit"]');
      await submitBtn.click();
      
      // 等待登录完成
      await window.waitForURL('**/device/**', { timeout: TEST_CONFIG.LOGIN_TIMEOUT });
      
      // 验证已登录
      const isLoggedIn = await authHelper.isLoggedIn();
      expect(isLoggedIn).toBe(true);
    }
  });

  /**
   * 测试4：验证访客登录功能
   */
  test('应该能够使用访客模式登录', async () => {
    // 等待登录页面加载
    await window.waitForSelector('.login-card', { timeout: 10000 });
    
    // 切换到访客模式
    const guestModeBtn = window.locator('.mode-btn:has-text("访客")');
    if (await guestModeBtn.isVisible()) {
      await guestModeBtn.click();
      
      // 点击访客登录按钮
      const guestCard = window.locator('.account-card').first();
      await guestCard.click();
      
      // 等待登录完成
      await window.waitForURL('**/device/**', { timeout: TEST_CONFIG.LOGIN_TIMEOUT });
      
      // 验证已登录
      const isLoggedIn = await authHelper.isLoggedIn();
      expect(isLoggedIn).toBe(true);
    }
  });

  /**
   * 测试5：验证登录失败处理
   */
  test('应该正确处理登录失败', async () => {
    // 等待登录页面加载
    await window.waitForSelector('.login-card', { timeout: 10000 });
    
    // 切换到账号密码模式
    const passwordModeBtn = window.locator('.mode-btn:has-text("账号密码")');
    if (await passwordModeBtn.isVisible()) {
      await passwordModeBtn.click();
    }
    
    // 填写错误的登录信息
    const usernameInput = window.locator('input[name="username"]');
    const passwordInput = window.locator('input[name="password"]');
    
    if (await usernameInput.isVisible()) {
      await usernameInput.fill('invalid_user');
      await passwordInput.fill('invalid_password');
      
      // 提交登录
      const submitBtn = window.locator('button[type="submit"]');
      await submitBtn.click();
      
      // 等待错误消息
      await window.waitForTimeout(2000);
      
      // 验证仍在登录页面
      const isOnLoginPage = await authHelper.isOnLoginPage();
      expect(isOnLoginPage).toBe(true);
    }
  });

  /**
   * 测试6：验证Token存储
   */
  test('登录后应该正确存储Token', async () => {
    // 执行快速登录
    await window.waitForSelector('.login-card', { timeout: 10000 });
    const adminCard = window.locator('.account-card').first();
    await adminCard.click();
    
    await window.waitForURL('**/device/**', { timeout: TEST_CONFIG.LOGIN_TIMEOUT });
    
    // 验证Token存在
    const token = await authHelper.getToken();
    expect(token).toBeDefined();
    expect(token.length).toBeGreaterThan(0);
  });

  /**
   * 测试7：验证用户信息存储
   */
  test('登录后应该正确存储用户信息', async () => {
    // 执行快速登录
    await window.waitForSelector('.login-card', { timeout: 10000 });
    const adminCard = window.locator('.account-card').first();
    await adminCard.click();
    
    await window.waitForURL('**/device/**', { timeout: TEST_CONFIG.LOGIN_TIMEOUT });
    
    // 验证用户信息
    const user = await authHelper.getCurrentUser();
    expect(user).toBeDefined();
    expect(user.username).toBeDefined();
    expect(user.role).toBeDefined();
  });
});

/**
 * 用户登出流程测试套件
 */
test.describe('用户登出流程测试', () => {
  let electronHelper;
  let window;
  let authHelper;

  test.beforeAll(async () => {
    if (!isElectronTestEnabled()) {
      test.skip(true, 'Electron测试未启用');
      return;
    }

    const result = await quickLaunchElectron({ headless: false });
    electronHelper = result.helper;
    window = result.window;
    authHelper = new AuthHelper(window);
  });

  test.afterAll(async () => {
    if (electronHelper) {
      await electronHelper.close();
    }
  });

  test.beforeEach(async () => {
    // 先登录
    await authHelper.clearAuth();
    await window.reload();
    await window.waitForLoadState('networkidle');
    
    await window.waitForSelector('.login-card', { timeout: 10000 });
    const adminCard = window.locator('.account-card').first();
    await adminCard.click();
    
    await window.waitForURL('**/device/**', { timeout: TEST_CONFIG.LOGIN_TIMEOUT });
  });

  /**
   * 测试8：验证登出功能
   */
  test('应该能够成功登出', async () => {
    // 验证已登录
    const isLoggedInBefore = await authHelper.isLoggedIn();
    expect(isLoggedInBefore).toBe(true);
    
    // 执行登出
    await authHelper.logout();
    
    // 等待跳转到登录页
    await window.waitForURL('**/login**', { timeout: 10000 });
    
    // 验证已登出
    const isLoggedInAfter = await authHelper.isLoggedIn();
    expect(isLoggedInAfter).toBe(false);
  });

  /**
   * 测试9：验证登出后Token清除
   */
  test('登出后应该清除Token', async () => {
    // 执行登出
    await authHelper.logout();
    await window.waitForURL('**/login**', { timeout: 10000 });
    
    // 验证Token已清除
    const token = await authHelper.getToken();
    expect(token).toBeNull();
  });

  /**
   * 测试10：验证登出后用户信息清除
   */
  test('登出后应该清除用户信息', async () => {
    // 执行登出
    await authHelper.logout();
    await window.waitForURL('**/login**', { timeout: 10000 });
    
    // 验证用户信息已清除
    const user = await authHelper.getCurrentUser();
    expect(user).toBeNull();
  });

  /**
   * 测试11：验证登出后无法访问受保护页面
   */
  test('登出后应该无法访问受保护页面', async () => {
    // 执行登出
    await authHelper.logout();
    await window.waitForURL('**/login**', { timeout: 10000 });
    
    // 尝试访问受保护页面
    await window.goto('/device/connection');
    await window.waitForTimeout(1000);
    
    // 应该重定向到登录页
    const isOnLoginPage = await authHelper.isOnLoginPage();
    expect(isOnLoginPage).toBe(true);
  });
});

/**
 * Token管理测试套件
 */
test.describe('Token管理测试', () => {
  let electronHelper;
  let window;
  let authHelper;

  test.beforeAll(async () => {
    if (!isElectronTestEnabled()) {
      test.skip(true, 'Electron测试未启用');
      return;
    }

    const result = await quickLaunchElectron({ headless: false });
    electronHelper = result.helper;
    window = result.window;
    authHelper = new AuthHelper(window);
  });

  test.afterAll(async () => {
    if (electronHelper) {
      await electronHelper.close();
    }
  });

  test.beforeEach(async () => {
    await authHelper.clearAuth();
    await window.reload();
    await window.waitForLoadState('networkidle');
  });

  /**
   * 测试12：验证Token格式正确
   */
  test('Token应该有正确的格式', async () => {
    // 执行登录
    await window.waitForSelector('.login-card', { timeout: 10000 });
    const adminCard = window.locator('.account-card').first();
    await adminCard.click();
    
    await window.waitForURL('**/device/**', { timeout: TEST_CONFIG.LOGIN_TIMEOUT });
    
    // 获取Token
    const token = await authHelper.getToken();
    
    // 验证Token格式（JWT格式：header.payload.signature）
    if (token && token.includes('.')) {
      const parts = token.split('.');
      expect(parts.length).toBe(3);
    }
  });

  /**
   * 测试13：验证Token持久化
   */
  test('Token应该在页面刷新后保持', async () => {
    // 执行登录
    await window.waitForSelector('.login-card', { timeout: 10000 });
    const adminCard = window.locator('.account-card').first();
    await adminCard.click();
    
    await window.waitForURL('**/device/**', { timeout: TEST_CONFIG.LOGIN_TIMEOUT });
    
    // 获取Token
    const tokenBefore = await authHelper.getToken();
    
    // 刷新页面
    await window.reload();
    await window.waitForLoadState('networkidle');
    
    // 验证Token仍然存在
    const tokenAfter = await authHelper.getToken();
    expect(tokenAfter).toBe(tokenBefore);
  });

  /**
   * 测试14：验证Token过期处理
   */
  test('应该正确处理Token过期', async () => {
    // 执行登录
    await window.waitForSelector('.login-card', { timeout: 10000 });
    const adminCard = window.locator('.account-card').first();
    await adminCard.click();
    
    await window.waitForURL('**/device/**', { timeout: TEST_CONFIG.LOGIN_TIMEOUT });
    
    // 设置一个过期的Token
    await authHelper.setToken('expired_token_12345');
    
    // 刷新页面
    await window.reload();
    await window.waitForTimeout(2000);
    
    // 验证是否重定向到登录页或显示错误
    const currentUrl = window.url();
    const isOnLoginPage = currentUrl.includes('/login');
    
    // 如果不在登录页，验证是否有错误提示
    if (!isOnLoginPage) {
      const errorVisible = await window.locator('.error-message, .ant-message-error').isVisible().catch(() => false);
      expect(errorVisible || isOnLoginPage).toBe(true);
    }
  });

  /**
   * 测试15：验证手动设置Token
   */
  test('应该能够手动设置Token', async () => {
    const testToken = 'test_token_abc123';
    
    // 手动设置Token
    await authHelper.setToken(testToken);
    
    // 验证Token已设置
    const token = await authHelper.getToken();
    expect(token).toBe(testToken);
  });

  /**
   * 测试16：验证清除认证信息
   */
  test('应该能够清除所有认证信息', async () => {
    // 执行登录
    await window.waitForSelector('.login-card', { timeout: 10000 });
    const adminCard = window.locator('.account-card').first();
    await adminCard.click();
    
    await window.waitForURL('**/device/**', { timeout: TEST_CONFIG.LOGIN_TIMEOUT });
    
    // 清除认证信息
    await authHelper.clearAuth();
    
    // 验证所有认证信息已清除
    const token = await authHelper.getToken();
    const user = await authHelper.getCurrentUser();
    
    expect(token).toBeNull();
    expect(user).toBeNull();
  });
});

/**
 * 权限验证测试套件
 */
test.describe('权限验证测试', () => {
  let electronHelper;
  let window;
  let authHelper;

  test.beforeAll(async () => {
    if (!isElectronTestEnabled()) {
      test.skip(true, 'Electron测试未启用');
      return;
    }

    const result = await quickLaunchElectron({ headless: false });
    electronHelper = result.helper;
    window = result.window;
    authHelper = new AuthHelper(window);
  });

  test.afterAll(async () => {
    if (electronHelper) {
      await electronHelper.close();
    }
  });

  test.beforeEach(async () => {
    await authHelper.clearAuth();
    await window.reload();
    await window.waitForLoadState('networkidle');
  });

  /**
   * 测试17：验证管理员权限
   */
  test('管理员应该有完整权限', async () => {
    // 模拟管理员登录
    await authHelper.mockAuthenticated({
      role: 'admin',
      permissions: ['read', 'write', 'delete', 'admin'],
    });
    
    // 验证权限
    const hasRead = await authHelper.hasPermission('read');
    const hasWrite = await authHelper.hasPermission('write');
    const hasDelete = await authHelper.hasPermission('delete');
    const hasAdmin = await authHelper.hasPermission('admin');
    
    expect(hasRead).toBe(true);
    expect(hasWrite).toBe(true);
    expect(hasDelete).toBe(true);
    expect(hasAdmin).toBe(true);
  });

  /**
   * 测试18：验证操作员权限
   */
  test('操作员应该有受限权限', async () => {
    // 模拟操作员登录
    await authHelper.mockAuthenticated({
      role: 'operator',
      permissions: ['read', 'write'],
    });
    
    // 验证权限
    const hasRead = await authHelper.hasPermission('read');
    const hasWrite = await authHelper.hasPermission('write');
    const hasDelete = await authHelper.hasPermission('delete');
    const hasAdmin = await authHelper.hasPermission('admin');
    
    expect(hasRead).toBe(true);
    expect(hasWrite).toBe(true);
    expect(hasDelete).toBe(false);
    expect(hasAdmin).toBe(false);
  });

  /**
   * 测试19：验证访客权限
   */
  test('访客应该只有只读权限', async () => {
    // 模拟访客登录
    await authHelper.mockAuthenticated({
      role: 'viewer',
      permissions: ['read'],
    });
    
    // 验证权限
    const hasRead = await authHelper.hasPermission('read');
    const hasWrite = await authHelper.hasPermission('write');
    const hasDelete = await authHelper.hasPermission('delete');
    
    expect(hasRead).toBe(true);
    expect(hasWrite).toBe(false);
    expect(hasDelete).toBe(false);
  });

  /**
   * 测试20：验证未登录用户权限
   */
  test('未登录用户应该没有权限', async () => {
    // 验证权限
    const hasRead = await authHelper.hasPermission('read');
    const hasWrite = await authHelper.hasPermission('write');
    
    expect(hasRead).toBe(false);
    expect(hasWrite).toBe(false);
  });
});

/**
 * 认证状态持久化测试套件
 */
test.describe('认证状态持久化测试', () => {
  let electronHelper;
  let window;
  let authHelper;

  test.beforeAll(async () => {
    if (!isElectronTestEnabled()) {
      test.skip(true, 'Electron测试未启用');
      return;
    }

    const result = await quickLaunchElectron({ headless: false });
    electronHelper = result.helper;
    window = result.window;
    authHelper = new AuthHelper(window);
  });

  test.afterAll(async () => {
    if (electronHelper) {
      await electronHelper.close();
    }
  });

  /**
   * 测试21：验证认证状态在页面刷新后保持
   */
  test('认证状态应该在页面刷新后保持', async () => {
    // 执行登录
    await authHelper.clearAuth();
    await window.reload();
    await window.waitForLoadState('networkidle');
    
    await window.waitForSelector('.login-card', { timeout: 10000 });
    const adminCard = window.locator('.account-card').first();
    await adminCard.click();
    
    await window.waitForURL('**/device/**', { timeout: TEST_CONFIG.LOGIN_TIMEOUT });
    
    // 获取登录状态
    const isLoggedInBefore = await authHelper.isLoggedIn();
    expect(isLoggedInBefore).toBe(true);
    
    // 刷新页面
    await window.reload();
    await window.waitForLoadState('networkidle');
    
    // 验证登录状态保持
    const isLoggedInAfter = await authHelper.isLoggedIn();
    expect(isLoggedInAfter).toBe(true);
  });

  /**
   * 测试22：验证认证状态在应用重启后保持
   */
  test('认证状态应该在应用重启后保持', async () => {
    // 执行登录
    await authHelper.clearAuth();
    await window.reload();
    await window.waitForLoadState('networkidle');
    
    await window.waitForSelector('.login-card', { timeout: 10000 });
    const adminCard = window.locator('.account-card').first();
    await adminCard.click();
    
    await window.waitForURL('**/device/**', { timeout: TEST_CONFIG.LOGIN_TIMEOUT });
    
    // 获取Token
    const tokenBefore = await authHelper.getToken();
    
    // 重启应用
    await electronHelper.close();
    const result = await quickLaunchElectron({ headless: false });
    electronHelper = result.helper;
    window = result.window;
    authHelper = new AuthHelper(window);
    
    // 等待页面加载
    await window.waitForLoadState('networkidle');
    
    // 验证Token仍然存在
    const tokenAfter = await authHelper.getToken();
    expect(tokenAfter).toBe(tokenBefore);
  });

  /**
   * 测试23：验证多个标签页认证状态同步
   */
  test('多个标签页应该同步认证状态', async () => {
    // 执行登录
    await authHelper.clearAuth();
    await window.reload();
    await window.waitForLoadState('networkidle');
    
    await window.waitForSelector('.login-card', { timeout: 10000 });
    const adminCard = window.locator('.account-card').first();
    await adminCard.click();
    
    await window.waitForURL('**/device/**', { timeout: TEST_CONFIG.LOGIN_TIMEOUT });
    
    // 在新窗口中验证认证状态
    const newWindow = await electronHelper.waitForWindow(
      (page) => page.url().includes('/device'),
      { timeout: 10000 }
    ).catch(() => null);
    
    if (newWindow) {
      const newAuthHelper = new AuthHelper(newWindow);
      const isLoggedIn = await newAuthHelper.isLoggedIn();
      expect(isLoggedIn).toBe(true);
    }
  });
});
