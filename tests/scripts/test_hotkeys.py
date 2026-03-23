from types import SimpleNamespace

from src.scripts.hotkeys import build_hotkey_signature, has_any_changed


def test_build_hotkey_signature_returns_expected_tuple():
    advanced_options = SimpleNamespace(
        run_vision_mode="f8",
        exit_key="f9",
        toggle_paragon_overlay="f10",
        vision_mode_only=False,
        run_filter="f11",
        run_filter_drop="f12",
        run_filter_force_refresh="f6",
        force_refresh_only="f7",
        move_to_inv="f2",
        move_to_chest="f3",
    )

    assert build_hotkey_signature(advanced_options) == ("f8", "f9", "f10", False, "f11", "f12", "f6", "f7", "f2", "f3")


def test_has_any_changed_detects_intersection():
    assert has_any_changed({"a", "b"}, {"c", "b"}) is True
    assert has_any_changed({"a"}, {"c", "d"}) is False
