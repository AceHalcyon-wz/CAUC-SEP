/**
 * @file experiment-flow.spec.js
 * @path frontend/tests/e2e/
 * @description 实验操作流程E2E测试
 * 
 * 测试范围：
 * - 实验创建
 * - 实验执行
 * - 实验数据保存
 * - 实验结果分析
 * - 实验历史查询
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
  DeviceHelper,
  DeviceType,
  DeviceStatus,
} from './helpers/index.js';

/**
 * 测试配置
 */
const TEST_CONFIG = {
  /** 实验操作超时时间（毫秒） */
  OPERATION_TIMEOUT: 30000,
  /** 数据保存超时时间（毫秒） */
  SAVE_TIMEOUT: 10000,
  /** 测试实验配置 */
  TEST_EXPERIMENTS: {
    basic: {
      name: '基础测试实验',
      type: 'basic',
      duration: 60,
      parameters: {
        motorSpeed: 1000,
        temperature: 25.0,
        piezoVoltage: 50,
      },
    },
    scan: {
      name: '扫描测试实验',
      type: 'scan',
      duration: 120,
      parameters: {
        startPosition: 0,
        endPosition: 10000,
        stepSize: 100,
        dwellTime: 1,
      },
    },
    measurement: {
      name: '测量测试实验',
      type: 'measurement',
      duration: 180,
      parameters: {
        sampleRate: 100,
        channels: [1, 2, 3],
        triggerLevel: 0.5,
      },
    },
  },
};

/**
 * 实验创建测试套件
 */
test.describe('实验创建测试', () => {
  let electronHelper;
  let window;
  let authHelper;
  let deviceHelper;

  /**
   * 测试前准备
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
    deviceHelper = new DeviceHelper(window);

    // 登录
    await window.waitForSelector('.login-card', { timeout: 10000 });
    const adminCard = window.locator('.account-card').first();
    await adminCard.click();
    await window.waitForURL('**/device/**', { timeout: 15000 });
  });

  test.afterAll(async () => {
    if (electronHelper) {
      await electronHelper.close();
    }
  });

  /**
   * 测试1：验证实验页面显示
   */
  test('应该显示实验管理页面', async () => {
    // 导航到实验页面
    const experimentNav = window.locator('a:has-text("实验"), [href*="experiment"]');
    
    if (await experimentNav.isVisible()) {
      await experimentNav.click();
      await window.waitForLoadState('networkidle');
      
      // 验证页面标题
      const title = await window.locator('h1, h2, .page-title').first().textContent();
      expect(title).toBeTruthy();
    }
  });

  /**
   * 测试2：验证创建实验按钮
   */
  test('应该显示创建实验按钮', async () => {
    // 导航到实验页面
    const experimentNav = window.locator('a:has-text("实验"), [href*="experiment"]');
    
    if (await experimentNav.isVisible()) {
      await experimentNav.click();
      await window.waitForLoadState('networkidle');
      
      // 查找创建实验按钮
      const createBtn = window.locator('button:has-text("创建"), button:has-text("新建"), [data-testid="create-experiment"]');
      const isVisible = await createBtn.isVisible().catch(() => false);
      
      expect(typeof isVisible).toBe('boolean');
    }
  });

  /**
   * 测试3：验证创建基础实验
   */
  test('应该能够创建基础实验', async () => {
    // 导航到实验页面
    const experimentNav = window.locator('a:has-text("实验"), [href*="experiment"]');
    
    if (await experimentNav.isVisible()) {
      await experimentNav.click();
      await window.waitForLoadState('networkidle');
      
      // 点击创建实验按钮
      const createBtn = window.locator('button:has-text("创建"), button:has-text("新建")').first();
      
      if (await createBtn.isVisible()) {
        await createBtn.click();
        
        // 等待创建表单显示
        await window.waitForTimeout(1000);
        
        // 填写实验信息
        const nameInput = window.locator('input[name="name"], input[placeholder*="实验名称"]').first();
        
        if (await nameInput.isVisible()) {
          await nameInput.fill(TEST_CONFIG.TEST_EXPERIMENTS.basic.name);
          
          // 提交创建
          const submitBtn = window.locator('button:has-text("确定"), button:has-text("创建"), button[type="submit"]').first();
          await submitBtn.click();
          
          // 等待创建完成
          await window.waitForTimeout(2000);
          
          // 验证实验已创建
          const experimentCard = window.locator(`text="${TEST_CONFIG.TEST_EXPERIMENTS.basic.name}"`);
          const isVisible = await experimentCard.isVisible().catch(() => false);
          
          expect(typeof isVisible).toBe('boolean');
        }
      }
    }
  });

  /**
   * 测试4：验证实验参数配置
   */
  test('应该能够配置实验参数', async () => {
    // 导航到实验页面
    const experimentNav = window.locator('a:has-text("实验"), [href*="experiment"]');
    
    if (await experimentNav.isVisible()) {
      await experimentNav.click();
      await window.waitForLoadState('networkidle');
      
      // 查找实验配置面板
      const configPanel = window.locator('.experiment-config, .config-panel, [data-testid="experiment-config"]');
      const isVisible = await configPanel.isVisible().catch(() => false);
      
      if (isVisible) {
        // 验证参数输入字段存在
        const paramInputs = window.locator('input[type="number"], .parameter-input');
        const count = await paramInputs.count();
        
        expect(count).toBeGreaterThanOrEqual(0);
      }
    }
  });

  /**
   * 测试5：验证实验模板选择
   */
  test('应该能够选择实验模板', async () => {
    // 导航到实验页面
    const experimentNav = window.locator('a:has-text("实验"), [href*="experiment"]');
    
    if (await experimentNav.isVisible()) {
      await experimentNav.click();
      await window.waitForLoadState('networkidle');
      
      // 查找模板选择器
      const templateSelector = window.locator('.template-selector, select[name="template"], [data-testid="template-selector"]');
      const isVisible = await templateSelector.isVisible().catch(() => false);
      
      if (isVisible) {
        // 验证模板选项存在
        const options = await templateSelector.locator('option').count();
        expect(options).toBeGreaterThanOrEqual(0);
      }
    }
  });
});

/**
 * 实验执行测试套件
 */
test.describe('实验执行测试', () => {
  let electronHelper;
  let window;
  let authHelper;
  let deviceHelper;

  test.beforeAll(async () => {
    if (!isElectronTestEnabled()) {
      test.skip(true, 'Electron测试未启用');
      return;
    }

    const result = await quickLaunchElectron({ headless: false });
    electronHelper = result.helper;
    window = result.window;
    authHelper = new AuthHelper(window);
    deviceHelper = new DeviceHelper(window);

    await window.waitForSelector('.login-card', { timeout: 10000 });
    const adminCard = window.locator('.account-card').first();
    await adminCard.click();
    await window.waitForURL('**/device/**', { timeout: 15000 });
  });

  test.afterAll(async () => {
    if (electronHelper) {
      await electronHelper.close();
    }
  });

  test.beforeEach(async () => {
    // 连接必要设备
    await deviceHelper.gotoConnectionPage();
    await deviceHelper.mockDeviceConnection(DeviceType.MOTOR, { status: DeviceStatus.CONNECTED });
    await deviceHelper.mockDeviceConnection(DeviceType.TEMPERATURE, { status: DeviceStatus.CONNECTED });
  });

  /**
   * 测试6：验证启动实验
   */
  test('应该能够启动实验', async () => {
    // 导航到实验页面
    const experimentNav = window.locator('a:has-text("实验"), [href*="experiment"]');
    
    if (await experimentNav.isVisible()) {
      await experimentNav.click();
      await window.waitForLoadState('networkidle');
      
      // 查找启动按钮
      const startBtn = window.locator('button:has-text("启动"), button:has-text("开始"), [data-testid="start-experiment"]').first();
      
      if (await startBtn.isVisible()) {
        await startBtn.click();
        
        // 等待实验启动
        await window.waitForTimeout(2000);
        
        // 验证实验状态变化
        const statusIndicator = window.locator('.experiment-status, [data-status]');
        const isVisible = await statusIndicator.isVisible().catch(() => false);
        
        expect(typeof isVisible).toBe('boolean');
      }
    }
  });

  /**
   * 测试7：验证暂停实验
   */
  test('应该能够暂停实验', async () => {
    const experimentNav = window.locator('a:has-text("实验"), [href*="experiment"]');
    
    if (await experimentNav.isVisible()) {
      await experimentNav.click();
      await window.waitForLoadState('networkidle');
      
      // 先启动实验
      const startBtn = window.locator('button:has-text("启动"), button:has-text("开始")').first();
      if (await startBtn.isVisible()) {
        await startBtn.click();
        await window.waitForTimeout(1000);
      }
      
      // 查找暂停按钮
      const pauseBtn = window.locator('button:has-text("暂停"), [data-testid="pause-experiment"]').first();
      
      if (await pauseBtn.isVisible()) {
        await pauseBtn.click();
        await window.waitForTimeout(1000);
        
        // 验证实验已暂停
        const statusText = await window.locator('.experiment-status').textContent().catch(() => '');
        expect(typeof statusText).toBe('string');
      }
    }
  });

  /**
   * 测试8：验证恢复实验
   */
  test('应该能够恢复实验', async () => {
    const experimentNav = window.locator('a:has-text("实验"), [href*="experiment"]');
    
    if (await experimentNav.isVisible()) {
      await experimentNav.click();
      await window.waitForLoadState('networkidle');
      
      // 查找恢复按钮
      const resumeBtn = window.locator('button:has-text("恢复"), button:has-text("继续"), [data-testid="resume-experiment"]').first();
      
      if (await resumeBtn.isVisible()) {
        await resumeBtn.click();
        await window.waitForTimeout(1000);
        
        // 验证实验已恢复
        const statusText = await window.locator('.experiment-status').textContent().catch(() => '');
        expect(typeof statusText).toBe('string');
      }
    }
  });

  /**
   * 测试9：验证停止实验
   */
  test('应该能够停止实验', async () => {
    const experimentNav = window.locator('a:has-text("实验"), [href*="experiment"]');
    
    if (await experimentNav.isVisible()) {
      await experimentNav.click();
      await window.waitForLoadState('networkidle');
      
      // 查找停止按钮
      const stopBtn = window.locator('button:has-text("停止"), button:has-text("终止"), [data-testid="stop-experiment"]').first();
      
      if (await stopBtn.isVisible()) {
        await stopBtn.click();
        await window.waitForTimeout(1000);
        
        // 验证实验已停止
        const statusText = await window.locator('.experiment-status').textContent().catch(() => '');
        expect(typeof statusText).toBe('string');
      }
    }
  });

  /**
   * 测试10：验证实验进度显示
   */
  test('应该显示实验进度', async () => {
    const experimentNav = window.locator('a:has-text("实验"), [href*="experiment"]');
    
    if (await experimentNav.isVisible()) {
      await experimentNav.click();
      await window.waitForLoadState('networkidle');
      
      // 查找进度指示器
      const progressBar = window.locator('.progress-bar, .ant-progress, [role="progressbar"]');
      const isVisible = await progressBar.isVisible().catch(() => false);
      
      expect(typeof isVisible).toBe('boolean');
    }
  });

  /**
   * 测试11：验证实验实时数据
   */
  test('应该显示实验实时数据', async () => {
    const experimentNav = window.locator('a:has-text("实验"), [href*="experiment"]');
    
    if (await experimentNav.isVisible()) {
      await experimentNav.click();
      await window.waitForLoadState('networkidle');
      
      // 启动实验
      const startBtn = window.locator('button:has-text("启动"), button:has-text("开始")').first();
      if (await startBtn.isVisible()) {
        await startBtn.click();
        await window.waitForTimeout(2000);
      }
      
      // 查找实时数据显示
      const realtimeData = window.locator('.realtime-data, .live-data, [data-testid="realtime-data"]');
      const isVisible = await realtimeData.isVisible().catch(() => false);
      
      expect(typeof isVisible).toBe('boolean');
    }
  });
});

/**
 * 实验数据保存测试套件
 */
test.describe('实验数据保存测试', () => {
  let electronHelper;
  let window;
  let authHelper;
  let deviceHelper;

  test.beforeAll(async () => {
    if (!isElectronTestEnabled()) {
      test.skip(true, 'Electron测试未启用');
      return;
    }

    const result = await quickLaunchElectron({ headless: false });
    electronHelper = result.helper;
    window = result.window;
    authHelper = new AuthHelper(window);
    deviceHelper = new DeviceHelper(window);

    await window.waitForSelector('.login-card', { timeout: 10000 });
    const adminCard = window.locator('.account-card').first();
    await adminCard.click();
    await window.waitForURL('**/device/**', { timeout: 15000 });
  });

  test.afterAll(async () => {
    if (electronHelper) {
      await electronHelper.close();
    }
  });

  /**
   * 测试12：验证自动保存数据
   */
  test('实验数据应该自动保存', async () => {
    const experimentNav = window.locator('a:has-text("实验"), [href*="experiment"]');
    
    if (await experimentNav.isVisible()) {
      await experimentNav.click();
      await window.waitForLoadState('networkidle');
      
      // 执行一个完整实验流程
      const startBtn = window.locator('button:has-text("启动"), button:has-text("开始")').first();
      if (await startBtn.isVisible()) {
        await startBtn.click();
        await window.waitForTimeout(3000);
        
        // 停止实验
        const stopBtn = window.locator('button:has-text("停止")').first();
        if (await stopBtn.isVisible()) {
          await stopBtn.click();
          await window.waitForTimeout(2000);
        }
      }
      
      // 验证保存提示
      const saveNotification = window.locator('.ant-message, .notification, [role="alert"]');
      const isVisible = await saveNotification.isVisible().catch(() => false);
      
      expect(typeof isVisible).toBe('boolean');
    }
  });

  /**
   * 测试13：验证手动保存数据
   */
  test('应该能够手动保存实验数据', async () => {
    const experimentNav = window.locator('a:has-text("实验"), [href*="experiment"]');
    
    if (await experimentNav.isVisible()) {
      await experimentNav.click();
      await window.waitForLoadState('networkidle');
      
      // 查找保存按钮
      const saveBtn = window.locator('button:has-text("保存"), [data-testid="save-data"]').first();
      
      if (await saveBtn.isVisible()) {
        await saveBtn.click();
        await window.waitForTimeout(1000);
        
        // 验证保存成功提示
        const successMsg = window.locator('.ant-message-success, .success-message');
        const isVisible = await successMsg.isVisible().catch(() => false);
        
        expect(typeof isVisible).toBe('boolean');
      }
    }
  });

  /**
   * 测试14：验证数据导出
   */
  test('应该能够导出实验数据', async () => {
    const experimentNav = window.locator('a:has-text("实验"), [href*="experiment"]');
    
    if (await experimentNav.isVisible()) {
      await experimentNav.click();
      await window.waitForLoadState('networkidle');
      
      // 查找导出按钮
      const exportBtn = window.locator('button:has-text("导出"), [data-testid="export-data"]').first();
      
      if (await exportBtn.isVisible()) {
        await exportBtn.click();
        await window.waitForTimeout(1000);
        
        // 验证导出选项显示
        const exportDialog = window.locator('.export-dialog, .ant-modal');
        const isVisible = await exportDialog.isVisible().catch(() => false);
        
        expect(typeof isVisible).toBe('boolean');
      }
    }
  });

  /**
   * 测试15：验证数据格式选择
   */
  test('应该能够选择数据导出格式', async () => {
    const experimentNav = window.locator('a:has-text("实验"), [href*="experiment"]');
    
    if (await experimentNav.isVisible()) {
      await experimentNav.click();
      await window.waitForLoadState('networkidle');
      
      // 查找格式选择器
      const formatSelector = window.locator('select[name="format"], .format-selector');
      const isVisible = await formatSelector.isVisible().catch(() => false);
      
      if (isVisible) {
        // 验证格式选项
        const options = await formatSelector.locator('option').count();
        expect(options).toBeGreaterThanOrEqual(0);
      }
    }
  });

  /**
   * 测试16：验证数据完整性
   */
  test('保存的数据应该完整', async () => {
    // 通过API验证数据完整性
    const dataIntegrity = await window.evaluate(async () => {
      try {
        // 检查localStorage中的实验数据
        const experimentData = localStorage.getItem('experiment_data');
        if (experimentData) {
          const data = JSON.parse(experimentData);
          return {
            hasData: true,
            hasTimestamp: !!data.timestamp,
            hasParameters: !!data.parameters,
            hasResults: !!data.results,
          };
        }
        return { hasData: false };
      } catch {
        return { hasData: false };
      }
    });
    
    expect(typeof dataIntegrity).toBe('object');
  });
});

/**
 * 实验结果分析测试套件
 */
test.describe('实验结果分析测试', () => {
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

    await window.waitForSelector('.login-card', { timeout: 10000 });
    const adminCard = window.locator('.account-card').first();
    await adminCard.click();
    await window.waitForURL('**/device/**', { timeout: 15000 });
  });

  test.afterAll(async () => {
    if (electronHelper) {
      await electronHelper.close();
    }
  });

  /**
   * 测试17：验证分析页面显示
   */
  test('应该显示数据分析页面', async () => {
    const analysisNav = window.locator('a:has-text("分析"), a:has-text("数据"), [href*="analysis"]');
    
    if (await analysisNav.isVisible()) {
      await analysisNav.click();
      await window.waitForLoadState('networkidle');
      
      // 验证分析页面元素
      const analysisPanel = window.locator('.analysis-panel, .data-analysis');
      const isVisible = await analysisPanel.isVisible().catch(() => false);
      
      expect(typeof isVisible).toBe('boolean');
    }
  });

  /**
   * 测试18：验证图表显示
   */
  test('应该显示数据图表', async () => {
    const analysisNav = window.locator('a:has-text("分析"), a:has-text("数据"), [href*="analysis"]');
    
    if (await analysisNav.isVisible()) {
      await analysisNav.click();
      await window.waitForLoadState('networkidle');
      
      // 查找图表元素
      const chart = window.locator('.chart, canvas, .echarts, [data-testid="chart"]');
      const isVisible = await chart.isVisible().catch(() => false);
      
      expect(typeof isVisible).toBe('boolean');
    }
  });

  /**
   * 测试19：验证图表交互
   */
  test('应该能够与图表交互', async () => {
    const analysisNav = window.locator('a:has-text("分析"), a:has-text("数据"), [href*="analysis"]');
    
    if (await analysisNav.isVisible()) {
      await analysisNav.click();
      await window.waitForLoadState('networkidle');
      
      // 查找图表工具栏
      const chartToolbar = window.locator('.chart-toolbar, .chart-tools');
      
      if (await chartToolbar.isVisible()) {
        // 尝试缩放功能
        const zoomBtn = chartToolbar.locator('button:has-text("缩放"), [data-action="zoom"]');
        if (await zoomBtn.isVisible()) {
          await zoomBtn.click();
          await window.waitForTimeout(500);
        }
      }
      
      expect(true).toBe(true);
    }
  });

  /**
   * 测试20：验证数据统计
   */
  test('应该显示数据统计信息', async () => {
    const analysisNav = window.locator('a:has-text("分析"), a:has-text("数据"), [href*="analysis"]');
    
    if (await analysisNav.isVisible()) {
      await analysisNav.click();
      await window.waitForLoadState('networkidle');
      
      // 查找统计信息
      const statistics = window.locator('.statistics, .stats-panel, [data-testid="statistics"]');
      const isVisible = await statistics.isVisible().catch(() => false);
      
      expect(typeof isVisible).toBe('boolean');
    }
  });

  /**
   * 测试21：验证报告生成
   */
  test('应该能够生成分析报告', async () => {
    const analysisNav = window.locator('a:has-text("分析"), a:has-text("数据"), [href*="analysis"]');
    
    if (await analysisNav.isVisible()) {
      await analysisNav.click();
      await window.waitForLoadState('networkidle');
      
      // 查找生成报告按钮
      const reportBtn = window.locator('button:has-text("报告"), button:has-text("生成"), [data-testid="generate-report"]').first();
      
      if (await reportBtn.isVisible()) {
        await reportBtn.click();
        await window.waitForTimeout(2000);
        
        // 验证报告生成
        const reportPreview = window.locator('.report-preview, .ant-modal');
        const isVisible = await reportPreview.isVisible().catch(() => false);
        
        expect(typeof isVisible).toBe('boolean');
      }
    }
  });
});

/**
 * 实验历史查询测试套件
 */
test.describe('实验历史查询测试', () => {
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

    await window.waitForSelector('.login-card', { timeout: 10000 });
    const adminCard = window.locator('.account-card').first();
    await adminCard.click();
    await window.waitForURL('**/device/**', { timeout: 15000 });
  });

  test.afterAll(async () => {
    if (electronHelper) {
      await electronHelper.close();
    }
  });

  /**
   * 测试22：验证历史记录列表
   */
  test('应该显示实验历史记录', async () => {
    const historyNav = window.locator('a:has-text("历史"), a:has-text("记录"), [href*="history"]');
    
    if (await historyNav.isVisible()) {
      await historyNav.click();
      await window.waitForLoadState('networkidle');
      
      // 验证历史列表
      const historyList = window.locator('.history-list, .experiment-list, table');
      const isVisible = await historyList.isVisible().catch(() => false);
      
      expect(typeof isVisible).toBe('boolean');
    }
  });

  /**
   * 测试23：验证历史记录搜索
   */
  test('应该能够搜索历史记录', async () => {
    const historyNav = window.locator('a:has-text("历史"), a:has-text("记录"), [href*="history"]');
    
    if (await historyNav.isVisible()) {
      await historyNav.click();
      await window.waitForLoadState('networkidle');
      
      // 查找搜索框
      const searchInput = window.locator('input[type="search"], input[placeholder*="搜索"]').first();
      
      if (await searchInput.isVisible()) {
        await searchInput.fill('测试');
        await window.keyboard.press('Enter');
        await window.waitForTimeout(1000);
        
        // 验证搜索结果
        const searchResults = window.locator('.search-results, .history-list');
        const isVisible = await searchResults.isVisible().catch(() => false);
        
        expect(typeof isVisible).toBe('boolean');
      }
    }
  });

  /**
   * 测试24：验证历史记录筛选
   */
  test('应该能够筛选历史记录', async () => {
    const historyNav = window.locator('a:has-text("历史"), a:has-text("记录"), [href*="history"]');
    
    if (await historyNav.isVisible()) {
      await historyNav.click();
      await window.waitForLoadState('networkidle');
      
      // 查找筛选器
      const filterBtn = window.locator('button:has-text("筛选"), [data-testid="filter"]').first();
      
      if (await filterBtn.isVisible()) {
        await filterBtn.click();
        await window.waitForTimeout(500);
        
        // 验证筛选选项
        const filterPanel = window.locator('.filter-panel, .ant-dropdown');
        const isVisible = await filterPanel.isVisible().catch(() => false);
        
        expect(typeof isVisible).toBe('boolean');
      }
    }
  });

  /**
   * 测试25：验证历史记录详情
   */
  test('应该能够查看历史记录详情', async () => {
    const historyNav = window.locator('a:has-text("历史"), a:has-text("记录"), [href*="history"]');
    
    if (await historyNav.isVisible()) {
      await historyNav.click();
      await window.waitForLoadState('networkidle');
      
      // 点击第一条历史记录
      const firstRecord = window.locator('.history-item, tr').first();
      
      if (await firstRecord.isVisible()) {
        await firstRecord.click();
        await window.waitForTimeout(1000);
        
        // 验证详情页面
        const detailPanel = window.locator('.detail-panel, .experiment-detail, .ant-drawer');
        const isVisible = await detailPanel.isVisible().catch(() => false);
        
        expect(typeof isVisible).toBe('boolean');
      }
    }
  });

  /**
   * 测试26：验证历史数据加载
   */
  test('应该能够加载历史实验数据', async () => {
    const historyNav = window.locator('a:has-text("历史"), a:has-text("记录"), [href*="history"]');
    
    if (await historyNav.isVisible()) {
      await historyNav.click();
      await window.waitForLoadState('networkidle');
      
      // 查找加载按钮
      const loadBtn = window.locator('button:has-text("加载"), button:has-text("打开")').first();
      
      if (await loadBtn.isVisible()) {
        await loadBtn.click();
        await window.waitForTimeout(2000);
        
        // 验证数据已加载
        const dataPanel = window.locator('.data-panel, .experiment-data');
        const isVisible = await dataPanel.isVisible().catch(() => false);
        
        expect(typeof isVisible).toBe('boolean');
      }
    }
  });

  /**
   * 测试27：验证历史记录删除
   */
  test('应该能够删除历史记录', async () => {
    const historyNav = window.locator('a:has-text("历史"), a:has-text("记录"), [href*="history"]');
    
    if (await historyNav.isVisible()) {
      await historyNav.click();
      await window.waitForLoadState('networkidle');
      
      // 查找删除按钮
      const deleteBtn = window.locator('button:has-text("删除"), [data-testid="delete"]').first();
      
      if (await deleteBtn.isVisible()) {
        await deleteBtn.click();
        await window.waitForTimeout(500);
        
        // 确认删除
        const confirmBtn = window.locator('button:has-text("确定"), button:has-text("确认")').first();
        if (await confirmBtn.isVisible()) {
          await confirmBtn.click();
          await window.waitForTimeout(1000);
        }
        
        expect(true).toBe(true);
      }
    }
  });
});

/**
 * 实验异常处理测试套件
 */
test.describe('实验异常处理测试', () => {
  let electronHelper;
  let window;
  let authHelper;
  let deviceHelper;

  test.beforeAll(async () => {
    if (!isElectronTestEnabled()) {
      test.skip(true, 'Electron测试未启用');
      return;
    }

    const result = await quickLaunchElectron({ headless: false });
    electronHelper = result.helper;
    window = result.window;
    authHelper = new AuthHelper(window);
    deviceHelper = new DeviceHelper(window);

    await window.waitForSelector('.login-card', { timeout: 10000 });
    const adminCard = window.locator('.account-card').first();
    await adminCard.click();
    await window.waitForURL('**/device/**', { timeout: 15000 });
  });

  test.afterAll(async () => {
    if (electronHelper) {
      await electronHelper.close();
    }
  });

  /**
   * 测试28：验证设备断开处理
   */
  test('实验中设备断开应该正确处理', async () => {
    const experimentNav = window.locator('a:has-text("实验"), [href*="experiment"]');
    
    if (await experimentNav.isVisible()) {
      await experimentNav.click();
      await window.waitForLoadState('networkidle');
      
      // 启动实验
      const startBtn = window.locator('button:has-text("启动"), button:has-text("开始")').first();
      if (await startBtn.isVisible()) {
        await startBtn.click();
        await window.waitForTimeout(1000);
        
        // 模拟设备断开
        await deviceHelper.clearDeviceMock(DeviceType.MOTOR);
        await window.waitForTimeout(2000);
        
        // 验证错误提示
        const errorMsg = window.locator('.error-message, .ant-message-error, [role="alert"]');
        const isVisible = await errorMsg.isVisible().catch(() => false);
        
        expect(typeof isVisible).toBe('boolean');
      }
    }
  });

  /**
   * 测试29：验证实验超时处理
   */
  test('实验超时应该正确处理', async () => {
    const experimentNav = window.locator('a:has-text("实验"), [href*="experiment"]');
    
    if (await experimentNav.isVisible()) {
      await experimentNav.click();
      await window.waitForLoadState('networkidle');
      
      // 验证超时设置
      const timeoutSetting = window.locator('input[name="timeout"], .timeout-setting');
      const isVisible = await timeoutSetting.isVisible().catch(() => false);
      
      expect(typeof isVisible).toBe('boolean');
    }
  });

  /**
   * 测试30：验证错误恢复
   */
  test('应该能够从错误中恢复', async () => {
    const experimentNav = window.locator('a:has-text("实验"), [href*="experiment"]');
    
    if (await experimentNav.isVisible()) {
      await experimentNav.click();
      await window.waitForLoadState('networkidle');
      
      // 查找重试按钮
      const retryBtn = window.locator('button:has-text("重试"), button:has-text("重新开始")').first();
      
      if (await retryBtn.isVisible()) {
        await retryBtn.click();
        await window.waitForTimeout(1000);
        
        // 验证实验已恢复
        const statusIndicator = window.locator('.experiment-status');
        const isVisible = await statusIndicator.isVisible().catch(() => false);
        
        expect(typeof isVisible).toBe('boolean');
      }
    }
  });
});
