"""Native Windows desktop workbench for the DeepSeek agent."""

from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from agent import BASE_DIR, SYSTEM_PROMPT, load_memory, run_agent, save_memory
from computer_tools import COMPUTER_TOOL_DEFINITIONS
from tools import TOOL_DEFINITIONS
from research_runner import run_research_task


load_dotenv(BASE_DIR / ".env")


class AgentWorkbench(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("DeepSeek 智能体工作台")
        self.geometry("1120x720")
        self.minsize(880, 580)
        self.configure(bg="#10131a")
        self.messages = load_memory()

        self.api_key = tk.StringVar(value=os.getenv("DEEPSEEK_API_KEY", ""))
        self.model = tk.StringVar(value=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"))
        self.computer_enabled = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="准备就绪")

        self._configure_style()
        self._build_ui()
        self._render_history()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Sidebar.TFrame", background="#171b25")
        style.configure("Main.TFrame", background="#10131a")
        style.configure("Title.TLabel", background="#171b25", foreground="#f4f7ff", font=("Microsoft YaHei UI", 16, "bold"))
        style.configure("Text.TLabel", background="#171b25", foreground="#c9d1e4", font=("Microsoft YaHei UI", 10))
        style.configure("Status.TLabel", background="#171b25", foreground="#5ed69a", font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("TButton", font=("Microsoft YaHei UI", 10), padding=7)
        style.configure("TCheckbutton", background="#171b25", foreground="#e2e7f3", font=("Microsoft YaHei UI", 10))

    def _build_ui(self) -> None:
        sidebar = ttk.Frame(self, style="Sidebar.TFrame", width=280)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        ttk.Label(sidebar, text="🤖 DeepSeek Agent", style="Title.TLabel").pack(anchor="w", padx=18, pady=(22, 18))
        ttk.Label(sidebar, text="API Key", style="Text.TLabel").pack(anchor="w", padx=18)
        ttk.Entry(sidebar, textvariable=self.api_key, show="●").pack(fill="x", padx=18, pady=(5, 15))

        ttk.Label(sidebar, text="模型", style="Text.TLabel").pack(anchor="w", padx=18)
        ttk.Combobox(
            sidebar,
            textvariable=self.model,
            values=("deepseek-v4-flash", "deepseek-v4-pro"),
            state="readonly",
        ).pack(fill="x", padx=18, pady=(5, 18))

        ttk.Separator(sidebar).pack(fill="x", padx=18, pady=5)
        ttk.Checkbutton(
            sidebar,
            text="允许控制本机",
            variable=self.computer_enabled,
            command=self._computer_toggle_changed,
        ).pack(anchor="w", padx=18, pady=(14, 4))
        ttk.Label(
            sidebar,
            text="可打开应用、搜索网页、输入文字、\n按键、点击和截图。\n紧急停止：鼠标移到左上角。",
            style="Text.TLabel",
            justify="left",
        ).pack(anchor="w", padx=22, pady=(0, 18))

        ttk.Button(sidebar, text="清空对话记忆", command=self._clear_history).pack(fill="x", padx=18, pady=5)
        ttk.Label(sidebar, textvariable=self.status, style="Status.TLabel", wraplength=235).pack(side="bottom", anchor="w", padx=18, pady=20)

        main = ttk.Frame(self, style="Main.TFrame")
        main.pack(side="left", fill="both", expand=True, padx=16, pady=16)

        notebook = ttk.Notebook(main)
        notebook.pack(fill="both", expand=True)

        chat_frame = ttk.Frame(notebook, style="Main.TFrame")
        research_frame = ttk.Frame(notebook, style="Main.TFrame")
        log_frame = ttk.Frame(notebook, style="Main.TFrame")
        notebook.add(chat_frame, text="  对话  ")
        notebook.add(research_frame, text="  独立研究任务  ")
        notebook.add(log_frame, text="  执行记录  ")

        self.chat = scrolledtext.ScrolledText(
            chat_frame,
            wrap="word",
            state="disabled",
            bg="#111722",
            fg="#eef2ff",
            insertbackground="white",
            font=("Microsoft YaHei UI", 11),
            padx=14,
            pady=14,
            relief="flat",
        )
        self.chat.pack(fill="both", expand=True, pady=(0, 10))
        self.chat.tag_configure("user", foreground="#7eb6ff", spacing1=10, spacing3=8)
        self.chat.tag_configure("assistant", foreground="#f2f4fa", spacing1=10, spacing3=8)

        input_row = ttk.Frame(chat_frame, style="Main.TFrame")
        input_row.pack(fill="x")
        self.input_box = tk.Text(
            input_row,
            height=3,
            wrap="word",
            bg="#1b2230",
            fg="white",
            insertbackground="white",
            font=("Microsoft YaHei UI", 11),
            relief="flat",
            padx=10,
            pady=8,
        )
        self.input_box.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.input_box.bind("<Control-Return>", lambda _event: self._send())
        self.send_button = ttk.Button(input_row, text="发送\nCtrl+Enter", command=self._send)
        self.send_button.pack(side="right", fill="y")

        ttk.Label(
            research_frame,
            text="输入最终目标，智能体将自动规划、搜索、阅读多个网页并保存报告。",
            font=("Microsoft YaHei UI", 11, "bold"),
        ).pack(anchor="w", pady=(8, 10))
        self.research_input = tk.Text(
            research_frame,
            height=5,
            wrap="word",
            bg="#1b2230",
            fg="white",
            insertbackground="white",
            font=("Microsoft YaHei UI", 11),
            relief="flat",
            padx=10,
            pady=8,
        )
        self.research_input.pack(fill="x", pady=(0, 10))
        self.research_button = ttk.Button(research_frame, text="开始独立研究", command=self._start_research)
        self.research_button.pack(anchor="e", pady=(0, 10))
        self.research_output = scrolledtext.ScrolledText(
            research_frame,
            wrap="word",
            state="disabled",
            bg="#111722",
            fg="#eef2ff",
            font=("Microsoft YaHei UI", 10),
            padx=14,
            pady=14,
            relief="flat",
        )
        self.research_output.pack(fill="both", expand=True)

        self.log = scrolledtext.ScrolledText(
            log_frame,
            wrap="word",
            state="disabled",
            bg="#111722",
            fg="#cdd7ef",
            font=("Consolas", 10),
            padx=14,
            pady=14,
            relief="flat",
        )
        self.log.pack(fill="both", expand=True)

    def _render_history(self) -> None:
        for item in self.messages:
            if item.get("role") in {"user", "assistant"} and item.get("content"):
                self._append_chat(item["role"], item["content"])

    def _append_chat(self, role: str, content: str) -> None:
        self.chat.configure(state="normal")
        label = "你" if role == "user" else "智能体"
        self.chat.insert("end", f"{label}：{content}\n", role)
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def _append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n\n")
        self.log.configure(state="disabled")
        self.log.see("end")

    def _computer_toggle_changed(self) -> None:
        if self.computer_enabled.get():
            allowed = messagebox.askyesno(
                "开启电脑控制",
                "智能体将能够操作鼠标、键盘和应用。执行时请观察屏幕。\n\n确定开启吗？",
            )
            if not allowed:
                self.computer_enabled.set(False)

    def _clear_history(self) -> None:
        if not messagebox.askyesno("清空记忆", "确定清空全部对话记忆吗？"):
            return
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        save_memory(self.messages)
        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.configure(state="disabled")
        self.status.set("对话记忆已清空")

    def _send(self) -> None:
        prompt = self.input_box.get("1.0", "end").strip()
        key = self.api_key.get().strip()
        if not prompt:
            return
        if not key or key.startswith("在这里"):
            messagebox.showwarning("缺少 API Key", "请先在左侧输入 DeepSeek API Key。")
            return

        self.input_box.delete("1.0", "end")
        self.messages.append({"role": "user", "content": prompt})
        self._append_chat("user", prompt)
        self.send_button.configure(state="disabled")
        self.status.set("智能体正在思考……")
        threading.Thread(target=self._run_task, args=(key,), daemon=True).start()

    def _run_task(self, key: str) -> None:
        definitions = list(TOOL_DEFINITIONS)
        if self.computer_enabled.get():
            definitions.extend(COMPUTER_TOOL_DEFINITIONS)

        def tool_event(name: str, arguments: dict[str, Any], result: dict[str, Any]) -> None:
            self.after(0, self._append_log, f"工具：{name}\n参数：{arguments}\n结果：{result}")
            self.after(0, self.status.set, f"正在执行：{name}")

        try:
            client = OpenAI(api_key=key, base_url="https://api.deepseek.com")
            answer = run_agent(
                client,
                self.model.get(),
                self.messages,
                tool_definitions=definitions,
                on_tool_event=tool_event,
            )
            save_memory(self.messages)
            self.after(0, self._finish_task, answer, False)
        except Exception as exc:
            self.after(0, self._finish_task, f"请求失败：{exc}", True)

    def _finish_task(self, answer: str, failed: bool) -> None:
        if failed:
            self.messages.append({"role": "assistant", "content": answer})
        self._append_chat("assistant", answer)
        self.status.set("执行失败" if failed else "任务完成")
        self.send_button.configure(state="normal")
        self.input_box.focus_set()

    def _set_research_output(self, text: str, append: bool = False) -> None:
        self.research_output.configure(state="normal")
        if not append:
            self.research_output.delete("1.0", "end")
        self.research_output.insert("end", text + "\n")
        self.research_output.configure(state="disabled")
        self.research_output.see("end")

    def _start_research(self) -> None:
        objective = self.research_input.get("1.0", "end").strip()
        key = self.api_key.get().strip()
        if not objective:
            messagebox.showwarning("缺少目标", "请先输入一个具体研究目标。")
            return
        if not key or key.startswith("在这里"):
            messagebox.showwarning("缺少 API Key", "请先在左侧输入 DeepSeek API Key。")
            return
        self.research_button.configure(state="disabled")
        self.status.set("正在制定研究计划……")
        self._set_research_output("任务已启动，请等待智能体制定计划……")
        threading.Thread(target=self._run_research, args=(key, objective), daemon=True).start()

    def _run_research(self, key: str, objective: str) -> None:
        def show_plan(plan: str) -> None:
            self.after(0, self._set_research_output, f"执行计划：\n{plan}\n", False)
            self.after(0, self.status.set, "正在搜索和阅读网页……")

        def tool_event(name: str, arguments: dict[str, Any], result: dict[str, Any]) -> None:
            summary = result.get("error") or result.get("title") or result.get("filename") or "完成"
            self.after(0, self._set_research_output, f"[{name}] {summary}", True)
            self.after(0, self._append_log, f"研究工具：{name}\n参数：{arguments}\n结果：{result}")

        try:
            client = OpenAI(api_key=key, base_url="https://api.deepseek.com")
            answer, report_path = run_research_task(
                client,
                self.model.get(),
                objective,
                on_plan=show_plan,
                on_tool_event=tool_event,
            )
            self.after(0, self._finish_research, answer, report_path, False)
        except Exception as exc:
            self.after(0, self._finish_research, f"研究失败：{exc}", "", True)

    def _finish_research(self, answer: str, report_path: str, failed: bool) -> None:
        self._set_research_output(f"\n最终结果：\n{answer}", True)
        if report_path:
            self._set_research_output(f"\n报告已保存：{report_path}", True)
        self.status.set("研究失败" if failed else "独立研究完成")
        self.research_button.configure(state="normal")


if __name__ == "__main__":
    AgentWorkbench().mainloop()
