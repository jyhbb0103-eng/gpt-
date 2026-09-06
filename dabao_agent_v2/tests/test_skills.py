from pathlib import Path

from memory.sqlite_store import SQLiteStore
from skills.skill_manager import SkillManager
from skills.skill_matcher import SkillMatcher


def test_skill_loading_matching_and_sqlite(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "test.db")
    manager = SkillManager(store=store)
    assert "stock_screening" in manager.skills
    matched = SkillMatcher().match("开始选股", manager.skills)
    assert matched[0]["name"] == "stock_screening"
    sector_matches = SkillMatcher().match("扫描今天强势板块", manager.skills)
    assert sector_matches[0]["name"] == "strong_sector_scan"
    assert "stock_screening" not in [item["name"] for item in sector_matches]
    assert len(store.skill_stats()) >= 6
