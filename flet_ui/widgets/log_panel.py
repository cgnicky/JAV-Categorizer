from __future__ import annotations

import threading
from collections.abc import Callable

import flet as ft

from flet_ui.schedule import schedule_ui

LOG_FLUSH_BATCH = 25


def make_log_field(expand: bool = True) -> ft.TextField:
    return ft.TextField(
        multiline=True,
        read_only=True,
        min_lines=10,
        expand=expand,
    )


def append_log(field: ft.TextField, line: str) -> None:
    field.value = (field.value or "") + line + "\n"


def clear_log(field: ft.TextField) -> None:
    field.value = ""


def make_buffered_log_sink(
    page: ft.Page,
    field: ft.TextField,
    *,
    batch_size: int = LOG_FLUSH_BATCH,
) -> tuple[Callable[[str], None], Callable[[], None], Callable[[], None]]:
    """Return ``(append_line, flush_async, drain_on_ui)`` for worker / UI threads."""
    pending: list[str] = []
    lock = threading.Lock()
    flush_scheduled = {"flag": False}

    def flush() -> None:
        flush_scheduled["flag"] = False
        with lock:
            if not pending:
                return
            block = "\n".join(pending) + "\n"
            pending.clear()
        field.value = (field.value or "") + block
        page.update()

    def schedule_flush() -> None:
        if flush_scheduled["flag"]:
            return
        flush_scheduled["flag"] = True

        async def _delayed() -> None:
            import asyncio

            await asyncio.sleep(0.08)
            schedule_ui(page, flush)

        page.run_task(_delayed)

    def append_line(line: str) -> None:
        with lock:
            pending.append(line)
            count = len(pending)
        if count >= batch_size:
            schedule_ui(page, flush)
        else:
            schedule_flush()

    def flush_async() -> None:
        schedule_ui(page, flush)

    return append_line, flush_async, flush
