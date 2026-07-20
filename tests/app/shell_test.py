import threading
from pathlib import Path
from types import SimpleNamespace

from PyQt6.QtWidgets import QApplication, QMainWindow

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
