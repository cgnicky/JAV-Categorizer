from pathlib import Path
from unittest.mock import MagicMock

from core.db import establish_to_db
from core.query import search_media
from core.updater import BATCH_SIZE, get_media_list, update_to_db


def test_get_media_list_skips_non_video(tmp_path: Path):
    actor_dir = tmp_path / "Actor"
    actor_dir.mkdir()
    (actor_dir / "SSIS-001.mp4").write_bytes(b"a")
    (actor_dir / "readme.txt").write_text("x", encoding="utf-8")

    rows = get_media_list(tmp_path)
    assert len(rows) == 1
    assert rows[0][0] == "Actor"
    assert rows[0][1] == "SSIS-001"


def test_update_to_db_batches():
    cur = MagicMock()
    rows = [
        ["A", f"L-{i}", "ts", f"/p/{i}.mp4"] for i in range(BATCH_SIZE + 2)
    ]
    progress = []

    update_to_db(cur, rows, on_progress=progress.append)

    assert cur.executemany.call_count == 2
    assert progress == [BATCH_SIZE, BATCH_SIZE + 2]


def test_search_media_roundtrip(tmp_path: Path):
    db_file = tmp_path / "roundtrip.db"
    conn = establish_to_db(db_file)
    conn.execute(
        "INSERT INTO javlist (actor, label, timestamp, path) VALUES (?, ?, ?, ?)",
        ("Yua", "SSIS-001", "2026-01-01", "/path/a.mp4"),
    )
    conn.commit()
    conn.close()

    count, rows = search_media("Yua", "actor", db_file)
    assert count == 1
    assert rows == [("Yua", "SSIS-001")]
