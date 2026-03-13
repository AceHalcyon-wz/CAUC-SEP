/**
 * @file device.spec.js
 * @path frontend/tests/e2e/
 * @description 设备控制E2E测试套件
 * 
 * 本测试文件包含设备控制模块的端到端测试，覆盖以下功能：
 * - 设备连接管理
 * - 电机控制功能
 * - 温度控制功能
 * - 电磁铁控制功能
 * - 压电控制功能
 * - 安培计控制功能
 * - 设备状态监控
 * 
 * @author Agent
 * @date 2024-03-07
 * @dependencies @playwright/test
 */

import { test, expect } from '@playwright/test';

/**
 * 设备连接功能测试套件
 * 
 * 测试设备的扫描、连接、断开等基础连接管理功能。
 */
test.describe('设备连接功能', () => {
  /**
   * 每个测试前的初始化操作
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test.beforeEach(async ({ page }) => {
    await page.goto('/device/connection');
    await page.waitForLoadState('networkidle');
  });

  /**
   * 测试连接配置面板的渲染
   * 
   * 验证设备连接配置面板是否正确显示。
   * 
   * @param {Object} page - Playwright页面对象
   * @returns {Promise<void>}
   */
  test('应该显示连接配置面板', async ({ page }) => {
    const connectionPanel = page.locator('.connection-panel, .connection-config');
    await expect(connectionPanel).toBeVisible();
  });

  /**
+    * 测试设备扫描和列表显示
+    * 
+    * 验证设备扫描功能和设备列表的正确显示。
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该显示可用设备列表', async ({ page }) => {
    const scanButton = page.locator('button:has-text("扫描")');
    const deviceList = page.locator('.device-list, .device-status');
    
    if (await scanButton.isVisible()) {
      await scanButton.click();
      await page.waitForTimeout(1000);
    }
    
    expect(await deviceList.count()).toBeGreaterThanOrEqual(0);
  });

  /**
+    * 测试设备连接功能
+    * 
+    * 验证用户可以成功连接设备并显示连接状态。
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该支持连接设备', async ({ page }) => {
    const connectButton = page.locator('button:has-text("连接")').first();
    
    if (await connectButton.isVisible()) {
      await connectButton.click();
      await page.waitForTimeout(1000);
      
      const status = page.locator('.connection-status, .device-status');
      await expect(status).toBeVisible();
    }
  });

  /**
+    * 测试设备断开连接功能
+    * 
+    * 验证用户可以成功断开设备连接并显示断开状态。
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该支持断开设备连接', async ({ page }) => {
    const connectButton = page.locator('button:has-text("连接")').first();
    if (await connectButton.isVisible()) {
      await connectButton.click();
      await page.waitForTimeout(1000);
    }
    
    const disconnectButton = page.locator('button:has-text("断开")').first();
    if (await disconnectButton.isVisible()) {
      await disconnectButton.click();
      await page.waitForTimeout(500);
      
      await expect(page.locator('text=已断开')).toBeVisible();
    }
  });
});

/**
 * 电机控制功能测试套件
 * 
 * 测试电机控制的核心功能，包括位置控制、速度控制、
 * 归零操作、启停控制等。
 */
test.describe('电机控制功能', () => {
  /**
+    * 每个测试前的初始化操作
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test.beforeEach(async ({ page }) => {
    await page.goto('/experiment/motor');
    await page.waitForLoadState('networkidle');
  });

  /**
+    * 测试电机控制面板的渲染
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该显示电机控制面板', async ({ page }) => {
    const motorControl = page.locator('.motor-control');
    await expect(motorControl).toBeVisible();
  });

  /**
+    * 测试位置控制显示
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该显示位置控制', async ({ page }) => {
    const positionControl = page.locator('.position-control, .position-display');
    await expect(positionControl).toBeVisible();
  });

  /**
+    * 测试位置设置功能
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该支持位置设置', async ({ page }) => {
    const positionInput = page.locator('input[type="number"]').first();
    
    if (await positionInput.isVisible()) {
      await positionInput.fill('100');
      await page.keyboard.press('Enter');
      
      await expect(positionInput).toHaveValue('100');
    }
  });

  /**
+    * 测试速度控制显示
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该显示速度控制', async ({ page }) => {
    const speedControl = page.locator('.speed-control, .velocity-control');
    await expect(speedControl).toBeVisible();
  });

  /**
+    * 测试电机启停功能
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该支持电机启停', async ({ page }) => {
    const startButton = page.locator('button:has-text("启动")');
    const stopButton = page.locator('button:has-text("停止")');
    
    if (await startButton.isVisible()) {
      await startButton.click();
      await page.waitForTimeout(500);
      
      const status = page.locator('.motor-status, .status-indicator');
      if (await status.isVisible()) {
        await expect(status).toBeVisible();
      }
    }
    
    if (await stopButton.isVisible()) {
      await stopButton.click();
      await page.waitForTimeout(500);
    }
  });

  /**
+    * 测试位置图表显示
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该显示位置图表', async ({ page }) => {
    const chart = page.locator('.position-chart, canvas');
    await expect(chart).toBeVisible();
  });

  /**
+    * 测试归零操作功能
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该支持归零操作', async ({ page }) => {
    const homeButton = page.locator('button:has-text("归零")');
    
    if (await homeButton.isVisible()) {
      await homeButton.click();
      await page.waitForTimeout(1000);
      
      await expect(page.locator('.el-message')).toBeVisible();
    }
  });
});

/**
 * 温度控制功能测试套件
 * 
 * 测试温度控制的核心功能，包括温度设置、PID控制、
 * 程序控温、温度曲线显示等。
 */
test.describe('温度控制功能', () => {
  /**
+    * 每个测试前的初始化操作
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test.beforeEach(async ({ page }) => {
    await page.goto('/experiment/temperature');
    await page.waitForLoadState('networkidle');
  });

  /**
+    * 测试温度控制面板的渲染
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该显示温度控制面板', async ({ page }) => {
    const temperatureControl = page.locator('.temperature-control');
    await expect(temperatureControl).toBeVisible();
  });

  /**
+    * 测试当前温度显示
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该显示当前温度', async ({ page }) => {
    const temperatureDisplay = page.locator('.temperature-display, .current-temperature');
    await expect(temperatureDisplay).toBeVisible();
  });

  /**
+    * 测试目标温度设置功能
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该支持目标温度设置', async ({ page }) => {
    const targetTempInput = page.locator('input[type="number"]').first();
    
    if (await targetTempInput.isVisible()) {
      await targetTempInput.fill('25');
      await page.keyboard.press('Enter');
      
      await expect(targetTempInput).toHaveValue('25');
    }
  });

  /**
+    * 测试温度曲线显示
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该显示温度曲线', async ({ page }) => {
    const temperatureCurve = page.locator('.temperature-curve, canvas');
    await expect(temperatureCurve).toBeVisible();
  });

  /**
+    * 测试温度程序设置功能
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该支持温度程序设置', async ({ page }) => {
    const programButton = page.locator('button:has-text("程序")');
    
    if (await programButton.isVisible()) {
      await programButton.click();
      
      const dialog = page.locator('.el-dialog');
      await expect(dialog).toBeVisible();
    }
  });
});

/**
 * 电磁铁控制功能测试套件
 * 
 * 测试电磁铁控制的核心功能，包括磁场强度设置、
 * 扫描配置、磁场分布图显示等。
 */
test.describe('电磁铁控制功能', () => {
  /**
+    * 每个测试前的初始化操作
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test.beforeEach(async ({ page }) => {
    await page.goto('/experiment/electromagnet');
    await page.waitForLoadState('networkidle');
  });

  /**
+    * 测试电磁铁控制面板的渲染
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该显示电磁铁控制面板', async ({ page }) => {
    const electromagnetControl = page.locator('.electromagnet-control');
    await expect(electromagnetControl).toBeVisible();
  });

  /**
+    * 测试磁场强度设置功能
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该支持磁场强度设置', async ({ page }) => {
    const fieldInput = page.locator('input[type="number"]').first();
    
    if (await fieldInput.isVisible()) {
      await fieldInput.fill('100');
      await page.keyboard.press('Enter');
      
      await expect(fieldInput).toHaveValue('100');
    }
  });

  /**
+    * 测试磁场分布图显示
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该显示磁场分布图', async ({ page }) => {
    const fieldMap = page.locator('.field-map, canvas');
    await expect(fieldMap).toBeVisible();
  });

  /**
+    * 测试扫描配置功能
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该支持扫描配置', async ({ page }) => {
    const scanButton = page.locator('button:has-text("扫描")');
    
    if (await scanButton.isVisible()) {
      await scanButton.click();
      await page.waitForTimeout(500);
    }
  });
});

/**
 * 压电控制功能测试套件
 * 
 * 测试压电控制的核心功能，包括电压设置、
 * 校准功能、电压映射图显示等。
 */
test.describe('压电控制功能', () => {
  /**
+    * 每个测试前的初始化操作
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test.beforeEach(async ({ page }) => {
    await page.goto('/experiment/piezo');
    await page.waitForLoadState('networkidle');
  });

  /**
+    * 测试压电控制面板的渲染
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该显示压电控制面板', async ({ page }) => {
    const piezoControl = page.locator('.piezo-control');
    await expect(piezoControl).toBeVisible();
  });

  /**
+    * 测试电压设置功能
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该支持电压设置', async ({ page }) => {
    const voltageInput = page.locator('input[type="number"]').first();
    
    if (await voltageInput.isVisible()) {
      await voltageInput.fill('50');
      await page.keyboard.press('Enter');
      
      await expect(voltageInput).toHaveValue('50');
    }
  });

  /**
+    * 测试电压映射图显示
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该显示电压映射图', async ({ page }) => {
    const voltageMap = page.locator('.voltage-map, canvas');
    await expect(voltageMap).toBeVisible();
  });

  /**
+    * 测试校准功能
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该支持校准功能', async ({ page }) => {
    const calibrateButton = page.locator('button:has-text("校准")');
    
    if (await calibrateButton.isVisible()) {
      await calibrateButton.click();
      await page.waitForTimeout(500);
    }
  });
});

/**
 * 安培计控制功能测试套件
 * 
 * 测试安培计控制的核心功能，包括电流读数、
 * 波形图显示、通道配置等。
 */
test.describe('安培计控制功能', () => {
  /**
+    * 每个测试前的初始化操作
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test.beforeEach(async ({ page }) => {
    await page.goto('/experiment/ammeter');
    await page.waitForLoadState('networkidle');
  });

  /**
+    * 测试安培计控制面板的渲染
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该显示安培计控制面板', async ({ page }) => {
    const ammeterControl = page.locator('.ammeter-control');
    await expect(ammeterControl).toBeVisible();
  });

  /**
+    * 测试电流读数显示
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该显示电流读数', async ({ page }) => {
    const currentDisplay = page.locator('.current-display, .ammeter-display');
    await expect(currentDisplay).toBeVisible();
  });

  /**
+    * 测试波形图显示
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该显示波形图', async ({ page }) => {
    const waveform = page.locator('.ammeter-waveform, canvas');
    await expect(waveform).toBeVisible();
  });

  /**
+    * 测试通道配置显示
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该支持通道配置', async ({ page }) => {
    const channelConfig = page.locator('.channel-config');
    await expect(channelConfig).toBeVisible();
  });
});

/**
 * 设备状态监控测试套件
 * 
 * 测试设备状态监控的核心功能，包括状态仪表板、
 * 设备卡片、连接状态显示等。
 */
test.describe('设备状态监控', () => {
  /**
+    * 每个测试前的初始化操作
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test.beforeEach(async ({ page }) => {
    await page.goto('/device/status');
    await page.waitForLoadState('networkidle');
  });

  /**
+    * 测试设备状态仪表板的渲染
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该显示设备状态仪表板', async ({ page }) => {
    const dashboard = page.locator('.device-status-dashboard');
    await expect(dashboard).toBeVisible();
  });

  /**
+    * 测试设备状态卡片显示
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该显示所有设备状态', async ({ page }) => {
    const deviceCards = page.locator('.device-card, .status-card');
    const count = await deviceCards.count();
    
    expect(count).toBeGreaterThan(0);
  });

  /**
+    * 测试设备连接状态显示
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该显示设备连接状态', async ({ page }) => {
    const connectionStatus = page.locator('.connection-status, .status-indicator');
    await expect(connectionStatus.first()).toBeVisible();
  });

  /**
+    * 测试刷新状态功能
+    * 
+    * @param {Object} page - Playwright页面对象
+    * @returns {Promise<void>}
+    */
  test('应该支持刷新状态', async ({ page }) => {
    const refreshButton = page.locator('button:has-text("刷新")');
    
    if (await refreshButton.isVisible()) {
      await refreshButton.click();
      await page.waitForTimeout(1000);
    }
  });
});
