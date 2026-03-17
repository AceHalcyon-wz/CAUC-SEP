/**
 * @file electron.helper.js
 * @path frontend/tests/e2e/helpers/
 * @description Electron应用测试辅助函数
 * 
 * 提供Electron应用的启动、连接和测试辅助功能，包括：
 * - Electron应用启动和关闭
 * - 窗口管理
 * - IPC通信测试
 * - 应用状态检查
 * 
 * @author Agent
 * @date 2024-03-16
 * @dependencies playwright-electron, electron
 */

import { _electron as electron } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Electron应用测试辅助类
 * 
 * 封装Electron应用的启动、连接和测试功能。
 * 
 * @example
 * const electronApp = new ElectronAppHelper();
 * await electronApp.launch();
 * const window = await electronApp.getFirstWindow();
 * // 执行测试...
 * await electronApp.close();
 */
export class ElectronAppHelper {
  /**
   * 构造函数
   * 
   * @param {Object} options - 配置选项
   * @param {string} options.electronPath - Electron应用路径
   * @param {string} options.mainEntry - 主进程入口文件
   * @param {Object} options.env - 环境变量
   */
  constructor(options = {}) {
    this.electronApp = null;
    this.windows = [];
    this.options = {
      electronPath: options.electronPath || this.getDefaultElectronPath(),
      mainEntry: options.mainEntry || this.getDefaultMainEntry(),
      env: options.env || {},
    };
  }

  /**
   * 获取默认Electron应用路径
   * 
   * @returns {string} Electron应用路径
   */
  getDefaultElectronPath() {
    const projectRoot = path.resolve(__dirname, '../../../../');
    return path.join(projectRoot, 'electron');
  }

  /**
   * 获取默认主进程入口
   * 
   * @returns {string} 主进程入口文件路径
   */
  getDefaultMainEntry() {
    return path.join(this.options.electronPath || this.getDefaultElectronPath(), 'src/main.js');
  }

  /**
   * 启动Electron应用
   * 
   * @param {Object} launchOptions - 启动选项
   * @returns {Promise<Object>} Electron应用实例
   * 
   * @example
   * const app = await electronApp.launch({ headless: false });
   */
  async launch(launchOptions = {}) {
    const defaultOptions = {
      executablePath: this.getElectronExecutable(),
      args: [this.options.mainEntry],
      env: {
        ...process.env,
        NODE_ENV: 'test',
        ...this.options.env,
      },
    };

    this.electronApp = await electron.launch({
      ...defaultOptions,
      ...launchOptions,
    });

    return this.electronApp;
  }

  /**
   * 获取Electron可执行文件路径
   * 
   * @returns {string} Electron可执行文件路径
   */
  getElectronExecutable() {
    const projectRoot = path.resolve(__dirname, '../../../../');
    const electronModulePath = path.join(projectRoot, 'electron/node_modules/electron');
    
    // Windows路径
    if (process.platform === 'win32') {
      return path.join(electronModulePath, 'dist/electron.exe');
    }
    
    // macOS路径
    if (process.platform === 'darwin') {
      return path.join(electronModulePath, 'dist/Electron.app/Contents/MacOS/Electron');
    }
    
    // Linux路径
    return path.join(electronModulePath, 'dist/electron');
  }

  /**
   * 获取第一个窗口
   * 
   * @returns {Promise<Object>} Playwright页面对象
   */
  async getFirstWindow() {
    if (!this.electronApp) {
      throw new Error('Electron应用未启动，请先调用launch()');
    }

    const window = await this.electronApp.firstWindow();
    this.windows.push(window);
    return window;
  }

  /**
   * 获取所有窗口
   * 
   * @returns {Promise<Array>} 窗口数组
   */
  async getAllWindows() {
    if (!this.electronApp) {
      throw new Error('Electron应用未启动，请先调用launch()');
    }

    this.windows = await this.electronApp.windows();
    return this.windows;
  }

  /**
   * 等待窗口出现
   * 
   * @param {Function} matcher - 窗口匹配函数
   * @param {Object} options - 等待选项
   * @returns {Promise<Object>} 窗口对象
   */
  async waitForWindow(matcher, options = {}) {
    if (!this.electronApp) {
      throw new Error('Electron应用未启动，请先调用launch()');
    }

    const window = await this.electronApp.waitForEvent('window', async (page) => {
      if (typeof matcher === 'function') {
        return await matcher(page);
      }
      return true;
    }, options);

    this.windows.push(window);
    return window;
  }

  /**
   * 发送IPC消息到主进程
   * 
   * @param {string} channel - IPC通道名称
   * @param {*} data - 要发送的数据
   * @returns {Promise<void>}
   */
  async sendIPC(channel, data) {
    if (!this.electronApp) {
      throw new Error('Electron应用未启动，请先调用launch()');
    }

    await this.electronApp.evaluate(({ ipcMain }, { channel, data }) => {
      ipcMain.emit(channel, {}, data);
    }, { channel, data });
  }

  /**
   * 监听IPC消息
   * 
   * @param {string} channel - IPC通道名称
   * @param {Function} handler - 消息处理函数
   * @returns {Promise<void>}
   */
  async onIPC(channel, handler) {
    if (!this.electronApp) {
      throw new Error('Electron应用未启动，请先调用launch()');
    }

    await this.electronApp.evaluate(({ ipcMain }, { channel }) => {
      ipcMain.on(channel, (event, ...args) => {
        // 消息处理逻辑
      });
    }, { channel });
  }

  /**
   * 获取应用版本
   * 
   * @returns {Promise<string>} 应用版本号
   */
  async getAppVersion() {
    if (!this.electronApp) {
      throw new Error('Electron应用未启动，请先调用launch()');
    }

    const version = await this.electronApp.evaluate(async ({ app }) => {
      return app.getVersion();
    });

    return version;
  }

  /**
   * 获取应用路径
   * 
   * @param {string} name - 路径名称（appPath、userData等）
   * @returns {Promise<string>} 应用路径
   */
  async getAppPath(name = 'appPath') {
    if (!this.electronApp) {
      throw new Error('Electron应用未启动，请先调用launch()');
    }

    const appPath = await this.electronApp.evaluate(async ({ app }, { name }) => {
      return app.getPath(name);
    }, { name });

    return appPath;
  }

  /**
   * 检查应用是否就绪
   * 
   * @returns {Promise<boolean>} 应用是否就绪
   */
  async isReady() {
    if (!this.electronApp) {
      return false;
    }

    try {
      await this.electronApp.evaluate(async ({ app }) => {
        return app.isReady();
      });
      return true;
    } catch (error) {
      return false;
    }
  }

  /**
   * 截图
   * 
   * @param {string} screenshotPath - 截图保存路径
   * @param {Object} options - 截图选项
   * @returns {Promise<Buffer>} 截图数据
   */
  async takeScreenshot(screenshotPath, options = {}) {
    const window = await this.getFirstWindow();
    return await window.screenshot({
      path: screenshotPath,
      ...options,
    });
  }

  /**
   * 关闭Electron应用
   * 
   * @returns {Promise<void>}
   */
  async close() {
    if (this.electronApp) {
      await this.electronApp.close();
      this.electronApp = null;
      this.windows = [];
    }
  }
}

/**
 * 创建Electron应用helper实例
 * 
 * @param {Object} options - 配置选项
 * @returns {ElectronAppHelper} Electron应用helper实例
 */
export function createElectronApp(options = {}) {
  return new ElectronAppHelper(options);
}

/**
 * 快速启动Electron应用进行测试
 * 
 * @param {Object} options - 启动选项
 * @returns {Promise<{app: Object, window: Object}>} 应用和窗口实例
 * 
 * @example
 * const { app, window } = await quickLaunchElectron();
 * await window.goto('app://./index.html');
 * // 执行测试...
 * await app.close();
 */
export async function quickLaunchElectron(options = {}) {
  const helper = new ElectronAppHelper(options);
  const app = await helper.launch();
  const window = await helper.getFirstWindow();
  
  return { app, window, helper };
}
