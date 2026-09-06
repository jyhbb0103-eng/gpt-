# 大宝 · Dabao Agent 2.0

大宝是一个以 DeepSeek 为“大脑”的 Windows 本地 AI 助手。第一阶段已经提供：

- 总管 Agent：理解命令、判断复杂度、匹配 Skill、选择专业 Agent、验证结果。
- Skill 系统：YAML 方便阅读，SQLite 用于搜索与统计；保存新 Skill 前必须确认。
- 五层记忆：短期、任务摘要、Skill、用户偏好和长期知识。
- Token 优化：只加载当前任务、相关 Skill、已确认偏好/规则和最近 2 次相似摘要。
- 股票 Agent：沪深主板筛选、强势板块、单股分析、算法评分和 Markdown 报告。
- Research Agent：使用公开网页接口搜索资料，不操作浏览器鼠标。
- Office Agent：读取并整理 Excel/CSV、去重、排序、重命名和合并。
- Coding Agent：DeepSeek 生成 Python 小工具，保存和运行前执行保守安全检查。
- Streamlit 工作台：聊天、状态、步骤、日志、结果、Skill 状态和停止按钮。

> 大宝第一阶段不包含 Windows 鼠标键盘控制，不登录券商，不自动交易，不支付、不转账。本项目仅用于研究与工具测试。

## 系统要求

- Windows 10 或 Windows 11
- 64 位 Python 3.12
- 可访问 DeepSeek API 和所需公开数据接口的网络
- DeepSeek API Key（股票算法和 Excel 可在无 Key 时运行；聊天、代码生成和 LLM 解释需要 Key）

## 第一次安装

以下命令都在项目目录内运行。假设你把项目放在 `D:\ai\dabao_agent`。

### 1. 打开项目目录

在文件夹地址栏输入 `powershell` 后回车，或在 VS Code 打开该文件夹，再打开终端：

```powershell
cd D:\ai\dabao_agent
```

### 2. 检查 Python 版本

```powershell
python --version
```

应显示 `Python 3.12.x`。如果显示其他版本，请尝试：

```powershell
py -3.12 --version
```

### 3. 创建虚拟环境

```powershell
py -3.12 -m venv .venv
```

### 4. 激活虚拟环境

PowerShell：

```powershell
.venv\Scripts\Activate.ps1
```

如果 PowerShell 提示禁止运行脚本，只修改当前窗口权限：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

CMD：

```bat
.venv\Scripts\activate.bat
```

成功后终端前面通常会出现 `(.venv)`。

### 5. 安装依赖

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

项目包含 `httpx[socks]`，可以兼容电脑上常见的 HTTP/SOCKS 代理设置。

### 6. 创建 `.env`

```powershell
Copy-Item .env.example .env
notepad .env
```

把：

```text
DEEPSEEK_API_KEY=xxxx
```

改成你的真实 DeepSeek API Key。不要加中文引号，不要把 `.env` 发给别人或上传 GitHub。

### 7. 启动大宝

推荐使用：

```powershell
python -m streamlit run app.py
```

也可以双击 `start.bat`。正常启动后，浏览器会打开：

```text
http://localhost:8501
```

页面顶部应显示：

```text
大宝 · 你的本地 AI 助手
```

页面中包含聊天输入、上传表格、任务状态、执行步骤、三路日志、Skill 状态、结果区域和停止任务按钮。

## 可以输入什么

```text
开始选股
扫描今天强势板块
分析 600000
搜索机器人行业最近资料
搜索机器人行业最近资料并整理成 Excel 表格
整理这个 Excel
帮我写一个 Python 小工具批量整理文本
```

整理 Excel 时，请先在聊天区上传 `.xlsx`、`.xlsm` 或 `.csv` 文件，再输入“整理这个 Excel”。输出文件会显示下载按钮。

## 如何停止

任务运行时，点击页面里的“停止任务”。大宝会停止后续阶段并保留日志。若正在等待第三方网络接口，当前请求最长等待配置的 timeout 后退出，不会无限等待。

要关闭整个工作台：

1. 点击启动 Streamlit 的终端窗口。
2. 按一次 `Ctrl+C`。
3. 等终端回到命令提示符后再关闭窗口。

## 数据和输出位置

| 内容 | 位置 | 是否默认发送给 DeepSeek |
|---|---|---|
| 完整执行日志 | `storage\logs\dabao.log` | 否 |
| 任务短摘要 | `storage\memory\dabao.db` | 仅最近 2 条相似摘要 |
| 内置 Skill | `skills\builtin\*.yaml` | 仅匹配的 Skill |
| 用户确认保存的 Skill | `storage\skills\*.yaml` | 仅匹配的 Skill |
| SQLite Skill/记忆索引 | `storage\memory\dabao.db` | 不会整库发送 |
| 股票/研究报告 | `storage\reports` | 否，除非当前任务需要 |
| 上传表格 | `storage\uploads` | 不会整目录发送 |
| 生成的 Python 工具 | `storage\generated` | 否 |
| 最近成功行情缓存 | `storage\cache` | 否 |

## Skill 如何工作

第一版内置 6 个 Skill：选股、单股分析、强势板块、网页研究、Excel 整理和 Python 工具生成。

每个 Skill 都很短，只记录触发语、步骤、版本、状态和运行统计。任务成功后，大宝判断是否值得形成新 Skill；若需要，会在页面询问“是否保存本次流程为新技能”，不会自动保存。

Skill 状态为：`draft`、`tested`、`stable`、`deprecated`。成功运行至少 3 次后，大宝只会建议升级为 `stable`，仍需点击确认。

## 股票 Agent 说明

股票范围仅包括代码前缀为 `600/601/603/605/000/001/002` 的沪深主板股票。第一版排除创业板、科创板、北交所、ST、*ST、退市整理、停牌、低流动性和明显异常数据。

评分共 100 分：

| 项目 | 分值 |
|---|---:|
| 板块强度 | 25 |
| 放量程度 | 20 |
| 突破质量 | 20 |
| 相对低位 | 15 |
| 个股相对强度 | 10 |
| 流动性与风险 | 10 |

Python 负责行情、指标、评分、排序、支撑和压力。DeepSeek 只能解释输入的结构化数据；Prompt 明确禁止补全行情数字。若 DeepSeek 不可用，程序仍保存纯算法报告。

所有权重、Top N、最低成交额、换手率、历史周期、并发数和 timeout 都在 `config\strategy_config.py` 中。

东方财富公开接口可能延迟、限流或调整。程序按“主域名 → 两个备用行情域名 → 最近成功缓存”降级；请求最多尝试 3 次，单只股票历史行情失败会记录并跳过。使用缓存时日志会明确警告，非交易日使用最近一个交易日，并在页面显示数据日期。

## 安全规则

第一阶段直接禁止：

- 自动买入、卖出、下单和券商登录
- 支付和转账
- 自动交易

删除、覆盖、卸载、上传、发送消息、修改系统设置等动作进入统一确认接口。当前阶段未实现 Windows 控制，因此不会操作你的鼠标、键盘或系统软件。

生成的 Python 工具会通过 AST 检查，拦截 `eval/exec`、系统命令、文件删除、注册表、网络套接字等高风险能力，并在受限输出目录内限时测试。它是安全护栏，不是绝对安全证明；运行涉及重要文件的脚本前仍应备份。

## 运行测试

离线关键模块测试：

```powershell
pytest -q
```

测试包含：配置加载、Skill 读取、Skill 匹配、SQLite 初始化、ContextBuilder、股票评分、停止任务、DeepSeek Mock、数据接口失败边界和 Excel 清理。

## 常见问题

### 未找到 `DEEPSEEK_API_KEY`

确认项目根目录存在 `.env`，内容为：

```text
DEEPSEEK_API_KEY=你的真实Key
```

保存后停止并重新启动 Streamlit。

### `streamlit` 不是内部或外部命令

说明虚拟环境可能没有激活，执行：

```powershell
.venv\Scripts\Activate.ps1
python -m streamlit run app.py
```

### 东方财富或网页搜索失败

先查看页面“执行日志”和 `storage\logs\dabao.log`。检查代理和网络后点击重试。所有请求有 timeout 和有限重试，不会永久卡住。

### 为什么“开始选股”需要一些时间

程序需要完整分页获取主板数据、获取强势板块成分股，并并发读取最多 80 只股票的 130 日历史行情。页面会持续显示阶段和日志。如果不需要继续，可点击停止。

### Ctrl+C 没反应

先点击运行 Streamlit 的终端窗口，使它获得键盘焦点，再按一次 `Ctrl+C`。不要在网页聊天输入框里按。

### Excel 文件无法读取

第一版支持 `.xlsx`、`.xlsm` 和 `.csv`。旧版 `.xls` 请先用 Excel 另存为 `.xlsx`。CSV 优先按 UTF-8 读取，失败时尝试 GBK。

## 主要目录

```text
dabao_agent/
├── agents/       # 总管和专业 Agent
├── config/       # 模型、Agent、股票配置
├── core/         # 路由、状态、上下文、验证、取消、安全
├── llm/          # DeepSeek Client
├── memory/       # 五层记忆与 SQLite
├── skills/       # Skill 管理及内置 YAML
├── stock/        # 东方财富数据、过滤、指标、评分
├── strategies/   # 可扩展股票策略
├── tools/        # 搜索、Excel、Python、文件工具
├── ui/           # Streamlit 面板
├── services/     # 日志与报告
├── storage/      # 运行数据和输出
└── tests/        # 关键离线测试
```

## 阶段边界

当前完成的是第一阶段 MVP。以下内容只预留安全和架构接口，尚未实现：

- 第二阶段：Computer Agent、Vision Agent、屏幕理解、鼠标键盘、人工接管和观察学习。
- 第三阶段：主动发现重复任务、定时任务、异常监控和复杂多 Agent 协作。

这能避免第一版再次因为依赖过重、浏览器驱动或无限等待而卡在启动阶段。
