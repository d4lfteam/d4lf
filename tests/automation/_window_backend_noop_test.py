from src.automation import _window_backend_noop as backend


def test_noop_backend_has_no_windows_on_non_windows_backend():
    assert backend.list_active_window_ids() == []
    assert not backend.is_self_foreground()
