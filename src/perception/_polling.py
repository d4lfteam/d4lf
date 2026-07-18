import time
from typing import TypeVar

T = TypeVar("T")


def run_until_condition(func, is_success, timeout: float = 3) -> tuple[T | None, bool]:
    """Poll a query until it succeeds or the timeout expires."""
    start_time = time.time()
    result = None
    while time.time() - start_time < timeout:
        result = func()
        if is_success(result):
            return result, True
        time.sleep(0.05)
    return result, False
