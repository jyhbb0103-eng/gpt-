# DeepSeek 智能体（新手版）

一个带 Windows 原生可视化工作台的 Python 智能体。它由 DeepSeek 驱动，会根据任务自行决定是否调用工具，并把最近的对话保存在本地。

## 已有能力

- 连续对话和本地记忆
- 安全计算数学表达式
- 获取当前时间
- 创建、读取和列出 Markdown 笔记
- 工具调用次数保护
- 不会把 `.env` 和 API Key 上传到 GitHub
- 可视化聊天、模型选择、工具开关、执行记录和笔记管理
- 可选择控制 Windows：打开应用/网页、搜索、输入文字、按键、点击和截图

## Windows 安装步骤

要求 Python 3.10 或更高版本（推荐你已经安装的 Python 3.12）。

在 VS Code 中打开本项目文件夹，然后打开终端，逐行运行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

如果 PowerShell 不允许激活虚拟环境，先只为当前窗口执行：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

打开 `.env`，把第一行替换成你的真实 DeepSeek API Key：

```dotenv
DEEPSEEK_API_KEY=sk-你的真实密钥
DEEPSEEK_MODEL=deepseek-v4-flash
```

不要把真实密钥发给别人，也不要删除 `.gitignore` 中的 `.env`。

## 启动可视化工作台（推荐）

安装完成后，直接双击项目中的 `start.bat`。

也可以在已激活虚拟环境的 CMD 中运行：

```cmd
python desktop_workbench.py
```

这是 Windows 原生窗口，不启动网页服务器，也不需要浏览器。你可以直接在左侧输入 API Key，不需要修改 `.env`。

需要操作电脑时，在左侧开启“允许控制本机”。例如：

```text
打开记事本，等待两秒，然后输入“今天开始学习 DeepSeek 智能体”
打开浏览器搜索 DeepSeek function calling 教程
```

电脑控制只会在运行本项目的那台 Windows 电脑上生效。执行时请观察屏幕；如需紧急中止，把鼠标快速移到屏幕左上角。程序不提供任意命令行执行能力，只能使用代码中明确允许的工具。

## 启动命令行版

```powershell
python agent.py
```

可以试着输入：

```text
帮我计算 (128+56)*7
把“每天学习30分钟Python”保存为学习计划
读取学习计划
```

输入 `/clear` 清空对话记忆，输入 `/exit` 退出。

## 测试

```powershell
python -m unittest discover -s tests -v
```

测试不调用 DeepSeek API，因此不会消耗额度。

## 项目结构

```text
deepseek-agent/
├─ agent.py              # 对话循环、DeepSeek 请求、工具调度和记忆
├─ desktop_workbench.py  # Windows 原生可视化工作台
├─ start.bat             # 双击启动脚本
├─ workbench.py          # 旧版 Streamlit 工作台（备用）
├─ computer_tools.py     # 受限制的 Windows 鼠标、键盘和应用工具
├─ tools.py              # 智能体可调用的工具
├─ tests/test_tools.py   # 工具安全性测试
├─ notes/                # 智能体创建的笔记
├─ .env.example          # 环境变量模板
└─ requirements.txt      # Python 依赖
```

## 修改模型

默认使用速度快、成本较低的 `deepseek-v4-flash`。需要更强能力时，把 `.env` 中的模型改为：

```dotenv
DEEPSEEK_MODEL=deepseek-v4-pro
```

模型名称和可用能力可能更新，以 DeepSeek 官方文档为准。
