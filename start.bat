@echo off
chcp 65001 >nul
cd /d "%~dp0"
title DeepSeek 智能体工作台

if not exist ".venv\Scripts\python.exe" (
    echo 正在创建独立虚拟环境...
    py -3.12 -m venv .venv
    if errorlevel 1 goto :error
)

call ".venv\Scripts\activate.bat"
python -c "import openai, dotenv, pyautogui, pyperclip, playwright" >nul 2>&1
if errorlevel 1 (
    echo 正在安装项目依赖，请稍候...
    python -m pip install -r requirements.txt
    if errorlevel 1 goto :error
)

echo 正在启动 DeepSeek 智能体工作台...
python desktop_workbench.py
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo 启动失败。请截图本窗口中的错误信息。
pause
