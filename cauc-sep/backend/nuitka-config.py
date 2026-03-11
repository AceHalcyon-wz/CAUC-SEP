"""
Nuitka打包配置文件 - 简化版v4

功能：
- 配置CAUC-SEP后端打包参数
- 支持Windows可执行文件生成
- 优化打包体积和启动性能

修复内容：
- 简化include-module列表，只包含必要的模块
- 移除可能导致问题的选项
- 添加更好的错误处理

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
        return 2


nuitka_options = {
    "project-name": "CAUC-SEP-Backend",
    "project-description": "CAUC自旋电子器件实验平台后端服务",
    "project-version": "0.4.0",
    "output-dir": str(project_dir / "dist"),
    "output-filename": "CAUC-SEP-Backend",
    "standalone": True,
    "onefile": True,
    "windows-console-mode": "disable",
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
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "uvicorn.config",
        "uvicorn.main",
        "sqlalchemy.dialects.sqlite",
        "sqlalchemy.pool",
        "sqlalchemy.engine",
        "sqlalchemy.orm",
        "pydantic_core",
        "pydantic_settings",
        "jose",
        "jose.jwt",
        "jose.jws",
        "jose.constants",
        "jose.exceptions",
        "passlib",
        "passlib.hash",
        "passlib.handlers",
        "passlib.handlers.bcrypt",
        "bcrypt",
        "starlette",
        "starlette.responses",
        "starlette.routing",
        "starlette.middleware",
        "starlette.middleware.cors",
        "starlette.requests",
        "starlette.exceptions",
        "starlette.staticfiles",
        "anyio",
        "anyio._backends",
        "anyio._backends._asyncio",
        "anyio.abc",
        "sniffio",
        "h11",
        "h11._events",
        "h11._connection",
        "h11._state",
        "h11._headers",
        "redis",
        "redis.asyncio",
        "redis.asyncio.connection",
        "redis.asyncio.client",
        "msgpack",
        "aiofiles",
        "aiofiles.os",
        "aiofiles.tempfile",
        "psutil",
        "lmfit.minimizer",
        "lmfit.model",
        "lmfit.parameter",
        "h5py.h5",
        "h5py._hl",
        "h5py._hl.files",
        "h5py._hl.dataset",
        "h5py._hl.group",
        "email_validator",
        "click",
        "click.core",
        "click.decorators",
        "click.exceptions",
        "typing_extensions",
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
        "anti-bloat",
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
    "follow-imports": True,
    "remove-output": True,
}


nuitka_options = {k: v for k, v in nuitka_options.items() if v is not None and v != [] and v != ""}


if __name__ == "__main__":
    print("Nuitka配置已加载（简化版v4）:")
    print(f"  - 并行任务数: {nuitka_options.get('jobs', 2)}")
    print(f"  - 输出目录: {nuitka_options['output-dir']}")
    print(f"  - 输出文件: {nuitka_options['output-filename']}.exe")
    print(f"  - Onefile模式: {nuitka_options.get('onefile', False)}")
    print(f"  - 包含包数量: {len(nuitka_options.get('include-package', []))}")
    print(f"  - 包含模块数量: {len(nuitka_options.get('include-module', []))}")
