import json
from dataclasses import asdict, dataclass
from pathlib import Path

SETTINGS_DIR = Path.home() / ".jav_tools"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"


@dataclass
class AppSettings:
    classifier_path: str = ""
    javlib_search_pause_seconds: float = 1.5
    updater_dir_placeholder: str = "Insert Directory Path Here!"
    fixer_path: str = ""
    actor_path: str = ""


def _migrate_settings_data(data: dict) -> dict:
    if "javlib_search_pause_seconds" not in data:
        for legacy_key in ("classifier_lookup_delay_seconds", "actor_lookup_delay_seconds"):
            if legacy_key in data:
                data["javlib_search_pause_seconds"] = data[legacy_key]
                break
    return data


def load_settings() -> AppSettings:
    if not SETTINGS_FILE.is_file():
        return AppSettings()
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        data = _migrate_settings_data(data)
        return AppSettings(**{k: data[k] for k in AppSettings.__dataclass_fields__ if k in data})
    except (json.JSONDecodeError, TypeError, OSError):
        return AppSettings()


def save_settings(settings: AppSettings) -> None:
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
