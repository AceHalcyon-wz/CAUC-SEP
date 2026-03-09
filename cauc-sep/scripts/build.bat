@echo off
chcp 65001 >nul
REM ============================================================================
REM CAUC-SEP 自旋电子实验平台 - 打包脚本
REM
REM 功能：
REM   - 自动化构建前端和后端
REM   - PyInstaller打包优化
REM   - 日志配置集成
REM   - 启动性能优化
REM
REM 作者：运维工程师 Agent
REM 更新日期：2026-03-07
REM ============================================================================

echo.
echo ==========================================
echo   CAUC-SEP 自旋电子实验平台 - 打包脚本
echo ==========================================
echo.

:: 设置工作目录
cd /d "%~dp0\.."

:: 设置颜色输出（Windows 10+）
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "RESET=[0m"

:: 解析命令行参数
set "SKIP_FRONTEND=0"
set "SKIP_BACKEND=0"
set "CLEAN_BUILD=1"

:parse_args
if "%~1"=="" goto :end_parse
if /i "%~1"=="--skip-frontend" set "SKIP_FRONTEND=1"
if /i "%~1"=="--skip-backend" set "SKIP_BACKEND=1"
if /i "%~1"=="--no-clean" set "CLEAN_BUILD=0"
shift
goto :parse_args
:end_parse

:: 显示构建配置
echo 构建配置:
echo   - 跳过前端: %SKIP_FRONTEND%
echo   - 跳过后端: %SKIP_BACKEND%
echo   - 清理构建: %CLEAN_BUILD%
echo.

:: ============================================================================
:: 1. 环境检查
:: ============================================================================
echo [1/6] 检查构建环境...

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo %RED%[错误] 未找到Python，请先安装Python 3.10+%RESET%
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo   - Python版本: %PYTHON_VERSION%

:: 检查Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo %RED%[错误] 未找到Node.js，请先安装Node.js 18+%RESET%
    pause
    exit /b 1
)
for /f %%i in ('node --version') do set NODE_VERSION=%%i
echo   - Node.js版本: %NODE_VERSION%

:: 检查PyInstaller
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%[提示] 正在安装PyInstaller...%RESET%
    pip install pyinstaller --quiet
)

:: 检查前端依赖
if "%SKIP_FRONTEND%"=="0" (
    if not exist "frontend\node_modules" (
        echo %YELLOW%[提示] 前端依赖未安装，即将安装...%RESET%
    )
)

echo   - 环境检查通过
echo.

:: ============================================================================
:: 2. 清理旧构建
:: ============================================================================
if "%CLEAN_BUILD%"=="1" (
    echo [2/6] 清理旧构建文件...
    
    if exist "dist" (
        echo   - 删除 dist 目录...
        rmdir /s /q "dist" 2>nul
    )
    if exist "build" (
        echo   - 删除 build 目录...
        rmdir /s /q "build" 2>nul
    )
    if exist "backend\build" (
        echo   - 删除 backend\build 目录...
        rmdir /s /q "backend\build" 2>nul
    )
    
    echo   - 清理完成
    echo.
) else (
    echo [2/6] 跳过清理步骤
    echo.
)

:: ============================================================================
:: 3. 安装Python依赖
:: ============================================================================
echo [3/6] 安装Python依赖...

pip install -r backend/requirements.txt --quiet --upgrade
if errorlevel 1 (
    echo %RED%[错误] Python依赖安装失败%RESET%
    pause
    exit /b 1
)

echo   - Python依赖安装完成
echo.

:: ============================================================================
:: 4. 构建前端
:: ============================================================================
if "%SKIP_FRONTEND%"=="0" (
    echo [4/6] 构建前端...
    
    cd frontend
    
    :: 安装依赖
    if not exist "node_modules" (
        echo   - 安装前端依赖...
        call npm install --silent
        if errorlevel 1 (
            echo %RED%[错误] 前端依赖安装失败%RESET%
            cd ..
            pause
            exit /b 1
        )
    )
    
    :: 执行构建
    echo   - 执行前端构建...
    call npm run build
    if errorlevel 1 (
        echo %RED%[错误] 前端构建失败%RESET%
        cd ..
        pause
        exit /b 1
    )
    
    cd ..
    echo   - 前端构建完成
    echo.
) else (
    echo [4/6] 跳过前端构建
    echo.
)

:: ============================================================================
:: 5. 打包后端
:: ============================================================================
if "%SKIP_BACKEND%"=="0" (
    echo [5/6] 打包后端...
    
    cd backend
    
    :: PyInstaller打包配置
    :: 优化说明：
    ::   --onefile: 单文件打包，便于分发
    ::   --windowed: 无控制台窗口，后台运行
    ::   --optimize 2: Python字节码优化级别
    ::   --exclude-module: 排除不必要的模块减小体积
    ::   --hidden-import: 显式导入uvicorn相关模块
    
    echo   - 执行PyInstaller打包...
    
    pyinstaller main.py ^
        --name CAUC-SEP-Backend ^
        --onefile ^
        --windowed ^
        --add-data "core;core" ^
        --add-data "api;api" ^
        --add-data "middleware;middleware" ^
        --add-data "models;models" ^
        --hidden-import uvicorn.logging ^
        --hidden-import uvicorn.loops ^
        --hidden-import uvicorn.loops.auto ^
        --hidden-import uvicorn.protocols ^
        --hidden-import uvicorn.protocols.http ^
        --hidden-import uvicorn.protocols.http.auto ^
        --hidden-import uvicorn.protocols.websockets ^
        --hidden-import uvicorn.protocols.websockets.auto ^
        --hidden-import uvicorn.lifespan ^
        --hidden-import uvicorn.lifespan.on ^
        --hidden-import sqlalchemy.dialects.sqlite ^
        --hidden-import pydantic ^
        --hidden-import pydantic_core ^
        --hidden-import pydantic_settings ^
        --exclude-module matplotlib ^
        --exclude-module PIL ^
        --exclude-module tkinter ^
        --exclude-module unittest ^
        --exclude-module test ^
        --exclude-module tests ^
        --noupx ^
        --optimize 2 ^
        --noconfirm ^
        --clean
    
    if errorlevel 1 (
        echo %RED%[错误] 后端打包失败%RESET%
        cd ..
        pause
        exit /b 1
    )
    
    cd ..
    echo   - 后端打包完成
    echo.
) else (
    echo [5/6] 跳过后端打包
    echo.
)

:: ============================================================================
:: 6. 组装发布包
:: ============================================================================
echo [6/6] 组装发布包...

:: 创建发布目录
set "RELEASE_DIR=dist\CAUC-SEP"
if not exist "%RELEASE_DIR%" mkdir "%RELEASE_DIR%"

:: 复制后端可执行文件
if exist "backend\dist\CAUC-SEP-Backend.exe" (
    echo   - 复制后端可执行文件...
    copy /y "backend\dist\CAUC-SEP-Backend.exe" "%RELEASE_DIR%\" >nul
)

:: 复制前端构建产物
if exist "frontend\dist" (
    echo   - 复制前端文件...
    xcopy /E /I /Y /Q "frontend\dist" "%RELEASE_DIR%\frontend" >nul
)

:: 创建日志目录
if not exist "%RELEASE_DIR%\logs" mkdir "%RELEASE_DIR%\logs"

:: 创建数据目录
if not exist "%RELEASE_DIR%\data" mkdir "%RELEASE_DIR%\data"

:: 创建启动脚本
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
    echo :: 启动后端服务
    echo start "" CAUC-SEP-Backend.exe
    echo.
    echo :: 等待服务启动
    echo timeout /t 3 /nobreak ^>nul
    echo.
    echo :: 打开浏览器
    echo start http://localhost:8000
    echo.
    echo echo 服务已启动，请勿关闭此窗口。
    echo echo 按任意键停止服务...
    echo pause ^>nul
    echo.
    echo :: 停止服务
    echo taskkill /f /im CAUC-SEP-Backend.exe ^>nul 2^>^&1
) > "%RELEASE_DIR%\start.bat"

:: 创建停止脚本
(
    echo @echo off
    echo echo 正在停止 CAUC-SEP 服务...
    echo taskkill /f /im CAUC-SEP-Backend.exe ^>nul 2^>^&1
    echo echo 服务已停止。
    echo pause
) > "%RELEASE_DIR%\stop.bat"

:: 创建配置文件
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
) > "%RELEASE_DIR%\config.ini"

:: 创建版本信息
(
    echo CAUC-SEP 自旋电子实验平台
    echo 版本: 0.3.0
    echo 构建日期: %date% %time%
    echo.
    echo 目录结构:
    echo   CAUC-SEP-Backend.exe  - 后端服务程序
    echo   frontend/             - 前端静态文件
    echo   logs/                 - 日志目录
    echo   data/                 - 数据存储目录
    echo   start.bat             - 启动脚本
    echo   stop.bat              - 停止脚本
    echo   config.ini            - 配置文件
    echo.
    echo 使用方法:
    echo   1. 双击 start.bat 启动服务
    echo   2. 浏览器自动打开 http://localhost:8000
    echo   3. 双击 stop.bat 停止服务
) > "%RELEASE_DIR%\README.txt"

echo   - 发布包组装完成
echo.

:: ============================================================================
:: 构建完成
:: ============================================================================
echo.
echo ==========================================
echo   构建完成！
echo ==========================================
echo.
echo 发布目录: %RELEASE_DIR%
echo.

:: 显示文件大小
if exist "%RELEASE_DIR%\CAUC-SEP-Backend.exe" (
    for %%I in ("%RELEASE_DIR%\CAUC-SEP-Backend.exe") do (
        set /a SIZE_MB=%%~zI/1024/1024
        echo 后端文件大小: !SIZE_MB! MB
    )
)

:: 显示目录结构
echo.
echo 发布包内容:
dir /b "%RELEASE_DIR%"

echo.
echo %GREEN%构建成功！%RESET%
echo.
echo 按任意键退出...
pause >nul
