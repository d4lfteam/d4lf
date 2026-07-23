import json

from src.tools.data_generation.common import get_power_id, string_list_map


def test_string_list_map_converts_localized_entries(tmp_path) -> None:
    path = tmp_path / "strings.json"
    path.write_text(json.dumps({"arStrings": [{"szLabel": "one", "szText": "One"}]}), encoding="utf-8")

    assert string_list_map(path) == {"one": "One"}


def test_get_power_id_extracts_file_stem() -> None:
    assert get_power_id({42: "powers/example.json"}, 42) == "example"
