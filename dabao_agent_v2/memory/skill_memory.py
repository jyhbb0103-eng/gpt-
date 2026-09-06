"""Skill usage statistics backed by SQLite."""

from memory.sqlite_store import SQLiteStore


class SkillMemory:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def record(self, skill_name: str, success: bool) -> None:
        self.store.record_skill_result(skill_name, success)

