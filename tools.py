"""Safe local tools exposed to the DeepSeek agent."""

from __future__ import annotations

import ast
import operator
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from computer_tools import COMPUTER_TOOL_DEFINITIONS, COMPUTER_TOOLS


NOTES_DIR = Path(__file__).resolve().parent / "notes"
NOTES_DIR.mkdir(exist_ok=True)


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前本地日期和时间。",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "安全计算四则运算、乘方、取余和括号表达式。",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string", "description": "例如 (25+3)*4"}},
                "required": ["expression"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_note",
            "description": "把内容保存为本地 Markdown 笔记。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "笔记名，不含路径"},
                    "content": {"type": "string", "description": "要保存的内容"},
                },
                "required": ["name", "content"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_note",
            "description": "读取一篇已经保存的本地笔记。",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "笔记名，不含路径"}},
                "required": ["name"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_notes",
            "description": "列出所有已经保存的本地笔记。",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
]

ALL_TOOL_DEFINITIONS = TOOL_DEFINITIONS + COMPUTER_TOOL_DEFINITIONS


_BINARY_OPERATORS: dict[type[ast.operator], Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPERATORS: dict[type[ast.unaryop], Callable[[float], float]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _evaluate(node: ast.AST) -> float | int:
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left, right = _evaluate(node.left), _evaluate(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("指数过大")
        return _BINARY_OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _UNARY_OPERATORS[type(node.op)](_evaluate(node.operand))
    raise ValueError("表达式包含不允许的内容")


def calculate(expression: str) -> dict[str, Any]:
    if len(expression) > 200:
        raise ValueError("表达式过长")
    value = _evaluate(ast.parse(expression, mode="eval"))
    return {"ok": True, "expression": expression, "result": value}


def _note_path(name: str) -> Path:
    clean = Path(name).stem.strip()
    if not clean or clean in {".", ".."} or len(clean) > 80:
        raise ValueError("笔记名无效")
    return NOTES_DIR / f"{clean}.md"


def get_current_time() -> dict[str, Any]:
    now = datetime.now().astimezone()
    return {"ok": True, "datetime": now.isoformat(timespec="seconds"), "timezone": str(now.tzinfo)}


def write_note(name: str, content: str) -> dict[str, Any]:
    path = _note_path(name)
    path.write_text(content, encoding="utf-8")
    return {"ok": True, "name": path.stem, "characters": len(content)}


def read_note(name: str) -> dict[str, Any]:
    path = _note_path(name)
    if not path.exists():
        return {"ok": False, "error": f"找不到笔记：{path.stem}"}
    return {"ok": True, "name": path.stem, "content": path.read_text(encoding="utf-8")}


def list_notes() -> dict[str, Any]:
    return {"ok": True, "notes": sorted(path.stem for path in NOTES_DIR.glob("*.md"))}


TOOLS: dict[str, Callable[..., dict[str, Any]]] = {
    "get_current_time": get_current_time,
    "calculate": calculate,
    "write_note": write_note,
    "read_note": read_note,
    "list_notes": list_notes,
}
TOOLS.update(COMPUTER_TOOLS)


def run_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    tool = TOOLS.get(name)
    if tool is None:
        return {"ok": False, "error": f"未知工具：{name}"}
    return tool(**arguments)
