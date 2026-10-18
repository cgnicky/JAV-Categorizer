import datetime
import os
import sqlite3
from pathlib import Path
from typing import Callable

from core.db import BATCH_SIZE, INSERT_QUERY, establish_to_db
from core.title_utils import MEDIA_EXTENSIONS

ProgressFn = Callable[[int], None]
MessageFn = Callable[[str], None]


def get_media_list(directory: str | Path) -> list[list[str]]:
    result_list: list[list[str]] = []
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    root = Path(directory)

    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in MEDIA_EXTENSIONS:
                continue
            elem = os.path.join(dirpath, filename)
            media_name = os.path.splitext(filename)[0]
            actor_name = os.path.basename(dirpath)
            if actor_name != "Downloading":
                result_list.append([actor_name, media_name, ts, elem])
    return result_list


def update_to_db(
    cur: sqlite3.Cursor,
    row_list: list[list[str]],
    on_progress: ProgressFn | None = None,
) -> None:
    total = len(row_list)
    if total == 0:
        if on_progress:
            on_progress(0)
        return
    for start in range(0, total, BATCH_SIZE):
        batch = row_list[start : start + BATCH_SIZE]
        cur.executemany(INSERT_QUERY, [tuple(row) for row in batch])
        if on_progress:
            on_progress(min(start + len(batch), total))


def run_update(
    directory: str | Path,
    on_message: MessageFn | None = None,
    on_progress: ProgressFn | None = None,
    on_max: Callable[[int], None] | None = None,
    db_path: str | Path | None = None,
) -> list[str]:
    messages: list[str] = []
    data_list = get_media_list(directory)
    if on_message:
        on_message(f"Working on {directory}")
    if on_max:
        on_max(len(data_list))

    conn = None
    try:
        if on_message:
            on_message("Connecting to the SQLite database...")
        conn = establish_to_db(db_path)
        cur = conn.cursor()
        update_to_db(cur, data_list, on_progress)
        conn.commit()
        cur.close()
        messages.append(f"Updated {len(data_list)} media records.")
    except sqlite3.Error as error:
        messages.append(f"Database error: {error}")
    finally:
        if conn is not None:
            conn.close()
            messages.append("Database connection closed.")
    return messages
