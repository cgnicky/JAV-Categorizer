import flet as ft

from flet_ui.schedule import schedule_ui
from flet_ui.widgets.layout import (
    folder_path_row,
    javlib_pause_advanced,
    primary_actions_row,
    side_log_layout,
)
from flet_ui.widgets.log_panel import clear_log, make_buffered_log_sink, make_log_field
from workers.classifier_worker import JavClassifier

TASK_NAME = "JAV Classifier"


def build_classifier_tab(state) -> ft.Column:
    path_field, path_row = folder_path_row(
        state,
        label="Folder",
        value=state.settings.classifier_path or "",
        persist_field="classifier_path",
    )
    log = make_log_field()
    pause_field = state.make_pause_field()
    run_btn = ft.FilledButton("Run")
    stop_btn = ft.OutlinedButton("Stop", disabled=True)
    clear_btn = ft.TextButton("Clear log", style=ft.ButtonStyle(text_style=ft.TextStyle(size=12)))

    def set_running(running: bool) -> None:
        run_btn.disabled = running
        stop_btn.disabled = not running
        state.page.update()

    def clear_output(_e):
        clear_log(log)
        state.page.update()

    def run_classifier(_e):
        if state.warn_busy():
            return
        path = (path_field.value or "").strip()
        if not path:
            state.show_snackbar("Please choose a folder first.")
            return
        state.persist_path("classifier_path", path)
        clear_log(log)
        set_running(True)

        worker = JavClassifier(path, lookup_delay_seconds=state.javlib_pause_seconds())
        append_line, _, drain_log = make_buffered_log_sink(state.page, log)

        def on_result(line: str) -> None:
            append_line(line)

        def on_finished() -> None:
            def done_ui() -> None:
                drain_log()
                set_running(False)
                state.end_task()
                state.show_snackbar("Classification finished.")

            schedule_ui(state.page, done_ui)

        state.begin_task(worker, TASK_NAME)
        worker.start(on_result=on_result, on_finished=on_finished)

    def stop_classifier(_e):
        state.busy.request_stop()

    run_btn.on_click = run_classifier
    stop_btn.on_click = stop_classifier
    clear_btn.on_click = clear_output

    body = side_log_layout(
        state.page,
        [
            path_row,
            primary_actions_row(run_btn, stop_btn, clear_btn),
            javlib_pause_advanced(state, pause_field),
        ],
        log,
        title="Output",
    )

    return ft.Column([body], expand=True)
