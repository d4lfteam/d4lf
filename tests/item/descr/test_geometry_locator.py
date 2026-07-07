import numpy as np

from src.item.data.affix import Affix
from src.item.data.aspect import Aspect
from src.item.descr.geometry_locator import (
    AffixMarkerLocator,
    AffixMarkerRequest,
    LocatedMarker,
    LocatorResult,
    apply_marker_locations,
)
from src.item.filter import FilterResult, MatchedFilter
from src.item.models import Item


def test_locator_skips_template_matching_when_nothing_matched() -> None:
    result = AffixMarkerLocator().locate(
        AffixMarkerRequest(tooltip_image=np.zeros((80, 40, 3), dtype=np.uint8), item=Item())
    )

    assert result.reliable
    assert result.markers == []


def test_low_confidence_locator_result_does_not_attach_marker_locations() -> None:
    matched_affix = Affix(name="life")
    item = Item(affixes=[matched_affix], aspect=Aspect(name="rapid"))
    filter_result = FilterResult(
        keep=True, matched=[MatchedFilter(profile="profile.yml", matched_affixes=[matched_affix], aspect_match=True)]
    )
    locator_result = LocatorResult(
        strategy="static",
        tooltip_found=True,
        markers=[LocatedMarker(kind="affix", index=0, center=(20, 30), confidence=0.4)],
        confidence=0.4,
        failure_reason="low confidence",
        reliable=False,
    )

    apply_marker_locations(item, filter_result, locator_result)

    assert matched_affix.loc is None
    assert item.aspect.loc is None
    assert filter_result.keep
