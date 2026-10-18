from core.settings import AppSettings, load_settings, save_settings


def test_save_and_load_settings(tmp_path, monkeypatch):
    monkeypatch.setattr("core.settings.SETTINGS_FILE", tmp_path / "settings.json")
    monkeypatch.setattr("core.settings.SETTINGS_DIR", tmp_path)

    settings = AppSettings(classifier_path="D:/Videos", fixer_path="/tmp/fix")
    save_settings(settings)
    loaded = load_settings()

    assert loaded.classifier_path == "D:/Videos"
    assert loaded.fixer_path == "/tmp/fix"
    assert loaded.javlib_search_pause_seconds == 1.5


def test_load_migrates_legacy_pause_keys(tmp_path, monkeypatch):
    monkeypatch.setattr("core.settings.SETTINGS_FILE", tmp_path / "settings.json")
    monkeypatch.setattr("core.settings.SETTINGS_DIR", tmp_path)
    (tmp_path / "settings.json").write_text(
        '{"classifier_lookup_delay_seconds": 2.5}',
        encoding="utf-8",
    )
    loaded = load_settings()
    assert loaded.javlib_search_pause_seconds == 2.5
