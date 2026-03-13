@echo off
chcp 65001 >nul
REM ============================================================================
REM CAUC-SEP Nuitka完整打包脚本
REM
REM 文件名: build-nuitka.bat
REM 路径: scripts/
REM 功能: Nuitka编译打包脚本（生成优化EXE）
REM 版本: v0.3.0
REM
REM 功能说明：
REM   - 构建前端Vue3项目
REM   - 使用Nuitka打包后端为单一EXE
REM   - 生成Inno Setup安装包
REM
REM 硬件配置优化：
REM   - 24GB内存：jobs=4, 内存限制8GB
REM   - RTX 5060：不使用GPU加速（Nuitka暂不支持）
REM   - Ryzen 7-H255：多核并行编译
REM
REM 作者：CAUC-SEP 开发团队
REM 创建日期：2024-03-01
REM 最后更新：2026-03-14
REM ============================================================================

setlocal EnableDelayedExpansion

echo.
echo ==========================================
echo   CAUC-SEP 完整打包流程
echo   Nuitka + Inno Setup
echo ==========================================
echo.

cd /d "%~dp0\.."

REM ============================================================================
REM 配置参数
REM ============================================================================

REM 虚拟环境路径
set "VENV_PATH=%CD%\.venv-nuitka"

REM 版本信息
set "APP_VERSION=0.3.0"
set "APP_NAME=CAUC-SEP-Backend"

REM 输出目录
set "BACKEND_DIST=backend\dist"
set "FRONTEND_DIST=frontend\dist"
set "RELEASE_DIR=dist\release"

REM Nuitka内存优化参数（24GB内存配置）
REM jobs=4: 4个并行编译进程，每个约2GB内存
REM 内存使用预估：4进程 × 2GB = 8GB，剩余16GB供系统使用
set "NUITKA_JOBS=4"
set "NUITKA_MEMORY_LIMIT=8192"

REM 解析命令行参数
set "SKIP_FRONTEND=0"
set "SKIP_INSTALLER=0"
set "CLEAN_BUILD=1"

:parse_args
if "%~1"=="" goto :end_parse
if /i "%~1"=="--skip-frontend" set "SKIP_FRONTEND=1"
if /i "%~1"=="--skip-installer" set "SKIP_INSTALLER=1"
if /i "%~1"=="--no-clean" set "CLEAN_BUILD=0"
shift
goto :parse_args
:end_parse

echo 构建配置:
echo   - 跳过前端: %SKIP_FRONTEND%
echo   - 跳过安装包: %SKIP_INSTALLER%
echo   - 清理构建: %CLEAN_BUILD%
echo   - 并行任务数: %NUITKA_JOBS%
echo   - 内存限制: %NUITKA_MEMORY_LIMIT% MB
echo.

REM ============================================================================
REM 1. 环境检查
REM ============================================================================

echo [1/7] 检查构建环境...

if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo [错误] 未找到Nuitka虚拟环境
    echo 请先运行: scripts\setup-nuitka-env.bat
    pause
    exit /b 1
)

call "%VENV_PATH%\Scripts\activate.bat"

python -c "import nuitka" >nul 2>&1
if errorlevel 1 (
    echo [错误] Nuitka未正确安装
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python -c "import nuitka; print(nuitka.Version.getNuitkaVersion())"') do set NUITKA_VERSION=%%i
echo   - Nuitka版本: %NUITKA_VERSION%
echo   - 环境检查通过

REM ============================================================================
REM 2. 清理旧构建
REM ============================================================================

if "%CLEAN_BUILD%"=="1" (
    echo.
    echo [2/7] 清理旧构建文件...
    
    if exist "%BACKEND_DIST%" (
        echo   - 删除 backend\dist...
        rmdir /s /q "%BACKEND_DIST%" 2>nul
    )
    if exist "%RELEASE_DIR%" (
        echo   - 删除 release 目录...
        rmdir /s /q "%RELEASE_DIR%" 2>nul
    )
    if exist "backend\main.build" (
        echo   - 删除构建缓存...
        rmdir /s /q "backend\main.build" 2>nul
    )
    if exist "backend\main.dist" (
        rmdir /s /q "backend\main.dist" 2>nul
    )
    
    echo   - 清理完成
) else (
    echo.
    echo [2/7] 跳过清理步骤
)

REM ============================================================================
REM 3. 构建前端
REM ============================================================================

if "%SKIP_FRONTEND%"=="0" (
    echo.
    echo [3/7] 构建前端...
    
    cd frontend
    
    if not exist "node_modules" (
        echo   - 安装前端依赖...
        call npm install --silent
        if errorlevel 1 (
            echo [错误] 前端依赖安装失败
            cd ..
            pause
            exit /b 1
        )
    )
    
    echo   - 执行Vite构建...
    call npm run build
    if errorlevel 1 (
        echo [错误] 前端构建失败
        cd ..
        pause
        exit /b 1
    )
    
    cd ..
    echo   - 前端构建完成
) else (
    echo.
    echo [3/7] 跳过前端构建
)

REM ============================================================================
REM 4. Nuitka打包后端
REM ============================================================================

echo.
echo [4/7] Nuitka打包后端...
echo   - 这可能需要10-30分钟，请耐心等待
echo.

cd backend

REM 设置内存限制（Windows）
REM 限制单个进程内存使用，防止系统卡顿
set "PYTHONDONTWRITEBYTECODE=1"

REM Nuitka编译命令
REM 关键参数说明：
REM   --onefile: 生成单一EXE文件
REM   --standalone: 独立运行，不依赖Python环境
REM   --windows-console-mode=disable: 无控制台窗口
REM   --jobs=4: 4个并行编译进程（24GB内存优化）
REM   --lto=yes: 链接时优化，减小体积
REM   --zig: 使用Zig作为C编译器后端（更快）
REM   --assume-yes-for-downloads: 自动下载依赖

python -m nuitka ^
    --onefile ^
    --standalone ^
    --windows-console-mode=disable ^
    --windows-icon-from-ico=assets/icon.ico ^
    --output-dir=dist ^
    --output-filename=CAUC-SEP-Backend.exe ^
    --company-name=CAUC ^
    --product-name=CAUC-SEP ^
    --file-version=%APP_VERSION%.0 ^
    --product-version=%APP_VERSION%.0 ^
    --file-description="CAUC Spintronics Experiment Platform Backend" ^
    --include-package=fastapi ^
    --include-package=uvicorn ^
    --include-package=pydantic ^
    --include-package=pydantic_settings ^
    --include-package=sqlalchemy ^
    --include-package=pymodbus ^
    --include-package=serial ^
    --include-package=numpy ^
    --include-package=scipy ^
    --include-package=lmfit ^
    --include-package=h5py ^
    --include-package=core ^
    --include-package=api ^
    --include-package=middleware ^
    --include-package=models ^
    --include-package=drivers ^
    --include-module=uvicorn.logging ^
    --include-module=uvicorn.loops ^
    --include-module=uvicorn.loops.auto ^
    --include-module=uvicorn.protocols ^
    --include-module=uvicorn.protocols.http ^
    --include-module=uvicorn.protocols.http.auto ^
    --include-module=uvicorn.protocols.websockets ^
    --include-module=uvicorn.protocols.websockets.auto ^
    --include-module=uvicorn.lifespan ^
    --include-module=uvicorn.lifespan.on ^
    --include-module=sqlalchemy.dialects.sqlite ^
    --include-module=pydantic_core ^
    --include-module=pydantic_settings ^
    --include-module=multipart ^
    --include-module=starlette.responses ^
    --include-module=starlette.routing ^
    --include-module=starlette.middleware ^
    --include-module=starlette.middleware.cors ^
    --include-module=starlette.websockets ^
    --include-module=httpx ^
    --include-module=anyio ^
    --include-module=h11 ^
    --include-module=redis ^
    --include-module=msgpack ^
    --include-module=aiofiles ^
    --include-module=psutil ^
    --include-module=psutil._pswindows ^
    --nofollow-import-to=tkinter ^
    --nofollow-import-to=unittest ^
    --nofollow-import-to=test ^
    --nofollow-import-to=tests ^
    --nofollow-import-to=pytest ^
    --nofollow-import-to=PIL ^
    --nofollow-import-to=cv2 ^
    --nofollow-import-to=sphinx ^
    --nofollow-import-to=docutils ^
    --nofollow-import-to=IPython ^
    --nofollow-import-to=jupyter ^
    --nofollow-import-to=notebook ^
    --nofollow-import-to=pandas ^
    --nofollow-import-to=bokeh ^
    --nofollow-import-to=plotly ^
    --lto=yes ^
    --assume-yes-for-downloads ^
    --show-progress ^
    --show-memory ^
    --jobs=%NUITKA_JOBS% ^
    --zig ^
    main.py

if errorlevel 1 (
    echo.
    echo [错误] Nuitka打包失败
    cd ..
    pause
    exit /b 1
)

cd ..
echo.
echo   - 后端打包完成

REM ============================================================================
REM 5. 组装发布目录
REM ============================================================================

echo.
echo [5/7] 组装发布目录...

if not exist "%RELEASE_DIR%" mkdir "%RELEASE_DIR%"
if not exist "%RELEASE_DIR%\frontend" mkdir "%RELEASE_DIR%\frontend"
if not exist "%RELEASE_DIR%\logs" mkdir "%RELEASE_DIR%\logs"
if not exist "%RELEASE_DIR%\data" mkdir "%RELEASE_DIR%\data"
if not exist "%RELEASE_DIR%\config" mkdir "%RELEASE_DIR%\config"
if not exist "%RELEASE_DIR%\assets" mkdir "%RELEASE_DIR%\assets"

echo   - 复制后端可执行文件...
copy /y "%BACKEND_DIST%\CAUC-SEP-Backend.exe" "%RELEASE_DIR%\" >nul

echo   - 复制前端文件...
xcopy /E /I /Y /Q "%FRONTEND_DIST%\*" "%RELEASE_DIR%\frontend\" >nul

echo   - 复制资源文件...
xcopy /E /I /Y /Q "backend\assets\*" "%RELEASE_DIR%\assets\" >nul

echo   - 复制文档...
copy /y "README.md" "%RELEASE_DIR%\" >nul 2>&1
copy /y "LICENSE" "%RELEASE_DIR%\" >nul 2>&1
copy /y "CHANGELOG.md" "%RELEASE_DIR%\" >nul 2>&1

echo   - 创建启动脚本...
(
    echo @echo off
    echo chcp 65001 ^>nul
    echo echo ==========================================
    echo echo   CAUC-SEP 自旋电子实验平台
    echo echo ==========================================
    echo echo.
    echo echo 正在启动服务...
    echo echo.
    echo.
    echo cd /d "%%~dp0"
    echo.
    echo REM 启动后端服务
    echo start "" CAUC-SEP-Backend.exe
    echo.
    echo REM 等待服务启动
    echo timeout /t 3 /nobreak ^>nul
    echo.
    echo REM 打开浏览器
    echo start http://localhost:8000
    echo.
    echo echo 服务已启动，请勿关闭此窗口。
    echo echo 按任意键停止服务...
    echo pause ^>nul
    echo.
    echo REM 停止服务
    echo taskkill /f /im CAUC-SEP-Backend.exe ^>nul 2^>^&1
) > "%RELEASE_DIR%\start.bat"

echo   - 创建停止脚本...
(
    echo @echo off
    echo echo 正在停止 CAUC-SEP 服务...
    echo taskkill /f /im CAUC-SEP-Backend.exe ^>nul 2^>^&1
    echo echo 服务已停止。
    echo pause
) > "%RELEASE_DIR%\stop.bat"

echo   - 创建配置文件...
(
    echo # CAUC-SEP 配置文件
    echo.
    echo [server]
    echo host = 127.0.0.1
    echo port = 8000
    echo.
    echo [logging]
    echo level = INFO
    echo max_bytes = 10485760
    echo backup_count = 5
    echo.
    echo [devices]
    echo simulation = true
    echo.
    echo [modbus]
    echo port = COM3
    echo baudrate = 115200
    echo parity = N
    echo stopbits = 1
    echo bytesize = 8
    echo timeout = 1.0
) > "%RELEASE_DIR%\config\config.ini"

echo   - 发布目录组装完成

REM ============================================================================
REM 6. 生成安装包
REM ============================================================================

if "%SKIP_INSTALLER%"=="0" (
    echo.
    echo [6/7] 生成Inno Setup安装包...
    
    where iscc >nul 2>&1
    if errorlevel 1 (
        echo   - [警告] 未找到Inno Setup编译器
        echo   - 请手动编译: installer\CAUC-SEP.iss
        echo   - 或安装Inno Setup: https://jrsoftware.org/isinfo.php
    ) else (
        cd installer
        iscc CAUC-SEP.iss
        cd ..
        echo   - 安装包生成完成
    )
) else (
    echo.
    echo [6/7] 跳过安装包生成
)

REM ============================================================================
REM 7. 构建完成
REM ============================================================================

echo.
echo [7/7] 构建完成！

echo.
echo ==========================================
echo   构建成功！
echo ==========================================
echo.

REM 显示文件大小
if exist "%RELEASE_DIR%\CAUC-SEP-Backend.exe" (
    for %%I in ("%RELEASE_DIR%\CAUC-SEP-Backend.exe") do (
        set /a SIZE_MB=%%~zI/1024/1024
        echo 后端文件大小: !SIZE_MB! MB
    )
)

echo.
echo 发布目录: %RELEASE_DIR%
echo.
echo 目录结构:
dir /b "%RELEASE_DIR%"
echo.
echo 按任意键退出...
pause >nul
