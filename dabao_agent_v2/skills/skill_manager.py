"""Keep YAML and SQLite Skill storage synchronized."""

from __future__ import annotations

from typing import Any

from memory.sqlite_store import SQLiteStore
from skills.skill_validator import SkillValidator
from skills.yaml_store import YAMLStore


class SkillManager:
    def __init__(self, store: SQLiteStore | None = None, yaml_store: YAMLStore | None = None) -> None:
        self.store = store or SQLiteStore()
        self.yaml_store = yaml_store or YAMLStore()
        self.validator = SkillValidator()
        self.skills: dict[str, dict[str, Any]] = {}
        self.reload()

    def reload(self) -> None:
        self.skills.clear()
        for skill, path in self.yaml_store.load_all():
            valid, _ = self.validator.validate(skill)
            if valid:
                self.skills[skill["name"]] = skill
                self.store.upsert_skill(skill, str(path))

    def save_confirmed_candidate(self, skill: dict[str, Any]) -> str:
        valid, message = self.validator.validate(skill)
        if not valid:
            raise ValueError(message)
        path = self.yaml_store.save_user_skill(skill)
        self.store.upsert_skill(skill, str(path))
        self.skills[skill["name"]] = skill
        return str(path)

    def stats(self) -> list[dict[str, Any]]:
        return self.store.skill_stats()

    def update_status(self, name: str, status: str) -> str:
        if status not in self.validator.ALLOWED_STATUS:
            raise ValueError("Skill 状态无效")
        if name not in self.skills:
            raise KeyError(f"未找到 Skill：{name}")
        skill = {**self.skills[name], "status": status}
        matching = [(payload, path) for payload, path in self.yaml_store.load_all() if payload.get("name") == name]
        if not matching:
            raise FileNotFoundError(f"未找到 Skill YAML：{name}")
        path = matching[0][1]
        import yaml
        path.write_text(yaml.safe_dump(skill, allow_unicode=True, sort_keys=False), encoding="utf-8")
        self.store.upsert_skill(skill, str(path))
        self.skills[name] = skill
        return str(path)
