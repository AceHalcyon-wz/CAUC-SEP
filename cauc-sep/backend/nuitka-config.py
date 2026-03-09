"""
Nuitka打包配置文件

功能：
- 配置CAUC-SEP后端打包参数
- 支持Windows可执行文件生成
- 优化打包体积和启动性能
- 24GB内存环境优化

使用方法：
    python -m nuitka --project-dir=backend --project-config=backend/nuitka-config.py main.py

或者直接运行：
    scripts\build-nuitka.bat

作者：Agent
日期：2026-03-09
"""

from pathlib import Path

project_dir = Path(__file__).parent


def get_memory_optimized_jobs():
    """
    根据系统内存自动计算并行任务数

    24GB内存配置：
    - 保留8GB给系统
    - 每个编译进程约2GB
    - 可用16GB / 2GB = 8进程（保守设为4）
    """
    try:
        import psutil

        total_memory_gb = psutil.virtual_memory().total / (1024**3)
        reserved_gb = 8
        per_job_gb = 2
        available_gb = max(total_memory_gb - reserved_gb, 4)
        jobs = min(int(available_gb / per_job_gb), 8)
        return max(jobs, 2)
    except ImportError:
        return 4


nuitka_options = {
    "project-name": "CAUC-SEP-Backend",
    "project-description": "CAUC自旋电子器件实验平台后端服务",
    "project-version": "0.3.0",
    "project-copyright": "CAUC 2024-2026",
    "output-dir": str(project_dir / "dist"),
    "output-filename": "CAUC-SEP-Backend",
    "onefile": True,
    "standalone": True,
    "windows-console-mode": "disable",
    "windows-icon-from-ico": (
        str(project_dir / "assets" / "icon.ico")
        if (project_dir / "assets" / "icon.ico").exists()
        else None
    ),
    "include-package": [
        "fastapi",
        "uvicorn",
        "pydantic",
        "pydantic_settings",
        "sqlalchemy",
        "pymodbus",
        "serial",
        "numpy",
        "scipy",
        "lmfit",
        "h5py",
        "core",
        "api",
        "middleware",
        "models",
        "drivers",
    ],
    "include-module": [
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "sqlalchemy.dialects.sqlite",
        "pydantic_core",
        "pydantic_settings",
        "multipart",
        "starlette",
        "starlette.responses",
        "starlette.routing",
        "starlette.middleware",
        "starlette.middleware.cors",
        "starlette.websockets",
        "httpx",
        "httpx._transports",
        "httpx._transports.default",
        "anyio",
        "anyio._backends",
        "anyio._backends._asyncio",
        "sniffio",
        "h11",
        "h11._events",
        "h11._connection",
        "h11._state",
        "h11._headers",
        "h11._util",
        "h11._receivebuffer",
        "h11._abate",
        "h11._version",
        "redis",
        "msgpack",
        "aiofiles",
        "psutil",
        "psutil._pswindows",
    ],
    "nofollow-import-to": [
        "tkinter",
        "unittest",
        "test",
        "tests",
        "pytest",
        "PIL",
        "cv2",
        "sphinx",
        "docutils",
        "IPython",
        "jupyter",
        "notebook",
        "matplotlib",
        "matplotlib.pyplot",
    ],
    "prefer-source-code": [],
    "enable-plugin": [
        "pydantic",
        "numpy",
        "scipy",
    ],
    "include-data-files": [],
    "include-data-dirs": [],
    "assume-yes-for-downloads": True,
    "show-progress": True,
    "show-memory": True,
    "show-modules": False,
    "lto": "yes",
    "python-flag": "no_site",
    "jobs": get_memory_optimized_jobs(),
    "zig": True,
    "company-name": "CAUC",
    "product-name": "CAUC-SEP",
    "file-version": "0.3.0.0",
    "product-version": "0.3.0.0",
    "file-description": "CAUC自旋电子器件实验平台后端服务",
    "legal-copyright": "Copyright (C) 2024-2026 CAUC",
    "legal-trademarks": "",
    "windows-uac-admin": False,
    "windows-uac-uiaccess": False,
}

nuitka_options = {k: v for k, v in nuitka_options.items() if v is not None and v != [] and v != ""}

if __name__ == "__main__":
    print("Nuitka配置已加载:")
    print(f"  - 并行任务数: {nuitka_options.get('jobs', 4)}")
    print(f"  - 输出目录: {nuitka_options['output-dir']}")
    print(f"  - 输出文件: {nuitka_options['output-filename']}.exe")
