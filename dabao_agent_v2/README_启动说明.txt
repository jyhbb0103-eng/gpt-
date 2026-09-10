Dabao Agent 2.0 启动说明
==========================

一、推荐：桌面版启动

直接双击：

大宝Agent.exe

只双击一次，然后最多等待 30 秒。
桌面版会打开独立的“大宝 Agent 2.0”窗口，不会打开 Chrome 或 Edge。
请把大宝Agent.exe 放在项目根目录，也就是与 app.py、.venv 同一个文件夹。
关闭桌面窗口后，后台 Streamlit 会自动停止。


二、桌面版启动失败时

打开项目中的：

logs\desktop_startup.log

查看最下面最新时间的错误。不要连续多次双击大宝Agent.exe。
如果看到“等待 Streamlit 启动超过 30 秒”，请确认使用的是最新代理修复版。


三、浏览器版备用启动

桌面版仍然无法使用时，可以双击：

启动大宝Agent.bat

浏览器工作台地址：
http://localhost:8501

如果 8501 端口被占用，可以双击：

启动大宝Agent-备用端口.bat

备用地址：
http://localhost:8502


四、常见提示

1. 提示“未找到 Python 虚拟环境”
   说明项目根目录中缺少 .venv 文件夹，或者首次安装还没有完成。

2. 提示“未找到 app.py”
   说明启动文件不在正确的项目根目录。请确认启动文件与 app.py 放在同一个文件夹中。

3. 桌面版提示启动失败
   查看 logs\desktop_startup.log 最下面最新时间的记录。
   先关闭所有旧的大宝窗口，再重新启动一次。

4. 浏览器版没有自动打开
   保持运行日志窗口不要关闭，然后手动输入 http://localhost:8501。

以后启动 Dabao Agent，不需要打开 PowerShell，不需要激活虚拟环境，也不需要输入 Python 或 Streamlit 命令。
