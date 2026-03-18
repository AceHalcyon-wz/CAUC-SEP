@echo off
chcp 65001 >nul
REM ============================================================================
REM CAUC-SEP 完整构建脚本 - Electron 打包方案
REM
REM 文件名: build-all.bat
REM 路径: scripts/
REM 功能: 前端构建 + 后端编译 + Electron 打包
REM 版本: v1.0.0
REM
REM 构建流程:
REM   1. 构建前端 (npm run build)
REM   2. 复制前端资源到 electron/resources/frontend/
REM   3. 执行 Nuitka 后端编译
REM   4. 执行 electron-builder 打包
REM
REM 作者：CAUC-SEP 开发团队
REM 创建日期：2026-03-15
REM ============================================================================

setlocal EnableDelayedExpansion

echo.
echo ==========================================
echo   CAUC-SEP 完整构建流程
echo   Electron + Nuitka 打包方案
echo ==========================================
echo.

cd /d "%~dp0.."

REM ============================================================================
REM 配置参数
REM ============================================================================
set "APP_VERSION=4.0.0"
set "PROJECT_ROOT=%cd%"
set "FRONTEND_DIR=%PROJECT_ROOT%\frontend"
set "BACKEND_DIR=%PROJECT_ROOT%\backend"
set "ELECTRON_DIR=%PROJECT_ROOT%\electron"
set "ELECTRON_RESOURCES=%ELECTRON_DIR%\resources"
set "FRONTEND_DIST=%FRONTEND_DIR%\dist"

REM 解析命令行参数
set "SKIP_FRONTEND=0"
set "SKIP_BACKEND=0"
set "SKIP_ELECTRON=0"
set "CLEAN_BUILD=1"

:parse_args
if "%~1"=="" goto :end_parse
if /i "%~1"=="--skip-frontend" set "SKIP_FRONTEND=1"
if /i "%~1"=="--skip-backend" set "SKIP_BACKEND=1"
if /i "%~1"=="--skip-electron" set "SKIP_ELECTRON=1"
if /i "%~1"=="--no-clean" set "CLEAN_BUILD=0"
shift
goto :parse_args
:end_parse

REM 显示构建配置
echo 构建配置:
echo   - 项目根目录: %PROJECT_ROOT%
echo   - 跳过前端: %SKIP_FRONTEND%
echo   - 跳过后端: %SKIP_BACKEND%
echo   - 跳过 Electron: %SKIP_ELECTRON%
echo   - 清理构建: %CLEAN_BUILD%
echo.

REM ============================================================================
REM 0. 环境检查
REM ============================================================================
echo [0/4] 检查构建环境...

REM 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Node.js，请先安装 Node.js 18+
    pause
    exit /b 1
)
for /f %%i in ('node --version') do set NODE_VERSION=%%i
echo   - Node.js 版本: %NODE_VERSION%

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo   - Python 版本: %PYTHON_VERSION%

REM 检查 Nuitka
python -c "import nuitka" >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装 Nuitka...
    pip install nuitka --quiet
)

echo   - 环境检查通过
echo.

REM ============================================================================
REM 清理旧构建
REM ============================================================================
if "%CLEAN_BUILD%"=="1" (
    echo [清理] 清理旧构建文件...

    if exist "%ELECTRON_RESOURCES%\frontend" (
        echo   - 删除 electron/resources/frontend/
        rmdir /s /q "%ELECTRON_RESOURCES%\frontend" 2>nul
    )
    if exist "%ELECTRON_RESOURCES%\backend" (
        echo   - 删除 electron/resources/backend/
        rmdir /s /q "%ELECTRON_RESOURCES%\backend" 2>nul
    )
    if exist "%FRONTEND_DIST%" (
        echo   - 删除 frontend/dist/
        rmdir /s /q "%FRONTEND_DIST%" 2>nul
    )

    echo   - 清理完成
    echo.
)

REM ============================================================================
REM 1. 构建前端
REM ============================================================================
if "%SKIP_FRONTEND%"=="0" (
    echo [1/4] 构建前端...
    echo   - 进入前端目录: %FRONTEND_DIR%

    cd /d "%FRONTEND_DIR%"

    REM 检查 node_modules
    if not exist "node_modules" (
        echo   - 安装前端依赖...
        call npm install --silent
        if errorlevel 1 (
            echo [错误] 前端依赖安装失败
            cd /d "%PROJECT_ROOT%"
            pause
            exit /b 1
        )
    )

    REM 执行 Vite 构建
    echo   - 执行 Vite 构建...
    call npm run build
    if errorlevel 1 (
        echo [错误] 前端构建失败
        cd /d "%PROJECT_ROOT%"
        pause
        exit /b 1
    )

    cd /d "%PROJECT_ROOT%"
    echo   - 前端构建完成
    echo.
) else (
    echo [1/4] 跳过前端构建
    echo.
)

REM ============================================================================
REM 2. 复制前端资源到 Electron 目录
REM ============================================================================
echo [2/4] 复制前端资源到 Electron 目录...

REM 创建目标目录
if not exist "%ELECTRON_RESOURCES%\frontend" (
    mkdir "%ELECTRON_RESOURCES%\frontend"
)

REM 复制前端文件
if exist "%FRONTEND_DIST%" (
    echo   - 复制 frontend/dist/ 到 electron/resources/frontend/
    xcopy /E /I /Y /Q "%FRONTEND_DIST%\*" "%ELECTRON_RESOURCES%\frontend\" >nul
    echo   - 前端资源复制完成
) else (
    echo [警告] 前端构建目录不存在: %FRONTEND_DIST%
    echo   - 请确保前端已构建，或使用 --skip-frontend 跳过
)

echo.

REM ============================================================================
REM 3. 执行 Nuitka 后端编译
REM ============================================================================
if "%SKIP_BACKEND%"=="0" (
    echo [3/4] 执行 Nuitka 后端编译...
    echo   - 这可能需要 10-30 分钟，请耐心等待
    echo.

    cd /d "%BACKEND_DIR%"
    python scripts\build_exe_standalone.py
    if errorlevel 1 (
        echo [错误] Nuitka 编译失败
        cd /d "%PROJECT_ROOT%"
        pause
        exit /b 1
    )
    cd /d "%PROJECT_ROOT%"

    echo   - 后端编译完成
    echo.
) else (
    echo [3/4] 跳过后端编译
    echo.
)

REM ============================================================================
REM 4. 执行 Electron 打包
REM ============================================================================
if "%SKIP_ELECTRON%"=="0" (
    echo [4/4] 执行 Electron 打包...

    cd /d "%ELECTRON_DIR%"

    REM 检查 electron 目录是否存在 package.json
    if not exist "package.json" (
        echo [警告] electron/package.json 不存在
        echo   - 请确保 Electron 项目已初始化
        echo   - 跳过 Electron 打包步骤
    ) else (
        REM 检查 node_modules
        if not exist "node_modules" (
            echo   - 安装 Electron 依赖...
            call npm install --silent
        )

        REM 检查 electron-builder
        npx electron-builder --version >nul 2>&1
        if errorlevel 1 (
            echo   - 安装 electron-builder...
            call npm install electron-builder --save-dev --silent
        )

        REM 执行打包
        echo   - 执行 electron-builder 打包...
        call npm run build:win
        if errorlevel 1 (
            echo [警告] Electron 打包可能失败
            echo   - 请检查 electron-builder 配置
        ) else (
            echo   - Electron 打包完成
        )
    )

    cd /d "%PROJECT_ROOT%"
    echo.
) else (
    echo [4/4] 跳过 Electron 打包
    echo.
)

REM ============================================================================
REM 构建完成
REM ============================================================================
echo.
echo ==========================================
echo   构建完成！
echo ==========================================
echo.

echo 输出目录:
if exist "%ELECTRON_RESOURCES%\frontend" (
    echo   - 前端资源: electron/resources/frontend/
)
if exist "%ELECTRON_RESOURCES%\backend\backend.dist" (
    echo   - 后端程序: electron/resources/backend/backend.dist/
)

echo.
echo 下一步:
echo   1. 检查 electron/resources/ 目录结构
echo   2. 配置 electron-builder 打包参数
echo   3. 运行 electron 应用测试
echo.

REM 显示总大小
if exist "%ELECTRON_RESOURCES%" (
    echo 资源目录大小:
    for /f "tokens=3" %%a in ('dir /s "%ELECTRON_RESOURCES%" 2^>nul ^| findstr "File(s)"') do (
        set TOTAL_SIZE=%%a
    )
    echo   - 总计: %TOTAL_SIZE% 字节
)

echo.
echo 按任意键退出...
pause >nul
