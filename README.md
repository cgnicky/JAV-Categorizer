# JAV Title Categorizer

PyQt desktop utilities for JAV media classification, SQLite catalog, filename fixing, and actor-based grouping.

See [CHANGELOG.md](CHANGELOG.md) for release notes.

## Setup

```sh
pip install -e ".[dev]"
# or: uv sync --extra dev
```

On Windows, use the pinned `pyqt5` / `pyqt5-qt5` versions in `pyproject.toml` (`uv sync`); unpinned `pyqt5` can resolve to Qt builds without a Windows wheel.

## Run

```sh
python JavTools.py
```

## Tests

```sh
pytest -q
ruff check .
```

## Project layout

- [`core/`](core/) — business logic (no PyQt)
- [`workers/`](workers/) — `QThread` wrappers around core
- [`ui/`](ui/) — tab controllers and widgets
- `JavTools.py` — entry point
- `PyQt5GUI.py` — widget tree (hand-maintained extensions for new tabs)
- `create_javlist.sql` — SQLite schema reference

## Notes

- Database: `javlist.db` at project root (auto-created).
- **JavLib pause:** use **JavLib pause (s)** on the Classifier or Actor Searcher tab (0 = off, default `1.5`). Saved as `javlib_search_pause_seconds` in `~/.jav_tools/settings.json`. Applies before each JavLibrary **web** request (not DB cache hits).
- **JavLibrary rate limits / resume:** web hits are saved to `javlist.db` and per-file `classification_progress` (`resolved`). Actor Searcher **Scan** skips those files (`From database:` in the log) and only opens the browser for the rest. After a rate limit, scan again to continue from the first pending file.
