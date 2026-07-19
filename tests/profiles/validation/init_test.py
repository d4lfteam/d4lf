from src.profiles.validation import check_greater_than_zero, validate_percent


def test_validation_interface_exposes_constraints() -> None:
    assert check_greater_than_zero(1) == 1
    assert validate_percent(100) == 100
