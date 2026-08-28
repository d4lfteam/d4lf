from typing import TYPE_CHECKING

import numpy as np
import pytest

from src.perception.matching import SearchArgs, SearchResult

if TYPE_CHECKING:
    from src.type_aliases import JsonValue


def test_search_args_accepts_numpy_images() -> None:
    query = SearchArgs(ref=np.zeros((2, 2, 3), dtype=np.uint8), threshold=0.8)

    assert query.as_dict()["threshold"] == pytest.approx(0.8)


def test_search_args_detects_through_the_matching_facade(monkeypatch) -> None:
    image = np.zeros((2, 2, 3), dtype=np.uint8)
    observed: dict[str, JsonValue] = {}

    def fake_search(**kwargs):
        observed.update(kwargs)
        return SearchResult(success=True)

    monkeypatch.setattr("src.perception.matching.query.search", fake_search)
    query = SearchArgs(ref=image)

    result = query.detect(image)

    assert result.success
    assert observed["inp_img"] is image


def test_search_args_uses_a_captured_image_when_no_image_is_supplied(monkeypatch) -> None:
    captured = np.full((2, 2, 3), 7, dtype=np.uint8)
    observed: dict[str, JsonValue] = {}

    def fake_search(**kwargs):
        observed.update(kwargs)
        return SearchResult(success=True)

    monkeypatch.setattr("src.perception.matching.query.search", fake_search)
    monkeypatch.setattr("src.perception.matching.query.Cam.grab", lambda _self: captured)

    result = SearchArgs(ref=captured).detect()

    assert result.success
    assert observed["inp_img"] is captured
