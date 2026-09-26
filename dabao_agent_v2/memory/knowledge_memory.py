"""Confirmed long-lived business rules."""

from memory.sqlite_store import SQLiteStore


class KnowledgeMemory:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def save_confirmed(self, key: str, content: str) -> None:
        self.store.upsert_memory("knowledge", key, content, "confirmed")

