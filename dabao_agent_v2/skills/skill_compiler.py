"""Create an unsaved reusable Skill candidate after a successful task."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any


class SkillCompiler:
    def candidate(self, command: str, task_type: str, steps: list[str], existing: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
        if len(steps) < 3 or task_type in existing:
            return None
        reusable_command = re.sub(r"\b[036]\d{5}\b", "指定股票", command)
        reusable_command = re.sub(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", "指定日期", reusable_command)
        now = datetime.now().isoformat(timespec="seconds")
        return {
            "name": f"custom_{task_type}",
            "description": f"由成功任务提炼：{reusable_command[:80]}",
            "version": "1.0",
            "status": "draft",
            "triggers": [reusable_command],
            "steps": steps,
            "success_count": 0,
            "failure_count": 0,
            "created_at": now,
            "updated_at": now,
        }

