"""
Nuitka打包配置文件 - 生产级优化版v3

功能：
- 配置CAUC-SEP后端打包参数
- 支持Windows可执行文件生成
- 优化打包体积和启动性能
- 24GB内存环境优化
- 完整模块包含配置

修复内容：
- 添加认证模块(jose, passlib, bcrypt)
- 添加pydantic补充模块
- 添加starlette补充模块
- 添加数据处理子模块
- 添加onefile模式支持
- 添加前端静态文件包含
- 添加缺失的uvicorn模块
- 添加缺失的anyio模块

使用方法：
    python build_nuitka.py

作者：Backend Engineer Agent
日期：2026-03-11
"""

from pathlib import Path

project_dir = Path(__file__).parent


def get_memory_optimized_jobs():
    """
    根据系统内存自动计算并行任务数。

    24GB内存配置：
    - 保留6GB给系统
    - 每个编译进程约1.5GB
    - 可用18GB / 1.5GB = 12进程（保守设为6）

    Returns:
        int: 并行任务数
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


def get_frontend_dist_path():
    """
    动态检测前端构建产物路径。

    Returns:
        Path | None: 前端dist目录路径
    """
    possible_paths = [
        project_dir / "frontend" / "dist",
        project_dir.parent / "frontend" / "dist",
        project_dir / "dist" / "frontend",
    ]

    for path in possible_paths:
        if path.exists() and any(path.iterdir()):
            return path
    return None


nuitka_options = {
    "project-name": "CAUC-SEP-Backend",
    "project-description": "CAUC自旋电子器件实验平台后端服务",
    "project-version": "0.4.0",
    "project-copyright": "CAUC 2024-2026",
    "output-dir": str(project_dir / "dist"),
    "output-filename": "CAUC-SEP-Backend",
    "standalone": True,
    "onefile": True,
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
        "migrations",
    ],
    "include-module": [
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.http.httptools_impl",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.websockets.websockets_impl",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        "uvicorn.config",
        "uvicorn.server",
        "uvicorn.main",
        "uvicorn.supervisors",
        "uvicorn.supervisors.basereload",
        "uvicorn.supervisors.statreload",
        "uvicorn.supervisors.watchgodreload",
        "sqlalchemy.dialects.sqlite",
        "sqlalchemy.pool",
        "sqlalchemy.engine",
        "sqlalchemy.orm",
        "sqlalchemy.ext.asyncio",
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
        "jose.backends",
        "jose.backends.cryptography_backend",
        "passlib",
        "passlib.hash",
        "passlib.handlers",
        "passlib.handlers.bcrypt",
        "passlib.utils",
        "passlib.utils.handlers",
        "bcrypt",
        "_bcrypt",
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
        "starlette.staticfiles",
        "starlette.templating",
        "httpx",
        "httpx._transports",
        "httpx._transports.default",
        "httpx._config",
        "httpx._content",
        "httpx._models",
        "anyio",
        "anyio._backends",
        "anyio._backends._asyncio",
        "anyio.abc",
        "anyio.from_thread",
        "anyio.lowlevel",
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
        "redis.asyncio",
        "redis.asyncio.connection",
        "redis.asyncio.client",
        "msgpack",
        "msgpack.fallback",
        "aiofiles",
        "aiofiles.os",
        "aiofiles.tempfile",
        "psutil",
        "psutil._pswindows",
        "psutil._common",
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
        "watchfiles",
        "watchfiles.main",
        "watchfiles.filters",
        "opentelemetry",
        "opentelemetry.sdk",
        "opentelemetry.sdk.trace",
        "opentelemetry.sdk.resources",
        "opentelemetry.exporter.otlp",
        "click",
        "click.core",
        "click.decorators",
        "click.exceptions",
        "click.formatting",
        "click.parser",
        "click.termui",
        "click.types",
        "click.utils",
        "typing_extensions",
        "typing_inspect",
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
        "matplotlib",
        "PIL",
        "cv2",
        "torch",
        "tensorflow",
        "pandas",
        "polars",
        "dask",
        "numba",
        "cython",
        "bokeh",
        "plotly",
        "black",
        "ruff",
        "mypy",
        "isort",
    ],
    "prefer-source-code": [],
    "enable-plugin": [
        "pydantic",
        "numpy",
        "scipy",
        "anti-bloat",
    ],
    "include-data-files": [
        (str(project_dir / "assets" / "icon.ico"), "assets/icon.ico")
    ] if (project_dir / "assets" / "icon.ico").exists() else [],
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
    "follow-imports": True,
    "remove-output": True,
}

nuitka_options = {k: v for k, v in nuitka_options.items() if v is not None and v != [] and v != ""}


if __name__ == "__main__":
    print("Nuitka配置已加载（生产级优化版v3）:")
    print(f"  - 并行任务数: {nuitka_options.get('jobs', 4)}")
    print(f"  - 输出目录: {nuitka_options['output-dir']}")
    print(f"  - 输出文件: {nuitka_options['output-filename']}.exe")
    print(f"  - Onefile模式: {nuitka_options.get('onefile', False)}")
    print(f"  - 认证模块: 已添加 (jose, passlib, bcrypt)")
    print(f"  - 数据处理: 已添加 (lmfit, h5py 子模块)")
    print(f"  - 前端静态文件: 将在build_nuitka.py中动态添加")
    print(f"  - 前端dist路径: {get_frontend_dist_path()}")
