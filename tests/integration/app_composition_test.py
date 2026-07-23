import sys

import src.main as main_module


def test_update_dispatch_does_not_load_the_desktop_shell(monkeypatch):
    sys.modules.pop("src.app.shell", None)
    monkeypatch.setattr(main_module.sys, "argv", ["d4lf", "--autoupdate"])
    monkeypatch.setattr(main_module, "_configure_logging", lambda **_: None)
    calls = []
    monkeypatch.setattr(main_module, "start_auto_update", lambda **kwargs: calls.append(kwargs))

    assert "src.app.shell" not in sys.modules
    assert main_module.run() == 0
    assert calls == [{}]
    assert "src.app.shell" not in sys.modules
