from src.tools.data_generation.affix_helpers import replace_numeric_value_placeholders


def test_replace_numeric_value_placeholders_removes_formatting_tokens() -> None:
    description = "+{VALUE1} {c_number}{VALUE2}%"

    assert replace_numeric_value_placeholders(description) == "+# #%"
