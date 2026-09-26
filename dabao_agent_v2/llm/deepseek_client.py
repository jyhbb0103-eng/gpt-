"""Unified bounded DeepSeek client."""

from __future__ import annotations

from typing import Any

import httpx

from config.settings import Settings, get_settings

MISSING_KEY_MESSAGE = "未找到 DEEPSEEK_API_KEY，请复制 .env.example 为 .env，并填写 DeepSeek API Key。"


class DeepSeekClient:
    def __init__(self, settings: Settings | None = None, transport: httpx.BaseTransport | None = None) -> None:
        self.settings = settings or get_settings()
        self.transport = transport

    def chat(self, messages: list[dict[str, str]], json_mode: bool = False) -> str:
        """Call DeepSeek no more than three times with a hard timeout."""
        if not self.settings.has_api_key:
            raise ValueError(MISSING_KEY_MESSAGE)
        payload: dict[str, Any] = {
            "model": self.settings.deepseek_model,
            "messages": messages,
            "temperature": self.settings.deepseek_temperature,
            "max_tokens": self.settings.deepseek_max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        last_error: Exception | None = None
        for _ in range(3):
            try:
                with httpx.Client(timeout=self.settings.deepseek_timeout, transport=self.transport) as client:
                    response = client.post("https://api.deepseek.com/chat/completions", headers={"Authorization": f"Bearer {self.settings.deepseek_api_key}"}, json=payload)
                    response.raise_for_status()
                    return str(response.json()["choices"][0]["message"]["content"])
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"DeepSeek 调用失败（已重试 3 次）：{type(last_error).__name__}: {last_error}")

