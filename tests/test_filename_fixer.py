from pathlib import Path

import pytest

from core.filename_fixer import RenameItem, apply_renames, propose_rename, scan_directory
from core.title_utils import extract_code, is_valid_code_filename


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("ABS-105 Two days and one night beautiful girl reserva.mp4", "ABS-105"),
        ("CUS-1047 帶父親去嫖娼 玩3p慘被抓.mp4", "CUS-1047"),
        ("abc-123_extra.avi", "ABC-123"),
        ("ABS-105.mp4", "ABS-105"),
        ("no-code-here.mp4", None),
    ],
)
def test_extract_code(filename, expected):
    assert extract_code(filename) == expected


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("ABS-105.mp4", True),
        ("abs-105.mp4", True),
        ("ABS-105 Two days.mp4", False),
        ("notes.txt", False),
    ],
)
def test_is_valid_code_filename(filename, expected):
    assert is_valid_code_filename(filename) is expected


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        (
            "ABS-105 Two days and one night beautiful girl reserva.mp4",
            "ABS-105.mp4",
        ),
        ("CUS-1047 帶父親去嫖娼 玩3p慘被抓.mp4", "CUS-1047.mp4"),
        ("ABS-105.mp4", None),
        ("random.mp4", None),
        ("readme.txt", None),
    ],
)
def test_propose_rename(filename, expected):
    assert propose_rename(filename) == expected


def test_scan_directory_lists_invalid_only(tmp_path: Path):
    (tmp_path / "ABS-105 Two days.mp4").write_bytes(b"a")
    (tmp_path / "ABS-105.mp4").write_bytes(b"b")
    (tmp_path / "notes.txt").write_text("x", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "CUS-1 foo.mp4").write_bytes(b"c")

    items = scan_directory(tmp_path)
    assert len(items) == 1
    assert items[0].src_name == "ABS-105 Two days.mp4"
    assert items[0].dest_name == "ABS-105.mp4"


def test_apply_renames_and_conflict_skip(tmp_path: Path):
    (tmp_path / "ABS-105 Two days.mp4").write_bytes(b"new")
    (tmp_path / "CUS-1 說明.mp4").write_bytes(b"c")
    (tmp_path / "CUS-1.mp4").write_bytes(b"old")

    items = [
        RenameItem("ABS-105 Two days.mp4", "ABS-105.mp4", checked=True),
        RenameItem("CUS-1 說明.mp4", "CUS-1.mp4", checked=True),
    ]
    messages = apply_renames(tmp_path, items)

    assert (tmp_path / "ABS-105.mp4").exists()
    assert not (tmp_path / "ABS-105 Two days.mp4").exists()
    assert (tmp_path / "CUS-1 說明.mp4").exists()
    assert any("Skipped (exists)" in msg for msg in messages)
