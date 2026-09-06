"""A small DeepSeek tool-calling agent with persistent local memory."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv
from openai import OpenAI

from tools import TOOL_DEFINITIONS, run_tool


BASE_DIR = Path(__file__).resolve().parent
MEMORY_FILE = BASE_DIR / "memory.json"
SYSTEM_PROMPT = """你是一个由 DeepSeek 驱动的中文智能体。
你会先理解用户目标，再决定是否调用工具。需要精确计算、时间或笔记操作时必须调用工具，
不要假装工具已经执行。回答清楚、简洁，并在工具失败时说明原因。
"""


def load_memory() -> list[dict[str, Any]]:
    """Load previous messages; return a clean conversation if unavailable."""
    if not MEMORY_FILE.exists():
        return [{"role": "system", "content": SYSTEM_PROMPT}]
    try:
        data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list) and data and data[0].get("role") == "system":
            return data
    except (OSError, json.JSONDecodeError, AttributeError):
        pass
    return [{"role": "system", "content": SYSTEM_PROMPT}]


def save_memory(messages: list[dict[str, Any]]) -> None:
    """Persist a bounded conversation history."""
    system = messages[:1]
    recent = messages[1:][-40:]
    MEMORY_FILE.write_text(
        json.dumps(system + recent, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def assistant_message_to_dict(message: Any) -> dict[str, Any]:
    """Convert an OpenAI SDK message into JSON-safe chat-completions input."""
    result: dict[str, Any] = {
        "role": "assistant",
        "content": message.content,
    }
    if message.tool_calls:
        result["tool_calls"] = [call.model_dump() for call in message.tool_calls]
    return result


def run_agent(
    client: OpenAI,
    model: str,
    messages: list[dict[str, Any]],
    max_tool_rounds: int = 8,
    tool_definitions: list[dict[str, Any]] | None = None,
    on_tool_event: Callable[[str, dict[str, Any], dict[str, Any]], None] | None = None,
) -> str:
    """Run the model/tool loop until DeepSeek returns a final answer."""
    active_tools = TOOL_DEFINITIONS if tool_definitions is None else tool_definitions
    for _ in range(max_tool_rounds):
        request: dict[str, Any] = {"model": model, "messages": messages}
        if active_tools:
            request.update({"tools": active_tools, "tool_choice": "auto"})
        response = client.chat.completions.create(**request)
        message = response.choices[0].message
        messages.append(assistant_message_to_dict(message))

        if not message.tool_calls:
            return message.content or "（模型没有返回文字内容）"

        for call in message.tool_calls:
            try:
                arguments = json.loads(call.function.arguments or "{}")
                result = run_tool(call.function.name, arguments)
            except json.JSONDecodeError as exc:
                result = {"ok": False, "error": f"工具参数不是有效 JSON：{exc}"}
            except Exception as exc:  # Keep one broken tool from crashing the agent.
                result = {"ok": False, "error": f"工具执行失败：{exc}"}

            if on_tool_event:
                on_tool_event(call.function.name, arguments, result)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    return "工具调用次数过多，本轮已安全停止。请把任务拆小后再试。"


def main() -> None:
    load_dotenv(BASE_DIR / ".env")
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise SystemExit("未找到 DEEPSEEK_API_KEY。请复制 .env.example 为 .env 并填入密钥。")

    model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    messages = load_memory()

    print(f"DeepSeek 智能体已启动（模型：{model}）")
    print("输入 /clear 清空记忆，输入 /exit 退出。")

    while True:
        try:
            user_input = input("\n你：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue
        if user_input.lower() in {"/exit", "exit", "quit"}:
            print("再见！")
            break
        if user_input.lower() == "/clear":
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            save_memory(messages)
            print("智能体：记忆已清空。")
            continue

        messages.append({"role": "user", "content": user_input})
        try:
            answer = run_agent(client, model, messages)
            print(f"智能体：{answer}")
        except Exception as exc:
            print(f"智能体：请求失败：{exc}")
        save_memory(messages)


if __name__ == "__main__":
    main()
