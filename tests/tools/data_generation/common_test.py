import json

from src.tools.data_generation.common import get_power_id, string_list_map, write_json_file


def test_string_list_map_converts_localized_entries(tmp_path) -> None:
    path = tmp_path / "strings.json"
    path.write_text(json.dumps({"arStrings": [{"szLabel": "one", "szText": "One"}]}), encoding="utf-8")

    assert string_list_map(path) == {"one": "One"}


def test_get_power_id_extracts_file_stem() -> None:
    assert get_power_id({42: "powers/example.json"}, 42) == "example"


def test_write_json_file_formats_sorted_unescaped_with_trailing_newline(tmp_path) -> None:
    path = tmp_path / "out.json"

    write_json_file(path, {"b": "é", "a": [1]})

    assert path.read_text(encoding="utf-8") == '{\n    "a": [\n        1\n    ],\n    "b": "é"\n}\n'
