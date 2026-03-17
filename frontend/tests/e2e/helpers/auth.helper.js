/**
 * @file auth.helper.js
 * @path frontend/tests/e2e/helpers/
 * @description 认证测试辅助函数
 * 
 * 提供用户认证相关的测试辅助功能，包括：
 * - 用户登录/登出
 * - Token管理
 * - 权限验证
 * - 用户状态检查
 * 
 * @author Agent
 * @date 2024-03-16
 * @dependencies @playwright/test
 */

import { expect } from '@playwright/test';

/**
 * 认证测试辅助类
 * 
 * 封装用户认证相关的测试功能。
 * 
 * @example
 * const authHelper = new AuthHelper(page);
 * await authHelper.login('admin', 'password');
 * await authHelper.isLoggedIn();
 */
export class AuthHelper {
  /**
   * 构造函数
   * 
   * @param {Object} page - Playwright页面对象
   * @param {Object} options - 配置选项
   */
  constructor(page, options = {}) {
    this.page = page;
    this.options = {
      loginUrl: options.loginUrl || '/login',
      homeUrl: options.homeUrl || '/',
      usernameSelector: options.usernameSelector || 'input[name="username"]',
      passwordSelector: options.passwordSelector || 'input[name="password"]',
      submitSelector: options.submitSelector || 'button[type="submit"]',
      ...options,
    };
  }

  /**
   * 登录
   * 
   * @param {string} username - 用户名
   * @param {string} password - 密码
   * @param {Object} options - 登录选项
   * @returns {Promise<void>}
   * 
   * @example
   * await authHelper.login('admin', 'password123');
   */
  async login(username, password, options = {}) {
    const { waitForNavigation = true, timeout = 30000 } = options;

    // 导航到登录页面
    await this.page.goto(this.options.loginUrl);
    await this.page.waitForLoadState('networkidle');

    // 填写登录表单
    await this.page.fill(this.options.usernameSelector, username);
    await this.page.fill(this.options.passwordSelector, password);

    // 提交登录
    if (waitForNavigation) {
      await Promise.all([
        this.page.waitForNavigation({ timeout }),
        this.page.click(this.options.submitSelector),
      ]);
    } else {
      await this.page.click(this.options.submitSelector);
    }

    // 等待登录完成
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * 登出
   * 
   * @param {Object} options - 登出选项
   * @returns {Promise<void>}
   */
  async logout(options = {}) {
    const { logoutSelector = '.logout-button, [data-testid="logout"]' } = options;

    // 点击登出按钮
    const logoutButton = this.page.locator(logoutSelector);
    if (await logoutButton.isVisible()) {
      await logoutButton.click();
      await this.page.waitForLoadState('networkidle');
    }
  }

  /**
   * 检查是否已登录
   * 
   * @returns {Promise<boolean>} 是否已登录
   */
  async isLoggedIn() {
    try {
      // 检查是否在登录页面
      const currentUrl = this.page.url();
      if (currentUrl.includes('/login')) {
        return false;
      }

      // 检查是否有用户信息
      const userAvatar = this.page.locator('.user-avatar, [data-testid="user-avatar"]');
      const userMenu = this.page.locator('.user-menu, [data-testid="user-menu"]');
      
      const hasAvatar = await userAvatar.isVisible().catch(() => false);
      const hasMenu = await userMenu.isVisible().catch(() => false);

      return hasAvatar || hasMenu;
    } catch (error) {
      return false;
    }
  }

  /**
   * 获取认证Token
   * 
   * @returns {Promise<string|null>} Token字符串
   */
  async getToken() {
    // 从localStorage获取token
    const token = await this.page.evaluate(() => {
      return localStorage.getItem('token') || localStorage.getItem('access_token');
    });

    return token;
  }

  /**
   * 设置认证Token
   * 
   * @param {string} token - Token字符串
   * @returns {Promise<void>}
   */
  async setToken(token) {
    await this.page.evaluate((token) => {
      localStorage.setItem('token', token);
      localStorage.setItem('access_token', token);
    }, token);
  }

  /**
   * 清除认证信息
   * 
   * @returns {Promise<void>}
   */
  async clearAuth() {
    await this.page.evaluate(() => {
      localStorage.removeItem('token');
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      sessionStorage.clear();
    });
  }

  /**
   * 检查用户权限
   * 
   * @param {string} permission - 权限名称
   * @returns {Promise<boolean>} 是否有权限
   */
  async hasPermission(permission) {
    const hasPermission = await this.page.evaluate((permission) => {
      const userStr = localStorage.getItem('user');
      if (!userStr) return false;

      try {
        const user = JSON.parse(userStr);
        return user.permissions?.includes(permission) || false;
      } catch {
        return false;
      }
    }, permission);

    return hasPermission;
  }

  /**
   * 获取当前用户信息
   * 
   * @returns {Promise<Object|null>} 用户信息对象
   */
  async getCurrentUser() {
    const user = await this.page.evaluate(() => {
      const userStr = localStorage.getItem('user');
      if (!userStr) return null;

      try {
        return JSON.parse(userStr);
      } catch {
        return null;
      }
    });

    return user;
  }

  /**
   * 等待认证完成
   * 
   * @param {Object} options - 等待选项
   * @returns {Promise<void>}
   */
  async waitForAuth(options = {}) {
    const { timeout = 30000 } = options;

    await this.page.waitForFunction(() => {
      return localStorage.getItem('token') !== null || 
             localStorage.getItem('access_token') !== null;
    }, { timeout });
  }

  /**
   * 验证登录错误消息
   * 
   * @param {string} expectedMessage - 预期的错误消息
   * @returns {Promise<void>}
   */
  async verifyLoginError(expectedMessage) {
    const errorSelector = '.error-message, .el-message--error, [role="alert"]';
    const errorElement = this.page.locator(errorSelector);
    
    await expect(errorElement).toBeVisible();
    await expect(errorElement).toContainText(expectedMessage);
  }

  /**
   * 模拟已登录状态
   * 
   * @param {Object} user - 用户信息
   * @returns {Promise<void>}
   */
  async mockAuthenticated(user = {}) {
    const defaultUser = {
      id: 'test-user-id',
      username: 'testuser',
      role: 'admin',
      permissions: ['read', 'write', 'delete'],
      ...user,
    };

    await this.page.evaluate((user) => {
      localStorage.setItem('token', 'mock-token-12345');
      localStorage.setItem('access_token', 'mock-token-12345');
      localStorage.setItem('user', JSON.stringify(user));
    }, defaultUser);

    // 刷新页面以应用认证状态
    await this.page.reload();
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * 检查是否在登录页面
   * 
   * @returns {Promise<boolean>} 是否在登录页面
   */
  async isOnLoginPage() {
    const currentUrl = this.page.url();
    return currentUrl.includes('/login');
  }

  /**
   * 验证登录表单存在
   * 
   * @returns {Promise<void>}
   */
  async verifyLoginFormExists() {
    await expect(this.page.locator(this.options.usernameSelector)).toBeVisible();
    await expect(this.page.locator(this.options.passwordSelector)).toBeVisible();
    await expect(this.page.locator(this.options.submitSelector)).toBeVisible();
  }
}

/**
 * 创建认证helper实例
 * 
 * @param {Object} page - Playwright页面对象
 * @param {Object} options - 配置选项
 * @returns {AuthHelper} 认证helper实例
 */
export function createAuthHelper(page, options = {}) {
  return new AuthHelper(page, options);
}

/**
 * 快速登录辅助函数
 * 
 * @param {Object} page - Playwright页面对象
 * @param {string} username - 用户名
 * @param {string} password - 密码
 * @returns {Promise<AuthHelper>} 认证helper实例
 * 
 * @example
 * const authHelper = await quickLogin(page, 'admin', 'password');
 */
export async function quickLogin(page, username, password) {
  const authHelper = new AuthHelper(page);
  await authHelper.login(username, password);
  return authHelper;
}
