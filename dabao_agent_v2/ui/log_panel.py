"""Visible execution logs."""

import streamlit as st


def render_logs(logs: list[str], expanded: bool) -> None:
    with st.expander("执行日志", expanded=expanded):
        st.code("\n".join(logs[-400:]) or "等待任务……", language=None)

