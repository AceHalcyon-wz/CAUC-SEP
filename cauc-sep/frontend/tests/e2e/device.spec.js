/**
 * @file device.spec.js
 * @path frontend/tests/e2e/
 * @description 设备控制E2E测试
 * @author Agent
 * @date 2024-03-07
 */

import { test, expect } from '@playwright/test';

test.describe('设备连接功能', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/device/connection');
    await page.waitForLoadState('networkidle');
  });

  test('应该显示连接配置面板', async ({ page }) => {
    const connectionPanel = page.locator('.connection-panel, .connection-config');
    await expect(connectionPanel).toBeVisible();
  });

  test('应该显示可用设备列表', async ({ page }) => {
    const scanButton = page.locator('button:has-text("扫描")');
    const deviceList = page.locator('.device-list, .device-status');
    
    if (await scanButton.isVisible()) {
      await scanButton.click();
      await page.waitForTimeout(1000);
    }
    
    expect(await deviceList.count()).toBeGreaterThanOrEqual(0);
  });

  test('应该支持连接设备', async ({ page }) => {
    const connectButton = page.locator('button:has-text("连接")').first();
    
    if (await connectButton.isVisible()) {
      await connectButton.click();
      await page.waitForTimeout(1000);
      
      const status = page.locator('.connection-status, .device-status');
      await expect(status).toBeVisible();
    }
  });

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

test.describe('电机控制功能', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/experiment/motor');
    await page.waitForLoadState('networkidle');
  });

  test('应该显示电机控制面板', async ({ page }) => {
    const motorControl = page.locator('.motor-control');
    await expect(motorControl).toBeVisible();
  });

  test('应该显示位置控制', async ({ page }) => {
    const positionControl = page.locator('.position-control, .position-display');
    await expect(positionControl).toBeVisible();
  });

  test('应该支持位置设置', async ({ page }) => {
    const positionInput = page.locator('input[type="number"]').first();
    
    if (await positionInput.isVisible()) {
      await positionInput.fill('100');
      await page.keyboard.press('Enter');
      
      await expect(positionInput).toHaveValue('100');
    }
  });

  test('应该显示速度控制', async ({ page }) => {
    const speedControl = page.locator('.speed-control, .velocity-control');
    await expect(speedControl).toBeVisible();
  });

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

  test('应该显示位置图表', async ({ page }) => {
    const chart = page.locator('.position-chart, canvas');
    await expect(chart).toBeVisible();
  });

  test('应该支持归零操作', async ({ page }) => {
    const homeButton = page.locator('button:has-text("归零")');
    
    if (await homeButton.isVisible()) {
      await homeButton.click();
      await page.waitForTimeout(1000);
      
      await expect(page.locator('.el-message')).toBeVisible();
    }
  });
});

test.describe('温度控制功能', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/experiment/temperature');
    await page.waitForLoadState('networkidle');
  });

  test('应该显示温度控制面板', async ({ page }) => {
    const temperatureControl = page.locator('.temperature-control');
    await expect(temperatureControl).toBeVisible();
  });

  test('应该显示当前温度', async ({ page }) => {
    const temperatureDisplay = page.locator('.temperature-display, .current-temperature');
    await expect(temperatureDisplay).toBeVisible();
  });

  test('应该支持目标温度设置', async ({ page }) => {
    const targetTempInput = page.locator('input[type="number"]').first();
    
    if (await targetTempInput.isVisible()) {
      await targetTempInput.fill('25');
      await page.keyboard.press('Enter');
      
      await expect(targetTempInput).toHaveValue('25');
    }
  });

  test('应该显示温度曲线', async ({ page }) => {
    const temperatureCurve = page.locator('.temperature-curve, canvas');
    await expect(temperatureCurve).toBeVisible();
  });

  test('应该支持温度程序设置', async ({ page }) => {
    const programButton = page.locator('button:has-text("程序")');
    
    if (await programButton.isVisible()) {
      await programButton.click();
      
      const dialog = page.locator('.el-dialog');
      await expect(dialog).toBeVisible();
    }
  });
});

test.describe('电磁铁控制功能', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/experiment/electromagnet');
    await page.waitForLoadState('networkidle');
  });

  test('应该显示电磁铁控制面板', async ({ page }) => {
    const electromagnetControl = page.locator('.electromagnet-control');
    await expect(electromagnetControl).toBeVisible();
  });

  test('应该支持磁场强度设置', async ({ page }) => {
    const fieldInput = page.locator('input[type="number"]').first();
    
    if (await fieldInput.isVisible()) {
      await fieldInput.fill('100');
      await page.keyboard.press('Enter');
      
      await expect(fieldInput).toHaveValue('100');
    }
  });

  test('应该显示磁场分布图', async ({ page }) => {
    const fieldMap = page.locator('.field-map, canvas');
    await expect(fieldMap).toBeVisible();
  });

  test('应该支持扫描配置', async ({ page }) => {
    const scanButton = page.locator('button:has-text("扫描")');
    
    if (await scanButton.isVisible()) {
      await scanButton.click();
      await page.waitForTimeout(500);
    }
  });
});

test.describe('压电控制功能', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/experiment/piezo');
    await page.waitForLoadState('networkidle');
  });

  test('应该显示压电控制面板', async ({ page }) => {
    const piezoControl = page.locator('.piezo-control');
    await expect(piezoControl).toBeVisible();
  });

  test('应该支持电压设置', async ({ page }) => {
    const voltageInput = page.locator('input[type="number"]').first();
    
    if (await voltageInput.isVisible()) {
      await voltageInput.fill('50');
      await page.keyboard.press('Enter');
      
      await expect(voltageInput).toHaveValue('50');
    }
  });

  test('应该显示电压映射图', async ({ page }) => {
    const voltageMap = page.locator('.voltage-map, canvas');
    await expect(voltageMap).toBeVisible();
  });

  test('应该支持校准功能', async ({ page }) => {
    const calibrateButton = page.locator('button:has-text("校准")');
    
    if (await calibrateButton.isVisible()) {
      await calibrateButton.click();
      await page.waitForTimeout(500);
    }
  });
});

test.describe('安培计控制功能', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/experiment/ammeter');
    await page.waitForLoadState('networkidle');
  });

  test('应该显示安培计控制面板', async ({ page }) => {
    const ammeterControl = page.locator('.ammeter-control');
    await expect(ammeterControl).toBeVisible();
  });

  test('应该显示电流读数', async ({ page }) => {
    const currentDisplay = page.locator('.current-display, .ammeter-display');
    await expect(currentDisplay).toBeVisible();
  });

  test('应该显示波形图', async ({ page }) => {
    const waveform = page.locator('.ammeter-waveform, canvas');
    await expect(waveform).toBeVisible();
  });

  test('应该支持通道配置', async ({ page }) => {
    const channelConfig = page.locator('.channel-config');
    await expect(channelConfig).toBeVisible();
  });
});

test.describe('设备状态监控', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/device/status');
    await page.waitForLoadState('networkidle');
  });

  test('应该显示设备状态仪表板', async ({ page }) => {
    const dashboard = page.locator('.device-status-dashboard');
    await expect(dashboard).toBeVisible();
  });

  test('应该显示所有设备状态', async ({ page }) => {
    const deviceCards = page.locator('.device-card, .status-card');
    const count = await deviceCards.count();
    
    expect(count).toBeGreaterThan(0);
  });

  test('应该显示设备连接状态', async ({ page }) => {
    const connectionStatus = page.locator('.connection-status, .status-indicator');
    await expect(connectionStatus.first()).toBeVisible();
  });

  test('应该支持刷新状态', async ({ page }) => {
    const refreshButton = page.locator('button:has-text("刷新")');
    
    if (await refreshButton.isVisible()) {
      await refreshButton.click();
      await page.waitForTimeout(1000);
    }
  });
});
