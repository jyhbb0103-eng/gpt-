"""Generic deterministic report writer."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import STORAGE_ROOT, ensure_storage


class ReportAgent:
    def save_json_report(self, title: str, task_type: str, data: Any) -> Path:
        ensure_storage()
        path = STORAGE_ROOT / "reports" / f"{task_type}_{datetime.now():%Y%m%d_%H%M%S}.md"
        body = [f"# {title}", "", f"生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}", "", "## 结果", "", "```json", json.dumps(data, ensure_ascii=False, indent=2, default=str), "```", ""]
        path.write_text("\n".join(body), encoding="utf-8")
        return path

