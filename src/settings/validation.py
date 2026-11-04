def check_greater_than_zero(v: int) -> int:
    if v < 0:
        msg = "must be greater than zero"
        raise ValueError(msg)
    return v
