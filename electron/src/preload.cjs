/**
 * @file preload.cjs
 * @path electron/src/
 * @description Electron 预加载脚本 - 暴露安全的 API 给渲染进程
 * @author CAUC-SEP Team
 * @date 2024-03-15
 * @dependencies electron
 * 
 * 注意: 使用 CommonJS 格式以确保 Electron preload 兼容性
 */

const { contextBridge, ipcRenderer } = require("electron");

/**
 * 验证 IPC 通道名称是否在白名单中
 * 
 * @param {string} channel - 通道名称
 * @returns {boolean} 是否为有效通道
 */
function isValidChannel(channel) {
  const validChannels = [
    "app:getVersion",
    "app:getPlatform",
    "app:getPaths",
    "backend:getStatus",
    "backend:restart",
    "shell:openExternal",
    "dialog:showMessage",
  ];
  return validChannels.includes(channel);
}

/**
 * 暴露给渲染进程的 API 对象
 */
const electronAPI = {
  app: {
    getVersion: () => ipcRenderer.invoke("app:getVersion"),
    getPlatform: () => ipcRenderer.invoke("app:getPlatform"),
    getPaths: () => ipcRenderer.invoke("app:getPaths"),
  },

  backend: {
    getStatus: () => ipcRenderer.invoke("backend:getStatus"),
    restart: () => ipcRenderer.invoke("backend:restart"),
  },

  shell: {
    openExternal: (url) => ipcRenderer.invoke("shell:openExternal", url),
  },

  dialog: {
    showMessage: (options) => ipcRenderer.invoke("dialog:showMessage", options),
  },

  system: {
    platform: process.platform,
    arch: process.arch,
    nodeVersion: process.versions.node,
    chromeVersion: process.versions.chrome,
    electronVersion: process.versions.electron,
    isDev: process.env.NODE_ENV === "development" || !process.env.NODE_ENV,
  },

  on: {
    backendStatus: (callback) => {
      const handler = (_event, status) => callback(status);
      ipcRenderer.on("backend:statusChanged", handler);
      return () => ipcRenderer.removeListener("backend:statusChanged", handler);
    },
  },
};

contextBridge.exposeInMainWorld("electronAPI", electronAPI);

if (process.env.NODE_ENV === "development") {
  console.log("[Preload] electronAPI 已暴露到 window.electronAPI");
  console.log("[Preload] 可用 API:", Object.keys(electronAPI));
}
