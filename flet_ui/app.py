"""Flet desktop application shell."""

import flet as ft

from flet_ui.state import AppState
from flet_ui.tabs.actor import build_actor_tab
from flet_ui.tabs.classifier import build_classifier_tab
from flet_ui.tabs.fixer import build_fixer_tab
from flet_ui.tabs.query import build_query_tab
from flet_ui.tabs.updater import build_updater_tab
from flet_ui.theme import build_theme_dropdown


def _styled_tabs(state: AppState) -> ft.Tabs:
    return ft.Tabs(
        selected_index=0,
        expand=True,
        scrollable=True,
        tab_alignment=ft.TabAlignment.START,
        animation_duration=200,
        indicator_color=ft.Colors.PRIMARY,
        indicator_border_radius=8,
        indicator_thickness=3,
        divider_color=ft.Colors.OUTLINE_VARIANT,
        label_color=ft.Colors.PRIMARY,
        unselected_label_color=ft.Colors.ON_SURFACE_VARIANT,
        overlay_color={ft.ControlState.HOVERED: ft.Colors.with_opacity(0.06, ft.Colors.PRIMARY)},
        label_text_style=ft.TextStyle(size=13, weight=ft.FontWeight.W_600),
        unselected_label_text_style=ft.TextStyle(size=13, weight=ft.FontWeight.W_400),
        tabs=[
            ft.Tab(text="Classifier", content=build_classifier_tab(state)),
            ft.Tab(text="Media Query", content=build_query_tab(state)),
            ft.Tab(text="DB Updater", content=build_updater_tab(state)),
            ft.Tab(text="Filename Fixer", content=build_fixer_tab(state)),
            ft.Tab(text="Actor Search", content=build_actor_tab(state)),
        ],
    )


def main(page: ft.Page) -> None:
    page.title = "JAV Tool"
    page.window.width = 960
    page.window.height = 640
    page.window.min_width = 720
    page.window.min_height = 520
    page.padding = 12

    state = AppState(page)
    busy_status = ft.Text("Ready", size=11, italic=True, color=ft.Colors.ON_SURFACE_VARIANT)
    state.attach_busy_status(busy_status)

    page.appbar = ft.AppBar(
        title=ft.Text("JAV Tool", size=17, weight=ft.FontWeight.W_600),
        center_title=False,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        elevation=0,
        actions=[
            ft.Container(
                content=ft.Row(
                    [
                        ft.Text("Theme", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                        build_theme_dropdown(state, width=108),
                    ],
                    spacing=6,
                ),
                padding=ft.padding.only(right=8),
            ),
        ],
    )

    page.add(
        ft.Column(
            [
                busy_status,
                _styled_tabs(state),
            ],
            expand=True,
            spacing=6,
        )
    )
    page.update()
