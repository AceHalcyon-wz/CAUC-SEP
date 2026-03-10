@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ============================================================
REM CAUC-SEP Backend Nuitka Build Script
REM Version: 1.0.0
REM Author: DevOps Team
REM Description: Windows本地Nuitka编译构建脚本
REM ============================================================

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
set "BACKEND_DIR=%PROJECT_ROOT%\cauc-sep\backend"
set "PYTHON_MIN_VERSION=3.8"
set "NUITKA_MIN_VERSION=1.8"

REM 颜色定义
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "CYAN=[96m"
set "RESET=[0m"

echo.
echo %CYAN%========================================%RESET%
echo %CYAN%  CAUC-SEP Backend Nuitka Build Script  %RESET%
echo %CYAN%========================================%RESET%
echo.

REM ============================================================
REM Step 1: 环境检查
REM ============================================================
echo %YELLOW%[Step 1/5] 环境检查%RESET%
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo %RED%[ERROR] Python未安装或未添加到PATH%RESET%
    echo 请安装Python %PYTHON_MIN_VERSION%或更高版本
    exit /b 1
)

REM 获取Python版本
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYTHON_VERSION=%%v
echo %GREEN%[OK]%RESET% Python版本: %PYTHON_VERSION%

REM 检查Python版本是否满足要求
python -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"
if errorlevel 1 (
    echo %RED%[ERROR] Python版本过低，需要 %PYTHON_MIN_VERSION% 或更高%RESET%
    exit /b 1
)

REM 检查pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo %RED%[ERROR] pip未安装%RESET%
    exit /b 1
)
echo %GREEN%[OK]%RESET% pip已安装

REM 检查项目目录是否存在
if not exist "%BACKEND_DIR%" (
    echo %RED%[ERROR] 后端目录不存在: %BACKEND_DIR%%RESET%
    exit /b 1
)
echo %GREEN%[OK]%RESET% 后端目录存在: %BACKEND_DIR%

REM 检查nuitka-config.py是否存在
if not exist "%BACKEND_DIR%\nuitka-config.py" (
    echo %RED%[ERROR] Nuitka配置文件不存在: %BACKEND_DIR%\nuitka-config.py%RESET%
    exit /b 1
)
echo %GREEN%[OK]%RESET% Nuitka配置文件存在

echo.

REM ============================================================
REM Step 2: 依赖检查
REM ============================================================
echo %YELLOW%[Step 2/5] 依赖检查%RESET%
echo.

REM 检查requirements.txt
if exist "%BACKEND_DIR%\requirements.txt" (
    echo %GREEN%[OK]%RESET% requirements.txt 存在
    
    REM 检查关键依赖是否已安装
    echo 正在检查关键依赖...
    
    python -c "import fastapi" >nul 2>&1
    if errorlevel 1 (
        echo %YELLOW%[WARN]%RESET% fastapi未安装，正在安装依赖...
        pip install -r "%BACKEND_DIR%\requirements.txt"
    ) else (
        echo %GREEN%[OK]%RESET% fastapi已安装
    )
    
    python -c "import uvicorn" >nul 2>&1
    if errorlevel 1 (
        echo %YELLOW%[WARN]%RESET% uvicorn未安装
    ) else (
        echo %GREEN%[OK]%RESET% uvicorn已安装
    )
    
    python -c "import pydantic" >nul 2>&1
    if errorlevel 1 (
        echo %YELLOW%[WARN]%RESET% pydantic未安装
    ) else (
        echo %GREEN%[OK]%RESET% pydantic已安装
    )
    
    python -c "import sqlalchemy" >nul 2>&1
    if errorlevel 1 (
        echo %YELLOW%[WARN]%RESET% sqlalchemy未安装
    ) else (
        echo %GREEN%[OK]%RESET% sqlalchemy已安装
    )
    
    python -c "import numpy" >nul 2>&1
    if errorlevel 1 (
        echo %YELLOW%[WARN]%RESET% numpy未安装
    ) else (
        echo %GREEN%[OK]%RESET% numpy已安装
    )
    
    python -c "import scipy" >nul 2>&1
    if errorlevel 1 (
        echo %YELLOW%[WARN]%RESET% scipy未安装
    ) else (
        echo %GREEN%[OK]%RESET% scipy已安装
    )
) else (
    echo %YELLOW%[WARN]%RESET% requirements.txt 不存在，跳过依赖检查
)

echo.

REM ============================================================
REM Step 3: Nuitka安装检查
REM ============================================================
echo %YELLOW%[Step 3/5] Nuitka安装检查%RESET%
echo.

REM 检查Nuitka是否安装
python -c "import nuitka" >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%[WARN]%RESET% Nuitka未安装，正在安装...
    pip install nuitka ordered-set zstandard
    
    REM 再次检查
    python -c "import nuitka" >nul 2>&1
    if errorlevel 1 (
        echo %RED%[ERROR] Nuitka安装失败%RESET%
        exit /b 1
    )
    echo %GREEN%[OK]%RESET% Nuitka安装成功
) else (
    echo %GREEN%[OK]%RESET% Nuitka已安装
)

REM 获取Nuitka版本
for /f "tokens=2 delims= " %%v in ('python -m nuitka --version 2^>^&1') do set NUITKA_VERSION=%%v
echo %GREEN%[OK]%RESET% Nuitka版本: %NUITKA_VERSION%

REM 检查C编译器
echo.
echo 正在检查C编译器...

REM 检查MSVC
where cl >nul 2>&1
if not errorlevel 1 (
    echo %GREEN%[OK]%RESET% MSVC编译器已配置
    set "CC_COMPILER=MSVC"
) else (
    REM 检查MinGW
    where gcc >nul 2>&1
    if not errorlevel 1 (
        echo %GREEN%[OK]%RESET% MinGW/GCC编译器已配置
        set "CC_COMPILER=MinGW"
    ) else (
        echo %YELLOW%[WARN]%RESET% 未检测到C编译器
        echo Nuitka将尝试自动下载MinGW编译器
        set "CC_COMPILER=Auto"
    )
)

REM 检查Zig编译器（可选优化）
where zig >nul 2>&1
if not errorlevel 1 (
    echo %GREEN%[OK]%RESET% Zig编译器已配置（将用于优化）
) else (
    echo %YELLOW%[INFO]%RESET% Zig编译器未安装（可选，用于额外优化）
)

echo.

REM ============================================================
REM Step 4: 执行Nuitka编译
REM ============================================================
echo %YELLOW%[Step 4/5] 执行Nuitka编译%RESET%
echo.

REM 切换到后端目录
cd /d "%BACKEND_DIR%"

REM 检查dist目录是否存在，不存在则创建
if not exist "dist" mkdir dist

REM 记录开始时间
set START_TIME=%TIME%

echo %CYAN%编译配置:%RESET%
echo   - 项目目录: %BACKEND_DIR%
echo   - 配置文件: nuitka-config.py
echo   - 输出目录: %BACKEND_DIR%\dist
echo   - 编译器: %CC_COMPILER%
echo.
echo %CYAN%开始编译...%RESET%
echo.

REM 使用Python运行nuitka-config.py进行编译
python nuitka-config.py

REM 检查编译结果
if errorlevel 1 (
    echo.
    echo %RED%========================================%RESET%
    echo %RED%  编译失败!%RESET%
    echo %RED%========================================%RESET%
    echo.
    echo 请检查错误日志并修复问题后重试
    cd /d "%SCRIPT_DIR%"
    exit /b 1
)

REM 记录结束时间
set END_TIME=%TIME%

echo.

REM ============================================================
REM Step 5: 编译结果输出
REM ============================================================
echo %YELLOW%[Step 5/5] 编译结果%RESET%
echo.

REM 检查输出文件是否存在
if exist "%BACKEND_DIR%\dist\CAUC-SEP-Backend.exe" (
    echo %GREEN%========================================%RESET%
    echo %GREEN%  编译成功!%RESET%
    echo %GREEN%========================================%RESET%
    echo.
    
    REM 获取文件大小
    for %%A in ("%BACKEND_DIR%\dist\CAUC-SEP-Backend.exe") do set FILE_SIZE=%%~zA
    set /a FILE_SIZE_MB=!FILE_SIZE! / 1048576
    
    echo %CYAN%输出信息:%RESET%
    echo   - 文件路径: %BACKEND_DIR%\dist\CAUC-SEP-Backend.exe
    echo   - 文件大小: !FILE_SIZE_MB! MB (!FILE_SIZE! bytes)
    echo   - 开始时间: %START_TIME%
    echo   - 结束时间: %END_TIME%
    echo.
    
    REM 列出dist目录内容
    echo %CYAN%dist目录内容:%RESET%
    dir /b "%BACKEND_DIR%\dist"
    echo.
    
    echo %CYAN%运行说明:%RESET%
    echo   1. 进入dist目录: cd "%BACKEND_DIR%\dist"
    echo   2. 运行程序: CAUC-SEP-Backend.exe
    echo   3. 默认访问: http://localhost:8000
    echo   4. API文档: http://localhost:8000/docs
    echo.
    
    echo %GREEN%构建完成!%RESET%
) else (
    echo %RED%[ERROR] 编译输出文件不存在%RESET%
    echo 请检查编译日志排查问题
    cd /d "%SCRIPT_DIR%"
    exit /b 1
)

REM 返回脚本目录
cd /d "%SCRIPT_DIR%"

echo.
echo %CYAN%按任意键退出...%RESET%
pause >nul

exit /b 0
