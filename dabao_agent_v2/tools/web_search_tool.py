"""Public-web search without browser GUI automation."""

from __future__ import annotations

from urllib.parse import parse_qs, unquote, urlparse

import httpx
from bs4 import BeautifulSoup

from config.agent_config import MAX_RETRIES
from core.cancellation import CancellationToken
from services.logging_service import TaskLogger


class WebSearchTool:
    def __init__(self, logger: TaskLogger, cancellation: CancellationToken) -> None:
        self.log, self.cancellation = logger, cancellation

    def search(self, query: str, limit: int = 8) -> list[dict[str, str]]:
        """Search DuckDuckGo's HTML endpoint with timeout and bounded retry."""
        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            self.cancellation.raise_if_cancelled()
            try:
                with httpx.Client(timeout=15, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 Dabao-Agent/2.0"}) as client:
                    response = client.get("https://html.duckduckgo.com/html/", params={"q": query})
                    response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
                results = []
                for item in soup.select(".result"):
                    anchor = item.select_one(".result__a")
                    if not anchor:
                        continue
                    href = str(anchor.get("href") or "")
                    parsed = parse_qs(urlparse(href).query).get("uddg")
                    link = unquote(parsed[0]) if parsed else href
                    snippet = item.select_one(".result__snippet")
                    results.append({"source": urlparse(link).netloc, "title": anchor.get_text(" ", strip=True), "summary": snippet.get_text(" ", strip=True) if snippet else "", "time": "网页未提供", "link": link})
                    if len(results) >= limit:
                        break
                if not results:
                    raise RuntimeError("搜索接口未返回结果，可能被网络或地区限制")
                return results
            except Exception as exc:
                last_error = exc
                self.log.error(f"公开网页搜索失败（{attempt}/{MAX_RETRIES}）：{exc}")
        raise RuntimeError(f"网页搜索失败，已重试 {MAX_RETRIES} 次：{last_error}")

