# 大宝 A股市场分析 Agent

点击一次按钮，自动获取当天 A 股市场数据、计算固定的市场温度，并让 DeepSeek
解释当前市场环境。本项目只做整体市场分析，不选股、不自动交易、不保证收益。

## 一、安装（Windows / Python 3.12）

在 VS Code 中打开 `dabao_market_agent` 文件夹，然后在终端逐行运行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

打开 `.env`，只把第一行改为你的真实 DeepSeek Key：

```dotenv
DEEPSEEK_API_KEY=sk-你的真实密钥
```

不要把 `.env` 上传到 GitHub，也不要把 API Key 发给别人。

## 二、按开发顺序测试

先测试数据和固定评分（这一步不调用 DeepSeek）：

```powershell
python run_analysis.py
```

再运行离线单元测试（不访问网络、不消耗 API 额度）：

```powershell
python -m unittest discover -s tests -v
```

最后启动界面：

```powershell
python -m streamlit run app.py
```

也可以双击 `start.bat`。浏览器会打开 `http://localhost:8501`。

## 三、点击按钮后会发生什么

1. AkShare 获取四大指数日线、沪深 A 股实时行情和涨跌停池。
2. Python 计算均线、涨跌家数、成交额对比和涨跌停情绪。
3. Python 按固定权重计算 0–100 分，DeepSeek 无权修改分数。
4. DeepSeek 只解释已整理的数据、主要依据、风险和环境建议。
5. 如果 DeepSeek 失败，页面仍会展示 Python 生成的基础结论。

评分权重：指数趋势 25 分、涨跌家数 25 分、成交量 20 分、涨跌停情绪
20 分、风险因素 10 分。评分映射严格使用需求中的五档边界。

## 四、稳定性说明

- 每个外部请求都有独立异常处理和超时。
- 单个接口失败不会让全部流程直接崩溃。
- 涨跌停池失败时，程序用行情涨跌幅保守估算，并明确标注来源。
- 数据不完整时页面显示“本次判断仅供参考”。
- DeepSeek 不获取数据、不猜测缺失数据、不推荐具体股票。

## 五、日志和排错

日志文件：`logs/dabao_market_agent.log`

如果按钮长时间没有结果或页面报错，先打开日志查看最后一条 `ERROR`。常见原因：

- AkShare 上游接口短暂不可用：稍后重试，或先升级 AkShare。
- DeepSeek Key 未填写：检查 `.env` 第一行。
- 端口被占用：关闭旧的 Streamlit 窗口后再启动。

## 项目结构

```text
dabao_market_agent/
├─ app.py                    # Streamlit 界面
├─ data_service.py           # 数据获取、超时和降级
├─ market_analyzer.py        # 固定评分和市场判断
├─ llm_service.py            # DeepSeek 解释
├─ config.py                 # 配置和日志
├─ run_analysis.py           # 终端测试入口
├─ tests/test_market_analyzer.py
├─ requirements.txt
├─ .env.example
└─ start.bat
```
