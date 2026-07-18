import logging
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication, QTextEdit

from src.desktop.activity import ANSIConsoleWidget, QtLogHandler


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if isinstance(app, QApplication):
        return app
    return QApplication([])


def test_ansi_console_escapes_text_and_renders_colors(qapp: QApplication) -> None:
    widget = ANSIConsoleWidget()

    widget.append_ansi_text("\x1b[31mred <item>\x1b[0m")

    assert "red &lt;item&gt;" in widget.toHtml()
    assert "#aa0000" in widget.toHtml()
    widget.close()


def test_qt_log_handler_emits_formatted_records(qapp: QApplication) -> None:
    handler = QtLogHandler()
    messages: list[str] = []
    handler.log_signal.connect(messages.append)
    handler.setFormatter(logging.Formatter("%(levelname)s:%(message)s"))

    handler.emit(logging.LogRecord("test", logging.INFO, __file__, 1, "hello", (), None))

    assert messages == ["INFO:hello"]
    handler.close()


def test_qt_log_handler_can_append_to_a_plain_text_edit(qapp: QApplication) -> None:
    text_widget = QTextEdit()
    handler = QtLogHandler(text_widget)

    handler.emit(logging.LogRecord("test", logging.INFO, __file__, 1, "hello", (), None))

    assert "hello" in text_widget.toPlainText()
    handler.close()
    text_widget.close()
