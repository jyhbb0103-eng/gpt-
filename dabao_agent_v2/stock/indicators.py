"""Numeric indicators and safe parsing."""

from __future__ import annotations

from typing import Any

import math
import pandas as pd


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        return number if math.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def moving_averages(history: pd.DataFrame) -> dict[str, float]:
    close = history["close"]
    return {"ma20": float(close.rolling(20).mean().iloc[-1]), "ma60": float(close.rolling(60).mean().iloc[-1])}

