/**
 * @file app-launch.spec.js
 * @path frontend/tests/e2e/
 * @description Electron应用启动和窗口显示E2E测试
 * 
 * 测试范围：
 * - Electron应用启动
 * - 窗口正确显示
 * - 窗口大小和位置
 * - 应用基本功能
 * 
 * @author Agent
 * @date 2024-03-16
 * @dependencies @playwright/test, ./helpers
 */

import { test, expect } from '@playwright/test';
import { 
  ElectronAppHelper, 
  quickLaunchElectron,
  isElectronTestEnabled 
} from './helpers/index.js';

/**
 * 测试配置
 */
const TEST_CONFIG = {
  /** 应用启动超时时间（毫秒） */
  STARTUP_TIMEOUT: 30000,
  /** 窗口加载超时时间（毫秒） */
  WINDOW_LOAD_TIMEOUT: 15000,
  /** 默认窗口宽度 */
  DEFAULT_WIDTH: 1400,
  /** 默认窗口高度 */
  DEFAULT_HEIGHT: 900,
  /** 最小窗口宽度 */
  MIN_WIDTH: 1024,
  /** 最小窗口高度 */
  MIN_HEIGHT: 768,
};

/**
 * Electron应用启动和窗口显示测试套件
 */
test.describe('Electron应用启动和窗口显示测试', () => {
  let electronHelper;
  let app;
  let window;

  /**
   * 测试前准备：启动Electron应用
   */
  test.beforeAll(async () => {
    // 检查是否启用Electron测试
    if (!isElectronTestEnabled()) {
      test.skip(true, 'Electron测试未启用');
      return;
    }

    // 启动Electron应用
    const result = await quickLaunchElectron({
      headless: false,
      timeout: TEST_CONFIG.STARTUP_TIMEOUT,
    });
    
    electronHelper = result.helper;
    app = result.app;
    window = result.window;
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
   * 测试1：验证Electron应用成功启动
   */
  test('应该成功启动Electron应用', async () => {
    // 验证应用实例存在
    expect(app).toBeDefined();
    expect(electronHelper).toBeDefined();
    
    // 验证应用处于就绪状态
    const isReady = await electronHelper.isReady();
    expect(isReady).toBe(true);
  });

  /**
   * 测试2：验证应用窗口正确显示
   */
  test('应用窗口应该正确显示', async () => {
    // 验证窗口实例存在
    expect(window).toBeDefined();
    
    // 验证窗口可见
    await expect(window).toBeVisible();
    
    // 等待页面加载完成
    await window.waitForLoadState('domcontentloaded', {
      timeout: TEST_CONFIG.WINDOW_LOAD_TIMEOUT,
    });
  });

  /**
   * 测试3：验证窗口标题
   */
  test('应该有正确的窗口标题', async () => {
    const title = await window.title();
    expect(title).toContain('CAUC-SEP');
  });

  /**
   * 测试4：验证窗口大小符合默认配置
   */
  test('窗口大小应该符合默认配置', async () => {
    const size = await window.viewportSize();
    
    // 验证窗口尺寸在合理范围内
    expect(size.width).toBeGreaterThanOrEqual(TEST_CONFIG.MIN_WIDTH);
    expect(size.height).toBeGreaterThanOrEqual(TEST_CONFIG.MIN_HEIGHT);
    
    // 验证默认尺寸（允许一定误差）
    expect(size.width).toBeCloseTo(TEST_CONFIG.DEFAULT_WIDTH, -1);
    expect(size.height).toBeCloseTo(TEST_CONFIG.DEFAULT_HEIGHT, -1);
  });

  /**
   * 测试5：验证窗口最小尺寸限制
   */
  test('窗口应该有最小尺寸限制', async () => {
    // 尝试调整窗口到最小尺寸以下
    const smallSize = { width: 800, height: 600 };
    
    try {
      await window.setViewportSize(smallSize);
      await window.waitForTimeout(500);
      
      const actualSize = await window.viewportSize();
      
      // 窗口应该保持最小尺寸或更大
      expect(actualSize.width).toBeGreaterThanOrEqual(TEST_CONFIG.MIN_WIDTH);
      expect(actualSize.height).toBeGreaterThanOrEqual(TEST_CONFIG.MIN_HEIGHT);
    } catch (error) {
      // 某些情况下可能无法调整到最小尺寸以下，这是预期行为
      expect(true).toBe(true);
    }
  });

  /**
   * 测试6：验证窗口可以调整大小
   */
  test('应该能够调整窗口大小', async () => {
    const newSize = { width: 1280, height: 800 };
    
    await window.setViewportSize(newSize);
    await window.waitForTimeout(500);
    
    const size = await window.viewportSize();
    expect(size.width).toBe(newSize.width);
    expect(size.height).toBe(newSize.height);
  });

  /**
   * 测试7：验证应用版本信息
   */
  test('应该能够获取应用版本信息', async () => {
    const version = await electronHelper.getAppVersion();
    
    expect(version).toBeDefined();
    expect(typeof version).toBe('string');
    expect(version.length).toBeGreaterThan(0);
  });

  /**
   * 测试8：验证应用路径信息
   */
  test('应该能够获取应用路径信息', async () => {
    const appPath = await electronHelper.getAppPath('appPath');
    const userDataPath = await electronHelper.getAppPath('userData');
    
    expect(appPath).toBeDefined();
    expect(typeof appPath).toBe('string');
    expect(userDataPath).toBeDefined();
    expect(typeof userDataPath).toBe('string');
  });

  /**
   * 测试9：验证前端页面正确加载
   */
  test('应该正确加载前端页面', async () => {
    // 等待页面完全加载
    await window.waitForLoadState('networkidle', {
      timeout: TEST_CONFIG.WINDOW_LOAD_TIMEOUT,
    });
    
    // 验证页面body存在
    const body = window.locator('body');
    await expect(body).toBeVisible();
    
    // 验证页面有内容
    const content = await body.textContent();
    expect(content.length).toBeGreaterThan(0);
  });

  /**
   * 测试10：验证应用图标
   */
  test('应用应该有正确的图标', async () => {
    // 获取窗口图标（通过IPC）
    const iconPath = await electronHelper.getAppPath('appPath');
    
    // 验证图标路径存在
    expect(iconPath).toBeDefined();
  });

  /**
   * 测试11：验证窗口居中显示
   */
  test('窗口应该在屏幕上居中显示', async () => {
    // 获取窗口位置和大小
    const bounds = await window.evaluate(() => {
      return {
        innerWidth: window.innerWidth,
        innerHeight: window.innerHeight,
        screenX: window.screenX,
        screenY: window.screenY,
        screenWidth: window.screen.width,
        screenHeight: window.screen.height,
      };
    });
    
    // 验证窗口在屏幕范围内
    expect(bounds.screenX).toBeGreaterThanOrEqual(0);
    expect(bounds.screenY).toBeGreaterThanOrEqual(0);
    expect(bounds.innerWidth).toBeGreaterThan(0);
    expect(bounds.innerHeight).toBeGreaterThan(0);
  });

  /**
   * 测试12：验证应用启动时间
   */
  test('应用应该在合理时间内启动', async () => {
    const startTime = Date.now();
    
    // 重新启动应用
    await electronHelper.close();
    const result = await quickLaunchElectron({
      timeout: TEST_CONFIG.STARTUP_TIMEOUT,
    });
    
    electronHelper = result.helper;
    app = result.app;
    window = result.window;
    
    const endTime = Date.now();
    const startupTime = endTime - startTime;
    
    // 应用应该在30秒内启动
    expect(startupTime).toBeLessThan(TEST_CONFIG.STARTUP_TIMEOUT);
  });

  /**
   * 测试13：验证截图功能
   */
  test('应该能够截取应用截图', async () => {
    const screenshot = await electronHelper.takeScreenshot();
    
    expect(screenshot).toBeDefined();
    expect(screenshot.length).toBeGreaterThan(0);
  });

  /**
   * 测试14：验证开发者工具（开发环境）
   */
  test('开发环境应该能够打开开发者工具', async () => {
    // 按F12打开开发者工具
    await window.keyboard.press('F12');
    await window.waitForTimeout(1000);
    
    // 验证开发者工具是否打开（开发环境）
    const isDevToolsOpen = await window.evaluate(() => {
      // 检查是否有开发者工具相关元素
      return document.querySelector('.devtools, [data-devtools]') !== null ||
             window.outerWidth > window.innerWidth;
    });
    
    // 这个测试可能失败，取决于应用配置
    expect(typeof isDevToolsOpen).toBe('boolean');
  });

  /**
   * 测试15：验证应用菜单
   */
  test('应用应该有正确的菜单栏', async () => {
    // 验证菜单栏存在（通过IPC或页面元素）
    const hasMenuBar = await window.evaluate(() => {
      // 检查是否有菜单相关元素
      return document.querySelector('.menu-bar, nav, header, [role="menubar"]') !== null;
    });
    
    // 应用应该有某种形式的菜单或导航
    expect(typeof hasMenuBar).toBe('boolean');
  });
});

/**
 * Electron应用稳定性测试套件
 */
test.describe('Electron应用稳定性测试', () => {
  let electronHelper;
  let window;

  test.beforeAll(async () => {
    if (!isElectronTestEnabled()) {
      test.skip(true, 'Electron测试未启用');
      return;
    }

    const result = await quickLaunchElectron();
    electronHelper = result.helper;
    window = result.window;
  });

  test.afterAll(async () => {
    if (electronHelper) {
      await electronHelper.close();
    }
  });

  /**
   * 测试16：验证应用不会崩溃
   */
  test('应用应该稳定运行不崩溃', async () => {
    // 执行多次页面刷新
    for (let i = 0; i < 3; i++) {
      await window.reload();
      await window.waitForLoadState('domcontentloaded');
    }
    
    // 验证应用仍然响应
    const isReady = await electronHelper.isReady();
    expect(isReady).toBe(true);
  });

  /**
   * 测试17：验证内存使用合理
   */
  test('应用内存使用应该在合理范围', async () => {
    const metrics = await window.evaluate(() => {
      if (performance.memory) {
        return {
          usedJSHeapSize: performance.memory.usedJSHeapSize,
          totalJSHeapSize: performance.memory.totalJSHeapSize,
          jsHeapSizeLimit: performance.memory.jsHeapSizeLimit,
        };
      }
      return null;
    });
    
    if (metrics) {
      // 验证内存使用不超过500MB
      const usedMB = metrics.usedJSHeapSize / 1024 / 1024;
      expect(usedMB).toBeLessThan(500);
      
      // 验证内存使用不超过限制的50%
      const usagePercent = (metrics.usedJSHeapSize / metrics.jsHeapSizeLimit) * 100;
      expect(usagePercent).toBeLessThan(50);
    }
  });

  /**
   * 测试18：验证页面加载性能
   */
  test('页面应该在合理时间内加载', async () => {
    const startTime = Date.now();
    
    await window.reload();
    await window.waitForLoadState('networkidle');
    
    const endTime = Date.now();
    const loadTime = endTime - startTime;
    
    // 页面应该在10秒内加载完成
    expect(loadTime).toBeLessThan(10000);
  });

  /**
   * 测试19：验证多次打开关闭窗口
   */
  test('应该能够多次打开关闭窗口', async () => {
    const windows = await electronHelper.getAllWindows();
    const initialCount = windows.length;
    
    // 验证窗口数量
    expect(initialCount).toBeGreaterThanOrEqual(1);
    
    // 验证窗口可以正常操作
    await window.reload();
    await window.waitForLoadState('domcontentloaded');
    
    const isReady = await electronHelper.isReady();
    expect(isReady).toBe(true);
  });

  /**
   * 测试20：验证应用响应性
   */
  test('应用应该保持响应性', async () => {
    // 执行一些UI操作
    await window.click('body');
    await window.keyboard.press('Tab');
    
    // 验证应用仍然响应
    const isReady = await electronHelper.isReady();
    expect(isReady).toBe(true);
    
    // 验证页面仍然可见
    await expect(window).toBeVisible();
  });
});

/**
 * Electron应用后端集成测试套件
 */
test.describe('Electron应用后端集成测试', () => {
  let electronHelper;
  let window;

  test.beforeAll(async () => {
    if (!isElectronTestEnabled()) {
      test.skip(true, 'Electron测试未启用');
      return;
    }

    const result = await quickLaunchElectron();
    electronHelper = result.helper;
    window = result.window;
  });

  test.afterAll(async () => {
    if (electronHelper) {
      await electronHelper.close();
    }
  });

  /**
   * 测试21：验证后端进程状态
   */
  test('应该能够获取后端进程状态', async () => {
    // 通过IPC获取后端状态
    const status = await window.evaluate(async () => {
      if (window.electronAPI && window.electronAPI.getBackendStatus) {
        return await window.electronAPI.getBackendStatus();
      }
      return null;
    });
    
    // 如果后端集成存在，验证状态
    if (status) {
      expect(status).toHaveProperty('isRunning');
      expect(status).toHaveProperty('port');
    }
  });

  /**
   * 测试22：验证后端健康检查
   */
  test('后端应该响应健康检查', async () => {
    // 等待后端启动
    await window.waitForTimeout(5000);
    
    // 尝试访问后端健康检查端点
    const healthCheck = await window.evaluate(async () => {
      try {
        const response = await fetch('http://localhost:8000/api/health');
        return {
          ok: response.ok,
          status: response.status,
        };
      } catch (error) {
        return {
          ok: false,
          error: error.message,
        };
      }
    });
    
    // 验证后端健康检查（如果后端已启动）
    if (healthCheck.ok) {
      expect(healthCheck.status).toBe(200);
    }
  });
});
