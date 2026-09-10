"""Small explicit registry instead of a heavy Agent framework."""

from typing import Any


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Any] = {}

    def register(self, name: str, tool: Any) -> None:
        self._tools[name] = tool

    def get(self, name: str) -> Any:
        if name not in self._tools:
            raise KeyError(f"工具未注册：{name}")
        return self._tools[name]

    def names(self) -> list[str]:
        return sorted(self._tools)

