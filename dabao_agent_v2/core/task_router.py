"""Fast deterministic routing before any LLM call."""

from __future__ import annotations

import re
from dataclasses import dataclass

from core.task_state import TaskType


@dataclass(slots=True)
class Route:
    task_type: TaskType
    parameters: dict[str, str]
    complex_task: bool


class TaskRouter:
    """Recognize built-in commands cheaply to reduce token use."""

    def route(self, command: str, attachments: list[str] | None = None) -> Route:
        text = command.strip()
        code = re.search(r"(?<!\d)([036]\d{5})(?!\d)", text)
        if "强势板块" in text or ("板块" in text and "扫描" in text):
            return Route(TaskType.STRONG_SECTOR, {}, False)
        if code and ("分析" in text or "股票" in text):
            return Route(TaskType.STOCK_ANALYSIS, {"code": code.group(1)}, True)
        if "选股" in text:
            return Route(TaskType.STOCK_SCREENING, {}, True)
        research_words = ("搜索", "研究", "资料", "新闻")
        excel_words = ("excel", "csv", "表格")
        if any(word in text for word in research_words) and any(word in text.lower() for word in excel_words):
            query = re.sub(r"^(帮我)?(搜索|研究|查找)", "", text).strip() or text
            return Route(TaskType.WEB_RESEARCH, {"query": query, "export_excel": "1"}, True)
        if attachments or any(word in text.lower() for word in excel_words):
            return Route(TaskType.EXCEL, {"path": (attachments or [""])[0]}, True)
        if any(word in text for word in research_words):
            query = re.sub(r"^(帮我)?(搜索|研究|查找)", "", text).strip() or text
            return Route(TaskType.WEB_RESEARCH, {"query": query}, True)
        if "Python" in text or "python" in text or "小工具" in text or "脚本" in text:
            return Route(TaskType.PYTHON_TOOL, {"requirement": text}, True)
        return Route(TaskType.CHAT, {"message": text}, False)
