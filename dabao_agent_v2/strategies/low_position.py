"""Relative-low-position turning-strong strategy."""

from typing import Any
import pandas as pd
from config import strategy_config as cfg
from stock.indicators import clamp
from strategies.base_strategy import BaseStrategy


class LowPositionStrategy(BaseStrategy):
    name, max_score = "low_position", cfg.LOW_POSITION_WEIGHT

    def calculate_score(self, stock: dict[str, Any], history: pd.DataFrame, context: dict[str, Any]) -> tuple[float, list[str]]:
        if len(history) < 60: return 0.0, ["低位历史不足"]
        close, current = history["close"], float(history["close"].iloc[-1])
        def pos(period: int) -> float:
            w = close.tail(min(period, len(close))); lo, hi = float(w.min()), float(w.max())
            return (current - lo) / (hi - lo) if hi > lo else .5
        p60, p120 = pos(60), pos(120)
        range_score = max(0, 8 - abs(p60 - .38) * 12 - abs(p120 - .35) * 6)
        ma20, ma60 = close.rolling(20).mean(), close.rolling(60).mean()
        slope20, slope60 = float(ma20.iloc[-1] / ma20.iloc[-6] - 1), float(ma60.iloc[-1] / ma60.iloc[-6] - 1)
        score = range_score + clamp(3 + slope20 * 100 + slope60 * 50, 0, 5) + (2 if current / close.iloc[-11] - 1 > -.04 else 0)
        return round(clamp(score, 0, 15), 1), [f"60日位置 {p60:.0%}", f"120日位置 {p120:.0%}", f"MA20斜率 {slope20:+.1%}"]

