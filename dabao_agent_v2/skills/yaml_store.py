"""Human-readable YAML Skill persistence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from config.settings import PROJECT_ROOT, STORAGE_ROOT, ensure_storage


class YAMLStore:
    def __init__(self) -> None:
        ensure_storage()
        self.builtin_dir = PROJECT_ROOT / "skills" / "builtin"
        self.user_dir = STORAGE_ROOT / "skills"

    def load_all(self) -> list[tuple[dict[str, Any], Path]]:
        loaded = []
        for folder in (self.builtin_dir, self.user_dir):
            for path in sorted(folder.glob("*.yaml")):
                payload = yaml.safe_load(path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    loaded.append((payload, path))
        return loaded

    def save_user_skill(self, skill: dict[str, Any]) -> Path:
        path = self.user_dir / f"{skill['name']}.yaml"
        path.write_text(yaml.safe_dump(skill, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return path

