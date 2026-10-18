import sqlite3
from pathlib import Path

from core.db import TABLE_NAME, establish_to_db


def search_media(
    keyword: str,
    search_type: str,
    db_path: str | Path | None = None,
) -> tuple[int, list[tuple[str, str]]]:
    if search_type == "label":
        sql = f"SELECT actor, label FROM {TABLE_NAME} WHERE label LIKE ? ORDER BY label"
    elif search_type == "actor":
        sql = f"SELECT actor, label FROM {TABLE_NAME} WHERE actor LIKE ? ORDER BY label"
    else:
        raise ValueError(f"Unknown search type: {search_type}")

    conn = establish_to_db(db_path)
    try:
        cur = conn.cursor()
        cur.execute(sql, (f"%{keyword}%",))
        rows = cur.fetchall()
        return len(rows), rows
    finally:
        conn.close()


def run_query(
    keyword: str,
    search_type: str,
    db_path: str | Path | None = None,
) -> tuple[int, list[str]]:
    try:
        count, rows = search_media(keyword, search_type, db_path)
    except (sqlite3.Error, ValueError) as error:
        return 0, [f"Database error: {error}"]

    if count == 0:
        return 0, ["No Records Found!"]
    lines = [f"{actor}, {label}" for actor, label in rows]
    return count, lines
