from src.perception.matching.models import TemplateMatch


def test_template_match_equality_uses_match_values() -> None:
    first = TemplateMatch(
        center=(1, 2), center_monitor=(1, 2), name="slot", region=[0, 0, 2, 2], region_monitor=[0, 0, 2, 2], score=0.9
    )

    assert first == TemplateMatch(
        center=(1, 2), center_monitor=(1, 2), name="slot", region=[0, 0, 2, 2], region_monitor=[0, 0, 2, 2], score=0.9
    )
