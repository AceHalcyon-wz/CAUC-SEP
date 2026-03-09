# CAUC-SEP Nuitka打包指南

## 概述

本文档提供CAUC-SEP自旋电子实验平台的完整打包方案，使用Nuitka工具生成专业级Windows安装包。

## 系统要求

### 硬件配置
- **CPU**: AMD Ryzen 7-H255 或同等性能处理器
- **内存**: 24GB DDR5（推荐）
- **硬盘**: 至少20GB可用空间（SSD推荐）
- **操作系统**: Windows 11 25H2 64位

### 软件要求
- Python 3.10+
- Node.js 18+
- Inno Setup 6.x（可选，用于生成安装包）

## 快速开始

### 一键打包

```batch
# 1. 初始化打包环境（首次运行）
scripts\setup-nuitka-env.bat

# 2. 执行完整打包
scripts\build-nuitka.bat
```

### 分步打包

```batch
# 步骤1: 激活虚拟环境
.venv-nuitka\Scripts\activate.bat

# 步骤2: 构建前端
cd frontend
npm install
npm run build
cd ..

# 步骤3: 打包后端
cd backend
python -m nuitka --onefile --standalone --windows-console-mode=disable --windows-icon-from-ico=assets/icon.ico --output-dir=dist --output-filename=CAUC-SEP-Backend.exe --jobs=4 main.py
cd ..

# 步骤4: 生成安装包（可选）
cd installer
iscc CAUC-SEP.iss
```

## 打包参数优化

### 24GB内存优化配置

| 参数 | 值 | 说明 |
|------|-----|------|
| `--jobs` | 4 | 并行编译进程数 |
| `--lto` | yes | 链接时优化，减小体积 |
| `--zig` | 启用 | 使用Zig编译器后端，更快 |
| 内存预留 | 8GB | 系统保留内存 |

### 内存使用预估

```
总内存: 24GB
├── 系统保留: 8GB
├── Nuitka编译: 8GB (4进程 × 2GB)
└── 可用内存: 8GB
```

## 输出文件

### 目录结构

```
dist/
├── release/                    # 发布目录
│   ├── CAUC-SEP-Backend.exe   # 后端可执行文件
│   ├── frontend/              # 前端静态文件
│   ├── assets/                # 资源文件
│   ├── logs/                  # 日志目录
│   ├── data/                  # 数据目录
│   ├── config/                # 配置目录
│   ├── start.bat              # 启动脚本
│   ├── stop.bat               # 停止脚本
│   └── README.txt             # 说明文件
│
└── installer/
    └── CAUC-SEP-Setup-v0.3.0.exe  # 安装包
```

### 文件大小预估

| 组件 | 大小 |
|------|------|
| 后端EXE | 80-120MB |
| 前端文件 | 5-10MB |
| 资源文件 | 1-2MB |
| 安装包 | 50-80MB |

## 常见问题

### Q: 编译时间太长怎么办？

A: Nuitka首次编译需要10-30分钟，这是正常的。后续增量编译会快很多。

### Q: 内存不足错误？

A: 减少`--jobs`参数值。对于16GB内存，建议设为2；对于8GB内存，建议设为1。

### Q: 编译失败提示缺少模块？

A: 检查`nuitka-config.py`中的`include-module`列表，添加缺失的模块。

### Q: 杀毒软件误报？

A: 这是Nuitka打包的常见问题。建议：
1. 申请代码签名证书
2. 将EXE添加到杀毒软件白名单
3. 使用UPX压缩（可能增加误报）

### Q: 启动时找不到前端文件？

A: 确保`main.py`使用绝对路径处理静态文件：

```python
import sys
from pathlib import Path

program_dir = Path(sys.argv[0]).parent
static_path = program_dir / "frontend"
```

## 性能优化建议

### 减小体积

1. **排除不需要的模块**
   ```python
   nofollow-import-to = ["tkinter", "unittest", "test", "PIL", "cv2"]
   ```

2. **使用LTO优化**
   ```batch
   --lto=yes
   ```

3. **启用压缩**
   ```batch
   --onefile  # 自动启用压缩
   ```

### 加快编译速度

1. **使用Zig编译器**
   ```batch
   --zig
   ```

2. **增加并行任务**
   ```batch
   --jobs=4  # 根据内存调整
   ```

3. **缓存编译结果**
   - Nuitka会自动缓存，不要删除`.build`目录

## 安装包特性

生成的安装包具有以下专业特性：

| 特性 | 说明 |
|------|------|
| 安装向导 | 中英文双语界面 |
| 桌面快捷方式 | 自动创建 |
| 开始菜单项 | 自动创建 |
| 卸载程序 | 控制面板可卸载 |
| 用户数据保护 | 卸载时询问是否保留 |
| 自动启动选项 | 可选开机启动 |

## 技术参考

- [Nuitka官方文档](https://nuitka.net/doc/)
- [Inno Setup文档](https://jrsoftware.org/ishelp/)
- [CAUC-SEP技术文档](../docs/CAUC-SEP_技术文档_v3.0.md)

## 更新日志

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-03-09 | v1.0 | 初始版本，24GB内存优化配置 |
