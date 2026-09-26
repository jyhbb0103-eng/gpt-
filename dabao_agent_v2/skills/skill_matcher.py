"""Local Skill matching avoids an unnecessary LLM planning call."""

from __future__ import annotations

from typing import Any


class SkillMatcher:
    def match(self, command: str, skills: dict[str, dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
        command_lower = command.lower()
        scored = []
        for skill in skills.values():
            if skill.get("status") == "deprecated":
                continue
            triggers = [str(item).lower() for item in skill.get("triggers", [])]
            exact = any(trigger in command_lower or command_lower in trigger for trigger in triggers)
            similarity = 0.0
            for trigger in triggers:
                trigger_pairs = {trigger[index:index + 2] for index in range(max(0, len(trigger) - 1))}
                command_pairs = {command_lower[index:index + 2] for index in range(max(0, len(command_lower) - 1))}
                if trigger_pairs:
                    similarity = max(similarity, len(trigger_pairs & command_pairs) / len(trigger_pairs))
            score = 100 if exact else similarity * 50 if similarity >= 0.4 else 0
            if score:
                scored.append((score, skill))
        return [skill for _, skill in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]
