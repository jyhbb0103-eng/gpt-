import numpy as np
import pandas as pd

from stock.scoring import StockScoring


def history() -> pd.DataFrame:
    close = np.concatenate([np.linspace(10, 8.5, 70), np.linspace(8.5, 9.2, 59), [9.8]])
    volume = np.full(130, 1_000_000.0); volume[-1] = 2_000_000
    return pd.DataFrame({"date": pd.date_range("2026-01-01", periods=130, freq="B"), "open": close*.99, "close": close, "high": close*1.01, "low": close*.98, "volume": volume, "amount": close*volume, "amplitude": 3, "change_pct": pd.Series(close).pct_change().fillna(0)*100, "change": 0, "turnover_rate": 2})


def test_stock_score_is_bounded() -> None:
    stock = {"code": "600000", "name": "测试", "sector": "测试板块", "price": 9.8, "change_pct": 4, "amount": 600_000_000, "turnover_rate": 3}
    result = StockScoring().score(stock, history(), {"sector_score": 80, "sector_change_pct": 2, "index_change_pct": .5})
    assert 0 <= result["total_score"] <= 100
    assert result["support"] > 0 and result["resistance"] > 0

