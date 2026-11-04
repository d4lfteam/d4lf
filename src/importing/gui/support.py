import logging
import threading
from typing import TYPE_CHECKING, override

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

from src.importing.contracts import ImportSourceError
from src.importing.service import import_build

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.importing.contracts import ImportRequest, ImportSession

LOGGER = logging.getLogger(__name__)


class ImportWorker(QRunnable):
    """Run one import step on the thread pool and always signal completion."""

    def __init__(
        self, task: Callable[[WorkerSignals], None], finished: Callable[[], None], *, thread_name: str, label: str
    ) -> None:
        super().__init__()
        self.task = task
        self.thread_name = thread_name
        self.label = label
        self.signals = WorkerSignals()
        self.signals.finished.connect(finished)

    @pyqtSlot()
    @override
    def run(self) -> None:
        threading.current_thread().name = self.thread_name
        try:
            self.task(self.signals)
        except ImportSourceError:
            pass
        except Exception:
            LOGGER.exception("%s worker failed", self.label)
        finally:
            self.signals.finished.emit()


def import_worker(request: ImportRequest, finished: Callable[[], None], session: ImportSession) -> ImportWorker:
    def task(_signals: WorkerSignals) -> None:
        import_build(request, session=session)

    return ImportWorker(task, finished, thread_name="import", label="Import")


def fetch_variants_worker(request: ImportRequest, finished: Callable[[], None], session: ImportSession) -> ImportWorker:
    def task(signals: WorkerSignals) -> None:
        signals.variants_extracted.emit(session.fetch_variants(request))

    return ImportWorker(task, finished, thread_name="import-fetch-variants", label="Fetch variants")


class WorkerSignals(QObject):
    finished = pyqtSignal()
    variants_extracted = pyqtSignal(object)
