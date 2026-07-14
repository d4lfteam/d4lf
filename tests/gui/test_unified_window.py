import logging
import os
from collections import UserList
from typing import override

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QApplication, QMainWindow

from src.gui.models.activity_log_widget import QtConsoleHandler
from src.gui.unified_window import UnifiedMainWindow


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if isinstance(app, QApplication):
        return app
    return QApplication([])


def test_close_event_preserves_existing_handler_registration(qapp: QApplication, monkeypatch) -> None:
    class TrackingHandlerList(UserList[object]):
        was_cleared = False

        @override
        def clear(self) -> None:
            self.was_cleared = True
            super().clear()

    handler_list = TrackingHandlerList()
    monkeypatch.setattr(logging, "_handlerList", handler_list)
    monkeypatch.setattr(UnifiedMainWindow, "__init__", QMainWindow.__init__)
    window = UnifiedMainWindow()
    window._child_windows = {}
    window.console_handler = QtConsoleHandler()
    monkeypatch.setattr(UnifiedMainWindow, "save_geometry", lambda _self: None)
    root_logger = logging.getLogger()
    handler = logging.NullHandler()
    root_logger.addHandler(handler)

    try:
        window.closeEvent(QCloseEvent())

        assert handler in root_logger.handlers
        assert not handler_list.was_cleared
    finally:
        root_logger.removeHandler(handler)
