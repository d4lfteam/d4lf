from typing import TYPE_CHECKING, cast

import numpy as np
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.perception.matching.config import SearchMode

from src.perception.matching import SearchConfig


def _invalid_search_mode() -> SearchMode:
    invalid_mode = "nearest".strip()
    return cast("SearchMode", invalid_mode)


def test_search_config_defaults_to_parallel_first_search() -> None:
    config = SearchConfig()

    assert config.mode == "first"
    assert config.use_parallel
    assert config.threshold == pytest.approx(0.7)


@pytest.mark.parametrize(
    ("config_factory", "message"),
    [
        (lambda: SearchConfig(mode=_invalid_search_mode()), "Invalid search mode"),
        (lambda: SearchConfig(timeout=-1), "timeout must not be negative"),
        (lambda: SearchConfig(threshold=np.inf), "threshold must be a finite number"),
        (lambda: SearchConfig(roi=[0, 0, 0, 10]), "roi must have a non-negative origin and positive dimensions"),
    ],
)
def test_search_config_rejects_invalid_values(config_factory: Callable[[], SearchConfig], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        config_factory()
