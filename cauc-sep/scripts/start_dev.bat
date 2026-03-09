@echo off
chcp 65001 >nul
echo ==========================================
echo   CAUC-SEP 自旋电子实验平台 - 开发环境启动脚本
echo ==========================================
echo.

:: 设置工作目录
cd /d "%~dp0\.."

:: 检查Python
echo [1/4] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请安装Python 3.8+
    pause
    exit /b 1
)
echo [OK] Python已安装

:: 检查Node.js
echo [2/4] 检查Node.js环境...
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Node.js，请安装Node.js 18+
    pause
    exit /b 1
)
echo [OK] Node.js已安装

:: 安装后端依赖
echo [3/4] 安装后端依赖...
cd backend
if not exist venv (
    echo 创建Python虚拟环境...
    python -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt -q
cd ..

:: 安装前端依赖
echo [4/4] 安装前端依赖...
cd frontend
if not exist node_modules (
    echo 安装Node依赖...
    call npm install
)
cd ..

echo.
echo ==========================================
echo   启动服务...
echo ==========================================
echo.

:: 启动后端服务（在新窗口）
echo 启动后端服务 (http://127.0.0.1:8000)...
start "后端服务" cmd /k "cd backend && call venv\Scripts\activate && python main.py"

:: 等待后端启动
timeout /t 3 /nobreak >nul

:: 启动前端服务（在新窗口）
echo 启动前端服务 (http://localhost:5173)...
start "前端服务" cmd /k "cd frontend && npm run dev"

:: 等待前端启动
timeout /t 3 /nobreak >nul

:: 打开浏览器
echo 打开浏览器...
start http://localhost:5173

echo.
echo ==========================================
echo   开发环境已启动！
echo ==========================================
echo.
echo 后端API: http://127.0.0.1:8000
echo 前端界面: http://localhost:5173
echo.
echo 按任意键关闭此窗口（服务将继续运行）
pause >nul
