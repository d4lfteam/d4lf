import pytest

from src.settings.binding.core import canonicalize_hotkey, normalize_hotkey, validate_hotkey


def test_hotkey_binding_is_canonicalized_without_loading_runtime_backend() -> None:
    assert canonicalize_hotkey("F11+Shift+Control") == "ctrl+shift+f11"
    assert normalize_hotkey("Control+F11") == "<ctrl>+<f11>"
    assert validate_hotkey("cmd+f11") == "cmd+f11"


def test_hotkey_binding_requires_a_non_modifier_key() -> None:
    with pytest.raises(ValueError, match="non-modifier"):
        validate_hotkey("ctrl+shift")
