"""Basic validation before results are shown or remembered."""

from core.task_state import TaskResult, TaskState


class ResultValidator:
    def validate(self, result: TaskResult) -> tuple[bool, str]:
        if result.state == TaskState.COMPLETED and not result.message.strip():
            return False, "完成状态缺少结果说明"
        if result.task_type.value.startswith("stock") and result.data.get("stocks"):
            for item in result.data["stocks"]:
                if not item.get("code") or not (0 <= float(item.get("total_score", -1)) <= 100):
                    return False, "股票结果包含无效代码或评分"
        return True, "验证通过"

