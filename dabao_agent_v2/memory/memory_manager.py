"""Facade over short-term, task, skill, preference and knowledge memory."""

from __future__ import annotations

from typing import Any

from memory.knowledge_memory import KnowledgeMemory
from memory.preference_memory import PreferenceMemory
from memory.skill_memory import SkillMemory
from memory.sqlite_store import SQLiteStore
from memory.task_memory import TaskMemory


class MemoryManager:
    def __init__(self, store: SQLiteStore | None = None) -> None:
        self.store = store or SQLiteStore()
        self.short_term: dict[str, Any] = {}
        self.tasks = TaskMemory(self.store)
        self.skills = SkillMemory(self.store)
        self.preferences = PreferenceMemory(self.store)
        self.knowledge = KnowledgeMemory(self.store)

    def relevant(self, task_type: str, memory_limit: int = 5, task_limit: int = 2) -> dict[str, Any]:
        return {
            "preferences_and_rules": self.store.memories(("preference", "knowledge"), memory_limit),
            "recent_similar_tasks": self.tasks.recent(task_type, task_limit),
        }

    def clear_short_term(self) -> None:
        self.short_term.clear()

