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


def test_actor_lookup_request_stop_sets_flag(tmp_path: Path):
    db_file = tmp_path / "db.db"
    from core.db import establish_to_db

    establish_to_db(db_file).close()
    lookup = ActorLookup(db_path=db_file)
    lookup.request_stop()
    assert lookup._stop_requested is True
