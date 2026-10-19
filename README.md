# JAV Title Categorizer

Flet desktop utilities for JAV media classification, SQLite catalog, filename fixing, and actor-based grouping.

See [CHANGELOG.md](CHANGELOG.md) for release notes.

## Setup

```sh
pip install -e ".[dev]"
# or: uv sync --extra dev
```

Desktop UI needs the `flet[desktop]` extra (included in project dependencies). If you installed plain `flet` only, run `pip install 'flet[desktop]==0.27.6'` or re-sync with uv.

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

- [`core/`](core/) — business logic (no UI framework)
- [`workers/`](workers/) — background threading wrappers around core
- [`flet_ui/`](flet_ui/) — Flet tabs and shared widgets
- `JavTools.py` — entry point
- `create_javlist.sql` — SQLite schema reference

## Notes

- Database: `javlist.db` at project root (auto-created).
- **Theme:** use the **Theme** dropdown in the app bar: Light, Dark, or System (follows OS). Stored as `ui_theme` in `~/.jav_tools/settings.json`.
- **JavLib pause:** use **JavLib pause (s)** on the Classifier or Actor Searcher tab (0 = off, default `1.5`). Saved as `javlib_search_pause_seconds` in `~/.jav_tools/settings.json`. Applies before each JavLibrary **web** request (not DB cache hits).
- **JavLibrary rate limits / resume:** web hits are saved to `javlist.db` and per-file `classification_progress` (`resolved`). Actor Searcher **Scan** skips those files (`From database:` in the log) and only opens the browser for the rest. After a rate limit, scan again to continue from the first pending file.
