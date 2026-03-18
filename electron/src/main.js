/**
 * @file main.js
 * @path electron/src/
 * @description Electron 主进程入口文件
 * @author CAUC-SEP Team
 * @date 2024-03-15
 * @dependencies electron, electron-log
 */

import {
  app,
  BrowserWindow,
  ipcMain,
  dialog,
  shell,
  Menu,
  Tray,
  nativeImage,
} from "electron";
import path from "path";
import { fileURLToPath } from "url";
import log from "electron-log";
import Store from "electron-store";

// ES Modules 环境下获取 __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// 配置日志
log.transports.file.level = "info";
log.transports.console.level = "debug";
log.transports.file.maxSize = 10 * 1024 * 1024; // 10MB

// 持久化存储
const store = new Store({
  name: "cauc-sep-config",
  defaults: {
    windowBounds: { width: 1400, height: 900 },
    backendPort: 8000,
    autoStartBackend: true,
  },
});

/**
 * 后端进程管理类
 * 
 * 负责启动、监控和关闭 FastAPI 后端子进程
 */
class BackendProcess {
  constructor() {
    /** @type {import('child_process').ChildProcess | null} */
    this.process = null;
    /** @type {number} */
    this.port = store.get("backendPort", 8000);
    /** @type {boolean} */
    this.isRunning = false;
    /** @type {number} */
    this.restartAttempts = 0;
    /** @type {number} */
    this.maxRestartAttempts = 3;
    /** @type {NodeJS.Timeout | null} */
    this.healthCheckInterval = null;
  }

  /**
   * 获取后端可执行文件路径
   * 
   * @returns {string} 后端 exe 文件路径
   */
  getBackendPath() {
    // 开发环境与生产环境路径区分
    if (app.isPackaged) {
      // 生产环境：从 resources 目录读取 (Nuitka输出在main.dist子目录)
      return path.join(process.resourcesPath, "backend", "main.dist", "backend.exe");
    }
    // 开发环境：从项目electron/resources目录读取
    return path.join(__dirname, "..", "resources", "backend", "main.dist", "backend.exe");
  }

  /**
   * 启动后端进程
   * 
   * @returns {Promise<boolean>} 启动是否成功
   */
  async start() {
    if (this.isRunning) {
      log.warn("[Backend] 进程已在运行中");
      return true;
    }

    const backendPath = this.getBackendPath();
    log.info(`[Backend] 启动路径: ${backendPath}`);

    // 检查后端文件是否存在
    const fs = await import("fs");
    if (!fs.existsSync(backendPath)) {
      log.error(`[Backend] 后端文件不存在: ${backendPath}`);
      return false;
    }

    try {
      // 使用 spawn 启动后端进程
      const { spawn } = await import("child_process");

      this.process = spawn(backendPath, ["--port", String(this.port)], {
        cwd: path.dirname(backendPath),
        windowsHide: true,
        env: {
          ...process.env,
          PYTHONIOENCODING: "utf-8",
        },
      });

      // 进程启动事件
      this.process.on("spawn", () => {
        log.info("[Backend] 进程启动成功");
        this.isRunning = true;
        this.restartAttempts = 0;
        this.startHealthCheck();
      });

      // 标准输出
      this.process.stdout?.on("data", (data) => {
        log.info(`[Backend stdout] ${data.toString().trim()}`);
      });

      // 标准错误
      this.process.stderr?.on("data", (data) => {
        log.warn(`[Backend stderr] ${data.toString().trim()}`);
      });

      // 进程关闭事件
      this.process.on("close", (code, signal) => {
        log.warn(`[Backend] 进程退出 code=${code}, signal=${signal}`);
        this.isRunning = false;
        this.stopHealthCheck();

        // 非正常退出时尝试重启
        if (code !== 0 && code !== null && this.restartAttempts < this.maxRestartAttempts) {
          this.restartAttempts++;
          log.info(`[Backend] 尝试重启 (${this.restartAttempts}/${this.maxRestartAttempts})`);
          setTimeout(() => this.start(), 3000);
        }
      });

      // 进程错误事件
      this.process.on("error", (err) => {
        log.error(`[Backend] 进程错误: ${err.message}`);
        this.isRunning = false;
      });

      // 等待进程启动
      await new Promise((resolve) => {
        this.process?.once("spawn", () => resolve(true));
        setTimeout(() => resolve(false), 5000);
      });

      return this.isRunning;
    } catch (err) {
      log.error(`[Backend] 启动失败: ${err}`);
      return false;
    }
  }

  /**
   * 停止后端进程
   * 
   * @returns {Promise<void>}
   */
  async stop() {
    this.stopHealthCheck();

    if (!this.process || !this.isRunning) {
      log.info("[Backend] 进程未运行，无需停止");
      return;
    }

    log.info("[Backend] 正在停止后端进程...");

    // Windows 下使用 taskkill 强制终止进程树
    if (process.platform === "win32") {
      const { exec } = await import("child_process");
      const promisifiedExec = (cmd) =>
        new Promise((resolve) => {
          exec(cmd, (error) => resolve(error));
        });

      await promisifiedExec(`taskkill /pid ${this.process.pid} /T /F`);
    } else {
      // Unix 系统发送 SIGTERM
      this.process.kill("SIGTERM");

      // 等待进程退出
      await new Promise((resolve) => {
        this.process?.once("close", resolve);
        setTimeout(resolve, 5000);
      });
    }

    this.process = null;
    this.isRunning = false;
    log.info("[Backend] 后端进程已停止");
  }

  /**
   * 启动健康检查
   */
  startHealthCheck() {
    this.healthCheckInterval = setInterval(async () => {
      try {
        const response = await fetch(`http://localhost:${this.port}/api/health`);
        if (!response.ok) {
          log.warn(`[Backend] 健康检查异常: ${response.status}`);
        }
      } catch {
        log.warn("[Backend] 健康检查失败，后端可能已停止响应");
      }
    }, 30000); // 每30秒检查一次
  }

  /**
   * 停止健康检查
   */
  stopHealthCheck() {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
    }
  }
}

/**
 * 主窗口管理类
 */
class MainWindow {
  constructor() {
    /** @type {BrowserWindow | null} */
    this.window = null;
    /** @type {Tray | null} */
    this.tray = null;
  }

  /**
   * 获取前端资源路径
   * 
   * @returns {string} 前端 HTML 文件路径
   */
  getFrontendPath() {
    if (app.isPackaged) {
      // 生产环境
      return path.join(process.resourcesPath, "frontend", "index.html");
    }
    // 开发环境
    return path.join(__dirname, "..", "..", "frontend", "dist", "index.html");
  }

  /**
   * 创建主窗口
   * 
   * @returns {BrowserWindow} 主窗口实例
   */
  create() {
    // 获取保存的窗口尺寸
    const bounds = store.get("windowBounds");

    this.window = new BrowserWindow({
      width: bounds.width || 1400,
      height: bounds.height || 900,
      minWidth: 1024,
      minHeight: 768,
      title: "CAUC-SEP 科学实验平台",
      icon: this.getIconPath(),
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        preload: path.join(__dirname, "preload.cjs"),
        webSecurity: false, // 禁用 webSecurity 以允许本地文件加载
        spellcheck: false,
      },
      show: false, // 先隐藏，加载完成后显示
      backgroundColor: "#f5f7fa",
      frame: true,
      titleBarStyle: "default",
    });

    // 窗口关闭事件
    this.window.on("close", (event) => {
      // 最小化到托盘而非关闭
      if (!app.isQuitting) {
        event.preventDefault();
        this.window?.hide();
        return false;
      }
      return true;
    });

    // 窗口关闭后清理
    this.window.on("closed", () => {
      this.window = null;
    });

    // 保存窗口尺寸
    this.window.on("resize", () => {
      if (this.window) {
        const [width, height] = this.window.getSize();
        store.set("windowBounds", { width, height });
      }
    });

    // 加载前端页面
    this.loadFrontend();

    // 创建系统托盘
    this.createTray();

    return this.window;
  }

  /**
   * 加载前端页面
   */
  async loadFrontend() {
    const frontendPath = this.getFrontendPath();
    log.info(`[Frontend] 加载路径: ${frontendPath}`);

    try {
      // 检查文件是否存在
      const fs = await import("fs");
      if (!fs.existsSync(frontendPath)) {
        log.error(`[Frontend] 前端文件不存在: ${frontendPath}`);
        // 显示错误页面
        this.window?.loadURL(
          `data:text/html;charset=utf-8,${encodeURIComponent(this.getErrorPage("前端资源未找到"))}`
        );
        return;
      }

      // 添加 webContents 错误监听
      this.window?.webContents.on("did-fail-load", (event, errorCode, errorDescription) => {
        log.error(`[Frontend] 页面加载失败: ${errorCode} - ${errorDescription}`);
        this.window?.loadURL(
          `data:text/html;charset=utf-8,${encodeURIComponent(this.getErrorPage(`加载失败: ${errorDescription}`))}`
        );
      });

      // 添加控制台消息监听
      this.window?.webContents.on("console-message", (event, level, message, line, sourceId) => {
        log.info(`[Frontend Console] ${message} (source: ${sourceId}:${line})`);
      });

      // 加载本地 HTML 文件
      await this.window?.loadFile(frontendPath);

      log.info("[Frontend] 页面加载成功");
      
      // 显示窗口
      this.window?.show();

      // 开发环境打开开发者工具，生产环境可通过快捷键 F12 打开
      if (!app.isPackaged) {
        this.window?.webContents.openDevTools({ mode: "right" });
      } else {
        // 生产环境添加 F12 快捷键打开开发者工具
        this.window?.webContents.on("before-input-event", (event, input) => {
          if (input.key === "F12") {
            this.window?.webContents.toggleDevTools();
          }
        });
      }
    } catch (err) {
      log.error(`[Frontend] 加载失败: ${err}`);
      this.window?.loadURL(
        `data:text/html;charset=utf-8,${encodeURIComponent(this.getErrorPage(err.message))}`
      );
    }
  }

  /**
   * 获取图标路径
   * 
   * @returns {string} 图标文件路径
   */
  getIconPath() {
    if (app.isPackaged) {
      return path.join(process.resourcesPath, "assets", "icons", "icon.ico");
    }
    return path.join(__dirname, "..", "..", "assets", "icons", "icon.ico");
  }

  /**
   * 创建系统托盘
   */
  createTray() {
    const iconPath = this.getIconPath();
    const icon = nativeImage.createFromPath(iconPath);

    this.tray = new Tray(icon.resize({ width: 16, height: 16 }));

    const contextMenu = Menu.buildFromTemplate([
      {
        label: "显示主窗口",
        click: () => {
          this.window?.show();
          this.window?.focus();
        },
      },
      {
        label: "重启后端",
        click: async () => {
          await backendProcess.stop();
          await backendProcess.start();
        },
      },
      { type: "separator" },
      {
        label: "退出",
        click: () => {
          app.isQuitting = true;
          app.quit();
        },
      },
    ]);

    this.tray.setToolTip("CAUC-SEP 科学实验平台");
    this.tray.setContextMenu(contextMenu);

    // 点击托盘图标显示窗口
    this.tray.on("click", () => {
      this.window?.show();
      this.window?.focus();
    });
  }

  /**
   * 生成错误页面 HTML
   * 
   * @param {string} message - 错误信息
   * @returns {string} HTML 内容
   */
  getErrorPage(message) {
    return `
      <!DOCTYPE html>
      <html lang="zh-CN">
      <head>
        <meta charset="UTF-8">
        <title>CAUC-SEP - 加载错误</title>
        <style>
          body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: #f5f7fa;
            color: #333;
          }
          .error-container {
            text-align: center;
            padding: 40px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.1);
          }
          h1 { color: #e74c3c; margin-bottom: 20px; }
          p { color: #666; margin-bottom: 20px; }
          button {
            padding: 10px 20px;
            background: #3498db;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
          }
          button:hover { background: #2980b9; }
        </style>
      </head>
      <body>
        <div class="error-container">
          <h1>加载失败</h1>
          <p>${message}</p>
          <button onclick="location.reload()">重试</button>
        </div>
      </body>
      </html>
    `;
  }
}

// 全局实例
const backendProcess = new BackendProcess();
const mainWindow = new MainWindow();

/**
 * 注册 IPC 通信处理
 */
function registerIpcHandlers() {
  // 获取应用版本
  ipcMain.handle("app:getVersion", () => {
    return app.getVersion();
  });

  // 获取平台信息
  ipcMain.handle("app:getPlatform", () => {
    return {
      platform: process.platform,
      arch: process.arch,
      versions: process.versions,
    };
  });

  // 获取后端状态
  ipcMain.handle("backend:getStatus", () => {
    return {
      isRunning: backendProcess.isRunning,
      port: backendProcess.port,
      pid: backendProcess.process?.pid || null,
    };
  });

  // 重启后端
  ipcMain.handle("backend:restart", async () => {
    await backendProcess.stop();
    return await backendProcess.start();
  });

  // 打开外部链接
  ipcMain.handle("shell:openExternal", async (_event, url) => {
    await shell.openExternal(url);
  });

  // 显示消息对话框
  ipcMain.handle("dialog:showMessage", async (_event, options) => {
    return await dialog.showMessageBox(mainWindow.window, options);
  });

  // 获取应用路径
  ipcMain.handle("app:getPaths", () => {
    return {
      appPath: app.getAppPath(),
      userData: app.getPath("userData"),
      logs: app.getPath("logs"),
      temp: app.getPath("temp"),
    };
  });
}

/**
 * 创建应用菜单
 */
function createApplicationMenu() {
  const template = [
    {
      label: "文件",
      submenu: [
        {
          label: "重新加载",
          accelerator: "CmdOrCtrl+R",
          click: () => {
            mainWindow.window?.reload();
          },
        },
        { type: "separator" },
        {
          label: "退出",
          accelerator: "CmdOrCtrl+Q",
          click: () => {
            app.isQuitting = true;
            app.quit();
          },
        },
      ],
    },
    {
      label: "视图",
      submenu: [
        { role: "reload", label: "刷新" },
        { role: "forceReload", label: "强制刷新" },
        { type: "separator" },
        { role: "resetZoom", label: "重置缩放" },
        { role: "zoomIn", label: "放大" },
        { role: "zoomOut", label: "缩小" },
        { type: "separator" },
        { role: "togglefullscreen", label: "全屏" },
      ],
    },
    {
      label: "开发",
      submenu: [
        {
          label: "开发者工具",
          accelerator: "F12",
          click: () => {
            mainWindow.window?.webContents.toggleDevTools();
          },
        },
        {
          label: "重启后端",
          click: async () => {
            await backendProcess.stop();
            await backendProcess.start();
          },
        },
      ],
    },
    {
      label: "帮助",
      submenu: [
        {
          label: "关于",
          click: () => {
            dialog.showMessageBox(mainWindow.window, {
              type: "info",
              title: "关于 CAUC-SEP",
              message: "CAUC-SEP 科学实验平台",
              detail: `版本: ${app.getVersion()}\n\n中国民航大学\n科学实验平台`,
            });
          },
        },
        {
          label: "查看日志",
          click: () => {
            shell.openPath(app.getPath("logs"));
          },
        },
      ],
    },
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

// 应用准备就绪
app.whenReady().then(async () => {
  log.info("[App] 应用启动中...");
  log.info(`[App] 版本: ${app.getVersion()}`);
  log.info(`[App] 平台: ${process.platform} ${process.arch}`);
  log.info(`[App] Node.js: ${process.versions.node}`);
  log.info(`[App] Electron: ${process.versions.electron}`);

  // 注册 IPC 处理
  registerIpcHandlers();

  // 创建应用菜单
  createApplicationMenu();

  // 启动后端进程
  if (store.get("autoStartBackend", true)) {
    log.info("[App] 启动后端进程...");
    const success = await backendProcess.start();
    if (!success) {
      log.warn("[App] 后端启动失败，应用将继续运行");
    }
  }

  // 创建主窗口
  mainWindow.create();

  // macOS 激活应用时重新创建窗口
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      mainWindow.create();
    }
  });
});

// 所有窗口关闭时退出应用（Windows/Linux）
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.isQuitting = true;
    app.quit();
  }
});

// 应用退出前清理
app.on("before-quit", async (event) => {
  if (app.isQuitting) {
    log.info("[App] 应用退出中，清理资源...");
    await backendProcess.stop();
  } else {
    event.preventDefault();
    app.isQuitting = true;
    app.quit();
  }
});

// 未捕获的异常处理
process.on("uncaughtException", (error) => {
  log.error(`[App] 未捕获异常: ${error}`);
  dialog.showErrorBox("应用程序错误", error.message);
});

process.on("unhandledRejection", (reason) => {
  log.error(`[App] 未处理的 Promise 拒绝: ${reason}`);
});
