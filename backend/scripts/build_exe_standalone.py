"""
CAUC-SEP Nuitka Build Script - Electron Integration
Python 3.13 Compatible - Uses MSVC compiler

功能:
1. 使用 MSVC 编译器 (Python 3.13 推荐)
2. 使用 standalone 模式 (适配 Electron 打包)
3. 输出到 electron/resources/backend/ 目录
4. 排除不必要的模块减少体积
5. 使用 anti-bloat 插件优化体积
6. 并行编译适配 24GB 内存

作者：CAUC-SEP 开发团队
创建日期：2024-03-01
最后更新：2026-03-15
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path
from datetime import datetime

# ============================================================================
# 路径配置
# ============================================================================
PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
ICON_PATH = PROJECT_ROOT / "assets" / "icons" / "icon.ico"
ELECTRON_DIR = PROJECT_ROOT / "electron"
OUTPUT_DIR = ELECTRON_DIR / "resources" / "backend"

# ============================================================================
# 应用信息
# ============================================================================
APP_VERSION = "4.0.0"
COMPANY_NAME = "CAUC"
DESCRIPTION = "CAUC Spintronics Experiment Platform - Backend Service"

# ============================================================================
# Nuitka 编译参数
# ============================================================================
NUITKA_ARGS = [
    sys.executable, "-m", "nuitka",

    # === 基础配置 ===
    "--standalone",  # 使用 standalone 模式，不使用 onefile
    "--windows-console-mode=force",  # 强制控制台模式，便于调试
    f"--windows-icon-from-ico={ICON_PATH}",
    f"--output-dir={OUTPUT_DIR}",
    "--output-filename=backend.exe",  # 输出文件名

    # === 元数据 ===
    f"--company-name={COMPANY_NAME}",
    "--product-name=CAUC-SEP-Backend",
    f"--file-version={APP_VERSION}.0",
    f"--product-version={APP_VERSION}.0",
    f"--file-description={DESCRIPTION}",

    # === 编译器配置 ===
    "--msvc=latest",  # 使用最新 MSVC 编译器
    "--jobs=4",  # 并行编译，适配 24GB 内存

    # === 包含配置 - 核心依赖 ===
    "--include-package=fastapi",
    "--include-package=uvicorn",
    "--include-package=pydantic",
    "--include-package=pydantic_settings",
    "--include-package=pydantic_core",
    "--include-package=sqlalchemy",
    "--include-package=numpy",
    "--include-package=scipy",
    "--include-package=lmfit",
    "--include-package=h5py",
    "--include-package=pymodbus",

    # === 包含配置 - 项目模块 ===
    "--include-package=core",
    "--include-package=api",
    "--include-package=middleware",
    "--include-package=models",
    "--include-package=drivers",
    "--include-package=devices",
    "--include-package=schemas",

    # === 包含配置 - uvicorn 详细模块 ===
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

    # === 包含配置 - starlette 模块 ===
    "--include-module=starlette.responses",
    "--include-module=starlette.routing",
    "--include-module=starlette.middleware",
    "--include-module=starlette.middleware.cors",
    "--include-module=starlette.staticfiles",

    # === 包含配置 - 其他依赖 ===
    "--include-module=sqlalchemy.dialects.sqlite",
    "--include-module=anyio",
    "--include-module=anyio._backends",
    "--include-module=anyio._core",
    "--include-module=h11",
    "--include-module=httptools",
    "--include-module=redis",
    "--include-module=msgpack",
    "--include-module=bcrypt",
    "--include-package=passlib",
    "--include-package=passlib.handlers",
    "--include-package=passlib.handlers.bcrypt",
    "--include-module=jose",
    "--include-module=jose.jwt",
    "--include-module=jose.jws",
    "--include-module=jose.jwe",
    "--include-module=jose.constants",
    "--include-module=aiofiles",
    "--include-module=psutil",
    "--include-module=webbrowser",
    "--include-module=typing_extensions",
    "--include-module=annotated_types",

    # === 排除配置 - 不需要的模块 ===
    "--nofollow-import-to=tkinter",
    "--nofollow-import-to=unittest",
    "--nofollow-import-to=pytest",
    "--nofollow-import-to=test",
    "--nofollow-import-to=tests",
    "--nofollow-import-to=PIL",
    "--nofollow-import-to=cv2",
    "--nofollow-import-to=matplotlib",
    "--nofollow-import-to=IPython",
    "--nofollow-import-to=jupyter",
    "--nofollow-import-to=notebook",
    "--nofollow-import-to=_pytest",
    "--nofollow-import-to=*.tests",
    "--nofollow-import-to=*.test",
    "--nofollow-import-to=test_*",

    # === Anti-bloat 插件配置 ===
    "--enable-plugin=anti-bloat",

    # === 编译优化 ===
    "--assume-yes-for-downloads",
    "--show-progress",
    "--show-memory",
    "--verbose",

    # === 入口文件 ===
    "main.py"
]


def create_data_dirs(standalone_dir: Path) -> bool:
    """
    创建数据目录结构。

    Args:
        standalone_dir: standalone 输出目录路径

    Returns:
        bool: 是否成功创建目录
    """
    if not standalone_dir.exists():
        print(f"错误: 输出目录不存在: {standalone_dir}")
        return False

    for dir_name in ["data", "logs", "config", "exports"]:
        dir_path = standalone_dir / dir_name
        dir_path.mkdir(exist_ok=True)

    print("数据目录已创建")
    return True


def check_msvc_environment() -> bool:
    """
    检查 MSVC 编译环境是否可用。

    Returns:
        bool: MSVC 是否可用
    """
    # 检查 Visual Studio 或 Build Tools 是否安装
    vs_where = Path(
        r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
    )

    if vs_where.exists():
        print("检测到 Visual Studio Installer")
        return True

    # 检查常见的 MSVC 安装路径
    msvc_paths = [
        Path(r"C:\Program Files\Microsoft Visual Studio\2022\Community"),
        Path(r"C:\Program Files\Microsoft Visual Studio\2022\Professional"),
        Path(r"C:\Program Files\Microsoft Visual Studio\2022\Enterprise"),
        Path(r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Community"),
        Path(r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Professional"),
    ]

    for path in msvc_paths:
        if path.exists():
            print(f"检测到 MSVC: {path.name}")
            return True

    print("警告: 未检测到 MSVC 编译环境")
    print("请安装 Visual Studio Build Tools 或 Visual Studio")
    return False


def main() -> int:
    """
    主构建函数。

    Returns:
        int: 构建返回码 (0 表示成功)
    """
    print("=" * 60)
    print("CAUC-SEP Backend Build Script (Electron Integration)")
    print(f"Python: {sys.version}")
    print("编译器: MSVC (latest)")
    print(f"输出目录: {OUTPUT_DIR}")
    print("=" * 60)

    # 检查图标文件
    if not ICON_PATH.exists():
        print(f"警告: 图标文件不存在: {ICON_PATH}")
    else:
        print(f"图标: {ICON_PATH}")

    # 检查 MSVC 环境
    check_msvc_environment()

    # 创建输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # standalone 输出目录 (Nuitka 会根据入口文件名创建 main.dist)
    standalone_dir = OUTPUT_DIR / "main.dist"

    # 清理旧的输出目录
    if standalone_dir.exists():
        print("清理旧的输出目录...")
        shutil.rmtree(standalone_dir)

    # 切换到后端目录
    os.chdir(BACKEND_DIR)

    print("\n开始 Nuitka 编译 (standalone 模式)...")
    print("预计耗时: 10-30 分钟，请耐心等待...")
    print("-" * 60)

    start_time = datetime.now()

    # 执行 Nuitka 编译
    result = subprocess.run(NUITKA_ARGS)

    if result.returncode == 0:
        end_time = datetime.now()
        duration = end_time - start_time

        exe_path = standalone_dir / "backend.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"\n{'=' * 60}")
            print("编译成功!")
            print(f"耗时: {duration}")
            print(f"主程序: {exe_path}")
            print(f"主程序大小: {size_mb:.2f} MB")

            # 创建数据目录
            create_data_dirs(standalone_dir)

            # 计算总大小
            total_size = sum(
                f.stat().st_size for f in standalone_dir.rglob("*") if f.is_file()
            )
            print(f"总大小: {total_size / (1024 * 1024):.2f} MB")

            print(f"\n输出目录: {standalone_dir}")
            print("-" * 60)
            print("下一步: 运行 build-all.bat 进行 Electron 打包")
        else:
            print("\n警告: 编译完成但未找到输出文件")
            print(f"预期路径: {exe_path}")
    else:
        print(f"\n编译失败, 返回码: {result.returncode}")
        print("请检查错误信息并重试")

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
