import logging
import sys
from types import SimpleNamespace

import pytest

import src.app.backend as backend_module
from src.app.backend import BackendWorker


def test_backend_worker_finishes_in_gui_only_mode(monkeypatch, caplog) -> None:
    monkeypatch.setattr("src.app.backend.sys.platform", "linux")
    worker = BackendWorker()
    finished = []
    worker.finished.connect(lambda: finished.append(True))

    with caplog.at_level(logging.INFO):
        worker.run()

    assert finished == [True]
    assert "GUI-only mode" in caplog.text


@pytest.mark.skipif(sys.platform != "win32", reason="The game backend runtime is Windows-only.")
def test_backend_starts_tts_listener_before_waiting_for_game_window(monkeypatch) -> None:
    calls = []

    class Filter:
        def load_files(self) -> None:
            calls.append("load_files")

    class Overlay:
        def run(self) -> None:
            calls.append("overlay")

    perception = SimpleNamespace(start_connection=lambda: calls.append("tts"))
    monkeypatch.setattr(backend_module.sys, "platform", "win32")
    monkeypatch.setattr(backend_module, "Filter", Filter)
    monkeypatch.setattr(backend_module, "_perception", perception)
    monkeypatch.setattr(backend_module, "Overlay", Overlay)
    monkeypatch.setattr(backend_module, "start_detecting_window", lambda _spec: calls.append("detect_window"))
    monkeypatch.setattr(backend_module, "game_window_ready", lambda: True)
    monkeypatch.setattr(backend_module, "ScriptHandler", lambda: calls.append("script_handler"))
    monkeypatch.setattr(backend_module, "check_for_proper_tts_configuration", lambda: calls.append("diagnostics"))
    monkeypatch.setattr(
        backend_module,
        "get_settings",
        lambda: SimpleNamespace(advanced_options=SimpleNamespace(process_name="Diablo IV.exe")),
    )
    monkeypatch.setattr(backend_module.time, "sleep", lambda _seconds: calls.append("sleep"))

    BackendWorker().run()

    assert calls.index("tts") < calls.index("load_files")
