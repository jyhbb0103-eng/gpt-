"""Streamlit 主界面。"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from config import LOG_FILE, setup_logging
from data_service import fetch_all_market_data
from llm_service import generate_explanation
from market_analyzer import analyze_market


logger = setup_logging()
logger.info("程序启动")

st.set_page_config(page_title="大宝 · A股市场分析", page_icon="📈", layout="wide")
st.markdown(
    """
    <style>
    .stButton > button {width:100%; height:3.5rem; font-size:1.2rem; font-weight:700;}
    .result-card {padding:1rem 1.2rem; border:1px solid #e5e7eb; border-radius:12px; background:#fafafa;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("大宝 · A股市场分析")
st.caption("点击一次，快速判断今日市场环境")
st.info("本工具只分析整体市场环境，不选股、不交易、不保证收益。")


def _format_yi(value):
    return "数据缺失" if value is None else f"{value / 100_000_000:,.0f} 亿元"


def _run_analysis():
    progress = st.progress(5, text="正在获取市场数据……")
    data = fetch_all_market_data()
    progress.progress(55, text="正在分析市场环境……")
    analysis = analyze_market(data)
    progress.progress(78, text="正在生成分析报告……")
    explanation = generate_explanation(data, analysis)
    progress.progress(100, text="分析完成")
    logger.info("分析结束")
    return data, analysis, explanation


if st.button("开始分析今日A股", type="primary", use_container_width=True):
    try:
        st.session_state["market_result"] = _run_analysis()
    except Exception as exc:
        logger.exception("完整分析流程失败：%s", exc)
        st.error(f"分析暂时失败：{exc}")
        st.caption(f"请查看日志：{LOG_FILE}")


if "market_result" in st.session_state:
    data, analysis, explanation = st.session_state["market_result"]
    if data.get("is_partial"):
        st.warning("部分市场数据暂时无法获取，本次判断仅供参考。")

    st.header("今日A股市场分析")
    st.subheader("区域1：市场结论")
    col1, col2, col3 = st.columns(3)
    col1.metric("市场环境", analysis["environment"])
    col2.metric("市场温度", f"{analysis['score']} / 100")
    col3.metric("指数环境", analysis["index_trend"])
    col4, col5, col6 = st.columns(3)
    col4.metric("成交量", analysis["volume_state"])
    col5.metric("赚钱效应", analysis["money_effect"])
    col6.metric("短线情绪", analysis["short_term_emotion"])

    st.subheader("区域2：投资环境建议")
    st.success(f"**{analysis['advice_level']}**")
    st.write(explanation["summary"])
    st.write(explanation["advice_explanation"])

    st.subheader("区域3：详细数据和分析")
    left, right = st.columns(2)
    with left:
        st.markdown("#### 主要依据")
        for index, reason in enumerate(explanation["main_reasons"], 1):
            st.write(f"{index}. {reason}")
    with right:
        st.markdown("#### 风险提示")
        for index, risk in enumerate(explanation["risks"], 1):
            st.write(f"{index}. {risk}")

    index_rows = []
    for name, item in data.get("indexes", {}).items():
        index_rows.append({
            "指数": name,
            "涨跌幅": None if item.get("change_pct") is None else f"{item['change_pct']:+.2f}%",
            "开盘": item.get("open"), "最高": item.get("high"), "最低": item.get("low"),
            "当前/收盘": item.get("close"), "成交额": _format_yi(item.get("amount")),
            "MA5": "上方" if item.get("above_ma5") else "下方",
            "MA10": "上方" if item.get("above_ma10") else "下方",
            "MA20": "上方" if item.get("above_ma20") else "下方",
        })
    if index_rows:
        st.markdown("#### 主要指数")
        st.dataframe(pd.DataFrame(index_rows), use_container_width=True, hide_index=True)

    market = data.get("market", {})
    turnover = data.get("turnover", {})
    st.markdown("#### 全市场数据")
    st.write(
        f"上涨 **{market.get('up_count', '缺失')}** 家 · "
        f"下跌 **{market.get('down_count', '缺失')}** 家 · "
        f"平盘 **{market.get('flat_count', '缺失')}** 家 · "
        f"涨停 **{market.get('limit_up_count', '缺失')}** 家 · "
        f"跌停 **{market.get('limit_down_count', '缺失')}** 家"
    )
    st.write(
        f"今日成交额：**{_format_yi(turnover.get('today'))}**　"
        f"昨日成交额：**{_format_yi(turnover.get('yesterday'))}**　"
        f"近5日均额：**{_format_yi(turnover.get('average_5d'))}**"
    )
    st.caption(f"涨跌停数据来源：{market.get('limit_count_source', '数据缺失')}")

    with st.expander("查看评分明细与缺失数据"):
        st.json(analysis["components"])
        if data.get("missing_or_degraded"):
            for message in data["missing_or_degraded"]:
                st.write(f"- {message}")
        if explanation.get("llm_error"):
            st.write(f"DeepSeek说明：{explanation['llm_error']}")
        st.caption(f"日志文件：{LOG_FILE}")
