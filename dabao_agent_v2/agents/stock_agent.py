"""A-share screening, sector scan and single-stock research Agent."""

from __future__ import annotations

import json
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Any

import pandas as pd

from config import strategy_config as cfg
from core.cancellation import CancellationToken
from llm.deepseek_client import DeepSeekClient
from services.logging_service import TaskLogger
from services.report_service import StockReportService
from stock.eastmoney_client import EastmoneyClient
from stock.history_data import HistoryData
from stock.market_data import MarketData
from stock.scoring import StockScoring
from stock.sector_data import SectorData
from strategies.strong_sector import StrongSectorStrategy


class StockAgent:
    def __init__(self, logger: TaskLogger, cancellation: CancellationToken, llm: DeepSeekClient) -> None:
        self.log, self.cancellation, self.llm = logger, cancellation, llm

    def scan_sectors(self) -> dict[str, Any]:
        with EastmoneyClient(self.log, self.cancellation) as client:
            sectors = StrongSectorStrategy().rank(SectorData(client).fetch_sectors())
        self.log.info(f"找到 {len(sectors)} 个强势板块")
        return {"sectors": sectors}

    def screen(self) -> dict[str, Any]:
        with EastmoneyClient(self.log, self.cancellation) as client:
            self.log.info("正在获取完整沪深主板行情")
            market = pd.DataFrame()
            try:
                market = MarketData(client).fetch()
                self.log.info(f"获取到 {len(market)} 只通过基础过滤的主板股票")
            except Exception as exc:
                self.log.error(f"全市场接口暂不可用，将从强势板块成分行情重建候选池：{exc}")
            self.cancellation.raise_if_cancelled()
            sector_service = SectorData(client)
            sectors = StrongSectorStrategy().rank(sector_service.fetch_sectors())
            self.log.info(f"找到 {len(sectors)} 个强势板块")
            sector_map, sector_frames = self._sector_members(sector_service, sectors)
            if market.empty and sector_frames:
                market = pd.concat(sector_frames, ignore_index=True).drop_duplicates("code")
                self.log.info(f"降级候选池重建成功，共 {len(market)} 只强势板块主板股票")
            if market.empty:
                raise RuntimeError("全市场与强势板块成分行情均不可用，请检查网络后重试")
            candidates = market[market["code"].isin(sector_map)].copy()
            if candidates.empty:
                raise RuntimeError("强势板块内没有通过基础过滤的股票")
            candidates["sector"] = candidates["code"].map(lambda code: sector_map[code]["sector_name"])
            candidates["sector_raw_score"] = candidates["code"].map(lambda code: sector_map[code]["score"])
            candidates["sector_change_pct"] = candidates["code"].map(lambda code: sector_map[code]["change_pct"])
            candidates["pre_score"] = candidates["sector_raw_score"] * .55 + candidates["change_pct"].clip(-5, 10) * 2 + candidates["volume_ratio_snapshot"].clip(0, 4) * 3 + candidates["amount"].rank(pct=True) * 10
            candidates = candidates.nlargest(cfg.MAX_HISTORY_CANDIDATES, "pre_score")
            self.log.info(f"初筛剩余 {len(candidates)} 只")
            history_service = HistoryData(client)
            data_date, index = history_service.fetch_index(cfg.HISTORY_DAYS)
            index_change = float(index["change_pct"].iloc[-1]) if not index.empty else 0.0
            histories = self._histories(history_service, candidates["code"].tolist())
            scored = self._score_candidates(candidates, histories, index_change)
            top = [item for item in scored if item["total_score"] >= cfg.MIN_FINAL_SCORE][:cfg.TOP_N]
            self.log.info(f"输出 {len(top)} 只候选股票" if len(top) < cfg.TOP_N else f"输出 Top {cfg.TOP_N}")
            narratives = self._explain(top)
            report = StockReportService().save(data_date or "未知", sectors, top, narratives)
        return {"data_date": data_date, "sectors": sectors, "stocks": top, "narratives": narratives, "report_path": str(report)}

    def analyze(self, code: str) -> dict[str, Any]:
        with EastmoneyClient(self.log, self.cancellation) as client:
            stock = MarketData(client).fetch_one(code)
            date, history = HistoryData(client).fetch_stock(code, cfg.HISTORY_DAYS)
            _, index = HistoryData(client).fetch_index(cfg.HISTORY_DAYS)
            if len(history) < cfg.MIN_HISTORY_DAYS:
                raise RuntimeError("该股票历史数据不足 60 个交易日")
            stock["sector"] = stock.get("industry") or "未知"
            result = StockScoring().score(stock, history, {"sector_score": 50, "sector_change_pct": 0, "index_change_pct": float(index["change_pct"].iloc[-1]) if not index.empty else 0})
            narratives = self._explain([result])
            report = StockReportService().save(date or "未知", [], [result], narratives)
        return {"data_date": date, "sectors": [], "stocks": [result], "narratives": narratives, "report_path": str(report)}

    def _sector_members(self, service: SectorData, sectors: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[pd.DataFrame]]:
        mapping: dict[str, dict[str, Any]] = {}
        frames: list[pd.DataFrame] = []
        with ThreadPoolExecutor(max_workers=6, thread_name_prefix="sector-members") as executor:
            futures = {executor.submit(service.constituents, str(sector["sector_code"])): sector for sector in sectors}
            for future in as_completed(futures):
                self.cancellation.raise_if_cancelled()
                sector = futures[future]
                try:
                    frame = future.result()
                    frames.append(frame)
                    for code in frame["code"].astype(str) if not frame.empty else []:
                        mapping.setdefault(code, sector)
                except Exception as exc:
                    self.log.error(f"板块 {sector['sector_name']} 成分股失败，已跳过：{exc}")
        return mapping, frames

    def _histories(self, service: HistoryData, codes: list[str]) -> dict[str, pd.DataFrame]:
        result: dict[str, pd.DataFrame] = {}
        with ThreadPoolExecutor(max_workers=cfg.HISTORY_WORKERS, thread_name_prefix="history") as executor:
            futures: dict[Future, str] = {executor.submit(service.fetch_stock, code, cfg.HISTORY_DAYS): code for code in codes}
            for future in as_completed(futures):
                self.cancellation.raise_if_cancelled()
                code = futures[future]
                try:
                    _, frame = future.result()
                    if not frame.empty: result[code] = frame
                except Exception as exc:
                    self.log.error(f"股票 {code} 历史数据失败，已跳过：{exc}")
        self.log.info(f"成功获取 {len(result)} 只股票历史数据")
        return result

    def _score_candidates(self, candidates: pd.DataFrame, histories: dict[str, pd.DataFrame], index_change: float) -> list[dict[str, Any]]:
        scorer, output = StockScoring(), []
        for stock in candidates.to_dict("records"):
            self.cancellation.raise_if_cancelled()
            history = histories.get(stock["code"])
            if history is None or len(history) < cfg.MIN_HISTORY_DAYS: continue
            context = {"sector_score": stock.pop("sector_raw_score"), "sector_change_pct": stock.pop("sector_change_pct"), "index_change_pct": index_change}
            stock.pop("pre_score", None)
            output.append(scorer.score(stock, history, context))
        return sorted(output, key=lambda item: item["total_score"], reverse=True)

    def _explain(self, stocks: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
        if not stocks: return {}
        compact = [{key: item[key] for key in ("code", "name", "sector", "price", "change_pct", "total_score", "sector_score", "volume_score", "breakout_score", "low_position_score", "strength_score", "risk_score", "support", "resistance", "selection_reasons", "risk_factors")} for item in stocks]
        system = "只允许根据输入数据分析；数据不足时明确说明；禁止补全行情数字、禁止买卖指令。返回JSON对象，键为股票代码，值含selection_reason和risk。"
        try:
            parsed = json.loads(self.llm.chat([{"role": "system", "content": system}, {"role": "user", "content": json.dumps(compact, ensure_ascii=False)}], json_mode=True))
            return {str(key): value for key, value in parsed.items() if isinstance(value, dict)}
        except Exception as exc:
            self.log.error(f"DeepSeek 暂不可用，报告降级为纯算法解释：{exc}")
            return {}
