import logging

from src.app.backend import BackendWorker


def test_backend_worker_finishes_in_gui_only_mode(monkeypatch, caplog) -> None:
    monkeypatch.setattr("src.app.backend.sys.platform", "linux")
    worker = BackendWorker()
    finished = []
    worker.finished.connect(lambda: finished.append(True))

    with caplog.at_level(logging.INFO):
        worker.run()

    assert finished == [True]
    assert "GUI-only mode" in caplog.text
