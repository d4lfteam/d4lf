import time
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")


def run_until_condition(
    func: Callable[[], T], is_success: Callable[[T], bool], timeout: float = 3
) -> tuple[T | None, bool]:
    """Poll a query until it succeeds or the timeout expires."""
    start_time = time.time()
    result: T | None = None
    while time.time() - start_time < timeout:
        result = func()
        if is_success(result):
            return result, True
        time.sleep(0.05)
    return result, False
