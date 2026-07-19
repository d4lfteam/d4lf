import json

import pytest

from src.item.data.loader import Dataloader, _load_string_map


def test_load_string_map_returns_string_values(tmp_path):
    path = tmp_path / "strings.json"
    path.write_text(json.dumps({"first": "one", "second": "two"}), encoding="utf-8")

    assert _load_string_map(path) == {"first": "one", "second": "two"}


@pytest.mark.parametrize("payload", [[], {"first": 1}, {"first": None}])
def test_load_string_map_rejects_non_string_maps(tmp_path, payload):
    path = tmp_path / "strings.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="only string keys and values"):
        _load_string_map(path)


def test_dataloader_has_expected_data_containers():
    assert isinstance(Dataloader.affix_dict, dict)
    assert isinstance(Dataloader.aspect_list, list)
