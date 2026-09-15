from dataclasses import dataclass
from typing import override


@dataclass
class Aspect:
    __hash__ = None

    name: str
    loc: tuple[int, int] | None = None
    min_value: float | None = None
    max_value: float | None = None
    text: str = ""
    value: float | None = None

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Aspect):
            return False
        return self.name == other.name and self.value == other.value
