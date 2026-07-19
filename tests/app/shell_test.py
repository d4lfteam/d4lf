from src.app.lifecycle import UnifiedWindowLifecycle
from src.app.shell import UnifiedMainWindow


def test_shell_uses_application_window_lifecycle() -> None:
    assert issubclass(UnifiedMainWindow, UnifiedWindowLifecycle)
