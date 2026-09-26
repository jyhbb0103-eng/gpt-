"""Thread-safe short-transaction SQLite storage."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import STORAGE_ROOT, ensure_storage


class SQLiteStore:
    def __init__(self, path: Path | None = None) -> None:
        ensure_storage()
        self.path = path or STORAGE_ROOT / "memory" / "dabao.db"
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        """Create all tables idempotently."""
        statements = [
            """CREATE TABLE IF NOT EXISTS skills (
                name TEXT PRIMARY KEY, description TEXT NOT NULL, version TEXT NOT NULL,
                status TEXT NOT NULL, yaml_path TEXT NOT NULL, triggers_json TEXT NOT NULL,
                steps_json TEXT NOT NULL, success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS task_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT, task TEXT NOT NULL, task_type TEXT NOT NULL,
                status TEXT NOT NULL, skills_json TEXT NOT NULL, events_json TEXT NOT NULL,
                result TEXT NOT NULL, output TEXT, execution_time REAL NOT NULL,
                created_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT, layer TEXT NOT NULL, memory_key TEXT NOT NULL,
                content TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'confirmed',
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                UNIQUE(layer, memory_key)
            )""",
        ]
        with self.connect() as connection:
            for statement in statements:
                connection.execute(statement)

    def upsert_skill(self, skill: dict[str, Any], yaml_path: str) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO skills(name, description, version, status, yaml_path, triggers_json,
                   steps_json, success_count, failure_count, created_at, updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(name) DO UPDATE SET description=excluded.description,
                   version=excluded.version,status=excluded.status,yaml_path=excluded.yaml_path,
                   triggers_json=excluded.triggers_json,steps_json=excluded.steps_json,updated_at=excluded.updated_at""",
                (
                    skill["name"], skill["description"], str(skill.get("version", "1.0")), skill.get("status", "draft"),
                    yaml_path, json.dumps(skill.get("triggers", []), ensure_ascii=False),
                    json.dumps(skill.get("steps", []), ensure_ascii=False), int(skill.get("success_count", 0)),
                    int(skill.get("failure_count", 0)), skill.get("created_at") or now, now,
                ),
            )

    def record_skill_result(self, name: str, success: bool) -> None:
        column = "success_count" if success else "failure_count"
        with self.connect() as connection:
            connection.execute(f"UPDATE skills SET {column}={column}+1, updated_at=? WHERE name=?", (datetime.now().isoformat(timespec="seconds"), name))

    def skill_stats(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute("SELECT name,status,version,success_count,failure_count,updated_at FROM skills ORDER BY name").fetchall()
        return [dict(row) for row in rows]

    def save_task_summary(self, summary: dict[str, Any]) -> None:
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO task_summaries(task,task_type,status,skills_json,events_json,result,output,execution_time,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (summary["task"], summary["task_type"], summary["status"], json.dumps(summary.get("skills_used", []), ensure_ascii=False),
                 json.dumps(summary.get("important_events", []), ensure_ascii=False), summary.get("result", ""), summary.get("output"),
                 float(summary.get("execution_time", 0)), datetime.now().isoformat(timespec="seconds")),
            )

    def recent_similar_tasks(self, task_type: str, limit: int = 2) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT task,status,result,output,created_at FROM task_summaries WHERE task_type=? ORDER BY id DESC LIMIT ?",
                (task_type, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def repeat_count(self, task_type: str) -> int:
        with self.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM task_summaries WHERE task_type=? AND status='success'", (task_type,)).fetchone()
        return int(row["count"])

    def upsert_memory(self, layer: str, key: str, content: str, status: str = "confirmed") -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO memories(layer,memory_key,content,status,created_at,updated_at) VALUES(?,?,?,?,?,?)
                   ON CONFLICT(layer,memory_key) DO UPDATE SET content=excluded.content,status=excluded.status,updated_at=excluded.updated_at""",
                (layer, key, content, status, now, now),
            )

    def memories(self, layers: tuple[str, ...], limit: int = 5) -> list[dict[str, Any]]:
        placeholders = ",".join("?" for _ in layers)
        with self.connect() as connection:
            rows = connection.execute(
                f"SELECT layer,memory_key,content FROM memories WHERE status='confirmed' AND layer IN ({placeholders}) ORDER BY id DESC LIMIT ?",
                (*layers, limit),
            ).fetchall()
        return [dict(row) for row in rows]
