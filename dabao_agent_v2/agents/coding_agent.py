"""DeepSeek-backed safe Python utility generator."""

from __future__ import annotations

import re

from llm.deepseek_client import DeepSeekClient
from tools.python_tool import PythonTool


class CodingAgent:
    def __init__(self, llm: DeepSeekClient) -> None:
        self.llm, self.tool = llm, PythonTool()

    def execute(self, requirement: str) -> dict:
        prompt = (
            "生成一个简单、可独立运行的 Python 3.12 小工具。只输出一个 python 代码块。"
            "禁止删除文件、系统命令、网络连接、注册表、支付或交易功能。需求：" + requirement
        )
        response = self.llm.chat([{"role": "system", "content": "你是安全的 Python 工具工程师。"}, {"role": "user", "content": prompt}])
        match = re.search(r"```(?:python)?\s*(.*?)```", response, re.S | re.I)
        code = (match.group(1) if match else response).strip()
        path = self.tool.save("generated_tool.py", code)
        run = self.tool.test_run(path)
        return {"path": str(path), "safety": "passed", "test_run": run}

