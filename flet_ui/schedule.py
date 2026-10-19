"""Thread-safe UI updates for Flet."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import flet as ft


def schedule_ui(page: ft.Page, fn: Callable[[], None]) -> None:
    """Run ``fn`` on the UI event loop (safe from worker threads)."""

    async def _task() -> None:
        fn()

    page.run_task(_task)
