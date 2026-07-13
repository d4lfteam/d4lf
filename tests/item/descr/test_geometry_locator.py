from pathlib import Path

import numpy as np

from src.item.data.affix import Affix
from src.item.descr.geometry_locator import (
    _AFFIX_BULLET_TEMPLATE_REFS,
    _ASPECT_BULLET_TEMPLATE_REFS,
    LocatedMarker,
    _select_requested_markers,
    locate_affix_markers,
)
from src.item.descr.texture import _LONG_SEPARATOR_TEMPLATE_REFS
from src.item.models import Item
from src.template_finder import TemplateMatch

TEMPLATE_DIR = Path(__file__).parents[3] / "assets" / "templates" / "item_descr"
ASPECT_BULLET_PREFIXES = ("legendary_bullet_point", "mythic_bullet_point", "unique_bullet_point")


def _available_bullet_template_refs() -> set[str]:
    return {
        template.stem
        for template in TEMPLATE_DIR.glob("*.png")
        if "bullet_point" in template.stem or "affix_bullet" in template.stem
    }


def _available_long_separator_template_refs() -> set[str]:
    return {template.stem for template in TEMPLATE_DIR.glob("item_seperator_long_*.png")}


def test_locator_skips_template_matching_when_nothing_matched() -> None:
    result = locate_affix_markers(tooltip_image=np.zeros((80, 40, 3), dtype=np.uint8), item=Item())

    assert result.reliable
    assert result.markers == []


def test_production_locator_uses_untraced_bullet_search(mocker) -> None:
    separator = TemplateMatch(name="item_seperator_short_rare", center=(50, 40), region=[46, 36, 8, 8], score=0.9)
    long_separator = TemplateMatch(name="item_seperator_long_rare", center=(50, 180), region=[46, 176, 8, 8], score=0.9)
    bullet = TemplateMatch(name="affix_bullet_point_1", center=(10, 60), region=[6, 56, 8, 8], score=0.9)
    plain_search = mocker.patch("src.item.descr.texture.find_bullets_for_templates", return_value=[bullet])
    traced_search = mocker.patch(
        "src.item.descr.texture.find_bullets_for_templates_traced",
        side_effect=AssertionError("production must not collect diagnostics"),
    )
    mocker.patch("src.item.descr.texture.find_seperator_short", return_value=separator)
    mocker.patch("src.item.descr.texture.find_seperator_long", return_value=long_separator)
    affix = Affix(name="life")

    result = locate_affix_markers(
        tooltip_image=np.zeros((300, 100, 3), dtype=np.uint8), item=Item(affixes=[affix]), matched_affixes=[affix]
    )

    assert result.reliable
    assert plain_search.call_args.kwargs["max_y"] == long_separator.region[1]
    traced_search.assert_not_called()


def test_locator_uses_all_available_affix_bullet_templates() -> None:
    all_bullet_templates = _available_bullet_template_refs()
    expected_affix_templates = {
        template for template in all_bullet_templates if not template.startswith(ASPECT_BULLET_PREFIXES)
    }

    assert set(_AFFIX_BULLET_TEMPLATE_REFS) == expected_affix_templates


def test_locator_uses_all_available_aspect_bullet_templates() -> None:
    all_bullet_templates = _available_bullet_template_refs()
    expected_aspect_templates = {
        template for template in all_bullet_templates if template.startswith(ASPECT_BULLET_PREFIXES)
    }

    assert set(_ASPECT_BULLET_TEMPLATE_REFS) == expected_aspect_templates


def test_locator_uses_all_available_long_separator_templates() -> None:
    assert set(_LONG_SEPARATOR_TEMPLATE_REFS) == _available_long_separator_template_refs()


def test_select_requested_markers_returns_locator_markers_without_mutating_item() -> None:
    matched_affix = Affix(name="life")
    item = Item(affixes=[matched_affix, Affix(name="armor")])
    markers = [
        LocatedMarker(kind="affix", index=0, center=(20, 30), confidence=0.9),
        LocatedMarker(kind="affix", index=1, center=(20, 50), confidence=0.9),
    ]

    selected = _select_requested_markers(item, [matched_affix], False, markers)

    assert selected == [markers[0]]
