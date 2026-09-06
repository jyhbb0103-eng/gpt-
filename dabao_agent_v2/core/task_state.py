"""Shared task states and execution result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class TaskState(StrEnum):
    IDLE = "IDLE"
    PLANNING = "PLANNING"
    MATCHING_SKILL = "MATCHING_SKILL"
    FETCHING_DATA = "FETCHING_DATA"
    EXECUTING = "EXECUTING"
    VALIDATING = "VALIDATING"
    WAITING_USER = "WAITING_USER"
    GENERATING_REPORT = "GENERATING_REPORT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"


class TaskType(StrEnum):
    STOCK_SCREENING = "stock_screening"
    STOCK_ANALYSIS = "stock_analysis"
    STRONG_SECTOR = "strong_sector_scan"
    WEB_RESEARCH = "web_research"
    EXCEL = "excel_cleanup"
    PYTHON_TOOL = "python_tool_generator"
    CHAT = "chat"


@dataclass(slots=True)
class TaskResult:
    """Consistent output shared by CLI, UI and memory."""

    state: TaskState
    message: str
    task_type: TaskType
    data: dict[str, Any] = field(default_factory=dict)
    report_path: str | None = None
    skill_candidate: dict[str, Any] | None = None
    error: str | None = None

