import pytest
from pydantic import ValidationError

from src.settings.models_core import AdvancedOptionsModel, SettingsCategory


def test_settings_categories_are_stable_public_values() -> None:
    assert SettingsCategory.LOOT.value == "📦 Loot Behavior"
    assert SettingsCategory.HOTKEYS.value == "⌨️ Hotkeys"


def test_advanced_options_reject_duplicate_hotkeys() -> None:
    with pytest.raises(ValidationError, match="unique"):
        AdvancedOptionsModel(exit_key="f1", run_filter="f1")


def test_advanced_options_accept_fast_vision_coordinates() -> None:
    model = AdvancedOptionsModel(fast_vision_mode_coordinates="12,34")
    assert model.fast_vision_mode_coordinates == (12, 34)
