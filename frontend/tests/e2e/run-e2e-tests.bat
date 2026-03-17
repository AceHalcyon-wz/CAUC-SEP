@echo off
REM CAUC-SEP E2E测试运行脚本
REM 用法: run-e2e-tests.bat [选项]
REM 选项:
REM   --auth          仅运行认证测试
REM   --settings      仅运行设置测试
REM   --cross-browser 仅运行跨浏览器测试
REM   --all           运行所有测试（默认）
REM   --ui            打开Playwright UI界面
REM   --debug         调试模式

SETLOCAL EnableDelayedExpansion

SET TEST_DIR=tests\e2e
SET REPORTER=list
SET WORKERS=1
SET PROJECT=chromium

REM 解析参数
SET TEST_TYPE=all
SET UI_MODE=false
SET DEBUG_MODE=false

:parse_args
IF "%~1"=="" GOTO end_parse
IF "%~1"=="--auth" SET TEST_TYPE=auth
IF "%~1"=="--settings" SET TEST_TYPE=settings
IF "%~1"=="--cross-browser" SET TEST_TYPE=cross-browser
IF "%~1"=="--all" SET TEST_TYPE=all
IF "%~1"=="--ui" SET UI_MODE=true
IF "%~1"=="--debug" SET DEBUG_MODE=true
SHIFT
GOTO parse_args
:end_parse

ECHO ========================================
ECHO CAUC-SEP E2E测试套件
ECHO ========================================
ECHO 测试类型: %TEST_TYPE%
ECHO 浏览器: %PROJECT%
ECHO 工作进程数: %WORKERS%
ECHO UI模式: %UI_MODE%
ECHO 调试模式: %DEBUG_MODE%
ECHO ========================================
ECHO.

REM 检查Node.js是否安装
WHERE node >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    ECHO 错误: 未找到Node.js，请先安装Node.js
    EXIT /B 1
)

REM 检查依赖是否安装
IF NOT EXIST "node_modules\@playwright" (
    ECHO 正在安装Playwright依赖...
    CALL npm install
    IF %ERRORLEVEL% NEQ 0 (
        ECHO 错误: 依赖安装失败
        EXIT /B 1
    )
)

REM 安装浏览器（如果需要）
IF NOT EXIST "%USERPROFILE%\AppData\Local\ms-playwright" (
    ECHO 正在安装Playwright浏览器...
    CALL npx playwright install
)

REM 构建测试命令
SET CMD=npx playwright test --reporter=%REPORTER% --workers=%WORKERS%

IF "%UI_MODE%"=="true" (
    SET CMD=%CMD% --ui
)

IF "%DEBUG_MODE%"=="true" (
    SET CMD=%CMD% --debug
)

REM 根据测试类型选择测试文件
IF "%TEST_TYPE%"=="auth" (
    SET CMD=%CMD% %TEST_DIR%\auth.spec.js
    ECHO 运行认证测试...
) ELSE IF "%TEST_TYPE%"=="settings" (
    SET CMD=%CMD% %TEST_DIR%\settings.spec.js
    ECHO 运行设置测试...
) ELSE IF "%TEST_TYPE%"=="cross-browser" (
    SET CMD=%CMD% %TEST_DIR%\cross-browser.spec.js
    ECHO 运行跨浏览器测试...
) ELSE (
    ECHO 运行所有E2E测试...
)

REM 执行测试
ECHO 执行命令: %CMD%
ECHO.
%CMD%

REM 检查测试结果
IF %ERRORLEVEL% EQU 0 (
    ECHO.
    ECHO ========================================
    ECHO 测试完成: 所有测试通过 ✓
    ECHO ========================================
) ELSE (
    ECHO.
    ECHO ========================================
    ECHO 测试完成: 部分测试失败 ✗
    ECHO 请查看上方的错误信息
    ECHO ========================================
)

REM 打开HTML报告（如果存在）
IF EXIST "playwright-report\index.html" (
    ECHO.
    ECHO 正在打开HTML测试报告...
    START playwright-report\index.html
)

EXIT /B %ERRORLEVEL%
