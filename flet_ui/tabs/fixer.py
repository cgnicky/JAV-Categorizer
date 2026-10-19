import flet as ft

from core.filename_fixer import RenameItem, apply_renames, scan_directory
from flet_ui.widgets.layout import (
    CAPTION_SIZE,
    folder_path_row,
    primary_actions_row,
    section_title,
    side_log_layout,
)
from flet_ui.widgets.log_panel import append_log, make_log_field


def build_fixer_tab(state) -> ft.Column:
    path_field, path_row = folder_path_row(
        state,
        label="Folder",
        value=state.settings.fixer_path or "",
        persist_field="fixer_path",
    )
    log = make_log_field()
    table_col = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
    empty_hint = ft.Text(
        "Scan to preview renames.",
        size=CAPTION_SIZE,
        italic=True,
        color=ft.Colors.ON_SURFACE_VARIANT,
    )
    rename_items: list[RenameItem] = []
    rename_btn = ft.FilledButton("Rename selected", disabled=True)

    def rebuild_table() -> None:
        table_col.controls.clear()
        if not rename_items:
            table_col.controls.append(empty_hint)
            rename_btn.disabled = True
        else:
            table_col.controls.append(
                ft.Row(
                    [
                        ft.Text("", width=36),
                        ft.Text("Original", size=12, weight=ft.FontWeight.W_600, expand=2),
                        ft.Text("Fixed", size=12, weight=ft.FontWeight.W_600, expand=2),
                    ]
                )
            )
            rename_btn.disabled = False
            for item in rename_items:
                cb = ft.Checkbox(value=item.checked)

                def on_check(_e, it=item, box=cb):
                    it.checked = box.value

                cb.on_change = on_check
                table_col.controls.append(
                    ft.Row(
                        [
                            cb,
                            ft.Text(item.src_name, size=12, expand=2),
                            ft.Text(item.dest_name, size=12, expand=2),
                        ]
                    )
                )
        state.page.update()

    def scan(_e):
        path = (path_field.value or "").strip()
        if not path:
            state.show_snackbar("Please select a folder.")
            return
        state.persist_path("fixer_path", path)
        rename_items.clear()
        rename_items.extend(scan_directory(path))
        rebuild_table()
        append_log(log, f"Found {len(rename_items)} file(s) to fix.")
        state.page.update()

    def select_all(_e):
        for item in rename_items:
            item.checked = True
        rebuild_table()

    def clear_selection(_e):
        for item in rename_items:
            item.checked = False
        rebuild_table()

    def rename(_e):
        path = (path_field.value or "").strip()
        if not path or not rename_items:
            state.show_snackbar("Scan a directory with invalid names first.")
            return
        for row in table_col.controls[1:]:
            if isinstance(row, ft.Row) and row.controls and isinstance(row.controls[0], ft.Checkbox):
                idx = table_col.controls.index(row) - 1
                if 0 <= idx < len(rename_items):
                    rename_items[idx].checked = row.controls[0].value
        for msg in apply_renames(path, rename_items):
            append_log(log, msg)
        scan(_e)

    scan_btn = ft.OutlinedButton("Scan", on_click=scan)
    rename_btn.on_click = rename

    rebuild_table()

    work = [
        path_row,
        primary_actions_row(
            scan_btn,
            ft.TextButton("Select all", on_click=select_all, style=ft.ButtonStyle(text_style=ft.TextStyle(size=12))),
            ft.TextButton(
                "Clear selection",
                on_click=clear_selection,
                style=ft.ButtonStyle(text_style=ft.TextStyle(size=12)),
            ),
            rename_btn,
        ),
        section_title("Preview"),
        table_col,
    ]

    body = side_log_layout(state.page, work, log, title="Log", work_flex=5, log_flex=3)

    return ft.Column([body], expand=True)
