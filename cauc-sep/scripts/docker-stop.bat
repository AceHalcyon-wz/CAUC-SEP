@echo off
REM ============================================================================
REM CAUC-SEP Docker Stop Script
REM 停止所有服务
REM ============================================================================

setlocal EnableDelayedExpansion

echo.
echo ========================================
echo CAUC-SEP Docker Stop Script
echo ========================================
echo.

REM 停止服务
echo [STEP 1] Stopping services...
docker compose down
if errorlevel 1 (
    echo [ERROR] Failed to stop services!
    pause
    exit /b 1
)

echo [OK] Services stopped
echo.

REM 显示状态
echo ========================================
echo Service Status
echo ========================================
docker compose ps
echo.

echo [SUCCESS] All services stopped!
echo.

pause
