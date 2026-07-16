def check_greater_than_zero(v: int) -> int:
    if v < 0:
        raise ValueError("must be greater than zero")
    return v


def validate_percent(v: int) -> int:
    check_greater_than_zero(v)
    if v > 100:
        raise ValueError("must be less than or equal to 100")
    return v


def validate_greater_affix_count(v: int) -> int:
    if not 0 <= v <= 4:
        raise ValueError("must be in [0, 4]")
    return v
