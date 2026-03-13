@echo off
chcp 65001 >nul
REM ============================================================================
REM CAUC-SEP Nuitka打包环境初始化脚本
REM
REM 文件名: setup-nuitka-env.bat
REM 路径: scripts/
REM 功能: 初始化Nuitka编译环境
REM 版本: v0.3.0
REM
REM 功能说明：
REM   - 创建独立Python虚拟环境
REM   - 安装Nuitka及所有依赖
REM   - 配置编译工具链
REM
REM 硬件配置：24GB内存优化
REM 作者：CAUC-SEP 开发团队
REM 创建日期：2024-03-01
REM 最后更新：2026-03-14
REM ============================================================================

echo.
echo ==========================================
echo   CAUC-SEP Nuitka打包环境初始化
echo ==========================================
echo.

cd /d "%~dp0\.."

set "VENV_NAME=.venv-nuitka"
set "VENV_PATH=%CD%\%VENV_NAME%"

echo [1/5] 检查Python环境...

python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.10+
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo   - Python版本: %PYTHON_VERSION%

echo.
echo [2/5] 创建独立虚拟环境...

if exist "%VENV_PATH%" (
    echo   - 检测到已存在虚拟环境
    set /p RECREATE="  - 是否重新创建？(y/N): "
    if /i "!RECREATE!"=="y" (
        echo   - 删除旧虚拟环境...
        rmdir /s /q "%VENV_PATH%"
    ) else (
        echo   - 使用现有虚拟环境
        goto :activate_venv
    )
)

echo   - 创建新虚拟环境...
python -m venv "%VENV_PATH%"
if errorlevel 1 (
    echo [错误] 虚拟环境创建失败
    pause
    exit /b 1
)

:activate_venv
echo.
echo [3/5] 激活虚拟环境并安装依赖...

call "%VENV_PATH%\Scripts\activate.bat"

echo   - 升级pip...
python -m pip install --upgrade pip --quiet

echo   - 安装Nuitka（最新稳定版）...
pip install nuitka --quiet

echo   - 安装项目依赖...
pip install -r backend\requirements.txt --quiet

echo   - 安装打包依赖...
pip install ordered-set zstandard --quiet

echo.
echo [4/5] 检查编译工具链...

where cl >nul 2>&1
if errorlevel 1 (
    echo   - 未检测到MSVC编译器
    echo   - Nuitka将自动下载MinGW64编译器
    echo   - 首次编译时会自动处理，请耐心等待
) else (
    echo   - 已检测到MSVC编译器
)

echo.
echo [5/5] 验证安装...

python -c "import nuitka; print(f'   - Nuitka版本: {nuitka.Version.getNuitkaVersion()}')"
if errorlevel 1 (
    echo [错误] Nuitka安装验证失败
    pause
    exit /b 1
)

python -c "import fastapi; import uvicorn; import numpy; import scipy; print('   - 核心依赖验证通过')"

echo.
echo ==========================================
echo   环境初始化完成！
echo ==========================================
echo.
echo 虚拟环境路径: %VENV_PATH%
echo.
echo 使用方法:
echo   1. 激活虚拟环境: %VENV_PATH%\Scripts\activate.bat
echo   2. 运行打包脚本: scripts\build-nuitka.bat
echo.
echo 按任意键退出...
pause >nul
