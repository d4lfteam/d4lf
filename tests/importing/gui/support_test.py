from src.importing.gui.support import ImportWorker, WorkerSignals, run_import


def test_import_support_exposes_worker_and_headless_runner() -> None:
    assert callable(run_import)
    assert ImportWorker is not None
    assert WorkerSignals is not None
