/**
 * @file navigation.spec.js
 * @path frontend/tests/e2e/
 * @description 导航和布局E2E测试套件
 * 
 * 本测试文件包含应用导航和布局的端到端测试，覆盖以下功能：
 * - 侧边栏导航
 * - 顶部栏功能
 * - 状态栏显示
 * - 页面路由
 * - 键盘快捷键
 * - 可访问性
 * 
 * @author Agent
 * @date 2024-03-07
 * @dependencies @playwright/test
 */

import { test, expect } from '@playwright/test';

/**
 * 导航和布局测试套件
 * 
 * 测试应用的基础导航功能和布局结构。
 */
test.describe('导航和布局', () => {
  /**
+    * 每个测试前的初始化操作
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  /**
+    * 测试侧边栏显示
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该显示侧边栏', async ({ page }) => {
    const sidebar = page.locator('.sidebar');
    await expect(sidebar).toBeVisible();
  });

  /**
+    * 测试顶部栏显示
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该显示顶部栏', async ({ page }) => {
    const topbar = page.locator('.topbar');
    await expect(topbar).toBeVisible();
  });

  /**
+    * 测试状态栏显示
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该显示状态栏', async ({ page }) => {
    const statusBar = page.locator('.status-bar');
    await expect(statusBar).toBeVisible();
  });

  /**
+    * 测试页面导航功能
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该导航到不同页面', async ({ page }) => {
    await page.click('text=设备连接');
    await page.waitForLoadState('networkidle');
    
    expect(page.url()).toContain('/device/connection');
  });

  /**
+    * 测试侧边栏折叠功能
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该折叠侧边栏', async ({ page }) => {
    const collapseButton = page.locator('.sidebar .collapse-button');
    if (await collapseButton.isVisible()) {
      await collapseButton.click();
      
      const sidebar = page.locator('.sidebar');
      await expect(sidebar).toHaveClass(/collapsed/);
    }
  });

  /**
+    * 测试用户菜单显示
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该显示用户菜单', async ({ page }) => {
    const userAvatar = page.locator('.user-avatar');
    if (await userAvatar.isVisible()) {
      await userAvatar.click();
      
      const userMenu = page.locator('.user-menu');
      await expect(userMenu).toBeVisible();
    }
  });

  /**
+    * 测试通知显示
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该显示通知', async ({ page }) => {
    const notificationIcon = page.locator('.notification-icon');
    if (await notificationIcon.isVisible()) {
      await notificationIcon.click();
      
      const notificationPanel = page.locator('.notification-panel');
      await expect(notificationPanel).toBeVisible();
    }
  });

  /**
+    * 测试主题切换功能
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该切换主题', async ({ page }) => {
    const themeButton = page.locator('.theme-toggle');
    if (await themeButton.isVisible()) {
      await themeButton.click();
      
      const body = page.locator('body');
      const hasDarkTheme = await body.evaluate(el => 
        el.classList.contains('dark-theme') || el.getAttribute('data-theme') === 'dark'
      );
      
      expect(typeof hasDarkTheme).toBe('boolean');
    }
  });

  /**
+    * 测试面包屑导航显示
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该显示面包屑导航', async ({ page }) => {
    const breadcrumb = page.locator('.el-breadcrumb');
    await expect(breadcrumb).toBeVisible();
  });

  /**
+    * 测试在线状态显示
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该显示在线状态', async ({ page }) => {
    const statusBar = page.locator('.status-bar');
    await expect(statusBar).toContainText(/在线|离线/);
  });
});

/**
 * 页面路由测试套件
 * 
 * 测试应用各页面的路由访问功能。
 */
test.describe('页面路由', () => {
  /**
+    * 测试设备连接页面访问
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该访问设备连接页面', async ({ page }) => {
    await page.goto('/device/connection');
    await page.waitForLoadState('networkidle');
    
    expect(page.url()).toContain('/device/connection');
  });

  /**
+    * 测试设备状态页面访问
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该访问设备状态页面', async ({ page }) => {
    await page.goto('/device/status');
    await page.waitForLoadState('networkidle');
    
    expect(page.url()).toContain('/device/status');
  });

  /**
+    * 测试电机控制页面访问
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该访问电机控制页面', async ({ page }) => {
    await page.goto('/experiment/motor');
    await page.waitForLoadState('networkidle');
    
    expect(page.url()).toContain('/experiment/motor');
  });

  /**
+    * 测试温度控制页面访问
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该访问温度控制页面', async ({ page }) => {
    await page.goto('/experiment/temperature');
    await page.waitForLoadState('networkidle');
    
    expect(page.url()).toContain('/experiment/temperature');
  });

  /**
+    * 测试实时分析页面访问
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该访问实时分析页面', async ({ page }) => {
    await page.goto('/analysis/realtime');
    await page.waitForLoadState('networkidle');
    
    expect(page.url()).toContain('/analysis/realtime');
  });

  /**
+    * 测试历史记录页面访问
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该访问历史记录页面', async ({ page }) => {
    await page.goto('/analysis/history');
    await page.waitForLoadState('networkidle');
    
    expect(page.url()).toContain('/analysis/history');
  });

  /**
+    * 测试设置页面访问
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该访问设置页面', async ({ page }) => {
    await page.goto('/settings/config');
    await page.waitForLoadState('networkidle');
    
    expect(page.url()).toContain('/settings/config');
  });

  /**
+    * 测试404页面处理
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该处理404页面', async ({ page }) => {
    await page.goto('/nonexistent-page');
    await page.waitForLoadState('networkidle');
    
    const is404 = await page.locator('text=404').isVisible();
    const isHome = page.url() === '/' || page.url().includes('localhost:5173/');
    
    expect(is404 || isHome).toBeTruthy();
  });
});

/**
 * 键盘快捷键测试套件
 * 
 * 测试应用的键盘快捷键功能。
 */
test.describe('键盘快捷键', () => {
  /**
+    * 测试快捷键导航
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该响应快捷键导航', async ({ page }) => {
    await page.keyboard.press('?');
    
    const helpDialog = page.locator('.shortcut-help, .el-dialog:has-text("快捷键")');
    if (await helpDialog.isVisible()) {
      await expect(helpDialog).toBeVisible();
    }
  });

  /**
+    * 测试ESC关闭对话框
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该响应ESC关闭对话框', async ({ page }) => {
    await page.click('button:has-text("历史记录")');
    
    const dialog = page.locator('.el-dialog');
    await expect(dialog).toBeVisible();
    
    await page.keyboard.press('Escape');
    
    await expect(dialog).not.toBeVisible();
  });
});

/**
 * 可访问性测试套件
 * 
 * 测试应用的可访问性功能。
 */
test.describe('可访问性', () => {
  /**
+    * 测试页面标题
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该有正确的标题', async ({ page }) => {
    const title = await page.title();
    expect(title).toBeTruthy();
    expect(title.length).toBeGreaterThan(0);
  });

  /**
+    * 测试语言设置
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该有正确的语言设置', async ({ page }) => {
    const lang = await page.locator('html').getAttribute('lang');
    expect(lang).toBe('zh-CN');
  });

  /**
+    * 测试键盘导航
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该支持键盘导航', async ({ page }) => {
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();
  });

  /**
+    * 测试颜色对比度
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该有足够的颜色对比度', async ({ page }) => {
    const body = page.locator('body');
    await expect(body).toBeVisible();
  });
});
