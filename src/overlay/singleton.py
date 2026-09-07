import threading
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.type_aliases import JsonValue

T = TypeVar("T")


def singleton(cls: type[T]) -> Callable[..., T]:
    instances: dict[type[T], T] = {}
    lock = threading.Lock()

    def get_instance(*args: JsonValue, **kwargs: JsonValue) -> T:
        with lock:
            if cls not in instances:
                instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance
