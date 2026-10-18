from pathlib import Path
from unittest.mock import MagicMock, patch

from core.classifier import ClassifierService
from core.db import count_pending_progress, lookup_actor_from_db, save_actor_record
from core.lookup_errors import RateLimitedError


def test_classifier_saves_progress_on_rate_limit(tmp_path: Path):
    (tmp_path / "SSIS-100.mp4").write_bytes(b"x")
    db_file = tmp_path / "javlist.db"

    lookup = MagicMock()
    lookup.lookup.side_effect = RateLimitedError("limit")

    service = ClassifierService(str(tmp_path), on_message=lambda _: None, db_path=db_file)
    with patch("core.classifier.ActorLookup", return_value=lookup):
        service.run()

    assert count_pending_progress(tmp_path, db_file) == 1
    assert (tmp_path / "SSIS-100.mp4").exists()


def test_classifier_resumes_from_db_without_web(tmp_path: Path):
    (tmp_path / "SSIS-101.mp4").write_bytes(b"x")
    db_file = tmp_path / "javlist.db"
    save_actor_record("SSIS-101", "Cached Actor", str(tmp_path / "SSIS-101.mp4"), db_file)

    service = ClassifierService(str(tmp_path), on_message=lambda _: None, db_path=db_file)
    service.run()

    assert (tmp_path / "Cached Actor" / "SSIS-101.mp4").exists()
    assert lookup_actor_from_db("SSIS-101", db_file) == "Cached Actor"
