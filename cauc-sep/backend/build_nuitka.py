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
    print("  Nuitka Compilation Script")
    print("=" * 50)
    print()

    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)

    base_args = [
        sys.executable, "-m", "nuitka",
        "--onefile",
        "--windows-console-mode=disable",
        "--windows-icon-from-ico=assets/icon.ico",
        "--output-dir=dist",
        "--output-filename=CAUC-SEP-Backend.exe",
    ]

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
        "sqlalchemy.dialects.sqlite", "pydantic_core", "pydantic_settings",
        "jose", "jose.jwt", "jose.jws", "jose.constants",
        "passlib", "passlib.hash", "passlib.handlers.bcrypt", "bcrypt",
        "starlette", "starlette.responses", "starlette.routing",
        "starlette.middleware", "starlette.middleware.cors", "starlette.websockets",
        "redis", "msgpack", "aiofiles",
        "psutil", "psutil._pswindows"
    ]

    nofollow = [
        "tkinter", "unittest", "test", "tests", "pytest",
        "PIL", "cv2", "sphinx", "docutils", "IPython", "jupyter", "notebook"
    ]

    plugins = ["pydantic", "numpy", "scipy"]

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
        zig_in_path = subprocess.run(["where", "zig"], capture_output=True)
        if zig_in_path.returncode == 0:
            print("Zig compiler found in PATH, enabling Zig optimization")
            base_args.append("--zig")
        else:
            print("Zig compiler not found, proceeding without Zig optimization")

    print(f"Running Nuitka with {len(base_args)} arguments...")
    print()

    result = subprocess.run(base_args)

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
        print("=" * 50)

        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write("status=failed\n")

        sys.exit(1)


if __name__ == "__main__":
    main()
