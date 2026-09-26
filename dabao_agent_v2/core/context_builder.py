"""Build a minimal effective LLM context instead of dumping all history."""

from __future__ import annotations

import json
from typing import Any

from config.agent_config import MAX_CONTEXT_CHARS, MAX_RELEVANT_MEMORIES, MAX_RELEVANT_SKILLS, MAX_SIMILAR_TASKS
from memory.memory_manager import MemoryManager


class ContextBuilder:
    def __init__(self, memory: MemoryManager) -> None:
        self.memory = memory

    def build(self, task: str, task_type: str, skills: list[dict[str, Any]], current_data: Any | None = None) -> dict[str, Any]:
        """Include only current task, matched Skills, confirmed memory and two summaries."""
        context = {
            "current_task": task,
            "matched_skills": [
                {key: skill.get(key) for key in ("name", "description", "steps")}
                for skill in skills[:MAX_RELEVANT_SKILLS]
            ],
            **self.memory.relevant(task_type, MAX_RELEVANT_MEMORIES, MAX_SIMILAR_TASKS),
            "current_data": current_data,
        }
        serialized = json.dumps(context, ensure_ascii=False, default=str)
        if len(serialized) > MAX_CONTEXT_CHARS and current_data is not None:
            context["current_data"] = str(current_data)[: MAX_CONTEXT_CHARS // 2] + "…"
        context["estimated_tokens"] = max(1, len(json.dumps(context, ensure_ascii=False, default=str)) // 4)
        return context

