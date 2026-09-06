"""Chat and attachment controls."""

from typing import Any
import streamlit as st


def render_chat(messages: list[dict[str, str]], running: bool) -> tuple[str | None, Any | None, bool]:
    st.subheader("和大宝对话")
    for message in messages[-10:]:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    uploaded = st.file_uploader("Excel / CSV（可选）", type=["xlsx", "xlsm", "csv"], disabled=running)
    quick = st.button("🚀 开始选股", type="primary", use_container_width=True, disabled=running)
    command = st.chat_input("开始选股 / 分析600xxx / 搜索资料 / 整理Excel", disabled=running)
    return ("开始选股" if quick else command), uploaded, quick

