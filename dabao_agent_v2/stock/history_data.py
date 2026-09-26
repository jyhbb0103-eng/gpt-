"""Adjusted daily K-line parsing."""

from __future__ import annotations

import pandas as pd

from stock.eastmoney_client import EastmoneyClient
from stock.indicators import safe_float

COLUMNS = ["date", "open", "close", "high", "low", "volume", "amount", "amplitude", "change_pct", "change", "turnover_rate"]


class HistoryData:
    def __init__(self, client: EastmoneyClient) -> None:
        self.client = client

    def fetch_stock(self, code: str, limit: int) -> tuple[str | None, pd.DataFrame]:
        return self._fetch(f"{1 if code.startswith('6') else 0}.{code}", limit)

    def fetch_index(self, limit: int) -> tuple[str | None, pd.DataFrame]:
        return self._fetch("1.000001", limit)

    def _fetch(self, secid: str, limit: int) -> tuple[str | None, pd.DataFrame]:
        date, rows = self.client.klines(secid, limit)
        parsed = []
        for row in rows:
            parts = row.split(",")
            if len(parts) >= 11:
                parsed.append([parts[0], *[safe_float(value) for value in parts[1:11]]])
        frame = pd.DataFrame(parsed, columns=COLUMNS)
        if not frame.empty:
            frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
            frame = frame.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
        return date, frame

