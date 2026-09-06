"""20-day high, platform and MA breakout strategy."""

from typing import Any
import pandas as pd
from config import strategy_config as cfg
from stock.indicators import clamp
from strategies.base_strategy import BaseStrategy


class BreakoutStrategy(BaseStrategy):
    name, max_score = "breakout", cfg.BREAKOUT_WEIGHT

    def calculate_score(self, stock: dict[str, Any], history: pd.DataFrame, context: dict[str, Any]) -> tuple[float, list[str]]:
        if len(history) < 61: return 0.0, ["突破历史不足"]
        close, volume = history["close"], history["volume"]
        today, prev20 = float(close.iloc[-1]), float(history["high"].iloc[-21:-1].max())
        high_score = 7 if today > prev20 else clamp((today / prev20 - .95) * 100, 0, 5)
        platform = close.iloc[-cfg.PLATFORM_LOOKBACK - 1:-1]
        upper, lower = float(platform.max()), float(platform.min())
        range_pct = (upper - lower) / max(float(platform.mean()), .01)
        volume_ratio = float(volume.iloc[-1] / volume.iloc[-11:-1].mean())
        platform_score = (3 if range_pct <= cfg.PLATFORM_MAX_RANGE_PCT else 0) + (3 if today > upper else 0) + (2 if volume_ratio >= 1.3 else 0)
        ma20, ma60 = float(close.rolling(20).mean().iloc[-1]), float(close.rolling(60).mean().iloc[-1])
        ma_score = (2 if today > ma20 else 0) + (2 if today > ma60 else 0)
        if (close.iloc[-2] <= close.rolling(20).mean().iloc[-2] < today) or (close.iloc[-2] <= close.rolling(60).mean().iloc[-2] < today): ma_score += 1
        return round(clamp(high_score + platform_score + ma_score, 0, 20), 1), ["突破20日高点" if today > prev20 else "接近20日高点", f"平台振幅 {range_pct:.1%}"]

