"""Public-web research Agent."""

from core.cancellation import CancellationToken
from services.logging_service import TaskLogger
from tools.web_search_tool import WebSearchTool


class ResearchAgent:
    def __init__(self, logger: TaskLogger, cancellation: CancellationToken) -> None:
        self.tool = WebSearchTool(logger, cancellation)

    def execute(self, query: str) -> dict:
        return {"query": query, "results": self.tool.search(query)}

