"""Plan and execute a bounded autonomous browser research task."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable

from openai import OpenAI

from browser_research_tools import RESEARCH_TOOL_DEFINITIONS, run_research_tool, save_research_report


RESEARCH_SYSTEM_PROMPT = """你是一名自主网络研究智能体。你的目标是独立完成用户交付的资料研究任务。

执行规则：
1. 按计划使用不同关键词搜索，不要只看一个结果。
2. 至少打开并阅读两个不同网站的正文；搜索摘要不能当作完整证据。
3. 比较来源，对无法确认或相互矛盾的信息明确标注。
4. 不访问登录页面、私人网络或执行任何购买、发送、提交操作。
5. 最终使用 save_research_report 保存一份 Markdown 报告，包含：任务、结论、关键发现、来源链接。
6. 保存成功后，用简短文字告诉用户报告名称和完成情况。
"""


def create_plan(client: OpenAI, model: str, objective: str) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你是任务规划器。输出4到6个简短、可执行的中文编号步骤，不执行任务。"},
            {"role": "user", "content": objective},
        ],
    )
    return response.choices[0].message.content or "1. 搜索资料\n2. 阅读来源\n3. 整理并保存报告"


def run_research_task(
    client: OpenAI,
    model: str,
    objective: str,
    on_plan: Callable[[str], None] | None = None,
    on_tool_event: Callable[[str, dict[str, Any], dict[str, Any]], None] | None = None,
    max_rounds: int = 12,
) -> tuple[str, str]:
    plan = create_plan(client, model, objective)
    if on_plan:
        on_plan(plan)

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": RESEARCH_SYSTEM_PROMPT},
        {"role": "user", "content": f"研究目标：{objective}\n\n执行计划：\n{plan}\n\n现在开始独立执行。"},
    ]
    saved_path = ""

    for _ in range(max_rounds):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=RESEARCH_TOOL_DEFINITIONS,
            tool_choice="auto",
        )
        message = response.choices[0].message
        assistant: dict[str, Any] = {"role": "assistant", "content": message.content}
        if message.tool_calls:
            assistant["tool_calls"] = [call.model_dump() for call in message.tool_calls]
        messages.append(assistant)

        if not message.tool_calls:
            answer = message.content or "研究任务已结束。"
            if not saved_path:
                fallback = save_research_report(
                    f"研究报告-{datetime.now():%Y%m%d-%H%M%S}",
                    f"# 研究任务\n\n{objective}\n\n# 研究结果\n\n{answer}",
                )
                saved_path = fallback.get("path", "")
            return answer, saved_path

        for call in message.tool_calls:
            try:
                arguments = json.loads(call.function.arguments or "{}")
                result = run_research_tool(call.function.name, arguments)
            except Exception as exc:
                arguments = {}
                result = {"ok": False, "error": f"工具执行失败：{exc}"}
            if call.function.name == "save_research_report" and result.get("ok"):
                saved_path = result.get("path", "")
            if on_tool_event:
                on_tool_event(call.function.name, arguments, result)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    answer = "已达到最大执行步数，任务安全停止。"
    fallback = save_research_report(
        f"未完成报告-{datetime.now():%Y%m%d-%H%M%S}",
        f"# 研究任务\n\n{objective}\n\n# 状态\n\n{answer}\n\n# 已执行计划\n\n{plan}",
    )
    return answer, fallback.get("path", "")
