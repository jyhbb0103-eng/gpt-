"""Full Shanghai/Shenzhen main-board snapshot."""

from __future__ import annotations

from typing import Any

import pandas as pd

from stock.eastmoney_client import EastmoneyClient
from stock.filters import StockFilters
from stock.indicators import safe_float

STOCK_FIELDS = "f2,f3,f5,f6,f8,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f100"


class MarketData:
    def __init__(self, client: EastmoneyClient) -> None:
        self.client = client

    def fetch(self) -> pd.DataFrame:
        # t:80 (创业板) and t:23 (科创板) are intentionally absent.
        rows = self.client.quote_list("m:0+t:6,m:1+t:2", STOCK_FIELDS)
        parsed: list[dict[str, Any]] = []
        for item in rows:
            parsed.append({
                "code": str(item.get("f12") or ""), "name": str(item.get("f14") or ""),
                "price": safe_float(item.get("f2")), "change_pct": safe_float(item.get("f3")),
                "volume": safe_float(item.get("f5")), "amount": safe_float(item.get("f6")),
                "turnover_rate": safe_float(item.get("f8")), "volume_ratio_snapshot": safe_float(item.get("f10")),
                "market": int(safe_float(item.get("f13"))), "high": safe_float(item.get("f15")),
                "low": safe_float(item.get("f16")), "open": safe_float(item.get("f17")),
                "previous_close": safe_float(item.get("f18")), "total_market_cap": safe_float(item.get("f20")),
                "float_market_cap": safe_float(item.get("f21")), "industry": str(item.get("f100") or "未知"),
            })
        return StockFilters().apply(pd.DataFrame(parsed))

    def fetch_one(self, code: str) -> dict[str, Any]:
        item = self.client.stock_quote(f"{1 if code.startswith('6') else 0}.{code}", STOCK_FIELDS)
        frame = pd.DataFrame([{
            "code": str(item.get("f12") or code), "name": str(item.get("f14") or ""), "price": safe_float(item.get("f2")),
            "change_pct": safe_float(item.get("f3")), "volume": safe_float(item.get("f5")), "amount": safe_float(item.get("f6")),
            "turnover_rate": safe_float(item.get("f8")), "volume_ratio_snapshot": safe_float(item.get("f10")),
            "high": safe_float(item.get("f15")), "low": safe_float(item.get("f16")), "open": safe_float(item.get("f17")),
            "previous_close": safe_float(item.get("f18")), "total_market_cap": safe_float(item.get("f20")),
            "float_market_cap": safe_float(item.get("f21")), "industry": str(item.get("f100") or "未知"),
        }])
        filtered = StockFilters().apply(frame)
        if filtered.empty:
            raise ValueError(f"股票 {code} 不属于可分析的沪深主板范围，或已被风险/流动性过滤")
        return filtered.iloc[0].to_dict()
