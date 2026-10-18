import shutil
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from core.actor_lookup import ActorLookup
from core.db import (
    DEFAULT_DB_PATH,
    mark_file_resolved,
    resolve_actor_for_file,
    save_classification_progress,
)
from core.lookup_errors import RateLimitedError, SearchStoppedError
from core.title_utils import extract_code

MessageFn = Callable[[str], None]


@dataclass
class ActorGroup:
    actor: str
    files: list[str] = field(default_factory=list)
    checked: bool = True


def scan_first_level_mp4(path: str | Path) -> list[str]:
    directory = Path(path)
    if not directory.is_dir():
        return []
    return sorted(
        entry.name
        for entry in directory.iterdir()
        if entry.is_file() and entry.suffix.lower() == ".mp4"
    )


def _groups_from_map(grouped: dict[str, list[str]]) -> list[ActorGroup]:
    return [
        ActorGroup(actor=actor, files=files, checked=True)
        for actor, files in sorted(grouped.items(), key=lambda item: item[0].lower())
    ]


def group_files_by_actor(
    path: str | Path,
    filenames: list[str],
    lookup: ActorLookup | None,
    on_message: MessageFn | None = None,
    db_path: str | Path | None = None,
) -> list[ActorGroup]:
    directory = Path(path)
    resolved_db = db_path if db_path is not None else DEFAULT_DB_PATH
    grouped: dict[str, list[str]] = defaultdict(list)
    pending: list[str] = []

    for filename in filenames:
        code = extract_code(filename) or Path(filename).stem
        cached = resolve_actor_for_file(directory, filename, code, resolved_db)
        if cached:
            grouped[cached].append(filename)
            mark_file_resolved(directory, filename, code, cached, resolved_db)
            if on_message:
                on_message(f"From database: {filename} ({code}) -> {cached}")
            continue
        pending.append(filename)

    if on_message and filenames:
        skipped = len(filenames) - len(pending)
        if skipped:
            on_message(
                f"Skipped {skipped} file(s) already in javlist.db / saved progress; "
                f"{len(pending)} need JavLibrary."
            )

    if not pending:
        return _groups_from_map(grouped)

    if lookup is None:
        if on_message:
            on_message("No JavLibrary client for pending files.")
        return _groups_from_map(grouped)

    for filename in pending:
        code = extract_code(filename) or Path(filename).stem
        if on_message:
            on_message(f"JavLibrary: {filename} ({code})")
        media_path = directory / filename
        try:
            actor = lookup.lookup(code, media_path=media_path) or "Others"
        except SearchStoppedError:
            if on_message:
                on_message("Search stopped (terminate or browser closed).")
            break
        except RateLimitedError as error:
            save_classification_progress(
                directory,
                filename,
                code,
                status="rate_limited",
                note=str(error),
                db_path=resolved_db,
            )
            if on_message:
                on_message(
                    "Rate limit on this file — partial results kept. "
                    "Scan again: completed files stay in the database and will be skipped."
                )
            break
        grouped[actor].append(filename)
        if actor.lower() != "others":
            mark_file_resolved(directory, filename, code, actor, resolved_db)

    return _groups_from_map(grouped)


def move_actor_groups(path: str | Path, groups: list[ActorGroup]) -> list[str]:
    directory = Path(path)
    messages: list[str] = []
    for group in groups:
        if not group.checked:
            continue
        dest_dir = directory / group.actor
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            messages.append(f"Failed to create {dest_dir}: {error}")
            continue
        for filename in group.files:
            src = directory / filename
            dest = dest_dir / filename
            if not src.is_file():
                messages.append(f"Missing: {filename}")
                continue
            if dest.exists():
                messages.append(f"Skipped (exists): {filename} -> {group.actor}/")
                continue
            try:
                shutil.move(str(src), str(dest))
                messages.append(f"Moved: {filename} -> {group.actor}/")
            except OSError as error:
                messages.append(f"Failed: {filename}: {error}")
    return messages


def scan_and_group(
    path: str | Path,
    on_message: MessageFn | None = None,
    lookup_factory: Callable[[MessageFn | None], ActorLookup] | None = None,
    db_path: str | Path | None = None,
    lookup_delay_seconds: float = 0.0,
    should_stop: Callable[[], bool] | None = None,
) -> list[ActorGroup]:
    filenames = scan_first_level_mp4(path)
    resolved_db = db_path if db_path is not None else DEFAULT_DB_PATH
    stop = should_stop or (lambda: False)

    def default_factory(msg: MessageFn | None) -> ActorLookup:
        return ActorLookup(
            msg,
            db_path=resolved_db,
            web_delay_seconds=lookup_delay_seconds,
            should_stop=stop,
        )

    factory = lookup_factory or default_factory

    needs_web = any(
        resolve_actor_for_file(path, name, extract_code(name) or Path(name).stem, resolved_db)
        is None
        for name in filenames
    )

    lookup_client: ActorLookup | None = None
    if needs_web:
        lookup_client = factory(on_message)
    try:
        return group_files_by_actor(
            path,
            filenames,
            lookup_client,
            on_message,
            db_path=resolved_db,
        )
    finally:
        if lookup_client is not None:
            lookup_client.close()
