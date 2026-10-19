import flet as ft

from core.logging_config import setup_logging
from flet_ui.app import main


def boot() -> None:
    setup_logging()
    ft.app(target=main)


if __name__ == "__main__":
    boot()
