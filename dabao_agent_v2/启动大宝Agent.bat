@echo off
chcp 65001 >nul
title Dabao Agent 2.0

cd /d "%~dp0"

echo.
echo ================================
echo      Dabao Agent 2.0
echo ================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] 未找到 Python 虚拟环境：
    echo %CD%\.venv
    echo.
    echo 请确认项目已经完成首次安装，并且 .venv 文件夹位于项目根目录。
    echo.
    pause
    exit /b 1
)

if not exist "app.py" (
    echo [ERROR] 未找到 app.py
    echo 当前目录：%CD%
    echo.
    pause
    exit /b 1
)

echo [1/3] 正在启动 Dabao Agent...
echo [2/3] 工作台地址：http://localhost:8501
echo [3/3] 浏览器将在几秒后自动打开...
echo.
echo 请保持本窗口打开。关闭本窗口将停止 Dabao Agent。
echo.

start "" /b powershell.exe -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process 'http://localhost:8501'"

".venv\Scripts\python.exe" -m streamlit run app.py --server.address localhost --server.port 8501 --server.headless true --server.fileWatcherType none --browser.gatherUsageStats false

echo.
echo Dabao Agent 已停止。
pause
