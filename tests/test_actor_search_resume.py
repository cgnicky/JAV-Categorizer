from pathlib import Path
from unittest.mock import MagicMock

from core.actor_searcher import group_files_by_actor, scan_and_group
from core.db import establish_to_db, mark_file_resolved, save_actor_record


def test_rescan_skips_files_already_in_javlist(tmp_path: Path):
    db_file = tmp_path / "javlist.db"
    save_actor_record("ABF-358", "Suzumori Remu", str(tmp_path / "ABF-358.mp4"), db_file)

    lookup = MagicMock()
    lookup.lookup.return_value = "Actor New"

    groups = group_files_by_actor(tmp_path, ["ABF-358.mp4", "CUS-001.mp4"], lookup, db_path=db_file)

    lookup.lookup.assert_called_once_with("CUS-001", media_path=tmp_path / "CUS-001.mp4")
    by_actor = {g.actor: g.files for g in groups}
    assert by_actor["Suzumori Remu"] == ["ABF-358.mp4"]


def test_rescan_uses_classification_progress(tmp_path: Path):
    db_file = tmp_path / "javlist.db"
    establish_to_db(db_file).close()
    mark_file_resolved(tmp_path, "DONE-1.mp4", "DONE-1", "Actor Cached", db_file)

    lookup = MagicMock()
    groups = group_files_by_actor(tmp_path, ["DONE-1.mp4"], lookup, db_path=db_file)

    lookup.lookup.assert_not_called()
    assert groups[0].actor == "Actor Cached"


def test_scan_and_group_no_browser_when_all_cached(tmp_path: Path):
    db_file = tmp_path / "javlist.db"
    save_actor_record("X-1", "Actor X", "", db_file)
    (tmp_path / "X-1.mp4").write_bytes(b"x")

    def factory(_msg):
        raise AssertionError("browser should not start")

    groups = scan_and_group(
        tmp_path,
        lookup_factory=factory,
        db_path=db_file,
    )
    assert groups[0].files == ["X-1.mp4"]
