import json
from typing import TYPE_CHECKING

import pytest

from src.item.data.loader import _load_string_map

if TYPE_CHECKING:
    from pathlib import Path


def test_load_string_map_returns_string_values(tmp_path: Path) -> None:
    path = tmp_path / "strings.json"
    path.write_text(json.dumps({"first": "one", "second": "two"}), encoding="utf-8")

    assert _load_string_map(path) == {"first": "one", "second": "two"}


@pytest.mark.parametrize("payload", [[], {"first": 1}, {"first": None}])
def test_load_string_map_rejects_non_string_maps(tmp_path: Path, payload: object) -> None:
    path = tmp_path / "strings.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="only string keys and values"):
        _load_string_map(path)
