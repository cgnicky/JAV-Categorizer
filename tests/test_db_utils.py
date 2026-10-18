from pathlib import Path

from core.db import (
    PROGRESS_TABLE,
    TABLE_NAME,
    clear_classification_progress,
    count_pending_progress,
    establish_to_db,
    lookup_actor_from_db,
    save_actor_record,
    save_classification_progress,
)


def test_establish_to_db_creates_schema(tmp_path: Path):
    db_file = tmp_path / "test.db"
    conn = establish_to_db(db_file)
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (TABLE_NAME,),
        )
        assert cur.fetchone()[0] == TABLE_NAME
    finally:
        conn.close()


def test_lookup_actor_from_db_exact_and_prefix(tmp_path: Path):
    db_file = tmp_path / "lookup.db"
    conn = establish_to_db(db_file)
    conn.execute(
        "INSERT INTO javlist (actor, label, timestamp, path) VALUES (?, ?, ?, ?)",
        ("Yua", "SSIS-001", "2026-01-01", "/a.mp4"),
    )
    conn.execute(
        "INSERT INTO javlist (actor, label, timestamp, path) VALUES (?, ?, ?, ?)",
        ("Others", "ABC-999", "2026-01-01", "/b.mp4"),
    )
    conn.commit()
    conn.close()

    assert lookup_actor_from_db("SSIS-001", db_file) == "Yua"
    assert lookup_actor_from_db("ssis-001", db_file) == "Yua"
    assert lookup_actor_from_db("SSIS-001 extra title", db_file) == "Yua"
    assert lookup_actor_from_db("ABC-999", db_file) is None
    assert lookup_actor_from_db("missing", db_file) is None


def test_save_actor_record_upserts(tmp_path: Path):
    db_file = tmp_path / "upsert.db"
    save_actor_record("SSIS-100", "Actor One", "/a.mp4", db_file)
    save_actor_record("SSIS-100", "Actor Two", "", db_file)
    assert lookup_actor_from_db("SSIS-100", db_file) == "Actor Two"


def test_classification_progress(tmp_path: Path):
    db_file = tmp_path / "progress.db"
    root = tmp_path / "inbox"
    root.mkdir()
    save_classification_progress(
        root,
        "A.mp4",
        "SSIS-1",
        status="rate_limited",
        note="limit",
        db_path=db_file,
    )
    assert count_pending_progress(root, db_file) == 1
    clear_classification_progress(root, "A.mp4", db_file)
    assert count_pending_progress(root, db_file) == 0

    conn = establish_to_db(db_file)
    cur = conn.execute(
        f"SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (PROGRESS_TABLE,),
    )
    assert cur.fetchone()[0] == PROGRESS_TABLE
    conn.close()
