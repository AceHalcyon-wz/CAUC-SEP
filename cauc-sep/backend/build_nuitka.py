"""
Nuitka编译脚本 - 简化版
用于在CI/CD环境中编译CAUC-SEP后端
"""
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, cwd=None, check=True):
    """运行命令并打印输出。"""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=False,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        print(f"Command failed with exit code: {result.returncode}")
        sys.exit(1)
    return result


def main():
    print("=" * 60)
    print("  CAUC-SEP Nuitka Build Script v5")
    print("=" * 60)
    print()

    backend_dir = Path(__file__).parent.resolve()
    print(f"Backend directory: {backend_dir}")
    print(f"Python: {sys.executable}")
    print(f"Python version: {sys.version}")
    print()

    os.chdir(backend_dir)
    print(f"Working directory: {os.getcwd()}")
    print()

    print("Step 1: Check Nuitka installation...")
    run_command([sys.executable, "-m", "nuitka", "--version"], check=False)
    print()

    print("Step 2: Check Zig compiler...")
    zig_exe = Path("C:/zig/zig.exe")
    use_zig = False
    if zig_exe.exists():
        print(f"Zig found at: {zig_exe}")
        run_command([str(zig_exe), "version"], check=False)
        use_zig = True
    else:
        print("Zig not found at C:/zig/zig.exe")
        result = run_command(["where", "zig"], check=False)
        if result.returncode == 0:
            use_zig = True
    print()

    print("Step 3: Build Nuitka command...")
    cmd = [
        sys.executable, "-m", "nuitka",
        "--onefile",
        "--windows-console-mode=disable",
        "--output-dir=dist",
        "--output-filename=CAUC-SEP-Backend.exe",
        "--assume-yes-for-downloads",
        "--show-progress",
        "--show-memory",
        "--jobs=4",
        "--lto=yes",
    ]

    if use_zig:
        cmd.append("--zig")
        print("Zig optimization: ENABLED")
    else:
        print("Zig optimization: DISABLED")

    icon_path = backend_dir / "assets" / "icon.ico"
    if icon_path.exists():
        cmd.append(f"--windows-icon-from-ico={icon_path}")
        print(f"Icon: {icon_path}")
    else:
        print("Icon: NOT FOUND (proceeding without)")

    cmd.append("main.py")

    print()
    print("Step 4: Run Nuitka compilation...")
    print(f"Command: {' '.join(cmd[:6])}... ({len(cmd)} args total)")
    print()

    result = subprocess.run(cmd, check=False)

    print()
    print("=" * 60)
    print(f"Nuitka exit code: {result.returncode}")
    print("=" * 60)

    if result.returncode == 0:
        exe_path = Path("dist/CAUC-SEP-Backend.exe")
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"SUCCESS: {exe_path} ({size_mb:.2f} MB)")
        else:
            print("WARNING: Exit code 0 but executable not found!")

    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"status={'success' if result.returncode == 0 else 'failed'}\n")

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
