import numpy as np
import pytest

from src.perception._matching_models import SearchArgs, TemplateMatch


def test_template_match_equality_uses_match_values() -> None:
    first = TemplateMatch(
        center=(1, 2), center_monitor=(1, 2), name="slot", region=[0, 0, 2, 2], region_monitor=[0, 0, 2, 2], score=0.9
    )

    assert first == TemplateMatch(
        center=(1, 2), center_monitor=(1, 2), name="slot", region=[0, 0, 2, 2], region_monitor=[0, 0, 2, 2], score=0.9
    )


def test_search_args_accepts_numpy_images() -> None:
    query = SearchArgs(ref=np.zeros((2, 2, 3), dtype=np.uint8), threshold=0.8)

    assert query.as_dict()["threshold"] == pytest.approx(0.8)
