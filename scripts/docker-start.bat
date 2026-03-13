@echo off
REM ============================================================================
REM CAUC-SEP Docker服务启动脚本
REM
REM 文件名: docker-start.bat
REM 路径: scripts/
REM 功能: 启动所有Docker容器服务
REM
REM 主要功能:
REM   1. 检查Docker Desktop运行状态
REM   2. 使用docker-compose启动所有服务
REM   3. 等待服务健康检查完成
REM   4. 显示服务状态和访问地址
REM
REM 启动服务:
REM   - backend:  FastAPI后端服务 (端口8000)
REM   - frontend: Nginx前端服务 (端口8080)
REM   - redis:    Redis缓存服务 (端口6379)
REM
REM 使用方法:
REM   双击运行或在命令行执行: docker-start.bat
REM
REM 作者: 运维工程师 Agent
REM 创建日期: 2024-03-01
REM 最后更新: 2026-03-14
REM ============================================================================

setlocal EnableDelayedExpansion

echo.
echo ========================================
echo CAUC-SEP Docker服务启动脚本
echo ========================================
echo.

REM 检查Docker是否运行
docker info >nul 2>&1
if errorlevel 1 (
    echo [错误] Docker Desktop未运行！
    echo 请启动Docker Desktop后重试。
    pause
    exit /b 1
)

echo [信息] Docker运行正常
echo.

REM 启动服务
echo [步骤 1] 正在启动服务...
docker compose up -d
if errorlevel 1 (
    echo [错误] 服务启动失败！
    pause
    exit /b 1
)

echo [成功] 服务已启动
echo.

REM 等待服务健康检查
echo [步骤 2] 等待服务健康检查...
timeout /t 10 /nobreak >nul

REM 检查服务状态
echo.
echo ========================================
echo 服务状态
echo ========================================
docker compose ps
echo.

REM 显示访问地址
echo ========================================
echo 访问地址
echo ========================================
echo 前端界面:    http://localhost:8080
echo 后端API:     http://localhost:8000
echo API文档:     http://localhost:8000/docs
echo Redis:       localhost:6379 (仅内部访问)
echo.

echo [成功] 所有服务已启动运行！
echo.
echo 停止服务请运行: stop.bat
echo 查看日志请运行: logs.bat
echo.

pause
