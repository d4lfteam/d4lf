import logging
import threading
from typing import override

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

from src.importing import ImportRequest, ImportResult, import_build

LOGGER = logging.getLogger(__name__)


def run_import(*, request: ImportRequest) -> ImportResult:
    return import_build(request)


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


class FetchVariantsWorker(QRunnable):
    def __init__(self, request: ImportRequest, finished):
        super().__init__()
        self.request = request
        self.finished = finished
        self.signals = WorkerSignals()
        self.signals.finished.connect(finished)

    @pyqtSlot()
    @override
    def run(self):
        threading.current_thread().name = "import-fetch-variants"
        try:
            from src.importing.service import select_source  # ruff:ignore[import-outside-top-level]

            source = select_source(self.request.url)
            variants = source.fetch_variants(self.request)
            self.signals.variants_extracted.emit(variants)
        except Exception:
            LOGGER.exception("Fetch variants worker failed")
        finally:
            self.signals.finished.emit()


class WorkerSignals(QObject):
    finished = pyqtSignal()
    variants_extracted = pyqtSignal(object)
