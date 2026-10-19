import flet as ft

from flet_ui.schedule import schedule_ui
from flet_ui.widgets.layout import (
    CAPTION_SIZE,
    LABEL_SIZE,
    primary_actions_row,
    section_divider,
    section_title,
)
from workers.updater_worker import JavDatabaseUpdater

TASK_NAME = "Database Updater"


def build_updater_tab(state) -> ft.Column:
    placeholder = state.settings.updater_dir_placeholder
    path_field = ft.TextField(
        value=placeholder,
        hint_text="Folder to add to queue…",
        expand=True,
        text_size=LABEL_SIZE,
    )
    dir_list = ft.ListView(expand=True, spacing=4)
    queue_label = ft.Text("0 folder(s) queued", size=CAPTION_SIZE)
    status = ft.Text("Idle", size=LABEL_SIZE)
    progress = ft.ProgressBar(value=0, expand=True)
    update_btn = ft.FilledButton("Update all")
    paths: list[str] = []
    prog_state = {"max": 1, "val": 0}

    def refresh_queue_label() -> None:
        queue_label.value = f"{len(paths)} folder(s) queued"
        update_btn.disabled = len(paths) == 0 or state.busy.is_busy()

    def refresh_list() -> None:
        dir_list.controls.clear()
        for p in paths:

            def remove_click(_e, path=p):
                if path in paths:
                    paths.remove(path)
                    refresh_list()
                    refresh_queue_label()
                    state.page.update()

            dir_list.controls.append(
                ft.ListTile(
                    title=ft.Text(p, size=13),
                    trailing=ft.IconButton(ft.Icons.CLOSE, tooltip="Remove", on_click=remove_click),
                )
            )
        refresh_queue_label()
        state.page.update()

    def browse(_e):
        start = path_field.value or ""
        if start == placeholder:
            start = ""
        state._browse_target = path_field
        state.file_picker.get_directory_path(initial_directory=start or None)

    def add_path(_e):
        cleaned = (path_field.value or "").strip()
        if cleaned and cleaned != placeholder:
            if cleaned not in paths:
                paths.append(cleaned)
                refresh_list()
        else:
            state.show_snackbar("Enter or browse to a valid folder.")

    def clear_paths(_e):
        paths.clear()
        refresh_list()

    def on_path_focus(_e):
        if path_field.value == placeholder:
            path_field.value = ""
            state.page.update()

    path_field.on_focus = on_path_focus

    def start_next_job() -> None:
        if not state._pending_update_paths:
            status.value = "Idle"
            update_btn.disabled = len(paths) == 0
            progress.value = 0
            state.end_task()
            state.show_snackbar("Database update finished.")
            state.page.update()
            return

        path = state._pending_update_paths.pop(0)
        prog_state["max"] = 1
        prog_state["val"] = 0
        progress.value = 0
        worker = JavDatabaseUpdater(path)

        def on_message(msg: str) -> None:
            schedule_ui(state.page, lambda m=msg: (setattr(status, "value", m), state.page.update()))

        def on_progress(val: int) -> None:
            prog_state["val"] = val
            mx = prog_state["max"]

            def upd() -> None:
                progress.value = val / mx if mx else 0
                state.page.update()

            schedule_ui(state.page, upd)

        def on_max(mx: int) -> None:
            prog_state["max"] = mx

        def on_finished() -> None:
            schedule_ui(state.page, start_next_job)

        state.busy.set_worker(worker)
        worker.start(on_message=on_message, on_progress=on_progress, on_max=on_max, on_finished=on_finished)

    def run_update(_e):
        if state.warn_busy():
            return
        if not paths:
            state.show_snackbar("Add at least one folder to the queue.")
            return
        state._pending_update_paths = list(paths)
        update_btn.disabled = True
        state.set_busy_label(TASK_NAME)
        state.page.update()
        start_next_job()

    update_btn.on_click = run_update
    refresh_queue_label()

    return ft.Column(
        [
            ft.Row(
                [
                    ft.Text("Folder", size=LABEL_SIZE, width=72),
                    path_field,
                    ft.OutlinedButton("Browse", on_click=browse),
                    ft.OutlinedButton("Add", on_click=add_path),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            primary_actions_row(ft.TextButton("Clear queue", on_click=clear_paths), queue_label),
            section_title("Queue"),
            dir_list,
            section_divider(),
            section_title("Progress"),
            status,
            progress,
            ft.Row([update_btn], alignment=ft.MainAxisAlignment.END),
        ],
        expand=True,
        spacing=10,
    )
