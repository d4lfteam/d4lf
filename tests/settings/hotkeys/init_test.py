from src.settings import hotkeys


def test_hotkeys_package_exposes_runtime_operations() -> None:
    assert callable(hotkeys.add_hotkey)
    assert callable(hotkeys.press)
    assert callable(hotkeys.release)
    assert callable(hotkeys.remove_hotkey)
    assert callable(hotkeys.send)
