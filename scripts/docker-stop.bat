@echo off
REM ============================================================================
REM CAUC-SEP Docker服务停止脚本
REM
REM 文件名: docker-stop.bat
REM 路径: scripts/
REM 功能: 停止所有Docker容器服务
REM
REM 主要功能:
REM   1. 使用docker-compose停止所有服务
REM   2. 清理容器资源
REM   3. 显示服务状态确认
REM
REM 停止服务:
REM   - backend:  FastAPI后端服务
REM   - frontend: Nginx前端服务
REM   - redis:    Redis缓存服务
REM
REM 使用方法:
REM   双击运行或在命令行执行: docker-stop.bat
REM
REM 注意事项:
REM   - 停止服务不会删除数据卷
REM   - 如需完全清理，请使用: docker compose down -v
REM
REM 作者: 运维工程师 Agent
REM 创建日期: 2024-03-01
REM 最后更新: 2026-03-14
REM ============================================================================

setlocal EnableDelayedExpansion

echo.
echo ========================================
echo CAUC-SEP Docker服务停止脚本
echo ========================================
echo.

REM 停止服务
echo [步骤 1] 正在停止服务...
docker compose down
if errorlevel 1 (
    echo [错误] 服务停止失败！
    pause
    exit /b 1
)

echo [成功] 服务已停止
echo.

REM 显示状态
echo ========================================
echo 服务状态
echo ========================================
docker compose ps
echo.

echo [成功] 所有服务已停止！
echo.

pause
