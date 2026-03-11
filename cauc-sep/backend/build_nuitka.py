"""
Nuitka编译脚本 - 优化版
用于在CI/CD环境中编译CAUC-SEP后端
功能：
- 读取nuitka-config.py配置
- 自动打包前端静态文件
- 增强错误处理和诊断
- 确保可执行文件运行时能找到前端资源
"""

import importlib.util
import io
import os
import subprocess
import sys
import traceback
from pathlib import Path

# Fix Windows encoding issues - force UTF-8 for stdout/stderr
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    # Also set environment variable for subprocess
    os.environ["PYTHONIOENCODING"] = "utf-8"


def run_command(cmd, cwd=None, check=True, capture_output=False):
    """运行命令并打印输出。"""
    try:
        print(f"Running: {' '.join(cmd)}")
    except UnicodeEncodeError:
        print(f"Running: [command contains non-ASCII characters]")
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            check=False,
        )
        if check and result.returncode != 0:
            print(f"Command failed with exit code: {result.returncode}")
            if capture_output:
                print(f"Stdout: {result.stdout}")
                print(f"Stderr: {result.stderr}")
            sys.exit(1)
        return result
    except Exception as e:
        print(f"Command execution error: {e}")
        traceback.print_exc()
        if check:
            sys.exit(1)
        return None


def load_nuitka_config(config_path):
    """加载nuitka-config.py配置文件。"""
    print(f"Loading configuration from: {config_path}")
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    spec = importlib.util.spec_from_file_location("nuitka_config", config_path)
    config_module = importlib.util.module_from_spec(spec)
    
    # 确保使用UTF-8编码读取配置文件
    import codecs
    with codecs.open(str(config_path), 'r', encoding='utf-8') as f:
        config_code = f.read()
    
    # 使用exec执行配置代码
    exec(compile(config_code, str(config_path), 'exec'), config_module.__dict__)

    if not hasattr(config_module, "nuitka_options"):
        raise AttributeError("nuitka-config.py must define 'nuitka_options'")

    return config_module.nuitka_options


def build_nuitka_command(config_options, backend_dir):
    """根据配置构建Nuitka命令。"""
    cmd = [sys.executable, "-m", "nuitka"]

    for key, value in config_options.items():
        if isinstance(value, bool):
            if value:
                cmd.append(f"--{key}")
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, (tuple, list)) and len(item) == 2:
                    cmd.append(f"--{key}={item[0]}={item[1]}")
                else:
                    cmd.append(f"--{key}={item}")
        elif value is not None:
            cmd.append(f"--{key}={value}")

    # 动态检测并添加Zig编译器支持
    zig_found = False
    zig_paths = [
        Path("C:/zig/zig.exe"),
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "zig" / "zig.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "zig" / "zig.exe",
    ]
    for zig_path in zig_paths:
        if zig_path.exists():
            print(f"Zig compiler found at: {zig_path}")
            cmd.append("--zig")
            zig_found = True
            break
    if not zig_found:
        # 检查PATH中是否有zig
        import shutil
        if shutil.which("zig"):
            print("Zig compiler found in PATH")
            cmd.append("--zig")
            zig_found = True
        else:
            print("Zig compiler not found, proceeding without Zig optimization")

    # 动态添加前端静态文件目录（如果存在）
    frontend_dist = backend_dir / "frontend" / "dist"
    try:
        if frontend_dist.exists() and any(frontend_dist.iterdir()):
            cmd.append(f"--include-data-dir={frontend_dist}=frontend/dist")
            print(f"Added frontend dist to Nuitka command: {frontend_dist}")
        else:
            print("WARNING: Frontend dist not found or empty, skipping include-data-dir")
    except Exception as e:
        print(f"WARNING: Error checking frontend dist: {e}, skipping include-data-dir")

    cmd.append("main.py")
    return cmd


def check_frontend_dist(backend_dir):
    """检查并准备前端静态文件。"""
    project_root = backend_dir.parent
    frontend_dist = project_root / "frontend" / "dist"
    backend_frontend_dist = backend_dir / "frontend" / "dist"

    print()
    print("Checking frontend static files...")
    print(f"  Project root: {project_root}")
    print(f"  Frontend dist (expected): {frontend_dist}")
    print(f"  Backend frontend dist: {backend_frontend_dist}")

    try:
        if frontend_dist.exists() and any(frontend_dist.iterdir()):
            print(f"Found frontend dist at: {frontend_dist}")
            print(f"  Contents: {list(frontend_dist.iterdir())[:5]}")

            if not backend_frontend_dist.parent.exists():
                backend_frontend_dist.parent.mkdir(parents=True, exist_ok=True)

            if not backend_frontend_dist.exists() or not any(backend_frontend_dist.iterdir()):
                print("Copying frontend dist to backend directory...")
                import shutil

                if backend_frontend_dist.exists():
                    shutil.rmtree(backend_frontend_dist)
                shutil.copytree(frontend_dist, backend_frontend_dist)
                print("Frontend dist copied successfully")
                copied_count = len(list(backend_frontend_dist.rglob("**/*")))
                print(f"  Copied files: {copied_count}")
            else:
                print("Frontend dist already present in backend directory")

            return True
        else:
            print("WARNING: Frontend dist not found or empty")
            print(f"  Expected path: {frontend_dist}")
            print(f"  Exists: {frontend_dist.exists()}")
            print(f"  Has files: {any(frontend_dist.iterdir()) if frontend_dist.exists() else False}")
            print("Please build the frontend first: cd frontend && npm install && npm run build")
            return False
    except Exception as e:
        print(f"WARNING: Error checking frontend dist: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("  CAUC-SEP Nuitka Build Script v6 - Optimized")
    print("=" * 60)
    print()

    try:
        backend_dir = Path(__file__).parent.resolve()
        print(f"Backend directory: {backend_dir}")
        print(f"Python: {sys.executable}")
        print(f"Python version: {sys.version}")
        print()

        os.chdir(backend_dir)
        print(f"Working directory: {os.getcwd()}")
        print()

        print("Step 1: Check Nuitka installation...")
        nuitka_check = run_command(
            [sys.executable, "-m", "nuitka", "--version"], check=False, capture_output=True
        )
        if nuitka_check and nuitka_check.returncode == 0:
            print(f"Nuitka version: {nuitka_check.stdout.strip()}")
        else:
            print("WARNING: Nuitka may not be installed correctly")
        print()

        print("Step 2: Load nuitka-config.py...")
        config_path = backend_dir / "nuitka-config.py"
        config_options = load_nuitka_config(config_path)
        print("Configuration loaded successfully")
        print(f"  - Output dir: {config_options.get('output-dir', 'dist')}")
        print(f"  - Output file: {config_options.get('output-filename', 'CAUC-SEP-Backend')}")
        print(f"  - Onefile mode: {config_options.get('onefile', False)}")
        print()

        print("Step 3: Prepare frontend static files...")
        frontend_ready = check_frontend_dist(backend_dir)
        print(f"Frontend ready: {frontend_ready}")
        if not frontend_ready:
            print("WARNING: Proceeding without frontend static files")
            print("WARNING: This may cause Nuitka build to fail if frontend resources are required at runtime")
        print()

        print("Step 4: Build Nuitka command...")
        cmd = build_nuitka_command(config_options, backend_dir)
        print(f"Command built with {len(cmd)} arguments")
        # Safe print to avoid encoding issues on Windows
        try:
            first_args = " ".join(cmd[:5])
            print(f"First 5 args: {first_args}...")
        except UnicodeEncodeError:
            print(f"First 5 args: [contains non-ASCII characters]")
        print()

        print("Step 5: Run Nuitka compilation...")
        print("=" * 60)
        result = subprocess.run(cmd, check=False)
        print("=" * 60)
        print()

        print("Step 6: Build result verification...")
        print(f"Nuitka exit code: {result.returncode}")

        output_dir = Path(config_options.get("output-dir", "dist"))
        output_filename = config_options.get("output-filename", "CAUC-SEP-Backend")
        exe_path = output_dir / f"{output_filename}.exe"

        if result.returncode == 0:
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                print("SUCCESS: Build completed successfully!")
                print(f"  Executable: {exe_path}")
                print(f"  Size: {size_mb:.2f} MB")
            else:
                print(f"WARNING: Exit code 0 but executable not found at {exe_path}")
        else:
            print(f"ERROR: Build failed with exit code {result.returncode}")
            print("Please check the Nuitka output above for details")
        print()

        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write(f"status={'success' if result.returncode == 0 else 'failed'}\n")
                if result.returncode == 0 and exe_path.exists():
                    f.write(f"executable_path={exe_path}\n")
                    f.write(f"executable_size_mb={size_mb:.2f}\n")

        sys.exit(result.returncode)

    except Exception as e:
        print()
        print("=" * 60)
        print(f"BUILD ERROR: {type(e).__name__}: {e}")
        print("=" * 60)
        traceback.print_exc()

        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write("status=failed\n")
                f.write(f"error={str(e)}\n")

        sys.exit(1)


if __name__ == "__main__":
    main()
