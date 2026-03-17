/**
 * @file device.helper.js
 * @path frontend/tests/e2e/helpers/
 * @description 设备测试辅助函数
 * 
 * 提供设备相关的测试辅助功能，包括：
 * - 设备连接/断开
 * - 设备状态检查
 * - 设备配置管理
 * - 设备操作测试
 * 
 * @author Agent
 * @date 2024-03-16
 * @dependencies @playwright/test
 */

import { expect } from '@playwright/test';

/**
 * 设备类型枚举
 */
export const DeviceType = {
  MOTOR: 'motor',
  TEMPERATURE: 'temperature',
  PIEZO: 'piezo',
  ELECTROMAGNET: 'electromagnet',
  AMMETER: 'ammeter',
};

/**
 * 设备状态枚举
 */
export const DeviceStatus = {
  CONNECTED: 'connected',
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  ERROR: 'error',
};

/**
 * 设备测试辅助类
 * 
 * 封装设备相关的测试功能。
 * 
 * @example
 * const deviceHelper = new DeviceHelper(page);
 * await deviceHelper.connectDevice('motor', 'COM3');
 * await deviceHelper.checkDeviceStatus('motor', 'connected');
 */
export class DeviceHelper {
  /**
   * 构造函数
   * 
   * @param {Object} page - Playwright页面对象
   * @param {Object} options - 配置选项
   */
  constructor(page, options = {}) {
    this.page = page;
    this.options = {
      connectionUrl: options.connectionUrl || '/device/connection',
      statusUrl: options.statusUrl || '/device/status',
      apiBaseUrl: options.apiBaseUrl || '/api/v1',
      ...options,
    };
  }

  /**
   * 导航到设备连接页面
   * 
   * @returns {Promise<void>}
   */
  async gotoConnectionPage() {
    await this.page.goto(this.options.connectionUrl);
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * 导航到设备状态页面
   * 
   * @returns {Promise<void>}
   */
  async gotoStatusPage() {
    await this.page.goto(this.options.statusUrl);
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * 连接设备
   * 
   * @param {string} deviceType - 设备类型
   * @param {string} port - 端口号
   * @param {Object} options - 连接选项
   * @returns {Promise<void>}
   * 
   * @example
   * await deviceHelper.connectDevice('motor', 'COM3');
   */
  async connectDevice(deviceType, port, options = {}) {
    const { timeout = 30000, waitForSuccess = true } = options;

    // 确保在设备连接页面
    if (!this.page.url().includes('/device/connection')) {
      await this.gotoConnectionPage();
    }

    // 选择设备类型
    const deviceSelector = `[data-device-type="${deviceType}"], .device-card:has-text("${this.getDeviceName(deviceType)}")`;
    await this.page.click(deviceSelector);

    // 选择端口
    const portSelector = `select[name="port"], .port-selector`;
    await this.page.selectOption(portSelector, port);

    // 点击连接按钮
    const connectButton = this.page.locator('button:has-text("连接"), [data-testid="connect-button"]');
    await connectButton.click();

    if (waitForSuccess) {
      // 等待连接成功
      await this.page.waitForSelector('.device-status.connected, [data-status="connected"]', { timeout });
    }
  }

  /**
   * 断开设备连接
   * 
   * @param {string} deviceType - 设备类型
   * @returns {Promise<void>}
   */
  async disconnectDevice(deviceType) {
    const disconnectButton = this.page.locator(
      `[data-device-type="${deviceType}"] button:has-text("断开"), ` +
      `.device-card:has-text("${this.getDeviceName(deviceType)}") button:has-text("断开")`
    );

    await disconnectButton.click();
    await this.page.waitForSelector('.device-status.disconnected, [data-status="disconnected"]');
  }

  /**
   * 检查设备状态
   * 
   * @param {string} deviceType - 设备类型
   * @param {string} expectedStatus - 预期状态
   * @returns {Promise<void>}
   */
  async checkDeviceStatus(deviceType, expectedStatus) {
    const statusSelector = `[data-device-type="${deviceType}"] .device-status, ` +
      `.device-card:has-text("${this.getDeviceName(deviceType)}") .device-status`;

    const statusElement = this.page.locator(statusSelector);
    
    await expect(statusElement).toHaveAttribute('data-status', expectedStatus);
    await expect(statusElement).toContainText(this.getStatusText(expectedStatus));
  }

  /**
   * 获取设备状态
   * 
   * @param {string} deviceType - 设备类型
   * @returns {Promise<string>} 设备状态
   */
  async getDeviceStatus(deviceType) {
    const statusSelector = `[data-device-type="${deviceType}"] .device-status, ` +
      `.device-card:has-text("${this.getDeviceName(deviceType)}") .device-status`;

    const statusElement = this.page.locator(statusSelector);
    const status = await statusElement.getAttribute('data-status');
    
    return status || DeviceStatus.DISCONNECTED;
  }

  /**
   * 检查设备是否已连接
   * 
   * @param {string} deviceType - 设备类型
   * @returns {Promise<boolean>} 是否已连接
   */
  async isDeviceConnected(deviceType) {
    const status = await this.getDeviceStatus(deviceType);
    return status === DeviceStatus.CONNECTED;
  }

  /**
   * 获取设备配置
   * 
   * @param {string} deviceType - 设备类型
   * @returns {Promise<Object>} 设备配置对象
   */
  async getDeviceConfig(deviceType) {
    const config = await this.page.evaluate(async (apiUrl) => {
      const response = await fetch(`${apiUrl}/devices/${deviceType}/config`);
      return response.json();
    }, this.options.apiBaseUrl);

    return config;
  }

  /**
   * 更新设备配置
   * 
   * @param {string} deviceType - 设备类型
   * @param {Object} config - 配置对象
   * @returns {Promise<void>}
   */
  async updateDeviceConfig(deviceType, config) {
    await this.page.evaluate(async ({ apiUrl, deviceType, config }) => {
      await fetch(`${apiUrl}/devices/${deviceType}/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
    }, { apiUrl: this.options.apiBaseUrl, deviceType, config });
  }

  /**
   * 模拟设备连接
   * 
   * @param {string} deviceType - 设备类型
   * @param {Object} mockData - 模拟数据
   * @returns {Promise<void>}
   */
  async mockDeviceConnection(deviceType, mockData = {}) {
    await this.page.evaluate(({ deviceType, mockData }) => {
      // 设置模拟设备状态
      window.__mockDevices = window.__mockDevices || {};
      window.__mockDevices[deviceType] = {
        status: DeviceStatus.CONNECTED,
        ...mockData,
      };
    }, { deviceType, mockData });
  }

  /**
   * 清除设备模拟
   * 
   * @param {string} deviceType - 设备类型
   * @returns {Promise<void>}
   */
  async clearDeviceMock(deviceType) {
    await this.page.evaluate((deviceType) => {
      if (window.__mockDevices) {
        delete window.__mockDevices[deviceType];
      }
    }, deviceType);
  }

  /**
   * 等待设备状态变化
   * 
   * @param {string} deviceType - 设备类型
   * @param {string} expectedStatus - 预期状态
   * @param {Object} options - 等待选项
   * @returns {Promise<void>}
   */
  async waitForDeviceStatus(deviceType, expectedStatus, options = {}) {
    const { timeout = 30000 } = options;

    await this.page.waitForFunction(
      ({ deviceType, expectedStatus }) => {
        const statusElement = document.querySelector(
          `[data-device-type="${deviceType}"] .device-status, ` +
          `.device-card .device-status`
        );
        return statusElement?.getAttribute('data-status') === expectedStatus;
      },
      { deviceType, expectedStatus },
      { timeout }
    );
  }

  /**
   * 获取设备列表
   * 
   * @returns {Promise<Array>} 设备列表
   */
  async getDeviceList() {
    const devices = await this.page.evaluate(async (apiUrl) => {
      const response = await fetch(`${apiUrl}/devices`);
      return response.json();
    }, this.options.apiBaseUrl);

    return devices;
  }

  /**
   * 验证设备配置表单
   * 
   * @param {string} deviceType - 设备类型
   * @returns {Promise<void>}
   */
  async verifyDeviceConfigForm(deviceType) {
    const formSelector = `[data-device-type="${deviceType}"] .config-form, ` +
      `.device-config-form:has-text("${this.getDeviceName(deviceType)}")`;

    await expect(this.page.locator(formSelector)).toBeVisible();
  }

  /**
   * 获取设备名称
   * 
   * @param {string} deviceType - 设备类型
   * @returns {string} 设备名称
   */
  getDeviceName(deviceType) {
    const names = {
      [DeviceType.MOTOR]: '步进电机',
      [DeviceType.TEMPERATURE]: '温度控制器',
      [DeviceType.PIEZO]: '压电控制器',
      [DeviceType.ELECTROMAGNET]: '电磁铁',
      [DeviceType.AMMETER]: '皮安表',
    };

    return names[deviceType] || deviceType;
  }

  /**
   * 获取状态文本
   * 
   * @param {string} status - 状态
   * @returns {string} 状态文本
   */
  getStatusText(status) {
    const texts = {
      [DeviceStatus.CONNECTED]: '已连接',
      [DeviceStatus.DISCONNECTED]: '未连接',
      [DeviceStatus.CONNECTING]: '连接中',
      [DeviceStatus.ERROR]: '错误',
    };

    return texts[status] || status;
  }

  /**
   * 执行设备操作
   * 
   * @param {string} deviceType - 设备类型
   * @param {string} operation - 操作名称
   * @param {Object} params - 操作参数
   * @returns {Promise<Object>} 操作结果
   */
  async executeDeviceOperation(deviceType, operation, params = {}) {
    const result = await this.page.evaluate(async ({ apiUrl, deviceType, operation, params }) => {
      const response = await fetch(`${apiUrl}/devices/${deviceType}/operations/${operation}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      });
      return response.json();
    }, { apiUrl: this.options.apiBaseUrl, deviceType, operation, params });

    return result;
  }

  /**
   * 检查设备告警
   * 
   * @param {string} deviceType - 设备类型
   * @returns {Promise<Array>} 告警列表
   */
  async checkDeviceAlarms(deviceType) {
    const alarms = await this.page.evaluate(async ({ apiUrl, deviceType }) => {
      const response = await fetch(`${apiUrl}/devices/${deviceType}/alarms`);
      return response.json();
    }, { apiUrl: this.options.apiBaseUrl, deviceType });

    return alarms;
  }
}

/**
 * 创建设备helper实例
 * 
 * @param {Object} page - Playwright页面对象
 * @param {Object} options - 配置选项
 * @returns {DeviceHelper} 设备helper实例
 */
export function createDeviceHelper(page, options = {}) {
  return new DeviceHelper(page, options);
}

/**
 * 快速连接设备辅助函数
 * 
 * @param {Object} page - Playwright页面对象
 * @param {string} deviceType - 设备类型
 * @param {string} port - 端口号
 * @returns {Promise<DeviceHelper>} 设备helper实例
 * 
 * @example
 * const deviceHelper = await quickConnectDevice(page, 'motor', 'COM3');
 */
export async function quickConnectDevice(page, deviceType, port) {
  const deviceHelper = new DeviceHelper(page);
  await deviceHelper.connectDevice(deviceType, port);
  return deviceHelper;
}
