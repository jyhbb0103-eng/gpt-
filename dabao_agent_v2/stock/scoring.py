"""Transparent 100-point scoring service."""

from typing import Any
import pandas as pd
from config import strategy_config as cfg
from stock.indicators import clamp
from stock.support_resistance import calculate_levels
from strategies.breakout import BreakoutStrategy
from strategies.low_position import LowPositionStrategy
from strategies.relative_strength import RelativeStrengthStrategy
from strategies.volume_breakout import VolumeBreakoutStrategy


class StockScoring:
    def __init__(self) -> None:
        self.strategies = [VolumeBreakoutStrategy(), BreakoutStrategy(), LowPositionStrategy(), RelativeStrengthStrategy()]

    def score(self, stock: dict[str, Any], history: pd.DataFrame, context: dict[str, Any]) -> dict[str, Any]:
        components = {"sector_score": round(clamp(float(context.get("sector_score", 0)) / 100 * cfg.SECTOR_WEIGHT, 0, 25), 1)}
        reasons, risks = [f"板块强度 {context.get('sector_score', 0):.1f}/100"], []
        for strategy in self.strategies:
            value, notes = strategy.calculate_score(stock, history, context)
            components[f"{strategy.name}_score"] = value
            reasons.extend(notes[:1])
        amount, turnover, change = float(stock.get("amount", 0)), float(stock.get("turnover_rate", 0)), abs(float(stock.get("change_pct", 0)))
        risk_score = 2 + clamp(amount / 500_000_000, 0, 1) * 4 + (3 if 1 <= turnover <= 12 else 1) + (1 if change < 9.5 else 0)
        components["risk_score"] = round(clamp(risk_score, 0, 10), 1)
        if turnover > 15: risks.append("换手率偏高")
        if change >= 9.5: risks.append("接近涨跌停，追高与流动性风险较大")
        if amount < 150_000_000: risks.append("成交额偏低")
        return {**stock, **components, "total_score": round(sum(components.values()), 1), "selection_reasons": reasons, "risk_factors": risks or ["未发现明显流动性异常"], **calculate_levels(history)}

