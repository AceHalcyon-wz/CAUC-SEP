"""
Nuitka打包配置文件 - 修复版

功能：
- 配置CAUC-SEP后端打包参数
- 支持Windows可执行文件生成
- 优化打包体积和启动性能
- 24GB内存环境优化

修复内容：
- 添加认证模块(jose, passlib, bcrypt)
- 添加pydantic补充模块
- 添加starlette补充模块
- 添加数据处理子模块

使用方法：
    python -m nuitka --project-dir=backend --project-config=backend/nuitka-config.py main.py

或者直接运行：
    scripts\build-nuitka.bat

作者：Agent
日期：2026-03-10
"""

from pathlib import Path

project_dir = Path(__file__).parent


def get_memory_optimized_jobs():
    """
    根据系统内存自动计算并行任务数

    24GB内存配置：
    - 保留6GB给系统（优化）
    - 每个编译进程约1.5GB（优化）
    - 可用18GB / 1.5GB = 12进程（保守设为6）
    """
    try:
        import psutil

        total_memory_gb = psutil.virtual_memory().total / (1024**3)
        reserved_gb = 6
        per_job_gb = 1.5
        available_gb = max(total_memory_gb - reserved_gb, 4)
        jobs = min(int(available_gb / per_job_gb), 10)
        return max(jobs, 2)
    except ImportError:
        return 4


nuitka_options = {
    "project-name": "CAUC-SEP-Backend",
    "project-description": "CAUC自旋电子器件实验平台后端服务",
    "project-version": "0.4.0",
    "project-copyright": "CAUC 2024-2026",
    "output-dir": str(project_dir / "dist"),
    "output-filename": "CAUC-SEP-Backend",
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
        "sqlalchemy.pool",
        "sqlalchemy.engine",
        "sqlalchemy.orm",
        "pydantic_core",
        "pydantic_settings",
        "pydantic_core.core_schema",
        "pydantic_core.validators",
        "annotated_types",
        "jose",
        "jose.jwt",
        "jose.jws",
        "jose.jwe",
        "jose.constants",
        "jose.exceptions",
        "jose.utils",
        "passlib",
        "passlib.hash",
        "passlib.handlers",
        "passlib.handlers.bcrypt",
        "passlib.utils",
        "passlib.utils.handlers",
        "bcrypt",
        "multipart",
        "starlette",
        "starlette.responses",
        "starlette.routing",
        "starlette.middleware",
        "starlette.middleware.cors",
        "starlette.websockets",
        "starlette.requests",
        "starlette.status",
        "starlette.exceptions",
        "starlette.background",
        "starlette.datastructures",
        "starlette.types",
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
        "lmfit.minimizer",
        "lmfit.model",
        "lmfit.parameter",
        "lmfit.confidence",
        "lmfit.printfuncs",
        "h5py.h5",
        "h5py._hl",
        "h5py._hl.files",
        "h5py._hl.dataset",
        "h5py._hl.group",
        "h5py._hl.attrs",
        "email_validator",
    ],
    "nofollow-import-to": [
        "tkinter",
        "unittest",
        "test",
        "tests",
        "pytest",
        "sphinx",
        "docutils",
        "IPython",
        "jupyter",
        "notebook",
    ],
    "prefer-source-code": [],
    "enable-plugin": [
        "pydantic",
        "numpy",
        "scipy",
        "anti-bloat",
    ],
    "include-data-files": [
        (str(project_dir / "assets" / "icon.ico"), "assets/icon.ico"),
    ],
    "assume-yes-for-downloads": True,
    "show-progress": True,
    "show-memory": True,
    "show-modules": False,
    "lto": "yes",
    "jobs": get_memory_optimized_jobs(),
    "company-name": "CAUC",
    "product-name": "CAUC-SEP",
    "file-version": "0.4.0.0",
    "product-version": "0.4.0.0",
    "file-description": "CAUC自旋电子器件实验平台后端服务",
    "legal-copyright": "Copyright (C) 2024-2026 CAUC",
    "legal-trademarks": "",
    "windows-uac-admin": False,
    "windows-uac-uiaccess": False,
}

nuitka_options = {k: v for k, v in nuitka_options.items() if v is not None and v != [] and v != ""}


if __name__ == "__main__":
    print("Nuitka配置已加载（修复版）:")
    print(f"  - 并行任务数: {nuitka_options.get('jobs', 4)}")
    print(f"  - 输出目录: {nuitka_options['output-dir']}")
    print(f"  - 输出文件: {nuitka_options['output-filename']}.exe")
    print(f"  - 认证模块: 已添加 (jose, passlib, bcrypt)")
    print(f"  - 数据处理: 已添加 (lmfit, h5py 子模块)")
