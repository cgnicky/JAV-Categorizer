# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- UI migrated from PyQt5 to **Flet** (desktop). Entry point remains `python JavTools.py`.
- Workers use `threading` instead of `QThread`; business logic in `core/` unchanged.
- Actor scan: one SQLite session per scan, batched progress writes, single pass (no duplicate DB resolution).
- Flet log panes batch lines to reduce UI churn during large scans.
- Flet UX: app bar + status line, shared folder/actions layout, expanding logs, Advanced JavLib pause, snackbars, shorter tab labels.
- Database updater worker no longer duplicates status messages.

## [0.2.0] - 2026-10-18

### Added

- **Filename Fixer** tab: scan first-level files, preview renames to `CODE.ext`, apply selected renames.
- **Actor Searcher** tab: group first-level `.mp4` by actor (JavLibrary), tree with checkboxes, move into actor subfolders.
- Package layout: [`core/`](core/) (logic), [`workers/`](workers/) (`QThread` wrappers), [`ui/`](ui/) (tabs and helpers).
- SQLite catalog at project root (`javlist.db`, table `javlist`); schema auto-created on connect.
- Settings file `~/.jav_tools/settings.json` (paths, JavLib pause).
- **JavLib pause (s)** spin boxes on Classifier and Actor Searcher (shared setting `javlib_search_pause_seconds`, default `1.5`).
- **Stop** buttons on Classifier and Actor Searcher; stop when the Chromium window is closed.
- JavLibrary lookup **resume**: upsert actors into `javlist`, per-file `classification_progress` (`resolved` / `rate_limited`).
- Actor Searcher skips files already in DB or progress (`From database:` log); browser starts only if something still needs the web.
- `scripts/check_progress.py` — inspect `classification_progress` (`uv run python -m scripts.check_progress`).
- Unit tests (pytest), Ruff lint, GitHub Actions CI on Windows.
- `pyproject.toml` / `uv` workflow with pinned `pyqt5` / `pyqt5-qt5` for Windows wheels.

### Changed

- Media Query and Database Updater use SQLite instead of PostgreSQL and `database.ini`.
- Classifier and actor lookup share `ActorLookup` with in-memory cache and **DB-first** resolution before JavLibrary.
- JavLibrary HTML handling: detail-page redirect, `videothumblist` / `div.id` matching, short wait for page content.
- Rate-limit detection: no bare `429` substring (avoids false positives from video IDs); skip throttle check on valid result pages.
- Quieter filesystem logging during batch moves (errors only by default).
- Removed fixed 1s pause per classifier file; pause is configurable and applies only to web requests.
- README updated for layout, setup, pause, and resume behavior.

### Removed

- Legacy root modules (`JavClassifier.py`, `JavQuery.py`, etc.), duplicate `src/` tree, `requirements.txt`, `database.ini`, PyInstaller `JavTool.spec`.
- Unused classifier UI (actor/title radios, unwired Cancel buttons on query/updater).

### Fixed

- Classifier LUXU/GANA duplicate routing to `Existed/` when target already exists in series folder.
- `uv sync` on Windows failing on `pyqt5-qt5` versions without `win_amd64` wheels.
- False “JavLibrary rate limit” retries when the page was a normal search result.
- Actor Searcher rescan re-querying JavLibrary for codes already stored in `javlist.db`.

## [0.1.0] - Earlier

- Monolithic PyQt app: classifier, media query, database updater (PostgreSQL via `database.ini`).
- Single-process `QThread` workers and root-level Python modules.
