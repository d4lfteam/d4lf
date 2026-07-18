from src.perception._text import clean_str, find_number, keep_letters_and_spaces


def test_text_helpers_normalize_numbers_and_punctuation() -> None:
    assert find_number("Damage +1,234", 0) == 1234
    assert keep_letters_and_spaces("A1-B!") == "AB"
    assert clean_str("+12% Movement Speed") == "movement speed"
