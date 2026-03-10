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
import os
import subprocess
import sys
import traceback
from pathlib import Path


def run_command(cmd, cwd=None, check=True, capture_output=False):
    """运行命令并打印输出。"""
    print(f"Running: {' '.join(cmd)}")
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
    spec.loader.exec_module(config_module)
    
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
                cmd.append(f"--{key}={item}")
        elif value is not None:
            cmd.append(f"--{key}={value}")
    
    cmd.append("main.py")
    return cmd


def check_frontend_dist(backend_dir):
    """检查并准备前端静态文件。"""
    project_root = backend_dir.parent
    frontend_dist = project_root / "frontend" / "dist"
    backend_frontend_dist = backend_dir / "frontend" / "dist"
    
    print()
    print("Checking frontend static files...")
    
    if frontend_dist.exists() and list(frontend_dist.iterdir()):
        print(f"Found frontend dist at: {frontend_dist}")
        
        if not backend_frontend_dist.parent.exists():
            backend_frontend_dist.parent.mkdir(parents=True, exist_ok=True)
        
        if not backend_frontend_dist.exists() or not list(backend_frontend_dist.iterdir()):
            print(f"Copying frontend dist to backend directory...")
            import shutil
            if backend_frontend_dist.exists():
                shutil.rmtree(backend_frontend_dist)
            shutil.copytree(frontend_dist, backend_frontend_dist)
            print("Frontend dist copied successfully")
        else:
            print("Frontend dist already present in backend directory")
        
        return True
    else:
        print("WARNING: Frontend dist not found or empty")
        print("Please build the frontend first: cd frontend && npm install && npm run build")
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
        nuitka_check = run_command([sys.executable, "-m", "nuitka", "--version"], check=False, capture_output=True)
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
        if not frontend_ready:
            print("WARNING: Proceeding without frontend static files")
        print()

        print("Step 4: Build Nuitka command...")
        cmd = build_nuitka_command(config_options, backend_dir)
        print(f"Command built with {len(cmd)} arguments")
        print(f"First 5 args: {' '.join(cmd[:5])}...")
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
                print(f"SUCCESS: Build completed successfully!")
                print(f"  Executable: {exe_path}")
                print(f"  Size: {size_mb:.2f} MB")
            else:
                print(f"WARNING: Exit code 0 but executable not found at {exe_path}")
        else:
            print(f"ERROR: Build failed with exit code {result.returncode}")
            print(f"Please check the Nuitka output above for details")
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
