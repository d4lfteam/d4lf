"""Reusable Qt activity-log widgets and thread-safe logging handlers."""

import logging
import re
from html import escape
from typing import override

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtWidgets import QTextEdit


class ANSIConsoleWidget(QTextEdit):
    """Read-only text widget that renders the ANSI colors used by D4LF logs."""

    ANSI_PATTERN = re.compile(r"\x1b\[(\d+)(;\d+)*m")
    ANSI_COLORS = {
        "30": "#000000",
        "31": "#AA0000",
        "32": "#00AA00",
        "33": "#AA5500",
        "34": "#0000AA",
        "35": "#AA00AA",
        "36": "#00AAAA",
        "37": "#AAAAAA",
        "90": "#555555",
        "91": "#FF5555",
        "92": "#55FF55",
        "93": "#FFFF55",
        "94": "#5555FF",
        "95": "#FF55FF",
        "96": "#AAFFFF",
        "97": "#FFFFFF",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        font = self.font()
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setStyleSheet("background-color: black; color: white; font-size: 12px;")

    def append_ansi_text(self, text: str) -> None:
        self.append(self._ansi_to_html(text))
        self.moveCursor(QTextCursor.MoveOperation.End)

    def _ansi_to_html(self, text: str) -> str:
        html_parts = []
        last_end = 0
        span_open = False

        for match in self.ANSI_PATTERN.finditer(text):
            start, end = match.span()
            html_parts.append(escape(text[last_end:start]).replace("\n", "<br>"))
            for code in match.group(0)[2:-1].split(";"):
                if code in self.ANSI_COLORS:
                    if span_open:
                        html_parts.append("</span>")
                    html_parts.append(f'<span style="color:{self.ANSI_COLORS[code]}">')
                    span_open = True
                elif code == "0" and span_open:
                    html_parts.append("</span>")
                    span_open = False
            last_end = end

        html_parts.append(escape(text[last_end:]).replace("\n", "<br>"))
        if span_open:
            html_parts.append("</span>")
        return "".join(html_parts)


class QtLogHandler(logging.Handler, QObject):
    """Forward log records to Qt through a queued signal-safe boundary."""

    # Keep logging.shutdown from resolving this attribute through QObject after
    # Qt has already torn down the C++ wrapper.
    flushOnClose = True  # ruff:ignore[mixed-case-variable-in-class-scope]
    log_signal = pyqtSignal(str)

    def __init__(self, text_widget: QTextEdit | None = None):
        logging.Handler.__init__(self)
        QObject.__init__(self)
        self.setLevel(logging.DEBUG)
        if text_widget is not None:
            self.log_signal.connect(lambda message: self._append_to(text_widget, message))

    @override
    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.log_signal.emit(self.format(record))
        except RuntimeError:
            self.handleError(record)

    @staticmethod
    def _append_to(text_widget: QTextEdit, message: str) -> None:
        try:
            text_widget.append(message)
            text_widget.ensureCursorVisible()
        except RuntimeError:
            # A widget can be deleted while a queued signal is in flight.
            pass
