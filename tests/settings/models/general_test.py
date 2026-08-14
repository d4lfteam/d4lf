from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from src.settings.models.core import CATEGORY_KEY, SettingsCategory
from src.settings.models.general import GeneralModel

if TYPE_CHECKING:
    from src.type_aliases import JsonValue


class TestGeneralModel:
    def test_loot_filter_overrides_default_to_enabled_with_loot_metadata(self) -> None:
        expected = {
            "filter_equipment": "Filter Equipment",
            "filter_sigils": "Filter Sigils",
            "filter_tributes": "Filter Tributes",
            "filter_seals": "Filter Seals",
            "filter_charms": "Filter Charms",
        }

        model = GeneralModel()

        assert {key: getattr(model, key) for key in expected} == dict.fromkeys(expected, True)
        for key, title in expected.items():
            field = GeneralModel.model_fields[key]
            assert field.title == title
            assert field.json_schema_extra[CATEGORY_KEY] == SettingsCategory.LOOT
            assert "all" in field.description
            assert "skipped" in field.description
            assert "including Mythic" in field.description
            assert "always kept" in field.description

    def test_profiles_empty_entries_are_removed(self) -> None:
        assert GeneralModel(profiles="alpha, , beta,   ,").profiles == ["alpha", "beta"]

    def test_check_chest_tabs_preserves_zero_based_integer_input(self) -> None:
        assert GeneralModel(check_chest_tabs=[0, 2]).check_chest_tabs == [0, 2]
        assert GeneralModel(check_chest_tabs=["1", "3"]).check_chest_tabs == [0, 2]

    @pytest.mark.parametrize("value", [[1.5], [None], [True], [{"tab": 1}]])
    def test_check_chest_tabs_rejects_invalid_values(self, value: list[JsonValue]) -> None:
        with pytest.raises(ValidationError, match="list entries must be strings or integers"):
            GeneralModel.model_validate({"check_chest_tabs": value})

    def test_stash_tab_count_is_limited_to_six_or_seven(self) -> None:
        with pytest.raises(ValidationError, match="must be 6 or 7"):
            GeneralModel(max_stash_tabs=8)
