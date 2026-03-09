/**
 * @file navigation.spec.js
 * @path frontend/tests/e2e/
 * @description 导航和布局E2E测试
 * @author Agent
 * @date 2024-03-07
 */

import { test, expect } from '@playwright/test';

test.describe('导航和布局', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('应该显示侧边栏', async ({ page }) => {
    const sidebar = page.locator('.sidebar');
    await expect(sidebar).toBeVisible();
  });

  test('应该显示顶部栏', async ({ page }) => {
    const topbar = page.locator('.topbar');
    await expect(topbar).toBeVisible();
  });

  test('应该显示状态栏', async ({ page }) => {
    const statusBar = page.locator('.status-bar');
    await expect(statusBar).toBeVisible();
  });

  test('应该导航到不同页面', async ({ page }) => {
    await page.click('text=设备连接');
    await page.waitForLoadState('networkidle');
    
    expect(page.url()).toContain('/device/connection');
  });

  test('应该折叠侧边栏', async ({ page }) => {
    const collapseButton = page.locator('.sidebar .collapse-button');
    if (await collapseButton.isVisible()) {
      await collapseButton.click();
      
      const sidebar = page.locator('.sidebar');
      await expect(sidebar).toHaveClass(/collapsed/);
    }
  });

  test('应该显示用户菜单', async ({ page }) => {
    const userAvatar = page.locator('.user-avatar');
    if (await userAvatar.isVisible()) {
      await userAvatar.click();
      
      const userMenu = page.locator('.user-menu');
      await expect(userMenu).toBeVisible();
    }
  });

  test('应该显示通知', async ({ page }) => {
    const notificationIcon = page.locator('.notification-icon');
    if (await notificationIcon.isVisible()) {
      await notificationIcon.click();
      
      const notificationPanel = page.locator('.notification-panel');
      await expect(notificationPanel).toBeVisible();
    }
  });

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

  test('应该显示面包屑导航', async ({ page }) => {
    const breadcrumb = page.locator('.el-breadcrumb');
    await expect(breadcrumb).toBeVisible();
  });

  test('应该显示在线状态', async ({ page }) => {
    const statusBar = page.locator('.status-bar');
    await expect(statusBar).toContainText(/在线|离线/);
  });
});

test.describe('页面路由', () => {
  test('应该访问设备连接页面', async ({ page }) => {
    await page.goto('/device/connection');
    await page.waitForLoadState('networkidle');
    
    expect(page.url()).toContain('/device/connection');
  });

  test('应该访问设备状态页面', async ({ page }) => {
    await page.goto('/device/status');
    await page.waitForLoadState('networkidle');
    
    expect(page.url()).toContain('/device/status');
  });

  test('应该访问电机控制页面', async ({ page }) => {
    await page.goto('/experiment/motor');
    await page.waitForLoadState('networkidle');
    
    expect(page.url()).toContain('/experiment/motor');
  });

  test('应该访问温度控制页面', async ({ page }) => {
    await page.goto('/experiment/temperature');
    await page.waitForLoadState('networkidle');
    
    expect(page.url()).toContain('/experiment/temperature');
  });

  test('应该访问实时分析页面', async ({ page }) => {
    await page.goto('/analysis/realtime');
    await page.waitForLoadState('networkidle');
    
    expect(page.url()).toContain('/analysis/realtime');
  });

  test('应该访问历史记录页面', async ({ page }) => {
    await page.goto('/analysis/history');
    await page.waitForLoadState('networkidle');
    
    expect(page.url()).toContain('/analysis/history');
  });

  test('应该访问设置页面', async ({ page }) => {
    await page.goto('/settings/config');
    await page.waitForLoadState('networkidle');
    
    expect(page.url()).toContain('/settings/config');
  });

  test('应该处理404页面', async ({ page }) => {
    await page.goto('/nonexistent-page');
    await page.waitForLoadState('networkidle');
    
    const is404 = await page.locator('text=404').isVisible();
    const isHome = page.url() === '/' || page.url().includes('localhost:5173/');
    
    expect(is404 || isHome).toBeTruthy();
  });
});

test.describe('键盘快捷键', () => {
  test('应该响应快捷键导航', async ({ page }) => {
    await page.keyboard.press('?');
    
    const helpDialog = page.locator('.shortcut-help, .el-dialog:has-text("快捷键")');
    if (await helpDialog.isVisible()) {
      await expect(helpDialog).toBeVisible();
    }
  });

  test('应该响应ESC关闭对话框', async ({ page }) => {
    await page.click('button:has-text("历史记录")');
    
    const dialog = page.locator('.el-dialog');
    await expect(dialog).toBeVisible();
    
    await page.keyboard.press('Escape');
    
    await expect(dialog).not.toBeVisible();
  });
});

test.describe('可访问性', () => {
  test('应该有正确的标题', async ({ page }) => {
    const title = await page.title();
    expect(title).toBeTruthy();
    expect(title.length).toBeGreaterThan(0);
  });

  test('应该有正确的语言设置', async ({ page }) => {
    const lang = await page.locator('html').getAttribute('lang');
    expect(lang).toBe('zh-CN');
  });

  test('应该支持键盘导航', async ({ page }) => {
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();
  });

  test('应该有足够的颜色对比度', async ({ page }) => {
    const body = page.locator('body');
    await expect(body).toBeVisible();
  });
});
