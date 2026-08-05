import logging
import threading
from typing import TYPE_CHECKING, override

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

from src.importing.contracts import ImportSourceError
from src.importing.service import import_build

if TYPE_CHECKING:
    from src.importing.contracts import ImportRequest, ImportResult, ImportSession

LOGGER = logging.getLogger(__name__)


def run_import(*, request: ImportRequest, session: ImportSession | None = None) -> ImportResult:
    """Run one import, optionally through a session retained by the window."""
    return import_build(request, session=session)


class ImportWorker(QRunnable):
    def __init__(self, request: ImportRequest, finished, session: ImportSession | None = None):
        super().__init__()
        self.request = request
        self.finished = finished
        self.session = session
        self.signals = WorkerSignals()
        self.signals.finished.connect(finished)

    @pyqtSlot()
    @override
    def run(self):
        threading.current_thread().name = "import"
        try:
            run_import(request=self.request, session=self.session)
        except ImportSourceError:
            pass
        except Exception:
            LOGGER.exception("Import worker failed")
        finally:
            self.signals.finished.emit()


class FetchVariantsWorker(QRunnable):
    def __init__(self, request: ImportRequest, finished, session: ImportSession):
        super().__init__()
        self.request = request
        self.finished = finished
        self.session = session
        self.signals = WorkerSignals()
        self.signals.finished.connect(finished)

    @pyqtSlot()
    @override
    def run(self):
        threading.current_thread().name = "import-fetch-variants"
        try:
            variants = self.session.fetch_variants(self.request)
            self.signals.variants_extracted.emit(variants)
        except ImportSourceError:
            pass
        except Exception:
            LOGGER.exception("Fetch variants worker failed")
        finally:
            self.signals.finished.emit()


class WorkerSignals(QObject):
    finished = pyqtSignal()
    variants_extracted = pyqtSignal(object)
