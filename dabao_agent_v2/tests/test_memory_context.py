from pathlib import Path

from core.context_builder import ContextBuilder
from memory.memory_manager import MemoryManager
from memory.sqlite_store import SQLiteStore


def test_context_uses_only_small_relevant_memory(tmp_path: Path) -> None:
    memory = MemoryManager(SQLiteStore(tmp_path / "context.db"))
    memory.preferences.save_confirmed("report_format", "默认Markdown")
    memory.tasks.save({"task": "开始选股", "task_type": "stock_screening", "status": "success", "skills_used": [], "important_events": [], "result": "8只", "output": None, "execution_time": 1})
    context = ContextBuilder(memory).build("开始选股", "stock_screening", [{"name": "stock_screening", "description": "选股", "steps": ["fetch", "score"]}], {"rows": 10})
    assert context["current_task"] == "开始选股"
    assert len(context["recent_similar_tasks"]) == 1
    assert context["estimated_tokens"] > 0
    assert "所有聊天记录" not in str(context)

