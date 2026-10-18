from pathlib import Path

from core.actor_searcher import ActorGroup, move_actor_groups
from core.filesystem import move_classified_file


def test_move_luxu_to_series_folder(tmp_path: Path):
    (tmp_path / "LUXU-001.mp4").write_bytes(b"x")
    msg = move_classified_file(tmp_path, "LUXU-001.mp4", "Ignored Actor")
    assert (tmp_path / "LUXU-Series" / "LUXU-001.mp4").exists()
    assert "LUXU-Series" in msg


def test_move_duplicate_to_existed(tmp_path: Path):
    actor_dir = tmp_path / "Actor A"
    actor_dir.mkdir()
    (actor_dir / "SSIS-100.mp4").write_bytes(b"old")
    (tmp_path / "SSIS-100.mp4").write_bytes(b"new")
    msg = move_classified_file(tmp_path, "SSIS-100.mp4", "Actor A")
    assert (tmp_path / "Existed" / "SSIS-100.mp4").exists()
    assert "Existed" in msg


def test_move_actor_groups_uses_classifier_rules(tmp_path: Path):
    (tmp_path / "CUS-1.mp4").write_bytes(b"a")
    groups = [ActorGroup("Actor B", ["CUS-1.mp4"], checked=True)]
    move_actor_groups(tmp_path, groups)
    assert (tmp_path / "Actor B" / "CUS-1.mp4").exists()
