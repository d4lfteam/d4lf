import src.main as main_module


def test_autoupdate_dispatches_without_qt_or_desktop_shell(monkeypatch):
    calls = []
    monkeypatch.setattr(main_module.sys, "argv", ["d4lf", "--autoupdate"])
    monkeypatch.setattr(main_module, "_configure_logging", lambda **kwargs: calls.append(("log", kwargs)))
    monkeypatch.setattr(main_module, "start_auto_update", lambda **kwargs: calls.append(("update", kwargs)))

    assert main_module.run() == 0
    assert calls == [("log", {"stdout": True}), ("update", {})]


def test_autoupdatepost_dispatches_postprocess(monkeypatch):
    calls = []
    monkeypatch.setattr(main_module.sys, "argv", ["d4lf", "--autoupdatepost"])
    monkeypatch.setattr(main_module, "_configure_logging", lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(main_module, "start_auto_update", lambda **kwargs: calls.append(kwargs))

    assert main_module.run() == 0
    assert calls == [{"stdout": True}, {"postprocess": True}]


def test_consoleonly_dispatches_main_without_starting_qt(monkeypatch):
    calls = []
    monkeypatch.setattr(main_module.sys, "argv", ["d4lf", "--consoleonly"])
    monkeypatch.setattr(main_module, "_configure_logging", lambda **kwargs: calls.append(("log", kwargs)))
    monkeypatch.setattr(main_module, "main", lambda: calls.append(("main", {})))

    assert main_module.run() == 0
    assert calls == [("log", {"stdout": True}), ("main", {})]


def test_run_does_not_construct_qt_for_cli_modes(monkeypatch):
    monkeypatch.setattr(main_module.sys, "argv", ["d4lf", "--autoupdate"])
    monkeypatch.setattr(main_module, "_configure_logging", lambda **_: None)
    monkeypatch.setattr(main_module, "start_auto_update", lambda **_: None)
    monkeypatch.setattr(main_module, "QApplication", lambda *_args: (_ for _ in ()).throw(AssertionError()))

    assert main_module.run() == 0
