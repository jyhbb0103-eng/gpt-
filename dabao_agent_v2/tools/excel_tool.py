"""Script-first Excel/CSV processing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.cancellation import CancellationToken
from tools.file_tool import FileTool


class ExcelTool:
    def __init__(self, cancellation: CancellationToken) -> None:
        self.cancellation = cancellation
        self.files = FileTool()

    def read(self, path: str) -> dict[str, pd.DataFrame]:
        source = Path(path)
        if not source.exists():
            raise FileNotFoundError(f"未找到表格文件：{source}")
        if source.suffix.lower() == ".csv":
            for encoding in ("utf-8-sig", "gbk"):
                try:
                    return {"Sheet1": pd.read_csv(source, encoding=encoding)}
                except UnicodeDecodeError:
                    continue
            raise ValueError("CSV 编码无法识别，请另存为 UTF-8")
        if source.suffix.lower() in {".xlsx", ".xlsm"}:
            return pd.read_excel(source, sheet_name=None)
        raise ValueError("第一版仅支持 .xlsx、.xlsm 和 .csv")

    def cleanup(self, path: str, sort_column: str | None = None, rename: dict[str, str] | None = None) -> dict[str, Any]:
        """Trim column names, drop empty rows/duplicates, optionally rename/sort, and save xlsx."""
        sheets = self.read(path)
        output = self.files.safe_output("reports", f"cleaned_{Path(path).stem}.xlsx")
        summary = []
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            for sheet_name, frame in sheets.items():
                self.cancellation.raise_if_cancelled()
                before = len(frame)
                cleaned = frame.copy()
                cleaned.columns = [str(column).strip() for column in cleaned.columns]
                cleaned = cleaned.dropna(how="all").drop_duplicates()
                if rename:
                    cleaned = cleaned.rename(columns=rename)
                if sort_column and sort_column in cleaned.columns:
                    cleaned = cleaned.sort_values(sort_column)
                cleaned.to_excel(writer, sheet_name=str(sheet_name)[:31], index=False)
                summary.append({"sheet": sheet_name, "before_rows": before, "after_rows": len(cleaned), "removed": before - len(cleaned)})
        return {"output": str(output), "sheets": summary}

    def merge(self, paths: list[str]) -> dict[str, Any]:
        frames = []
        for path in paths:
            self.cancellation.raise_if_cancelled()
            frames.extend(self.read(path).values())
        merged = pd.concat(frames, ignore_index=True).drop_duplicates()
        output = self.files.safe_output("reports", "merged_tables.xlsx")
        merged.to_excel(output, index=False)
        return {"output": str(output), "rows": len(merged), "files": len(paths)}

    def records_to_excel(self, records: list[dict[str, Any]], filename: str) -> str:
        self.cancellation.raise_if_cancelled()
        output = self.files.safe_output("reports", filename)
        pd.DataFrame(records).drop_duplicates().to_excel(output, index=False)
        return str(output)
