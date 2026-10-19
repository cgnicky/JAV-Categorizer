import flet as ft

from core.actor_searcher import ActorGroup, count_move_tasks, scan_first_level_mp4
from core.db import DEFAULT_DB_PATH
from flet_ui.schedule import schedule_ui
from flet_ui.widgets.layout import (
    CAPTION_SIZE,
    folder_path_row,
    javlib_pause_advanced,
    primary_actions_row,
    section_title,
    side_log_layout,
)
from flet_ui.widgets.log_panel import append_log, clear_log, make_buffered_log_sink, make_log_field
from workers.actor_move_worker import ActorMoveWorker
from workers.actor_search_worker import ActorSearchWorker

SCAN_TASK = "Actor Search"
MOVE_TASK = "Move files"


def build_actor_tab(state) -> ft.Column:
    path_field, path_row = folder_path_row(
        state,
        label="Folder",
        value=state.settings.actor_path or "",
        persist_field="actor_path",
    )
    log = make_log_field()
    groups_col = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
    actor_groups: list[ActorGroup] = []
    group_checks: list[ft.Checkbox] = []
    header_sync = {"flag": False}
    header_check = ft.Checkbox(disabled=True)
    scan_btn = ft.FilledButton("Scan")
    stop_btn = ft.OutlinedButton("Stop", disabled=True)
    move_btn = ft.OutlinedButton("Move selected", disabled=True)
    pause_field = state.make_pause_field()
    move_dialog_holder: dict = {"dlg": None}
    move_progress = ft.ProgressBar(width=400, value=0)
    move_label = ft.Text("Moving files...")

    empty_hint = ft.Text(
        "Scan to list actors.",
        size=CAPTION_SIZE,
        italic=True,
        color=ft.Colors.ON_SURFACE_VARIANT,
    )

    def set_scan_ui(scanning: bool) -> None:
        scan_btn.disabled = scanning
        move_btn.disabled = scanning or not actor_groups
        stop_btn.disabled = not scanning
        header_check.disabled = scanning or not actor_groups
        state.page.update()

    def refresh_header_check() -> None:
        if not actor_groups:
            header_sync["flag"] = True
            header_check.value = False
            header_sync["flag"] = False
            return
        checked = sum(1 for g in actor_groups if g.checked)
        total = len(actor_groups)
        header_sync["flag"] = True
        if checked == 0:
            header_check.value = False
            header_check.tristate = False
        elif checked == total:
            header_check.value = True
            header_check.tristate = False
        else:
            header_check.tristate = True
            header_check.value = None
        header_sync["flag"] = False

    def set_all_checks(checked: bool) -> None:
        for g in actor_groups:
            g.checked = checked
        rebuild_groups()
        refresh_header_check()

    def on_header_change(e: ft.ControlEvent) -> None:
        if header_sync["flag"]:
            return
        val = header_check.value
        if header_check.tristate and val is None:
            set_all_checks(True)
            return
        set_all_checks(bool(val))

    header_check.on_change = on_header_change

    def rebuild_groups() -> None:
        groups_col.controls.clear()
        group_checks.clear()
        if not actor_groups:
            groups_col.controls.append(empty_hint)
        else:
            for group in actor_groups:
                cb = ft.Checkbox(value=group.checked)

                def on_gcheck(_e, g=group, box=cb):
                    g.checked = bool(box.value)
                    refresh_header_check()

                cb.on_change = on_gcheck
                group_checks.append(cb)
                groups_col.controls.append(
                    ft.ExpansionTile(
                        tile_padding=ft.padding.symmetric(horizontal=0, vertical=0),
                        title=ft.Row(
                            [
                                cb,
                                ft.Text(group.actor, size=12, expand=True),
                            ]
                        ),
                        subtitle=ft.Text(
                            f"{len(group.files)} file(s)",
                            size=CAPTION_SIZE,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        controls=[ft.Text(name, size=CAPTION_SIZE) for name in group.files],
                        initially_expanded=False,
                        dense=True,
                    )
                )
        header_check.disabled = not actor_groups
        move_btn.disabled = not actor_groups
        refresh_header_check()
        state.page.update()

    def sync_checks_from_ui() -> None:
        for i, group in enumerate(actor_groups):
            if i < len(group_checks):
                group.checked = bool(group_checks[i].value)

    def on_groups_ready(groups: list) -> None:
        actor_groups.clear()
        actor_groups.extend(groups)
        rebuild_groups()

    def scan_done() -> None:
        state.end_task()
        set_scan_ui(False)

    def run_scan(_e):
        if state.warn_busy():
            return
        path = (path_field.value or "").strip()
        if not path:
            state.show_snackbar("Please select a folder.")
            return
        state.persist_path("actor_path", path)
        clear_log(log)
        actor_groups.clear()
        rebuild_groups()
        set_scan_ui(True)

        worker = ActorSearchWorker(path, lookup_delay_seconds=state.javlib_pause_seconds())
        append_line, _, drain_log = make_buffered_log_sink(state.page, log)

        def on_log(line: str) -> None:
            append_line(line)

        def on_ready(groups: list) -> None:
            schedule_ui(state.page, lambda: on_groups_ready(groups))

        def on_finished() -> None:
            schedule_ui(state.page, lambda: (drain_log(), scan_done()))

        state.begin_task(worker, SCAN_TASK)
        worker.start(on_log=on_log, on_groups_ready=on_ready, on_finished=on_finished)

    def stop_scan(_e):
        state.busy.request_stop()

    def close_move_dialog() -> None:
        dlg = move_dialog_holder["dlg"]
        if dlg is not None:
            dlg.open = False
            move_dialog_holder["dlg"] = None
            state.page.update()

    def after_move() -> None:
        close_move_dialog()
        path = (path_field.value or "").strip()
        remaining = set(scan_first_level_mp4(path))
        kept = [
            ActorGroup(
                g.actor,
                [n for n in g.files if n in remaining],
                g.checked,
            )
            for g in actor_groups
            if any(n in remaining for n in g.files)
        ]
        actor_groups.clear()
        actor_groups.extend(kept)
        rebuild_groups()
        state.end_task()
        scan_btn.disabled = False
        move_btn.disabled = not actor_groups
        state.show_snackbar("Move finished.")
        state.page.update()

    def run_move(_e):
        if state.warn_busy():
            return
        path = (path_field.value or "").strip()
        if not path or not actor_groups:
            state.show_snackbar("Scan a directory first.")
            return
        sync_checks_from_ui()
        snapshot = [ActorGroup(g.actor, list(g.files), g.checked) for g in actor_groups]
        total = count_move_tasks(snapshot)
        if total == 0:
            state.show_snackbar("No files selected to move.")
            return

        move_progress.value = 0
        move_label.value = "Moving files..."
        dlg = ft.AlertDialog(
            title=ft.Text("Moving files"),
            content=ft.Column([move_label, move_progress], tight=True),
            modal=True,
        )
        move_dialog_holder["dlg"] = dlg
        state.page.dialog = dlg
        dlg.open = True
        scan_btn.disabled = True
        move_btn.disabled = True
        state.page.update()

        worker = ActorMoveWorker(path, snapshot, db_path=DEFAULT_DB_PATH)

        def on_progress(current: int, tot: int, filename: str) -> None:
            def upd() -> None:
                move_label.value = f"Moving ({current}/{tot}): {filename}"
                move_progress.value = current / tot if tot else 0
                state.page.update()

            schedule_ui(state.page, upd)

        def on_log_line(line: str) -> None:
            schedule_ui(state.page, lambda: (append_log(log, line), state.page.update()))

        def on_finished() -> None:
            schedule_ui(state.page, after_move)

        state.begin_task(worker, MOVE_TASK)
        worker.start(on_progress=on_progress, on_log=on_log_line, on_finished=on_finished)

    scan_btn.on_click = run_scan
    stop_btn.on_click = stop_scan
    move_btn.on_click = run_move

    rebuild_groups()

    work = [
        path_row,
        primary_actions_row(scan_btn, stop_btn, move_btn),
        javlib_pause_advanced(state, pause_field),
        ft.Row([header_check, ft.Text("Select all actors", size=12)]),
        section_title("Actors"),
        groups_col,
    ]

    body = side_log_layout(state.page, work, log, title="Log", work_flex=5, log_flex=4)

    return ft.Column([body], expand=True)
