from typing import TYPE_CHECKING, cast

from src.game_data import ItemType
from src.importing import ImportRequest
from src.importing.mobalytics import filters
from src.importing.mobalytics.filters import _resolve_item_type

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver


def test_mobalytics_filter_type_resolution_handles_missing_values() -> None:
    assert _resolve_item_type([], "", "") is None


def test_build_variant_normalizes_unique_weapon_slot_suffix(monkeypatch) -> None:
    monkeypatch.setattr(filters, "_get_weapon_type_from_slot_tooltip", lambda **_kwargs: None)
    variant = filters.build_variant(
        items=[
            {
                "gameEntity": {"type": "uniqueItems", "entity": {"title": "Grief (1h Sword)"}},
                "gameSlotSlug": "dual-wield-weapon-1",
            }
        ],
        class_name="Rogue",
        request=ImportRequest(url="https://example.invalid/build"),
        driver=cast("WebDriver", object()),
        variant_name="",
        build_name="",
        paragon_data={},
        error_type=ValueError,
    )

    assert len(variant.affix_filters) == 1
    assert variant.affix_filters[0].unique_aspect[0].name == "grief"
    assert variant.affix_filters[0].item_type == [ItemType.Sword]
