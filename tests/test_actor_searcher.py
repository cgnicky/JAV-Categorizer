from pathlib import Path
from unittest.mock import MagicMock

import bs4

from core.actor_lookup import extract_actor_name, validate_search_result
from core.actor_searcher import (
    ActorGroup,
    group_files_by_actor,
    move_actor_groups,
    scan_first_level_mp4,
)


def test_scan_first_level_mp4_only(tmp_path: Path):
    (tmp_path / "A.mp4").write_bytes(b"a")
    (tmp_path / "B.avi").write_bytes(b"b")
    nested = tmp_path / "sub"
    nested.mkdir()
    (nested / "C.mp4").write_bytes(b"c")

    assert scan_first_level_mp4(tmp_path) == ["A.mp4"]


def test_group_files_by_actor_uses_lookup(tmp_path: Path):
    lookup = MagicMock()
    lookup.lookup.side_effect = lambda code, media_path=None: {
        "ABS-105": "Actor A",
        "CUS-1": "Actor B",
    }.get(code, "Others")

    groups = group_files_by_actor(
        tmp_path,
        ["ABS-105 foo.mp4", "CUS-1 bar.mp4", "ABS-105.mp4"],
        lookup,
        db_path=tmp_path / "empty.db",
    )
    by_actor = {g.actor: g.files for g in groups}
    assert by_actor["Actor A"] == ["ABS-105 foo.mp4", "ABS-105.mp4"]
    assert by_actor["Actor B"] == ["CUS-1 bar.mp4"]


def test_move_actor_groups(tmp_path: Path):
    (tmp_path / "ABS-105.mp4").write_bytes(b"a")
    (tmp_path / "CUS-1.mp4").write_bytes(b"b")
    groups = [
        ActorGroup("Actor A", ["ABS-105.mp4"], checked=True),
        ActorGroup("Actor B", ["CUS-1.mp4"], checked=False),
    ]

    messages = move_actor_groups(tmp_path, groups)

    assert (tmp_path / "Actor A" / "ABS-105.mp4").exists()
    assert (tmp_path / "CUS-1.mp4").exists()
    assert any("Moved:" in msg for msg in messages)


def test_validate_and_extract_single_result():
    soup = bs4.BeautifulSoup(
        "<html><head><title>Ok</title></head>"
        "<body><div class='video'><span class='star'>Yua</span></div></body></html>",
        "html.parser",
    )
    assert validate_search_result(soup) is True
    assert extract_actor_name(soup, "SSIS-001") == "Yua"


def test_extract_actor_follows_multiple_results():
    list_soup = bs4.BeautifulSoup(
        """
        <html><body>
          <div class="videos">
            <a title="ABC-123 Sample" href="./?v=javli1">ABC-123</a>
          </div>
        </body></html>
        """,
        "html.parser",
    )
    driver = MagicMock()
    driver.title = "Ok"
    driver.html = "<html><body><span class='star'>Actor A</span></body></html>"
    assert extract_actor_name(list_soup, "ABC-123", driver) == "Actor A"
