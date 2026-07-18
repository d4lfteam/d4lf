from src.perception._polling import run_until_condition


def test_run_until_condition_returns_the_first_successful_value() -> None:
    values = iter(["waiting", "ready"])

    result, succeeded = run_until_condition(lambda: next(values), lambda value: value == "ready")

    assert (result, succeeded) == ("ready", True)
