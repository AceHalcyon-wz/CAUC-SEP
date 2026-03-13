@echo off
REM ============================================================================
REM CAUC-SEP Docker镜像构建脚本
REM
REM 文件名: docker-build.bat
REM 路径: scripts/
REM 功能: 自动化构建所有Docker镜像（后端、前端、Redis）
REM
REM 主要功能:
REM   1. 检查Docker Desktop运行状态
REM   2. 验证docker-compose.yml配置文件
REM   3. 构建后端FastAPI镜像
REM   4. 构建前端Nginx镜像
REM   5. 拉取Redis缓存服务镜像
REM   6. 显示构建结果汇总
REM
REM 使用方法:
REM   双击运行或在命令行执行: docker-build.bat
REM
REM 前置条件:
REM   - Docker Desktop已安装并运行
REM   - docker-compose.yml配置文件存在
REM   - 网络连接正常（用于拉取基础镜像）
REM
REM 作者: 运维工程师 Agent
REM 创建日期: 2024-03-01
REM 最后更新: 2026-03-14
REM ============================================================================

setlocal EnableDelayedExpansion

echo.
echo ========================================
echo CAUC-SEP Docker镜像构建脚本
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

REM 验证docker-compose配置
echo [步骤 1] 验证docker-compose.yml配置文件...
docker compose config --quiet
if errorlevel 1 (
    echo [错误] docker-compose.yml配置验证失败！
    pause
    exit /b 1
)
echo [成功] 配置文件验证通过
echo.

REM 构建后端镜像
echo [步骤 2] 构建后端镜像...
docker compose build --no-cache backend
if errorlevel 1 (
    echo [错误] 后端镜像构建失败！
    pause
    exit /b 1
)
echo [成功] 后端镜像构建完成
echo.

REM 构建前端镜像
echo [步骤 3] 构建前端镜像...
docker compose build --no-cache frontend
if errorlevel 1 (
    echo [错误] 前端镜像构建失败！
    pause
    exit /b 1
)
echo [成功] 前端镜像构建完成
echo.

REM 拉取Redis镜像
echo [步骤 4] 拉取Redis镜像...
docker compose pull redis
if errorlevel 1 (
    echo [错误] Redis镜像拉取失败！
    pause
    exit /b 1
)
echo [成功] Redis镜像拉取完成
echo.

REM 显示构建结果
echo ========================================
echo 构建结果汇总
echo ========================================
docker images --filter "reference=cauc-sep*" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
echo.

echo [成功] 所有镜像构建完成！
echo.
echo 启动应用请运行: start.bat
echo.

pause
