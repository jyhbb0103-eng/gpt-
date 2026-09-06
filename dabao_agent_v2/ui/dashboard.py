"""Non-blocking Streamlit dashboard."""

from __future__ import annotations

import queue
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from agents.orchestrator import OrchestratorAgent
from config.settings import STORAGE_ROOT, ensure_storage, get_settings
from core.cancellation import CancellationToken
from core.task_state import TaskResult, TaskState
from skills.skill_manager import SkillManager
from ui.chat_panel import render_chat
from ui.log_panel import render_logs
from ui.stock_panel import render_download, render_other_data, render_stock_data
from ui.task_panel import render_task


def _initialize() -> None:
    ensure_storage()
    defaults: dict[str, Any] = {
        "messages": [{"role": "assistant", "content": "你好，我是大宝。可以选股、分析股票、搜索资料、整理 Excel，或生成安全的 Python 小工具。"}],
        "task_state": TaskState.IDLE, "task_future": None, "task_result": None, "logs": [],
        "events": queue.Queue(), "cancel_token": CancellationToken(), "executor": ThreadPoolExecutor(max_workers=1, thread_name_prefix="dabao-task"),
    }
    for key, value in defaults.items():
        if key not in st.session_state: st.session_state[key] = value


def _drain() -> None:
    events: queue.Queue = st.session_state.events
    while True:
        try: kind, value = events.get_nowait()
        except queue.Empty: break
        if kind == "log": st.session_state.logs.append(f"[{datetime.now():%H:%M:%S}] {value}")
        elif kind == "state": st.session_state.task_state = value


def _save_upload(uploaded: Any | None) -> list[str]:
    if uploaded is None: return []
    safe_name = Path(uploaded.name).name
    target = STORAGE_ROOT / "uploads" / safe_name
    target.write_bytes(uploaded.getvalue())
    return [str(target)]


def _start(command: str, uploaded: Any | None) -> None:
    future: Future | None = st.session_state.task_future
    if future and not future.done():
        st.warning("已有任务正在运行，请等待或点击停止。")
        return
    st.session_state.task_result = None
    st.session_state.logs = []
    st.session_state.task_state = TaskState.IDLE
    st.session_state.events = queue.Queue()
    st.session_state.cancel_token = CancellationToken(threading.Event())
    st.session_state.messages.append({"role": "user", "content": command})
    attachments = _save_upload(uploaded)
    events = st.session_state.events
    agent = OrchestratorAgent(st.session_state.cancel_token, lambda msg: events.put(("log", msg)), lambda state: events.put(("state", state)))
    st.session_state.task_future = st.session_state.executor.submit(agent.execute, command, attachments)


def _collect() -> None:
    future: Future[TaskResult] | None = st.session_state.task_future
    if future and future.done() and st.session_state.task_result is None:
        result = future.result()
        st.session_state.task_result = result
        st.session_state.task_state = result.state
        st.session_state.messages.append({"role": "assistant", "content": result.message})


def render() -> None:
    st.set_page_config(page_title="大宝 · 本地 AI 助手", page_icon="🤖", layout="wide")
    _initialize(); _drain(); _collect()
    st.title("🤖 大宝 · 你的本地 AI 助手")
    st.caption("Dabao Agent 2.0 第一阶段 ｜ DeepSeek + Skill + Memory + 股票 + Research + Excel + Python Tool")
    if not get_settings().has_api_key:
        st.warning("未找到 DEEPSEEK_API_KEY，请复制 .env.example 为 .env，并填写 DeepSeek API Key。股票算法与 Excel 仍可运行，LLM 解释会降级。")
    future = st.session_state.task_future
    running = bool(future and not future.done())
    left, right = st.columns([1, 1.65], gap="large")
    with left:
        command, uploaded, _ = render_chat(st.session_state.messages, running)
        if command:
            _start(command, uploaded); st.rerun()
        if st.button("⏹ 停止任务", use_container_width=True, disabled=not running):
            st.session_state.cancel_token.cancel()
            st.session_state.logs.append(f"[{datetime.now():%H:%M:%S}] 已收到停止请求；当前网络请求将在 timeout 后退出")
            st.rerun()
    with right:
        render_task(st.session_state.task_state, SkillManager().stats())
        render_logs(st.session_state.logs, running)
    result: TaskResult | None = st.session_state.task_result
    if result:
        st.divider()
        if result.data.get("data_date"):
            st.info(f"数据日期：{result.data['data_date']}。非交易日自动使用最近交易日。")
        render_stock_data(result.data)
        render_other_data(result.data)
        if result.data.get("repeat_suggestion"): st.info(result.data["repeat_suggestion"])
        if result.data.get("stable_suggestion"):
            st.warning(result.data["stable_suggestion"])
            if st.button("确认升级为 stable"):
                manager = SkillManager()
                for name in result.data.get("stable_skills", []): manager.update_status(name, "stable")
                result.data.pop("stable_suggestion", None); result.data.pop("stable_skills", None)
                st.success("Skill 状态已升级。")
        if result.skill_candidate:
            st.warning("是否保存本次流程为新技能？")
            a, b = st.columns(2)
            if a.button("保存 Skill", type="primary"):
                path = SkillManager().save_confirmed_candidate(result.skill_candidate)
                result.skill_candidate = None
                st.success(f"Skill 已保存：{Path(path).name}")
            if b.button("不保存"):
                result.skill_candidate = None; st.rerun()
        render_download(result.report_path)
    if running:
        time.sleep(1); st.rerun()
