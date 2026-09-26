"""Workspace-scoped file helper."""

from pathlib import Path
from config.settings import STORAGE_ROOT, ensure_storage


class FileTool:
    def __init__(self) -> None:
        ensure_storage()

    def safe_output(self, folder: str, filename: str) -> Path:
        base = (STORAGE_ROOT / folder).resolve()
        base.mkdir(parents=True, exist_ok=True)
        target = (base / Path(filename).name).resolve()
        if base not in target.parents:
            raise ValueError("输出路径超出大宝 storage 范围")
        return target

