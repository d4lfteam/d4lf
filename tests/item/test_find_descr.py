from types import SimpleNamespace

import numpy as np

import src.item.find_descr as find_descr_module
from src.template_finder import SearchResult


def test_find_descr_ignores_successful_search_without_matches(monkeypatch) -> None:
    resources = SimpleNamespace(
        offsets=SimpleNamespace(item_descr_width=100, item_descr_pad=10),
        pos=SimpleNamespace(window_dimensions=(3840, 2160)),
        roi=SimpleNamespace(
            rel_descr_search_left=np.array([0, 0, 10, 10]), rel_descr_search_right=np.array([0, 0, 10, 10])
        ),
    )
    search_results = iter([SearchResult(success=True), SearchResult()])
    monkeypatch.setattr(find_descr_module, "get_ui_coordinates", lambda: resources)
    monkeypatch.setattr(find_descr_module, "_template_search", lambda *_args, **_kwargs: next(search_results))

    assert find_descr_module.find_descr(np.zeros((20, 20, 3), dtype=np.uint8), (0, 0)) == (False, None, None)
