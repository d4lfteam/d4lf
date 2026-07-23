import logging
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import src.main as main_module

if TYPE_CHECKING:
    from src.settings import Settings

from src.settings import SettingsLoadError


def test_autoupdate_dispatches_without_qt_or_desktop_shell(monkeypatch):
    calls = []
    monkeypatch.setattr(main_module.sys, "argv", ["d4lf", "--autoupdate"])
    monkeypatch.setattr(main_module, "_configure_logging", lambda **kwargs: calls.append(("log", kwargs)))
    monkeypatch.setattr(main_module, "start_auto_update", lambda **kwargs: calls.append(("update", kwargs)))

    assert main_module.run() == 0
    assert calls == [("log", {"stdout": True}), ("update", {})]


def test_autoupdatepost_dispatches_postprocess(monkeypatch):
    calls = []
    monkeypatch.setattr(main_module.sys, "argv", ["d4lf", "--autoupdatepost"])
    monkeypatch.setattr(main_module, "_configure_logging", lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(main_module, "start_auto_update", lambda **kwargs: calls.append(kwargs))

    assert main_module.run() == 0
    assert calls == [{"stdout": True}, {"postprocess": True}]


def test_consoleonly_dispatches_main_without_starting_qt(monkeypatch):
    calls = []
    monkeypatch.setattr(main_module.sys, "argv", ["d4lf", "--consoleonly"])
    monkeypatch.setattr(main_module, "_configure_logging", lambda **kwargs: calls.append(("log", kwargs)))
    monkeypatch.setattr(main_module, "main", lambda: calls.append(("main", {})))

    assert main_module.run() == 0
    assert calls == [("log", {"stdout": True}), ("main", {})]


def test_run_does_not_construct_qt_for_cli_modes(monkeypatch):
    monkeypatch.setattr(main_module.sys, "argv", ["d4lf", "--autoupdate"])
    monkeypatch.setattr(main_module, "_configure_logging", lambda **_: None)
    monkeypatch.setattr(main_module, "start_auto_update", lambda **_: None)
    monkeypatch.setattr(main_module, "QApplication", lambda *_args: (_ for _ in ()).throw(AssertionError()))

    assert main_module.run() == 0


def test_cli_settings_failure_is_logged_before_load_without_qt(monkeypatch, capsys):
    calls = []
    error = SettingsLoadError(Path("params.ini"), ValueError("invalid"), log_path=Path("logs"))
    monkeypatch.setattr(main_module.sys, "argv", ["d4lf", "--autoupdate"])
    monkeypatch.setattr(main_module.src.logger, "is_configured", lambda: False)
    monkeypatch.setattr(main_module.src.logger, "setup", lambda **_kwargs: calls.append("setup"))

    def fail_settings_load():
        calls.append("load")
        raise error

    monkeypatch.setattr(main_module, "get_settings", fail_settings_load)
    monkeypatch.setattr(main_module, "QApplication", lambda *_args: (_ for _ in ()).throw(AssertionError()))

    assert main_module.run() == 1
    assert calls == ["setup", "load"]
    assert "params.ini" in capsys.readouterr().err


def test_configured_logging_updates_bootstrap_handlers(monkeypatch):
    root_logger = logging.getLogger()
    file_handler = logging.Handler()
    file_handler.name = "D4LF_FILE"
    file_handler.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler()
    console_handler.name = "D4LF_CONSOLE"
    console_handler.setLevel(logging.DEBUG)
    original_handlers = root_logger.handlers[:]
    root_logger.handlers[:] = [file_handler, console_handler]
    settings = cast(
        "Settings",
        SimpleNamespace(
            advanced_options=SimpleNamespace(
                log_lvl=SimpleNamespace(value="warning"), technical_log_info=True, log_timestamp=True
            )
        ),
    )

    try:
        main_module._apply_configured_logging(settings)
    finally:
        root_logger.handlers[:] = original_handlers

    assert console_handler.level == logging.WARNING
    assert console_handler.formatter is not None
    assert file_handler.level == logging.DEBUG
