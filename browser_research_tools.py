"""Browser tools for autonomous web research using the installed Microsoft Edge."""

from __future__ import annotations

import re
import urllib.parse
from pathlib import Path
from typing import Any, Callable


REPORTS_DIR = Path(__file__).resolve().parent / "reports"

RESEARCH_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "browser_search",
            "description": "使用浏览器搜索互联网并返回多个结果的标题、网址和摘要。需要不同角度时应使用不同关键词多次搜索。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "准确、具体的搜索关键词"},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": 8, "default": 5},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_read_page",
            "description": "打开一个搜索结果网页并提取可读正文。研究报告不能只依赖搜索摘要，应读取多个来源。",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "要读取的 http/https 网页地址"}},
                "required": ["url"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_research_report",
            "description": "把最终研究结果保存为 Markdown 报告。报告必须包含结论、关键发现和来源网址。",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "简短报告文件名，不含路径"},
                    "content": {"type": "string", "description": "完整 Markdown 报告内容"},
                },
                "required": ["filename", "content"],
                "additionalProperties": False,
            },
        },
    },
]


def _open_browser():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("缺少 Playwright，请重新运行 start.bat 安装依赖") from exc

    playwright = sync_playwright().start()
    try:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
    except Exception:
        playwright.stop()
        raise RuntimeError("无法启动 Microsoft Edge。请确认电脑已安装 Edge 浏览器。")
    return playwright, browser


def _valid_public_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or not host:
        return False
    return host not in {"localhost", "127.0.0.1", "0.0.0.0", "::1"} and not host.endswith(".local")


def browser_search(query: str, max_results: int = 5) -> dict[str, Any]:
    query = query.strip()
    if not query or len(query) > 300:
        return {"ok": False, "error": "搜索关键词为空或过长"}
    max_results = min(max(int(max_results), 1), 8)
    playwright, browser = _open_browser()
    try:
        page = browser.new_page(locale="zh-CN")
        url = "https://www.bing.com/search?q=" + urllib.parse.quote_plus(query)
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1000)
        items = page.locator("li.b_algo")
        results: list[dict[str, str]] = []
        for index in range(min(items.count(), max_results)):
            item = items.nth(index)
            link = item.locator("h2 a").first
            if link.count() == 0:
                continue
            href = link.get_attribute("href") or ""
            title = link.inner_text().strip()
            snippet_node = item.locator(".b_caption p").first
            snippet = snippet_node.inner_text().strip() if snippet_node.count() else ""
            if _valid_public_url(href):
                results.append({"title": title, "url": href, "snippet": snippet})
        if not results:
            return {"ok": False, "error": "没有提取到搜索结果，可能遇到网络限制或验证码"}
        return {"ok": True, "query": query, "results": results}
    finally:
        browser.close()
        playwright.stop()


def browser_read_page(url: str) -> dict[str, Any]:
    if not _valid_public_url(url):
        return {"ok": False, "error": "只允许读取公开的 http/https 网页"}
    playwright, browser = _open_browser()
    try:
        page = browser.new_page(locale="zh-CN")
        response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(800)
        page.locator("script, style, noscript, svg").evaluate_all("els => els.forEach(el => el.remove())")
        title = page.title().strip()
        text = page.locator("body").inner_text(timeout=10000)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if len(text) > 18000:
            text = text[:18000] + "\n\n[正文过长，已截断]"
        return {
            "ok": bool(text),
            "url": page.url,
            "title": title,
            "status": response.status if response else None,
            "content": text,
        }
    except Exception as exc:
        return {"ok": False, "url": url, "error": f"网页读取失败：{exc}"}
    finally:
        browser.close()
        playwright.stop()


def save_research_report(filename: str, content: str) -> dict[str, Any]:
    clean = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", Path(filename).stem).strip("-")[:80]
    if not clean:
        return {"ok": False, "error": "报告文件名无效"}
    REPORTS_DIR.mkdir(exist_ok=True)
    path = REPORTS_DIR / f"{clean}.md"
    path.write_text(content, encoding="utf-8")
    return {"ok": True, "filename": path.name, "path": str(path), "characters": len(content)}


RESEARCH_TOOLS: dict[str, Callable[..., dict[str, Any]]] = {
    "browser_search": browser_search,
    "browser_read_page": browser_read_page,
    "save_research_report": save_research_report,
}


def run_research_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    tool = RESEARCH_TOOLS.get(name)
    if not tool:
        return {"ok": False, "error": f"未知研究工具：{name}"}
    return tool(**arguments)
