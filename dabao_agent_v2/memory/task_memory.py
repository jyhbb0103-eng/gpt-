"""Task-summary memory; full logs stay outside LLM context."""

from memory.sqlite_store import SQLiteStore


class TaskMemory:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def save(self, summary: dict) -> None:
        self.store.save_task_summary(summary)

    def recent(self, task_type: str, limit: int = 2) -> list[dict]:
        return self.store.recent_similar_tasks(task_type, limit)

