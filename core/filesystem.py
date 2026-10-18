import os
import shutil
from pathlib import Path
from typing import Callable

MessageFn = Callable[[str], None]


def ensure_directory(
    path: str | Path,
    on_message: MessageFn | None = None,
    *,
    quiet: bool = True,
) -> None:
    if os.path.exists(path):
        return
    try:
        os.makedirs(path, exist_ok=True)
        if not quiet and on_message:
            on_message(f"Successfully created the directory {path}")
    except OSError as error:
        if on_message:
            on_message(f"Directory {path} failed to be created: {error}")


def move_file(
    src: str | Path,
    dest: str | Path,
    on_message: MessageFn | None = None,
    *,
    quiet: bool = True,
) -> None:
    try:
        shutil.move(str(src), str(dest))
        if not quiet and on_message:
            on_message(f"Moved {src} to {dest}")
    except OSError as error:
        if on_message:
            on_message(f"Failed to move {src} to {dest}: {error}")
