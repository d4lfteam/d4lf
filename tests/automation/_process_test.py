from src.automation import _process


def test_safe_exit_delegates_to_process_exit(monkeypatch):
    called = []
    monkeypatch.setattr(_process.psutil, "process_iter", lambda *_args: [])
    monkeypatch.setattr(_process.time, "sleep", lambda *_args: None)
    monkeypatch.setattr(_process.os, "_exit", lambda code: called.append(code))
    _process.safe_exit(7)
    assert called == [7]
