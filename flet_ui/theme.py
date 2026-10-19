import flet as ft

from core.settings import UI_THEME_CHOICES


def panel_bgcolor() -> str:
    """Subtle panel fill (Flet 0.27 has no SURFACE_CONTAINER_LOW)."""
    return ft.Colors.with_opacity(0.06, ft.Colors.ON_SURFACE)


def theme_mode_for_setting(value: str) -> ft.ThemeMode:
    key = (value or "system").lower()
    if key == "light":
        return ft.ThemeMode.LIGHT
    if key == "dark":
        return ft.ThemeMode.DARK
    return ft.ThemeMode.SYSTEM


def build_theme_dropdown(state, width: int = 120) -> ft.Dropdown:
    return ft.Dropdown(
        width=width,
        dense=True,
        value=state.settings.ui_theme if state.settings.ui_theme in UI_THEME_CHOICES else "system",
        options=[
            ft.dropdown.Option("light", "Light"),
            ft.dropdown.Option("dark", "Dark"),
            ft.dropdown.Option("system", "System"),
        ],
        on_change=lambda e: state.set_ui_theme(e.control.value or "system"),
    )
