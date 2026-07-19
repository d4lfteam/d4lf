from src.importing.conversion import as_string_keyed_mapping, as_string_keyed_mapping_list, as_text


def test_conversion_helpers_retain_only_string_data() -> None:
    assert as_string_keyed_mapping({"name": 1, 2: "ignored"}) == {"name": 1}
    assert as_string_keyed_mapping_list([{"name": 1}, "ignored"]) == [{"name": 1}]
    assert as_text("value") == "value"
    assert not as_text(None)
