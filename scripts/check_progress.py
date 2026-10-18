"""Inspect classification_progress in javlist.db. Run: uv run python -m scripts.check_progress"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.db import DEFAULT_DB_PATH, PROGRESS_TABLE  # noqa: E402


def main() -> int:
    db_path = DEFAULT_DB_PATH
    if not db_path.is_file():
        print(f"No database at {db_path.resolve()}")
        return 1

    conn = sqlite3.connect(db_path)
    try:
        exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (PROGRESS_TABLE,),
        ).fetchone()
        if not exists:
            print(f"Table {PROGRESS_TABLE} does not exist (open app once to create schema).")
            return 1

        total = conn.execute(f"SELECT COUNT(*) FROM {PROGRESS_TABLE}").fetchone()[0]
        print(f"Database: {db_path.resolve()}")
        print(f"Table: {PROGRESS_TABLE} — {total} row(s)\n")

        by_status = conn.execute(
            f"SELECT status, COUNT(*) FROM {PROGRESS_TABLE} GROUP BY status ORDER BY status"
        ).fetchall()
        print("By status:")
        for status, count in by_status:
            print(f"  {status}: {count}")

        rows = conn.execute(
            f"""
            SELECT source_dir, filename, code, actor, status, note, updated_at
            FROM {PROGRESS_TABLE}
            ORDER BY updated_at DESC
            LIMIT 50
            """
        ).fetchall()
        if rows:
            print("\nLatest rows (newest first):")
            for row in rows:
                print("  ---")
                print(f"  dir:      {row[0]}")
                print(f"  file:     {row[1]}")
                print(f"  code:     {row[2]}")
                print(f"  actor:    {row[3] or '(empty)'}")
                print(f"  status:   {row[4]}")
                print(f"  note:     {row[5] or ''}")
                print(f"  updated:  {row[6]}")
        else:
            print("\nNo rows yet.")

        resolved_with_actor = conn.execute(
            f"""
            SELECT COUNT(*) FROM {PROGRESS_TABLE}
            WHERE status = 'resolved' AND actor IS NOT NULL AND TRIM(actor) != ''
            """
        ).fetchone()[0]
        rate_limited = conn.execute(
            f"SELECT COUNT(*) FROM {PROGRESS_TABLE} WHERE status = 'rate_limited'"
        ).fetchone()[0]
        print(f"\nSummary: {resolved_with_actor} resolved (with actor), {rate_limited} rate_limited")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
