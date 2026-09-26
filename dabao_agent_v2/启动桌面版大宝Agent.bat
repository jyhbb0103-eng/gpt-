@echo off
chcp 65001 >nul
title 大宝 Agent 2.0
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] 未找到项目虚拟环境：%CD%\.venv
    echo 请先完成项目的首次安装。
    pause
    exit /b 1
)

if not exist "desktop_app.py" (
    echo [ERROR] 未找到 desktop_app.py
    pause
    exit /b 1
)

".venv\Scripts\python.exe" desktop_app.py

if errorlevel 1 (
    echo.
    echo 大宝 Agent 启动失败，请查看 logs\desktop_startup.log
    pause
)
