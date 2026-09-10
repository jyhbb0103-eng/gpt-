"""Sector strength from board change and advancing breadth."""

import pandas as pd
from config import strategy_config as cfg
from stock.indicators import clamp


class StrongSectorStrategy:
    def rank(self, sectors: pd.DataFrame) -> list[dict]:
        if sectors.empty:
            return []
        ranked = sectors.copy()
        ranked["score"] = (ranked["change_pct"].map(lambda x: clamp((x + 1) / 6, 0, 1)) * 60 + ranked["up_ratio"].map(lambda x: clamp(x / 0.8, 0, 1)) * 40).round(1)
        return ranked.sort_values(["score", "change_pct"], ascending=False).head(cfg.STRONG_SECTOR_COUNT).to_dict("records")

