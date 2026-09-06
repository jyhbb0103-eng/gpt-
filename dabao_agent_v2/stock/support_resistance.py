"""Algorithmic support and resistance; the LLM never invents these."""

import pandas as pd


def calculate_levels(history: pd.DataFrame) -> dict[str, float]:
    close = history["close"]
    current = float(close.iloc[-1])
    ma20 = float(close.rolling(20).mean().iloc[-1])
    ma60 = float(close.rolling(60).mean().iloc[-1]) if len(close) >= 60 else ma20
    low20 = float(history["low"].tail(20).min())
    high20 = float(history["high"].tail(20).max())
    support = max([x for x in (low20, ma20, ma60) if 0 < x <= current] or [low20])
    resistance = min([x for x in (high20, ma20, ma60) if x >= current] or [high20])
    return {"support": round(support, 2), "resistance": round(resistance, 2), "ma20": round(ma20, 2), "ma60": round(ma60, 2), "low20": round(low20, 2), "high20": round(high20, 2)}

