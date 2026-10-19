"""Shared layout helpers for tabs."""

import flet as ft

from flet_ui.theme import panel_bgcolor

LABEL_SIZE = 13
CAPTION_SIZE = 11
SECTION_SIZE = 12
SIDE_LOG_COLLAPSED = 48


def section_title(text: str) -> ft.Text:
    return ft.Text(text, size=SECTION_SIZE, weight=ft.FontWeight.W_600)


def section_divider() -> ft.Divider:
    return ft.Divider(height=1)


def folder_path_row(
    state,
    *,
    label: str,
    value: str = "",
    hint: str = "Select a folder…",
    persist_field: str | None = None,
) -> tuple[ft.TextField, ft.Row]:
    field = ft.TextField(value=value, hint_text=hint, expand=True, text_size=LABEL_SIZE)
    row = ft.Row(
        [
            ft.Text(label, size=LABEL_SIZE, width=72),
            field,
            ft.OutlinedButton("Browse", on_click=lambda _e: state.browse_into(field, persist_field)),
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    return field, row


def javlib_pause_advanced(state, pause_field: ft.TextField) -> ft.ExpansionTile:
    return ft.ExpansionTile(
        tile_padding=ft.padding.symmetric(horizontal=4, vertical=0),
        title=ft.Text("Advanced", size=12, weight=ft.FontWeight.W_500),
        subtitle=ft.Text(
            "JavLibrary delay between requests",
            size=CAPTION_SIZE,
            color=ft.Colors.ON_SURFACE_VARIANT,
        ),
        controls=[
            ft.Row(
                [
                    ft.Text("Pause (s)", size=CAPTION_SIZE, width=72),
                    pause_field,
                ]
            ),
        ],
        initially_expanded=False,
        dense=True,
    )


def primary_actions_row(*buttons: ft.Control) -> ft.Row:
    return ft.Row(list(buttons), spacing=8, wrap=True)


def side_log_layout(
    page: ft.Page,
    work_controls: list[ft.Control],
    log_field: ft.TextField,
    *,
    title: str = "Output",
    work_flex: int = 5,
    log_flex: int = 4,
) -> ft.Row:
    """Main controls on the left; collapsible log panel on the right."""
    panel_open = {"value": True}

    header_title = ft.Text(title, size=SECTION_SIZE, weight=ft.FontWeight.W_600)
    collapse_btn = ft.IconButton(
        icon=ft.Icons.KEYBOARD_DOUBLE_ARROW_RIGHT,
        icon_size=18,
        tooltip="Collapse log panel",
        style=ft.ButtonStyle(padding=4),
    )

    log_field.expand = True
    log_field.text_size = CAPTION_SIZE

    log_body = ft.Column(
        [
            ft.Row(
                [header_title, collapse_btn],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            log_field,
        ],
        expand=True,
        spacing=6,
    )

    expand_btn = ft.IconButton(
        icon=ft.Icons.KEYBOARD_DOUBLE_ARROW_LEFT,
        icon_size=18,
        tooltip="Expand log panel",
        style=ft.ButtonStyle(padding=4),
    )
    collapsed_strip = ft.Column(
        [
            expand_btn,
            ft.Text("Log", size=CAPTION_SIZE, weight=ft.FontWeight.W_500),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=0,
    )

    log_panel = ft.Container(
        content=log_body,
        expand=log_flex,
        padding=10,
        border_radius=8,
        bgcolor=panel_bgcolor(),
        border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
    )

    work_column = ft.Column(work_controls, expand=work_flex, spacing=10, scroll=ft.ScrollMode.AUTO)
    divider = ft.VerticalDivider(width=1, color=ft.Colors.OUTLINE_VARIANT)

    def apply_panel_state() -> None:
        if panel_open["value"]:
            log_panel.content = log_body
            log_panel.expand = log_flex
            log_panel.width = None
            work_column.expand = work_flex
        else:
            log_panel.content = collapsed_strip
            log_panel.expand = None
            log_panel.width = SIDE_LOG_COLLAPSED
            work_column.expand = True

    def open_panel(_e) -> None:
        panel_open["value"] = True
        apply_panel_state()
        page.update()

    def close_panel(_e) -> None:
        panel_open["value"] = False
        apply_panel_state()
        page.update()

    collapse_btn.on_click = close_panel
    expand_btn.on_click = open_panel
    apply_panel_state()

    return ft.Row(
        [
            work_column,
            divider,
            log_panel,
        ],
        expand=True,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        spacing=10,
    )
