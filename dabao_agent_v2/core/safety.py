"""Safety decision interface reserved for current and future tools."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RiskLevel(StrEnum):
    SAFE = "safe"
    CONFIRM = "confirm"
    FORBIDDEN = "forbidden"


@dataclass(slots=True)
class SafetyDecision:
    level: RiskLevel
    reason: str


class SafetyPolicy:
    """Block financial actions and mark destructive actions for confirmation."""

    FORBIDDEN = ("买入", "卖出", "下单", "券商登录", "支付", "转账", "自动交易")
    CONFIRM = ("删除", "覆盖", "卸载", "系统设置", "发送邮件", "发送消息", "上传")

    def evaluate(self, action: str) -> SafetyDecision:
        if any(term in action for term in self.FORBIDDEN):
            return SafetyDecision(RiskLevel.FORBIDDEN, "第一阶段禁止金融交易、支付或券商操作。")
        if any(term in action for term in self.CONFIRM):
            return SafetyDecision(RiskLevel.CONFIRM, "该操作可能修改或发送数据，必须先由用户确认。")
        return SafetyDecision(RiskLevel.SAFE, "未发现高风险动作。")

