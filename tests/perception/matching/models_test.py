import pytest

from src.perception.matching.models import ImageMatch, TemplateMatch


def test_image_match_keeps_image_region_and_score() -> None:
    match = ImageMatch(region=(1, 2, 3, 4), score=0.9)

    assert match.region == (1, 2, 3, 4)
    assert match.score == pytest.approx(0.9)


def test_template_match_equality_uses_match_values() -> None:
    first = TemplateMatch(
        center=(1, 2), center_monitor=(1, 2), name="slot", region=[0, 0, 2, 2], region_monitor=[0, 0, 2, 2], score=0.9
    )

    assert first == TemplateMatch(
        center=(1, 2), center_monitor=(1, 2), name="slot", region=[0, 0, 2, 2], region_monitor=[0, 0, 2, 2], score=0.9
    )
