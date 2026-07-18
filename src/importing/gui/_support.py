import logging
import threading
from typing import override

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

from src.importing import ImportRequest, ImportResult, import_build

LOGGER = logging.getLogger(__name__)


def run_import(*, request: ImportRequest) -> ImportResult:
    return import_build(request)


class GuiLogHandler(logging.Handler):
    """Thread-safe log handler that emits signals for GUI updates."""

    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.signals = LogSignals()
        self.signals.log_message.connect(self._append_log)
        self.setLevel(logging.DEBUG)

    @override
    def emit(self, record: logging.LogRecord):
        """Called from any thread - emit a signal instead of touching Qt directly."""
        try:
            self.signals.log_message.emit(self.format(record))
        except RuntimeError:
            self.handleError(record)

    def _append_log(self, message: str):
        try:
            self.text_widget.append(message)
            self.text_widget.ensureCursorVisible()
        except RuntimeError:
            # Handle a widget being deleted while a signal is in flight.
            pass


class LogSignals(QObject):
    log_message = pyqtSignal(str)


class ImportWorker(QRunnable):
    def __init__(self, request: ImportRequest, finished):
        super().__init__()
        self.request = request
        self.finished = finished
        self.signals = WorkerSignals()
        self.signals.finished.connect(finished)

    @pyqtSlot()
    @override
    def run(self):
        threading.current_thread().name = "import"
        try:
            run_import(request=self.request)
        except Exception:
            LOGGER.exception("Import worker failed")
        finally:
            self.signals.finished.emit()


class WorkerSignals(QObject):
    finished = pyqtSignal()
