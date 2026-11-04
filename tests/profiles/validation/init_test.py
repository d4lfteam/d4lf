from src.profiles.validation import validate_greater_affix_count, validate_percent


def test_validation_interface_exposes_constraints() -> None:
    assert validate_greater_affix_count(4) == 4
    assert validate_percent(100) == 100
