from pathlib import Path
from unittest.mock import MagicMock, patch

from core.classifier import ClassifierService
from core.db import DEFAULT_DB_PATH


def test_classifier_runs_and_closes_lookup(tmp_path: Path):
    (tmp_path / "SSIS-100.mp4").write_bytes(b"x")
    lookup = MagicMock()
    lookup.lookup.return_value = "Actor Name"

    service = ClassifierService(str(tmp_path), on_message=lambda _: None)
    with patch("core.classifier.ActorLookup", return_value=lookup) as lookup_cls:
        service.run()

    lookup.close.assert_called_once()
    lookup_cls.assert_called_once()
    kwargs = lookup_cls.call_args.kwargs
    assert kwargs["db_path"] == DEFAULT_DB_PATH
    assert kwargs["web_delay_seconds"] == 0.0
    assert (tmp_path / "Actor Name" / "SSIS-100.mp4").exists()


def test_classifier_invalid_path_emits_message():
    messages = []
    service = ClassifierService("/not/a/real/path_xyz", on_message=messages.append)
    service.run()
    assert any("Invalid source path" in msg for msg in messages)


def test_move_files_luxu_duplicate_goes_to_existed(tmp_path: Path):
    luxu_dir = tmp_path / "LUXU-Series"
    luxu_dir.mkdir()
    (luxu_dir / "LUXU-001.mp4").write_bytes(b"old")
    (tmp_path / "LUXU-001.mp4").write_bytes(b"new")

    lookup = MagicMock()
    lookup.lookup.return_value = "Ignored"

    service = ClassifierService(str(tmp_path), on_message=lambda _: None)
    service.move_files(tmp_path, "LUXU-001.mp4", "LUXU-001", lookup)

    assert (tmp_path / "Existed" / "LUXU-001.mp4").exists()
