import ast
import logging
import sys
from pathlib import Path

import src.main as main_module
from src.app.backend import BackendWorker
from src.app.startup import prepare_runtime_directories


def test_backend_worker_is_gui_only_off_windows(monkeypatch, caplog):
    monkeypatch.setattr("src.app.backend.sys.platform", "linux")
    worker = BackendWorker()
    finished = []
    worker.finished.connect(lambda: finished.append(True))

    with caplog.at_level(logging.INFO):
        worker.run()

    assert finished == [True]
    assert "GUI-only mode" in caplog.text


def test_runtime_directories_are_composed_from_settings(monkeypatch, tmp_path):
    class Settings:
        user_dir = tmp_path / "user"

    monkeypatch.setattr("src.app.startup.get_settings", lambda: Settings())
    monkeypatch.setattr("src.app.startup.LOG_DIR", tmp_path / "logs")

    prepare_runtime_directories()

    assert (tmp_path / "logs" / "screenshots").is_dir()
    assert (tmp_path / "user" / "profiles").is_dir()


def test_unified_shell_uses_application_asset_facade():
    source = Path("src/app/shell.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert "src.gui" not in source
    assert "src.importing.gui" not in source
    assert "src.profiles.editor" not in source
    assert {"BackendWorker", "get_perception_module"} <= {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "backend"
        for alias in node.names
    }
    assert "ICON_PATH" in {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "assets"
        for alias in node.names
    }


def test_update_dispatch_does_not_load_the_desktop_shell(monkeypatch):
    sys.modules.pop("src.app.shell", None)
    monkeypatch.setattr(main_module.sys, "argv", ["d4lf", "--autoupdate"])
    monkeypatch.setattr(main_module, "_configure_logging", lambda **_: None)
    calls = []
    monkeypatch.setattr(main_module, "start_auto_update", lambda **kwargs: calls.append(kwargs))

    assert "src.app.shell" not in sys.modules
    assert main_module.run() == 0
    assert calls == [{}]
    assert "src.app.shell" not in sys.modules
