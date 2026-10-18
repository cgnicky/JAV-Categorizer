import datetime
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "javlist.db"
TABLE_NAME = "javlist"
PROGRESS_TABLE = "classification_progress"
BATCH_SIZE = 200

SCHEMA_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor TEXT,
  label TEXT NOT NULL UNIQUE,
  timestamp TEXT,
  path TEXT
);
"""

PROGRESS_SCHEMA_SQL = f"""
CREATE TABLE IF NOT EXISTS {PROGRESS_TABLE} (
  source_dir TEXT NOT NULL,
  filename TEXT NOT NULL,
  code TEXT,
  actor TEXT,
  status TEXT NOT NULL,
  note TEXT,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (source_dir, filename)
);
"""

INSERT_QUERY = (
    f"INSERT INTO {TABLE_NAME} (actor, label, timestamp, path) VALUES (?, ?, ?, ?) "
    "ON CONFLICT(label) DO NOTHING"
)

UPSERT_ACTOR_QUERY = f"""
INSERT INTO {TABLE_NAME} (actor, label, timestamp, path) VALUES (?, ?, ?, ?)
ON CONFLICT(label) DO UPDATE SET
  actor = excluded.actor,
  timestamp = excluded.timestamp,
  path = CASE
    WHEN excluded.path IS NOT NULL AND excluded.path != '' THEN excluded.path
    ELSE {TABLE_NAME}.path
  END
"""


def establish_to_db(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute(SCHEMA_SQL)
    conn.execute(PROGRESS_SCHEMA_SQL)
    conn.commit()
    return conn


def _now_ts() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def save_actor_record(
    label: str,
    actor: str,
    path: str = "",
    db_path: str | Path | None = None,
) -> None:
    """Store or refresh a resolved actor for a label (web lookup / resume)."""
    from core.title_utils import extract_code

    code = extract_code(label) or label.strip()
    if not code:
        return
    normalized_label = code.upper()
    name = str(actor).strip()
    if not name or name.lower() == "others":
        return

    conn = establish_to_db(db_path)
    try:
        conn.execute(
            UPSERT_ACTOR_QUERY,
            (name, normalized_label, _now_ts(), path or ""),
        )
        conn.commit()
    finally:
        conn.close()


def save_classification_progress(
    source_dir: str | Path,
    filename: str,
    code: str,
    status: str,
    note: str = "",
    actor: str = "",
    db_path: str | Path | None = None,
) -> None:
    root = str(Path(source_dir).resolve())
    conn = establish_to_db(db_path)
    try:
        conn.execute(
            f"""
            INSERT INTO {PROGRESS_TABLE}
              (source_dir, filename, code, actor, status, note, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_dir, filename) DO UPDATE SET
              code = excluded.code,
              actor = excluded.actor,
              status = excluded.status,
              note = excluded.note,
              updated_at = excluded.updated_at
            """,
            (root, filename, code, actor, status, note, _now_ts()),
        )
        conn.commit()
    finally:
        conn.close()


def clear_classification_progress(
    source_dir: str | Path,
    filename: str,
    db_path: str | Path | None = None,
) -> None:
    root = str(Path(source_dir).resolve())
    conn = establish_to_db(db_path)
    try:
        conn.execute(
            f"DELETE FROM {PROGRESS_TABLE} WHERE source_dir = ? AND filename = ?",
            (root, filename),
        )
        conn.commit()
    finally:
        conn.close()


def resolve_actor_for_file(
    source_dir: str | Path,
    filename: str,
    code: str,
    db_path: str | Path | None = None,
) -> str | None:
    """Actor for this file from scan progress or javlist (no web)."""
    from core.title_utils import extract_code

    root = str(Path(source_dir).resolve())
    conn = establish_to_db(db_path)
    try:
        row = conn.execute(
            f"""
            SELECT actor FROM {PROGRESS_TABLE}
            WHERE source_dir = ? AND filename = ? AND status = 'resolved'
            """,
            (root, filename),
        ).fetchone()
        actor = _usable_actor(row[0] if row else None)
        if actor:
            return actor
    finally:
        conn.close()

    stem = Path(filename).stem
    for label in (code, stem, extract_code(filename) or ""):
        needle = label.strip()
        if not needle:
            continue
        actor = lookup_actor_from_db(needle, db_path)
        if actor:
            return actor
    return None


def mark_file_resolved(
    source_dir: str | Path,
    filename: str,
    code: str,
    actor: str,
    db_path: str | Path | None = None,
) -> None:
    name = str(actor).strip()
    if not name or name.lower() == "others":
        return
    save_classification_progress(
        source_dir,
        filename,
        code,
        status="resolved",
        actor=name,
        db_path=db_path,
    )


def count_pending_progress(
    source_dir: str | Path,
    db_path: str | Path | None = None,
) -> int:
    root = str(Path(source_dir).resolve())
    conn = establish_to_db(db_path)
    try:
        cur = conn.execute(
            f"SELECT COUNT(*) FROM {PROGRESS_TABLE} WHERE source_dir = ?",
            (root,),
        )
        row = cur.fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()


def _usable_actor(actor: str | None) -> str | None:
    if actor is None:
        return None
    name = str(actor).strip()
    if not name or name.lower() == "others":
        return None
    return name


def lookup_actor_from_db(label: str, db_path: str | Path | None = None) -> str | None:
    """Resolve actor from local catalog by exact or prefix label match."""
    from core.title_utils import extract_code

    needle = label.strip()
    if not needle:
        return None

    candidates: list[str] = []
    seen: set[str] = set()
    for item in (needle, extract_code(needle) or ""):
        key = item.strip()
        if not key:
            continue
        upper = key.upper()
        if upper in seen:
            continue
        seen.add(upper)
        candidates.append(key)

    conn = establish_to_db(db_path)
    try:
        for candidate in candidates:
            cur = conn.execute(
                f"SELECT actor FROM {TABLE_NAME} WHERE label = ? COLLATE NOCASE LIMIT 1",
                (candidate,),
            )
            row = cur.fetchone()
            actor = _usable_actor(row[0] if row else None)
            if actor:
                return actor

        code = extract_code(needle) or needle.upper()
        cur = conn.execute(
            f"SELECT actor FROM {TABLE_NAME} WHERE label LIKE ? ORDER BY LENGTH(label) LIMIT 1",
            (f"{code}%",),
        )
        row = cur.fetchone()
        return _usable_actor(row[0] if row else None)
    finally:
        conn.close()
