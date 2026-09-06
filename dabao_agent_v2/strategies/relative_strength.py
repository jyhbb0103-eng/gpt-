"""Relative stock strength strategy."""

from typing import Any
import pandas as pd
from config import strategy_config as cfg
from stock.indicators import clamp
from strategies.base_strategy import BaseStrategy


class RelativeStrengthStrategy(BaseStrategy):
    name, max_score = "strength", cfg.STRENGTH_WEIGHT

    def calculate_score(self, stock: dict[str, Any], history: pd.DataFrame, context: dict[str, Any]) -> tuple[float, list[str]]:
        change, sector, index = float(stock.get("change_pct", 0)), float(context.get("sector_change_pct", 0)), float(context.get("index_change_pct", 0))
        five = float(history["close"].iloc[-1] / history["close"].iloc[-6] - 1) * 100
        high, low, close = (float(history[key].iloc[-1]) for key in ("high", "low", "close"))
        location = (close - low) / (high - low) if high > low else .5
        score = 4 + (change - sector) * .7 + (change - index) * .4 + five * .2 + location * 2
        return round(clamp(score, 0, 10), 1), [f"跑赢板块 {change-sector:+.2f}pct", f"近5日 {five:+.2f}%"]

