"""DeepSeek 解释层。模型只能解释数据，不计算或修改市场分数。"""

from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

from config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    LLM_TIMEOUT_SECONDS,
    setup_logging,
)


logger = setup_logging()


def _fallback(analysis: dict[str, Any], error: str | None = None) -> dict[str, Any]:
    explanation = (
        f"当前市场被程序评定为{analysis['environment']}，市场温度为"
        f"{analysis['score']}分。判断主要来自指数、涨跌家数、成交量和涨跌停情绪。"
    )
    if error:
        explanation += " DeepSeek 暂时不可用，以上为程序生成的基础说明。"
    return {
        "summary": explanation,
        "main_reasons": analysis.get("main_reasons", [])[:5],
        "risks": analysis.get("risks", [])[:3],
        "advice_explanation": (
            f"建议等级：{analysis['advice_level']}。不预测个股，不盲目追高，"
            "根据市场强弱控制仓位并持续观察成交量。"
        ),
        "llm_error": error,
    }


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fenced:
        text = fenced.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
    return json.loads(text)


def generate_explanation(data: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    if not DEEPSEEK_API_KEY:
        logger.warning("未配置 DEEPSEEK_API_KEY，使用本地基础说明")
        return _fallback(analysis, "未配置 DEEPSEEK_API_KEY")

    payload = {"market_data": data, "fixed_analysis": analysis}
    system_prompt = """你是A股市场环境解释助手。Python程序已经完成所有计算和打分。
你不得修改分数、环境分类或建议等级，不得补全或猜测缺失数据，不推荐具体股票，
不预测必涨，不保证收益。只基于输入JSON写简洁中文说明。
只返回合法JSON，结构为：
{"summary":"不超过120字", "main_reasons":["最多5条"],
 "risks":["最多3条"], "advice_explanation":"不超过100字"}
若输入标记数据缺失，必须在summary中明确说明判断仅供参考。"""
    logger.info("开始调用DeepSeek")
    try:
        client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            timeout=LLM_TIMEOUT_SECONDS,
            max_retries=1,
        )
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            temperature=0.1,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)},
            ],
        )
        content = response.choices[0].message.content or ""
        parsed = _extract_json(content)
        # 固定字段始终取 Python 分析结果，防止模型越权修改。
        parsed["main_reasons"] = list(parsed.get("main_reasons") or analysis["main_reasons"])[:5]
        parsed["risks"] = list(parsed.get("risks") or analysis["risks"])[:3]
        parsed["llm_error"] = None
        logger.info("DeepSeek返回成功")
        return parsed
    except Exception as exc:
        logger.exception("DeepSeek调用失败：%s", exc)
        return _fallback(analysis, str(exc))
