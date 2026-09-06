"""Constrained local-computer tools for Windows.

These tools intentionally avoid arbitrary shell execution. PyAutoGUI's fail-safe
remains enabled: moving the mouse to the upper-left corner aborts automation.
"""

from __future__ import annotations

import subprocess
import time
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Any, Callable


SCREENSHOTS_DIR = Path(__file__).resolve().parent / "screenshots"

COMPUTER_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "在 Windows 打开允许列表中的应用程序。",
            "parameters": {
                "type": "object",
                "properties": {
                    "application": {
                        "type": "string",
                        "enum": ["notepad", "calculator", "explorer", "vscode", "edge", "chrome"],
                        "description": "要打开的应用程序",
                    }
                },
                "required": ["application"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_website",
            "description": "用系统默认浏览器打开 http 或 https 网页。",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "完整网址"}},
                "required": ["url"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "打开浏览器并使用必应搜索指定内容。",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "搜索关键词"}},
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "type_text",
            "description": "在当前获得焦点的位置输入文字，支持中文。执行前应先打开目标应用并等待。",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "要输入的文字"},
                    "interval": {"type": "number", "minimum": 0, "maximum": 0.2, "default": 0.02},
                },
                "required": ["text"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "press_keys",
            "description": "按下单个按键或组合键，例如 enter、ctrl+l、ctrl+s。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                        "maxItems": 4,
                        "description": "按键名称数组",
                    }
                },
                "required": ["keys"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "click_mouse",
            "description": "点击屏幕坐标。仅当用户明确给出坐标或任务确实需要时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "minimum": 0},
                    "y": {"type": "integer", "minimum": 0},
                    "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
                },
                "required": ["x", "y"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wait_for_screen",
            "description": "等待应用或网页加载，最多等待 10 秒。",
            "parameters": {
                "type": "object",
                "properties": {"seconds": {"type": "number", "minimum": 0.2, "maximum": 10}},
                "required": ["seconds"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "截取当前屏幕并保存，返回截图文件路径和屏幕尺寸。",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
]


def _pyautogui():
    try:
        import pyautogui
    except ImportError as exc:
        raise RuntimeError("缺少 pyautogui，请先运行 pip install -r requirements.txt") from exc
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.15
    return pyautogui


def open_application(application: str) -> dict[str, Any]:
    commands = {
        "notepad": ["notepad.exe"],
        "calculator": ["calc.exe"],
        "explorer": ["explorer.exe"],
        "vscode": ["code"],
        "edge": ["cmd", "/c", "start", "", "msedge"],
        "chrome": ["cmd", "/c", "start", "", "chrome"],
    }
    command = commands.get(application)
    if not command:
        return {"ok": False, "error": "该应用不在允许列表中"}
    subprocess.Popen(command, shell=False)
    return {"ok": True, "application": application}


def open_website(url: str) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return {"ok": False, "error": "只允许打开有效的 http/https 网址"}
    return {"ok": bool(webbrowser.open(url)), "url": url}


def search_web(query: str) -> dict[str, Any]:
    if not query.strip() or len(query) > 300:
        return {"ok": False, "error": "搜索关键词为空或过长"}
    url = "https://www.bing.com/search?q=" + urllib.parse.quote_plus(query)
    return {"ok": bool(webbrowser.open(url)), "query": query}


def type_text(text: str, interval: float = 0.02) -> dict[str, Any]:
    if len(text) > 2000:
        return {"ok": False, "error": "单次输入不能超过 2000 个字符"}
    gui = _pyautogui()
    try:
        import pyperclip
    except ImportError as exc:
        raise RuntimeError("缺少 pyperclip，请先安装项目依赖") from exc
    pyperclip.copy(text)
    gui.hotkey("ctrl", "v")
    if interval:
        time.sleep(min(float(interval), 0.2))
    return {"ok": True, "characters": len(text)}


def press_keys(keys: list[str]) -> dict[str, Any]:
    allowed = {
        "ctrl", "shift", "alt", "enter", "tab", "esc", "escape", "space",
        "backspace", "delete", "up", "down", "left", "right", "home", "end",
        "a", "c", "f", "l", "n", "s", "v", "w", "x", "z",
    }
    normalized = [key.lower().strip() for key in keys]
    if any(key not in allowed for key in normalized):
        return {"ok": False, "error": "包含未允许的按键"}
    gui = _pyautogui()
    if len(normalized) == 1:
        gui.press(normalized[0])
    else:
        gui.hotkey(*normalized)
    return {"ok": True, "keys": normalized}


def click_mouse(x: int, y: int, button: str = "left") -> dict[str, Any]:
    gui = _pyautogui()
    width, height = gui.size()
    if not (0 <= x < width and 0 <= y < height):
        return {"ok": False, "error": f"坐标超出屏幕范围 {width}×{height}"}
    gui.click(x=x, y=y, button=button)
    return {"ok": True, "x": x, "y": y, "button": button}


def wait_for_screen(seconds: float) -> dict[str, Any]:
    seconds = min(max(float(seconds), 0.2), 10.0)
    time.sleep(seconds)
    return {"ok": True, "waited_seconds": seconds}


def take_screenshot() -> dict[str, Any]:
    gui = _pyautogui()
    SCREENSHOTS_DIR.mkdir(exist_ok=True)
    filename = time.strftime("screen-%Y%m%d-%H%M%S.png")
    path = SCREENSHOTS_DIR / filename
    image = gui.screenshot()
    image.save(path)
    width, height = image.size
    return {"ok": True, "path": str(path), "width": width, "height": height}


COMPUTER_TOOLS: dict[str, Callable[..., dict[str, Any]]] = {
    "open_application": open_application,
    "open_website": open_website,
    "search_web": search_web,
    "type_text": type_text,
    "press_keys": press_keys,
    "click_mouse": click_mouse,
    "wait_for_screen": wait_for_screen,
    "take_screenshot": take_screenshot,
}
