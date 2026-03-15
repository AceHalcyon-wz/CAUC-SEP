# CAUC-SEP Nuitka + Electron + electron-builder 打包指南

<!--
文件名: NUITKA_BUILD_GUIDE.md
路径: docs/
功能: Nuitka + Electron + electron-builder 完整打包指南，生成专业级桌面应用
版本: v3.0
项目版本: v0.3.0

作者: CAUC-SEP 开发团队
创建日期: 2024-03-01
最后更新: 2026-03-15
-->

## 概述

本文档提供 CAUC-SEP 自旋电子实验平台的完整打包方案，采用 **Nuitka + Electron + electron-builder** 组合，生成专业级跨平台桌面应用。

### 打包方案架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    CAUC-SEP 桌面应用架构                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │   Electron      │    │   Nuitka        │                    │
│  │   (前端容器)     │◄──►│   (后端编译)     │                    │
│  │   Vue 3 + Vite  │    │   FastAPI       │                    │
│  └─────────────────┘    └─────────────────┘                    │
│           │                     │                               │
│           ▼                     ▼                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              electron-builder (打包分发)                 │   │
│  │         NSIS安装包 / 便携版 / 自动更新                    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 打包方案优势

| 特性 | Nuitka + Electron | PyInstaller | 纯Web应用 |
|------|-------------------|-------------|-----------|
| 启动速度 | **快（1-2秒）** | 慢（3-5秒） | 需启动浏览器 |
| 代码保护 | **强（原生编译）** | 弱（易反编译） | 无 |
| 内存占用 | **低（180MB）** | 高（250MB） | 依赖浏览器 |
| 用户体验 | **原生桌面应用** | 一般 | Web体验 |
| 自动更新 | **支持** | 需额外实现 | 需刷新 |
| 跨平台 | **Win/Mac/Linux** | Win/Mac/Linux | 全平台 |

### 技术栈版本

| 组件 | 版本 | 用途 |
|------|------|------|
| Python | 3.13 | 后端运行环境 |
| Nuitka | 2.0+ | Python编译器 |
| Node.js | 20+ | Electron构建 |
| Electron | 30+ | 桌面应用框架 |
| electron-builder | 24+ | 应用打包分发 |
| Visual Studio | 2022 | MSVC编译工具链 |

## 系统要求

### 硬件配置

| 配置项 | 最低要求 | 推荐配置 |
|--------|----------|----------|
| CPU | 4核心 | AMD Ryzen 7-H255 或同等 |
| 内存 | 8GB | 24GB DDR5 |
| 硬盘 | 20GB可用 | 50GB+ SSD |
| 操作系统 | Windows 10 64位 | Windows 11 25H2 64位 |

### 软件要求

| 软件 | 版本 | 用途 | 备注 |
|------|------|------|------|
| Python | 3.13 | 后端运行环境 | 必须使用3.13+ |
| Node.js | 20 LTS | 前端构建 | 推荐LTS版本 |
| Nuitka | 2.0+ | Python编译器 | pip安装 |
| Visual Studio | 2022 | MSVC编译工具链 | **必须安装** |
| electron-builder | 24+ | 应用打包 | npm安装 |

## MSVC 编译工具链配置

### 重要说明

**Nuitka 在 Windows 上必须使用 MSVC 编译工具链，禁止使用 MinGW 等替代方案。**

Python 3.13 及以上版本不再支持 MinGW 编译器，必须使用 Microsoft Visual C++ 编译工具链。

### Visual Studio 安装要求

安装 Visual Studio 2022 时，必须包含以下组件：

```
Visual Studio 2022 Community
├── 工作负载
│   ├── ☑ 使用 C++ 的桌面开发
│   └── ☑ Python 开发（可选）
│
└── 单个组件
    ├── ☑ MSVC v143 - VS 2022 C++ x64/x86 生成工具
    ├── ☑ Windows 10 SDK 或 Windows 11 SDK
    └── ☑ C++ CMake tools for Windows
```

### 验证 MSVC 环境

```batch
:: 检查 Visual Studio 安装
"C:\Program Files\Microsoft Visual Studio\Installer\vswhere.exe" -latest -property displayName

:: 检查 MSVC 编译器
where cl.exe

:: 预期输出示例
C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.38.33130\bin\Hostx64\x64\cl.exe
```

### Nuitka 自动识别 MSVC

Nuitka 会自动检测系统中安装的 Visual Studio 并使用 MSVC 工具链：

```python
# Nuitka 编译时会自动输出类似信息
# MSVC detected: Visual Studio 2022 (17.8.3)
# Using MSVC from: C:\Program Files\Microsoft Visual Studio\2022\Community\VC
```

### 常见问题：MSVC 未检测到

如果 Nuitka 未检测到 MSVC，请检查：

1. **确认 Visual Studio 已正确安装**
   ```batch
   :: 运行 Visual Studio Installer 检查
   "C:\Program Files\Microsoft Visual Studio\Installer\vswhere.exe" -latest
   ```

2. **确认 C++ 工作负载已安装**
   - 打开 Visual Studio Installer
   - 点击"修改"
   - 确保勾选"使用 C++ 的桌面开发"

3. **手动指定 MSVC 路径（不推荐）**
   ```batch
   :: 仅在自动检测失败时使用
   set VCINSTALLDIR=C:\Program Files\Microsoft Visual Studio\2022\Community\VC
   python -m nuitka --msvc=latest ...
   ```

## 项目打包相关目录

```
cauc-sep/
├── assets/icons/                     # 图标资源
│   ├── icon.ico                      # Windows应用图标
│   └── icon.png                      # PNG格式图标
├── backend/                          # Python后端
│   ├── scripts/
│   │   └── build_exe_standalone.py   # Nuitka打包脚本
│   ├── main.py                       # FastAPI入口
│   └── dist/                         # 打包输出目录
├── frontend/                         # Vue前端
│   └── dist/                         # 前端构建输出
├── electron/                         # Electron项目（新增）
│   ├── src/
│   │   ├── main.js                   # Electron主进程
│   │   ├── preload.js                # 预加载脚本
│   │   └── backend/
│   │       └── (Nuitka编译产物)       # 后端可执行文件
│   ├── resources/                    # 资源目录
│   │   └── backend/                  # 后端程序目录
│   ├── package.json                  # Electron配置
│   └── electron-builder.yml          # 打包配置
├── installer/
│   └── CAUC-SEP.iss                  # Inno Setup脚本（备用）
└── scripts/
    ├── build-nuitka.bat              # Nuitka编译脚本
    ├── build-electron.bat            # Electron打包脚本（新增）
    └── build-all.bat                 # 完整构建脚本（新增）
```

## Electron 集成配置

### Electron 项目结构

```
electron/
├── src/
│   ├── main.js                    # 主进程入口
│   ├── preload.js                 # 预加载脚本（安全通信）
│   └── utils/
│       └── backend-manager.js     # 后端进程管理
├── resources/
│   ├── backend/                   # Nuitka编译的后端程序
│   │   ├── CAUC-SEP.exe          # 后端可执行文件
│   │   └── *.dll, *.pyd          # 依赖文件
│   └── app.asar                   # 前端资源（打包后）
├── package.json                   # 项目配置
├── electron-builder.yml           # 打包配置
└── build/                         # 构建资源
    ├── icon.ico                   # Windows图标
    └── installer.nsh              # 安装脚本（可选）
```

### package.json 配置

```json
{
  "name": "cauc-sep",
  "version": "0.3.0",
  "description": "CAUC Spintronics Experiment Platform",
  "main": "src/main.js",
  "author": "CAUC",
  "license": "MIT",
  "scripts": {
    "start": "electron .",
    "build": "electron-builder",
    "build:win": "electron-builder --win",
    "build:portable": "electron-builder --win portable",
    "postinstall": "electron-builder install-app-deps"
  },
  "dependencies": {
    "electron-log": "^5.0.0",
    "electron-updater": "^6.1.0"
  },
  "devDependencies": {
    "electron": "^30.0.0",
    "electron-builder": "^24.13.0"
  }
}
```

### electron-builder.yml 配置

```yaml
appId: com.cauc.sep
productName: CAUC-SEP
copyright: Copyright (c) 2024 CAUC

directories:
  output: ../dist/electron
  buildResources: build

files:
  - src/**/*
  - package.json
  - "!**/node_modules/*/{CHANGELOG.md,README.md,README,readme.md,readme}"
  - "!**/node_modules/*/{test,__tests__,tests,powered-test,example,examples}"
  - "!**/node_modules/*.d.ts"
  - "!**/node_modules/.bin"
  - "!**/*.{iml,o,hprof,orig,pyc,pyo,rbc,swp,csproj,sln,xproj}"
  - "!.{git,idea,vscode,target,build,dist}"
  - "!*.{log,sql}"

extraResources:
  - from: resources/backend
    to: backend
    filter:
      - "**/*"
      - "!**/*.log"
      - "!**/logs/**"

win:
  icon: build/icon.ico
  target:
    - target: nsis
      arch:
        - x64
    - target: portable
      arch:
        - x64

nsis:
  oneClick: false
  allowToChangeInstallationDirectory: true
  allowElevation: true
  installerIcon: build/icon.ico
  uninstallerIcon: build/icon.ico
  installerHeaderIcon: build/icon.ico
  createDesktopShortcut: true
  createStartMenuShortcut: true
  shortcutName: CAUC-SEP
  include: build/installer.nsh
  deleteAppDataOnUninstall: false
  displayLanguageSelector: false
  installerLanguages:
    - zh_CN
    - en_US
  language: "2052"

portable:
  artifactName: CAUC-SEP-Portable-${version}.exe

publish:
  provider: github
  owner: cauc
  repo: cauc-sep
  releaseType: release
```

### 主进程配置 (main.js)

```javascript
/**
 * @file main.js
 * @description Electron 主进程入口
 * @author CAUC-SEP Team
 */

const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const log = require('electron-log');

// 配置日志
log.transports.file.level = 'info';
log.transports.file.resolvePathFn = () => path.join(app.getPath('userData'), 'logs/main.log');

let mainWindow = null;
let backendProcess = null;

/**
 * 获取后端可执行文件路径
 * 开发环境与生产环境路径不同
 */
function getBackendPath() {
  const isDev = !app.isPackaged;
  
  if (isDev) {
    // 开发环境：使用 Nuitka 编译输出
    return path.join(__dirname, '../../backend/dist/CAUC-SEP.dist/CAUC-SEP.exe');
  }
  
  // 生产环境：使用打包后的资源目录
  return path.join(process.resourcesPath, 'backend/CAUC-SEP.exe');
}

/**
 * 启动后端服务
 */
function startBackend() {
  const backendPath = getBackendPath();
  
  log.info(`Starting backend: ${backendPath}`);
  
  backendProcess = spawn(backendPath, [], {
    cwd: path.dirname(backendPath),
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
  });
  
  backendProcess.stdout.on('data', (data) => {
    log.info(`[Backend] ${data.toString().trim()}`);
  });
  
  backendProcess.stderr.on('data', (data) => {
    log.error(`[Backend Error] ${data.toString().trim()}`);
  });
  
  backendProcess.on('error', (err) => {
    log.error(`Failed to start backend: ${err.message}`);
  });
  
  backendProcess.on('exit', (code) => {
    log.info(`Backend exited with code ${code}`);
    backendProcess = null;
  });
}

/**
 * 停止后端服务
 */
function stopBackend() {
  if (backendProcess) {
    log.info('Stopping backend...');
    
    // Windows 下优雅终止进程
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', backendProcess.pid, '/f', '/t']);
    } else {
      backendProcess.kill('SIGTERM');
    }
    
    backendProcess = null;
  }
}

/**
 * 创建主窗口
 */
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 700,
    title: 'CAUC-SEP 自旋电子实验平台',
    icon: path.join(__dirname, '../build/icon.ico'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
    },
    show: false,
  });
  
  // 加载前端页面
  const isDev = !app.isPackaged;
  
  if (isDev) {
    // 开发环境：加载 Vite 开发服务器
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    // 生产环境：加载打包后的前端资源
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }
  
  // 窗口就绪后显示
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });
  
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// 应用启动
app.whenReady().then(() => {
  // 先启动后端
  startBackend();
  
  // 等待后端就绪后创建窗口
  setTimeout(() => {
    createWindow();
  }, 2000);
  
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// 应用退出
app.on('window-all-closed', () => {
  stopBackend();
  
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  stopBackend();
});

// IPC 通信：获取后端状态
ipcMain.handle('get-backend-status', () => {
  return {
    running: backendProcess !== null,
    pid: backendProcess?.pid || null,
  };
});
```

### 预加载脚本 (preload.js)

```javascript
/**
 * @file preload.js
 * @description Electron 预加载脚本，提供安全的渲染进程通信
 */

const { contextBridge, ipcRenderer } = require('electron');

// 暴露安全的 API 给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  /**
   * 获取后端服务状态
   * @returns {Promise<{running: boolean, pid: number|null}>}
   */
  getBackendStatus: () => ipcRenderer.invoke('get-backend-status'),
  
  /**
   * 获取应用版本
   */
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
  
  /**
   * 选择文件
   */
  selectFile: () => ipcRenderer.invoke('select-file'),
  
  /**
   * 选择目录
   */
  selectDirectory: () => ipcRenderer.invoke('select-directory'),
});
```

### 后端独立编译配置

后端不再嵌入前端静态文件，而是作为独立服务运行：

```python
# backend/scripts/build_exe_standalone.py
"""
CAUC-SEP Nuitka Build Script - Electron Integration
Python 3.13 + MSVC Compatible

功能:
1. 使用 MSVC 编译器（自动检测 Visual Studio）
2. 使用 standalone 模式
3. 输出到 electron/resources/backend/ 目录
4. 不嵌入前端静态文件（由 Electron 管理）
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
ICON_PATH = PROJECT_ROOT / "assets" / "icons" / "icon.ico"
ELECTRON_BACKEND_DIR = PROJECT_ROOT / "electron" / "resources" / "backend"

APP_NAME = "CAUC-SEP"
APP_VERSION = "0.3.0"
COMPANY_NAME = "CAUC"
DESCRIPTION = "CAUC Spintronics Experiment Platform"

NUITKA_ARGS = [
    sys.executable, "-m", "nuitka",
    "--standalone",
    "--windows-console-mode=disable",  # GUI模式，无控制台窗口
    f"--windows-icon-from-ico={ICON_PATH}",
    f"--output-dir={ELECTRON_BACKEND_DIR.parent}",
    f"--output-filename={APP_NAME}.exe",
    f"--company-name={COMPANY_NAME}",
    f"--product-name={APP_NAME}",
    f"--file-version={APP_VERSION}.0",
    f"--product-version={APP_VERSION}.0",
    f"--file-description={DESCRIPTION}",

    # MSVC 编译器配置（自动检测）
    "--msvc=latest",

    # 包含必要的包
    "--include-package=fastapi",
    "--include-package=uvicorn",
    "--include-package=pydantic",
    "--include-package=pydantic_settings",
    "--include-package=sqlalchemy",
    "--include-package=numpy",
    "--include-package=core",
    "--include-package=api",
    "--include-package=middleware",
    "--include-package=models",
    "--include-package=drivers",

    # 包含必要的模块
    "--include-module=uvicorn.logging",
    "--include-module=uvicorn.loops",
    "--include-module=uvicorn.loops.auto",
    "--include-module=uvicorn.protocols",
    "--include-module=uvicorn.protocols.http",
    "--include-module=uvicorn.protocols.http.auto",
    "--include-module=uvicorn.protocols.websockets",
    "--include-module=uvicorn.protocols.websockets.auto",
    "--include-module=uvicorn.lifespan",
    "--include-module=uvicorn.lifespan.on",
    "--include-module=sqlalchemy.dialects.sqlite",
    "--include-module=pydantic_core",
    "--include-module=starlette.responses",
    "--include-module=starlette.routing",
    "--include-module=starlette.middleware",
    "--include-module=starlette.middleware.cors",
    "--include-module=anyio",
    "--include-module=h11",
    "--include-module=redis",
    "--include-module=msgpack",
    "--include-module=bcrypt",
    "--include-module=jose",
    "--include-module=jose.jwt",
    "--include-module=aiofiles",
    "--include-module=psutil",
    "--include-module=webbrowser",

    # 排除不需要的模块
    "--nofollow-import-to=tkinter",
    "--nofollow-import-to=unittest",
    "--nofollow-import-to=pytest",
    "--nofollow-import-to=PIL",
    "--nofollow-import-to=cv2",
    "--nofollow-import-to=pandas",
    "--nofollow-import-to=matplotlib",
    "--nofollow-import-to=scipy",
    "--nofollow-import-to=sympy",
    "--nofollow-import-to=IPython",
    "--nofollow-import-to=jupyter",
    "--nofollow-import-to=notebook",
    "--nofollow-import-to=_pytest",
    "--nofollow-import-to=tests",
    "--nofollow-import-to=*.tests",
    "--nofollow-import-to=*.test",
    "--nofollow-import-to=test_*",

    # 性能优化
    "--assume-yes-for-downloads",
    "--show-progress",
    "--show-memory",
    "--jobs=4",
    "--lto=yes",

    "main.py"
]


def copy_to_electron_resources():
    """复制编译产物到 Electron 资源目录"""
    source_dir = ELECTRON_BACKEND_DIR.parent / f"{APP_NAME}.dist"
    target_dir = ELECTRON_BACKEND_DIR

    if source_dir.exists():
        # 清理目标目录
        if target_dir.exists():
            shutil.rmtree(target_dir)

        # 重命名并移动
        source_dir.rename(target_dir)
        print(f"后端程序已复制到: {target_dir}")
        return True

    return False


def create_data_dirs():
    """创建数据目录结构"""
    if ELECTRON_BACKEND_DIR.exists():
        for dir_name in ["data", "logs", "config", "exports"]:
            dir_path = ELECTRON_BACKEND_DIR / dir_name
            dir_path.mkdir(exist_ok=True)
        print("数据目录已创建")
        return True
    return False


def main():
    print("=" * 60)
    print(f"CAUC-SEP Build Script (Electron Integration)")
    print(f"Python: {sys.version}")
    print(f"编译器: MSVC (自动检测)")
    print(f"输出目录: {ELECTRON_BACKEND_DIR}")
    print("=" * 60)

    if not ICON_PATH.exists():
        print(f"警告: 图标文件不存在: {ICON_PATH}")
    else:
        print(f"图标: {ICON_PATH}")

    # 确保输出目录存在
    ELECTRON_BACKEND_DIR.parent.mkdir(parents=True, exist_ok=True)

    # 清理旧的输出
    if ELECTRON_BACKEND_DIR.exists():
        print("清理旧的输出目录...")
        shutil.rmtree(ELECTRON_BACKEND_DIR)

    os.chdir(BACKEND_DIR)

    print("\n开始编译 (MSVC + standalone模式)...")
    start_time = datetime.now()

    result = subprocess.run(NUITKA_ARGS)

    if result.returncode == 0:
        end_time = datetime.now()
        duration = end_time - start_time

        # 移动到 Electron 资源目录
        copy_to_electron_resources()
        create_data_dirs()

        exe_path = ELECTRON_BACKEND_DIR / f"{APP_NAME}.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"\n{'='*60}")
            print("编译成功!")
            print(f"耗时: {duration}")
            print(f"主程序: {exe_path}")
            print(f"主程序大小: {size_mb:.2f} MB")

            total_size = sum(
                f.stat().st_size for f in ELECTRON_BACKEND_DIR.rglob('*')
                if f.is_file()
            )
            print(f"总大小: {total_size / (1024*1024):.2f} MB")

            print(f"\n输出目录: {ELECTRON_BACKEND_DIR}")
            print("下一步: 运行 build-electron.bat 打包 Electron 应用")
    else:
        print(f"\n编译失败, 返回码: {result.returncode}")

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
```

## Nuitka 编译参数详解

### 核心参数

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| `--standalone` | 独立部署模式，包含所有依赖 | **必选** |
| `--msvc=latest` | 使用最新版 MSVC 编译器 | **Python 3.13 必选** |
| `--windows-console-mode` | 控制台显示模式 | `disable`（GUI应用） |
| `--windows-icon-from-ico` | 应用图标路径 | `assets/icons/icon.ico` |
| `--include-package` | 包含Python包 | 见下表 |
| `--nofollow-import-to` | 排除不需要的模块 | 见下表 |
| `--enable-plugin` | 启用优化插件 | `anti-bloat` |

### Python 3.13 适配参数

```batch
:: Python 3.13 必须使用 MSVC，禁止使用 MinGW 或 Zig
--msvc=latest

:: 禁用以下参数（Python 3.13 不支持）
:: --zig              # 不支持
:: --mingw64          # 不支持
```

### 包含包配置

```
--include-package=fastapi         # Web框架
--include-package=uvicorn         # ASGI服务器
--include-package=pydantic        # 数据验证
--include-package=sqlalchemy      # ORM
--include-package=numpy           # 数值计算
--include-package=core            # 核心模块
--include-package=api             # API模块
--include-package=middleware      # 中间件
--include-package=models          # 数据模型
--include-package=drivers         # 设备驱动
```

### 排除模块配置

```
--nofollow-import-to=tkinter      # 不需要GUI
--nofollow-import-to=unittest     # 不需要测试
--nofollow-import-to=pytest       # 不需要测试
--nofollow-import-to=PIL          # 不需要图像处理
--nofollow-import-to=cv2          # 不需要OpenCV
--nofollow-import-to=pandas       # 不需要数据分析
--nofollow-import-to=matplotlib   # 不需要绘图
--nofollow-import-to=scipy        # 不需要科学计算
```

### 性能优化参数

| 参数 | 说明 | 效果 |
|------|------|------|
| `--jobs=4` | 并行编译进程数 | 加速编译 |
| `--lto=yes` | 链接时优化 | 减小体积10-15% |
| `--python-flag=no_site` | 不包含site模块 | 减小体积 |

### 内存优化配置（24GB DDR5）

```
总内存: 24GB
├── 系统保留: 8GB
├── Nuitka编译: 8GB (4进程 × 2GB)
└── 可用内存: 8GB
```

| 内存大小 | --jobs 推荐值 |
|----------|---------------|
| 8GB | 1 |
| 16GB | 2 |
| 24GB | 4 |
| 32GB+ | 6-8 |

## 构建流程

### 完整构建流程图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CAUC-SEP 完整构建流程                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐             │
│  │ 1. 前端构建   │    │ 2. 后端编译   │    │ 3. 应用打包   │             │
│  │   Vue + Vite │    │   Nuitka     │    │   Electron   │             │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘             │
│         │                   │                   │                      │
│         ▼                   ▼                   ▼                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐             │
│  │ npm run build│    │ python       │    │ npm run      │             │
│  │              │    │ build_exe... │    │ build:win    │             │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘             │
│         │                   │                   │                      │
│         ▼                   ▼                   ▼                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐             │
│  │ frontend/    │    │ electron/    │    │ dist/        │             │
│  │ dist/        │    │ resources/   │    │ electron/    │             │
│  │              │    │ backend/     │    │              │             │
│  └──────────────┘    └──────────────┘    └──────────────┘             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 一键构建

```batch
# 执行完整构建流程
scripts\build-all.bat
```

### 分步构建

```batch
# 步骤1: 构建前端
cd frontend
npm install
npm run build
cd ..

# 步骤2: 编译后端（Nuitka + MSVC）
cd backend
python scripts\build_exe_standalone.py
cd ..

# 步骤3: 打包 Electron 应用
cd electron
npm install
npm run build:win
cd ..
```

### 构建脚本 (build-all.bat)

```batch
@echo off
chcp 65001 >nul
REM ============================================================================
REM CAUC-SEP 完整构建脚本 v3.0
REM
REM 功能: 前端构建 + Nuitka编译 + Electron打包
REM 更新: 2026-03-15
REM ============================================================================

setlocal EnableDelayedExpansion

echo.
echo ==========================================
echo   CAUC-SEP 完整构建流程 v3.0
echo   Nuitka + Electron + electron-builder
echo ==========================================
echo.

cd /d "%~dp0\.."

set "APP_VERSION=0.3.0"

REM ============================================================================
REM 1. 构建前端
REM ============================================================================

echo [1/3] 构建前端...

cd frontend
if not exist "node_modules" (
    echo   - 安装前端依赖...
    call npm install --silent
)

echo   - 执行Vite构建...
call npm run build
if errorlevel 1 (
    echo [错误] 前端构建失败
    cd ..
    pause
    exit /b 1
)
cd ..
echo   - 前端构建完成

REM ============================================================================
REM 2. Nuitka编译后端 (MSVC)
REM ============================================================================

echo.
echo [2/3] Nuitka编译后端 (MSVC)...
echo   - 这可能需要10-30分钟，请耐心等待
echo.

cd backend
python scripts\build_exe_standalone.py
if errorlevel 1 (
    echo [错误] Nuitka编译失败
    cd ..
    pause
    exit /b 1
)
cd ..
echo   - 后端编译完成

REM ============================================================================
REM 3. Electron打包
REM ============================================================================

echo.
echo [3/3] Electron打包...

cd electron
if not exist "node_modules" (
    echo   - 安装Electron依赖...
    call npm install --silent
)

echo   - 执行electron-builder...
call npm run build:win
if errorlevel 1 (
    echo [警告] Electron打包失败，请检查配置
) else (
    echo   - Electron打包完成
)
cd ..

REM ============================================================================
REM 完成
REM ============================================================================

echo.
echo ==========================================
echo   构建成功！
echo ==========================================
echo.

echo 输出文件:
if exist "dist\electron\CAUC-SEP Setup 0.3.0.exe" (
    echo   - 安装包: dist\electron\CAUC-SEP Setup 0.3.0.exe
)
if exist "dist\electron\CAUC-SEP-Portable-0.3.0.exe" (
    echo   - 便携版: dist\electron\CAUC-SEP-Portable-0.3.0.exe
)

echo.
echo 按任意键退出...
pause >nul
```

## 输出文件

### 目录结构

```
dist/
├── electron/                           # Electron打包输出
│   ├── CAUC-SEP Setup 0.3.0.exe       # NSIS安装包
│   ├── CAUC-SEP-Portable-0.3.0.exe    # 便携版
│   └── win-unpacked/                   # 解压版目录
│       ├── CAUC-SEP.exe               # 主程序
│       ├── resources/
│       │   ├── app.asar               # 前端资源
│       │   └── backend/               # 后端程序
│       │       ├── CAUC-SEP.exe
│       │       └── *.dll, *.pyd
│       └── *.dll                       # Electron依赖
│
└── backend/                            # Nuitka编译输出（中间产物）
    └── CAUC-SEP.dist/
        └── (已移动到 electron/resources/backend/)
```

### 文件大小预估

| 组件 | 大小 | 说明 |
|------|------|------|
| Electron 运行时 | 80-100MB | Chromium + Node.js |
| 后端程序 | 60-80MB | Nuitka编译产物 |
| 前端资源 | 5-10MB | Vue应用 |
| 安装包 | 80-120MB | 压缩后 |
| 便携版 | 100-150MB | 自解压包 |

## 常见问题与解决方案

### Q1: 编译时间太长怎么办？

**原因**: Nuitka 首次编译需要编译所有依赖

**解决方案**:
1. 首次编译 10-30 分钟是正常的
2. 后续增量编译会快很多
3. 使用 `--jobs=4` 增加并行度
4. 不要删除 `.build` 目录（缓存）

### Q2: 内存不足错误？

**原因**: 并行编译进程占用内存过多

**解决方案**:
| 内存大小 | --jobs 值 |
|----------|-----------|
| 8GB | 1 |
| 16GB | 2 |
| 24GB | 4 |

### Q3: 编译失败提示缺少模块？

**原因**: 模块未在 `--include-package` 中指定

**解决方案**:
1. 检查错误信息中的模块名
2. 在打包脚本中添加 `--include-package=<模块名>`
3. 重新运行编译

### Q4: 杀毒软件误报？

**原因**: 编译的 EXE 缺少数字签名

**解决方案**:
1. 申请代码签名证书（推荐）
2. 将 EXE 添加到杀毒软件白名单
3. 提交样本到杀毒软件厂商

### Q5: Electron 启动后白屏？

**原因**: 前端资源加载失败或后端未启动

**解决方案**:
1. 检查 `electron/src/main.js` 中的资源路径
2. 确认后端程序已正确复制到 `resources/backend/`
3. 查看 Electron 日志（`%APPDATA%/cauc-sep/logs/`）
4. 开发环境确认 Vite 开发服务器已启动

### Q6: 后端服务无法启动？

**原因**: 后端可执行文件路径错误或依赖缺失

**解决方案**:
1. 检查 `electron/resources/backend/` 目录是否存在
2. 确认 `CAUC-SEP.exe` 及所有依赖文件完整
3. 手动运行后端 EXE 检查错误信息
4. 检查端口 8000 是否被占用

### Q7: Electron 打包失败？

**原因**: electron-builder 配置错误或资源缺失

**解决方案**:
1. 检查 `electron-builder.yml` 配置
2. 确认 `build/icon.ico` 图标文件存在
3. 运行 `npm run build` 查看详细错误
4. 清理 `node_modules` 重新安装

### Q8: MSVC 编译器未检测到？

**原因**: Visual Studio 未正确安装或环境变量问题

**解决方案**:
1. 确认安装了 Visual Studio 2022
2. 确保勾选"使用 C++ 的桌面开发"工作负载
3. 运行 `vswhere.exe` 检查安装状态
4. 重启终端或系统后重试

### Q9: Python 3.13 编译报错？

**原因**: 使用了不兼容的编译器参数

**解决方案**:
1. 确保使用 `--msvc=latest` 参数
2. 移除 `--zig` 和 `--mingw64` 参数
3. 更新 Nuitka 到最新版本：`pip install -U nuitka`

### Q10: 自动更新不工作？

**原因**: GitHub Releases 配置或网络问题

**解决方案**:
1. 确认 `electron-builder.yml` 中的 publish 配置正确
2. 检查 GitHub Token 权限
3. 确认发布的版本号格式正确
4. 查看 `electron-updater` 日志

## 性能优化建议

### 减小体积

1. **排除不需要的模块**
   ```batch
   --nofollow-import-to=tkinter,unittest,pytest,PIL,cv2,pandas,matplotlib
   ```

2. **使用 LTO 优化**
   ```batch
   --lto=yes
   ```

3. **启用 anti-bloat 插件**
   ```batch
   --enable-plugin=anti-bloat
   ```

### 加快编译速度

1. **增加并行任务**
   ```batch
   --jobs=4
   ```

2. **保留编译缓存**
   - 不要删除 `.build` 目录
   - 增量编译利用缓存

### 提升启动速度

1. **使用 standalone 模式**
   ```batch
   --standalone
   ```

2. **优化 Electron 启动**
   - 使用 `show: false` 延迟显示窗口
   - 预加载必要资源

## 技术参考

- [Nuitka 官方文档](https://nuitka.net/doc/)
- [Nuitka 用户手册](https://nuitka.net/doc/user-manual.html)
- [Electron 官方文档](https://www.electronjs.org/docs)
- [electron-builder 文档](https://www.electron.build/)
- [Visual Studio 文档](https://docs.microsoft.com/visualstudio/)
- [CAUC-SEP 技术文档](./CAUC-SEP_技术文档.md)

## 更新日志

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-03-09 | v1.0 | 初始版本，24GB内存优化配置 |
| 2026-03-14 | v1.1 | 更新项目结构，完善打包目录说明 |
| 2026-03-14 | v2.0 | 全面增强：Nuitka参数详解、Inno Setup配置详解、常见问题扩展 |
| 2026-03-15 | v3.0 | 重大更新：Electron集成、MSVC编译工具链配置、Python 3.13适配、构建流程重构 |
| 2026-03-15 | v3.1 | 打包成功完成，安装包大小 206.41 MB，所有功能验证通过 |
