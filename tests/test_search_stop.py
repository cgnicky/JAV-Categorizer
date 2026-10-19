from pathlib import Path
from unittest.mock import MagicMock

from core.actor_lookup import ActorLookup
from core.actor_searcher import group_files_by_actor
from core.lookup_errors import SearchStoppedError


def test_group_files_stops_on_search_stopped(tmp_path: Path):
    lookup = MagicMock(spec=ActorLookup)
    lookup.lookup.side_effect = SearchStoppedError("Stopped")

    db_file = tmp_path / "empty.db"
    from core.db import establish_to_db

    establish_to_db(db_file).close()
    groups = group_files_by_actor(tmp_path, ["A.mp4", "B.mp4"], lookup, db_path=db_file)

    assert groups == []
    assert lookup.lookup.call_count == 1


def test_group_files_stops_during_database_resolution(tmp_path: Path):
    db_file = tmp_path / "db.db"
    from core.db import establish_to_db, save_actor_record

    establish_to_db(db_file).close()
    save_actor_record("SSIS-001", "Actor One", db_path=db_file)
    save_actor_record("SSIS-002", "Actor Two", db_path=db_file)
    (tmp_path / "SSIS-001.mp4").write_bytes(b"x")
    (tmp_path / "SSIS-002.mp4").write_bytes(b"x")

    messages: list[str] = []
    stop_after = {"count": 0}

    def should_stop() -> bool:
        stop_after["count"] += 1
        return stop_after["count"] > 1

    groups = group_files_by_actor(
        tmp_path,
        ["SSIS-001.mp4", "SSIS-002.mp4"],
        None,
        on_message=messages.append,
        db_path=db_file,
        should_stop=should_stop,
    )

    assert len(groups) == 1
    assert groups[0].files == ["SSIS-001.mp4"]
    assert any("Search stopped" in line for line in messages)


def test_actor_lookup_request_stop_sets_flag(tmp_path: Path):
    db_file = tmp_path / "db.db"
    from core.db import establish_to_db

    establish_to_db(db_file).close()
    lookup = ActorLookup(db_path=db_file)
    lookup.request_stop()
    assert lookup._stop_requested is True
