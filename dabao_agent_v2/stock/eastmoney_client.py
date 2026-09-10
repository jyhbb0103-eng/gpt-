"""Low-level Eastmoney client with bounded retry and complete pagination."""

from __future__ import annotations

import hashlib
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import httpx

from config import strategy_config as cfg
from config.settings import STORAGE_ROOT, ensure_storage
from core.cancellation import CancellationToken
from services.logging_service import TaskLogger


class EastmoneyClient:
    QUOTE_URL = "https://push2.eastmoney.com/api/qt/clist/get"
    STOCK_URL = "https://push2.eastmoney.com/api/qt/stock/get"
    HISTORY_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    QUOTE_FALLBACK_HOSTS = ("https://push2delay.eastmoney.com", "https://82.push2.eastmoney.com")

    def __init__(self, logger: TaskLogger, cancellation: CancellationToken) -> None:
        self.log = logger
        self.cancellation = cancellation
        self._quote_host = "https://push2.eastmoney.com"
        self.client = httpx.Client(
            timeout=httpx.Timeout(cfg.HTTP_TIMEOUT),
            headers={"User-Agent": "Mozilla/5.0 Dabao-Agent/2.0"},
            follow_redirects=True,
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "EastmoneyClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def get_json(self, url: str, params: dict[str, Any], label: str) -> dict[str, Any]:
        if url.startswith("https://push2.eastmoney.com") and self._quote_host != "https://push2.eastmoney.com":
            url = self._quote_host + url.removeprefix("https://push2.eastmoney.com")
        last_error: Exception | None = None
        for attempt in range(1, cfg.HTTP_RETRIES + 2):
            self.cancellation.raise_if_cancelled()
            try:
                response = self.client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ValueError("接口返回不是 JSON 对象")
                return payload
            except Exception as exc:
                last_error = exc
                self.log.error(f"{label}失败（{attempt}/{cfg.HTTP_RETRIES + 1}）：{type(exc).__name__}: {exc}")
                if attempt <= cfg.HTTP_RETRIES:
                    time.sleep(cfg.RETRY_BACKOFF_SECONDS * attempt)
        if url.startswith("https://push2.eastmoney.com"):
            suffix = url.removeprefix("https://push2.eastmoney.com")
            for host in self.QUOTE_FALLBACK_HOSTS:
                self.cancellation.raise_if_cancelled()
                try:
                    response = self.client.get(host + suffix, params=params)
                    response.raise_for_status()
                    payload = response.json()
                    if isinstance(payload, dict):
                        self._quote_host = host
                        self.log.info(f"{label}已切换备用行情域名：{host}")
                        return payload
                except Exception as exc:
                    last_error = exc
                    self.log.error(f"{label}备用域名失败：{host}：{exc}")
        raise RuntimeError(f"{label}连续失败：{last_error}")

    def quote_list(self, fs: str, fields: str) -> list[dict[str, Any]]:
        """Load every page because the public endpoint caps responses at 100 rows."""
        base = {"pn": 1, "pz": 100, "po": 1, "np": 1, "fltt": 2, "invt": 2, "fid": "f3", "fs": fs, "fields": fields}
        try:
            payload = self.get_json(self.QUOTE_URL, base, "东方财富行情第1页")
        except Exception:
            cached = self._load_quote_cache(fs, fields)
            if cached is not None:
                return cached
            raise
        data = payload.get("data") or {}
        pages: dict[int, list[dict[str, Any]]] = {1: data.get("diff") or []}
        page_count = math.ceil(int(data.get("total") or len(pages[1])) / 100)
        if page_count <= 1:
            self._save_quote_cache(fs, fields, pages[1])
            return pages[1]

        def fetch(page: int) -> tuple[int, list[dict[str, Any]]]:
            self.cancellation.raise_if_cancelled()
            item = self.get_json(self.QUOTE_URL, {**base, "pn": page}, f"东方财富行情第{page}页")
            return page, ((item.get("data") or {}).get("diff") or [])

        with ThreadPoolExecutor(max_workers=6, thread_name_prefix="quote-page") as executor:
            futures = [executor.submit(fetch, page) for page in range(2, page_count + 1)]
            for future in as_completed(futures):
                self.cancellation.raise_if_cancelled()
                page, rows = future.result()
                pages[page] = rows
        rows = [row for page in range(1, page_count + 1) for row in pages.get(page, [])]
        self._save_quote_cache(fs, fields, rows)
        return rows

    def _cache_path(self, fs: str, fields: str):
        ensure_storage()
        digest = hashlib.sha1(f"{fs}|{fields}".encode()).hexdigest()[:16]
        return STORAGE_ROOT / "cache" / f"quotes_{digest}.json"

    def _save_quote_cache(self, fs: str, fields: str, rows: list[dict[str, Any]]) -> None:
        from datetime import datetime
        payload = {"saved_at": datetime.now().isoformat(timespec="seconds"), "rows": rows}
        self._cache_path(fs, fields).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def _load_quote_cache(self, fs: str, fields: str) -> list[dict[str, Any]] | None:
        path = self._cache_path(fs, fields)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.log.error(f"实时行情不可用，使用最近成功缓存（{payload.get('saved_at', '时间未知')}），请谨慎核对")
            return payload.get("rows") or []
        except Exception:
            return None

    def klines(self, secid: str, limit: int = 130) -> tuple[str | None, list[str]]:
        params = {
            "secid": secid, "klt": 101, "fqt": 1, "lmt": limit, "end": 20500101, "iscca": 1,
            "fields1": "f1,f2,f3,f4,f5,f6", "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        }
        payload = self.get_json(self.HISTORY_URL, params, f"历史行情 {secid}")
        rows = (payload.get("data") or {}).get("klines") or []
        return (rows[-1].split(",", 1)[0] if rows else None), rows

    def stock_quote(self, secid: str, fields: str) -> dict[str, Any]:
        payload = self.get_json(self.STOCK_URL, {"secid": secid, "fltt": 2, "fields": fields}, f"股票行情 {secid}")
        return payload.get("data") or {}
