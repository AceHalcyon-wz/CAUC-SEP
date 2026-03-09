/**
 * @file analysis.spec.js
 * @path frontend/tests/e2e/
 * @description 数据分析功能E2E测试
 * @author Agent
 * @date 2024-03-07
 */

import { test, expect } from '@playwright/test';

test.describe('数据分析功能', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    
    await page.waitForLoadState('networkidle');
  });

  test('应该显示数据分析页面', async ({ page }) => {
    const dataAnalysis = page.locator('.data-analysis');
    await expect(dataAnalysis).toBeVisible();
    
    await expect(page.locator('.card-header')).toContainText('数据分析');
  });

  test('应该显示四个标签页', async ({ page }) => {
    const tabs = page.locator('.el-tabs__item');
    await expect(tabs).toHaveCount(4);
    
    await expect(tabs.nth(0)).toContainText('信号平滑');
    await expect(tabs.nth(1)).toContainText('磁滞回线分析');
    await expect(tabs.nth(2)).toContainText('多模型对比');
    await expect(tabs.nth(3)).toContainText('分析报告');
  });

  test('应该切换标签页', async ({ page }) => {
    await page.click('.el-tabs__item:has-text("磁滞回线分析")');
    
    const activeTab = page.locator('.el-tabs__item.is-active');
    await expect(activeTab).toContainText('磁滞回线分析');
  });

  test.describe('信号平滑功能', () => {
    test('应该生成示例数据', async ({ page }) => {
      await page.click('button:has-text("生成示例数据")');
      
      await page.waitForTimeout(1000);
      
      await expect(page.locator('.el-message--success')).toBeVisible();
    });

    test('应该应用信号平滑', async ({ page }) => {
      await page.click('button:has-text("生成示例数据")');
      await page.waitForTimeout(1000);
      
      await page.click('button:has-text("应用平滑")');
      await page.waitForTimeout(2000);
      
      await expect(page.locator('.el-message--success')).toBeVisible();
    });

    test('应该切换平滑方法', async ({ page }) => {
      await page.click('.el-select:has-text("Savitzky-Golay")');
      await page.click('.el-select-dropdown__item:has-text("巴特沃斯低通滤波")');
      
      const select = page.locator('.el-select .el-input__inner');
      await expect(select).toHaveValue(/butterworth/);
    });
  });

  test.describe('磁滞回线分析功能', () => {
    test.beforeEach(async ({ page }) => {
      await page.click('.el-tabs__item:has-text("磁滞回线分析")');
    });

    test('应该生成磁滞回线示例数据', async ({ page }) => {
      await page.click('button:has-text("生成示例数据")');
      await page.waitForTimeout(1000);
      
      await expect(page.locator('.el-message--success')).toBeVisible();
    });

    test('应该执行磁滞回线分析', async ({ page }) => {
      await page.click('button:has-text("生成示例数据")');
      await page.waitForTimeout(1000);
      
      await page.click('button:has-text("分析磁滞回线")');
      await page.waitForTimeout(2000);
      
      const resultDisplay = page.locator('.result-display');
      await expect(resultDisplay).toBeVisible();
    });

    test('应该显示分析结果', async ({ page }) => {
      await page.click('button:has-text("生成示例数据")');
      await page.waitForTimeout(1000);
      await page.click('button:has-text("分析磁滞回线")');
      await page.waitForTimeout(2000);
      
      await expect(page.locator('text=矫顽力')).toBeVisible();
      await expect(page.locator('text=剩磁')).toBeVisible();
      await expect(page.locator('text=饱和磁矩')).toBeVisible();
    });
  });

  test.describe('多模型对比功能', () => {
    test.beforeEach(async ({ page }) => {
      await page.click('.el-tabs__item:has-text("磁滞回线分析")');
      await page.click('button:has-text("生成示例数据")');
      await page.waitForTimeout(1000);
      
      await page.click('.el-tabs__item:has-text("多模型对比")');
    });

    test('应该显示模型选择器', async ({ page }) => {
      const checkboxGroup = page.locator('.el-checkbox-group');
      await expect(checkboxGroup).toBeVisible();
      
      await expect(page.locator('text=双曲正切模型')).toBeVisible();
      await expect(page.locator('text=反正切模型')).toBeVisible();
    });

    test('应该执行多模型拟合', async ({ page }) => {
      const checkboxes = page.locator('.el-checkbox');
      const count = await checkboxes.count();
      
      if (count >= 2) {
        await page.click('button:has-text("执行多模型拟合")');
        await page.waitForTimeout(3000);
        
        const table = page.locator('.el-table');
        await expect(table).toBeVisible();
      }
    });

    test('应该显示最佳模型推荐', async ({ page }) => {
      await page.click('button:has-text("执行多模型拟合")');
      await page.waitForTimeout(3000);
      
      const bestModel = page.locator('.result-display:has-text("最佳模型")');
      await expect(bestModel).toBeVisible();
    });

    test('应该查看模型详情', async ({ page }) => {
      await page.click('button:has-text("执行多模型拟合")');
      await page.waitForTimeout(3000);
      
      const detailButton = page.locator('button:has-text("查看详情")').first();
      if (await detailButton.isVisible()) {
        await detailButton.click();
        
        const dialog = page.locator('.el-dialog');
        await expect(dialog).toBeVisible();
      }
    });
  });

  test.describe('报告功能', () => {
    test.beforeEach(async ({ page }) => {
      await page.click('.el-tabs__item:has-text("磁滞回线分析")');
      await page.click('button:has-text("生成示例数据")');
      await page.waitForTimeout(1000);
      
      await page.click('.el-tabs__item:has-text("分析报告")');
    });

    test('应该生成分析报告', async ({ page }) => {
      await page.click('button:has-text("生成报告")');
      await page.waitForTimeout(2000);
      
      const reportContent = page.locator('.report-content');
      await expect(reportContent).toBeVisible();
    });

    test('应该显示报告预览', async ({ page }) => {
      await page.click('button:has-text("生成报告")');
      await page.waitForTimeout(2000);
      
      await expect(page.locator('text=磁滞回线分析报告')).toBeVisible();
      
      await expect(page.locator('text=磁滞参数')).toBeVisible();
    });

    test('应该导出JSON格式报告', async ({ page }) => {
      await page.click('button:has-text("生成报告")');
      await page.waitForTimeout(2000);
      
      await page.click('.el-dropdown:has-text("导出报告")');
      
      const downloadPromise = page.waitForEvent('download');
      await page.click('.el-dropdown-item:has-text("JSON格式")');
      
      const download = await downloadPromise;
      expect(download.suggestedFilename()).toContain('analysis_report');
      expect(download.suggestedFilename()).toContain('.json');
    });

    test('应该导出CSV格式报告', async ({ page }) => {
      await page.click('button:has-text("生成报告")');
      await page.waitForTimeout(2000);
      
      await page.click('.el-dropdown:has-text("导出报告")');
      
      const downloadPromise = page.waitForEvent('download');
      await page.click('.el-dropdown-item:has-text("CSV格式")');
      
      const download = await downloadPromise;
      expect(download.suggestedFilename()).toContain('.csv');
    });
  });

  test.describe('历史记录功能', () => {
    test('应该显示历史记录对话框', async ({ page }) => {
      await page.click('button:has-text("历史记录")');
      
      const dialog = page.locator('.el-dialog:has-text("分析历史记录")');
      await expect(dialog).toBeVisible();
    });

    test('应该清空历史记录', async ({ page }) => {
      await page.click('button:has-text("历史记录")');
      
      await page.click('button:has-text("清空历史")');
      
      page.on('dialog', dialog => dialog.accept());
    });
  });

  test.describe('标注功能', () => {
    test('应该切换标注面板', async ({ page }) => {
      await page.click('button:has-text("开启标注")');
      
      const annotationPanel = page.locator('.annotation-panel');
      await expect(annotationPanel).toBeVisible();
      
      await page.click('button:has-text("关闭标注")');
      await expect(annotationPanel).not.toBeVisible();
    });

    test('应该切换标注类型', async ({ page }) => {
      await page.click('button:has-text("开启标注")');
      
      await page.click('.el-radio-button:has-text("标注线")');
      
      const selectedRadio = page.locator('.el-radio-button.is-active');
      await expect(selectedRadio).toContainText('标注线');
    });

    test('应该清除所有标注', async ({ page }) => {
      await page.click('button:has-text("开启标注")');
      
      await page.click('button:has-text("清除所有标注")');
      
      await expect(page.locator('.el-message--success')).toBeVisible();
    });
  });

  test.describe('数据导出功能', () => {
    test('应该显示导出菜单', async ({ page }) => {
      await page.click('.el-dropdown:has-text("导出数据")');
      
      const dropdown = page.locator('.el-dropdown-menu');
      await expect(dropdown).toBeVisible();
      
      await expect(page.locator('.el-dropdown-item:has-text("导出为 CSV")')).toBeVisible();
      await expect(page.locator('.el-dropdown-item:has-text("导出图表为 PNG")')).toBeVisible();
      await expect(page.locator('.el-dropdown-item:has-text("导出图表为 SVG")')).toBeVisible();
    });

    test('应该导出CSV数据', async ({ page }) => {
      await page.click('button:has-text("生成示例数据")');
      await page.waitForTimeout(1000);
      
      await page.click('.el-dropdown:has-text("导出数据")');
      
      const downloadPromise = page.waitForEvent('download');
      await page.click('.el-dropdown-item:has-text("导出为 CSV")');
      
      const download = await downloadPromise;
      expect(download.suggestedFilename()).toContain('.csv');
    });
  });

  test.describe('响应式设计', () => {
    test('应该在移动端正常显示', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      
      await page.reload();
      await page.waitForLoadState('networkidle');
      
      const dataAnalysis = page.locator('.data-analysis');
      await expect(dataAnalysis).toBeVisible();
    });

    test('应该在平板端正常显示', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      
      await page.reload();
      await page.waitForLoadState('networkidle');
      
      const dataAnalysis = page.locator('.data-analysis');
      await expect(dataAnalysis).toBeVisible();
    });
  });

  test.describe('错误处理', () => {
    test('应该在没有数据时显示警告', async ({ page }) => {
      await page.click('button:has-text("应用平滑")');
      
      await expect(page.locator('.el-message--warning')).toBeVisible();
    });

    test('应该在模型选择不足时显示警告', async ({ page }) => {
      await page.click('.el-tabs__item:has-text("磁滞回线分析")');
      await page.click('button:has-text("生成示例数据")');
      await page.waitForTimeout(1000);
      
      await page.click('.el-tabs__item:has-text("多模型对比")');
      
      const checkboxes = page.locator('.el-checkbox');
      const count = await checkboxes.count();
      
      for (let i = 0; i < count; i++) {
        await checkboxes.nth(i).click();
      }
      
      await page.click('button:has-text("执行多模型拟合")');
      
      const button = page.locator('button:has-text("执行多模型拟合")');
      await expect(button).toBeDisabled();
    });
  });

  test.describe('性能测试', () => {
    test('应该快速加载页面', async ({ page }) => {
      const startTime = Date.now();
      
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      
      const loadTime = Date.now() - startTime;
      
      expect(loadTime).toBeLessThan(3000);
    });

    test('应该流畅处理大数据量', async ({ page }) => {
      await page.click('button:has-text("生成示例数据")');
      
      const startTime = Date.now();
      await page.waitForTimeout(1000);
      
      await page.click('button:has-text("应用平滑")');
      await page.waitForTimeout(3000);
      
      const processTime = Date.now() - startTime;
      
      expect(processTime).toBeLessThan(10000);
    });
  });
});
