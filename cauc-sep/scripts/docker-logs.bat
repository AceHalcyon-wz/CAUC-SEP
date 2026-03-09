@echo off
REM ============================================================================
REM CAUC-SEP Docker Logs Script
REM 查看服务日志
REM ============================================================================

setlocal EnableDelayedExpansion

echo.
echo ========================================
echo CAUC-SEP Docker Logs Script
echo ========================================
echo.

if "%1"=="" (
    echo Usage: logs.bat [SERVICE]
    echo.
    echo Available services:
    echo   backend  - FastAPI backend
    echo   frontend - Nginx frontend
    echo   redis    - Redis cache
    echo   all      - All services
    echo.
    set /p SERVICE="Enter service name (default: all): "
    if "!SERVICE!"=="" set SERVICE=all
) else (
    set SERVICE=%1
)

echo.
echo [INFO] Showing logs for: !SERVICE!
echo ========================================
echo.

if "!SERVICE!"=="all" (
    docker compose logs -f --tail=100
) else (
    docker compose logs -f --tail=100 !SERVICE!
)
