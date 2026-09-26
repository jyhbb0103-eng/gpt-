"""Healthy volume expansion strategy."""

from typing import Any
import pandas as pd
from config import strategy_config as cfg
from stock.indicators import clamp
from strategies.base_strategy import BaseStrategy


class VolumeBreakoutStrategy(BaseStrategy):
    name, max_score = "volume", cfg.VOLUME_WEIGHT

    def calculate_score(self, stock: dict[str, Any], history: pd.DataFrame, context: dict[str, Any]) -> tuple[float, list[str]]:
        if len(history) < 11:
            return 0.0, ["成交量历史不足"]
        volume = history["volume"]
        r5 = float(volume.iloc[-1] / volume.iloc[-6:-1].mean())
        r10 = float(volume.iloc[-1] / volume.iloc[-11:-1].mean())
        ratio = (r5 + r10) / 2
        if ratio < 0.8: score = ratio * 2
        elif ratio < cfg.IDEAL_VOLUME_RATIO_LOW: score = 5 + (ratio - 0.8) * 12
        elif ratio <= cfg.IDEAL_VOLUME_RATIO_HIGH: score = 13 + min(7, (ratio - cfg.IDEAL_VOLUME_RATIO_LOW) * 3.2)
        elif ratio < cfg.EXTREME_VOLUME_RATIO: score = 16 - (ratio - cfg.IDEAL_VOLUME_RATIO_HIGH) * 3
        else: score = 5
        return round(clamp(score, 0, self.max_score), 1), [f"当日量/5日均量 {r5:.2f}", f"当日量/10日均量 {r10:.2f}"]

