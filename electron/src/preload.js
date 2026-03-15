/**
 * @file preload.js
 * @path electron/src/
 * @description Electron 预加载脚本 - 暴露安全的 API 给渲染进程
 * @author CAUC-SEP Team
 * @date 2024-03-15
 * @dependencies electron
 */

import { contextBridge, ipcRenderer } from "electron";

/**
 * 验证 IPC 通道名称是否在白名单中
 * 
 * @param {string} channel - 通道名称
 * @returns {boolean} 是否为有效通道
 */
function isValidChannel(channel) {
  const validChannels = [
    // 应用相关
    "app:getVersion",
    "app:getPlatform",
    "app:getPaths",
    // 后端相关
    "backend:getStatus",
    "backend:restart",
    // Shell 相关
    "shell:openExternal",
    // 对话框相关
    "dialog:showMessage",
  ];
  return validChannels.includes(channel);
}

/**
 * 暴露给渲染进程的 API 对象
 */
const electronAPI = {
  /**
   * 应用相关 API
   */
  app: {
    /**
     * 获取应用版本号
     * @returns {Promise<string>} 版本号
     */
    getVersion: () => ipcRenderer.invoke("app:getVersion"),

    /**
     * 获取平台信息
     * @returns {Promise<{platform: string, arch: string, versions: object}>} 平台信息
     */
    getPlatform: () => ipcRenderer.invoke("app:getPlatform"),

    /**
     * 获取应用路径
     * @returns {Promise<{appPath: string, userData: string, logs: string, temp: string}>} 路径信息
     */
    getPaths: () => ipcRenderer.invoke("app:getPaths"),
  },

  /**
   * 后端进程相关 API
   */
  backend: {
    /**
     * 获取后端进程状态
     * @returns {Promise<{isRunning: boolean, port: number, pid: number | null}>} 后端状态
     */
    getStatus: () => ipcRenderer.invoke("backend:getStatus"),

    /**
     * 重启后端进程
     * @returns {Promise<boolean>} 重启是否成功
     */
    restart: () => ipcRenderer.invoke("backend:restart"),
  },

  /**
   * Shell 相关 API
   */
  shell: {
    /**
     * 在默认浏览器中打开外部链接
     * @param {string} url - 要打开的 URL
     * @returns {Promise<void>}
     */
    openExternal: (url) => ipcRenderer.invoke("shell:openExternal", url),
  },

  /**
   * 对话框相关 API
   */
  dialog: {
    /**
     * 显示消息对话框
     * @param {object} options - 对话框选项
     * @param {string} [options.type] - 对话框类型 ('none' | 'info' | 'error' | 'question' | 'warning')
     * @param {string} [options.title] - 对话框标题
     * @param {string} [options.message] - 对话框消息
     * @param {string} [options.detail] - 详细信息
     * @param {Array<string>} [options.buttons] - 按钮文本数组
     * @returns {Promise<{response: number, checkboxChecked: boolean}>} 用户响应
     */
    showMessage: (options) => ipcRenderer.invoke("dialog:showMessage", options),
  },

  /**
   * 系统信息
   */
  system: {
    /** 当前平台 */
    platform: process.platform,
    /** CPU 架构 */
    arch: process.arch,
    /** Node.js 版本 */
    nodeVersion: process.versions.node,
    /** Chrome 版本 */
    chromeVersion: process.versions.chrome,
    /** Electron 版本 */
    electronVersion: process.versions.electron,
    /** 是否为开发环境 */
    isDev: process.env.NODE_ENV === "development" || !process.env.NODE_ENV,
  },

  /**
   * 事件监听
   */
  on: {
    /**
     * 监听后端状态变化
     * @param {function} callback - 回调函数
     * @returns {function} 取消监听函数
     */
    backendStatus: (callback) => {
      const handler = (_event, status) => callback(status);
      ipcRenderer.on("backend:statusChanged", handler);
      return () => ipcRenderer.removeListener("backend:statusChanged", handler);
    },
  },
};

// 使用 contextBridge 安全地暴露 API
contextBridge.exposeInMainWorld("electronAPI", electronAPI);

// 开发环境下输出调试信息
if (process.env.NODE_ENV === "development") {
  console.log("[Preload] electronAPI 已暴露到 window.electronAPI");
  console.log("[Preload] 可用 API:", Object.keys(electronAPI));
}
