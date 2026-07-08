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
from src.item.models import Item

TEMPLATE_DIR = Path(__file__).parents[3] / "assets" / "templates" / "item_descr"
ASPECT_BULLET_PREFIXES = ("legendary_bullet_point", "mythic_bullet_point", "unique_bullet_point")


def _available_bullet_template_refs() -> set[str]:
    return {
        template.stem
        for template in TEMPLATE_DIR.glob("*.png")
        if "bullet_point" in template.stem or "affix_bullet" in template.stem
    }


def test_locator_skips_template_matching_when_nothing_matched() -> None:
    result = locate_affix_markers(tooltip_image=np.zeros((80, 40, 3), dtype=np.uint8), item=Item())

    assert result.reliable
    assert result.markers == []


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


def test_select_requested_markers_returns_locator_markers_without_mutating_item() -> None:
    matched_affix = Affix(name="life")
    item = Item(affixes=[matched_affix, Affix(name="armor")])
    markers = [
        LocatedMarker(kind="affix", index=0, center=(20, 30), confidence=0.9),
        LocatedMarker(kind="affix", index=1, center=(20, 50), confidence=0.9),
    ]

    selected = _select_requested_markers(item, [matched_affix], False, markers)

    assert selected == [markers[0]]
