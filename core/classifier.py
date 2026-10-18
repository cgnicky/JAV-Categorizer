import os
from pathlib import Path
from typing import Callable

from core.actor_lookup import ActorLookup
from core.db import (
    DEFAULT_DB_PATH,
    clear_classification_progress,
    count_pending_progress,
    save_classification_progress,
)
from core.filesystem import ensure_directory, move_file
from core.lookup_errors import RateLimitedError, SearchStoppedError
from core.title_utils import MEDIA_EXTENSIONS, extract_code

MessageFn = Callable[[str], None]


class ClassifierService:
    def __init__(
        self,
        path: str,
        on_message: MessageFn,
        should_stop: Callable[[], bool] | None = None,
        lookup_delay_seconds: float = 0.0,
        db_path: str | Path | None = None,
    ):
        self.path = path
        self.on_message = on_message
        self.should_stop = should_stop or (lambda: False)
        self.lookup_delay_seconds = lookup_delay_seconds
        self.db_path = db_path if db_path is not None else DEFAULT_DB_PATH
        self.lookup: ActorLookup | None = None

    def move_files(
        self,
        base_path: Path,
        filename: str,
        title: str,
        lookup: ActorLookup,
    ) -> None:
        src = base_path / filename
        try:
            actor_name = lookup.lookup(title, media_path=src)
        except SearchStoppedError:
            raise
        except RateLimitedError as error:
            save_classification_progress(
                base_path,
                filename,
                title,
                status="rate_limited",
                note=str(error),
                db_path=self.db_path,
            )
            raise

        if "LUXU" in filename.upper():
            dest = base_path / "LUXU-Series"
        elif "GANA" in filename.upper():
            dest = base_path / "GANA-Series"
        else:
            dest = base_path / actor_name
        ensure_directory(dest, self.on_message)
        target_file = dest / filename
        if not target_file.is_file():
            move_file(src, dest, self.on_message)
        else:
            existed_dest = base_path / "Existed"
            ensure_directory(existed_dest, self.on_message)
            move_file(src, existed_dest, self.on_message)
        clear_classification_progress(base_path, filename, self.db_path)

    def run(self) -> None:
        base_path = Path(self.path)
        if not base_path.is_dir():
            self.on_message(f"Invalid source path: {self.path}")
            return

        pending = count_pending_progress(base_path, self.db_path)
        if pending:
            self.on_message(
                f"Resuming: {pending} file(s) marked from a previous run "
                "(lookups saved in javlist.db where possible)."
            )

        self.lookup = ActorLookup(
            self.on_message,
            db_path=self.db_path,
            web_delay_seconds=self.lookup_delay_seconds,
            should_stop=self.should_stop,
        )
        lookup = self.lookup
        try:
            for filename in sorted(os.listdir(base_path)):
                if self.should_stop():
                    self.on_message("Stopped by user.")
                    break
                file_path = base_path / filename
                if not file_path.is_file():
                    continue
                self.on_message(f"Processing: [{filename}] ...")
                stem, ext = os.path.splitext(filename)
                if ext.lower() not in MEDIA_EXTENSIONS:
                    self.on_message("Extension not supported!")
                    continue
                title = extract_code(stem) or stem
                try:
                    self.move_files(base_path, filename, title, lookup)
                except SearchStoppedError:
                    self.on_message("Stopped by user or browser closed.")
                    break
                except RateLimitedError:
                    self.on_message(
                        "Stopped: JavLibrary rate limit. Progress saved — "
                        "run again later; known actors are already in javlist.db."
                    )
                    break
            else:
                self.on_message("Process all completed !")
        finally:
            lookup.close()
            self.lookup = None
