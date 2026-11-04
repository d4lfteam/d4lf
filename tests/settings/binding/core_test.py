import pytest

from src.settings.binding.core import canonicalize_hotkey, normalize_hotkey, validate_hotkey


def test_hotkey_binding_is_canonicalized_without_loading_runtime_backend() -> None:
    assert canonicalize_hotkey("F11+Shift+Control") == "ctrl+shift+f11"
    assert normalize_hotkey("Control+F11") == "<ctrl>+<f11>"
    assert validate_hotkey("cmd+f11") == "cmd+f11"


def test_hotkey_binding_requires_a_non_modifier_key() -> None:
    with pytest.raises(ValueError, match="non-modifier"):
        validate_hotkey("ctrl+shift")


@pytest.mark.parametrize(
    ("hotkey", "expected"),
    [
        ("a", "a"),
        ("shift+a", "shift+a"),
        ("shift+ctrl+f11", "ctrl+shift+f11"),
        ("<ctrl>+<shift>+<f11>", "ctrl+shift+f11"),
    ],
)
def test_hotkey_binding_is_validated_to_canonical_form(hotkey: str, expected: str) -> None:
    assert validate_hotkey(hotkey) == expected


def test_hotkey_binding_rejects_unknown_key() -> None:
    with pytest.raises(ValueError, match=r"Key 'non_existing_key' is not mapped to any known key\."):
        validate_hotkey("non_existing_key")
