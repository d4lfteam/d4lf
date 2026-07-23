from pathlib import Path

from src.app.startup import get_d4_local_prefs_file, prepare_runtime_directories


def test_runtime_directories_are_composed_from_settings(monkeypatch, tmp_path) -> None:
    class Settings:
        user_dir = tmp_path / "user"

    monkeypatch.setattr("src.app.startup.get_settings", lambda: Settings())
    monkeypatch.setattr("src.app.startup.LOG_DIR", tmp_path / "logs")

    prepare_runtime_directories()

    assert (tmp_path / "logs" / "screenshots").is_dir()
    assert (tmp_path / "user" / "profiles").is_dir()


def test_local_prefs_returns_most_recent_candidate(monkeypatch, tmp_path) -> None:
    documents = tmp_path / "Documents" / "Diablo IV"
    documents.mkdir(parents=True)
    prefs = documents / "LocalPrefs.txt"
    prefs.write_text("prefs", encoding="utf-8")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    assert get_d4_local_prefs_file() == prefs
