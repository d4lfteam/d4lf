import os
from pathlib import Path

from src.bootstrap import ensure_runtime_dirs, resolve_local_prefs_file


def test_ensure_runtime_dirs_creates_nested_directories(tmp_path):
    screenshots_dir = tmp_path / "logs" / "screenshots"
    profiles_dir = tmp_path / ".d4lf" / "profiles"

    ensure_runtime_dirs(screenshots_dir, profiles_dir)

    assert screenshots_dir.is_dir()
    assert profiles_dir.is_dir()


def test_resolve_local_prefs_file_returns_none_when_missing(tmp_path):
    assert resolve_local_prefs_file(tmp_path) is None


def test_resolve_local_prefs_file_returns_most_recent_existing_file(tmp_path):
    documents_file = tmp_path / "Documents" / "Diablo IV" / "LocalPrefs.txt"
    onedrive_file = tmp_path / "OneDrive" / "Documents" / "Diablo IV" / "LocalPrefs.txt"

    documents_file.parent.mkdir(parents=True, exist_ok=True)
    onedrive_file.parent.mkdir(parents=True, exist_ok=True)

    documents_file.write_text("old", encoding="utf-8")
    onedrive_file.write_text("new", encoding="utf-8")

    os.utime(documents_file, (1, 1))
    os.utime(onedrive_file, (2, 2))

    assert resolve_local_prefs_file(tmp_path) == onedrive_file
