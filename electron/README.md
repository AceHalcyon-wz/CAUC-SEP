# Electron 桌面容器

CAUC-SEP 科学实验平台 Electron 桌面应用程序。

## 项目结构

```
electron/
├── src/
│   ├── main.js          # 主进程入口
│   └── preload.js       # 预加载脚本
├── build/
│   ├── entitlements.mac.plist  # macOS 权限配置
│   └── installer.nsh           # NSIS 自定义脚本
├── package.json         # 项目配置
└── electron-builder.yml # 构建配置
```

## 开发环境

### 前置要求

- Node.js >= 20.0.0
- npm >= 10.0.0

### 安装依赖

```bash
cd electron
npm install
```

### 开发模式运行

```bash
npm run dev
```

## 构建打包

### Windows NSIS 安装包

```bash
npm run build:win
```

构建产物位于 `dist/` 目录。

### macOS DMG

```bash
npm run build:mac
```

### Linux AppImage/DEB

```bash
npm run build:linux
```

## 资源路径

### 生产环境

- 后端: `resources/backend/backend.exe`
- 前端: `resources/frontend/`
- 图标: `resources/assets/icons/`

### 开发环境

- 后端: `../backend/dist/backend.exe`
- 前端: `../frontend/dist/`
- 图标: `../assets/icons/`

## 功能特性

### 后端进程管理

- 自动启动 FastAPI 后端子进程
- 进程健康检查（每30秒）
- 异常退出自动重启（最多3次）
- 优雅关闭进程

### 窗口管理

- 窗口尺寸记忆
- 最小化到系统托盘
- 开发者工具（开发模式）

### IPC 通信

渲染进程可通过 `window.electronAPI` 访问以下接口：

```javascript
// 应用信息
await window.electronAPI.app.getVersion()
await window.electronAPI.app.getPlatform()
await window.electronAPI.app.getPaths()

// 后端管理
await window.electronAPI.backend.getStatus()
await window.electronAPI.backend.restart()

// 外部链接
await window.electronAPI.shell.openExternal(url)

// 对话框
await window.electronAPI.dialog.showMessage(options)
```

## 配置项

应用配置存储在 `%APPDATA%/cauc-sep-config.json`：

```json
{
  "windowBounds": { "width": 1400, "height": 900 },
  "backendPort": 8000,
  "autoStartBackend": true
}
```

## 日志

日志文件位置：
- Windows: `%USERPROFILE%/AppData/Roaming/cauc-sep/logs/`
- macOS: `~/Library/Logs/cauc-sep/`
- Linux: `~/.config/cauc-sep/logs/`

## 注意事项

1. 构建前需先构建后端和前端：
   ```bash
   # 构建后端
   cd backend
   python -m nuitka ...

   # 构建前端
   cd frontend
   npm run build
   ```

2. Windows 下需要管理员权限才能安装到 Program Files

3. macOS 需要签名才能正常分发

## 版本历史

- v3.5.0 - 初始版本
