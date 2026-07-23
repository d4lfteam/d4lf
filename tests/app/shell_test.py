import threading
from pathlib import Path
from types import SimpleNamespace

from PyQt6.QtWidgets import QApplication, QMainWindow

import src.app.shell as shell_module
from src.app.lifecycle import UnifiedWindowLifecycle
from src.app.shell import UnifiedMainWindow
from src.item import ProfileLoadReport
from src.settings import SettingsLoadError


def test_shell_uses_application_window_lifecycle() -> None:
    assert issubclass(UnifiedMainWindow, UnifiedWindowLifecycle)


def test_profile_report_is_delivered_through_qt_signal() -> None:
    app = QApplication.instance() or QApplication([])
    window = UnifiedMainWindow.__new__(UnifiedMainWindow)
    QMainWindow.__init__(window)  # ruff:ignore[unnecessary-dunder-call] - initialize a shell instance without its full UI
    received = []
    window.profile_load_report_signal.connect(received.append)

    window._queue_profile_load_report(ProfileLoadReport(skipped=("bad",), message="bad skipped"))
    app.processEvents()

    assert received[0].message == "bad skipped"
    window.deleteLater()


def test_settings_error_from_worker_is_delivered_on_gui_thread() -> None:
    app = QApplication.instance() or QApplication([])
    window = UnifiedMainWindow.__new__(UnifiedMainWindow)
    QMainWindow.__init__(window)  # ruff:ignore[unnecessary-dunder-call] - initialize without full UI
    gui_thread = threading.get_ident()
    notification_threads = []
    window.tray_icon = SimpleNamespace(showMessage=lambda *_args: notification_threads.append(threading.get_ident()))
    window.settings_load_error_signal.connect(window._on_settings_load_error)
    error = SettingsLoadError(Path("params.ini"), ValueError("invalid"))

    worker = threading.Thread(target=window._queue_settings_load_error, args=(error,))
    worker.start()
    worker.join()
    app.processEvents()

    assert notification_threads == [gui_thread]
    window.deleteLater()


def test_profile_editor_inherits_main_window_maximized_state(monkeypatch) -> None:
    window = UnifiedMainWindow.__new__(UnifiedMainWindow)
    window.isMaximized = lambda: True
    calls = []
    monkeypatch.setattr(
        window,
        "_show_singleton_modal",
        lambda key, window_factory, **kwargs: calls.append((key, window_factory, kwargs)),
    )

    window.open_profile_editor("beta")

    assert calls == [
        ("editor", shell_module.create_profile_editor_window, {"profile_name": "beta", "force_maximized": True})
    ]


def test_settings_window_inherits_main_window_maximized_state(monkeypatch) -> None:
    window = UnifiedMainWindow.__new__(UnifiedMainWindow)
    window.isMaximized = lambda: True
    window.apply_theme = lambda: None
    calls = []
    monkeypatch.setattr(
        window,
        "_show_singleton_modal",
        lambda key, window_factory, **kwargs: calls.append((key, window_factory, kwargs)),
    )
    monkeypatch.setattr(shell_module, "set_accent_color", lambda _color: None)
    monkeypatch.setattr(shell_module, "get_filter_colors", lambda: SimpleNamespace(matched="#fff"))

    window.open_settings_dialog()

    assert calls == [
        (
            "config",
            shell_module.create_settings_window,
            {"theme_changed_callback": window.apply_theme, "force_maximized": True},
        )
    ]
