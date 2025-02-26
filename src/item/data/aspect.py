from dataclasses import dataclass


@dataclass
class Aspect:
    name: str
    loc: tuple[int, int] = None
    min_value: float = None
    max_value: float = None
    text: str = ""
    value: float = None

    def __eq__(self, other: "Aspect") -> bool:
        if not isinstance(other, Aspect):
            return False
        return self.name == other.name and self.value == other.value
