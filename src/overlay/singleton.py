import threading
from typing import TYPE_CHECKING, TypeVar, cast

if TYPE_CHECKING:
    from src.type_aliases import JsonValue

T = TypeVar("T")


def singleton(cls: type[T]) -> type[T]:
    instances: dict[type[T], T] = {}
    lock = threading.Lock()

    def get_instance(*args: JsonValue, **kwargs: JsonValue) -> T:
        with lock:
            if cls not in instances:
                instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return cast("type[T]", get_instance)
