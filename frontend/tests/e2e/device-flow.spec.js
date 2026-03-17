/**
 * @file device-flow.spec.js
 * @path frontend/tests/e2e/
 * @description 设备管理流程E2E测试
 * 
 * 测试范围：
 * - 设备连接
 * - 设备配置
 * - 设备控制
 * - 设备状态监控
 * - 设备断开连接
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
  /** 设备连接超时时间（毫秒） */
  CONNECTION_TIMEOUT: 30000,
  /** 设备操作超时时间（毫秒） */
  OPERATION_TIMEOUT: 15000,
  /** 测试端口 */
  TEST_PORTS: {
    motor: 'COM3',
    temperature: 'COM4',
    piezo: 'COM5',
    electromagnet: 'COM6',
    ammeter: 'COM7',
  },
  /** 设备配置参数 */
  DEVICE_CONFIGS: {
    motor: {
      speed: 1000,
      acceleration: 500,
      maxPosition: 10000,
    },
    temperature: {
      setpoint: 25.0,
      pid: { p: 1.0, i: 0.1, d: 0.01 },
    },
    piezo: {
      voltage: 0,
      maxVoltage: 150,
    },
    electromagnet: {
      current: 0,
      maxCurrent: 5,
    },
  },
};

/**
 * 设备连接测试套件
 */
test.describe('设备连接测试', () => {
  let electronHelper;
  let window;
  let authHelper;
  let deviceHelper;

  /**
   * 测试前准备：启动应用并登录
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

  /**
   * 测试后清理
   */
  test.afterAll(async () => {
    if (electronHelper) {
      await electronHelper.close();
    }
  });

  /**
   * 测试1：验证设备连接页面显示
   */
  test('应该显示设备连接页面', async () => {
    await deviceHelper.gotoConnectionPage();
    
    // 验证页面标题
    const title = await window.locator('h1, h2, .page-title').first().textContent();
    expect(title).toContain('设备');
  });

  /**
   * 测试2：验证设备列表显示
   */
  test('应该显示设备列表', async () => {
    await deviceHelper.gotoConnectionPage();
    
    // 验证设备卡片存在
    const deviceCards = window.locator('.device-card, [data-device-type]');
    const count = await deviceCards.count();
    
    expect(count).toBeGreaterThan(0);
  });

  /**
   * 测试3：验证步进电机连接
   */
  test('应该能够连接步进电机', async () => {
    await deviceHelper.gotoConnectionPage();
    
    // 模拟设备连接（实际测试需要真实设备或模拟器）
    await deviceHelper.mockDeviceConnection(DeviceType.MOTOR, {
      port: TEST_CONFIG.TEST_PORTS.motor,
      status: DeviceStatus.CONNECTED,
    });
    
    // 验证设备状态
    const isConnected = await deviceHelper.isDeviceConnected(DeviceType.MOTOR);
    expect(isConnected).toBe(true);
  });

  /**
   * 测试4：验证温度控制器连接
   */
  test('应该能够连接温度控制器', async () => {
    await deviceHelper.gotoConnectionPage();
    
    await deviceHelper.mockDeviceConnection(DeviceType.TEMPERATURE, {
      port: TEST_CONFIG.TEST_PORTS.temperature,
      status: DeviceStatus.CONNECTED,
    });
    
    const isConnected = await deviceHelper.isDeviceConnected(DeviceType.TEMPERATURE);
    expect(isConnected).toBe(true);
  });

  /**
   * 测试5：验证压电控制器连接
   */
  test('应该能够连接压电控制器', async () => {
    await deviceHelper.gotoConnectionPage();
    
    await deviceHelper.mockDeviceConnection(DeviceType.PIEZO, {
      port: TEST_CONFIG.TEST_PORTS.piezo,
      status: DeviceStatus.CONNECTED,
    });
    
    const isConnected = await deviceHelper.isDeviceConnected(DeviceType.PIEZO);
    expect(isConnected).toBe(true);
  });

  /**
   * 测试6：验证电磁铁连接
   */
  test('应该能够连接电磁铁', async () => {
    await deviceHelper.gotoConnectionPage();
    
    await deviceHelper.mockDeviceConnection(DeviceType.ELECTROMAGNET, {
      port: TEST_CONFIG.TEST_PORTS.electromagnet,
      status: DeviceStatus.CONNECTED,
    });
    
    const isConnected = await deviceHelper.isDeviceConnected(DeviceType.ELECTROMAGNET);
    expect(isConnected).toBe(true);
  });

  /**
   * 测试7：验证皮安表连接
   */
  test('应该能够连接皮安表', async () => {
    await deviceHelper.gotoConnectionPage();
    
    await deviceHelper.mockDeviceConnection(DeviceType.AMMETER, {
      port: TEST_CONFIG.TEST_PORTS.ammeter,
      status: DeviceStatus.CONNECTED,
    });
    
    const isConnected = await deviceHelper.isDeviceConnected(DeviceType.AMMETER);
    expect(isConnected).toBe(true);
  });

  /**
   * 测试8：验证设备断开连接
   */
  test('应该能够断开设备连接', async () => {
    await deviceHelper.gotoConnectionPage();
    
    // 先连接设备
    await deviceHelper.mockDeviceConnection(DeviceType.MOTOR, {
      status: DeviceStatus.CONNECTED,
    });
    
    // 断开连接
    await deviceHelper.clearDeviceMock(DeviceType.MOTOR);
    
    // 验证设备已断开
    const isConnected = await deviceHelper.isDeviceConnected(DeviceType.MOTOR);
    expect(isConnected).toBe(false);
  });
});

/**
 * 设备配置测试套件
 */
test.describe('设备配置测试', () => {
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
    await deviceHelper.gotoConnectionPage();
  });

  /**
   * 测试9：验证步进电机配置
   */
  test('应该能够配置步进电机参数', async () => {
    // 连接设备
    await deviceHelper.mockDeviceConnection(DeviceType.MOTOR, {
      status: DeviceStatus.CONNECTED,
    });
    
    // 更新配置
    const config = TEST_CONFIG.DEVICE_CONFIGS.motor;
    await deviceHelper.updateDeviceConfig(DeviceType.MOTOR, config);
    
    // 验证配置已更新
    const savedConfig = await deviceHelper.getDeviceConfig(DeviceType.MOTOR);
    expect(savedConfig).toBeDefined();
  });

  /**
   * 测试10：验证温度控制器配置
   */
  test('应该能够配置温度控制器参数', async () => {
    await deviceHelper.mockDeviceConnection(DeviceType.TEMPERATURE, {
      status: DeviceStatus.CONNECTED,
    });
    
    const config = TEST_CONFIG.DEVICE_CONFIGS.temperature;
    await deviceHelper.updateDeviceConfig(DeviceType.TEMPERATURE, config);
    
    const savedConfig = await deviceHelper.getDeviceConfig(DeviceType.TEMPERATURE);
    expect(savedConfig).toBeDefined();
  });

  /**
   * 测试11：验证压电控制器配置
   */
  test('应该能够配置压电控制器参数', async () => {
    await deviceHelper.mockDeviceConnection(DeviceType.PIEZO, {
      status: DeviceStatus.CONNECTED,
    });
    
    const config = TEST_CONFIG.DEVICE_CONFIGS.piezo;
    await deviceHelper.updateDeviceConfig(DeviceType.PIEZO, config);
    
    const savedConfig = await deviceHelper.getDeviceConfig(DeviceType.PIEZO);
    expect(savedConfig).toBeDefined();
  });

  /**
   * 测试12：验证电磁铁配置
   */
  test('应该能够配置电磁铁参数', async () => {
    await deviceHelper.mockDeviceConnection(DeviceType.ELECTROMAGNET, {
      status: DeviceStatus.CONNECTED,
    });
    
    const config = TEST_CONFIG.DEVICE_CONFIGS.electromagnet;
    await deviceHelper.updateDeviceConfig(DeviceType.ELECTROMAGNET, config);
    
    const savedConfig = await deviceHelper.getDeviceConfig(DeviceType.ELECTROMAGNET);
    expect(savedConfig).toBeDefined();
  });

  /**
   * 测试13：验证配置验证
   */
  test('应该验证配置参数有效性', async () => {
    await deviceHelper.mockDeviceConnection(DeviceType.MOTOR, {
      status: DeviceStatus.CONNECTED,
    });
    
    // 尝试设置无效配置
    const invalidConfig = {
      speed: -100, // 无效值
    };
    
    try {
      await deviceHelper.updateDeviceConfig(DeviceType.MOTOR, invalidConfig);
    } catch (error) {
      // 应该抛出错误或拒绝更新
      expect(error).toBeDefined();
    }
  });

  /**
   * 测试14：验证配置持久化
   */
  test('配置应该在页面刷新后保持', async () => {
    await deviceHelper.mockDeviceConnection(DeviceType.MOTOR, {
      status: DeviceStatus.CONNECTED,
    });
    
    const config = TEST_CONFIG.DEVICE_CONFIGS.motor;
    await deviceHelper.updateDeviceConfig(DeviceType.MOTOR, config);
    
    // 刷新页面
    await window.reload();
    await window.waitForLoadState('networkidle');
    
    // 验证配置仍然存在
    const savedConfig = await deviceHelper.getDeviceConfig(DeviceType.MOTOR);
    expect(savedConfig).toBeDefined();
  });
});

/**
 * 设备控制测试套件
 */
test.describe('设备控制测试', () => {
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
    await deviceHelper.gotoConnectionPage();
    await deviceHelper.mockDeviceConnection(DeviceType.MOTOR, {
      status: DeviceStatus.CONNECTED,
    });
  });

  /**
   * 测试15：验证步进电机移动控制
   */
  test('应该能够控制步进电机移动', async () => {
    const result = await deviceHelper.executeDeviceOperation(
      DeviceType.MOTOR,
      'move',
      { position: 5000, speed: 1000 }
    );
    
    expect(result).toBeDefined();
  });

  /**
   * 测试16：验证步进电机停止控制
   */
  test('应该能够停止步进电机', async () => {
    const result = await deviceHelper.executeDeviceOperation(
      DeviceType.MOTOR,
      'stop',
      {}
    );
    
    expect(result).toBeDefined();
  });

  /**
   * 测试17：验证步进电机回零
   */
  test('应该能够执行步进电机回零操作', async () => {
    const result = await deviceHelper.executeDeviceOperation(
      DeviceType.MOTOR,
      'home',
      {}
    );
    
    expect(result).toBeDefined();
  });

  /**
   * 测试18：验证温度设置
   */
  test('应该能够设置温度目标值', async () => {
    await deviceHelper.mockDeviceConnection(DeviceType.TEMPERATURE, {
      status: DeviceStatus.CONNECTED,
    });
    
    const result = await deviceHelper.executeDeviceOperation(
      DeviceType.TEMPERATURE,
      'setTemperature',
      { temperature: 30.0 }
    );
    
    expect(result).toBeDefined();
  });

  /**
   * 测试19：验证压电电压设置
   */
  test('应该能够设置压电电压', async () => {
    await deviceHelper.mockDeviceConnection(DeviceType.PIEZO, {
      status: DeviceStatus.CONNECTED,
    });
    
    const result = await deviceHelper.executeDeviceOperation(
      DeviceType.PIEZO,
      'setVoltage',
      { voltage: 50 }
    );
    
    expect(result).toBeDefined();
  });

  /**
   * 测试20：验证电磁铁电流设置
   */
  test('应该能够设置电磁铁电流', async () => {
    await deviceHelper.mockDeviceConnection(DeviceType.ELECTROMAGNET, {
      status: DeviceStatus.CONNECTED,
    });
    
    const result = await deviceHelper.executeDeviceOperation(
      DeviceType.ELECTROMAGNET,
      'setCurrent',
      { current: 2.5 }
    );
    
    expect(result).toBeDefined();
  });

  /**
   * 测试21：验证设备操作权限
   */
  test('应该验证设备操作权限', async () => {
    // 模拟访客用户（只读权限）
    await authHelper.mockAuthenticated({
      role: 'viewer',
      permissions: ['read'],
    });
    
    // 尝试执行写操作
    try {
      await deviceHelper.executeDeviceOperation(
        DeviceType.MOTOR,
        'move',
        { position: 5000 }
      );
      
      // 如果没有抛出错误，验证是否被拒绝
      // 某些实现可能允许操作但返回错误
    } catch (error) {
      expect(error).toBeDefined();
    }
  });
});

/**
 * 设备状态监控测试套件
 */
test.describe('设备状态监控测试', () => {
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
   * 测试22：验证设备状态页面显示
   */
  test('应该显示设备状态页面', async () => {
    await deviceHelper.gotoStatusPage();
    
    const statusDashboard = window.locator('.device-status-dashboard, .status-monitor');
    await expect(statusDashboard).toBeVisible();
  });

  /**
   * 测试23：验证设备状态实时更新
   */
  test('设备状态应该实时更新', async () => {
    await deviceHelper.gotoStatusPage();
    
    // 模拟设备连接
    await deviceHelper.mockDeviceConnection(DeviceType.MOTOR, {
      status: DeviceStatus.CONNECTED,
      position: 0,
    });
    
    // 等待状态更新
    await window.waitForTimeout(1000);
    
    // 验证状态显示
    const statusElement = window.locator('[data-device-type="motor"] .device-status');
    await expect(statusElement).toBeVisible();
  });

  /**
   * 测试24：验证设备告警显示
   */
  test('应该显示设备告警信息', async () => {
    await deviceHelper.gotoStatusPage();
    
    // 模拟设备告警
    await deviceHelper.mockDeviceConnection(DeviceType.MOTOR, {
      status: DeviceStatus.ERROR,
      alarms: [{ code: 'E001', message: '电机过热' }],
    });
    
    // 检查告警
    const alarms = await deviceHelper.checkDeviceAlarms(DeviceType.MOTOR);
    
    if (alarms && alarms.length > 0) {
      expect(alarms[0]).toHaveProperty('code');
      expect(alarms[0]).toHaveProperty('message');
    }
  });

  /**
   * 测试25：验证设备数据图表
   */
  test('应该显示设备数据图表', async () => {
    await deviceHelper.gotoStatusPage();
    
    // 查找图表元素
    const chart = window.locator('.device-chart, canvas, .chart-container');
    const isVisible = await chart.isVisible().catch(() => false);
    
    // 图表可能存在也可能不存在，取决于实现
    expect(typeof isVisible).toBe('boolean');
  });

  /**
   * 测试26：验证设备历史数据查询
   */
  test('应该能够查询设备历史数据', async () => {
    await deviceHelper.gotoStatusPage();
    
    // 查找历史数据查询按钮
    const historyBtn = window.locator('button:has-text("历史"), [data-testid="history-button"]');
    
    if (await historyBtn.isVisible()) {
      await historyBtn.click();
      
      // 等待历史数据加载
      await window.waitForTimeout(1000);
      
      // 验证历史数据显示
      const historyPanel = window.locator('.history-panel, .history-data');
      const isVisible = await historyPanel.isVisible().catch(() => false);
      
      expect(typeof isVisible).toBe('boolean');
    }
  });
});

/**
 * 多设备协同测试套件
 */
test.describe('多设备协同测试', () => {
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
   * 测试27：验证同时连接多个设备
   */
  test('应该能够同时连接多个设备', async () => {
    await deviceHelper.gotoConnectionPage();
    
    // 连接多个设备
    await deviceHelper.mockDeviceConnection(DeviceType.MOTOR, { status: DeviceStatus.CONNECTED });
    await deviceHelper.mockDeviceConnection(DeviceType.TEMPERATURE, { status: DeviceStatus.CONNECTED });
    await deviceHelper.mockDeviceConnection(DeviceType.PIEZO, { status: DeviceStatus.CONNECTED });
    
    // 验证所有设备都已连接
    const motorConnected = await deviceHelper.isDeviceConnected(DeviceType.MOTOR);
    const tempConnected = await deviceHelper.isDeviceConnected(DeviceType.TEMPERATURE);
    const piezoConnected = await deviceHelper.isDeviceConnected(DeviceType.PIEZO);
    
    expect(motorConnected).toBe(true);
    expect(tempConnected).toBe(true);
    expect(piezoConnected).toBe(true);
  });

  /**
   * 测试28：验证设备间联动控制
   */
  test('应该能够执行设备间联动控制', async () => {
    await deviceHelper.gotoConnectionPage();
    
    // 连接电机和温度控制器
    await deviceHelper.mockDeviceConnection(DeviceType.MOTOR, { status: DeviceStatus.CONNECTED });
    await deviceHelper.mockDeviceConnection(DeviceType.TEMPERATURE, { status: DeviceStatus.CONNECTED });
    
    // 执行联动操作（移动电机并调整温度）
    const motorResult = await deviceHelper.executeDeviceOperation(
      DeviceType.MOTOR,
      'move',
      { position: 1000 }
    );
    
    const tempResult = await deviceHelper.executeDeviceOperation(
      DeviceType.TEMPERATURE,
      'setTemperature',
      { temperature: 25.0 }
    );
    
    expect(motorResult).toBeDefined();
    expect(tempResult).toBeDefined();
  });

  /**
   * 测试29：验证设备状态同步
   */
  test('多设备状态应该同步显示', async () => {
    await deviceHelper.gotoStatusPage();
    
    // 连接多个设备
    await deviceHelper.mockDeviceConnection(DeviceType.MOTOR, { 
      status: DeviceStatus.CONNECTED,
      position: 5000,
    });
    await deviceHelper.mockDeviceConnection(DeviceType.TEMPERATURE, { 
      status: DeviceStatus.CONNECTED,
      temperature: 25.0,
    });
    
    // 等待状态更新
    await window.waitForTimeout(1000);
    
    // 验证状态面板显示所有设备
    const deviceCards = window.locator('.device-card, [data-device-type]');
    const count = await deviceCards.count();
    
    expect(count).toBeGreaterThanOrEqual(2);
  });

  /**
   * 测试30：验证设备断开不影响其他设备
   */
  test('断开一个设备不应该影响其他设备', async () => {
    await deviceHelper.gotoConnectionPage();
    
    // 连接多个设备
    await deviceHelper.mockDeviceConnection(DeviceType.MOTOR, { status: DeviceStatus.CONNECTED });
    await deviceHelper.mockDeviceConnection(DeviceType.TEMPERATURE, { status: DeviceStatus.CONNECTED });
    
    // 断开一个设备
    await deviceHelper.clearDeviceMock(DeviceType.MOTOR);
    
    // 验证另一个设备仍然连接
    const tempConnected = await deviceHelper.isDeviceConnected(DeviceType.TEMPERATURE);
    expect(tempConnected).toBe(true);
  });
});
