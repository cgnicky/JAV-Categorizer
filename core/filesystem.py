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


def classification_destination(base_path: Path, filename: str, actor_name: str) -> Path:
    """Target folder for classifier / actor searcher (LUXU/GANA series or actor name)."""
    upper = filename.upper()
    if "LUXU" in upper:
        return base_path / "LUXU-Series"
    if "GANA" in upper:
        return base_path / "GANA-Series"
    return base_path / actor_name


def move_classified_file(
    base_path: Path,
    filename: str,
    actor_name: str,
    on_message: MessageFn | None = None,
) -> str:
    """Move one media file using the same rules as the JAV classifier."""
    src = base_path / filename
    if not src.is_file():
        return f"Missing: {filename}"

    dest_dir = classification_destination(base_path, filename, actor_name)
    ensure_directory(dest_dir, on_message)
    target_file = dest_dir / filename
    if target_file.is_file():
        dest_dir = base_path / "Existed"
        ensure_directory(dest_dir, on_message)
        move_file(src, dest_dir, on_message)
        return f"Moved duplicate: {filename} -> Existed/"

    move_file(src, dest_dir, on_message)
    return f"Moved: {filename} -> {dest_dir.name}/"
