import re
from pathlib import Path

TITLE_PATTERN = re.compile(r"^([A-Za-z]+-\d+)", re.IGNORECASE)
MEDIA_EXTENSIONS = {".mp4", ".avi", ".mkv", ".wmv"}


def extract_code(filename: str) -> str | None:
    stem = Path(filename).stem
    match = TITLE_PATTERN.match(stem)
    if not match:
        return None
    return match.group(1).upper()


def is_valid_code_filename(filename: str) -> bool:
    stem = Path(filename).stem
    code = extract_code(stem)
    return code is not None and stem.upper() == code


def media_extension(filename: str) -> str:
    return Path(filename).suffix.lower()
