"""Cooperative cancellation checked between every long-running step."""

import threading


class TaskCancelled(Exception):
    """Raised when the user has requested task cancellation."""


class CancellationToken:
    def __init__(self, event: threading.Event | None = None) -> None:
        self.event = event or threading.Event()

    def cancel(self) -> None:
        self.event.set()

    @property
    def cancelled(self) -> bool:
        return self.event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise TaskCancelled("任务已停止。")

