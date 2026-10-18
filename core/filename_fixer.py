import os
from dataclasses import dataclass
from pathlib import Path

from core.title_utils import MEDIA_EXTENSIONS, extract_code, is_valid_code_filename, media_extension


@dataclass
class RenameItem:
    src_name: str
    dest_name: str
    checked: bool = True


def propose_rename(filename: str) -> str | None:
    ext = media_extension(filename)
    if ext not in MEDIA_EXTENSIONS:
        return None
    if is_valid_code_filename(filename):
        return None
    code = extract_code(filename)
    if not code:
        return None
    proposed = f"{code}{ext}"
    if proposed == filename:
        return None
    return proposed


def scan_directory(path: str | Path) -> list[RenameItem]:
    directory = Path(path)
    if not directory.is_dir():
        return []

    items: list[RenameItem] = []
    for entry in sorted(directory.iterdir()):
        if not entry.is_file():
            continue
        proposed = propose_rename(entry.name)
        if proposed is None:
            continue
        items.append(RenameItem(src_name=entry.name, dest_name=proposed, checked=True))
    return items


def apply_renames(path: str | Path, items: list[RenameItem]) -> list[str]:
    directory = Path(path)
    messages: list[str] = []
    for item in items:
        if not item.checked:
            continue
        src = directory / item.src_name
        dest = directory / item.dest_name
        if not src.is_file():
            messages.append(f"Missing: {item.src_name}")
            continue
        if dest.exists():
            messages.append(f"Skipped (exists): {item.src_name} -> {item.dest_name}")
            continue
        try:
            os.rename(src, dest)
            messages.append(f"Renamed: {item.src_name} -> {item.dest_name}")
        except OSError as error:
            messages.append(f"Failed: {item.src_name}: {error}")
    return messages
