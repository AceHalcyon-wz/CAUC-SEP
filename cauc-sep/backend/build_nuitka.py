"""
Nuitka编译脚本
用于在CI/CD环境中编译CAUC-SEP后端
"""
import os
import subprocess
import sys
from pathlib import Path


def main():
    print("=" * 50)
    print("  Nuitka Compilation Script v3")
    print("=" * 50)
    print()

    backend_dir = Path(__file__).parent.resolve()
    print(f"Backend directory: {backend_dir}")
    print(f"Current working directory: {os.getcwd()}")
    os.chdir(backend_dir)
    print(f"Changed to: {os.getcwd()}")
    print()

    icon_path = backend_dir / "assets" / "icon.ico"
    if not icon_path.exists():
        print(f"WARNING: Icon file not found at {icon_path}")
        print("Proceeding without icon...")
        icon_arg = None
    else:
        print(f"Icon found at: {icon_path}")
        icon_arg = f"--windows-icon-from-ico={icon_path}"

    base_args = [
        sys.executable, "-m", "nuitka",
        "--onefile",
        "--windows-console-mode=disable",
        "--output-dir=dist",
        "--output-filename=CAUC-SEP-Backend.exe",
    ]

    if icon_arg:
        base_args.append(icon_arg)

    packages = [
        "fastapi", "uvicorn", "pydantic", "pydantic_settings",
        "sqlalchemy", "pymodbus", "serial", "numpy", "scipy",
        "lmfit", "h5py", "core", "api", "middleware", "models", "drivers"
    ]

    modules = [
        "uvicorn.logging", "uvicorn.loops", "uvicorn.loops.auto",
        "uvicorn.protocols", "uvicorn.protocols.http", "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets", "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan", "uvicorn.lifespan.on",
        "sqlalchemy.dialects.sqlite", "sqlalchemy.pool", "sqlalchemy.engine", "sqlalchemy.orm",
        "pydantic_core", "pydantic_settings", "pydantic_core.core_schema", "pydantic_core.validators",
        "annotated_types",
        "jose", "jose.jwt", "jose.jws", "jose.jwe", "jose.constants", "jose.exceptions", "jose.utils",
        "passlib", "passlib.hash", "passlib.handlers", "passlib.handlers.bcrypt", "passlib.utils", "passlib.utils.handlers",
        "bcrypt",
        "multipart",
        "starlette", "starlette.responses", "starlette.routing",
        "starlette.middleware", "starlette.middleware.cors", "starlette.websockets",
        "starlette.requests", "starlette.status", "starlette.exceptions",
        "starlette.background", "starlette.datastructures", "starlette.types",
        "httpx", "httpx._transports", "httpx._transports.default",
        "anyio", "anyio._backends", "anyio._backends._asyncio",
        "sniffio",
        "h11", "h11._events", "h11._connection", "h11._state",
        "redis", "msgpack", "aiofiles",
        "psutil", "psutil._pswindows",
        "lmfit.minimizer", "lmfit.model", "lmfit.parameter", "lmfit.confidence", "lmfit.printfuncs",
        "h5py.h5", "h5py._hl", "h5py._hl.files", "h5py._hl.dataset", "h5py._hl.group", "h5py._hl.attrs",
        "email_validator",
        "matplotlib", "matplotlib.pyplot", "matplotlib.backends", "matplotlib.backends.backend_agg",
    ]

    nofollow = [
        "tkinter", "unittest", "test", "tests", "pytest",
        "PIL", "cv2", "sphinx", "docutils", "IPython", "jupyter", "notebook"
    ]

    plugins = ["pydantic", "numpy", "scipy", "anti-bloat", "matplotlib"]

    for pkg in packages:
        base_args.append(f"--include-package={pkg}")

    for mod in modules:
        base_args.append(f"--include-module={mod}")

    for nf in nofollow:
        base_args.append(f"--nofollow-import-to={nf}")

    for plugin in plugins:
        base_args.append(f"--enable-plugin={plugin}")

    base_args.extend([
        "--lto=yes",
        "--assume-yes-for-downloads",
        "--show-progress",
        "--show-memory",
        "--jobs=4",
        "main.py"
    ])

    zig_path = Path("C:/zig/zig.exe")
    if zig_path.exists():
        print("Zig compiler found at C:/zig, enabling Zig optimization")
        os.environ["PATH"] = f"C:\\zig;{os.environ.get('PATH', '')}"
        base_args.append("--zig")
    else:
        try:
            result = subprocess.run(["where", "zig"], capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                print("Zig compiler found in PATH, enabling Zig optimization")
                base_args.append("--zig")
            else:
                print("Zig compiler not found, proceeding without Zig optimization")
        except Exception:
            print("Zig compiler not found, proceeding without Zig optimization")

    print(f"Running Nuitka with {len(base_args)} arguments...")
    print()
    print("Command arguments:")
    for i, arg in enumerate(base_args):
        print(f"  [{i}] {arg}")
    print()

    command_str = " ".join(f'"{arg}"' if " " in arg else arg for arg in base_args)
    print(f"Full command:\n{command_str}")
    print()

    try:
        result = subprocess.run(
            base_args,
            check=False,
            text=True,
        )
    except Exception as e:
        print(f"ERROR: Failed to run Nuitka: {e}")
        import traceback
        traceback.print_exc()
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write("status=failed\n")
        sys.exit(1)

    if result.returncode == 0:
        print()
        print("=" * 50)
        print("  Nuitka Compilation Successful!")
        print("=" * 50)

        exe_path = Path("dist/CAUC-SEP-Backend.exe")
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"Output: {exe_path} ({size_mb:.2f} MB)")

        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write("status=success\n")
    else:
        print()
        print("=" * 50)
        print("  Nuitka Compilation FAILED!")
        print(f"  Exit code: {result.returncode}")
        print("=" * 50)

        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write("status=failed\n")

        sys.exit(1)


if __name__ == "__main__":
    main()
