"""Task state, steps and Skill status."""

import pandas as pd
import streamlit as st

from core.task_state import TaskState

ORDER = [TaskState.PLANNING, TaskState.MATCHING_SKILL, TaskState.FETCHING_DATA, TaskState.EXECUTING, TaskState.VALIDATING, TaskState.GENERATING_REPORT, TaskState.COMPLETED]
LABELS = {
    TaskState.IDLE: "等待任务", TaskState.PLANNING: "规划任务", TaskState.MATCHING_SKILL: "匹配 Skill",
    TaskState.FETCHING_DATA: "获取数据", TaskState.EXECUTING: "执行工具", TaskState.VALIDATING: "验证结果",
    TaskState.WAITING_USER: "等待用户处理", TaskState.GENERATING_REPORT: "生成报告", TaskState.COMPLETED: "已完成",
    TaskState.FAILED: "失败", TaskState.STOPPED: "已停止",
}


def render_task(state: TaskState, skill_stats: list[dict]) -> None:
    st.subheader(f"任务状态：{LABELS.get(state, state.value)}")
    if state in (TaskState.WAITING_USER, TaskState.FAILED):
        st.warning("任务需要处理后再继续，请查看聊天消息和日志。")
    elif state == TaskState.STOPPED:
        st.info("任务已安全停止，日志已保留。")
    else:
        current = ORDER.index(state) if state in ORDER else -1
        for index, item in enumerate(ORDER):
            icon = "✅" if state == TaskState.COMPLETED or index < current else "🔵" if index == current else "⬜"
            st.markdown(f"{icon} {LABELS[item]}")
    with st.expander("Skill 状态", expanded=False):
        if skill_stats:
            frame = pd.DataFrame(skill_stats).rename(columns={"name": "名称", "status": "状态", "version": "版本", "success_count": "成功", "failure_count": "失败"})
            st.dataframe(frame[["名称", "状态", "版本", "成功", "失败"]], hide_index=True, use_container_width=True)

