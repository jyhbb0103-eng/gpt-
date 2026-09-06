"""Dabao's lightweight total-manager Agent."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from agents.coding_agent import CodingAgent
from agents.office_agent import OfficeAgent
from agents.report_agent import ReportAgent
from agents.research_agent import ResearchAgent
from agents.stock_agent import StockAgent
from config.agent_config import REPEAT_TASK_SUGGESTION_COUNT, SKILL_STABLE_SUCCESS_COUNT
from core.cancellation import CancellationToken, TaskCancelled
from core.context_builder import ContextBuilder
from core.result_validator import ResultValidator
from core.safety import RiskLevel, SafetyPolicy
from core.task_router import TaskRouter
from core.task_state import TaskResult, TaskState, TaskType
from llm.deepseek_client import DeepSeekClient
from memory.memory_manager import MemoryManager
from services.logging_service import TaskLogger
from skills.skill_compiler import SkillCompiler
from skills.skill_manager import SkillManager
from skills.skill_matcher import SkillMatcher
from tools.excel_tool import ExcelTool


class OrchestratorAgent:
    """Route, match Skills, retrieve minimal memory, execute, validate and summarize."""

    def __init__(self, cancellation: CancellationToken | None = None, log_callback: Callable[[str], None] | None = None, state_callback: Callable[[TaskState], None] | None = None) -> None:
        self.cancellation = cancellation or CancellationToken()
        self.log = TaskLogger(log_callback)
        self.state_callback = state_callback
        self.state = TaskState.IDLE
        self.memory = MemoryManager()
        self.skill_manager = SkillManager(self.memory.store)
        self.matcher = SkillMatcher()
        self.context_builder = ContextBuilder(self.memory)
        self.router = TaskRouter()
        self.validator = ResultValidator()
        self.llm = DeepSeekClient()

    def _state(self, value: TaskState) -> None:
        self.state = value
        if self.state_callback:
            self.state_callback(value)

    def execute(self, command: str, attachments: list[str] | None = None) -> TaskResult:
        started = time.monotonic()
        used_skills: list[str] = []
        self.log.info(f"收到任务：{command}")
        try:
            decision = SafetyPolicy().evaluate(command)
            if decision.level == RiskLevel.FORBIDDEN:
                return self._finish(TaskResult(TaskState.FAILED, decision.reason, TaskType.CHAT, error=decision.reason), command, used_skills, started)
            if decision.level == RiskLevel.CONFIRM:
                self._state(TaskState.WAITING_USER)
                return TaskResult(TaskState.WAITING_USER, f"需要你确认：{decision.reason}", TaskType.CHAT, data={"confirmation_required": True})

            route = self.router.route(command, attachments)
            if route.complex_task:
                self._state(TaskState.PLANNING)
                self.log.info("复杂任务：正在生成简短执行计划")
            self.cancellation.raise_if_cancelled()
            self._state(TaskState.MATCHING_SKILL)
            matched = self.matcher.match(command, self.skill_manager.skills)
            used_skills = [skill["name"] for skill in matched]
            self.log.info(f"匹配到 Skill：{', '.join(used_skills) if used_skills else '无，使用基础路由'}")
            context = self.context_builder.build(command, route.task_type.value, matched)
            self.log.info(f"最小上下文预计约 {context['estimated_tokens']} Tokens")
            self.cancellation.raise_if_cancelled()
            result = self._dispatch(route.task_type, route.parameters, command, context)

            self._state(TaskState.VALIDATING)
            valid, validation_message = self.validator.validate(result)
            self.log.info(f"结果验证：{validation_message}")
            if not valid:
                raise RuntimeError(validation_message)
            result.skill_candidate = SkillCompiler().candidate(command, route.task_type.value, matched[0].get("steps", []) if matched else [], self.skill_manager.skills)
            result.data["context_tokens_estimate"] = context["estimated_tokens"]
            result.data["skills_used"] = used_skills
            return self._finish(result, command, used_skills, started)
        except TaskCancelled:
            self._state(TaskState.STOPPED)
            self.log.info("任务已停止，当前日志已保留")
            return self._finish(TaskResult(TaskState.STOPPED, "任务已停止。", TaskType.CHAT), command, used_skills, started)
        except Exception as exc:
            failed_step = self.state.value
            self._state(TaskState.WAITING_USER)
            message = f"任务在“{failed_step}”阶段失败：{exc}。已完成有限重试。你可以检查网络/文件后重试，或停止任务。"
            self.log.error(message)
            return self._finish(TaskResult(TaskState.WAITING_USER, message, self.router.route(command, attachments).task_type, data={"failed_step": failed_step, "attempts": "最多3次", "suggestions": ["重试", "检查网络或文件", "停止任务"]}, error=str(exc)), command, used_skills, started)

    def _dispatch(self, task_type: TaskType, params: dict[str, str], command: str, context: dict[str, Any]) -> TaskResult:
        self._state(TaskState.EXECUTING)
        if task_type == TaskType.STOCK_SCREENING:
            self._state(TaskState.FETCHING_DATA)
            data = StockAgent(self.log, self.cancellation, self.llm).screen()
            return TaskResult(TaskState.COMPLETED, f"选股完成，返回 {len(data['stocks'])} 只候选股票。", task_type, data, data["report_path"])
        if task_type == TaskType.STOCK_ANALYSIS:
            self._state(TaskState.FETCHING_DATA)
            data = StockAgent(self.log, self.cancellation, self.llm).analyze(params["code"])
            return TaskResult(TaskState.COMPLETED, f"股票 {params['code']} 分析完成。", task_type, data, data["report_path"])
        if task_type == TaskType.STRONG_SECTOR:
            self._state(TaskState.FETCHING_DATA)
            data = StockAgent(self.log, self.cancellation, self.llm).scan_sectors()
            return TaskResult(TaskState.COMPLETED, f"强势板块扫描完成，共 {len(data['sectors'])} 个。", task_type, data)
        if task_type == TaskType.WEB_RESEARCH:
            data = ResearchAgent(self.log, self.cancellation).execute(params["query"])
            if params.get("export_excel") == "1":
                data["excel_output"] = ExcelTool(self.cancellation).records_to_excel(data["results"], "research_results.xlsx")
            path = ReportAgent().save_json_report(f"大宝资料研究：{params['query']}", task_type.value, data)
            return TaskResult(TaskState.COMPLETED, f"资料搜索完成，共整理 {len(data['results'])} 条来源。", task_type, data, str(path))
        if task_type == TaskType.EXCEL:
            data = OfficeAgent(self.cancellation).execute(params["path"])
            return TaskResult(TaskState.COMPLETED, f"Excel 整理完成：{data['output']}", task_type, data, data["output"])
        if task_type == TaskType.PYTHON_TOOL:
            data = CodingAgent(self.llm).execute(params["requirement"])
            return TaskResult(TaskState.COMPLETED, f"Python 工具已生成并完成安全检查：{data['path']}", task_type, data, data["path"])
        answer = self.llm.chat([{"role": "system", "content": "你是大宝，一个简洁、可靠的本地AI助手。不要声称执行未执行的工具。"}, {"role": "user", "content": str(context)}])
        return TaskResult(TaskState.COMPLETED, answer, task_type, {"context_tokens_estimate": context["estimated_tokens"]})

    def _finish(self, result: TaskResult, command: str, skills: list[str], started: float) -> TaskResult:
        if result.state == TaskState.COMPLETED:
            self._state(TaskState.COMPLETED)
        for name in skills:
            self.memory.skills.record(name, result.state == TaskState.COMPLETED)
        duration = round(time.monotonic() - started, 2)
        self.memory.tasks.save({"task": command, "task_type": result.task_type.value, "status": "success" if result.state == TaskState.COMPLETED else result.state.value.lower(), "skills_used": skills, "important_events": [result.error] if result.error else [], "result": result.message[:500], "output": result.report_path, "execution_time": duration})
        repeats = self.memory.store.repeat_count(result.task_type.value)
        if repeats >= REPEAT_TASK_SUGGESTION_COUNT:
            result.data["repeat_suggestion"] = "这个任务已经重复执行多次。可以保存为 Skill；第三阶段可创建自动任务。"
        stats = {item["name"]: item for item in self.skill_manager.stats()}
        stable = [name for name in skills if stats.get(name, {}).get("status") != "stable" and stats.get(name, {}).get("success_count", 0) >= SKILL_STABLE_SUCCESS_COUNT]
        if stable:
            result.data["stable_suggestion"] = f"Skill {', '.join(stable)} 已成功运行至少3次，是否升级为 stable？不会自动升级。"
            result.data["stable_skills"] = stable
        self.memory.clear_short_term()
        return result
