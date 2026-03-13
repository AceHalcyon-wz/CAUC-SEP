@echo off
REM ============================================================================
REM CAUC-SEP Docker日志查看脚本
REM
REM 文件名: docker-logs.bat
REM 路径: scripts/
REM 功能: 实时查看Docker容器服务日志
REM
REM 主要功能:
REM   1. 支持查看指定服务日志（backend/frontend/redis）
REM   2. 支持查看所有服务日志汇总
REM   3. 实时跟踪日志输出（-f参数）
REM   4. 显示最近100行日志记录
REM
REM 使用方法:
REM   查看所有服务日志: logs.bat all
REM   查看后端日志:     logs.bat backend
REM   查看前端日志:     logs.bat frontend
REM   查看Redis日志:    logs.bat redis
REM   交互式选择:       logs.bat（不带参数）
REM
REM 作者: 运维工程师 Agent
REM 创建日期: 2024-03-01
REM 最后更新: 2026-03-14
REM ============================================================================

setlocal EnableDelayedExpansion

echo.
echo ========================================
echo CAUC-SEP Docker日志查看脚本
echo ========================================
echo.

if "%1"=="" (
    echo 用法: logs.bat [服务名]
    echo.
    echo 可用服务:
    echo   backend  - FastAPI后端服务
    echo   frontend - Nginx前端服务
    echo   redis    - Redis缓存服务
    echo   all      - 所有服务
    echo.
    set /p SERVICE="请输入服务名称 (默认: all): "
    if "!SERVICE!"=="" set SERVICE=all
) else (
    set SERVICE=%1
)

echo.
echo [信息] 正在显示服务日志: !SERVICE!
echo ========================================
echo.

if "!SERVICE!"=="all" (
    docker compose logs -f --tail=100
) else (
    docker compose logs -f --tail=100 !SERVICE!
)
