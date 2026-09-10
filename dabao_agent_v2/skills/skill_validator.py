"""Validate compact Skill documents."""

from typing import Any


class SkillValidator:
    ALLOWED_STATUS = {"draft", "tested", "stable", "deprecated"}

    def validate(self, skill: dict[str, Any]) -> tuple[bool, str]:
        for key in ("name", "description", "triggers", "steps"):
            if not skill.get(key):
                return False, f"Skill 缺少字段：{key}"
        if skill.get("status", "draft") not in self.ALLOWED_STATUS:
            return False, "Skill 状态无效"
        if not isinstance(skill["triggers"], list) or not isinstance(skill["steps"], list):
            return False, "triggers 和 steps 必须是列表"
        return True, "验证通过"

