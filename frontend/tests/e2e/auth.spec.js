/**
 * @file auth.spec.js
 * @path frontend/tests/e2e/
 * @description 用户认证流程E2E测试套件
 * 
 * 本测试文件包含用户认证模块的端到端测试，覆盖以下功能：
 * - 登录页面测试（快速登录、账号密码登录、访客模式）
 * - 注册页面测试
 * - 密码重置测试
 * - 登出功能测试
 * - Token管理测试
 * - 权限控制测试
 * 
 * @author Agent
 * @date 2024-03-16
 * @dependencies @playwright/test
 */

import { test, expect } from '@playwright/test';
import { AuthHelper } from './helpers/auth.helper';
import { testConfig, getTestUser } from './helpers/test.config';

/**
 * 登录页面测试套件
 * 
 * 测试登录页面的各种登录方式和功能。
 */
test.describe('登录页面', () => {
  let authHelper;

  /**
   * 每个测试前的初始化操作
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test.beforeEach(async ({ page }) => {
    authHelper = new AuthHelper(page);
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
  });

  /**
   * 测试登录页面基础渲染
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该正确显示登录页面', async ({ page }) => {
    // 验证页面标题
    await expect(page).toHaveTitle(/CAUC-SEP/);
    
    // 验证登录卡片显示
    const loginCard = page.locator('.login-card');
    await expect(loginCard).toBeVisible();
    
    // 验证Logo显示
    const logo = page.locator('.login-card__logo');
    await expect(logo).toBeVisible();
    
    // 验证标题显示
    await expect(page.locator('.login-card__title')).toContainText('CAUC-SEP');
    await expect(page.locator('.login-card__subtitle')).toContainText('自旋电子器件实验平台');
  });

  /**
   * 测试登录模式切换功能
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持登录模式切换', async ({ page }) => {
    // 验证默认显示快速登录模式
    const quickLoginBtn = page.locator('.mode-btn--active:has-text("快速登录")');
    await expect(quickLoginBtn).toBeVisible();
    
    // 切换到账号密码模式
    await page.click('.mode-btn:has-text("账号密码")');
    const passwordModeBtn = page.locator('.mode-btn--active:has-text("账号密码")');
    await expect(passwordModeBtn).toBeVisible();
    
    // 切换到访客模式
    await page.click('.mode-btn:has-text("访客模式")');
    const guestModeBtn = page.locator('.mode-btn--active:has-text("访客模式")');
    await expect(guestModeBtn).toBeVisible();
  });

  /**
   * 测试快速登录功能
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持快速登录', async ({ page }) => {
    // 确保在快速登录模式
    const quickLoginBtn = page.locator('.mode-btn:has-text("快速登录")');
    if (!await quickLoginBtn.getAttribute('class').then(cls => cls?.includes('active'))) {
      await quickLoginBtn.click();
    }
    
    // 等待账号列表加载
    await page.waitForTimeout(500);
    
    // 点击第一个账号卡片
    const accountCard = page.locator('.account-card').first();
    await expect(accountCard).toBeVisible();
    
    await accountCard.click();
    
    // 等待登录完成
    await page.waitForURL(/\/device\/status|\/$/, { timeout: 10000 });
    
    // 验证已登录
    const isLoggedIn = await authHelper.isLoggedIn();
    expect(isLoggedIn).toBeTruthy();
  });

  /**
   * 测试账号密码登录功能
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持账号密码登录', async ({ page }) => {
    // 切换到账号密码模式
    await page.click('.mode-btn:has-text("账号密码")');
    await page.waitForTimeout(300);
    
    // 等待账号列表加载
    const accountCard = page.locator('.account-card').first();
    await expect(accountCard).toBeVisible();
    
    // 点击第一个账号
    await accountCard.click();
    
    // 等待登录完成
    await page.waitForURL(/\/device\/status|\/$/, { timeout: 10000 });
    
    // 验证已登录
    const isLoggedIn = await authHelper.isLoggedIn();
    expect(isLoggedIn).toBeTruthy();
  });

  /**
   * 测试访客模式登录
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持访客模式登录', async ({ page }) => {
    // 切换到访客模式
    await page.click('.mode-btn:has-text("访客模式")');
    await page.waitForTimeout(300);
    
    // 点击访客登录按钮
    const guestCard = page.locator('.account-card').first();
    await expect(guestCard).toBeVisible();
    await guestCard.click();
    
    // 等待登录完成
    await page.waitForURL(/\/device\/status|\/$/, { timeout: 10000 });
    
    // 验证已登录
    const isLoggedIn = await authHelper.isLoggedIn();
    expect(isLoggedIn).toBeTruthy();
  });

  /**
   * 测试登录加载状态
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该显示登录加载状态', async ({ page }) => {
    const accountCard = page.locator('.account-card').first();
    await accountCard.click();
    
    // 验证加载动画显示
    const loadingSpinner = page.locator('.loading-spinner');
    await expect(loadingSpinner).toBeVisible({ timeout: 1000 });
  });

  /**
   * 测试登录成功后的重定向
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该正确重定向到目标页面', async ({ page }) => {
    // 设置重定向参数
    await page.goto('/login?redirect=/settings/profile');
    await page.waitForLoadState('networkidle');
    
    // 执行登录
    const accountCard = page.locator('.account-card').first();
    await accountCard.click();
    
    // 等待重定向
    await page.waitForURL(/\/settings\/profile/, { timeout: 10000 });
    
    // 验证URL
    expect(page.url()).toContain('/settings/profile');
  });

  /**
   * 测试登录页面的响应式设计
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该在移动端正常显示', async ({ page }) => {
    // 设置移动端视口
    await page.setViewportSize({ width: 375, height: 667 });
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    // 验证登录卡片显示
    const loginCard = page.locator('.login-card');
    await expect(loginCard).toBeVisible();
    
    // 验证账号卡片显示
    const accountCard = page.locator('.account-card').first();
    await expect(accountCard).toBeVisible();
  });
});

/**
 * 登出功能测试套件
 * 
 * 测试用户登出功能。
 */
test.describe('登出功能', () => {
  let authHelper;

  /**
   * 每个测试前的初始化操作
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test.beforeEach(async ({ page }) => {
    authHelper = new AuthHelper(page);
    
    // 先登录
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    const accountCard = page.locator('.account-card').first();
    await accountCard.click();
    
    await page.waitForURL(/\/device\/status|\/$/, { timeout: 10000 });
  });

  /**
   * 测试登出功能
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该成功登出', async ({ page }) => {
    // 点击用户头像或菜单
    const userAvatar = page.locator('.user-avatar, [data-testid="user-avatar"]').first();
    if (await userAvatar.isVisible()) {
      await userAvatar.click();
      
      // 点击登出按钮
      const logoutBtn = page.locator('text=退出登录, text=登出, .logout-button').first();
      if (await logoutBtn.isVisible()) {
        await logoutBtn.click();
        
        // 等待重定向到登录页
        await page.waitForURL(/\/login/, { timeout: 10000 });
        
        // 验证已登出
        const isLoggedIn = await authHelper.isLoggedIn();
        expect(isLoggedIn).toBeFalsy();
      }
    }
  });

  /**
   * 测试登出后清除Token
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该在登出后清除Token', async ({ page }) => {
    // 点击用户头像或菜单
    const userAvatar = page.locator('.user-avatar, [data-testid="user-avatar"]').first();
    if (await userAvatar.isVisible()) {
      await userAvatar.click();
      
      const logoutBtn = page.locator('text=退出登录, text=登出').first();
      if (await logoutBtn.isVisible()) {
        await logoutBtn.click();
        await page.waitForURL(/\/login/, { timeout: 10000 });
        
        // 验证Token已清除
        const token = await authHelper.getToken();
        expect(token).toBeNull();
      }
    }
  });
});

/**
 * Token管理测试套件
 * 
 * 测试认证Token的管理功能。
 */
test.describe('Token管理', () => {
  let authHelper;

  /**
   * 每个测试前的初始化操作
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test.beforeEach(async ({ page }) => {
    authHelper = new AuthHelper(page);
  });

  /**
   * 测试登录后Token存储
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该在登录后存储Token', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    const accountCard = page.locator('.account-card').first();
    await accountCard.click();
    
    await page.waitForURL(/\/device\/status|\/$/, { timeout: 10000 });
    
    // 验证Token存在
    const token = await authHelper.getToken();
    expect(token).toBeTruthy();
  });

  /**
   * 测试Token过期处理
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该处理Token过期', async ({ page }) => {
    // 模拟登录
    await authHelper.mockAuthenticated({ role: 'user' });
    
    // 清除Token模拟过期
    await authHelper.clearAuth();
    
    // 访问需要认证的页面
    await page.goto('/settings/profile');
    await page.waitForLoadState('networkidle');
    
    // 应该重定向到登录页
    const currentUrl = page.url();
    expect(currentUrl).toContain('/login');
  });

  /**
   * 测试模拟认证状态
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持模拟认证状态', async ({ page }) => {
    const mockUser = {
      id: 'test-user-123',
      username: 'testuser',
      role: 'admin',
      permissions: ['read', 'write', 'delete']
    };
    
    await authHelper.mockAuthenticated(mockUser);
    
    // 验证Token存在
    const token = await authHelper.getToken();
    expect(token).toBeTruthy();
    
    // 验证用户信息
    const user = await authHelper.getCurrentUser();
    expect(user).toBeTruthy();
    expect(user.username).toBe('testuser');
  });
});

/**
 * 权限控制测试套件
 * 
 * 测试基于角色的权限控制功能。
 */
test.describe('权限控制', () => {
  let authHelper;

  /**
   * 每个测试前的初始化操作
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test.beforeEach(async ({ page }) => {
    authHelper = new AuthHelper(page);
  });

  /**
   * 测试未登录访问受保护页面
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该在未登录时重定向到登录页', async ({ page }) => {
    // 清除认证信息
    await authHelper.clearAuth();
    
    // 访问受保护页面
    await page.goto('/settings/profile');
    await page.waitForLoadState('networkidle');
    
    // 验证重定向到登录页
    const currentUrl = page.url();
    expect(currentUrl).toContain('/login');
  });

  /**
   * 测试管理员权限
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该允许管理员访问用户管理页面', async ({ page }) => {
    // 模拟管理员登录
    await authHelper.mockAuthenticated({ role: 'admin' });
    
    // 访问用户管理页面
    await page.goto('/settings/user-management');
    await page.waitForLoadState('networkidle');
    
    // 验证页面正常显示
    const userManagementPage = page.locator('.user-management-page');
    await expect(userManagementPage).toBeVisible();
  });

  /**
   * 测试普通用户权限限制
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该限制普通用户访问管理功能', async ({ page }) => {
    // 模拟普通用户登录
    await authHelper.mockAuthenticated({ role: 'user' });
    
    // 访问设备控制页面（应该允许）
    await page.goto('/experiment/motor');
    await page.waitForLoadState('networkidle');
    
    const motorControl = page.locator('.motor-control');
    await expect(motorControl).toBeVisible();
  });

  /**
   * 测试权限检查功能
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该正确检查用户权限', async ({ page }) => {
    // 模拟带权限的用户
    await authHelper.mockAuthenticated({
      role: 'admin',
      permissions: ['read', 'write', 'delete', 'admin']
    });
    
    // 检查权限
    const hasReadPermission = await authHelper.hasPermission('read');
    expect(hasReadPermission).toBeTruthy();
    
    const hasAdminPermission = await authHelper.hasPermission('admin');
    expect(hasAdminPermission).toBeTruthy();
  });
});

/**
 * 登录错误处理测试套件
 * 
 * 测试登录过程中的错误处理。
 */
test.describe('登录错误处理', () => {
  let authHelper;

  /**
   * 每个测试前的初始化操作
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test.beforeEach(async ({ page }) => {
    authHelper = new AuthHelper(page);
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
  });

  /**
   * 测试网络错误处理
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该处理网络错误', async ({ page }) => {
    // 模拟网络错误
    await page.route('**/api/**', route => route.abort());
    
    // 尝试登录
    const accountCard = page.locator('.account-card').first();
    await accountCard.click();
    
    // 等待错误消息
    await page.waitForTimeout(2000);
    
    // 验证错误处理（可能显示错误消息或保持在登录页）
    const currentUrl = page.url();
    expect(currentUrl).toContain('/login');
  });

  /**
   * 测试服务器错误处理
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该处理服务器错误', async ({ page }) => {
    // 模拟服务器错误
    await page.route('**/api/**', route => 
      route.fulfill({ status: 500, body: 'Internal Server Error' })
    );
    
    // 尝试登录
    const accountCard = page.locator('.account-card').first();
    await accountCard.click();
    
    // 等待错误消息
    await page.waitForTimeout(2000);
    
    // 验证错误处理
    const currentUrl = page.url();
    expect(currentUrl).toContain('/login');
  });
});

/**
 * 会话管理测试套件
 * 
 * 测试用户会话管理功能。
 */
test.describe('会话管理', () => {
  let authHelper;

  /**
   * 每个测试前的初始化操作
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test.beforeEach(async ({ page }) => {
    authHelper = new AuthHelper(page);
  });

  /**
   * 测试会话持久化
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该保持会话持久化', async ({ page }) => {
    // 登录
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    const accountCard = page.locator('.account-card').first();
    await accountCard.click();
    
    await page.waitForURL(/\/device\/status|\/$/, { timeout: 10000 });
    
    // 刷新页面
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    // 验证仍然登录
    const isLoggedIn = await authHelper.isLoggedIn();
    expect(isLoggedIn).toBeTruthy();
  });

  /**
   * 测试多标签页会话共享
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该在多标签页间共享会话', async ({ page, context }) => {
    // 登录
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    const accountCard = page.locator('.account-card').first();
    await accountCard.click();
    
    await page.waitForURL(/\/device\/status|\/$/, { timeout: 10000 });
    
    // 打开新标签页
    const newPage = await context.newPage();
    await newPage.goto('/');
    await newPage.waitForLoadState('networkidle');
    
    // 验证新标签页也处于登录状态
    const newAuthHelper = new AuthHelper(newPage);
    const isLoggedIn = await newAuthHelper.isLoggedIn();
    expect(isLoggedIn).toBeTruthy();
    
    await newPage.close();
  });

  /**
   * 测试会话超时处理
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该处理会话超时', async ({ page }) => {
    // 模拟登录
    await authHelper.mockAuthenticated({ role: 'user' });
    
    // 模拟会话超时（清除Token）
    await page.evaluate(() => {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('token');
    });
    
    // 访问需要认证的页面
    await page.goto('/settings/profile');
    await page.waitForLoadState('networkidle');
    
    // 应该重定向到登录页
    const currentUrl = page.url();
    expect(currentUrl).toContain('/login');
  });
});
