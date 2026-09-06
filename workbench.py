"""Streamlit visual workbench for the DeepSeek agent."""

from __future__ import annotations

import os
from typing import Any

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from agent import BASE_DIR, SYSTEM_PROMPT, load_memory, run_agent, save_memory
from computer_tools import COMPUTER_TOOL_DEFINITIONS
from tools import TOOL_DEFINITIONS, list_notes, read_note


load_dotenv(BASE_DIR / ".env")

st.set_page_config(
    page_title="DeepSeek 智能体工作台",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.6rem; max-width: 1500px;}
    [data-testid="stSidebar"] {border-right: 1px solid rgba(128,128,128,.18);}
    .hero {padding: 1rem 1.2rem; border-radius: 16px; margin-bottom: 1rem;
           background: linear-gradient(120deg, rgba(32,110,255,.16), rgba(120,50,255,.10));
           border: 1px solid rgba(90,130,255,.22);}
    .hero h1 {font-size: 1.65rem; margin: 0 0 .25rem 0;}
    .hero p {margin: 0; opacity: .72;}
    .status-ok {color: #20b26b; font-weight: 650;}
    </style>
    """,
    unsafe_allow_html=True,
)


TOOL_LABELS = {
    "get_current_time": "当前时间",
    "calculate": "安全计算器",
    "write_note": "保存笔记",
    "read_note": "读取笔记",
    "list_notes": "笔记列表",
    "open_application": "打开应用",
    "open_website": "打开网页",
    "search_web": "网页搜索",
    "type_text": "输入文字",
    "press_keys": "键盘操作",
    "click_mouse": "鼠标点击",
    "wait_for_screen": "等待加载",
    "take_screenshot": "屏幕截图",
}


def reset_conversation() -> None:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    st.session_state.tool_events = []
    save_memory(st.session_state.messages)


if "messages" not in st.session_state:
    st.session_state.messages = load_memory()
if "tool_events" not in st.session_state:
    st.session_state.tool_events = []


with st.sidebar:
    st.title("⚙️ 控制中心")
    api_key = st.text_input(
        "DeepSeek API Key",
        value=os.getenv("DEEPSEEK_API_KEY", ""),
        type="password",
        help="只在当前程序中使用，不会被保存到对话记忆。",
    )
    model = st.selectbox(
        "模型",
        ["deepseek-v4-flash", "deepseek-v4-pro"],
        index=0,
        help="Flash 更快更省，Pro 更适合复杂任务。",
    )
    st.divider()
    st.subheader("智能体工具")
    enabled_names: list[str] = []
    for definition in TOOL_DEFINITIONS:
        name = definition["function"]["name"]
        if st.toggle(TOOL_LABELS[name], value=True, key=f"tool_{name}"):
            enabled_names.append(name)

    st.divider()
    computer_control = st.toggle(
        "🖥️ 允许控制本机",
        value=False,
        help="开启后，智能体才能操作鼠标、键盘、浏览器和允许列表中的应用。",
    )
    if computer_control:
        st.warning("执行期间请观察屏幕。紧急停止：把鼠标快速移到屏幕左上角。")
        for definition in COMPUTER_TOOL_DEFINITIONS:
            name = definition["function"]["name"]
            if st.checkbox(TOOL_LABELS[name], value=True, key=f"computer_{name}"):
                enabled_names.append(name)

    st.divider()
    memory_turns = sum(1 for item in st.session_state.messages if item["role"] == "user")
    st.metric("已记忆对话", f"{memory_turns} 轮")
    if st.button("清空对话记忆", use_container_width=True):
        reset_conversation()
        st.rerun()

    api_ready = bool(api_key and not api_key.startswith("在这里"))
    if api_ready:
        st.markdown('<span class="status-ok">● API Key 已就绪</span>', unsafe_allow_html=True)
    else:
        st.warning("请先填写 DeepSeek API Key")


st.markdown(
    """
    <div class="hero">
      <h1>🤖 DeepSeek 智能体工作台</h1>
      <p>和智能体对话，观察工具执行过程，并管理它保存的笔记。</p>
    </div>
    """,
    unsafe_allow_html=True,
)

chat_tab, activity_tab, notes_tab = st.tabs(["💬 对话", "🛠️ 执行记录", "📝 笔记"])

with chat_tab:
    for message in st.session_state.messages:
        if message["role"] not in {"user", "assistant"}:
            continue
        if message["role"] == "assistant" and not message.get("content"):
            continue
        with st.chat_message(message["role"]):
            st.markdown(message.get("content") or "")

    prompt = st.chat_input("给智能体一个任务，例如：计算收入并保存为本月总结")
    if prompt:
        if not api_ready:
            st.error("请先在左侧填写 DeepSeek API Key。")
            st.stop()

        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        available_tools = TOOL_DEFINITIONS + COMPUTER_TOOL_DEFINITIONS
        selected_tools = [item for item in available_tools if item["function"]["name"] in enabled_names]

        def record_tool(name: str, arguments: dict[str, Any], result: dict[str, Any]) -> None:
            st.session_state.tool_events.append(
                {"name": name, "arguments": arguments, "result": result}
            )

        with st.chat_message("assistant"):
            with st.status("智能体正在思考和执行工具……", expanded=True) as status:
                try:
                    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
                    answer = run_agent(
                        client,
                        model,
                        st.session_state.messages,
                        tool_definitions=selected_tools,
                        on_tool_event=record_tool,
                    )
                    status.update(label="任务完成", state="complete", expanded=False)
                    st.markdown(answer)
                except Exception as exc:
                    answer = f"请求失败：{exc}"
                    status.update(label="执行失败", state="error", expanded=True)
                    st.error(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                save_memory(st.session_state.messages)

with activity_tab:
    if not st.session_state.tool_events:
        st.info("智能体调用工具后，这里会显示工具名称、参数和执行结果。")
    for index, event in enumerate(reversed(st.session_state.tool_events), start=1):
        label = TOOL_LABELS.get(event["name"], event["name"])
        with st.expander(f"{index}. {label}", expanded=index == 1):
            st.caption("调用参数")
            st.json(event["arguments"])
            st.caption("执行结果")
            st.json(event["result"])

with notes_tab:
    notes = list_notes()["notes"]
    if not notes:
        st.info("还没有笔记。你可以在对话中让智能体保存一篇笔记。")
    else:
        selected_note = st.selectbox("选择笔记", notes)
        note = read_note(selected_note)
        st.markdown(note.get("content", ""))
