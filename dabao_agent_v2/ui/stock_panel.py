"""Stock and research result panels."""

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


def render_stock_data(data: dict[str, Any]) -> None:
    sectors, stocks = data.get("sectors", []), data.get("stocks", [])
    if sectors:
        st.subheader("强势板块")
        frame = pd.DataFrame(sectors).rename(columns={"sector_name": "板块", "score": "强度", "change_pct": "涨幅%", "up_ratio": "上涨比例"})
        cols = [col for col in ("板块", "强度", "涨幅%", "上涨比例") if col in frame]
        st.dataframe(frame[cols], hide_index=True, use_container_width=True)
    if stocks:
        st.subheader("候选股票排行榜")
        rows = [{"排名": i, "代码": s["code"], "名称": s["name"], "板块": s["sector"], "现价": s["price"], "涨幅%": s["change_pct"], "综合": s["total_score"], "板块分": s["sector_score"], "放量": s["volume_score"], "突破": s["breakout_score"], "低位": s["low_position_score"], "强度": s["strength_score"], "风险": s["risk_score"]} for i, s in enumerate(stocks, 1)]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        options = [f"{s['code']} {s['name']}" for s in stocks]
        selected = st.selectbox("查看股票详情", options)
        stock = stocks[options.index(selected)]
        left, right = st.columns(2)
        left.markdown("**入选原因**\n\n" + "\n".join(f"- {x}" for x in stock["selection_reasons"]))
        right.markdown("**风险因素**\n\n" + "\n".join(f"- {x}" for x in stock["risk_factors"]))
        st.caption(f"支撑 {stock['support']:.2f} ｜ 压力 {stock['resistance']:.2f} ｜ MA20 {stock['ma20']:.2f} ｜ MA60 {stock['ma60']:.2f}")


def render_other_data(data: dict[str, Any]) -> None:
    if data.get("results"):
        st.subheader("资料搜索结果")
        for item in data["results"]:
            st.markdown(f"### [{item['title']}]({item['link']})\n{item['summary']}\n\n来源：`{item['source']}` ｜ 时间：{item['time']}")
    if data.get("sheets"):
        st.subheader("Excel 处理记录")
        st.dataframe(pd.DataFrame(data["sheets"]), hide_index=True, use_container_width=True)
    if data.get("test_run"):
        st.subheader("Python 工具测试")
        st.json(data["test_run"])


def render_download(path_text: str | None) -> None:
    if not path_text:
        return
    path = Path(path_text)
    if path.exists() and path.is_file():
        st.download_button("下载输出文件", path.read_bytes(), file_name=path.name, mime="application/octet-stream")

