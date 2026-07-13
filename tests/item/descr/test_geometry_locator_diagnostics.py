from pathlib import Path

import cv2
import numpy as np
import pytest

from src.config.ui import ResManager
from src.item.data.affix import Affix
from src.item.data.aspect import Aspect
from src.item.data.item_type import ItemType
from src.item.descr.geometry_locator import (
    BulletMatchDiagnostics,
    DiagnosticLocatorResult,
    locate_affix_markers,
    locate_affix_markers_with_diagnostics,
)
from src.item.descr.texture import (
    BulletSearchTrace,
    _filter_outliers,
    find_bullets_for_templates,
    find_bullets_for_templates_traced,
)
from src.item.models import Item
from src.template_finder import SearchResult, TemplateMatch

TEMPLATE_DIR = Path(__file__).parents[3] / "assets" / "templates" / "item_descr"


@pytest.fixture(autouse=True)
def use_tooltip_fixture_resolution():
    resolution_manager = ResManager()
    previous_resolution = "x".join(str(value) for value in resolution_manager.resolution)
    resolution_manager.set_resolution("3840x2160")
    yield
    resolution_manager.set_resolution(previous_resolution)


def _make_tm(name: str, cx: int, cy: int, score: float = 0.9) -> TemplateMatch:
    return TemplateMatch(name=name, center=(cx, cy), region=[cx - 4, cy - 4, 8, 8], score=score)


def _realistic_tooltip_image() -> np.ndarray:
    image = np.zeros((600, 500, 3), dtype=np.uint8)
    separator = cv2.imread(str(TEMPLATE_DIR / "item_seperator_short_rare.png"), cv2.IMREAD_UNCHANGED)[:, :, :3]
    image[100 : 100 + separator.shape[0], : separator.shape[1]] = separator

    affix_bullet = cv2.imread(str(TEMPLATE_DIR / "affix_bullet_point_1.png"))
    for y in (150, 190):
        image[y : y + affix_bullet.shape[0], 10 : 10 + affix_bullet.shape[1]] = affix_bullet

    aspect_bullet = cv2.imread(str(TEMPLATE_DIR / "legendary_bullet_point.png"))
    image[250 : 250 + aspect_bullet.shape[0], 10 : 10 + aspect_bullet.shape[1]] = aspect_bullet
    return image


def test_diagnostic_result_uses_same_public_locator_result() -> None:
    first_affix = Affix(name="life")
    second_affix = Affix(name="armor")
    item = Item(affixes=[first_affix, second_affix], aspect=Aspect(name="test"))
    image = _realistic_tooltip_image()

    diagnostic = locate_affix_markers_with_diagnostics(
        tooltip_image=image, item=item, matched_affixes=[first_affix, second_affix], aspect_matched=True
    )
    plain = locate_affix_markers(
        tooltip_image=image, item=item, matched_affixes=[first_affix, second_affix], aspect_matched=True
    )

    assert isinstance(diagnostic, DiagnosticLocatorResult)
    assert diagnostic.result.reliable == plain.reliable
    assert [(marker.kind, marker.index) for marker in diagnostic.result.markers] == [
        (marker.kind, marker.index) for marker in plain.markers
    ]
    assert diagnostic.result.reliable
    assert [(marker.kind, marker.index) for marker in diagnostic.result.markers] == [
        ("affix", 0),
        ("affix", 1),
        ("aspect", 0),
    ]
    assert diagnostic.diagnostics.separator is not None
    assert diagnostic.diagnostics.separator.name == "item_seperator_short_rare"
    assert diagnostic.diagnostics.separator.region == [0, 100, 359, 22]
    assert diagnostic.diagnostics.affix_bullets is not None
    assert len(diagnostic.diagnostics.affix_bullets.raw) >= 2
    for match in diagnostic.diagnostics.affix_bullets.raw:
        assert match.name.startswith("affix_bullet_point")
        assert len(match.region) == 4
        assert match.confidence >= 0.8
    assert diagnostic.diagnostics.aspect_bullets is not None
    aspect_match = diagnostic.diagnostics.aspect_bullets.accepted[0]
    assert aspect_match.name.startswith("legendary_bullet_point")
    assert aspect_match.center[1] == 260
    assert aspect_match.confidence >= 0.8
    assert diagnostic.diagnostics.failure_reason is None
    assert diagnostic.diagnostics.selected_markers == diagnostic.result.markers


def test_diagnostic_result_skips_matching_when_nothing_matched() -> None:
    result = locate_affix_markers_with_diagnostics(tooltip_image=np.zeros((80, 40, 3), dtype=np.uint8), item=Item())

    assert result.result.reliable
    assert result.result.markers == []
    assert result.diagnostics.failure_reason is None
    assert result.diagnostics.separator is None


def test_missing_separator_is_reported(mocker) -> None:
    mocker.patch("src.item.descr.texture.find_seperator_short", return_value=None)
    affix = Affix(name="life")

    result = locate_affix_markers_with_diagnostics(
        tooltip_image=np.zeros((200, 100, 3), dtype=np.uint8), item=Item(affixes=[affix]), matched_affixes=[affix]
    )

    assert not result.result.reliable
    assert result.result.markers == []
    assert result.diagnostics.failure_reason == "missing_separator"
    assert result.diagnostics.separator is None


def test_insufficient_affix_rows_are_reported(mocker) -> None:
    separator = _make_tm("item_seperator_short_rare", 50, 40)
    bullet = _make_tm("affix_bullet_point_1", 10, 60)
    trace = BulletSearchTrace(raw=[bullet], accepted=[bullet])
    mocker.patch("src.item.descr.texture.find_seperator_short", return_value=separator)
    mocker.patch("src.item.descr.texture.find_seperator_long", return_value=None)
    mocker.patch("src.item.descr.texture.find_bullets_for_templates_traced", return_value=([bullet], trace))
    first_affix = Affix(name="life")
    second_affix = Affix(name="armor")

    result = locate_affix_markers_with_diagnostics(
        tooltip_image=np.zeros((200, 100, 3), dtype=np.uint8),
        item=Item(affixes=[first_affix, second_affix]),
        matched_affixes=[first_affix, second_affix],
    )

    assert not result.result.reliable
    assert result.diagnostics.failure_reason == "insufficient_affix_rows"
    assert result.diagnostics.affix_bullets is not None
    assert len(result.diagnostics.affix_bullets.accepted) == 1


def test_affix_search_stops_at_long_separator(mocker) -> None:
    short_separator = _make_tm("item_seperator_short_legendary", 50, 40)
    long_separator = _make_tm("item_seperator_long_legendary", 50, 180)
    bullet = _make_tm("affix_bullet_point_1", 10, 60)
    trace = BulletSearchTrace(raw=[bullet], accepted=[bullet])
    affix = Affix(name="life")

    mocker.patch("src.item.descr.texture.find_seperator_short", return_value=short_separator)
    mocker.patch("src.item.descr.texture.find_seperator_long", return_value=long_separator)
    find_bullets = mocker.patch(
        "src.item.descr.texture.find_bullets_for_templates_traced", return_value=([bullet], trace)
    )

    result = locate_affix_markers_with_diagnostics(
        tooltip_image=np.zeros((300, 100, 3), dtype=np.uint8), item=Item(affixes=[affix]), matched_affixes=[affix]
    )

    assert result.result.reliable
    assert result.diagnostics.long_separator is not None
    assert result.diagnostics.long_separator.region == long_separator.region
    assert find_bullets.call_args.kwargs["max_y"] == long_separator.region[1]


def test_long_separator_is_collected_for_aspect_only_replays(mocker) -> None:
    short_separator = _make_tm("item_seperator_short_legendary", 50, 40)
    long_separator = _make_tm("item_seperator_long_legendary", 50, 180)
    aspect_bullet = _make_tm("legendary_bullet_point", 10, 220)
    aspect_trace = BulletSearchTrace(raw=[aspect_bullet], accepted=[aspect_bullet])

    mocker.patch("src.item.descr.texture.find_seperator_short", return_value=short_separator)
    mocker.patch("src.item.descr.texture.find_seperator_long", return_value=long_separator)
    mocker.patch(
        "src.item.descr.texture.find_bullets_for_templates_traced", return_value=([aspect_bullet], aspect_trace)
    )

    result = locate_affix_markers_with_diagnostics(
        tooltip_image=np.zeros((300, 100, 3), dtype=np.uint8),
        item=Item(aspect=Aspect(name="test")),
        matched_affixes=[],
        aspect_matched=True,
    )

    assert result.diagnostics.long_separator is not None
    assert result.diagnostics.long_separator.region == long_separator.region


def test_outlier_filter_keeps_horizontal_template_variants() -> None:
    matches = [_make_tm("bullet", 10, 60), _make_tm("bullet_medium", 18, 90)]

    assert _filter_outliers(matches) == matches


def test_missing_aspect_marker_is_reported(mocker) -> None:
    separator = _make_tm("item_seperator_short_rare", 50, 40)
    affix_bullet = _make_tm("affix_bullet_point_1", 10, 60)
    affix_trace = BulletSearchTrace(raw=[affix_bullet], accepted=[affix_bullet])
    empty_trace = BulletSearchTrace()
    mocker.patch("src.item.descr.texture.find_seperator_short", return_value=separator)
    mocker.patch("src.item.descr.texture.find_seperator_long", return_value=None)
    mocker.patch(
        "src.item.descr.texture.find_bullets_for_templates_traced",
        side_effect=[([affix_bullet], affix_trace), ([], empty_trace)],
    )
    affix = Affix(name="life")

    result = locate_affix_markers_with_diagnostics(
        tooltip_image=np.zeros((200, 100, 3), dtype=np.uint8),
        item=Item(affixes=[affix], aspect=Aspect(name="test")),
        matched_affixes=[affix],
        aspect_matched=True,
    )

    assert not result.result.reliable
    assert result.diagnostics.failure_reason == "missing_aspect_marker"
    assert result.diagnostics.aspect_bullets == BulletMatchDiagnostics()


def test_low_confidence_selected_marker_is_reported(mocker) -> None:
    separator = _make_tm("item_seperator_short_rare", 50, 40)
    bullet = _make_tm("affix_bullet_point_1", 10, 60, score=0.75)
    trace = BulletSearchTrace(raw=[bullet], accepted=[bullet])
    mocker.patch("src.item.descr.texture.find_seperator_short", return_value=separator)
    mocker.patch("src.item.descr.texture.find_seperator_long", return_value=None)
    mocker.patch("src.item.descr.texture.find_bullets_for_templates_traced", return_value=([bullet], trace))
    affix = Affix(name="life")

    result = locate_affix_markers_with_diagnostics(
        tooltip_image=np.zeros((200, 100, 3), dtype=np.uint8), item=Item(affixes=[affix]), matched_affixes=[affix]
    )

    assert not result.result.reliable
    assert result.result.markers == []
    assert result.diagnostics.failure_reason == "marker_below_threshold"
    assert result.diagnostics.selected_markers[0].confidence == pytest.approx(0.75)


def test_trace_preserves_filter_stages_and_horadric_suppression(mocker) -> None:
    separator = _make_tm("item_seperator_short_rare", 50, 40)
    accepted = _make_tm("affix_bullet_point_1", 10, 60)
    duplicate = _make_tm("affix_bullet_point_1_medium", 10, 61, score=0.85)
    outlier = _make_tm("affix_bullet_point_2", 80, 62, score=0.88)
    mocker.patch(
        "src.item.descr.texture.search",
        side_effect=[
            SearchResult(matches=[separator], success=True),
            SearchResult(),
            SearchResult(matches=[accepted, duplicate, outlier], success=True),
        ],
    )
    affix = Affix(name="life")

    result = locate_affix_markers_with_diagnostics(
        tooltip_image=np.zeros((200, 100, 3), dtype=np.uint8),
        item=Item(item_type=ItemType.HoradricSeal, affixes=[affix]),
        matched_affixes=[affix],
    )

    assert not result.result.reliable
    assert result.diagnostics.failure_reason == "insufficient_affix_rows"
    assert result.diagnostics.affix_bullets is not None
    assert len(result.diagnostics.affix_bullets.rejected_outliers) == 1
    assert len(result.diagnostics.affix_bullets.rejected_duplicates) == 1
    assert len(result.diagnostics.affix_bullets.suppressed_horadric_seal) == 1


def test_plain_and_traced_bullet_searches_return_same_matches(mocker) -> None:
    first = _make_tm("affix_bullet_point_1", 10, 60)
    second = _make_tm("affix_bullet_point_1", 10, 90)
    mocker.patch("src.item.descr.texture.search", return_value=SearchResult(matches=[first, second], success=True))
    image = np.zeros((200, 100, 3), dtype=np.uint8)
    separator = _make_tm("item_seperator_short_rare", 50, 40)

    plain = find_bullets_for_templates(image, separator, ["affix_bullet_point_1"])
    traced, trace = find_bullets_for_templates_traced(image, separator, ["affix_bullet_point_1"])

    assert plain == traced
    assert trace.accepted == traced
