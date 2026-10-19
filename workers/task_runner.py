"""Background task threading (UI-framework agnostic)."""

from __future__ import annotations

import threading
from collections.abc import Callable


class BackgroundTask:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._running = False

    def is_running(self) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()

    def start(self, target: Callable[[], None], on_finished: Callable[[], None] | None = None) -> None:
        if self.is_running():
            raise RuntimeError("Task already running")

        def wrapper() -> None:
            try:
                target()
            finally:
                self._running = False
                if on_finished is not None:
                    on_finished()

        self._running = True
        self._thread = threading.Thread(target=wrapper, daemon=True)
        self._thread.start()

    def join(self, timeout: float | None = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout=timeout)


class StoppableBackgroundTask(BackgroundTask):
    """Task with optional request_stop() for cooperative cancellation."""

    def request_stop(self) -> None:
        if hasattr(self, "_on_request_stop"):
            self._on_request_stop()  # type: ignore[attr-defined]
