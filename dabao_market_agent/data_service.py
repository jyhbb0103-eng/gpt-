"""A股市场数据获取层。

本文件只负责拿数据和整理数据，不判断市场强弱。每个外部接口都独立捕获异常，
单个数据源失败不会导致整个分析流程崩溃。
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime, timedelta
from typing import Any, Callable
from zoneinfo import ZoneInfo

import akshare as ak
import pandas as pd

from config import DATA_TIMEOUT_SECONDS, INDEXES, setup_logging


logger = setup_logging()
CHINA_TZ = ZoneInfo("Asia/Shanghai")


def _safe_float(value: Any) -> float | None:
    try:
        number = float(value)
        return None if pd.isna(number) else number
    except (TypeError, ValueError):
        return None


def _call_with_timeout(name: str, func: Callable[[], Any]) -> Any:
    """限制单个 AkShare 调用的等待时间。超时后让主流程继续。"""
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"ak-{name}")
    future = executor.submit(func)
    try:
        result = future.result(timeout=DATA_TIMEOUT_SECONDS)
        logger.info("数据接口成功：%s", name)
        return result
    except FutureTimeoutError as exc:
        future.cancel()
        logger.error("数据接口超时：%s（%s秒）", name, DATA_TIMEOUT_SECONDS)
        raise TimeoutError(f"{name} 获取超时") from exc
    except Exception as exc:
        logger.exception("数据接口失败：%s - %s", name, exc)
        raise
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _date_range() -> tuple[str, str]:
    today = datetime.now(CHINA_TZ).date()
    return (today - timedelta(days=50)).strftime("%Y%m%d"), today.strftime("%Y%m%d")


def _normalise_history(df: pd.DataFrame) -> pd.DataFrame:
    rename = {
        "日期": "date", "开盘": "open", "收盘": "close", "最高": "high",
        "最低": "low", "成交量": "volume", "成交额": "amount",
    }
    frame = df.rename(columns=rename).copy()
    for column in ("open", "close", "high", "low", "volume", "amount"):
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if "date" in frame:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame = frame.dropna(subset=["date"]).sort_values("date")
    return frame


def _fetch_index_history(symbol: str) -> pd.DataFrame:
    start_date, end_date = _date_range()
    try:
        return _normalise_history(
            _call_with_timeout(
                f"指数日线-东财-{symbol}",
                lambda: ak.stock_zh_index_daily_em(
                    symbol=symbol, start_date=start_date, end_date=end_date
                ),
            )
        )
    except Exception:
        # 腾讯接口作为指数日线备用源；amount 在该接口表示成交量，不能用于成交额统计。
        return _normalise_history(
            _call_with_timeout(
                f"指数日线-腾讯-{symbol}",
                lambda: ak.stock_zh_index_daily_tx(
                    symbol=symbol.replace("csi", "sh"),
                    start_date=start_date,
                    end_date=end_date,
                ),
            )
        )


def _fetch_index_spot() -> tuple[dict[str, dict[str, Any]], list[str]]:
    """获取指数实时快照；东财失败时自动切换到新浪。"""
    wanted = set(INDEXES)
    errors: list[str] = []
    try:
        frame = _call_with_timeout(
            "指数实时-东财",
            lambda: ak.stock_zh_index_spot_em(symbol="沪深重要指数"),
        )
    except Exception as first_exc:
        errors.append(f"东财指数实时接口失败：{first_exc}")
        try:
            frame = _call_with_timeout("指数实时-新浪", ak.stock_zh_index_spot_sina)
        except Exception as second_exc:
            errors.append(f"新浪指数实时接口失败：{second_exc}")
            return {}, errors

    result: dict[str, dict[str, Any]] = {}
    for _, row in frame.iterrows():
        name = str(row.get("名称", "")).strip()
        if name not in wanted:
            continue
        result[name] = {
            "open": _safe_float(row.get("今开")),
            "high": _safe_float(row.get("最高")),
            "low": _safe_float(row.get("最低")),
            "close": _safe_float(row.get("最新价")),
            "change_pct": _safe_float(row.get("涨跌幅")),
            "amount": _safe_float(row.get("成交额")),
        }
    if not result:
        errors.append("指数实时接口返回结果中未找到四大指数")
    return result, errors


def fetch_indexes() -> tuple[dict[str, dict[str, Any]], dict[str, pd.DataFrame], list[str]]:
    """获取四大指数及均线。实时接口失败时使用最新日线降级。"""
    spot_data, errors = _fetch_index_spot()
    histories: dict[str, pd.DataFrame] = {}
    indexes: dict[str, dict[str, Any]] = {}

    for name, symbol in INDEXES.items():
        try:
            history = _fetch_index_history(symbol)
            histories[name] = history
            if history.empty or "close" not in history:
                raise ValueError("指数日线为空")
            latest = history.iloc[-1]
            previous = history.iloc[-2] if len(history) >= 2 else latest
            close = _safe_float(latest.get("close"))
            previous_close = _safe_float(previous.get("close"))
            change_pct = None
            if close is not None and previous_close not in (None, 0):
                change_pct = (close / previous_close - 1) * 100
            item = {
                "symbol": symbol,
                "date": str(latest.get("date", ""))[:10],
                "open": _safe_float(latest.get("open")),
                "high": _safe_float(latest.get("high")),
                "low": _safe_float(latest.get("low")),
                "close": close,
                "change_pct": change_pct,
                "amount": _safe_float(latest.get("amount")),
            }
            # 交易时段优先使用实时快照；缺字段时保留最新日线值。
            for field, value in spot_data.get(name, {}).items():
                if value is not None:
                    item[field] = value

            closes = history["close"].dropna().copy()
            today_cn = datetime.now(CHINA_TZ).date()
            current_close = item.get("close")
            if current_close is not None and not history.empty:
                latest_date = history.iloc[-1].get("date")
                if pd.notna(latest_date) and latest_date.date() == today_cn:
                    closes.iloc[-1] = current_close
                else:
                    closes = pd.concat([closes, pd.Series([current_close])], ignore_index=True)
            for window in (5, 10, 20):
                ma = _safe_float(closes.tail(window).mean()) if len(closes) >= window else None
                item[f"ma{window}"] = ma
                item[f"above_ma{window}"] = (
                    close >= ma if close is not None and ma is not None else None
                )
            indexes[name] = item
        except Exception as exc:
            message = f"{name}数据获取失败：{exc}"
            errors.append(message)
            logger.error(message)

    return indexes, histories, errors


def _is_sh_sz_a_share(code: str) -> bool:
    code = str(code).zfill(6)
    return code.startswith(("600", "601", "603", "605", "688", "689", "000", "001", "002", "003", "300", "301"))


def _estimated_limit_counts(frame: pd.DataFrame) -> tuple[int, int]:
    """涨跌停池不可用时的保守估算；只作为降级数据。"""
    up = down = 0
    for _, row in frame.iterrows():
        code = str(row.get("代码", "")).zfill(6)
        name = str(row.get("名称", ""))
        pct = _safe_float(row.get("涨跌幅"))
        if pct is None:
            continue
        limit = 5.0 if "ST" in name.upper() else (20.0 if code.startswith(("300", "301", "688", "689")) else 10.0)
        if pct >= limit - 0.15:
            up += 1
        elif pct <= -limit + 0.15:
            down += 1
    return up, down


def fetch_market_breadth() -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    try:
        frame = _call_with_timeout("沪深京A股实时行情", ak.stock_zh_a_spot_em)
        frame = frame[frame["代码"].astype(str).map(_is_sh_sz_a_share)].copy()
        pct = pd.to_numeric(frame["涨跌幅"], errors="coerce")
        amount = pd.to_numeric(frame["成交额"], errors="coerce")
        breadth = {
            "up_count": int((pct > 0.001).sum()),
            "down_count": int((pct < -0.001).sum()),
            "flat_count": int((pct.abs() <= 0.001).sum()),
            "total_amount": _safe_float(amount.sum(min_count=1)),
            "sample_size": int(pct.notna().sum()),
            "limit_count_source": "涨跌停池",
        }
    except Exception as exc:
        return {}, [f"市场涨跌家数获取失败：{exc}"]

    trade_date = datetime.now(CHINA_TZ).strftime("%Y%m%d")
    limit_up = limit_down = None
    try:
        limit_up = len(_call_with_timeout("涨停股池", lambda: ak.stock_zt_pool_em(date=trade_date)))
    except Exception as exc:
        errors.append(f"涨停池获取失败：{exc}")
    try:
        limit_down = len(_call_with_timeout("跌停股池", lambda: ak.stock_zt_pool_dtgc_em(date=trade_date)))
    except Exception as exc:
        errors.append(f"跌停池获取失败：{exc}")

    if limit_up is None or limit_down is None:
        estimated_up, estimated_down = _estimated_limit_counts(frame)
        limit_up = estimated_up if limit_up is None else limit_up
        limit_down = estimated_down if limit_down is None else limit_down
        breadth["limit_count_source"] = "行情涨跌幅估算"

    breadth["limit_up_count"] = int(limit_up)
    breadth["limit_down_count"] = int(limit_down)
    return breadth, errors


def build_turnover(histories: dict[str, pd.DataFrame], spot_total: float | None) -> dict[str, Any]:
    """用沪、深指数成交额计算可比的今日/昨日/近5日成交额。"""
    sh = histories.get("上证指数")
    sz = histories.get("深证成指")
    if sh is None or sz is None or "amount" not in sh or "amount" not in sz:
        return {"today": spot_total, "yesterday": None, "average_5d": None}

    left = sh[["date", "amount"]].rename(columns={"amount": "sh_amount"})
    right = sz[["date", "amount"]].rename(columns={"amount": "sz_amount"})
    combined = left.merge(right, on="date", how="inner").dropna().sort_values("date")
    if combined.empty:
        return {"today": spot_total, "yesterday": None, "average_5d": None}
    combined["total"] = combined["sh_amount"] + combined["sz_amount"]
    today_cn = datetime.now(CHINA_TZ).date()
    today_rows = combined[combined["date"].dt.date == today_cn]
    past = combined[combined["date"].dt.date < today_cn]
    today_amount = _safe_float(today_rows.iloc[-1]["total"]) if not today_rows.empty else spot_total
    yesterday = _safe_float(past.iloc[-1]["total"]) if not past.empty else None
    average_5d = _safe_float(past.tail(5)["total"].mean()) if len(past) >= 1 else None
    return {"today": today_amount, "yesterday": yesterday, "average_5d": average_5d}


def fetch_all_market_data() -> dict[str, Any]:
    logger.info("开始获取数据")
    indexes, histories, index_errors = fetch_indexes()
    breadth, breadth_errors = fetch_market_breadth()
    turnover = build_turnover(histories, breadth.get("total_amount"))
    errors = index_errors + breadth_errors
    return {
        "generated_at": datetime.now(CHINA_TZ).isoformat(timespec="seconds"),
        "indexes": indexes,
        "market": breadth,
        "turnover": turnover,
        "missing_or_degraded": errors,
        "is_partial": bool(errors),
    }
