"""Confirmed user preferences only; discovery candidates are not auto-saved."""

from memory.sqlite_store import SQLiteStore


class PreferenceMemory:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def save_confirmed(self, key: str, content: str) -> None:
        self.store.upsert_memory("preference", key, content, "confirmed")

