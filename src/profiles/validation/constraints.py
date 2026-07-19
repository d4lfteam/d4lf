GREATER_THAN_ZERO_ERROR = "must be greater than zero"
PERCENT_TOO_LARGE_ERROR = "must be less than or equal to 100"
GREATER_AFFIX_COUNT_ERROR = "must be in [0, 4]"


def check_greater_than_zero(v: int) -> int:
    if v < 0:
        raise ValueError(GREATER_THAN_ZERO_ERROR)
    return v


def validate_percent(v: int) -> int:
    check_greater_than_zero(v)
    if v > 100:
        raise ValueError(PERCENT_TOO_LARGE_ERROR)
    return v


def validate_greater_affix_count(v: int) -> int:
    if not 0 <= v <= 4:
        raise ValueError(GREATER_AFFIX_COUNT_ERROR)
    return v
