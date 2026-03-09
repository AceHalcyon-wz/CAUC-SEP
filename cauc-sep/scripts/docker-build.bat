@echo off
REM ============================================================================
REM CAUC-SEP Docker Build Script
REM 构建所有Docker镜像
REM ============================================================================

setlocal EnableDelayedExpansion

echo.
echo ========================================
echo CAUC-SEP Docker Build Script
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

REM 验证docker-compose配置
echo [STEP 1] Validating docker-compose.yml...
docker compose config --quiet
if errorlevel 1 (
    echo [ERROR] docker-compose.yml validation failed!
    pause
    exit /b 1
)
echo [OK] Configuration is valid
echo.

REM 构建后端镜像
echo [STEP 2] Building backend image...
docker compose build --no-cache backend
if errorlevel 1 (
    echo [ERROR] Backend build failed!
    pause
    exit /b 1
)
echo [OK] Backend image built successfully
echo.

REM 构建前端镜像
echo [STEP 3] Building frontend image...
docker compose build --no-cache frontend
if errorlevel 1 (
    echo [ERROR] Frontend build failed!
    pause
    exit /b 1
)
echo [OK] Frontend image built successfully
echo.

REM 拉取Redis镜像
echo [STEP 4] Pulling Redis image...
docker compose pull redis
if errorlevel 1 (
    echo [ERROR] Redis pull failed!
    pause
    exit /b 1
)
echo [OK] Redis image pulled successfully
echo.

REM 显示构建结果
echo ========================================
echo Build Summary
echo ========================================
docker images --filter "reference=cauc-sep*" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
echo.

echo [SUCCESS] All images built successfully!
echo.
echo To start the application, run: start.bat
echo.

pause
