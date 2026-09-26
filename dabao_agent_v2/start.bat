@echo off
chcp 65001 >nul
title Dabao Agent 2.0
if not exist .venv\Scripts\python.exe (
  echo [ERROR] 未找到虚拟环境，请先运行 python -m venv .venv
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python -m streamlit run app.py
pause

