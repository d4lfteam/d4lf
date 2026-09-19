import logging
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.app.startup import check_for_proper_tts_configuration, get_d4_local_prefs_file, prepare_runtime_directories


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


@pytest.mark.parametrize("returncode", [0, 1])
def test_signature_check_handles_non_cp1252_subprocess_output(tmp_path, monkeypatch, caplog, returncode) -> None:
    (tmp_path / "saapi64.dll").touch()
    process = SimpleNamespace(name=lambda: "Diablo IV.exe", exe=lambda: str(tmp_path / "Diablo IV.exe"))
    monkeypatch.setattr("src.app.startup.sys.platform", "win32")
    monkeypatch.setattr("src.app.startup.psutil.process_iter", lambda _attrs: [process])
    monkeypatch.setattr(
        "src.app.startup.get_settings",
        lambda: SimpleNamespace(advanced_options=SimpleNamespace(disable_tts_warning=True)),
    )
    run = subprocess.run

    def run_signature_check(command, **kwargs):
        assert "OutputEncoding" in command[-1]
        return run(
            [
                sys.executable,
                "-c",
                (
                    "import sys; sys.stdout.buffer.write(b'Valid\\n'); "
                    f"sys.stderr.buffer.write(b'diagnostic \\x81'); sys.exit({returncode})"
                ),
            ],
            **kwargs,
        )

    monkeypatch.setattr("src.app.startup.subprocess.run", run_signature_check)
    with caplog.at_level(logging.DEBUG, logger="src.app.startup"):
        check_for_proper_tts_configuration()

    expected = "locally signed and valid" if returncode == 0 else "Error checking saapi64.dll signature"
    assert expected in caplog.text
