import flet as ft

from flet_ui.schedule import schedule_ui
from flet_ui.state import PLACEHOLDER_KEYWORDS
from flet_ui.widgets.layout import LABEL_SIZE, primary_actions_row, side_log_layout
from flet_ui.widgets.log_panel import clear_log, make_buffered_log_sink, make_log_field
from workers.query_worker import JavQuery

TASK_NAME = "Media Query"


def build_query_tab(state) -> ft.Column:
    keywords = ft.TextField(
        value=PLACEHOLDER_KEYWORDS,
        hint_text="Title or code…",
        expand=True,
        text_size=LABEL_SIZE,
    )
    record_count = ft.Text("0 results", size=12)
    results = make_log_field()
    search_btn = ft.FilledButton("Search")
    clear_btn = ft.TextButton("Clear", style=ft.ButtonStyle(text_style=ft.TextStyle(size=12)))
    title_radio = ft.Radio(value="label", label="Title")
    actor_radio = ft.Radio(value="actor", label="Actor")
    search_type = ft.RadioGroup(content=ft.Row([title_radio, actor_radio]), value="label")

    def on_focus(_e: ft.ControlEvent) -> None:
        if keywords.value == PLACEHOLDER_KEYWORDS:
            keywords.value = ""
            state.page.update()

    keywords.on_focus = on_focus

    def clear_results(_e):
        clear_log(results)
        record_count.value = "0 results"
        state.page.update()

    def run_query(_e):
        if state.warn_busy():
            return
        if not search_type.value:
            state.show_info("Error!", "No Type Selected!")
            return
        clear_log(results)
        record_count.value = "0 results"
        search_btn.disabled = True
        state.page.update()

        worker = JavQuery(keywords.value, search_type.value)
        append_line, _, drain_log = make_buffered_log_sink(state.page, results)

        def on_result(line: str) -> None:
            append_line(line)

        def on_count(count: int) -> None:
            schedule_ui(
                state.page,
                lambda c=count: (setattr(record_count, "value", f"{c} results"), state.page.update()),
            )

        def on_finished() -> None:
            schedule_ui(
                state.page,
                lambda: (
                    drain_log(),
                    setattr(search_btn, "disabled", False),
                    state.end_task(),
                    state.page.update(),
                ),
            )

        state.begin_task(worker, TASK_NAME)
        worker.start(on_result=on_result, on_count=on_count, on_finished=on_finished)

    search_btn.on_click = run_query
    clear_btn.on_click = clear_results

    body = side_log_layout(
        state.page,
        [
            ft.Row(
                [
                    search_type,
                    keywords,
                    search_btn,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            primary_actions_row(clear_btn, record_count),
        ],
        results,
        title="Results",
        work_flex=4,
        log_flex=5,
    )

    return ft.Column([body], expand=True)
