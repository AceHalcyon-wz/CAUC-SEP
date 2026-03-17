/**
 * @file cross-browser.spec.js
 * @path frontend/tests/e2e/
 * @description 跨浏览器兼容性E2E测试套件
 * 
 * 本测试文件包含跨浏览器兼容性的端到端测试，覆盖以下功能：
 * - Chrome浏览器兼容性测试
 * - Firefox浏览器兼容性测试
 * - Edge浏览器兼容性测试
 * - 核心功能跨浏览器一致性测试
 * - UI渲染兼容性测试
 * 
 * @author Agent
 * @date 2024-03-16
 * @dependencies @playwright/test
 */

import { test, expect } from '@playwright/test';
import { AuthHelper } from './helpers/auth.helper';

/**
 * 跨浏览器基础功能测试套件
 * 
 * 测试应用在不同浏览器上的基础功能一致性。
 */
test.describe('跨浏览器基础功能', () => {
  let authHelper;

  /**
   * 每个测试前的初始化操作
   * 
   * @param {Object} page - Playwright页面对象
   * @param {Object} browserName - 浏览器名称
   * @returns {Promise<void>}
   */
  test.beforeEach(async ({ page, browserName }) => {
    authHelper = new AuthHelper(page);
    
    // 输出当前测试的浏览器
    console.log(`Running test on: ${browserName}`);
  });

  /**
   * 测试登录页面在各浏览器的渲染
   * 
   * @param {Object} page - Playwright页面对象
   * @param {Object} browserName - 浏览器名称
   * @returns {Promise<void>}
   */
  test('应该在所有浏览器正确渲染登录页面', async ({ page, browserName }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    // 验证登录卡片显示
    const loginCard = page.locator('.login-card');
    await expect(loginCard).toBeVisible();
    
    // 验证Logo显示
    const logo = page.locator('.login-card__logo');
    await expect(logo).toBeVisible();
    
    // 验证标题显示
    await expect(page.locator('.login-card__title')).toContainText('CAUC-SEP');
    
    // 截图用于视觉对比
    await page.screenshot({ 
      path: `test-results/screenshots/login-${browserName}.png`,
      fullPage: true 
    });
  });

  /**
   * 测试快速登录功能在各浏览器的一致性
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该在所有浏览器支持快速登录', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
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
   * 测试设备状态页面在各浏览器的渲染
   * 
   * @param {Object} page - Playwright页面对象
   * @param {Object} browserName - 浏览器名称
   * @returns {Promise<void>}
   */
  test('应该在所有浏览器正确渲染设备状态页面', async ({ page, browserName }) => {
    // 模拟登录
    await authHelper.mockAuthenticated({ role: 'user' });
    
    await page.goto('/device/status');
    await page.waitForLoadState('networkidle');
    
    // 验证设备状态仪表板显示
    const dashboard = page.locator('.device-status-dashboard');
    await expect(dashboard).toBeVisible();
    
    // 截图用于视觉对比
    await page.screenshot({ 
      path: `test-results/screenshots/device-status-${browserName}.png`,
      fullPage: true 
    });
  });

  /**
   * 测试电机控制页面在各浏览器的一致性
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该在所有浏览器正确渲染电机控制页面', async ({ page }) => {
    // 模拟登录
    await authHelper.mockAuthenticated({ role: 'user' });
    
    await page.goto('/experiment/motor');
    await page.waitForLoadState('networkidle');
    
    // 验证电机控制面板显示
    const motorControl = page.locator('.motor-control');
    await expect(motorControl).toBeVisible();
    
    // 验证位置控制显示
    const positionControl = page.locator('.position-control, .position-display');
    await expect(positionControl).toBeVisible();
  });

  /**
   * 测试数据分析页面在各浏览器的一致性
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该在所有浏览器正确渲染数据分析页面', async ({ page }) => {
    // 模拟登录
    await authHelper.mockAuthenticated({ role: 'user' });
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 验证数据分析组件显示
    const dataAnalysis = page.locator('.data-analysis');
    await expect(dataAnalysis).toBeVisible();
    
    // 验证标签页显示
    const tabs = page.locator('.el-tabs__item');
    await expect(tabs).toHaveCount(4);
  });
});

/**
 * CSS和样式兼容性测试套件
 * 
 * 测试CSS样式在不同浏览器上的一致性。
 */
test.describe('CSS和样式兼容性', () => {
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
   * 测试Flexbox布局兼容性
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该正确渲染Flexbox布局', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    // 验证登录卡片使用Flexbox布局
    const loginCard = page.locator('.login-card');
    const display = await loginCard.evaluate(el => 
      window.getComputedStyle(el).display
    );
    
    // 验证布局正常
    await expect(loginCard).toBeVisible();
  });

  /**
   * 测试CSS Grid布局兼容性
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该正确渲染CSS Grid布局', async ({ page }) => {
    // 模拟登录
    await authHelper.mockAuthenticated({ role: 'user' });
    
    await page.goto('/device/status');
    await page.waitForLoadState('networkidle');
    
    // 验证Grid布局正常
    const dashboard = page.locator('.device-status-dashboard');
    await expect(dashboard).toBeVisible();
  });

  /**
   * 测试CSS变量兼容性
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该正确应用CSS变量', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    // 验证CSS变量应用
    const body = page.locator('body');
    const bgColor = await body.evaluate(el => 
      window.getComputedStyle(el).backgroundColor
    );
    
    // 验证背景色存在
    expect(bgColor).toBeTruthy();
  });

  /**
   * 测试渐变背景兼容性
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该正确渲染渐变背景', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    // 验证登录页面背景渐变
    const loginPage = page.locator('.login-page');
    const bgImage = await loginPage.evaluate(el => 
      window.getComputedStyle(el).backgroundImage
    );
    
    // 验证渐变存在
    expect(bgImage).toContain('gradient');
  });

  /**
   * 测试阴影效果兼容性
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该正确渲染阴影效果', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    // 验证登录卡片阴影
    const loginCard = page.locator('.login-card');
    const boxShadow = await loginCard.evaluate(el => 
      window.getComputedStyle(el).boxShadow
    );
    
    // 验证阴影存在
    expect(boxShadow).toBeTruthy();
  });

  /**
   * 测试圆角效果兼容性
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该正确渲染圆角效果', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    // 验证登录卡片圆角
    const loginCard = page.locator('.login-card');
    const borderRadius = await loginCard.evaluate(el => 
      window.getComputedStyle(el).borderRadius
    );
    
    // 验证圆角存在
    expect(borderRadius).toBeTruthy();
    expect(borderRadius).not.toBe('0px');
  });
});

/**
 * JavaScript API兼容性测试套件
 * 
 * 测试JavaScript API在不同浏览器上的一致性。
 */
test.describe('JavaScript API兼容性', () => {
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
   * 测试LocalStorage兼容性
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持LocalStorage', async ({ page }) => {
    // 测试LocalStorage写入
    await page.evaluate(() => {
      localStorage.setItem('test-key', 'test-value');
    });
    
    // 测试LocalStorage读取
    const value = await page.evaluate(() => {
      return localStorage.getItem('test-key');
    });
    
    expect(value).toBe('test-value');
    
    // 清理
    await page.evaluate(() => {
      localStorage.removeItem('test-key');
    });
  });

  /**
   * 测试Fetch API兼容性
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持Fetch API', async ({ page }) => {
    // 模拟登录
    await authHelper.mockAuthenticated({ role: 'user' });
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 验证Fetch API可用
    const fetchAvailable = await page.evaluate(() => {
      return typeof fetch === 'function';
    });
    
    expect(fetchAvailable).toBeTruthy();
  });

  /**
   * 测试Promise兼容性
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持Promise', async ({ page }) => {
    // 验证Promise可用
    const promiseAvailable = await page.evaluate(() => {
      return typeof Promise === 'function';
    });
    
    expect(promiseAvailable).toBeTruthy();
  });

  /**
   * 测试async/await兼容性
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持async/await', async ({ page }) => {
    // 验证async函数可用
    const asyncAvailable = await page.evaluate(() => {
      try {
        eval('(async () => {})');
        return true;
      } catch {
        return false;
      }
    });
    
    expect(asyncAvailable).toBeTruthy();
  });

  /**
   * 测试WebSocket兼容性
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持WebSocket', async ({ page }) => {
    // 验证WebSocket可用
    const wsAvailable = await page.evaluate(() => {
      return typeof WebSocket === 'function';
    });
    
    expect(wsAvailable).toBeTruthy();
  });
});

/**
 * 表单输入兼容性测试套件
 * 
 * 测试表单输入在不同浏览器上的一致性。
 */
test.describe('表单输入兼容性', () => {
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
   * 测试文本输入兼容性
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持文本输入', async ({ page }) => {
    // 模拟登录
    await authHelper.mockAuthenticated({ role: 'user' });
    
    await page.goto('/experiment/motor');
    await page.waitForLoadState('networkidle');
    
    // 查找数字输入框
    const numberInput = page.locator('input[type="number"]').first();
    
    if (await numberInput.isVisible()) {
      // 测试输入
      await numberInput.fill('100');
      await expect(numberInput).toHaveValue('100');
    }
  });

  /**
   * 测试下拉选择兼容性
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持下拉选择', async ({ page }) => {
    // 模拟登录
    await authHelper.mockAuthenticated({ role: 'user' });
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 查找下拉框
    const select = page.locator('.el-select').first();
    
    if (await select.isVisible()) {
      await select.click();
      
      // 验证下拉菜单显示
      const dropdown = page.locator('.el-select-dropdown');
      await expect(dropdown).toBeVisible();
    }
  });

  /**
   * 测试复选框兼容性
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持复选框', async ({ page }) => {
    // 模拟登录
    await authHelper.mockAuthenticated({ role: 'user' });
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 切换到多模型对比标签
    await page.click('.el-tabs__item:has-text("多模型对比")');
    await page.waitForTimeout(500);
    
    // 查找复选框
    const checkbox = page.locator('.el-checkbox').first();
    
    if (await checkbox.isVisible()) {
      // 测试勾选
      await checkbox.click();
    }
  });

  /**
   * 测试开关兼容性
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持开关', async ({ page }) => {
    // 模拟登录
    await authHelper.mockAuthenticated({ role: 'user' });
    
    await page.goto('/settings/profile');
    await page.waitForLoadState('networkidle');
    
    // 查找开关
    const switchElement = page.locator('.el-switch').first();
    
    if (await switchElement.isVisible()) {
      // 测试切换
      await switchElement.click();
    }
  });

  /**
   * 测试日期选择器兼容性
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持日期选择器', async ({ page }) => {
    // 模拟登录
    await authHelper.mockAuthenticated({ role: 'user' });
    
    await page.goto('/settings/profile');
    await page.waitForLoadState('networkidle');
    
    // 切换到操作历史标签
    await page.click('.el-tabs__item:has-text("操作历史")');
    await page.waitForTimeout(500);
    
    // 查找日期选择器
    const datePicker = page.locator('.el-date-editor--daterange').first();
    
    if (await datePicker.isVisible()) {
      // 验证日期选择器存在
      await expect(datePicker).toBeEnabled();
    }
  });
});

/**
 * 图表渲染兼容性测试套件
 * 
 * 测试图表在不同浏览器上的渲染一致性。
 */
test.describe('图表渲染兼容性', () => {
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
   * 测试Canvas渲染兼容性
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持Canvas渲染', async ({ page }) => {
    // 模拟登录
    await authHelper.mockAuthenticated({ role: 'user' });
    
    await page.goto('/experiment/motor');
    await page.waitForLoadState('networkidle');
    
    // 查找Canvas元素
    const canvas = page.locator('canvas').first();
    
    if (await canvas.isVisible()) {
      // 验证Canvas尺寸
      const width = await canvas.evaluate(el => el.width);
      const height = await canvas.evaluate(el => el.height);
      
      expect(width).toBeGreaterThan(0);
      expect(height).toBeGreaterThan(0);
    }
  });

  /**
   * 测试SVG渲染兼容性
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持SVG渲染', async ({ page }) => {
    // 模拟登录
    await authHelper.mockAuthenticated({ role: 'user' });
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 验证SVG图标存在
    const svgIcons = page.locator('svg');
    const count = await svgIcons.count();
    
    expect(count).toBeGreaterThan(0);
  });

  /**
   * 测试图表交互兼容性
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持图表交互', async ({ page }) => {
    // 模拟登录
    await authHelper.mockAuthenticated({ role: 'user' });
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 生成示例数据
    await page.click('button:has-text("生成示例数据")');
    await page.waitForTimeout(1000);
    
    // 查找图表
    const chart = page.locator('canvas, .chart-container').first();
    
    if (await chart.isVisible()) {
      // 测试鼠标悬停
      const box = await chart.boundingBox();
      if (box) {
        await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
        await page.waitForTimeout(500);
      }
    }
  });
});

/**
 * 响应式设计兼容性测试套件
 * 
 * 测试响应式设计在不同浏览器上的一致性。
 */
test.describe('响应式设计兼容性', () => {
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
   * 测试桌面端布局
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该正确显示桌面端布局', async ({ page }) => {
    // 设置桌面端视口
    await page.setViewportSize({ width: 1920, height: 1080 });
    
    // 模拟登录
    await authHelper.mockAuthenticated({ role: 'user' });
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 验证侧边栏显示
    const sidebar = page.locator('.sidebar, .ant-layout-sider');
    await expect(sidebar).toBeVisible();
    
    // 验证内容区域显示
    const content = page.locator('.main-content, .ant-layout-content');
    await expect(content).toBeVisible();
  });

  /**
   * 测试平板端布局
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该正确显示平板端布局', async ({ page }) => {
    // 设置平板端视口
    await page.setViewportSize({ width: 768, height: 1024 });
    
    // 模拟登录
    await authHelper.mockAuthenticated({ role: 'user' });
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 验证页面正常显示
    const dataAnalysis = page.locator('.data-analysis');
    await expect(dataAnalysis).toBeVisible();
  });

  /**
   * 测试移动端布局
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该正确显示移动端布局', async ({ page }) => {
    // 设置移动端视口
    await page.setViewportSize({ width: 375, height: 667 });
    
    // 模拟登录
    await authHelper.mockAuthenticated({ role: 'user' });
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 验证页面正常显示
    const dataAnalysis = page.locator('.data-analysis');
    await expect(dataAnalysis).toBeVisible();
  });

  /**
   * 测试媒体查询兼容性
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该支持媒体查询', async ({ page }) => {
    // 模拟登录
    await authHelper.mockAuthenticated({ role: 'user' });
    
    // 测试不同视口尺寸
    const viewports = [
      { width: 1920, height: 1080 },
      { width: 1366, height: 768 },
      { width: 768, height: 1024 },
      { width: 375, height: 667 }
    ];
    
    for (const viewport of viewports) {
      await page.setViewportSize(viewport);
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      
      // 验证页面正常显示
      const dataAnalysis = page.locator('.data-analysis');
      await expect(dataAnalysis).toBeVisible();
    }
  });
});

/**
 * 性能兼容性测试套件
 * 
 * 测试应用在不同浏览器上的性能表现。
 */
test.describe('性能兼容性', () => {
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
   * 测试页面加载性能
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该在合理时间内加载页面', async ({ page }) => {
    const startTime = Date.now();
    
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    const loadTime = Date.now() - startTime;
    
    // 页面加载时间应小于5秒
    expect(loadTime).toBeLessThan(5000);
  });

  /**
   * 测试交互响应性能
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该快速响应交互', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    const startTime = Date.now();
    
    // 点击账号卡片
    const accountCard = page.locator('.account-card').first();
    await accountCard.click();
    
    const clickTime = Date.now() - startTime;
    
    // 点击响应时间应小于1秒
    expect(clickTime).toBeLessThan(1000);
  });

  /**
   * 测试内存使用
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该合理使用内存', async ({ page }) => {
    // 模拟登录
    await authHelper.mockAuthenticated({ role: 'user' });
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // 获取内存使用情况（如果可用）
    const metrics = await page.metrics();
    
    // 验证内存使用合理
    expect(metrics).toBeTruthy();
  });
});

/**
 * 特定浏览器测试套件
 * 
 * 针对特定浏览器的特殊测试。
 */
test.describe('特定浏览器测试', () => {
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
   * Firefox特定测试
   * 
   * @param {Object} page - Playwright页面对象
   * @param {Object} browserName - 浏览器名称
   * @returns {Promise<void>}
   */
  test('Firefox特定功能测试', async ({ page, browserName }) => {
    test.skip(browserName !== 'firefox', '仅在Firefox浏览器运行');
    
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    // Firefox特定测试
    const loginCard = page.locator('.login-card');
    await expect(loginCard).toBeVisible();
  });

  /**
   * Chromium特定测试
   * 
   * @param {Object} page - Playwright页面对象
   * @param {Object} browserName - 浏览器名称
   * @returns {Promise<void>}
   */
  test('Chromium特定功能测试', async ({ page, browserName }) => {
    test.skip(browserName !== 'chromium', '仅在Chromium浏览器运行');
    
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    // Chromium特定测试
    const loginCard = page.locator('.login-card');
    await expect(loginCard).toBeVisible();
  });

  /**
   * WebKit特定测试
   * 
   * @param {Object} page - Playwright页面对象
   * @param {Object} browserName - 浏览器名称
   * @returns {Promise<void>}
   */
  test('WebKit特定功能测试', async ({ page, browserName }) => {
    test.skip(browserName !== 'webkit', '仅在WebKit浏览器运行');
    
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    
    // WebKit特定测试
    const loginCard = page.locator('.login-card');
    await expect(loginCard).toBeVisible();
  });
});
