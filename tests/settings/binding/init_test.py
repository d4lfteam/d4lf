from src.settings import binding


def test_binding_package_exposes_persisted_hotkey_vocabulary() -> None:
    assert binding.canonicalize_hotkey("Control+F11") == "ctrl+f11"
    assert binding.normalize_hotkey("Control+F11") == "<ctrl>+<f11>"
    assert binding.validate_hotkey("Control+F11") == "ctrl+f11"
