from src.tools.data_generation.datasets import string_list_value


def test_get_string_list_name_returns_a_stable_name() -> None:
    assert string_list_value({"arStrings": [{"szLabel": "name", "szText": "Example"}]}, "name") == "Example"
