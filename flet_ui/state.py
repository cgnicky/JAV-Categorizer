"""Application state, settings, busy guard, and dialogs."""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from core.settings import UI_THEME_CHOICES, load_settings, save_settings
from flet_ui.busy_guard import BusyGuard
from flet_ui.theme import theme_mode_for_setting

JAVLIB_PAUSE_MAX_SECONDS = 120.0
PLACEHOLDER_KEYWORDS = "Enter Your Search Keywords Here!!"


class AppState:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.settings = load_settings()
        self.busy = BusyGuard()
        self.file_picker = ft.FilePicker()
        self._browse_target: ft.TextField | None = None
        self._browse_persist_field: str | None = None
        self.pause_fields: list[ft.TextField] = []
        self._pause_sync = False
        self._pending_update_paths: list[str] = []
        self._busy_status: ft.Text | None = None

        page.overlay.append(self.file_picker)
        self.file_picker.on_result = self._on_picker_result
        self.apply_ui_theme()

    def attach_busy_status(self, control: ft.Text) -> None:
        self._busy_status = control

    def set_busy_label(self, task: str | None) -> None:
        if self._busy_status is None:
            return
        self._busy_status.value = f"Running: {task}" if task else "Ready"
        self.page.update()

    def apply_ui_theme(self) -> None:
        self.page.theme_mode = theme_mode_for_setting(self.settings.ui_theme)

    def set_ui_theme(self, value: str) -> None:
        theme = (value or "system").lower()
        if theme not in UI_THEME_CHOICES:
            theme = "system"
        self.settings.ui_theme = theme
        save_settings(self.settings)
        self.apply_ui_theme()
        self.page.update()

    def persist_path(self, field: str, value: str) -> None:
        setattr(self.settings, field, value)
        save_settings(self.settings)

    def javlib_pause_seconds(self) -> float:
        if self.pause_fields:
            try:
                return float(self.pause_fields[0].value or self.settings.javlib_search_pause_seconds)
            except ValueError:
                return self.settings.javlib_search_pause_seconds
        return self.settings.javlib_search_pause_seconds

    def make_pause_field(self) -> ft.TextField:
        field = ft.TextField(
            value=str(self.settings.javlib_search_pause_seconds),
            width=80,
            suffix_text=" s",
            on_change=self._on_pause_changed,
        )
        self.pause_fields.append(field)
        return field

    def _on_pause_changed(self, e: ft.ControlEvent) -> None:
        if self._pause_sync:
            return
        try:
            value = float(e.control.value)
        except (TypeError, ValueError):
            return
        value = max(0.0, min(JAVLIB_PAUSE_MAX_SECONDS, value))
        self.settings.javlib_search_pause_seconds = value
        save_settings(self.settings)
        self._pause_sync = True
        for field in self.pause_fields:
            if field is not e.control:
                field.value = str(value)
        self._pause_sync = False
        self.page.update()

    def show_info(self, title: str, message: str) -> None:
        dlg = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=lambda e: self._close_dialog(dlg))],
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    def show_snackbar(self, message: str) -> None:
        self.page.snack_bar = ft.SnackBar(ft.Text(message), open=True)
        self.page.update()

    def _close_dialog(self, dlg: ft.AlertDialog) -> None:
        dlg.open = False
        self.page.update()

    def warn_busy(self) -> bool:
        if self.busy.warn_if_busy():
            self.show_snackbar("Another task is still running.")
            return True
        return False

    def browse_into(self, target: ft.TextField, persist_field: str | None = None) -> None:
        self._browse_target = target
        self._browse_persist_field = persist_field
        start = (target.value or "").strip()
        self.file_picker.get_directory_path(initial_directory=start if start else None)

    def _on_picker_result(self, e: ft.FilePickerResultEvent) -> None:
        if e.path and self._browse_target is not None:
            self._browse_target.value = e.path
            if self._browse_persist_field:
                self.persist_path(self._browse_persist_field, e.path)
            self.page.update()

    def ui(self, fn: Callable[[], None]) -> Callable[[], None]:
        """Wrap a no-arg callback to run on the UI thread."""

        def wrapper() -> None:
            from flet_ui.schedule import schedule_ui

            schedule_ui(self.page, fn)

        return wrapper

    def begin_task(self, worker, task_name: str) -> None:
        self.busy.set_worker(worker)
        self.set_busy_label(task_name)

    def end_task(self) -> None:
        self.busy.set_worker(None)
        self.set_busy_label(None)
