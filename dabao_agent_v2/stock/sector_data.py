"""Industry board data and constituents."""

from __future__ import annotations

import pandas as pd

from stock.filters import StockFilters
from stock.eastmoney_client import EastmoneyClient
from stock.indicators import safe_float
from stock.market_data import STOCK_FIELDS


class SectorData:
    def __init__(self, client: EastmoneyClient) -> None:
        self.client = client

    def fetch_sectors(self) -> pd.DataFrame:
        rows = self.client.quote_list("m:90+t:2+f:!50", "f2,f3,f6,f12,f14,f104,f105,f106")
        parsed = []
        for item in rows:
            up, down, flat = (int(safe_float(item.get(key))) for key in ("f104", "f105", "f106"))
            total = up + down + flat
            parsed.append({"sector_code": str(item.get("f12") or ""), "sector_name": str(item.get("f14") or "未知"),
                           "change_pct": safe_float(item.get("f3")), "amount": safe_float(item.get("f6")),
                           "up_count": up, "down_count": down, "up_ratio": up / total if total else 0.0})
        return pd.DataFrame(parsed)

    def constituent_codes(self, sector_code: str) -> set[str]:
        frame = self.constituents(sector_code)
        return set(frame["code"].astype(str)) if not frame.empty else set()

    def constituents(self, sector_code: str) -> pd.DataFrame:
        """Return filtered quote rows so they can also serve as market fallback."""
        rows = self.client.quote_list(f"b:{sector_code}", STOCK_FIELDS)
        parsed = []
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
