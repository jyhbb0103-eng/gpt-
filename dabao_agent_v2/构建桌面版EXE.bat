@echo off
chcp 65001 >nul
title 构建大宝 Agent 2.0
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] 未找到项目虚拟环境：%CD%\.venv
    pause
    exit /b 1
)

echo [1/3] 检查并安装 pywebview...
".venv\Scripts\python.exe" -m pip show pywebview >nul 2>&1
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m pip install pywebview
    if errorlevel 1 goto :install_failed
)

echo [2/3] 检查并安装 PyInstaller...
".venv\Scripts\python.exe" -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m pip install pyinstaller
    if errorlevel 1 goto :install_failed
)

echo [3/3] 正在生成 dist\大宝Agent.exe...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name "大宝Agent" --collect-all webview desktop_app.py
if errorlevel 1 goto :build_failed

echo.
echo 构建成功：%CD%\dist\大宝Agent.exe
echo 请把 exe 保留在 dist 文件夹中，或复制到项目根目录使用。
pause
exit /b 0

:install_failed
echo.
echo [ERROR] 桌面依赖安装失败，请检查网络后重试。
pause
exit /b 1

:build_failed
echo.
echo [ERROR] EXE 构建失败。
pause
exit /b 1
