@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [错误] 未找到虚拟环境。请先按照 README.md 完成安装。
  pause
  exit /b 1
)

if not exist ".env" (
  echo [提示] 未找到 .env，正在从 .env.example 创建。
  copy /Y ".env.example" ".env" >nul
  echo 请先打开 .env，填写 DEEPSEEK_API_KEY，然后重新启动。
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m streamlit run app.py --server.address localhost --server.port 8501
if errorlevel 1 (
  echo.
  echo [错误] 启动失败。请查看 logs\dabao_market_agent.log
  pause
)
