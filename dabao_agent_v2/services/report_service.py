"""Dabao stock report rendering."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import STORAGE_ROOT, ensure_storage


class StockReportService:
    def save(self, data_date: str, sectors: list[dict[str, Any]], stocks: list[dict[str, Any]], narratives: dict[str, dict[str, str]]) -> Path:
        ensure_storage()
        lines = ["# 大宝 A股研究报告", "", "## 数据日期", "", data_date or "数据不足", "", "## 市场概况", "", f"本次共有 {len(stocks)} 只股票达到当前策略最低分数。", "", "## 强势板块", ""]
        lines.extend([f"- {s['sector_name']}：强度 {s['score']}/100，涨跌 {s['change_pct']:+.2f}%" for s in sectors] or ["- 数据不足"])
        lines.extend(["", "## Top 候选股票", ""])
        for rank, stock in enumerate(stocks, 1):
            narrative = narratives.get(stock["code"], {})
            lines.extend([
                f"### {rank}. {stock['name']} {stock['code']}", "",
                f"- 所属板块：{stock['sector']}", f"- 当前价格：{stock['price']:.2f}", f"- 涨跌幅：{stock['change_pct']:+.2f}%",
                f"- 综合评分：{stock['total_score']}/100", f"- 板块评分：{stock['sector_score']}/25",
                f"- 放量评分：{stock['volume_score']}/20", f"- 突破评分：{stock['breakout_score']}/20",
                f"- 低位评分：{stock['low_position_score']}/15", f"- 个股强度评分：{stock['strength_score']}/10",
                f"- 风险评分：{stock['risk_score']}/10", "",
                f"入选原因：{narrative.get('selection_reason') or '；'.join(stock['selection_reasons'])}", "",
                f"风险：{narrative.get('risk') or '；'.join(stock['risk_factors'])}", "",
                f"支撑位：{stock['support']:.2f}（Python 算法）", "", f"压力位：{stock['resistance']:.2f}（Python 算法）", "",
            ])
        lines.extend(["## 风险提示", "", "本报告仅用于市场研究与策略测试，不构成投资建议。", ""])
        path = STORAGE_ROOT / "reports" / f"stock_report_{datetime.now():%Y%m%d_%H%M%S}.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

