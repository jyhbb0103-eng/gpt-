"""Main-board, suspension, anomaly and liquidity filters."""

import pandas as pd

from config import strategy_config as cfg


class StockFilters:
    MAIN_PREFIXES = ("600", "601", "603", "605", "000", "001", "002")

    def apply(self, frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return frame
        code_ok = frame["code"].astype(str).str.startswith(self.MAIN_PREFIXES)
        name_ok = ~frame["name"].str.upper().str.contains(r"\*?ST|退", regex=True, na=False)
        data_ok = (frame["price"] >= cfg.MIN_PRICE) & (frame["volume"] > 0) & (frame["high"] >= frame["low"]) & (frame["low"] > 0)
        liquidity = (frame["amount"] >= cfg.MIN_AMOUNT) & frame["turnover_rate"].between(cfg.MIN_TURNOVER_RATE, cfg.MAX_TURNOVER_RATE)
        return frame[code_ok & name_ok & data_ok & liquidity].drop_duplicates("code").reset_index(drop=True)

