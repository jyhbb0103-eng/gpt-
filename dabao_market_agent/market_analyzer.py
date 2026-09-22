"""确定性的市场判断与评分逻辑。DeepSeek 不参与本文件的计算。"""

from __future__ import annotations

from typing import Any

from config import setup_logging


logger = setup_logging()


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _ratio(a: Any, b: Any) -> float | None:
    denominator = _number(b)
    return _number(a) / denominator if denominator > 0 else None


def _index_component(indexes: dict[str, dict[str, Any]]) -> tuple[int, str, list[str]]:
    if not indexes:
        return 12, "中性", ["主要指数数据缺失，指数维度按中性处理"]
    changes = [_number(v.get("change_pct")) for v in indexes.values() if v.get("change_pct") is not None]
    ma_flags = [
        v.get(f"above_ma{window}")
        for v in indexes.values()
        for window in (5, 10, 20)
        if v.get(f"above_ma{window}") is not None
    ]
    average_change = sum(changes) / len(changes) if changes else 0
    positive_ratio = sum(x > 0 for x in changes) / len(changes) if changes else 0.5
    above_ma_ratio = sum(bool(x) for x in ma_flags) / len(ma_flags) if ma_flags else 0.5
    raw = 12.5 + average_change * 3.0 + (positive_ratio - 0.5) * 8 + (above_ma_ratio - 0.5) * 10
    score = round(max(0, min(25, raw)))
    label = "偏强" if score >= 17 else ("偏弱" if score <= 9 else "中性")
    reason = f"主要指数平均涨跌幅 {average_change:+.2f}%，均线之上的比例 {above_ma_ratio:.0%}"
    return score, label, [reason]


def _breadth_component(market: dict[str, Any]) -> tuple[int, str, list[str]]:
    up, down = _number(market.get("up_count")), _number(market.get("down_count"))
    active = up + down
    if active <= 0:
        return 12, "一般", ["涨跌家数缺失，赚钱效应按一般处理"]
    up_ratio = up / active
    score = round(max(0, min(25, up_ratio * 25)))
    if up_ratio >= 0.68:
        label = "强"
    elif up_ratio >= 0.58:
        label = "较强"
    elif up_ratio >= 0.45:
        label = "一般"
    elif up_ratio >= 0.35:
        label = "较弱"
    else:
        label = "弱"
    return score, label, [f"上涨 {int(up)} 家、下跌 {int(down)} 家，上涨占比 {up_ratio:.0%}"]


def _volume_component(turnover: dict[str, Any]) -> tuple[int, str, list[str]]:
    today = turnover.get("today")
    yesterday_ratio = _ratio(today, turnover.get("yesterday"))
    average_ratio = _ratio(today, turnover.get("average_5d"))
    ratios = [x for x in (yesterday_ratio, average_ratio) if x is not None]
    if not ratios:
        return 10, "正常", ["可比成交额缺失，成交量维度按正常处理"]
    ratio = sum(ratios) / len(ratios)
    if ratio >= 1.18:
        return 20, "明显放量", [f"成交额约为可比基准的 {ratio:.0%}"]
    if ratio >= 1.05:
        return 16, "温和放量", [f"成交额约为可比基准的 {ratio:.0%}"]
    if ratio >= 0.90:
        return 12, "正常", [f"成交额约为可比基准的 {ratio:.0%}"]
    return max(0, round(ratio * 10)), "缩量", [f"成交额约为可比基准的 {ratio:.0%}"]


def _emotion_component(market: dict[str, Any]) -> tuple[int, str, list[str]]:
    limit_up = market.get("limit_up_count")
    limit_down = market.get("limit_down_count")
    if limit_up is None or limit_down is None:
        return 10, "中性", ["涨跌停数据缺失，短线情绪按中性处理"]
    up, down = _number(limit_up), _number(limit_down)
    net = up - down * 1.5
    score = round(max(0, min(20, 10 + net / 6)))
    if score >= 17:
        label = "强势"
    elif score >= 13:
        label = "偏强"
    elif score >= 8:
        label = "中性"
    elif score >= 4:
        label = "偏弱"
    else:
        label = "弱势"
    return score, label, [f"涨停 {int(up)} 家、跌停 {int(down)} 家"]


def _risk_component(data: dict[str, Any]) -> tuple[int, list[str]]:
    market = data.get("market", {})
    indexes = data.get("indexes", {})
    score = 10
    risks: list[str] = []
    down_limits = _number(market.get("limit_down_count"))
    if down_limits >= 15:
        score -= 4
        risks.append("跌停数量较多，极端风险正在扩散")
    elif down_limits >= 6:
        score -= 2
        risks.append("跌停数量不低，需防范弱势股风险")
    changes = [_number(x.get("change_pct")) for x in indexes.values() if x.get("change_pct") is not None]
    if changes and max(changes) - min(changes) >= 2.0:
        score -= 2
        risks.append("主要指数分化较大，市场一致性不足")
    if data.get("is_partial"):
        score -= 2
        risks.append("部分数据缺失或使用降级数据，本次判断可信度下降")
    turnover = data.get("turnover", {})
    avg_ratio = _ratio(turnover.get("today"), turnover.get("average_5d"))
    if avg_ratio is not None and avg_ratio < 0.8:
        score -= 2
        risks.append("成交额显著低于近5日水平，行情持续性可能不足")
    if not risks:
        risks.append("未发现突出的系统性风险信号，但仍需防范盘中波动")
    return max(0, score), risks


def environment_from_score(score: int) -> str:
    if score >= 80:
        return "强势"
    if score >= 65:
        return "震荡偏强"
    if score >= 50:
        return "震荡"
    if score >= 35:
        return "震荡偏弱"
    return "弱势"


def advice_from_score(score: int) -> str:
    if score >= 80:
        return "可以积极关注"
    if score >= 65:
        return "可以参与，但注意控制仓位"
    if score >= 50:
        return "谨慎参与"
    if score >= 35:
        return "以观察为主"
    return "风险较高，优先控制风险"


def analyze_market(data: dict[str, Any]) -> dict[str, Any]:
    logger.info("开始市场分析")
    index_score, index_label, index_reasons = _index_component(data.get("indexes", {}))
    breadth_score, breadth_label, breadth_reasons = _breadth_component(data.get("market", {}))
    volume_score, volume_label, volume_reasons = _volume_component(data.get("turnover", {}))
    emotion_score, emotion_label, emotion_reasons = _emotion_component(data.get("market", {}))
    risk_score, risks = _risk_component(data)

    components = {
        "指数趋势": {"score": index_score, "max": 25},
        "涨跌家数": {"score": breadth_score, "max": 25},
        "成交量": {"score": volume_score, "max": 20},
        "涨跌停情绪": {"score": emotion_score, "max": 20},
        "风险因素": {"score": risk_score, "max": 10},
    }
    score = int(sum(item["score"] for item in components.values()))
    reasons = index_reasons + volume_reasons + breadth_reasons + emotion_reasons
    result = {
        "score": score,
        "environment": environment_from_score(score),
        "index_trend": index_label,
        "volume_state": volume_label,
        "money_effect": breadth_label,
        "short_term_emotion": emotion_label,
        "advice_level": advice_from_score(score),
        "components": components,
        "main_reasons": reasons,
        "risks": risks,
    }
    logger.info("市场分析完成：%s分，%s", score, result["environment"])
    return result
