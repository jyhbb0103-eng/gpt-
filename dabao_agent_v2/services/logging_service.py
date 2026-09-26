"""Terminal, file and UI event logging."""

from __future__ import annotations

import logging
from collections.abc import Callable

from config.settings import STORAGE_ROOT, ensure_storage


def get_logger() -> logging.Logger:
    ensure_storage()
    logger = logging.getLogger("dabao")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S")
    for handler in (logging.StreamHandler(), logging.FileHandler(STORAGE_ROOT / "logs" / "dabao.log", encoding="utf-8")):
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


class TaskLogger:
    def __init__(self, callback: Callable[[str], None] | None = None) -> None:
        self.base = get_logger()
        self.callback = callback

    def info(self, message: str) -> None:
        self.base.info(message)
        if self.callback:
            self.callback(message)

    def error(self, message: str) -> None:
        self.base.error(message)
        if self.callback:
            self.callback(f"错误：{message}")

