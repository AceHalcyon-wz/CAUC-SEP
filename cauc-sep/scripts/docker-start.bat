@echo off
REM ============================================================================
REM CAUC-SEP Docker Start Script
REM 启动所有服务
REM ============================================================================

setlocal EnableDelayedExpansion

echo.
echo ========================================
echo CAUC-SEP Docker Start Script
echo ========================================
echo.

REM 检查Docker是否运行
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo [INFO] Docker is running
echo.

REM 启动服务
echo [STEP 1] Starting services...
docker compose up -d
if errorlevel 1 (
    echo [ERROR] Failed to start services!
    pause
    exit /b 1
)

echo [OK] Services started
echo.

REM 等待服务健康检查
echo [STEP 2] Waiting for services to be healthy...
timeout /t 10 /nobreak >nul

REM 检查服务状态
echo.
echo ========================================
echo Service Status
echo ========================================
docker compose ps
echo.

REM 显示访问地址
echo ========================================
echo Access URLs
echo ========================================
echo Frontend:    http://localhost:8080
echo Backend API: http://localhost:8000
echo API Docs:    http://localhost:8000/docs
echo Redis:       localhost:6379 (internal only)
echo.

echo [SUCCESS] All services are running!
echo.
echo To stop the application, run: stop.bat
echo To view logs, run: logs.bat
echo.

pause
